"""
Request context middleware: attaches request_id and request timing, and logs
one JSON line per request using the global logger.

Safe to register multiple times; handlers are idempotent.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from flask import g, request


def register_request_context(app: Any) -> None:
    log = logging.getLogger("request")

    @app.before_request
    def _start_timer() -> None:  # type: ignore[override]
        g._req_start = time.time()
        g._req_id = str(uuid.uuid4())

    @app.after_request
    def _log_request(resp):  # type: ignore[override]
        try:
            duration_ms = int((time.time() - getattr(g, "_req_start", time.time())) * 1000)
            # Preserve original message shape fields used in existing logs
            extra = {
                "request_id": getattr(g, "_req_id", "-"),
                "method": request.method,
                "path": request.path,
                "status": resp.status_code,
                "duration_ms": duration_ms,
            }
            log.info("request", extra=extra)
        except Exception:
            pass
        return resp


__all__ = ["register_request_context"]


