import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import time
import re
from typing import Optional, Dict, Any, List
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.config_manager import check_is_owner
from cogs.economy import INF_CASH_AMOUNT

def is_inf_cash_str(prize_str: str) -> bool:
    """Detect if a prize specifies infinite cash/money/coins."""
    if not prize_str:
        return False
    lower = prize_str.lower().strip()
    if lower in ["inf", "infinite", "infinity", "♾️", "inf$", "$inf"]:
        return True
    patterns = [
        "inf cash", "infinite cash", "inf money", "infinite money",
        "inf coin", "infinite coin", "infinity cash", "infinity money",
        "inf balance", "infinite balance", "unlimited cash", "unlimited money",
        "inf eco", "infinite eco", "♾️ cash", "♾️ coin"
    ]
    return any(p in lower for p in patterns)


async def validate_minigame_prize(ctx: commands.Context, prize_str: str) -> bool:
    """Ensure that only bot owners can add infinite cash in minigames."""
    if is_inf_cash_str(prize_str):
        if not await check_is_owner(ctx.bot, ctx.author):
            await ctx.send(embed=error_embed(
                "Restricted Prize",
                "⛔ **Access Denied:** Only bot owners can add **infinite cash** in minigames!"
            ))
            return False
    return True

async def process_minigame_win(guild_id: int, winner: discord.Member, prize: str) -> Optional[str]:
    """Awards cash or infinite cash to winner if the prize specifies economy currency."""
    if not winner or not prize:
        return None
    try:
        from utils.database import db
        if is_inf_cash_str(prize):
            await db.update_economy(guild_id, winner.id, wallet=INF_CASH_AMOUNT, bank_max=INF_CASH_AMOUNT)
            return f"♾️ **Infinite Cash** (`{INF_CASH_AMOUNT:,}` coins) has been credited to {winner.mention}'s wallet!"

        m = re.search(r'(\d[\d,]*)\s*(?:coins?|cash|\$|credits?)', prize, re.IGNORECASE) or re.search(r'\$\s*(\d[\d,]*)', prize)
        if m:
            val_str = m.group(1).replace(",", "")
            if val_str.isdigit():
                val = int(val_str)
                if val > 0:
                    eco = await db.get_economy(guild_id, winner.id)
                    new_wallet = min(INF_CASH_AMOUNT, eco["wallet"] + val)
                    await db.update_economy(guild_id, winner.id, wallet=new_wallet)
                    return f"🪙 **+{val:,} coins** deposited directly into {winner.mention}'s wallet!"
    except Exception as e:
        print(f"[MINIGAME REWARD ERROR] {e}")
    return None


# --- Word List for Scramble ---
SCRAMBLE_WORDS = [
    "NITRO", "DISCORD", "GIVEAWAY", "KYOKA", "VALORANT", "MINECRAFT", "ROBLOX",
    "CYBERPUNK", "ETHEREUM", "BITCOIN", "REPUTATION", "MERCHANT", "CHAMPION",
    "COMMUNITY", "PLATINUM", "DIAMOND", "FORTNITE", "VOUCHES", "MIDDLEMAN",
    "TRANSACTION", "TICKETS", "SECURITY", "DEVELOPER", "PHANTOM", "LEGENDARY",
    "INVINCIBLE", "ULTIMATE", "BLOSSOM", "AVATAR", "DATABASE", "FIREWALL",
    "SPEEDRUN", "VICTORY", "WARRIOR", "GUARDIAN", "PREMIUM", "HEADSHOT",
    "JACKPOT", "TREASURE", "INFINITY", "SHERIFF", "DOMINATOR", "HYPERDRIVE"
]

# --- Trivia Questions Database ---
TRIVIA_QUESTIONS = [
    {
        "q": "What year was Discord officially released to the public?",
        "options": ["2014", "2015", "2016", "2017"],
        "answer": 1  # 2015
    },
    {
        "q": "What is the maximum character limit for a standard Discord message without Nitro?",
        "options": ["1000", "2000", "4000", "5000"],
        "answer": 1  # 2000
    },
    {
        "q": "Which game popularised the 100-player Battle Royale genre in 2017?",
        "options": ["Apex Legends", "PUBG", "Warzone", "Fortnite"],
        "answer": 1  # PUBG
    },
    {
        "q": "What was the very first cryptocurrency ever created?",
        "options": ["Ethereum", "Dogecoin", "Bitcoin", "Litecoin"],
        "answer": 2  # Bitcoin
    },
    {
        "q": "In Minecraft, what material is required to mine Obsidian?",
        "options": ["Iron Pickaxe", "Diamond Pickaxe", "Golden Pickaxe", "Netherite Sword"],
        "answer": 1  # Diamond Pickaxe
    },
    {
        "q": "What is the name of the main mascot of Discord?",
        "options": ["Clyde", "Wumpus", "Nelly", "Phred"],
        "answer": 1  # Wumpus
    },
    {
        "q": "How many bits are in one single byte?",
        "options": ["4", "8", "16", "32"],
        "answer": 1  # 8
    },
    {
        "q": "What programming language is this Discord bot primarily written in?",
        "options": ["JavaScript", "Python", "Rust", "C++"],
        "answer": 1  # Python
    },
    {
        "q": "In Grand Theft Auto V, how many playable protagonists are there?",
        "options": ["1", "2", "3", "4"],
        "answer": 2  # 3
    },
    {
        "q": "Which company originally created and owns GitHub?",
        "options": ["Google", "Microsoft", "Amazon", "Meta"],
        "answer": 1  # Microsoft
    }
]

# --- Rumble Elimination Sentences ---
RUMBLE_KILLS = [
    "⚔️ {p1} sliced {p2} with an enchanted diamond sword!",
    "💥 {p1} threw a frag grenade right under {p2}'s feet!",
    "🕳️ {p1} shoved {p2} straight into the bottomless void!",
    "⚡ {p1} summoned a bolt of lightning that struck {p2} down!",
    "🍌 {p1} planted a banana peel; {p2} slipped and fell out of the arena!",
    "🎯 {p1} hit a 360 no-scope sniper shot on {p2}!",
    "🥋 {p1} performed a high-flying roundhouse kick on {p2}!",
    "🚀 {p1} strapped a rocket to {p2} and launched them into orbit!",
    "🛡️ {p1} parried {p2}'s attack and counter-crushed them!",
    "🔥 {p1} used a flamethrower to turn {p2} into toast!"
]

BLACKTEA_PROMPTS = [
    "ing", "pro", "str", "tra", "ver", "ous", "ion", "pre", "con", "cat",
    "sta", "ble", "ent", "que", "ful", "ght", "tch", "est", "ast", "ani",
    "gen", "phy", "log", "sys", "com", "ter", "per", "dis", "res", "rec",
    "min", "mon", "man", "den", "tin", "ten", "par", "gra", "flo", "bla",
    "cra", "dra", "sha", "cha", "tha", "wha", "cre", "dre", "bre", "fre",
    "gre", "tre", "pri", "tri", "bri", "fri", "gri", "dri", "cro", "dro",
    "bro", "fro", "gro", "tro", "cru", "dru", "bru", "fru", "gru", "tru",
    "ack", "eck", "ick", "ock", "uck", "all", "ell", "ill", "oll", "ull",
    "and", "end", "ind", "ond", "und", "ang", "eng", "ong", "ung",
    "ank", "enk", "ink", "onk", "unk", "ant", "int", "ont", "unt",
    "art", "ert", "irt", "ort", "urt", "ash", "esh", "ish", "osh", "ush",
    "amp", "emp", "imp", "omp", "ump", "ate", "ete", "ite", "ote", "ute",
    "ive", "eve", "ave", "ove", "ure", "ire", "ore", "are", "ere", "ard"
]

class GWGames(commands.Cog):
    """Ultimate Giveaway Mini-Games Suite: GTN, BlackTea, Word Scramble, Fast Drop, Math Race, Battle Royale, Trivia, High Roll, Roulette, TicTacToe, RPS, Blackjack, Hack, Whisper."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Active GTN games per channel: {channel_id: {"target": int, "min": int, "max": int, "guesses": int, "starter": int, "prize": str}}
        self.active_gtn: Dict[int, Dict[str, Any]] = {}
        # Active Scramble games per channel: {channel_id: {"word": str, "scrambled": str, "prize": str, "starter": int, "hint_given": bool}}
        self.active_scramble: Dict[int, Dict[str, Any]] = {}
        # Active Math games per channel: {channel_id: {"answer": int, "equation": str, "prize": str, "starter": int}}
        self.active_math: Dict[int, Dict[str, Any]] = {}
        # Active BlackTea games per channel: {channel_id: BlackTeaGame}
        self.active_blacktea: Dict[int, Any] = {}
        # Active Roulette games per channel: {channel_id: Any}
        self.active_roulette: Dict[int, Any] = {}

    # Backward compatibility with existing cog name
    @property
    def active_games(self):
        return self.active_gtn

    async def _lock_channel(self, channel: discord.TextChannel, reason: str = "GW Event won"):
        """Auto lock channel after a game win."""
        try:
            overwrite = channel.overwrites_for(channel.guild.default_role)
            overwrite.send_messages = False
            await channel.set_permissions(channel.guild.default_role, overwrite=overwrite, reason=reason)
            return True
        except Exception:
            return False

    async def _unlock_channel(self, channel: discord.TextChannel):
        """Auto unlock channel."""
        try:
            overwrite = channel.overwrites_for(channel.guild.default_role)
            overwrite.send_messages = True
            await channel.set_permissions(channel.guild.default_role, overwrite=overwrite, reason="GW Event re-opened")
            return True
        except Exception:
            return False

    # ==========================================
    # 1. ENHANCED GUESS THE NUMBER (GTN)
    # ==========================================
    @commands.command(
        name="gtn",
        aliases=["guessthenumber", "guess"],
        help="Start a Guess The Number game. E.g. $gtn 1 1000 [prize]"
    )
    @commands.has_permissions(manage_channels=True)
    async def start_gtn(self, ctx: commands.Context, min_val: int = 1, max_val: int = 1000, *, prize: str = "Bragging Rights"):
        """Start GTN with +/- reactions, DM secret answer to host, prize support, and auto-lock on win."""
        if not await validate_minigame_prize(ctx, prize):
            return

        if min_val >= max_val:
            return await ctx.send(embed=error_embed("Invalid Range", "Minimum value must be less than maximum value."))
        if max_val - min_val < 5:
            return await ctx.send(embed=error_embed("Range Too Small", "Please choose a range with at least 5 numbers."))

        if ctx.channel.id in self.active_gtn:
            return await ctx.send(embed=error_embed("Game Already Active", "A GTN game is already running in this channel!\nUse `$gtnstop` to end it."))

        target_number = random.randint(min_val, max_val)
        self.active_gtn[ctx.channel.id] = {
            "target": target_number,
            "min": min_val,
            "max": max_val,
            "guesses": 0,
            "starter": ctx.author.id,
            "prize": prize.strip(),
            "highest_low": min_val,
            "lowest_high": max_val
        }

        # DM secret answer to host
        dm_status = ""
        try:
            host_embed = standard_embed(
                title="🎯 GTN • Secret Host Answer",
                description=(
                    f"You started a Guess The Number game in {ctx.channel.mention}!\n\n"
                    f"🔢 **Secret Target Number:** `{target_number}`\n"
                    f"📊 **Range:** Between `{min_val}` and `{max_val}`\n"
                    f"🎁 **Prize:** `{prize}`\n\n"
                    f"🤫 *Keep this number secret to ensure fair play!*"
                ),
                color=0x57F287
            )
            host_embed.set_footer(text=f"Server: {ctx.guild.name}")
            await ctx.author.send(embed=host_embed)
            dm_status = "\n📩 *Secret answer sent to host's DMs!*"
        except Exception:
            dm_status = "\n⚠️ *(Could not DM secret answer to host - please open your DMs)*"

        embed = standard_embed(
            title="🎮 Guess The Number Started!",
            description=(
                f"A new game of **Guess The Number** has begun!\n\n"
                f"🎁 **Prize:** **{prize}**\n"
                f"🔢 **Range:** Between `{min_val}` and `{max_val}`\n\n"
                f"➕ Bot reacts with `➕` if your guess is **LOWER** (guess higher!)\n"
                f"➖ Bot reacts with `➖` if your guess is **HIGHER** (guess lower!)\n\n"
                f"🏆 First person to guess correctly wins the prize and locks the channel!{dm_status}\n\n"
                f"💡 *Host can type `$gtnhint` to drop a clue!*"
            ),
            color=0x5865F2
        )
        embed.set_footer(text=f"Host: {ctx.author.display_name} • Good luck!")
        await ctx.send(embed=embed)

    @commands.command(name="gtnhint", aliases=["gtnclue", "ghint"], help="Host clue command to drop an automatic hint for active GTN game.")
    @commands.has_permissions(manage_channels=True)
    async def gtn_hint(self, ctx: commands.Context):
        """Drop a smart mathematical hint about the active GTN target."""
        game = self.active_gtn.get(ctx.channel.id)
        if not game:
            return await ctx.send(embed=error_embed("No Game", "No GTN game currently active in this channel."))

        target = game["target"]
        hints = [
            f"The secret number is **{'EVEN (divisible by 2)' if target % 2 == 0 else 'ODD'}**!",
            f"The secret number is **{'DIVISIBLE by 5' if target % 5 == 0 else 'NOT divisible by 5'}**!",
            f"The secret number is between **{game['highest_low']}** and **{game['lowest_high']}**!",
            f"The secret number is **{'greater than' if target > (game['min'] + game['max']) // 2 else 'less than or equal to'} { (game['min'] + game['max']) // 2 }**!"
        ]
        chosen = random.choice(hints)

        embed = standard_embed(
            title="💡 GTN Host Clue!",
            description=f"🔍 **Hint:** {chosen}",
            color=0xFEE75C
        )
        await ctx.send(embed=embed)

    @commands.command(name="gtnstop", aliases=["gstop", "endgtn", "gtnx"], help="Stop an active Guess The Number game in this channel.")
    @commands.has_permissions(manage_channels=True)
    async def stop_gtn(self, ctx: commands.Context):
        if ctx.channel.id not in self.active_gtn:
            return await ctx.send(embed=error_embed("No Active Game", "There is no Guess The Number game running in this channel."))

        game = self.active_gtn.pop(ctx.channel.id)
        await ctx.send(embed=info_embed("Game Stopped", f"The GTN game was stopped by {ctx.author.mention}.\nThe secret number was **{game['target']}**."))

    @commands.command(name="gtnstatus", aliases=["gstatus", "gtns", "ginfo"], help="Check current GTN game range and guess count.")
    async def status_gtn(self, ctx: commands.Context):
        if ctx.channel.id not in self.active_gtn:
            return await ctx.send(embed=info_embed("No Game Running", "No active Guess The Number game in this channel."))

        game = self.active_gtn[ctx.channel.id]
        embed = info_embed(
            "GTN Game In Progress",
            f"• **Prize:** `{game['prize']}`\n"
            f"• **Original Range:** `{game['min']}` to `{game['max']}`\n"
            f"• **Narrowed Range:** `{game['highest_low']}` to `{game['lowest_high']}`\n"
            f"• **Total Guesses Made:** `{game['guesses']}`"
        )
        await ctx.send(embed=embed)

    # ==========================================
    # 2. WORD SCRAMBLE GIVEAWAY GAME
    # ==========================================
    @commands.command(
        name="scramble",
        aliases=["wordscramble", "wordgw", "unscramble"],
        help="Start a Word Scramble giveaway game. E.g. $scramble [prize]"
    )
    @commands.has_permissions(manage_channels=True)
    async def start_scramble(self, ctx: commands.Context, *, prize: str = "Discord Nitro"):
        """Scramble a word; first user to unscramble and type it wins!"""
        if not await validate_minigame_prize(ctx, prize):
            return

        if ctx.channel.id in self.active_scramble:
            return await ctx.send(embed=error_embed("Game Active", "A Word Scramble game is already running in this channel!\nUse `$scramblestop` to end it."))

        word = random.choice(SCRAMBLE_WORDS)
        letters = list(word)
        # Ensure scrambled is not identical to word
        for _ in range(10):
            random.shuffle(letters)
            scrambled = " ".join(letters)
            if scrambled.replace(" ", "") != word:
                break

        self.active_scramble[ctx.channel.id] = {
            "word": word,
            "scrambled": scrambled,
            "prize": prize.strip(),
            "starter": ctx.author.id,
            "start_time": time.time(),
            "hint_given": False
        }

        embed = standard_embed(
            title="🧩 Word Scramble GW!",
            description=(
                f"Unscramble the letters below to win the prize!\n\n"
                f"🔀 **Scrambled Word:**\n# `{scrambled}`\n\n"
                f"🎁 **Prize:** **{prize}**\n"
                f"👑 **Hosted by:** {ctx.author.mention}\n\n"
                f"⚡ First person to type the correct word in chat wins and locks the channel!"
            ),
            color=0xFEE75C
        )
        embed.set_footer(text=f"Total letters: {len(word)} • Type your answer directly!")
        await ctx.send(embed=embed)

    @commands.command(name="scramblestop", aliases=["stopscramble", "endscramble"], help="Stop an active Word Scramble game.")
    @commands.has_permissions(manage_channels=True)
    async def stop_scramble(self, ctx: commands.Context):
        if ctx.channel.id not in self.active_scramble:
            return await ctx.send(embed=error_embed("No Game", "No Word Scramble game running in this channel."))
        game = self.active_scramble.pop(ctx.channel.id)
        await ctx.send(embed=info_embed("Game Ended", f"Word Scramble was ended by {ctx.author.mention}.\nThe word was **{game['word']}**!"))

    # ==========================================
    # 3. FAST REACTION DROP / FAST CLICK GW
    # ==========================================
    @commands.command(
        name="drop",
        aliases=["fastclick", "reactiongw", "quickdrop"],
        help="Drop a fast-reaction claim button. E.g. $drop 5 Nitro Basic or $drop Nitro"
    )
    @commands.has_permissions(manage_channels=True)
    async def reaction_drop(self, ctx: commands.Context, *args):
        """Drop a button that users race to click. First clicker wins!"""
        args_list = list(args)
        delay_sec = 3
        if args_list and args_list[0].isdigit():
            delay_sec = max(1, min(30, int(args_list.pop(0))))

        prize = " ".join(args_list).strip() or "Discord Nitro"
        if not await validate_minigame_prize(ctx, prize):
            return

        prep_msg = await ctx.send(embed=standard_embed(
            title="⚡ Reaction Drop Incoming!",
            description=(
                f"🎁 **Prize:** **{prize}**\n\n"
                f"⏳ The claim button will drop in **{delay_sec} seconds**...\n"
                f"Get your fingers ready!"
            ),
            color=0x5865F2
        ))

        await asyncio.sleep(delay_sec)

        # Drop view
        start_time = time.time()
        winner_claimed = False

        class DropView(discord.ui.View):
            def __init__(self, parent_cog):
                super().__init__(timeout=60)
                self.parent_cog = parent_cog

            @discord.ui.button(label="🎁 CLAIM PRIZE NOW!", style=discord.ButtonStyle.success, emoji="⚡")
            async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
                nonlocal winner_claimed
                if winner_claimed:
                    return await interaction.response.send_message("❌ Someone already claimed this drop a fraction of a second ahead of you!", ephemeral=True)

                winner_claimed = True
                elapsed = round(time.time() - start_time, 3)

                button.disabled = True
                button.label = f"Claimed by {interaction.user.name} ({elapsed}s)!"
                button.style = discord.ButtonStyle.secondary
                await interaction.response.edit_message(view=self)

                # Lock channel
                await self.parent_cog._lock_channel(interaction.channel, f"Drop won by {interaction.user}")
                reward_msg = await process_minigame_win(interaction.guild_id, interaction.user, prize)
                reward_str = f"\n💎 **Auto-Reward:** {reward_msg}" if reward_msg else ""

                win_embed = standard_embed(
                    title="⚡ REACTION DROP CLAIMED! ⚡",
                    description=(
                        f"🎉 Congratulations {interaction.user.mention}!\n\n"
                        f"🎁 **Prize Won:** **{prize}**{reward_str}\n"
                        f"⚡ **Reaction Speed:** `{elapsed} seconds`\n"
                        f"👑 **Hosted by:** {ctx.author.mention}\n\n"
                        f"🔒 **Channel Status:** Auto-locked to prevent spam!"
                    ),
                    color=0x57F287,
                    thumbnail=interaction.user.display_avatar.url
                )
                win_embed.set_footer(text=f"Winner: {interaction.user} • Blazing Fast!")
                await interaction.channel.send(content=f"👑 {interaction.user.mention}", embed=win_embed)

                # DM winner
                try:
                    dm_emb = standard_embed(
                        title="🎁 Reaction Drop Victory!",
                        description=f"You won **{prize}** in **{ctx.guild.name}** with a reaction time of `{elapsed}s`!\nContact {ctx.author.mention} to claim.",
                        color=0x57F287
                    )
                    await interaction.user.send(embed=dm_emb)
                except Exception:
                    pass

        drop_embed = standard_embed(
            title="🔥 DROP IS LIVE — CLICK FIRST TO WIN! 🔥",
            description=f"🎁 **Prize:** **{prize}**\n\n👇 **FIRST TO CLICK THE BUTTON WINS!**",
            color=0xED4245
        )
        await prep_msg.edit(embed=drop_embed, view=DropView(self))

    # ==========================================
    # 4. MATH RACE GIVEAWAY GAME
    # ==========================================
    @commands.command(
        name="mathrace",
        aliases=["mathgw", "quickmath", "speedmath"],
        help="Start a Speed Math race. E.g. $mathrace easy Nitro or $mathrace hard $5"
    )
    @commands.has_permissions(manage_channels=True)
    async def start_math(self, ctx: commands.Context, difficulty: str = "easy", *, prize: str = "Discord Nitro"):
        """Mental math challenge; first to type correct answer wins and locks channel."""
        if not await validate_minigame_prize(ctx, prize):
            return

        if ctx.channel.id in self.active_math:
            return await ctx.send(embed=error_embed("Game Active", "A Math Race is already active in this channel!\nUse `$mathstop` to end it."))

        diff = difficulty.lower().strip()
        if diff == "hard":
            a = random.randint(15, 50)
            b = random.randint(11, 25)
            c = random.randint(20, 100)
            eq = f"({a} * {b}) - {c}"
            ans = (a * b) - c
        elif diff == "medium" or diff == "med":
            a = random.randint(12, 35)
            b = random.randint(5, 15)
            c = random.randint(10, 50)
            eq = f"{a} * {b} + {c}"
            ans = a * b + c
        else:
            diff = "easy"
            a = random.randint(25, 95)
            b = random.randint(15, 85)
            eq = f"{a} + {b}"
            ans = a + b

        self.active_math[ctx.channel.id] = {
            "answer": ans,
            "equation": eq,
            "prize": prize.strip(),
            "starter": ctx.author.id,
            "difficulty": diff.capitalize()
        }

        embed = standard_embed(
            title="🧮 Math Race GW!",
            description=(
                f"Solve the math problem below to win the prize!\n\n"
                f"# `{eq} = ?`\n\n"
                f"🎁 **Prize:** **{prize}**\n"
                f"📊 **Difficulty:** `{diff.capitalize()}`\n"
                f"👑 **Hosted by:** {ctx.author.mention}\n\n"
                f"⚡ First person to type the correct number in chat wins!"
            ),
            color=0x5865F2
        )
        embed.set_footer(text="Type only the number answer!")
        await ctx.send(embed=embed)

    @commands.command(name="mathstop", aliases=["stopmath"], help="Stop an active Math Race game.")
    @commands.has_permissions(manage_channels=True)
    async def stop_math(self, ctx: commands.Context):
        if ctx.channel.id not in self.active_math:
            return await ctx.send(embed=error_embed("No Game", "No Math Race active in this channel."))
        game = self.active_math.pop(ctx.channel.id)
        await ctx.send(embed=info_embed("Game Stopped", f"Math Race ended by {ctx.author.mention}.\nThe correct answer was **{game['answer']}**!"))

    # ==========================================
    # 5. RUMBLE / BATTLE ROYALE GW
    # ==========================================
    @commands.command(
        name="rumble",
        aliases=["battleroyale", "br", "rumblegw"],
        help="Start a Rumble Battle Royale. E.g. $rumble 30s Nitro or $rumble Nitro"
    )
    @commands.has_permissions(manage_channels=True)
    async def start_rumble(self, ctx: commands.Context, *args):
        """Host a Battle Royale lobby. Players join with button; simulated rounds eliminate until 1 champion remains!"""
        args_list = list(args)
        lobby_time = 30
        if args_list and args_list[0].endswith("s") and args_list[0][:-1].isdigit():
            lobby_time = max(10, min(120, int(args_list.pop(0)[:-1])))
        elif args_list and args_list[0].isdigit():
            lobby_time = max(10, min(120, int(args_list.pop(0))))

        prize = " ".join(args_list).strip() or "Discord Nitro"
        if not await validate_minigame_prize(ctx, prize):
            return

        players = set()
        players.add(ctx.author)  # Host joins by default

        end_lobby = int(time.time()) + lobby_time

        class RumbleLobbyView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=lobby_time + 5)
                self.join_btn = discord.ui.Button(label="Join Battle (1)", style=discord.ButtonStyle.danger, emoji="⚔️")
                self.join_btn.callback = self.join_callback
                self.add_item(self.join_btn)

            async def join_callback(self, interaction: discord.Interaction):
                if interaction.user in players:
                    return await interaction.response.send_message("🛡️ You are already registered in the battle arena!", ephemeral=True)
                players.add(interaction.user)
                self.join_btn.label = f"Join Battle ({len(players)})"
                await interaction.response.edit_message(view=self)

        embed = standard_embed(
            title="⚔️ RUMBLE BATTLE ROYALE! ⚔️",
            description=(
                f"Enter the arena! Last player standing wins the prize!\n\n"
                f"🎁 **Prize:** **{prize}**\n"
                f"👑 **Hosted by:** {ctx.author.mention}\n"
                f"⏰ **Lobby Closes:** <t:{end_lobby}:R>\n\n"
                f"👇 Click **Join Battle** below to step into the fight!"
            ),
            color=0xED4245
        )
        embed.set_footer(text=f"Total warriors ready: {len(players)}")

        view = RumbleLobbyView()
        msg = await ctx.send(embed=embed, view=view)

        await asyncio.sleep(lobby_time)

        if len(players) < 2:
            cancel_emb = error_embed(
                "Rumble Cancelled",
                f"At least **2 players** are required to start a Rumble Battle Royale! Only {len(players)} entered."
            )
            return await msg.edit(embed=cancel_emb, view=None)

        # Start Elimination Rounds
        arena = list(players)
        round_num = 1
        await msg.edit(view=None)

        start_ann = standard_embed(
            title="⚔️ THE RUMBLE HAS BEGUN! ⚔️",
            description=f"**{len(arena)} Warriors** entered the arena!\nMay the strongest survive!",
            color=0xED4245
        )
        battle_msg = await ctx.send(embed=start_ann)
        await asyncio.sleep(3)

        while len(arena) > 1:
            # Pick a killer and a victim
            p1, p2 = random.sample(arena, 2)
            arena.remove(p2)

            kill_template = random.choice(RUMBLE_KILLS)
            kill_text = kill_template.format(p1=f"**{p1.display_name}**", p2=f"~~{p2.display_name}~~")

            round_emb = standard_embed(
                title=f"⚔️ Rumble • Round {round_num} (Remaining: {len(arena)})",
                description=f"{kill_text}\n\n💀 **Eliminated:** {p2.mention}",
                color=0xE67E22
            )
            round_emb.set_footer(text=f"{len(arena)} survivors remaining in the arena!")
            try:
                await battle_msg.edit(embed=round_emb)
            except Exception:
                pass

            round_num += 1
            await asyncio.sleep(3.5)

        # Final Champion!
        champion = arena[0]
        await self._lock_channel(ctx.channel, f"Rumble won by {champion}")
        reward_msg = await process_minigame_win(ctx.guild.id, champion, prize)
        reward_str = f"\n💎 **Auto-Reward:** {reward_msg}" if reward_msg else ""

        champ_embed = standard_embed(
            title="👑 RUMBLE CHAMPION CROWNED! 👑",
            description=(
                f"🎉 Hail to the ultimate victor: {champion.mention}!\n\n"
                f"🏆 **Title:** Rumble Arena Champion\n"
                f"🎁 **Prize Won:** **{prize}**{reward_str}\n"
                f"⚔️ **Warriors Defeated:** `{len(players) - 1}`\n"
                f"👑 **Hosted by:** {ctx.author.mention}\n\n"
                f"🔒 **Channel Status:** Automatically locked!"
            ),
            color=0x57F287,
            thumbnail=champion.display_avatar.url
        )
        champ_embed.set_footer(text=f"Champion: {champion} • GG!")

        await ctx.send(content=f"🏆 {champion.mention} **VICTORY ROYALE!**", embed=champ_embed)

        try:
            dm_emb = standard_embed(
                title="👑 Rumble Victory!",
                description=f"You survived the Rumble in **{ctx.guild.name}** and won **{prize}**!\nContact {ctx.author.mention} to claim your reward.",
                color=0xFEE75C
            )
            await champion.send(embed=dm_emb)
        except Exception:
            pass

    # ==========================================
    # 6. TRIVIA RACE GW
    # ==========================================
    @commands.command(
        name="trivia",
        aliases=["triviagw", "quizgw"],
        help="Start a Trivia Race with 4 answer buttons. E.g. $trivia [prize]"
    )
    @commands.has_permissions(manage_channels=True)
    async def start_trivia(self, ctx: commands.Context, *, prize: str = "Discord Nitro"):
        """Drop a trivia question with buttons. First correct click wins prize and locks channel!"""
        if not await validate_minigame_prize(ctx, prize):
            return

        item = random.choice(TRIVIA_QUESTIONS)
        question = item["q"]
        options = item["options"]
        correct_idx = item["answer"]
        winner_claimed = False

        parent_cog = self

        class TriviaView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                labels = ["A", "B", "C", "D"]
                for i, opt in enumerate(options):
                    btn = discord.ui.Button(
                        label=f"{labels[i]}: {opt}",
                        style=discord.ButtonStyle.primary,
                        custom_id=f"trivia_opt_{i}"
                    )
                    btn.callback = self.make_callback(i)
                    self.add_item(btn)

            def make_callback(self, chosen_index):
                async def cb(interaction: discord.Interaction):
                    nonlocal winner_claimed
                    if winner_claimed:
                        return await interaction.response.send_message("❌ This trivia has already been won!", ephemeral=True)

                    if chosen_index != correct_idx:
                        return await interaction.response.send_message("❌ Incorrect answer! Better luck next time!", ephemeral=True)

                    winner_claimed = True
                    # Disable all buttons
                    for child in self.children:
                        child.disabled = True
                        if isinstance(child, discord.ui.Button) and child.custom_id == f"trivia_opt_{correct_idx}":
                            child.style = discord.ButtonStyle.success

                    await interaction.response.edit_message(view=self)
                    await parent_cog._lock_channel(interaction.channel, f"Trivia won by {interaction.user}")
                    reward_msg = await process_minigame_win(interaction.guild_id, interaction.user, prize)
                    reward_str = f"\n💎 **Auto-Reward:** {reward_msg}" if reward_msg else ""

                    win_embed = standard_embed(
                        title="🧠 TRIVIA WINNER! 🧠",
                        description=(
                            f"🎉 Congratulations {interaction.user.mention}!\n\n"
                            f"❓ **Question:** *{question}*\n"
                            f"✅ **Correct Answer:** **{options[correct_idx]}**\n\n"
                            f"🎁 **Prize Won:** **{prize}**{reward_str}\n"
                            f"👑 **Hosted by:** {ctx.author.mention}\n\n"
                            f"🔒 **Channel Status:** Automatically locked!"
                        ),
                        color=0x57F287,
                        thumbnail=interaction.user.display_avatar.url
                    )
                    win_embed.set_footer(text=f"Winner: {interaction.user} • Big Brain!")
                    await interaction.channel.send(content=f"👑 {interaction.user.mention}", embed=win_embed)

                return cb

        embed = standard_embed(
            title="🧠 Trivia Race GW!",
            description=(
                f"First person to click the correct answer wins!\n\n"
                f"❓ **Question:**\n# {question}\n\n"
                f"🎁 **Prize:** **{prize}**\n"
                f"👑 **Hosted by:** {ctx.author.mention}\n\n"
                f"👇 Choose wisely below:"
            ),
            color=0x5865F2
        )
        embed.set_footer(text="Click only once • Fast fingers win!")
        await ctx.send(embed=embed, view=TriviaView())

    # ==========================================
    # 7. HIGH ROLL / ROLL DUEL GW
    # ==========================================
    @commands.command(
        name="rollgw",
        aliases=["dicegw", "highroll"],
        help="High Roll contest. E.g. $rollgw 30s Nitro or $rollgw Nitro"
    )
    @commands.has_permissions(manage_channels=True)
    async def start_roll_gw(self, ctx: commands.Context, *args):
        """Roll contest; players click to roll 1-100. Highest roll wins!"""
        args_list = list(args)
        roll_time = 30
        if args_list and args_list[0].endswith("s") and args_list[0][:-1].isdigit():
            roll_time = max(10, min(60, int(args_list.pop(0)[:-1])))

        prize = " ".join(args_list).strip() or "Discord Nitro"
        if not await validate_minigame_prize(ctx, prize):
            return

        rolls: Dict[int, tuple[discord.User, int]] = {}
        end_time = int(time.time()) + roll_time

        class RollView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=roll_time + 5)

            @discord.ui.button(label="🎲 Roll Dice (1-100)", style=discord.ButtonStyle.primary)
            async def roll_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id in rolls:
                    val = rolls[interaction.user.id][1]
                    return await interaction.response.send_message(f"🎲 You already rolled a **{val}**!", ephemeral=True)

                rolled = random.randint(1, 100)
                rolls[interaction.user.id] = (interaction.user, rolled)

                await interaction.response.send_message(f"🎲 You rolled a **{rolled}**/100! Good luck!", ephemeral=True)

        embed = standard_embed(
            title="🎲 High Roll Contest!",
            description=(
                f"Click the button below to roll a 100-sided dice!\n"
                f"The highest roll when the timer expires wins!\n\n"
                f"🎁 **Prize:** **{prize}**\n"
                f"⏰ **Rolling Closes:** <t:{end_time}:R>\n"
                f"👑 **Hosted by:** {ctx.author.mention}"
            ),
            color=0x9B59B6
        )
        msg = await ctx.send(embed=embed, view=RollView())
        await asyncio.sleep(roll_time)

        if not rolls:
            cancel_emb = error_embed("Roll Ended", "Nobody rolled, so no winner was chosen.")
            return await msg.edit(embed=cancel_emb, view=None)

        sorted_rolls = sorted(rolls.values(), key=lambda x: x[1], reverse=True)
        winner_user, win_score = sorted_rolls[0]

        await self._lock_channel(ctx.channel, f"High roll won by {winner_user}")
        reward_msg = await process_minigame_win(ctx.guild.id, winner_user, prize)
        reward_str = f"\n💎 **Auto-Reward:** {reward_msg}" if reward_msg else ""

        leaderboard_str = "\n".join([f"• {u.mention}: **{s}**" for u, s in sorted_rolls[:5]])

        res_embed = standard_embed(
            title="🎲 HIGH ROLL WINNER! 🎲",
            description=(
                f"🎉 Congratulations {winner_user.mention} with a roll of **{win_score}**!\n\n"
                f"🎁 **Prize Won:** **{prize}**{reward_str}\n"
                f"📊 **Top 5 Rollers:**\n{leaderboard_str}\n\n"
                f"🔒 **Channel Status:** Automatically locked!"
            ),
            color=0x57F287,
            thumbnail=winner_user.display_avatar.url
        )
        res_embed.set_footer(text=f"Winner: {winner_user} • Total rolls: {len(rolls)}")
        await msg.edit(view=None)
        await ctx.send(content=f"👑 {winner_user.mention}", embed=res_embed)

    # ==========================================
    # 8. STAFF CHANNEL CONTROLS
    # ==========================================
    @commands.command(name="gunlock", aliases=["gtnunlock", "gwunlock"], help="Quickly unlock the current channel after a game.")
    @commands.has_permissions(manage_channels=True)
    async def unlock_cmd(self, ctx: commands.Context):
        """Staff command to re-open channel chatting."""
        success = await self._unlock_channel(ctx.channel)
        if success:
            await ctx.send(embed=success_embed("Channel Unlocked", "🔓 Channel chatting permissions have been restored!"))
        else:
            await ctx.send(embed=error_embed("Permission Error", "Could not modify channel permissions."))

    @commands.command(name="glock", aliases=["gtnlock", "gwlock"], help="Quickly lock the current channel.")
    @commands.has_permissions(manage_channels=True)
    async def lock_cmd(self, ctx: commands.Context):
        """Staff command to lock channel chatting."""
        success = await self._lock_channel(ctx.channel, f"Locked by {ctx.author}")
        if success:
            await ctx.send(embed=info_embed("Channel Locked", "🔒 Channel has been locked."))
        else:
            await ctx.send(embed=error_embed("Permission Error", "Could not modify channel permissions."))

    # ==========================================
    # 9. BLACKTEA / WORD BOMB MULTIPLAYER GW
    # ==========================================
    @commands.command(
        name="blacktea",
        aliases=["wordbomb", "bombparty", "bt"],
        help="Start a BlackTea word-bomb elimination tournament! E.g. $blacktea [prize]"
    )
    @commands.has_permissions(manage_channels=True)
    async def start_blacktea(self, ctx: commands.Context, *, prize: str = "Discord Nitro"):
        """Multiplayer word bomb. Players have 3 lives and 10 seconds to type a word containing the 3-letter prompt."""
        if not await validate_minigame_prize(ctx, prize):
            return

        if ctx.channel.id in self.active_blacktea:
            return await ctx.send(embed=error_embed("Game Active", "A BlackTea game is already active in this channel!\nUse `$blackteastop` to end it."))

        players: List[discord.Member] = [ctx.author]
        game_started = False
        lobby_time = 45
        end_lobby = int(time.time()) + lobby_time
        parent_cog = self

        class BlackTeaLobby(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=lobby_time + 5)

            @discord.ui.button(label="Join Game (1)", style=discord.ButtonStyle.success, emoji="☕")
            async def join_btn(self, inter: discord.Interaction, btn: discord.ui.Button):
                if any(p.id == inter.user.id for p in players):
                    return await inter.response.send_message("☕ You have already joined the lobby!", ephemeral=True)
                if len(players) >= 12:
                    return await inter.response.send_message("❌ Lobby is full (max 12 players)!", ephemeral=True)
                players.append(inter.user)
                btn.label = f"Join Game ({len(players)})"
                await inter.response.edit_message(view=self)

            @discord.ui.button(label="Start Game", style=discord.ButtonStyle.primary, emoji="🚀")
            async def start_btn(self, inter: discord.Interaction, btn: discord.ui.Button):
                nonlocal game_started
                if inter.user.id != ctx.author.id and not inter.user.guild_permissions.manage_channels:
                    return await inter.response.send_message("⛔ Only the host or staff can start the game early!", ephemeral=True)
                if len(players) < 2:
                    return await inter.response.send_message("❌ Need at least 2 players to start a BlackTea tournament!", ephemeral=True)
                game_started = True
                self.stop()
                await inter.response.defer()

        embed = standard_embed(
            title="☕ BLACKTEA WORD-BOMB GW! ☕",
            description=(
                f"Players take turns typing words containing a 3-letter prompt before the bomb explodes!\n\n"
                f"🎁 **Prize:** **{prize}**\n"
                f"👑 **Hosted by:** {ctx.author.mention}\n"
                f"❤️ **Lives:** 3 Lives per player | ⏱️ 10s Turn Timer\n"
                f"⏰ **Lobby Closes:** <t:{end_lobby}:R>\n\n"
                f"👇 Click **Join Game** below to enter!"
            ),
            color=0x7C3AED
        )
        msg = await ctx.send(embed=embed, view=BlackTeaLobby())

        # Wait for lobby timer or manual start
        start_wait = time.time()
        while time.time() - start_wait < lobby_time and not game_started:
            await asyncio.sleep(1)

        if len(players) < 2:
            await msg.edit(view=None)
            return await ctx.send(embed=error_embed("Game Cancelled", "BlackTea requires at least 2 players to start!"))

        # Initialize game state
        game_state = {
            "channel_id": ctx.channel.id,
            "prize": prize,
            "players": [{"member": p, "lives": 3} for p in players],
            "used_words": set(),
            "active": True,
            "current_idx": 0,
            "current_prompt": "",
            "turn_future": None
        }
        self.active_blacktea[ctx.channel.id] = game_state

        await msg.edit(view=None)
        await ctx.send(embed=standard_embed(
            title="💣 BLACKTEA MATCH STARTED! 💣",
            description=f"**{len(players)} Players** entered the arena!\nBomb is armed! Let the battle begin!",
            color=0xED4245
        ))
        await asyncio.sleep(2)

        # Game loop
        try:
            while len(game_state["players"]) > 1 and game_state["active"]:
                curr_player_data = game_state["players"][game_state["current_idx"]]
                player = curr_player_data["member"]
                lives = curr_player_data["lives"]
                lives_str = ("❤️ " * lives) + ("🖤 " * (3 - lives))

                prompt = random.choice(BLACKTEA_PROMPTS)
                game_state["current_prompt"] = prompt.upper()

                loop = asyncio.get_running_loop()
                game_state["turn_future"] = loop.create_future()

                turn_embed = standard_embed(
                    title=f"💣 Turn: {player.display_name}",
                    description=(
                        f"👉 {player.mention}, type an English word containing:\n\n"
                        f"# `{prompt.upper()}`\n\n"
                        f"❤️ **Lives:** {lives_str.strip()}\n"
                        f"⏱️ **Time:** You have **10 seconds** before the bomb explodes!"
                    ),
                    color=0xFEE75C
                )
                turn_msg = await ctx.send(embed=turn_embed)

                word_solved = False
                try:
                    solved_word = await asyncio.wait_for(game_state["turn_future"], timeout=10.0)
                    word_solved = True
                    game_state["used_words"].add(solved_word.upper())
                    try:
                        await turn_msg.reply(f"✅ **{solved_word.upper()}** accepted! Bomb passed! 🍵", mention_author=False)
                    except Exception:
                        pass
                except asyncio.TimeoutError:
                    pass

                if not word_solved:
                    # Player loses a life!
                    curr_player_data["lives"] -= 1
                    remaining = curr_player_data["lives"]
                    new_lives = ("❤️ " * remaining) + ("🖤 " * (3 - remaining))

                    if remaining <= 0:
                        await ctx.send(f"💥 **BOOM!** {player.mention} ran out of time and has been **ELIMINATED**! 💀")
                        game_state["players"].pop(game_state["current_idx"])
                        if game_state["current_idx"] >= len(game_state["players"]):
                            game_state["current_idx"] = 0
                    else:
                        await ctx.send(f"💥 **BOOM!** {player.mention} failed to answer in time! Lost 1 life ({new_lives.strip()})!")
                        game_state["current_idx"] = (game_state["current_idx"] + 1) % len(game_state["players"])
                else:
                    game_state["current_idx"] = (game_state["current_idx"] + 1) % len(game_state["players"])

                await asyncio.sleep(2)

            # Check champion
            if len(game_state["players"]) == 1:
                champion = game_state["players"][0]["member"]
                await parent_cog._lock_channel(ctx.channel, f"BlackTea won by {champion}")
                reward_msg = await process_minigame_win(ctx.guild.id, champion, prize)
                reward_str = f"\n💎 **Auto-Reward:** {reward_msg}" if reward_msg else ""

                win_embed = standard_embed(
                    title="👑 BLACKTEA CHAMPION CROWNED! 👑",
                    description=(
                        f"🎉 Hail to the word master: {champion.mention}!\n\n"
                        f"🏆 **Title:** BlackTea Champion\n"
                        f"🎁 **Prize Won:** **{prize}**{reward_str}\n"
                        f"📚 **Total Words Used in Game:** `{len(game_state['used_words'])}`\n"
                        f"👑 **Hosted by:** {ctx.author.mention}\n\n"
                        f"🔒 **Channel Status:** Automatically locked!"
                    ),
                    color=0x57F287,
                    thumbnail=champion.display_avatar.url
                )
                win_embed.set_footer(text=f"Winner: {champion} • GG!")
                await ctx.send(content=f"👑 {champion.mention} **VICTORY!**", embed=win_embed)

                try:
                    dm_emb = standard_embed(
                        title="🎁 BlackTea Tournament Victory!",
                        description=f"You won the BlackTea tournament in **{ctx.guild.name}** for **{prize}**!\nContact {ctx.author.mention} to claim.",
                        color=0x57F287
                    )
                    await champion.send(embed=dm_emb)
                except Exception:
                    pass
        finally:
            if ctx.channel.id in self.active_blacktea:
                del self.active_blacktea[ctx.channel.id]

    @commands.command(name="blackteastop", aliases=["btstop", "stopbt"], help="Stop an active BlackTea game in this channel.")
    @commands.has_permissions(manage_channels=True)
    async def stop_blacktea(self, ctx: commands.Context):
        if ctx.channel.id not in self.active_blacktea:
            return await ctx.send(embed=error_embed("No Game", "No BlackTea game currently running in this channel."))
        self.active_blacktea[ctx.channel.id]["active"] = False
        del self.active_blacktea[ctx.channel.id]
        await ctx.send(embed=info_embed("Game Stopped", f"BlackTea game was stopped by {ctx.author.mention}."))

    # ==========================================
    # 10. RUSSIAN ROULETTE GW
    # ==========================================
    @commands.command(
        name="roulette",
        aliases=["russianroulette", "rr", "cylinder"],
        help="Start Russian Roulette! E.g. $roulette [prize]"
    )
    @commands.has_permissions(manage_channels=True)
    async def start_roulette(self, ctx: commands.Context, *, prize: str = "Discord Nitro"):
        """Russian Roulette: 6 chambers, 1 bullet. Players take turns pulling trigger until 1 survivor remains!"""
        if not await validate_minigame_prize(ctx, prize):
            return

        if ctx.channel.id in self.active_roulette:
            return await ctx.send(embed=error_embed("Game Active", "A Roulette game is already running in this channel!"))

        players: List[discord.Member] = [ctx.author]
        lobby_time = 30
        end_lobby = int(time.time()) + lobby_time
        parent_cog = self

        class RouletteLobby(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=lobby_time + 5)

            @discord.ui.button(label="Join Chamber (1)", style=discord.ButtonStyle.danger, emoji="🔫")
            async def join_btn(self, inter: discord.Interaction, btn: discord.ui.Button):
                if any(p.id == inter.user.id for p in players):
                    return await inter.response.send_message("🔫 You are already in the chamber!", ephemeral=True)
                if len(players) >= 6:
                    return await inter.response.send_message("❌ Chamber full (max 6 players)!", ephemeral=True)
                players.append(inter.user)
                btn.label = f"Join Chamber ({len(players)})"
                await inter.response.edit_message(view=self)

        embed = standard_embed(
            title="🔫 RUSSIAN ROULETTE GW! 🔫",
            description=(
                f"6 Chambers. 1 Live Round. Who will survive?\n\n"
                f"🎁 **Prize:** **{prize}**\n"
                f"👑 **Hosted by:** {ctx.author.mention}\n"
                f"⏰ **Lobby Closes:** <t:{end_lobby}:R>\n\n"
                f"👇 Click **Join Chamber** below to enter!"
            ),
            color=0xED4245
        )
        msg = await ctx.send(embed=embed, view=RouletteLobby())
        await asyncio.sleep(lobby_time)

        if len(players) < 2:
            await msg.edit(view=None)
            return await ctx.send(embed=error_embed("Cancelled", "At least 2 players are required for Russian Roulette!"))

        await msg.edit(view=None)
        await ctx.send(embed=standard_embed(
            title="🔄 SPINNING THE CYLINDER...",
            description=f"**{len(players)} Players** loaded into the game!\nThe cylinder has been spun and loaded!",
            color=0x34495E
        ))
        await asyncio.sleep(2)

        self.active_roulette[ctx.channel.id] = True
        chamber = random.randint(0, 5)
        bullet = random.randint(0, 5)
        curr_idx = 0

        try:
            while len(players) > 1 and ctx.channel.id in self.active_roulette:
                curr_player = players[curr_idx]
                trigger_pulled = False

                class TriggerView(discord.ui.View):
                    def __init__(self):
                        super().__init__(timeout=15)

                    @discord.ui.button(label="💥 PULL TRIGGER", style=discord.ButtonStyle.danger, emoji="🔫")
                    async def pull(self, inter: discord.Interaction, btn: discord.ui.Button):
                        nonlocal trigger_pulled
                        if inter.user.id != curr_player.id:
                            return await inter.response.send_message("⛔ It's not your turn to pull the trigger!", ephemeral=True)
                        trigger_pulled = True
                        self.stop()
                        await inter.response.defer()

                t_embed = standard_embed(
                    title=f"🔫 Turn: {curr_player.display_name}",
                    description=f"{curr_player.mention}, click the button below to pull the trigger!\n*You have 15 seconds...*",
                    color=0xED4245
                )
                t_msg = await ctx.send(embed=t_embed, view=TriggerView())
                await asyncio.sleep(15)

                try:
                    await t_msg.edit(view=None)
                except Exception:
                    pass

                # If did not pull trigger, automatic trigger pull
                if chamber == bullet:
                    await ctx.send(f"💥 **BANG!** A round fired! 💀 {curr_player.mention} has been **ELIMINATED**!")
                    players.pop(curr_idx)
                    # Respin and reload
                    chamber = random.randint(0, 5)
                    bullet = random.randint(0, 5)
                    if curr_idx >= len(players):
                        curr_idx = 0
                else:
                    await ctx.send(f"*Click...* 😅 The hammer hit an empty chamber! {curr_player.mention} survived!")
                    chamber = (chamber + 1) % 6
                    curr_idx = (curr_idx + 1) % len(players)

                await asyncio.sleep(3)

            # Winner!
            if len(players) == 1:
                survivor = players[0]
                await parent_cog._lock_channel(ctx.channel, f"Roulette won by {survivor}")
                reward_msg = await process_minigame_win(ctx.guild.id, survivor, prize)
                reward_str = f"\n💎 **Auto-Reward:** {reward_msg}" if reward_msg else ""

                win_embed = standard_embed(
                    title="👑 ROULETTE SOLE SURVIVOR! 👑",
                    description=(
                        f"🎉 {survivor.mention} survived the cylinder!\n\n"
                        f"🎁 **Prize Won:** **{prize}**{reward_str}\n"
                        f"👑 **Hosted by:** {ctx.author.mention}\n\n"
                        f"🔒 **Channel Status:** Automatically locked!"
                    ),
                    color=0x57F287,
                    thumbnail=survivor.display_avatar.url
                )
                await ctx.send(content=f"👑 {survivor.mention} **SURVIVOR!**", embed=win_embed)
        finally:
            if ctx.channel.id in self.active_roulette:
                del self.active_roulette[ctx.channel.id]

    # ==========================================
    # 11. TIC-TAC-TOE PVP DUEL
    # ==========================================
    @commands.command(
        name="tictactoe",
        aliases=["ttt"],
        help="Challenge a player to Tic-Tac-Toe. E.g. $ttt @opponent [prize]"
    )
    async def tictactoe_cmd(self, ctx: commands.Context, opponent: discord.Member, *, prize: str = "Bragging Rights"):
        """Interactive 3x3 button Tic-Tac-Toe PvP duel."""
        if not await validate_minigame_prize(ctx, prize):
            return

        if opponent.bot or opponent.id == ctx.author.id:
            return await ctx.send(embed=error_embed("Invalid Opponent", "Please mention a real other member to play against!"))

        board = [None] * 9
        turn = ctx.author  # Author is X, opponent is O
        winner = None
        game_over = False
        parent_cog = self

        def check_win():
            lines = [
                (0, 1, 2), (3, 4, 5), (6, 7, 8),
                (0, 3, 6), (1, 4, 7), (2, 5, 8),
                (0, 4, 8), (2, 4, 6)
            ]
            for a, b, c in lines:
                if board[a] and board[a] == board[b] == board[c]:
                    return board[a]
            if all(cell is not None for cell in board):
                return "Tie"
            return None

        class TTTView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=120)
                for i in range(9):
                    btn = discord.ui.Button(label="‎", style=discord.ButtonStyle.secondary, row=i // 3, custom_id=f"ttt_{i}")
                    btn.callback = self.make_callback(i)
                    self.add_item(btn)

            def make_callback(self, idx):
                async def cb(inter: discord.Interaction):
                    nonlocal turn, game_over, winner
                    if game_over:
                        return await inter.response.send_message("Game is over!", ephemeral=True)

                    if inter.user.id != turn.id:
                        return await inter.response.send_message(f"It is currently {turn.display_name}'s turn!", ephemeral=True)

                    mark = "❌" if turn == ctx.author else "⭕"
                    board[idx] = mark

                    # Update button
                    for child in self.children:
                        if isinstance(child, discord.ui.Button) and child.custom_id == f"ttt_{idx}":
                            child.label = mark
                            child.disabled = True
                            child.style = discord.ButtonStyle.danger if mark == "❌" else discord.ButtonStyle.primary

                    res = check_win()
                    if res:
                        game_over = True
                        for child in self.children:
                            child.disabled = True

                        if res == "Tie":
                            await inter.response.edit_message(content="🤝 **Tic-Tac-Toe ended in a TIE!**", view=self)
                        else:
                            winner = ctx.author if res == "❌" else opponent
                            await inter.response.edit_message(content=f"🏆 **{winner.mention} WON TIC-TAC-TOE!**", view=self)
                            if prize != "Bragging Rights":
                                await parent_cog._lock_channel(ctx.channel, f"TTT won by {winner}")
                                reward_msg = await process_minigame_win(ctx.guild.id, winner, prize)
                                reward_str = f"\n💎 **Auto-Reward:** {reward_msg}" if reward_msg else ""
                                await ctx.send(embed=standard_embed(
                                    title="🎉 TIC-TAC-TOE VICTORY! 🎉",
                                    description=f"Congratulations {winner.mention}!\n🎁 **Prize:** **{prize}**{reward_str}\n🔒 Channel locked!",
                                    color=0x57F287
                                ))
                    else:
                        turn = opponent if turn == ctx.author else ctx.author
                        await inter.response.edit_message(content=f"🎮 **Tic-Tac-Toe:** {turn.mention}'s turn ({'❌' if turn == ctx.author else '⭕'})", view=self)

                return cb

        await ctx.send(content=f"🎮 **Tic-Tac-Toe Duel:** {ctx.author.mention} (❌) vs {opponent.mention} (⭕)\n🎁 **Prize:** `{prize}`\nTurn: {turn.mention}", view=TTTView())

    # ==========================================
    # 12. ROCK PAPER SCISSORS DUEL
    # ==========================================
    @commands.command(
        name="rps",
        aliases=["rockpaperscissors"],
        help="Rock Paper Scissors. Play against the bot or challenge a user! E.g. $rps [@user] [prize]"
    )
    async def rps_cmd(self, ctx: commands.Context, opponent: Optional[discord.Member] = None, *, prize: str = "Bragging Rights"):
        """Interactive Rock Paper Scissors with button controls."""
        if not await validate_minigame_prize(ctx, prize):
            return

        choices = {"rock": "🪨 Rock", "paper": "📄 Paper", "scissors": "✂️ Scissors"}
        rules = {"rock": "scissors", "paper": "rock", "scissors": "paper"}

        if not opponent or opponent.id == ctx.author.id:
            # Play against Bot
            class SoloRPS(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=60)

                async def handle_pick(self, inter: discord.Interaction, user_pick: str):
                    if inter.user.id != ctx.author.id:
                        return await inter.response.send_message("This game is for the command author!", ephemeral=True)
                    bot_pick = random.choice(["rock", "paper", "scissors"])
                    if user_pick == bot_pick:
                        desc = f"🤝 **It's a TIE!**\nBoth picked **{choices[user_pick]}**!"
                        col = 0xFEE75C
                    elif rules[user_pick] == bot_pick:
                        desc = f"🏆 **YOU WIN!**\nYou picked **{choices[user_pick]}** and bot picked **{choices[bot_pick]}**!"
                        col = 0x57F287
                    else:
                        desc = f"💀 **BOT WINS!**\nBot picked **{choices[bot_pick]}** and beat your **{choices[user_pick]}**!"
                        col = 0xED4245

                    for c in self.children:
                        c.disabled = True
                    await inter.response.edit_message(embed=standard_embed(title="🎮 Rock Paper Scissors", description=desc, color=col), view=self)

                @discord.ui.button(label="Rock", style=discord.ButtonStyle.primary, emoji="🪨")
                async def rock_btn(self, inter: discord.Interaction, btn: discord.ui.Button):
                    await self.handle_pick(inter, "rock")

                @discord.ui.button(label="Paper", style=discord.ButtonStyle.primary, emoji="📄")
                async def paper_btn(self, inter: discord.Interaction, btn: discord.ui.Button):
                    await self.handle_pick(inter, "paper")

                @discord.ui.button(label="Scissors", style=discord.ButtonStyle.primary, emoji="✂️")
                async def sci_btn(self, inter: discord.Interaction, btn: discord.ui.Button):
                    await self.handle_pick(inter, "scissors")

            await ctx.send(embed=standard_embed(title="🪨 Rock Paper Scissors", description=f"Choose your move against **{self.bot.user.name}**!", color=0x5865F2), view=SoloRPS())
        else:
            # PvP Duel
            user_choices = {}

            class PvPRPS(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=60)

                async def register_pick(self, inter: discord.Interaction, pick: str):
                    if inter.user.id not in (ctx.author.id, opponent.id):
                        return await inter.response.send_message("⛔ You are not in this RPS duel!", ephemeral=True)
                    if inter.user.id in user_choices:
                        return await inter.response.send_message(f"You already locked in **{choices[user_choices[inter.user.id]]}**!", ephemeral=True)

                    user_choices[inter.user.id] = pick
                    await inter.response.send_message(f"✅ Locked in **{choices[pick]}**!", ephemeral=True)

                    if len(user_choices) == 2:
                        p1_pick = user_choices[ctx.author.id]
                        p2_pick = user_choices[opponent.id]
                        for c in self.children:
                            c.disabled = True

                        if p1_pick == p2_pick:
                            res_txt = f"🤝 **It's a TIE!** Both players chose **{choices[p1_pick]}**!"
                            col = 0xFEE75C
                        elif rules[p1_pick] == p2_pick:
                            reward_msg = await process_minigame_win(ctx.guild.id, ctx.author, prize)
                            reward_str = f"\n💎 **Auto-Reward:** {reward_msg}" if reward_msg else ""
                            res_txt = f"🏆 **{ctx.author.mention} WINS!**\n{choices[p1_pick]} beats {choices[p2_pick]}!\n🎁 Prize: **{prize}**{reward_str}"
                            col = 0x57F287
                        else:
                            reward_msg = await process_minigame_win(ctx.guild.id, opponent, prize)
                            reward_str = f"\n💎 **Auto-Reward:** {reward_msg}" if reward_msg else ""
                            res_txt = f"🏆 **{opponent.mention} WINS!**\n{choices[p2_pick]} beats {choices[p1_pick]}!\n🎁 Prize: **{prize}**{reward_str}"
                            col = 0x57F287

                        await ctx.send(embed=standard_embed(title="🎮 RPS Duel Result!", description=res_txt, color=col))

                @discord.ui.button(label="Rock", style=discord.ButtonStyle.primary, emoji="🪨")
                async def rock_btn(self, inter: discord.Interaction, btn: discord.ui.Button):
                    await self.register_pick(inter, "rock")

                @discord.ui.button(label="Paper", style=discord.ButtonStyle.primary, emoji="📄")
                async def paper_btn(self, inter: discord.Interaction, btn: discord.ui.Button):
                    await self.register_pick(inter, "paper")

                @discord.ui.button(label="Scissors", style=discord.ButtonStyle.primary, emoji="✂️")
                async def sci_btn(self, inter: discord.Interaction, btn: discord.ui.Button):
                    await self.register_pick(inter, "scissors")

            await ctx.send(
                content=f"⚔️ **RPS DUEL:** {ctx.author.mention} vs {opponent.mention}!\n*Click your secret choice below:*",
                view=PvPRPS()
            )

    # ==========================================
    # 13. CASINO BLACKJACK 21
    # ==========================================
    @commands.command(
        name="blackjack",
        aliases=["bj", "21"],
        help="Play Blackjack 21 against the Dealer! E.g. $blackjack [prize]"
    )
    async def blackjack_cmd(self, ctx: commands.Context, *, prize: str = "Discord Nitro"):
        """Interactive Casino Blackjack 21."""
        if not await validate_minigame_prize(ctx, prize):
            return

        ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        suits = ["♠", "♥", "♦", "♣"]
        deck = [f"{r}{s}" for r in ranks for s in suits]
        random.shuffle(deck)

        def hand_val(hand):
            val = 0
            aces = 0
            for card in hand:
                r = card[:-1]
                if r in ["J", "Q", "K"]:
                    val += 10
                elif r == "A":
                    val += 11
                    aces += 1
                else:
                    val += int(r)
            while val > 21 and aces > 0:
                val -= 10
                aces -= 1
            return val

        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]

        p_score = hand_val(player_hand)
        game_ended = False

        class BJView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)

            def make_embed(self, reveal_dealer=False, status_note=""):
                d_score = hand_val(dealer_hand)
                p_score_curr = hand_val(player_hand)

                d_str = " ".join(dealer_hand) if reveal_dealer else f"{dealer_hand[0]} 🂠"
                d_score_str = f"(`{d_score}`)" if reveal_dealer else "(`?`)"

                col = 0x5865F2
                if "Bust" in status_note or "Dealer Wins" in status_note:
                    col = 0xED4245
                elif "Win" in status_note:
                    col = 0x57F287

                emb = standard_embed(
                    title="🃏 Casino Blackjack 21",
                    description=(
                        f"**Dealer's Hand:** {d_str} {d_score_str}\n"
                        f"**Your Hand:** {' '.join(player_hand)} (`{p_score_curr}`)\n\n"
                        f"🎁 **Prize:** `{prize}`\n"
                        f"{status_note}"
                    ),
                    color=col
                )
                emb.set_footer(text=f"Player: {ctx.author.display_name}")
                return emb

            @discord.ui.button(label="Hit", style=discord.ButtonStyle.success, emoji="🃏")
            async def hit_btn(self, inter: discord.Interaction, btn: discord.ui.Button):
                nonlocal game_ended
                if inter.user.id != ctx.author.id:
                    return await inter.response.send_message("Not your hand!", ephemeral=True)
                if game_ended:
                    return

                player_hand.append(deck.pop())
                new_p = hand_val(player_hand)
                if new_p > 21:
                    game_ended = True
                    for c in self.children:
                        c.disabled = True
                    emb = self.make_embed(reveal_dealer=True, status_note="💥 **BUST!** You went over 21! Dealer wins.")
                    await inter.response.edit_message(embed=emb, view=self)
                elif new_p == 21:
                    # Auto stand on 21
                    await self.stand_logic(inter)
                else:
                    await inter.response.edit_message(embed=self.make_embed(), view=self)

            @discord.ui.button(label="Stand", style=discord.ButtonStyle.danger, emoji="🛑")
            async def stand_btn(self, inter: discord.Interaction, btn: discord.ui.Button):
                if inter.user.id != ctx.author.id:
                    return await inter.response.send_message("Not your hand!", ephemeral=True)
                await self.stand_logic(inter)

            async def stand_logic(self, inter: discord.Interaction):
                nonlocal game_ended
                game_ended = True
                for c in self.children:
                    c.disabled = True

                # Dealer plays
                while hand_val(dealer_hand) < 17:
                    dealer_hand.append(deck.pop())

                final_p = hand_val(player_hand)
                final_d = hand_val(dealer_hand)

                if final_d > 21:
                    reward_msg = await process_minigame_win(ctx.guild.id, ctx.author, prize)
                    reward_str = f"\n💎 **Auto-Reward:** {reward_msg}" if reward_msg else ""
                    note = f"🎉 **DEALER BUST!** You win the hand!{reward_str}"
                elif final_p > final_d:
                    reward_msg = await process_minigame_win(ctx.guild.id, ctx.author, prize)
                    reward_str = f"\n💎 **Auto-Reward:** {reward_msg}" if reward_msg else ""
                    note = f"🏆 **YOU WIN!** `{final_p}` beats Dealer's `{final_d}`!{reward_str}"
                elif final_p < final_d:
                    note = f"💀 **DEALER WINS!** `{final_d}` beats your `{final_p}`."
                else:
                    note = "🤝 **PUSH (TIE)!** Hand was a draw."

                await inter.response.edit_message(embed=self.make_embed(reveal_dealer=True, status_note=note), view=self)

        view = BJView()
        # Initial natural 21 check
        if p_score == 21:
            reward_msg = await process_minigame_win(ctx.guild.id, ctx.author, prize)
            reward_str = f"\n💎 **Auto-Reward:** {reward_msg}" if reward_msg else ""
            emb = standard_embed(
                title="🃏 Casino Blackjack 21",
                description=(
                    f"**Dealer's Hand:** {' '.join(dealer_hand)} (`{hand_val(dealer_hand)}`)\n"
                    f"**Your Hand:** {' '.join(player_hand)} (`21`)\n\n"
                    f"✨ **NATURAL BLACKJACK! YOU WIN!** ✨{reward_str}"
                ),
                color=0x57F287
            )
            return await ctx.send(embed=emb)

        await ctx.send(embed=view.make_embed(), view=view)

    # ==========================================
    # 14. CYBER HACK SIMULATOR
    # ==========================================
    @commands.command(
        name="hack",
        aliases=["cyberhack"],
        help="Simulate a hilarious realistic cyber hack on a user. E.g. $hack @user"
    )
    async def hack_cmd(self, ctx: commands.Context, user: discord.Member):
        """Simulate hacking a user with progressive realistic steps."""
        if user.bot:
            return await ctx.send("🤖 Cannot hack synthetic bot mainframe — firewall too strong!")

        fake_ip = f"192.168.{random.randint(1, 254)}.{random.randint(2, 254)}"
        fake_token = f"MTA{random.randint(100000, 999999)}.{random.choice(['X', 'Y', 'Z'])}{random.randint(100, 999)}...[REDACTED]"
        searches = [
            '"how to get free discord nitro 2026"',
            '"why is my crush not texting me back"',
            '"can you microwave cereal"',
            '"how to become a discord admin fast"',
            '"is touching grass safe"'
        ]
        chosen_search = random.choice(searches)

        steps = [
            f"💻 `[0%] Initializing breach protocol on {user.display_name}...`",
            f"📡 `[25%] Bypassing local router firewall... IP Found: {fake_ip}`",
            f"🔑 `[50%] Decrypting Discord authentication token: {fake_token}`",
            f"🔍 `[75%] Extracting private search history: {chosen_search}`",
            f"📦 `[100%] Infiltration complete! Leaking user files to dark web for 0.05 BTC...`"
        ]

        hack_msg = await ctx.send(embed=standard_embed(
            title="⚠️ CYBER INFILTRATION IN PROGRESS",
            description=steps[0],
            color=0xED4245
        ))

        for step in steps[1:]:
            await asyncio.sleep(2)
            try:
                await hack_msg.edit(embed=standard_embed(
                    title="⚠️ CYBER INFILTRATION IN PROGRESS",
                    description=step,
                    color=0xED4245
                ))
            except Exception:
                pass

        await asyncio.sleep(1.5)
        done_emb = success_embed(
            "Target Successfully Hacked!",
            f"✅ **{user.mention}** has been thoroughly compromised!\n\n"
            f"• **IP Address:** `{fake_ip}`\n"
            f"• **Token Status:** `Compromised`\n"
            f"• **Most Frequent Search:** *{chosen_search}*\n"
            f"• **Security Rating:** `0/100`"
        )
        done_emb.set_thumbnail(url=user.display_avatar.url)
        await hack_msg.edit(embed=done_emb)

    # ==========================================
    # 15. SECRET WHISPER
    # ==========================================
    @commands.command(
        name="whisper",
        aliases=["secretmsg", "confidential"],
        help="Send a confidential whisper in chat that only the target user can click to reveal! E.g. $whisper @user Meet me in ticket"
    )
    async def whisper_cmd(self, ctx: commands.Context, user: discord.Member, *, message: str):
        """Send an encrypted whisper with an ephemeral reveal button."""
        try:
            await ctx.message.delete()
        except Exception:
            pass

        whisper_text = message.strip()
        author = ctx.author

        class WhisperView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)

            @discord.ui.button(label="Reveal Secret Whisper", style=discord.ButtonStyle.secondary, emoji="🔒")
            async def reveal(self, inter: discord.Interaction, btn: discord.ui.Button):
                if inter.user.id not in (user.id, author.id):
                    return await inter.response.send_message("⛔ This secret whisper is encrypted for another user!", ephemeral=True)

                sender_tag = f"from **{author.display_name}**" if inter.user.id == user.id else f"sent to **{user.display_name}**"
                await inter.response.send_message(
                    f"📩 **Secret Whisper ({sender_tag}):**\n>>> {whisper_text}",
                    ephemeral=True
                )

        embed = standard_embed(
            title="🔒 Confidential Whisper",
            description=(
                f"A secret message was delivered for {user.mention}!\n\n"
                f"Click the button below to decrypt and read your whisper."
            ),
            color=0x2B2D31
        )
        embed.set_footer(text=f"Sent by {ctx.author.display_name} • Only target can read")
        await ctx.send(content=f"🤫 {user.mention}", embed=embed, view=WhisperView())

    # ==========================================
    # MESSAGE LISTENER FOR GTN, SCRAMBLE, & MATH
    # ==========================================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        ch_id = message.channel.id
        content = message.content.strip()

        # 1. Check GTN
        if ch_id in self.active_gtn:
            if content.isdigit() or (content.startswith('-') and content[1:].isdigit()):
                try:
                    guess = int(content)
                    game = self.active_gtn[ch_id]
                    game["guesses"] += 1
                    target = game["target"]

                    if guess < target:
                        if guess > game["highest_low"]:
                            game["highest_low"] = guess
                        try:
                            await message.add_reaction("➕")
                        except Exception:
                            pass
                    elif guess > target:
                        if guess < game["lowest_high"]:
                            game["lowest_high"] = guess
                        try:
                            await message.add_reaction("➖")
                        except Exception:
                            pass
                    else:
                        # WINNER!
                        del self.active_gtn[ch_id]
                        await self._lock_channel(message.channel, "GTN Winner found - channel locked")
                        reward_msg = await process_minigame_win(message.guild.id, message.author, game['prize'])
                        reward_str = f"\n💎 **Auto-Reward:** {reward_msg}" if reward_msg else ""

                        win_emb = standard_embed(
                            title="🎉 WE HAVE A WINNER! 🎉",
                            description=(
                                f"Congratulations {message.author.mention}!\n\n"
                                f"🎯 **Correct Number:** `{target}`\n"
                                f"🎁 **Prize:** **{game['prize']}**{reward_str}\n"
                                f"📊 **Total Guesses:** `{game['guesses']}`\n"
                                f"👑 **Hosted by:** <@{game['starter']}>\n\n"
                                f"🔒 **Channel Status:** Automatically locked!"
                            ),
                            color=0x57F287,
                            thumbnail=message.author.display_avatar.url
                        )
                        win_emb.set_footer(text=f"Winner: {message.author} • GG!")
                        await message.channel.send(content=f"👑 {message.author.mention}", embed=win_emb)

                        try:
                            dm_reward_text = f"\n{reward_msg}" if reward_msg else f"\nContact <@{game['starter']}> to claim your reward."
                            dm_emb = standard_embed(
                                title="🎯 GTN Victory!",
                                description=f"You guessed `{target}` correctly in **{message.guild.name}** and won **{game['prize']}**!{dm_reward_text}",
                                color=0x57F287
                            )
                            await message.author.send(embed=dm_emb)
                        except Exception:
                            pass
                except ValueError:
                    pass

        # 2. Check Word Scramble
        if ch_id in self.active_scramble:
            game = self.active_scramble[ch_id]
            target_word = game["word"].upper()
            if content.upper() == target_word:
                del self.active_scramble[ch_id]
                await self._lock_channel(message.channel, "Word Scramble won")
                reward_msg = await process_minigame_win(message.guild.id, message.author, game['prize'])
                reward_str = f"\n💎 **Auto-Reward:** {reward_msg}" if reward_msg else ""

                win_emb = standard_embed(
                    title="🧩 SCRAMBLE SOLVED! 🧩",
                    description=(
                        f"🎉 Congratulations {message.author.mention}!\n\n"
                        f"🔤 **Unscrambled Word:** **{target_word}**\n"
                        f"🎁 **Prize:** **{game['prize']}**{reward_str}\n"
                        f"👑 **Hosted by:** <@{game['starter']}>\n\n"
                        f"🔒 **Channel Status:** Automatically locked!"
                    ),
                    color=0x57F287,
                    thumbnail=message.author.display_avatar.url
                )
                win_emb.set_footer(text=f"Winner: {message.author} • Fast Mind!")
                await message.channel.send(content=f"👑 {message.author.mention}", embed=win_emb)

                try:
                    dm_reward_text = f"\n{reward_msg}" if reward_msg else f"\nContact <@{game['starter']}> to claim your reward."
                    dm_emb = standard_embed(
                        title="🧩 Scramble Victory!",
                        description=f"You solved **{target_word}** in **{message.guild.name}** and won **{game['prize']}**!{dm_reward_text}",
                        color=0x57F287
                    )
                    await message.author.send(embed=dm_emb)
                except Exception:
                    pass

        # 3. Check Math Race
        if ch_id in self.active_math:
            game = self.active_math[ch_id]
            if content.isdigit() or (content.startswith('-') and content[1:].isdigit()):
                try:
                    num_val = int(content)
                    if num_val == game["answer"]:
                        del self.active_math[ch_id]
                        await self._lock_channel(message.channel, "Math Race won")
                        reward_msg = await process_minigame_win(message.guild.id, message.author, game['prize'])
                        reward_str = f"\n💎 **Auto-Reward:** {reward_msg}" if reward_msg else ""

                        win_emb = standard_embed(
                            title="🧮 MATH RACE WINNER! 🧮",
                            description=(
                                f"🎉 Congratulations {message.author.mention}!\n\n"
                                f"📊 **Equation:** `{game['equation']} = {game['answer']}`\n"
                                f"🎁 **Prize:** **{game['prize']}**{reward_str}\n"
                                f"👑 **Hosted by:** <@{game['starter']}>\n\n"
                                f"🔒 **Channel Status:** Automatically locked!"
                            ),
                            color=0x57F287,
                            thumbnail=message.author.display_avatar.url
                        )
                        win_emb.set_footer(text=f"Winner: {message.author} • Lightning Calculator!")
                        await message.channel.send(content=f"👑 {message.author.mention}", embed=win_emb)

                        try:
                            dm_reward_text = f"\n{reward_msg}" if reward_msg else f"\nContact <@{game['starter']}> to claim your reward."
                            dm_emb = standard_embed(
                                title="🧮 Math Race Victory!",
                                description=f"You solved `{game['equation']} = {game['answer']}` in **{message.guild.name}** and won **{game['prize']}**!{dm_reward_text}",
                                color=0x57F287
                            )
                            await message.author.send(embed=dm_emb)
                        except Exception:
                            pass
                except ValueError:
                    pass

        # 4. Check BlackTea
        if ch_id in self.active_blacktea:
            game = self.active_blacktea[ch_id]
            if game.get("players") and game.get("active"):
                curr_player = game["players"][game["current_idx"]]["member"]
                if message.author.id == curr_player.id:
                    word = content.strip().upper()
                    prompt = game.get("current_prompt", "")
                    if prompt in word and len(word) >= 3 and word.isalpha():
                        if word not in game["used_words"]:
                            if game.get("turn_future") and not game["turn_future"].done():
                                game["turn_future"].set_result(word)
                                try:
                                    await message.add_reaction("🍵")
                                except Exception:
                                    pass
                        else:
                            try:
                                await message.add_reaction("⚠️")
                            except Exception:
                                pass

# Alias class for backward compatibility with GuessTheNumber
class GuessTheNumber(GWGames):
    pass

async def setup(bot: commands.Bot):
    await bot.add_cog(GWGames(bot))
