import os
import re
import aiohttp
from typing import Dict, Any, List, Optional
from utils.database import db

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

async def generate_ai_shop_response(
    guild_id: int,
    user_query: str,
    user_name: str,
    seller_offline: bool = False,
    custom_prompt: str = ""
) -> str:
    """
    Intelligent AI Shop Assistant response generator.
    Uses Gemini API if key is available, or advanced built-in semantic store engine as fallback.
    """
    clean_query = user_query.strip()
    
    # 1. Fetch live database store context
    items = await db.get_shop_items(guild_id)
    stock_counts = await db.get_stock_counts(guild_id)
    payment_methods = await db.get_payment_methods(guild_id)
    tos = await db.get_shop_tos(guild_id)
    
    # Build text summary of inventory and stock
    item_lines = []
    for it in items:
        stk = stock_counts.get(it["name"], 0)
        stk_str = f"{stk} in stock" if stk > 0 else "Instant Delivery / In Stock"
        desc_str = f" - {it['description']}" if it.get("description") else ""
        item_lines.append(f"• {it['name']}: {it['price']} [{it['category']}] ({stk_str}){desc_str}")
    catalog_text = "\n".join(item_lines) if item_lines else "No products currently listed in shop."

    pay_lines = []
    for pm in payment_methods:
        note_str = f" ({pm['note']})" if pm.get("note") else ""
        pay_lines.append(f"• {pm['method_name']}: {pm['address']}{note_str}")
    payments_text = "\n".join(pay_lines) if pay_lines else "Payment methods available via ticket."

    tos_text = tos or "All sales final upon delivery. 24h replacement warranty with proof."

    # 2. If Gemini API key is configured, query Gemini
    if GEMINI_API_KEY:
        try:
            prompt = f"""You are Zyath AI Assistant, the professional automated store & ticket manager for this Discord shop.
Your goal is to assist customers politely, accurately, and concisely.

STORE CONTEXT:
Items & Stock:
{catalog_text}

Accepted Payment Gateways:
{payments_text}

Terms of Service & Warranty:
{tos_text}

Seller Status: {'OFFLINE / AWAY (Staff will fulfill order once back)' if seller_offline else 'ONLINE'}
{f'Custom Store Instructions: {custom_prompt}' if custom_prompt else ''}

Customer Name: {user_name}
Customer Question: "{clean_query}"

INSTRUCTIONS:
1. If the seller is offline, briefly inform the customer that staff is away, but you are here to assist.
2. Answer the customer's question directly using the store context (prices, stock, payment methods, or warranty).
3. Keep the response friendly, professional, clean markdown, under 180 words.
4. If they want to buy, tell them they can send payment details or specify their order item."""

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.4, "maxOutputTokens": 300}
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=8) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            reply = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            if reply and reply.strip():
                                return reply.strip()
        except Exception:
            pass  # Fall back to built-in semantic engine

    # 3. Built-In Semantic Shop Manager Engine
    q = clean_query.lower()

    # Prefix offline notice if seller is offline
    offline_prefix = ""
    if seller_offline:
        offline_prefix = "💤 **Support Notice:** *Staff / Sellers are currently offline or away. I am your automated AI Shop Assistant, here to help 24/7!*\n\n"

    # Intent A: Stock inquiry
    if any(w in q for w in ["stock", "in stock", "have any", "available", "left", "how many", "quantity"]):
        # Check if asking about specific product
        matched_items = []
        for it in items:
            if it["name"].lower() in q:
                matched_items.append(it)

        if matched_items:
            res_lines = [f"{offline_prefix}📊 **Live Stock Status:**"]
            for m in matched_items:
                cnt = stock_counts.get(m["name"], 0)
                status = f"🟢 **{cnt} units available**" if cnt > 0 else "🟢 **In Stock** (Instant fulfillment)"
                res_lines.append(f"• **{m['name']}** — `{m['price']}`: {status}")
            res_lines.append("\n👉 *Click an item in `$shop` or type `$ticket` to purchase immediately!*")
            return "\n".join(res_lines)
        else:
            res_lines = [f"{offline_prefix}📦 **Current Shop Inventory & Stock:**"]
            for it in items[:8]:
                cnt = stock_counts.get(it["name"], 0)
                stk_msg = f"`{cnt} in stock`" if cnt > 0 else "`Ready to order`"
                res_lines.append(f"• **{it['name']}** — `{it['price']}` ({stk_msg})")
            if not items:
                res_lines.append("No products currently listed. Staff will restock soon!")
            else:
                res_lines.append("\n💡 *To order any product, use `$shop` or tell us what you'd like to buy!*")
            return "\n".join(res_lines)

    # Intent B: Price / Cost inquiry
    if any(w in q for w in ["price", "cost", "how much", "pricing", "rate", "rates", "cheap"]):
        matched = [it for it in items if it["name"].lower() in q]
        if matched:
            res_lines = [f"{offline_prefix}🏷️ **Pricing Information:**"]
            for m in matched:
                res_lines.append(f"• **{m['name']}**: `{m['price']}` (*{m['category']}*)")
                if m.get("description"):
                    res_lines.append(f"  └ *{m['description']}*")
            res_lines.append("\n💳 *We accept Crypto, LTC, PayPal, and more! Type `$payment` for addresses.*")
            return "\n".join(res_lines)
        else:
            res_lines = [f"{offline_prefix}🛒 **Product Catalog & Prices:**"]
            for it in items[:8]:
                res_lines.append(f"• **{it['name']}**: `{it['price']}`")
            res_lines.append("\n✨ *Browse all products with `$shop`!*")
            return "\n".join(res_lines)

    # Intent C: Payment methods / Wallets
    if any(w in q for w in ["payment", "pay", "crypto", "ltc", "litecoin", "paypal", "btc", "bitcoin", "cashapp", "wallet", "address", "methods", "gateway"]):
        res_lines = [f"{offline_prefix}💳 **Accepted Payment Gateways:**"]
        if payment_methods:
            for pm in payment_methods:
                note = f" — *{pm['note']}*" if pm.get("note") else ""
                res_lines.append(f"• **{pm['method_name']}**: `{pm['address']}`{note}")
            res_lines.append("\n📌 *After sending payment, please send a screenshot or transaction hash here for instant verification!*")
        else:
            res_lines.append("• We accept Crypto (LTC/BTC/USDT), PayPal, and CashApp.")
            res_lines.append("\n📌 *Staff will drop the official address in this ticket shortly!*")
        return "\n".join(res_lines)

    # Intent D: TOS / Warranty / Replacement / Legit
    if any(w in q for w in ["tos", "warranty", "replace", "replacement", "refund", "policy", "legit", "proof", "safe", "scam"]):
        return (
            f"{offline_prefix}🛡️ **Shop Terms & Warranty Policy:**\n"
            f"> {tos_text}\n\n"
            f"⭐ **Reputation:** Check our verified vouch record with `$vouches` or `$vouchlb`!\n"
            f"🔒 All transactions are protected and tracked by Zyath Assistant."
        )

    # Intent E: How to buy / Order
    if any(w in q for w in ["how to buy", "how do i buy", "buy", "order", "purchase", "want"]):
        return (
            f"{offline_prefix}🛒 **How to Complete Your Purchase:**\n"
            f"1. **Specify Your Item**: Tell us which item and quantity you'd like.\n"
            f"2. **Choose Payment**: Check accepted methods with `$payment` (LTC, PayPal, etc.).\n"
            f"3. **Send Payment & Proof**: Post your payment screenshot or TXID here.\n"
            f"4. **Fulfillment**: Staff will deliver your items with warranty!\n\n"
            f"✨ *If staff is currently offline, leave your details and we will deliver immediately upon return.*"
        )

    # Intent F: Greeting / General inquiry
    if any(w in q for w in ["hi", "hello", "hey", "sup", "anyone", "seller", "here", "help"]):
        return (
            f"{offline_prefix}👋 **Hey {user_name}! Welcome to the support desk.**\n\n"
            f"I'm the **Zyath AI Shop Assistant**! Here's what I can help you with:\n"
            f"• 📦 **Check Stock**: Ask me `Do you have Nitro in stock?`\n"
            f"• 💰 **Check Prices**: Ask me `How much is Nitro?`\n"
            f"• 💳 **Payment Methods**: Ask me `What payment methods do you take?`\n"
            f"• 🛡️ **Warranty & TOS**: Ask me `What is your warranty?`\n\n"
            f"Feel free to ask any question or leave your order details below!"
        )

    # Default smart assistant response
    return (
        f"{offline_prefix}🤖 **Zyath AI Assistant Response:**\n"
        f"Thank you for reaching out, {user_name}! I am monitoring this ticket while staff is handling orders.\n\n"
        f"• **Shop Catalog**: Browse items with `$shop`\n"
        f"• **Payment Gateways**: Check addresses with `$payment`\n"
        f"• **Live Vouches**: View seller reputation with `$vouches`\n\n"
        f"Please leave all details about your request or order, and our staff will fulfill it right away!"
    )
