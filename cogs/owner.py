import discord
from discord.ext import commands
import os
import psutil
from datetime import datetime
from typing import Optional
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

def is_bot_staff():
    async def predicate(ctx: commands.Context):
        if (
            ctx.author.id in OWNER_IDS
            or await ctx.bot.is_owner(ctx.author)
            or db.is_staff_cached(ctx.author.id)
        ):
            return True
        await ctx.send(embed=error_embed("Access Denied", "⛔ This command is restricted to authorized bot staff only."))
        return False
    return commands.check(predicate)

class Owner(commands.Cog):
    """Exclusive command suite for bot owners and staff."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = datetime.utcnow()

    @commands.command(name="reload", help="Hot reload a cog or all cogs without downtime. E.g. $reload shop or $reload all")
    @is_bot_staff()
    async def reload_cog(self, ctx: commands.Context, cog_name: str):
        cogs = [
            "moderation", "automod", "tickets", "welcomer", "giveaway", "gw_games",
            "economy", "utility", "vouches", "trades", "shop", "fun", "help",
            "owner", "ai_manager", "slash", "premium", "levels", "autoresponder"
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

    @commands.command(name="botstats", aliases=["stats"], help="View hardware, database, and system statistics.")
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
        db_lat, db_engine = await db.ping()
        embed.add_field(name="🗄️ Database", value=f"`{db_engine}` ({db_lat}ms)", inline=True)

        await ctx.send(embed=embed)

    # Helper to resolve user mention or raw ID
    def _resolve_id(self, target: str) -> Optional[int]:
        clean = target.strip().replace("<@", "").replace(">", "").replace("!", "")
        return int(clean) if clean.isdigit() else None

    # ==========================================
    # NO-PREFIX SUITE ($np)
    # ==========================================
    @commands.group(name="np", invoke_without_command=True, help="Manage no-prefix authorized users. E.g. $np add @user")
    @is_bot_owner()
    async def np_group(self, ctx: commands.Context):
        await ctx.send(embed=info_embed(
            "⚡ No-Prefix Management",
            "• `$np add <@user|id>` - Grant no-prefix access (run commands without prefix `$`).\n"
            "• `$np remove <@user|id>` - Revoke no-prefix access.\n"
            "• `$np list` - List all authorized no-prefix users."
        ))

    @np_group.command(name="add", help="Authorize a user to run all commands without prefix.")
    @is_bot_owner()
    async def np_add(self, ctx: commands.Context, target: str):
        uid = self._resolve_id(target)
        if not uid:
            return await ctx.send(embed=error_embed("Invalid User", "Please mention a valid member or provide a 64-bit Discord User ID."))

        await db.add_no_prefix_user(uid, ctx.author.id)
        await ctx.send(embed=success_embed(
            "No-Prefix Granted",
            f"🌟 User <@{uid}> (`{uid}`) can now run all bot commands **without prefix**!\n*Saved permanently to database.*"
        ))

    @np_group.command(name="remove", aliases=["del", "rem"], help="Revoke no-prefix access for a user.")
    @is_bot_owner()
    async def np_remove(self, ctx: commands.Context, target: str):
        uid = self._resolve_id(target)
        if not uid:
            return await ctx.send(embed=error_embed("Invalid User", "Please mention a valid member or provide a 64-bit Discord User ID."))

        removed = await db.remove_no_prefix_user(uid)
        if removed:
            await ctx.send(embed=success_embed("No-Prefix Revoked", f"Removed no-prefix access for <@{uid}> (`{uid}`)."))
        else:
            await ctx.send(embed=error_embed("Not Found", f"User <@{uid}> was not in the no-prefix database."))

    @np_group.command(name="list", help="List all users authorized to run commands without prefix.")
    @is_bot_staff()
    async def np_list(self, ctx: commands.Context):
        users = await db.get_all_no_prefix_users()
        desc = "**Default Owners (Permanent NP):**\n• <@1521774957065928734>\n• <@1505515188991033409>\n\n**Authorized Database Users:**\n"
        if not users:
            desc += "*No additional users authorized in database.*"
        else:
            for u in users:
                desc += f"• <@{u['user_id']}> (`{u['user_id']}`) — added by <@{u['added_by']}>\n"

        embed = standard_embed(
            title="⚡ No-Prefix Whitelist",
            description=desc,
            color=0x57F287
        )
        await ctx.send(embed=embed)

    # ==========================================
    # BOT STAFF SYSTEM ($botstaff / $staff)
    # ==========================================
    @commands.group(name="botstaff", aliases=["staff", "team"], invoke_without_command=True, help="Manage authorized bot staff. E.g. $botstaff")
    @is_bot_staff()
    async def botstaff_group(self, ctx: commands.Context):
        embed = info_embed(
            "🛡️ Bot Staff Management",
            "• `$botstaff add <@user|id> [role]` - Appoint an authorized bot staff member.\n"
            "• `$botstaff remove <@user|id>` - Remove staff status from a user.\n"
            "• `$botstaff list` - List all active bot staff and roles.\n\n"
            "*Bot staff have access to diagnostics, server audits, reload controls, and command bypasses.*"
        )
        await ctx.send(embed=embed)

    @botstaff_group.command(name="add", help="Add an authorized bot staff member. E.g. $botstaff add @user Admin")
    @is_bot_owner()
    async def botstaff_add(self, ctx: commands.Context, target: str, *, role: str = "Staff"):
        uid = self._resolve_id(target)
        if not uid:
            return await ctx.send(embed=error_embed("Invalid User", "Please mention a member or provide a Discord User ID."))

        await db.add_bot_staff(uid, role, ctx.author.id)
        await ctx.send(embed=success_embed(
            "Bot Staff Appointed",
            f"🛡️ Appointed <@{uid}> (`{uid}`) as **{role}**!\n*Saved permanently in database.*"
        ))

    @botstaff_group.command(name="remove", aliases=["del", "rem"], help="Remove an authorized bot staff member.")
    @is_bot_owner()
    async def botstaff_remove(self, ctx: commands.Context, target: str):
        uid = self._resolve_id(target)
        if not uid:
            return await ctx.send(embed=error_embed("Invalid User", "Please mention a member or provide a Discord User ID."))

        removed = await db.remove_bot_staff(uid)
        if removed:
            await ctx.send(embed=success_embed("Staff Removed", f"Successfully removed <@{uid}> (`{uid}`) from Bot Staff."))
        else:
            await ctx.send(embed=error_embed("Not Found", f"User <@{uid}> was not listed as Bot Staff."))

    @botstaff_group.command(name="list", help="List all authorized bot staff members.")
    @is_bot_staff()
    async def botstaff_list(self, ctx: commands.Context):
        staff = await db.get_all_bot_staff()
        desc = "**Bot Owners (Root):**\n• <@1521774957065928734> (`1521774957065928734`)\n• <@1505515188991033409> (`1505515188991033409`)\n\n**Appointed Staff:**\n"
        if not staff:
            desc += "*No additional staff appointed in database.*"
        else:
            for s in staff:
                desc += f"• <@{s['user_id']}> (`{s['user_id']}`) — **{s['role']}** (added by <@{s['added_by']}>)\n"

        embed = standard_embed(
            title="🛡️ Official Bot Staff Directory",
            description=desc,
            color=0x5865F2
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

    @commands.command(name="checkperms", aliases=["perms"], help="Check and diagnose bot permissions in this server.")
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
        attach_files = perms.attach_files
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

    async def _get_image_bytes(self, ctx: commands.Context, url: str = None) -> tuple[bytes | None, str | None]:
        """Helper to extract image bytes from either an attachment or an HTTP(S) URL."""
        import aiohttp
        # 1. Check attachments
        if ctx.message.attachments:
            att = ctx.message.attachments[0]
            if att.size > 10 * 1024 * 1024:
                return None, "File too large! Discord images must be under 10MB."
            try:
                data = await att.read()
                return data, None
            except Exception as e:
                return None, f"Failed reading attachment: {e}"

        # 2. Check URL argument
        if url:
            clean_url = url.strip("<>").strip()
            if not clean_url.startswith(("http://", "https://")):
                return None, "Invalid image URL! Must start with `http://` or `https://`."
            try:
                timeout = aiohttp.ClientTimeout(total=15)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(clean_url) as resp:
                        if resp.status != 200:
                            return None, f"Could not download image (HTTP {resp.status})."
                        content_type = resp.headers.get("Content-Type", "")
                        if "image" not in content_type and not any(clean_url.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]):
                            return None, "The provided link does not appear to be a direct image file."
                        data = await resp.read()
                        if len(data) > 10 * 1024 * 1024:
                            return None, "Image exceeds 10MB maximum limit."
                        return data, None
            except Exception as e:
                return None, f"Network error downloading image: {e}"

        return None, "Please provide an image URL or attach an image file with your command!"

    @commands.command(name="setavatar", aliases=["changeavatar", "botavatar"], help="Change the bot profile avatar. E.g. $setavatar <url> or upload an image.")
    @is_bot_owner()
    async def set_avatar(self, ctx: commands.Context, url: str = None):
        """Owner-only command to change bot avatar."""
        msg = await ctx.send(embed=info_embed("Updating Avatar", "⏳ Downloading and processing image..."))
        data, err = await self._get_image_bytes(ctx, url)
        if err:
            return await msg.edit(embed=error_embed("Avatar Error", err))

        try:
            await self.bot.user.edit(avatar=data)
            embed = success_embed(
                "Bot Avatar Updated",
                "🎉 The bot avatar has been successfully updated!\n*(Discord may take 1-2 minutes to refresh the cache for all clients)*"
            )
            if self.bot.user.avatar:
                embed.set_thumbnail(url=self.bot.user.avatar.url)
            await msg.edit(embed=embed)
        except discord.HTTPException as e:
            if e.status == 429:
                await msg.edit(embed=error_embed("Rate Limited", "⚠️ Discord limits bot avatar changes to 2 per 10 minutes. Please wait before trying again."))
            else:
                await msg.edit(embed=error_embed("Discord API Error", f"Failed updating avatar: {e.text}"))
        except Exception as e:
            await msg.edit(embed=error_embed("Unexpected Error", str(e)))

    @commands.command(name="setbanner", aliases=["changebanner", "botbanner"], help="Change the bot profile banner. E.g. $setbanner <url> or upload an image.")
    @is_bot_owner()
    async def set_banner(self, ctx: commands.Context, url: str = None):
        """Owner-only command to change bot profile banner."""
        msg = await ctx.send(embed=info_embed("Updating Banner", "⏳ Downloading and processing banner image..."))
        data, err = await self._get_image_bytes(ctx, url)
        if err:
            return await msg.edit(embed=error_embed("Banner Error", err))

        try:
            await self.bot.user.edit(banner=data)
            embed = success_embed(
                "Bot Banner Updated",
                "🎉 The bot banner has been successfully updated!"
            )
            if self.bot.user.banner:
                embed.set_image(url=self.bot.user.banner.url)
            await msg.edit(embed=embed)
        except discord.HTTPException as e:
            if e.status == 429:
                await msg.edit(embed=error_embed("Rate Limited", "⚠️ Discord rate limit encountered. Please try again shortly."))
            else:
                await msg.edit(embed=error_embed("Discord API Error", f"Failed updating banner: {e.text}\n*Note: Setting a bot banner requires the application to support banners or Nitro.*"))
        except Exception as e:
            await msg.edit(embed=error_embed("Unexpected Error", str(e)))

    @commands.command(name="setname", aliases=["setbotname", "botname"], help="Change the bot username. E.g. $setname Zyath Bot")
    @is_bot_owner()
    async def set_name(self, ctx: commands.Context, *, new_name: str):
        """Owner-only command to change bot username."""
        clean_name = new_name.strip()
        if len(clean_name) < 2 or len(clean_name) > 32:
            return await ctx.send(embed=error_embed("Invalid Name", "Bot username must be between 2 and 32 characters."))

        try:
            await self.bot.user.edit(username=clean_name)
            from utils.config_manager import set_config_value
            set_config_value("bot_name", clean_name)
            await ctx.send(embed=success_embed("Bot Name Updated", f"✅ Bot username successfully changed to **{clean_name}**!"))
        except discord.HTTPException as e:
            await ctx.send(embed=error_embed("Discord API Error", f"Failed updating name: {e.text} *(Discord limits username changes to twice per hour)*"))
        except Exception as e:
            await ctx.send(embed=error_embed("Error", str(e)))

    @commands.command(name="setsupport", aliases=["setsupportserver", "supportserverset"], help="Change the official bot support server link dynamically. E.g. $setsupport https://discord.gg/zyath")
    @is_bot_owner()
    async def set_support_server_cmd(self, ctx: commands.Context, url: str):
        """Owner command to change the bot support server link."""
        from utils.config_manager import set_support_server
        clean_url = url.strip("<>").strip()
        if not (clean_url.startswith("http://") or clean_url.startswith("https://") or "discord.gg/" in clean_url):
            return await ctx.send(embed=error_embed("Invalid Link", "Please provide a valid Discord invite link (e.g. `https://discord.gg/zyath`)."))

        if not clean_url.startswith(("http://", "https://")):
            clean_url = f"https://{clean_url}"

        success = set_support_server(clean_url)
        if success:
            embed = standard_embed(
                title="✅ Support Server Link Updated",
                description=(
                    f"The official support server invite has been updated across all bot modules!\n\n"
                    f"🔗 **New Link:** {clean_url}\n\n"
                    f"All `$help`, `/help`, `$support`, `/support`, and ticket panels now point to this URL."
                ),
                color=0x57F287
            )
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Test Support Link", style=discord.ButtonStyle.link, url=clean_url, emoji="💬"))
            await ctx.send(embed=embed, view=view)
        else:
            await ctx.send(embed=error_embed("Config Error", "Failed to save support server link to `config.json`."))

    @commands.command(name="support", aliases=["supportserver", "invite-support"], help="Get the official bot support server invite link.")
    async def support_cmd(self, ctx: commands.Context):
        """Public command to view the support server invite and get help."""
        from utils.config_manager import get_support_server
        support_url = get_support_server()
        bot_name = self.bot.user.name if self.bot.user else "Zyath Bot"

        embed = standard_embed(
            title=f"💬 {bot_name} Official Support Server",
            description=(
                f"Need assistance, want to report a bug, or request a new feature?\n\n"
                f"Join our official support server for 24/7 staff help, announcements, updates, and community events!\n\n"
                f"🔗 **Direct Invite:** {support_url}"
            ),
            color=0x5865F2
        )
        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.set_footer(text=f"Requested by {ctx.author.display_name} • Zyath Management")

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Join Support Server", style=discord.ButtonStyle.link, url=support_url, emoji="💬"))
        if self.bot.user:
            invite_url = f"https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot%20applications.commands"
            view.add_item(discord.ui.Button(label="Invite Bot", style=discord.ButtonStyle.link, url=invite_url, emoji="🚀"))

        await ctx.send(embed=embed, view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(Owner(bot))

