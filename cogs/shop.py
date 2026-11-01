import discord
from discord.ext import commands
from typing import Optional
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db
from cogs.tickets import TicketControlsView
from utils.ticket_creator import create_safe_ticket_channel

class ShopItemSelect(discord.ui.Select):
    def __init__(self, items: list):
        options = []
        for item in items[:25]:
            options.append(discord.SelectOption(
                label=f"{item['name'][:25]} - {item['price']}",
                description=f"[{item['category']}] {item['description'][:50]}" if item['description'] else f"Category: {item['category']}",
                value=str(item['id']),
                emoji="🛒"
            ))

        super().__init__(
            placeholder="🛒 Select an item to purchase / order...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        item_id = int(self.values[0])
        item = await db.get_shop_item(item_id)
        if not item:
            return await interaction.response.send_message(embed=error_embed("Not Found", "Item no longer exists in shop."), ephemeral=True)

        guild = interaction.guild
        user = interaction.user

        settings = await db.get_guild_settings(guild.id)
        parent_cat_id = settings.get("ticket_category_id")
        parent_cat = guild.get_channel(parent_cat_id) if parent_cat_id else None

        staff_role_id = settings.get("ticket_staff_role_id")
        staff_role = guild.get_role(staff_role_id) if staff_role_id else None

        # Create private order ticket channel
        clean_user = user.name.lower().replace(" ", "-")
        channel_name = f"order-{clean_user}"

        try:
            order_channel = await create_safe_ticket_channel(
                guild=guild,
                user=user,
                channel_name=channel_name,
                category=parent_cat,
                staff_role=staff_role,
                topic=f"Order Ticket for {user.name} | Product: {item['name']} ({item['price']})"
            )
        except Exception as e:
            return await interaction.response.send_message(embed=error_embed("Error", f"Failed to create order ticket: {str(e)}"), ephemeral=True)

        await db.create_ticket_record(guild.id, order_channel.id, user.id, f"Shop Order: {item['name']}")

        await interaction.response.send_message(
            embed=success_embed("Order Ticket Created", f"Your order ticket for **{item['name']}** has been opened at {order_channel.mention}!"),
            ephemeral=True
        )

        pings = user.mention
        if staff_role:
            pings += f" | {staff_role.mention}"

        order_embed = standard_embed(
            title=f"🛒 Purchase Order: {item['name']}",
            description=(
                f"Thank you for your order {user.mention}!\n\n"
                f"**Product:** `{item['name']}`\n"
                f"**Price:** `{item['price']}`\n"
                f"**Category:** `{item['category']}`\n"
                f"**Details:**\n```{item['description'] or 'No extra description provided.'}```\n"
                f"Support staff will provide payment information and fulfill your order here."
            ),
            thumbnail=user.display_avatar.url
        )
        await order_channel.send(content=pings, embed=order_embed, view=TicketControlsView())

class AddPaymentModal(discord.ui.Modal, title="Add Payment Gateway"):
    method_name = discord.ui.TextInput(
        label="Method Name",
        placeholder="e.g. Litecoin (LTC), PayPal, CashApp",
        required=True
    )
    address = discord.ui.TextInput(
        label="Wallet Address / Payment Info",
        placeholder="e.g. ltc1q9k9... or billing@paypal.com",
        required=True
    )
    note = discord.ui.TextInput(
        label="Note / Memo (Optional)",
        placeholder="e.g. 1 confirmation required, F&F only",
        required=False
    )

    def __init__(self, guild_id: int):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        mid = await db.add_payment_method(
            self.guild_id,
            self.method_name.value.strip(),
            self.address.value.strip(),
            self.note.value.strip() if self.note.value else ""
        )
        embed = success_embed(
            "Payment Gateway Added",
            f"**ID:** `#{mid}`\n"
            f"**Method:** `{self.method_name.value.strip()}`\n"
            f"**Address:** `{self.address.value.strip()}`\n"
            f"**Note:** {self.note.value.strip() or 'None'}\n\n"
            f"Run `$payment` to view your updated payment gateways."
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class PaymentDeleteSelect(discord.ui.Select):
    def __init__(self, methods: list, guild_id: int):
        self.guild_id = guild_id
        options = []
        for m in methods[:25]:
            note = f" | {m['note']}" if m.get('note') else ""
            desc = (f"{m['address'][:40]}..." if len(m['address']) > 40 else m['address']) + note
            options.append(discord.SelectOption(
                label=f"#{m['id']} • {m['method_name'][:25]}",
                description=desc[:100],
                value=str(m['id']),
                emoji="🗑️"
            ))
        super().__init__(
            placeholder="🗑️ Select a payment method to delete...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(embed=error_embed("Unauthorized", "Only administrators can remove payment methods."), ephemeral=True)

        target_id = int(self.values[0])
        removed = await db.remove_payment_method(self.guild_id, target_id)
        if removed:
            await interaction.response.send_message(
                embed=success_embed("Payment Method Removed", f"Successfully deleted payment method `#{target_id}` from the shop."),
                ephemeral=True
            )
            try:
                methods_left = await db.get_payment_methods(self.guild_id)
                if methods_left:
                    new_desc = (
                        "> Choose a payment method from the dropdown below to remove it immediately,\n"
                        "> or run `$delpayment <ID or Name>` directly.\n\n"
                        "**Remaining Methods in Shop:**\n" +
                        "\n".join([f"• **#{m['id']}** — `{m['method_name']}` (`{m['address'][:25]}...`)" for m in methods_left])
                    )
                    new_embed = standard_embed(title="🗑️ Select Payment Method to Remove", description=new_desc, color=0xED4245)
                    await interaction.message.edit(embed=new_embed, view=PaymentDeleteView(methods_left, self.guild_id))
                else:
                    await interaction.message.edit(embed=info_embed("Payment Methods", "All payment methods have been removed."), view=None)
            except Exception:
                pass
        else:
            await interaction.response.send_message(embed=error_embed("Not Found", "That payment method was already deleted."), ephemeral=True)

class PaymentDeleteView(discord.ui.View):
    def __init__(self, methods: list, guild_id: int):
        super().__init__(timeout=180)
        self.add_item(PaymentDeleteSelect(methods, guild_id))

class PaymentAdminControlsView(discord.ui.View):
    def __init__(self, methods: list, guild_id: int):
        super().__init__(timeout=180)
        self.methods = methods
        self.guild_id = guild_id

    @discord.ui.button(label="Add Payment Method", style=discord.ButtonStyle.success, emoji="➕")
    async def add_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Only Administrators can add payment methods.", ephemeral=True)
        await interaction.response.send_modal(AddPaymentModal(self.guild_id))

    @discord.ui.button(label="Delete Payment Method", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def del_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Only Administrators can delete payment methods.", ephemeral=True)
        curr_methods = await db.get_payment_methods(self.guild_id)
        if not curr_methods:
            return await interaction.response.send_message(embed=info_embed("No Payment Methods", "No payment methods configured yet."), ephemeral=True)
        view = PaymentDeleteView(curr_methods, self.guild_id)
        embed = standard_embed(
            title="🗑️ Select Payment Method to Delete",
            description=(
                "> Choose a payment method from the dropdown below to delete it from the storefront,\n"
                "> or run `$delpayment <ID or Name>` directly.\n\n"
                "**Active Methods:**\n" +
                "\n".join([f"• **#{m['id']}** — `{m['method_name']}`" for m in curr_methods])
            ),
            color=0xED4245
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class ShopQuickButtons(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=180)
        self.guild_id = guild_id

    @discord.ui.button(label="Payment Methods", style=discord.ButtonStyle.secondary, emoji="💳")
    async def pay_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        target_gid = self.guild_id or interaction.guild_id
        methods = await db.get_payment_methods(target_gid)
        if not methods:
            return await interaction.response.send_message(embed=info_embed("Payment Gateways", "No payment methods configured yet.\n*Admins can add methods using `$setpayment`.*"), ephemeral=True)
        embed = standard_embed(
            title=f"💳 {interaction.guild.name} • Official Payment Gateways",
            description=(
                "> Send funds only to the verified addresses below. Confirm tx ID in ticket.\n\n"
                "💡 **Admin Quick Guide:**\n"
                "• **Add:** `$setpayment <Name> | <Address> | [Note]`\n"
                "• **Delete:** `$delpayment <ID or Name>` (e.g. `$delpayment 1` or `$delpayment LTC`)\n"
            ),
            color=0x2ECC71
        )
        for m in methods:
            note_str = f"\n└ ℹ️ *{m['note']}*" if m.get('note') else ""
            embed.add_field(
                name=f"💳 #{m['id']} • {m['method_name']}",
                value=f"```{m['address']}```{note_str}",
                inline=False
            )
        embed.set_footer(text="Zyath Financial Security • Verified Addresses")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Terms of Service", style=discord.ButtonStyle.secondary, emoji="📜")
    async def tos_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        target_gid = self.guild_id or interaction.guild_id
        tos_text = await db.get_shop_tos(target_gid)
        if not tos_text:
            tos_text = (
                "**1. General Policy:** All sales are final once delivered unless specified otherwise.\n"
                "**2. Warranty & Proof:** Replacements are provided within warranty period with valid unedited proof.\n"
                "**3. Payment Verification:** Only send payments to official addresses in `$payment`.\n"
                "**4. Scams & Chargebacks:** Chargebacks result in a permanent ban & universal blacklist."
            )
        embed = standard_embed(
            title=f"📜 {interaction.guild.name} • Storefront Terms & Warranty",
            description=tos_text,
            color=0xFEE75C
        )
        embed.set_footer(text="By ordering from our store, you agree to these terms.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Reputation & Vouches", style=discord.ButtonStyle.secondary, emoji="⭐")
    async def vouch_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        target_gid = self.guild_id or interaction.guild_id
        stats = await db.get_server_vouch_stats(target_gid)
        total = stats.get("total", 0)
        avg = stats.get("avg_rating", 0.0)
        embed = standard_embed(
            title=f"⭐ {interaction.guild.name} • Verified Community Reputation",
            description=(
                f"> **Total Vouches Recorded:** `{total}`\n"
                f"> **Customer Satisfaction Rating:** `⭐ {avg}/5.0`\n"
                f"> **Reputation Index:** ▰▰▰▰▰▰▰▰▰▰ `100% Verified`\n\n"
                f"Type `$vouchlb` to see our top trusted sellers or `$vouches @user` to inspect any member."
            ),
            color=0xFEE75C
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ShopView(discord.ui.View):
    def __init__(self, items: list, guild_id: int = None):
        super().__init__(timeout=180)
        self.guild_id = guild_id or (items[0].get("guild_id") if (items and isinstance(items[0], dict)) else None)
        if items:
            self.add_item(ShopItemSelect(items))

    @discord.ui.button(label="Payment Methods", style=discord.ButtonStyle.secondary, emoji="💳", row=1)
    async def pay_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        target_gid = self.guild_id or interaction.guild_id
        methods = await db.get_payment_methods(target_gid)
        if not methods:
            return await interaction.response.send_message(embed=info_embed("Payment Gateways", "No payment methods configured yet.\n*Admins can add methods using `$setpayment`.*"), ephemeral=True)
        embed = standard_embed(
            title=f"💳 {interaction.guild.name} • Official Payment Gateways",
            description=(
                "> Send funds only to the verified addresses below. Confirm transaction in ticket.\n\n"
                "💡 **Admin Quick Guide:**\n"
                "• **Add:** `$setpayment <Name> | <Address> | [Note]`\n"
                "• **Delete:** `$delpayment <ID or Name>` (e.g. `$delpayment 1` or `$delpayment LTC`)\n"
            ),
            color=0x2ECC71
        )
        for m in methods:
            note_str = f"\n└ ℹ️ *{m['note']}*" if m.get('note') else ""
            embed.add_field(
                name=f"💳 #{m['id']} • {m['method_name']}",
                value=f"```{m['address']}```{note_str}",
                inline=False
            )
        embed.set_footer(text="Zyath Financial Security • Verified Addresses")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        embed.set_footer(text="Zyath Financial Security • Verified Addresses")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Terms of Service", style=discord.ButtonStyle.secondary, emoji="📜", row=1)
    async def tos_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        tos_text = await db.get_shop_tos(self.guild_id)
        if not tos_text:
            tos_text = (
                "**1. General Policy:** All sales are final once delivered unless specified otherwise.\n"
                "**2. Warranty & Proof:** Replacements are provided within warranty period with valid unedited proof.\n"
                "**3. Payment Verification:** Only send payments to official addresses in `$payment`.\n"
                "**4. Scams & Chargebacks:** Chargebacks result in a permanent ban & universal blacklist."
            )
        embed = standard_embed(
            title=f"📜 {interaction.guild.name} • Storefront Terms & Warranty",
            description=tos_text,
            color=0xFEE75C
        )
        embed.set_footer(text="By ordering from our store, you automatically agree to these terms.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Reputation & Vouches", style=discord.ButtonStyle.secondary, emoji="⭐", row=1)
    async def vouch_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        stats = await db.get_server_vouch_stats(self.guild_id)
        total = stats.get("total", 0)
        avg = stats.get("avg_rating", 0.0)
        embed = standard_embed(
            title=f"⭐ {interaction.guild.name} • Verified Community Reputation",
            description=(
                f"> **Total Vouches Recorded:** `{total}`\n"
                f"> **Customer Satisfaction Rating:** `⭐ {avg}/5.0`\n"
                f"> **Reputation Index:** ▰▰▰▰▰▰▰▰▰▰ `100% Verified`\n\n"
                f"Type `$vouchlb` to see our top trusted sellers or `$vouches @user` to inspect any member."
            ),
            color=0xFEE75C
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class RestockBuyView(discord.ui.View):
    def __init__(self, item_name: str = "Restocked Item"):
        super().__init__(timeout=None)
        self.item_name = item_name

    @discord.ui.button(label="🛒 Open Ticket to Buy", style=discord.ButtonStyle.success, emoji="🛒", custom_id="restock_open_ticket_btn")
    async def buy_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.tickets import CreateTicketModal
        await interaction.response.send_modal(CreateTicketModal("Buy / Order", interaction.guild_id, default_subject=f"Order: {self.item_name}"))

class Shop(commands.Cog):
    """Server storefront system with direct ticket ordering."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(RestockBuyView())

    @commands.command(name="shop", aliases=["store"], help="View server shop catalog. E.g. $shop or $store")
    async def view_shop(self, ctx: commands.Context, category: str = None):
        items = await db.get_shop_items(ctx.guild.id, category)
        categories = await db.get_shop_categories(ctx.guild.id)

        if not items:
            cat_list = ", ".join([f"`{c}`" for c in categories]) if categories else "None"
            return await ctx.send(embed=info_embed(
                "Shop Catalog",
                f"No items currently listed{' in category ' + category if category else ''}.\n\n"
                f"**Available Categories:** {cat_list}\n"
                f"*Admins can add items with `$shopadd`!*"
            ))

        embed = standard_embed(
            title=f"🛍️ {ctx.guild.name} • Official Marketplace",
            description=(
                f"> Welcome to our verified digital storefront. Select any item from the dropdown\n"
                f"> below to automatically open an instant private purchase ticket.\n\n"
                f"⚡ **Catalog Highlights ({len(items)} Items):**\n"
            ),
            color=0x2B2D31
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        for item in items[:15]:
            desc = item['description'] or "Instant delivery upon ticket confirmation."
            embed.add_field(
                name=f"📦 #{item['id']} • {item['name']} — `{item['price']}`",
                value=f"└ 🏷️ **Category:** `{item['category']}` • 🟢 **In Stock**\n└ *{desc}*",
                inline=False
            )

        embed.set_footer(text="Select an item below to order • 24/7 AI & Staff Assistance Active")
        view = ShopView(items, ctx.guild.id)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="shopadd", help="Add an item to the shop. E.g. $shopadd Nitro 1 Month | $5.00 | Subscriptions | Instant delivery")
    @commands.has_permissions(administrator=True)
    async def shop_add(self, ctx: commands.Context, *, details: str):
        parts = [p.strip() for p in details.split("|")]
        if len(parts) < 2:
            return await ctx.send(embed=error_embed(
                "Invalid Format",
                "Format: `$shopadd <Name> | <Price> | [Category] | [Description]`\nExample: `$shopadd OG Account | $50 | Accounts | Full access with receipts`"
            ))

        name = parts[0]
        price = parts[1]
        category = parts[2] if len(parts) > 2 and parts[2] else "General"
        description = parts[3] if len(parts) > 3 and parts[3] else ""

        item_id = await db.add_shop_item(ctx.guild.id, name, price, category, description)
        embed = success_embed(
            "Item Added to Shop",
            f"**Item ID:** `#{item_id}`\n**Name:** `{name}`\n**Price:** `{price}`\n**Category:** `{category}`\n**Description:** {description or 'None'}"
        )
        await ctx.send(embed=embed)

    @commands.command(name="shopremove", aliases=["shopdel"], help="Remove an item from the shop by ID. E.g. $shopremove 3")
    @commands.has_permissions(administrator=True)
    async def shop_remove(self, ctx: commands.Context, item_id: int):
        removed = await db.remove_shop_item(ctx.guild.id, item_id)
        if removed:
            await ctx.send(embed=success_embed("Item Removed", f"Successfully removed item `#{item_id}` from the shop."))
        else:
            await ctx.send(embed=error_embed("Item Not Found", f"No item found with ID `#{item_id}`."))

    @commands.command(name="shoplist", help="Admin overview of all shop items and IDs.")
    @commands.has_permissions(administrator=True)
    async def shop_list(self, ctx: commands.Context):
        items = await db.get_shop_items(ctx.guild.id)
        if not items:
            return await ctx.send(embed=info_embed("Shop Inventory", "No items in shop. Use `$shopadd` to add items."))

        lines = []
        for i in items:
            lines.append(f"**#{i['id']}** | **{i['name']}** - `{i['price']}` (`{i['category']}`)")

        embed = standard_embed(
            title="📋 Shop Inventory Admin List",
            description="\n".join(lines)
        )
        await ctx.send(embed=embed)

    @commands.command(name="payment", aliases=["wallets", "payments", "gateways"], help="View accepted shop payment methods and wallet addresses.")
    async def view_payment(self, ctx: commands.Context):
        methods = await db.get_payment_methods(ctx.guild.id)
        if not methods:
            embed = info_embed(
                "Payment Gateways",
                "No payment methods currently listed in this server.\n\n"
                "💡 **Admin Quick Setup:**\n"
                "• Add a method: `$setpayment <Method Name> | <Wallet/Address> | [Note]`\n"
                "• *Example:* `$setpayment Litecoin (LTC) | ltc1q9... | 1 confirmation required`"
            )
            if ctx.author.guild_permissions.administrator:
                view = PaymentAdminControlsView([], ctx.guild.id)
                return await ctx.send(embed=embed, view=view)
            return await ctx.send(embed=embed)

        embed = standard_embed(
            title=f"💳 {ctx.guild.name} • Official Payment Gateways",
            description=(
                "> Send funds only to the verified addresses below. Confirm transaction ID in ticket.\n\n"
                "💡 **Admin Controls:**\n"
                "• **Add:** `$setpayment <Name> | <Address> | [Note]`\n"
                "• **Delete:** `$delpayment <ID or Name>` (e.g. `$delpayment 1` or `$delpayment LTC`)\n"
            ),
            color=0x2ECC71
        )
        for m in methods:
            note_str = f"\n└ ℹ️ *{m['note']}*" if m.get('note') else ""
            embed.add_field(
                name=f"🔹 #{m['id']} • {m['method_name']}",
                value=f"```{m['address']}```{note_str}",
                inline=False
            )
        embed.set_footer(text="Zyath Financial Security • Verified Addresses")

        if ctx.author.guild_permissions.administrator:
            view = PaymentAdminControlsView(methods, ctx.guild.id)
            await ctx.send(embed=embed, view=view)
        else:
            await ctx.send(embed=embed)

    @commands.command(name="setpayment", aliases=["addpay"], help="Add or update a payment method. E.g. $setpayment LTC | ltc1q... | Fast confirmations")
    @commands.has_permissions(administrator=True)
    async def set_payment(self, ctx: commands.Context, *, details: str = None):
        if not details or "|" not in details:
            return await ctx.send(embed=error_embed(
                "Invalid Format",
                "**Usage:** `$setpayment <Method Name> | <Wallet/Details> | [Note]`\n\n"
                "**Examples:**\n"
                "• `$setpayment Litecoin (LTC) | ltc1q9... | 1 confirmation required`\n"
                "• `$setpayment PayPal | billing@zyath.store | Friends & Family only`\n"
                "• `$setpayment CashApp | $ZyathStore | Instant verification`\n\n"
                "*Tip: You can also click the `➕ Add Payment Method` button on `$payment`!*"
            ))

        parts = [p.strip() for p in details.split("|")]
        if len(parts) < 2 or not parts[0] or not parts[1]:
            return await ctx.send(embed=error_embed(
                "Invalid Format",
                "Format: `$setpayment <Method Name> | <Wallet/Details> | [Note]`\nExample: `$setpayment Litecoin (LTC) | ltc1q9... | 1 confirmation required`"
            ))

        method_name = parts[0]
        address = parts[1]
        note = parts[2] if len(parts) > 2 else ""

        mid = await db.add_payment_method(ctx.guild.id, method_name, address, note)
        embed = success_embed(
            "Payment Method Added",
            f"✅ **#{mid} • {method_name}** has been added to the storefront!\n\n"
            f"• **ID:** `#{mid}`\n"
            f"• **Address:** `{address}`\n"
            f"• **Note:** {note or 'None'}\n\n"
            f"💡 *To remove this method later, run:* `$delpayment {mid}` or `$delpayment {method_name.split()[0]}`"
        )
        await ctx.send(embed=embed)

    @commands.command(name="delpayment", aliases=["removepayment", "delpay", "deletepayment"], help="Delete a payment method by ID or Name. E.g. $delpayment 2 or $delpayment LTC")
    @commands.has_permissions(administrator=True)
    async def del_payment(self, ctx: commands.Context, *, query: str = None):
        methods = await db.get_payment_methods(ctx.guild.id)
        if not methods:
            return await ctx.send(embed=info_embed(
                "Payment Gateways",
                "No payment methods are currently configured in this server.\n"
                "Use `$setpayment <Name> | <Address> | [Note]` to add one!"
            ))

        # If user didn't specify query, present an interactive dropdown + list of methods!
        if not query or not query.strip():
            desc = (
                "> **Select a payment method from the dropdown below to delete it immediately,**\n"
                "> or type `$delpayment <ID or Name>` directly.\n\n"
                "**Active Payment Methods in Shop:**\n"
            )
            for m in methods:
                desc += f"• **#{m['id']}** — `{m['method_name']}` (`{m['address'][:30]}...`)\n"

            embed = standard_embed(
                title="🗑️ Remove Payment Gateway",
                description=desc,
                color=0xED4245
            )
            embed.set_footer(text="Select from dropdown below to delete immediately")
            view = PaymentDeleteView(methods, ctx.guild.id)
            return await ctx.send(embed=embed, view=view)

        query = query.strip()
        target_id = None
        target_name = None

        if query.isdigit():
            target_id = int(query)
            match = next((m for m in methods if m['id'] == target_id), None)
            if match:
                target_name = match['method_name']
        else:
            # Case-insensitive search by method name or address
            matches = [m for m in methods if query.lower() in m['method_name'].lower() or query.lower() in m['address'].lower()]
            if len(matches) == 1:
                target_id = matches[0]['id']
                target_name = matches[0]['method_name']
            elif len(matches) > 1:
                options_str = "\n".join([f"• **#{m['id']}** • `{m['method_name']}`" for m in matches])
                return await ctx.send(embed=warning_embed(
                    "Multiple Payment Methods Match",
                    f"Multiple methods match `{query}`. Please specify the exact ID:\n\n{options_str}\n\n*Example:* `$delpayment {matches[0]['id']}`"
                ))

        if target_id is not None:
            removed = await db.remove_payment_method(ctx.guild.id, target_id)
            if removed:
                name_display = f"**#{target_id} • {target_name}**" if target_name else f"`#{target_id}`"
                return await ctx.send(embed=success_embed(
                    "Payment Method Removed",
                    f"Successfully deleted {name_display} from the storefront.\nRun `$payment` to inspect your updated gateways."
                ))

        # Not found
        avail_str = "\n".join([f"• **#{m['id']}** • `{m['method_name']}`" for m in methods])
        await ctx.send(embed=error_embed(
            "Payment Method Not Found",
            f"No payment method matched `{query}`.\n\n"
            f"**Currently Active Methods:**\n{avail_str}\n\n"
            f"💡 *Tip:* Run `$delpayment {methods[0]['id']}` or just `$delpayment` to select from an interactive dropdown!"
        ))

    @commands.command(name="tos", aliases=["terms"], help="View shop Terms of Service, warranty, and refund policy.")
    async def view_tos(self, ctx: commands.Context):
        tos_text = await db.get_shop_tos(ctx.guild.id)
        if not tos_text:
            tos_text = (
                "**1. General Terms:**\nAll sales are final once delivered unless specified otherwise.\n\n"
                "**2. Warranty & Replacements:**\nReplacements are offered if reported within 24 hours with valid proof.\n\n"
                "**3. Payments:**\nOnly send payments to official addresses listed in `$payment`.\n\n"
                "**4. Chargebacks:**\nAny unauthorized chargebacks will lead to a permanent ban & scammer report."
            )

        embed = standard_embed(
            title=f"📜 {ctx.guild.name} • Terms of Service & Policy",
            description=tos_text,
            color=0xFEE75C
        )
        embed.set_footer(text="By purchasing from our shop, you automatically agree to these terms.")
        await ctx.send(embed=embed)

    @commands.command(name="settos", help="Set the shop Terms of Service text.")
    @commands.has_permissions(administrator=True)
    async def set_tos(self, ctx: commands.Context, *, text: str):
        await db.set_shop_tos(ctx.guild.id, text)
        await ctx.send(embed=success_embed("TOS Updated", "Shop Terms of Service have been successfully updated!"))

    @commands.command(name="restock", help="Broadcast an official shop restock alert with an instant 1-click buy button. E.g. $restock #announcements @everyone Nitro 1 Year | $15.00 | 50 in stock!")
    @commands.has_permissions(administrator=True)
    async def restock_announcement(self, ctx: commands.Context, *, raw_input: str = None):
        """
        Broadcasts a restock alert with optional @everyone/@here ping and instant order button.
        Examples:
        • $restock #announcements @everyone Nitro 1 Year | $15.00 | 50 units in stock!
        • $restock @everyone Nitro 1 Month | $5.00
        • $restock #updates Spotify 1 Year restocked!
        """
        if not raw_input or not raw_input.strip():
            return await ctx.send(embed=error_embed(
                "Missing Restock Details",
                "**Usage:** `$restock [#channel] [@everyone|@here] <Item Name> | <Price> | [Details]`\n\n"
                "**Examples:**\n"
                "• `$restock #announcements @everyone Nitro 1 Year | $15.00 | 50 in stock! Instant delivery.`\n"
                "• `$restock @everyone Spotify Premium 1 Year | $12.00 | Fresh accounts restocked!`"
            ))

        target_channel = ctx.channel
        text = raw_input.strip()

        # Check if first token is a channel mention (e.g. <#123456789>)
        tokens = text.split(maxsplit=1)
        if tokens[0].startswith("<#") and tokens[0].endswith(">"):
            try:
                chan_id = int(tokens[0].replace("<#", "").replace(">", ""))
                found_chan = ctx.guild.get_channel(chan_id)
                if found_chan and isinstance(found_chan, discord.TextChannel):
                    target_channel = found_chan
                    text = tokens[1] if len(tokens) > 1 else ""
            except Exception:
                pass

        # Check for @everyone or @here mentions
        mention_str = ""
        if "@everyone" in text:
            mention_str = "@everyone"
            text = text.replace("@everyone", "").strip()
        elif "@here" in text:
            mention_str = "@here"
            text = text.replace("@here", "").strip()

        # Parse pipe syntax if provided
        parts = [p.strip() for p in text.split("|")]
        item_name = parts[0]
        price_str = parts[1] if len(parts) > 1 else None
        extra_details = parts[2] if len(parts) > 2 else None

        # If price wasn't specified via pipe, check database
        if not price_str:
            items = await db.get_shop_items(ctx.guild.id)
            for it in items:
                if it["name"].lower() in item_name.lower():
                    price_str = it["price"]
                    if not extra_details and it.get("description"):
                        extra_details = it["description"]
                    break

        # Check real-time stock count from DB
        stock_count = await db.get_item_stock_count(ctx.guild.id, item_name)
        stock_display = f"🟢 **{stock_count} units available**" if stock_count > 0 else "🟢 **Fresh Batch In Stock**"

        # Fetch accepted payment methods
        payment_methods = await db.get_payment_methods(ctx.guild.id)
        pm_names = ", ".join([f"`{pm['method_name']}`" for pm in payment_methods[:4]]) if payment_methods else "`Crypto (LTC/BTC)`, `PayPal`, `CashApp`"

        embed = standard_embed(
            title=f"🔥 MASSIVE SHOP RESTOCK ALERT • {item_name}",
            description=(
                f"Fresh inventory has just been restocked in the store!\n"
                f"Grab yours now before stock sells out!\n\n"
                f"📦 **Product:** `{item_name}`\n"
                f"💰 **Price:** `{price_str or 'See Catalog ($shop)'}`\n"
                f"📊 **Availability:** {stock_display}\n"
                f"💳 **Accepted Gateways:** {pm_names}\n"
                f"⚡ **Delivery:** Instant automated delivery with warranty!\n"
            ),
            color=0x2ECC71
        )
        if extra_details:
            embed.add_field(name="📝 Details & Features", value=f"```{extra_details}```", inline=False)

        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=f"Zyath Official Store • Click the button below to buy instantly!")

        view = RestockBuyView(item_name)
        allowed = discord.AllowedMentions(everyone=True, roles=True, users=True)

        if mention_str:
            await target_channel.send(content=mention_str, embed=embed, view=view, allowed_mentions=allowed)
        else:
            await target_channel.send(embed=embed, view=view)

        if target_channel.id != ctx.channel.id:
            await ctx.send(embed=success_embed("Restock Alert Sent", f"Broadcasted restock alert to {target_channel.mention}!"))

async def setup(bot: commands.Bot):
    await bot.add_cog(Shop(bot))
