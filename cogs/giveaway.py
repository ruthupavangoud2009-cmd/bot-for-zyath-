import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import time
import re
import random
from typing import Optional, List
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db

def parse_duration(time_str: str) -> Optional[int]:
    """Parse time string like 30s, 10m, 2h, 1d, 1w into seconds."""
    time_str = time_str.lower().strip()
    match = re.match(r"^(\d+)([smhdw])$", time_str)
    if not match:
        return None
    amount, unit = int(match.group(1)), match.group(2)
    multipliers = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
        "w": 604800
    }
    return amount * multipliers.get(unit, 1)

class GiveawayJoinView(discord.ui.View):
    def __init__(self, message_id: int = 0, initial_count: int = 0):
        super().__init__(timeout=None)
        self.message_id = message_id
        # Dynamic enter button
        self.enter_btn = discord.ui.Button(
            label=f"Enter ({initial_count})",
            style=discord.ButtonStyle.success,
            emoji="🎉",
            custom_id="gw_btn_enter"
        )
        self.enter_btn.callback = self.enter_callback
        self.add_item(self.enter_btn)

        # Leave button
        self.leave_btn = discord.ui.Button(
            label="Leave",
            style=discord.ButtonStyle.secondary,
            emoji="🚪",
            custom_id="gw_btn_leave"
        )
        self.leave_btn.callback = self.leave_callback
        self.add_item(self.leave_btn)

        # Entrants list button
        self.entrants_btn = discord.ui.Button(
            label="Entrants",
            style=discord.ButtonStyle.primary,
            emoji="👥",
            custom_id="gw_btn_entrants"
        )
        self.entrants_btn.callback = self.entrants_callback
        self.add_item(self.entrants_btn)

    async def _resolve_gw(self, interaction: discord.Interaction):
        msg_id = self.message_id or interaction.message.id
        return await db.get_giveaway(msg_id)

    async def enter_callback(self, interaction: discord.Interaction):
        gw = await self._resolve_gw(interaction)
        if not gw or gw.get("status") != "active":
            return await interaction.response.send_message("❌ This giveaway is no longer active.", ephemeral=True)

        if int(time.time()) >= gw["end_time"]:
            return await interaction.response.send_message("⌛ This giveaway has already expired and is rolling winners!", ephemeral=True)

        # Check role requirement
        req_role_id = gw.get("requirements_role_id")
        if req_role_id and interaction.guild:
            role = interaction.guild.get_role(req_role_id)
            if role and role not in interaction.user.roles:
                return await interaction.response.send_message(
                    f"⛔ **Entry Requirement Not Met!**\nYou need the {role.mention} role to participate in this giveaway.",
                    ephemeral=True
                )

        # Add entrant
        already_entered = interaction.user.id in await db.get_giveaway_entrants(gw["id"])
        if already_entered:
            return await interaction.response.send_message("✅ You are already participating in this giveaway! Good luck!", ephemeral=True)

        await db.add_giveaway_entrant(gw["id"], interaction.user.id)
        count = await db.get_giveaway_entrants_count(gw["id"])

        # Update button label
        self.enter_btn.label = f"Enter ({count})"
        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass

        await interaction.response.send_message(
            f"🎉 **You're in!** You entered the giveaway for **{gw['prize']}**!\nGood luck, winner(s) will be drawn when the timer finishes.",
            ephemeral=True
        )

    async def leave_callback(self, interaction: discord.Interaction):
        gw = await self._resolve_gw(interaction)
        if not gw or gw.get("status") != "active":
            return await interaction.response.send_message("❌ This giveaway is no longer active.", ephemeral=True)

        entrants = await db.get_giveaway_entrants(gw["id"])
        if interaction.user.id not in entrants:
            return await interaction.response.send_message("ℹ️ You are not currently entered in this giveaway.", ephemeral=True)

        await db.remove_giveaway_entrant(gw["id"], interaction.user.id)
        count = await db.get_giveaway_entrants_count(gw["id"])

        self.enter_btn.label = f"Enter ({count})"
        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass

        await interaction.response.send_message(
            f"🚪 You have left the giveaway for **{gw['prize']}**.",
            ephemeral=True
        )

    async def entrants_callback(self, interaction: discord.Interaction):
        gw = await self._resolve_gw(interaction)
        if not gw:
            return await interaction.response.send_message("Giveaway details not found.", ephemeral=True)

        entrants = await db.get_giveaway_entrants(gw["id"])
        count = len(entrants)
        if count == 0:
            return await interaction.response.send_message("👥 **Current Entrants (0):**\nNo one has entered yet! Be the first!", ephemeral=True)

        # Preview up to 30
        preview = [f"<@{uid}>" for uid in entrants[:30]]
        more = f"\n*...and {count - 30} more*" if count > 30 else ""
        text = f"👥 **Total Entrants ({count}):**\n" + ", ".join(preview) + more
        await interaction.response.send_message(text, ephemeral=True)


class Giveaway(commands.Cog):
    """Ultimate Giveaway Suite with persistent storage, role requirements, live countdowns, and rerolls."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Register persistent view handler
        self.bot.add_view(GiveawayJoinView())
        self.check_giveaways.start()

    def cog_unload(self):
        self.check_giveaways.cancel()

    @tasks.loop(seconds=5)
    async def check_giveaways(self):
        """Check for expired giveaways every 5 seconds."""
        now = int(time.time())
        try:
            active_gws = await db.get_active_giveaways()
            for gw in active_gws:
                if gw["end_time"] <= now:
                    await self.finish_giveaway(gw)
        except Exception as e:
            # Avoid breaking loop on occasional network glitches
            pass

    @check_giveaways.before_loop
    async def before_check_giveaways(self):
        await self.bot.wait_until_ready()

    async def finish_giveaway(self, gw: dict):
        """Finish a giveaway, pick winners, edit embed, announce in channel, and DM winners."""
        await db.end_giveaway(gw["message_id"], status="ended")

        channel = self.bot.get_channel(gw["channel_id"])
        if not channel:
            try:
                channel = await self.bot.fetch_channel(gw["channel_id"])
            except Exception:
                return

        try:
            message = await channel.fetch_message(gw["message_id"])
        except Exception:
            return

        entrants = await db.get_giveaway_entrants(gw["id"])
        winners_count = gw.get("winners_count", 1) or 1
        prize = gw.get("prize", "Prize")
        host_id = gw.get("host_id")
        guild = channel.guild

        # Filter valid entrants still in guild and possessing requirements
        valid_entrants = []
        req_role_id = gw.get("requirements_role_id")
        for uid in entrants:
            m = guild.get_member(uid)
            if m:
                if req_role_id:
                    role = guild.get_role(req_role_id)
                    if role and role not in m.roles:
                        continue
                valid_entrants.append(uid)

        # Disable view buttons on ended giveaway
        disabled_view = discord.ui.View()
        disabled_view.add_item(discord.ui.Button(label=f"Ended ({len(entrants)} Entered)", style=discord.ButtonStyle.secondary, disabled=True, emoji="🔒"))

        if not valid_entrants:
            embed = standard_embed(
                title=f"🎉 GIVEAWAY ENDED: {prize}",
                description=(
                    "❌ **Giveaway Ended — No Winner!**\n\n"
                    "No valid members entered this giveaway before it expired.\n\n"
                    f"👑 **Hosted by:** <@{host_id}>\n"
                    f"📊 **Total Entrants:** `{len(entrants)}`"
                ),
                color=0xED4245
            )
            embed.set_footer(text=f"Ended • Zyath Giveaway Engine")
            try:
                await message.edit(embed=embed, view=disabled_view)
            except Exception:
                pass
            await channel.send(f"⚠️ The giveaway for **{prize}** has ended, but there were no valid entries to draw a winner from!")
            return

        # Pick random winners
        sampled_winners = random.sample(valid_entrants, k=min(winners_count, len(valid_entrants)))
        winners_mentions = ", ".join(f"<@{w}>" for w in sampled_winners)

        embed = standard_embed(
            title=f"🎉 GIVEAWAY ENDED: {prize} 🎉",
            description=(
                f"🏆 **Winner(s):** {winners_mentions}\n"
                f"👑 **Hosted by:** <@{host_id}>\n"
                f"📊 **Total Entrants:** `{len(entrants)}`\n"
                f"⏰ **Ended:** <t:{int(time.time())}:R>"
            ),
            color=0x57F287
        )
        embed.set_footer(text=f"Winners drawn! • Zyath Giveaway Engine")

        try:
            await message.edit(embed=embed, view=disabled_view)
        except Exception:
            pass

        # Celebratory announcement in channel
        win_msg = (
            f"🎊 **GIVEAWAY WINNER!** 🎊\n"
            f"Congratulations {winners_mentions}! You won the giveaway for **{prize}**! 🎁\n"
            f"Hosted by <@{host_id}> • [Jump to Giveaway]({message.jump_url})"
        )
        await channel.send(win_msg)

        # Attempt to DM each winner
        for winner_id in sampled_winners:
            try:
                winner_member = guild.get_member(winner_id)
                if winner_member:
                    dm_embed = standard_embed(
                        title="🎁 You Won a Giveaway!",
                        description=(
                            f"🎉 Congratulations **{winner_member.name}**!\n\n"
                            f"You just won **{prize}** in **{guild.name}**!\n\n"
                            f"👑 **Hosted by:** <@{host_id}>\n"
                            f"🔗 **Channel:** {channel.mention}\n\n"
                            f"Please contact <@{host_id}> or open a ticket to claim your prize!"
                        ),
                        color=0xFEE75C
                    )
                    dm_embed.set_footer(text=f"Server: {guild.name}")
                    await winner_member.send(embed=dm_embed)
            except Exception:
                pass

    # ==========================================
    # COMMANDS
    # ==========================================
    @commands.command(
        name="gstart",
        aliases=["giveaway", "gwstart"],
        help="Start a giveaway. E.g. $gstart 10m 1w $10 Nitro or $gstart 1h 2 Nitro Basic --role @VIP"
    )
    @commands.has_permissions(manage_messages=True)
    async def start_giveaway(self, ctx: commands.Context, duration_str: str, *args):
        """Start a new interactive giveaway with live timer and persistent DB."""
        duration_sec = parse_duration(duration_str)
        if not duration_sec or duration_sec < 10:
            return await ctx.send(embed=error_embed(
                "Invalid Duration",
                "Please specify a valid duration (minimum 10s).\nFormat examples: `30s`, `10m`, `2h`, `1d`, `1w`.\nUsage: `$gstart 10m 1w $10 Nitro`"
            ))

        if not args:
            return await ctx.send(embed=error_embed("Missing Prize", "Please specify the prize for the giveaway!\nUsage: `$gstart 10m 1w Discord Nitro`"))

        args_list = list(args)
        winners_count = 1

        # Check if first arg in args is winner count like '1w', '2w', '3'
        first_arg = args_list[0].lower()
        if re.match(r"^(\d+)w?$", first_arg):
            try:
                parsed_w = int(re.match(r"^(\d+)w?$", first_arg).group(1))
                if 1 <= parsed_w <= 50:
                    winners_count = parsed_w
                    args_list.pop(0)
            except Exception:
                pass

        if not args_list:
            return await ctx.send(embed=error_embed("Missing Prize", "Please provide a prize description!"))

        full_text = " ".join(args_list)

        # Check for role requirement option: --role @Role or --role 1234
        req_role = None
        if "--role" in full_text:
            parts = full_text.split("--role", 1)
            full_text = parts[0].strip()
            role_part = parts[1].strip()
            # Match role mention or ID
            role_match = re.search(r"(\d+)", role_part)
            if role_match:
                req_role = ctx.guild.get_role(int(role_match.group(1)))

        prize = full_text.strip()
        if not prize:
            return await ctx.send(embed=error_embed("Missing Prize", "Please specify what you are giving away!"))

        end_time = int(time.time()) + duration_sec

        req_text = f"\n📜 **Requirement:** {req_role.mention}" if req_role else ""

        embed = standard_embed(
            title=f"🎉 GIVEAWAY: {prize} 🎉",
            description=(
                f"Click the **🎉 Enter** button below to participate!\n\n"
                f"🏆 **Winners:** `{winners_count}`\n"
                f"👑 **Hosted by:** {ctx.author.mention}\n"
                f"⏰ **Ends:** <t:{end_time}:R> (<t:{end_time}:f>){req_text}\n\n"
                f"Good luck everyone!"
            ),
            color=0x5865F2
        )
        embed.set_footer(text=f"Zyath Ultimate Giveaway • Ends")
        embed.timestamp = discord.utils.utcnow() + discord.utils.get_as_snowflake(None) if False else None

        view = GiveawayJoinView(initial_count=0)
        msg = await ctx.send(content="🎉 **NEW GIVEAWAY!** 🎉", embed=embed, view=view)
        view.message_id = msg.id

        # Save to database
        await db.create_giveaway(
            guild_id=ctx.guild.id,
            channel_id=ctx.channel.id,
            message_id=msg.id,
            host_id=ctx.author.id,
            prize=prize,
            winners_count=winners_count,
            end_time=end_time,
            requirements_role_id=req_role.id if req_role else None
        )

        try:
            await ctx.message.delete()
        except Exception:
            pass

    @commands.command(name="gend", aliases=["gwstop", "endgw"], help="End an active giveaway early and pick winners. E.g. $gend <message_id>")
    @commands.has_permissions(manage_messages=True)
    async def end_giveaway_cmd(self, ctx: commands.Context, message_id: int):
        """End a giveaway early."""
        gw = await db.get_giveaway(message_id)
        if not gw:
            return await ctx.send(embed=error_embed("Not Found", "No giveaway found with that message ID."))

        if gw["status"] != "active":
            return await ctx.send(embed=info_embed("Already Ended", "This giveaway has already concluded."))

        await ctx.send(embed=info_embed("Ending Giveaway", "Rolling winners now..."))
        await self.finish_giveaway(gw)

    @commands.command(name="greroll", aliases=["reroll", "gwreroll"], help="Reroll new winner(s) for a finished giveaway. E.g. $greroll <message_id> [winners]")
    @commands.has_permissions(manage_messages=True)
    async def reroll_giveaway(self, ctx: commands.Context, message_id: int, winners: int = 1):
        """Reroll winner(s) from existing entrants."""
        gw = await db.get_giveaway(message_id)
        if not gw:
            return await ctx.send(embed=error_embed("Not Found", "No giveaway record found for that message ID."))

        entrants = await db.get_giveaway_entrants(gw["id"])
        if not entrants:
            return await ctx.send(embed=error_embed("No Entrants", "Nobody entered this giveaway, so it cannot be rerolled."))

        # Filter valid entrants still in guild
        valid = [uid for uid in entrants if ctx.guild.get_member(uid)]
        if not valid:
            return await ctx.send(embed=error_embed("No Valid Entrants", "None of the previous entrants are currently in the server."))

        picked = random.sample(valid, k=min(winners, len(valid)))
        mentions = ", ".join(f"<@{uid}>" for uid in picked)

        embed = standard_embed(
            title="🎲 Giveaway Rerolled!",
            description=(
                f"🎉 **New Winner(s):** {mentions}\n\n"
                f"🎁 **Prize:** `{gw['prize']}`\n"
                f"👑 **Hosted by:** <@{gw['host_id']}>\n"
                f"📊 Drawn from `{len(entrants)}` total entrants."
            ),
            color=0xFEE75C
        )
        embed.set_footer(text=f"Rerolled by {ctx.author.display_name}")

        await ctx.send(content=f"🎉 Congratulations {mentions}! You were drawn as the new winner for **{gw['prize']}**!", embed=embed)

    @commands.command(name="gcancel", aliases=["cancelgw", "gdelete"], help="Cancel an active giveaway without drawing winners. E.g. $gcancel <message_id>")
    @commands.has_permissions(manage_messages=True)
    async def cancel_giveaway(self, ctx: commands.Context, message_id: int):
        """Cancel an ongoing giveaway."""
        gw = await db.get_giveaway(message_id)
        if not gw:
            return await ctx.send(embed=error_embed("Not Found", "No giveaway found with that message ID."))

        if gw["status"] != "active":
            return await ctx.send(embed=info_embed("Not Active", "This giveaway is not currently active."))

        await db.end_giveaway(message_id, status="cancelled")

        try:
            channel = ctx.guild.get_channel(gw["channel_id"])
            if channel:
                msg = await channel.fetch_message(message_id)
                embed = standard_embed(
                    title=f"❌ GIVEAWAY CANCELLED: {gw['prize']}",
                    description=f"This giveaway was cancelled by {ctx.author.mention}.",
                    color=0xED4245
                )
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Cancelled", style=discord.ButtonStyle.secondary, disabled=True))
                await msg.edit(embed=embed, view=view)
        except Exception:
            pass

        await ctx.send(embed=success_embed("Giveaway Cancelled", f"Successfully cancelled giveaway for **{gw['prize']}**."))

    @commands.command(name="glist", aliases=["giveaways", "activegw"], help="View all active giveaways in the server.")
    async def list_giveaways(self, ctx: commands.Context):
        """List active giveaways in this server."""
        active = await db.get_active_giveaways(guild_id=ctx.guild.id)
        if not active:
            return await ctx.send(embed=info_embed("No Active Giveaways", "There are no active giveaways currently running in this server.\nStart one with `$gstart <time> [winners] <prize>`!"))

        embed = standard_embed(
            title=f"🎉 Active Giveaways • {ctx.guild.name}",
            description=f"Showing **{len(active)}** running giveaway(s):\n",
            color=0x5865F2
        )

        for gw in active[:10]:
            ch_str = f"<#{gw['channel_id']}>"
            time_str = f"<t:{gw['end_time']}:R>"
            count = await db.get_giveaway_entrants_count(gw["id"])
            link = f"https://discord.com/channels/{ctx.guild.id}/{gw['channel_id']}/{gw['message_id']}"
            embed.add_field(
                name=f"🎁 {gw['prize']} ({gw['winners_count']}w)",
                value=f"• **Channel:** {ch_str}\n• **Ends:** {time_str}\n• **Entries:** `{count}`\n• **Link:** [Jump to Message]({link})",
                inline=False
            )

        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Giveaway(bot))
