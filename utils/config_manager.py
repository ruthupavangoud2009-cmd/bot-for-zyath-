import os
import json
from typing import Optional, Dict, Any

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

DEFAULT_SUPPORT_SERVER = "https://discord.gg/zyath"

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
