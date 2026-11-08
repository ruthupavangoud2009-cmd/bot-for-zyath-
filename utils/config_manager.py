import os
import json
from typing import Optional, Dict, Any

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

DEFAULT_SUPPORT_SERVER = "https://discord.gg/kyoka"
HARDCODED_BOT_OWNER_ID = 1505515188991033409

_cached_config: Optional[Dict[str, Any]] = None

def load_config() -> Dict[str, Any]:
    global _cached_config
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                _cached_config = json.load(f)
                return _cached_config
        except Exception as e:
            print(f"[CONFIG] Error loading config.json: {e}")
    if _cached_config is None:
        _cached_config = {}
    return _cached_config

def save_config(data: Dict[str, Any]) -> bool:
    global _cached_config
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        _cached_config = data
        return True
    except Exception as e:
        print(f"[CONFIG] Error saving config.json: {e}")
        return False

def get_bot_name() -> str:
    cfg = load_config()
    return cfg.get("bot_name") or "Kyoka Shop"

def get_support_server() -> str:
    cfg = load_config()
    return cfg.get("support_server") or DEFAULT_SUPPORT_SERVER

def set_support_server(url: str) -> bool:
    cfg = load_config()
    cfg["support_server"] = url.strip()
    return save_config(cfg)

def get_config_value(key: str, default: Any = None) -> Any:
    cfg = load_config()
    return cfg.get(key, default)

def set_config_value(key: str, value: Any) -> bool:
    cfg = load_config()
    cfg[key] = value
    return save_config(cfg)

def get_owner_ids() -> set[int]:
    """Returns only the hardcoded bot owner ID (1505515188991033409)."""
    return {HARDCODED_BOT_OWNER_ID}

def add_owner_to_config(user_id: int) -> bool:
    """Bot owner is hardcoded to 1505515188991033409 only."""
    return False

def remove_owner_from_config(user_id: int) -> bool:
    """Bot owner is hardcoded to 1505515188991033409 only."""
    return False

def get_bot_staff() -> Dict[str, str]:
    cfg = load_config()
    staff = cfg.get("bot_staff", {})
    if not isinstance(staff, dict):
        staff = {}
    return staff

def save_bot_staff(staff_map: Dict[str, str]) -> bool:
    cfg = load_config()
    # Filter out banned owner IDs
    clean_map = {k: v for k, v in staff_map.items() if str(k) != "1521774957065928734"}
    cfg["bot_staff"] = clean_map
    cfg["staff_ids"] = list(clean_map.keys())
    return save_config(cfg)

def add_staff_to_config(user_id: int, role: str) -> bool:
    if user_id == 1521774957065928734:
        return False
    staff = get_bot_staff()
    staff[str(user_id)] = (role or "Staff").strip()[:30]
    return save_bot_staff(staff)

def remove_staff_from_config(user_id: int) -> bool:
    staff = get_bot_staff()
    uid_str = str(user_id)
    if uid_str in staff:
        del staff[uid_str]
        return save_bot_staff(staff)
    return False

def get_no_prefix_users() -> list[str]:
    cfg = load_config()
    raw = cfg.get("no_prefix_users", [])
    if not isinstance(raw, list):
        raw = []
    return [str(x) for x in raw if str(x) != "1521774957065928734"]

def save_no_prefix_users(users: list[str]) -> bool:
    cfg = load_config()
    cfg["no_prefix_users"] = [str(x) for x in list(dict.fromkeys(users)) if str(x) != "1521774957065928734"]
    return save_config(cfg)

def add_no_prefix_to_config(user_id: int) -> bool:
    if user_id == 1521774957065928734:
        return False
    users = get_no_prefix_users()
    uid_str = str(user_id)
    if uid_str not in users:
        users.append(uid_str)
        return save_no_prefix_users(users)
    return True

def remove_no_prefix_from_config(user_id: int) -> bool:
    users = get_no_prefix_users()
    uid_str = str(user_id)
    if uid_str in users:
        users.remove(uid_str)
        return save_no_prefix_users(users)
    return False

async def check_is_owner(bot, user) -> bool:
    user_id = getattr(user, "id", None)
    return user_id == HARDCODED_BOT_OWNER_ID
