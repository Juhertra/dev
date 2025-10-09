from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional
from urllib.parse import urlencode

Json = Dict[str, Any]

def compose_display_url(url: str, query: Dict[str, Any]) -> str:
    """Build a display URL including query params (dicts are JSON-encoded; lists expand)."""
    if not url or not query:
        return url
    flat = {
        k: (json.dumps(v) if isinstance(v, dict) else v)
        for k, v in (query or {}).items()
    }
    try:
        return f"{url}?{urlencode(flat, doseq=True)}"
    except Exception:
        return url

def safe_id(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", s)

def read_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as e:
        print(f"Warning: Invalid JSON in {path}: {e}")
        return default
    except PermissionError as e:
        print(f"Error: Permission denied reading {path}: {e}")
        return default
    except Exception as e:
        print(f"Error: Unexpected error reading {path}: {e}")
        return default

def write_json(path: str, obj):
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)
        os.replace(tmp, path)
    except PermissionError as e:
        print(f"Error: Permission denied writing to {path}: {e}")
        raise
    except OSError as e:
        print(f"Error: OS error writing to {path}: {e}")
        raise
    except Exception as e:
        print(f"Error: Unexpected error writing to {path}: {e}")
        raise

def parse_json_field(txt: str, default):
    if not txt or not txt.strip():
        return default
    try:
        return json.loads(txt)
    except Exception:
        return default

# ---- files/json preview helpers for templates ----

def _files_preview_map(files: Any) -> Optional[Dict[str, str]]:
    """Map requests 'files' to display-only placeholders: { field: '<filename>' }."""
    if not isinstance(files, dict) or not files:
        return None
    out: Dict[str, str] = {}
    for name, val in files.items():
        filename: Optional[str] = None
        if isinstance(val, (list, tuple)) and len(val) >= 1:
            first = val[0]
            if isinstance(first, str):
                filename = first
        out[name] = f"<{filename}>" if filename else "<file>"
    return out

def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return "<bytes>"
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    try:
        import json as _json
        return _json.loads(_json.dumps(value, default=str))
    except Exception:
        return str(value)
