import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db
from utils.ltc import (
    is_valid_ltc_address,
    is_valid_txid,
    shorten_address,
    get_ltc_price,
    get_ltc_balance,
    get_ltc_address_transactions,
    get_ltc_tx_status
)

class LTC(commands.Cog):
    """Taka-style Litecoin Wallet Tracking & Blockchain Explorer."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def build_wallet_embed(self, address: str, title: str = "Litecoin Wallet Overview") -> discord.Embed:
        bal_data = await get_ltc_balance(address)
        price_usd = await get_ltc_price()

        bal_ltc = bal_data.get("balance_ltc", 0.0)
        unconfirmed_ltc = bal_data.get("unconfirmed_ltc", 0.0)
        total_received = bal_data.get("total_received_ltc", 0.0)
        tx_count = bal_data.get("tx_count", 0)

        usd_val = bal_ltc * price_usd
        short_addr = shorten_address(address, 8, 8)

        txs = await get_ltc_address_transactions(address, limit=3)
        tx_lines = []
        if txs:
            for t in txs:
                direction = "🟢 IN" if t.get("is_incoming") else "🔴 OUT"
                status_icon = "✅" if t.get("confirmed") else "⏳"
                tx_lines.append(f"{direction} `{t.get('amount_ltc', 0.0):.4f} LTC` • {status_icon} `{shorten_address(t.get('txid', ''), 4, 4)}`")
        else:
            tx_lines.append("*No recent transactions found.*")

        embed = discord.Embed(
            title=f"🪙 {title}",
            color=0x345C9C, # Litecoin brand blue
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Wallet Address", value=f"`{address}`\n*Shortened:* `{short_addr}`", inline=False)
        embed.add_field(name="Confirmed Balance", value=f"**{bal_ltc:.6f} LTC**\n`≈ ${usd_val:,.2f} USD`", inline=True)
        embed.add_field(name="Current LTC Price", value=f"**${price_usd:,.2f} USD**\n`Live Market Rate`", inline=True)

        if unconfirmed_ltc != 0:
            embed.add_field(name="Pending Unconfirmed", value=f"`{unconfirmed_ltc:+.6f} LTC`", inline=True)

        embed.add_field(name="Total Received", value=f"`{total_received:.4f} LTC`", inline=True)
        embed.add_field(name="Total Transactions", value=f"`{tx_count}`", inline=True)
        embed.add_field(name="Network Status", value="🟢 Mainnet Healthy", inline=True)
        embed.add_field(name="Recent Activity", value="\n".join(tx_lines), inline=False)

        embed.set_footer(text="Litecoin Blockchain Data • Taka-Style Live Tracking")
        return embed

    # --- Prefix Commands Group ---
    @commands.group(name="ltc", invoke_without_command=True)
    async def ltc_group(self, ctx: commands.Context):
        """Litecoin wallet tracker commands: link, balance, price, portfolio, check, etc."""
        linked_addr = await db.get_user_ltc(ctx.author.id)
        if linked_addr:
            embed = await self.build_wallet_embed(linked_addr, f"{ctx.author.display_name}'s Linked LTC Wallet")
            await ctx.send(embed=embed)
        else:
            price = await get_ltc_price()
            embed = info_embed(
                "🪙 Litecoin Wallet Tracking (Taka-Style)",
                f"**Current LTC Price:** `${price:,.2f} USD`\n\n"
                f"You have not linked a Litecoin wallet yet!\n"
                f"• Link your wallet: `$ltc link <address>`\n"
                f"• Check any public address: `$ltc check <address>`\n"
                f"• Check transaction: `$ltc status <txid>`\n"
                f"• View price: `$ltc price`"
            )
            await ctx.send(embed=embed)

    @ltc_group.command(name="link")
    async def ltc_link(self, ctx: commands.Context, address: str):
        """Link your public Litecoin wallet address to your profile."""
        clean = address.strip()
        if not is_valid_ltc_address(clean):
            return await ctx.send(embed=error_embed(
                "Invalid Litecoin Address",
                "That does not match any valid Litecoin Mainnet address format.\n"
                "Supported formats:\n"
                "• Legacy (`L...`)\n"
                "• SegWit P2SH (`M...` or `3...`)\n"
                "• Native SegWit Bech32 (`ltc1...`)"
            ))

        await db.link_user_ltc(ctx.author.id, clean)
        await ctx.send(embed=success_embed(
            "LTC Wallet Linked",
            f"Successfully linked wallet `{shorten_address(clean)}` to your account!\n"
            f"Run `$ltc balance` or `$ltc portfolio` anytime to view your blockchain holdings."
        ))

    @ltc_group.command(name="unlink")
    async def ltc_unlink(self, ctx: commands.Context):
        """Unlink your Litecoin wallet from your profile."""
        unlinked = await db.unlink_user_ltc(ctx.author.id)
        if unlinked:
            await ctx.send(embed=success_embed("LTC Wallet Unlinked", "Your Litecoin wallet has been disconnected."))
        else:
            await ctx.send(embed=info_embed("Not Linked", "You do not have a linked LTC wallet."))

    @ltc_group.command(name="address", aliases=["addr"])
    async def ltc_address(self, ctx: commands.Context, member: discord.Member = None):
        """Show your linked Litecoin address or inspect another member's linked address."""
        target = member or ctx.author
        addr = await db.get_user_ltc(target.id)
        if not addr:
            msg = "You have not linked an LTC wallet yet. Use `$ltc link <address>`." if target == ctx.author else f"{target.mention} has not linked an LTC wallet."
            return await ctx.send(embed=info_embed("No Wallet Linked", msg))

        embed = standard_embed(
            title=f"🪙 {target.display_name}'s Litecoin Address",
            description=f"```{addr}```",
            color=0x345C9C
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @ltc_group.command(name="balance", aliases=["bal"])
    async def ltc_balance(self, ctx: commands.Context, member: discord.Member = None):
        """Check the actual blockchain balance of your linked wallet."""
        target = member or ctx.author
        addr = await db.get_user_ltc(target.id)
        if not addr:
            return await ctx.send(embed=info_embed("No Wallet Linked", f"{target.mention} has no linked LTC wallet. Run `$ltc link <address>` to link one."))

        embed = await self.build_wallet_embed(addr, f"{target.display_name}'s Balance")
        await ctx.send(embed=embed)

    @ltc_group.command(name="portfolio", aliases=["port"])
    async def ltc_portfolio(self, ctx: commands.Context, member: discord.Member = None):
        """Show balance and estimated USD value of your holdings."""
        target = member or ctx.author
        addr = await db.get_user_ltc(target.id)
        if not addr:
            return await ctx.send(embed=info_embed("No Wallet Linked", f"{target.mention} has no linked LTC wallet. Run `$ltc link <address>`."))

        embed = await self.build_wallet_embed(addr, f"{target.display_name}'s Portfolio")
        await ctx.send(embed=embed)

    @ltc_group.command(name="price")
    async def ltc_price_cmd(self, ctx: commands.Context):
        """Show current live market LTC/USD price."""
        price = await get_ltc_price()
        embed = standard_embed(
            title="🪙 Litecoin (LTC) Market Price",
            description=(
                f"> **Current Price:** `${price:,.2f} USD`\n"
                f"> **Ticker:** `LTC / USD` • **Network:** `Mainnet`\n"
                f"> **API Feeds:** Multi-Provider Verified (CoinGecko / Binance / Coinbase)"
            ),
            color=0x345C9C
        )
        embed.set_footer(text="Live Market Rate • Refreshes Every 60s")
        await ctx.send(embed=embed)

    @ltc_group.command(name="transactions", aliases=["txs"])
    async def ltc_txs_cmd(self, ctx: commands.Context, member: discord.Member = None):
        """Show recent incoming and outgoing transactions for linked wallet."""
        target = member or ctx.author
        addr = await db.get_user_ltc(target.id)
        if not addr:
            return await ctx.send(embed=info_embed("No Wallet Linked", f"{target.mention} has no linked LTC wallet."))

        txs = await get_ltc_address_transactions(addr, limit=5)
        if not txs:
            return await ctx.send(embed=info_embed("No Transactions", f"No recent transactions found on blockchain for `{shorten_address(addr)}`."))

        desc = f"**Address:** `{addr}`\n\n"
        for idx, t in enumerate(txs, 1):
            direction = "🟢 INCOMING" if t.get("is_incoming") else "🔴 OUTGOING"
            status = "Confirmed" if t.get("confirmed") else "Pending"
            desc += f"**#{idx} • {direction}**\n• Amount: `{t.get('amount_ltc', 0.0):.6f} LTC`\n• Status: `{status}` ({t.get('confirmations', 0)} confs)\n• TXID: [`{shorten_address(t.get('txid', ''), 8, 8)}`](https://litecoinspace.org/tx/{t.get('txid')})\n\n"

        embed = standard_embed(
            title=f"📜 Recent LTC Transactions • {target.display_name}",
            description=desc,
            color=0x345C9C
        )
        await ctx.send(embed=embed)

    @ltc_group.command(name="check")
    async def ltc_check(self, ctx: commands.Context, address: str):
        """Check any public Litecoin address on the blockchain."""
        clean = address.strip()
        if not is_valid_ltc_address(clean):
            return await ctx.send(embed=error_embed("Invalid Address", "That is not a valid Litecoin Mainnet address."))

        embed = await self.build_wallet_embed(clean, f"Public Address: {shorten_address(clean, 6, 6)}")
        await ctx.send(embed=embed)

    @ltc_group.command(name="status")
    async def ltc_status_cmd(self, ctx: commands.Context, txid: str):
        """Check Litecoin transaction confirmation status and metadata."""
        clean_tx = txid.strip()
        if not is_valid_txid(clean_tx):
            return await ctx.send(embed=error_embed("Invalid TXID", "Litecoin transaction IDs must be 64 hexadecimal characters."))

        tx_info = await get_ltc_tx_status(clean_tx)
        if not tx_info.get("found"):
            return await ctx.send(embed=error_embed("Not Found", "Transaction not found on the blockchain. It may be unbroadcasted or pending network propagation."))

        confs = tx_info.get("confirmations", 0)
        status_str = f"✅ Confirmed ({confs} Confirmations)" if confs > 0 else "⏳ Unconfirmed (In Mempool)"
        color_val = 0x2ECC71 if confs >= 1 else 0xFEE75C

        embed = standard_embed(
            title="🔍 Litecoin Transaction Audit",
            description=(
                f"• **Status:** `{status_str}`\n"
                f"• **Confirmations:** `{confs}`\n"
                f"• **Block Height:** `{tx_info.get('block_height') or 'Pending'}`\n"
                f"• **Total Output:** `{tx_info.get('total_value_ltc', 0.0):.6f} LTC`\n"
                f"• **TXID:** [`{clean_tx}`](https://litecoinspace.org/tx/{clean_tx})\n\n"
                f"**Outputs:**\n" +
                "\n".join([f"• `{shorten_address(o['address'])}`: `{o['amount_ltc']:.6f} LTC`" for o in tx_info.get("outputs", [])[:4]])
            ),
            color=color_val
        )
        embed.set_footer(text="Litecoin Independent Blockchain Verification")
        await ctx.send(embed=embed)

    # --- Slash Commands ---
    @app_commands.command(name="ltc", description="Taka-style Litecoin wallet tracking and market commands.")
    @app_commands.describe(
        action="Action to execute",
        address="Litecoin wallet address (for link or check)",
        txid="Litecoin transaction ID (for status)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="balance", value="balance"),
        app_commands.Choice(name="portfolio", value="portfolio"),
        app_commands.Choice(name="price", value="price"),
        app_commands.Choice(name="link", value="link"),
        app_commands.Choice(name="unlink", value="unlink"),
        app_commands.Choice(name="address", value="address"),
        app_commands.Choice(name="transactions", value="transactions"),
        app_commands.Choice(name="check", value="check"),
        app_commands.Choice(name="status", value="status")
    ])
    async def slash_ltc(
        self,
        interaction: discord.Interaction,
        action: str,
        address: Optional[str] = None,
        txid: Optional[str] = None
    ):
        if action == "link":
            if not address:
                return await interaction.response.send_message(embed=error_embed("Missing Address", "Please provide a valid Litecoin address to link."), ephemeral=True)
            clean = address.strip()
            if not is_valid_ltc_address(clean):
                return await interaction.response.send_message(embed=error_embed("Invalid Address", "Must be a valid Litecoin address (legacy, segwit, or bech32)."), ephemeral=True)
            await db.link_user_ltc(interaction.user.id, clean)
            await interaction.response.send_message(embed=success_embed("Wallet Linked", f"Linked wallet `{shorten_address(clean)}` to your account!"), ephemeral=True)

        elif action == "unlink":
            unlinked = await db.unlink_user_ltc(interaction.user.id)
            if unlinked:
                await interaction.response.send_message(embed=success_embed("Unlinked", "Your Litecoin wallet was unlinked."), ephemeral=True)
            else:
                await interaction.response.send_message(embed=info_embed("Not Linked", "You do not have a linked wallet."), ephemeral=True)

        elif action == "price":
            price = await get_ltc_price()
            embed = standard_embed(title="🪙 Litecoin Market Price", description=f"> **Current Price:** `${price:,.2f} USD`", color=0x345C9C)
            await interaction.response.send_message(embed=embed)

        elif action == "balance" or action == "portfolio":
            addr = await db.get_user_ltc(interaction.user.id)
            if not addr:
                return await interaction.response.send_message(embed=info_embed("No Wallet Linked", "Please link your wallet first using `/ltc link <address>`."), ephemeral=True)
            await interaction.response.defer()
            embed = await self.build_wallet_embed(addr, f"{interaction.user.display_name}'s Holdings")
            await interaction.followup.send(embed=embed)

        elif action == "address":
            addr = await db.get_user_ltc(interaction.user.id)
            if not addr:
                return await interaction.response.send_message(embed=info_embed("No Wallet Linked", "Use `/ltc link <address>` to link a wallet."), ephemeral=True)
            embed = standard_embed(title="🪙 Your Linked Litecoin Address", description=f"```{addr}```", color=0x345C9C)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif action == "transactions":
            addr = await db.get_user_ltc(interaction.user.id)
            if not addr:
                return await interaction.response.send_message(embed=info_embed("No Wallet Linked", "Link your wallet first using `/ltc link <address>`."), ephemeral=True)
            await interaction.response.defer()
            txs = await get_ltc_address_transactions(addr, limit=5)
            if not txs:
                return await interaction.followup.send(embed=info_embed("No Transactions", "No recent transactions found on blockchain."))
            desc = f"**Address:** `{addr}`\n\n"
            for idx, t in enumerate(txs, 1):
                direction = "🟢 IN" if t.get("is_incoming") else "🔴 OUT"
                desc += f"• **{direction}** `{t.get('amount_ltc', 0.0):.6f} LTC` • `{shorten_address(t.get('txid', ''), 6, 6)}`\n"
            embed = standard_embed(title="📜 Recent Transactions", description=desc, color=0x345C9C)
            await interaction.followup.send(embed=embed)

        elif action == "check":
            if not address:
                return await interaction.response.send_message(embed=error_embed("Missing Address", "Provide an address to check."), ephemeral=True)
            clean = address.strip()
            if not is_valid_ltc_address(clean):
                return await interaction.response.send_message(embed=error_embed("Invalid Address", "Must be a valid Litecoin Mainnet address."), ephemeral=True)
            await interaction.response.defer()
            embed = await self.build_wallet_embed(clean, f"Public Address: {shorten_address(clean)}")
            await interaction.followup.send(embed=embed)

        elif action == "status":
            if not txid:
                return await interaction.response.send_message(embed=error_embed("Missing TXID", "Provide a transaction ID to check."), ephemeral=True)
            clean_tx = txid.strip()
            if not is_valid_txid(clean_tx):
                return await interaction.response.send_message(embed=error_embed("Invalid TXID", "TXID must be 64 hex characters."), ephemeral=True)
            await interaction.response.defer()
            tx_info = await get_ltc_tx_status(clean_tx)
            if not tx_info.get("found"):
                return await interaction.followup.send(embed=error_embed("Not Found", "Transaction not found on the blockchain."))
            confs = tx_info.get("confirmations", 0)
            status_str = f"✅ Confirmed ({confs} Confirmations)" if confs > 0 else "⏳ Unconfirmed"
            embed = standard_embed(
                title="🔍 Litecoin Transaction Status",
                description=f"• **Status:** `{status_str}`\n• **Block:** `{tx_info.get('block_height') or 'Pending'}`\n• **Total Output:** `{tx_info.get('total_value_ltc', 0.0):.6f} LTC`",
                color=0x2ECC71 if confs >= 1 else 0xFEE75C
            )
            await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(LTC(bot))
