from aiohttp import web
import os
import asyncio
from datetime import datetime

routes = web.RouteTableDef()
start_time = datetime.utcnow()

@routes.get('/')
async def home(request):
    uptime_delta = datetime.utcnow() - start_time
    hours, remainder = divmod(int(uptime_delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zyath Bot • 24/7 Online</title>
    <style>
        body {{
            background: linear-gradient(135deg, #0b0e14 0%, #1a1f2c 100%);
            color: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
        }}
        .card {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(88, 101, 242, 0.3);
            border-radius: 16px;
            padding: 40px 48px;
            text-align: center;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            max-width: 440px;
        }}
        .badge {{
            display: inline-flex;
            align-items: center;
            background: rgba(87, 242, 135, 0.15);
            color: #57F287;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 20px;
            border: 1px solid rgba(87, 242, 135, 0.4);
        }}
        .dot {{
            width: 8px;
            height: 8px;
            background: #57F287;
            border-radius: 50%;
            margin-right: 8px;
            box-shadow: 0 0 8px #57F287;
        }}
        h1 {{
            margin: 0 0 10px 0;
            font-size: 28px;
            color: #ffffff;
        }}
        p {{
            color: #949ba4;
            margin: 0 0 24px 0;
            font-size: 15px;
            line-height: 1.5;
        }}
        .stats {{
            background: rgba(0, 0, 0, 0.25);
            border-radius: 10px;
            padding: 14px;
            font-size: 13px;
            color: #dbdee1;
            border-left: 3px solid #5865F2;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="badge"><span class="dot"></span>24/7 ONLINE & HEALTHY</div>
        <h1>Zyath Multi-Purpose Bot</h1>
        <p>Bot is actively connected to Discord Gateway and serving all shop, moderation, tickets, and game commands.</p>
        <div class="stats">
            <strong>System Uptime:</strong> {uptime_str} &bull; Port Binding OK
        </div>
    </div>
</body>
</html>"""
    return web.Response(text=html_content, content_type='text/html')

@routes.get('/health')
async def health(request):
    return web.json_response({"status": "healthy", "service": "Zyath Bot", "timestamp": str(datetime.utcnow())})

@routes.get('/ping')
async def ping(request):
    return web.Response(text="pong")

async def start_web_server():
    """Start web server on the port assigned by Render or default to 10000."""
    port = int(os.environ.get("PORT", 10000))
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"\033[92m[RENDER WEB SERVICE]\033[0m Port binding successful on 0.0.0.0:{port} (24/7 Health Check Active)")
