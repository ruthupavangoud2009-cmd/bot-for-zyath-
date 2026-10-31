import discord
from discord.ext import commands
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db

class Welcomer(commands.Cog):
    """Customizable welcome system, goodbye logger, and autorole."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def format_text(self, template: str, member: discord.Member) -> str:
        if not template:
            return f"Welcome to the server, {member.mention}! We're thrilled to have you here."
        return (
            template.replace("{user}", str(member))
            .replace("{user.mention}", member.mention)
            .replace("{user.name}", member.name)
            .replace("{server}", member.guild.name)
            .replace("{membercount}", str(member.guild.member_count))
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        settings = await db.get_guild_settings(member.guild.id)

        # Autorole assignment
        autorole_id = settings.get("autorole_id")
        if autorole_id:
            role = member.guild.get_role(autorole_id)
            if role and member.guild.me.guild_permissions.manage_roles:
                try:
                    await member.add_roles(role, reason="Zyath Welcomer: Autorole")
                except Exception:
                    pass

        # Welcome message embed
        channel_id = settings.get("welcome_channel_id")
        if channel_id:
            channel = member.guild.get_channel(channel_id)
            if channel and channel.permissions_for(member.guild.me).send_messages:
                custom_msg = settings.get("welcome_message")
                description = self.format_text(custom_msg, member)

                embed = standard_embed(
                    title=f"👋 Welcome to {member.guild.name}!",
                    description=description,
                    thumbnail=member.display_avatar.url
                )
                embed.add_field(name="👤 User", value=member.mention, inline=True)
                embed.add_field(name="👥 Member Count", value=f"#{member.guild.member_count}", inline=True)
                created_ago = discord.utils.format_dt(member.created_at, style="R")
                embed.add_field(name="📅 Account Created", value=created_ago, inline=False)
                
                if member.guild.icon:
                    embed.set_author(name=member.guild.name, icon_url=member.guild.icon.url)

                try:
                    await channel.send(content=member.mention, embed=embed)
                except Exception:
                    pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        settings = await db.get_guild_settings(member.guild.id)
        channel_id = settings.get("leave_channel_id")
        if channel_id:
            channel = member.guild.get_channel(channel_id)
            if channel and channel.permissions_for(member.guild.me).send_messages:
                embed = standard_embed(
                    title="👋 Member Left",
                    description=f"**{member}** has left the server.\nWe now have **{member.guild.member_count}** members.",
                    color=0xED4245,
                    thumbnail=member.display_avatar.url
                )
                try:
                    await channel.send(embed=embed)
                except Exception:
                    pass

    @commands.command(name="setwelcome", help="Set the channel where welcome messages are sent.")
    @commands.has_permissions(administrator=True)
    async def set_welcome(self, ctx: commands.Context, channel: discord.TextChannel):
        await db.update_guild_setting(ctx.guild.id, "welcome_channel_id", channel.id)
        await ctx.send(embed=success_embed("Welcome Channel Set", f"Welcome messages will now be posted in {channel.mention}."))

    @commands.command(name="setleave", help="Set the channel where member leave logs are sent.")
    @commands.has_permissions(administrator=True)
    async def set_leave(self, ctx: commands.Context, channel: discord.TextChannel):
        await db.update_guild_setting(ctx.guild.id, "leave_channel_id", channel.id)
        await ctx.send(embed=success_embed("Leave Channel Set", f"Leave notifications will now be posted in {channel.mention}."))

    @commands.command(name="setautorole", help="Set the role given to new members automatically.")
    @commands.has_permissions(administrator=True)
    async def set_autorole(self, ctx: commands.Context, role: discord.Role):
        if role >= ctx.guild.me.top_role:
            return await ctx.send(embed=error_embed("Hierarchy Error", "That role is higher or equal to my highest role, so I cannot assign it."))
        await db.update_guild_setting(ctx.guild.id, "autorole_id", role.id)
        await ctx.send(embed=success_embed("Auto Role Set", f"New members will automatically receive {role.mention}."))

    @commands.command(name="setwelcomemsg", help="Set a custom welcome message template. Placeholders: {user.mention}, {server}, {membercount}")
    @commands.has_permissions(administrator=True)
    async def set_welcome_msg(self, ctx: commands.Context, *, message: str):
        await db.update_guild_setting(ctx.guild.id, "welcome_message", message)
        await ctx.send(embed=success_embed("Welcome Message Updated", f"New welcome template:\n>>> {message}"))

    @commands.command(name="welcometest", help="Simulate a welcome message for yourself.")
    @commands.has_permissions(administrator=True)
    async def welcome_test(self, ctx: commands.Context):
        settings = await db.get_guild_settings(ctx.guild.id)
        custom_msg = settings.get("welcome_message")
        description = self.format_text(custom_msg, ctx.author)

        embed = standard_embed(
            title=f"👋 Welcome to {ctx.guild.name}!",
            description=description,
            thumbnail=ctx.author.display_avatar.url
        )
        embed.add_field(name="👤 User", value=ctx.author.mention, inline=True)
        embed.add_field(name="👥 Member Count", value=f"#{ctx.guild.member_count}", inline=True)
        created_ago = discord.utils.format_dt(ctx.author.created_at, style="R")
        embed.add_field(name="📅 Account Created", value=created_ago, inline=False)
        embed.set_footer(text="Zyath Bot • Test Preview")
        await ctx.send(content=ctx.author.mention, embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Welcomer(bot))
