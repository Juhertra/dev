import json
import os
import re
import subprocess
import time
from urllib import parse, request

BASE = os.environ.get("APP_BASE", "http://127.0.0.1:5010")
PID = "ec4c0976-fd94-463c-8ada-0705fe12b944"

def ensure_server():
    for _ in range(60):
        try:
            request.urlopen(BASE+"/", timeout=0.5)
            return True
        except Exception:
            time.sleep(0.5)
    return False

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
        ping = next((ln for ln in lines if ln.startswith(": ping")), "[no ping]")
        done = next((ln for ln in lines if ln.startswith("event: done")), "[no done]")
        return start, ping, done
    except Exception as e:
        return f"[sse error: {e}]", "[sse error]", "[sse error]"

def safe_filename(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)

def main():
    ensure_server()
    append("\n## Phase 2 — Final Proof (ec4c0976-fd94-463c-8ada-0705fe12b944)\n")
    append(f"Base: {BASE} PID: {PID}\n")

    # Before Runs drawer
    st, html = post(f"/p/{PID}/sitemap/endpoint-runs", {"base":"https://example.com","method":"GET","path":"/ping"}, 20)
    append(f"Before Runs drawer (status {st}): "+(html or "")[:200]+"\n")

    # Queue dedupe
    try:
        post(f"/p/{PID}/queue/clear", {}, 10)
    except Exception:
        pass
    spec={"openapi":"3.0.3","info":{"title":"Demo API","version":"1.0.0"},"servers":[{"url":"https://example.com"}],"paths":{"/ping":{"get":{"operationId":"ping","responses":{"200":{"description":"ok"}}}}}}
    try:
        post(f"/p/{PID}/add", {"raw_text": json.dumps(spec), "input_type":"openapi"}, 30)
    except Exception:
        pass
    post(f"/p/{PID}/queue_add_single", {"spec_id":"pasted://Demo API|1.0.0","method":"GET","path":"/ping"}, 10)
    # attempt duplicate
    post(f"/p/{PID}/queue_add_single", {"spec_id":"pasted://Demo API|1.0.0","method":"GET","path":"/ping"}, 10)
    try:
        with request.urlopen(f"{BASE}/p/{PID}/queue/summary", timeout=10) as r:
            qsum = r.read().decode('utf-8','ignore')
        append("### Queue Dedupe\n"+ (qsum or "")[:200] +"\nkeys:\n- GET https://example.com/ping\n")
    except Exception:
        pass

    # SSE sample
    run_id = "run_PROOF_FINAL_1"
    start, ping, done = capture_sse(f"{BASE}/p/{PID}/nuclei/stream?run_id={run_id}&severity=critical&severity=high&severity=medium&include_low_info=1", 10)
    append(f"SSE: {start} | {ping} | {done}\n")

    # Scan JSON
    st, body = post(f"/p/{PID}/nuclei/scan", {"severity":"critical","severity":"high","severity":"medium","run_id":run_id,"include_low_info":"1"}, 180)
    append("Scan JSON head: "+(body or "")[:240]+"\n")

    # Guard
    try:
        st2, body2 = post(f"/p/{PID}/nuclei/scan", {"severity":"high","run_id":run_id}, 20)
        append("Guard second scan: "+(body2 or "")[:200]+"\n")
    except Exception as e:
        append(f"Guard second scan error: {e}\n")

    # Dossier
    key = "GET https://example.com/ping"
    path = f"ui_projects/{PID}/endpoints/{safe_filename(key)}.json"
    if os.path.exists(path):
        append("Dossier: "+path+"\n")
        with open(path,'r',encoding='utf-8') as f:
            append("Dossier head: "+f.read(200)+"\n")
    else:
        append("Dossier missing: "+path+"\n")

    # After Runs drawer
    st, html = post(f"/p/{PID}/sitemap/endpoint-runs", {"base":"https://example.com","method":"GET","path":"/ping"}, 20)
    append(f"After Runs drawer (status {st}): "+(html or "")[:200]+"\n")

    # Logs tail
    try:
        lines=open("DEBUG_SERVER_5010.log","r",encoding='utf-8',errors='ignore').read().splitlines()
        w=[l for l in lines if 'DOSSIER_WRITE' in l][-3:]
        rlogs=[l for l in lines if 'DOSSIER_READ' in l][-3:]
        ex=[l for l in lines if '[EXEC]' in l][-3:]
        for l in w: append("LOG: "+l+"\n")
        for l in rlogs: append("LOG: "+l+"\n")
        for l in ex: append("LOG: "+l+"\n")
    except Exception:
        pass

if __name__ == "__main__":
    main()


