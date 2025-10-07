"""
API package scaffold. For Phase 1, we re-export the existing api blueprint to
avoid any behavior changes while providing a stable import path.
"""

from typing import Any


try:
    # Re-export current blueprint defined in api_endpoints.py
    from api_endpoints import api_bp  # type: ignore
except Exception:
    api_bp = None  # type: ignore


def get_blueprint() -> Any:
    return api_bp


__all__ = ["api_bp", "get_blueprint"]


