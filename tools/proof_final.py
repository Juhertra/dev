import json
import os
import re
import subprocess
import time
from urllib import parse, request

BASE = os.environ.get("APP_BASE", "http://127.0.0.1:5010")

def ensure_server():
    for _ in range(60):
        try:
            request.urlopen(BASE+"/", timeout=0.5)
            return True
        except Exception:
            time.sleep(0.5)
    return False

def get_pid():
    override = os.environ.get("PROOF_PID")
    if override:
        return override
    idx = json.load(open("ui_projects/projects.json"))
    return idx.get("current") or (idx.get("projects") or [{}])[0].get("id")

def append(md: str):
    with open("DEBUG_RUN.md", "a", encoding="utf-8") as f:
        f.write(md)

def post(path: str, data: dict, timeout_s: float = 90.0):
    url = BASE + path
    body = parse.urlencode(data, doseq=True).encode()
    req = request.Request(url, data=body)
    with request.urlopen(req, timeout=timeout_s) as r:
        return getattr(r, 'status', 200), r.read().decode('utf-8', 'ignore')

def capture_sse(url: str, max_time: int = 10):
    try:
        cp = subprocess.run(["curl", "-sS", "-N", "--max-time", str(max_time), url], capture_output=True, text=True)
        txt = cp.stdout or ""
        lines = [ln for ln in (txt.splitlines() if txt else []) if ln.strip()]
        start = next((ln for ln in lines if ln.startswith("event: start")), "[no start]")
        done = next((ln for ln in lines if ln.startswith("event: done")), "[no done]")
        return start, done
    except Exception as e:
        return f"[sse error: {e}]", "[sse error]"

def safe_filename(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)

def main():
    ensure_server()
    pid = get_pid()
    append("\n## Phase 2 — Deterministic Cycle\n")

    # Before drawer
    st, html = post(f"/p/{pid}/sitemap/endpoint-runs", {"base":"https://example.com","method":"GET","path":"/ping"}, 20)
    append(f"Before Runs drawer: {st} excerpt: " + (html or "")[:200] + "\n")

    # Ensure demo spec present and queue single endpoint
    try:
        # Add Demo API spec if missing
        spec = {
            "openapi":"3.0.3","info":{"title":"Demo API","version":"1.0.0"},
            "servers":[{"url":"https://example.com"}],
            "paths":{"/ping":{"get":{"operationId":"ping","responses":{"200":{"description":"ok"}}}}}
        }
        post(f"/p/{pid}/add", {"raw_text": json.dumps(spec), "input_type":"openapi"}, 30)
    except Exception:
        pass
    try:
        post(f"/p/{pid}/queue/clear", {}, 10)
    except Exception:
        pass
    post(f"/p/{pid}/queue_add_single", {"spec_id":"pasted://Demo API|1.0.0","method":"GET","path":"/ping"}, 10)

    # SSE sample for fixed run id
    run_id = "run_PROOF_FINAL_1"
    start, done = capture_sse(f"{BASE}/p/{pid}/nuclei/stream?run_id={run_id}&severity=critical&severity=high&severity=medium&include_low_info=1", 10)
    append(f"SSE start line: {start}\nSSE done line: {done}\n")

    # Scan
    st, body = post(f"/p/{pid}/nuclei/scan", {"severity":"critical","severity":"high","severity":"medium","run_id":run_id,"include_low_info":"1"}, 180)
    append("Scan JSON head: "+ (body or "")[:240] + "\n")

    # Attempt second scan to prove single-executor guard
    try:
        st2, body2 = post(f"/p/{pid}/nuclei/scan", {"severity":"high","run_id":run_id}, 20)
        append("Second scan (same run_id): "+ (body2 or "")[:200] + "\n")
    except Exception as e:
        append(f"Second scan error: {e}\n")

    # Dossier by-key
    key = "GET https://example.com/ping"
    path = f"ui_projects/{pid}/endpoints/{safe_filename(key)}.json"
    if os.path.exists(path):
        append("Dossier path: "+path+"\n")
        with open(path, 'r', encoding='utf-8') as f:
            append("Dossier head: "+f.read(200)+"\n")
    else:
        append("Dossier missing: "+path+"\n")

    # After drawer
    st, html = post(f"/p/{pid}/sitemap/endpoint-runs", {"base":"https://example.com","method":"GET","path":"/ping"}, 20)
    append(f"After Runs drawer: {st} excerpt: "+(html or "")[:200]+"\n")

    # Log tails
    try:
        lines = open("DEBUG_SERVER_5010.log","r",encoding="utf-8",errors="ignore").read().splitlines()
        w = [l for l in lines if "DOSSIER_WRITE" in l][-2:]
        r = [l for l in lines if "DOSSIER_READ" in l][-1:]
        e = [l for l in lines if "[EXEC]" in l][-2:]
        for l in w: append("LOG: "+l+"\n")
        for l in r: append("LOG: "+l+"\n")
        for l in e: append("LOG: "+l+"\n")
    except Exception:
        pass

if __name__ == "__main__":
    main()


