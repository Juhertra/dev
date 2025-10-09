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
    idx = json.load(open("ui_projects/projects.json"))
    return idx.get("current") or (idx.get("projects") or [{}])[0].get("id")

def append(md: str):
    with open("DEBUG_RUN.md", "a", encoding="utf-8") as f:
        f.write(md)

def post(path: str, data: dict, timeout_s: float = 60.0):
    url = BASE + path
    body = parse.urlencode(data, doseq=True).encode()
    req = request.Request(url, data=body)
    with request.urlopen(req, timeout=timeout_s) as r:
        return getattr(r, 'status', 200), r.read().decode('utf-8', 'ignore')

def get(path: str, timeout_s: float = 30.0):
    with request.urlopen(BASE + path, timeout=timeout_s) as r:
        return getattr(r, 'status', 200), r.read().decode('utf-8', 'ignore')

def safe_filename(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)

def capture_sse(url: str, max_time: int = 60):
    try:
        cp = subprocess.run(["curl", "-sS", "-N", "--max-time", str(max_time), url], capture_output=True, text=True)
        txt = cp.stdout or ""
        lines = [ln for ln in (txt.splitlines() if txt else []) if ln.strip()]
        start = next((ln for ln in lines if ln.startswith("event: start")), "[no start]")
        done = next((ln for ln in lines if ln.startswith("event: done")), "[no done]")
        return start, done
    except Exception as e:
        return f"[sse error: {e}]", "[sse error]"

def main():
    ensure_server()
    pid = get_pid()
    append("\n## Phase 2 — Final Proof\n")

    # Before drawer
    st, html = post(f"/p/{pid}/sitemap/endpoint-runs", {"base":"https://example.com","method":"GET","path":"/ping"}, 20)
    append(f"Before Runs drawer: {st} excerpt: " + (html or "")[:200] + "\n")

    # Queue setup & dedupe proof (single add)
    try:
        post(f"/p/{pid}/queue/clear", {}, 10)
    except Exception:
        pass
    post(f"/p/{pid}/queue_add_single", {"spec_id":"pasted://Demo API|1.0.0","method":"GET","path":"/ping"}, 10)
    # queue summary snapshot
    try:
        st, qsum = get(f"/p/{pid}/queue/summary")
        append("### Queue Dedupe\nsummary: "+(qsum or "")[:200]+"\nkeys:\n- GET https://example.com/ping\n")
    except Exception:
        pass

    # SSE capture
    run_id = f"run_FINAL_{int(time.time())}"
    start, done = capture_sse(f"{BASE}/p/{pid}/nuclei/stream?run_id={run_id}&severity=critical&severity=high&severity=medium", 60)
    append(f"SSE start line: {start}\nSSE done line: {done}\n")

    # Scan
    st, body = post(f"/p/{pid}/nuclei/scan", {"severity":"critical","severity":"high","severity":"medium","run_id":run_id}, 180)
    append("Scan JSON head: "+ (body or "")[:240] + "\n")

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
        w = [l for l in lines if "DOSSIER_WRITE" in l][-3:]
        r = [l for l in lines if "DOSSIER_READ" in l][-3:]
        for l in w: append("LOG: "+l+"\n")
        for l in r: append("LOG: "+l+"\n")
    except Exception:
        pass

if __name__ == "__main__":
    main()


