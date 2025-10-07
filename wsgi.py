"""
Production WSGI entrypoint using the new app package factory, which loads the
existing top-level app.py under the hood. Behavior remains unchanged.
"""

from app import create_app  # type: ignore

app = create_app()


