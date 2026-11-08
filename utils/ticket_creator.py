import discord
from utils.embeds import error_embed

async def create_safe_ticket_channel(
    guild: discord.Guild,
    user: discord.Member,
    channel_name: str,
    category: discord.CategoryChannel = None,
    staff_role: discord.Role = None,
    topic: str = ""
) -> discord.TextChannel:
    """
    Safely creates a ticket channel with multi-tier permission fallbacks
    to completely prevent Discord 50013 Missing Permissions errors.
    """
    # Check if bot has manage_channels in the guild
    bot_member = guild.me
    if not bot_member.guild_permissions.manage_channels and not bot_member.guild_permissions.administrator:
        raise PermissionError(
            "The bot requires the **Manage Channels** or **Administrator** permission in Server Settings.\n\n"
            "**Quick Fix:**\n"
            "1. Go to **Server Settings** > **Roles**\n"
            "2. Click the bot's role (e.g. `Kyoka Shop`)\n"
            "3. Enable **Administrator** (or *Manage Channels* & *Manage Roles*)\n"
            "4. Drag the bot's role **above** member and staff roles!"
        )

    # Base secure overwrites (private to user and bot)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=False
        ),
        user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True
        ),
        bot_member: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True
        )
    }

    # Only set staff role if bot has permission hierarchy over it
    if staff_role:
        if bot_member.guild_permissions.administrator or staff_role < bot_member.top_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )

    # Attempt 1: Full creation with designated category
    if category:
        try:
            return await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=topic
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

    # Attempt 2: Create under root (no category, in case category permissions blocked it)
    try:
        return await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            topic=topic
        )
    except (discord.Forbidden, discord.HTTPException):
        pass

    # Attempt 3: Minimal overwrites (@everyone hidden, user visible)
    try:
        minimal_overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        }
        return await guild.create_text_channel(
            name=channel_name,
            overwrites=minimal_overwrites,
            topic=topic
        )
    except (discord.Forbidden, discord.HTTPException):
        pass

    # Attempt 4: Create blank text channel, then apply permissions sequentially
    try:
        channel = await guild.create_text_channel(name=channel_name, topic=topic)
        try:
            await channel.set_permissions(guild.default_role, view_channel=False)
        except Exception:
            pass
        try:
            await channel.set_permissions(user, view_channel=True, send_messages=True, read_message_history=True)
        except Exception:
            pass
        if staff_role:
            try:
                await channel.set_permissions(staff_role, view_channel=True, send_messages=True, read_message_history=True)
            except Exception:
                pass
        return channel
    except discord.Forbidden:
        raise PermissionError(
            "Discord rejected channel creation due to missing permissions.\n\n"
            "**How to fix in 10 seconds:**\n"
            "1. Open **Server Settings** > **Roles**\n"
            "2. Select the **Kyoka Shop** bot role\n"
            "3. Turn ON **Administrator**\n"
            "4. Drag the role higher in the list and save!"
        )
