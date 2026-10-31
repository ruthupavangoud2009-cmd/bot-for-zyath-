import discord
from discord.ext import commands
import random
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db

class TradeStatusView(discord.ui.View):
    def __init__(self, trade_id: str, mm_id: int):
        super().__init__(timeout=None)
        self.trade_id = trade_id
        self.mm_id = mm_id

    @discord.ui.button(label="Mark Completed", style=discord.ButtonStyle.success, emoji="✅", custom_id="trade_complete_btn")
    async def mark_complete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.mm_id and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(embed=error_embed("Unauthorized", "Only the assigned Middleman or an Admin can update this trade."), ephemeral=True)

        await db.update_trade_status(self.trade_id, "Completed")
        embed = interaction.message.embeds[0]
        embed.color = 0x57F287
        
        # Update status field
        for i, field in enumerate(embed.fields):
            if field.name == "📊 Status":
                embed.set_field_at(i, name="📊 Status", value="🟢 **Completed & Verified**", inline=True)
                break

        button.disabled = True
        # disable cancel button too
        for child in self.children:
            child.disabled = True

        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(embed=success_embed("Trade Completed", f"Trade **#{self.trade_id}** marked as Completed!"))

    @discord.ui.button(label="Cancel Trade", style=discord.ButtonStyle.danger, emoji="❌", custom_id="trade_cancel_btn")
    async def mark_cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.mm_id and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(embed=error_embed("Unauthorized", "Only the assigned Middleman or an Admin can cancel this trade."), ephemeral=True)

        await db.update_trade_status(self.trade_id, "Cancelled")
        embed = interaction.message.embeds[0]
        embed.color = 0xED4245

        for i, field in enumerate(embed.fields):
            if field.name == "📊 Status":
                embed.set_field_at(i, name="📊 Status", value="🔴 **Cancelled / Refunded**", inline=True)
                break

        for child in self.children:
            child.disabled = True

        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(embed=error_embed("Trade Cancelled", f"Trade **#{self.trade_id}** was cancelled."))

class MercyModal(discord.ui.Modal, title="Mercy • Log MM Transaction"):
    buyer = discord.ui.TextInput(
        label="Buyer (Mention or ID)",
        placeholder="@Buyer or 123456789",
        required=True
    )
    seller = discord.ui.TextInput(
        label="Seller (Mention or ID)",
        placeholder="@Seller or 987654321",
        required=True
    )
    amount = discord.ui.TextInput(
        label="Trade Value / Amount",
        placeholder="$50.00 / 5,000 Robux / 0.02 ETH",
        required=True
    )
    details = discord.ui.TextInput(
        label="Items / Deal Details",
        placeholder="e.g. Account + 2x Limiteds for PayPal",
        style=discord.TextStyle.paragraph,
        required=True
    )

    def __init__(self, bot, target_channel: discord.TextChannel):
        super().__init__()
        self.bot = bot
        self.target_channel = target_channel

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        trade_id = f"TRD-{random.randint(1000, 9999)}"

        # Resolve buyer and seller
        def parse_user_str(raw: str):
            clean = raw.replace("<@", "").replace(">", "").replace("!", "").strip()
            if clean.isdigit():
                m = guild.get_member(int(clean))
                if m:
                    return m
            return raw

        buyer_obj = parse_user_str(self.buyer.value)
        seller_obj = parse_user_str(self.seller.value)

        buyer_mention = buyer_obj.mention if isinstance(buyer_obj, discord.Member) else str(buyer_obj)
        seller_mention = seller_obj.mention if isinstance(seller_obj, discord.Member) else str(seller_obj)

        buyer_id = buyer_obj.id if isinstance(buyer_obj, discord.Member) else 0
        seller_id = seller_obj.id if isinstance(seller_obj, discord.Member) else 0

        embed = standard_embed(
            title=f"🤝 Live Trade Receipt • #{trade_id}",
            description="A new official Middleman transaction is currently active.",
            color=0xFEE75C
        )
        embed.add_field(name="🛡️ Middleman (MM)", value=interaction.user.mention, inline=True)
        embed.add_field(name="👤 Buyer", value=buyer_mention, inline=True)
        embed.add_field(name="📦 Seller", value=seller_mention, inline=True)
        embed.add_field(name="💰 Value / Amount", value=f"`{self.amount.value}`", inline=True)
        embed.add_field(name="📊 Status", value="🟡 **In Progress**", inline=True)
        embed.add_field(name="📝 Deal Details", value=f"```{self.details.value}```", inline=False)
        embed.set_footer(text=f"Trade ID: {trade_id} • Zyath Live MM Logger")

        view = TradeStatusView(trade_id=trade_id, mm_id=interaction.user.id)
        msg = await self.target_channel.send(content=f"{buyer_mention} {seller_mention}", embed=embed, view=view)

        await db.create_trade(
            trade_id=trade_id,
            guild_id=guild.id,
            mm_id=interaction.user.id,
            buyer_id=buyer_id,
            seller_id=seller_id,
            amount=self.amount.value,
            details=self.details.value,
            channel_id=self.target_channel.id,
            message_id=msg.id
        )

        await interaction.response.send_message(
            embed=success_embed(
                "MM Transaction Posted",
                f"Live trade **#{trade_id}** was posted in {self.target_channel.mention}!"
            ),
            ephemeral=True
        )

class Trades(commands.Cog):
    """Live trade logger and Middleman ($mercy) transaction manager."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_destination_channel(self, ctx: commands.Context) -> discord.TextChannel:
        settings = await db.get_guild_settings(ctx.guild.id)
        # Check trade channel first, then vouch channel, fallback to current channel
        channel_id = settings.get("trade_channel_id") or settings.get("vouch_channel_id")
        if channel_id:
            channel = ctx.guild.get_channel(channel_id)
            if channel and channel.permissions_for(ctx.guild.me).send_messages:
                return channel
        return ctx.channel

    @commands.command(name="settradechannel", aliases=["tradechan"], help="Set dedicated channel for live trade receipts.")
    @commands.has_permissions(administrator=True)
    async def set_trade_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        await db.update_guild_setting(ctx.guild.id, "trade_channel_id", channel.id)
        await ctx.send(embed=success_embed("Trade Channel Set", f"Live MM receipts will be posted in {channel.mention}."))

    @commands.command(name="mercy", aliases=["deal", "mm"], help="Log an MM transaction in the vouch/trade channel. E.g. $mercy or $mercy @buyer @seller $50 Item description")
    async def mercy_cmd(self, ctx: commands.Context, buyer: discord.Member = None, seller: discord.Member = None, amount: str = None, *, details: str = None):
        target_channel = await self.get_destination_channel(ctx)

        # Direct argument method
        if buyer and seller and amount and details:
            trade_id = f"TRD-{random.randint(1000, 9999)}"

            embed = standard_embed(
                title=f"🤝 Live Trade Receipt • #{trade_id}",
                description="A new official Middleman transaction is currently active.",
                color=0xFEE75C
            )
            embed.add_field(name="🛡️ Middleman (MM)", value=ctx.author.mention, inline=True)
            embed.add_field(name="👤 Buyer", value=buyer.mention, inline=True)
            embed.add_field(name="📦 Seller", value=seller.mention, inline=True)
            embed.add_field(name="💰 Value / Amount", value=f"`{amount}`", inline=True)
            embed.add_field(name="📊 Status", value="🟡 **In Progress**", inline=True)
            embed.add_field(name="📝 Deal Details", value=f"```{details}```", inline=False)
            embed.set_footer(text=f"Trade ID: {trade_id} • Zyath Live MM Logger")

            view = TradeStatusView(trade_id=trade_id, mm_id=ctx.author.id)
            msg = await target_channel.send(content=f"{buyer.mention} {seller.mention}", embed=embed, view=view)

            await db.create_trade(
                trade_id=trade_id,
                guild_id=ctx.guild.id,
                mm_id=ctx.author.id,
                buyer_id=buyer.id,
                seller_id=seller.id,
                amount=amount,
                details=details,
                channel_id=target_channel.id,
                message_id=msg.id
            )

            if target_channel.id != ctx.channel.id:
                await ctx.send(embed=success_embed("MM Trade Posted", f"Trade **#{trade_id}** posted to {target_channel.mention}!"))
            return

        # Interactive button to open Modal
        view = discord.ui.View()
        async def open_modal_cb(interaction: discord.Interaction):
            await interaction.response.send_modal(MercyModal(self.bot, target_channel))

        btn = discord.ui.Button(label="Open MM Receipt Form", style=discord.ButtonStyle.primary, emoji="📝")
        btn.callback = open_modal_cb
        view.add_item(btn)

        await ctx.send(
            embed=info_embed(
                "Mercy MM Transaction Setup",
                f"Click the button below to enter the Middleman trade details, or use:\n`$mercy @buyer @seller <amount> <details>`\n\nTarget Channel: {target_channel.mention}"
            ),
            view=view
        )

    @commands.command(name="trade", aliases=["dealinfo"], help="Check status of a trade. E.g. $trade TRD-1234")
    async def trade_info(self, ctx: commands.Context, trade_id: str):
        trade_id = trade_id.upper()
        trade = await db.get_trade(trade_id)
        if not trade:
            return await ctx.send(embed=error_embed("Trade Not Found", f"No trade record found with ID `{trade_id}`."))

        embed = standard_embed(
            title=f"Trade Details • #{trade['id']}",
            description=f"**Status:** `{trade['status']}`\n**Timestamp:** `{trade['timestamp']}`"
        )
        embed.add_field(name="🛡️ Middleman", value=f"<@{trade['mm_id']}>", inline=True)
        embed.add_field(name="👤 Buyer", value=f"<@{trade['buyer_id']}>", inline=True)
        embed.add_field(name="📦 Seller", value=f"<@{trade['seller_id']}>", inline=True)
        embed.add_field(name="💰 Amount", value=f"`{trade['amount']}`", inline=True)
        embed.add_field(name="📝 Details", value=f"```{trade['details']}```", inline=False)
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Trades(bot))
