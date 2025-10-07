from __future__ import annotations
import os, sys, json, time, hashlib
from urllib import request, parse


def main() -> None:
    base = os.environ.get("BASE_URL", "http://127.0.0.1:5010")
    root = os.getcwd()
    sys.path.insert(0, root)

    idx = json.load(open(os.path.join(root, "ui_projects", "projects.json")))
    pid = idx.get("current") or (idx.get("projects") or [{}])[0].get("id")

    def http_post(path: str, items: list[tuple[str, str]], timeout_s: int = 120) -> tuple[int, str]:
        url = f"{base}{path}"
        body = parse.urlencode(items, doseq=True).encode()
        req = request.Request(url, data=body)  # data implies POST
        # Avoid header quoting issues in some shells; most servers accept form
        with request.urlopen(req, timeout=timeout_s) as r:
            return getattr(r, "status", 200), r.read().decode("utf-8", "ignore")

    def http_get_stream(url: str, max_bytes: int = 1024, timeout: int = 8) -> str:
        req = request.Request(url)
        with request.urlopen(req, timeout=timeout) as r:
            return r.read(max_bytes).decode("utf-8", "ignore")

    debug_run = os.path.join(root, "DEBUG_RUN.md")

    # Clear queue to ensure we only scan the specific endpoint
    try:
        http_post(f"/p/{pid}/queue/clear", [])
    except Exception:
        pass

    # Before drawer (should be empty or say No runs yet)
    st, html = http_post(f"/p/{pid}/sitemap/endpoint-runs", [("base", "https://example.com"), ("method", "GET"), ("path", "/ping")])
    with open(debug_run, "a", encoding="utf-8") as f:
        f.write("\n-- Before: Runs drawer\n")
        f.write((html or "")[:200] + "\n")

    # Add spec
    spec = {
        "openapi": "3.0.3",
        "info": {"title": "Demo API", "version": "1.0.0"},
        "servers": [{"url": "https://example.com"}],
        "paths": {"/ping": {"get": {"operationId": "ping", "responses": {"200": {"description": "ok"}}}}},
    }
    http_post(f"/p/{pid}/add", [("raw_text", json.dumps(spec)), ("input_type", "openapi")])

    # Queue endpoint
    http_post(f"/p/{pid}/queue_add_single", [("spec_id", "pasted://Demo API|1.0.0"), ("method", "GET"), ("path", "/ping")])

    # Fixed run id
    run_id = os.environ.get("RUN_ID", "run_TESTKEY_1")

    # SSE sample first (guaranteed start/done)
    sse_url = f"{base}/p/{pid}/nuclei/stream?run_id={run_id}&severity=critical&severity=high&severity=medium"
    try:
        sse = http_get_stream(sse_url, max_bytes=512, timeout=6)
    except Exception as _e:
        sse = "[no SSE data within timeout]"
    with open(debug_run, "a", encoding="utf-8") as f:
        f.write("-- SSE sample\n")
        f.write((sse or "") + "\n")

    # Then POST scan to persist run_doc and dossiers (larger timeout)
    st, body = http_post(
        f"/p/{pid}/nuclei/scan",
        [("severity", "critical"), ("severity", "high"), ("severity", "medium"), ("run_id", run_id)],
        timeout_s=180,
    )
    with open(debug_run, "a", encoding="utf-8") as f:
        f.write("-- Scan JSON (first240)\n")
        f.write((body or "")[:240] + "\n")

    # NDJSON first two lines
    art = os.path.join(root, "ui_projects", pid, "runs", f"{run_id}.nuclei.ndjson")
    if os.path.exists(art):
        head = ""
        with open(art, "r", encoding="utf-8") as af:
            head += af.readline()
            head += af.readline()
    else:
        head = "[empty]\n"
    with open(debug_run, "a", encoding="utf-8") as f:
        f.write("-- NDJSON first2\n")
        f.write(head + "\n")

    # After drawer (+ key proof)
    st, html = http_post(f"/p/{pid}/sitemap/endpoint-runs", [("base", "https://example.com"), ("method", "GET"), ("path", "/ping")], timeout_s=30)
    with open(debug_run, "a", encoding="utf-8") as f:
        f.write("-- After: Runs drawer\n")
        f.write((html or "")[:200] + "\n")

    # Dossier excerpt by canonical key
    from utils.endpoints import endpoint_key
    import re as _re

    key = endpoint_key("GET", "https://example.com", "/ping")
    safe = _re.sub(r"[^A-Za-z0-9._-]+", "_", key)
    dossier = os.path.join(root, "ui_projects", pid, "endpoints", f"{safe}.json")
    if os.path.exists(dossier):
        doc = json.load(open(dossier, "r", encoding="utf-8"))
        excerpt = {
            "key": key,
            "last_run": (doc.get("last_run") or {}).get("run_id") if isinstance(doc.get("last_run"), dict) else doc.get("last_run"),
            "runs_top": [r.get("run_id") for r in (doc.get("runs") or [])[:1]],
        }
        with open(debug_run, "a", encoding="utf-8") as f:
            f.write("-- Dossier excerpt\n")
            f.write(json.dumps(excerpt, ensure_ascii=False) + "\n")
    else:
        with open(debug_run, "a", encoding="utf-8") as f:
            f.write(f"-- Dossier missing for key: {key}\n")

    print("OK")


if __name__ == "__main__":
    main()


