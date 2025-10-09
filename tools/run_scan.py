from __future__ import annotations

import json
import os
import time
from urllib import parse, request

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:5010")
IDX = json.load(open(os.path.join(os.path.dirname(__file__), "..", "ui_projects", "projects.json")))
PID = IDX.get("current") or (IDX.get("projects") or [{}])[0].get("id")


def http_get(path: str) -> tuple[int, str]:
    url = f"{BASE}{path}"
    resp = request.urlopen(url, timeout=20)
    try:
        status = getattr(resp, "status", 200)
    except Exception:
        status = 200
    body = resp.read().decode("utf-8", "ignore")
    try:
        resp.close()
    except Exception:
        pass
    return status, body


def http_post(path: str, items: list[tuple[str, str]]) -> tuple[int, str]:
    url = f"{BASE}{path}"
    body = parse.urlencode(items, doseq=True).encode()
    req = request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    resp = request.urlopen(req, timeout=60)
    try:
        status = getattr(resp, "status", 200)
    except Exception:
        status = 200
    body_text = resp.read().decode("utf-8", "ignore")
    try:
        resp.close()
    except Exception:
        pass
    return status, body_text


def ensure_spec_and_queue() -> str:
    # Add minimal OpenAPI via raw_text
    openapi = {
        "openapi": "3.0.3",
        "info": {"title": "Demo API", "version": "1.0.0"},
        "servers": [{"url": "https://example.com"}],
        "paths": {"/ping": {"get": {"operationId": "ping", "responses": {"200": {"description": "ok"}}}}},
    }
    raw_text = json.dumps(openapi)
    http_post(f"/p/{PID}/add", [("raw_text", raw_text), ("input_type", "openapi")])
    # Queue first op
    spec_id = "pasted://Demo API|1.0.0"
    http_post(f"/p/{PID}/queue_add", [("spec_id", spec_id), ("sel", "0")])
    return spec_id


def pick_templates(n: int = 2) -> list[str]:
    st, body = http_get(f"/p/{PID}/nuclei/templates?all=1")
    try:
        data = json.loads(body)
        if data.get("success"):
            tids = [t.get("id") for t in data.get("templates", []) if t.get("id")]
            return tids[:n] if tids else []
    except Exception:
        pass
    # Fallback to likely IDs
    return ["http-default-login", "apache-server-status"][:n]


def run_scan() -> dict:
    run_id = f"run_{int(time.time())}"
    templates = pick_templates(2)
    severities = ["critical", "high", "medium"]
    form = [("templates", t) for t in templates] + [("severity", s) for s in severities] + [("run_id", run_id)]
    status, body = http_post(f"/p/{PID}/nuclei/scan", form)
    try:
        data = json.loads(body)
    except Exception:
        data = {"raw": body}
    data["http_status"] = status
    data["run_id"] = run_id
    return data


def sse_preview(run_id: str, limit_events: int = 5) -> list[str]:
    # Minimal preview via urllib (blocking): fetch a small chunk
    url = f"{BASE}/p/{PID}/nuclei/stream?run_id={run_id}"
    try:
        resp = request.urlopen(url, timeout=10)
        raw = resp.read(4096).decode("utf-8", "ignore")
        resp.close()
        # Extract a few SSE lines
        lines = [ln for ln in raw.splitlines() if ln.strip()][:limit_events]
        return lines
    except Exception as e:
        return [f"sse_error: {e}"]


def append_debug_run(entries: list[tuple[str, str]]):
    with open("DEBUG_RUN.md", "a", encoding="utf-8") as f:
        for title, text in entries:
            f.write(f"{title}\n{text}\n")


def main():
    ensure_spec_and_queue()
    # Drawer: ensure Runs works after scan, so run scan first
    data = run_scan()
    run_id = data.get("run_id")
    artifact = data.get("artifact_path")
    nd_head = []
    if artifact and os.path.exists(artifact):
        with open(artifact, "r", encoding="utf-8", errors="ignore") as fh:
            try:
                nd_head.append(next(fh).strip())
                nd_head.append(next(fh).strip())
            except Exception:
                pass
    sse_lines = sse_preview(run_id)

    # Append proof
    out = []
    out.append(("\nActive Testing (programmatic)\n-----------------------------\n",
                f"Scan JSON (status={data.get('http_status')}): {json.dumps(data)[:800]}\nNDJSON first lines: {nd_head}\nSSE sample: {sse_lines[:3]}\n"))

    # Runs drawer now should be non-empty
    st_r, body_r = http_post(f"/p/{PID}/sitemap/endpoint-runs", [("base","https://example.com"),("method","GET"),("path","/ping")])
    out.append(("Site Map Runs drawer after scan\n--------------------------------\n",
                f"status={st_r} excerpt: {(body_r or '')[:200]}\n"))

    # Run JSON proof if created
    runs_dir = os.path.join("ui_projects", PID, "runs")
    sample_run = None
    if os.path.isdir(runs_dir):
        for fn in os.listdir(runs_dir):
            if fn.endswith('.json'):
                sample_run = os.path.join(runs_dir, fn)
                break
    if sample_run:
        try:
            run_doc = json.load(open(sample_run))
            keys = list(run_doc.keys())
            stats = run_doc.get('stats')
            out.append(("Run JSON proof\n---------------\n",
                        f"file={sample_run} keys={keys} stats={stats}\n"))
        except Exception:
            pass
    append_debug_run(out)


if __name__ == "__main__":
    main()


