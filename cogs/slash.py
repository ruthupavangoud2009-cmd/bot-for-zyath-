import discord
from discord import app_commands
from discord.ext import commands
import datetime
import random
import time
import math
import urllib.parse
from typing import Optional
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db
from utils.config_manager import check_is_owner
from cogs.economy import INF_CASH_AMOUNT
from cogs.gw_games import is_inf_cash_str
from cogs.help import HelpView
from cogs.tickets import TicketPanelView, CreateEmbedModal
from cogs.trades import TradeStatusView, MercyModal
from cogs.shop import ShopView

class SlashCommands(commands.Cog):
    """Top application slash commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 1. /help
    @app_commands.command(name="help", description="Open the clean interactive help desk.")
    async def slash_help(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        total_cmds = len(self.bot.commands) + len(self.bot.tree.get_commands())
        bot_name = self.bot.user.name if self.bot.user else "Kyoka Shop"

        embed = standard_embed(
            title=f"Hey, I'm {bot_name}",
            description=(
                "> Built for our community — keeping your server safe, active, and effortlessly connected.\n\n"
                f"• **Latency:** `{latency}ms`\n"
                f"• **Prefix:** `$` | **Slash:** `/`\n"
                f"• **Available Commands:** `{total_cmds}`"
            ),
            color=0x2B2D31
        )
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        view = HelpView(self.bot, interaction.user.display_name, "/")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # 2. /shop
    @app_commands.command(name="shop", description="Browse the official server shop and order items.")
    async def slash_shop(self, interaction: discord.Interaction, category: str = None):
        items = await db.get_shop_items(interaction.guild_id, category)
        if not items:
            return await interaction.response.send_message(embed=info_embed("Shop Catalog", "No items currently listed in the shop."), ephemeral=True)
        embed = standard_embed(
            title=f"🛒 {interaction.guild.name} Official Shop",
            description="Select an item below to automatically open an Order Ticket!",
            color=0x5763719
        )
        for i in items[:15]:
            embed.add_field(name=f"📦 {i['name']} — {i['price']}", value=f"**Category:** `{i['category']}`\n*{i['description'] or 'In stock'}*", inline=False)
        await interaction.response.send_message(embed=embed, view=ShopView(items))

    # 3. /payment
    @app_commands.command(name="payment", description="View accepted payment methods and wallet addresses.")
    async def slash_payment(self, interaction: discord.Interaction):
        methods = await db.get_payment_methods(interaction.guild_id)
        if not methods:
            return await interaction.response.send_message(embed=info_embed("Payment Methods", "No payment methods listed yet."), ephemeral=True)
        embed = standard_embed(title=f"💳 {interaction.guild.name} Payment Gateways", color=0x2ECC71)
        for m in methods:
            note_str = f"\n*{m['note']}*" if m.get("note") else ""
            embed.add_field(name=f"💳 #{m['id']} • {m['method_name']}", value=f"```{m['address']}```{note_str}", inline=False)
        await interaction.response.send_message(embed=embed)

    # 4. /tos
    @app_commands.command(name="tos", description="View shop Terms of Service, warranty, and refund policy.")
    async def slash_tos(self, interaction: discord.Interaction):
        tos_text = await db.get_shop_tos(interaction.guild_id)
        if not tos_text:
            tos_text = "All sales are final once delivered. Replacements provided within 24h with proof."
        embed = standard_embed(title=f"📜 {interaction.guild.name} Terms of Service", description=tos_text, color=0xFEE75C)
        await interaction.response.send_message(embed=embed)

    # 5. /ticket
    @app_commands.command(name="ticket", description="Close current ticket or get HTML transcript.")
    @app_commands.describe(action="Ticket action (close or transcript)")
    @app_commands.choices(action=[
        app_commands.Choice(name="close", value="close"),
        app_commands.Choice(name="transcript", value="transcript")
    ])
    async def slash_ticket(self, interaction: discord.Interaction, action: str):
        if action == "close":
            record = await db.get_ticket_record(interaction.channel_id)
            if not record:
                return await interaction.response.send_message(embed=error_embed("Error", "Not an active ticket channel."), ephemeral=True)
            from cogs.tickets import TicketClosedControlsView
            await db.close_ticket_record(interaction.channel_id)
            await interaction.response.send_message(embed=warning_embed("Ticket Closed", f"Closed by {interaction.user.mention}."), view=TicketClosedControlsView())
        elif action == "transcript":
            from utils.transcript import generate_html_transcript
            await interaction.response.defer()
            file = await generate_html_transcript(interaction.channel)
            await interaction.followup.send(content="📄 **Ticket Transcript:**", file=file)

    # 6. /ticketpanel
    @app_commands.command(name="ticketpanel", description="Deploy the modular ticket creation panel with categories and buttons.")
    @app_commands.default_permissions(administrator=True)
    async def slash_ticketpanel(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        target = channel or interaction.channel
        categories = await db.get_ticket_categories(interaction.guild_id)
        stats = await db.get_ticket_stats(interaction.guild_id)
        bot_name = self.bot.user.name if self.bot.user else "Kyoka Shop"

        cat_bullets = []
        for cat in categories:
            cat_bullets.append(f"• **{cat.get('emoji', '🎫')} {cat['name']}**\n  └ *{cat.get('description', 'Click to open ticket')}*")
        cat_desc = "\n".join(cat_bullets)

        embed = standard_embed(
            title=f"Hey, I'm {bot_name} • Support Desk",
            description=(
                "> Built for our community — keeping orders safe, tickets verified, and support instant.\n\n"
                f"• **Support Status:** `🟢 Active 24/7` | **AI Assistant:** `Online`\n"
                f"• **Available Hubs:** `{len(categories)} Modules` | **Resolved:** `{stats['total']}` Tickets\n"
                f"• **Prefix:** `$` | **Slash:** `/`\n\n"
                f"{cat_desc}\n\n"
                "⚡ *Select a category from the dropdown or click a quick button below to open a ticket.*"
            ),
            color=0x2B2D31
        )
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text=f"Kyoka Modular Desk • {interaction.guild.name}")
        bot_id = self.bot.user.id if self.bot.user else None
        await target.send(embed=embed, view=TicketPanelView(categories, bot_user_id=bot_id))
        await interaction.response.send_message(embed=success_embed("Deployed", f"Modular panel sent to {target.mention}!"), ephemeral=True)

    # 7. /vouch
    @app_commands.command(name="vouch", description="Submit a reputation vouch for a member.")
    @app_commands.describe(member="Member to vouch for", stars="Rating from 1 to 5 stars", comment="Feedback or deal details")
    async def slash_vouch(self, interaction: discord.Interaction, member: discord.Member, stars: int, comment: str):
        if member.id == interaction.user.id or member.bot:
            return await interaction.response.send_message(embed=error_embed("Error", "You cannot vouch for yourself or a bot."), ephemeral=True)
        stars = max(1, min(5, stars))
        vouch_id = await db.add_vouch(interaction.guild_id, member.id, interaction.user.id, stars, comment)
        total, avg = await db.get_vouch_stats(interaction.guild_id, member.id)

        embed = standard_embed(
            title="⭐ New Vouch Received!",
            description=(
                f"**User:** {member.mention}\n**By:** {interaction.user.mention}\n"
                f"**Rating:** {'⭐' * stars} (`{stars}/5`)\n**Comment:**\n>>> {comment}\n\n"
                f"📊 **User Stats:** `{total}` Total Vouches • ⭐ `{avg}/5.0` Avg"
            ),
            color=0xFEE75C,
            thumbnail=member.display_avatar.url
        )
        settings = await db.get_guild_settings(interaction.guild_id)
        chan_id = settings.get("vouch_channel_id")
        if chan_id:
            chan = interaction.guild.get_channel(chan_id)
            if chan:
                await chan.send(embed=embed)
        await interaction.response.send_message(embed=embed)

    # 8. /vouches
    @app_commands.command(name="vouches", description="View vouches and reputation rating for a member.")
    async def slash_vouches(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        vouches = await db.get_vouches(interaction.guild_id, target.id)
        total, avg = await db.get_vouch_stats(interaction.guild_id, target.id)
        if not vouches:
            return await interaction.response.send_message(embed=info_embed("Vouches", f"{target.mention} has no vouches yet."))

        desc = f"📊 **Total Vouches:** `{total}` • ⭐ **Average Rating:** `{avg}/5.0`\n\n"
        for v in vouches[:5]:
            desc += f"• {'⭐' * v['stars']} by <@{v['author_id']}>: *{v['comment']}*\n"
        embed = standard_embed(title=f"⭐ Reputation Profile • {target.display_name}", description=desc, thumbnail=target.display_avatar.url, color=0xFEE75C)
        await interaction.response.send_message(embed=embed)

    # 9. /mercy
    @app_commands.command(name="mercy", description="Log an official Middleman (MM) transaction receipt.")
    async def slash_mercy(self, interaction: discord.Interaction, buyer: discord.Member, seller: discord.Member, amount: str, details: str):
        settings = await db.get_guild_settings(interaction.guild_id)
        dest_id = settings.get("trade_channel_id") or settings.get("vouch_channel_id") or interaction.channel_id
        dest_chan = interaction.guild.get_channel(dest_id) or interaction.channel

        import random
        trade_id = f"TRD-{random.randint(1000, 9999)}"
        embed = standard_embed(
            title=f"🤝 Live Trade Receipt • #{trade_id}",
            description="Official Middleman transaction active.",
            color=0xFEE75C
        )
        embed.add_field(name="🛡️ Middleman", value=interaction.user.mention, inline=True)
        embed.add_field(name="👤 Buyer", value=buyer.mention, inline=True)
        embed.add_field(name="📦 Seller", value=seller.mention, inline=True)
        embed.add_field(name="💰 Amount", value=f"`{amount}`", inline=True)
        embed.add_field(name="📊 Status", value="🟡 **In Progress**", inline=True)
        embed.add_field(name="📝 Details", value=f"```{details}```", inline=False)

        view = TradeStatusView(trade_id=trade_id, mm_id=interaction.user.id)
        msg = await dest_chan.send(content=f"{buyer.mention} {seller.mention}", embed=embed, view=view)
        await db.create_trade(trade_id, interaction.guild_id, interaction.user.id, buyer.id, seller.id, amount, details, dest_chan.id, msg.id)
        await interaction.response.send_message(embed=success_embed("MM Trade Posted", f"Trade **#{trade_id}** posted in {dest_chan.mention}!"), ephemeral=True)

    # 10. /trade
    @app_commands.command(name="trade", description="Look up status and details of a trade ID.")
    async def slash_trade(self, interaction: discord.Interaction, trade_id: str):
        trade = await db.get_trade(trade_id.upper())
        if not trade:
            return await interaction.response.send_message(embed=error_embed("Not Found", f"No trade found with ID `{trade_id}`."), ephemeral=True)
        embed = standard_embed(title=f"Trade Details • #{trade['id']}", description=f"**Status:** `{trade['status']}`")
        embed.add_field(name="Middleman", value=f"<@{trade['mm_id']}>", inline=True)
        embed.add_field(name="Buyer", value=f"<@{trade['buyer_id']}>", inline=True)
        embed.add_field(name="Seller", value=f"<@{trade['seller_id']}>", inline=True)
        embed.add_field(name="Amount", value=f"`{trade['amount']}`", inline=True)
        embed.add_field(name="Details", value=f"```{trade['details']}```", inline=False)
        await interaction.response.send_message(embed=embed)

    # 11. /createembed
    @app_commands.command(name="createembed", description="Open interactive modal to design and post a custom embed.")
    @app_commands.default_permissions(manage_messages=True)
    async def slash_createembed(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        target = channel or interaction.channel
        await interaction.response.send_modal(CreateEmbedModal(target))

    # 12. /gtn
    @app_commands.command(name="gtn", description="Start a Guess The Number game in this channel.")
    @app_commands.describe(min_val="Minimum number", max_val="Maximum number", prize="Prize for the winner")
    @app_commands.default_permissions(manage_channels=True)
    async def slash_gtn(self, interaction: discord.Interaction, min_val: int = 1, max_val: int = 1000, prize: str = "Discord Nitro"):
        if is_inf_cash_str(prize) and not await check_is_owner(self.bot, interaction.user):
            return await interaction.response.send_message(
                embed=error_embed("Restricted Prize", "⛔ **Access Denied:** Only bot owners can add **infinite cash** in minigames!"),
                ephemeral=True
            )

        cog = self.bot.get_cog("GWGames") or self.bot.get_cog("GuessTheNumber")
        if not cog:
            return await interaction.response.send_message("GTN game cog not loaded.", ephemeral=True)
        import random
        if min_val >= max_val or max_val - min_val < 5:
            return await interaction.response.send_message(embed=error_embed("Invalid Range", "Min must be less than max (range at least 5)."), ephemeral=True)
        
        target = random.randint(min_val, max_val)
        game_data = {
            "target": target,
            "min": min_val,
            "max": max_val,
            "guesses": 0,
            "starter": interaction.user.id,
            "prize": prize,
            "highest_low": min_val,
            "lowest_high": max_val
        }
        if hasattr(cog, "active_gtn"):
            cog.active_gtn[interaction.channel_id] = game_data
        else:
            cog.active_games[interaction.channel_id] = game_data

        try:
            await interaction.user.send(f"🎯 **Secret GTN Target:** `{target}` in {interaction.channel.mention} for **{prize}**!")
        except Exception:
            pass

        embed = standard_embed(
            title="🎮 Guess The Number Started!",
            description=(
                f"A new game of **Guess The Number** has begun!\n\n"
                f"🎁 **Prize:** **{prize}**\n"
                f"🔢 **Range:** Between `{min_val}` and `{max_val}`\n\n"
                f"➕ = Higher, ➖ = Lower\n"
                f"Channel will be locked on win!"
            ),
            color=0x57F287
        )
        embed.set_footer(text=f"Host: {interaction.user.display_name} • Good luck!")
        await interaction.response.send_message(embed=embed)

    # 13. /ping
    @app_commands.command(name="ping", description="View real-time latencies across Gateway, Database, and Web server.")
    async def slash_ping(self, interaction: discord.Interaction):
        ws_latency = round(self.bot.latency * 1000)
        await interaction.response.defer()
        db_latency, db_engine = await db.ping()

        embed = standard_embed(
            title="🏓 Pong! • Network Diagnostics",
            description=(
                f"• ⚡ **WebSocket Gateway:** `{ws_latency}ms`\n"
                f"• 🗄️ **Database ({db_engine}):** `{db_latency}ms`\n"
                f"• 🌐 **Render 24/7 Web Server:** `Operational (Port Active)`\n\n"
                f"⏱️ *Supabase PostgreSQL connected & synchronized.*"
            ),
            color=0x57F287
        )
        await interaction.followup.send(embed=embed)

    # 14. /avatar
    @app_commands.command(name="avatar", description="View full-resolution avatar of a user.")
    async def slash_avatar(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        embed = standard_embed(title=f"Avatar for {target.display_name}", image=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # 15. /userinfo
    @app_commands.command(name="userinfo", description="View profile details of a member.")
    async def slash_userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        embed = standard_embed(title=f"User Info • {target}", thumbnail=target.display_avatar.url)
        embed.add_field(name="ID", value=str(target.id), inline=True)
        embed.add_field(name="Created", value=discord.utils.format_dt(target.created_at, style="d"), inline=True)
        embed.add_field(name="Joined", value=discord.utils.format_dt(target.joined_at, style="d") if target.joined_at else "N/A", inline=True)
        await interaction.response.send_message(embed=embed)

    # 16. /serverinfo
    @app_commands.command(name="serverinfo", description="View server stats, member count, and details.")
    async def slash_serverinfo(self, interaction: discord.Interaction):
        g = interaction.guild
        embed = standard_embed(title=f"Server Info • {g.name}", thumbnail=g.icon.url if g.icon else None)
        embed.add_field(name="Owner", value=f"<@{g.owner_id}>", inline=True)
        embed.add_field(name="Members", value=f"{g.member_count:,}", inline=True)
        embed.add_field(name="Channels", value=f"{len(g.channels)}", inline=True)
        embed.add_field(name="Roles", value=f"{len(g.roles)}", inline=True)
        await interaction.response.send_message(embed=embed)

    # 17. /purge
    @app_commands.command(name="purge", description="Bulk delete messages from the channel.")
    @app_commands.default_permissions(manage_messages=True)
    async def slash_purge(self, interaction: discord.Interaction, amount: int):
        amount = max(1, min(100, amount))
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(embed=success_embed("Purged", f"Deleted **{len(deleted)}** messages."), ephemeral=True)

    # 18. /mute
    @app_commands.command(name="mute", description="Timeout/mute a member.")
    @app_commands.default_permissions(moderate_members=True)
    async def slash_mute(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided"):
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message(embed=error_embed("Permission Denied", "Cannot mute higher or equal role."), ephemeral=True)
        until = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)
        await member.timeout(until, reason=f"{interaction.user}: {reason}")
        await interaction.response.send_message(embed=success_embed("Timed Out", f"🔇 {member.mention} muted for **{minutes}m**."))

    # 19. /vouchlb
    @app_commands.command(name="vouchlb", description="View the top vouched members leaderboard in this server.")
    async def slash_vouchlb(self, interaction: discord.Interaction):
        lb = await db.get_vouch_leaderboard(interaction.guild_id, limit=10)
        if not lb:
            return await interaction.response.send_message(embed=info_embed("Vouch Leaderboard", "No vouches logged in this server yet!"), ephemeral=True)

        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        desc = "🏆 **Top Reputable Members:**\n\n"
        for idx, entry in enumerate(lb):
            icon = medals[idx] if idx < len(medals) else f"**#{idx+1}**"
            desc += f"{icon} <@{entry['target_id']}> — **{entry['count']}** Vouches (⭐ `{entry['avg_stars']}/5.0`)\n"

        embed = standard_embed(title=f"🏆 Vouch Leaderboard • {interaction.guild.name}", description=desc, color=0xFEE75C)
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        await interaction.response.send_message(embed=embed)

    # 20. /ban
    @app_commands.command(name="ban", description="Ban a member from the server.")
    @app_commands.default_permissions(ban_members=True)
    async def slash_ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message(embed=error_embed("Permission Denied", "Cannot ban higher or equal role."), ephemeral=True)
        await member.ban(reason=f"{interaction.user}: {reason}")
        await interaction.response.send_message(embed=success_embed("Banned", f"🔨 {member.mention} has been banned."))

    # 21. /support
    @app_commands.command(name="support", description="Get the official bot support server link.")
    async def slash_support(self, interaction: discord.Interaction):
        from utils.config_manager import get_support_server
        support_url = get_support_server()
        bot_name = self.bot.user.name if self.bot.user else "Kyoka Shop"

        embed = standard_embed(
            title=f"💬 {bot_name} Official Support Server",
            description=(
                f"Need assistance, want to report a bug, or request a feature?\n\n"
                f"Join our official support server for 24/7 staff help, announcements, updates, and community events!\n\n"
                f"🔗 **Direct Invite:** {support_url}"
            ),
            color=0x5865F2
        )
        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Join Support Server", style=discord.ButtonStyle.link, url=support_url, emoji="💬"))
        if self.bot.user:
            invite_url = f"https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot%20applications.commands"
            view.add_item(discord.ui.Button(label="Invite Bot", style=discord.ButtonStyle.link, url=invite_url, emoji="🚀"))

        await interaction.response.send_message(embed=embed, view=view)

    # 22. /botname (Owner only)
    @app_commands.command(name="botname", description="Change the bot username (Bot Owner only).")
    @app_commands.describe(new_name="New username for the bot (2-32 chars)")
    async def slash_botname(self, interaction: discord.Interaction, new_name: str):
        from utils.config_manager import check_is_owner, set_config_value
        if not await check_is_owner(self.bot, interaction.user):
            return await interaction.response.send_message(
                embed=error_embed("Access Denied", "⛔ This command is restricted to the bot owner only."),
                ephemeral=True
            )
        clean_name = new_name.strip()
        if len(clean_name) < 2 or len(clean_name) > 32:
            return await interaction.response.send_message(
                embed=error_embed("Invalid Name", "Bot username must be between 2 and 32 characters."),
                ephemeral=True
            )
        try:
            await self.bot.user.edit(username=clean_name)
            set_config_value("bot_name", clean_name)
            await interaction.response.send_message(
                embed=success_embed("Bot Name Updated", f"✅ Bot username successfully changed to **{clean_name}**!")
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                embed=error_embed("Discord API Error", f"Failed updating name: {e.text} *(Discord limits username changes to twice per hour)*"),
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed("Error", str(e)),
                ephemeral=True
            )

    # 23. /setsupport
    @app_commands.command(name="setsupport", description="Change the official bot support server link dynamically.")
    @app_commands.describe(url="New Discord invite link (e.g. https://discord.gg/kyoka)")
    async def slash_setsupport(self, interaction: discord.Interaction, url: str):
        from utils.config_manager import check_is_owner, set_support_server
        if not await check_is_owner(self.bot, interaction.user):
            return await interaction.response.send_message(
                embed=error_embed("Access Denied", "⛔ This command is restricted to the bot owner only."),
                ephemeral=True
            )
        clean_url = url.strip("<>").strip()
        if not (clean_url.startswith("http://") or clean_url.startswith("https://") or "discord.gg/" in clean_url):
            return await interaction.response.send_message(embed=error_embed("Invalid Link", "Please provide a valid Discord invite link."), ephemeral=True)
        if not clean_url.startswith(("http://", "https://")):
            clean_url = f"https://{clean_url}"

        set_support_server(clean_url)
        embed = success_embed(
            "Support Link Updated",
            f"✅ Official support server invite changed to:\n🔗 **{clean_url}**\n\nAll `$help`, `/help`, and `$support` commands have been updated!"
        )
        await interaction.response.send_message(embed=embed)

    # 23. /scramble
    @app_commands.command(name="scramble", description="Start a Word Scramble giveaway game in this channel.")
    @app_commands.describe(prize="Prize for the winner")
    @app_commands.default_permissions(manage_channels=True)
    async def slash_scramble(self, interaction: discord.Interaction, prize: str = "Discord Nitro"):
        cog = self.bot.get_cog("GWGames")
        if not cog:
            return await interaction.response.send_message("GW Games cog not loaded.", ephemeral=True)
        import random
        from cogs.gw_games import SCRAMBLE_WORDS
        word = random.choice(SCRAMBLE_WORDS)
        letters = list(word)
        for _ in range(10):
            random.shuffle(letters)
            scrambled = " ".join(letters)
            if scrambled.replace(" ", "") != word:
                break
        cog.active_scramble[interaction.channel_id] = {
            "word": word,
            "scrambled": scrambled,
            "prize": prize,
            "starter": interaction.user.id,
            "start_time": datetime.datetime.utcnow().timestamp(),
            "hint_given": False
        }
        embed = standard_embed(
            title="🧩 Word Scramble GW!",
            description=(
                f"Unscramble the letters below to win the prize!\n\n"
                f"🔀 **Scrambled Word:**\n# `{scrambled}`\n\n"
                f"🎁 **Prize:** **{prize}**\n"
                f"👑 **Hosted by:** {interaction.user.mention}\n\n"
                f"⚡ First person to type the correct word in chat wins!"
            ),
            color=0xFEE75C
        )
        embed.set_footer(text=f"Total letters: {len(word)} • Type your answer directly!")
        await interaction.response.send_message(embed=embed)

    # 24. /drop
    @app_commands.command(name="drop", description="Drop a fast-reaction button in this channel.")
    @app_commands.describe(delay="Countdown seconds before button appears", prize="Prize for the fastest clicker")
    @app_commands.default_permissions(manage_channels=True)
    async def slash_drop(self, interaction: discord.Interaction, delay: int = 3, prize: str = "Discord Nitro"):
        cog = self.bot.get_cog("GWGames")
        if not cog:
            return await interaction.response.send_message("GW Games cog not loaded.", ephemeral=True)
        delay = max(1, min(30, delay))
        await interaction.response.send_message(f"⏳ **Reaction Drop starting in {delay} seconds...** Get ready!")
        # Trigger drop
        import asyncio, time
        await asyncio.sleep(delay)
        start_time = time.time()
        winner_claimed = False

        class SlashDropView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)

            @discord.ui.button(label="🎁 CLAIM PRIZE NOW!", style=discord.ButtonStyle.success, emoji="⚡")
            async def claim(self, inter: discord.Interaction, button: discord.ui.Button):
                nonlocal winner_claimed
                if winner_claimed:
                    return await inter.response.send_message("❌ Someone clicked a split-second ahead of you!", ephemeral=True)
                winner_claimed = True
                elapsed = round(time.time() - start_time, 3)
                button.disabled = True
                button.label = f"Claimed by {inter.user.name} ({elapsed}s)!"
                await inter.response.edit_message(view=self)
                await cog._lock_channel(inter.channel, f"Drop won by {inter.user}")

                win_embed = standard_embed(
                    title="⚡ REACTION DROP CLAIMED! ⚡",
                    description=(
                        f"🎉 Congratulations {inter.user.mention}!\n\n"
                        f"🎁 **Prize Won:** **{prize}**\n"
                        f"⚡ **Reaction Speed:** `{elapsed}s`\n"
                        f"🔒 **Channel Status:** Automatically locked!"
                    ),
                    color=0x57F287,
                    thumbnail=inter.user.display_avatar.url
                )
                await inter.channel.send(content=f"👑 {inter.user.mention}", embed=win_embed)

        embed = standard_embed(
            title="🔥 DROP IS LIVE — CLICK FIRST TO WIN! 🔥",
            description=f"🎁 **Prize:** **{prize}**\n\n👇 **FIRST TO CLICK WINS!**",
            color=0xED4245
        )
        await interaction.channel.send(embed=embed, view=SlashDropView())

    # 25. /balance
    @app_commands.command(name="balance", description="Check your or another member's bank and wallet balance.")
    async def slash_balance(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        target = member or interaction.user
        eco = await db.get_economy(interaction.guild_id, target.id)
        wallet = eco["wallet"]
        bank = eco["bank"]
        net_worth = wallet + bank

        embed = standard_embed(
            title=f"💰 {target.display_name}'s Financial Portfolio",
            description=(
                f"• **Wallet:** `{wallet:,}` coins 🪙\n"
                f"• **Bank Vault:** `{bank:,}` coins 🏦\n"
                f"• **Net Worth:** `{net_worth:,}` coins ✨\n"
                f"• **Daily Streak:** `{eco.get('streak', 0)}` days 🔥"
            ),
            color=0xF1C40F,
            thumbnail=target.display_avatar.url
        )
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    # 26. /daily
    @app_commands.command(name="daily", description="Claim your daily streak reward bonus.")
    async def slash_daily(self, interaction: discord.Interaction):
        eco = await db.get_economy(interaction.guild_id, interaction.user.id)
        now = time.time()
        last_daily = eco["last_daily"]
        cooldown = 86400

        if (now - last_daily) < cooldown:
            remaining = int(cooldown - (now - last_daily))
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            return await interaction.response.send_message(
                embed=error_embed("Cooldown Active", f"⏳ You have already claimed your daily reward!\nCome back in **{hours}h {minutes}m**."),
                ephemeral=True
            )

        streak = eco["streak"] + 1 if (now - last_daily) < (cooldown * 2) else 1
        reward = 1000 + (streak * 100) + random.randint(50, 250)

        await db.update_economy(
            interaction.guild_id,
            interaction.user.id,
            wallet_delta=reward,
            last_daily=now,
            streak=streak
        )

        embed = success_embed(
            "🎁 Daily Reward Claimed!",
            f"You received **+{reward:,}** coins!\n\n"
            f"🔥 **Current Streak:** `{streak}` days in a row!\n"
            f"🪙 **New Wallet Balance:** `{eco['wallet'] + reward:,}` coins"
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # 27. /slots
    @app_commands.command(name="slots", description="Bet coins on the 3-reel casino slot machine.")
    @app_commands.describe(bet="Amount of coins to gamble")
    async def slash_slots(self, interaction: discord.Interaction, bet: int):
        if bet < 10:
            return await interaction.response.send_message(embed=error_embed("Invalid Bet", "Minimum bet is 10 coins."), ephemeral=True)

        eco = await db.get_economy(interaction.guild_id, interaction.user.id)
        has_inf = eco["wallet"] >= INF_CASH_AMOUNT
        if eco["wallet"] < bet and not has_inf:
            return await interaction.response.send_message(
                embed=error_embed("Insufficient Funds", f"You only have **{eco['wallet']:,}** coins in your wallet!"),
                ephemeral=True
            )

        slot_emojis = ["🍒", "🍋", "🍇", "💎", "7️⃣", "🔔"]
        reels = [random.choice(slot_emojis) for _ in range(3)]

        if reels[0] == reels[1] == reels[2]:
            multiplier = 10 if reels[0] == "7️⃣" else (7 if reels[0] == "💎" else 4)
            winnings = bet * multiplier
            new_wallet = INF_CASH_AMOUNT if has_inf else eco["wallet"] + winnings
            await db.update_economy(interaction.guild_id, interaction.user.id, wallet=new_wallet)
            bal_str = "♾️ Infinite" if new_wallet >= INF_CASH_AMOUNT else f"`{new_wallet:,}` coins"
            embed = standard_embed(
                title="🎰 CASINO SLOTS — JACKPOT! 🎰",
                description=(
                    f"**[ {reels[0]} | {reels[1]} | {reels[2]} ]**\n\n"
                    f"🎉 **TRIPLE MATCH!** You won **+{winnings:,} coins** ({multiplier}x payout)!\n"
                    f"🪙 **New Wallet:** {bal_str}"
                ),
                color=0x57F287,
                thumbnail=interaction.user.display_avatar.url
            )
        elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
            winnings = int(bet * 1.5)
            new_wallet = INF_CASH_AMOUNT if has_inf else eco["wallet"] + (winnings - bet)
            await db.update_economy(interaction.guild_id, interaction.user.id, wallet=new_wallet)
            bal_str = "♾️ Infinite" if new_wallet >= INF_CASH_AMOUNT else f"`{new_wallet:,}` coins"
            embed = standard_embed(
                title="🎰 CASINO SLOTS — NICE WIN! 🎰",
                description=(
                    f"**[ {reels[0]} | {reels[1]} | {reels[2]} ]**\n\n"
                    f"✨ **DOUBLE MATCH!** You won **+{winnings:,} coins** (1.5x)!\n"
                    f"🪙 **New Wallet:** {bal_str}"
                ),
                color=0xFEE75C,
                thumbnail=interaction.user.display_avatar.url
            )
        else:
            new_wallet = INF_CASH_AMOUNT if has_inf else max(0, eco["wallet"] - bet)
            await db.update_economy(interaction.guild_id, interaction.user.id, wallet=new_wallet)
            bal_str = "♾️ Infinite" if new_wallet >= INF_CASH_AMOUNT else f"`{new_wallet:,}` coins"
            embed = standard_embed(
                title="🎰 CASINO SLOTS — NO MATCH 🎰",
                description=(
                    f"**[ {reels[0]} | {reels[1]} | {reels[2]} ]**\n\n"
                    f"❌ Better luck next spin! You lost **-{bet:,} coins**.\n"
                    f"🪙 **New Wallet:** {bal_str}"
                ),
                color=0xED4245,
                thumbnail=interaction.user.display_avatar.url
            )
        await interaction.response.send_message(embed=embed)


    # 28. /afk
    @app_commands.command(name="afk", description="Set your AFK status with an optional reason.")
    @app_commands.describe(reason="Reason for stepping away")
    async def slash_afk(self, interaction: discord.Interaction, reason: Optional[str] = "AFK"):
        clean_reason = (reason or "AFK").strip()[:150]
        await db.set_afk(interaction.guild_id, interaction.user.id, clean_reason)
        try:
            if not interaction.user.display_name.startswith("[AFK]"):
                new_nick = f"[AFK] {interaction.user.display_name}"[:32]
                await interaction.user.edit(nick=new_nick, reason="Slash AFK")
        except Exception:
            pass
        embed = standard_embed(
            title="💤 AFK Status Set",
            description=f"{interaction.user.mention} is now AFK: **{clean_reason}**\n*I will notify anyone who mentions you!*",
            color=0x34495E
        )
        await interaction.response.send_message(embed=embed)

    # 29. /snipe
    @app_commands.command(name="snipe", description="View the most recently deleted message in this channel.")
    async def slash_snipe(self, interaction: discord.Interaction):
        util_cog = self.bot.get_cog("Utility")
        if not util_cog or interaction.channel_id not in util_cog.snipes:
            return await interaction.response.send_message(embed=error_embed("Snipe Empty", "There is nothing to snipe in this channel!"), ephemeral=True)
        data = util_cog.snipes[interaction.channel_id]
        author = data["author"]
        content = data["content"]
        time_str = f"<t:{int(data['time'])}:R>"
        embed = standard_embed(
            title="🎯 Sniped Message",
            description=content or "*[No text content / Only media]*",
            color=0xED4245
        )
        embed.set_author(name=f"{author.display_name} ({author.id})", icon_url=author.display_avatar.url)
        embed.add_field(name="Deleted", value=time_str, inline=True)
        if data.get("attachments"):
            embed.add_field(name="Attachments", value="\n".join(f"[{a['filename']}]({a['url']})" for a in data["attachments"]), inline=False)
        await interaction.response.send_message(embed=embed)

    # 30. /qrcode
    @app_commands.command(name="qrcode", description="Generate a scannable QR Code image.")
    @app_commands.describe(text="The URL or text content to encode")
    async def slash_qrcode(self, interaction: discord.Interaction, text: str):
        encoded = urllib.parse.quote_plus(text)
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded}"
        embed = standard_embed(
            title="📱 QR Code Generator",
            description=f"**Target Content:**\n```{text[:200]}```",
            color=0x3498DB
        )
        embed.set_image(url=qr_url)
        embed.set_footer(text=f"Requested by {interaction.user.display_name} • Scan with any smartphone camera")
        await interaction.response.send_message(embed=embed)

    # 31. /calc
    @app_commands.command(name="calc", description="Safely evaluate an arithmetic math expression.")
    @app_commands.describe(expression="Arithmetic math expression (e.g. (100 * 5) + 25)")
    async def slash_calc(self, interaction: discord.Interaction, expression: str):
        sanitized = expression.replace("^", "**").replace("x", "*").replace("X", "*")
        if not all(c in "0123456789+-*/().% " for c in sanitized):
            return await interaction.response.send_message(embed=error_embed("Invalid Characters", "Only numbers and math operators (`+`, `-`, `*`, `/`, `(`, `)`) are permitted."), ephemeral=True)
        try:
            result = eval(sanitized, {"__builtins__": None}, {})
            embed = standard_embed(
                title="🧮 Math Calculator",
                description=f"**Expression:** `{expression}`\n**Result:** `{result}`",
                color=0x2ECC71
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(embed=error_embed("Calculation Error", f"Could not solve expression: `{e}`"), ephemeral=True)

    # 32. /automod
    @app_commands.command(name="automod", description="View server AutoMod shield protection status.")
    @app_commands.default_permissions(administrator=True)
    async def slash_automod(self, interaction: discord.Interaction):
        settings = await db.get_automod_settings(interaction.guild_id)
        def badge(val: bool):
            return "🟢 **Active**" if val else "⚪ **Disabled**"

        embed = standard_embed(
            title=f"🛡️ Automod Security Center • {interaction.guild.name}",
            description=(
                f"Automated server protection safeguards your community 24/7.\n\n"
                f"• **Anti-Invite Links:** {badge(settings['anti_invite'])}\n"
                f"• **Anti-Spam Flooding:** {badge(settings['anti_spam'])}\n"
                f"• **Anti-Mass Mentions (>5):** {badge(settings['anti_mention'])}\n"
                f"• **Anti-Caps Flood (>70%):** {badge(settings['anti_caps'])}\n\n"
                f"To toggle shields, use `$automod <invite|spam|mentions|caps> <on|off>`"
            ),
            color=0x5865F2
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # 33. /rank
    @app_commands.command(name="rank", description="Check your or another member's level, XP, and rank card.")
    async def slash_rank(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        target = member or interaction.user
        data = await db.get_level_data(interaction.guild_id, target.id)
        lvl = data["level"]
        xp = data["xp"]
        needed_xp = 5 * (lvl ** 2) + 50 * lvl + 100
        rank = await db.get_user_rank(interaction.guild_id, target.id)

        # Progress bar
        ratio = min(1.0, max(0.0, xp / needed_xp)) if needed_xp > 0 else 0
        filled = int(ratio * 10)
        empty = 10 - filled
        bar = f"[{'█' * filled}{'░' * empty}] `{int(ratio * 100)}%`"

        embed = standard_embed(
            title=f"📊 {target.display_name}'s Level Dossier",
            description=(
                f"• **Server Rank:** `#{rank}` 🏆\n"
                f"• **Current Level:** `Level {lvl}` ⭐\n"
                f"• **Experience:** `{xp:,} / {needed_xp:,} XP`\n"
                f"• **Progress:** {bar}"
            ),
            color=0x5865F2,
            thumbnail=target.display_avatar.url
        )
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    # 34. /levels
    @app_commands.command(name="levels", description="View the top active chatters in this server.")
    async def slash_levels(self, interaction: discord.Interaction):
        top_users = await db.get_leaderboard(interaction.guild_id, limit=10)
        if not top_users:
            return await interaction.response.send_message(embed=info_embed("Server Leaderboard", "No member XP records found yet."), ephemeral=True)

        lines = []
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        for idx, u in enumerate(top_users):
            user_id = u["user_id"]
            lvl = u["level"]
            xp = u["xp"]
            medal = medals[idx] if idx < len(medals) else f"`#{idx+1}`"
            lines.append(f"{medal} <@{user_id}> — **Level {lvl}** (`{xp:,} XP`)")

        embed = standard_embed(
            title=f"🏆 {interaction.guild.name} • Active Chat Leaderboard",
            description="\n".join(lines),
            color=0xFEE75C
        )
        await interaction.response.send_message(embed=embed)

    # 35. /premium
    @app_commands.command(name="premium", description="View current server and personal premium status and active perks.")
    async def slash_premium(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        user_id = interaction.user.id

        is_guild_prem = db.is_guild_premium(guild_id)
        is_user_prem = db.is_user_premium(user_id)

        guild_prem_data = await db.get_premium(guild_id) if is_guild_prem else None
        user_prem_data = await db.get_premium(user_id) if is_user_prem else None

        def format_badge(data):
            if not data:
                return "⚪ **Inactive**"
            exp = data.get("expires_at")
            if not exp:
                return "🌟 **Active** (Lifetime / Permanent)"
            if isinstance(exp, str):
                return f"🌟 **Active** (`{exp[:10]}`)"
            ts = int(exp.timestamp())
            return f"🌟 **Active** (Expires <t:{ts}:R>)"

        embed = standard_embed(
            title="💎 Kyoka Elite Premium Status",
            description=(
                f"• **This Server:** {format_badge(guild_prem_data)}\n"
                f"• **Your Account:** {format_badge(user_prem_data)}\n\n"
                "**👑 Active Premium Perks:**\n"
                "✨ **2x Daily Coins:** Double rewards on `$daily` streak.\n"
                "🎰 **High-Roller Limits:** Bet up to 250,000 coins on `$slots` and `$gamble`.\n"
                "🎫 **Unlimited Ticket Categories:** No restrictions on modular ticket setups.\n"
                "🚀 **Multi-Winner Boosts:** Run giveaways with up to 20 winners simultaneously.\n"
                "🛡️ **VIP AutoMod Sensitivity:** Ultra-fast sub-second spam and raid suppression."
            ),
            color=0xF1C40F
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # 36. /infcash (Owner Only)
    @app_commands.command(name="infcash", description="[Bot Owner Only] Grant infinite minigame cash to a user.")
    @app_commands.describe(user="User to grant infinite cash to (defaults to yourself)")
    async def slash_infcash(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        if not await check_is_owner(self.bot, interaction.user):
            return await interaction.response.send_message(
                embed=error_embed(
                    "Access Denied",
                    "⛔ **Restricted Feature:** Only bot owners can add **infinite cash** in minigames!"
                ),
                ephemeral=True
            )

        target = user or interaction.user
        await db.update_economy(
            interaction.guild_id,
            target.id,
            wallet=INF_CASH_AMOUNT,
            bank=INF_CASH_AMOUNT,
            bank_max=INF_CASH_AMOUNT
        )

        embed = standard_embed(
            title="♾️ Infinite Cash Activated!",
            description=(
                f"🌟 Successfully granted **Infinite Minigame Funds** to {target.mention}!\n\n"
                f"🪙 **Wallet:** `♾️ Infinite` (`{INF_CASH_AMOUNT:,}` coins)\n"
                f"🏦 **Bank Vault:** `♾️ Infinite` (`{INF_CASH_AMOUNT:,}` coins)\n\n"
                f"🎮 **Minigames & Casino Status:** Unlimited betting enabled for Slots, Gamble, BlackTea, Roulette, and GW games!"
            ),
            color=0x57F287
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text=f"Authorized by Bot Owner: {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    # 37. /addcash (Owner Only)
    @app_commands.command(name="addcash", description="[Bot Owner Only] Add cash or infinite cash to a user.")
    @app_commands.describe(user="User to receive cash", amount="Numeric coins or 'inf' for infinite cash")
    async def slash_addcash(self, interaction: discord.Interaction, user: discord.Member, amount: str):
        if not await check_is_owner(self.bot, interaction.user):
            return await interaction.response.send_message(
                embed=error_embed(
                    "Access Denied",
                    "⛔ **Restricted Feature:** Only bot owners can add cash in minigames and economy!"
                ),
                ephemeral=True
            )

        clean_amt = amount.lower().strip()
        eco = await db.get_economy(interaction.guild_id, user.id)

        if clean_amt in ["inf", "infinite", "infinity", "max"]:
            new_wallet = INF_CASH_AMOUNT
            new_bank_max = INF_CASH_AMOUNT
            await db.update_economy(interaction.guild_id, user.id, wallet=new_wallet, bank_max=new_bank_max)
            return await interaction.response.send_message(embed=success_embed(
                "Infinite Cash Added",
                f"♾️ Granted **Infinite Cash** (`{INF_CASH_AMOUNT:,}` coins) to {user.mention}!\n🪙 **Wallet:** `♾️ Infinite`"
            ))

        clean_num = clean_amt.replace(",", "").replace("$", "")
        if not clean_num.isdigit():
            return await interaction.response.send_message(
                embed=error_embed("Invalid Amount", "Please specify a valid numeric coin amount or `inf`."),
                ephemeral=True
            )

        added = int(clean_num)
        if added <= 0:
            return await interaction.response.send_message(
                embed=error_embed("Invalid Amount", "Amount must be greater than 0."),
                ephemeral=True
            )

        new_wallet = min(INF_CASH_AMOUNT, eco["wallet"] + added)
        await db.update_economy(interaction.guild_id, user.id, wallet=new_wallet)

        wallet_display = "♾️ Infinite" if new_wallet >= INF_CASH_AMOUNT else f"`{new_wallet:,}` coins"
        await interaction.response.send_message(embed=success_embed(
            "Cash Added",
            f"💵 Added **+{added:,} coins** to {user.mention}'s wallet!\n🪙 **New Wallet Balance:** {wallet_display}"
        ))

    # --- ADVANCED SHOP SLASH COMMANDS ---
    @app_commands.command(name="product", description="Manage or browse shop products.")
    @app_commands.describe(action="Action: list, info, add, remove, or stock", query="Product name or ID", price="Price e.g. $5.00", category="Category name")
    @app_commands.choices(action=[
        app_commands.Choice(name="list", value="list"),
        app_commands.Choice(name="info", value="info"),
        app_commands.Choice(name="stock", value="stock"),
        app_commands.Choice(name="add", value="add"),
        app_commands.Choice(name="remove", value="remove")
    ])
    async def slash_product(
        self,
        interaction: discord.Interaction,
        action: str,
        query: Optional[str] = None,
        price: Optional[str] = None,
        category: Optional[str] = "General"
    ):
        if action == "list":
            items = await db.get_shop_items(interaction.guild_id)
            if not items:
                return await interaction.response.send_message(embed=info_embed("Products", "No products listed in the shop."), ephemeral=True)
            desc = "\n".join([f"• **#{i['id']} • {i['name']}** — `{i['price']}` (`{i['category']}`)" for i in items[:15]])
            embed = standard_embed(title=f"📦 {interaction.guild.name} • Products", description=desc, color=0x2ECC71)
            await interaction.response.send_message(embed=embed)
        elif action == "info":
            if not query:
                return await interaction.response.send_message(embed=error_embed("Missing Name", "Please specify a product name or ID."), ephemeral=True)
            items = await db.get_shop_items(interaction.guild_id)
            matched = next((i for i in items if query.lower() in i["name"].lower() or (query.isdigit() and int(query) == i["id"])), None)
            if not matched:
                return await interaction.response.send_message(embed=error_embed("Not Found", f"No product matched `{query}`."), ephemeral=True)
            count = await db.get_item_stock_count(interaction.guild_id, matched["name"])
            embed = standard_embed(
                title=f"📦 {matched['name']} • #{matched['id']}",
                description=f"• **Price:** `{matched['price']}`\n• **Category:** `{matched['category']}`\n• **Stock:** `{count}`\n• **Details:**\n```{matched['description'] or 'Instant delivery.'}```",
                color=0x2ECC71
            )
            await interaction.response.send_message(embed=embed)
        elif action == "add":
            if not interaction.user.guild_permissions.administrator:
                return await interaction.response.send_message(embed=error_embed("Unauthorized", "Admin only."), ephemeral=True)
            if not query or not price:
                return await interaction.response.send_message(embed=error_embed("Missing Info", "Please specify both `query` (name) and `price`."), ephemeral=True)
            item_id = await db.add_shop_item(interaction.guild_id, query, price, category or "General", "")
            await interaction.response.send_message(embed=success_embed("Product Added", f"Created product **#{item_id} • {query}** ({price})!"))
        elif action == "remove":
            if not interaction.user.guild_permissions.administrator:
                return await interaction.response.send_message(embed=error_embed("Unauthorized", "Admin only."), ephemeral=True)
            if not query or not query.isdigit():
                return await interaction.response.send_message(embed=error_embed("Invalid ID", "Provide a numeric product ID to remove."), ephemeral=True)
            removed = await db.remove_shop_item(interaction.guild_id, int(query))
            if removed:
                await interaction.response.send_message(embed=success_embed("Product Removed", f"Deleted product `#{query}`."))
            else:
                await interaction.response.send_message(embed=error_embed("Not Found", f"No product with ID `#{query}`."), ephemeral=True)
        elif action == "stock":
            counts = await db.get_stock_counts(interaction.guild_id)
            desc = "\n".join([f"• **{k}:** `{v}` in stock" for k, v in counts.items()]) if counts else "No digital stock recorded."
            embed = standard_embed(title="📊 Product Stock", description=desc, color=0x2ECC71)
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="buy", description="Quickly initiate a purchase for an item.")
    @app_commands.describe(product="Product name or ID")
    async def slash_buy(self, interaction: discord.Interaction, product: Optional[str] = None):
        cfg = await db.get_shop_config(interaction.guild_id)
        shop_title = cfg.get("shop_name", "Jack's Shop")
        embed = success_embed(
            f"🛒 {shop_title} • Ready to Order",
            f"To purchase **{product or 'items'}**, open a private purchase ticket on our Purchase Panel!\n"
            f"Use `/shoppanel` or click **Initiate Purchase** on the panel to get an automated invoice and blockchain verification."
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="cart", description="Manage or view your personal shopping cart.")
    @app_commands.describe(action="Cart action (view, add, clear)", item_id="Item ID to add", quantity="Item quantity")
    @app_commands.choices(action=[
        app_commands.Choice(name="view", value="view"),
        app_commands.Choice(name="add", value="add"),
        app_commands.Choice(name="clear", value="clear")
    ])
    async def slash_cart(self, interaction: discord.Interaction, action: str, item_id: Optional[int] = None, quantity: Optional[int] = 1):
        if action == "add" and item_id:
            await db.add_to_cart(interaction.guild_id, interaction.user.id, item_id, quantity or 1)
            await interaction.response.send_message(embed=success_embed("Cart Updated", f"Added `{quantity}x` of item `#{item_id}` to your cart."), ephemeral=True)
        elif action == "clear":
            await db.clear_cart(interaction.guild_id, interaction.user.id)
            await interaction.response.send_message(embed=success_embed("Cart Cleared", "Your cart is now empty."), ephemeral=True)
        else:
            items = await db.get_cart(interaction.guild_id, interaction.user.id)
            if not items:
                return await interaction.response.send_message(embed=info_embed("Shopping Cart", "Your cart is currently empty."), ephemeral=True)
            desc = "\n".join([f"• **{ci['name']}** (x{ci['quantity']}) — `{ci['price']}`" for ci in items])
            embed = standard_embed(title=f"🛒 {interaction.user.display_name}'s Cart", description=desc, color=0x2ECC71)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="order", description="Inspect order status, view receipts, or manage fulfillment.")
    @app_commands.describe(action="Order action", order_id="Order ID (e.g. ORD-123456)")
    @app_commands.choices(action=[
        app_commands.Choice(name="view", value="view"),
        app_commands.Choice(name="history", value="history"),
        app_commands.Choice(name="claim", value="claim"),
        app_commands.Choice(name="complete", value="complete"),
        app_commands.Choice(name="cancel", value="cancel")
    ])
    async def slash_order(self, interaction: discord.Interaction, action: str, order_id: Optional[str] = None):
        if action == "history":
            orders = await db.get_user_orders(interaction.guild_id, interaction.user.id)
            if not orders:
                return await interaction.response.send_message(embed=info_embed("Orders", "No orders on record."), ephemeral=True)
            desc = "\n".join([f"• `{o['order_id']}` — **{o['product_name']}** (`${o['total_usd']:.2f}`) — `{o['status'].title()}`" for o in orders[:8]])
            embed = standard_embed(title="📦 Order History", description=desc, color=0x2ECC71)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if not order_id:
            return await interaction.response.send_message(embed=error_embed("Missing ID", "Please specify an `order_id`."), ephemeral=True)

        order = await db.get_shop_order(order_id)
        if not order:
            return await interaction.response.send_message(embed=error_embed("Not Found", f"No order found with ID `{order_id}`."), ephemeral=True)

        if action == "view":
            tx_str = f"[`{shorten_address(order['txid'])}`](https://litecoinspace.org/tx/{order['txid']})" if order.get("txid") else "Pending"
            embed = standard_embed(
                title=f"📦 Order Details • {order['order_id']}",
                description=(
                    f"• **Product:** `{order['product_name']}` (x{order['quantity']})\n"
                    f"• **Total:** `${order['total_usd']:.2f}` ({order['total_ltc']:.6f} LTC)\n"
                    f"• **Status:** `{order['status'].title()}`\n"
                    f"• **Receipt:** `{order['receipt_id']}`\n"
                    f"• **TXID:** {tx_str}"
                ),
                color=0x2ECC71 if order["status"] == "completed" else 0xFEE75C
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif action == "claim":
            if not interaction.user.guild_permissions.manage_messages:
                return await interaction.response.send_message(embed=error_embed("Unauthorized", "Staff only."), ephemeral=True)
            await db.claim_order(order_id, interaction.user.id)
            await interaction.response.send_message(embed=success_embed("Order Claimed", f"Claimed Order `{order_id}`."))
        elif action == "complete":
            if not interaction.user.guild_permissions.manage_messages:
                return await interaction.response.send_message(embed=error_embed("Unauthorized", "Staff only."), ephemeral=True)
            completed = await db.complete_order(order_id, staff_id=interaction.user.id)
            cfg = await db.get_shop_config(interaction.guild_id)
            await log_deal_completed(interaction.guild, completed, completed_by=interaction.user, custom_branding=cfg.get("shop_name"))
            await interaction.response.send_message(embed=success_embed("Completed", f"Order `{order_id}` marked complete and logged."))
        elif action == "cancel":
            await db.cancel_order(order_id)
            await interaction.response.send_message(embed=warning_embed("Cancelled", f"Order `{order_id}` cancelled."))

    @app_commands.command(name="orders", description="List your recent purchases.")
    async def slash_orders(self, interaction: discord.Interaction):
        orders = await db.get_user_orders(interaction.guild_id, interaction.user.id)
        if not orders:
            return await interaction.response.send_message(embed=info_embed("Orders", "No orders on file."), ephemeral=True)
        desc = "\n".join([f"• `{o['order_id']}` — **{o['product_name']}** (`${o['total_usd']:.2f}`) — `{o['status'].title()}`" for o in orders[:8]])
        embed = standard_embed(title="📦 Your Orders", description=desc, color=0x2ECC71)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="track", description="Track an order or receipt ID in real time.")
    @app_commands.describe(query="Order ID or Receipt ID (e.g. ORD-123456 or RD-123456)")
    async def slash_track(self, interaction: discord.Interaction, query: str):
        clean = query.strip()
        order = await db.get_shop_order(clean) or await db.get_order_by_receipt(clean)
        if not order:
            return await interaction.response.send_message(embed=error_embed("Not Found", f"No record found for `{clean}`."), ephemeral=True)
        embed = standard_embed(
            title=f"🔍 Order Tracking • {order['order_id']}",
            description=f"• **Product:** `{order['product_name']}` (x{order['quantity']})\n• **Status:** `{order['status'].title()}`\n• **Amount:** `${order['total_usd']:.2f}`\n• **Receipt:** `{order['receipt_id']}`",
            color=0x2ECC71 if order["status"] == "completed" else 0xFEE75C
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="receipt", description="Inspect verified receipt details for a transaction.")
    @app_commands.describe(receipt_id="Receipt ID (e.g. RD-731158)")
    async def slash_receipt(self, interaction: discord.Interaction, receipt_id: str):
        order = await db.get_order_by_receipt(receipt_id.strip())
        if not order:
            return await interaction.response.send_message(embed=error_embed("Not Found", f"No receipt found matching `{receipt_id}`."), ephemeral=True)
        embed = standard_embed(
            title=f"🧾 Verified Receipt • {order['receipt_id']}",
            description=f"• **Order ID:** `{order['order_id']}`\n• **Buyer:** <@{order['user_id']}>\n• **Product:** `{order['product_name']}`\n• **Total Paid:** `${order['total_usd']:.2f}`\n• **Status:** `{order['status'].title()}`",
            color=0x2ECC71
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="coupon", description="Create or inspect store promo codes.")
    @app_commands.describe(action="create or view", code="Coupon code", discount="Discount percentage")
    @app_commands.choices(action=[
        app_commands.Choice(name="create", value="create"),
        app_commands.Choice(name="view", value="view")
    ])
    async def slash_coupon(self, interaction: discord.Interaction, action: str, code: str, discount: Optional[float] = 10.0):
        if action == "create":
            if not interaction.user.guild_permissions.administrator:
                return await interaction.response.send_message(embed=error_embed("Unauthorized", "Admin only."), ephemeral=True)
            cid = await db.create_coupon(interaction.guild_id, code, discount or 10.0)
            await interaction.response.send_message(embed=success_embed("Coupon Created", f"Coupon **`{code.upper()}`** created for `{discount}%` off!"))
        else:
            c = await db.get_coupon(interaction.guild_id, code)
            if not c:
                return await interaction.response.send_message(embed=error_embed("Not Found", f"Coupon `{code}` not found."), ephemeral=True)
            await interaction.response.send_message(embed=info_embed("Coupon Details", f"• **Code:** `{c['code']}`\n• **Discount:** `{c['discount_percent']}%`\n• **Uses:** `{c['uses_count']}/{c['max_uses']}`"))

    @app_commands.command(name="redeem", description="Check or redeem a store coupon code.")
    @app_commands.describe(code="Promo code to redeem")
    async def slash_redeem(self, interaction: discord.Interaction, code: str):
        c = await db.get_coupon(interaction.guild_id, code)
        if not c:
            return await interaction.response.send_message(embed=error_embed("Invalid Coupon", "Promo code not found."), ephemeral=True)
        if c["uses_count"] >= c["max_uses"]:
            return await interaction.response.send_message(embed=error_embed("Expired", "Coupon has reached maximum uses."), ephemeral=True)
        await interaction.response.send_message(embed=success_embed("Coupon Active", f"🎉 Coupon **`{c['code']}`** is valid for **{c['discount_percent']}% OFF**!"))

    @app_commands.command(name="staff", description="Staff order management and analytics dashboard.")
    @app_commands.describe(action="Staff action", order_id="Order ID")
    @app_commands.choices(action=[
        app_commands.Choice(name="stats", value="stats"),
        app_commands.Choice(name="claim", value="claim"),
        app_commands.Choice(name="complete", value="complete")
    ])
    async def slash_staff(self, interaction: discord.Interaction, action: str, order_id: Optional[str] = None):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(embed=error_embed("Unauthorized", "Staff only."), ephemeral=True)
        if action == "stats":
            stats = await db.get_shop_revenue_stats(interaction.guild_id)
            cfg = await db.get_shop_config(interaction.guild_id)
            desc = (
                f"> **Total Revenue:** `${stats['total_revenue']:,.2f} USD`\n"
                f"> **Monthly (30d):** `${stats['monthly_revenue']:,.2f} USD`\n"
                f"> **Daily (24h):** `${stats['daily_revenue']:,.2f} USD`\n\n"
                f"• **Completed Orders:** `{stats['completed_orders']}`\n"
                f"• **Total Orders:** `{stats['total_orders']}`"
            )
            embed = standard_embed(title=f"📊 {cfg.get('shop_name', 'Shop')} • Revenue Stats", description=desc, color=0x2ECC71)
            await interaction.response.send_message(embed=embed)
        elif action == "claim" and order_id:
            await db.claim_order(order_id, interaction.user.id)
            await interaction.response.send_message(embed=success_embed("Claimed", f"Claimed Order `{order_id}`."))
        elif action == "complete" and order_id:
            completed = await db.complete_order(order_id, staff_id=interaction.user.id)
            cfg = await db.get_shop_config(interaction.guild_id)
            await log_deal_completed(interaction.guild, completed, completed_by=interaction.user, custom_branding=cfg.get("shop_name"))
            await interaction.response.send_message(embed=success_embed("Completed", f"Completed Order `{order_id}`."))
        else:
            await interaction.response.send_message("Please provide an `order_id` for this action.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(SlashCommands(bot))

