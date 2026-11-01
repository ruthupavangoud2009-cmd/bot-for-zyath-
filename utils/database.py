import os
import json
import time
import datetime
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

CREATE TABLE IF NOT EXISTS giveaways (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL UNIQUE,
    host_id BIGINT NOT NULL,
    prize TEXT NOT NULL,
    winners_count INTEGER DEFAULT 1,
    end_time BIGINT NOT NULL,
    requirements_role_id BIGINT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS giveaway_entrants (
    giveaway_id INTEGER NOT NULL,
    user_id BIGINT NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (giveaway_id, user_id)
);

CREATE TABLE IF NOT EXISTS economy (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    wallet BIGINT DEFAULT 1000,
    bank BIGINT DEFAULT 0,
    bank_max BIGINT DEFAULT 10000,
    last_daily BIGINT DEFAULT 0,
    last_work BIGINT DEFAULT 0,
    last_crime BIGINT DEFAULT 0,
    last_rob BIGINT DEFAULT 0,
    streak INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS afk_users (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    reason TEXT DEFAULT 'AFK',
    afk_time BIGINT NOT NULL,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS sticky_messages (
    channel_id BIGINT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    message_text TEXT NOT NULL,
    last_message_id BIGINT
);

CREATE TABLE IF NOT EXISTS automod_settings (
    guild_id BIGINT PRIMARY KEY,
    anti_invite BOOLEAN DEFAULT FALSE,
    anti_spam BOOLEAN DEFAULT FALSE,
    anti_mention BOOLEAN DEFAULT FALSE,
    anti_caps BOOLEAN DEFAULT FALSE,
    log_channel_id BIGINT
);

CREATE TABLE IF NOT EXISTS bot_staff (
    user_id BIGINT PRIMARY KEY,
    role TEXT DEFAULT 'Staff',
    added_by BIGINT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS premium_records (
    target_id BIGINT PRIMARY KEY,
    target_type TEXT NOT NULL,
    tier TEXT DEFAULT 'Premium',
    expires_at TIMESTAMP,
    added_by BIGINT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS auto_responders (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    trigger_text TEXT NOT NULL,
    response_text TEXT NOT NULL,
    added_by BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, trigger_text)
);

CREATE TABLE IF NOT EXISTS levels (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    xp BIGINT DEFAULT 0,
    level INTEGER DEFAULT 0,
    last_xp_time DOUBLE PRECISION DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS level_settings (
    guild_id BIGINT PRIMARY KEY,
    enabled BOOLEAN DEFAULT TRUE,
    channel_id BIGINT
);

CREATE TABLE IF NOT EXISTS reaction_roles (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    emoji TEXT,
    label TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS allowed_spam_users (
    user_id BIGINT PRIMARY KEY,
    added_by BIGINT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shop_orders (
    order_id TEXT PRIMARY KEY,
    receipt_id TEXT UNIQUE,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    product_name TEXT NOT NULL,
    quantity INTEGER DEFAULT 1,
    total_usd DOUBLE PRECISION NOT NULL,
    total_ltc DOUBLE PRECISION DEFAULT 0.0,
    status TEXT DEFAULT 'pending_payment',
    payment_method TEXT DEFAULT 'Litecoin',
    ltc_address TEXT,
    txid TEXT,
    claimed_by BIGINT,
    ticket_channel_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS used_ltc_transactions (
    txid TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    guild_id BIGINT NOT NULL,
    amount_ltc DOUBLE PRECISION NOT NULL,
    confirmations INTEGER DEFAULT 1,
    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_ltc_wallets (
    user_id BIGINT PRIMARY KEY,
    ltc_address TEXT NOT NULL,
    linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customer_feedback (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    order_id TEXT UNIQUE NOT NULL,
    user_id BIGINT NOT NULL,
    stars INTEGER DEFAULT 5,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shop_legit_vouches (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS shop_config (
    guild_id BIGINT PRIMARY KEY,
    shop_name TEXT DEFAULT 'Jack''s Shop',
    ltc_address TEXT,
    deal_log_channel_id BIGINT,
    feedback_channel_id BIGINT,
    purchase_category_id BIGINT,
    staff_role_id BIGINT,
    min_confirmations INTEGER DEFAULT 1,
    currency TEXT DEFAULT 'USD'
);

CREATE TABLE IF NOT EXISTS shop_coupons (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    code TEXT NOT NULL,
    discount_percent DOUBLE PRECISION DEFAULT 10.0,
    max_uses INTEGER DEFAULT 100,
    uses_count INTEGER DEFAULT 0,
    expires_at TIMESTAMP,
    UNIQUE (guild_id, code)
);

CREATE TABLE IF NOT EXISTS shopping_carts (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    item_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 1,
    PRIMARY KEY (guild_id, user_id, item_id)
);

CREATE TABLE IF NOT EXISTS deal_audit_logs (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    receipt_id TEXT NOT NULL,
    action TEXT NOT NULL,
    staff_id BIGINT NOT NULL,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

CREATE TABLE IF NOT EXISTS giveaways (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL UNIQUE,
    host_id INTEGER NOT NULL,
    prize TEXT NOT NULL,
    winners_count INTEGER DEFAULT 1,
    end_time INTEGER NOT NULL,
    requirements_role_id INTEGER,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS giveaway_entrants (
    giveaway_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (giveaway_id, user_id)
);

CREATE TABLE IF NOT EXISTS economy (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    wallet INTEGER DEFAULT 1000,
    bank INTEGER DEFAULT 0,
    bank_max INTEGER DEFAULT 10000,
    last_daily INTEGER DEFAULT 0,
    last_work INTEGER DEFAULT 0,
    last_crime INTEGER DEFAULT 0,
    last_rob INTEGER DEFAULT 0,
    streak INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS afk_users (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    reason TEXT DEFAULT 'AFK',
    afk_time INTEGER NOT NULL,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS sticky_messages (
    channel_id INTEGER PRIMARY KEY,
    guild_id INTEGER NOT NULL,
    message_text TEXT NOT NULL,
    last_message_id INTEGER
);

CREATE TABLE IF NOT EXISTS automod_settings (
    guild_id INTEGER PRIMARY KEY,
    anti_invite BOOLEAN DEFAULT 0,
    anti_spam BOOLEAN DEFAULT 0,
    anti_mention BOOLEAN DEFAULT 0,
    anti_caps BOOLEAN DEFAULT 0,
    log_channel_id INTEGER
);

CREATE TABLE IF NOT EXISTS bot_staff (
    user_id INTEGER PRIMARY KEY,
    role TEXT DEFAULT 'Staff',
    added_by INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS premium_records (
    target_id INTEGER PRIMARY KEY,
    target_type TEXT NOT NULL,
    tier TEXT DEFAULT 'Premium',
    expires_at TIMESTAMP,
    added_by INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS auto_responders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    trigger_text TEXT NOT NULL,
    response_text TEXT NOT NULL,
    added_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, trigger_text)
);

CREATE TABLE IF NOT EXISTS levels (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 0,
    last_xp_time REAL DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS level_settings (
    guild_id INTEGER PRIMARY KEY,
    enabled BOOLEAN DEFAULT 1,
    channel_id INTEGER
);

CREATE TABLE IF NOT EXISTS reaction_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    emoji TEXT,
    label TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS allowed_spam_users (
    user_id INTEGER PRIMARY KEY,
    added_by INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shop_orders (
    order_id TEXT PRIMARY KEY,
    receipt_id TEXT UNIQUE,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    quantity INTEGER DEFAULT 1,
    total_usd REAL NOT NULL,
    total_ltc REAL DEFAULT 0.0,
    status TEXT DEFAULT 'pending_payment',
    payment_method TEXT DEFAULT 'Litecoin',
    ltc_address TEXT,
    txid TEXT,
    claimed_by INTEGER,
    ticket_channel_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS used_ltc_transactions (
    txid TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    guild_id INTEGER NOT NULL,
    amount_ltc REAL NOT NULL,
    confirmations INTEGER DEFAULT 1,
    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_ltc_wallets (
    user_id INTEGER PRIMARY KEY,
    ltc_address TEXT NOT NULL,
    linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customer_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    order_id TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    stars INTEGER DEFAULT 5,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shop_legit_vouches (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS shop_config (
    guild_id INTEGER PRIMARY KEY,
    shop_name TEXT DEFAULT 'Jack''s Shop',
    ltc_address TEXT,
    deal_log_channel_id INTEGER,
    feedback_channel_id INTEGER,
    purchase_category_id INTEGER,
    staff_role_id INTEGER,
    min_confirmations INTEGER DEFAULT 1,
    currency TEXT DEFAULT 'USD'
);

CREATE TABLE IF NOT EXISTS shop_coupons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    code TEXT NOT NULL,
    discount_percent REAL DEFAULT 10.0,
    max_uses INTEGER DEFAULT 100,
    uses_count INTEGER DEFAULT 0,
    expires_at TIMESTAMP,
    UNIQUE (guild_id, code)
);

CREATE TABLE IF NOT EXISTS shopping_carts (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 1,
    PRIMARY KEY (guild_id, user_id, item_id)
);

CREATE TABLE IF NOT EXISTS deal_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    receipt_id TEXT NOT NULL,
    action TEXT NOT NULL,
    staff_id INTEGER NOT NULL,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

class Database:
    def __init__(self, sqlite_path: str = SQLITE_PATH):
        self.sqlite_path = sqlite_path
        self.is_postgres = False
        self.pool: Optional[asyncpg.Pool] = None
        self._np_cache = set()
        self._staff_cache: Dict[int, str] = {}
        self._premium_cache: Dict[int, Dict[str, Any]] = {}
        self._spam_cache = set()

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

        # Always ensure SQLite schema is initialized for local backup & offline resilience
        try:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.executescript(SQLITE_SCHEMA)
                await db.commit()
            if not self.is_postgres:
                print("\033[92m[DATABASE]\033[0m Local SQLite database initialized.")
        except Exception as e:
            print(f"\033[93m[DATABASE WARNING]\033[0m SQLite schema init warning: {e}")


        await self.load_np_cache()
        await self.load_staff_cache()
        await self.load_premium_cache()
        await self.load_spam_cache()

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
        """Loads whitelisted no-prefix users from Postgres, SQLite, and config.json into in-memory cache."""
        loaded_np = set()
        try:
            if self.is_postgres and self.pool:
                async with self.pool.acquire() as conn:
                    rows = await conn.fetch("SELECT user_id FROM no_prefix_users")
                    for r in rows:
                        loaded_np.add(int(r["user_id"]))
        except Exception as e:
            print(f"[CACHE] Error loading NP cache from Postgres: {e}")

        try:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("SELECT user_id FROM no_prefix_users")
                rows = await cursor.fetchall()
                for r in rows:
                    loaded_np.add(int(r[0]))
        except Exception as e:
            print(f"[CACHE] Error loading NP cache from SQLite: {e}")

        try:
            from utils.config_manager import get_no_prefix_users, save_no_prefix_users
            cfg_users = get_no_prefix_users()
            for u in cfg_users:
                if str(u).isdigit():
                    loaded_np.add(int(u))
            save_no_prefix_users([str(x) for x in loaded_np])
        except Exception as e:
            print(f"[CACHE] Error syncing NP cache with config.json: {e}")

        self._np_cache = loaded_np

    def is_no_prefix_cached(self, user_id: int) -> bool:
        return user_id in self._np_cache

    async def load_staff_cache(self):
        """Loads authorized bot staff from Postgres, SQLite, and config.json with full synchronization."""
        loaded_staff: Dict[int, str] = {}
        try:
            if self.is_postgres and self.pool:
                async with self.pool.acquire() as conn:
                    rows = await conn.fetch("SELECT user_id, role FROM bot_staff")
                    for r in rows:
                        loaded_staff[int(r["user_id"])] = str(r["role"] or "Staff")
        except Exception as e:
            print(f"[CACHE] Error loading staff cache from Postgres: {e}")

        try:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("SELECT user_id, role FROM bot_staff")
                rows = await cursor.fetchall()
                for r in rows:
                    uid = int(r[0])
                    if uid not in loaded_staff:
                        loaded_staff[uid] = str(r[1] or "Staff")
        except Exception as e:
            print(f"[CACHE] Error loading staff cache from SQLite: {e}")

        try:
            from utils.config_manager import get_bot_staff, save_bot_staff
            cfg_staff = get_bot_staff()
            for uid_str, role in cfg_staff.items():
                if uid_str.isdigit():
                    uid = int(uid_str)
                    if uid not in loaded_staff:
                        loaded_staff[uid] = str(role or "Staff")
            # Sync merged staff back to config.json
            save_bot_staff({str(k): v for k, v in loaded_staff.items()})
        except Exception as e:
            print(f"[CACHE] Error syncing staff cache with config.json: {e}")

        self._staff_cache = loaded_staff

        # Sync back to SQLite to guarantee offline permanence
        try:
            async with aiosqlite.connect(self.sqlite_path) as db:
                for uid, role in self._staff_cache.items():
                    await db.execute("""
                        INSERT INTO bot_staff (user_id, role, added_by) VALUES (?, ?, 0)
                        ON CONFLICT(user_id) DO UPDATE SET role = excluded.role
                    """, (uid, role))
                await db.commit()
        except Exception as e:
            print(f"[CACHE] Error syncing staff cache to SQLite backup: {e}")

    def is_staff_cached(self, user_id: int) -> bool:
        return user_id in self._staff_cache

    def get_staff_role(self, user_id: int) -> Optional[str]:
        return self._staff_cache.get(user_id)


    async def load_premium_cache(self):
        """Loads active premium guilds & users into memory cache."""
        try:
            now = time.time()
            if self.is_postgres and self.pool:
                async with self.pool.acquire() as conn:
                    rows = await conn.fetch("SELECT * FROM premium_records")
                    self._premium_cache = {}
                    for r in rows:
                        exp = r["expires_at"]
                        if exp is None or exp.timestamp() > now:
                            self._premium_cache[int(r["target_id"])] = dict(r)
            else:
                async with aiosqlite.connect(self.sqlite_path) as db:
                    db.row_factory = aiosqlite.Row
                    cursor = await db.execute("SELECT * FROM premium_records")
                    rows = await cursor.fetchall()
                    self._premium_cache = {}
                    for r in rows:
                        exp = r["expires_at"]
                        # SQLite stores as ISO string or timestamp
                        self._premium_cache[int(r["target_id"])] = dict(r)
        except Exception as e:
            print(f"[CACHE] Error loading premium cache: {e}")

    def is_premium_cached(self, target_id: int) -> bool:
        return target_id in self._premium_cache

    def is_guild_premium(self, guild_id: int) -> bool:
        return self.is_premium_cached(guild_id)

    def is_user_premium(self, user_id: int) -> bool:
        return self.is_premium_cached(user_id)

    async def load_spam_cache(self):
        """Loads authorized spam command users into memory cache."""
        try:
            if self.is_postgres and self.pool:
                async with self.pool.acquire() as conn:
                    rows = await conn.fetch("SELECT user_id FROM allowed_spam_users")
                    self._spam_cache = {int(r["user_id"]) for r in rows}
            else:
                async with aiosqlite.connect(self.sqlite_path) as db:
                    cursor = await db.execute("SELECT user_id FROM allowed_spam_users")
                    rows = await cursor.fetchall()
                    self._spam_cache = {int(r[0]) for r in rows}
        except Exception as e:
            print(f"[CACHE] Error loading spam cache: {e}")

    def is_spam_allowed(self, user_id: int) -> bool:
        return user_id in self._spam_cache

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

    async def get_ticket_stats(self, guild_id: int) -> Dict[str, Any]:
        stats = {"total": 0, "open": 0, "closed": 0, "categories": {}}
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                stats["total"] = await conn.fetchval("SELECT COUNT(*) FROM tickets WHERE guild_id = $1", guild_id) or 0
                stats["open"] = await conn.fetchval("SELECT COUNT(*) FROM tickets WHERE guild_id = $1 AND status = 'open'", guild_id) or 0
                stats["closed"] = await conn.fetchval("SELECT COUNT(*) FROM tickets WHERE guild_id = $1 AND status = 'closed'", guild_id) or 0
                cat_rows = await conn.fetch("SELECT category, COUNT(*) as c FROM tickets WHERE guild_id = $1 GROUP BY category ORDER BY c DESC LIMIT 5", guild_id)
                for r in cat_rows:
                    stats["categories"][r["category"]] = r["c"]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM tickets WHERE guild_id = ?", (guild_id,))
                stats["total"] = (await cursor.fetchone())[0] or 0
                cursor = await db.execute("SELECT COUNT(*) FROM tickets WHERE guild_id = ? AND status = 'open'", (guild_id,))
                stats["open"] = (await cursor.fetchone())[0] or 0
                cursor = await db.execute("SELECT COUNT(*) FROM tickets WHERE guild_id = ? AND status = 'closed'", (guild_id,))
                stats["closed"] = (await cursor.fetchone())[0] or 0
                cursor = await db.execute("SELECT category, COUNT(*) as c FROM tickets WHERE guild_id = ? GROUP BY category ORDER BY c DESC LIMIT 5", (guild_id,))
                for r in await cursor.fetchall():
                    stats["categories"][r[0]] = r[1]
        return stats

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
        # 1. PostgreSQL
        if self.is_postgres and self.pool:
            try:
                async with self.pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO no_prefix_users (user_id, added_by) VALUES ($1, $2)
                        ON CONFLICT(user_id) DO NOTHING
                    """, user_id, added_by)
            except Exception as e:
                print(f"[DB] Error adding NP user to postgres: {e}")

        # 2. SQLite local backup
        try:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("""
                    INSERT INTO no_prefix_users (user_id, added_by) VALUES (?, ?)
                    ON CONFLICT(user_id) DO NOTHING
                """, (user_id, added_by))
                await db.commit()
        except Exception as e:
            print(f"[DB] Error adding NP user to sqlite: {e}")

        # 3. config.json
        try:
            from utils.config_manager import add_no_prefix_to_config
            add_no_prefix_to_config(user_id)
        except Exception as e:
            print(f"[CONFIG] Error adding NP user to config.json: {e}")

        self._np_cache.add(user_id)

    async def remove_no_prefix_user(self, user_id: int) -> bool:
        removed = False
        # 1. PostgreSQL
        if self.is_postgres and self.pool:
            try:
                async with self.pool.acquire() as conn:
                    res = await conn.execute("DELETE FROM no_prefix_users WHERE user_id = $1", user_id)
                    removed = "DELETE 1" in res
            except Exception as e:
                print(f"[DB] Error removing NP user from postgres: {e}")

        # 2. SQLite
        try:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("DELETE FROM no_prefix_users WHERE user_id = ?", (user_id,))
                await db.commit()
                if cursor.rowcount > 0:
                    removed = True
        except Exception as e:
            print(f"[DB] Error removing NP user from sqlite: {e}")

        # 3. config.json
        try:
            from utils.config_manager import remove_no_prefix_from_config
            if remove_no_prefix_from_config(user_id):
                removed = True
        except Exception as e:
            print(f"[CONFIG] Error removing NP user from config.json: {e}")

        self._np_cache.discard(user_id)
        return removed

    async def get_all_no_prefix_users(self) -> List[Dict[str, Any]]:
        entries: Dict[int, Dict[str, Any]] = {}
        if self.is_postgres and self.pool:
            try:
                async with self.pool.acquire() as conn:
                    rows = await conn.fetch("SELECT * FROM no_prefix_users ORDER BY timestamp DESC")
                    for r in rows:
                        entries[int(r["user_id"])] = dict(r)
            except Exception as e:
                print(f"[DB] Error fetching NP users from postgres: {e}")

        try:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM no_prefix_users ORDER BY timestamp DESC")
                rows = await cursor.fetchall()
                for r in rows:
                    uid = int(r["user_id"])
                    if uid not in entries:
                        entries[uid] = dict(r)
        except Exception as e:
            print(f"[DB] Error fetching NP users from sqlite: {e}")

        for uid in self._np_cache:
            if uid not in entries:
                entries[uid] = {"user_id": uid, "added_by": 0, "timestamp": datetime.datetime.utcnow()}

        return list(entries.values())

    # ==========================================
    # BOT STAFF SYSTEM
    # ==========================================
    async def add_bot_staff(self, user_id: int, role: str, added_by: int):
        clean_role = (role or "Staff").strip()[:30]
        # 1. PostgreSQL
        if self.is_postgres and self.pool:
            try:
                async with self.pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO bot_staff (user_id, role, added_by) VALUES ($1, $2, $3)
                        ON CONFLICT(user_id) DO UPDATE SET role = EXCLUDED.role, added_by = EXCLUDED.added_by
                    """, user_id, clean_role, added_by)
            except Exception as e:
                print(f"[DB] Error adding bot staff to postgres: {e}")

        # 2. SQLite local backup
        try:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("""
                    INSERT INTO bot_staff (user_id, role, added_by) VALUES (?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET role = excluded.role, added_by = excluded.added_by
                """, (user_id, clean_role, added_by))
                await db.commit()
        except Exception as e:
            print(f"[DB] Error adding bot staff to sqlite: {e}")

        # 3. config.json
        try:
            from utils.config_manager import add_staff_to_config
            add_staff_to_config(user_id, clean_role)
        except Exception as e:
            print(f"[CONFIG] Error adding bot staff to config.json: {e}")

        self._staff_cache[user_id] = clean_role

    async def remove_bot_staff(self, user_id: int) -> bool:
        removed = False
        # 1. PostgreSQL
        if self.is_postgres and self.pool:
            try:
                async with self.pool.acquire() as conn:
                    res = await conn.execute("DELETE FROM bot_staff WHERE user_id = $1", user_id)
                    removed = "DELETE 1" in res
            except Exception as e:
                print(f"[DB] Error removing bot staff from postgres: {e}")

        # 2. SQLite
        try:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("DELETE FROM bot_staff WHERE user_id = ?", (user_id,))
                await db.commit()
                if cursor.rowcount > 0:
                    removed = True
        except Exception as e:
            print(f"[DB] Error removing bot staff from sqlite: {e}")

        # 3. config.json
        try:
            from utils.config_manager import remove_staff_from_config
            if remove_staff_from_config(user_id):
                removed = True
        except Exception as e:
            print(f"[CONFIG] Error removing bot staff from config.json: {e}")

        self._staff_cache.pop(user_id, None)
        return removed

    async def get_all_bot_staff(self) -> List[Dict[str, Any]]:
        entries: Dict[int, Dict[str, Any]] = {}
        # 1. PostgreSQL
        if self.is_postgres and self.pool:
            try:
                async with self.pool.acquire() as conn:
                    rows = await conn.fetch("SELECT * FROM bot_staff ORDER BY timestamp DESC")
                    for r in rows:
                        entries[int(r["user_id"])] = dict(r)
            except Exception as e:
                print(f"[DB] Error fetching bot staff from postgres: {e}")

        # 2. SQLite
        try:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM bot_staff ORDER BY timestamp DESC")
                rows = await cursor.fetchall()
                for r in rows:
                    uid = int(r["user_id"])
                    if uid not in entries:
                        entries[uid] = dict(r)
        except Exception as e:
            print(f"[DB] Error fetching bot staff from sqlite: {e}")

        # 3. Include memory cache / config.json items
        for uid, role in self._staff_cache.items():
            if uid not in entries:
                entries[uid] = {"user_id": uid, "role": role, "added_by": 0, "timestamp": datetime.datetime.utcnow()}

        return list(entries.values())


    # ==========================================
    # PREMIUM SUBSCRIPTION SYSTEM
    # ==========================================
    async def add_premium(self, target_id: int, target_type: str, tier: str, expires_at: Optional[datetime.datetime], added_by: int):
        target_type = target_type.lower()
        tier = (tier or "Premium").strip()
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO premium_records (target_id, target_type, tier, expires_at, added_by)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT(target_id) DO UPDATE SET
                        target_type = EXCLUDED.target_type,
                        tier = EXCLUDED.tier,
                        expires_at = EXCLUDED.expires_at,
                        added_by = EXCLUDED.added_by
                """, target_id, target_type, tier, expires_at, added_by)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                exp_str = expires_at.isoformat() if expires_at else None
                await db.execute("""
                    INSERT INTO premium_records (target_id, target_type, tier, expires_at, added_by)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(target_id) DO UPDATE SET
                        target_type = excluded.target_type,
                        tier = excluded.tier,
                        expires_at = excluded.expires_at,
                        added_by = excluded.added_by
                """, (target_id, target_type, tier, exp_str, added_by))
                await db.commit()
        await self.load_premium_cache()

    async def remove_premium(self, target_id: int) -> bool:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                res = await conn.execute("DELETE FROM premium_records WHERE target_id = $1", target_id)
                removed = "DELETE 1" in res
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("DELETE FROM premium_records WHERE target_id = ?", (target_id,))
                await db.commit()
                removed = cursor.rowcount > 0
        if removed:
            self._premium_cache.pop(target_id, None)
        return removed

    async def get_premium(self, target_id: int) -> Optional[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM premium_records WHERE target_id = $1", target_id)
                return dict(row) if row else None
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM premium_records WHERE target_id = ?", (target_id,))
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_all_premium(self) -> List[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM premium_records ORDER BY timestamp DESC")
                return [dict(r) for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM premium_records ORDER BY timestamp DESC")
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    # ==========================================
    # AUTO-RESPONDERS (LAL & COMMUNITY SERVERS)
    # ==========================================
    async def add_auto_responder(self, guild_id: int, trigger: str, response: str, added_by: int):
        clean_trig = trigger.strip().lower()[:100]
        clean_resp = response.strip()[:2000]
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO auto_responders (guild_id, trigger_text, response_text, added_by)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT(guild_id, trigger_text) DO UPDATE SET
                        response_text = EXCLUDED.response_text,
                        added_by = EXCLUDED.added_by
                """, guild_id, clean_trig, clean_resp, added_by)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("""
                    INSERT INTO auto_responders (guild_id, trigger_text, response_text, added_by)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(guild_id, trigger_text) DO UPDATE SET
                        response_text = excluded.response_text,
                        added_by = excluded.added_by
                """, (guild_id, clean_trig, clean_resp, added_by))
                await db.commit()

    async def remove_auto_responder(self, guild_id: int, trigger: str) -> bool:
        clean_trig = trigger.strip().lower()
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                res = await conn.execute("DELETE FROM auto_responders WHERE guild_id = $1 AND trigger_text = $2", guild_id, clean_trig)
                return "DELETE 1" in res
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("DELETE FROM auto_responders WHERE guild_id = ? AND trigger_text = ?", (guild_id, clean_trig))
                await db.commit()
                return cursor.rowcount > 0

    async def get_auto_responders(self, guild_id: int) -> List[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM auto_responders WHERE guild_id = $1 ORDER BY id ASC", guild_id)
                return [dict(r) for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM auto_responders WHERE guild_id = ? ORDER BY id ASC", (guild_id,))
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def find_auto_response(self, guild_id: int, text: str) -> Optional[str]:
        clean_text = text.strip().lower()
        responders = await self.get_auto_responders(guild_id)
        for r in responders:
            trig = r["trigger_text"].lower()
            # Exact match or word boundary match
            if clean_text == trig or clean_text.startswith(f"{trig} ") or f" {trig} " in f" {clean_text} ":
                return r["response_text"]
        return None

    # ==========================================
    # LEVELING & XP SYSTEM (RANK & LEADERBOARD)
    # ==========================================
    async def get_level_data(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM levels WHERE guild_id = $1 AND user_id = $2", guild_id, user_id)
                if not row:
                    await conn.execute("INSERT INTO levels (guild_id, user_id) VALUES ($1, $2) ON CONFLICT DO NOTHING", guild_id, user_id)
                    return {"guild_id": guild_id, "user_id": user_id, "xp": 0, "level": 0, "last_xp_time": 0}
                return dict(row)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM levels WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
                row = await cursor.fetchone()
                if not row:
                    await db.execute("INSERT INTO levels (guild_id, user_id) VALUES (?, ?) ON CONFLICT DO NOTHING", (guild_id, user_id))
                    await db.commit()
                    return {"guild_id": guild_id, "user_id": user_id, "xp": 0, "level": 0, "last_xp_time": 0}
                return dict(row)

    async def add_xp(self, guild_id: int, user_id: int, xp_amount: int) -> Tuple[bool, int, int]:
        """Awards XP and calculates if user leveled up. Formula: next_level_xp = 5 * (lvl ** 2) + 50 * lvl + 100"""
        data = await self.get_level_data(guild_id, user_id)
        current_xp = data["xp"] + xp_amount
        current_lvl = data["level"]
        now = time.time()

        needed_xp = 5 * (current_lvl ** 2) + 50 * current_lvl + 100
        leveled_up = False
        new_lvl = current_lvl

        while current_xp >= needed_xp:
            current_xp -= needed_xp
            new_lvl += 1
            leveled_up = True
            needed_xp = 5 * (new_lvl ** 2) + 50 * new_lvl + 100

        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE levels SET xp = $1, level = $2, last_xp_time = $3
                    WHERE guild_id = $4 AND user_id = $5
                """, current_xp, new_lvl, now, guild_id, user_id)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("""
                    UPDATE levels SET xp = ?, level = ?, last_xp_time = ?
                    WHERE guild_id = ? AND user_id = ?
                """, (current_xp, new_lvl, now, guild_id, user_id))
                await db.commit()

        return leveled_up, new_lvl, current_xp

    async def get_leaderboard(self, guild_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT user_id, xp, level FROM levels
                    WHERE guild_id = $1
                    ORDER BY level DESC, xp DESC
                    LIMIT $2
                """, guild_id, limit)
                return [dict(r) for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT user_id, xp, level FROM levels
                    WHERE guild_id = ?
                    ORDER BY level DESC, xp DESC
                    LIMIT ?
                """, (guild_id, limit))
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_user_rank(self, guild_id: int, user_id: int) -> int:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                rank = await conn.fetchval("""
                    SELECT COUNT(*) + 1 FROM levels
                    WHERE guild_id = $1 AND (level > (SELECT level FROM levels WHERE guild_id = $1 AND user_id = $2)
                       OR (level = (SELECT level FROM levels WHERE guild_id = $1 AND user_id = $2) AND xp > (SELECT xp FROM levels WHERE guild_id = $1 AND user_id = $2)))
                """, guild_id, user_id)
                return rank or 1
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("""
                    SELECT COUNT(*) + 1 FROM levels
                    WHERE guild_id = ? AND (level > (SELECT level FROM levels WHERE guild_id = ? AND user_id = ?)
                       OR (level = (SELECT level FROM levels WHERE guild_id = ? AND user_id = ?) AND xp > (SELECT xp FROM levels WHERE guild_id = ? AND user_id = ?)))
                """, (guild_id, guild_id, user_id, guild_id, user_id, guild_id, user_id))
                row = await cursor.fetchone()
                return row[0] if row else 1

    async def set_user_xp(self, guild_id: int, user_id: int, xp: int, level: int):
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO levels (guild_id, user_id, xp, level) VALUES ($1, $2, $3, $4)
                    ON CONFLICT(guild_id, user_id) DO UPDATE SET xp = EXCLUDED.xp, level = EXCLUDED.level
                """, guild_id, user_id, xp, level)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("""
                    INSERT INTO levels (guild_id, user_id, xp, level) VALUES (?, ?, ?, ?)
                    ON CONFLICT(guild_id, user_id) DO UPDATE SET xp = excluded.xp, level = excluded.level
                """, (guild_id, user_id, xp, level))
                await db.commit()

    async def reset_guild_levels(self, guild_id: int):
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("DELETE FROM levels WHERE guild_id = $1", guild_id)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("DELETE FROM levels WHERE guild_id = ?", (guild_id,))
                await db.commit()

    # ==========================================
    # SPAM COMMAND WHITELIST (PERSISTENT DB)
    # ==========================================
    async def add_spam_user(self, user_id: int, added_by: int):
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO allowed_spam_users (user_id, added_by) VALUES ($1, $2)
                    ON CONFLICT(user_id) DO NOTHING
                """, user_id, added_by)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("""
                    INSERT INTO allowed_spam_users (user_id, added_by) VALUES (?, ?)
                    ON CONFLICT(user_id) DO NOTHING
                """, (user_id, added_by))
                await db.commit()
        self._spam_cache.add(user_id)

    async def remove_spam_user(self, user_id: int) -> bool:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                res = await conn.execute("DELETE FROM allowed_spam_users WHERE user_id = $1", user_id)
                removed = "DELETE 1" in res
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("DELETE FROM allowed_spam_users WHERE user_id = ?", (user_id,))
                await db.commit()
                removed = cursor.rowcount > 0
        if removed:
            self._spam_cache.discard(user_id)
        return removed

    async def get_all_spam_users(self) -> List[int]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT user_id FROM allowed_spam_users")
                return [int(r["user_id"]) for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("SELECT user_id FROM allowed_spam_users")
                rows = await cursor.fetchall()
                return [int(r[0]) for r in rows]

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

    # ==========================================
    # GIVEAWAY OPERATIONS
    # ==========================================
    async def create_giveaway(
        self,
        guild_id: int,
        channel_id: int,
        message_id: int,
        host_id: int,
        prize: str,
        winners_count: int,
        end_time: int,
        requirements_role_id: Optional[int] = None
    ) -> Optional[int]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    INSERT INTO giveaways (guild_id, channel_id, message_id, host_id, prize, winners_count, end_time, requirements_role_id)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    RETURNING id
                """, guild_id, channel_id, message_id, host_id, prize, winners_count, end_time, requirements_role_id)
                return row["id"] if row else None
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("""
                    INSERT INTO giveaways (guild_id, channel_id, message_id, host_id, prize, winners_count, end_time, requirements_role_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (guild_id, channel_id, message_id, host_id, prize, winners_count, end_time, requirements_role_id))
                await db.commit()
                return cursor.lastrowid

    async def get_giveaway(self, message_id: int) -> Optional[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM giveaways WHERE message_id = $1", message_id)
                return dict(row) if row else None
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM giveaways WHERE message_id = ?", (message_id,))
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_giveaway_by_id(self, giveaway_id: int) -> Optional[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM giveaways WHERE id = $1", giveaway_id)
                return dict(row) if row else None
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM giveaways WHERE id = ?", (giveaway_id,))
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_active_giveaways(self, guild_id: Optional[int] = None) -> List[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                if guild_id:
                    rows = await conn.fetch("SELECT * FROM giveaways WHERE status = 'active' AND guild_id = $1 ORDER BY end_time ASC", guild_id)
                else:
                    rows = await conn.fetch("SELECT * FROM giveaways WHERE status = 'active' ORDER BY end_time ASC")
                return [dict(r) for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                if guild_id:
                    cursor = await db.execute("SELECT * FROM giveaways WHERE status = 'active' AND guild_id = ? ORDER BY end_time ASC", (guild_id,))
                else:
                    cursor = await db.execute("SELECT * FROM giveaways WHERE status = 'active' ORDER BY end_time ASC")
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def end_giveaway(self, message_id: int, status: str = "ended") -> bool:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                res = await conn.execute("UPDATE giveaways SET status = $1 WHERE message_id = $2", status, message_id)
                return "UPDATE 1" in res
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("UPDATE giveaways SET status = ? WHERE message_id = ?", (status, message_id))
                await db.commit()
                return cursor.rowcount > 0

    async def add_giveaway_entrant(self, giveaway_id: int, user_id: int) -> bool:
        try:
            if self.is_postgres and self.pool:
                async with self.pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO giveaway_entrants (giveaway_id, user_id)
                        VALUES ($1, $2)
                        ON CONFLICT DO NOTHING
                    """, giveaway_id, user_id)
                    return True
            else:
                async with aiosqlite.connect(self.sqlite_path) as db:
                    await db.execute("""
                        INSERT OR IGNORE INTO giveaway_entrants (giveaway_id, user_id)
                        VALUES (?, ?)
                    """, (giveaway_id, user_id))
                    await db.commit()
                    return True
        except Exception:
            return False

    async def remove_giveaway_entrant(self, giveaway_id: int, user_id: int) -> bool:
        try:
            if self.is_postgres and self.pool:
                async with self.pool.acquire() as conn:
                    res = await conn.execute("DELETE FROM giveaway_entrants WHERE giveaway_id = $1 AND user_id = $2", giveaway_id, user_id)
                    return "DELETE 1" in res
            else:
                async with aiosqlite.connect(self.sqlite_path) as db:
                    cursor = await db.execute("DELETE FROM giveaway_entrants WHERE giveaway_id = ? AND user_id = ?", (giveaway_id, user_id))
                    await db.commit()
                    return cursor.rowcount > 0
        except Exception:
            return False

    async def get_giveaway_entrants(self, giveaway_id: int) -> List[int]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT user_id FROM giveaway_entrants WHERE giveaway_id = $1", giveaway_id)
                return [r["user_id"] for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("SELECT user_id FROM giveaway_entrants WHERE giveaway_id = ?", (giveaway_id,))
                rows = await cursor.fetchall()
                return [r[0] for r in rows]

    async def get_giveaway_entrants_count(self, giveaway_id: int) -> int:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                val = await conn.fetchval("SELECT COUNT(*) FROM giveaway_entrants WHERE giveaway_id = $1", giveaway_id)
                return val or 0
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM giveaway_entrants WHERE giveaway_id = ?", (giveaway_id,))
                row = await cursor.fetchone()
                return row[0] if row else 0

    # ==========================================
    # ECONOMY OPERATIONS
    # ==========================================
    async def get_economy(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        default = {
            "guild_id": guild_id, "user_id": user_id, "wallet": 1000, "bank": 0,
            "bank_max": 10000, "last_daily": 0, "last_work": 0, "last_crime": 0,
            "last_rob": 0, "streak": 0
        }
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM economy WHERE guild_id = $1 AND user_id = $2", guild_id, user_id)
                if row:
                    return dict(row)
                await conn.execute("""
                    INSERT INTO economy (guild_id, user_id, wallet, bank, bank_max)
                    VALUES ($1, $2, 1000, 0, 10000)
                    ON CONFLICT DO NOTHING
                """, guild_id, user_id)
                return default
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM economy WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                await db.execute("""
                    INSERT OR IGNORE INTO economy (guild_id, user_id, wallet, bank, bank_max)
                    VALUES (?, ?, 1000, 0, 10000)
                """, (guild_id, user_id))
                await db.commit()
                return default

    async def update_economy(self, guild_id: int, user_id: int, **kwargs) -> Dict[str, Any]:
        curr = await self.get_economy(guild_id, user_id)
        for k, v in kwargs.items():
            if v is not None:
                curr[k] = v

        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO economy (guild_id, user_id, wallet, bank, bank_max, last_daily, last_work, last_crime, last_rob, streak)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (guild_id, user_id) DO UPDATE SET
                        wallet = EXCLUDED.wallet,
                        bank = EXCLUDED.bank,
                        bank_max = EXCLUDED.bank_max,
                        last_daily = EXCLUDED.last_daily,
                        last_work = EXCLUDED.last_work,
                        last_crime = EXCLUDED.last_crime,
                        last_rob = EXCLUDED.last_rob,
                        streak = EXCLUDED.streak
                """, guild_id, user_id, curr["wallet"], curr["bank"], curr["bank_max"],
                    curr["last_daily"], curr["last_work"], curr["last_crime"], curr["last_rob"], curr["streak"])
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("""
                    INSERT INTO economy (guild_id, user_id, wallet, bank, bank_max, last_daily, last_work, last_crime, last_rob, streak)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(guild_id, user_id) DO UPDATE SET
                        wallet = excluded.wallet,
                        bank = excluded.bank,
                        bank_max = excluded.bank_max,
                        last_daily = excluded.last_daily,
                        last_work = excluded.last_work,
                        last_crime = excluded.last_crime,
                        last_rob = excluded.last_rob,
                        streak = excluded.streak
                """, (guild_id, user_id, curr["wallet"], curr["bank"], curr["bank_max"],
                      curr["last_daily"], curr["last_work"], curr["last_crime"], curr["last_rob"], curr["streak"]))
                await db.commit()
        return curr

    async def get_economy_leaderboard(self, guild_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT user_id, wallet, bank, (wallet + bank) AS total
                    FROM economy
                    WHERE guild_id = $1
                    ORDER BY total DESC
                    LIMIT $2
                """, guild_id, limit)
                return [dict(r) for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT user_id, wallet, bank, (wallet + bank) AS total
                    FROM economy
                    WHERE guild_id = ?
                    ORDER BY total DESC
                    LIMIT ?
                """, (guild_id, limit))
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    # ==========================================
    # AFK OPERATIONS
    # ==========================================
    async def set_afk(self, guild_id: int, user_id: int, reason: str) -> bool:
        now_ts = int(time.time())
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO afk_users (guild_id, user_id, reason, afk_time)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (guild_id, user_id) DO UPDATE SET
                        reason = EXCLUDED.reason,
                        afk_time = EXCLUDED.afk_time
                """, guild_id, user_id, reason, now_ts)
                return True
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("""
                    INSERT INTO afk_users (guild_id, user_id, reason, afk_time)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(guild_id, user_id) DO UPDATE SET
                        reason = excluded.reason,
                        afk_time = excluded.afk_time
                """, (guild_id, user_id, reason, now_ts))
                await db.commit()
                return True

    async def get_afk(self, guild_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM afk_users WHERE guild_id = $1 AND user_id = $2", guild_id, user_id)
                return dict(row) if row else None
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM afk_users WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def remove_afk(self, guild_id: int, user_id: int) -> bool:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                res = await conn.execute("DELETE FROM afk_users WHERE guild_id = $1 AND user_id = $2", guild_id, user_id)
                return "DELETE 1" in res
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("DELETE FROM afk_users WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
                await db.commit()
                return cursor.rowcount > 0

    # ==========================================
    # STICKY MESSAGE OPERATIONS
    # ==========================================
    async def set_sticky(self, channel_id: int, guild_id: int, message_text: str) -> bool:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO sticky_messages (channel_id, guild_id, message_text, last_message_id)
                    VALUES ($1, $2, $3, NULL)
                    ON CONFLICT (channel_id) DO UPDATE SET
                        message_text = EXCLUDED.message_text
                """, channel_id, guild_id, message_text)
                return True
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("""
                    INSERT INTO sticky_messages (channel_id, guild_id, message_text, last_message_id)
                    VALUES (?, ?, ?, NULL)
                    ON CONFLICT(channel_id) DO UPDATE SET
                        message_text = excluded.message_text
                """, (channel_id, guild_id, message_text))
                await db.commit()
                return True

    async def get_sticky(self, channel_id: int) -> Optional[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM sticky_messages WHERE channel_id = $1", channel_id)
                return dict(row) if row else None
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM sticky_messages WHERE channel_id = ?", (channel_id,))
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def update_sticky_last_id(self, channel_id: int, last_message_id: int) -> bool:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE sticky_messages SET last_message_id = $1 WHERE channel_id = $2", last_message_id, channel_id)
                return True
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("UPDATE sticky_messages SET last_message_id = ? WHERE channel_id = ?", (last_message_id, channel_id))
                await db.commit()
                return True

    async def remove_sticky(self, channel_id: int) -> bool:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                res = await conn.execute("DELETE FROM sticky_messages WHERE channel_id = $1", channel_id)
                return "DELETE 1" in res
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("DELETE FROM sticky_messages WHERE channel_id = ?", (channel_id,))
                await db.commit()
                return cursor.rowcount > 0

    # ==========================================
    # AUTOMOD OPERATIONS
    # ==========================================
    async def get_automod_settings(self, guild_id: int) -> Dict[str, Any]:
        default = {
            "guild_id": guild_id, "anti_invite": False, "anti_spam": False,
            "anti_mention": False, "anti_caps": False, "log_channel_id": None
        }
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM automod_settings WHERE guild_id = $1", guild_id)
                if row:
                    return dict(row)
                await conn.execute("INSERT INTO automod_settings (guild_id) VALUES ($1) ON CONFLICT DO NOTHING", guild_id)
                return default
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM automod_settings WHERE guild_id = ?", (guild_id,))
                row = await cursor.fetchone()
                if row:
                    res = dict(row)
                    res["anti_invite"] = bool(res.get("anti_invite", 0))
                    res["anti_spam"] = bool(res.get("anti_spam", 0))
                    res["anti_mention"] = bool(res.get("anti_mention", 0))
                    res["anti_caps"] = bool(res.get("anti_caps", 0))
                    return res
                await db.execute("INSERT OR IGNORE INTO automod_settings (guild_id) VALUES (?)", (guild_id,))
                await db.commit()
                return default

    async def set_automod_setting(self, guild_id: int, key: str, value: Any) -> bool:
        curr = await self.get_automod_settings(guild_id)
        curr[key] = value

        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO automod_settings (guild_id, anti_invite, anti_spam, anti_mention, anti_caps, log_channel_id)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (guild_id) DO UPDATE SET
                        anti_invite = EXCLUDED.anti_invite,
                        anti_spam = EXCLUDED.anti_spam,
                        anti_mention = EXCLUDED.anti_mention,
                        anti_caps = EXCLUDED.anti_caps,
                        log_channel_id = EXCLUDED.log_channel_id
                """, guild_id, curr["anti_invite"], curr["anti_spam"], curr["anti_mention"], curr["anti_caps"], curr["log_channel_id"])
                return True
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("""
                    INSERT INTO automod_settings (guild_id, anti_invite, anti_spam, anti_mention, anti_caps, log_channel_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(guild_id) DO UPDATE SET
                        anti_invite = excluded.anti_invite,
                        anti_spam = excluded.anti_spam,
                        anti_mention = excluded.anti_mention,
                        anti_caps = excluded.anti_caps,
                        log_channel_id = excluded.log_channel_id
                """, (guild_id, 1 if curr["anti_invite"] else 0, 1 if curr["anti_spam"] else 0,
                      1 if curr["anti_mention"] else 0, 1 if curr["anti_caps"] else 0, curr["log_channel_id"]))
                await db.commit()
                return True

    # ==========================================
    # SHOP CONFIG & BRANDING
    # ==========================================
    async def get_shop_config(self, guild_id: int) -> Dict[str, Any]:
        default = {
            "guild_id": guild_id,
            "shop_name": "Jack's Shop",
            "ltc_address": None,
            "deal_log_channel_id": None,
            "feedback_channel_id": None,
            "purchase_category_id": None,
            "staff_role_id": None,
            "min_confirmations": 1,
            "currency": "USD"
        }
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM shop_config WHERE guild_id = $1", guild_id)
                if row:
                    res = dict(row)
                    if not res.get("shop_name"):
                        res["shop_name"] = "Jack's Shop"
                    return res
                return default
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM shop_config WHERE guild_id = ?", (guild_id,))
                row = await cursor.fetchone()
                if row:
                    res = dict(row)
                    if not res.get("shop_name"):
                        res["shop_name"] = "Jack's Shop"
                    return res
                return default

    async def set_shop_config(self, guild_id: int, **kwargs) -> bool:
        curr = await self.get_shop_config(guild_id)
        for k, v in kwargs.items():
            if k in curr:
                curr[k] = v

        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO shop_config (guild_id, shop_name, ltc_address, deal_log_channel_id, feedback_channel_id, purchase_category_id, staff_role_id, min_confirmations, currency)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (guild_id) DO UPDATE SET
                        shop_name = EXCLUDED.shop_name,
                        ltc_address = EXCLUDED.ltc_address,
                        deal_log_channel_id = EXCLUDED.deal_log_channel_id,
                        feedback_channel_id = EXCLUDED.feedback_channel_id,
                        purchase_category_id = EXCLUDED.purchase_category_id,
                        staff_role_id = EXCLUDED.staff_role_id,
                        min_confirmations = EXCLUDED.min_confirmations,
                        currency = EXCLUDED.currency
                """, guild_id, curr["shop_name"], curr["ltc_address"], curr["deal_log_channel_id"],
                    curr["feedback_channel_id"], curr["purchase_category_id"], curr["staff_role_id"],
                    curr["min_confirmations"], curr["currency"])
                return True
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("""
                    INSERT INTO shop_config (guild_id, shop_name, ltc_address, deal_log_channel_id, feedback_channel_id, purchase_category_id, staff_role_id, min_confirmations, currency)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(guild_id) DO UPDATE SET
                        shop_name = excluded.shop_name,
                        ltc_address = excluded.ltc_address,
                        deal_log_channel_id = excluded.deal_log_channel_id,
                        feedback_channel_id = excluded.feedback_channel_id,
                        purchase_category_id = excluded.purchase_category_id,
                        staff_role_id = excluded.staff_role_id,
                        min_confirmations = excluded.min_confirmations,
                        currency = excluded.currency
                """, (guild_id, curr["shop_name"], curr["ltc_address"], curr["deal_log_channel_id"],
                      curr["feedback_channel_id"], curr["purchase_category_id"], curr["staff_role_id"],
                      curr["min_confirmations"], curr["currency"]))
                await db.commit()
                return True

    # ==========================================
    # USER LITECOIN WALLETS
    # ==========================================
    async def link_user_ltc(self, user_id: int, address: str) -> bool:
        clean = address.strip()
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO user_ltc_wallets (user_id, ltc_address)
                    VALUES ($1, $2)
                    ON CONFLICT (user_id) DO UPDATE SET
                        ltc_address = EXCLUDED.ltc_address,
                        linked_at = CURRENT_TIMESTAMP
                """, user_id, clean)
                return True
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("""
                    INSERT INTO user_ltc_wallets (user_id, ltc_address)
                    VALUES (?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        ltc_address = excluded.ltc_address,
                        linked_at = CURRENT_TIMESTAMP
                """, (user_id, clean))
                await db.commit()
                return True

    async def unlink_user_ltc(self, user_id: int) -> bool:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                res = await conn.execute("DELETE FROM user_ltc_wallets WHERE user_id = $1", user_id)
                return "DELETE 1" in res
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("DELETE FROM user_ltc_wallets WHERE user_id = ?", (user_id,))
                await db.commit()
                return cursor.rowcount > 0

    async def get_user_ltc(self, user_id: int) -> Optional[str]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                val = await conn.fetchval("SELECT ltc_address FROM user_ltc_wallets WHERE user_id = $1", user_id)
                return val
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("SELECT ltc_address FROM user_ltc_wallets WHERE user_id = ?", (user_id,))
                row = await cursor.fetchone()
                return row[0] if row else None

    # ==========================================
    # SHOP ORDERS & INVOICES
    # ==========================================
    async def create_shop_order(
        self,
        guild_id: int,
        user_id: int,
        product_name: str,
        quantity: int,
        total_usd: float,
        total_ltc: float,
        payment_method: str = "Litecoin",
        ltc_address: str = None,
        ticket_channel_id: int = None
    ) -> Dict[str, Any]:
        import random
        order_id = f"ORD-{random.randint(100000, 999999)}"
        receipt_id = f"RD-{random.randint(100000, 999999)}"

        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO shop_orders (
                        order_id, receipt_id, guild_id, user_id, product_name, quantity,
                        total_usd, total_ltc, status, payment_method, ltc_address, ticket_channel_id
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """, order_id, receipt_id, guild_id, user_id, product_name, quantity,
                    total_usd, total_ltc, 'pending_payment', payment_method, ltc_address, ticket_channel_id)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("""
                    INSERT INTO shop_orders (
                        order_id, receipt_id, guild_id, user_id, product_name, quantity,
                        total_usd, total_ltc, status, payment_method, ltc_address, ticket_channel_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (order_id, receipt_id, guild_id, user_id, product_name, quantity,
                      total_usd, total_ltc, 'pending_payment', payment_method, ltc_address, ticket_channel_id))
                await db.commit()

        return await self.get_shop_order(order_id)

    async def get_shop_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        clean = order_id.strip()
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM shop_orders WHERE order_id = $1", clean)
                return dict(row) if row else None
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM shop_orders WHERE order_id = ?", (clean,))
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_order_by_receipt(self, receipt_id: str) -> Optional[Dict[str, Any]]:
        clean = receipt_id.strip()
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM shop_orders WHERE receipt_id = $1", clean)
                return dict(row) if row else None
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM shop_orders WHERE receipt_id = ?", (clean,))
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_user_orders(self, guild_id: int, user_id: int) -> List[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM shop_orders WHERE guild_id = $1 AND user_id = $2 ORDER BY created_at DESC", guild_id, user_id)
                return [dict(r) for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM shop_orders WHERE guild_id = ? AND user_id = ? ORDER BY created_at DESC", (guild_id, user_id))
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_guild_orders(self, guild_id: int, limit: int = 50, status: str = None) -> List[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                if status:
                    rows = await conn.fetch("SELECT * FROM shop_orders WHERE guild_id = $1 AND status = $2 ORDER BY created_at DESC LIMIT $3", guild_id, status, limit)
                else:
                    rows = await conn.fetch("SELECT * FROM shop_orders WHERE guild_id = $1 ORDER BY created_at DESC LIMIT $2", guild_id, limit)
                return [dict(r) for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                if status:
                    cursor = await db.execute("SELECT * FROM shop_orders WHERE guild_id = ? AND status = ? ORDER BY created_at DESC LIMIT ?", (guild_id, status, limit))
                else:
                    cursor = await db.execute("SELECT * FROM shop_orders WHERE guild_id = ? ORDER BY created_at DESC LIMIT ?", (guild_id, limit))
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def claim_order(self, order_id: str, staff_id: int) -> bool:
        clean = order_id.strip()
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                res = await conn.execute("UPDATE shop_orders SET claimed_by = $1 WHERE order_id = $2", staff_id, clean)
                return "UPDATE 1" in res
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("UPDATE shop_orders SET claimed_by = ? WHERE order_id = ?", (staff_id, clean))
                await db.commit()
                return cursor.rowcount > 0

    async def complete_order(self, order_id: str, staff_id: int = None, txid: str = None) -> Optional[Dict[str, Any]]:
        clean = order_id.strip()
        order = await self.get_shop_order(clean)
        if not order:
            return None

        # Prevent duplicate completion
        if order.get("status") == "completed":
            return order

        final_staff = staff_id or order.get("claimed_by") or 0
        final_txid = txid or order.get("txid")

        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE shop_orders
                    SET status = 'completed', claimed_by = $1, txid = $2, completed_at = CURRENT_TIMESTAMP
                    WHERE order_id = $3
                """, final_staff, final_txid, clean)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("""
                    UPDATE shop_orders
                    SET status = 'completed', claimed_by = ?, txid = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE order_id = ?
                """, (final_staff, final_txid, clean))
                await db.commit()

        return await self.get_shop_order(clean)

    async def cancel_order(self, order_id: str, reason: str = None) -> bool:
        clean = order_id.strip()
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                res = await conn.execute("UPDATE shop_orders SET status = 'cancelled' WHERE order_id = $1 AND status != 'completed'", clean)
                return "UPDATE 1" in res
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("UPDATE shop_orders SET status = 'cancelled' WHERE order_id = ? AND status != 'completed'", (clean,))
                await db.commit()
                return cursor.rowcount > 0

    async def refund_order(self, order_id: str, reason: str = None) -> bool:
        clean = order_id.strip()
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                res = await conn.execute("UPDATE shop_orders SET status = 'refunded' WHERE order_id = $1", clean)
                return "UPDATE 1" in res
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("UPDATE shop_orders SET status = 'refunded' WHERE order_id = ?", (clean,))
                await db.commit()
                return cursor.rowcount > 0

    # ==========================================
    # USED LTC TRANSACTIONS (PREVENT REUSE)
    # ==========================================
    async def record_used_txid(self, txid: str, order_id: str, guild_id: int, amount_ltc: float, confirmations: int = 1) -> bool:
        clean_tx = txid.strip().lower()
        if await self.is_txid_used(clean_tx):
            return False
        try:
            if self.is_postgres and self.pool:
                async with self.pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO used_ltc_transactions (txid, order_id, guild_id, amount_ltc, confirmations)
                        VALUES ($1, $2, $3, $4, $5)
                    """, clean_tx, order_id, guild_id, amount_ltc, confirmations)
                    return True
            else:
                async with aiosqlite.connect(self.sqlite_path) as db:
                    await db.execute("""
                        INSERT INTO used_ltc_transactions (txid, order_id, guild_id, amount_ltc, confirmations)
                        VALUES (?, ?, ?, ?, ?)
                    """, (clean_tx, order_id, guild_id, amount_ltc, confirmations))
                    await db.commit()
                    return True
        except Exception:
            return False

    async def is_txid_used(self, txid: str) -> bool:
        clean_tx = txid.strip().lower()
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                val = await conn.fetchval("SELECT txid FROM used_ltc_transactions WHERE LOWER(txid) = $1", clean_tx)
                return bool(val)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("SELECT txid FROM used_ltc_transactions WHERE LOWER(txid) = ?", (clean_tx,))
                row = await cursor.fetchone()
                return bool(row)

    # ==========================================
    # DIGITAL PRODUCT DELIVERY (DISPENSE STOCK)
    # ==========================================
    async def dispense_stock(self, guild_id: int, item_name: str, quantity: int = 1) -> List[str]:
        clean = item_name.strip()
        dispensed = []
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    rows = await conn.fetch("""
                        SELECT id, stock_data FROM shop_stock
                        WHERE guild_id = $1 AND LOWER(item_name) = LOWER($2) AND is_used = FALSE
                        LIMIT $3
                        FOR UPDATE
                    """, guild_id, clean, quantity)
                    if rows:
                        ids = [r["id"] for r in rows]
                        dispensed = [r["stock_data"] for r in rows]
                        await conn.execute("UPDATE shop_stock SET is_used = TRUE WHERE id = ANY($1)", ids)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("""
                    SELECT id, stock_data FROM shop_stock
                    WHERE guild_id = ? AND LOWER(item_name) = LOWER(?) AND is_used = 0
                    LIMIT ?
                """, (guild_id, clean, quantity))
                rows = await cursor.fetchall()
                if rows:
                    ids = [r[0] for r in rows]
                    dispensed = [r[1] for r in rows]
                    placeholders = ",".join("?" * len(ids))
                    await db.execute(f"UPDATE shop_stock SET is_used = 1 WHERE id IN ({placeholders})", ids)
                    await db.commit()
        return dispensed

    # ==========================================
    # CUSTOMER METRICS & LIFETIME SPEND
    # ==========================================
    async def get_customer_lifetime_spend(self, guild_id: int, user_id: int) -> float:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                val = await conn.fetchval("""
                    SELECT COALESCE(SUM(total_usd), 0.0) FROM shop_orders
                    WHERE guild_id = $1 AND user_id = $2 AND status = 'completed'
                """, guild_id, user_id)
                return round(float(val or 0.0), 2)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("""
                    SELECT COALESCE(SUM(total_usd), 0.0) FROM shop_orders
                    WHERE guild_id = ? AND user_id = ? AND status = 'completed'
                """, (guild_id, user_id))
                row = await cursor.fetchone()
                return round(float(row[0] if row else 0.0), 2)

    async def get_customer_profile(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        lifetime_spend = await self.get_customer_lifetime_spend(guild_id, user_id)
        orders = await self.get_user_orders(guild_id, user_id)
        completed_orders = [o for o in orders if o.get("status") == "completed"]
        refunded_orders = [o for o in orders if o.get("status") == "refunded"]
        active_orders = [o for o in orders if o.get("status") in ("pending_payment", "paid")]

        # Determine loyalty tier
        if lifetime_spend >= 500:
            tier = "💎 Diamond VIP"
        elif lifetime_spend >= 200:
            tier = "🥇 Gold Member"
        elif lifetime_spend >= 50:
            tier = "🥈 Silver Regular"
        elif lifetime_spend > 0:
            tier = "🥉 Bronze Patron"
        else:
            tier = "🌱 New Customer"

        # Linked LTC
        ltc_addr = await self.get_user_ltc(user_id)

        # Reviews by this customer
        reviews = await self.get_customer_feedback(guild_id, user_id=user_id)
        avg_rating = round(sum(r["stars"] for r in reviews) / len(reviews), 1) if reviews else 5.0

        return {
            "guild_id": guild_id,
            "user_id": user_id,
            "total_orders": len(orders),
            "completed_orders": len(completed_orders),
            "active_orders": len(active_orders),
            "refunded_orders": len(refunded_orders),
            "lifetime_spend": lifetime_spend,
            "loyalty_tier": tier,
            "ltc_address": ltc_addr,
            "total_reviews": len(reviews),
            "avg_review_rating": avg_rating,
            "recent_orders": orders[:5]
        }

    async def get_customer_spending_leaderboard(self, guild_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT user_id, COALESCE(SUM(total_usd), 0.0) as total_spent, COUNT(*) as orders_count
                    FROM shop_orders
                    WHERE guild_id = $1 AND status = 'completed'
                    GROUP BY user_id
                    ORDER BY total_spent DESC
                    LIMIT $2
                """, guild_id, limit)
                return [{"user_id": r["user_id"], "total_spent": round(float(r["total_spent"]), 2), "orders_count": r["orders_count"]} for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("""
                    SELECT user_id, COALESCE(SUM(total_usd), 0.0) as total_spent, COUNT(*) as orders_count
                    FROM shop_orders
                    WHERE guild_id = ? AND status = 'completed'
                    GROUP BY user_id
                    ORDER BY total_spent DESC
                    LIMIT ?
                """, (guild_id, limit))
                rows = await cursor.fetchall()
                return [{"user_id": r[0], "total_spent": round(float(r[1]), 2), "orders_count": r[2]} for r in rows]

    # ==========================================
    # CUSTOMER FEEDBACK & STAR RATINGS
    # ==========================================
    async def add_customer_feedback(self, guild_id: int, order_id: str, user_id: int, stars: int, description: str) -> int:
        clean_order = order_id.strip()
        clamped_stars = max(1, min(5, stars))
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                fid = await conn.fetchval("""
                    INSERT INTO customer_feedback (guild_id, order_id, user_id, stars, description)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                """, guild_id, clean_order, user_id, clamped_stars, description.strip())
                return fid
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("""
                    INSERT INTO customer_feedback (guild_id, order_id, user_id, stars, description)
                    VALUES (?, ?, ?, ?, ?)
                """, (guild_id, clean_order, user_id, clamped_stars, description.strip()))
                await db.commit()
                return cursor.lastrowid

    async def get_customer_feedback(self, guild_id: int, user_id: int = None, order_id: str = None) -> List[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                if order_id:
                    rows = await conn.fetch("SELECT * FROM customer_feedback WHERE guild_id = $1 AND order_id = $2", guild_id, order_id.strip())
                elif user_id:
                    rows = await conn.fetch("SELECT * FROM customer_feedback WHERE guild_id = $1 AND user_id = $2 ORDER BY id DESC", guild_id, user_id)
                else:
                    rows = await conn.fetch("SELECT * FROM customer_feedback WHERE guild_id = $1 ORDER BY id DESC", guild_id)
                return [dict(r) for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                if order_id:
                    cursor = await db.execute("SELECT * FROM customer_feedback WHERE guild_id = ? AND order_id = ?", (guild_id, order_id.strip()))
                elif user_id:
                    cursor = await db.execute("SELECT * FROM customer_feedback WHERE guild_id = ? AND user_id = ? ORDER BY id DESC", (guild_id, user_id))
                else:
                    cursor = await db.execute("SELECT * FROM customer_feedback WHERE guild_id = ? ORDER BY id DESC", (guild_id,))
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_feedback_stats(self, guild_id: int) -> Dict[str, Any]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT COUNT(*) as total, COALESCE(AVG(stars), 0.0) as avg_stars
                    FROM customer_feedback WHERE guild_id = $1
                """, guild_id)
                total = row["total"] if row else 0
                avg = round(float(row["avg_stars"]), 2) if row else 5.0
                return {"total": total, "avg_stars": avg}
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("""
                    SELECT COUNT(*), COALESCE(AVG(stars), 0.0)
                    FROM customer_feedback WHERE guild_id = ?
                """, (guild_id,))
                row = await cursor.fetchone()
                total = row[0] if row else 0
                avg = round(float(row[1]), 2) if row else 5.0
                return {"total": total, "avg_stars": avg}

    async def delete_customer_feedback(self, guild_id: int, review_id: int) -> bool:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                res = await conn.execute("DELETE FROM customer_feedback WHERE id = $1 AND guild_id = $2", review_id, guild_id)
                return "DELETE 1" in res
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("DELETE FROM customer_feedback WHERE id = ? AND guild_id = ?", (review_id, guild_id))
                await db.commit()
                return cursor.rowcount > 0

    # ==========================================
    # LEGIT COUNTER & VOUCH SYSTEM
    # ==========================================
    async def toggle_legit_vouch(self, guild_id: int, user_id: int) -> Tuple[bool, int]:
        has_vouched = await self.has_user_vouched_legit(guild_id, user_id)
        if has_vouched:
            await self.remove_legit_vouch(guild_id, user_id)
            total = await self.get_legit_count(guild_id)
            return False, total
        else:
            if self.is_postgres and self.pool:
                async with self.pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO shop_legit_vouches (guild_id, user_id)
                        VALUES ($1, $2)
                        ON CONFLICT DO NOTHING
                    """, guild_id, user_id)
            else:
                async with aiosqlite.connect(self.sqlite_path) as db:
                    await db.execute("INSERT OR IGNORE INTO shop_legit_vouches (guild_id, user_id) VALUES (?, ?)", (guild_id, user_id))
                    await db.commit()
            total = await self.get_legit_count(guild_id)
            return True, total

    async def has_user_vouched_legit(self, guild_id: int, user_id: int) -> bool:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                val = await conn.fetchval("SELECT user_id FROM shop_legit_vouches WHERE guild_id = $1 AND user_id = $2", guild_id, user_id)
                return bool(val)
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("SELECT user_id FROM shop_legit_vouches WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
                row = await cursor.fetchone()
                return bool(row)

    async def get_legit_count(self, guild_id: int) -> int:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                val = await conn.fetchval("SELECT COUNT(*) FROM shop_legit_vouches WHERE guild_id = $1", guild_id)
                return val or 0
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM shop_legit_vouches WHERE guild_id = ?", (guild_id,))
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def get_legit_vouches(self, guild_id: int, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM shop_legit_vouches WHERE guild_id = $1 ORDER BY timestamp DESC LIMIT $2 OFFSET $3", guild_id, limit, offset)
                return [dict(r) for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM shop_legit_vouches WHERE guild_id = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?", (guild_id, limit, offset))
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def remove_legit_vouch(self, guild_id: int, user_id: int) -> bool:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                res = await conn.execute("DELETE FROM shop_legit_vouches WHERE guild_id = $1 AND user_id = $2", guild_id, user_id)
                return "DELETE 1" in res
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("DELETE FROM shop_legit_vouches WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
                await db.commit()
                return cursor.rowcount > 0

    async def reset_legit_vouches(self, guild_id: int) -> int:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                res = await conn.execute("DELETE FROM shop_legit_vouches WHERE guild_id = $1", guild_id)
                parts = res.split()
                return int(parts[1]) if len(parts) > 1 else 0
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("DELETE FROM shop_legit_vouches WHERE guild_id = ?", (guild_id,))
                await db.commit()
                return cursor.rowcount

    # ==========================================
    # COUPONS & DISCOUNTS
    # ==========================================
    async def create_coupon(self, guild_id: int, code: str, discount_percent: float, max_uses: int = 100) -> int:
        clean = code.strip().upper()
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                cid = await conn.fetchval("""
                    INSERT INTO shop_coupons (guild_id, code, discount_percent, max_uses)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (guild_id, code) DO UPDATE SET
                        discount_percent = EXCLUDED.discount_percent,
                        max_uses = EXCLUDED.max_uses
                    RETURNING id
                """, guild_id, clean, discount_percent, max_uses)
                return cid
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("""
                    INSERT INTO shop_coupons (guild_id, code, discount_percent, max_uses)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(guild_id, code) DO UPDATE SET
                        discount_percent = excluded.discount_percent,
                        max_uses = excluded.max_uses
                """, (guild_id, clean, discount_percent, max_uses))
                await db.commit()
                return cursor.lastrowid

    async def get_coupon(self, guild_id: int, code: str) -> Optional[Dict[str, Any]]:
        clean = code.strip().upper()
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM shop_coupons WHERE guild_id = $1 AND code = $2", guild_id, clean)
                return dict(row) if row else None
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM shop_coupons WHERE guild_id = ? AND code = ?", (guild_id, clean))
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def use_coupon(self, guild_id: int, code: str) -> bool:
        clean = code.strip().upper()
        coupon = await self.get_coupon(guild_id, clean)
        if not coupon or coupon["uses_count"] >= coupon["max_uses"]:
            return False
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("UPDATE shop_coupons SET uses_count = uses_count + 1 WHERE id = $1", coupon["id"])
                return True
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("UPDATE shop_coupons SET uses_count = uses_count + 1 WHERE id = ?", (coupon["id"],))
                await db.commit()
                return True

    # ==========================================
    # SHOPPING CART
    # ==========================================
    async def add_to_cart(self, guild_id: int, user_id: int, item_id: int, quantity: int = 1) -> bool:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO shopping_carts (guild_id, user_id, item_id, quantity)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (guild_id, user_id, item_id) DO UPDATE SET
                        quantity = shopping_carts.quantity + EXCLUDED.quantity
                """, guild_id, user_id, item_id, quantity)
                return True
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("""
                    INSERT INTO shopping_carts (guild_id, user_id, item_id, quantity)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(guild_id, user_id, item_id) DO UPDATE SET
                        quantity = shopping_carts.quantity + excluded.quantity
                """, (guild_id, user_id, item_id, quantity))
                await db.commit()
                return True

    async def get_cart(self, guild_id: int, user_id: int) -> List[Dict[str, Any]]:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT c.item_id, c.quantity, i.name, i.price, i.category
                    FROM shopping_carts c
                    JOIN shop_items i ON c.item_id = i.id
                    WHERE c.guild_id = $1 AND c.user_id = $2
                """, guild_id, user_id)
                return [dict(r) for r in rows]
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT c.item_id, c.quantity, i.name, i.price, i.category
                    FROM shopping_carts c
                    JOIN shop_items i ON c.item_id = i.id
                    WHERE c.guild_id = ? AND c.user_id = ?
                """, (guild_id, user_id))
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def remove_from_cart(self, guild_id: int, user_id: int, item_id: int) -> bool:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                res = await conn.execute("DELETE FROM shopping_carts WHERE guild_id = $1 AND user_id = $2 AND item_id = $3", guild_id, user_id, item_id)
                return "DELETE 1" in res
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("DELETE FROM shopping_carts WHERE guild_id = ? AND user_id = ? AND item_id = ?", (guild_id, user_id, item_id))
                await db.commit()
                return cursor.rowcount > 0

    async def clear_cart(self, guild_id: int, user_id: int) -> bool:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("DELETE FROM shopping_carts WHERE guild_id = $1 AND user_id = $2", guild_id, user_id)
                return True
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("DELETE FROM shopping_carts WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
                await db.commit()
                return True

    # ==========================================
    # REVENUE & SALES ANALYTICS
    # ==========================================
    async def get_shop_revenue_stats(self, guild_id: int) -> Dict[str, Any]:
        orders = await self.get_guild_orders(guild_id, limit=500)
        completed = [o for o in orders if o.get("status") == "completed"]

        total_rev = sum(o.get("total_usd", 0.0) for o in completed)
        now = datetime.datetime.utcnow()

        # Compute daily & monthly revenue
        daily_rev = 0.0
        monthly_rev = 0.0
        product_sales: Dict[str, int] = {}

        for o in completed:
            p_name = o.get("product_name", "Unknown")
            product_sales[p_name] = product_sales.get(p_name, 0) + o.get("quantity", 1)
            created_at = o.get("created_at")
            if created_at:
                try:
                    if isinstance(created_at, str):
                        dt = datetime.datetime.fromisoformat(created_at.replace("Z", "+00:00").split(".")[0])
                    else:
                        dt = created_at
                    if (now - dt).days < 1:
                        daily_rev += o.get("total_usd", 0.0)
                    if (now - dt).days < 30:
                        monthly_rev += o.get("total_usd", 0.0)
                except Exception:
                    pass

        top_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_revenue": round(total_rev, 2),
            "daily_revenue": round(daily_rev, 2),
            "monthly_revenue": round(monthly_rev, 2),
            "completed_orders": len(completed),
            "total_orders": len(orders),
            "top_products": top_products
        }

    async def log_deal_audit(self, guild_id: int, receipt_id: str, action: str, staff_id: int, details: str) -> int:
        if self.is_postgres and self.pool:
            async with self.pool.acquire() as conn:
                aid = await conn.fetchval("""
                    INSERT INTO deal_audit_logs (guild_id, receipt_id, action, staff_id, details)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                """, guild_id, receipt_id, action, staff_id, details)
                return aid
        else:
            async with aiosqlite.connect(self.sqlite_path) as db:
                cursor = await db.execute("""
                    INSERT INTO deal_audit_logs (guild_id, receipt_id, action, staff_id, details)
                    VALUES (?, ?, ?, ?, ?)
                """, (guild_id, receipt_id, action, staff_id, details))
                await db.commit()
                return cursor.lastrowid

db = Database()



