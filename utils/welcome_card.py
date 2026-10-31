import io
import os
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import discord

FONTS_DIR = r"C:\Windows\Fonts"

def get_font(size: int, bold: bool = False):
    """Retrieve an installed Windows TrueType font or fallback safely."""
    font_names = ["segoeuib.ttf", "arialbd.ttf"] if bold else ["segoeui.ttf", "arial.ttf", "calibri.ttf"]
    for name in font_names:
        font_path = os.path.join(FONTS_DIR, name)
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue
    return ImageFont.load_default()

def create_circular_avatar(avatar_img: Image.Image, size: int) -> Image.Image:
    """Resize avatar and apply a smooth anti-aliased circular mask."""
    avatar_img = avatar_img.convert("RGBA")
    avatar_img = avatar_img.resize((size, size), Image.Resampling.LANCZOS)
    
    # 4x super-sampled mask for smooth edges
    scale = 4
    mask = Image.new("L", (size * scale, size * scale), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, size * scale, size * scale), fill=255)
    mask = mask.resize((size, size), Image.Resampling.LANCZOS)
    
    output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    output.paste(avatar_img, (0, 0), mask=mask)
    return output

def generate_welcome_image_sync(avatar_bytes: bytes, username: str, guild_name: str, member_count: int) -> io.BytesIO:
    """Generate a sleek, futuristic dark-mode welcome banner."""
    width, height = 1000, 380
    banner = Image.new("RGBA", (width, height), (12, 14, 22, 255))
    draw = ImageDraw.Draw(banner)

    # 1. Subtle horizontal gradient background
    for x in range(width):
        r = int(12 + (24 - 12) * (x / width))
        g = int(15 + (32 - 15) * (x / width))
        b = int(24 + (52 - 24) * (x / width))
        draw.line([(x, 0), (x, height)], fill=(r, g, b, 255))

    # 2. Glowing background accents (ambient orbs)
    glow_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_overlay)
    # Cyan/Blue left glow behind avatar
    glow_draw.ellipse([(-50, 40), (320, 410)], fill=(88, 101, 242, 60))
    # Magenta/Violet right glow
    glow_draw.ellipse([(650, -50), (1050, 350)], fill=(155, 89, 182, 45))
    glow_overlay = glow_overlay.filter(ImageFilter.GaussianBlur(50))
    banner = Image.alpha_composite(banner, glow_overlay)
    draw = ImageDraw.Draw(banner)

    # 3. Inner Card Glass Effect Container
    margin = 18
    card_shape = [margin, margin, width - margin, height - margin]
    draw.rounded_rectangle(card_shape, radius=22, fill=(20, 24, 38, 200), outline=(88, 101, 242, 120), width=2)

    # 4. Avatar Rendering
    avatar_size = 190
    av_x, av_y = 65, (height - avatar_size) // 2

    # Avatar outer glow ring
    ring_padding = 6
    ring_rect = [av_x - ring_padding, av_y - ring_padding, av_x + avatar_size + ring_padding, av_y + avatar_size + ring_padding]
    draw.ellipse(ring_rect, fill=(88, 101, 242, 255))
    
    # Inner ring accent
    inner_ring = [av_x - 2, av_y - 2, av_x + avatar_size + 2, av_y + avatar_size + 2]
    draw.ellipse(inner_ring, fill=(20, 24, 38, 255))

    try:
        raw_avatar = Image.open(io.BytesIO(avatar_bytes))
        avatar = create_circular_avatar(raw_avatar, avatar_size)
        banner.paste(avatar, (av_x, av_y), mask=avatar)
    except Exception:
        # Fallback circle if avatar fails
        draw.ellipse([av_x, av_y, av_x + avatar_size, av_y + avatar_size], fill=(88, 101, 242, 255))

    # 5. Typography and Text
    text_x = av_x + avatar_size + 50

    # Top Tagline: "WELCOME TO <SERVER>"
    font_sub = get_font(20, bold=True)
    server_text = f"WELCOME TO {guild_name.upper()}"
    if len(server_text) > 36:
        server_text = server_text[:33] + "..."
    draw.text((text_x, 82), server_text, fill=(148, 155, 164), font=font_sub)

    # Main Username Header
    font_title = get_font(46, bold=True)
    clean_user = username if len(username) <= 20 else username[:18] + "..."
    draw.text((text_x, 116), clean_user, fill=(255, 255, 255), font=font_title)

    # Decorative Accent Line
    draw.line([(text_x, 185), (text_x + 350, 185)], fill=(88, 101, 242, 220), width=3)

    # Member Count Pill Badge
    font_badge = get_font(20, bold=True)
    badge_text = f"🎉 MEMBER #{member_count:,}"
    badge_x, badge_y = text_x, 210
    badge_w, badge_h = 240, 42
    draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], radius=12, fill=(88, 101, 242, 50), outline=(88, 101, 242, 200), width=2)
    draw.text((badge_x + 18, badge_y + 8), badge_text, fill=(254, 231, 92), font=font_badge)

    # Bottom Welcome Message
    font_bottom = get_font(18, bold=False)
    draw.text((text_x, 275), "Enjoy your stay & make sure to check out our shop & rules!", fill=(181, 186, 193), font=font_bottom)

    # Export to memory
    output = io.BytesIO()
    banner.convert("RGB").save(output, format="PNG", quality=95)
    output.seek(0)
    return output

async def generate_welcome_card(member: discord.Member) -> discord.File:
    """Download avatar asynchronously and compile the dynamic welcome banner."""
    import asyncio
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(member.display_avatar.url) as resp:
                if resp.status == 200:
                    avatar_bytes = await resp.read()
                else:
                    avatar_bytes = b""
        except Exception:
            avatar_bytes = b""

    # Run image synthesis in worker thread to prevent event loop blocking
    img_buffer = await asyncio.to_thread(
        generate_welcome_image_sync,
        avatar_bytes,
        member.display_name,
        member.guild.name,
        member.guild.member_count
    )

    return discord.File(fp=img_buffer, filename="welcome.png")
