"""Profiles storage wrappers delegating to existing store.py (Phase 1)."""

from __future__ import annotations
from typing import Any, Dict, List

try:
    from store import (
        get_profiles as _get_profiles,
        save_profile as _save_profile,
        load_profile as _load_profile,
        delete_profile as _delete_profile,
    )
except Exception as _e:  # pragma: no cover
    def _get_profiles(pid: str) -> List[Dict[str, Any]]: return []
    def _save_profile(pid: str, name: str, templates: List[str]) -> None: return None
    def _load_profile(pid: str, name: str) -> List[str]: return []
    def _delete_profile(pid: str, name: str) -> None: return None


get_profiles = _get_profiles
save_profile = _save_profile
load_profile = _load_profile
delete_profile = _delete_profile

__all__ = [
    "get_profiles",
    "save_profile",
    "load_profile",
    "delete_profile",
]


