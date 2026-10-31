import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "zyath_bot.db")

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    async def init(self):
        """Initialize all database tables with proper indexes."""
        async with aiosqlite.connect(self.db_path) as db:
            # Guild settings table
            await db.execute("""
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
                )
            """)

            # Vouches table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS vouches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    target_id INTEGER NOT NULL,
                    author_id INTEGER NOT NULL,
                    stars INTEGER DEFAULT 5,
                    comment TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Trades table ($mercy live trade logger)
            await db.execute("""
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
                )
            """)

            # Shop items table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS shop_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    price TEXT NOT NULL,
                    category TEXT DEFAULT 'General',
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Warnings table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    mod_id INTEGER NOT NULL,
                    reason TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tickets table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL UNIQUE,
                    user_id INTEGER NOT NULL,
                    category TEXT DEFAULT 'General Support',
                    status TEXT DEFAULT 'open',
                    claimed_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Payment methods table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS payment_methods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    method_name TEXT NOT NULL,
                    address TEXT NOT NULL,
                    note TEXT
                )
            """)

            # Shop Terms of Service table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS shop_tos (
                    guild_id INTEGER PRIMARY KEY,
                    tos_text TEXT NOT NULL
                )
            """)

            # No-Prefix Users table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS no_prefix_users (
                    user_id INTEGER PRIMARY KEY,
                    added_by INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await db.commit()
            await self.load_np_cache()

    async def load_np_cache(self):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT user_id FROM no_prefix_users")
            rows = await cursor.fetchall()
            self._np_cache = {r[0] for r in rows}

    def is_no_prefix_cached(self, user_id: int) -> bool:
        if not hasattr(self, "_np_cache"):
            self._np_cache = set()
        return user_id in self._np_cache

    # --- Guild Settings ---
    async def get_guild_settings(self, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
            if not row:
                await db.execute("INSERT INTO guild_settings (guild_id) VALUES (?)", (guild_id,))
                await db.commit()
                cursor = await db.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,))
                row = await cursor.fetchone()
            return dict(row)

    async def update_guild_setting(self, guild_id: int, key: str, value):
        allowed_keys = [
            "prefix", "vouch_channel_id", "trade_channel_id", "modlog_channel_id",
            "welcome_channel_id", "leave_channel_id", "welcome_message", "leave_message",
            "ticket_category_id", "ticket_logs_channel_id", "ticket_staff_role_id", "autorole_id"
        ]
        if key not in allowed_keys:
            raise ValueError(f"Invalid setting key: {key}")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"""
                INSERT INTO guild_settings (guild_id, {key}) VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET {key} = ?
            """, (guild_id, value, value))
            await db.commit()

    # --- Vouches ---
    async def add_vouch(self, guild_id: int, target_id: int, author_id: int, stars: int, comment: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO vouches (guild_id, target_id, author_id, stars, comment)
                VALUES (?, ?, ?, ?, ?)
            """, (guild_id, target_id, author_id, stars, comment))
            await db.commit()
            return cursor.lastrowid

    async def get_vouches(self, guild_id: int, target_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM vouches WHERE guild_id = ? AND target_id = ? ORDER BY id DESC
            """, (guild_id, target_id))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_vouch_stats(self, guild_id: int, target_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT COUNT(*), AVG(stars) FROM vouches WHERE guild_id = ? AND target_id = ?
            """, (guild_id, target_id))
            row = await cursor.fetchone()
            count = row[0] or 0
            avg = row[1] or 0.0
            return count, round(avg, 1)

    # --- Trades ($mercy) ---
    async def create_trade(self, trade_id: str, guild_id: int, mm_id: int, buyer_id: int, seller_id: int, amount: str, details: str, channel_id: int = None, message_id: int = None):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO trades (id, guild_id, mm_id, buyer_id, seller_id, amount, details, status, channel_id, message_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'In Progress', ?, ?)
            """, (trade_id, guild_id, mm_id, buyer_id, seller_id, amount, details, channel_id, message_id))
            await db.commit()

    async def get_trade(self, trade_id: str):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_trade_status(self, trade_id: str, status: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE trades SET status = ? WHERE id = ?", (status, trade_id))
            await db.commit()

    async def update_trade_message(self, trade_id: str, channel_id: int, message_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE trades SET channel_id = ?, message_id = ? WHERE id = ?", (channel_id, message_id, trade_id))
            await db.commit()

    # --- Shop ---
    async def add_shop_item(self, guild_id: int, name: str, price: str, category: str, description: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO shop_items (guild_id, name, price, category, description)
                VALUES (?, ?, ?, ?, ?)
            """, (guild_id, name, price, category, description))
            await db.commit()
            return cursor.lastrowid

    async def get_shop_items(self, guild_id: int, category: str = None):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if category:
                cursor = await db.execute("SELECT * FROM shop_items WHERE guild_id = ? AND category = ? ORDER BY id ASC", (guild_id, category))
            else:
                cursor = await db.execute("SELECT * FROM shop_items WHERE guild_id = ? ORDER BY id ASC", (guild_id,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_shop_item(self, item_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM shop_items WHERE id = ?", (item_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def remove_shop_item(self, guild_id: int, item_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM shop_items WHERE id = ? AND guild_id = ?", (item_id, guild_id))
            await db.commit()
            return cursor.rowcount > 0

    async def get_shop_categories(self, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT DISTINCT category FROM shop_items WHERE guild_id = ?", (guild_id,))
            rows = await cursor.fetchall()
            return [r[0] for r in rows if r[0]]

    # --- Warnings ---
    async def add_warning(self, guild_id: int, user_id: int, mod_id: int, reason: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO warnings (guild_id, user_id, mod_id, reason)
                VALUES (?, ?, ?, ?)
            """, (guild_id, user_id, mod_id, reason))
            await db.commit()
            return cursor.lastrowid

    async def get_warnings(self, guild_id: int, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY id DESC", (guild_id, user_id))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def clear_warnings(self, guild_id: int, user_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM warnings WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            await db.commit()
            return cursor.rowcount

    # --- Tickets ---
    async def create_ticket_record(self, guild_id: int, channel_id: int, user_id: int, category: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO tickets (guild_id, channel_id, user_id, category)
                VALUES (?, ?, ?, ?)
            """, (guild_id, channel_id, user_id, category))
            await db.commit()
            return cursor.lastrowid

    async def get_ticket_record(self, channel_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM tickets WHERE channel_id = ?", (channel_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def claim_ticket(self, channel_id: int, staff_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE tickets SET claimed_by = ? WHERE channel_id = ?", (staff_id, channel_id))
            await db.commit()

    async def close_ticket_record(self, channel_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE tickets SET status = 'closed' WHERE channel_id = ?", (channel_id,))
            await db.commit()

    async def reopen_ticket_record(self, channel_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE tickets SET status = 'open' WHERE channel_id = ?", (channel_id,))
            await db.commit()

    async def delete_ticket_record(self, channel_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM tickets WHERE channel_id = ?", (channel_id,))
            await db.commit()

    # --- Payment Methods ---
    async def add_payment_method(self, guild_id: int, method_name: str, address: str, note: str = "") -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO payment_methods (guild_id, method_name, address, note)
                VALUES (?, ?, ?, ?)
            """, (guild_id, method_name, address, note))
            await db.commit()
            return cursor.lastrowid

    async def get_payment_methods(self, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM payment_methods WHERE guild_id = ? ORDER BY id ASC", (guild_id,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def remove_payment_method(self, guild_id: int, method_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM payment_methods WHERE id = ? AND guild_id = ?", (method_id, guild_id))
            await db.commit()
            return cursor.rowcount > 0

    # --- Shop TOS ---
    async def set_shop_tos(self, guild_id: int, tos_text: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO shop_tos (guild_id, tos_text) VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET tos_text = ?
            """, (guild_id, tos_text, tos_text))
            await db.commit()

    async def get_shop_tos(self, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT tos_text FROM shop_tos WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
            return row[0] if row else None

    # --- No Prefix ---
    async def add_no_prefix_user(self, user_id: int, added_by: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO no_prefix_users (user_id, added_by) VALUES (?, ?)
                ON CONFLICT(user_id) DO NOTHING
            """, (user_id, added_by))
            await db.commit()
        if not hasattr(self, "_np_cache"):
            self._np_cache = set()
        self._np_cache.add(user_id)

    async def remove_no_prefix_user(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM no_prefix_users WHERE user_id = ?", (user_id,))
            await db.commit()
            removed = cursor.rowcount > 0
        if removed and hasattr(self, "_np_cache"):
            self._np_cache.discard(user_id)
        return removed

    async def get_all_no_prefix_users(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM no_prefix_users ORDER BY timestamp DESC")
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

db = Database()
