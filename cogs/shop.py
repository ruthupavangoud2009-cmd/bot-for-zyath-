import discord
from discord.ext import commands
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

class ShopView(discord.ui.View):
    def __init__(self, items: list):
        super().__init__(timeout=180)
        if items:
            self.add_item(ShopItemSelect(items))

class Shop(commands.Cog):
    """Server storefront system with direct ticket ordering."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="shop", aliases=["s", "store"], help="View server shop catalog. E.g. $shop or $s")
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
            title=f"🛒 {ctx.guild.name} Official Shop",
            description=(
                "Browse our catalog of items and services below.\n"
                "To buy, select an item from the dropdown to automatically open an Order Ticket!\n"
            ),
            color=0x5763719
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        for item in items[:15]:
            desc = item['description'] or "No description provided."
            embed.add_field(
                name=f"📦 #{item['id']} • {item['name']} — {item['price']}",
                value=f"**Category:** `{item['category']}`\n*{desc}*",
                inline=False
            )

        embed.set_footer(text="Select an item below to order • Zyath Shop")
        view = ShopView(items)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="shopadd", aliases=["sa", "sadd"], help="Add an item to the shop. E.g. $shopadd Nitro 1 Month | $5.00 | Subscriptions | Instant delivery")
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

    @commands.command(name="shopremove", aliases=["shopdel", "sr", "sdel"], help="Remove an item from the shop by ID. E.g. $shopremove 3")
    @commands.has_permissions(administrator=True)
    async def shop_remove(self, ctx: commands.Context, item_id: int):
        removed = await db.remove_shop_item(ctx.guild.id, item_id)
        if removed:
            await ctx.send(embed=success_embed("Item Removed", f"Successfully removed item `#{item_id}` from the shop."))
        else:
            await ctx.send(embed=error_embed("Item Not Found", f"No item found with ID `#{item_id}`."))

    @commands.command(name="shoplist", aliases=["sl", "slist"], help="Admin overview of all shop items and IDs.")
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

    @commands.command(name="payment", aliases=["pay", "wallets", "pm"], help="View accepted shop payment methods and wallet addresses.")
    async def view_payment(self, ctx: commands.Context):
        methods = await db.get_payment_methods(ctx.guild.id)
        if not methods:
            return await ctx.send(embed=info_embed(
                "Payment Methods",
                "No payment methods currently listed.\n*Admins can add methods using `$setpayment <Name> | <Address> | [Note]`!*"
            ))

        embed = standard_embed(
            title=f"💳 {ctx.guild.name} • Accepted Payment Methods",
            description="Use the addresses below to complete payments. Always double check addresses before sending!\n",
            color=0x2ECC71
        )
        for m in methods:
            note_str = f"\n*{m['note']}*" if m.get('note') else ""
            embed.add_field(
                name=f"🔹 {m['method_name']}",
                value=f"```{m['address']}```{note_str}",
                inline=False
            )
        embed.set_footer(text="Zyath Shop • Verified Payment Gateways")
        await ctx.send(embed=embed)

    @commands.command(name="setpayment", aliases=["sp", "addpay"], help="Add or update a payment method. E.g. $setpayment LTC | ltc1q... | Fast confirmations")
    @commands.has_permissions(administrator=True)
    async def set_payment(self, ctx: commands.Context, *, details: str):
        parts = [p.strip() for p in details.split("|")]
        if len(parts) < 2:
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
            f"**ID:** `#{mid}`\n**Method:** `{method_name}`\n**Address:** `{address}`\n**Note:** {note or 'None'}"
        )
        await ctx.send(embed=embed)

    @commands.command(name="delpayment", aliases=["removepayment", "dp"], help="Delete a payment method by ID. E.g. $delpayment 2")
    @commands.has_permissions(administrator=True)
    async def del_payment(self, ctx: commands.Context, method_id: int):
        removed = await db.remove_payment_method(ctx.guild.id, method_id)
        if removed:
            await ctx.send(embed=success_embed("Payment Method Removed", f"Payment method `#{method_id}` was removed."))
        else:
            await ctx.send(embed=error_embed("Not Found", f"No payment method found with ID `#{method_id}`."))

    @commands.command(name="tos", aliases=["rules", "terms"], help="View shop Terms of Service, warranty, and refund policy.")
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

    @commands.command(name="settos", aliases=["st"], help="Set the shop Terms of Service text.")
    @commands.has_permissions(administrator=True)
    async def set_tos(self, ctx: commands.Context, *, text: str):
        await db.set_shop_tos(ctx.guild.id, text)
        await ctx.send(embed=success_embed("TOS Updated", "Shop Terms of Service have been successfully updated!"))

async def setup(bot: commands.Bot):
    await bot.add_cog(Shop(bot))
