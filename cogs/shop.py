import discord
from discord.ext import commands
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db
from cogs.tickets import TicketControlsView

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

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True)

        try:
            order_channel = await guild.create_text_channel(
                name=channel_name,
                category=parent_cat,
                overwrites=overwrites,
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

    @commands.command(name="shop", help="View server shop catalog. E.g. $shop or $shop [category]")
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

async def setup(bot: commands.Bot):
    await bot.add_cog(Shop(bot))
