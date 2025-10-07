from typing import Any, Dict


def build_endpoint_preview(base: str, method: str, path: str) -> Dict[str, Any]:
    """Best-effort endpoint preview context for drawer templates.

    Keeps structure compatible with existing op preview templates; callers can
    pass fields through to templates like drawer_endpoint_preview.html.
    """
    base = base or ""
    path = path or ""
    method = (method or "GET").upper()
    url = f"{base}{path}"
    curl = f"curl -i -X {method} '{url}'"
    return {
        "base": base,
        "method": method,
        "path": path,
        "url": url,
        "curl": curl,
        "request_headers": {},
        "request_body": "",
        "response_headers": {},
        "response_body": "",
        "status": None,
    }


