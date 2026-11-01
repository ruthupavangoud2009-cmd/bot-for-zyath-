import discord
from discord.ext import commands
from cogs.gw_games import GWGames, GuessTheNumber

async def setup(bot: commands.Bot):
    # Backward compatibility redirect to GWGames
    if not bot.get_cog("GWGames"):
        await bot.add_cog(GWGames(bot))
