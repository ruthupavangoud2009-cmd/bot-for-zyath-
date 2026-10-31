import discord
from discord.ext import commands
import random
import asyncio
import json
import os
import time
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

def get_allowed_spam_users():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [str(u) for u in data.get("allowed_spam_users", [])]
        except Exception:
            pass
    return []

def save_allowed_spam_users(users: list):
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["allowed_spam_users"] = users
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

class Fun(commands.Cog):
    """Fun, utilities, $say, and restricted ghost spam commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Active ghost spam tracking per channel_id
        self.active_spams = {}

    @commands.command(name="say", help="Make the bot say something and delete your message. E.g. $say hi")
    async def say(self, ctx: commands.Context, *, message: str = "hi"):
        # Check if user attached any files/images first before deleting
        files = []
        if ctx.message.attachments:
            for attachment in ctx.message.attachments:
                try:
                    files.append(await attachment.to_file())
                except Exception:
                    pass

        # Delete author's trigger message immediately
        try:
            await ctx.message.delete()
        except Exception:
            pass

        msg_text = message.strip() if (message and message.strip()) else "hi"

        if files:
            await ctx.send(content=msg_text, files=files)
        else:
            await ctx.send(msg_text)

    @commands.command(name="hi", help="Say hi to Zyath Bot with a sleek interactive greeting!")
    async def hi_command(self, ctx: commands.Context):
        try:
            await ctx.message.delete()
        except Exception:
            pass

        guild_name = ctx.guild.name if ctx.guild else "Zyath Community"
        embed = standard_embed(
            title=f"👋 Welcome to {guild_name}!",
            description=(
                f"> Hello {ctx.author.mention}! I'm **Zyath**, your all-in-one server concierge.\n"
                f"> Powered by 24/7 AI, automated shop routing, and dual-engine Supabase storage.\n\n"
                f"✨ **Quick Navigation:**\n"
                f"• 🛍️ **Official Shop:** `$shop` — Browse digital catalog & order instantly\n"
                f"• 🎫 **Support Tickets:** `$ticketpanel` — Open a private modular ticket\n"
                f"• 🏆 **Reputation:** `$vouchlb` — View top vouched merchants & traders\n"
                f"• 🤝 **Middleman:** `$mercy` — Log and escrow secure community deals\n"
                f"• 📜 **Command Center:** `$help` — Comprehensive command guide"
            ),
            color=0x2B2D31
        )
        if ctx.guild and ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=f"Zyath Concierge • Serving {ctx.author.display_name}")

        class HiQuickView(discord.ui.View):
            def __init__(self, guild_id: int):
                super().__init__(timeout=180)
                self.guild_id = guild_id

            @discord.ui.button(label="Storefront", style=discord.ButtonStyle.secondary, emoji="🛍️")
            async def shop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
                from cogs.shop import ShopView
                items = await db.get_shop_items(self.guild_id)
                if not items:
                    return await interaction.response.send_message(embed=info_embed("Shop Catalog", "No items currently listed in the shop."), ephemeral=True)
                embed = standard_embed(
                    title=f"🛍️ {interaction.guild.name} • Official Marketplace",
                    description="> Select an item below to open an instant order ticket:\n",
                    color=0x2B2D31
                )
                for item in items[:10]:
                    embed.add_field(name=f"📦 {item['name']} — `{item['price']}`", value=f"└ *{item['description'] or 'In stock'}*", inline=False)
                await interaction.response.send_message(embed=embed, view=ShopView(items, self.guild_id), ephemeral=True)

            @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.secondary, emoji="🎫")
            async def ticket_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
                from cogs.tickets import TicketPanelView
                embed = standard_embed(
                    title="🎫 Zyath Support Desk • Select Category",
                    description="> Choose your inquiry type below to open a private ticket:"
                )
                await interaction.response.send_message(embed=embed, view=TicketPanelView(), ephemeral=True)

            @discord.ui.button(label="Vouch Leaderboard", style=discord.ButtonStyle.secondary, emoji="🏆")
            async def lb_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
                lb = await db.get_vouch_leaderboard(self.guild_id, limit=5)
                if not lb:
                    return await interaction.response.send_message(embed=info_embed("Leaderboard", "No vouches logged yet."), ephemeral=True)
                desc = "> 🏆 **Top Reputable Traders:**\n\n"
                medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
                for idx, entry in enumerate(lb):
                    desc += f"{medals[idx]} <@{entry['target_id']}> — **{entry['count']}** Vouches (⭐ `{entry['avg_stars']}/5.0`)\n"
                embed = standard_embed(title=f"🏆 Top Traders • {interaction.guild.name}", description=desc, color=0xFEE75C)
                await interaction.response.send_message(embed=embed, ephemeral=True)

        await ctx.send(embed=embed, view=HiQuickView(ctx.guild.id if ctx.guild else 0))

    @commands.command(name="sayembed", help="Make the bot speak in a clean embed. E.g. $sayembed Title | Description")
    async def say_embed(self, ctx: commands.Context, *, text: str):
        try:
            await ctx.message.delete()
        except Exception:
            pass

        if "|" in text:
            parts = text.split("|", 1)
            title = parts[0].strip()
            desc = parts[1].strip()
        else:
            title = None
            desc = text.strip()

        embed = standard_embed(title=title, description=desc)
        await ctx.send(embed=embed)

    @commands.command(name="spam", help="Restricted fast ping spam that deletes trigger and all spam messages.")
    async def spam(self, ctx: commands.Context, count: int, member: discord.Member, *, extra_msg: str = ""):
        # Delete user trigger message immediately
        try:
            await ctx.message.delete()
        except Exception:
            pass

        allowed_users = get_allowed_spam_users()
        is_owner = await self.bot.is_owner(ctx.author)
        if str(ctx.author.id) not in allowed_users and not is_owner:
            err = await ctx.send(embed=error_embed("Restricted Command", "⛔ You are not authorized to use the `$spam` command."))
            await err.delete(delay=3)
            return

        if count < 1:
            return
        if count > 100:
            count = 100  # Cap at 100

        text = f"{member.mention} {extra_msg}".strip()

        # Mark spam active for this channel
        self.active_spams[ctx.channel.id] = True

        try:
            for _ in range(count):
                # Check if cancelled
                if not self.active_spams.get(ctx.channel.id, False):
                    break

                try:
                    msg = await ctx.send(text)
                    await msg.delete()
                    await asyncio.sleep(0.3)
                except discord.HTTPException:
                    await asyncio.sleep(1.0)
                except Exception:
                    break
        finally:
            self.active_spams.pop(ctx.channel.id, None)

    @commands.command(name="cancelspam", aliases=["stopspam"], help="Cancel any active ghost spam in this channel.")
    async def cancel_spam(self, ctx: commands.Context, scope: str = ""):
        # Delete trigger message immediately
        try:
            await ctx.message.delete()
        except Exception:
            pass

        allowed_users = get_allowed_spam_users()
        is_owner = await self.bot.is_owner(ctx.author)
        if str(ctx.author.id) not in allowed_users and not is_owner:
            return

        if scope.lower() == "all":
            for cid in list(self.active_spams.keys()):
                self.active_spams[cid] = False
            notice = await ctx.send(embed=info_embed("Ghost Spam Stopped", "🛑 All active ghost spams were cancelled!"))
            await notice.delete(delay=3)
            return

        if self.active_spams.get(ctx.channel.id, False):
            self.active_spams[ctx.channel.id] = False
            notice = await ctx.send(embed=info_embed("Ghost Spam Stopped", "🛑 Active ghost spam was cancelled!"))
            await notice.delete(delay=3)
        else:
            notice = await ctx.send(embed=info_embed("No Active Spam", "No ghost spam is running in this channel."))
            await notice.delete(delay=3)

    @commands.command(name="setspamusers", aliases=["addspamuser"], help="Set or add allowed user IDs for the $spam command.")
    @commands.has_permissions(administrator=True)
    async def set_spam_users(self, ctx: commands.Context, member: discord.Member):
        allowed = get_allowed_spam_users()
        user_id_str = str(member.id)
        if user_id_str not in allowed:
            allowed.append(user_id_str)
            save_allowed_spam_users(allowed)
            await ctx.send(embed=success_embed("Spam Whitelist Updated", f"Added {member.mention} (`{member.id}`) to allowed spam users."))
        else:
            await ctx.send(embed=info_embed("Already Whitelisted", f"{member.mention} is already in the spam allowed list."))

    @commands.command(name="removespamuser", help="Remove a user from the allowed spam users list.")
    @commands.has_permissions(administrator=True)
    async def remove_spam_user(self, ctx: commands.Context, member: discord.Member):
        allowed = get_allowed_spam_users()
        user_id_str = str(member.id)
        if user_id_str in allowed:
            allowed.remove(user_id_str)
            save_allowed_spam_users(allowed)
            await ctx.send(embed=success_embed("Spam Whitelist Updated", f"Removed {member.mention} from allowed spam users."))
        else:
            await ctx.send(embed=error_embed("Not Found", f"{member.mention} was not in the allowed list."))

    @commands.command(name="8ball", help="Ask the magic 8ball a question.")
    async def eight_ball(self, ctx: commands.Context, *, question: str):
        responses = [
            "It is certain.", "It is decidedly so.", "Without a doubt.",
            "Yes definitely.", "You may rely on it.", "As I see it, yes.",
            "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
            "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
            "Cannot predict now.", "Concentrate and ask again.",
            "Don't count on it.", "My reply is no.", "My sources say no.",
            "Outlook not so good.", "Very doubtful."
        ]
        choice = random.choice(responses)
        embed = standard_embed(
            title="🎱 Magic 8-Ball",
            description=f"**Question:** {question}\n**Answer:** {choice}",
            color=0x3498DB
        )
        await ctx.send(embed=embed)

    @commands.command(name="coinflip", aliases=["flip", "cf"], help="Flip a coin.")
    async def coin_flip(self, ctx: commands.Context):
        result = random.choice(["Heads 🪙", "Tails 🪙"])
        await ctx.send(embed=info_embed("Coin Flip", f"The coin landed on **{result}**!"))

    @commands.command(name="roll", help="Roll a dice. E.g. $roll 100")
    async def roll(self, ctx: commands.Context, max_val: int = 6):
        if max_val < 2:
            max_val = 6
        result = random.randint(1, max_val)
        await ctx.send(embed=info_embed("Dice Roll", f"🎲 You rolled a **{result}** (1-{max_val})!"))

    @commands.command(name="roast", help="Roast a member.")
    async def roast(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        roasts = [
            "You bring everyone so much joy... when you leave the room.",
            "I'd agree with you, but then we'd both be wrong.",
            "I'm not saying I hate you, but I would unplug your life support to charge my phone.",
            "You have something on your chin... no, the 3rd one down.",
            "Light travels faster than sound, which is why you seemed bright until you spoke.",
            "If I had a face like yours, I'd sue my parents.",
            "You're like a cloud. When you disappear, it's a beautiful day.",
            "I'd give you a nasty look, but you've already got one."
        ]
        await ctx.send(f"{member.mention} {random.choice(roasts)}")

    @commands.command(name="avatar", aliases=["av", "pfp"], help="Get a member's avatar.")
    async def avatar(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        embed = standard_embed(
            title=f"Avatar for {member.display_name}",
            image=member.display_avatar.url
        )
        await ctx.send(embed=embed)

    @commands.command(name="userinfo", aliases=["whois", "ui", "uinfo"], help="Get detailed user profile dossier.")
    async def user_info(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author

        # Badges calculation
        badges = []
        if ctx.guild and member.id == ctx.guild.owner_id:
            badges.append("👑 Owner")
        if member.guild_permissions.administrator:
            badges.append("🛡️ Admin")
        elif member.guild_permissions.manage_guild or member.guild_permissions.moderate_members:
            badges.append("🔨 Staff")
        if member.premium_since:
            badges.append("💎 Booster")
        if member.bot:
            badges.append("🤖 Bot")
        if not badges:
            badges.append("👤 Member")

        roles = [r.mention for r in reversed(member.roles) if r.name != "@everyone"]
        roles_str = ", ".join(roles[:12]) if roles else "None"
        if len(roles) > 12:
            roles_str += f" *(+{len(roles) - 12} more)*"

        created_ts = int(member.created_at.timestamp())
        joined_ts = int(member.joined_at.timestamp()) if member.joined_at else 0

        embed = standard_embed(
            title=f"👤 User Dossier • {member.display_name}",
            description=(
                f"> **Identity Overview**\n"
                f"> Badges: {' • '.join([f'`{b}`' for b in badges])}\n\n"
                f"🆔 **User ID:** `{member.id}`\n"
                f"🏷️ **Username:** `{member.name}`\n"
                f"📛 **Server Nick:** `{member.nick or 'None'}`\n"
                f"🔝 **Highest Role:** {member.top_role.mention}\n"
                f"📅 **Registered:** <t:{created_ts}:D> (<t:{created_ts}:R>)\n"
                f"📥 **Joined Server:** <t:{joined_ts}:D> (<t:{joined_ts}:R>)\n\n"
                f"🎭 **Assigned Roles ({len(roles)}):**\n{roles_str}"
            ),
            color=member.color if member.color.value != 0 else 0x2B2D31,
            thumbnail=member.display_avatar.url
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name} • Zyath Identity System")
        await ctx.send(embed=embed)

    @commands.command(name="serverinfo", aliases=["si", "sinfo"], help="Get comprehensive server telemetry.")
    async def server_info(self, ctx: commands.Context):
        g = ctx.guild
        created_ts = int(g.created_at.timestamp())

        # Channels stats
        text_count = len(g.text_channels)
        voice_count = len(g.voice_channels)
        category_count = len(g.categories)

        # Verification Level
        v_level = str(g.verification_level).capitalize()

        embed = standard_embed(
            title=f"🌐 Server Telemetry • {g.name}",
            description=(
                f"> **Infrastructure Overview**\n"
                f"> Owner: <@{g.owner_id}> • ID: `{g.id}`\n\n"
                f"👥 **Community Metrics:**\n"
                f"• Total Members: **{g.member_count:,}**\n"
                f"• Boost Level: **Tier {g.premium_tier}** ({g.premium_subscription_count} Boosts)\n"
                f"• Security Level: `{v_level}`\n\n"
                f"📁 **Channels & Roles:**\n"
                f"• Text Channels: `{text_count}` | Voice: `{voice_count}` | Categories: `{category_count}`\n"
                f"• Roles: `{len(g.roles)}` | Custom Emojis: `{len(g.emojis)}`\n\n"
                f"📅 **Established:** <t:{created_ts}:D> (<t:{created_ts}:R>)"
            ),
            color=0x2B2D31,
            thumbnail=g.icon.url if g.icon else None
        )
        embed.set_footer(text=f"Zyath Server Intelligence • System Online")
        await ctx.send(embed=embed)

    @commands.command(name="poll", help="Create a reaction poll. E.g. $poll Should we do a giveaway?")
    async def poll(self, ctx: commands.Context, *, question: str):
        try:
            await ctx.message.delete()
        except Exception:
            pass

        embed = standard_embed(
            title="📊 Community Poll",
            description=f"> **{question}**\n\n*Cast your vote using the reactions below:*",
            color=0x5865F2,
            author=ctx.author
        )
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")

    @commands.command(name="ping", aliases=["latency"], help="View real-time latencies across Gateway, REST API, Database, and Web server.")
    async def ping(self, ctx: commands.Context):
        ws_latency = round(self.bot.latency * 1000)

        t_start = time.perf_counter()
        initial_msg = await ctx.send("⚡ *Initiating comprehensive node diagnostics...*")
        api_latency = round((time.perf_counter() - t_start) * 1000)

        db_latency, db_engine = await db.ping()

        if ws_latency < 80 and api_latency < 150:
            status_text = "🟢 Optimal • Sub-100ms Ultra Performance"
            status_color = 0x57F287
        elif ws_latency < 180 and api_latency < 300:
            status_text = "🟡 Nominal • Stable Network"
            status_color = 0xFEE75C
        else:
            status_text = "🔴 High Latency • Network Congestion"
            status_color = 0xED4245

        embed = standard_embed(
            title="⚡ Zyath Telemetry • Real-Time Diagnostics",
            description=(
                f"> **System Health:** {status_text}\n\n"
                f"🌐 **Network & API Clusters:**\n"
                f"• ⚡ **WebSocket Gateway:** `{ws_latency}ms` (Real-Time Heartbeat)\n"
                f"• 💬 **Discord REST API:** `{api_latency}ms` (HTTP Response Round-Trip)\n"
                f"• 🗄️ **Database Pool:** `{db_latency}ms` (`{db_engine}` Active)\n"
                f"• 🚀 **24/7 Web Server:** `Operational (Port 10000 Active)`\n\n"
                f"⏱️ *Synchronized across cloud workers.*"
            ),
            color=status_color
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name} • Zyath Diagnostic Engine")

        class PingRefreshView(discord.ui.View):
            def __init__(self, bot):
                super().__init__(timeout=60)
                self.bot = bot

            @discord.ui.button(label="Re-Probe Nodes", style=discord.ButtonStyle.primary, emoji="🔄")
            async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
                ws = round(self.bot.latency * 1000)
                t1 = time.perf_counter()
                await interaction.response.defer()
                api = round((time.perf_counter() - t1) * 1000)
                db_lat, engine = await db.ping()

                new_embed = standard_embed(
                    title="⚡ Zyath Telemetry • Real-Time Diagnostics",
                    description=(
                        f"> **System Health:** 🟢 Refreshed & Synced\n\n"
                        f"🌐 **Network & API Clusters:**\n"
                        f"• ⚡ **WebSocket Gateway:** `{ws}ms`\n"
                        f"• 💬 **Discord REST API:** `{api}ms`\n"
                        f"• 🗄️ **Database Pool:** `{db_lat}ms` (`{engine}`)\n"
                        f"• 🚀 **24/7 Web Server:** `Operational (Port 10000 Active)`\n\n"
                        f"⏱️ *Telemetry updated live.*"
                    ),
                    color=0x57F287
                )
                new_embed.set_footer(text=f"Telemetry refreshed by {interaction.user.display_name}")
                await interaction.message.edit(embed=new_embed, view=self)

        await initial_msg.edit(content=None, embed=embed, view=PingRefreshView(self.bot))

async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))
