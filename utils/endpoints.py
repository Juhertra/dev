import re
from typing import Optional
from urllib.parse import urlsplit


def _norm_base(base: str) -> str:
    u = urlsplit(base)
    if u.scheme and u.netloc:
        return f"{u.scheme.lower()}://{u.netloc.lower()}"
    # If someone passed a bare host, assume https
    if re.match(r"^[A-Za-z0-9._-]+(:\d+)?$", base):
        return f"https://{base.lower()}"
    return base.lower()


def _norm_path(path: str) -> str:
    p = (path or "/").strip()
    return p if p.startswith("/") else f"/{p}"


def endpoint_key(method: str, base_or_url: str, path: Optional[str] = None) -> str:
    """
    Canonical key used EVERYWHERE: 'METHOD https://host[:port]/path'
    Accepts either (method, url) or (method, base, path).
    """
    m = (method or "GET").upper().strip()
    if path is None:
        u = urlsplit(base_or_url)
        base = f"{u.scheme.lower()}://{u.netloc.lower()}" if u.scheme and u.netloc else _norm_base(base_or_url)
        p = _norm_path(u.path or "/")
        if u.query:
            p = f"{p}?{u.query}"
    else:
        base = _norm_base(base_or_url)
        p = _norm_path(path)
    return f"{m} {base}{p}"


# Safe filename for canonical keys
def endpoint_safe_key(key: str) -> str:
    s = key
    for ch in ("://", "/", "?", "&", "=", " "):
        s = s.replace(ch, "_")
    return s

