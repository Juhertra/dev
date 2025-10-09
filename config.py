import json
import os
from typing import Any, Dict, Optional

_CONFIG_FILENAME = "app_config.json"

def _config_path() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, _CONFIG_FILENAME)

def load_config() -> Dict[str, Any]:
    path = _config_path()
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh) or {}
    except Exception:
        pass
    return {}

def save_config(cfg: Dict[str, Any]) -> None:
    path = _config_path()
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2, ensure_ascii=False)
    except Exception:
        pass

def get(key: str, default: Optional[Any] = None) -> Any:
    cfg = load_config()
    return cfg.get(key, default)

def set(key: str, value: Any) -> None:
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)

def append_to_list(key: str, value: Any) -> None:
    cfg = load_config()
    arr = cfg.get(key)
    if not isinstance(arr, list):
        arr = []
    if value not in arr:
        arr.append(value)
    cfg[key] = arr
    save_config(cfg)


