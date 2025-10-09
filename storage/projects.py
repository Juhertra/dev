"""Projects storage wrappers delegating to existing store.py (Phase 1)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from store import (
        create_project as _create_project,
    )
    from store import (
        delete_project as _delete_project,
    )
    from store import (
        get_current_project_id as _get_current_project_id,
    )
    from store import (
        get_project_name as _get_project_name,
    )
    from store import (
        list_projects as _list_projects,
    )
    from store import (
        rename_project as _rename_project,
    )
    from store import (
        set_current_project_id as _set_current_project_id,
    )
except Exception as _e:  # pragma: no cover
    # Fallback no-ops to avoid crashes during early wiring
    def _list_projects() -> List[Dict[str, Any]]: return []
    def _get_current_project_id() -> Optional[str]: return None
    def _set_current_project_id(pid: Optional[str]) -> None: return None
    def _create_project(name: str) -> str: return ""
    def _rename_project(pid: str, name: str) -> None: return None
    def _delete_project(pid: str) -> None: return None
    def _get_project_name(pid: str) -> str: return "Project"


list_projects = _list_projects
get_current_project_id = _get_current_project_id
set_current_project_id = _set_current_project_id
create_project = _create_project
rename_project = _rename_project
delete_project = _delete_project
get_project_name = _get_project_name

__all__ = [
    "list_projects",
    "get_current_project_id",
    "set_current_project_id",
    "create_project",
    "rename_project",
    "delete_project",
    "get_project_name",
]


