"""Simple Tool protocol and in-memory registry (Phase 1)."""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol


class Tool(Protocol):
    name: str
    def status(self) -> Dict[str, Any]: ...
    def update(self) -> Dict[str, Any]: ...
    def configure(self, **opts) -> Dict[str, Any]: ...
    def reindex(self) -> Dict[str, Any]: ...


_REGISTRY: Dict[str, Tool] = {}


def register(tool: Tool) -> None:
    _REGISTRY[tool.name] = tool


def get(name: str) -> Optional[Tool]:
    return _REGISTRY.get(name)


def all_tools() -> Dict[str, Tool]:
    return dict(_REGISTRY)


__all__ = ["Tool", "register", "get", "all_tools"]


