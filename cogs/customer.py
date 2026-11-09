import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db
from utils.ltc import shorten_address

class Customer(commands.Cog):
    """Customer profile management, lifetime spending analytics, and loyalty tiers."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="customer", invoke_without_command=True)
    async def customer_group(self, ctx: commands.Context, member: discord.Member = None):
        """View a customer's comprehensive profile and purchase statistics."""
        target = member or ctx.author
        await self.show_profile(ctx, target)

    async def show_profile(self, ctx: commands.Context, member: discord.Member):
        profile = await db.get_customer_profile(ctx.guild.id, member.id)
        cfg = await db.get_shop_config(ctx.guild.id)
        shop_title = cfg.get("shop_name", "Kyoka Shop")

        wallet_str = f"`{shorten_address(profile['ltc_address'])}`" if profile.get("ltc_address") else "*Not Linked*"
        stars_bar = "⭐" * int(round(profile["avg_review_rating"]))

        desc = (
            f"👤 **Customer:** {member.mention} (`{member.id}`)\n"
            f"🏷️ **Loyalty Status:** `{profile['loyalty_tier']}`\n"
            f"🪙 **Linked LTC Wallet:** {wallet_str}\n\n"
            f"💰 **Lifetime Spend:** `${profile['lifetime_spend']:.2f} USD`\n"
            f"📦 **Orders Completed:** `{profile['completed_orders']}` of `{profile['total_orders']}` total\n"
            f"⏳ **Active Orders:** `{profile['active_orders']}`\n"
            f"↩️ **Refunds:** `{profile['refunded_orders']}`\n"
            f"⭐ **Satisfaction:** {stars_bar} (`{profile['avg_review_rating']}/5.0` from {profile['total_reviews']} reviews)\n\n"
            f"📜 **Recent Orders:**\n"
        )
        if profile["recent_orders"]:
            for o in profile["recent_orders"]:
                desc += f"• `{o['order_id']}` — **{o['product_name']}** (x{o['quantity']}) — `${o['total_usd']:.2f}` (`{o['status'].title()}`)\n"
        else:
            desc += "*No previous purchase history on file.*"

        embed = standard_embed(
            title=f"💳 {shop_title} • Customer Profile: {member.display_name}",
            description=desc,
            color=0x2ECC71
        )
        if member.display_avatar:
            embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Requested by {ctx.author.display_name} • Verified Shop CRM")
        await ctx.send(embed=embed)

    @customer_group.command(name="profile")
    async def customer_profile(self, ctx: commands.Context, member: discord.Member = None):
        """View a customer's full CRM profile and loyalty level."""
        target = member or ctx.author
        await self.show_profile(ctx, target)

    @customer_group.command(name="spend", aliases=["spending"])
    async def customer_spend(self, ctx: commands.Context, member: discord.Member = None):
        """View total verified lifetime spending for a customer."""
        target = member or ctx.author
        spend = await db.get_customer_lifetime_spend(ctx.guild.id, target.id)
        embed = standard_embed(
            title=f"💰 Lifetime Customer Spending • {target.display_name}",
            description=f"{target.mention} has spent a total of **${spend:.2f} USD** in this store.",
            color=0x2ECC71
        )
        await ctx.send(embed=embed)

    @customer_group.command(name="orders")
    async def customer_orders(self, ctx: commands.Context, member: discord.Member = None):
        """View complete purchase history for a customer."""
        target = member or ctx.author
        orders = await db.get_user_orders(ctx.guild.id, target.id)
        if not orders:
            return await ctx.send(embed=info_embed("No Orders", f"{target.mention} has no recorded purchases."))

        desc = f"**Total Orders Recorded:** `{len(orders)}`\n\n"
        for o in orders[:10]:
            icon = "✅" if o["status"] == "completed" else ("⏳" if o["status"] == "pending_payment" else "✖️")
            desc += f"{icon} **`{o['order_id']}`** — **{o['product_name']}** (x{o['quantity']})\n"
            desc += f"└ 💵 `${o['total_usd']:.2f}` • Status: `{o['status'].title()}` • Receipt: `{o['receipt_id']}`\n\n"

        embed = standard_embed(
            title=f"📦 Purchase History • {target.display_name}",
            description=desc,
            color=0x2ECC71
        )
        await ctx.send(embed=embed)

    @customer_group.command(name="feedback")
    async def customer_feedback_cmd(self, ctx: commands.Context, member: discord.Member = None):
        """View customer feedback history for a user."""
        target = member or ctx.author
        reviews = await db.get_customer_feedback(ctx.guild.id, user_id=target.id)
        if not reviews:
            return await ctx.send(embed=info_embed("No Feedback", f"{target.mention} has not submitted any feedback yet."))

        desc = f"**Customer:** {target.mention} • **Reviews:** `{len(reviews)}`\n\n"
        for r in reviews[:8]:
            stars_str = "⭐" * r["stars"]
            desc += f"• **{stars_str}** for Order `{r['order_id']}`\n  *{r['description']}*\n"

        embed = standard_embed(
            title=f"⭐ Reviews by {target.display_name}",
            description=desc,
            color=0xFEE75C
        )
        await ctx.send(embed=embed)

    @customer_group.command(name="leaderboard", aliases=["lb", "top"])
    async def customer_leaderboard(self, ctx: commands.Context):
        """Display the highest spending customer leaderboard."""
        lb = await db.get_customer_spending_leaderboard(ctx.guild.id, limit=10)
        if not lb:
            return await ctx.send(embed=info_embed("Spending Leaderboard", "No completed purchases recorded yet."))

        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        desc = "> 🏆 **Top Customer Spending Leaderboard**\n> *Ranked by verified completed order volume.*\n\n"
        for idx, entry in enumerate(lb):
            icon = medals[idx] if idx < len(medals) else f"**#{idx+1}**"
            desc += f"{icon} <@{entry['user_id']}>\n"
            desc += f"└ 💰 **${entry['total_spent']:.2f}** Lifetime Spend • `{entry['orders_count']}` Orders Completed\n\n"

        cfg = await db.get_shop_config(ctx.guild.id)
        shop_title = cfg.get("shop_name", "Kyoka Shop")
        embed = standard_embed(
            title=f"🏆 {shop_title} • Top Customers",
            description=desc,
            color=0x2ECC71
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.send(embed=embed)

    # --- Slash Commands ---
    @app_commands.command(name="customer", description="Customer profile, spending history, and leaderboard.")
    @app_commands.describe(
        action="Action to perform",
        user="Target user to inspect"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="profile", value="profile"),
        app_commands.Choice(name="spend", value="spend"),
        app_commands.Choice(name="orders", value="orders"),
        app_commands.Choice(name="feedback", value="feedback"),
        app_commands.Choice(name="leaderboard", value="leaderboard")
    ])
    async def slash_customer(
        self,
        interaction: discord.Interaction,
        action: str,
        user: Optional[discord.Member] = None
    ):
        target = user or interaction.user
        if action == "profile":
            profile = await db.get_customer_profile(interaction.guild_id, target.id)
            wallet_str = f"`{shorten_address(profile['ltc_address'])}`" if profile.get("ltc_address") else "*Not Linked*"
            desc = (
                f"👤 **Customer:** {target.mention}\n"
                f"🏷️ **Loyalty:** `{profile['loyalty_tier']}`\n"
                f"🪙 **LTC Wallet:** {wallet_str}\n\n"
                f"💰 **Lifetime Spend:** `${profile['lifetime_spend']:.2f} USD`\n"
                f"📦 **Completed Orders:** `{profile['completed_orders']}`\n"
                f"⏳ **Active Orders:** `{profile['active_orders']}`\n"
                f"⭐ **Avg Rating:** ⭐ `{profile['avg_review_rating']}/5.0`"
            )
            embed = standard_embed(title=f"Customer Profile • {target.display_name}", description=desc, color=0x2ECC71)
            await interaction.response.send_message(embed=embed)

        elif action == "spend":
            spend = await db.get_customer_lifetime_spend(interaction.guild_id, target.id)
            embed = standard_embed(
                title=f"💰 Lifetime Spend • {target.display_name}",
                description=f"{target.mention} has spent a total of **${spend:.2f} USD**.",
                color=0x2ECC71
            )
            await interaction.response.send_message(embed=embed)

        elif action == "orders":
            orders = await db.get_user_orders(interaction.guild_id, target.id)
            if not orders:
                return await interaction.response.send_message(embed=info_embed("Orders", "No orders on file."), ephemeral=True)
            desc = f"**Total Orders:** `{len(orders)}`\n\n"
            for o in orders[:8]:
                desc += f"• `{o['order_id']}` — **{o['product_name']}** (`${o['total_usd']:.2f}`) — `{o['status']}`\n"
            embed = standard_embed(title=f"📦 Orders for {target.display_name}", description=desc, color=0x2ECC71)
            await interaction.response.send_message(embed=embed)

        elif action == "feedback":
            reviews = await db.get_customer_feedback(interaction.guild_id, user_id=target.id)
            if not reviews:
                return await interaction.response.send_message(embed=info_embed("Feedback", "No feedback submitted yet."), ephemeral=True)
            desc = "\n".join([f"• {'⭐' * r['stars']} for `{r['order_id']}`: *{r['description']}*" for r in reviews[:6]])
            embed = standard_embed(title=f"⭐ Reviews by {target.display_name}", description=desc, color=0xFEE75C)
            await interaction.response.send_message(embed=embed)

        elif action == "leaderboard":
            lb = await db.get_customer_spending_leaderboard(interaction.guild_id, limit=10)
            if not lb:
                return await interaction.response.send_message(embed=info_embed("Leaderboard", "No completed purchases yet."), ephemeral=True)
            desc = "\n".join([f"**#{i+1}** <@{e['user_id']}> — **${e['total_spent']:.2f}** ({e['orders_count']} orders)" for i, e in enumerate(lb)])
            embed = standard_embed(title="🏆 Customer Spending Leaderboard", description=desc, color=0x2ECC71)
            await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Customer(bot))
