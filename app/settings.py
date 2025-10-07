"""
Minimal configuration loader.
Reads environment variables and app_config.json if present.
Expose get_settings() returning a dict-like settings snapshot.
"""

from __future__ import annotations
import os
import json
from typing import Any, Dict


def _load_app_config_json() -> Dict[str, Any]:
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # app_config.json sits at project root next to top-level app.py
        path = os.path.join(os.path.dirname(base_dir), "app_config.json")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh) or {}
    except Exception:
        pass
    return {}


def get_settings() -> Dict[str, Any]:
    cfg: Dict[str, Any] = {}
    # Environment overrides
    cfg["ENV"] = os.environ.get("ENV", "development")
    cfg["DEBUG"] = os.environ.get("DEBUG", "0") in ("1", "true", "True")
    cfg["API_KEYS"] = [k.strip() for k in os.environ.get("API_KEYS", "test-key-123").split(",") if k.strip()]
    # Merge app_config.json (does not override env-derived values)
    file_cfg = _load_app_config_json()
    for k, v in file_cfg.items():
        if k not in cfg:
            cfg[k] = v
    return cfg


__all__ = ["get_settings"]


