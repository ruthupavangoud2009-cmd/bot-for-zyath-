import discord
from discord.ext import commands
import os
import psutil
from datetime import datetime
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db

OWNER_IDS = {1521774957065928734, 1505515188991033409}

def is_bot_owner():
    async def predicate(ctx: commands.Context):
        if ctx.author.id in OWNER_IDS or await ctx.bot.is_owner(ctx.author):
            return True
        await ctx.send(embed=error_embed("Access Denied", "⛔ This command is restricted to the bot owners only."))
        return False
    return commands.check(predicate)

class Owner(commands.Cog):
    """Exclusive command suite for the 2 bot owners."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = datetime.utcnow()

    @commands.command(name="reload", aliases=["rl"], help="Hot reload a cog or all cogs without downtime. E.g. $reload shop or $reload all")
    @is_bot_owner()
    async def reload_cog(self, ctx: commands.Context, cog_name: str):
        cogs = [
            "moderation", "tickets", "welcomer", "gtn", "vouches",
            "trades", "shop", "fun", "help", "owner", "slash"
        ]
        
        target = cog_name.lower().replace("cogs.", "").strip()

        if target == "all":
            reloaded = []
            failed = []
            for c in cogs:
                try:
                    await self.bot.reload_extension(f"cogs.{c}")
                    reloaded.append(c)
                except Exception as e:
                    failed.append(f"{c}: {str(e)}")

            desc = f"✅ **Reloaded ({len(reloaded)}):** {', '.join(reloaded)}\n"
            if failed:
                desc += f"❌ **Failed ({len(failed)}):**\n" + "\n".join(failed)
            return await ctx.send(embed=info_embed("Extensions Reloaded", desc))

        full_name = f"cogs.{target}"
        try:
            await self.bot.reload_extension(full_name)
            await ctx.send(embed=success_embed("Extension Reloaded", f"Successfully reloaded `{full_name}`!"))
        except Exception as e:
            await ctx.send(embed=error_embed("Reload Error", f"Failed to reload `{full_name}`:\n```{str(e)}```"))

    @commands.command(name="announce", help="Broadcast an official embed announcement to a channel.")
    @is_bot_owner()
    async def announce(self, ctx: commands.Context, channel: discord.TextChannel, *, message: str):
        if "|" in message:
            parts = message.split("|", 1)
            title = parts[0].strip()
            desc = parts[1].strip()
        else:
            title = f"📢 Official Announcement • {ctx.guild.name}"
            desc = message.strip()

        embed = standard_embed(title=title, description=desc, color=0x5865F2)
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=f"Sent by {ctx.author.display_name} • Zyath Management")

        await channel.send(embed=embed)
        await ctx.send(embed=success_embed("Announcement Sent", f"Broadcast posted in {channel.mention}."))

    @commands.command(name="dm", help="Send a direct message to a user as the bot.")
    @is_bot_owner()
    async def direct_message(self, ctx: commands.Context, member: discord.Member, *, text: str):
        try:
            embed = standard_embed(
                title=f"Message from {ctx.guild.name} Management",
                description=text,
                color=0x5865F2
            )
            await member.send(embed=embed)
            await ctx.send(embed=success_embed("DM Delivered", f"Successfully sent message to {member.mention}."))
        except Exception as e:
            await ctx.send(embed=error_embed("DM Failed", f"Could not message user: {str(e)}"))

    @commands.command(name="botstats", aliases=["diagnostics", "bs", "stats"], help="View hardware, database, and system statistics.")
    @is_bot_owner()
    async def system_diagnostics(self, ctx: commands.Context):
        uptime = datetime.utcnow() - self.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        # Memory usage
        process = psutil.Process(os.getpid())
        ram_mb = round(process.memory_info().rss / 1024 / 1024, 2)

        # Database counts
        settings = await db.get_guild_settings(ctx.guild.id)
        vouches = await db.get_vouches(ctx.guild.id, ctx.author.id)
        shop_items = await db.get_shop_items(ctx.guild.id)

        embed = standard_embed(
            title="⚙️ Zyath Bot • Master Diagnostics",
            description="System performance and database diagnostics.",
            color=0x3447003
        )
        embed.add_field(name="👑 Bot Owners", value="<@1521774957065928734>\n<@1505515188991033409>", inline=True)
        embed.add_field(name="⏱️ Uptime", value=uptime_str, inline=True)
        embed.add_field(name="📶 WebSocket Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="💾 RAM Usage", value=f"{ram_mb} MB", inline=True)
        embed.add_field(name="🌐 Guilds", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="👥 Total Members", value=f"{sum(g.member_count for g in self.bot.guilds):,}", inline=True)
        embed.add_field(name="🛒 Shop Items (Server)", value=str(len(shop_items)), inline=True)
        embed.add_field(name="🗄️ Database", value="`zyath_bot.db` (SQLite3 / aiosqlite)", inline=True)

        await ctx.send(embed=embed)

    @commands.group(name="np", invoke_without_command=True, help="Manage no-prefix authorized users. E.g. $np add @user")
    @is_bot_owner()
    async def np_group(self, ctx: commands.Context):
        await ctx.send(embed=info_embed(
            "No-Prefix Management",
            "• `$np add @user` - Grant no-prefix access (run commands without `$`).\n"
            "• `$np remove @user` - Revoke no-prefix access.\n"
            "• `$np list` - List all authorized no-prefix users."
        ))

    @np_group.command(name="add", help="Authorize a user to run all commands without prefix.")
    @is_bot_owner()
    async def np_add(self, ctx: commands.Context, member: discord.Member):
        await db.add_no_prefix_user(member.id, ctx.author.id)
        await ctx.send(embed=success_embed(
            "No-Prefix Granted",
            f"🌟 {member.mention} (`{member.id}`) can now run all bot commands **without prefix**!"
        ))

    @np_group.command(name="remove", aliases=["del", "rem"], help="Revoke no-prefix access for a user.")
    @is_bot_owner()
    async def np_remove(self, ctx: commands.Context, member: discord.Member):
        removed = await db.remove_no_prefix_user(member.id)
        if removed:
            await ctx.send(embed=success_embed("No-Prefix Revoked", f"Removed no-prefix access for {member.mention}."))
        else:
            await ctx.send(embed=error_embed("Not Found", f"{member.mention} was not in the no-prefix list."))

    @np_group.command(name="list", help="List all users authorized to run commands without prefix.")
    @is_bot_owner()
    async def np_list(self, ctx: commands.Context):
        users = await db.get_all_no_prefix_users()
        desc = "**Default Owners (Permanent NP):**\n• <@1521774957065928734>\n• <@1505515188991033409>\n\n**Authorized Users:**\n"
        if not users:
            desc += "*No additional users authorized.*"
        else:
            for u in users:
                desc += f"• <@{u['user_id']}> (`{u['user_id']}`) — added by <@{u['added_by']}>\n"

        embed = standard_embed(
            title="⚡ No-Prefix Whitelist",
            description=desc,
            color=0x57F287
        )
        await ctx.send(embed=embed)

    @commands.command(name="sync", help="Sync application slash commands tree.")
    @is_bot_owner()
    async def sync_tree(self, ctx: commands.Context):
        msg = await ctx.send("🔄 Syncing slash commands to Discord...")
        try:
            synced = await self.bot.tree.sync()
            await msg.edit(content=f"✅ Successfully synced **{len(synced)}** slash commands globally!")
        except Exception as e:
            await msg.edit(content=f"❌ Error syncing commands: {str(e)}")

    @commands.command(name="checkperms", aliases=["perms", "testperms"], help="Check and diagnose bot permissions in this server.")
    async def check_perms(self, ctx: commands.Context):
        me = ctx.guild.me
        perms = me.guild_permissions
        settings = await db.get_guild_settings(ctx.guild.id)
        
        def mark(val: bool):
            return "✅ Enabled" if val else "❌ Missing (Required!)"

        admin = perms.administrator
        manage_channels = perms.manage_channels
        manage_roles = perms.manage_roles
        manage_messages = perms.manage_messages
        send_messages = perms.send_messages
        embed_links = perms.embed_links
        cat_id = settings.get("ticket_category_id")
        role_id = settings.get("ticket_staff_role_id")
        logs_id = settings.get("ticket_logs_channel_id")

        cat_str = f"<#{cat_id}>" if cat_id else "⚠️ Not set (Creates at root)"
        role_str = f"<@&{role_id}>" if role_id else "⚠️ Not set (Admins only)"
        logs_str = f"<#{logs_id}>" if logs_id else "⚠️ Not set"

        embed = standard_embed(
            title=f"🛡️ Server Permissions Audit • {ctx.guild.name}",
            description=(
                f"**Bot Highest Role:** {me.top_role.mention}\n"
                f"**Bot Position:** #{me.top_role.position} of {len(ctx.guild.roles)} roles\n\n"
                f"**Critical Permissions:**\n"
                f"• **Administrator:** {mark(admin)}\n"
                f"• **Manage Channels:** {mark(manage_channels)}\n"
                f"• **Manage Roles:** {mark(manage_roles)}\n"
                f"• **Manage Messages:** {mark(manage_messages)}\n"
                f"• **Embed Links:** {mark(embed_links)}\n"
                f"• **Attach Files:** {mark(attach_files)}\n\n"
                f"**Ticket System Configuration:**\n"
                f"• Category: {cat_str}\n"
                f"• Staff Role: {role_str}\n"
                f"• Logs Channel: {logs_str}\n\n"
                f"💡 *Tip: Grant the bot role **Administrator** in Server Settings to ensure 100% functionality without permission conflicts!*"
            ),
            color=0x57F287 if (admin or manage_channels) else 0xED4245
        )
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Owner(bot))
