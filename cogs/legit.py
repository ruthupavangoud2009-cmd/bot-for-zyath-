import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db

class CheckTPaginationView(discord.ui.View):
    def __init__(self, vouches: list, guild: discord.Guild, shop_name: str, page: int = 0):
        super().__init__(timeout=120)
        self.vouches = vouches
        self.guild = guild
        self.shop_name = shop_name
        self.page = page
        self.per_page = 8
        self.max_page = max(0, (len(vouches) - 1) // self.per_page)
        self.update_buttons()

    def update_buttons(self):
        self.prev_btn.disabled = (self.page <= 0)
        self.next_btn.disabled = (self.page >= self.max_page)

    def get_embed(self) -> discord.Embed:
        start = self.page * self.per_page
        end = start + self.per_page
        chunk = self.vouches[start:end]

        embed = discord.Embed(
            title=f"📖 {self.shop_name} • Verified Community Vouches",
            color=0x57F287
        )
        desc = f"**Total Legit Vouches:** `{len(self.vouches)}`\n\n"
        if not chunk:
            desc += "*No vouches recorded yet.*"
        else:
            for idx, item in enumerate(chunk, start=start + 1):
                uid = item["user_id"]
                member = self.guild.get_member(uid)
                user_str = member.name if member else f"User {uid}"
                ts = item.get("timestamp", "Recent")
                desc += f"**#{idx}** • **{user_str}** (`{uid}`)\n└ 📅 <t:{int(discord.utils.utcnow().timestamp())}:d> • ✅ Verified\n"

        embed.description = desc
        embed.set_footer(text=f"Page {self.page + 1} of {max(1, self.max_page + 1)} • {self.shop_name}")
        return embed

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary, custom_id="checkt_prev")
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary, custom_id="checkt_next")
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.max_page:
            self.page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)

class LegitPanelView(discord.ui.View):
    def __init__(self, shop_name: str = "Jack's Shop"):
        super().__init__(timeout=None)
        self.shop_name = shop_name

    @discord.ui.button(label="Legit", style=discord.ButtonStyle.success, emoji="✅", custom_id="legit_vouch_btn")
    async def legit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.bot:
            return await interaction.response.send_message("Bots cannot vouch.", ephemeral=True)

        added, total = await db.toggle_legit_vouch(interaction.guild_id, interaction.user.id)
        cfg = await db.get_shop_config(interaction.guild_id)
        shop_title = cfg.get("shop_name", "Jack's Shop")

        if added:
            await interaction.response.send_message(
                embed=success_embed(
                    "Vouch Registered",
                    f"Thank you for vouching for **{shop_title}**!\n"
                    f"Current Trust Count: **{total}** verified vouches. ✅\n\n"
                    f"*(Click again anytime if you wish to withdraw your vouch)*"
                ),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=info_embed(
                    "Vouch Removed",
                    f"Your vouch for **{shop_title}** has been withdrawn.\n"
                    f"Current Trust Count: **{total}** verified vouches."
                ),
                ephemeral=True
            )

    @discord.ui.button(label="CheckT", style=discord.ButtonStyle.primary, emoji="📖", custom_id="legit_checkt_btn")
    async def checkt_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        vouches = await db.get_legit_vouches(interaction.guild_id, limit=200)
        cfg = await db.get_shop_config(interaction.guild_id)
        shop_title = cfg.get("shop_name", "Jack's Shop")

        view = CheckTPaginationView(vouches, interaction.guild, shop_title, page=0)
        await interaction.response.send_message(embed=view.get_embed(), view=view, ephemeral=True)

class Legit(commands.Cog):
    """Legit Counter and Shop Vouch System matching reference specifications."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(LegitPanelView())

    @commands.group(name="legit", aliases=["trusted", "vouchpanel"], invoke_without_command=True)
    async def legit_group(self, ctx: commands.Context):
        """Show current legit count or post the trusted shop panel."""
        count = await db.get_legit_count(ctx.guild.id)
        cfg = await db.get_shop_config(ctx.guild.id)
        shop_name = cfg.get("shop_name", "Jack's Shop")
        embed = standard_embed(
            title=f"✨ {shop_name} • Legitimacy Score",
            description=(
                f"> **Total Verified Vouches:** `{count}` ✅\n"
                f"> **Authenticity Status:** `100% Genuine & Trusted`\n\n"
                f"Type `$legit panel` to post the interactive Legit Panel."
            ),
            color=0x57F287
        )
        await ctx.send(embed=embed)

    @legit_group.command(name="panel")
    @commands.has_permissions(administrator=True)
    async def legit_panel_cmd(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Post the official 'Is Jack's Shop Trusted?' panel."""
        target_chan = channel or ctx.channel
        cfg = await db.get_shop_config(ctx.guild.id)
        shop_name = cfg.get("shop_name", "Jack's Shop")

        embed = discord.Embed(
            title=f"✨ Is {shop_name} Trusted?",
            description=f"If you find {shop_name} trusted, press the button below.",
            color=0x2B2D31
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=f"© {shop_name} | All Rights Reserved.")

        view = LegitPanelView(shop_name)
        await target_chan.send(embed=embed, view=view)
        if target_chan.id != ctx.channel.id:
            await ctx.send(embed=success_embed("Panel Sent", f"Legit panel posted in {target_chan.mention}!"))

    @legit_group.command(name="check")
    async def legit_check_cmd(self, ctx: commands.Context):
        """View the list of members who vouched for the shop."""
        vouches = await db.get_legit_vouches(ctx.guild.id, limit=200)
        cfg = await db.get_shop_config(ctx.guild.id)
        shop_name = cfg.get("shop_name", "Jack's Shop")

        view = CheckTPaginationView(vouches, ctx.guild, shop_name, page=0)
        await ctx.send(embed=view.get_embed(), view=view)

    @legit_group.command(name="remove")
    @commands.has_permissions(manage_messages=True)
    async def legit_remove_cmd(self, ctx: commands.Context, member: discord.Member):
        """Staff only: remove a user's vouch."""
        removed = await db.remove_legit_vouch(ctx.guild.id, member.id)
        if removed:
            count = await db.get_legit_count(ctx.guild.id)
            await ctx.send(embed=success_embed("Vouch Removed", f"Removed vouch from {member.mention}. Total now: `{count}`."))
        else:
            await ctx.send(embed=error_embed("Not Found", f"{member.mention} has not vouched."))

    @legit_group.command(name="reset")
    @commands.has_permissions(administrator=True)
    async def legit_reset_cmd(self, ctx: commands.Context):
        """Admin only: reset all legit vouches for this shop."""
        count = await db.reset_legit_vouches(ctx.guild.id)
        await ctx.send(embed=success_embed("Vouches Reset", f"Cleared `{count}` vouches from the shop ledger."))

    # --- Slash Commands ---
    @app_commands.command(name="legit", description="Shop legitimacy counter and vouch list.")
    @app_commands.describe(action="Choose action (check, panel, or stats)")
    @app_commands.choices(action=[
        app_commands.Choice(name="check", value="check"),
        app_commands.Choice(name="panel", value="panel"),
        app_commands.Choice(name="stats", value="stats")
    ])
    async def slash_legit(self, interaction: discord.Interaction, action: str):
        cfg = await db.get_shop_config(interaction.guild_id)
        shop_name = cfg.get("shop_name", "Jack's Shop")

        if action == "panel":
            if not interaction.user.guild_permissions.administrator:
                return await interaction.response.send_message(embed=error_embed("Unauthorized", "Admin only."), ephemeral=True)
            embed = discord.Embed(
                title=f"✨ Is {shop_name} Trusted?",
                description=f"If you find {shop_name} trusted, press the button below.",
                color=0x2B2D31
            )
            embed.set_footer(text=f"© {shop_name} | All Rights Reserved.")
            await interaction.response.send_message(embed=embed, view=LegitPanelView(shop_name))
        elif action == "check":
            vouches = await db.get_legit_vouches(interaction.guild_id, limit=200)
            view = CheckTPaginationView(vouches, interaction.guild, shop_name, page=0)
            await interaction.response.send_message(embed=view.get_embed(), view=view, ephemeral=True)
        else:
            count = await db.get_legit_count(interaction.guild_id)
            embed = standard_embed(
                title=f"✨ {shop_name} • Legitimacy Score",
                description=f"• **Total Verified Vouches:** `{count}` ✅\n• **Status:** `100% Genuine & Trusted`",
                color=0x57F287
            )
            await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Legit(bot))
