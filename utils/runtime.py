from typing import Any, Dict


def get_runtime(pid: str) -> Dict[str, Any]:
    """Thin wrapper to centralize runtime access and avoid circular imports.

    Prefer importing this in routes and delegating to store.get_runtime inside
    to keep import graph shallow in route modules.
    """
    try:
        from store import get_runtime as _get_runtime  # type: ignore
        return _get_runtime(pid)
    except Exception:
        # Graceful fallback for early wiring
        return {}, {}, []  # session, SPECS, QUEUE


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


