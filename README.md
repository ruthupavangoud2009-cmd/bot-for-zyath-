# ⚡ Zyath Bot — All-in-One Multi-Purpose Discord Bot

A state-of-the-art, feature-complete Discord bot built with **discord.py 2.x**, **aiosqlite**, and modern Discord UI components (Select Menus, Buttons, Modals).

---

## 🌟 Key Features

1. **🛡️ Complete Moderation Suite**
   - Ban, unban, kick, timeout/mute with custom durations (`10m`, `1h`, `7d`), unmute.
   - Warning system with user history and clear commands.
   - Bulk message purge with optional member filter.
   - Instant channel lock/unlock and slowmode management.
   - Nickname and role management.
   - Dedicated mod-log channel support (`$setmodlog`).

2. **🎫 Advanced & Customizable Ticket System**
   - Interactive dropdown panel with multi-category support:
     - 🛠️ General Support
     - 🛒 Buy / Order
     - 🤝 Middleman Service
     - ⚠️ Report / Appeal
   - Automated channel permissions per ticket (private to user and staff role).
   - In-ticket control panel:
     - 🔒 **Close Ticket** (archives access)
     - 🙋‍♂️ **Claim Ticket** (assigns handling staff member)
     - 📜 **HTML Transcript Generator** (interactive visual dark-themed transcript file)
     - ➕ **Add Member** & ➖ **Remove Member** (via modals)
     - 🔓 **Re-Open** & 🗑️ **Delete Ticket** (with 5-second countdown & archive)

3. **🎮 Guess The Number Mini-Game**
   - Start games with custom ranges: `$gtn <min> <max>` (e.g., `$gtn 1 5000`).
   - Bot automatically reacts:
     - Reacts `➕` if the guess is **lower** than the secret number (guess higher!).
     - Reacts `➖` if the guess is **higher** than the secret number (guess lower!).
   - Automatically crowns the **Winner** in an embed and **locks the channel**!

4. **🤝 Live Trade Logger & `$mercy` MM System**
   - Official Middleman (MM) transaction logger.
   - Command `$mercy` (with direct arguments or an interactive Discord Modal).
   - Generates unique Trade IDs (`#TRD-XXXX`).
   - Posts official live receipts in the vouch/trade channel with **`✅ Mark Completed`** and **`❌ Cancel`** buttons!

5. **⭐ Vouch Logger & Reputation**
   - `$vouch @user <1-5 stars> <comment>`
   - Calculates total vouches and average star ratings in real time.
   - Broadcasts verified vouches to the configured vouch channel.
   - `$vouches @user` profile view with history and breakdown.

6. **🛒 Shop System with 1-Click Ordering**
   - Clean storefront catalog with category filtering (`$shop`).
   - Integrated dropdown selector: selecting an item **automatically opens an Order Ticket** with the item name, price, and details pre-loaded for staff!
   - Admin management commands: `$shopadd`, `$shopremove`, `$shoplist`.

7. **👋 Welcomer & Autorole**
   - Rich welcome cards with avatar, member count, and account creation age.
   - Leave/Goodbye logger.
   - Automatic role assignment on member join (`$setautorole`).
   - Test simulator (`$welcometest`).

8. **🎉 Fun, `$say`, and Restricted `$spam`**
   - **`$say <message>`**: Immediately deletes your command message and speaks as the bot.
   - **`$sayembed <title> | <description>`**: Speaks in a clean styled embed.
   - **`$spam <count> @user [msg]`**: Restricted command (limited to authorized user IDs in `config.json`). Immediately deletes your trigger message, ghost mentions the target up to 100 times, and cleans up!
   - 8ball, coinflip, dice roll, playful roast, avatar lookup, userinfo, serverinfo, polls, ping.

9. **📂 Modern Module-Based Help Menu**
   - Interactive select dropdown menu to browse through all 9 modules and 53 commands with syntax and examples.

---

## ⚡ Hosting & Run Commands

If you are deploying on a cloud host (Render, Railway, Heroku, SquareCloud, Pterodactyl, or a VPS):

| Command Type | Exact Command |
|---|---|
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python main.py` |

---

## ⚡ No-Prefix System (`$np`)

Users authorized with **No-Prefix** can run every single bot command **without typing the `$` prefix** (e.g. just typing `help`, `shop`, `vouch @user 5 ...`, `mercy ...`, etc.).

- **Both Bot Owners** (`1521774957065928734` & `1505515188991033409`) have **Permanent No-Prefix** enabled!
- **Owner-Only Commands**:
  - `$np add @user` — Authorize a user to run all commands without prefix.
  - `$np remove @user` — Revoke a user's no-prefix access.
  - `$np list` — View all authorized no-prefix users.

---

## ⚡ Top 20 Slash (`/`) Commands
All commands work with prefix `$` (or no-prefix for authorized users), plus the **top 20 most important commands** are registered globally as Discord slash commands:

1. `/help` — Interactive module-based command center
2. `/shop` — Browse official store catalog
3. `/payment` — View accepted payment methods & wallet addresses
4. `/tos` — View shop warranty & refund policy
5. `/ticket` — Close active ticket or generate HTML transcript
6. `/ticketpanel` — Deploy support & order ticket panel
7. `/vouch` — Submit a reputation review with 1-5 stars
8. `/vouches` — View reputation rating for a user
9. `/mercy` — Log official Middleman transaction
10. `/trade` — Look up trade receipt by ID
11. `/createembed` — Open interactive modal to create custom embeds
12. `/gtn` — Start Guess The Number game in channel
13. `/say` — Speak as bot in channel
14. `/avatar` — View user avatar
15. `/userinfo` — View user Discord information
16. `/serverinfo` — View server statistics
17. `/purge` — Bulk delete messages
18. `/mute` — Timeout member
19. `/kick` — Kick member
20. `/ban` — Ban member

---

## 🚀 Quick Setup Guide

### 1. Requirements
- Python 3.10+ installed
- Git

### 2. Install Dependencies (Build Command)
```bash
pip install -r requirements.txt
```

### 3. Configure the Bot
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and paste your bot token:
   ```env
   DISCORD_TOKEN=your_bot_token_here
   PREFIX=$
   ```
3. Open `config.json` to verify:
   - `owner_ids`: `["1521774957065928734", "1505515188991033409"]`
   - `allowed_spam_users`

### 4. Enable Discord Privileged Intents
In the [Discord Developer Portal](https://discord.com/developers/applications):
- Select your Application -> **Bot** tab.
- Scroll down to **Privileged Gateway Intents** and enable:
  - ✅ **Presence Intent**
  - ✅ **Server Members Intent**
  - ✅ **Message Content Intent**
- Save changes.

### 5. Run the Bot (Start Command)
```bash
python main.py
```

---

## 📜 Full Command Reference

### 🛡️ Moderation
| Command | Description |
|---|---|
| `$kick @user [reason]` | Kick a user from the server |
| `$ban @user [reason]` | Ban a user from the server |
| `$unban <user_id> [reason]` | Unban a user by their ID |
| `$mute @user <time> [reason]` | Timeout user (e.g. `10m`, `1h`, `7d`) |
| `$unmute @user` | Remove timeout from user |
| `$warn @user [reason]` | Issue logged warning to member |
| `$warnings @user` | View member warnings |
| `$clearwarnings @user` | Clear member warnings |
| `$purge <amount> [@user]` | Bulk delete 1-100 messages |
| `$lock [channel] [reason]` | Lock channel chatting |
| `$unlock [channel]` | Unlock channel chatting |
| `$slowmode <seconds>` | Set channel slowmode |
| `$nick @user <nickname>` | Change member nickname |
| `$role <add/remove> @user @role` | Assign or remove role |
| `$setmodlog #channel` | Set moderation log channel |

### 🎫 Tickets
| Command | Description |
|---|---|
| `$ticketpanel [#channel]` | Send interactive ticket creation panel |
| `$setticketcategory <id>` | Set category under which tickets are created |
| `$setticketrole @role` | Set staff role pinged for tickets |
| `$setticketlogs #channel` | Set channel for ticket transcripts & logs |
| `$ticket close` | Close current ticket channel |
| `$ticket transcript` | Export HTML transcript of ticket |
| `$ticket add @user` | Add member to ticket |
| `$ticket remove @user` | Remove member from ticket |

### 🎁 Ultimate Giveaway Suite
| Command | Description |
|---|---|
| `$gstart <time> [winners] <prize>` | Start interactive giveaway with live timer & buttons (e.g. `$gstart 10m 1w Nitro` or `$gstart 1h 2 Nitro --role @VIP`) |
| `$gend <message_id>` | End an active giveaway early and pick winners immediately |
| `$greroll <message_id> [count]` | Reroll new winner(s) from previous entrants |
| `$glist` | List all active giveaways currently running in this server |
| `$gcancel <message_id>` | Cancel an active giveaway without picking winners |

### 🎮 GW Event Mini-Games Suite
| Command | Description |
|---|---|
| `$gtn <min> <max> [prize]` | Start GTN with prize tracking (reacts `➕` if lower, `➖` if higher, locks channel on win) |
| `$gtnhint` / `$gtnclue` | Host clue: drop automatic parity or range clue in chat |
| `$gtnstop` | Stop active GTN game |
| `$gtnstatus` | View active GTN range and guess count |
| `$blacktea [prize]` / `$wordbomb` | BlackTea: 3 lives, 10s bomb timer! Type words containing prompt or explode! |
| `$blackteastop` | Stop an active BlackTea tournament |
| `$roulette [prize]` | Russian Roulette: 6 chambers, 1 bullet. Take turns pulling trigger until 1 survives! |
| `$tictactoe @user [prize]` / `$ttt` | Tic-Tac-Toe: 3x3 interactive button PvP duel! |
| `$rps [@user] [prize]` | Rock Paper Scissors: secret button choices vs player or bot! |
| `$blackjack [prize]` / `$bj` | Casino Blackjack 21: hit or stand against Dealer AI! |
| `$scramble [prize]` / `$wordgw` | Word Scramble event: first person to unscramble & type word wins! |
| `$scramblestop` | Stop active Word Scramble game |
| `$drop [delay_sec] [prize]` / `$fastclick` | Fast Reaction Drop: countdown then glowing button drops — first click wins! |
| `$mathrace [easy\|med\|hard] [prize]` | Speed Math: first person to solve arithmetic problem wins! |
| `$mathstop` | Stop active Math Race |
| `$rumble [lobby_time] [prize]` | Battle Royale: warriors join lobby and fight round-by-round until 1 champion survives! |
| `$trivia [prize]` | Trivia Race: interactive 4-button trivia question — first correct click wins! |
| `$rollgw [time] [prize]` | High Roll Duel: highest 1-100 dice roller takes the prize! |
| `$hack @user` | Cyber Hack: animated simulated hacker infiltration on user! |
| `$whisper @user <msg>` | Secret Whisper: encrypted message only target can reveal with button! |
| `$gunlock` / `$glock` | Staff quick channel lock/unlock for giveaway event channels |

### 👑 Bot Management & Owner Suite
| Command | Description |
|---|---|
| `$setsupport <url>` | Dynamically update official bot support server link (Owner/Admin) |
| `$support` | Display official support server invite embed & direct button |
| `$setavatar [url/upload]` | **Owner-Only**: Update bot avatar from link or file upload |
| `$setbanner [url/upload]` | **Owner-Only**: Update bot banner profile from link or upload |
| `$setname <name>` | **Owner-Only**: Update bot username |
| `$np add @user` | Grant permanent no-prefix execution to a user |
| `$np remove @user` | Revoke no-prefix execution from a user |
| `$np list` | View all authorized no-prefix users |
| `$botstats` | View real-time hardware diagnostics (RAM, CPU, Latency, DB) |
| `$checkperms` | Comprehensive server permissions audit |
| `$reload <cog\|all>` | Hot reload cogs without downtime |
| `$sync` | Globally synchronize Discord slash command tree |

### 🤝 Middleman & Trades ($mercy)
| Command | Description |
|---|---|
| `$mercy` | Open interactive modal to create an MM receipt |
| `$mercy @buyer @seller <amount> <details>` | Directly post verified MM trade receipt |
| `$trade <trade_id>` | View status and info of trade |
| `$settradechannel #channel` | Set dedicated channel for live receipts |

### ⭐ Vouches
| Command | Description |
|---|---|
| `$vouch @user [1-5 stars] <comment>` | Submit a reputation vouch |
| `$vouches [@user]` | View user's vouches and rating profile |
| `$setvouchchannel #channel` | Set channel for public vouch logs |

### 🛒 Shop
| Command | Description |
|---|---|
| `$shop [category]` | View shop catalog with 1-click ticket order menu |
| `$shopadd <name> \| <price> \| [cat] \| [desc]` | Add product to shop |
| `$shopremove <item_id>` | Remove product from shop |
| `$shoplist` | Admin inventory overview with IDs |

### 👋 Welcomer
| Command | Description |
|---|---|
| `$setwelcome #channel` | Set channel for welcome cards |
| `$setleave #channel` | Set channel for leave logs |
| `$setautorole @role` | Automatically assign role to new joins |
| `$setwelcomemsg <message>` | Customize welcome template text |
| `$welcometest` | Test and preview welcome card |

### 🎉 Fun & Utility
| Command | Description |
|---|---|
| `$say <message>` | Bot repeats message and deletes your command |
| `$sayembed <title> \| <desc>` | Bot speaks in styled embed and deletes command |
| `$spam <count> @user [msg]` | Restricted ghost mention spam (up to 100x) and deletes all messages |
| `$setspamusers @user` | Authorize user to use `$spam` |
| `$removespamuser @user` | Revoke `$spam` permission |
| `$8ball <question>` | Magic 8ball answer |
| `$coinflip` | Flip coin |
| `$roll [max]` | Roll dice |
| `$roast [@user]` | Playful roast |
| `$avatar [@user]` | Display user avatar |
| `$userinfo [@user]` | View profile info |
| `$serverinfo` | View server stats |
| `$poll <question>` | Create community poll |
| `$ping` | Check bot latency |
| `$help` | Interactive module-based help menu |

---

### 💰 Virtual Economy & Casino
| Command | Description |
|---|---|
| `$balance [@user]` / `$bal` | Check wallet, bank vault, and net worth portfolio |
| `$daily` | Claim daily streak reward (1,000 - 10,000 coins) |
| `$work` | Work a shift to earn steady income |
| `$beg` | Beg on the streets for coins |
| `$crime` | High-stakes street heist for huge cash or fines |
| `$rob @user` | Attempt to pickpocket coins from another member |
| `$deposit <amount\|all>` | Store wallet coins in safe bank vault |
| `$withdraw <amount\|all>` | Withdraw coins from bank vault |
| `$pay @user <amount>` | Transfer coins to another member |
| `$slots <bet>` | Spin 3-reel casino slot machine for up to 10x jackpot |
| `$gamble <bet>` / `$bet` | High-stakes roll against the house |
| `$baltop` / `$rich` | Top 10 richest server leaderboard |

### 🛠️ All-In-One Utility Suite
| Command | Description |
|---|---|
| `$afk [reason]` | Set AFK status; notifies mentioners and welcomes you back |
| `$sticky <message>` | Pin persistent message to bottom of channel |
| `$unsticky` | Remove channel sticky message |
| `$snipe` | Recover and view most recently deleted message |
| `$editsnipe` | View before and after content of last edited message |
| `$calc <expression>` | Safe arithmetic calculator |
| `$qrcode <text/url>` | Generate scannable high-res QR code image |
| `$roleinfo @role` | Detailed role dossier, permissions, and member count |
| `$channelinfo [#channel]` | Channel creation date, topic, category, and stats |
| `$servericon` | Full-resolution server icon |
| `$serverbanner` | Full-resolution server banner |
| `$userbanner [@user]` | Profile banner image of member |

### 🛡️ AutoMod Shield & Protection
| Command | Description |
|---|---|
| `$automod` | View 24/7 security status dashboard |
| `$automod invite <on\|off>` | Toggle Anti-Invite link deletion filter |
| `$automod spam <on\|off>` | Toggle Anti-Spam flooding rate limiter |
| `$automod mentions <on\|off>` | Toggle Anti-Mass Mentions (>5) filter |
| `$automod caps <on\|off>` | Toggle Anti-Caps (>70%) filter |

### 🎁 Giveaways & Event Mini-Games
| Command | Description |
|---|---|
| `$gstart <time> [winners] <prize>` | Start persistent giveaway with live countdowns & role reqs |
| `$gend <msg_id>` / `$greroll <msg_id>` | End giveaway immediately or reroll new winner(s) |
| `$glist` / `$gcancel <msg_id>` | List running giveaways or cancel without drawing |
| `$gtn <min> <max> [prize]` | Guess The Number with secret DM & `➕`/`➖` feedback |
| `$gtnhint` / `$gtnstop` | Drop parity/range clues or stop GTN game |
| `$blacktea [prize]` / `$wordbomb` | BlackTea: 3 lives, 10s bomb timer word game |
| `$roulette [prize]` | Russian Roulette: 6 chambers, 1 bullet PvP elimination |
| `$tictactoe @user [prize]` | 3x3 interactive button PvP duel |
| `$rps [@user] [prize]` | Rock Paper Scissors secret button duel |
| `$blackjack [prize]` / `$bj` | Casino Blackjack 21 vs Dealer AI |
| `$scramble [prize]` | Word Scramble speed unscrambling |
| `$drop [delay] [prize]` | Reaction Drop: first to click glowing button |
| `$mathrace [diff] [prize]` | Speed arithmetic race |
| `$rumble [time] [prize]` | Battle Royale elimination tournament |
| `$trivia [prize]` | Interactive 4-choice trivia race |
| `$rollgw [time] [prize]` | High Roll dice duel |
| `$hack @user` | Simulated animated hacker infiltration |
| `$whisper @user <msg>` | Encrypted message revealable only by target |
| `$gunlock` / `$glock` | Lock or restore channel permissions |

### 👑 Owner, Bot Staff & No-Prefix (100% Persistent Database)
| Command | Description |
|---|---|
| `$botstaff add <@user\|id> [role]` | Appoint authorized bot staff member (saved in Supabase/SQLite DB) |
| `$botstaff remove <@user\|id>` | Revoke staff status from a user |
| `$botstaff list` | List all authorized bot staff and roles |
| `$np add <@user\|id>` | Whitelist member to execute all commands without prefix |
| `$np remove <@user\|id>` | Revoke permanent no-prefix access |
| `$np list` | View all authorized no-prefix users in database |
| `$setsupport <url>` | Dynamically update official support server link |
| `$support` | Display official support server invite card & button |
| `$setavatar <url/upload>` | Change bot profile avatar directly from Discord |
| `$setbanner <url/upload>` | Change bot banner profile directly from Discord |
| `$setname <name>` | Change bot username and save configuration |
| `$botstats` | View hardware diagnostics (CPU, RAM, DB latency) |
| `$sync` | Globally synchronize Discord application slash commands |
| `$reload <cog\|all>` | Hot-reload bot modules without downtime |

### 💎 Elite Premium Subscriptions (Servers & Users)
| Command | Description |
|---|---|
| `$premium` / `$perks` / `$vip` | View server & account premium status and active perks |
| `$premium add <id> [time] [tier]` | Owner/Staff: Grant premium (e.g. `$premium add 123 30d` or `lifetime`) |
| `$premium remove <id>` | Owner/Staff: Revoke premium status |
| `$premium list` | Owner/Staff: List all active premium subscriptions |

### 📊 Levels & Community XP (Lal & Active Servers)
| Command | Description |
|---|---|
| `$rank [@user]` / `$lvl` | Inspect level dossier, XP progress bar `[████░░] 60%`, and server rank |
| `$leaderboard` / `$levels` / `$top` | Top 10 most active chatters in the server |
| `$setxp @user <xp> [level]` | Admin: Adjust member XP and level |
| `$resetlevels` | Admin: Reset all server leveling and XP records |

### 🤖 Auto-Responder & Triggers
| Command | Description |
|---|---|
| `$ar` | View auto-responder dashboard and template placeholders |
| `$ar add <trigger> \| <response>` | Create automated reply (e.g. `$ar add pricing \| Check #shop!`) |
| `$ar remove <trigger>` | Delete custom auto-reply trigger |
| `$ar list` | List all active server triggers and response previews |

---

## 🔒 Security & Privacy
- All credentials should be stored in `.env`.
- Dual database support: seamlessly connects to **Supabase PostgreSQL** or **SQLite** with automated fallback.
- Database stores configuration, vouches, tickets, giveaways, economy, automod, bot staff, no-prefix whitelist, premium records, levels, and auto-responders locally with zero external telemetry.
