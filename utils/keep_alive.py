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
    <title>Kyoka Shop • 24/7 Online</title>
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
        <h1>Kyoka Shop Bot</h1>
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
    return web.json_response({"status": "healthy", "service": "Kyoka Shop", "timestamp": str(datetime.utcnow())})

@routes.get('/ping')
async def ping(request):
    return web.Response(text="pong")

@routes.get('/api/shop/stats')
async def api_shop_stats(request):
    try:
        from utils.database import db
        # If guild_id is provided in query params, use it, else default to 0
        gid = int(request.query.get("guild_id", 0))
        stats = await db.get_shop_revenue_stats(gid)
        feedback_stats = await db.get_feedback_stats(gid)
        legit_count = await db.get_legit_count(gid)
        cfg = await db.get_shop_config(gid)
        return web.json_response({
            "status": "success",
            "shop_name": cfg.get("shop_name", "Jack's Shop"),
            "revenue": stats,
            "feedback": feedback_stats,
            "legit_vouches": legit_count
        })
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

@routes.get('/api/shop/orders')
async def api_shop_orders(request):
    try:
        from utils.database import db
        gid = int(request.query.get("guild_id", 0))
        orders = await db.get_guild_orders(gid, limit=50)
        return web.json_response({"status": "success", "orders": [dict(o) for o in orders]})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

@routes.get('/api/shop/products')
async def api_shop_products(request):
    try:
        from utils.database import db
        gid = int(request.query.get("guild_id", 0))
        products = await db.get_shop_items(gid)
        counts = await db.get_stock_counts(gid)
        res = []
        for p in products:
            item = dict(p)
            item["stock_available"] = counts.get(p["name"], 0)
            res.append(item)
        return web.json_response({"status": "success", "products": res})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

@routes.get('/dashboard')
async def dashboard_page(request):
    from utils.database import db
    gid = int(request.query.get("guild_id", 0))
    cfg = await db.get_shop_config(gid)
    stats = await db.get_shop_revenue_stats(gid)
    feedback_stats = await db.get_feedback_stats(gid)
    legit_count = await db.get_legit_count(gid)
    orders = await db.get_guild_orders(gid, limit=10)
    products = await db.get_shop_items(gid)
    counts = await db.get_stock_counts(gid)
    shop_title = cfg.get("shop_name", "Jack's Shop")

    orders_html = "".join([
        f"<tr><td><code>{o['order_id']}</code></td><td>{o['product_name']} (x{o['quantity']})</td><td>${o['total_usd']:.2f}</td><td><code>{o.get('total_ltc', 0.0):.6f} LTC</code></td><td><span class='badge-status {o['status']}'>{o['status'].title()}</span></td><td><code>{o['receipt_id']}</code></td></tr>"
        for o in orders
    ]) or "<tr><td colspan='6' style='text-align:center; color:#949ba4;'>No orders recorded yet.</td></tr>"

    products_html = "".join([
        f"<tr><td><code>#{p['id']}</code></td><td><strong>{p['name']}</strong></td><td>{p['price']}</td><td><span class='category-tag'>{p['category']}</span></td><td><span class='stock-tag'>{counts.get(p['name'], 0)} units</span></td></tr>"
        for p in products
    ]) or "<tr><td colspan='5' style='text-align:center; color:#949ba4;'>No products added to catalog yet.</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{shop_title} • Shop Administration Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: #0d1117;
            color: #e6edf3;
            font-family: 'Inter', -apple-system, sans-serif;
            min-height: 100vh;
            padding: 32px 24px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 28px;
            padding-bottom: 20px;
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }}
        .brand {{ display: flex; align-items: center; gap: 12px; }}
        .brand-icon {{ font-size: 28px; }}
        h1 {{ font-size: 24px; font-weight: 700; color: #ffffff; }}
        .subtitle {{ font-size: 14px; color: #8b949e; margin-top: 4px; }}
        .badge-live {{
            background: rgba(46, 204, 113, 0.15);
            color: #2ecc71;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
            border: 1px solid rgba(46, 204, 113, 0.3);
        }}
        .dot {{ width: 8px; height: 8px; background: #2ecc71; border-radius: 50%; box-shadow: 0 0 6px #2ecc71; }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 28px;
        }}
        .card {{
            background: rgba(22, 27, 34, 0.7);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 20px;
        }}
        .card-label {{ font-size: 13px; color: #8b949e; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px; }}
        .card-value {{ font-size: 26px; font-weight: 700; color: #ffffff; margin-top: 8px; }}
        .card-sub {{ font-size: 12px; color: #2ecc71; margin-top: 4px; }}
        .section-title {{ font-size: 18px; font-weight: 600; margin: 28px 0 14px 0; display: flex; align-items: center; gap: 8px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: rgba(22, 27, 34, 0.7);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 24px;
        }}
        th, td {{ padding: 12px 16px; text-align: left; font-size: 14px; border-bottom: 1px solid rgba(255,255,255,0.05); }}
        th {{ background: rgba(33, 38, 45, 0.7); color: #8b949e; font-weight: 600; text-transform: uppercase; font-size: 12px; }}
        code {{ background: rgba(110, 118, 129, 0.2); padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 13px; color: #58a6ff; }}
        .badge-status {{ padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: 600; }}
        .badge-status.completed {{ background: rgba(46, 204, 113, 0.2); color: #2ecc71; }}
        .badge-status.pending_payment {{ background: rgba(241, 196, 15, 0.2); color: #f1c40f; }}
        .badge-status.cancelled {{ background: rgba(231, 76, 60, 0.2); color: #e74c3c; }}
        .category-tag {{ background: rgba(88, 101, 242, 0.2); color: #5865f2; padding: 2px 8px; border-radius: 4px; font-size: 12px; }}
        .stock-tag {{ background: rgba(46, 204, 113, 0.15); color: #2ecc71; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
        .footer {{ text-align: center; color: #8b949e; font-size: 13px; margin-top: 40px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.08); }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="brand">
                <span class="brand-icon">🛒</span>
                <div>
                    <h1>{shop_title} Administration</h1>
                    <div class="subtitle">Live Discord Shop & Litecoin Blockchain Gateway</div>
                </div>
            </div>
            <div class="badge-live"><span class="dot"></span>SHOP & BLOCKCHAIN ONLINE</div>
        </div>

        <div class="grid">
            <div class="card">
                <div class="card-label">Total Revenue</div>
                <div class="card-value">${stats['total_revenue']:,.2f}</div>
                <div class="card-sub">⚡ ${stats['monthly_revenue']:,.2f} last 30d</div>
            </div>
            <div class="card">
                <div class="card-label">Completed Deals</div>
                <div class="card-value">{stats['completed_orders']}</div>
                <div class="card-sub">📦 {stats['total_orders']} total orders</div>
            </div>
            <div class="card">
                <div class="card-label">Legit Vouches</div>
                <div class="card-value">{legit_count}</div>
                <div class="card-sub">⭐ 100% Community Verified</div>
            </div>
            <div class="card">
                <div class="card-label">Satisfaction Rating</div>
                <div class="card-value">{feedback_stats['avg_stars']}/5.0</div>
                <div class="card-sub">💬 {feedback_stats['total']} customer reviews</div>
            </div>
        </div>

        <div class="section-title">📦 Recent Orders & Blockchain Invoices</div>
        <table>
            <thead>
                <tr>
                    <th>Order ID</th>
                    <th>Product & Qty</th>
                    <th>Total (USD)</th>
                    <th>Total (LTC)</th>
                    <th>Status</th>
                    <th>Receipt ID</th>
                </tr>
            </thead>
            <tbody>
                {orders_html}
            </tbody>
        </table>

        <div class="section-title">🛍️ Active Product Inventory</div>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Product Name</th>
                    <th>Price</th>
                    <th>Category</th>
                    <th>Digital Stock</th>
                </tr>
            </thead>
            <tbody>
                {products_html}
            </tbody>
        </table>

        <div class="footer">
            &copy; {shop_title} &bull; Powered by Kyoka Shop Discord Store Architecture &bull; All Rights Reserved.
        </div>
    </div>
</body>
</html>"""
    return web.Response(text=html, content_type='text/html')

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
