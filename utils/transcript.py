import discord
import io
import html
from datetime import datetime

async def generate_text_transcript(channel: discord.TextChannel) -> discord.File:
    """Generates a formatted text file transcript of the given channel."""
    lines = [
        f"=== TRANSCRIPT FOR #{channel.name} ===",
        f"Server: {channel.guild.name} (ID: {channel.guild.id})",
        f"Exported at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "=" * 45,
        ""
    ]

    async for msg in channel.history(limit=500, oldest_first=True):
        timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        author = f"{msg.author.name} ({msg.author.id})"
        content = msg.content or ""
        
        # Attachments
        if msg.attachments:
            att_urls = " [Attachments: " + ", ".join(a.url for a in msg.attachments) + "]"
            content += att_urls
            
        # Embed summaries
        if msg.embeds:
            for em in msg.embeds:
                content += f"\n  [Embed: {em.title or ''} - {em.description or ''}]"

        lines.append(f"[{timestamp}] {author}: {content}")

    output_text = "\n".join(lines)
    buffer = io.BytesIO(output_text.encode("utf-8"))
    buffer.seek(0)
    return discord.File(buffer, filename=f"transcript-{channel.name}.txt")

async def generate_html_transcript(channel: discord.TextChannel) -> discord.File:
    """Generates an aesthetic modern dark-themed HTML transcript."""
    messages_html = []
    
    async for msg in channel.history(limit=500, oldest_first=True):
        timestamp = msg.created_at.strftime("%b %d, %Y %I:%M %p")
        author_name = html.escape(msg.author.display_name)
        avatar_url = msg.author.display_avatar.url
        content_text = html.escape(msg.clean_content) if msg.clean_content else ""

        att_html = ""
        for att in msg.attachments:
            att_html += f'<div class="att"><a href="{att.url}" target="_blank">📎 {html.escape(att.filename)}</a></div>'

        embed_html = ""
        for em in msg.embeds:
            title = f"<h4>{html.escape(em.title)}</h4>" if em.title else ""
            desc = f"<p>{html.escape(em.description)}</p>" if em.description else ""
            embed_html += f'<div class="embed">{title}{desc}</div>'

        messages_html.append(f"""
        <div class="message">
            <img class="avatar" src="{avatar_url}" alt="{author_name}">
            <div class="msg-body">
                <div class="msg-header">
                    <span class="author">{author_name}</span>
                    <span class="time">{timestamp}</span>
                </div>
                <div class="content">{content_text}</div>
                {att_html}
                {embed_html}
            </div>
        </div>
        """)

    body_content = "\n".join(messages_html)
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Transcript #{html.escape(channel.name)}</title>
    <style>
        body {{
            background-color: #1e1f22;
            color: #dbdee1;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
        }}
        .header {{
            background-color: #2b2d31;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #5865f2;
        }}
        .header h2 {{ margin: 0 0 8px 0; color: #ffffff; }}
        .header p {{ margin: 0; color: #949ba4; font-size: 14px; }}
        .message {{
            display: flex;
            margin-bottom: 16px;
            padding: 6px 10px;
            border-radius: 6px;
        }}
        .message:hover {{ background-color: #2b2d31; }}
        .avatar {{
            width: 42px;
            height: 42px;
            border-radius: 50%;
            margin-right: 14px;
        }}
        .msg-body {{ flex: 1; }}
        .msg-header {{ margin-bottom: 4px; }}
        .author {{ font-weight: 600; color: #f2f3f5; margin-right: 8px; }}
        .time {{ font-size: 12px; color: #949ba4; }}
        .content {{ line-height: 1.4; word-break: break-word; }}
        .att a {{ color: #00a8fc; text-decoration: none; font-size: 14px; margin-top: 6px; display: inline-block; }}
        .embed {{
            background: #2b2d31;
            border-left: 4px solid #5865f2;
            padding: 10px 14px;
            border-radius: 4px;
            margin-top: 8px;
        }}
        .embed h4 {{ margin: 0 0 6px 0; color: #ffffff; }}
        .embed p {{ margin: 0; font-size: 14px; color: #dbdee1; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>Channel: #{html.escape(channel.name)}</h2>
        <p>Server: {html.escape(channel.guild.name)} | Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    </div>
    {body_content}
</body>
</html>"""
    
    buffer = io.BytesIO(full_html.encode("utf-8"))
    buffer.seek(0)
    return discord.File(buffer, filename=f"transcript-{channel.name}.html")
