import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, List, Dict, Any
from datetime import datetime
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db
from utils.config_manager import get_bot_name

def get_reputation_tier(count: int) -> tuple[str, str]:
    """Return reputation tier title and star representation based on vouch count."""
    if count >= 100:
        return "💎 DIAMOND TRUSTED MERCHANT (God Tier)", "⭐⭐⭐⭐⭐"
    elif count >= 50:
        return "🥇 PLATINUM TRUSTED VENDOR (Elite Tier)", "⭐⭐⭐⭐⭐"
    elif count >= 20:
        return "🥈 GOLD VERIFIED SHOP (Highly Trusted)", "⭐⭐⭐⭐"
    elif count >= 5:
        return "🥉 SILVER VERIFIED SHOP (Trusted)", "⭐⭐⭐"
    else:
        return "🔰 VERIFIED COMMUNITY SHOP (Emerging)", "⭐⭐"

def format_vouch_timestamp(ts: Any) -> str:
    """Format stored timestamp into a clean Discord relative timestamp."""
    if not ts:
        return "Recently"
    if hasattr(ts, "timestamp"):
        return f"<t:{int(ts.timestamp())}:R>"
    if isinstance(ts, str):
        try:
            clean_ts = ts.split(".")[0].replace("T", " ")
            parsed = datetime.fromisoformat(clean_ts)
            return f"<t:{int(parsed.timestamp())}:R>"
        except Exception:
            return ts
    return "Recently"

def build_legit_panel_embed(shop_name: str, guild: Optional[discord.Guild], count: int) -> discord.Embed:
    """Construct a high-end, aesthetic trust panel embed for Kyoka Shop."""
    tier_title, stars = get_reputation_tier(count)
    embed = discord.Embed(
        title=f"✨ Is {shop_name} Trusted?",
        description=(
            f"Welcome to **{shop_name}**! Customer satisfaction, lightning-fast delivery, and verified security are our core commitments.\n\n"
            f"```ansi\n"
            f"\u001b[1;32m● Store Status: 100% Genuine & Verified Storefront\u001b[0m\n"
            f"\u001b[1;36m● Delivery: Instant & Automated LTC / Crypto\u001b[0m\n"
            f"\u001b[1;33m● Support: 24/7 Dedicated Staff Assistance\u001b[0m\n"
            f"```\n"
            f"### 🌟 Verified Community Vouches: `{count}` ✅\n"
            f"> **Reputation Tier:** `{tier_title}`\n"
            f"> **Rating:** {stars}\n\n"
            f"**Have you dealt with {shop_name}?**\n"
            f"• Click **`✅ Legit`** below to cast your verified trust vouch.\n"
            f"• Click **`📖 CheckT`** to inspect the public trust ledger."
        ),
        color=0x2B2D31
    )
    if guild and guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text=f"© {shop_name} • Official Trust & Reputation System | All Rights Reserved")
    return embed

class CheckTPaginationView(discord.ui.View):
    def __init__(self, vouches: list, guild: discord.Guild, shop_name: str, page: int = 0):
        super().__init__(timeout=120)
        self.vouches = vouches
        self.guild = guild
        self.shop_name = shop_name or "Kyoka Shop"
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
            title=f"📖 {self.shop_name} • Verified Community Trust Ledger",
            color=0x57F287
        )
        desc = (
            f"> **Total Verified Vouches:** `{len(self.vouches)}` ✅\n"
            f"> **Ledger Status:** `100% Genuine Community Feedback`\n\n"
        )
        if not chunk:
            desc += "*No vouches recorded yet. Be the first to vouch!*"
        else:
            for idx, item in enumerate(chunk, start=start + 1):
                uid = item["user_id"]
                member = self.guild.get_member(uid) if self.guild else None
                user_label = f"**{member.display_name}**" if member else f"`User {uid}`"
                mention_str = f"<@{uid}>"
                time_str = format_vouch_timestamp(item.get("timestamp"))
                desc += f"`#{idx:02d}` • {mention_str} ({user_label})\n└ 📅 Vouched: {time_str} • ✅ Verified\n"

        embed.description = desc
        embed.set_footer(text=f"Page {self.page + 1} of {max(1, self.max_page + 1)} • {self.shop_name}")
        if self.guild and self.guild.icon:
            embed.set_thumbnail(url=self.guild.icon.url)
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
    def __init__(self, shop_name: str = "Kyoka Shop"):
        super().__init__(timeout=None)
        self.shop_name = shop_name or "Kyoka Shop"

    @discord.ui.button(label="Legit", style=discord.ButtonStyle.success, emoji="✅", custom_id="legit_vouch_btn")
    async def legit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.bot:
            return await interaction.response.send_message("Bots cannot vouch.", ephemeral=True)

        added, total = await db.toggle_legit_vouch(interaction.guild_id, interaction.user.id)
        cfg = await db.get_shop_config(interaction.guild_id)
        shop_title = cfg.get("shop_name") or get_bot_name()

        tier_title, stars = get_reputation_tier(total)

        if added:
            await interaction.response.send_message(
                embed=success_embed(
                    "✨ Vouch Registered!",
                    f"Thank you for vouching for **{shop_title}**!\n\n"
                    f"📊 **Current Community Trust:** `{total}` verified vouches ✅\n"
                    f"⭐ **Store Rating:** {stars} (`{tier_title}`)\n"
                    f"🛡️ Your trust helps new customers purchase with confidence.\n\n"
                    f"*(Click the button again anytime if you ever wish to withdraw your vouch)*"
                ),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=info_embed(
                    "↩️ Vouch Withdrawn",
                    f"Your vouch for **{shop_title}** has been removed.\n\n"
                    f"📊 **Current Community Trust:** `{total}` verified vouches."
                ),
                ephemeral=True
            )

    @discord.ui.button(label="CheckT", style=discord.ButtonStyle.primary, emoji="📖", custom_id="legit_checkt_btn")
    async def checkt_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        vouches = await db.get_legit_vouches(interaction.guild_id, limit=200)
        cfg = await db.get_shop_config(interaction.guild_id)
        shop_title = cfg.get("shop_name") or get_bot_name()

        view = CheckTPaginationView(vouches, interaction.guild, shop_title, page=0)
        await interaction.response.send_message(embed=view.get_embed(), view=view, ephemeral=True)

class Legit(commands.Cog):
    """Legit Counter and Shop Vouch System matching reference specifications."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(LegitPanelView())

    @commands.group(name="legit", aliases=["trusted", "vouchpanel"], invoke_without_command=True)
    async def legit_group(self, ctx: commands.Context):
        """Show current legit count and shop trust score."""
        count = await db.get_legit_count(ctx.guild.id)
        cfg = await db.get_shop_config(ctx.guild.id)
        shop_name = cfg.get("shop_name") or get_bot_name()
        tier_title, stars = get_reputation_tier(count)

        embed = discord.Embed(
            title=f"🛡️ {shop_name} • Trust & Legitimacy Score",
            description=(
                f"### {stars}\n"
                f"> **Total Verified Vouches:** `{count}` ✅\n"
                f"> **Merchant Tier:** `{tier_title}`\n"
                f"> **Authenticity Status:** `100% Genuine & Community Backed`\n\n"
                f"• Type **`$legit panel`** to post the interactive vouch panel.\n"
                f"• Type **`$legit check`** to view the verified vouches ledger."
            ),
            color=0x57F287
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=f"© {shop_name} • Verified Shop Reputation System")
        await ctx.send(embed=embed)

    @legit_group.command(name="panel")
    @commands.has_permissions(administrator=True)
    async def legit_panel_cmd(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Post the official 'Is Kyoka Shop Trusted?' panel."""
        target_chan = channel or ctx.channel
        cfg = await db.get_shop_config(ctx.guild.id)
        shop_name = cfg.get("shop_name") or get_bot_name()
        count = await db.get_legit_count(ctx.guild.id)

        embed = build_legit_panel_embed(shop_name, ctx.guild, count)
        view = LegitPanelView(shop_name)
        await target_chan.send(embed=embed, view=view)
        if target_chan.id != ctx.channel.id:
            await ctx.send(embed=success_embed("Panel Sent", f"Legit panel posted in {target_chan.mention}!"))

    @legit_group.command(name="check")
    async def legit_check_cmd(self, ctx: commands.Context):
        """View the list of members who vouched for the shop."""
        vouches = await db.get_legit_vouches(ctx.guild.id, limit=200)
        cfg = await db.get_shop_config(ctx.guild.id)
        shop_name = cfg.get("shop_name") or get_bot_name()

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
        shop_name = cfg.get("shop_name") or get_bot_name()

        if action == "panel":
            if not interaction.user.guild_permissions.administrator:
                return await interaction.response.send_message(embed=error_embed("Unauthorized", "Admin only."), ephemeral=True)
            count = await db.get_legit_count(interaction.guild_id)
            embed = build_legit_panel_embed(shop_name, interaction.guild, count)
            await interaction.response.send_message(embed=embed, view=LegitPanelView(shop_name))
        elif action == "check":
            vouches = await db.get_legit_vouches(interaction.guild_id, limit=200)
            view = CheckTPaginationView(vouches, interaction.guild, shop_name, page=0)
            await interaction.response.send_message(embed=view.get_embed(), view=view, ephemeral=True)
        else:
            count = await db.get_legit_count(interaction.guild_id)
            tier_title, stars = get_reputation_tier(count)
            embed = discord.Embed(
                title=f"🛡️ {shop_name} • Trust & Legitimacy Score",
                description=(
                    f"### {stars}\n"
                    f"> **Total Verified Vouches:** `{count}` ✅\n"
                    f"> **Merchant Tier:** `{tier_title}`\n"
                    f"> **Authenticity Status:** `100% Genuine & Community Backed`"
                ),
                color=0x57F287
            )
            if interaction.guild and interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.set_footer(text=f"© {shop_name} • Verified Shop Reputation System")
            await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Legit(bot))
