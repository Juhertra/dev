"""
Pydantic v2 model for findings (validation only in Phase 1).
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
        def model_dump(self) -> Dict[str, Any]:
            return self.__dict__


class FindingDoc(BaseModel):
    id: Optional[str] = None
    pid: Optional[str] = None
    version: Optional[str] = None
    ts: Optional[str] = None
    title: Optional[str] = None
    severity: Optional[str] = None
    detector_id: Optional[str] = None
    owasp: Optional[str] = None
    owasp_api: Optional[str] = None
    cwe: Optional[str] = None
    detail: Optional[str] = None
    evidence: Optional[str] = None
    match: Optional[str] = None
    tags: Optional[List[str]] = None
    subcategory: Optional[str] = None
    confidence: Optional[int] = None
    method: Optional[str] = None
    url: Optional[str] = None
    status: Optional[int] = None
    req: Optional[Dict[str, Any]] = None
    res: Optional[Dict[str, Any]] = None


__all__ = ["FindingDoc"]


