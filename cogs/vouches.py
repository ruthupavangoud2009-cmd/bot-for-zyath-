import discord
from discord.ext import commands
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db

class Vouches(commands.Cog):
    """Vouch logger system to record reputations and ratings."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="setvouchchannel", help="Set the channel where all vouches will be logged.")
    @commands.has_permissions(administrator=True)
    async def set_vouch_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        await db.update_guild_setting(ctx.guild.id, "vouch_channel_id", channel.id)
        await ctx.send(embed=success_embed("Vouch Channel Configured", f"Vouches will be logged in {channel.mention}."))

    @commands.command(name="vouch", help="Vouch for a user. E.g. $vouch @user 5 Fast and legit trader!")
    async def vouch(self, ctx: commands.Context, member: discord.Member, *args):
        if member.id == ctx.author.id:
            return await ctx.send(embed=error_embed("Invalid Target", "You cannot vouch for yourself!"))
        if member.bot:
            return await ctx.send(embed=error_embed("Invalid Target", "You cannot vouch for a bot."))

        if not args:
            return await ctx.send(embed=error_embed("Missing Details", "Please provide a comment. Usage: `$vouch @user [1-5 stars] <comment>`"))

        # Check if first arg is stars number
        first_arg = args[0]
        if first_arg.isdigit() and 1 <= int(first_arg) <= 5:
            stars = int(first_arg)
            comment = " ".join(args[1:])
        else:
            stars = 5
            comment = " ".join(args)

        if not comment.strip():
            comment = "Positive vouch! Trusted user."

        vouch_id = await db.add_vouch(ctx.guild.id, member.id, ctx.author.id, stars, comment)
        total_vouches, avg_stars = await db.get_vouch_stats(ctx.guild.id, member.id)

        star_emojis = "⭐" * stars

        # Vouch log embed
        embed = standard_embed(
            title="⭐ New Vouch Received!",
            description=(
                f"**Vouched User:** {member.mention} (`{member.id}`)\n"
                f"**Vouched By:** {ctx.author.mention} (`{ctx.author.id}`)\n"
                f"**Rating:** {star_emojis} (`{stars}/5`)\n"
                f"**Comment:**\n>>> {comment}\n\n"
                f"📊 **User Reputation:** `{total_vouches}` Total Vouches • ⭐ `{avg_stars}/5.0` Avg"
            ),
            color=0xFEE75C,
            thumbnail=member.display_avatar.url
        )
        embed.set_footer(text=f"Vouch #{vouch_id} • Zyath Vouch Logger")

        # Post to vouch channel if configured
        settings = await db.get_guild_settings(ctx.guild.id)
        vouch_channel_id = settings.get("vouch_channel_id")
        logged_channel = None

        if vouch_channel_id:
            vouch_channel = ctx.guild.get_channel(vouch_channel_id)
            if vouch_channel and vouch_channel.permissions_for(ctx.guild.me).send_messages:
                await vouch_channel.send(embed=embed)
                logged_channel = vouch_channel

        if logged_channel and logged_channel.id != ctx.channel.id:
            await ctx.send(embed=success_embed(
                "Vouch Submitted",
                f"Your vouch for {member.mention} has been logged in {logged_channel.mention}!\nTotal vouches: **{total_vouches}**"
            ))
        else:
            await ctx.send(embed=embed)

    @commands.command(name="vouches", aliases=["rep", "reputation"], help="Check vouches for yourself or another user.")
    async def view_vouches(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        vouches = await db.get_vouches(ctx.guild.id, member.id)
        total_vouches, avg_stars = await db.get_vouch_stats(ctx.guild.id, member.id)

        if not vouches:
            return await ctx.send(embed=info_embed(
                f"Vouches for {member.display_name}",
                f"{member.mention} currently has no vouches in this server."
            ))

        desc = f"📊 **Total Vouches:** `{total_vouches}`\n⭐ **Average Rating:** `{avg_stars}/5.0`\n\n**Recent Vouches:**\n"
        for v in vouches[:8]:
            stars_str = "⭐" * v['stars']
            desc += f"• **{stars_str}** by <@{v['author_id']}> ({v['timestamp']})\n  *{v['comment']}*\n\n"

        embed = standard_embed(
            title=f"⭐ Reputation Profile: {member.display_name}",
            description=desc,
            thumbnail=member.display_avatar.url,
            color=0xFEE75C
        )
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Vouches(bot))
