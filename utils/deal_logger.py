import discord
from typing import Optional, Dict, Any
from utils.embeds import standard_embed, success_embed
from utils.database import db

async def log_deal_completed(
    guild: discord.Guild,
    order: Dict[str, Any],
    completed_by: Optional[discord.Member | discord.User] = None,
    custom_branding: Optional[str] = None
) -> Optional[discord.Message]:
    """
    Sends the polished green 'Deal Completed' embed to the configured deal-log channel.
    Matches Requirement 7 reference format.
    """
    if not guild or not order:
        return None

    # Prevent duplicate deal log if already completed
    # Fetch shop config
    cfg = await db.get_shop_config(guild.id)
    shop_name = custom_branding or cfg.get("shop_name", "Jack's Shop")
    deal_log_channel_id = cfg.get("deal_log_channel_id")

    # If deal_log_channel_id is not set, try default_channels in config or guild settings
    if not deal_log_channel_id:
        settings = await db.get_guild_settings(guild.id)
        deal_log_channel_id = settings.get("trade_channel_id") or settings.get("vouch_channel_id")

    channel = guild.get_channel(deal_log_channel_id) if deal_log_channel_id else None
    if not channel:
        return None

    customer_id = order.get("user_id")
    customer = guild.get_member(customer_id)
    customer_mention = customer.mention if customer else f"<@{customer_id}>"

    # Completed by
    if completed_by:
        staff_mention = completed_by.mention
    elif order.get("claimed_by"):
        staff_member = guild.get_member(order["claimed_by"])
        staff_mention = staff_member.mention if staff_member else f"<@{order['claimed_by']}>"
    else:
        staff_mention = "Automated Digital Delivery"

    product_name = order.get("product_name", "Product")
    quantity = order.get("quantity", 1)
    items_display = f"{product_name} (x{quantity})" if quantity > 1 else product_name

    price_usd = float(order.get("total_usd", 0.0))
    receipt_id = order.get("receipt_id", f"RD-{order.get('order_id', '000000')}")

    # Calculate customer lifetime spending automatically
    lifetime_spend = await db.get_customer_lifetime_spend(guild.id, customer_id)

    # Green Deal Completed Embed (0x2ECC71)
    embed = discord.Embed(
        title="🤝 Deal Completed",
        color=0x2ECC71,
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Customer", value=customer_mention, inline=False)
    embed.add_field(name="Items", value=items_display, inline=False)
    embed.add_field(name="Price", value=f"${price_usd:.2f}", inline=False)
    embed.add_field(name="Completed by", value=staff_mention, inline=False)
    embed.add_field(name="Receipt", value=receipt_id, inline=False)
    embed.add_field(name="Customer lifetime spend", value=f"${lifetime_spend:.2f}", inline=False)

    if customer and customer.display_avatar:
        embed.set_thumbnail(url=customer.display_avatar.url)

    embed.set_footer(text=f"{shop_name} • Deal Completed")

    try:
        msg = await channel.send(embed=embed)
        return msg
    except Exception as e:
        print(f"[DEAL LOG] Error sending deal log: {e}")
        return None
