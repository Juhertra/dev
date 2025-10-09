"""Findings storage wrappers delegating to existing findings.py (Phase 1)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

try:
    from findings import (
        append_findings as _append_findings,
    )
    from findings import (
        clear_findings as _clear_findings,
    )
    from findings import (
        count_findings as _count_findings,
    )
    from findings import (
        get_findings as _get_findings,
    )
except Exception as _e:  # pragma: no cover
    def _get_findings(pid: str) -> List[Dict[str, Any]]: return []
    def _count_findings(pid: str) -> int: return 0
    def _clear_findings(pid: str) -> None: return None
    def _append_findings(pid: str, items: List[Dict[str, Any]]): return None

try:
    from schemas.finding import FindingDoc
except Exception:
    FindingDoc = None  # type: ignore

log = logging.getLogger("storage.findings")


def get_findings(pid: str) -> List[Dict[str, Any]]:
    rows = _get_findings(pid)
    # Validate shape (best-effort); do not fail writes/reads in Phase 1
    if FindingDoc and isinstance(rows, list):
        for i, r in enumerate(rows[:50]):  # sample to avoid overhead
            try:
                FindingDoc(**r)  # type: ignore
            except Exception as e:
                log.warning("finding_validation_error", extra={"pid": pid, "index": i, "error": str(e)})
                break
    return rows


def count_findings(pid: str) -> int:
    return _count_findings(pid)


def clear_findings(pid: str) -> None:
    _clear_findings(pid)


def append_findings(pid: str, items: List[Dict[str, Any]]):
    # Validate items individually (best-effort)
    if FindingDoc and isinstance(items, list):
        for i, it in enumerate(items[:50]):
            try:
                FindingDoc(**it)  # type: ignore
            except Exception as e:
                log.warning("finding_validation_error", extra={"pid": pid, "index": i, "error": str(e)})
                break
    _append_findings(pid, items)


__all__ = [
    "get_findings",
    "count_findings",
    "clear_findings",
    "append_findings",
]


