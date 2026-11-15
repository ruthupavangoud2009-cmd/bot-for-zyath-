import discord
from discord.ext import commands
import time
import random
from typing import Optional, Dict
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db


class Levels(commands.Cog):
    """Configurable server leveling, announcements and milestone roles."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.xp_cooldowns: Dict[tuple, float] = {}

    def make_progress_bar(self, current: int, total: int, length: int = 10) -> str:
        if total <= 0:
            return "░" * length
        ratio = min(1.0, max(0.0, current / total))
        filled = int(ratio * length)
        return f"[{'█' * filled}{'░' * (length - filled)}] `{int(ratio * 100)}%`"

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        settings = await db.get_level_settings(message.guild.id)
        if not settings.get("enabled", False):
            return
        key = (message.guild.id, message.author.id)
        now = time.time()
        if now - self.xp_cooldowns.get(key, 0) < 60:
            return
        self.xp_cooldowns[key] = now
        gained_xp = random.randint(15, 25)
        if db.is_guild_premium(message.guild.id) or db.is_user_premium(message.author.id):
            gained_xp = int(gained_xp * 1.5)
        leveled_up, new_level, _ = await db.add_xp(message.guild.id, message.author.id, gained_xp)
        if not leveled_up:
            return

        rewards = await db.get_level_rewards(message.guild.id)
        reached = [r for r in rewards if new_level >= int(r["level"])]
        reward_text = ""
        if reached:
            earned_roles = []
            failed_roles = []
            for reward in sorted(reached, key=lambda r: int(r["level"])):
                role = message.guild.get_role(int(reward["role_id"]))
                if role and role not in message.author.roles:
                    try:
                        await message.author.add_roles(role, reason=f"Reached level {new_level} milestone")
                        earned_roles.append(role)
                    except discord.Forbidden:
                        failed_roles.append(role)
            if earned_roles:
                reward_text = f"\\n🏅 **Milestone rewards:** " + ", ".join(role.mention for role in earned_roles)
            if failed_roles:
                reward_text += "\\n⚠️ Some milestone roles could not be assigned. Check my Manage Roles permission and role position.\n\n        embed = standard_embed(
            title="🎉 LEVEL UP!",
            description=f"Congratulations {message.author.mention}! You reached **Level {new_level}**! 🚀{reward_text}",
            color=0x57F287,
            thumbnail=message.author.display_avatar.url
        )
        embed.set_footer(text=f"{message.guild.name} • Community Levels")
        target = self.bot.get_channel(settings.get("channel_id")) if settings.get("channel_id") else message.channel
        if target is None:
            target = message.channel
        try:
            await target.send(content=message.author.mention, embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            pass

    @commands.command(name="rank", aliases=["lvl", "level"], help="View your or another member's level.")
    async def rank_cmd(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        settings = await db.get_level_settings(ctx.guild.id)
        if not settings.get("enabled", False):
            return await ctx.send(embed=info_embed("Levels Disabled", "An administrator can enable levels with `$levels enable`."))
        target = member or ctx.author
        data = await db.get_level_data(ctx.guild.id, target.id)
        lvl, xp = data["level"], data["xp"]
        needed_xp = 5 * (lvl ** 2) + 50 * lvl + 100
        rank = await db.get_user_rank(ctx.guild.id, target.id)
        prem_badge = " 💎 [VIP]" if (db.is_user_premium(target.id) or db.is_guild_premium(ctx.guild.id)) else ""
        embed = standard_embed(
            title=f"📊 {target.display_name}'s Level{prem_badge}",
            description=f"• **Server Rank:** `#{rank}` 🏆\n• **Level:** `{lvl}` ⭐\n• **XP:** `{xp:,} / {needed_xp:,}`\n• **Progress:** {self.make_progress_bar(xp, needed_xp)}",
            color=0x5865F2, thumbnail=target.display_avatar.url
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command(name="leaderboard", aliases=["top", "xplb"], help="Show the server XP leaderboard.")
    async def leaderboard_cmd(self, ctx: commands.Context):
        settings = await db.get_level_settings(ctx.guild.id)
        if not settings.get("enabled", False):
            return await ctx.send(embed=info_embed("Levels Disabled", "An administrator can enable levels with `$levels enable`."))
        top_users = await db.get_leaderboard(ctx.guild.id, limit=10)
        if not top_users:
            return await ctx.send(embed=info_embed("Leaderboard", "No XP records yet. Start chatting!"))
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        lines = [f"{medals[i]} <@{u['user_id']}> — **Level {u['level']}** (`{u['xp']:,} XP`)" for i, u in enumerate(top_users)]
        embed = standard_embed(title=f"🏆 {ctx.guild.name} • Leaderboard", description="\n".join(lines), color=0xFEE75C)
        embed.set_footer(text="Live server XP rankings")
        await ctx.send(embed=embed)

    @commands.group(name="levels", invoke_without_command=True, help="Configure the server leveling system.")
    @commands.has_guild_permissions(administrator=True)
    async def levels_group(self, ctx: commands.Context):
        settings = await db.get_level_settings(ctx.guild.id)
        channel = f"<#{settings['channel_id']}>" if settings.get("channel_id") else "Same channel where the member levels up"
        rewards = await db.get_level_rewards(ctx.guild.id)
        reward_lines = [f"• Level **{r['level']}** → <@&{r['role_id']}>" for r in rewards] or ["No milestone roles configured."]
        embed = standard_embed(
            title="⚙️ Level System Settings",
            description=f"**Status:** {'🟢 Enabled' if settings.get('enabled') else '🔴 Disabled'}\n**Announcement channel:** {channel}\n\n**Milestone roles**\n" + "\n".join(reward_lines) + "\n\n**Commands**\n`$levels enable/disable`\n`$levels channel #channel`\n`$levels reward set <level> @role`\n`$levels reward remove <level>`",
            color=0x5865F2
        )
        await ctx.send(embed=embed)

    @levels_group.command(name="enable")
    async def levels_enable(self, ctx: commands.Context):
        await db.set_level_settings(ctx.guild.id, enabled=True)
        await ctx.send(embed=success_embed("Levels Enabled", "Members now earn XP when chatting."))

    @levels_group.command(name="disable")
    async def levels_disable(self, ctx: commands.Context):
        await db.set_level_settings(ctx.guild.id, enabled=False)
        await ctx.send(embed=success_embed("Levels Disabled", "XP earning and level announcements are now paused. Existing levels are saved and will remain."))

    @levels_group.command(name="channel")
    async def levels_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        if channel is None:
            await db.set_level_settings(ctx.guild.id, channel_id=None)
            return await ctx.send(embed=success_embed("Level Channel Reset", "Level-up messages will appear in the channel where the member levels up."))
        await db.set_level_settings(ctx.guild.id, channel_id=channel.id)
        await ctx.send(embed=success_embed("Level Channel Set", f"Level-up announcements will be sent to {channel.mention}."))

    @levels_group.group(name="reward", invoke_without_command=True)
    async def levels_reward(self, ctx: commands.Context):
        await ctx.send("Use `$levels reward set <level> @role` or `$levels reward remove <level>`.")

    @levels_reward.command(name="set")
    async def levels_reward_set(self, ctx: commands.Context, level: int, role: discord.Role):
        if level < 1:
            return await ctx.send(embed=error_embed("Invalid Level", "Reward level must be 1 or higher."))
        if role.is_default() or role.managed:
            return await ctx.send(embed=error_embed("Invalid Role", "Choose a normal server role."))
        await db.set_level_reward(ctx.guild.id, level, role.id)
        await ctx.send(embed=success_embed("Milestone Role Saved", f"Members who reach level **{level}** will receive {role.mention}."))

    @levels_reward.command(name="remove")
    async def levels_reward_remove(self, ctx: commands.Context, level: int):
        removed = await db.remove_level_reward(ctx.guild.id, level)
        if removed:
            await ctx.send(embed=success_embed("Reward Removed", f"Removed the level **{level}** role reward."))
        else:
            await ctx.send(embed=error_embed("Not Found", f"No reward is configured for level {level}."))

    @commands.command(name="setxp", help="Set a member's XP and level. Example: $setxp @user 500 5")
    @commands.has_permissions(administrator=True)
    async def set_xp_cmd(self, ctx: commands.Context, member: discord.Member, xp: int, level: int = 0):
        await db.set_user_xp(ctx.guild.id, member.id, max(0, xp), max(0, level))
        await ctx.send(embed=success_embed("Level Updated", f"Updated {member.mention} to **Level {max(0, level)}** (`{max(0, xp):,} XP`)."))

    @commands.command(name="resetlevels", help="Reset all XP and levels in this server.")
    @commands.has_permissions(administrator=True)
    async def reset_levels_cmd(self, ctx: commands.Context):
        await db.reset_guild_levels(ctx.guild.id)
        await ctx.send(embed=success_embed("Leaderboard Reset", "All level and XP progress has been reset."))


async def setup(bot: commands.Bot):
    await bot.add_cog(Levels(bot))
