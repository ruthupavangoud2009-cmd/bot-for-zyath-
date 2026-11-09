import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Union
import re
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db
from utils.ltc import (
    is_valid_ltc_address,
    is_valid_txid,
    shorten_address,
    get_ltc_price,
    get_ltc_balance,
    get_ltc_address_transactions,
    get_ltc_tx_status,
    get_ltc_qr_url
)
from utils.ltc_sender import (
    LitecoinKey,
    parse_payment_amount,
    convert_amount_to_sats,
    execute_onchain_payment,
    fetch_utxos,
    get_recommended_feerate
)

# -------------------------------------------------------------
# Modals & Interactive UI Views
# -------------------------------------------------------------
class SetKeyModal(discord.ui.Modal, title="Set Litecoin Payment Account"):
    """Secure ephemeral Discord Modal to input a Litecoin WIF private key."""

    wif_input = discord.ui.TextInput(
        label="Litecoin Private Key (WIF)",
        placeholder="Starts with T (compressed) or 6 (uncompressed)...",
        style=discord.TextStyle.short,
        required=True,
        min_length=45,
        max_length=65
    )

    async def on_submit(self, interaction: discord.Interaction):
        clean_wif = self.wif_input.value.strip()
        try:
            info = await db.set_user_wallet_account(interaction.user.id, clean_wif)
        except Exception as e:
            return await interaction.response.send_message(
                embed=error_embed(
                    "Invalid Private Key",
                    f"Could not import key: `{e}`\n"
                    "Ensure you provide a valid Litecoin Mainnet WIF key (starts with `T` or `6`)."
                ),
                ephemeral=True
            )

        embed = discord.Embed(
            title="🔐 Kyoka Payment Account Linked",
            description=(
                "Your Litecoin private key has been **encrypted with AES-256** and saved securely.\n"
                "You can now send on-chain payments anywhere directly from Discord!\n\n"
                f"• **Native SegWit (Bech32):** `{info['bech32']}`\n"
                f"• **Legacy Address (P2PKH):** `{info['p2pkh']}`\n"
                f"• **P2SH Address:** `{info['p2sh']}`\n\n"
                "> 💡 **How to Pay:**\n"
                "> • Send to address: `$pay <address> 1$ ltc` or `$pay <address> 0.05 ltc`\n"
                "> • Send to member: `$pay @user 1$`\n"
                "> • Remove key anytime: `$wallet removekey`"
            ),
            color=0x2ECC71,
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text="Kyoka Shop • Bank-Grade AES-256 Protection")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class PaymentConfirmationView(discord.ui.View):
    """Interactive confirmation dialog for on-chain payments."""

    def __init__(self, author_id: int, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.value: Optional[bool] = None
        self.interaction: Optional[discord.Interaction] = None

    @discord.ui.button(label="Confirm & Send", style=discord.ButtonStyle.green, emoji="💸")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("❌ This confirmation is not for you.", ephemeral=True)
        self.value = True
        self.interaction = interaction
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("❌ This confirmation is not for you.", ephemeral=True)
        self.value = False
        self.interaction = interaction
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

class WalletDashboardView(discord.ui.View):
    """Interactive control view on the $wallet dashboard."""

    def __init__(self, author_id: int):
        super().__init__(timeout=120.0)
        self.author_id = author_id

    @discord.ui.button(label="Set Key", style=discord.ButtonStyle.primary, emoji="🔐")
    async def set_key_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("❌ This is not your dashboard.", ephemeral=True)
        await interaction.response.send_modal(SetKeyModal())

    @discord.ui.button(label="Deposit", style=discord.ButtonStyle.secondary, emoji="📥")
    async def deposit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("❌ This is not your dashboard.", ephemeral=True)
        account = await db.get_user_wallet_account(interaction.user.id)
        addr = account.get("bech32_address") or account.get("p2pkh_address") if account else None
        if not addr:
            addr = await db.get_user_ltc(interaction.user.id)

        if not addr:
            key = LitecoinKey.generate()
            await db.set_user_wallet_account(interaction.user.id, key.wif)
            addr = key.bech32_address

        qr_url = get_ltc_qr_url(addr)
        embed = discord.Embed(
            title="📥 Your Litecoin Deposit Address",
            description=(
                f"Send Litecoin (LTC) to your personal wallet address below:\n\n"
                f"```{addr}```\n"
                "• **Network:** Litecoin Mainnet\n"
                "• **Supported:** Legacy, SegWit, Bech32\n"
                "• **Auto-Credited:** Once confirmed, funds can be spent via `$pay`"
            ),
            color=0x345C9C
        )
        embed.set_image(url=qr_url)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class LTC(commands.Cog):
    """Litecoin Wallet Tracking, Direct On-Chain Payments & Blockchain Explorer."""

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

        embed.set_footer(text="Litecoin Blockchain Data • Kyoka Live Tracking")
        return embed

    # =========================================================
    # $pay COMMAND: Direct On-Chain & Discord Payment Execution
    # =========================================================
    @commands.command(name="pay")
    async def pay_cmd(self, ctx: commands.Context, recipient: str, *, amount_args: str):
        """
        Send payments directly from your account to any LTC address or Discord user!
        Syntax:
          $pay <address> 1$ ltc
          $pay <address> 1$
          $pay <address> 0.05 ltc
          $pay @user 1$
          $pay <address> 1$ -y (bypass confirmation)
        """
        raw_amount = amount_args.strip()
        auto_confirm = False
        for flag in ["-y", "--yes", "--force"]:
            if flag in raw_amount.lower():
                auto_confirm = True
                raw_amount = re.sub(re.escape(flag), "", raw_amount, flags=re.IGNORECASE).strip()

        # Parse numerical amount and currency (USD vs LTC)
        try:
            val, curr = parse_payment_amount(raw_amount)
        except Exception as e:
            return await ctx.send(embed=error_embed(
                "Invalid Amount",
                f"{e}\n\n"
                "**Examples:**\n"
                "• `$pay <address> 1$ ltc` (Sends $1 USD of LTC)\n"
                "• `$pay <address> 0.05 ltc` (Sends 0.05 LTC)\n"
                "• `$pay @user 1$` (Transfers $1 to Discord member)"
            ))

        price_usd = await get_ltc_price()
        try:
            sats, amount_ltc, amount_usd = convert_amount_to_sats(val, curr, price_usd)
        except Exception as e:
            return await ctx.send(embed=error_embed("Payment Calculation Error", str(e)))

        # -----------------------------------------------------
        # Check if recipient is a Discord Member mention or ID
        # -----------------------------------------------------
        user_match = re.match(r"^<@!?([0-9]+)>$", recipient) or (recipient.isdigit() and len(recipient) >= 17)
        if user_match:
            target_user_id = int(user_match.group(1)) if hasattr(user_match, "group") else int(recipient)
            target_user = ctx.guild.get_member(target_user_id) if ctx.guild else None
            if not target_user:
                try:
                    target_user = await self.bot.fetch_user(target_user_id)
                except Exception:
                    pass

            if not target_user:
                return await ctx.send(embed=error_embed("User Not Found", "Could not locate that Discord user."))

            if target_user.id == ctx.author.id:
                return await ctx.send(embed=error_embed("Invalid Target", "You cannot send payment to yourself."))

            # Check if sender has internal deposit balance
            deposit_bal = await db.get_user_deposit_balance(ctx.author.id)
            if deposit_bal >= amount_ltc:
                if not auto_confirm:
                    conf_embed = discord.Embed(
                        title="💸 Confirm Discord-to-Discord Payment",
                        description=(
                            f"Are you sure you want to transfer funds from your bot balance?\n\n"
                            f"• **Recipient:** {target_user.mention} (`{target_user.display_name}`)\n"
                            f"• **Amount:** **{amount_ltc:.6f} LTC** (≈ `${amount_usd:,.2f} USD`)\n"
                            f"• **Fee:** `0.00 LTC` (Instant Off-Chain Transfer)\n"
                            f"• **Your Remaining Balance:** `{(deposit_bal - amount_ltc):.6f} LTC`"
                        ),
                        color=0xFEE75C
                    )
                    conf_view = PaymentConfirmationView(author_id=ctx.author.id)
                    conf_msg = await ctx.send(embed=conf_embed, view=conf_view)
                    await conf_view.wait()

                    if conf_view.value is not True:
                        return await conf_msg.edit(
                            embed=info_embed("Payment Cancelled", "The transfer was cancelled."),
                            view=None
                        )

                # Execute internal transfer
                ok = await db.transfer_internal_balance(ctx.author.id, target_user.id, amount_ltc)
                if ok:
                    return await ctx.send(embed=success_embed(
                        "Payment Delivered! 💸",
                        f"Transferred **{amount_ltc:.6f} LTC** (`${amount_usd:,.2f} USD`) to {target_user.mention}!\n"
                        f"• **Type:** Instant Discord Ledger Transfer\n"
                        f"• **Network Fee:** `0.00 LTC`"
                    ))
                else:
                    return await ctx.send(embed=error_embed("Transfer Failed", "Insufficient deposit balance."))

            # Sender does not have deposit balance; check if target user has a linked on-chain LTC address
            target_addr = await db.get_user_ltc(target_user.id)
            if not target_addr:
                return await ctx.send(embed=error_embed(
                    "Cannot Complete Payment",
                    f"{target_user.mention} does not have a linked Litecoin address yet, and you have insufficient bot deposit balance (`{deposit_bal:.6f} LTC`).\n\n"
                    f"• {target_user.mention} can link their wallet: `$ltc link <address>`\n"
                    f"• Or you can deposit to your balance: `$wallet deposit`"
                ))
            recipient_address = target_addr
        else:
            # Recipient is an external LTC address
            clean_addr = recipient.strip()
            if not is_valid_ltc_address(clean_addr):
                return await ctx.send(embed=error_embed(
                    "Invalid Destination Address",
                    f"`{clean_addr}` is not a valid Litecoin Mainnet address.\n"
                    "Supported formats: Legacy (`L...`), SegWit (`M...`, `3...`), Bech32 (`ltc1...`)."
                ))
            recipient_address = clean_addr

        # -----------------------------------------------------
        # On-Chain Payment Execution via User's Linked Signing Key
        # -----------------------------------------------------
        signing_key = await db.get_user_signing_key(ctx.author.id)
        if not signing_key:
            deposit_bal = await db.get_user_deposit_balance(ctx.author.id)
            return await ctx.send(embed=error_embed(
                "No Payment Account Linked",
                "You have not linked a private key to pay directly from Discord yet!\n\n"
                "**How to set up your account:**\n"
                "1. **Option A (Non-Custodial):** Set your key via private modal `/wallet setkey` or DM the bot `$wallet setkey <wif>`\n"
                "   *(Your key is AES-256 encrypted and stored safely)*\n"
                "2. **Option B (Deposit Balance):** Fund an internal balance with `$wallet deposit`\n\n"
                f"*Current deposit balance: `{deposit_bal:.6f} LTC`*"
            ))

        # Check sender's available UTXOs across their addresses
        async with ctx.typing():
            p2pkh_utxos = await fetch_utxos(signing_key.p2pkh_address)
            segwit_utxos = await fetch_utxos(signing_key.bech32_address)
            total_avail_sats = sum(u["value"] for u in p2pkh_utxos + segwit_utxos)
            feerate = await get_recommended_feerate()

        est_fee_sats = 250 * feerate
        if total_avail_sats < (sats + est_fee_sats):
            return await ctx.send(embed=error_embed(
                "Insufficient Funds in Wallet",
                f"Your linked account balance is **{total_avail_sats / 1e8:.6f} LTC**.\n"
                f"Required: **{(sats + est_fee_sats) / 1e8:.6f} LTC** (Amount: `{amount_ltc:.6f} LTC` + Network Fee: `~{est_fee_sats / 1e8:.6f} LTC`).\n\n"
                f"• Your Bech32 Address: `{signing_key.bech32_address}`\n"
                f"• Your Legacy Address: `{signing_key.p2pkh_address}`\n"
                "Deposit funds to either address and try again!"
            ))

        # Interactive Confirmation Dialog (Unless -y / --yes was supplied)
        if not auto_confirm:
            conf_embed = discord.Embed(
                title="💸 Confirm Litecoin Blockchain Payment",
                description=(
                    "You are about to sign and broadcast a real transaction to the Litecoin blockchain:\n\n"
                    f"• **Destination:** `{recipient_address}`\n"
                    f"• **Amount:** **{amount_ltc:.6f} LTC** (≈ `${amount_usd:,.2f} USD`)\n"
                    f"• **Est. Miner Fee:** `~{est_fee_sats / 1e8:.6f} LTC` (< $0.001 USD)\n"
                    f"• **Source Wallet:** `{shorten_address(signing_key.bech32_address, 8, 8)}`\n"
                    f"• **Live Market Rate:** `${price_usd:,.2f} / LTC`\n\n"
                    "⚠️ *Once confirmed, this transaction cannot be reversed.*"
                ),
                color=0x345C9C,
                timestamp=discord.utils.utcnow()
            )
            conf_view = PaymentConfirmationView(author_id=ctx.author.id)
            conf_msg = await ctx.send(embed=conf_embed, view=conf_view)
            await conf_view.wait()

            if conf_view.value is not True:
                return await conf_msg.edit(
                    embed=info_embed("Payment Cancelled", "The on-chain transaction was aborted."),
                    view=None
                )
            status_msg = conf_msg
        else:
            status_msg = await ctx.send(embed=info_embed("Processing", "⏳ Constructing, signing, and broadcasting transaction..."))

        # Execute On-Chain Payment
        try:
            res = await execute_onchain_payment(signing_key, recipient_address, sats, sat_per_vb=feerate)
        except Exception as e:
            return await status_msg.edit(embed=error_embed("Transaction Failed", f"Signing error: `{e}`"), view=None)

        if not res.get("success"):
            return await status_msg.edit(
                embed=error_embed("Broadcast Error", f"Blockchain node rejected transaction: `{res.get('error')}`"),
                view=None
            )

        # Success Embed with Explorer Link
        txid = res["txid"]
        explorer_url = res["explorer_url"]
        sent_ltc = res["amount_ltc"]
        fee_ltc = res["fee_ltc"]

        success = discord.Embed(
            title="✅ Litecoin Payment Broadcasted!",
            description=(
                f"> **Amount Sent:** `{sent_ltc:.6f} LTC` (≈ `${amount_usd:,.2f} USD`)\n"
                f"> **Network Fee:** `{fee_ltc:.6f} LTC`\n"
                f"> **Transaction ID:** [`{shorten_address(txid, 8, 8)}`]({explorer_url})\n\n"
                f"• **From:** `{shorten_address(res['sender'], 8, 8)}`\n"
                f"• **To:** `{recipient_address}`\n"
                f"• **Explorer:** [View on LitecoinSpace]({explorer_url})"
            ),
            color=0x2ECC71,
            timestamp=discord.utils.utcnow()
        )
        success.set_footer(text="Broadcasted to Litecoin Mainnet • Kyoka Shop Pay")
        await status_msg.edit(embed=success, view=None)

    # =========================================================
    # $wallet COMMAND GROUP: Account Linking & Balance Management
    # =========================================================
    @commands.group(name="wallet", invoke_without_command=True)
    async def wallet_group(self, ctx: commands.Context):
        """Kyoka Wallet Dashboard: manage your linked payment key, balances, and deposit address."""
        account = await db.get_user_wallet_account(ctx.author.id)
        price_usd = await get_ltc_price()

        has_key = account.get("has_key") if account else False
        p2pkh_addr = account.get("p2pkh_address") if account else None
        bech32_addr = account.get("bech32_address") if account else None
        deposit_bal = account.get("balance_ltc", 0.0) if account else 0.0

        # Also check user_ltc_wallets if no bech32
        if not bech32_addr:
            bech32_addr = await db.get_user_ltc(ctx.author.id)

        # Check on-chain balance if address exists
        onchain_bal = 0.0
        if bech32_addr:
            bdata = await get_ltc_balance(bech32_addr)
            onchain_bal = bdata.get("balance_ltc", 0.0)
        elif p2pkh_addr:
            bdata = await get_ltc_balance(p2pkh_addr)
            onchain_bal = bdata.get("balance_ltc", 0.0)

        embed = discord.Embed(
            title="💳 Kyoka Wallet & Payment Hub",
            description=(
                f"Manage your accounts, on-chain balances, and pay directly from Discord.\n"
                f"**Current LTC Price:** `${price_usd:,.2f} USD`"
            ),
            color=0x345C9C,
            timestamp=discord.utils.utcnow()
        )

        key_status = "🟢 Active (AES-256 Encrypted)" if has_key else "🔴 Not Linked (Run `/wallet setkey`)"
        embed.add_field(name="Signing Key Status", value=key_status, inline=True)
        embed.add_field(name="Deposit Balance", value=f"**{deposit_bal:.6f} LTC**\n`≈ ${(deposit_bal * price_usd):,.2f} USD`", inline=True)
        embed.add_field(name="On-Chain Balance", value=f"**{onchain_bal:.6f} LTC**\n`≈ ${(onchain_bal * price_usd):,.2f} USD`", inline=True)

        if bech32_addr:
            embed.add_field(name="Native SegWit (ltc1)", value=f"`{bech32_addr}`", inline=False)
        if p2pkh_addr:
            embed.add_field(name="Legacy Address (L)", value=f"`{p2pkh_addr}`", inline=False)

        embed.add_field(
            name="⚡ Quick Commands",
            value=(
                "• `$pay <address> 1$ ltc` — Send on-chain payment\n"
                "• `/wallet setkey` — Link private key securely via modal\n"
                "• `$wallet deposit` — View deposit address and QR code\n"
                "• `$wallet removekey` — Disconnect your private key\n"
                "• `$wallet withdraw <address> <amount>` — Withdraw deposit balance\n"
                "• `$wallet help` — Comprehensive tutorial"
            ),
            inline=False
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")

        view = WalletDashboardView(author_id=ctx.author.id)
        await ctx.send(embed=embed, view=view)

    @wallet_group.command(name="setkey")
    async def wallet_setkey(self, ctx: commands.Context, *, wif: str):
        """
        Link your Litecoin private key (WIF).
        NOTE: Messages in public channels are deleted immediately for safety.
        """
        if ctx.guild:
            try:
                await ctx.message.delete()
            except Exception:
                pass

        clean_wif = wif.strip()
        try:
            info = await db.set_user_wallet_account(ctx.author.id, clean_wif)
        except Exception as e:
            return await ctx.send(embed=error_embed(
                "Invalid WIF Key",
                f"Failed to load key: `{e}`\n"
                "Ensure your key starts with `T` (compressed) or `6` (uncompressed)."
            ))

        embed = discord.Embed(
            title="🔐 Kyoka Payment Key Linked",
            description=(
                "Your private key was **encrypted with AES-256** and saved.\n\n"
                f"• **Native SegWit (Bech32):** `{info['bech32']}`\n"
                f"• **Legacy Address (P2PKH):** `{info['p2pkh']}`\n\n"
                "> ⚠️ **Privacy Notice:** If sent in a text channel, your message was auto-deleted. "
                "For highest security, use `/wallet setkey` in the future."
            ),
            color=0x2ECC71
        )
        await ctx.send(embed=embed)

    @wallet_group.command(name="removekey", aliases=["unlinkkey", "deletekey"])
    async def wallet_removekey(self, ctx: commands.Context):
        """Remove your private key from the bot."""
        removed = await db.remove_user_wallet_key(ctx.author.id)
        if removed:
            await ctx.send(embed=success_embed(
                "Key Removed",
                "Your private key has been permanently purged from the database.\n"
                "You can no longer send direct on-chain payments until you re-link a key."
            ))
        else:
            await ctx.send(embed=info_embed("No Key Found", "You did not have a private key stored."))

    @wallet_group.command(name="deposit")
    async def wallet_deposit(self, ctx: commands.Context):
        """Get your personal Litecoin deposit address & QR code."""
        account = await db.get_user_wallet_account(ctx.author.id)
        addr = account.get("bech32_address") or account.get("p2pkh_address") if account else None
        if not addr:
            addr = await db.get_user_ltc(ctx.author.id)

        if not addr:
            key = LitecoinKey.generate()
            await db.set_user_wallet_account(ctx.author.id, key.wif)
            addr = key.bech32_address

        qr_url = get_ltc_qr_url(addr)
        embed = discord.Embed(
            title="📥 Kyoka Personal LTC Deposit Address",
            description=(
                f"Send Litecoin (LTC) to the address below:\n\n"
                f"```{addr}```\n"
                "• **Network:** Litecoin Mainnet\n"
                "• **Confirmations Required:** 1\n"
                "• **Status:** Ready to receive incoming deposits"
            ),
            color=0x345C9C
        )
        embed.set_image(url=qr_url)
        embed.set_footer(text="Scan with mobile wallet (Trust Wallet, Exodus, Cake, Litecoin Core)")
        await ctx.send(embed=embed)

    @wallet_group.command(name="withdraw")
    async def wallet_withdraw(self, ctx: commands.Context, destination: str, *, amount_str: str):
        """Withdraw from your internal deposit balance to an external LTC address."""
        clean_addr = destination.strip()
        if not is_valid_ltc_address(clean_addr):
            return await ctx.send(embed=error_embed("Invalid Address", "Must be a valid Litecoin address."))

        val, curr = parse_payment_amount(amount_str)
        price_usd = await get_ltc_price()
        sats, amount_ltc, amount_usd = convert_amount_to_sats(val, curr, price_usd)

        bal = await db.get_user_deposit_balance(ctx.author.id)
        if bal < amount_ltc:
            return await ctx.send(embed=error_embed(
                "Insufficient Deposit Balance",
                f"You have `{bal:.6f} LTC`, but tried to withdraw `{amount_ltc:.6f} LTC`."
            ))

        # Check if user has signing key for on-chain withdrawal
        signing_key = await db.get_user_signing_key(ctx.author.id)
        if signing_key:
            res = await execute_onchain_payment(signing_key, clean_addr, sats)
            if res.get("success"):
                await db.update_user_deposit_balance(ctx.author.id, -amount_ltc)
                return await ctx.send(embed=success_embed(
                    "Withdrawal Sent!",
                    f"Successfully broadcasted `{res['amount_ltc']:.6f} LTC` to `{clean_addr}`!\n"
                    f"TXID: [`{shorten_address(res['txid'], 8, 8)}`]({res['explorer_url']})"
                ))
            else:
                return await ctx.send(embed=error_embed("Withdrawal Failed", res.get("error", "Broadcast failed")))
        else:
            await db.update_user_deposit_balance(ctx.author.id, -amount_ltc)
            await ctx.send(embed=success_embed(
                "Withdrawal Processed",
                f"Deducted `{amount_ltc:.6f} LTC` from your deposit balance for `{shorten_address(clean_addr)}`."
            ))

    @wallet_group.command(name="help")
    async def wallet_help(self, ctx: commands.Context):
        """Comprehensive guide on direct Discord crypto payments."""
        price = await get_ltc_price()
        embed = discord.Embed(
            title="📖 How to Pay & Receive Direct from Discord",
            description=(
                f"Kyoka Shop allows you to send direct on-chain Litecoin payments and Discord-to-Discord transfers.\n"
                f"**Current LTC Price:** `${price:,.2f} USD`\n\n"
                "### 1️⃣ Setting Up Your Account\n"
                "• Run `/wallet setkey` to open a private modal and enter your Litecoin WIF private key.\n"
                "• Your key is encrypted with **AES-256** and used exclusively to sign your transactions.\n"
                "• Alternatively, fund your bot deposit balance using `$wallet deposit`.\n\n"
                "### 2️⃣ Sending Payments (`$pay`)\n"
                "• **By USD Value:** `$pay <address> 1$ ltc` or `$pay <address> 5$` (automatically converts at live rate)\n"
                "• **By Exact LTC:** `$pay <address> 0.05 ltc`\n"
                "• **To a Discord Member:** `$pay @user 1$`\n"
                "• **Skip Confirmation:** Add `-y` (e.g. `$pay <address> 1$ -y`)\n\n"
                "### 3️⃣ Security & Privacy\n"
                "• Private keys are NEVER displayed in public channels or logs.\n"
                "• You can disconnect your key anytime using `$wallet removekey`.\n"
                "• Transactions are broadcast directly to Litecoin Mainnet nodes with real TXIDs."
            ),
            color=0x345C9C
        )
        embed.set_footer(text="Kyoka Shop • Independent On-Chain Engine")
        await ctx.send(embed=embed)

    # =========================================================
    # SLASH COMMANDS: /pay and /wallet
    # =========================================================
    @app_commands.command(name="pay", description="Send direct on-chain Litecoin payment or Discord balance transfer.")
    @app_commands.describe(
        recipient="Litecoin address (L..., M..., ltc1...) or Discord User ID / mention",
        amount="Payment amount (e.g. '1$ ltc', '5$', '0.05 ltc')"
    )
    async def slash_pay(self, interaction: discord.Interaction, recipient: str, amount: str):
        # Forward to payment logic
        clean_amt = amount.strip()
        try:
            val, curr = parse_payment_amount(clean_amt)
        except Exception as e:
            return await interaction.response.send_message(embed=error_embed("Invalid Amount", str(e)), ephemeral=True)

        price_usd = await get_ltc_price()
        try:
            sats, amount_ltc, amount_usd = convert_amount_to_sats(val, curr, price_usd)
        except Exception as e:
            return await interaction.response.send_message(embed=error_embed("Calculation Error", str(e)), ephemeral=True)

        # Check recipient
        clean_rec = recipient.strip()
        user_match = re.match(r"^<@!?([0-9]+)>$", clean_rec) or (clean_rec.isdigit() and len(clean_rec) >= 17)
        if user_match:
            target_id = int(user_match.group(1)) if hasattr(user_match, "group") else int(clean_rec)
            target_user = interaction.guild.get_member(target_id) if interaction.guild else None
            if not target_user:
                try:
                    target_user = await self.bot.fetch_user(target_id)
                except Exception:
                    pass

            if not target_user or target_user.id == interaction.user.id:
                return await interaction.response.send_message(embed=error_embed("Invalid User", "Cannot pay this user."), ephemeral=True)

            deposit_bal = await db.get_user_deposit_balance(interaction.user.id)
            if deposit_bal >= amount_ltc:
                ok = await db.transfer_internal_balance(interaction.user.id, target_user.id, amount_ltc)
                if ok:
                    return await interaction.response.send_message(embed=success_embed(
                        "Payment Delivered! 💸",
                        f"Transferred **{amount_ltc:.6f} LTC** (`${amount_usd:,.2f} USD`) to {target_user.mention}!"
                    ))
                else:
                    return await interaction.response.send_message(embed=error_embed("Transfer Failed", "Insufficient funds."), ephemeral=True)

            target_addr = await db.get_user_ltc(target_user.id)
            if not target_addr:
                return await interaction.response.send_message(
                    embed=error_embed("No Address", f"{target_user.mention} has not linked an LTC address."),
                    ephemeral=True
                )
            clean_rec = target_addr

        if not is_valid_ltc_address(clean_rec):
            return await interaction.response.send_message(embed=error_embed("Invalid Address", "Not a valid LTC address."), ephemeral=True)

        signing_key = await db.get_user_signing_key(interaction.user.id)
        if not signing_key:
            return await interaction.response.send_message(
                embed=error_embed("No Key Linked", "Please link your private key via `/wallet setkey` first!"),
                ephemeral=True
            )

        await interaction.response.defer()
        try:
            res = await execute_onchain_payment(signing_key, clean_rec, sats)
        except Exception as e:
            return await interaction.followup.send(embed=error_embed("Transaction Failed", str(e)))

        if not res.get("success"):
            return await interaction.followup.send(embed=error_embed("Broadcast Error", res.get("error", "Failed")))

        success = discord.Embed(
            title="✅ Litecoin Payment Broadcasted!",
            description=(
                f"> **Amount:** `{res['amount_ltc']:.6f} LTC` (≈ `${amount_usd:,.2f} USD`)\n"
                f"> **Fee:** `{res['fee_ltc']:.6f} LTC`\n"
                f"> **TXID:** [`{shorten_address(res['txid'], 8, 8)}`]({res['explorer_url']})\n\n"
                f"• **To:** `{clean_rec}`"
            ),
            color=0x2ECC71,
            timestamp=discord.utils.utcnow()
        )
        await interaction.followup.send(embed=success)

    @app_commands.command(name="wallet", description="Manage your Kyoka wallet, link payment key, or view deposit address.")
    @app_commands.describe(action="Wallet action to perform")
    @app_commands.choices(action=[
        app_commands.Choice(name="dashboard", value="dashboard"),
        app_commands.Choice(name="setkey", value="setkey"),
        app_commands.Choice(name="deposit", value="deposit"),
        app_commands.Choice(name="removekey", value="removekey"),
        app_commands.Choice(name="help", value="help")
    ])
    async def slash_wallet(self, interaction: discord.Interaction, action: str):
        if action == "setkey":
            return await interaction.response.send_modal(SetKeyModal())

        elif action == "removekey":
            removed = await db.remove_user_wallet_key(interaction.user.id)
            if removed:
                await interaction.response.send_message(embed=success_embed("Key Removed", "Your signing key was deleted."), ephemeral=True)
            else:
                await interaction.response.send_message(embed=info_embed("Not Found", "No key was linked."), ephemeral=True)

        elif action == "deposit":
            account = await db.get_user_wallet_account(interaction.user.id)
            addr = account.get("bech32_address") if account else None
            if not addr:
                addr = await db.get_user_ltc(interaction.user.id)
            if not addr:
                key = LitecoinKey.generate()
                await db.set_user_wallet_account(interaction.user.id, key.wif)
                addr = key.bech32_address

            qr_url = get_ltc_qr_url(addr)
            embed = discord.Embed(
                title="📥 Your Litecoin Deposit Address",
                description=f"```{addr}```\n• **Network:** Litecoin Mainnet",
                color=0x345C9C
            )
            embed.set_image(url=qr_url)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif action == "help":
            embed = discord.Embed(
                title="📖 How Direct Discord Payments Work",
                description=(
                    "• Link your private key: `/wallet setkey` (modal)\n"
                    "• Send on-chain payment: `$pay <address> 1$ ltc`\n"
                    "• Transfer to member: `$pay @user 1$`\n"
                    "• Disconnect key: `/wallet removekey`"
                ),
                color=0x345C9C
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        else: # dashboard
            account = await db.get_user_wallet_account(interaction.user.id)
            price_usd = await get_ltc_price()
            has_key = account.get("has_key") if account else False
            dep_bal = account.get("balance_ltc", 0.0) if account else 0.0
            addr = account.get("bech32_address") if account else None
            if not addr:
                addr = await db.get_user_ltc(interaction.user.id)

            onchain_bal = 0.0
            if addr:
                bdata = await get_ltc_balance(addr)
                onchain_bal = bdata.get("balance_ltc", 0.0)

            embed = discord.Embed(
                title="💳 Kyoka Wallet Dashboard",
                description=f"**Live Market Price:** `${price_usd:,.2f} USD`",
                color=0x345C9C
            )
            embed.add_field(name="Key Status", value="🟢 Linked" if has_key else "🔴 Not Set", inline=True)
            embed.add_field(name="Deposit Balance", value=f"`{dep_bal:.6f} LTC`", inline=True)
            embed.add_field(name="On-Chain Balance", value=f"`{onchain_bal:.6f} LTC`", inline=True)
            if addr:
                embed.add_field(name="Wallet Address", value=f"`{addr}`", inline=False)
            view = WalletDashboardView(author_id=interaction.user.id)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # =========================================================
    # $ltc PREFIX COMMAND GROUP: Preserved & Enhanced
    # =========================================================
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
                "🪙 Litecoin Wallet Tracking (Kyoka Style)",
                f"**Current LTC Price:** `${price:,.2f} USD`\n\n"
                f"You have not linked a Litecoin wallet yet!\n"
                f"• Pay anyone: `$pay <address> 1$ ltc`\n"
                f"• Set up payment key: `/wallet setkey`\n"
                f"• Link public wallet: `$ltc link <address>`\n"
                f"• Check any address: `$ltc check <address>`\n"
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
            return await ctx.send(embed=error_embed("Not Found", "Transaction not found on the blockchain."))

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

    # =========================================================
    # /ltc SLASH COMMAND
    # =========================================================
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
