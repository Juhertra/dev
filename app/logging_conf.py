"""
Structured JSON logging setup with request_id support.
Default level: INFO. Safe to call multiple times.
"""

from __future__ import annotations
import json
import logging
import os
from typing import Any, Dict


class JsonRequestFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        base: Dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Optional request context fields
        rid = getattr(record, "request_id", None)
        if rid:
            base["request_id"] = rid
        dur = getattr(record, "duration_ms", None)
        if dur is not None:
            base["duration_ms"] = dur
        path = getattr(record, "path", None)
        if path:
            base["path"] = path
        method = getattr(record, "method", None)
        if method:
            base["method"] = method
        status = getattr(record, "status", None)
        if status is not None:
            base["status"] = status
        return json.dumps(base, ensure_ascii=False)


_configured = False


def setup_logging(level: str | int = None) -> None:
    global _configured
    if _configured:
        return
    lvl = level or os.environ.get("LOG_LEVEL", "INFO").upper()
    try:
        resolved = getattr(logging, str(lvl))
    except Exception:
        resolved = logging.INFO

    root = logging.getLogger()
    root.setLevel(resolved)
    # Clear existing handlers to avoid duplicates
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonRequestFormatter())
    root.addHandler(handler)

    _configured = True


__all__ = ["setup_logging", "JsonRequestFormatter"]


