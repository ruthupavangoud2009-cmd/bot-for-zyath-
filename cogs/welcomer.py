import discord
from discord.ext import commands
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db
from utils.welcome_card import generate_welcome_card

class WelcomeQuickView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Browse Shop", style=discord.ButtonStyle.success, emoji="🛒", custom_id="welcome_shop_btn")
    async def shop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Open shop catalog for the user
        items = await db.get_shop_items(interaction.guild_id)
        if not items:
            return await interaction.response.send_message("No items currently in shop.", ephemeral=True)
        from cogs.shop import ShopView
        embed = standard_embed(
            title=f"🛒 {interaction.guild.name} Official Shop",
            description="Select an item from the dropdown below to order directly!",
            color=0x5763719
        )
        for item in items[:10]:
            embed.add_field(name=f"📦 {item['name']} — {item['price']}", value=f"*{item['description'] or 'In stock'}*", inline=False)
        await interaction.response.send_message(embed=embed, view=ShopView(items), ephemeral=True)

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="welcome_ticket_btn")
    async def ticket_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.tickets import TicketPanelView
        embed = standard_embed(
            title="🎫 Open a Support / Order Ticket",
            description="Select your desired category below to open a private ticket:"
        )
        await interaction.response.send_message(embed=embed, view=TicketPanelView(), ephemeral=True)

class Welcomer(commands.Cog):
    """Customizable visual welcome system with custom PIL banners, goodbye logger, and autorole."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(WelcomeQuickView())

    def format_text(self, template: str, member: discord.Member) -> str:
        if not template:
            return (
                f"Welcome to **{member.guild.name}**, {member.mention}! 🎉\n"
                f"We are excited to have you here! Check out our shop, open a ticket for questions, and enjoy your stay!"
            )
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

        # Welcome message embed + image banner
        channel_id = settings.get("welcome_channel_id")
        if channel_id:
            channel = member.guild.get_channel(channel_id)
            if channel and channel.permissions_for(member.guild.me).send_messages:
                custom_msg = settings.get("welcome_message")
                description = self.format_text(custom_msg, member)

                embed = standard_embed(
                    title=f"⚡ WELCOME TO {member.guild.name.upper()}!",
                    description=description,
                    color=0x5865F2,
                    thumbnail=member.display_avatar.url
                )
                embed.add_field(name="👤 Member", value=f"{member.mention} (`{member.id}`)", inline=True)
                embed.add_field(name="👥 Member Count", value=f"**#{member.guild.member_count:,}**", inline=True)
                created_ago = discord.utils.format_dt(member.created_at, style="R")
                embed.add_field(name="📅 Account Age", value=created_ago, inline=True)
                embed.set_footer(text=f"Welcome {member.name} • Have an amazing time!")

                try:
                    # Generate dynamic high-definition image card
                    welcome_file = await generate_welcome_card(member)
                    embed.set_image(url="attachment://welcome.png")
                    await channel.send(content=member.mention, embed=embed, file=welcome_file, view=WelcomeQuickView())
                except Exception as e:
                    print(f"Error sending welcome card: {e}")
                    await channel.send(content=member.mention, embed=embed, view=WelcomeQuickView())

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

    @commands.command(name="setwelcome", help="Set the channel where visual welcome messages are sent.")
    @commands.has_permissions(administrator=True)
    async def set_welcome(self, ctx: commands.Context, channel: discord.TextChannel):
        await db.update_guild_setting(ctx.guild.id, "welcome_channel_id", channel.id)
        await ctx.send(embed=success_embed("Welcome Channel Set", f"Welcome messages with custom visual cards will now be posted in {channel.mention}."))

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

    @commands.command(name="setwelcomemsg", help="Set custom welcome text. Placeholders: {user.mention}, {server}, {membercount}")
    @commands.has_permissions(administrator=True)
    async def set_welcome_msg(self, ctx: commands.Context, *, message: str):
        await db.update_guild_setting(ctx.guild.id, "welcome_message", message)
        await ctx.send(embed=success_embed("Welcome Message Updated", f"New welcome template:\n>>> {message}"))

    @commands.command(name="welcometest", help="Simulate and test your visual welcome card.")
    @commands.has_permissions(administrator=True)
    async def welcome_test(self, ctx: commands.Context):
        settings = await db.get_guild_settings(ctx.guild.id)
        custom_msg = settings.get("welcome_message")
        description = self.format_text(custom_msg, ctx.author)

        embed = standard_embed(
            title=f"⚡ WELCOME TO {ctx.guild.name.upper()}!",
            description=description,
            color=0x5865F2,
            thumbnail=ctx.author.display_avatar.url
        )
        embed.add_field(name="👤 Member", value=f"{ctx.author.mention} (`{ctx.author.id}`)", inline=True)
        embed.add_field(name="👥 Member Count", value=f"**#{ctx.guild.member_count:,}**", inline=True)
        created_ago = discord.utils.format_dt(ctx.author.created_at, style="R")
        embed.add_field(name="📅 Account Age", value=created_ago, inline=True)
        embed.set_footer(text="Zyath Bot • Dynamic Welcome Preview")

        try:
            welcome_file = await generate_welcome_card(ctx.author)
            embed.set_image(url="attachment://welcome.png")
            await ctx.send(content=ctx.author.mention, embed=embed, file=welcome_file, view=WelcomeQuickView())
        except Exception as e:
            await ctx.send(embed=error_embed("Error Generating Card", str(e)))

async def setup(bot: commands.Bot):
    await bot.add_cog(Welcomer(bot))
