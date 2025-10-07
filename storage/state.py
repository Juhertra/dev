"""State storage wrappers delegating to existing store.py (Phase 1)."""

from __future__ import annotations
from typing import Any, Dict, List, Tuple

try:
    from store import (
        ensure_runtime as _ensure_runtime,
        get_runtime as _get_runtime,
        persist_from_runtime as _persist_from_runtime,
        append_send_log as _append_send_log,
        get_sends as _get_sends,
        clear_sends as _clear_sends,
    )
except Exception as _e:  # pragma: no cover
    def _ensure_runtime(pid: str) -> None: return None
    def _get_runtime(pid: str): return {}, {}, []
    def _persist_from_runtime(pid: str, s: Dict[str, Any], sp: Dict[str, Any], q: List[Dict[str, Any]]): return None
    def _append_send_log(pid: str, entry: Dict[str, Any]): return None
    def _get_sends(pid: str): return []
    def _clear_sends(pid: str): return None


ensure_runtime = _ensure_runtime
get_runtime = _get_runtime
persist_from_runtime = _persist_from_runtime
append_send_log = _append_send_log
get_sends = _get_sends
clear_sends = _clear_sends

__all__ = [
    "ensure_runtime",
    "get_runtime",
    "persist_from_runtime",
    "append_send_log",
    "get_sends",
    "clear_sends",
]


