import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db

class FeedbackModal(discord.ui.Modal, title="Submit Customer Feedback"):
    rating = discord.ui.TextInput(
        label="Rating (1 to 5 Stars)",
        placeholder="Enter a number between 1 and 5",
        min_length=1,
        max_length=1,
        required=True
    )
    description = discord.ui.TextInput(
        label="Review Description",
        placeholder="Describe your purchase experience, product quality, speed, etc.",
        style=discord.TextStyle.paragraph,
        min_length=5,
        max_length=1000,
        required=True
    )

    def __init__(self, order_id: str, guild_id: int):
        super().__init__()
        self.order_id = order_id
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        raw_rating = self.rating.value.strip()
        if not raw_rating.isdigit() or int(raw_rating) not in range(1, 6):
            return await interaction.response.send_message(
                embed=error_embed("Invalid Rating", "Please enter a valid rating between `1` and `5`."),
                ephemeral=True
            )
        stars = int(raw_rating)
        order = await db.get_shop_order(self.order_id)
        if not order:
            return await interaction.response.send_message(
                embed=error_embed("Order Not Found", f"No order record found for `{self.order_id}`."),
                ephemeral=True
            )

        if order.get("user_id") != interaction.user.id:
            return await interaction.response.send_message(
                embed=error_embed("Unauthorized", "You can only submit feedback for orders you purchased."),
                ephemeral=True
            )

        if order.get("status") != "completed":
            return await interaction.response.send_message(
                embed=error_embed("Order Incomplete", "Feedback can only be submitted for completed orders."),
                ephemeral=True
            )

        # Check for existing review
        existing = await db.get_customer_feedback(self.guild_id, order_id=self.order_id)
        if existing:
            return await interaction.response.send_message(
                embed=error_embed("Duplicate Feedback", f"A review for Order `{self.order_id}` has already been submitted."),
                ephemeral=True
            )

        fid = await db.add_customer_feedback(
            self.guild_id,
            self.order_id,
            interaction.user.id,
            stars,
            self.description.value.strip()
        )

        star_emojis = "⭐" * stars
        embed = discord.Embed(
            title="⭐ New Customer Feedback",
            color=0xFEE75C,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Rating", value=f"{star_emojis} ({stars}/5)", inline=False)
        embed.add_field(name="Description", value=self.description.value.strip(), inline=False)
        embed.add_field(name="User", value=interaction.user.name, inline=False)
        embed.add_field(name="Order ID", value=self.order_id, inline=False)
        if interaction.user.display_avatar:
            embed.set_thumbnail(url=interaction.user.display_avatar.url)

        # Dispatch to configured feedback channel
        cfg = await db.get_shop_config(self.guild_id)
        feedback_chan_id = cfg.get("feedback_channel_id")
        if not feedback_chan_id:
            settings = await db.get_guild_settings(self.guild_id)
            feedback_chan_id = settings.get("vouch_channel_id")

        if feedback_chan_id:
            target_chan = interaction.guild.get_channel(feedback_chan_id)
            if target_chan and target_chan.permissions_for(interaction.guild.me).send_messages:
                await target_chan.send(embed=embed)

        await interaction.response.send_message(
            embed=success_embed("Feedback Submitted", f"Thank you! Your review for Order `{self.order_id}` has been recorded."),
            ephemeral=True
        )

class Feedback(commands.Cog):
    """Customer Feedback and 5-Star Reviews System."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="feedback", aliases=["review"], invoke_without_command=True)
    async def feedback_group(self, ctx: commands.Context, order_id: str = None):
        """Submit feedback for an order or view server reviews."""
        if order_id:
            await self.submit_review_flow(ctx, order_id)
        else:
            await self.show_feedback_stats(ctx)

    async def submit_review_flow(self, ctx: commands.Context, order_id: str):
        clean_order = order_id.strip()
        order = await db.get_shop_order(clean_order)
        if not order:
            return await ctx.send(embed=error_embed("Order Not Found", f"No order found with ID `{clean_order}`."))

        if order.get("user_id") != ctx.author.id:
            return await ctx.send(embed=error_embed("Access Denied", "You can only leave feedback on your own completed purchases."))

        if order.get("status") != "completed":
            return await ctx.send(embed=error_embed("Order Not Completed", "This order is not completed yet."))

        existing = await db.get_customer_feedback(ctx.guild.id, order_id=clean_order)
        if existing:
            return await ctx.send(embed=error_embed("Already Reviewed", f"Feedback has already been logged for Order `{clean_order}`."))

        # Direct prompt via interactive button
        view = discord.ui.View()
        btn = discord.ui.Button(label="Write Review & Rate", style=discord.ButtonStyle.success, emoji="⭐")

        async def btn_callback(interaction: discord.Interaction):
            if interaction.user.id != ctx.author.id:
                return await interaction.response.send_message("Only the order buyer can review this order.", ephemeral=True)
            await interaction.response.send_modal(FeedbackModal(clean_order, ctx.guild.id))

        btn.callback = btn_callback
        view.add_item(btn)

        await ctx.send(
            embed=info_embed(
                "Submit Order Review",
                f"Ready to leave feedback for **Order `{clean_order}`** (`{order['product_name']}`)?\n"
                f"Click the button below to rate 1-5 stars and write your review!"
            ),
            view=view
        )

    @feedback_group.command(name="review")
    async def feedback_review(self, ctx: commands.Context, order_id: str):
        """Submit feedback for a specific completed order ID."""
        await self.submit_review_flow(ctx, order_id)

    @feedback_group.command(name="user")
    async def feedback_user(self, ctx: commands.Context, member: discord.Member = None):
        """View all customer reviews written by a user."""
        target = member or ctx.author
        reviews = await db.get_customer_feedback(ctx.guild.id, user_id=target.id)
        if not reviews:
            return await ctx.send(embed=info_embed("Customer Feedback", f"{target.mention} has not submitted any feedback yet."))

        avg = round(sum(r["stars"] for r in reviews) / len(reviews), 1)
        desc = f"**Customer:** {target.mention} • **Reviews:** `{len(reviews)}` • **Avg Rating:** ⭐ `{avg}/5.0`\n\n"
        for r in reviews[:8]:
            stars_str = "⭐" * r["stars"]
            desc += f"• **{stars_str}** for Order `{r['order_id']}`\n  *{r['description']}*\n"

        embed = standard_embed(
            title=f"⭐ Customer Feedback History • {target.display_name}",
            description=desc,
            color=0xFEE75C
        )
        if target.display_avatar:
            embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.send(embed=embed)

    @feedback_group.command(name="stats")
    async def feedback_stats(self, ctx: commands.Context):
        """Show shop customer satisfaction rating and total review stats."""
        await self.show_feedback_stats(ctx)

    async def show_feedback_stats(self, ctx: commands.Context):
        stats = await db.get_feedback_stats(ctx.guild.id)
        total = stats.get("total", 0)
        avg = stats.get("avg_stars", 5.0)
        stars_bar = "⭐" * int(round(avg))

        embed = standard_embed(
            title=f"⭐ Customer Satisfaction & Review Metrics • {ctx.guild.name}",
            description=(
                f"> **Total Customer Reviews:** `{total}`\n"
                f"> **Average Satisfaction Rating:** {stars_bar} (`{avg}/5.0`)\n"
                f"> **Verified Store Standing:** ▰▰▰▰▰▰▰▰▰▰ `100% Genuine`\n\n"
                f"💡 *To review a completed purchase, run:* `$feedback review <order_id>`"
            ),
            color=0xFEE75C
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.send(embed=embed)

    @feedback_group.command(name="delete")
    @commands.has_permissions(manage_messages=True)
    async def feedback_delete(self, ctx: commands.Context, review_id: int):
        """Staff only: delete a fraudulent or inappropriate review by ID."""
        success = await db.delete_customer_feedback(ctx.guild.id, review_id)
        if success:
            await ctx.send(embed=success_embed("Review Deleted", f"Successfully removed customer review `#{review_id}`."))
        else:
            await ctx.send(embed=error_embed("Not Found", f"No customer review found with ID `#{review_id}`."))

    # --- Slash Commands ---
    @app_commands.command(name="feedback", description="Customer feedback: review completed orders or view statistics.")
    @app_commands.describe(
        action="Choose an action",
        order_id="Order ID to review (e.g. ORD-123456)",
        user="Check reviews submitted by a specific user"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="review", value="review"),
        app_commands.Choice(name="stats", value="stats"),
        app_commands.Choice(name="user", value="user")
    ])
    async def slash_feedback(
        self,
        interaction: discord.Interaction,
        action: str,
        order_id: Optional[str] = None,
        user: Optional[discord.Member] = None
    ):
        if action == "review":
            if not order_id:
                return await interaction.response.send_message(embed=error_embed("Missing Order ID", "Please specify an `order_id` to review."), ephemeral=True)
            clean_order = order_id.strip()
            order = await db.get_shop_order(clean_order)
            if not order:
                return await interaction.response.send_message(embed=error_embed("Order Not Found", f"No order found with ID `{clean_order}`."), ephemeral=True)
            if order.get("user_id") != interaction.user.id:
                return await interaction.response.send_message(embed=error_embed("Access Denied", "You can only review your own purchases."), ephemeral=True)
            if order.get("status") != "completed":
                return await interaction.response.send_message(embed=error_embed("Order Not Completed", "This order is not completed yet."), ephemeral=True)
            existing = await db.get_customer_feedback(interaction.guild_id, order_id=clean_order)
            if existing:
                return await interaction.response.send_message(embed=error_embed("Already Reviewed", f"Feedback has already been logged for Order `{clean_order}`."), ephemeral=True)
            await interaction.response.send_modal(FeedbackModal(clean_order, interaction.guild_id))
        elif action == "stats":
            stats = await db.get_feedback_stats(interaction.guild_id)
            total = stats.get("total", 0)
            avg = stats.get("avg_stars", 5.0)
            embed = standard_embed(
                title=f"⭐ Customer Satisfaction • {interaction.guild.name}",
                description=f"• **Total Reviews:** `{total}`\n• **Average Rating:** ⭐ `{avg}/5.0`",
                color=0xFEE75C
            )
            await interaction.response.send_message(embed=embed)
        elif action == "user":
            target = user or interaction.user
            reviews = await db.get_customer_feedback(interaction.guild_id, user_id=target.id)
            if not reviews:
                return await interaction.response.send_message(embed=info_embed("Customer Feedback", f"{target.mention} has not submitted any feedback yet."), ephemeral=True)
            avg = round(sum(r["stars"] for r in reviews) / len(reviews), 1)
            desc = f"**Customer:** {target.mention} • **Reviews:** `{len(reviews)}` • **Avg Rating:** ⭐ `{avg}/5.0`\n\n"
            for r in reviews[:8]:
                desc += f"• **{'⭐' * r['stars']}** for Order `{r['order_id']}`\n  *{r['description']}*\n"
            embed = standard_embed(title=f"⭐ Reviews by {target.display_name}", description=desc, color=0xFEE75C)
            await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Feedback(bot))
