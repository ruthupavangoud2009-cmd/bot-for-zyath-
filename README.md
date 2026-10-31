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

### 🎮 Guess The Number
| Command | Description |
|---|---|
| `$gtn <min> <max>` | Start GTN game (reacts `➕` if lower, `➖` if higher, locks channel on win) |
| `$gtnstop` | Stop active GTN game |
| `$gtnstatus` | View active GTN range and guess count |

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

## 🔒 Security & Privacy
- All credentials should be stored in `.env`.
- Database (`zyath_bot.db`) stores configuration, vouches, and warnings locally without external tracking.
