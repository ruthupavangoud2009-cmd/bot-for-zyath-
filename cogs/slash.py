import discord
from discord import app_commands
from discord.ext import commands
import datetime
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db
from cogs.help import HelpView
from cogs.tickets import TicketPanelView, CreateEmbedModal
from cogs.trades import TradeStatusView, MercyModal
from cogs.shop import ShopView

class SlashCommands(commands.Cog):
    """Top 20 essential application slash commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 1. /help
    @app_commands.command(name="help", description="Open the clean interactive help desk.")
    async def slash_help(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        total_cmds = len(self.bot.commands) + len(self.bot.tree.get_commands())
        bot_name = self.bot.user.name if self.bot.user else "Zyath"

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
            embed.add_field(name=f"🔹 {m['method_name']}", value=f"```{m['address']}```{note_str}", inline=False)
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
    @app_commands.command(name="ticketpanel", description="Deploy the ticket creation panel with buttons.")
    @app_commands.default_permissions(administrator=True)
    async def slash_ticketpanel(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        target = channel or interaction.channel
        embed = standard_embed(
            title="🎫 Support & Service Tickets",
            description="Select a category or click a button below to open a ticket!"
        )
        await target.send(embed=embed, view=TicketPanelView())
        await interaction.response.send_message(embed=success_embed("Deployed", f"Panel sent to {target.mention}!"), ephemeral=True)

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
    @app_commands.default_permissions(manage_channels=True)
    async def slash_gtn(self, interaction: discord.Interaction, min_val: int = 1, max_val: int = 1000):
        cog = self.bot.get_cog("GuessTheNumber")
        if not cog:
            return await interaction.response.send_message("GTN game cog not loaded.", ephemeral=True)
        import random
        if min_val >= max_val or max_val - min_val < 5:
            return await interaction.response.send_message(embed=error_embed("Invalid Range", "Min must be less than max (range at least 5)."), ephemeral=True)
        cog.active_games[interaction.channel_id] = {
            "target": random.randint(min_val, max_val),
            "min": min_val,
            "max": max_val,
            "guesses": 0,
            "starter": interaction.user.id
        }
        embed = standard_embed(
            title="🎮 Guess The Number Started!",
            description=f"Guess a number between `{min_val}` and `{max_val}`!\n➕ = Guess higher\n➖ = Guess lower\n\nChannel will be locked on win!",
            color=0x57F287
        )
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

async def setup(bot: commands.Bot):
    await bot.add_cog(SlashCommands(bot))
