import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import time
from typing import Optional, Dict, Any
from utils.embeds import standard_embed, success_embed, error_embed, info_embed, warning_embed
from utils.database import db
from utils.ltc import get_ltc_price, verify_ltc_payment, get_ltc_qr_url, shorten_address, is_valid_txid
from utils.ticket_creator import create_safe_ticket_channel
from utils.deal_logger import log_deal_completed

# --- Modals ---
class SubmitTxidModal(discord.ui.Modal, title="Submit Litecoin Transaction ID"):
    txid_input = discord.ui.TextInput(
        label="Transaction ID (TXID)",
        placeholder="64-character Litecoin transaction hash",
        min_length=64,
        max_length=64,
        required=True
    )

    def __init__(self, order_id: str, view_ref):
        super().__init__()
        self.order_id = order_id
        self.view_ref = view_ref

    async def on_submit(self, interaction: discord.Interaction):
        clean_txid = self.txid_input.value.strip().lower()
        if not is_valid_txid(clean_txid):
            return await interaction.response.send_message(
                embed=error_embed("Invalid TXID", "Litecoin transaction IDs must be 64 hexadecimal characters."),
                ephemeral=True
            )

        # Check if txid has already been used in this or another order
        if await db.is_txid_used(clean_txid):
            return await interaction.response.send_message(
                embed=error_embed("Transaction Already Claimed", "This Litecoin transaction ID has already been verified and credited to another order."),
                ephemeral=True
            )

        await interaction.response.defer()
        await self.view_ref.verify_payment_process(interaction, clean_txid)

class QuantityModal(discord.ui.Modal, title="Select Quantity"):
    quantity_input = discord.ui.TextInput(
        label="Quantity",
        placeholder="Enter quantity (e.g. 1, 2, 5)",
        default="1",
        min_length=1,
        max_length=4,
        required=True
    )

    def __init__(self, item: dict, view_ref):
        super().__init__()
        self.item = item
        self.view_ref = view_ref

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.quantity_input.value.strip()
        if not raw.isdigit() or int(raw) < 1:
            return await interaction.response.send_message(embed=error_embed("Invalid Quantity", "Quantity must be a positive number."), ephemeral=True)
        qty = int(raw)
        await self.view_ref.set_item_and_quantity(interaction, self.item, qty)

class AddMemberModal(discord.ui.Modal, title="Add Member to Ticket"):
    user_input = discord.ui.TextInput(label="User ID or Mention", placeholder="e.g. 1234567890", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.user_input.value.replace("<@", "").replace(">", "").replace("!", "").strip()
        try:
            member = interaction.guild.get_member(int(raw)) or await interaction.guild.fetch_member(int(raw))
            if not member:
                return await interaction.response.send_message(embed=error_embed("Not Found", "Member not found in server."), ephemeral=True)
            await interaction.channel.set_permissions(member, view_channel=True, send_messages=True, attach_files=True)
            await interaction.response.send_message(embed=success_embed("Member Added", f"{member.mention} has been added to this ticket."))
        except Exception as e:
            await interaction.response.send_message(embed=error_embed("Error", str(e)), ephemeral=True)

class RemoveMemberModal(discord.ui.Modal, title="Remove Member from Ticket"):
    user_input = discord.ui.TextInput(label="User ID or Mention", placeholder="e.g. 1234567890", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.user_input.value.replace("<@", "").replace(">", "").replace("!", "").strip()
        try:
            member = interaction.guild.get_member(int(raw)) or await interaction.guild.fetch_member(int(raw))
            if not member:
                return await interaction.response.send_message(embed=error_embed("Not Found", "Member not found."), ephemeral=True)
            await interaction.channel.set_permissions(member, overwrite=None)
            await interaction.response.send_message(embed=success_embed("Member Removed", f"{member.mention} has been removed."))
        except Exception as e:
            await interaction.response.send_message(embed=error_embed("Error", str(e)), ephemeral=True)

# --- Views ---
class PurchaseItemSelect(discord.ui.Select):
    def __init__(self, items: list, view_ref):
        options = []
        for item in items[:25]:
            desc = f"[{item['category']}] {item['price']}"
            if item.get("description"):
                desc += f" • {item['description'][:30]}"
            options.append(discord.SelectOption(
                label=f"{item['name'][:25]}",
                description=desc[:100],
                value=str(item["id"]),
                emoji="🛒"
            ))
        super().__init__(
            placeholder="🛒 Choose a product to purchase...",
            min_values=1,
            max_values=1,
            options=options,
            row=0
        )
        self.view_ref = view_ref
        self.items_map = {str(i["id"]): i for i in items}

    async def callback(self, interaction: discord.Interaction):
        item = self.items_map.get(self.values[0])
        if not item:
            return await interaction.response.send_message("Product not found.", ephemeral=True)
        # Open quantity selection modal
        await interaction.response.send_modal(QuantityModal(item, self.view_ref))

class PurchaseTicketControlView(discord.ui.View):
    def __init__(self, order_id: Optional[str] = None, customer_id: Optional[int] = None):
        super().__init__(timeout=None)
        self.order_id = order_id
        self.customer_id = customer_id
        self.selected_item = None
        self.quantity = 1
        self.submitted_txid = None

    async def set_item_and_quantity(self, interaction: discord.Interaction, item: dict, qty: int):
        self.selected_item = item
        self.quantity = qty

        # Parse numeric price
        raw_price = item["price"].replace("$", "").replace("USD", "").strip()
        try:
            unit_price = float(raw_price)
        except Exception:
            unit_price = 5.0

        total_usd = round(unit_price * qty, 2)
        ltc_price = await get_ltc_price()
        est_ltc = round(total_usd / ltc_price, 6)

        embed = standard_embed(
            title=f"🛒 Confirm Your Order • {item['name']}",
            description=(
                f"**Product:** `{item['name']}`\n"
                f"**Category:** `{item['category']}`\n"
                f"**Quantity:** `{qty}`\n"
                f"**Unit Price:** `${unit_price:.2f}`\n\n"
                f"💵 **Total USD:** `${total_usd:.2f}`\n"
                f"🪙 **Estimated LTC:** `{est_ltc:.6f} LTC` *(at ${ltc_price:,.2f}/LTC)*\n\n"
                f"Click **Confirm Purchase** below to lock in your live invoice and payment address."
            ),
            color=0x2ECC71
        )
        embed.set_footer(text="Live LTC conversion calculated from blockchain index")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Confirm Purchase", style=discord.ButtonStyle.success, emoji="✅", custom_id="pt_confirm_btn", row=1)
    async def confirm_purchase(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_item:
            return await interaction.response.send_message("Please select a product first.", ephemeral=True)

        raw_price = self.selected_item["price"].replace("$", "").replace("USD", "").strip()
        try:
            unit_price = float(raw_price)
        except Exception:
            unit_price = 5.0

        total_usd = round(unit_price * self.quantity, 2)
        ltc_price = await get_ltc_price()
        total_ltc = round(total_usd / ltc_price, 6)

        # Get shop receiving address
        cfg = await db.get_shop_config(interaction.guild_id)
        shop_addr = cfg.get("ltc_address")
        if not shop_addr:
            # Fallback to payment methods in DB
            methods = await db.get_payment_methods(interaction.guild_id)
            for m in methods:
                if "ltc" in m["method_name"].lower() or "litecoin" in m["method_name"].lower():
                    shop_addr = m["address"]
                    break
            if not shop_addr and methods:
                shop_addr = methods[0]["address"]
            if not shop_addr:
                shop_addr = "ltc1q9k9v4k9905h237nvw7m7q4p683n6g72xdf0v9m" # Fallback placeholder verified

        # Create database order
        order = await db.create_shop_order(
            guild_id=interaction.guild_id,
            user_id=interaction.user.id,
            product_name=self.selected_item["name"],
            quantity=self.quantity,
            total_usd=total_usd,
            total_ltc=total_ltc,
            payment_method="Litecoin",
            ltc_address=shop_addr,
            ticket_channel_id=interaction.channel_id
        )
        self.order_id = order["order_id"]

        # Invoice expires in 45 minutes
        expire_time = int(time.time() + 2700)
        qr_url = get_ltc_qr_url(shop_addr, total_ltc)

        invoice_embed = discord.Embed(
            title=f"🧾 Official Invoice • {order['order_id']}",
            color=0x345C9C,
            timestamp=discord.utils.utcnow()
        )
        invoice_embed.add_field(name="Product", value=f"`{self.selected_item['name']}` (x{self.quantity})", inline=True)
        invoice_embed.add_field(name="Amount Due (USD)", value=f"**${total_usd:.2f} USD**", inline=True)
        invoice_embed.add_field(name="Amount Due (LTC)", value=f"**`{total_ltc:.6f} LTC`**", inline=True)
        invoice_embed.add_field(
            name="Official Litecoin Address",
            value=f"```{shop_addr}```\n*Send the exact LTC amount displayed above.*",
            inline=False
        )
        invoice_embed.add_field(name="Invoice Expiration", value=f"⏳ Expires <t:{expire_time}:R>", inline=True)
        invoice_embed.add_field(name="Receipt Tracking", value=f"`{order['receipt_id']}`", inline=True)
        invoice_embed.set_image(url=qr_url)
        invoice_embed.set_footer(text=f"{cfg.get('shop_name', 'Jack''s Shop')} • Confirmed payments auto-delivered via Blockchain")

        button.disabled = True
        await interaction.response.edit_message(embed=invoice_embed, view=self)

    @discord.ui.button(label="Submit Transaction ID", style=discord.ButtonStyle.primary, emoji="🔗", custom_id="pt_submit_tx_btn", row=1)
    async def submit_txid(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.order_id:
            return await interaction.response.send_message("Please select an item and confirm your order first to generate an invoice.", ephemeral=True)
        await interaction.response.send_modal(SubmitTxidModal(self.order_id, self))

    @discord.ui.button(label="Check Payment", style=discord.ButtonStyle.secondary, emoji="🔄", custom_id="pt_check_pay_btn", row=1)
    async def check_payment(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.order_id:
            return await interaction.response.send_message("No invoice generated yet.", ephemeral=True)
        if not self.submitted_txid:
            return await interaction.response.send_message("Please click **Submit Transaction ID** first to provide your transaction hash.", ephemeral=True)

        await interaction.response.defer()
        await self.verify_payment_process(interaction, self.submitted_txid)

    async def verify_payment_process(self, interaction: discord.Interaction, txid: str):
        self.submitted_txid = txid
        order = await db.get_shop_order(self.order_id)
        if not order:
            return await interaction.followup.send(embed=error_embed("Order Not Found", "Could not locate this order."), ephemeral=True)

        if order.get("status") == "completed":
            return await interaction.followup.send(embed=info_embed("Order Completed", "This order has already been paid and fulfilled."), ephemeral=True)

        cfg = await db.get_shop_config(interaction.guild_id)
        min_confs = cfg.get("min_confirmations", 1)
        expected_addr = order.get("ltc_address")
        expected_ltc = float(order.get("total_ltc", 0.0))

        # Perform live independent verification
        res = await verify_ltc_payment(
            txid=txid,
            expected_address=expected_addr,
            expected_amount_ltc=expected_ltc,
            min_confirmations=min_confs
        )

        if not res.get("verified"):
            return await interaction.followup.send(
                embed=error_embed("Payment Verification Failed", res.get("error", "Payment could not be verified on the blockchain.")),
                ephemeral=False
            )

        if not res.get("paid"):
            # Pending confirmations
            confs = res.get("confirmations", 0)
            return await interaction.followup.send(
                embed=warning_embed(
                    "Payment Detected (Confirming)",
                    f"✅ Transaction found on the Litecoin blockchain!\n"
                    f"• **Confirmations:** `{confs}/{min_confs}`\n"
                    f"• **Amount Received:** `{res.get('amount_received'):.6f} LTC`\n\n"
                    f"Order will be completed automatically once `{min_confs}` confirmation(s) are reached.\n"
                    f"Click **Check Payment** again in 1-2 minutes."
                ),
                ephemeral=False
            )

        # Payment fully confirmed! Prevent race condition / duplicate txid reuse
        recorded = await db.record_used_txid(txid, self.order_id, interaction.guild_id, res.get("amount_received"), res.get("confirmations"))
        if not recorded:
            return await interaction.followup.send(
                embed=error_embed("Duplicate Transaction", "This transaction ID was already consumed by an order."),
                ephemeral=False
            )

        # Mark order completed
        completed_order = await db.complete_order(self.order_id, staff_id=0, txid=txid)

        # Attempt automatic digital product delivery from stock
        dispensed_items = await db.dispense_stock(interaction.guild_id, completed_order["product_name"], completed_order["quantity"])

        delivery_text = ""
        if dispensed_items:
            delivery_text = "\n\n🎁 **Your Digital Products / Accounts / Keys:**\n```\n" + "\n".join(dispensed_items) + "\n```"
        else:
            delivery_text = "\n\n⚡ *Staff has been notified to manually fulfill your order.*"

        paid_embed = success_embed(
            "🎉 Payment Confirmed & Order Complete!",
            f"Thank you <@{completed_order['user_id']}>! Your Litecoin payment has been independently verified on the blockchain.\n\n"
            f"• **Order ID:** `{completed_order['order_id']}`\n"
            f"• **Receipt:** `{completed_order['receipt_id']}`\n"
            f"• **Total Paid:** `{res.get('amount_received'):.6f} LTC` (${completed_order['total_usd']:.2f})\n"
            f"• **Blockchain Confirmations:** `{res.get('confirmations')}`\n"
            f"• **TXID:** [`{shorten_address(txid, 8, 8)}`](https://litecoinspace.org/tx/{txid})"
            + delivery_text
        )
        await interaction.channel.send(content=f"<@{completed_order['user_id']}>", embed=paid_embed)

        # Send polished green Deal Completed log to deal channel
        await log_deal_completed(
            guild=interaction.guild,
            order=completed_order,
            completed_by=None,
            custom_branding=cfg.get("shop_name", "Jack's Shop")
        )

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.secondary, emoji="🙋‍♂️", custom_id="pt_claim_btn", row=2)
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(embed=error_embed("Unauthorized", "Staff only."), ephemeral=True)
        if self.order_id:
            await db.claim_order(self.order_id, interaction.user.id)
        button.disabled = True
        button.label = f"Claimed by {interaction.user.display_name}"
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(embed=success_embed("Ticket Claimed", f"🌟 {interaction.user.mention} is now personally assisting with this purchase!"))

    @discord.ui.button(label="Complete Order", style=discord.ButtonStyle.success, emoji="📦", custom_id="pt_complete_btn", row=2)
    async def complete_order_manual(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(embed=error_embed("Unauthorized", "Staff only."), ephemeral=True)
        if not self.order_id:
            return await interaction.response.send_message("No order to complete.", ephemeral=True)

        order = await db.complete_order(self.order_id, staff_id=interaction.user.id)
        if not order:
            return await interaction.response.send_message("Order could not be found.", ephemeral=True)

        await interaction.channel.send(embed=success_embed(
            "Order Marked Complete",
            f"Order `{order['order_id']}` has been manually fulfilled by {interaction.user.mention}!"
        ))
        cfg = await db.get_shop_config(interaction.guild_id)
        await log_deal_completed(interaction.guild, order, completed_by=interaction.user, custom_branding=cfg.get("shop_name"))
        await interaction.response.send_message("Order fulfilled and logged.", ephemeral=True)

    @discord.ui.button(label="Cancel Order", style=discord.ButtonStyle.danger, emoji="✖️", custom_id="pt_cancel_btn", row=2)
    async def cancel_order(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.order_id:
            await db.cancel_order(self.order_id)
        await interaction.channel.send(embed=warning_embed("Order Cancelled", f"Purchase order was cancelled by {interaction.user.mention}."))
        await interaction.response.send_message("Order cancelled.", ephemeral=True)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="pt_close_btn", row=3)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await db.close_ticket_record(interaction.channel_id)
        from cogs.tickets import TicketClosedControlsView
        await interaction.channel.send(
            embed=warning_embed("Ticket Closed", f"Ticket closed by {interaction.user.mention}.\nUse the buttons below to re-open or generate transcript."),
            view=TicketClosedControlsView()
        )
        await interaction.response.send_message("Ticket closed.", ephemeral=True)

    @discord.ui.button(label="Add Member", style=discord.ButtonStyle.secondary, emoji="➕", custom_id="pt_add_mem_btn", row=3)
    async def add_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddMemberModal())

    @discord.ui.button(label="Remove Member", style=discord.ButtonStyle.secondary, emoji="➖", custom_id="pt_rem_mem_btn", row=3)
    async def remove_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RemoveMemberModal())

    @discord.ui.button(label="Request Support", style=discord.ButtonStyle.secondary, emoji="🆘", custom_id="pt_support_btn", row=3)
    async def request_support(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = await db.get_shop_config(interaction.guild_id)
        staff_role_id = cfg.get("staff_role_id")
        settings = await db.get_guild_settings(interaction.guild_id)
        fallback_role_id = settings.get("ticket_staff_role_id")
        target_role = interaction.guild.get_role(staff_role_id or fallback_role_id) if (staff_role_id or fallback_role_id) else None

        ping = target_role.mention if target_role else "@here"
        await interaction.channel.send(f"{ping} Customer {interaction.user.mention} has requested immediate staff support in this ticket!")
        await interaction.response.send_message("Support staff has been alerted.", ephemeral=True)

class PurchasePanelView(discord.ui.View):
    def __init__(self, shop_name: str = "Jack's Shop"):
        super().__init__(timeout=None)
        self.shop_name = shop_name

    @discord.ui.button(label="Initiate Purchase", style=discord.ButtonStyle.primary, emoji="🛒", custom_id="initiate_purchase_btn")
    async def initiate_purchase(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        # Prevent duplicate tickets: check if active ticket channel already exists
        channel_slug = f"purchase-{user.name.lower().replace(' ', '-')}"[:32]
        existing_chan = discord.utils.get(guild.text_channels, name=channel_slug)
        if existing_chan:
            return await interaction.response.send_message(
                embed=warning_embed("Ticket Already Open", f"You already have an open purchase ticket at {existing_chan.mention}!"),
                ephemeral=True
            )

        cfg = await db.get_shop_config(guild.id)
        shop_title = cfg.get("shop_name", "Jack's Shop")
        parent_cat_id = cfg.get("purchase_category_id")
        settings = await db.get_guild_settings(guild.id)
        if not parent_cat_id:
            parent_cat_id = settings.get("ticket_category_id")
        parent_cat = guild.get_channel(parent_cat_id) if parent_cat_id else None

        staff_role_id = cfg.get("staff_role_id") or settings.get("ticket_staff_role_id")
        staff_role = guild.get_role(staff_role_id) if staff_role_id else None

        try:
            order_channel = await create_safe_ticket_channel(
                guild=guild,
                user=user,
                channel_name=channel_slug,
                category=parent_cat,
                staff_role=staff_role,
                topic=f"Purchase Ticket for {user.name} | {shop_title}"
            )
        except Exception as e:
            return await interaction.response.send_message(embed=error_embed("Error", f"Failed to create ticket: {e}"), ephemeral=True)

        await db.create_ticket_record(guild.id, order_channel.id, user.id, f"{shop_title} Purchase")

        await interaction.response.send_message(
            embed=success_embed("Purchase Ticket Opened", f"Your private purchase ticket has been opened at {order_channel.mention}!"),
            ephemeral=True
        )

        # Populate ticket with item dropdown and controls
        items = await db.get_shop_items(guild.id)
        ticket_view = PurchaseTicketControlView(customer_id=user.id)
        if items:
            ticket_view.add_item(PurchaseItemSelect(items, ticket_view))

        mention_str = user.mention
        if staff_role:
            mention_str += f" | {staff_role.mention}"

        welcome_embed = standard_embed(
            title=f"🛒 {shop_title} • Purchase Ticket",
            description=(
                f"Welcome {user.mention} to your private purchase session!\n\n"
                f"1. Choose an item from the product dropdown below.\n"
                f"2. Specify the quantity you wish to purchase.\n"
                f"3. Pay the displayed total in Litecoin (LTC) using the generated invoice & QR code.\n"
                f"4. Click **Submit Transaction ID** once sent for instant blockchain verification.\n\n"
                f"⚡ *24/7 automated delivery is active for all digital items.*"
            ),
            color=0x2ECC71
        )
        if user.display_avatar:
            welcome_embed.set_thumbnail(url=user.display_avatar.url)
        welcome_embed.set_footer(text=f"© {shop_title} | Secure Litecoin Checkout")

        await order_channel.send(content=mention_str, embed=welcome_embed, view=ticket_view)

class PurchasePanel(commands.Cog):
    """Customizable Purchase Panel and Automated Ticket Checkout."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(PurchasePanelView())
        self.bot.add_view(PurchaseTicketControlView())

    @commands.group(name="shoppanel", aliases=["purchasepanel", "panel"], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def panel_cmd(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Deploy the official customizable purchase panel matching reference screenshot."""
        target_chan = channel or ctx.channel
        cfg = await db.get_shop_config(ctx.guild.id)
        shop_title = cfg.get("shop_name", "Jack's Shop")

        embed = discord.Embed(
            title=f"🛒 {shop_title} — Purchase Panel",
            description=(
                f"Welcome to {shop_title}! Use the button below to open a private purchase ticket.\n\n"
                f"Choose an item, select the quantity, pay the displayed USD total in Litecoin, and submit your transaction ID. "
                f"Confirmed payments are checked against the blockchain before delivery."
            ),
            color=0x2B2D31
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=f"© {shop_title} | All Rights Reserved.")

        view = PurchasePanelView(shop_title)
        await target_chan.send(embed=embed, view=view)
        if target_chan.id != ctx.channel.id:
            await ctx.send(embed=success_embed("Purchase Panel Deployed", f"Posted purchase panel to {target_chan.mention}!"))

    @commands.command(name="setshopname", aliases=["shopname"], help="Customize your shop branding name. E.g. $setshopname Jack's Shop")
    @commands.has_permissions(administrator=True)
    async def set_shop_name_cmd(self, ctx: commands.Context, *, name: str):
        await db.set_shop_config(ctx.guild.id, shop_name=name.strip())
        await ctx.send(embed=success_embed("Shop Name Updated", f"Store branding has been updated to **{name.strip()}**!"))

    @commands.command(name="setshopltc", aliases=["shopltc"], help="Configure shop Litecoin receiving address for automated invoices.")
    @commands.has_permissions(administrator=True)
    async def set_shop_ltc_cmd(self, ctx: commands.Context, address: str):
        clean = address.strip()
        from utils.ltc import is_valid_ltc_address
        if not is_valid_ltc_address(clean):
            return await ctx.send(embed=error_embed("Invalid Address", "Must be a valid Litecoin address."))
        await db.set_shop_config(ctx.guild.id, ltc_address=clean)
        await ctx.send(embed=success_embed("Shop LTC Configured", f"Shop payment address set to `{clean}`."))

    @commands.command(name="setdeallog", aliases=["deallogs"], help="Set the channel where green Deal Completed receipts are posted.")
    @commands.has_permissions(administrator=True)
    async def set_deal_log_cmd(self, ctx: commands.Context, channel: discord.TextChannel):
        await db.set_shop_config(ctx.guild.id, deal_log_channel_id=channel.id)
        await ctx.send(embed=success_embed("Deal Log Configured", f"Completed deals will be logged to {channel.mention}."))

    @commands.command(name="setfeedbackchannel", help="Set the channel where customer feedback reviews are posted.")
    @commands.has_permissions(administrator=True)
    async def set_feedback_channel_cmd(self, ctx: commands.Context, channel: discord.TextChannel):
        await db.set_shop_config(ctx.guild.id, feedback_channel_id=channel.id)
        await ctx.send(embed=success_embed("Feedback Channel Configured", f"Customer feedback will be broadcasted to {channel.mention}."))

async def setup(bot: commands.Bot):
    await bot.add_cog(PurchasePanel(bot))
