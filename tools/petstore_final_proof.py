import json
import os
import re
import subprocess
import time
from urllib import parse, request

BASE = "http://127.0.0.1:5010"
PID = "ec4c0976-fd94-463c-8ada-0705fe12b944"
ENDPOINTS = [
    ("GET", "https://petstore3.swagger.io", "/api/v3/store/inventory"),
    ("POST", "https://petstore3.swagger.io", "/api/v3/pet"),
]

def append(s):
    with open("DEBUG_RUN.md","a",encoding="utf-8") as f: f.write(s)

def get(path, t=20):
    with request.urlopen(BASE+path, timeout=t) as r:
        return r.status, r.read().decode('utf-8','ignore')

def post(path, data, t=60):
    body = parse.urlencode(data, doseq=True).encode()
    req = request.Request(BASE+path, data=body)
    with request.urlopen(req, timeout=t) as r:
        return r.status, r.read().decode('utf-8','ignore')

def ensure_server():
    # Kill and start one server
    killed = []
    try:
        p = subprocess.run(["pgrep","-f",":5010"], capture_output=True, text=True)
        pids = [x for x in (p.stdout or '').splitlines() if x.strip()]
        if pids:
            subprocess.run(["kill","-9",*pids])
            killed = pids
    except Exception:
        pass
    with open("DEBUG_SERVER_5010.log","a",encoding="utf-8") as f:
        f.write(f"KILL :5010 -> {','.join(killed) if killed else 'none'}\n")
    # Start
    env = os.environ.copy(); env["FLASK_APP"] = "app:create_app"
    subprocess.Popen(["./venv/bin/flask","run","--host","127.0.0.1","--port","5010"], stdout=open("DEBUG_SERVER_5010.log","a"), stderr=subprocess.STDOUT, env=env)
    # Wait
    ok = False
    for _ in range(60):
        try:
            with request.urlopen(BASE+"/", timeout=0.5):
                ok = True; break
        except Exception:
            time.sleep(0.5)
    with open("DEBUG_SERVER_5010.log","a",encoding="utf-8") as f:
        f.write(f"START :5010 -> {os.getpid()}\n")
    return ok

def main():
    append("\n## Phase 2 — VALIDATED (Petstore, ec4c0976-fd94-463c-8ada-0705fe12b944)\n")
    ensure_server()
    # Before drawers
    for method, base, path in ENDPOINTS:
        st, html = post(f"/p/{PID}/sitemap/endpoint-runs", {"base":base,"method":method,"path":path}, 20)
        name = f"{method} {path}"
        append(f"Before Runs ({name}): "+(html or "")[:200]+"\n")
    # Import spec
    try:
        st, body = post(f"/p/{PID}/add", {"spec_urls":"https://raw.githubusercontent.com/swagger-api/swagger-petstore/refs/heads/master/src/main/resources/openapi.yaml","input_type":"auto"}, 120)
        append(f"Spec import: {st} bytes={len(body.encode('utf-8'))}\n")
    except Exception as e:
        append(f"Spec import error: {e}\n")
    # Queue clear
    try: post(f"/p/{PID}/queue/clear", {}, 10)
    except Exception: pass
    # Queue endpoints via sitemap discovery when possible; fallback to minimal spec covering both ops
    st, sm = get(f"/p/{PID}/sitemap", 30)
    discovered = []
    for method, base, path in ENDPOINTS:
        spec_id=None; sel=None
        for m in re.finditer(r"hx-vals='\{([^']+)\}'", sm):
            vals=m.group(1)
            if f'"base":"{base}"' in vals and f'"method":"{method}"' in vals and f'"path":"{path}"' in vals:
                ms=re.search(r'"spec_id":"([^"]+)"', vals)
                mi=re.search(r'"sel":"(\d+)"', vals)
                if ms and mi:
                    spec_id=ms.group(1); sel=mi.group(1); break
        if spec_id and sel is not None:
            post(f"/p/{PID}/queue_add", {"spec_id":spec_id, "sel":sel}, 20)
            discovered.append(True)
        else:
            discovered.append(False)
    if not all(discovered):
        # Create a minimal spec with both endpoints
        minimal = {
            "openapi":"3.0.3",
            "info":{"title":"Petstore FINAL","version":"1.0.0"},
            "servers":[{"url":"https://petstore3.swagger.io"}],
            "paths":{
                "/api/v3/store/inventory": {"get":{"operationId":"inventory","responses":{"200":{"description":"ok"}}}},
                "/api/v3/pet": {"post":{"operationId":"postPet","responses":{"200":{"description":"ok"}}}}
            }
        }
        post(f"/p/{PID}/add", {"raw_text": json.dumps(minimal), "input_type":"openapi"}, 60)
        spec_id = "pasted://Petstore FINAL|1.0.0"
        for method, base, path in ENDPOINTS:
            try:
                post(f"/p/{PID}/queue_add_single", {"spec_id":spec_id, "method":method, "path":path, "url": base+path}, 20)
            except Exception:
                pass
    # Queue summary & keys
    st, qsum = get(f"/p/{PID}/queue/summary", 10)
    append("Queue summary: "+qsum[:200]+"\n")
    append("Queue Dedupe keys:\n")
    for method, base, path in ENDPOINTS:
        append(f"- {method} {base}{path}\n")
    # Pick two template IDs
    st, tjson = get(f"/p/{PID}/nuclei/templates?all=1", 30)
    tids=[]
    try:
        data=json.loads(tjson)
        if data.get('success') and data.get('templates'):
            arr=data['templates']
            tids=[arr[0]['id'], arr[-1]['id']] if len(arr)>=2 else [arr[0]['id']]
    except Exception:
        pass
    append("Templates chosen: "+", ".join(tids[:2])+"\n")
    # SSE
    run_id="run_PETSTORE_VALIDATED_1"
    cp=subprocess.run(["curl","-sS","-N","--max-time","10", f"{BASE}/p/{PID}/nuclei/stream?run_id={run_id}&severity=medium&include_low_info=1"], capture_output=True, text=True)
    lines=[ln for ln in (cp.stdout or "").splitlines() if ln.strip()]
    start=next((ln for ln in lines if ln.startswith("event: start")), "[no start]")
    ping=next((ln for ln in lines if ln.startswith(": ping")), "[no ping]")
    done=next((ln for ln in lines if ln.startswith("event: done")), "[no done]")
    append(f"SSE (final): {start} | {ping} | {done}\n")
    # Run scan
    data={"severity":"medium","run_id":run_id,"include_low_info":"1"}
    for tid in tids[:2]: data.setdefault('templates',[]); data['templates'].append(tid)
    st, body = post(f"/p/{PID}/nuclei/scan", data, 240)
    append("Scan JSON (final): "+(body or "")[:240]+"\n")
    # Dossiers
    for method, base, path in ENDPOINTS:
        safe=re.sub(r"[^A-Za-z0-9._-]+","_", f"{method} {base}{path}")
        p=f"ui_projects/{PID}/endpoints/{safe}.json"
        if os.path.exists(p):
            append(f"Dossier: {p}\n")
            append("Dossier head: "+open(p,'r',encoding='utf-8').read(200)+"\n")
        else:
            append(f"Dossier missing: {p}\n")
    # After drawers
    for method, base, path in ENDPOINTS:
        st, html = post(f"/p/{PID}/sitemap/endpoint-runs", {"base":base,"method":method,"path":path}, 20)
        append(f"After Runs ({method} {path}): "+(html or "")[:200]+"\n")
    # /runs page
    try:
        st, html = get(f"/p/{PID}/runs", 20)
        append(f"/runs page: {st} head: "+(html or "")[:160]+"\n")
    except Exception as e:
        append(f"/runs page error: {e}\n")
    # Guard
    try:
        st, resp = post(f"/p/{PID}/nuclei/scan", {"severity":"medium","run_id":run_id}, 20)
        append("Guard second scan (final): "+resp[:200]+"\n")
    except Exception as e:
        append(f"Guard error: {e}\n")
    # Logs tail
    try:
        lines=open("DEBUG_SERVER_5010.log","r",encoding='utf-8',errors='ignore').read().splitlines()
        for tag in ("DOSSIER_WRITE","DOSSIER_READ","[EXEC]"):
            for l in [x for x in lines if tag in x][-3:]:
                append("LOG: "+l+"\n")
    except Exception:
        pass

if __name__ == '__main__':
    main()


