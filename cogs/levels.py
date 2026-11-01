import discord
from discord.ext import commands
import time
import random
from typing import Optional, Dict
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db

class Levels(commands.Cog):
    """Lal & Community Server Leveling Suite: XP Engine, Rank Cards, and Leaderboards."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # In-memory cooldown: {(guild_id, user_id): timestamp}
        self.xp_cooldowns: Dict[tuple, float] = {}

    def make_progress_bar(self, current: int, total: int, length: int = 10) -> str:
        """Constructs an aesthetic visual text progress bar."""
        if total <= 0:
            return "░" * length
        ratio = min(1.0, max(0.0, current / total))
        filled = int(ratio * length)
        empty = length - filled
        pct = int(ratio * 100)
        return f"[{'█' * filled}{'░' * empty}] `{pct}%`"

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        key = (message.guild.id, message.author.id)
        now = time.time()
        last_time = self.xp_cooldowns.get(key, 0)

        # 60 second cooldown between XP gains
        if (now - last_time) < 60:
            return

        self.xp_cooldowns[key] = now
        gained_xp = random.randint(15, 25)

        # If user or guild has premium, award 1.5x XP!
        if db.is_guild_premium(message.guild.id) or db.is_user_premium(message.author.id):
            gained_xp = int(gained_xp * 1.5)

        leveled_up, new_level, cur_xp = await db.add_xp(message.guild.id, message.author.id, gained_xp)

        if leveled_up:
            embed = standard_embed(
                title="🎉 LEVEL UP! 🎉",
                description=(
                    f"Congratulations {message.author.mention}!\n"
                    f"You have reached **Level {new_level}**! 🚀\n"
                    f"Keep chatting to unlock new achievements!"
                ),
                color=0x57F287,
                thumbnail=message.author.display_avatar.url
            )
            embed.set_footer(text=f"{message.guild.name} Community Levels")
            try:
                await message.channel.send(content=message.author.mention, embed=embed)
            except Exception:
                pass

    # ==========================================
    # 1. RANK CARD
    # ==========================================
    @commands.command(name="rank", aliases=["lvl", "level"], help="View your or another member's level, XP, and rank card.")
    async def rank_cmd(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        target = member or ctx.author
        data = await db.get_level_data(ctx.guild.id, target.id)

        lvl = data["level"]
        xp = data["xp"]
        needed_xp = 5 * (lvl ** 2) + 50 * lvl + 100
        rank = await db.get_user_rank(ctx.guild.id, target.id)
        bar = self.make_progress_bar(xp, needed_xp)

        prem_badge = " 💎 [VIP]" if (db.is_user_premium(target.id) or db.is_guild_premium(ctx.guild.id)) else ""

        embed = standard_embed(
            title=f"📊 {target.display_name}'s Level Dossier{prem_badge}",
            description=(
                f"• **Server Rank:** `#{rank}` 🏆\n"
                f"• **Current Level:** `Level {lvl}` ⭐\n"
                f"• **Experience:** `{xp:,} / {needed_xp:,} XP`\n"
                f"• **Progress:** {bar}"
            ),
            color=0x5865F2,
            thumbnail=target.display_avatar.url
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name} • Chat actively to earn XP")
        await ctx.send(embed=embed)

    # ==========================================
    # 2. SERVER LEADERBOARD
    # ==========================================
    @commands.command(name="leaderboard", aliases=["levels", "top", "xplb"], help="Display the top 10 most active chatters in this server.")
    async def leaderboard_cmd(self, ctx: commands.Context):
        top_users = await db.get_leaderboard(ctx.guild.id, limit=10)
        if not top_users:
            return await ctx.send(embed=info_embed("Server Leaderboard", "No member XP records found yet. Start chatting!"))

        lines = []
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

        for idx, u in enumerate(top_users):
            user_id = u["user_id"]
            lvl = u["level"]
            xp = u["xp"]
            medal = medals[idx] if idx < len(medals) else f"`#{idx+1}`"
            lines.append(f"{medal} <@{user_id}> — **Level {lvl}** (`{xp:,} XP`)")

        embed = standard_embed(
            title=f"🏆 {ctx.guild.name} • Active Chat Leaderboard",
            description="\n".join(lines),
            color=0xFEE75C
        )
        embed.set_footer(text="Updated in real time • Chat to climb the ranks")
        await ctx.send(embed=embed)

    # ==========================================
    # 3. ADMIN MANAGEMENT COMMANDS
    # ==========================================
    @commands.command(name="setxp", help="Admin command: Set a user's XP and Level. E.g. $setxp @user 500 5")
    @commands.has_permissions(administrator=True)
    async def set_xp_cmd(self, ctx: commands.Context, member: discord.Member, xp: int, level: int = 0):
        await db.set_user_xp(ctx.guild.id, member.id, max(0, xp), max(0, level))
        await ctx.send(embed=success_embed(
            "Level Updated",
            f"Successfully updated {member.mention}'s stats to **Level {level}** (`{xp:,} XP`)."
        ))

    @commands.command(name="resetlevels", help="Admin command: Reset all member levels and XP for this server.")
    @commands.has_permissions(administrator=True)
    async def reset_levels_cmd(self, ctx: commands.Context):
        await db.reset_guild_levels(ctx.guild.id)
        await ctx.send(embed=success_embed(
            "Leaderboard Reset",
            f"All leveling progress and XP records for **{ctx.guild.name}** have been reset."
        ))

async def setup(bot: commands.Bot):
    await bot.add_cog(Levels(bot))
