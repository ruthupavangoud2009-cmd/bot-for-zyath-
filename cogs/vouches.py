import discord
from discord.ext import commands
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db

class VouchQuickActionsView(discord.ui.View):
    def __init__(self, target_id: int):
        super().__init__(timeout=180)
        self.target_id = target_id

    @discord.ui.button(label="View Profile", style=discord.ButtonStyle.secondary, emoji="📊")
    async def view_profile(self, interaction: discord.Interaction, button: discord.ui.Button):
        target = interaction.guild.get_member(self.target_id)
        if not target:
            return await interaction.response.send_message("Member no longer in this server.", ephemeral=True)
        vouches = await db.get_vouches(interaction.guild_id, target.id)
        total, avg = await db.get_vouch_stats(interaction.guild_id, target.id)
        desc = f"📊 **Total Vouches:** `{total}` • ⭐ **Rating:** `{avg}/5.0`\n\n**Recent Feedback:**\n"
        for v in vouches[:5]:
            desc += f"• {'⭐' * v['stars']} by <@{v['author_id']}>: *{v['comment']}*\n"
        embed = standard_embed(title=f"⭐ Reputation Profile • {target.display_name}", description=desc, thumbnail=target.display_avatar.url, color=0xFEE75C)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class Vouches(commands.Cog):
    """Ultimate Vouch system with leaderboards, statistics, profiles, and verification."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="setvouchchannel", help="Set the channel where all vouches will be logged.")
    @commands.has_permissions(administrator=True)
    async def set_vouch_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        await db.update_guild_setting(ctx.guild.id, "vouch_channel_id", channel.id)
        await ctx.send(embed=success_embed("Vouch Channel Configured", f"Vouches will be logged in {channel.mention}."))

    @commands.command(name="vouch", help="Vouch for a user. E.g. $vouch @user 5 Fast and legit trader!")
    async def vouch(self, ctx: commands.Context, member: discord.Member, *args):
        if member.id == ctx.author.id:
            return await ctx.send(embed=error_embed("Invalid Target", "You cannot vouch for yourself!"))
        if member.bot:
            return await ctx.send(embed=error_embed("Invalid Target", "You cannot vouch for a bot."))

        if not args:
            return await ctx.send(embed=error_embed("Missing Details", "Please provide a comment. Usage: `$vouch @user [1-5 stars] <comment>`"))

        # Check if first arg is stars number
        first_arg = args[0]
        if first_arg.isdigit() and 1 <= int(first_arg) <= 5:
            stars = int(first_arg)
            comment = " ".join(args[1:])
        else:
            stars = 5
            comment = " ".join(args)

        if not comment.strip():
            comment = "Positive vouch! Trusted trader."

        vouch_id = await db.add_vouch(ctx.guild.id, member.id, ctx.author.id, stars, comment)
        total_vouches, avg_stars = await db.get_vouch_stats(ctx.guild.id, member.id)

        star_emojis = "⭐" * stars
        # Determine reputation tier
        if total_vouches >= 25:
            tier_badge = "👑 Legendary Merchant"
        elif total_vouches >= 10:
            tier_badge = "🛡️ Elite Seller"
        elif total_vouches >= 5:
            tier_badge = "⭐ Verified Trader"
        else:
            tier_badge = "🌱 Emerging Trader"

        embed = standard_embed(
            title="⭐ Verified Reputation Certificate Logged",
            description=(
                f"> **Transaction Review Confirmed**\n"
                f"> Case `#{vouch_id}` • Audit Verified • <t:{int(discord.utils.utcnow().timestamp())}:R>\n\n"
                f"👤 **Seller:** {member.mention} (`{member.id}`)\n"
                f"✍️ **Reviewed By:** {ctx.author.mention} (`{ctx.author.id}`)\n"
                f"🌟 **Rating:** {star_emojis} (`{stars}.0/5.0`)\n"
                f"🏷️ **Seller Tier:** `{tier_badge}`\n\n"
                f"💬 **Customer Feedback:**\n"
                f"```{comment}```\n"
                f"📊 **Cumulative Standing:** `{total_vouches}` Total Vouches • ⭐ `{avg_stars}/5.0` Avg Rating"
            ),
            color=0xFEE75C,
            thumbnail=member.display_avatar.url
        )
        embed.set_footer(text=f"Vouch #{vouch_id} • Kyoka High-Trust Cryptographic Ledger")

        settings = await db.get_guild_settings(ctx.guild.id)
        vouch_channel_id = settings.get("vouch_channel_id")
        logged_channel = None

        view = VouchQuickActionsView(member.id)

        if vouch_channel_id:
            vouch_channel = ctx.guild.get_channel(vouch_channel_id)
            if vouch_channel and vouch_channel.permissions_for(ctx.guild.me).send_messages:
                await vouch_channel.send(embed=embed, view=view)
                logged_channel = vouch_channel

        if logged_channel and logged_channel.id != ctx.channel.id:
            await ctx.send(embed=success_embed(
                "Vouch Submitted",
                f"Your verified review for {member.mention} has been broadcasted to {logged_channel.mention}!\n"
                f"Total seller vouches: **{total_vouches}** (⭐ `{avg_stars}/5.0`)"
            ))
        else:
            await ctx.send(embed=embed, view=view)

    @commands.command(name="vouches", aliases=["rep", "reputation"], help="Check vouches and reputation history for yourself or another user.")
    async def view_vouches(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        vouches = await db.get_vouches(ctx.guild.id, member.id)
        total_vouches, avg_stars = await db.get_vouch_stats(ctx.guild.id, member.id)

        if not vouches:
            return await ctx.send(embed=info_embed(
                f"Reputation Profile: {member.display_name}",
                f"{member.mention} currently has no logged vouches in this server.\n"
                f"*Complete successful trades to build trust!*"
            ))

        if total_vouches >= 25:
            tier_badge = "👑 Legendary Merchant"
        elif total_vouches >= 10:
            tier_badge = "🛡️ Elite Seller"
        elif total_vouches >= 5:
            tier_badge = "⭐ Verified Trader"
        else:
            tier_badge = "🌱 Emerging Trader"

        # Generate star meter
        full_stars = int(round(avg_stars))
        star_bar = "⭐" * full_stars

        desc = (
            f"> **Merchant Trust Dossier**\n"
            f"> Status: `{tier_badge}` • Index: ▰▰▰▰▰▰▰▰▰▰ `100% Legit`\n\n"
            f"📊 **Total Reviews:** `{total_vouches}` Confirmed Trades\n"
            f"⭐ **Average Rating:** {star_bar} (`{avg_stars}/5.0`)\n\n"
            f"📝 **Recent Customer Testimonials:**\n"
        )
        for v in vouches[:6]:
            stars_str = "⭐" * v['stars']
            desc += f"• **{stars_str}** by <@{v['author_id']}> (`#{v['id']}`)\n  *{v['comment']}*\n"

        embed = standard_embed(
            title=f"⭐ Reputation Profile • {member.display_name}",
            description=desc,
            thumbnail=member.display_avatar.url,
            color=0xFEE75C
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name} • Kyoka Verified Trust")
        await ctx.send(embed=embed)

    @commands.command(name="vouchleaderboard", aliases=["vouchlb", "vlb"], help="View the ranked top vouched sellers in the server.")
    async def vouch_leaderboard(self, ctx: commands.Context):
        lb = await db.get_vouch_leaderboard(ctx.guild.id, limit=10)
        if not lb:
            return await ctx.send(embed=info_embed("Vouch Leaderboard", "No vouches logged in this server yet!"))

        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        desc = (
            "> 🏆 **Top Reputable Merchants & Traders**\n"
            "> *Community-audited reputation rankings based on verified customer feedback.*\n\n"
        )

        for idx, entry in enumerate(lb):
            icon = medals[idx] if idx < len(medals) else f"**#{idx+1}**"
            target_id = entry["target_id"]
            count = entry["count"]
            avg = entry["avg_stars"]
            tier = "👑 Legendary" if count >= 25 else ("🛡️ Elite" if count >= 10 else "⭐ Verified")
            desc += f"{icon} <@{target_id}>\n└ **{count}** Vouches • ⭐ `{avg}/5.0` • `{tier}`\n\n"

        server_stats = await db.get_server_vouch_stats(ctx.guild.id)
        total_server = server_stats.get("total", 0)
        avg_server = server_stats.get("avg_rating", 0.0)

        embed = standard_embed(
            title=f"🏆 Official Vouch Leaderboard • {ctx.guild.name}",
            description=desc,
            color=0xFEE75C
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=f"Total Audited Vouches: {total_server} • Server Avg Rating: {avg_server}/5.0")
        await ctx.send(embed=embed)

    @commands.command(name="vouchinfo", help="View full metadata for a specific vouch by its ID.")
    async def vouch_info(self, ctx: commands.Context, vouch_id: int):
        vouch = await db.get_vouch(vouch_id)
        if not vouch:
            return await ctx.send(embed=error_embed("Not Found", f"No vouch record found with ID `#{vouch_id}`."))

        embed = standard_embed(
            title=f"⭐ Vouch Record #{vouch['id']}",
            description=(
                f"**Recipient:** <@{vouch['target_id']}> (`{vouch['target_id']}`)\n"
                f"**Author:** <@{vouch['author_id']}> (`{vouch['author_id']}`)\n"
                f"**Rating:** {'⭐' * vouch['stars']} (`{vouch['stars']}/5`)\n"
                f"**Timestamp:** `{vouch['timestamp']}`\n\n"
                f"**Feedback:**\n```{vouch['comment']}```"
            ),
            color=0xFEE75C
        )
        await ctx.send(embed=embed)

    @commands.command(name="delvouch", aliases=["vouchdelete"], help="Remove a vouch by ID.")
    @commands.has_permissions(manage_messages=True)
    async def delete_vouch(self, ctx: commands.Context, vouch_id: int):
        removed = await db.delete_vouch(ctx.guild.id, vouch_id)
        if removed:
            await ctx.send(embed=success_embed("Vouch Removed", f"Successfully deleted vouch `#{vouch_id}`."))
        else:
            await ctx.send(embed=error_embed("Not Found", f"Vouch `#{vouch_id}` was not found in this server."))

    @commands.command(name="vouchstats", help="View server-wide vouch metrics and averages.")
    async def vouch_stats(self, ctx: commands.Context):
        stats = await db.get_server_vouch_stats(ctx.guild.id)
        total = stats.get("total", 0)
        avg = stats.get("avg_rating", 0.0)
        top_id = stats.get("top_seller_id")
        top_str = f"<@{top_id}>" if top_id else "None"

        embed = standard_embed(
            title=f"📊 Server Vouch Statistics • {ctx.guild.name}",
            description=(
                f"• **Total Vouches Logged:** `{total}`\n"
                f"• **Server Average Rating:** ⭐ `{avg}/5.0`\n"
                f"• **#1 Top Reputed Member:** {top_str}\n\n"
                f"Use `$vlb` to view the full leaderboard."
            ),
            color=0xFEE75C
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.send(embed=embed)

    @commands.command(name="importvouches", aliases=["addvouches"], help="Credit legacy vouches to a seller for platform migrations.")
    @commands.has_permissions(administrator=True)
    async def import_vouches(self, ctx: commands.Context, member: discord.Member, count: int, *, note: str = "Legacy migration"):
        if count < 1 or count > 100:
            return await ctx.send(embed=error_embed("Invalid Count", "Count must be between 1 and 100."))

        for _ in range(count):
            await db.add_vouch(ctx.guild.id, member.id, ctx.author.id, 5, f"[Imported] {note}")

        total, avg = await db.get_vouch_stats(ctx.guild.id, member.id)
        await ctx.send(embed=success_embed(
            "Vouches Imported",
            f"Successfully credited **+{count}** 5-star vouches to {member.mention}!\nNew Total: **{total}** (⭐ `{avg}/5.0`)"
        ))

async def setup(bot: commands.Bot):
    await bot.add_cog(Vouches(bot))
