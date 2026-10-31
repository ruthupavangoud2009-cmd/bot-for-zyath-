import os
import json
import time
import asyncio
import aiosqlite
import asyncpg
from typing import Optional, List, Dict, Tuple, Any

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
SQLITE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "zyath_bot.db")

def get_database_url() -> Optional[str]:
    url = os.getenv("DATABASE_URL")
    if url and url.strip():
        return url.strip()
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("database_url")
        except Exception:
            pass
    return None

PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id BIGINT PRIMARY KEY,
    prefix TEXT DEFAULT '$',
    vouch_channel_id BIGINT,
    trade_channel_id BIGINT,
    modlog_channel_id BIGINT,
    welcome_channel_id BIGINT,
    leave_channel_id BIGINT,
    welcome_message TEXT,
    leave_message TEXT,
    ticket_category_id BIGINT,
    ticket_logs_channel_id BIGINT,
    ticket_staff_role_id BIGINT,
    autorole_id BIGINT
);

CREATE TABLE IF NOT EXISTS vouches (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    target_id BIGINT NOT NULL,
    author_id BIGINT NOT NULL,
    stars INTEGER DEFAULT 5,
    comment TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    mm_id BIGINT NOT NULL,
    buyer_id BIGINT NOT NULL,
    seller_id BIGINT NOT NULL,
    amount TEXT NOT NULL,
    details TEXT NOT NULL,
    status TEXT DEFAULT 'In Progress',
    channel_id BIGINT,
    message_id BIGINT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shop_items (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    name TEXT NOT NULL,
    price TEXT NOT NULL,
    category TEXT DEFAULT 'General',
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS warnings (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    mod_id BIGINT NOT NULL,
    reason TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL UNIQUE,
    user_id BIGINT NOT NULL,
    category TEXT DEFAULT 'General Support',
    status TEXT DEFAULT 'open',
    claimed_by BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payment_methods (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    method_name TEXT NOT NULL,
    address TEXT NOT NULL,
    note TEXT
);

CREATE TABLE IF NOT EXISTS shop_tos (
    guild_id BIGINT PRIMARY KEY,
    tos_text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS no_prefix_users (
    user_id BIGINT PRIMARY KEY,
    added_by BIGINT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ticket_categories (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    name TEXT NOT NULL,
    emoji TEXT DEFAULT '🎫',
    description TEXT DEFAULT 'Open a support ticket',
    category_channel_id BIGINT,
    staff_role_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, name)
);

CREATE TABLE IF NOT EXISTS shop_stock (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    item_name TEXT NOT NULL,
    stock_data TEXT NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_settings (
    guild_id BIGINT PRIMARY KEY,
    enabled BOOLEAN DEFAULT TRUE,
    offline_only BOOLEAN DEFAULT TRUE,
    custom_prompt TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id INTEGER PRIMARY KEY,
    prefix TEXT DEFAULT '$',
    vouch_channel_id INTEGER,
    trade_channel_id INTEGER,
    modlog_channel_id INTEGER,
    welcome_channel_id INTEGER,
    leave_channel_id INTEGER,
    welcome_message TEXT,
    leave_message TEXT,
    ticket_category_id INTEGER,
    ticket_logs_channel_id INTEGER,
    ticket_staff_role_id INTEGER,
    autorole_id INTEGER
);

CREATE TABLE IF NOT EXISTS vouches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    stars INTEGER DEFAULT 5,
    comment TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    guild_id INTEGER NOT NULL,
    mm_id INTEGER NOT NULL,
    buyer_id INTEGER NOT NULL,
    seller_id INTEGER NOT NULL,
    amount TEXT NOT NULL,
    details TEXT NOT NULL,
    status TEXT DEFAULT 'In Progress',
    channel_id INTEGER,
    message_id INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shop_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    price TEXT NOT NULL,
    category TEXT DEFAULT 'General',
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    mod_id INTEGER NOT NULL,
    reason TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL UNIQUE,
    user_id INTEGER NOT NULL,
    category TEXT DEFAULT 'General Support',
    status TEXT DEFAULT 'open',
    claimed_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payment_methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    method_name TEXT NOT NULL,
    address TEXT NOT NULL,
    note TEXT
);

CREATE TABLE IF NOT EXISTS shop_tos (
    guild_id INTEGER PRIMARY KEY,
    tos_text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS no_prefix_users (
    user_id INTEGER PRIMARY KEY,
    added_by INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ticket_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    emoji TEXT DEFAULT '🎫',
    description TEXT DEFAULT 'Open a support ticket',
    category_channel_id INTEGER,
    staff_role_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, name)
);

CREATE TABLE IF NOT EXISTS shop_stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    stock_data TEXT NOT NULL,
    is_used BOOLEAN DEFAULT 0,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_settings (
    guild_id INTEGER PRIMARY KEY,
    enabled BOOLEAN DEFAULT 1,
    offline_only BOOLEAN DEFAULT 1,
    custom_prompt TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

class Database:
    def __init__(self, sqlite_path: str = SQLITE_PATH):
        self.sqlite_path = sqlite_path
        self.is_postgres = False
        self.pool: Optional[asyncpg.Pool] = None
        self._np_cache = set()

    async def init(self):
        """Initialize database connection to Supabase PostgreSQL with SQLite fallback."""
        db_url = get_database_url()
        if db_url:
            try:
                # Attempt to create asyncpg pool
                self.pool = await asyncpg.create_pool(
                    dsn=db_url,
                    min_size=1,
                    max_size=10,
                    command_timeout=15,
                    timeout=10
                )
                async with self.pool.acquire() as conn:
                    await conn.execute(PG_SCHEMA)
                self.is_postgres = True
                print("\033[92m[DATABASE]\033[0m Successfully connected to Supabase PostgreSQL!")
            except Exception as e:
                print(f"\033[93m[DATABASE WARNING]\033[0m Could not connect to Supabase: {e}. Falling back to SQLite.")
                self.is_postgres = False

        if not self.is_postgres:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.executescript(SQLITE_SCHEMA)
                await db.commit()
            print("\033[92m[DATABASE]\033[0m Local SQLite database initialized.")

        await self.load_np_cache()

    async def ping(self) -> Tuple[float, str]:
        """Measure database query round-trip latency in milliseconds."""
        t_start = time.perf_counter()
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1;")
            engine = "Supabase PostgreSQL"
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("SELECT 1;")
            engine = "Local SQLite"
        latency_ms = (time.perf_counter() - t_start) * 1000
        return round(latency_ms, 2), engine

    async def load_np_cache(self):
        """Loads whitelisted no-prefix users into in-memory cache for fast sync lookups."""
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT user_id FROM no_prefix_users")
                self._np_cache = {int(r["user_id"]) for r in rows}
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("SELECT user_id FROM no_prefix_users")
                rows = await cursor.fetchall()
                self._np_cache = {int(r[0]) for r in rows}

    def is_no_prefix_cached(self, user_id: int) -> bool:
        return user_id in self._np_cache

    # ==========================================
    # GUILD SETTINGS
    # ==========================================
    async def get_guild_settings(self, guild_id: int) -> Dict[str, Any]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM guild_settings WHERE guild_id = $1", guild_id)
                if not row:
                    await conn.execute("INSERT INTO guild_settings (guild_id) VALUES ($1) ON CONFLICT (guild_id) DO NOTHING", guild_id)
                    row = await conn.fetchrow("SELECT * FROM guild_settings WHERE guild_id = $1", guild_id)
                return dict(row) if row else {"guild_id": guild_id, "prefix": "$"}
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,))
                row = await cursor.fetchone()
                if not row:
                    await db.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,))
                    await db.commit()
                    cursor = await db.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,))
                    row = await cursor.fetchone()
                return dict(row) if row else {"guild_id": guild_id, "prefix": "$"}

    async def update_guild_setting(self, guild_id: int, key: str, value: Any):
        allowed_keys = [
            "prefix", "vouch_channel_id", "trade_channel_id", "modlog_channel_id",
            "welcome_channel_id", "leave_channel_id", "welcome_message", "leave_message",
            "ticket_category_id", "ticket_logs_channel_id", "ticket_staff_role_id", "autorole_id"
        ]
        if key not in allowed_keys:
            raise ValueError(f"Invalid setting key: {key}")

        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO guild_settings (guild_id, {key}) VALUES ($1, $2)
                    ON CONFLICT(guild_id) DO UPDATE SET {key} = $2
                """, guild_id, value)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute(f"""
                    INSERT INTO guild_settings (guild_id, {key}) VALUES (?, ?)
                    ON CONFLICT(guild_id) DO UPDATE SET {key} = ?
                """, (guild_id, value, value))
                await db.commit()

    # ==========================================
    # VOUCHES SYSTEM
    # ==========================================
    async def add_vouch(self, guild_id: int, target_id: int, author_id: int, stars: int, comment: str) -> int:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                vouch_id = await conn.fetchval("""
                    INSERT INTO vouches (guild_id, target_id, author_id, stars, comment)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                """, guild_id, target_id, author_id, stars, comment)
                return vouch_id
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("""
                    INSERT INTO vouches (guild_id, target_id, author_id, stars, comment)
                    VALUES (?, ?, ?, ?, ?)
                """, (guild_id, target_id, author_id, stars, comment))
                await db.commit()
                return cursor.lastrowid

    async def get_vouches(self, guild_id: int, target_id: int) -> List[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM vouches WHERE guild_id = $1 AND target_id = $2 ORDER BY id DESC
                """, guild_id, target_id)
                return [dict(r) for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT * FROM vouches WHERE guild_id = ? AND target_id = ? ORDER BY id DESC
                """, (guild_id, target_id))
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_vouch_stats(self, guild_id: int, target_id: int) -> Tuple[int, float]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT COUNT(*) as cnt, AVG(stars) as avg_stars 
                    FROM vouches WHERE guild_id = $1 AND target_id = $2
                """, guild_id, target_id)
                count = row["cnt"] if row and row["cnt"] else 0
                avg = float(row["avg_stars"]) if row and row["avg_stars"] else 0.0
                return count, round(avg, 1)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("""
                    SELECT COUNT(*), AVG(stars) FROM vouches WHERE guild_id = ? AND target_id = ?
                """, (guild_id, target_id))
                row = await cursor.fetchone()
                count = row[0] or 0
                avg = row[1] or 0.0
                return count, round(avg, 1)

    async def get_vouch_leaderboard(self, guild_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get ranked top vouched members for a guild."""
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT target_id, COUNT(*) as count, ROUND(AVG(stars)::numeric, 1) as avg_stars
                    FROM vouches
                    WHERE guild_id = $1
                    GROUP BY target_id
                    ORDER BY count DESC, avg_stars DESC
                    LIMIT $2
                """, guild_id, limit)
                return [{"target_id": int(r["target_id"]), "count": int(r["count"]), "avg_stars": float(r["avg_stars"])} for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT target_id, COUNT(*) as count, ROUND(AVG(stars), 1) as avg_stars
                    FROM vouches
                    WHERE guild_id = ?
                    GROUP BY target_id
                    ORDER BY count DESC, avg_stars DESC
                    LIMIT ?
                """, (guild_id, limit))
                rows = await cursor.fetchall()
                return [{"target_id": int(r["target_id"]), "count": int(r["count"]), "avg_stars": float(r["avg_stars"] or 5.0)} for r in rows]

    async def get_vouch(self, vouch_id: int) -> Optional[Dict[str, Any]]:
        """Get a single vouch record by its ID."""
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM vouches WHERE id = $1", vouch_id)
                return dict(row) if row else None
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM vouches WHERE id = ?", (vouch_id,))
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def delete_vouch(self, guild_id: int, vouch_id: int) -> bool:
        """Delete a vouch by ID."""
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                result = await conn.execute("DELETE FROM vouches WHERE id = $1 AND guild_id = $2", vouch_id, guild_id)
                return "DELETE 1" in result
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("DELETE FROM vouches WHERE id = ? AND guild_id = ?", (vouch_id, guild_id))
                await db.commit()
                return cursor.rowcount > 0

    async def get_server_vouch_stats(self, guild_id: int) -> Dict[str, Any]:
        """Aggregate vouch metrics for the entire server."""
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT COUNT(*) as total, ROUND(AVG(stars)::numeric, 1) as avg_rating
                    FROM vouches WHERE guild_id = $1
                """, guild_id)
                top = await conn.fetchrow("""
                    SELECT target_id, COUNT(*) as cnt FROM vouches 
                    WHERE guild_id = $1 GROUP BY target_id ORDER BY cnt DESC LIMIT 1
                """, guild_id)
                return {
                    "total": row["total"] if row and row["total"] else 0,
                    "avg_rating": float(row["avg_rating"]) if row and row["avg_rating"] else 0.0,
                    "top_seller_id": int(top["target_id"]) if top else None
                }
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("""
                    SELECT COUNT(*), ROUND(AVG(stars), 1) FROM vouches WHERE guild_id = ?
                """, (guild_id,))
                row = await cursor.fetchone()
                cursor2 = await db.execute("""
                    SELECT target_id, COUNT(*) as cnt FROM vouches 
                    WHERE guild_id = ? GROUP BY target_id ORDER BY cnt DESC LIMIT 1
                """, (guild_id,))
                top = await cursor2.fetchone()
                return {
                    "total": row[0] or 0,
                    "avg_rating": float(row[1] or 0.0),
                    "top_seller_id": int(top[0]) if top else None
                }

    # ==========================================
    # TRADES ($mercy live trade logger)
    # ==========================================
    async def create_trade(self, trade_id: str, guild_id: int, mm_id: int, buyer_id: int, seller_id: int, amount: str, details: str, channel_id: int = None, message_id: int = None):
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO trades (id, guild_id, mm_id, buyer_id, seller_id, amount, details, status, channel_id, message_id)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, 'In Progress', $8, $9)
                """, trade_id, guild_id, mm_id, buyer_id, seller_id, amount, details, channel_id, message_id)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("""
                    INSERT INTO trades (id, guild_id, mm_id, buyer_id, seller_id, amount, details, status, channel_id, message_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'In Progress', ?, ?)
                """, (trade_id, guild_id, mm_id, buyer_id, seller_id, amount, details, channel_id, message_id))
                await db.commit()

    async def get_trade(self, trade_id: str) -> Optional[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM trades WHERE id = $1", trade_id)
                return dict(row) if row else None
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def update_trade_status(self, trade_id: str, status: str):
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE trades SET status = $1 WHERE id = $2", status, trade_id)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("UPDATE trades SET status = ? WHERE id = ?", (status, trade_id))
                await db.commit()

    async def update_trade_message(self, trade_id: str, channel_id: int, message_id: int):
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE trades SET channel_id = $1, message_id = $2 WHERE id = $3", channel_id, message_id, trade_id)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("UPDATE trades SET channel_id = ?, message_id = ? WHERE id = ?", (channel_id, message_id, trade_id))
                await db.commit()

    # ==========================================
    # SHOP & PRODUCTS
    # ==========================================
    async def add_shop_item(self, guild_id: int, name: str, price: str, category: str, description: str) -> int:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                item_id = await conn.fetchval("""
                    INSERT INTO shop_items (guild_id, name, price, category, description)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                """, guild_id, name, price, category, description)
                return item_id
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("""
                    INSERT INTO shop_items (guild_id, name, price, category, description)
                    VALUES (?, ?, ?, ?, ?)
                """, (guild_id, name, price, category, description))
                await db.commit()
                return cursor.lastrowid

    async def get_shop_items(self, guild_id: int, category: str = None) -> List[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                if category:
                    rows = await conn.fetch("SELECT * FROM shop_items WHERE guild_id = $1 AND category = $2 ORDER BY id ASC", guild_id, category)
                else:
                    rows = await conn.fetch("SELECT * FROM shop_items WHERE guild_id = $1 ORDER BY id ASC", guild_id)
                return [dict(r) for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                if category:
                    cursor = await db.execute("SELECT * FROM shop_items WHERE guild_id = ? AND category = ? ORDER BY id ASC", (guild_id, category))
                else:
                    cursor = await db.execute("SELECT * FROM shop_items WHERE guild_id = ? ORDER BY id ASC", (guild_id,))
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_shop_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM shop_items WHERE id = $1", item_id)
                return dict(row) if row else None
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM shop_items WHERE id = ?", (item_id,))
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def remove_shop_item(self, guild_id: int, item_id: int) -> bool:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                res = await conn.execute("DELETE FROM shop_items WHERE id = $1 AND guild_id = $2", item_id, guild_id)
                return "DELETE 1" in res
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("DELETE FROM shop_items WHERE id = ? AND guild_id = ?", (item_id, guild_id))
                await db.commit()
                return cursor.rowcount > 0

    async def get_shop_categories(self, guild_id: int) -> List[str]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT DISTINCT category FROM shop_items WHERE guild_id = $1", guild_id)
                return [r["category"] for r in rows if r["category"]]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("SELECT DISTINCT category FROM shop_items WHERE guild_id = ?", (guild_id,))
                rows = await cursor.fetchall()
                return [r[0] for r in rows if r[0]]

    # ==========================================
    # MODERATION WARNINGS
    # ==========================================
    async def add_warning(self, guild_id: int, user_id: int, mod_id: int, reason: str) -> int:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                warn_id = await conn.fetchval("""
                    INSERT INTO warnings (guild_id, user_id, mod_id, reason)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                """, guild_id, user_id, mod_id, reason)
                return warn_id
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("""
                    INSERT INTO warnings (guild_id, user_id, mod_id, reason)
                    VALUES (?, ?, ?, ?)
                """, (guild_id, user_id, mod_id, reason))
                await db.commit()
                return cursor.lastrowid

    async def get_warnings(self, guild_id: int, user_id: int) -> List[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM warnings WHERE guild_id = $1 AND user_id = $2 ORDER BY id DESC", guild_id, user_id)
                return [dict(r) for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY id DESC", (guild_id, user_id))
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def clear_warnings(self, guild_id: int, user_id: int) -> int:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                res = await conn.execute("DELETE FROM warnings WHERE guild_id = $1 AND user_id = $2", guild_id, user_id)
                # Res looks like "DELETE X"
                parts = res.split()
                return int(parts[1]) if len(parts) > 1 else 0
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("DELETE FROM warnings WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
                await db.commit()
                return cursor.rowcount

    # ==========================================
    # TICKETS
    # ==========================================
    async def create_ticket_record(self, guild_id: int, channel_id: int, user_id: int, category: str) -> int:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                t_id = await conn.fetchval("""
                    INSERT INTO tickets (guild_id, channel_id, user_id, category)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                """, guild_id, channel_id, user_id, category)
                return t_id
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("""
                    INSERT INTO tickets (guild_id, channel_id, user_id, category)
                    VALUES (?, ?, ?, ?)
                """, (guild_id, channel_id, user_id, category))
                await db.commit()
                return cursor.lastrowid

    async def get_ticket_record(self, channel_id: int) -> Optional[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM tickets WHERE channel_id = $1", channel_id)
                return dict(row) if row else None
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM tickets WHERE channel_id = ?", (channel_id,))
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def claim_ticket(self, channel_id: int, staff_id: int):
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE tickets SET claimed_by = $1 WHERE channel_id = $2", staff_id, channel_id)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("UPDATE tickets SET claimed_by = ? WHERE channel_id = ?", (staff_id, channel_id))
                await db.commit()

    async def close_ticket_record(self, channel_id: int):
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE tickets SET status = 'closed' WHERE channel_id = $1", channel_id)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("UPDATE tickets SET status = 'closed' WHERE channel_id = ?", (channel_id,))
                await db.commit()

    async def reopen_ticket_record(self, channel_id: int):
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE tickets SET status = 'open' WHERE channel_id = $1", channel_id)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("UPDATE tickets SET status = 'open' WHERE channel_id = ?", (channel_id,))
                await db.commit()

    async def delete_ticket_record(self, channel_id: int):
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("DELETE FROM tickets WHERE channel_id = $1", channel_id)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("DELETE FROM tickets WHERE channel_id = ?", (channel_id,))
                await db.commit()

    # ==========================================
    # MODULAR TICKET CATEGORIES
    # ==========================================
    async def add_ticket_category(
        self,
        guild_id: int,
        name: str,
        emoji: str = "🎫",
        description: str = "Open a support ticket",
        category_channel_id: Optional[int] = None,
        staff_role_id: Optional[int] = None
    ) -> bool:
        clean_name = name.strip()
        clean_emoji = emoji.strip() if emoji else "🎫"
        clean_desc = description.strip() if description else "Open a support ticket"
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO ticket_categories (guild_id, name, emoji, description, category_channel_id, staff_role_id)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (guild_id, name) DO UPDATE SET
                        emoji = EXCLUDED.emoji,
                        description = EXCLUDED.description,
                        category_channel_id = COALESCE(EXCLUDED.category_channel_id, ticket_categories.category_channel_id),
                        staff_role_id = COALESCE(EXCLUDED.staff_role_id, ticket_categories.staff_role_id)
                """, guild_id, clean_name, clean_emoji, clean_desc, category_channel_id, staff_role_id)
                return True
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("""
                    INSERT INTO ticket_categories (guild_id, name, emoji, description, category_channel_id, staff_role_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT (guild_id, name) DO UPDATE SET
                        emoji = excluded.emoji,
                        description = excluded.description,
                        category_channel_id = COALESCE(excluded.category_channel_id, ticket_categories.category_channel_id),
                        staff_role_id = COALESCE(excluded.staff_role_id, ticket_categories.staff_role_id)
                """, (guild_id, clean_name, clean_emoji, clean_desc, category_channel_id, staff_role_id))
                await db.commit()
                return True

    async def get_ticket_categories(self, guild_id: int) -> List[Dict[str, Any]]:
        rows = []
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                res = await conn.fetch("SELECT * FROM ticket_categories WHERE guild_id = $1 ORDER BY id ASC", guild_id)
                rows = [dict(r) for r in res]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM ticket_categories WHERE guild_id = ? ORDER BY id ASC", (guild_id,))
                res = await cursor.fetchall()
                rows = [dict(r) for r in res]

        if not rows:
            default_categories = [
                {"name": "Buy / Order", "emoji": "🛒", "description": "Purchase products, services, or custom orders"},
                {"name": "Middleman", "emoji": "🤝", "description": "Request a trusted Middleman (MM) for safe trades"},
                {"name": "General Support", "emoji": "🛠️", "description": "Need help, questions, or server support"},
                {"name": "Report / Dispute", "emoji": "⚠️", "description": "Report a user, scam, or submit an appeal"}
            ]
            for c in default_categories:
                await self.add_ticket_category(guild_id, c["name"], c["emoji"], c["description"])
            return await self.get_ticket_categories(guild_id)

        return rows

    async def get_ticket_category(self, guild_id: int, name: str) -> Optional[Dict[str, Any]]:
        clean = name.strip()
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM ticket_categories WHERE guild_id = $1 AND LOWER(name) = LOWER($2)", guild_id, clean)
                return dict(row) if row else None
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM ticket_categories WHERE guild_id = ? AND LOWER(name) = LOWER(?)", (guild_id, clean))
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def remove_ticket_category(self, guild_id: int, name: str) -> bool:
        clean = name.strip()
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                res = await conn.execute("DELETE FROM ticket_categories WHERE guild_id = $1 AND LOWER(name) = LOWER($2)", guild_id, clean)
                parts = res.split()
                return int(parts[1]) > 0 if len(parts) > 1 else False
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("DELETE FROM ticket_categories WHERE guild_id = ? AND LOWER(name) = LOWER(?)", (guild_id, clean))
                await db.commit()
                return cursor.rowcount > 0

    async def update_ticket_category(self, guild_id: int, name: str, **kwargs) -> bool:
        if not kwargs:
            return False
        clean = name.strip()
        cols = []
        vals = []
        for k, v in kwargs.items():
            if k in ["emoji", "description", "category_channel_id", "staff_role_id"]:
                cols.append(k)
                vals.append(v)
        if not cols:
            return False

        if self.is_postgres and self.pool:
            set_clause = ", ".join(f"{col} = ${i+1}" for i, col in enumerate(cols))
            vals.extend([guild_id, clean])
            q = f"UPDATE ticket_categories SET {set_clause} WHERE guild_id = ${len(vals)-1} AND LOWER(name) = LOWER(${len(vals)})"
            async with self.pool.acquire() as conn:
                res = await conn.execute(q, *vals)
                return "UPDATE 0" not in res
        else:
            set_clause = ", ".join(f"{col} = ?" for col in cols)
            vals.extend([guild_id, clean])
            q = f"UPDATE ticket_categories SET {set_clause} WHERE guild_id = ? AND LOWER(name) = LOWER(?)"
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute(q, tuple(vals))
                await db.commit()
                return cursor.rowcount > 0

    async def reset_ticket_categories(self, guild_id: int) -> List[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("DELETE FROM ticket_categories WHERE guild_id = $1", guild_id)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("DELETE FROM ticket_categories WHERE guild_id = ?", (guild_id,))
                await db.commit()
        return await self.get_ticket_categories(guild_id)


    # ==========================================
    # PAYMENT METHODS
    # ==========================================
    async def add_payment_method(self, guild_id: int, method_name: str, address: str, note: str = "") -> int:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                p_id = await conn.fetchval("""
                    INSERT INTO payment_methods (guild_id, method_name, address, note)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                """, guild_id, method_name, address, note)
                return p_id
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("""
                    INSERT INTO payment_methods (guild_id, method_name, address, note)
                    VALUES (?, ?, ?, ?)
                """, (guild_id, method_name, address, note))
                await db.commit()
                return cursor.lastrowid

    async def get_payment_methods(self, guild_id: int) -> List[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM payment_methods WHERE guild_id = $1 ORDER BY id ASC", guild_id)
                return [dict(r) for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM payment_methods WHERE guild_id = ? ORDER BY id ASC", (guild_id,))
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def remove_payment_method(self, guild_id: int, method_id: int) -> bool:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                res = await conn.execute("DELETE FROM payment_methods WHERE id = $1 AND guild_id = $2", method_id, guild_id)
                return "DELETE 1" in res
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("DELETE FROM payment_methods WHERE id = ? AND guild_id = ?", (method_id, guild_id))
                await db.commit()
                return cursor.rowcount > 0

    # ==========================================
    # SHOP TERMS OF SERVICE
    # ==========================================
    async def set_shop_tos(self, guild_id: int, tos_text: str):
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO shop_tos (guild_id, tos_text) VALUES ($1, $2)
                    ON CONFLICT(guild_id) DO UPDATE SET tos_text = $2
                """, guild_id, tos_text)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("""
                    INSERT INTO shop_tos (guild_id, tos_text) VALUES (?, ?)
                    ON CONFLICT(guild_id) DO UPDATE SET tos_text = ?
                """, (guild_id, tos_text, tos_text))
                await db.commit()

    async def get_shop_tos(self, guild_id: int) -> Optional[str]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT tos_text FROM shop_tos WHERE guild_id = $1", guild_id)
                return row["tos_text"] if row else None
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("SELECT tos_text FROM shop_tos WHERE guild_id = ?", (guild_id,))
                row = await cursor.fetchone()
                return row[0] if row else None

    # ==========================================
    # NO-PREFIX USERS
    # ==========================================
    async def add_no_prefix_user(self, user_id: int, added_by: int):
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO no_prefix_users (user_id, added_by) VALUES ($1, $2)
                    ON CONFLICT(user_id) DO NOTHING
                """, user_id, added_by)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("""
                    INSERT INTO no_prefix_users (user_id, added_by) VALUES (?, ?)
                    ON CONFLICT(user_id) DO NOTHING
                """, (user_id, added_by))
                await db.commit()
        self._np_cache.add(user_id)

    async def remove_no_prefix_user(self, user_id: int) -> bool:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                res = await conn.execute("DELETE FROM no_prefix_users WHERE user_id = $1", user_id)
                removed = "DELETE 1" in res
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("DELETE FROM no_prefix_users WHERE user_id = ?", (user_id,))
                await db.commit()
                removed = cursor.rowcount > 0
        if removed:
            self._np_cache.discard(user_id)
        return removed

    async def get_all_no_prefix_users(self) -> List[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM no_prefix_users ORDER BY timestamp DESC")
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM no_prefix_users ORDER BY timestamp DESC")
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    # ==========================================
    # SHOP STOCK & INVENTORY
    # ==========================================
    async def add_stock_batch(self, guild_id: int, item_name: str, stock_lines: List[str]) -> int:
        clean_name = item_name.strip()
        filtered = [line.strip() for line in stock_lines if line and line.strip()]
        if not filtered:
            return 0
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.executemany(
                    "INSERT INTO shop_stock (guild_id, item_name, stock_data) VALUES ($1, $2, $3)",
                    [(guild_id, clean_name, line) for line in filtered]
                )
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.executemany(
                    "INSERT INTO shop_stock (guild_id, item_name, stock_data) VALUES (?, ?, ?)",
                    [(guild_id, clean_name, line) for line in filtered]
                )
                await db.commit()
        return len(filtered)

    async def get_stock_counts(self, guild_id: int) -> Dict[str, int]:
        counts = {}
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT item_name, COUNT(*) as count 
                    FROM shop_stock 
                    WHERE guild_id = $1 AND is_used = FALSE 
                    GROUP BY item_name
                """, guild_id)
                for r in rows:
                    counts[r["item_name"]] = r["count"]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("""
                    SELECT item_name, COUNT(*) as count 
                    FROM shop_stock 
                    WHERE guild_id = ? AND is_used = 0 
                    GROUP BY item_name
                """, (guild_id,))
                rows = await cursor.fetchall()
                for r in rows:
                    counts[r[0]] = r[1]
        return counts

    async def get_item_stock_count(self, guild_id: int, item_name: str) -> int:
        clean = item_name.strip()
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                val = await conn.fetchval("""
                    SELECT COUNT(*) FROM shop_stock 
                    WHERE guild_id = $1 AND LOWER(item_name) = LOWER($2) AND is_used = FALSE
                """, guild_id, clean)
                return val or 0
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("""
                    SELECT COUNT(*) FROM shop_stock 
                    WHERE guild_id = ? AND LOWER(item_name) = LOWER(?) AND is_used = 0
                """, (guild_id, clean))
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def clear_stock(self, guild_id: int, item_name: str) -> int:
        clean = item_name.strip()
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                res = await conn.execute("DELETE FROM shop_stock WHERE guild_id = $1 AND LOWER(item_name) = LOWER($2)", guild_id, clean)
                parts = res.split()
                return int(parts[1]) if len(parts) > 1 else 0
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("DELETE FROM shop_stock WHERE guild_id = ? AND LOWER(item_name) = LOWER(?)", (guild_id, clean))
                await db.commit()
                return cursor.rowcount

    # ==========================================
    # AI SETTINGS
    # ==========================================
    async def get_ai_settings(self, guild_id: int) -> Dict[str, Any]:
        default = {
            "guild_id": guild_id,
            "enabled": True,
            "offline_only": True,
            "custom_prompt": ""
        }
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM ai_settings WHERE guild_id = $1", guild_id)
                if row:
                    return dict(row)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM ai_settings WHERE guild_id = ?", (guild_id,))
                row = await cursor.fetchone()
                if row:
                    res = dict(row)
                    res["enabled"] = bool(res.get("enabled", 1))
                    res["offline_only"] = bool(res.get("offline_only", 1))
                    return res
        return default

    async def set_ai_settings(
        self,
        guild_id: int,
        enabled: Optional[bool] = None,
        offline_only: Optional[bool] = None,
        custom_prompt: Optional[str] = None
    ) -> bool:
        current = await self.get_ai_settings(guild_id)
        new_enabled = enabled if enabled is not None else current["enabled"]
        new_offline = offline_only if offline_only is not None else current["offline_only"]
        new_prompt = custom_prompt if custom_prompt is not None else current.get("custom_prompt", "")

        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO ai_settings (guild_id, enabled, offline_only, custom_prompt)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (guild_id) DO UPDATE SET
                        enabled = EXCLUDED.enabled,
                        offline_only = EXCLUDED.offline_only,
                        custom_prompt = EXCLUDED.custom_prompt
                """, guild_id, new_enabled, new_offline, new_prompt)
                return True
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("""
                    INSERT INTO ai_settings (guild_id, enabled, offline_only, custom_prompt)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT (guild_id) DO UPDATE SET
                        enabled = excluded.enabled,
                        offline_only = excluded.offline_only,
                        custom_prompt = excluded.custom_prompt
                """, (guild_id, 1 if new_enabled else 0, 1 if new_offline else 0, new_prompt))
                await db.commit()
                return True

db = Database()
