import discord
import json
import os
from datetime import datetime

# Load configuration for default colors
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
def get_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

config = get_config()

# Primary Colors
COLOR_PRIMARY = config.get("embed_color", 0x2B2D31)   # Discord Dark Theme
COLOR_SUCCESS = config.get("success_color", 0x57F287)   # Emerald Green
COLOR_ERROR = config.get("error_color", 0xED4245)       # Crimson Red
COLOR_WARNING = config.get("warning_color", 0xFEE75C)   # Radiant Gold
COLOR_INFO = config.get("info_color", 0x5865F2)         # Modern Blurple

def standard_embed(
    title: str = None,
    description: str = None,
    color: int = COLOR_PRIMARY,
    author: discord.User | discord.Member = None,
    footer_text: str = None,
    footer_icon: str = None,
    thumbnail: str = None,
    image: str = None
) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.utcnow()
    )
    if author:
        embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)
    if footer_text:
        embed.set_footer(text=footer_text, icon_url=footer_icon)
    else:
        embed.set_footer(text="Kyoka Shop • All-in-One Discord Suite")
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    if image:
        embed.set_image(url=image)
    return embed

def success_embed(title: str = "Success", description: str = "") -> discord.Embed:
    return standard_embed(
        title=f"✅ {title}",
        description=f"> {description}" if description and not description.startswith(">") and "\n" not in description else description,
        color=COLOR_SUCCESS
    )

def error_embed(title: str = "Error", description: str = "") -> discord.Embed:
    return standard_embed(
        title=f"❌ {title}",
        description=f"> {description}" if description and not description.startswith(">") and "\n" not in description else description,
        color=COLOR_ERROR
    )

def warning_embed(title: str = "Warning", description: str = "") -> discord.Embed:
    return standard_embed(
        title=f"⚠️ {title}",
        description=f"> {description}" if description and not description.startswith(">") and "\n" not in description else description,
        color=COLOR_WARNING
    )

def info_embed(title: str = "Information", description: str = "") -> discord.Embed:
    return standard_embed(
        title=f"ℹ️ {title}",
        description=f"> {description}" if description and not description.startswith(">") and "\n" not in description else description,
        color=COLOR_INFO
    )
