"""Nuclei tool adapter (Phase 1). Pass-through to existing integration."""

from __future__ import annotations
from typing import Any, Dict

from .registry import Tool


class NucleiTool:
    name = "nuclei"

    def __init__(self) -> None:
        from nuclei_integration import nuclei_integration  # lazy import
        self._n = nuclei_integration

    def status(self) -> Dict[str, Any]:
        try:
            return {"success": True, "status": self._n.check_nuclei_status()}
        except Exception as e:  # pragma: no cover
            return {"success": False, "error": str(e)}

    def update(self) -> Dict[str, Any]:
        try:
            ok, msg = self._n.update_templates()
            return {"success": ok, "message": msg}
        except Exception as e:  # pragma: no cover
            return {"success": False, "error": str(e)}

    def configure(self, **opts) -> Dict[str, Any]:  # placeholder
        return {"success": True, "applied": opts}

    def reindex(self) -> Dict[str, Any]:
        try:
            # Force index rebuild
            self._n.nuclei._index_built = False
            self._n.nuclei._build_index()
            items = self._n.nuclei.list_templates(all_templates=True)
            return {"success": True, "count": len(items)}
        except Exception as e:  # pragma: no cover
            return {"success": False, "error": str(e)}


__all__ = ["NucleiTool"]


