import discord
from discord.ext import commands
import random
import time
from typing import Optional
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db

WORK_SCENARIOS = [
    ("You worked as a Discord Moderator", 250, 600),
    ("You designed a custom Discord Bot banner", 400, 950),
    ("You traded crypto during a bull run", 500, 1200),
    ("You served coffee at Starbucks", 200, 450),
    ("You fixed a severe database bug on Render", 600, 1500),
    ("You streamed gaming on Twitch and got gifted subs", 350, 800),
    ("You mined 100 blocks of virtual Bitcoin", 300, 750),
    ("You reviewed and verified vouches in the marketplace", 400, 900)
]

CRIME_SUCCESS = [
    ("You hacked an ATM with a USB drive", 800, 2200),
    ("You pickpocketed a wealthy NFT investor", 600, 1800),
    ("You sold counterfeit Discord Nitro gift cards", 900, 2500),
    ("You successfully infiltrated a bank vault", 1200, 3500)
]

CRIME_FAILS = [
    ("The police caught you red-handed! You paid a fine of", 400, 900),
    ("An alarm tripped and guard dogs chased you! You dropped", 300, 800),
    ("You slipped on a security guard's donut and were fined", 250, 650)
]

SLOT_EMOJIS = ["🍒", "🍋", "🍇", "💎", "7️⃣", "🔔"]

class Economy(commands.Cog):
    """Complete Virtual Economy, Banking, Robbery, and Casino Suite."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ==========================================
    # 1. BALANCE & PROFILES
    # ==========================================
    @commands.command(name="balance", aliases=["bal", "wallet", "bank"], help="Check your or another member's bank and wallet balance.")
    async def balance(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        target = member or ctx.author
        eco = await db.get_economy(ctx.guild.id, target.id)

        wallet = eco["wallet"]
        bank = eco["bank"]
        bank_max = eco.get("bank_max", 10000)
        net_worth = wallet + bank
        streak = eco.get("streak", 0)

        embed = standard_embed(
            title=f"💳 Financial Dossier • {target.display_name}",
            description=(
                f"🪙 **Wallet:** `{wallet:,}` coins\n"
                f"🏦 **Bank:** `{bank:,}` / `{bank_max:,}` coins\n"
                f"💎 **Net Worth:** `{net_worth:,}` coins\n"
                f"🔥 **Daily Streak:** `{streak}` days"
            ),
            color=0xFEE75C
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=embed)

    # ==========================================
    # 2. DAILY REWARDS & STREAKS
    # ==========================================
    @commands.command(name="daily", aliases=["claim"], help="Claim your daily coins reward and build your streak!")
    async def daily(self, ctx: commands.Context):
        eco = await db.get_economy(ctx.guild.id, ctx.author.id)
        now = int(time.time())
        last = eco.get("last_daily", 0)
        cooldown = 86400  # 24 hours

        if now - last < cooldown:
            rem = cooldown - (now - last)
            hours, remainder = divmod(rem, 3600)
            minutes, seconds = divmod(remainder, 60)
            return await ctx.send(embed=error_embed(
                "Daily Cooldown",
                f"⏳ You have already claimed your daily reward!\nCome back in **{hours}h {minutes}m {seconds}s**."
            ))

        # Check if streak is preserved (claimed within 48 hours)
        streak = eco.get("streak", 0)
        if now - last < 172800 and last > 0:
            streak += 1
        else:
            streak = 1

        base_reward = 1000
        streak_bonus = min(streak * 150, 3000)
        total_reward = base_reward + streak_bonus

        new_wallet = eco["wallet"] + total_reward
        await db.update_economy(ctx.guild.id, ctx.author.id, wallet=new_wallet, last_daily=now, streak=streak)

        embed = standard_embed(
            title="🎁 Daily Reward Claimed!",
            description=(
                f"You received **+{total_reward:,} coins**!\n\n"
                f"• **Base Reward:** `1,000` coins\n"
                f"• **Streak Bonus:** `+{streak_bonus:,}` coins\n"
                f"• **Current Streak:** 🔥 `{streak}` day(s)\n"
                f"• **New Balance:** `{new_wallet:,}` coins"
            ),
            color=0x57F287
        )
        embed.set_footer(text="Claim every 24h to keep your multiplier going!")
        await ctx.send(embed=embed)

    # ==========================================
    # 3. WORK
    # ==========================================
    @commands.command(name="work", help="Work a shift and earn cash! (Cooldown: 30m)")
    async def work(self, ctx: commands.Context):
        eco = await db.get_economy(ctx.guild.id, ctx.author.id)
        now = int(time.time())
        last = eco.get("last_work", 0)
        cooldown = 1800  # 30 mins

        if now - last < cooldown:
            rem = cooldown - (now - last)
            mins, secs = divmod(rem, 60)
            return await ctx.send(embed=error_embed("Shift Cooldown", f"You are exhausted from your last shift! Rest for **{mins}m {secs}s**."))

        job_desc, min_earn, max_earn = random.choice(WORK_SCENARIOS)
        earned = random.randint(min_earn, max_earn)
        new_wallet = eco["wallet"] + earned

        await db.update_economy(ctx.guild.id, ctx.author.id, wallet=new_wallet, last_work=now)

        await ctx.send(embed=success_embed(
            "Shift Completed!",
            f"💼 {job_desc} and earned **+{earned:,} coins**!\n🪙 **Wallet:** `{new_wallet:,}` coins"
        ))

    # ==========================================
    # 4. BEG
    # ==========================================
    @commands.command(name="beg", help="Beg for spare change. (Cooldown: 2m)")
    async def beg(self, ctx: commands.Context):
        eco = await db.get_economy(ctx.guild.id, ctx.author.id)
        now = int(time.time())
        last = eco.get("last_crime", 0) # Share light cooldown

        if random.random() < 0.35:
            responses = [
                "A kind stranger felt bad for you and gave you",
                "You found some shiny coins in a fountain worth",
                "A tourist tossed a generous tip of"
            ]
            amt = random.randint(50, 250)
            new_wallet = eco["wallet"] + amt
            await db.update_economy(ctx.guild.id, ctx.author.id, wallet=new_wallet)
            await ctx.send(embed=standard_embed(
                title="🤲 Spare Change Found!",
                description=f"{random.choice(responses)} **+{amt} coins**!\n🪙 **Wallet:** `{new_wallet:,}` coins",
                color=0x57F287
            ))
        else:
            rejections = [
                "A bystander yelled: 'Get a real job!' and walked away.",
                "Someone threw an empty soda can at you.",
                "Nobody stopped to give you a single coin."
            ]
            await ctx.send(embed=info_embed("Denied", random.choice(rejections)))

    # ==========================================
    # 5. CRIME (HIGH RISK / HIGH REWARD)
    # ==========================================
    @commands.command(name="crime", help="Commit a high-stakes crime! (Cooldown: 1h)")
    async def crime(self, ctx: commands.Context):
        eco = await db.get_economy(ctx.guild.id, ctx.author.id)
        now = int(time.time())
        last = eco.get("last_crime", 0)
        cooldown = 3600  # 1 hour

        if now - last < cooldown:
            rem = cooldown - (now - last)
            mins, secs = divmod(rem, 60)
            return await ctx.send(embed=error_embed("Heat Warning", f"The police are actively searching for you! Lie low for **{mins}m {secs}s**."))

        if random.random() < 0.55:
            # Crime Success
            desc, min_earn, max_earn = random.choice(CRIME_SUCCESS)
            loot = random.randint(min_earn, max_earn)
            new_wallet = eco["wallet"] + loot
            await db.update_economy(ctx.guild.id, ctx.author.id, wallet=new_wallet, last_crime=now)
            await ctx.send(embed=standard_embed(
                title="🔫 Crime Succeeded!",
                description=f"🥷 {desc} and escaped with **+{loot:,} coins**!\n🪙 **Wallet:** `{new_wallet:,}` coins",
                color=0x57F287
            ))
        else:
            # Crime Failed
            desc, min_fine, max_fine = random.choice(CRIME_FAILS)
            fine = random.randint(min_fine, max_fine)
            new_wallet = max(0, eco["wallet"] - fine)
            await db.update_economy(ctx.guild.id, ctx.author.id, wallet=new_wallet, last_crime=now)
            await ctx.send(embed=error_embed(
                "Crime Busted!",
                f"🚨 {desc} **-{fine:,} coins** in fines!\n🪙 **Wallet:** `{new_wallet:,}` coins"
            ))

    # ==========================================
    # 6. ROB / STEAL
    # ==========================================
    @commands.command(name="rob", aliases=["steal"], help="Attempt to pickpocket another member's wallet! E.g. $rob @user")
    async def rob(self, ctx: commands.Context, target: discord.Member):
        if target.bot or target.id == ctx.author.id:
            return await ctx.send(embed=error_embed("Invalid Target", "You cannot rob bots or yourself!"))

        robber = await db.get_economy(ctx.guild.id, ctx.author.id)
        victim = await db.get_economy(ctx.guild.id, target.id)

        if robber["wallet"] < 250:
            return await ctx.send(embed=error_embed("Too Poor", "You need at least **250 coins** in your wallet to cover the police fine if you get caught!"))

        if victim["wallet"] < 500:
            return await ctx.send(embed=error_embed("Not Worth It", f"{target.display_name} has less than 500 coins in their wallet. Leave them alone!"))

        now = int(time.time())
        if now - robber.get("last_rob", 0) < 1800:
            rem = 1800 - (now - robber["last_rob"])
            mins, secs = divmod(rem, 60)
            return await ctx.send(embed=error_embed("Robbery Cooldown", f"You need to wait **{mins}m {secs}s** before robbing someone again!"))

        if random.random() < 0.50:
            # Success
            stolen = random.randint(int(victim["wallet"] * 0.20), int(victim["wallet"] * 0.50))
            new_robber = robber["wallet"] + stolen
            new_victim = victim["wallet"] - stolen

            await db.update_economy(ctx.guild.id, ctx.author.id, wallet=new_robber, last_rob=now)
            await db.update_economy(ctx.guild.id, target.id, wallet=new_victim)

            await ctx.send(embed=success_embed(
                "Robbery Successful!",
                f"🥷 You slipped your hand into {target.mention}'s pocket and stole **+{stolen:,} coins**!\n🪙 Your Wallet: `{new_robber:,}` coins"
            ))
        else:
            # Failed
            fine = random.randint(200, 500)
            new_robber = max(0, robber["wallet"] - fine)
            new_victim = victim["wallet"] + fine  # Victim gets the fine as compensation

            await db.update_economy(ctx.guild.id, ctx.author.id, wallet=new_robber, last_rob=now)
            await db.update_economy(ctx.guild.id, target.id, wallet=new_victim)

            await ctx.send(embed=error_embed(
                "Caught Red-Handed!",
                f"🚨 {target.mention} caught you trying to steal their wallet! You were fined **-{fine:,} coins** and had to give it to them as compensation!"
            ))

    # ==========================================
    # 7. DEPOSIT & WITHDRAW
    # ==========================================
    @commands.command(name="deposit", aliases=["dep"], help="Deposit money from your wallet to bank. E.g. $dep 500 or $dep all")
    async def deposit(self, ctx: commands.Context, amount: str):
        eco = await db.get_economy(ctx.guild.id, ctx.author.id)
        wallet = eco["wallet"]
        bank = eco["bank"]
        bank_max = eco.get("bank_max", 10000)

        space = max(0, bank_max - bank)
        if space <= 0:
            return await ctx.send(embed=error_embed("Bank Full", "Your bank account has reached maximum capacity!"))

        if amount.lower() in ["all", "max"]:
            to_dep = min(wallet, space)
        elif amount.isdigit():
            to_dep = int(amount)
        else:
            return await ctx.send(embed=error_embed("Invalid Amount", "Please specify a valid number or `all`."))

        if to_dep <= 0:
            return await ctx.send(embed=error_embed("Invalid Amount", "Amount must be at least 1 coin."))

        if to_dep > wallet:
            return await ctx.send(embed=error_embed("Insufficient Funds", f"You only have **{wallet:,} coins** in your wallet!"))

        if to_dep > space:
            to_dep = space

        new_wallet = wallet - to_dep
        new_bank = bank + to_dep

        await db.update_economy(ctx.guild.id, ctx.author.id, wallet=new_wallet, bank=new_bank)
        await ctx.send(embed=success_embed("Deposit Confirmed", f"🏦 Deposited **+{to_dep:,} coins** into your bank!\n🏦 Bank Balance: `{new_bank:,}` / `{bank_max:,}`"))

    @commands.command(name="withdraw", aliases=["with"], help="Withdraw money from your bank. E.g. $with 500 or $with all")
    async def withdraw(self, ctx: commands.Context, amount: str):
        eco = await db.get_economy(ctx.guild.id, ctx.author.id)
        wallet = eco["wallet"]
        bank = eco["bank"]

        if amount.lower() in ["all", "max"]:
            to_with = bank
        elif amount.isdigit():
            to_with = int(amount)
        else:
            return await ctx.send(embed=error_embed("Invalid Amount", "Please specify a valid number or `all`."))

        if to_with <= 0:
            return await ctx.send(embed=error_embed("Invalid Amount", "Amount must be at least 1 coin."))

        if to_with > bank:
            return await ctx.send(embed=error_embed("Insufficient Bank Balance", f"You only have **{bank:,} coins** stored in your bank!"))

        new_wallet = wallet + to_with
        new_bank = bank - to_with

        await db.update_economy(ctx.guild.id, ctx.author.id, wallet=new_wallet, bank=new_bank)
        await ctx.send(embed=success_embed("Withdrawal Confirmed", f"🏧 Withdrew **+{to_with:,} coins** from your bank!\n🪙 Wallet Balance: `{new_wallet:,}` coins"))

    # ==========================================
    # 8. PAY / TRANSFER
    # ==========================================
    @commands.command(name="pay", aliases=["transfer", "give"], help="Transfer coins to another member. E.g. $pay @user 500")
    async def pay(self, ctx: commands.Context, recipient: discord.Member, amount: int):
        if recipient.bot or recipient.id == ctx.author.id:
            return await ctx.send(embed=error_embed("Invalid Recipient", "Cannot transfer coins to bots or yourself!"))

        if amount <= 0:
            return await ctx.send(embed=error_embed("Invalid Amount", "Transfer amount must be at least 1 coin."))

        sender_eco = await db.get_economy(ctx.guild.id, ctx.author.id)
        if sender_eco["wallet"] < amount:
            return await ctx.send(embed=error_embed("Insufficient Funds", f"You only have **{sender_eco['wallet']:,} coins** in your wallet!"))

        recip_eco = await db.get_economy(ctx.guild.id, recipient.id)

        new_sender = sender_eco["wallet"] - amount
        new_recip = recip_eco["wallet"] + amount

        await db.update_economy(ctx.guild.id, ctx.author.id, wallet=new_sender)
        await db.update_economy(ctx.guild.id, recipient.id, wallet=new_recip)

        await ctx.send(embed=success_embed(
            "Transfer Complete",
            f"💸 {ctx.author.mention} sent **{amount:,} coins** to {recipient.mention}!\n🪙 Your remaining wallet: `{new_sender:,}` coins"
        ))

    # ==========================================
    # 9. CASINO SLOTS
    # ==========================================
    @commands.command(name="slots", aliases=["slotmachine"], help="Play the casino slot machine! E.g. $slots 100")
    async def slots(self, ctx: commands.Context, bet: int):
        if bet < 10:
            return await ctx.send(embed=error_embed("Minimum Bet", "Minimum slot machine bet is **10 coins**."))

        eco = await db.get_economy(ctx.guild.id, ctx.author.id)
        if eco["wallet"] < bet:
            return await ctx.send(embed=error_embed("Insufficient Funds", f"You only have **{eco['wallet']:,} coins** in your wallet!"))

        # Deduct bet upfront
        curr_wallet = eco["wallet"] - bet

        r1 = random.choice(SLOT_EMOJIS)
        r2 = random.choice(SLOT_EMOJIS)
        r3 = random.choice(SLOT_EMOJIS)

        winnings = 0
        if r1 == r2 == r3:
            if r1 == "7️⃣":
                multiplier = 10
                note = "🎉 **JACKPOT! TRIPLE SEVENS (10x)!** 🎉"
            elif r1 == "💎":
                multiplier = 7
                note = "💎 **DIAMOND JACKPOT (7x)!** 💎"
            else:
                multiplier = 5
                note = "✨ **TRIPLE MATCH (5x)!** ✨"
            winnings = bet * multiplier
        elif r1 == r2 or r2 == r3 or r1 == r3:
            multiplier = 2
            note = "🎊 **DOUBLE MATCH (2x)!** 🎊"
            winnings = bet * multiplier
        else:
            note = "💀 **No match. Better luck next spin!**"

        final_wallet = curr_wallet + winnings
        await db.update_economy(ctx.guild.id, ctx.author.id, wallet=final_wallet)

        embed = standard_embed(
            title="🎰 Zyath Casino Slots 🎰",
            description=(
                f"```\n"
                f"┌───────────┐\n"
                f"│ {r1} │ {r2} │ {r3} │\n"
                f"└───────────┘\n"
                f"```\n"
                f"{note}\n\n"
                f"• **Wager:** `{bet:,}` coins\n"
                f"• **Payout:** `+{winnings:,}` coins\n"
                f"• **New Balance:** `{final_wallet:,}` coins"
            ),
            color=0x57F287 if winnings > 0 else 0xED4245
        )
        embed.set_footer(text=f"Player: {ctx.author.display_name}")
        await ctx.send(embed=embed)

    # ==========================================
    # 10. CASINO GAMBLE / DICE DUEL
    # ==========================================
    @commands.command(name="gamble", aliases=["bet"], help="Roll the dice against the house (double or nothing)! E.g. $gamble 100")
    async def gamble(self, ctx: commands.Context, bet: int):
        if bet < 10:
            return await ctx.send(embed=error_embed("Minimum Bet", "Minimum bet is 10 coins."))

        eco = await db.get_economy(ctx.guild.id, ctx.author.id)
        if eco["wallet"] < bet:
            return await ctx.send(embed=error_embed("Insufficient Funds", f"You only have **{eco['wallet']:,} coins** in your wallet!"))

        player_roll = random.randint(1, 100)
        bot_roll = random.randint(1, 100)

        if player_roll > bot_roll:
            winnings = bet * 2
            new_wallet = eco["wallet"] + bet  # Net gain is +bet
            res_str = f"🏆 **YOU WIN!** You rolled a **{player_roll}** beating House's **{bot_roll}**!\n💰 Won: **+{bet:,} coins**!"
            col = 0x57F287
        elif player_roll < bot_roll:
            new_wallet = eco["wallet"] - bet
            res_str = f"💀 **HOUSE WINS!** House rolled a **{bot_roll}** beating your **{player_roll}**!\n💸 Lost: **-{bet:,} coins**."
            col = 0xED4245
        else:
            new_wallet = eco["wallet"]
            res_str = f"🤝 **TIE ROLL!** Both rolled **{player_roll}**! Bet returned."
            col = 0xFEE75C

        await db.update_economy(ctx.guild.id, ctx.author.id, wallet=new_wallet)

        embed = standard_embed(
            title="🎲 High-Stakes Gamble",
            description=f"{res_str}\n\n🪙 **Wallet:** `{new_wallet:,}` coins",
            color=col
        )
        await ctx.send(embed=embed)

    # ==========================================
    # 11. WEALTH LEADERBOARD
    # ==========================================
    @commands.command(name="baltop", aliases=["rich", "economylb"], help="View the richest server tycoons leaderboard!")
    async def baltop(self, ctx: commands.Context):
        lb = await db.get_economy_leaderboard(ctx.guild.id, limit=10)
        if not lb:
            return await ctx.send(embed=info_embed("Economy Leaderboard", "No financial records found in this server yet!"))

        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        desc = "🏆 **Top 10 Wealthiest Members:**\n\n"

        for idx, entry in enumerate(lb):
            icon = medals[idx] if idx < len(medals) else f"**#{idx+1}**"
            desc += f"{icon} <@{entry['user_id']}> — **{entry['total']:,}** coins (Wallet: `{entry['wallet']:,}` | Bank: `{entry['bank']:,}`)\n"

        embed = standard_embed(
            title=f"💰 Wealth Leaderboard • {ctx.guild.name}",
            description=desc,
            color=0xFEE75C
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))
