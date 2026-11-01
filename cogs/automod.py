import discord
from discord.ext import commands
import re
import time
from typing import Dict, List
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db

DISCORD_INVITE_REGEX = r"(?:https?:\/\/)?(?:www\.)?(?:discord\.(?:gg|io|me|li)|discord(?:app)?\.com\/invite)\/([a-zA-Z0-9\-]+)"

class Automod(commands.Cog):
    """Server Shield Automoderation: Anti-Invites, Anti-Spam, Anti-Mass Mentions, Anti-Caps."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # In-memory rate limiting: {guild_id: {user_id: [timestamps]}}
        self.spam_tracker: Dict[int, Dict[int, List[float]]] = {}

    def is_staff(self, member: discord.Member) -> bool:
        return (
            member.guild_permissions.administrator
            or member.guild_permissions.manage_guild
            or member.guild_permissions.manage_messages
            or member.id == member.guild.owner_id
        )

    # ==========================================
    # AUTOMOD MANAGEMENT COMMAND
    # ==========================================
    @commands.group(name="automod", invoke_without_command=True, help="Manage server automoderation shields. E.g. $automod")
    @commands.has_permissions(administrator=True)
    async def automod_group(self, ctx: commands.Context):
        settings = await db.get_automod_settings(ctx.guild.id)

        def badge(val: bool):
            return "🟢 **Active**" if val else "⚪ **Disabled**"

        embed = standard_embed(
            title=f"🛡️ Automod Security Center • {ctx.guild.name}",
            description=(
                f"Automated server protection safeguards your community 24/7.\n\n"
                f"• **Anti-Invite Links:** {badge(settings['anti_invite'])}\n"
                f"• **Anti-Spam Flooding:** {badge(settings['anti_spam'])}\n"
                f"• **Anti-Mass Mentions (>5):** {badge(settings['anti_mention'])}\n"
                f"• **Anti-Caps Flood (>70%):** {badge(settings['anti_caps'])}\n\n"
                f"**Configuration Commands:**\n"
                f"`$automod invite on/off` — Toggle invite link filter\n"
                f"`$automod spam on/off` — Toggle message flooding filter\n"
                f"`$automod mentions on/off` — Toggle mass mention filter\n"
                f"`$automod caps on/off` — Toggle excessive caps filter"
            ),
            color=0x5865F2
        )
        await ctx.send(embed=embed)

    @automod_group.command(name="invite", help="Toggle Anti-Invite links. E.g. $automod invite on")
    @commands.has_permissions(administrator=True)
    async def toggle_invite(self, ctx: commands.Context, state: str):
        enabled = state.lower() in ["on", "enable", "true", "yes", "1"]
        await db.set_automod_setting(ctx.guild.id, "anti_invite", enabled)
        await ctx.send(embed=success_embed("Automod Updated", f"Anti-Invite protection is now **{'Enabled' if enabled else 'Disabled'}**."))

    @automod_group.command(name="spam", help="Toggle Anti-Spam flooding. E.g. $automod spam on")
    @commands.has_permissions(administrator=True)
    async def toggle_spam(self, ctx: commands.Context, state: str):
        enabled = state.lower() in ["on", "enable", "true", "yes", "1"]
        await db.set_automod_setting(ctx.guild.id, "anti_spam", enabled)
        await ctx.send(embed=success_embed("Automod Updated", f"Anti-Spam protection is now **{'Enabled' if enabled else 'Disabled'}**."))

    @automod_group.command(name="mentions", help="Toggle Anti-Mass Mentions. E.g. $automod mentions on")
    @commands.has_permissions(administrator=True)
    async def toggle_mentions(self, ctx: commands.Context, state: str):
        enabled = state.lower() in ["on", "enable", "true", "yes", "1"]
        await db.set_automod_setting(ctx.guild.id, "anti_mention", enabled)
        await ctx.send(embed=success_embed("Automod Updated", f"Anti-Mass Mentions protection is now **{'Enabled' if enabled else 'Disabled'}**."))

    @automod_group.command(name="caps", help="Toggle Anti-Caps filter. E.g. $automod caps on")
    @commands.has_permissions(administrator=True)
    async def toggle_caps(self, ctx: commands.Context, state: str):
        enabled = state.lower() in ["on", "enable", "true", "yes", "1"]
        await db.set_automod_setting(ctx.guild.id, "anti_caps", enabled)
        await ctx.send(embed=success_embed("Automod Updated", f"Anti-Caps filter is now **{'Enabled' if enabled else 'Disabled'}**."))

    # ==========================================
    # AUTOMOD LISTENER
    # ==========================================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or not isinstance(message.author, discord.Member):
            return

        if self.is_staff(message.author):
            return

        settings = await db.get_automod_settings(message.guild.id)

        # 1. Anti-Invite Links
        if settings.get("anti_invite"):
            if re.search(DISCORD_INVITE_REGEX, message.content, re.IGNORECASE):
                try:
                    await message.delete()
                    await message.channel.send(
                        f"⛔ {message.author.mention}, posting Discord invite links is strictly prohibited in **{message.guild.name}**!",
                        delete_after=8
                    )
                    return
                except Exception:
                    pass

        # 2. Anti-Mass Mentions (> 5 mentions)
        if settings.get("anti_mention"):
            total_mentions = len(message.mentions) + len(message.role_mentions)
            if total_mentions >= 5:
                try:
                    await message.delete()
                    await message.channel.send(
                        f"⛔ {message.author.mention}, mass mentions (> 5 pings) are blocked by server security!",
                        delete_after=8
                    )
                    return
                except Exception:
                    pass

        # 3. Anti-Caps (> 70% uppercase and length >= 15)
        if settings.get("anti_caps"):
            content = message.content.strip()
            letters = [c for c in content if c.isalpha()]
            if len(letters) >= 15:
                upper_count = sum(1 for c in letters if c.isupper())
                if upper_count / len(letters) >= 0.70:
                    try:
                        await message.delete()
                        await message.channel.send(
                            f"⛔ {message.author.mention}, please do not spam excessive ALL CAPS!",
                            delete_after=6
                        )
                        return
                    except Exception:
                        pass

        # 4. Anti-Spam Flooding (> 5 messages in 3 seconds)
        if settings.get("anti_spam"):
            gid = message.guild.id
            uid = message.author.id
            now = time.time()

            if gid not in self.spam_tracker:
                self.spam_tracker[gid] = {}
            if uid not in self.spam_tracker[gid]:
                self.spam_tracker[gid][uid] = []

            timestamps = self.spam_tracker[gid][uid]
            # Keep only timestamps within 3 seconds
            self.spam_tracker[gid][uid] = [t for t in timestamps if now - t < 3.0]
            self.spam_tracker[gid][uid].append(now)

            if len(self.spam_tracker[gid][uid]) >= 5:
                try:
                    await message.delete()
                    await message.channel.send(
                        f"⚠️ {message.author.mention}, slow down! Fast message flooding is blocked by Automod.",
                        delete_after=6
                    )
                    return
                except Exception:
                    pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Automod(bot))
