import discord
from discord.ext import commands
import random
from utils.embeds import standard_embed, success_embed, error_embed, info_embed

class GuessTheNumber(commands.Cog):
    """Guess the Number game with +/- reactions and channel locking on win."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Active games per channel_id: {channel_id: {"target": int, "min": int, "max": int, "guesses": int, "starter": int}}
        self.active_games = {}

    @commands.command(name="gtn", aliases=["guessthenumber", "guess"], help="Start a Guess The Number game. E.g. $gtn 1 5000")
    @commands.has_permissions(manage_channels=True)
    async def start_gtn(self, ctx: commands.Context, min_val: int = 1, max_val: int = 1000):
        if min_val >= max_val:
            return await ctx.send(embed=error_embed("Invalid Range", "Minimum value must be less than maximum value."))
        if max_val - min_val < 5:
            return await ctx.send(embed=error_embed("Range Too Small", "Please choose a range with at least 5 numbers."))

        if ctx.channel.id in self.active_games:
            return await ctx.send(embed=error_embed("Game Already Active", "A Guess The Number game is already running in this channel!\nUse `$gtnstop` to end it."))

        target_number = random.randint(min_val, max_val)
        self.active_games[ctx.channel.id] = {
            "target": target_number,
            "min": min_val,
            "max": max_val,
            "guesses": 0,
            "starter": ctx.author.id
        }

        # Send the secret answer to the host in private DMs
        dm_status = ""
        try:
            host_embed = standard_embed(
                title="🎯 GTN • Secret Host Answer",
                description=(
                    f"You started a Guess The Number game in {ctx.channel.mention}!\n\n"
                    f"🔢 **Secret Target Number:** `{target_number}`\n"
                    f"📊 **Range:** Between `{min_val}` and `{max_val}`\n\n"
                    f"🤫 *Keep this number secret to ensure a fair competition!*"
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
                f"🔢 **Range:** Between `{min_val}` and `{max_val}`\n"
                f"➕ Bot reacts with `➕` if your guess is **LOWER** than the secret number (guess higher!)\n"
                f"➖ Bot reacts with `➖` if your guess is **HIGHER** than the secret number (guess lower!)\n\n"
                f"🏆 First person to guess correctly will be crowned **WINNER** and this channel will be locked!{dm_status}\n\n"
                f"Good luck everyone!"
            ),
            color=0x5865F2
        )
        embed.set_footer(text=f"Game hosted by {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command(name="gtnstop", aliases=["gstop", "endgtn", "gtnx"], help="Stop an active Guess The Number game in this channel.")
    @commands.has_permissions(manage_channels=True)
    async def stop_gtn(self, ctx: commands.Context):
        if ctx.channel.id not in self.active_games:
            return await ctx.send(embed=error_embed("No Active Game", "There is no Guess The Number game running in this channel."))

        game = self.active_games.pop(ctx.channel.id)
        await ctx.send(embed=info_embed("Game Stopped", f"The game was stopped by {ctx.author.mention}.\nThe secret number was **{game['target']}**."))

    @commands.command(name="gtnstatus", aliases=["gstatus", "gtns", "ginfo"], help="Check current GTN game range and guess count.")
    async def status_gtn(self, ctx: commands.Context):
        if ctx.channel.id not in self.active_games:
            return await ctx.send(embed=info_embed("No Game Running", "No active Guess The Number game in this channel."))

        game = self.active_games[ctx.channel.id]
        embed = info_embed(
            "GTN Game In Progress",
            f"**Range:** `{game['min']}` to `{game['max']}`\n**Total Guesses Made:** `{game['guesses']}`"
        )
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        channel_id = message.channel.id
        if channel_id not in self.active_games:
            return

        # Check if message is a valid integer
        content = message.content.strip()
        if not content.isdigit() and not (content.startswith('-') and content[1:].isdigit()):
            return

        try:
            guess = int(content)
        except ValueError:
            return

        game = self.active_games[channel_id]
        game["guesses"] += 1
        target = game["target"]

        if guess < target:
            # Guess is lower than answer -> React with +
            try:
                await message.add_reaction("➕")
            except Exception:
                pass
        elif guess > target:
            # Guess is higher than answer -> React with -
            try:
                await message.add_reaction("➖")
            except Exception:
                pass
        else:
            # CORRECT GUESS! WINNER!
            del self.active_games[channel_id]

            # Lock channel
            try:
                overwrite = message.channel.overwrites_for(message.guild.default_role)
                overwrite.send_messages = False
                await message.channel.set_permissions(message.guild.default_role, overwrite=overwrite, reason="GTN Winner found - channel auto-locked")
            except Exception as e:
                print(f"Error locking channel: {e}")

            # Winner embed
            winner_embed = standard_embed(
                title="🎉 WE HAVE A WINNER! 🎉",
                description=(
                    f"Congratulations {message.author.mention}!\n\n"
                    f"🎯 **Correct Number:** `{target}`\n"
                    f"📊 **Total Guesses in Game:** `{game['guesses']}`\n\n"
                    f"🔒 **Channel Status:** Channel has been automatically locked!"
                ),
                color=0x57F287,
                thumbnail=message.author.display_avatar.url
            )
            winner_embed.set_footer(text=f"Winner: {message.author} • GG!")

            await message.channel.send(content=f"👑 {message.author.mention}", embed=winner_embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(GuessTheNumber(bot))
