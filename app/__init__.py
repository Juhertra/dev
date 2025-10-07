"""
Application package scaffold (Phase 1).

Provides a factory to create the Flask app by delegating to the existing
top-level application wiring while allowing centralized logging and
middleware registration. Behavior and URLs remain unchanged.
"""

from typing import Any
import os
import importlib.util


def create_app() -> Any:
    """
    Create the Flask app using the existing entrypoint module, then register
    request context middleware and logging. This keeps all routes and URLs
    exactly as they are today.
    """
    # Import existing top-level app.py module by file path to avoid name
    # collision with this package.
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app_py = os.path.join(root_dir, "app.py")
    spec = importlib.util.spec_from_file_location("_legacy_app_module", app_py)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to locate top-level app.py")
    base_app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base_app)
    flask_app = getattr(base_app, "app", None)
    if flask_app is None and hasattr(base_app, "create_app"):
        flask_app = base_app.create_app()

    # Best-effort logging setup (no-op if already configured)
    try:
        from .logging_conf import setup_logging

        setup_logging()
    except Exception:
        pass

    # Register request context middleware (safe if double-registered)
    try:
        from .middleware.request_context import register_request_context

        if flask_app is not None:
            register_request_context(flask_app)
    except Exception:
        pass

    return flask_app


__all__ = ["create_app"]


