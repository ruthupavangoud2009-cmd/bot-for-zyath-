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
        "title": "🛒 Shop & Storefront",
        "description": "Storefront catalog, interactive purchase panel, and shop settings.",
        "emoji": "🛒",
        "color": 0x2ECC71,
        "commands": [
            ("`$shop [category]` / `/shop`", "Browse the server shop with dropdown ordering and quick links."),
            ("`$shoppanel` / `/shop panel`", "Deploy the customizable purchase panel matching reference."),
            ("`$setshopname <Name>`", "Configure official store branding name (e.g. Kyoka Shop)."),
            ("`$tos` / `$terms` / `/tos`", "View shop Terms of Service, warranty, and refund policy."),
            ("`$settos <text>`", "Set custom shop Terms of Service and warranty."),
            ("`$restock [#channel] [@everyone] <Item> | <Price> | [Details]`", "Broadcast restock alert with 1-click buy button.")
        ]
    },
    "products": {
        "title": "📦 Product Management",
        "description": "Create, edit, inspect, and remove shop catalog products.",
        "emoji": "📦",
        "color": 0x2ECC71,
        "commands": [
            ("`$product list` / `/product list`", "List all products available in the shop catalog."),
            ("`$product info <Name/ID>` / `/product info`", "View detailed specifications and price for a product."),
            ("`$product add <Name> | <Price> | [Cat] | [Desc]`", "Add a new product to the shop inventory."),
            ("`$product remove <ID>` / `$shopdel`", "Remove a product from the shop catalog by ID."),
            ("`$product stock [name]` / `/product stock`", "Check live digital stock counts across products."),
            ("`$shopadd <Name> | <Price> | [Cat] | [Desc]`", "Classic command to add an item to the storefront."),
            ("`$shoplist`", "Admin overview of all shop items and IDs.")
        ]
    },
    "purchases": {
        "title": "🛍️ Purchases & Shopping Cart",
        "description": "Instant purchases, product variations, and shopping cart management.",
        "emoji": "🛍️",
        "color": 0x2ECC71,
        "commands": [
            ("`$buy [product]` / `/buy`", "Initiate purchase flow for a product."),
            ("`$cart` / `/cart`", "View items currently in your shopping cart."),
            ("`$cart add <item_id> [qty]`", "Add products to your cart before checkout."),
            ("`$cart remove <item_id>`", "Remove an item from your shopping cart."),
            ("`$cart clear`", "Empty your shopping cart.")
        ]
    },
    "orders": {
        "title": "📋 Orders & Tracking",
        "description": "Order lookup, real-time tracking, receipts, and order lifecycle management.",
        "emoji": "📋",
        "color": 0x2ECC71,
        "commands": [
            ("`$order view <order_id>` / `/order view`", "Inspect order status, blockchain payment, and receipts."),
            ("`$order history [@user]` / `/order history`", "View previous purchases and receipts for a customer."),
            ("`$track <order_or_receipt_id>` / `/track`", "Track the live status of an order or receipt ID in real time."),
            ("`$receipt <receipt_id>` / `/receipt`", "View verified cryptographic receipt certificate for a trade."),
            ("`$order claim <order_id>`", "Staff: claim a pending purchase ticket."),
            ("`$order complete <order_id>`", "Staff: mark an order fulfilled and trigger deal completion log."),
            ("`$order cancel <order_id>`", "Cancel a pending purchase ticket."),
            ("`$order refund <order_id>`", "Admin: record an official order refund.")
        ]
    },
    "payments": {
        "title": "💳 Payments & Gateways",
        "description": "Payment gateway management and automated Litecoin blockchain invoicing.",
        "emoji": "💳",
        "color": 0x2ECC71,
        "commands": [
            ("`$payment` / `$wallets` / `/payment`", "Display accepted payment methods and verified wallet addresses."),
            ("`$setpayment <Name> | <Address> | [Note]`", "Add or update an official payment gateway."),
            ("`$delpayment [ID or Name]`", "Delete a payment gateway by ID, Name, or interactive dropdown."),
            ("`$setshopltc <address>`", "Configure shop receiving Litecoin address for automated invoices.")
        ]
    },
    "ltc": {
        "title": "🪙 Litecoin (LTC) Payments & Wallet Tracking",
        "description": "Send direct on-chain LTC payments, manage your wallet, and track blockchain transactions live.",
        "emoji": "🪙",
        "color": 0x345C9C,
        "commands": [
            ("`$pay <address|@user> <amount> [ltc] [-y]` / `/pay`", "Send direct on-chain LTC payment or off-chain Discord transfer. (e.g. `$pay addy 1$ ltc` or `$pay addy 0.05 ltc`)."),
            ("`$wallet` / `/wallet`", "Open Kyoka Wallet Dashboard: balances, deposit address, and payment key status."),
            ("`$wallet setkey <wif>` / `/wallet setkey`", "Link your Litecoin private key (AES-256 encrypted) to pay directly from Discord."),
            ("`$wallet deposit` / `/wallet deposit`", "Display your personal Litecoin deposit address and QR code."),
            ("`$wallet withdraw <address> <amount>`", "Withdraw funds from your deposit balance to an external LTC address."),
            ("`$wallet removekey`", "Purge your private signing key from the bot database."),
            ("`$ltc link <address>` / `/ltc link`", "Link your public Litecoin wallet (supports legacy, segwit, bech32)."),
            ("`$ltc balance [@user]` / `/ltc balance`", "Check the actual blockchain balance of your linked wallet."),
            ("`$ltc price` / `/ltc price`", "View live LTC/USD price updated across public exchanges."),
            ("`$ltc portfolio` / `/ltc portfolio`", "Display your balance and live estimated USD valuation."),
            ("`$ltc transactions` / `/ltc transactions`", "Show recent incoming and outgoing blockchain transactions."),
            ("`$ltc unlink` / `/ltc unlink`", "Disconnect your linked wallet from your profile."),
            ("`$ltc address` / `/ltc address`", "Display your or another member's linked LTC address."),
            ("`$ltc check <address>` / `/ltc check`", "Audit any public Litecoin address directly on the blockchain."),
            ("`$ltc status <txid>` / `/ltc status`", "Inspect confirmation count and block status of any LTC transaction.")
        ]
    },
    "purchase_tickets": {
        "title": "🎫 Purchase Tickets",
        "description": "Private customer purchase channels, invoice generation, and ticket controls.",
        "emoji": "🎫",
        "color": 0x5865F2,
        "commands": [
            ("`$ticket close` / `/ticket close`", "Close the current active purchase ticket channel."),
            ("`$ticket transcript` / `/ticket transcript`", "Generate and save a complete HTML and text transcript."),
            ("`$ticket add @user`", "Add a member or co-buyer to the ticket."),
            ("`$ticket remove @user`", "Remove a member from the ticket channel."),
            ("`$ticket claim`", "Claim ticket as assigned staff handler."),
            ("`$shopsupport [details]`", "Open a private support ticket for order assistance.")
        ]
    },
    "feedback": {
        "title": "⭐ Customer Feedback & Reviews",
        "description": "Verified customer feedback system with 5-star ratings and testimonials.",
        "emoji": "⭐",
        "color": 0xFEE75C,
        "commands": [
            ("`$feedback review <order_id>` / `/feedback review`", "Submit a 5-star rating and written review for a completed order."),
            ("`$feedback stats` / `/feedback stats`", "View shop customer satisfaction metrics and total review counts."),
            ("`$feedback user [@user]` / `/feedback user`", "Inspect all reviews written by a specific customer."),
            ("`$feedback delete <review_id>`", "Staff only: delete a fraudulent review."),
            ("`$setfeedbackchannel #channel`", "Configure the official channel where customer feedback is posted.")
        ]
    },
    "legit": {
        "title": "✨ Legit Counter & Vouch System",
        "description": "Interactive trust panel with 1-click vouch button and CheckT ledger.",
        "emoji": "✨",
        "color": 0x57F287,
        "commands": [
            ("`$legit` / `/legit`", "View the current store legitimacy score and total verified vouches."),
            ("`$legit panel [#channel]` / `/legit panel`", "Deploy the 'Is Kyoka Shop Trusted?' panel with Legit & CheckT buttons."),
            ("`$legit check` / `/legit check`", "Inspect the complete paginated ledger of users who vouched."),
            ("`$legit remove @user`", "Staff only: remove a fraudulent vouch."),
            ("`$legit reset`", "Admin only: reset all legit vouches."),
            ("`$vouch @user [1-5 stars] <comment>`", "Submit a verified vouch for a community trader."),
            ("`$vouches [@user]` / `$rep`", "View member vouches and reputation rating."),
            ("`$vouchlb` / `$vlb`", "View the top vouched seller leaderboard.")
        ]
    },
    "deal_logs": {
        "title": "🤝 Deal Completed Logs",
        "description": "Automated polished green receipts logged to the official deal channel.",
        "emoji": "🤝",
        "color": 0x2ECC71,
        "commands": [
            ("`$setdeallog #channel`", "Configure the official channel for green Deal Completed embeds."),
            ("`$track <receipt_id>`", "Verify receipt authenticity and customer lifetime spend."),
            ("`$mercy @buyer @seller <amount> <details>`", "Post an official Middleman deal completion receipt.")
        ]
    },
    "customer": {
        "title": "👤 Customer Management",
        "description": "Customer CRM profiles, lifetime spending, loyalty tiers, and leaderboards.",
        "emoji": "👤",
        "color": 0x2ECC71,
        "commands": [
            ("`$customer profile [@user]` / `/customer profile`", "View customer CRM profile: spend, completed orders, loyalty tier."),
            ("`$customer spend [@user]` / `/customer spend`", "View total verified lifetime spending for a customer."),
            ("`$customer orders [@user]` / `/customer orders`", "View full purchase history for a customer."),
            ("`$customer feedback [@user]` / `/customer feedback`", "View all customer reviews written by a user."),
            ("`$customer leaderboard` / `$customerlb`", "View the top customer spending leaderboard.")
        ]
    },
    "staff_tools": {
        "title": "🛡️ Staff Order Processing",
        "description": "Staff order dashboard, claiming, fulfillment, and digital delivery.",
        "emoji": "🛡️",
        "color": 0x5865F2,
        "commands": [
            ("`$shopstaff` / `/staff`", "View pending orders awaiting staff fulfillment."),
            ("`$shopstaff claim <order_id>` / `/staff claim`", "Claim a pending order to handle delivery."),
            ("`$shopstaff complete <order_id>` / `/staff complete`", "Complete an order and trigger deal logs."),
            ("`$shopstaff deliver <order_id> <content>`", "Directly deliver digital credentials/accounts to customer."),
            ("`$shopstaff stats` / `/staff stats`", "View store revenue, daily sales, and top selling products.")
        ]
    },
    "admin_tools": {
        "title": "⚙️ Shop Admin & Settings",
        "description": "Store branding, discounts, promo codes, and configuration.",
        "emoji": "⚙️",
        "color": 0xED4245,
        "commands": [
            ("`$setshopname <Name>`", "Configure shop branding title (default: Kyoka Shop)."),
            ("`$setshopltc <address>`", "Set official shop Litecoin payment address."),
            ("`$setdeallog #channel`", "Set the deal-log channel for completed receipts."),
            ("`$setfeedbackchannel #channel`", "Set the customer feedback channel."),
            ("`$coupon create <CODE> <percent>`", "Create a store discount promo code."),
            ("`$redeem <CODE>` / `/redeem`", "Redeem a promo code for purchase discounts."),
            ("`$settos <text>`", "Set shop Terms of Service.")
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
    "giveaways": {
        "title": "🎁 Ultimate Giveaways Suite",
        "description": "Host persistent giveaways with live countdowns, role requirements, and instant rerolls.",
        "emoji": "🎁",
        "color": 0x5865F2,
        "commands": [
            ("`$gstart <time> [winners] <prize>`", "Start a giveaway (e.g. `$gstart 10m 1w Nitro` or `$gstart 1h 2 Nitro --role @VIP`)."),
            ("`$gend <message_id>`", "End an active giveaway early and pick winners immediately."),
            ("`$greroll <message_id> [count]`", "Reroll new winner(s) from previous entrants."),
            ("`$glist`", "List all active giveaways currently running in this server."),
            ("`$gcancel <message_id>`", "Cancel a running giveaway without drawing winners.")
        ]
    },
    "games": {
        "title": "🎮 GW Event Mini-Games",
        "description": "Exciting chat-based mini-games for giveaways with prize tracking and channel auto-locking.",
        "emoji": "🎮",
        "color": 0x57F287,
        "commands": [
            ("`$gtn <min> <max> [prize]`", "Start Guess The Number. DMs host secret number; reacts `➕`/`➖`."),
            ("`$gtnhint` / `$gtnclue`", "Host command: drop an automated parity or range clue in chat."),
            ("`$gtnstop`", "Stop an active GTN game."),
            ("`$blacktea [prize]` / `$wordbomb`", "BlackTea: 3 lives, 10s bomb timer! Type words containing prompt or explode!"),
            ("`$blackteastop`", "Stop an active BlackTea tournament."),
            ("`$roulette [prize]`", "Russian Roulette: 6 chambers, 1 bullet. Take turns pulling trigger until 1 survives!"),
            ("`$tictactoe @user [prize]` / `$ttt`", "Tic-Tac-Toe: 3x3 interactive button PvP duel!"),
            ("`$rps [@user] [prize]`", "Rock Paper Scissors: secret button choices vs player or bot!"),
            ("`$blackjack [prize]` / `$bj`", "Casino Blackjack 21: hit or stand against Dealer AI!"),
            ("`$scramble [prize]` / `$wordgw`", "Word Scramble: first to unscramble and type word wins!"),
            ("`$scramblestop`", "Stop an active Word Scramble game."),
            ("`$drop [delay_sec] [prize]`", "Reaction Drop: first person to click the glowing drop button wins!"),
            ("`$mathrace [difficulty] [prize]`", "Speed Math: first person to solve arithmetic problem wins!"),
            ("`$rumble [lobby_time] [prize]`", "Battle Royale: warriors join lobby and fight round-by-round until 1 champion survives!"),
            ("`$trivia [prize]`", "Trivia Race: first person to click correct answer button wins!"),
            ("`$rollgw [time] [prize]`", "High Roll Duel: highest 1-100 dice roller takes the prize!"),
            ("`$hack @user`", "Cyber Hack: animated simulated hacker infiltration on user!"),
            ("`$whisper @user <msg>`", "Secret Whisper: encrypted message only target can reveal with button!"),
            ("`$gunlock` / `$glock`", "Staff commands to quickly lock or restore channel permissions.")
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
            ("`$hi`", "Say hi to Kyoka Shop with an interactive response and quick buttons."),
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
    "economy": {
        "title": "💰 Virtual Economy & Casino",
        "description": "Full server economy system with banking, jobs, crimes, and casino gambling games.",
        "emoji": "💰",
        "color": 0xF1C40F,
        "commands": [
            ("`$balance [@user]` / `$bal`", "View your wallet, bank balance, and net worth."),
            ("`$daily`", "Claim your daily reward streak bonus (1,000 - 10,000 coins)."),
            ("`$work`", "Work a shift at an honest job to earn steady cash."),
            ("`$beg`", "Humbly beg the streets for spare change."),
            ("`$crime`", "Attempt a high-risk street heist for big rewards or hefty fines."),
            ("`$rob @user`", "Attempt to sneakily pickpocket coins from a member's wallet."),
            ("`$deposit <amount|all>` / `$dep`", "Safely store coins into your protected bank vault."),
            ("`$withdraw <amount|all>` / `$with`", "Withdraw coins from your bank vault into your wallet."),
            ("`$paycoins @user <amount>` / `$give`", "Transfer virtual coins from your wallet directly to another member."),
            ("`$slots <bet>`", "Spin the 3-reel casino slot machine for up to 10x jackpot payout! (Supports `inf` for owners)"),
            ("`$gamble <bet>` / `$bet`", "Roll 1-100 against the house in high-stakes double-or-nothing! (Supports `inf` for owners)"),
            ("`$baltop` / `$rich`", "View the top 10 richest server millionaires leaderboard."),
            ("`$infcash [@user]`", "Owner only: Grant unlimited infinite cash (`♾️`) for minigames & economy."),
            ("`$addcash @user <amount|inf>`", "Owner only: Add cash coins or infinite cash to a user's wallet."),
            ("`$setcash @user <amount|inf>`", "Owner only: Set a user's exact cash wallet balance.")
        ]
    },
    "utility": {
        "title": "🛠️ All-In-One Utility Suite",
        "description": "Essential server utilities: AFK system, sticky messages, snipe, math, QR codes, and profile cards.",
        "emoji": "🛠️",
        "color": 0x3498DB,
        "commands": [
            ("`$afk [reason]`", "Set an AFK status. Automatically announces AFK when mentioned and welcomes you back upon chatting!"),
            ("`$sticky <message>`", "Pin a persistent sticky message at the bottom of the channel that auto-reposts."),
            ("`$unsticky`", "Remove the sticky message from the current channel."),
            ("`$snipe`", "Recover and view the most recently deleted message in this channel."),
            ("`$editsnipe`", "Inspect the original before & after content of the most recently edited message."),
            ("`$calc <expression>`", "Safe arithmetic math calculator (e.g. `$calc (50 * 4) + 12`)."),
            ("`$qrcode <text/url>`", "Instantly generate a high-res scannable QR Code image."),
            ("`$roleinfo @role`", "Display detailed dossier, color, permissions, and member count for a role."),
            ("`$channelinfo [#channel]`", "Display channel creation date, category, topic, and telemetry."),
            ("`$servericon`", "Display full-resolution server icon."),
            ("`$serverbanner`", "Display full-resolution server banner."),
            ("`$userbanner [@user]`", "Display custom profile banner of a member.")
        ]
    },
    "automod": {
        "title": "🛡️ AutoMod Shield & Protection",
        "description": "Real-time automated server protection filters: anti-invite, anti-spam, anti-mass-mentions, and anti-caps.",
        "emoji": "🚨",
        "color": 0xE74C3C,
        "commands": [
            ("`$automod`", "View the current server AutoMod protection status dashboard."),
            ("`$automod anti_invites <on|off>`", "Toggle automatic deletion of unauthorized Discord invite links."),
            ("`$automod anti_mentions <on|off>`", "Toggle automatic deletion of messages with excessive mass mentions (>5)."),
            ("`$automod anti_spam <on|off>`", "Toggle automatic flood protection (>5 fast messages in 5 seconds)."),
            ("`$automod anti_caps <on|off>`", "Toggle automatic suppression of messages with >70% excessive caps.")
        ]
    },
    "owner": {
        "title": "👑 Management, Staff & No-Prefix",
        "description": "Bot control, staff team, live diagnostics, reload, and persistent no-prefix whitelist.",
        "emoji": "👑",
        "color": 0x57F287,
        "commands": [
            ("`$setsupport <url>`", "Dynamically change the official bot support server link."),
            ("`$support`", "Display official support server invite embed and button."),
            ("`$setavatar <url/upload>`", "Owner command: update bot avatar from URL or direct attachment."),
            ("`$setbanner <url/upload>`", "Owner command: update bot banner profile from URL or attachment."),
            ("`$setname <name>`", "Owner command: change bot username and update config."),
            ("`$botstaff add <@user|id> [role]`", "Appoint authorized bot staff (saved permanently to DB & config)."),
            ("`$botstaff remove <@user|id>`", "Remove an authorized bot staff member."),
            ("`$botstaff list`", "List all authorized bot staff and roles."),
            ("`$owner add <@user|id>`", "Add permanent root bot owner (saved permanently to DB & config)."),
            ("`$owner remove <@user|id>`", "Remove root bot owner."),
            ("`$owner list`", "List all root bot owners."),
            ("`$np add <@user|id>`", "Authorize a user to use all bot commands without prefix (saved permanently)."),
            ("`$np remove <@user|id>`", "Revoke no-prefix permissions for a user."),
            ("`$np list`", "List all authorized no-prefix members."),
            ("`$botstats`", "View system hardware diagnostics, CPU, RAM, and database latency."),
            ("`$checkperms` / `$perms`", "Perform full server permission audit to ensure zero missing permissions."),
            ("`$sync`", "Globally synchronize application slash commands to Discord."),
            ("`$reload <cog|all>`", "Hot-reload bot cogs without taking the bot offline."),
            ("`$infcash [@user]`", "Grant unlimited infinite cash for minigames & economy (Bot Owner Only)."),
            ("`$addcash @user <amount|inf>`", "Add cash coins or infinite cash to wallet (Bot Owner Only).")
        ]
    },
    "premium": {
        "title": "💎 Elite Premium System",
        "description": "Unlock double economy rewards, higher limits, priority perks, and server branding.",
        "emoji": "💎",
        "color": 0xF1C40F,
        "commands": [
            ("`$premium` / `$perks` / `$vip`", "View current server and personal premium status and active perks."),
            ("`$premium add <guild_id|user_id> [duration]`", "Owner/Staff: Grant premium (e.g. `$premium add 123 30d` or `$premium add 123 lifetime`)."),
            ("`$premium remove <guild_id|user_id>`", "Owner/Staff: Revoke premium status."),
            ("`$premium list`", "Owner/Staff: List all active premium subscriptions.")
        ]
    },
    "levels": {
        "title": "📊 Levels & Community XP",
        "description": "Active chatting experience engine, visual progress bars, and server leaderboards.",
        "emoji": "📊",
        "color": 0x5865F2,
        "commands": [
            ("`$rank [@user]` / `$lvl`", "Display your or another member's rank card, level, and visual progress bar."),
            ("`$leaderboard` / `$levels` / `$top`", "View the top 10 most active chatters in the server."),
            ("`$setxp @user <xp> [level]`", "Admin command to adjust member XP and level."),
            ("`$resetlevels`", "Admin command to reset server leveling progress.")
        ]
    },
    "autoresponder": {
        "title": "🤖 Auto-Responder & Triggers",
        "description": "Automated smart replies for community & Lal servers (rules, pricing, FAQs).",
        "emoji": "🤖",
        "color": 0x2ECC71,
        "commands": [
            ("`$ar`", "View auto-responder dashboard and supported template variables."),
            ("`$ar add <trigger> | <response>`", "Create a new auto-response trigger (e.g. `$ar add pricing | Check #shop!`)."),
            ("`$ar remove <trigger>`", "Delete an existing auto-responder trigger."),
            ("`$ar list`", "List all active custom triggers and previews in this server.")
        ]
    },
    "slash": {
        "title": "⚡ Application Slash Commands (/)",
        "description": "Native Discord slash command equivalents available across the entire server.",
        "emoji": "⚡",
        "color": 0x5865F2,
        "commands": [
            ("`/help`", "Open the clean interactive help desk modal & menu."),
            ("`/support`", "View official bot support server link and community resources."),
            ("`/balance`", "View your wallet, bank, and net worth balance."),
            ("`/daily`", "Claim your daily coin streak reward."),
            ("`/slots <bet>`", "Spin casino slot reels."),
            ("`/afk [reason]`", "Set your AFK status with return notices."),
            ("`/snipe`", "View the last deleted message in this channel."),
            ("`/qrcode <text>`", "Generate a QR Code."),
            ("`/calc <expr>`", "Evaluate a safe arithmetic expression."),
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
            ("`/gtn <min> <max> [prize]`", "Start Guess The Number game."),
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
            discord.SelectOption(label="Shop & Storefront", description="Store catalog, purchase panel, settings", emoji="🛒", value="shop"),
            discord.SelectOption(label="Product Management", description="Add, remove, list, and check product stock", emoji="📦", value="products"),
            discord.SelectOption(label="Purchases & Cart", description="Instant purchases and shopping cart", emoji="🛍️", value="purchases"),
            discord.SelectOption(label="Orders & Tracking", description="Lookup, live tracking, and receipts", emoji="📋", value="orders"),
            discord.SelectOption(label="Payment Gateways", description="Litecoin, PayPal, CashApp, and methods", emoji="💳", value="payments"),
            discord.SelectOption(label="Litecoin (LTC) Wallet", description="Taka-style wallet tracking and balance", emoji="🪙", value="ltc"),
            discord.SelectOption(label="Purchase Tickets", description="Private purchase tickets and controls", emoji="🎫", value="purchase_tickets"),
            discord.SelectOption(label="Customer Feedback", description="5-star ratings, reviews, and testimonials", emoji="⭐", value="feedback"),
            discord.SelectOption(label="Legit Counter", description="Legit vouch button and CheckT ledger", emoji="✨", value="legit"),
            discord.SelectOption(label="Deal Completed Logs", description="Green deal completion receipt logs", emoji="🤝", value="deal_logs"),
            discord.SelectOption(label="Customer CRM", description="Profiles, lifetime spend, leaderboard", emoji="👤", value="customer"),
            discord.SelectOption(label="Staff Order Tools", description="Claim, complete, deliver, revenue stats", emoji="🛡️", value="staff_tools"),
            discord.SelectOption(label="Shop Admin Controls", description="Branding, LTC config, coupons, TOS", emoji="⚙️", value="admin_tools"),
            discord.SelectOption(label="AI Store & Restock", description="24/7 AI Manager, stock scanner, answers", emoji="🤖", value="ai"),
            discord.SelectOption(label="Modular Tickets", description="Support categories, claims, transcripts", emoji="🎟️", value="tickets"),
            discord.SelectOption(label="Giveaways Suite", description="Persistent giveaways and rerolls", emoji="🎁", value="giveaways"),
            discord.SelectOption(label="Event Mini-Games", description="GTN, Scramble, Drop, Roulette, Blackjack", emoji="🎮", value="games"),
            discord.SelectOption(label="Economy & Casino", description="Balance, daily, jobs, rob, slots, baltop", emoji="💰", value="economy"),
            discord.SelectOption(label="Moderation Suite", description="Kick, ban, mute, warn, purge, lock", emoji="🚨", value="moderation"),
            discord.SelectOption(label="Utility Suite", description="AFK, sticky, snipe, qrcode, calc, banners", emoji="🛠️", value="utility"),
            discord.SelectOption(label="Welcomer", description="Welcome embeds, autoroles, leave logs", emoji="👋", value="welcomer"),
            discord.SelectOption(label="Slash Commands", description="Top Discord application slash commands", emoji="⚡", value="slash")
        ]
        super().__init__(
            placeholder="🏠 Home • Select Category",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]

        if choice == "home":
            latency = round(self.bot.latency * 1000)
            total_cmds = len(self.bot.commands) + len(self.bot.tree.get_commands())
            bot_name = self.bot.user.name if self.bot.user else "Kyoka Shop"

            embed = standard_embed(
                title=f"Hey, I'm {bot_name}",
                description=(
                    "> Built for our community — keeping your server safe, active, and effortlessly connected.\n\n"
                    f"• **Latency:** `{latency}ms`\n"
                    f"• **Prefix:** `{self.prefix}` | **Slash:** `/`\n"
                    f"• **Available Commands:** `{total_cmds}`\n\n"
                    "Select any category from the dropdown menu below to view full command references!"
                ),
                color=0x2B2D31
            )
            embed.set_footer(text=f"Requested by {self.author_name}")
            return await interaction.response.edit_message(embed=embed, view=self.view)

        module = MODULES.get(choice)
        if not module:
            return await interaction.response.send_message("Category not found.", ephemeral=True)

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

        # Add dynamic link buttons
        invite_url = "https://discord.com/oauth2/authorize?client_id=1505515188991033409&permissions=8&scope=bot%20applications.commands"
        if bot.user:
            invite_url = f"https://discord.com/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands"

        from utils.config_manager import get_support_server
        self.add_item(discord.ui.Button(label="Invite Kyoka Shop", style=discord.ButtonStyle.link, url=invite_url, emoji="🚀"))
        self.add_item(discord.ui.Button(label="Support Server", style=discord.ButtonStyle.link, url=get_support_server(), emoji="💬"))

class Help(commands.Cog):
    """Modern, minimalist, and ultra-aesthetic help desk modeled after top-tier community bots."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="help", aliases=["h"], help="Display the clean interactive help desk.")
    async def help_cmd(self, ctx: commands.Context, *, search_query: str = None):
        prefix = ctx.prefix or "$"

        if search_query:
            clean = search_query.lower().strip()
            # 1. Exact or partial match on category key
            for key, mod in MODULES.items():
                if clean == key or clean in key or key in clean:
                    desc = f"> {mod['description']}\n\n"
                    for cmd, cmd_desc in mod["commands"]:
                        desc += f"• **{cmd}**\n  └ *{cmd_desc}*\n"
                    embed = standard_embed(title=mod["title"], description=desc, color=mod["color"])
                    embed.set_footer(text=f"Category Help • Requested by {ctx.author.display_name}")
                    return await ctx.send(embed=embed)

            # 2. Search commands across all modules
            matches = []
            for key, mod in MODULES.items():
                for cmd, cmd_desc in mod["commands"]:
                    if clean in cmd.lower() or clean in cmd_desc.lower():
                        matches.append((cmd, cmd_desc, mod["title"]))

            if matches:
                desc = f"> Found **{len(matches)}** matching commands for `{search_query}`:\n\n"
                for cmd, cmd_desc, mod_title in matches[:12]:
                    desc += f"• **{cmd}** [{mod_title.split()[0]}]\n  └ *{cmd_desc}*\n"
                embed = standard_embed(
                    title=f"🔍 Command Search • \"{search_query}\"",
                    description=desc,
                    color=0x5865F2
                )
                embed.set_footer(text=f"Requested by {ctx.author.display_name}")
                return await ctx.send(embed=embed)

            return await ctx.send(embed=error_embed("No Matches", f"No command or category found matching `{search_query}`.\nRun `$help` to browse all categories."))

        latency = round(self.bot.latency * 1000)
        total_cmds = len(self.bot.commands) + len(self.bot.tree.get_commands())
        bot_name = self.bot.user.name if self.bot.user else "Kyoka Shop"

        embed = standard_embed(
            title=f"Hey, I'm {bot_name}",
            description=(
                "> Built for our community — keeping your server safe, active, and effortlessly connected.\n\n"
                f"• **Latency:** `{latency}ms`\n"
                f"• **Prefix:** `{prefix}` | **Slash:** `/`\n"
                f"• **Available Commands:** `{total_cmds}`\n\n"
                "Select a category below or search with `$help <command>`!"
            ),
            color=0x2B2D31
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")

        view = HelpView(self.bot, ctx.author.display_name, prefix)
        await ctx.send(embed=embed, view=view)

async def setup(bot: commands.Bot):
    bot.help_command = None
    await bot.add_cog(Help(bot))
