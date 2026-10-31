import discord
from discord.ext import commands
import datetime
import re
from utils.embeds import success_embed, error_embed, info_embed, standard_embed
from utils.database import db

def parse_time(time_str: str) -> datetime.timedelta | None:
    match = re.match(r"^(\d+)([smhd])$", time_str.lower().strip())
    if not match:
        return None
    val, unit = int(match.group(1)), match.group(2)
    if unit == "s":
        return datetime.timedelta(seconds=val)
    elif unit == "m":
        return datetime.timedelta(minutes=val)
    elif unit == "h":
        return datetime.timedelta(hours=val)
    elif unit == "d":
        return datetime.timedelta(days=val)
    return None

class Moderation(commands.Cog):
    """Full-featured modern moderation suite."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def log_action(self, guild: discord.Guild, embed: discord.Embed):
        settings = await db.get_guild_settings(guild.id)
        channel_id = settings.get("modlog_channel_id")
        if channel_id:
            channel = guild.get_channel(channel_id)
            if channel and channel.permissions_for(guild.me).send_messages:
                try:
                    await channel.send(embed=embed)
                except Exception:
                    pass

    @commands.command(name="setmodlog", help="Set the channel where moderation actions will be logged.")
    @commands.has_permissions(administrator=True)
    async def set_modlog(self, ctx: commands.Context, channel: discord.TextChannel):
        await db.update_guild_setting(ctx.guild.id, "modlog_channel_id", channel.id)
        await ctx.send(embed=success_embed("Mod Log Channel Set", f"Moderation logs will now be sent to {channel.mention}."))

    @commands.command(name="kick", help="Kick a member from the server.")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send(embed=error_embed("Permission Denied", "You cannot kick members with higher or equal roles."))
        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send(embed=error_embed("Bot Hierarchy Error", "I cannot kick someone with higher or equal roles to mine."))

        try:
            await member.send(embed=error_embed("You Were Kicked", f"You have been kicked from **{ctx.guild.name}**.\n**Reason:** {reason}"))
        except Exception:
            pass

        await member.kick(reason=f"{ctx.author} ({ctx.author.id}): {reason}")
        embed = success_embed("Member Kicked", f"👢 **{member}** was kicked by {ctx.author.mention}.\n**Reason:** {reason}")
        await ctx.send(embed=embed)
        await self.log_action(ctx.guild, embed)

    @commands.command(name="ban", help="Ban a member from the server.")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send(embed=error_embed("Permission Denied", "You cannot ban members with higher or equal roles."))
        if member.top_role >= ctx.guild.me.top_role:
            return await ctx.send(embed=error_embed("Bot Hierarchy Error", "I cannot ban someone with higher or equal roles to mine."))

        try:
            await member.send(embed=error_embed("You Were Banned", f"You have been banned from **{ctx.guild.name}**.\n**Reason:** {reason}"))
        except Exception:
            pass

        await member.ban(reason=f"{ctx.author} ({ctx.author.id}): {reason}", delete_message_days=1)
        embed = success_embed("Member Banned", f"🔨 **{member}** was banned by {ctx.author.mention}.\n**Reason:** {reason}")
        await ctx.send(embed=embed)
        await self.log_action(ctx.guild, embed)

    @commands.command(name="unban", help="Unban a user by their ID.")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: int, *, reason: str = "No reason provided"):
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=f"{ctx.author}: {reason}")
            embed = success_embed("Member Unbanned", f"🔓 **{user}** ({user.id}) was unbanned.\n**Reason:** {reason}")
            await ctx.send(embed=embed)
            await self.log_action(ctx.guild, embed)
        except discord.NotFound:
            await ctx.send(embed=error_embed("Not Found", "That user is not banned or could not be found."))
        except Exception as e:
            await ctx.send(embed=error_embed("Error", str(e)))

    @commands.command(name="mute", aliases=["timeout"], help="Timeout/mute a member. E.g. $mute @user 10m [reason]")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def mute(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = "No reason provided"):
        delta = parse_time(duration)
        if not delta:
            return await ctx.send(embed=error_embed("Invalid Duration", "Please provide a valid duration like `10m`, `1h`, or `7d`."))
        if delta.total_seconds() > 28 * 86400:
            return await ctx.send(embed=error_embed("Duration Too Long", "Discord timeouts can be at most 28 days."))

        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send(embed=error_embed("Permission Denied", "You cannot mute members with higher or equal roles."))

        until = discord.utils.utcnow() + delta
        await member.timeout(until, reason=f"{ctx.author}: {reason}")
        embed = success_embed("Member Timed Out", f"🔇 **{member.mention}** was muted for **{duration}**.\n**Reason:** {reason}")
        await ctx.send(embed=embed)
        await self.log_action(ctx.guild, embed)

    @commands.command(name="unmute", help="Remove timeout/mute from a member.")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def unmute(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        await member.timeout(None, reason=f"{ctx.author}: {reason}")
        embed = success_embed("Member Unmuted", f"🔊 **{member.mention}** timeout was removed by {ctx.author.mention}.")
        await ctx.send(embed=embed)
        await self.log_action(ctx.guild, embed)

    @commands.command(name="warn", help="Issue an official logged warning to a member and deliver a direct message notification.")
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        warn_id = await db.add_warning(ctx.guild.id, member.id, ctx.author.id, reason)
        warnings = await db.get_warnings(ctx.guild.id, member.id)

        # Send super cool official DM notification to warned member
        dm_delivered = False
        try:
            dm_embed = standard_embed(
                title=f"⚠️ Official Warning • {ctx.guild.name}",
                description=(
                    f"Hello {member.mention},\n"
                    f"You have received an official disciplinary warning in **{ctx.guild.name}**.\n\n"
                    f"📋 **Warning Details:**\n"
                    f"• **Reason:** `{reason}`\n"
                    f"• **Issued By:** {ctx.author.mention} (`{ctx.author.display_name}`)\n"
                    f"• **Warning ID:** `#{warn_id}`\n"
                    f"• **Your Total Warnings:** `{len(warnings)}` active warning(s)\n\n"
                    f"🛡️ **Important Notice:**\n"
                    f"> Repeated violations may lead to temporary timeouts, kicks, or a permanent server ban.\n"
                    f"> Please review the rules in **{ctx.guild.name}** to maintain a clean standing."
                ),
                color=0xED4245
            )
            if ctx.guild.icon:
                dm_embed.set_thumbnail(url=ctx.guild.icon.url)
            dm_embed.set_footer(text=f"Server Moderation Team • {ctx.guild.name}")
            await member.send(embed=dm_embed)
            dm_delivered = True
        except (discord.Forbidden, discord.HTTPException):
            dm_delivered = False

        dm_note = "📬 *User was notified via Direct Message.*" if dm_delivered else "⚠️ *Could not deliver DM (User has DMs closed).* "
        embed = success_embed(
            "Member Warned",
            f"⚠️ **{member.mention}** (`{member.id}`) was officially warned.\n"
            f"**Reason:** `{reason}`\n"
            f"**Warning ID:** `#{warn_id}` • **Total Warnings:** `{len(warnings)}`\n\n"
            f"{dm_note}"
        )
        await ctx.send(embed=embed)
        await self.log_action(ctx.guild, embed)

    @commands.command(name="warnings", aliases=["warns"], help="Check warnings for a member.")
    @commands.has_permissions(moderate_members=True)
    async def warnings(self, ctx: commands.Context, member: discord.Member):
        warns = await db.get_warnings(ctx.guild.id, member.id)
        if not warns:
            return await ctx.send(embed=info_embed("Clean Record", f"**{member.display_name}** has 0 warnings."))

        desc = f"Total Warnings: **{len(warns)}**\n\n"
        for idx, w in enumerate(warns[:10], start=1):
            mod = ctx.guild.get_member(w['mod_id'])
            mod_name = mod.display_name if mod else f"ID: {w['mod_id']}"
            desc += f"**#{w['id']}** | Mod: {mod_name} | {w['timestamp']}\n`{w['reason']}`\n\n"

        embed = standard_embed(
            title=f"Warnings for {member.display_name}",
            description=desc,
            author=member
        )
        await ctx.send(embed=embed)

    @commands.command(name="clearwarnings", aliases=["clearwarns"], help="Clear all warnings for a member.")
    @commands.has_permissions(moderate_members=True)
    async def clearwarnings(self, ctx: commands.Context, member: discord.Member):
        count = await db.clear_warnings(ctx.guild.id, member.id)
        await ctx.send(embed=success_embed("Warnings Cleared", f"Cleared **{count}** warning(s) for {member.mention}."))

    @commands.command(name="purge", aliases=["clear"], help="Bulk delete messages. E.g. $purge 20 [@user]")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, limit: int, member: discord.Member = None):
        if limit < 1 or limit > 100:
            return await ctx.send(embed=error_embed("Invalid Amount", "Please specify a number between 1 and 100."))

        await ctx.message.delete()

        def check(m):
            if member:
                return m.author.id == member.id
            return True

        deleted = await ctx.channel.purge(limit=limit, check=check)
        msg = await ctx.send(embed=success_embed("Purged Messages", f"Successfully deleted **{len(deleted)}** messages."))
        await msg.delete(delay=4)

    @commands.command(name="lock", help="Lock a channel to prevent regular members from chatting.")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def lock(self, ctx: commands.Context, channel: discord.TextChannel = None, *, reason: str = "Channel locked by moderator"):
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        if overwrite.send_messages is False:
            return await ctx.send(embed=error_embed("Already Locked", f"{channel.mention} is already locked."))

        overwrite.send_messages = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason=reason)
        await channel.send(embed=warning_embed("Channel Locked", f"🔒 This channel was locked by {ctx.author.mention}.\n**Reason:** {reason}"))
        if channel.id != ctx.channel.id:
            await ctx.send(embed=success_embed("Channel Locked", f"Successfully locked {channel.mention}."))

    @commands.command(name="unlock", help="Unlock a previously locked channel.")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def unlock(self, ctx: commands.Context, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        if overwrite.send_messages is not False:
            return await ctx.send(embed=error_embed("Not Locked", f"{channel.mention} is not locked."))

        overwrite.send_messages = None
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await channel.send(embed=success_embed("Channel Unlocked", f"🔓 This channel has been unlocked by {ctx.author.mention}."))
        if channel.id != ctx.channel.id:
            await ctx.send(embed=success_embed("Channel Unlocked", f"Successfully unlocked {channel.mention}."))

    @commands.command(name="slowmode", help="Set channel slowmode in seconds. E.g. $slowmode 5")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def slowmode(self, ctx: commands.Context, seconds: int, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        if seconds < 0 or seconds > 21600:
            return await ctx.send(embed=error_embed("Invalid Duration", "Slowmode must be between 0 and 21600 seconds (6 hours)."))

        await channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await ctx.send(embed=success_embed("Slowmode Disabled", f"Slowmode removed in {channel.mention}."))
        else:
            await ctx.send(embed=success_embed("Slowmode Updated", f"Slowmode set to **{seconds}s** in {channel.mention}."))

    @commands.command(name="nick", help="Change a member's nickname.")
    @commands.has_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(manage_nicknames=True)
    async def nick(self, ctx: commands.Context, member: discord.Member, *, nickname: str = None):
        try:
            await member.edit(nick=nickname)
            name = nickname if nickname else member.name
            await ctx.send(embed=success_embed("Nickname Changed", f"Updated nickname for {member.mention} to **{name}**."))
        except Exception as e:
            await ctx.send(embed=error_embed("Error", str(e)))

    @commands.command(name="role", help="Add or remove role from member. E.g. $role add @user @Role")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def role(self, ctx: commands.Context, action: str, member: discord.Member, role: discord.Role):
        action = action.lower()
        if role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send(embed=error_embed("Permission Denied", "You cannot manage roles higher or equal to your own top role."))
        if role >= ctx.guild.me.top_role:
            return await ctx.send(embed=error_embed("Bot Hierarchy Error", "I cannot assign or remove a role equal or above my highest role."))

        if action == "add":
            if role in member.roles:
                return await ctx.send(embed=warning_embed("Already Has Role", f"{member.mention} already has the {role.mention} role."))
            await member.add_roles(role)
            await ctx.send(embed=success_embed("Role Added", f"Added {role.mention} to {member.mention}."))
        elif action in ["remove", "rem"]:
            if role not in member.roles:
                return await ctx.send(embed=warning_embed("Does Not Have Role", f"{member.mention} does not have the {role.mention} role."))
            await member.remove_roles(role)
            await ctx.send(embed=success_embed("Role Removed", f"Removed {role.mention} from {member.mention}."))
        else:
            await ctx.send(embed=error_embed("Invalid Action", "Usage: `$role add @user @Role` or `$role remove @user @Role`"))

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
