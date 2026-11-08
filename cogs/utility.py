import discord
from discord.ext import commands
import time
import math
import re
import urllib.parse
from typing import Optional, Dict, Any
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db

class Utility(commands.Cog):
    """Essential All-in-One Server Utilities: AFK System, Sticky Messages, Snipe, QR Code, Math, Info."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # In-memory snipes: {channel_id: {"author": Member, "content": str, "time": timestamp, "attachments": []}}
        self.snipes: Dict[int, Dict[str, Any]] = {}
        # In-memory edit snipes: {channel_id: {"author": Member, "before": str, "after": str, "time": timestamp}}
        self.edit_snipes: Dict[int, Dict[str, Any]] = {}

    # ==========================================
    # 1. AFK SYSTEM
    # ==========================================
    @commands.command(name="afk", help="Set your status to AFK with an optional custom reason. E.g. $afk Eating lunch")
    async def afk_command(self, ctx: commands.Context, *, reason: str = "AFK"):
        clean_reason = reason.strip()[:150]
        await db.set_afk(ctx.guild.id, ctx.author.id, clean_reason)

        # Attempt to prepend [AFK] to nickname
        try:
            if not ctx.author.display_name.startswith("[AFK]"):
                new_nick = f"[AFK] {ctx.author.display_name}"[:32]
                await ctx.author.edit(nick=new_nick, reason="User set AFK status")
        except Exception:
            pass

        embed = standard_embed(
            title="💤 AFK Status Set",
            description=f"{ctx.author.mention} is now AFK: **{clean_reason}**\n*I will notify anyone who mentions you!*",
            color=0x34495E
        )
        await ctx.send(embed=embed)

    # ==========================================
    # 2. STICKY MESSAGES
    # ==========================================
    @commands.command(name="sticky", aliases=["stickymsg"], help="Pin a persistent message to the bottom of this channel. E.g. $sticky Read our rules!")
    @commands.has_permissions(manage_messages=True)
    async def set_sticky_cmd(self, ctx: commands.Context, *, message: str):
        clean_text = message.strip()
        await db.set_sticky(ctx.channel.id, ctx.guild.id, clean_text)

        # Send initial sticky message
        embed = standard_embed(
            title="📌 Pinned Announcement",
            description=clean_text,
            color=0xFEE75C
        )
        embed.set_footer(text="Sticky Message • Automatically stays at the bottom")
        msg = await ctx.send(embed=embed)
        await db.update_sticky_last_id(ctx.channel.id, msg.id)

        try:
            await ctx.message.delete()
        except Exception:
            pass

    @commands.command(name="unsticky", aliases=["delsticky"], help="Remove sticky message from this channel.")
    @commands.has_permissions(manage_messages=True)
    async def remove_sticky_cmd(self, ctx: commands.Context):
        sticky = await db.get_sticky(ctx.channel.id)
        if not sticky:
            return await ctx.send(embed=error_embed("No Sticky Message", "There is no active sticky message in this channel."))

        await db.remove_sticky(ctx.channel.id)
        if sticky.get("last_message_id"):
            try:
                old = await ctx.channel.fetch_message(sticky["last_message_id"])
                await old.delete()
            except Exception:
                pass

        await ctx.send(embed=success_embed("Sticky Removed", "The sticky message has been disabled for this channel."))

    # ==========================================
    # 3. SNIPE & EDITSNIPE
    # ==========================================
    @commands.command(name="snipe", help="Retrieve the last deleted message in this channel.")
    async def snipe_cmd(self, ctx: commands.Context):
        data = self.snipes.get(ctx.channel.id)
        if not data:
            return await ctx.send(embed=info_embed("Nothing to Snipe", "No recently deleted messages found in this channel!"))

        author = data["author"]
        content = data["content"] or "*[No text content (Image/Embed)]*"
        ts = data["time"]

        embed = standard_embed(
            title="🎯 Deleted Message Sniped",
            description=content,
            color=0xED4245
        )
        embed.set_author(name=f"{author.name} ({author.id})", icon_url=author.display_avatar.url)
        embed.set_footer(text=f"Deleted • {ts}")

        if data.get("attachments"):
            embed.set_image(url=data["attachments"][0])

        await ctx.send(embed=embed)

    @commands.command(name="editsnipe", aliases=["esnipe"], help="Retrieve the last edited message in this channel.")
    async def editsnipe_cmd(self, ctx: commands.Context):
        data = self.edit_snipes.get(ctx.channel.id)
        if not data:
            return await ctx.send(embed=info_embed("Nothing to Snipe", "No recently edited messages found in this channel!"))

        author = data["author"]
        before = data["before"]
        after = data["after"]

        embed = standard_embed(
            title="✏️ Edited Message Sniped",
            description=f"**Before:**\n{before}\n\n**After:**\n{after}",
            color=0xFEE75C
        )
        embed.set_author(name=f"{author.name} ({author.id})", icon_url=author.display_avatar.url)
        embed.set_footer(text=f"Edited • {data['time']}")
        await ctx.send(embed=embed)

    # ==========================================
    # 4. QR CODE GENERATOR
    # ==========================================
    @commands.command(name="qrcode", aliases=["qr"], help="Generate a high-resolution QR code image. E.g. $qr https://discord.gg/kyoka")
    async def qrcode_cmd(self, ctx: commands.Context, *, text: str):
        clean_text = text.strip()
        encoded = urllib.parse.quote(clean_text)
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=350x350&data={encoded}"

        embed = standard_embed(
            title="📱 QR Code Generated",
            description=f"**Content:** `{clean_text}`",
            color=0x5865F2
        )
        embed.set_image(url=qr_url)
        embed.set_footer(text="Scan with your phone camera!")
        await ctx.send(embed=embed)

    # ==========================================
    # 5. SAFE CALCULATOR
    # ==========================================
    @commands.command(name="calc", aliases=["calculate", "math"], help="Perform a mathematical calculation. E.g. $calc (25 * 4) / 5")
    async def calc_cmd(self, ctx: commands.Context, *, expression: str):
        clean_expr = expression.strip().replace("^", "**").replace("x", "*")
        # Security sanitization: only allow numbers and basic math characters
        if not re.match(r"^[\d\s\+\-\*\/\(\)\.\%]+$", clean_expr):
            return await ctx.send(embed=error_embed("Invalid Expression", "Only numbers and basic arithmetic operators `+ - * / ( ) %` are allowed."))

        try:
            # Safe evaluation with empty builtins
            result = eval(clean_expr, {"__builtins__": None}, {})
            embed = standard_embed(
                title="🧮 Math Calculation",
                description=f"**Input:** `{expression}`\n**Result:** `# {result}`",
                color=0x57F287
            )
            await ctx.send(embed=embed)
        except ZeroDivisionError:
            await ctx.send(embed=error_embed("Math Error", "Cannot divide by zero!"))
        except Exception as e:
            await ctx.send(embed=error_embed("Calculation Error", str(e)))

    # ==========================================
    # 6. ROLE INFO & CHANNEL INFO
    # ==========================================
    @commands.command(name="roleinfo", aliases=["ri"], help="View metadata, permissions, and member count of a role.")
    async def role_info(self, ctx: commands.Context, role: discord.Role):
        created_ts = int(role.created_at.timestamp())
        perms = [p[0].replace("_", " ").title() for p in role.permissions if p[1]]

        embed = standard_embed(
            title=f"🛡️ Role Dossier • {role.name}",
            description=(
                f"• **Role Mention:** {role.mention}\n"
                f"• **Role ID:** `{role.id}`\n"
                f"• **Hex Color:** `#{role.color.value:06X}`\n"
                f"• **Members with Role:** `{len(role.members)}`\n"
                f"• **Hoisted (Separated):** `{'Yes' if role.hoist else 'No'}`\n"
                f"• **Mentionable:** `{'Yes' if role.mentionable else 'No'}`\n"
                f"• **Position:** `#{role.position}` of `{len(ctx.guild.roles)}`\n"
                f"• **Created:** <t:{created_ts}:R>\n\n"
                f"**Key Permissions ({len(perms)}):**\n"
                f"*{', '.join(perms[:15]) if perms else 'None'}*"
            ),
            color=role.color if role.color.value != 0 else 0x5865F2
        )
        await ctx.send(embed=embed)

    @commands.command(name="channelinfo", aliases=["ci"], help="View telemetry, slowmode, and topic of a channel.")
    async def channel_info(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        target = channel or ctx.channel
        created_ts = int(target.created_at.timestamp())

        embed = standard_embed(
            title=f"📁 Channel Dossier • #{target.name}",
            description=(
                f"• **Mention:** {target.mention}\n"
                f"• **ID:** `{target.id}`\n"
                f"• **Category:** `{target.category.name if target.category else 'None'}`\n"
                f"• **Slowmode Rate:** `{target.slowmode_delay}s`\n"
                f"• **NSFW Channel:** `{'Yes' if target.is_nsfw() else 'No'}`\n"
                f"• **Created:** <t:{created_ts}:R>\n\n"
                f"**Channel Topic:**\n"
                f"*{target.topic or 'No topic configured.'}*"
            ),
            color=0x5865F2
        )
        await ctx.send(embed=embed)

    # ==========================================
    # 7. SERVER ICONS & BANNERS
    # ==========================================
    @commands.command(name="servericon", aliases=["guildicon", "sicon"], help="View server icon in high resolution.")
    async def server_icon(self, ctx: commands.Context):
        if not ctx.guild.icon:
            return await ctx.send(embed=error_embed("No Icon", "This server has no icon configured."))
        embed = standard_embed(title=f"🌐 {ctx.guild.name} • Server Icon", color=0x5865F2)
        embed.set_image(url=ctx.guild.icon.url)
        await ctx.send(embed=embed)

    @commands.command(name="serverbanner", aliases=["sbanner"], help="View server banner in high resolution.")
    async def server_banner(self, ctx: commands.Context):
        if not ctx.guild.banner:
            return await ctx.send(embed=error_embed("No Banner", "This server has no banner configured."))
        embed = standard_embed(title=f"🌐 {ctx.guild.name} • Server Banner", color=0x5865F2)
        embed.set_image(url=ctx.guild.banner.url)
        await ctx.send(embed=embed)

    @commands.command(name="userbanner", aliases=["ubanner"], help="View a member's profile banner.")
    async def user_banner(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        target = member or ctx.author
        fetched = await self.bot.fetch_user(target.id)
        if not fetched.banner:
            return await ctx.send(embed=error_embed("No Banner", f"{target.display_name} has no profile banner set."))
        embed = standard_embed(title=f"🎨 {target.display_name} • Profile Banner", color=0x5865F2)
        embed.set_image(url=fetched.banner.url)
        await ctx.send(embed=embed)

    # ==========================================
    # LISTENERS: SNIPES, AFK, & STICKY MESSAGES
    # ==========================================
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        attachments = [a.url for a in message.attachments if a.url]
        self.snipes[message.channel.id] = {
            "author": message.author,
            "content": message.content,
            "time": time.strftime("%H:%M:%S UTC"),
            "attachments": attachments
        }

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        self.edit_snipes[before.channel.id] = {
            "author": before.author,
            "before": before.content,
            "after": after.content,
            "time": time.strftime("%H:%M:%S UTC")
        }

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # 1. Check if author is returning from AFK
        afk_author = await db.get_afk(message.guild.id, message.author.id)
        if afk_author:
            await db.remove_afk(message.guild.id, message.author.id)
            elapsed_sec = int(time.time()) - afk_author["afk_time"]
            mins, secs = divmod(elapsed_sec, 60)
            hrs, mins = divmod(mins, 60)
            time_str = f"{hrs}h {mins}m" if hrs > 0 else f"{mins}m {secs}s"

            # Restore nick if possible
            try:
                if message.author.display_name.startswith("[AFK]"):
                    cleaned = message.author.display_name.replace("[AFK]", "").strip()
                    await message.author.edit(nick=cleaned, reason="User returned from AFK")
            except Exception:
                pass

            await message.channel.send(
                content=f"👋 Welcome back {message.author.mention}! I removed your AFK status. (You were away for `{time_str}`)",
                delete_after=10
            )

        # 2. Check if author mentioned someone who is AFK
        if message.mentions:
            for mentioned in message.mentions:
                if mentioned.id != message.author.id:
                    afk_data = await db.get_afk(message.guild.id, mentioned.id)
                    if afk_data:
                        ts = afk_data["afk_time"]
                        reason = afk_data["reason"]
                        await message.reply(
                            f"💤 **{mentioned.display_name}** is currently AFK: *{reason}* (<t:{ts}:R>)",
                            mention_author=False,
                            delete_after=15
                        )

        # 3. Handle Sticky Message reposting
        sticky = await db.get_sticky(message.channel.id)
        if sticky and message.id != sticky.get("last_message_id"):
            last_id = sticky.get("last_message_id")
            if last_id:
                try:
                    old_msg = await message.channel.fetch_message(last_id)
                    await old_msg.delete()
                except Exception:
                    pass

            embed = standard_embed(
                title="📌 Pinned Announcement",
                description=sticky["message_text"],
                color=0xFEE75C
            )
            embed.set_footer(text="Sticky Message • Automatically stays at the bottom")
            try:
                new_msg = await message.channel.send(embed=embed)
                await db.update_sticky_last_id(message.channel.id, new_msg.id)
            except Exception:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
