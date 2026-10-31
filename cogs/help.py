import discord
from discord.ext import commands
from utils.embeds import standard_embed, COLOR_PRIMARY
from utils.database import db

MODULES = {
    "moderation": {
        "title": "🛡️ Moderation Commands",
        "description": "Essential moderation commands to secure and organize your server.",
        "emoji": "🛡️",
        "color": 0xED4245,
        "commands": [
            ("`$kick @user [reason]`", "Kick a user from the server."),
            ("`$ban @user [reason]`", "Ban a user permanently from the server."),
            ("`$unban <user_id> [reason]`", "Unban a user by their user ID."),
            ("`$mute @user <duration> [reason]`", "Timeout a member (e.g. `10m`, `1h`, `7d`)."),
            ("`$unmute @user`", "Remove timeout from a member."),
            ("`$warn @user [reason]`", "Issue an official logged warning to a member."),
            ("`$warnings @user`", "View all warning records for a member."),
            ("`$clearwarnings @user`", "Clear all warning records for a member."),
            ("`$purge <amount> [@user]`", "Bulk delete between 1 and 100 messages."),
            ("`$lock [channel] [reason]`", "Lock channel permissions to prevent members from chatting."),
            ("`$unlock [channel]`", "Unlock a previously locked channel."),
            ("`$slowmode <seconds> [channel]`", "Set channel message slowmode rate."),
            ("`$nick @user <nickname>`", "Change or reset a member's nickname."),
            ("`$role <add/remove> @user @role`", "Assign or remove a role from a user."),
            ("`$setmodlog #channel`", "Configure the moderation audit log channel.")
        ]
    },
    "tickets": {
        "title": "🎫 Ultra-Modular Ticket System",
        "description": "Fully modular, interactive tickets with custom categories, buttons, dropdowns, routing, modals, and invoices.",
        "emoji": "🎫",
        "color": 0x5865F2,
        "commands": [
            ("`$ticketpanel [#channel]`", "Deploy the dynamic modular ticket panel with dropdown & buttons."),
            ("`$addcategory <name> | [emoji] | [desc]`", "Create or update a custom modular ticket category."),
            ("`$delcategory <name>`", "Delete a modular ticket category from the server."),
            ("`$categories`", "List all active modular ticket categories with routing details."),
            ("`$setcategorychannel <name> <#cat>`", "Route a specific category to its own Discord category channel."),
            ("`$setcategoryrole <name> <@role>`", "Assign a specific staff alert role to a category."),
            ("`$resetticketcategories`", "Reset categories back to default 4 modules."),
            ("`$setticketcategory <#category>`", "Set server default Discord category for tickets."),
            ("`$setticketrole <@role>`", "Set server default staff role for tickets."),
            ("`$setticketlogs <#channel>`", "Set transcript and ticket audit archive channel."),
            ("`$createembed [#channel]`", "Open interactive custom embed creator modal."),
            ("`$invoice <amount> <method> [product]`", "Send official order payment invoice inside a ticket."),
            ("`$ticket close`", "Close the current active ticket channel."),
            ("`$ticket transcript`", "Generate and save a complete HTML and text transcript."),
            ("`$ticket add @user`", "Add a member to the current ticket."),
            ("`$ticket remove @user`", "Remove a member from the current ticket."),
            ("`$ticket claim`", "Claim ticket as assigned staff handler."),
            ("`$ticket priority <low|med|high|urgent>`", "Set ticket priority level."),
            ("`$ticket rename <new-name>`", "Rename the current ticket channel."),
            ("`$ticket alert [message]`", "Ping ticket creator with a high-priority alert notification."),
            ("`$ticket stats`", "View server ticket resolution metrics.")
        ]
    },
    "vouches": {
        "title": "⭐ Vouch System & Leaderboard",
        "description": "Track member reputation, review history, leaderboards, and star ratings.",
        "emoji": "⭐",
        "color": 0xFEE75C,
        "commands": [
            ("`$vouch @user [1-5 stars] <comment>`", "Submit a verified reputation vouch for a trader/member."),
            ("`$vouches [@user]` / `$rep`", "View total vouches, star rating, and recent feedback for a user."),
            ("`$vouchlb` / `$vlb`", "View the ranked top vouched members leaderboard in the server."),
            ("`$vouchinfo <vouch_id>`", "View full metadata for a specific vouch."),
            ("`$delvouch <vouch_id>`", "Staff command to delete a false or inappropriate vouch."),
            ("`$vouchstats`", "View server-wide vouch metrics and averages."),
            ("`$importvouches @user <count>`", "Admin command to credit legacy vouches for migration."),
            ("`$setvouchchannel #channel`", "Set the official channel where new vouches are broadcasted.")
        ]
    },
    "shop": {
        "title": "🛒 Storefront & Payment Management",
        "description": "Product catalog with 1-click ticket order creation and payment gateways.",
        "emoji": "🛒",
        "color": 0x2ECC71,
        "commands": [
            ("`$shop [category]`", "Browse the server shop with dropdown ordering and quick links."),
            ("`$shopadd <name> | <price> | [cat] | [desc]`", "Add a new product or service to the shop."),
            ("`$shopremove <item_id>` / `$shopdel`", "Delete a product from the shop catalog by ID."),
            ("`$shoplist`", "Admin inventory overview of all shop items and IDs."),
            ("`$payment` / `$wallets` / `$pay`", "Display accepted payment methods and verified wallet addresses."),
            ("`$setpayment <name> | <addr> | [note]`", "Add a payment method (e.g. `$setpayment LTC | ltc1q... | Fast`)."),
            ("`$delpayment [ID or Name]`", "Delete a payment method by ID (e.g. `$delpayment 1`) or Name (`$delpayment LTC`), or run without args for an interactive dropdown!"),
            ("`$restock [#channel] [@everyone] <Item> | <Price> | [Details]`", "Broadcast restock alert with 1-click buy button."),
            ("`$tos` / `$terms`", "View shop Terms of Service, warranty, and replacement policy."),
            ("`$settos <text>`", "Set custom shop Terms of Service.")
        ]
    },
    "ai": {
        "title": "🤖 AI Store & Ticket Manager",
        "description": "24/7 intelligent automated shop assistant. Answers customer tickets when sellers are offline, scans stock, and gives real-time inventory updates.",
        "emoji": "🤖",
        "color": 0x5865F2,
        "commands": [
            ("`$ai <question>` / `$ask`", "Ask the AI Shop Assistant any question directly."),
            ("`$stock` / `$inventory`", "View real-time live stock counts of all products."),
            ("`$airestock <Item> [list/.txt]`", "AI stock scanner: feed raw accounts/keys or attach file to auto-count and import stock."),
            ("`$clearstock <Item>`", "Purge stock records for a specific product."),
            ("`$aimanager <on|off>` / `$aitoggle`", "Toggle automated AI offline ticket assistance."),
            ("`$aisettings`", "View current AI Assistant configuration and stock metrics."),
            ("`$aisetprompt <text>`", "Set custom personality or store instructions for the AI.")
        ]
    },
    "trades": {
        "title": "🤝 Live MM Trades & Mercy",
        "description": "Log and track Middleman transactions with verified receipt cards.",
        "emoji": "🤝",
        "color": 0xFEE75C,
        "commands": [
            ("`$mercy`", "Open the interactive MM Receipt Modal or provide parameters directly."),
            ("`$mercy @buyer @seller <amount> <details>`", "Quickly post a verified Middleman receipt to the trade/vouch channel."),
            ("`$trade <trade_id>`", "Check the status and metadata of a specific trade (e.g. `$trade TRD-8421`)."),
            ("`$settradechannel #channel`", "Set the dedicated channel for live MM receipts.")
        ]
    },
    "gtn": {
        "title": "🎮 Guess The Number Game",
        "description": "Interactive mini-game with real-time reaction hints and channel locking.",
        "emoji": "🎮",
        "color": 0x57F287,
        "commands": [
            ("`$gtn <min> <max>`", "Start a game (e.g. `$gtn 1 5000`). Bot reacts with `➕` if lower, `➖` if higher."),
            ("`$gtnstop`", "Stop the currently running game in this channel."),
            ("`$gtnstatus`", "Check the current game range and total guesses made.")
        ]
    },
    "welcomer": {
        "title": "👋 Welcomer & Goodbye",
        "description": "Customizable greeting embeds, autoroles, and goodbye logs.",
        "emoji": "👋",
        "color": 0x9B59B6,
        "commands": [
            ("`$setwelcome #channel`", "Set the channel for welcome embeds with custom PIL cards."),
            ("`$setleave #channel`", "Set the channel for member leave logs."),
            ("`$setautorole @role`", "Set the role automatically assigned to joining members."),
            ("`$setwelcomemsg <text>`", "Set custom welcome message (Supports `{user.mention}`, `{server}`, `{membercount}`)."),
            ("`$welcometest`", "Send a test welcome card to preview your settings.")
        ]
    },
    "fun": {
        "title": "🎉 Fun & Utilities",
        "description": "Community commands, $say auto-delete, and restricted ghost ping spam.",
        "emoji": "🎉",
        "color": 0xE91E63,
        "commands": [
            ("`$say <message>`", "Make the bot say something and automatically delete your message."),
            ("`$hi`", "Say hi to Zyath Bot with an interactive response and quick buttons."),
            ("`$sayembed <title> | <desc>`", "Make the bot speak in a styled embed and delete trigger message."),
            ("`$spam <count> @user [msg]`", "Restricted command: deletes trigger, ghost mentions user up to 100x and cleans up!"),
            ("`$cancelspam [all]` / `$stopspam`", "Cancel and stop active ghost spam immediately."),
            ("`$setspamusers @user`", "Authorize a user to execute the restricted `$spam` command."),
            ("`$removespamuser @user`", "Revoke `$spam` command permission for a user."),
            ("`$ping` / `$latency`", "Display real-time latencies (WebSocket, REST API, Database, 24/7 Web Server)."),
            ("`$8ball <question>`", "Ask the magic fortune 8-ball."),
            ("`$coinflip`", "Flip a coin (Heads or Tails)."),
            ("`$roll [max]`", "Roll a random number dice."),
            ("`$roast [@user]`", "Playfully roast a member."),
            ("`$avatar [@user]` / `$av` / `$pfp`", "Display full-resolution avatar of a user."),
            ("`$userinfo [@user]` / `$whois` / `$ui`", "Display detailed Discord profile dossier for a member."),
            ("`$serverinfo` / `$si`", "Display server telemetry, member count, boost level, and info."),
            ("`$poll <question>`", "Create a thumbs up/down reaction poll.")
        ]
    },
    "owner": {
        "title": "👑 Management & No-Prefix",
        "description": "Bot control, live diagnostics, reload, and no-prefix whitelist.",
        "emoji": "👑",
        "color": 0x57F287,
        "commands": [
            ("`$np add @user`", "Authorize a member to use all bot commands without prefix."),
            ("`$np remove @user`", "Revoke no-prefix permissions for a user."),
            ("`$np list`", "List all authorized no-prefix members."),
            ("`$botstats`", "View system hardware diagnostics, CPU, RAM, and Supabase database latency."),
            ("`$checkperms` / `$perms`", "Perform full server permission audit to ensure zero missing permissions."),
            ("`$sync`", "Globally synchronize application slash commands to Discord."),
            ("`$reload <cog|all>`", "Hot-reload bot cogs without taking the bot offline.")
        ]
    },
    "slash": {
        "title": "⚡ Application Slash Commands (/)",
        "description": "Native Discord slash command equivalents available across the entire server.",
        "emoji": "⚡",
        "color": 0x5865F2,
        "commands": [
            ("`/help`", "Open the clean interactive help desk modal & menu."),
            ("`/shop [category]`", "Browse the verified marketplace catalog with direct ticket ordering."),
            ("`/payment`", "View accepted payment methods and wallet addresses."),
            ("`/tos`", "View shop Terms of Service and warranty guidelines."),
            ("`/ticket <close|transcript>`", "Close current ticket channel or export HTML transcript."),
            ("`/vouch @user <stars> <comment>`", "Submit a verified customer review for a trader."),
            ("`/vouchlb`", "View top vouched server merchants leaderboard."),
            ("`/ping`", "Check real-time network and gateway latency."),
            ("`/avatar [@user]`", "View a member's avatar in full resolution."),
            ("`/userinfo [@user]`", "Inspect a member's profile dossier, badges, and roles."),
            ("`/serverinfo`", "Inspect server telemetry and stats."),
            ("`/say <message>`", "Make the bot repeat a message."),
            ("`/warn @user <reason>`", "Issue an official disciplinary warning to a member."),
            ("`/mute @user <duration> <reason>`", "Timeout a member (e.g. `10m`, `1h`, `7d`)."),
            ("`/kick @user <reason>`", "Kick a member from the server."),
            ("`/ban @user <reason>`", "Ban a member permanently."),
            ("`/purge <amount>`", "Bulk delete messages (1 to 100)."),
            ("`/stock`", "Check live product inventory levels."),
            ("`/gtn <min> <max>`", "Start Guess The Number game."),
            ("`/poll <question>`", "Create a community reaction poll.")
        ]
    }
}

class HelpSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot, author_name: str, prefix: str):
        self.bot = bot
        self.author_name = author_name
        self.prefix = prefix

        options = [
            discord.SelectOption(label="Home", description="Return to main dashboard overview", emoji="🏠", value="home"),
            discord.SelectOption(label="Moderation", description="Ban, kick, mute, warn, lock, purge", emoji="🛡️", value="moderation"),
            discord.SelectOption(label="Tickets", description="Panels, transcripts, claim, invoices", emoji="🎫", value="tickets"),
            discord.SelectOption(label="Vouches & Leaderboard", description="Reputation logger, top sellers, stats", emoji="⭐", value="vouches"),
            discord.SelectOption(label="Shop & Storefront", description="Store catalog, crypto payments, TOS", emoji="🛒", value="shop"),
            discord.SelectOption(label="AI Store & Restock", description="AI Manager, live stock, bulk restocks", emoji="🤖", value="ai"),
            discord.SelectOption(label="Middleman & Trades", description="Live MM trade receipts and $mercy", emoji="🤝", value="trades"),
            discord.SelectOption(label="Guess The Number", description="GTN mini-game with +/- reactions", emoji="🎮", value="gtn"),
            discord.SelectOption(label="Welcomer", description="Welcome embeds, autoroles, leave logs", emoji="👋", value="welcomer"),
            discord.SelectOption(label="Fun & Utilities", description="$say, $spam, multi-ping, 8ball, tools", emoji="🎉", value="fun"),
            discord.SelectOption(label="Management & Owner", description="No-prefix, diagnostics, perms audit", emoji="👑", value="owner"),
            discord.SelectOption(label="Slash Commands", description="Top 20 Discord application slash commands", emoji="⚡", value="slash")
        ]
        super().__init__(
            placeholder="🏠 Home",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]

        if choice == "home":
            latency = round(self.bot.latency * 1000)
            total_cmds = len(self.bot.commands) + len(self.bot.tree.get_commands())
            bot_name = self.bot.user.name if self.bot.user else "Zyath"

            embed = standard_embed(
                title=f"Hey, I'm {bot_name}",
                description=(
                    "> Built for our community — keeping your server safe, active, and effortlessly connected.\n\n"
                    f"• **Latency:** `{latency}ms`\n"
                    f"• **Prefix:** `{self.prefix}` | **Slash:** `/`\n"
                    f"• **Available Commands:** `{total_cmds}`"
                ),
                color=0x2B2D31
            )
            embed.set_footer(text=f"Requested by {self.author_name}")
            return await interaction.response.edit_message(embed=embed, view=self.view)

        module = MODULES.get(choice)
        if not module:
            return await interaction.response.send_message("Module not found.", ephemeral=True)

        desc = f"> {module['description']}\n\n"
        for cmd, cmd_desc in module["commands"]:
            desc += f"• **{cmd}**\n  └ *{cmd_desc}*\n"

        embed = standard_embed(
            title=module["title"],
            description=desc,
            color=module["color"]
        )
        embed.set_footer(text=f"Requested by {self.author_name} • Use {self.prefix} before commands")
        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(discord.ui.View):
    def __init__(self, bot: commands.Bot, author_name: str, prefix: str):
        super().__init__(timeout=300)
        self.add_item(HelpSelect(bot, author_name, prefix))

        # Add link buttons matching user screenshot
        invite_url = "https://discord.com/oauth2/authorize?client_id=1521774957065928734&permissions=8&scope=bot%20applications.commands"
        if bot.user:
            invite_url = f"https://discord.com/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands"

        self.add_item(discord.ui.Button(label="Invite Zyath", style=discord.ButtonStyle.link, url=invite_url, emoji="🚀"))
        self.add_item(discord.ui.Button(label="Support Server", style=discord.ButtonStyle.link, url="https://discord.gg/zyath", emoji="💬"))

class Help(commands.Cog):
    """Modern, minimalist, and ultra-aesthetic help desk modeled after top-tier community bots."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="help", aliases=["h"], help="Display the clean interactive help desk.")
    async def help_cmd(self, ctx: commands.Context, module_name: str = None):
        prefix = ctx.prefix or "$"

        if module_name:
            clean_name = module_name.lower().strip()
            for key, mod in MODULES.items():
                if clean_name in key or key in clean_name:
                    desc = f"> {mod['description']}\n\n"
                    for cmd, cmd_desc in mod["commands"]:
                        desc += f"• **{cmd}**\n  └ *{cmd_desc}*\n"
                    embed = standard_embed(
                        title=mod["title"],
                        description=desc,
                        color=mod["color"]
                    )
                    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
                    return await ctx.send(embed=embed)

        latency = round(self.bot.latency * 1000)
        total_cmds = len(self.bot.commands) + len(self.bot.tree.get_commands())
        bot_name = self.bot.user.name if self.bot.user else "Zyath"

        embed = standard_embed(
            title=f"Hey, I'm {bot_name}",
            description=(
                "> Built for our community — keeping your server safe, active, and effortlessly connected.\n\n"
                f"• **Latency:** `{latency}ms`\n"
                f"• **Prefix:** `{prefix}` | **Slash:** `/`\n"
                f"• **Available Commands:** `{total_cmds}`"
            ),
            color=0x2B2D31
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")

        view = HelpView(self.bot, ctx.author.display_name, prefix)
        await ctx.send(embed=embed, view=view)

async def setup(bot: commands.Bot):
    bot.help_command = None
    await bot.add_cog(Help(bot))
