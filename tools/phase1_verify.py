from __future__ import annotations
import os
import re
import json
import socket
import http.client
import importlib.util
import sys
from typing import Any, Dict, List, Tuple


def detect_base() -> Tuple[str | None, str | None]:
    for port in (5010, 5011):
        s = socket.socket()
        s.settimeout(0.3)
        try:
            s.connect(("127.0.0.1", port))
            s.close()
            return f"http://127.0.0.1:{port}", f"DEBUG_SERVER_{port}.log"
        except Exception:
            try:
                s.close()
            except Exception:
                pass
    return None, None


def http_fetch(base: str, path: str, method: str = "GET") -> Tuple[int | None, Dict[str, str] | None, str | None]:
    m = re.match(r"^http://([^:/]+):(\d+)$", base)
    if not m:
        return None, None, None
    host, port = m.group(1), int(m.group(2))
    conn = http.client.HTTPConnection(host, port, timeout=6)
    try:
        conn.request(method, path)
        resp = conn.getresponse()
        headers = {k: v for k, v in resp.getheaders()}
        body = resp.read().decode("utf-8", "ignore")
        conn.close()
        return resp.status, headers, body
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return None, None, None


def load_pid(root: str) -> str | None:
    idx_path = os.path.join(root, "ui_projects", "projects.json")
    if not os.path.exists(idx_path):
        return None
    idx = json.load(open(idx_path))
    return idx.get("current") or (idx.get("projects") or [{}])[0].get("id")


def route_map_from_top_level_app(root: str) -> List[str]:
    app_py = os.path.join(root, "app.py")
    spec = importlib.util.spec_from_file_location("_legacy_app_for_map", app_py)
    if not spec or not spec.loader:
        return []
    # Ensure project root is on sys.path so absolute imports inside app.py work
    if root not in sys.path:
        sys.path.insert(0, root)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    app = getattr(mod, "app", None)
    if not app:
        return []
    return sorted([f"{sorted(list(r.methods))}-{r.rule}" for r in app.url_map.iter_rules()])


def route_map_from_new_factory() -> List[str]:
    from app import create_app  # type: ignore
    app = create_app()
    return sorted([f"{sorted(list(r.methods))}-{r.rule}" for r in app.url_map.iter_rules()])


def main() -> None:
    root = os.getcwd()
    base, log_file = detect_base()
    pid = load_pid(root) or ""

    legacy = route_map_from_top_level_app(root)
    newmap = route_map_from_new_factory()
    before_set, after_set = set(legacy), set(newmap)
    added = sorted(list(after_set - before_set))
    removed = sorted(list(before_set - after_set))

    pages = [
        f"/p/{pid}",
        f"/p/{pid}/sitemap",
        f"/p/{pid}/queue",
        f"/p/{pid}/active-testing",
        f"/p/{pid}/findings",
        f"/p/{pid}/sends",
    ]

    page_results: List[Dict[str, Any]] = []
    if base:
        for p in pages:
            st_h, _, _ = http_fetch(base, p, method="HEAD")
            st_g, _, body = http_fetch(base, p, method="GET")
            first160 = (body or "")[:160] if isinstance(body, str) else ""
            gi = len(re.findall(r'id\s*=\s*"global-indicator"', body or "", re.I))
            pb = len(re.findall(r'id\s*=\s*"panel-body"', body or "", re.I))
            page_results.append({
                "path": p,
                "head_status": st_h,
                "get_status": st_g,
                "first160": first160,
                "global_indicator_count": gi,
                "panel_body_count": pb,
            })

    # Drawer probes (HTMX): collect hx-post URLs from the browser page
    htmx_results: List[Dict[str, Any]] = []
    if base and pid:
        st, _, body = http_fetch(base, f"/p/{pid}")
        posts: List[str] = []
        if isinstance(body, str):
            for m in re.finditer(r'hx-post=\"([^\"]+)\"', body):
                u = m.group(1)
                if u.startswith("/") and f"/p/{pid}/" in u:
                    posts.append(u)
        posts = list(dict.fromkeys(posts))[:3]
        for u in posts:
            stp, _, b = http_fetch(base, u, method="POST")
            htmx_results.append({
                "url": u,
                "status": stp,
                "first160": (b or "")[:160] if isinstance(b, str) else "",
            })

    # Sample logs (last 3 lines with request_id & duration_ms)
    log_tail: List[str] = []
    if log_file and os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as fh:
                lines = fh.readlines()[-400:]
            for line in reversed(lines):
                if "request_id" in line and "duration_ms" in line:
                    log_tail.append(line.strip())
                if len(log_tail) >= 3:
                    break
        except Exception:
            pass

    # Write DEBUG_RUN.md
    out: List[str] = []
    out.append(f"Base URL: {base}\nPID: {pid}\nLog: {log_file}\n")
    out.append("\nRoute map diff (before vs after)\n-------------------------------\n")
    out.append(f"Added: {added}\nRemoved: {removed}\n")
    out.append("\nPages\n-----\n")
    for pr in page_results:
        out.append(
            f"{pr['path']}: HEAD={pr['head_status']} GET={pr['get_status']}\n"
            f"first160: {pr['first160']}\n"
            f"#global-indicator: {pr['global_indicator_count']}  #panel-body: {pr['panel_body_count']}\n"
        )
    out.append("\nDrawer (HTMX) probes\n--------------------\n")
    for hr in htmx_results:
        out.append(f"{hr['url']}: status={hr['status']} first160: {hr['first160']}")
    out.append("\n\nSample JSON logs\n----------------\n")
    for ln in log_tail:
        out.append(ln)
    with open("DEBUG_RUN.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))


if __name__ == "__main__":
    main()


