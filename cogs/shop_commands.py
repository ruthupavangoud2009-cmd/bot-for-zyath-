import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, List
import datetime
from utils.embeds import standard_embed, success_embed, error_embed, info_embed, warning_embed
from utils.database import db
from utils.ltc import get_ltc_price, verify_ltc_payment, shorten_address, get_ltc_qr_url
from utils.deal_logger import log_deal_completed

class ShopCommands(commands.Cog):
    """Complete premium shop command suite covering products, orders, cart, coupons, and staff tools."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ==========================================
    # 1. PRODUCT COMMANDS ($product ...)
    # ==========================================
    @commands.group(name="product", invoke_without_command=True)
    async def product_group(self, ctx: commands.Context, *, product_name: str = None):
        """View info for a product or list all products."""
        if product_name:
            await self.show_product_info(ctx, product_name)
        else:
            await self.list_products(ctx)

    async def list_products(self, ctx: commands.Context, category: str = None):
        items = await db.get_shop_items(ctx.guild.id, category)
        if not items:
            return await ctx.send(embed=info_embed("Products", f"No products found{' in ' + category if category else ''}."))
        desc = f"**Available Products ({len(items)}):**\n\n"
        for i in items[:15]:
            desc += f"• **#{i['id']} • {i['name']}** — `{i['price']}` (`{i['category']}`)\n  *{i['description'] or 'In stock'}*\n"
        embed = standard_embed(title=f"📦 {ctx.guild.name} • Product Catalog", description=desc, color=0x2ECC71)
        await ctx.send(embed=embed)

    async def show_product_info(self, ctx: commands.Context, query: str):
        items = await db.get_shop_items(ctx.guild.id)
        matched = None
        for i in items:
            if query.lower() in i["name"].lower() or (query.isdigit() and int(query) == i["id"]):
                matched = i
                break
        if not matched:
            return await ctx.send(embed=error_embed("Product Not Found", f"No product matched `{query}`."))

        stock_count = await db.get_item_stock_count(ctx.guild.id, matched["name"])
        embed = standard_embed(
            title=f"📦 Product #{matched['id']} • {matched['name']}",
            description=(
                f"• **Price:** `{matched['price']}`\n"
                f"• **Category:** `{matched['category']}`\n"
                f"• **Stock Available:** `{'🟢 ' + str(stock_count) if stock_count > 0 else '🟢 Active'}`\n"
                f"• **Details:**\n```{matched['description'] or 'Instant delivery.'}```"
            ),
            color=0x2ECC71
        )
        await ctx.send(embed=embed)

    @product_group.command(name="add")
    @commands.has_permissions(administrator=True)
    async def product_add(self, ctx: commands.Context, *, details: str):
        """Add a product. Usage: $product add <Name> | <Price> | [Category] | [Description]"""
        parts = [p.strip() for p in details.split("|")]
        if len(parts) < 2:
            return await ctx.send(embed=error_embed("Invalid Format", "Format: `$product add <Name> | <Price> | [Category] | [Description]`"))
        name, price = parts[0], parts[1]
        cat = parts[2] if len(parts) > 2 and parts[2] else "General"
        desc = parts[3] if len(parts) > 3 else ""
        item_id = await db.add_shop_item(ctx.guild.id, name, price, cat, desc)
        await ctx.send(embed=success_embed("Product Added", f"Created product **#{item_id} • {name}** (`{price}`)."))

    @product_group.command(name="remove", aliases=["del", "delete"])
    @commands.has_permissions(administrator=True)
    async def product_remove(self, ctx: commands.Context, item_id: int):
        """Delete a product by ID."""
        removed = await db.remove_shop_item(ctx.guild.id, item_id)
        if removed:
            await ctx.send(embed=success_embed("Product Removed", f"Deleted product `#{item_id}`."))
        else:
            await ctx.send(embed=error_embed("Not Found", f"No product with ID `#{item_id}`."))

    @product_group.command(name="list")
    async def product_list_cmd(self, ctx: commands.Context, category: str = None):
        """List all shop products."""
        await self.list_products(ctx, category)

    @product_group.command(name="info")
    async def product_info_cmd(self, ctx: commands.Context, *, name_or_id: str):
        """View detailed information for a specific product."""
        await self.show_product_info(ctx, name_or_id)

    @product_group.command(name="stock")
    async def product_stock_cmd(self, ctx: commands.Context, *, product_name: str = None):
        """View digital stock inventory for products."""
        if product_name:
            count = await db.get_item_stock_count(ctx.guild.id, product_name)
            await ctx.send(embed=info_embed("Product Stock", f"**{product_name}:** `{count}` digital unit(s) in stock."))
        else:
            counts = await db.get_stock_counts(ctx.guild.id)
            if not counts:
                return await ctx.send(embed=info_embed("Stock Inventory", "No digital stock recorded. Admins can add stock with `$airestock <Item> <keys>`."))
            desc = "\n".join([f"• **{k}:** `{v}` available" for k, v in counts.items()])
            embed = standard_embed(title="📊 Shop Stock Inventory", description=desc, color=0x2ECC71)
            await ctx.send(embed=embed)

    # ==========================================
    # 2. ORDERS & CART COMMANDS ($order, $buy, $cart, $track, $receipt)
    # ==========================================
    @commands.command(name="buy")
    async def buy_cmd(self, ctx: commands.Context, *, product_query: str = None):
        """Instant purchase flow for an item."""
        if not product_query:
            return await ctx.send(embed=info_embed("How to Buy", "Run `$buy <Product Name>` or use `$shoppanel` to open an interactive purchase ticket!"))
        items = await db.get_shop_items(ctx.guild.id)
        matched = None
        for i in items:
            if product_query.lower() in i["name"].lower() or (product_query.isdigit() and int(product_query) == i["id"]):
                matched = i
                break
        if not matched:
            return await ctx.send(embed=error_embed("Not Found", f"No product matching `{product_query}`."))

        # Direct user to shop panel
        await ctx.send(embed=success_embed(
            "Ready to Purchase",
            f"You selected **{matched['name']}** (`{matched['price']}`).\n"
            f"Click the button on our Purchase Panel or run `$shoppanel` to start your private checkout session!"
        ))

    @commands.command(name="cart")
    async def cart_cmd(self, ctx: commands.Context, action: str = None, item_id: int = None, quantity: int = 1):
        """View or manage your shopping cart. Usage: $cart, $cart add <ID> [qty], $cart clear"""
        if action == "add" and item_id:
            await db.add_to_cart(ctx.guild.id, ctx.author.id, item_id, quantity)
            return await ctx.send(embed=success_embed("Added to Cart", f"Added `{quantity}x` of item `#{item_id}` to your cart."))
        elif action == "clear":
            await db.clear_cart(ctx.guild.id, ctx.author.id)
            return await ctx.send(embed=success_embed("Cart Cleared", "Your shopping cart is now empty."))
        elif action == "remove" and item_id:
            await db.remove_from_cart(ctx.guild.id, ctx.author.id, item_id)
            return await ctx.send(embed=success_embed("Removed", f"Removed item `#{item_id}` from your cart."))

        cart_items = await db.get_cart(ctx.guild.id, ctx.author.id)
        if not cart_items:
            return await ctx.send(embed=info_embed("Shopping Cart", "Your cart is currently empty.\nAdd items using `$cart add <Item ID>`."))

        desc = "**Items in your Shopping Cart:**\n\n"
        total = 0.0
        for ci in cart_items:
            price_str = ci["price"].replace("$", "").replace("USD", "").strip()
            try:
                p = float(price_str)
            except Exception:
                p = 5.0
            sub = p * ci["quantity"]
            total += sub
            desc += f"• **{ci['name']}** (x{ci['quantity']}) — `${sub:.2f}`\n"

        desc += f"\n**Total:** `${total:.2f} USD`\n*Open a ticket on `$shoppanel` to complete checkout.*"
        embed = standard_embed(title=f"🛒 {ctx.author.display_name}'s Shopping Cart", description=desc, color=0x2ECC71)
        await ctx.send(embed=embed)

    @commands.group(name="order", invoke_without_command=True)
    async def order_group(self, ctx: commands.Context, order_id: str = None):
        """Inspect order status or manage orders."""
        if order_id:
            await self.view_order(ctx, order_id)
        else:
            orders = await db.get_user_orders(ctx.guild.id, ctx.author.id)
            if not orders:
                return await ctx.send(embed=info_embed("Your Orders", "You have not placed any orders yet."))
            desc = "\n".join([f"• `{o['order_id']}` — **{o['product_name']}** (`${o['total_usd']:.2f}`) — `{o['status'].title()}`" for o in orders[:8]])
            embed = standard_embed(title="📦 Your Orders", description=desc, color=0x2ECC71)
            await ctx.send(embed=embed)

    async def view_order(self, ctx: commands.Context, order_id: str):
        clean = order_id.strip()
        order = await db.get_shop_order(clean)
        if not order:
            return await ctx.send(embed=error_embed("Order Not Found", f"No order found with ID `{clean}`."))

        # Permissions check: buyer or staff
        if order["user_id"] != ctx.author.id and not ctx.author.guild_permissions.manage_messages:
            return await ctx.send(embed=error_embed("Unauthorized", "You can only view your own orders."))

        tx_str = f"[`{shorten_address(order['txid'])}`](https://litecoinspace.org/tx/{order['txid']})" if order.get("txid") else "Pending"
        embed = standard_embed(
            title=f"📦 Order Status • {order['order_id']}",
            description=(
                f"• **Customer:** <@{order['user_id']}>\n"
                f"• **Product:** `{order['product_name']}` (x{order['quantity']})\n"
                f"• **Total USD:** `${order['total_usd']:.2f}`\n"
                f"• **Total LTC:** `{order['total_ltc']:.6f} LTC`\n"
                f"• **Status:** `{order['status'].title()}`\n"
                f"• **Receipt:** `{order['receipt_id']}`\n"
                f"• **TXID:** {tx_str}\n"
                f"• **Created:** `{order.get('created_at', 'Recent')}`"
            ),
            color=0x2ECC71 if order["status"] == "completed" else 0xFEE75C
        )
        await ctx.send(embed=embed)

    @order_group.command(name="view")
    async def order_view(self, ctx: commands.Context, order_id: str):
        """View full details and blockchain status of an order."""
        await self.view_order(ctx, order_id)

    @order_group.command(name="history")
    async def order_history(self, ctx: commands.Context, member: discord.Member = None):
        """View purchase history for yourself or another user."""
        target = member or ctx.author
        orders = await db.get_user_orders(ctx.guild.id, target.id)
        if not orders:
            return await ctx.send(embed=info_embed("Purchase History", f"{target.mention} has no orders."))
        desc = "\n".join([f"• `{o['order_id']}` — **{o['product_name']}** (`${o['total_usd']:.2f}`) — `{o['status'].title()}`" for o in orders[:10]])
        embed = standard_embed(title=f"📜 Order History • {target.display_name}", description=desc, color=0x2ECC71)
        await ctx.send(embed=embed)

    @order_group.command(name="claim")
    @commands.has_permissions(manage_messages=True)
    async def order_claim_cmd(self, ctx: commands.Context, order_id: str):
        """Staff: claim an order to handle fulfillment."""
        success = await db.claim_order(order_id, ctx.author.id)
        if success:
            await ctx.send(embed=success_embed("Order Claimed", f"🌟 {ctx.author.mention} claimed Order `{order_id}`."))
        else:
            await ctx.send(embed=error_embed("Failed", f"Could not claim Order `{order_id}`."))

    @order_group.command(name="complete")
    @commands.has_permissions(manage_messages=True)
    async def order_complete_cmd(self, ctx: commands.Context, order_id: str):
        """Staff: mark an order as fulfilled and trigger Deal Completed log."""
        order = await db.complete_order(order_id, staff_id=ctx.author.id)
        if not order:
            return await ctx.send(embed=error_embed("Not Found", f"Order `{order_id}` not found."))
        await ctx.send(embed=success_embed("Order Completed", f"Order `{order['order_id']}` completed by {ctx.author.mention}!"))
        cfg = await db.get_shop_config(ctx.guild.id)
        await log_deal_completed(ctx.guild, order, completed_by=ctx.author, custom_branding=cfg.get("shop_name"))

    @order_group.command(name="cancel")
    async def order_cancel_cmd(self, ctx: commands.Context, order_id: str):
        """Cancel a pending order."""
        order = await db.get_shop_order(order_id)
        if not order:
            return await ctx.send(embed=error_embed("Not Found", f"Order `{order_id}` not found."))
        if order["user_id"] != ctx.author.id and not ctx.author.guild_permissions.manage_messages:
            return await ctx.send(embed=error_embed("Unauthorized", "Access denied."))
        await db.cancel_order(order_id)
        await ctx.send(embed=warning_embed("Order Cancelled", f"Order `{order_id}` was marked as cancelled."))

    @order_group.command(name="refund")
    @commands.has_permissions(administrator=True)
    async def order_refund_cmd(self, ctx: commands.Context, order_id: str, *, reason: str = "Customer requested refund"):
        """Admin: mark an order as refunded."""
        success = await db.refund_order(order_id, reason)
        if success:
            await ctx.send(embed=warning_embed("Order Refunded", f"Order `{order_id}` was refunded.\nReason: *{reason}*"))
        else:
            await ctx.send(embed=error_embed("Not Found", f"Order `{order_id}` could not be refunded."))

    @commands.command(name="track")
    async def track_cmd(self, ctx: commands.Context, order_or_receipt_id: str):
        """Track an order or receipt ID in real time."""
        clean = order_or_receipt_id.strip()
        order = await db.get_shop_order(clean) or await db.get_order_by_receipt(clean)
        if not order:
            return await ctx.send(embed=error_embed("Not Found", f"No record matching `{clean}`."))
        await self.view_order(ctx, order["order_id"])

    @commands.command(name="receipt")
    async def receipt_cmd(self, ctx: commands.Context, receipt_id: str):
        """Look up verified transaction receipt."""
        clean = receipt_id.strip()
        order = await db.get_order_by_receipt(clean)
        if not order:
            return await ctx.send(embed=error_embed("Receipt Not Found", f"No transaction found for Receipt `{clean}`."))
        embed = standard_embed(
            title=f"🧾 Verified Receipt • {order['receipt_id']}",
            description=(
                f"• **Order ID:** `{order['order_id']}`\n"
                f"• **Customer:** <@{order['user_id']}>\n"
                f"• **Item:** `{order['product_name']}` (x{order['quantity']})\n"
                f"• **Total Paid:** `${order['total_usd']:.2f}` ({order['total_ltc']:.6f} LTC)\n"
                f"• **Status:** `{order['status'].title()}`\n"
                f"• **Timestamp:** `{order.get('completed_at') or order.get('created_at')}`"
            ),
            color=0x2ECC71
        )
        await ctx.send(embed=embed)

    # ==========================================
    # 3. COUPONS & PROMOS ($coupon, $redeem)
    # ==========================================
    @commands.command(name="coupon")
    @commands.has_permissions(administrator=True)
    async def coupon_cmd(self, ctx: commands.Context, action: str, code: str = None, discount: float = 10.0):
        """Create or inspect discount promo codes. Usage: $coupon create <CODE> <percent>"""
        if action == "create" and code:
            cid = await db.create_coupon(ctx.guild.id, code, discount)
            await ctx.send(embed=success_embed("Coupon Created", f"Coupon **`{code.upper()}`** created for `{discount}%` off!"))
        elif action == "view" and code:
            c = await db.get_coupon(ctx.guild.id, code)
            if not c:
                return await ctx.send(embed=error_embed("Not Found", f"Coupon `{code}` not found."))
            await ctx.send(embed=info_embed("Coupon Details", f"• **Code:** `{c['code']}`\n• **Discount:** `{c['discount_percent']}%`\n• **Uses:** `{c['uses_count']}/{c['max_uses']}`"))
        else:
            await ctx.send(embed=info_embed("Coupon Usage", "`$coupon create <CODE> <discount_percent>`\n`$coupon view <CODE>`"))

    @commands.command(name="redeem")
    async def redeem_cmd(self, ctx: commands.Context, code: str):
        """Redeem a store coupon code for order discounts."""
        c = await db.get_coupon(ctx.guild.id, code)
        if not c:
            return await ctx.send(embed=error_embed("Invalid Coupon", "That coupon code does not exist."))
        if c["uses_count"] >= c["max_uses"]:
            return await ctx.send(embed=error_embed("Expired Coupon", "This promo code has reached its maximum usage limit."))
        await ctx.send(embed=success_embed(
            "Coupon Verified",
            f"🎉 Coupon **`{c['code']}`** is active!\nYou receive **{c['discount_percent']}% OFF** on your next purchase ticket!"
        ))

    # ==========================================
    # 4. STAFF & SHOP REVENUE COMMANDS ($shopstaff, $shop revenue, $shop stats)
    # ==========================================
    @commands.group(name="shopstaff", aliases=["storestaff", "sstaff"], invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    async def staff_group(self, ctx: commands.Context):
        """Staff order processing tools."""
        orders = await db.get_guild_orders(ctx.guild.id, limit=20, status="pending_payment")
        desc = f"**Pending Orders Awaiting Fulfillment ({len(orders)}):**\n\n"
        for o in orders[:8]:
            desc += f"• `{o['order_id']}` — **{o['product_name']}** (`${o['total_usd']:.2f}`) — <@{o['user_id']}>\n"
        embed = standard_embed(title="🛡️ Staff Order Dashboard", description=desc, color=0x5865F2)
        await ctx.send(embed=embed)

    @staff_group.command(name="claim")
    @commands.has_permissions(manage_messages=True)
    async def staff_claim(self, ctx: commands.Context, order_id: str):
        """Claim an order ticket."""
        await self.order_claim_cmd(ctx, order_id)

    @staff_group.command(name="complete")
    @commands.has_permissions(manage_messages=True)
    async def staff_complete(self, ctx: commands.Context, order_id: str):
        """Complete an order ticket."""
        await self.order_complete_cmd(ctx, order_id)

    @staff_group.command(name="deliver")
    @commands.has_permissions(manage_messages=True)
    async def staff_deliver(self, ctx: commands.Context, order_id: str, *, content: str):
        """Deliver digital credentials/files directly to customer."""
        order = await db.get_shop_order(order_id)
        if not order:
            return await ctx.send(embed=error_embed("Not Found", "Order not found."))
        customer = ctx.guild.get_member(order["user_id"])
        if customer:
            try:
                await customer.send(embed=success_embed(
                    f"🎁 Digital Delivery • Order {order['order_id']}",
                    f"Here is your order content for **{order['product_name']}**:\n```\n{content}\n```"
                ))
            except Exception:
                await ctx.send(f"⚠️ Could not DM customer. Sending in ticket channel.")
        await ctx.send(embed=success_embed("Delivered", f"Delivered order contents for `{order_id}`."))
        await db.complete_order(order_id, staff_id=ctx.author.id)

    @staff_group.command(name="stats")
    @commands.has_permissions(manage_messages=True)
    async def staff_stats(self, ctx: commands.Context):
        """View server sales and revenue statistics."""
        stats = await db.get_shop_revenue_stats(ctx.guild.id)
        cfg = await db.get_shop_config(ctx.guild.id)
        shop_title = cfg.get("shop_name", "Kyoka Shop")

        top_p = "\n".join([f"• **{p[0]}:** `{p[1]}` sold" for p in stats["top_products"]]) if stats["top_products"] else "None"
        desc = (
            f"> 💰 **Total Revenue:** `${stats['total_revenue']:,.2f} USD`\n"
            f"> 📅 **Monthly Revenue (30d):** `${stats['monthly_revenue']:,.2f} USD`\n"
            f"> ⚡ **Daily Revenue (24h):** `${stats['daily_revenue']:,.2f} USD`\n\n"
            f"📦 **Orders Completed:** `{stats['completed_orders']}` of `{stats['total_orders']}` total\n\n"
            f"🏆 **Top Selling Products:**\n{top_p}"
        )
        embed = standard_embed(title=f"📊 {shop_title} • Sales & Revenue Analytics", description=desc, color=0x2ECC71)
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.send(embed=embed)

    @commands.command(name="shopsupport", aliases=["tickethelp", "customersupport"])
    async def support_cmd(self, ctx: commands.Context, *, details: str = "General Support Request"):
        """Open a dedicated customer support ticket."""
        from cogs.tickets import CreateTicketModal
        await ctx.send(embed=info_embed(
            "Customer Support",
            "Please use our ticket system or click the button below to reach 24/7 staff support."
        ))

async def setup(bot: commands.Bot):
    await bot.add_cog(ShopCommands(bot))
