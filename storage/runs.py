"""Runs storage wrappers delegating to existing store.py (Phase 1)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

try:
    from store import (
        append_run as _append_run,
    )
    from store import (
        list_runs as _list_runs,
    )
    from store import (
        load_run as _load_run,
    )
    from store import (
        save_run as _save_run,
    )
    from store import (
        update_endpoint_dossier as _update_endpoint_dossier,
    )
except Exception as _e:  # pragma: no cover
    def _append_run(pid: str, run: Dict[str, Any]): return None
    def _list_runs(pid: str) -> List[Dict[str, Any]]: return []
    def _save_run(pid: str, run_doc: Dict[str, Any]): return None
    def _load_run(pid: str, run_id: str) -> Dict[str, Any]: return {}
    def _update_endpoint_dossier(pid: str, base: str, method: str, path: str, summary: Dict[str, Any]): return None

try:
    from schemas.run import RunDoc
except Exception:
    RunDoc = None  # type: ignore

log = logging.getLogger("storage.runs")


def list_runs(pid: str) -> List[Dict[str, Any]]:
    items = _list_runs(pid)
    if RunDoc and isinstance(items, list):
        for i, it in enumerate(items[:50]):
            try:
                RunDoc(**it)  # type: ignore
            except Exception as e:
                log.warning("run_validation_error", extra={"pid": pid, "index": i, "error": str(e)})
                break
    return items


def append_run(pid: str, run: Dict[str, Any]):
    # Do not validate here to avoid overhead; append_run is legacy
    _append_run(pid, run)


def save_run(pid: str, run_doc: Dict[str, Any]):
    if RunDoc:
        try:
            RunDoc(**run_doc)  # type: ignore
        except Exception as e:
            log.warning("run_validation_error", extra={"pid": pid, "error": str(e)})
    _save_run(pid, run_doc)


def load_run(pid: str, run_id: str) -> Dict[str, Any]:
    doc = _load_run(pid, run_id)
    if RunDoc:
        try:
            RunDoc(**doc)  # type: ignore
        except Exception as e:
            log.warning("run_validation_error", extra={"pid": pid, "run_id": run_id, "error": str(e)})
    return doc


def update_endpoint_dossier(pid: str, base: str, method: str, path: str, summary: Dict[str, Any]):
    _update_endpoint_dossier(pid, base, method, path, summary)


__all__ = [
    "list_runs",
    "append_run",
    "save_run",
    "load_run",
    "update_endpoint_dossier",
]


