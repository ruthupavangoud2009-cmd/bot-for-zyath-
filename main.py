import discord
from discord.ext import commands, tasks
import asyncio
import os
import json
from dotenv import load_dotenv
from colorama import Fore, Style, init

from utils.database import db
from utils.embeds import error_embed

# Initialize colorama
init(autoreset=True)

# Load environment
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
ENV_PREFIX = os.getenv("PREFIX", "$")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
def get_config_prefix():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("prefix", "$")
        except Exception:
            pass
    return "$"

DEFAULT_PREFIX = get_config_prefix() or ENV_PREFIX or "$"

def get_config_owner_ids():
    ids = {1521774957065928734, 1505515188991033409}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                for oid in data.get("owner_ids", []):
                    ids.add(int(oid))
        except Exception:
            pass
    return ids

OWNER_IDS = get_config_owner_ids()

async def get_prefix(bot, message):
    guild_prefix = DEFAULT_PREFIX
    if message.guild:
        try:
            settings = await db.get_guild_settings(message.guild.id)
            guild_prefix = settings.get("prefix") or DEFAULT_PREFIX
        except Exception:
            guild_prefix = DEFAULT_PREFIX

    # Check if author is an owner or in no-prefix whitelist
    author_id = message.author.id if message.author else 0
    if author_id in OWNER_IDS or db.is_no_prefix_cached(author_id):
        return (guild_prefix, "")
    return guild_prefix

# Setup bot intents
intents = discord.Intents.all()

class ZyathBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=get_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True,
            owner_ids=OWNER_IDS
        )

    async def setup_hook(self):
        # Initialize SQLite database schema
        await db.init()
        print(f"{Fore.GREEN}[DATABASE]{Style.RESET_ALL} SQLite database initialized successfully.")

        # Load all cogs
        initial_extensions = [
            "cogs.moderation",
            "cogs.tickets",
            "cogs.welcomer",
            "cogs.gtn",
            "cogs.vouches",
            "cogs.trades",
            "cogs.shop",
            "cogs.fun",
            "cogs.help",
            "cogs.owner",
            "cogs.slash"
        ]

        for ext in initial_extensions:
            try:
                await self.load_extension(ext)
                print(f"{Fore.CYAN}[EXTENSION]{Style.RESET_ALL} Loaded {ext}")
            except Exception as e:
                print(f"{Fore.RED}[EXTENSION ERROR]{Style.RESET_ALL} Failed to load {ext}: {e}")

        # Extensions loaded successfully

    async def on_ready(self):
        try:
            synced = await self.tree.sync()
            print(f"{Fore.GREEN}[SLASH COMMANDS]{Style.RESET_ALL} Synced {len(synced)} slash commands.")
        except Exception as e:
            print(f"{Fore.YELLOW}[SLASH COMMANDS]{Style.RESET_ALL} Note: Tree sync will complete once connected: {e}")
        banner = f"""
{Fore.MAGENTA}====================================================
{Fore.CYAN}       ⚡ ZYATH MULTI-PURPOSE DISCORD BOT ⚡
{Fore.MAGENTA}====================================================
{Fore.YELLOW}  Logged in as : {self.user} (ID: {self.user.id})
{Fore.YELLOW}  Guilds Count : {len(self.guilds)}
{Fore.YELLOW}  Total Users  : {sum(g.member_count for g in self.guilds)}
{Fore.YELLOW}  Prefix       : {DEFAULT_PREFIX}
{Fore.MAGENTA}====================================================
{Fore.GREEN}  All Systems Live & Operational!
{Fore.MAGENTA}====================================================
"""
        print(banner)
        if not self.status_loop.is_running():
            self.status_loop.start()

    @tasks.loop(minutes=2)
    async def status_loop(self):
        activities = [
            discord.Activity(type=discord.ActivityType.watching, name=f"$help | {len(self.guilds)} servers"),
            discord.Activity(type=discord.ActivityType.playing, name="$gtn | Guess The Number!"),
            discord.Activity(type=discord.ActivityType.watching, name="Tickets & Trades ($mercy)"),
            discord.Activity(type=discord.ActivityType.listening, name="$shop | Browse & Order")
        ]
        for act in activities:
            try:
                await self.change_presence(activity=act, status=discord.Status.online)
                await asyncio.sleep(30)
            except Exception:
                pass

    @status_loop.before_loop
    async def before_status_loop(self):
        await self.wait_until_ready()

bot = ZyathBot()

# --- Global Command Error Handling ---
@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send(embed=error_embed(
            "Missing Argument",
            f"You missed a required parameter: `{error.param.name}`.\nUsage: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`"
        ))

    if isinstance(error, commands.MissingPermissions):
        perms = ", ".join(f"`{p}`" for p in error.missing_permissions)
        return await ctx.send(embed=error_embed("Missing Permissions", f"You need {perms} permission(s) to use this command."))

    if isinstance(error, commands.BotMissingPermissions):
        perms = ", ".join(f"`{p}`" for p in error.missing_permissions)
        return await ctx.send(embed=error_embed("Bot Missing Permissions", f"I need {perms} permission(s) to run this command."))

    if isinstance(error, commands.BadArgument):
        return await ctx.send(embed=error_embed("Invalid Argument", f"{str(error)}\nCheck `{ctx.prefix}help {ctx.command.name}` for usage."))

    if isinstance(error, commands.CheckFailure):
        return await ctx.send(embed=error_embed("Access Denied", "You do not have permission to run this command."))

    # Log unexpected errors to console
    print(f"{Fore.RED}[COMMAND ERROR in {ctx.command}]{Style.RESET_ALL} {error}")

if __name__ == "__main__":
    if not TOKEN or TOKEN == "your_bot_token_here":
        print(f"{Fore.RED}[CRITICAL ERROR]{Style.RESET_ALL} No valid DISCORD_TOKEN found in .env file!")
        print(f"{Fore.YELLOW}Please create a .env file and set DISCORD_TOKEN=your_token{Style.RESET_ALL}")
    else:
        bot.run(TOKEN)
