import discord
from discord.ext import commands
import datetime
import time
from typing import Optional
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db

OWNER_IDS = {1521774957065928734, 1505515188991033409}

def is_bot_staff_or_owner():
    async def predicate(ctx: commands.Context):
        if ctx.author.id in OWNER_IDS or await ctx.bot.is_owner(ctx.author) or db.is_staff_cached(ctx.author.id):
            return True
        await ctx.send(embed=error_embed("Access Denied", "⛔ Restricted to bot owners and authorized bot staff."))
        return False
    return commands.check(predicate)

class Premium(commands.Cog):
    """Elite Premium Subscription System for Guilds and Members."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def parse_duration(self, duration_str: str) -> Optional[datetime.datetime]:
        """Parses durations like '30d', '1y', 'lifetime', 'permanent'."""
        d = duration_str.lower().strip()
        if d in ["permanent", "lifetime", "forever", "perm", "inf"]:
            return None
        
        now = datetime.datetime.utcnow()
        if d.endswith("d") and d[:-1].isdigit():
            return now + datetime.timedelta(days=int(d[:-1]))
        elif d.endswith("m") and d[:-1].isdigit():
            return now + datetime.timedelta(days=int(d[:-1]) * 30)
        elif d.endswith("y") and d[:-1].isdigit():
            return now + datetime.timedelta(days=int(d[:-1]) * 365)
        elif d.isdigit():
            return now + datetime.timedelta(days=int(d))
        return None

    # ==========================================
    # 1. USER & SERVER PREMIUM STATUS
    # ==========================================
    @commands.group(name="premium", aliases=["perks", "vip"], invoke_without_command=True, help="Check current server and user premium status and perks.")
    async def premium_status(self, ctx: commands.Context):
        guild_id = ctx.guild.id
        user_id = ctx.author.id

        is_guild_prem = db.is_guild_premium(guild_id)
        is_user_prem = db.is_user_premium(user_id)

        guild_prem_data = await db.get_premium(guild_id) if is_guild_prem else None
        user_prem_data = await db.get_premium(user_id) if is_user_prem else None

        def format_badge(data):
            if not data:
                return "⚪ **Inactive**"
            exp = data.get("expires_at")
            if not exp:
                return f"🌟 **Active** (Lifetime / Permanent)"
            if isinstance(exp, str):
                return f"🌟 **Active** (`{exp[:10]}`)"
            ts = int(exp.timestamp())
            return f"🌟 **Active** (Expires <t:{ts}:R>)"

        embed = standard_embed(
            title="💎 Zyath Elite Premium Status",
            description=(
                "> Unlock exclusive server perks, 2x economy rewards, priority queues, and custom branding.\n\n"
                f"• **This Server:** {format_badge(guild_prem_data)}\n"
                f"• **Your Account:** {format_badge(user_prem_data)}\n\n"
                "**👑 Active Premium Perks:**\n"
                "✨ **2x Daily Coins:** Double rewards on `$daily` streak.\n"
                "🎰 **High-Roller Limits:** Bet up to 250,000 coins on `$slots` and `$gamble`.\n"
                "🎫 **Unlimited Ticket Categories:** No restrictions on modular ticket setups.\n"
                "🚀 **Multi-Winner Boosts:** Run giveaways with up to 20 winners simultaneously.\n"
                "🛡️ **VIP AutoMod Sensitivity:** Ultra-fast sub-second spam and raid suppression.\n"
                "💎 **Exclusive Profile Badge:** Glowing VIP crown in profile lookups."
            ),
            color=0xF1C40F
        )
        embed.set_footer(text="To upgrade this server or your account, contact bot owners via $support.")
        await ctx.send(embed=embed)

    # ==========================================
    # 2. OWNER & STAFF MANAGEMENT COMMANDS
    # ==========================================
    @premium_status.command(name="add", aliases=["grant"], help="Grant premium to a server or user. E.g. $premium add 123456789 30d [Tier]")
    @is_bot_staff_or_owner()
    async def add_premium_cmd(self, ctx: commands.Context, target: str, duration: str = "lifetime", *, tier: str = "Premium"):
        clean_id = target.strip().replace("<@", "").replace(">", "").replace("!", "").replace("&", "")
        if not clean_id.isdigit():
            return await ctx.send(embed=error_embed("Invalid Target", "Please provide a valid 64-bit Discord Guild ID or User ID."))

        target_id = int(clean_id)
        
        # Determine target type
        is_guild = self.bot.get_guild(target_id) is not None
        target_type = "guild" if is_guild else "user"
        
        exp_dt = self.parse_duration(duration)

        await db.add_premium(target_id, target_type, tier, exp_dt, ctx.author.id)

        exp_str = f"until <t:{int(exp_dt.timestamp())}:f>" if exp_dt else "**Lifetime / Permanent**"
        
        embed = success_embed(
            "💎 Premium Activated",
            f"Successfully granted **{tier}** to {target_type.upper()} `{target_id}`!\n\n"
            f"• **Type:** `{target_type.capitalize()}`\n"
            f"• **Duration:** {exp_str}\n"
            f"• **Staff Handler:** {ctx.author.mention}\n"
            f"• **Database Sync:** Saved permanently across restarts."
        )
        await ctx.send(embed=embed)

    @premium_status.command(name="remove", aliases=["del", "revoke"], help="Revoke premium from a server or user. E.g. $premium remove 123456789")
    @is_bot_staff_or_owner()
    async def remove_premium_cmd(self, ctx: commands.Context, target: str):
        clean_id = target.strip().replace("<@", "").replace(">", "").replace("!", "")
        if not clean_id.isdigit():
            return await ctx.send(embed=error_embed("Invalid Target", "Please provide a valid Discord Guild ID or User ID."))

        target_id = int(clean_id)
        removed = await db.remove_premium(target_id)
        if removed:
            await ctx.send(embed=success_embed("Premium Revoked", f"Successfully revoked premium status from `{target_id}`."))
        else:
            await ctx.send(embed=error_embed("Not Found", f"No active premium record found for `{target_id}`."))

    @premium_status.command(name="list", help="List all active premium servers and members.")
    @is_bot_staff_or_owner()
    async def list_premium_cmd(self, ctx: commands.Context):
        records = await db.get_all_premium()
        if not records:
            return await ctx.send(embed=info_embed("Premium Directory", "No active premium subscriptions currently registered."))

        guild_lines = []
        user_lines = []

        now = time.time()
        for r in records:
            tid = r["target_id"]
            ttype = r["target_type"]
            tier = r["tier"]
            exp = r["expires_at"]

            exp_str = "Permanent"
            if exp:
                if isinstance(exp, str):
                    exp_str = exp[:10]
                else:
                    exp_str = f"<t:{int(exp.timestamp())}:R>"

            entry = f"• `{tid}` — **{tier}** ({exp_str})"
            if ttype == "guild":
                g = self.bot.get_guild(tid)
                name = f" ({g.name})" if g else ""
                guild_lines.append(f"• `{tid}`{name} — **{tier}** ({exp_str})")
            else:
                user_lines.append(entry)

        desc = ""
        if guild_lines:
            desc += "**🏰 Premium Servers:**\n" + "\n".join(guild_lines) + "\n\n"
        if user_lines:
            desc += "**👑 Premium Users:**\n" + "\n".join(user_lines)

        embed = standard_embed(
            title="💎 Official Premium Directory",
            description=desc or "No records.",
            color=0xF1C40F
        )
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Premium(bot))
