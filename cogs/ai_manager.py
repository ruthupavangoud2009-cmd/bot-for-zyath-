import discord
from discord.ext import commands
import time
import asyncio
from typing import Optional, List, Dict, Any

from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db
from utils.ai_engine import generate_ai_shop_response

class AIManager(commands.Cog):
    """
    Intelligent AI Store & Ticket Assistant.
    Monitors customer tickets when sellers are offline, answers inquiries, scans restocks, and tracks live inventory.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Track last AI reply timestamp per channel to prevent spam (channel_id: float)
        self.last_reply: Dict[int, float] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bots and DMs
        if message.author.bot or not message.guild:
            return

        # Ignore bot prefix commands
        content = message.content.strip()
        if content.startswith("$") or content.startswith("/"):
            return

        # Check if current channel is an active ticket in database
        ticket = await db.get_ticket_record(message.channel.id)
        if not ticket or ticket.get("status") != "open":
            return

        # Check if message is from the ticket creator (customer)
        if message.author.id != ticket["user_id"]:
            return

        # Check AI settings for this server
        ai_cfg = await db.get_ai_settings(message.guild.id)
        if not ai_cfg.get("enabled", True):
            return

        # Check if sellers/staff are offline
        settings = await db.get_guild_settings(message.guild.id)
        staff_role_id = settings.get("ticket_staff_role_id")
        seller_offline = False

        if staff_role_id:
            staff_role = message.guild.get_role(staff_role_id)
            if staff_role and staff_role.members:
                # Check if ANY staff member is online
                online_staff = [m for m in staff_role.members if m.status != discord.Status.offline]
                if not online_staff:
                    seller_offline = True
            else:
                seller_offline = True
        else:
            # Check guild administrators
            online_admins = [m for m in message.guild.members if m.guild_permissions.administrator and not m.bot and m.status != discord.Status.offline]
            if not online_admins:
                seller_offline = True

        # Check if offline_only is enabled
        is_bot_mentioned = self.bot.user in message.mentions if self.bot.user else False
        if ai_cfg.get("offline_only", True) and not seller_offline and not is_bot_mentioned:
            return

        # Cooldown check: 18 seconds per channel (unless explicitly pinging the bot)
        now = time.time()
        last_t = self.last_reply.get(message.channel.id, 0)
        if not is_bot_mentioned and (now - last_t) < 18:
            return

        self.last_reply[message.channel.id] = now

        # Show typing indicator
        try:
            async with message.channel.typing():
                await asyncio.sleep(1.2)  # Natural conversational pacing
                response = await generate_ai_shop_response(
                    guild_id=message.guild.id,
                    user_query=content,
                    user_name=message.author.display_name,
                    seller_offline=seller_offline,
                    custom_prompt=ai_cfg.get("custom_prompt", "")
                )
                await message.reply(content=response, mention_author=False)
        except Exception:
            pass

    # ==========================================
    # AI RESTOCK & SCANNER
    # ==========================================
    @commands.command(name="airestock", aliases=["stockscan", "addstock"], help="AI stock scanner: feed raw accounts/keys or attach a .txt file. E.g. $airestock Nitro 1 Year [list]")
    @commands.has_permissions(administrator=True)
    async def ai_restock(self, ctx: commands.Context, item_name: str, *, raw_data: str = None):
        """
        Intelligently scans, parses, counts, and imports bulk stock into the database.
        Accepts pasted lines or text file attachments.
        """
        lines = []

        # Read from attachments first if provided
        if ctx.message.attachments:
            for att in ctx.message.attachments:
                if att.filename.endswith(".txt") or att.filename.endswith(".csv"):
                    try:
                        content_bytes = await att.read()
                        text = content_bytes.decode("utf-8", errors="ignore")
                        lines.extend(text.splitlines())
                    except Exception as e:
                        return await ctx.send(embed=error_embed("Attachment Read Error", f"Could not read attachment: {e}"))

        # Also read from raw_data if provided
        if raw_data:
            lines.extend(raw_data.splitlines())

        # Clean and filter lines
        clean_lines = [l.strip() for l in lines if l.strip()]
        if not clean_lines:
            return await ctx.send(embed=error_embed(
                "No Stock Lines Detected",
                "**Usage:** `$airestock <Item Name> [paste lines or attach .txt file]`\n\n"
                "**Example:**\n"
                "```\n"
                "$airestock Nitro 1 Year\n"
                "key1-xxxx-yyyy\n"
                "key2-xxxx-yyyy\n"
                "key3-xxxx-yyyy\n"
                "```"
            ))

        # Add to database
        added_count = await db.add_stock_batch(ctx.guild.id, item_name, clean_lines)
        total_stock = await db.get_item_stock_count(ctx.guild.id, item_name)

        # Mask sample preview for privacy
        sample_preview = []
        for sample in clean_lines[:3]:
            if len(sample) > 6:
                sample_preview.append(f"`{sample[:3]}***{sample[-2:]}`")
            else:
                sample_preview.append("`***`")
        sample_str = ", ".join(sample_preview) if sample_preview else "None"

        embed = standard_embed(
            title=f"🤖 AI Stock Scanner • {item_name}",
            description=(
                f"Successfully parsed and ingested fresh stock into the secure database!\n\n"
                f"📦 **Product:** `{item_name}`\n"
                f"📥 **Units Scanned & Ingested:** `{added_count}` items\n"
                f"📈 **Total Live Stock:** `{total_stock}` units in database\n"
                f"🔒 **Sample Verification:** {sample_str}\n\n"
                f"📢 **Next Step:**\n"
                f"Broadcast this restock to your members using:\n"
                f"`$restock #channel @everyone {item_name} | $Price | Fresh batch available now!`"
            ),
            color=0x2ECC71
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=f"Zyath AI Inventory Management • {ctx.guild.name}")
        await ctx.send(embed=embed)

    @commands.command(name="stock", aliases=["inventory"], help="View real-time stock levels of all products in the store.")
    async def view_stock(self, ctx: commands.Context):
        items = await db.get_shop_items(ctx.guild.id)
        stock_counts = await db.get_stock_counts(ctx.guild.id)

        if not items and not stock_counts:
            return await ctx.send(embed=info_embed(
                "Shop Inventory",
                "No products currently listed in the store.\n*Admins can add stock using `$airestock <Item Name>`!*"
            ))

        embed = standard_embed(
            title=f"📊 {ctx.guild.name} • Live Stock Inventory",
            description=(
                f"> Real-time stock audit monitored by **Zyath AI Assistant**\n"
                f"> Verified products: `{len(items)}` | Direct 1-click orders available in `$shop`\n"
            ),
            color=0x2B2D31
        )

        # If items exist in shop_items
        shown_names = set()
        for it in items:
            shown_names.add(it["name"].lower())
            cnt = stock_counts.get(it["name"], 0)
            status_emoji = "🟢" if cnt > 0 else "🟡"
            status_text = f"**{cnt} units available**" if cnt > 0 else "*Available on order (Instant Delivery)*"
            embed.add_field(
                name=f"{status_emoji} {it['name']} — `{it['price']}`",
                value=f"└ 📦 **Stock:** {status_text}\n└ 🏷️ **Category:** `{it['category']}`",
                inline=False
            )

        # Also show any stock batches not yet tied to a shop_item
        for name, cnt in stock_counts.items():
            if name.lower() not in shown_names:
                embed.add_field(
                    name=f"📦 {name}",
                    value=f"└ **Stock:** 🟢 **{cnt} units available**\n└ *Use `$shopadd` to link to storefront*",
                    inline=False
                )

        embed.set_footer(text="Live Inventory • Powered by Zyath AI Assistant")
        await ctx.send(embed=embed)

    @commands.command(name="clearstock", help="Purge all stock for a specific product. E.g. $clearstock Nitro 1 Year")
    @commands.has_permissions(administrator=True)
    async def clear_product_stock(self, ctx: commands.Context, *, item_name: str):
        count = await db.clear_stock(ctx.guild.id, item_name)
        if count > 0:
            await ctx.send(embed=success_embed("Stock Cleared", f"Purged `{count}` stock records for **{item_name}**."))
        else:
            await ctx.send(embed=error_embed("No Stock Found", f"No active stock found for `{item_name}`."))

    # ==========================================
    # DIRECT AI QUERY & CONFIGURATION
    # ==========================================
    @commands.command(name="ai", aliases=["ask"], help="Ask the AI Store Assistant any question. E.g. $ai do you have nitro in stock?")
    async def ask_ai(self, ctx: commands.Context, *, question: str):
        async with ctx.typing():
            reply = await generate_ai_shop_response(
                guild_id=ctx.guild.id,
                user_query=question,
                user_name=ctx.author.display_name,
                seller_offline=False
            )
            embed = standard_embed(
                title="🤖 Zyath Intelligence • Automated Response",
                description=f"> **Query:** *\"{question}\"*\n\n{reply}",
                color=0x2B2D31
            )
            embed.set_footer(text=f"Requested by {ctx.author.display_name} • Zyath Neural Engine")
            await ctx.send(embed=embed)

    @commands.command(name="aimanager", aliases=["aitoggle"], help="Toggle the automated AI assistant in tickets on or off. E.g. $aimanager on")
    @commands.has_permissions(administrator=True)
    async def toggle_ai_manager(self, ctx: commands.Context, status: str = None):
        curr = await db.get_ai_settings(ctx.guild.id)
        if not status:
            new_val = not curr.get("enabled", True)
        else:
            new_val = status.lower() in ["on", "enable", "true", "yes", "1"]

        await db.set_ai_settings(ctx.guild.id, enabled=new_val)
        state_str = "ENABLED 🟢" if new_val else "DISABLED 🔴"
        await ctx.send(embed=success_embed(
            "AI Manager Updated",
            f"Automated AI Ticket Manager is now **{state_str}**!\n"
            f"When staff/sellers are offline, the AI will assist customers with products, stock, prices, and payments."
        ))

    @commands.command(name="aisettings", help="View current AI Shop Manager configuration and status.")
    @commands.has_permissions(administrator=True)
    async def ai_settings_cmd(self, ctx: commands.Context):
        cfg = await db.get_ai_settings(ctx.guild.id)
        stock_counts = await db.get_stock_counts(ctx.guild.id)
        total_units = sum(stock_counts.values())

        enabled_str = "🟢 Active (Online)" if cfg.get("enabled", True) else "🔴 Disabled"
        mode_str = "💤 Offline Only (Triggers when staff is away)" if cfg.get("offline_only", True) else "🌐 Always Active"
        prompt_str = f"```{cfg['custom_prompt']}```" if cfg.get("custom_prompt") else "*Default Professional Shop Persona*"

        embed = standard_embed(
            title="⚙️ Zyath AI Store Manager Telemetry",
            description=(
                f"> **Autonomous Storefront Assistant**\n"
                f"> 24/7 intelligent ticket responder & inventory scanner.\n"
            ),
            color=0x2B2D31
        )
        embed.add_field(name="🤖 Assistant Status", value=enabled_str, inline=True)
        embed.add_field(name="🎯 Trigger Mode", value=mode_str, inline=True)
        embed.add_field(name="📦 Stocked Units in DB", value=f"`{total_units}` items across `{len(stock_counts)}` products", inline=True)
        embed.add_field(name="🧠 Custom Instructions", value=prompt_str, inline=False)
        embed.add_field(
            name="💡 Admin Commands",
            value=(
                "• `$aimanager <on|off>` - Enable or disable AI assistant\n"
                "• `$airestock <Product> [list]` - Ingest stock into AI scanner\n"
                "• `$stock` - Check real-time inventory levels\n"
                "• `$restock #channel @everyone <Item>` - Broadcast restock alert\n"
                "• `$aisetprompt <text>` - Set custom store rules for the AI"
            ),
            inline=False
        )
        embed.set_footer(text=f"Zyath Assistant • Server: {ctx.guild.name}")
        await ctx.send(embed=embed)

    @commands.command(name="aisetprompt", help="Set custom instructions or store policies for the AI. E.g. $aisetprompt Delivery takes 5 mins. Crypto only.")
    @commands.has_permissions(administrator=True)
    async def set_ai_prompt(self, ctx: commands.Context, *, custom_instructions: str):
        await db.set_ai_settings(ctx.guild.id, custom_prompt=custom_instructions)
        await ctx.send(embed=success_embed(
            "AI Instructions Saved",
            f"Successfully updated AI Store persona instructions:\n```{custom_instructions}```"
        ))

async def setup(bot: commands.Bot):
    await bot.add_cog(AIManager(bot))
