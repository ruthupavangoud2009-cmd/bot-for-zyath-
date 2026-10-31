import discord
from discord.ext import commands
from utils.embeds import standard_embed, COLOR_PRIMARY

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
            ("`$mute / $timeout @user <duration> [reason]`", "Timeout a member (e.g. `10m`, `1h`, `7d`)."),
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
        "title": "🎫 Advanced Ticket System",
        "description": "Fully automated, interactive support tickets with modals, transcripts, and claim features.",
        "emoji": "🎫",
        "color": 0x5865F2,
        "commands": [
            ("`$ticketpanel [#channel]`", "Deploy the interactive ticket creation panel with categories."),
            ("`$createembed [#channel]`", "Open the interactive custom embed creator modal."),
            ("`$invoice <amount> <method> [product]`", "Send an official order payment invoice inside a ticket."),
            ("`$setticketcategory <category_id>`", "Set the Discord category under which tickets are opened."),
            ("`$setticketrole @role`", "Set the support staff role pinged and granted access to tickets."),
            ("`$setticketlogs #channel`", "Set the transcript and ticket audit archive channel."),
            ("`$ticket close`", "Close the current active ticket channel."),
            ("`$ticket transcript`", "Export an aesthetic HTML transcript of this ticket."),
            ("`$ticket add @user`", "Add a member to the active ticket."),
            ("`$ticket remove @user`", "Remove a member from the active ticket.")
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
    "vouches": {
        "title": "⭐ Vouch System",
        "description": "Track member reputation, review history, and 5-star ratings.",
        "emoji": "⭐",
        "color": 0xFEE75C,
        "commands": [
            ("`$vouch @user [1-5 stars] <comment>`", "Submit a reputation vouch for a trader/member."),
            ("`$vouches [@user]`", "View total vouches, star rating, and recent feedback for a user."),
            ("`$setvouchchannel #channel`", "Set the official channel where new vouches are broadcasted.")
        ]
    },
    "shop": {
        "title": "🛒 Storefront & Orders",
        "description": "Product catalog with 1-click ticket order creation.",
        "emoji": "🛒",
        "color": 0x2ECC71,
        "commands": [
            ("`$shop [category]`", "Browse the server shop with dropdown ordering."),
            ("`$shopadd <name> | <price> | [cat] | [desc]`", "Add a new product or service to the shop."),
            ("`$shopremove <item_id>`", "Delete a product from the shop catalog."),
            ("`$shoplist`", "Admin inventory overview of all shop items and IDs."),
            ("`$payment`", "Display accepted payment methods and verified wallet addresses."),
            ("`$setpayment <name> | <addr> | [note]`", "Configure a payment method or crypto wallet."),
            ("`$delpayment <id>`", "Remove an existing payment method."),
            ("`$tos`", "View shop Terms of Service, warranty, and replacement policy."),
            ("`$settos <text>`", "Set custom shop Terms of Service.")
        ]
    },
    "welcomer": {
        "title": "👋 Welcomer & Goodbye",
        "description": "Customizable greeting embeds, autoroles, and goodbye logs.",
        "emoji": "👋",
        "color": 0x9B59B6,
        "commands": [
            ("`$setwelcome #channel`", "Set the channel for welcome embeds."),
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
            ("`$say <message>`", "Make the bot say something and automatically deletes your trigger message."),
            ("`$hi`", "Say hi to Zyath Bot with an interactive response and delete command message."),
            ("`$sayembed <title> | <desc>`", "Make the bot speak in a styled embed and deletes trigger message."),
            ("`$spam <count> @user [msg]`", "Restricted command: deletes trigger, ghost mentions user up to 100x and deletes all spam messages!"),
            ("`$cancelspam [all]`", "Cancel and stop active ghost spam immediately (Aliases: $stopspam, $stop)."),
            ("`$setspamusers @user`", "Authorize a user to execute the restricted `$spam` command."),
            ("`$removespamuser @user`", "Revoke `$spam` command permission for a user."),
            ("`$8ball <question>`", "Ask the magic fortune 8-ball."),
            ("`$coinflip`", "Flip a coin (Heads or Tails)."),
            ("`$roll [max]`", "Roll a random number dice."),
            ("`$roast [@user]`", "Playfully roast a member."),
            ("`$avatar [@user]`", "Display full-resolution avatar of a user."),
            ("`$userinfo [@user]`", "Display detailed Discord profile data for a member."),
            ("`$serverinfo`", "Display server stats, member count, boost level, and info."),
            ("`$poll <question>`", "Create a thumbs up/down reaction poll."),
            ("`$ping`", "Display bot WebSocket latency.")
        ]
    }
}

class HelpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Home / Overview", description="Main help desk and overview", emoji="🏠", value="home"),
            discord.SelectOption(label="Moderation", description="Ban, kick, mute, warn, lock, purge", emoji="🛡️", value="moderation"),
            discord.SelectOption(label="Ticket System", description="Panels, transcripts, claim, controls", emoji="🎫", value="tickets"),
            discord.SelectOption(label="Guess The Number", description="GTN mini-game with +/- reactions", emoji="🎮", value="gtn"),
            discord.SelectOption(label="Middleman & Trades", description="Live MM trade receipts and $mercy", emoji="🤝", value="trades"),
            discord.SelectOption(label="Vouch System", description="Reputation logger and 5-star ratings", emoji="⭐", value="vouches"),
            discord.SelectOption(label="Shop System", description="Storefront catalog and ticket ordering", emoji="🛒", value="shop"),
            discord.SelectOption(label="Welcomer", description="Welcome embeds, autoroles, leave logs", emoji="👋", value="welcomer"),
            discord.SelectOption(label="Fun & Utilities", description="$say, $spam, 8ball, coinflip, avatar", emoji="🎉", value="fun")
        ]
        super().__init__(
            placeholder="📂 Select a module to explore commands...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]

        if choice == "home":
            embed = standard_embed(
                title="⚡ Zyath Bot • Command Center",
                description=(
                    "Welcome to the **Zyath Bot** Help Menu!\n\n"
                    "Use the dropdown selector below to browse through each command category.\n\n"
                    "**Available Modules:**\n"
                    "• 🛡️ **Moderation** — Powerful server moderation & audit logs\n"
                    "• 🎫 **Ticket System** — Automated interactive support & orders\n"
                    "• 🎮 **Guess The Number** — Channel locking mini-game with reactions\n"
                    "• 🤝 **Middleman & Trades** — Official `$mercy` live transaction logger\n"
                    "• ⭐ **Vouch System** — Reputation logger with star ratings\n"
                    "• 🛒 **Shop System** — Digital store with direct-to-ticket checkout\n"
                    "• 👋 **Welcomer** — Custom greetings & autorole\n"
                    "• 🎉 **Fun & Utilities** — `$say`, restricted ghost `$spam`, tools\n\n"
                    "💡 *Default prefix is `$` (e.g. `$help`). Select a module below to start!*"
                ),
                color=COLOR_PRIMARY
            )
            embed.set_thumbnail(url=interaction.client.user.display_avatar.url)
            await interaction.response.edit_message(embed=embed, view=self.view)
            return

        module = MODULES.get(choice)
        if not module:
            return await interaction.response.send_message("Module not found.", ephemeral=True)

        embed = standard_embed(
            title=module["title"],
            description=f"{module['description']}\n\n",
            color=module["color"]
        )

        for cmd, desc in module["commands"]:
            embed.add_field(name=cmd, value=f"> {desc}", inline=False)

        embed.set_footer(text=f"Zyath Bot • {module['title']} • Use $ before commands")
        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(HelpSelect())

class Help(commands.Cog):
    """Modern module-based help menu with interactive dropdowns."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="help", help="Display the interactive module-based help menu.")
    async def help_cmd(self, ctx: commands.Context, module_name: str = None):
        if module_name:
            clean_name = module_name.lower().strip()
            for key, mod in MODULES.items():
                if clean_name in key or key in clean_name:
                    embed = standard_embed(
                        title=mod["title"],
                        description=f"{mod['description']}\n\n",
                        color=mod["color"]
                    )
                    for cmd, desc in mod["commands"]:
                        embed.add_field(name=cmd, value=f"> {desc}", inline=False)
                    return await ctx.send(embed=embed)

        embed = standard_embed(
            title="⚡ Zyath Bot • Command Center",
            description=(
                "Welcome to the **Zyath Bot** Help Menu!\n\n"
                "Use the dropdown selector below to browse through each command category.\n\n"
                "**Available Modules:**\n"
                "• 🛡️ **Moderation** — Powerful server moderation & audit logs\n"
                "• 🎫 **Ticket System** — Automated interactive support & orders\n"
                "• 🎮 **Guess The Number** — Channel locking mini-game with reactions\n"
                "• 🤝 **Middleman & Trades** — Official `$mercy` live transaction logger\n"
                "• ⭐ **Vouch System** — Reputation logger with star ratings\n"
                "• 🛒 **Shop System** — Digital store with direct-to-ticket checkout\n"
                "• 👋 **Welcomer** — Custom greetings & autorole\n"
                "• 🎉 **Fun & Utilities** — `$say`, restricted ghost `$spam`, tools\n\n"
                "💡 *Default prefix is `$` (e.g. `$help`). Select a module below to start!*"
            ),
            color=COLOR_PRIMARY
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url if self.bot.user else None)
        embed.set_footer(text="Select a category from the dropdown below")
        await ctx.send(embed=embed, view=HelpView())

async def setup(bot: commands.Bot):
    # Remove default discord.py help command
    bot.help_command = None
    await bot.add_cog(Help(bot))
