"""
Pydantic v2 model for run documents (validation only in Phase 1).
If pydantic is unavailable, provide a minimal shim to avoid runtime errors.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel
except Exception:
    class BaseModel:  # type: ignore
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)
        def model_dump(self) -> Dict[str, Any]:  # mimic pydantic v2
            return self.__dict__


class RunStats(BaseModel):
    findings: Optional[int] = None
    by_severity: Optional[Dict[str, int]] = None
    worst: Optional[str] = None


class RunDoc(BaseModel):
    run_id: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    initiator: Optional[Dict[str, Any]] = None
    provenance: Optional[Dict[str, Any]] = None
    targets: Optional[List[Dict[str, Any]]] = None
    stats: Optional[Dict[str, Any]] = None
    results: Optional[List[Dict[str, Any]]] = None
    artifact: Optional[str] = None
    artifact_path: Optional[str] = None


__all__ = ["RunDoc", "RunStats"]


