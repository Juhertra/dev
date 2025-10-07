import os, re, json, time, subprocess
from urllib import request, parse

BASE = os.environ.get("APP_BASE", "http://127.0.0.1:5010")
PID = "ec4c0976-fd94-463c-8ada-0705fe12b944"
METHOD = "GET"
BASE_URL = "https://petstore3.swagger.io"
PATH = "/api/v3/store/inventory"
KEY = f"{METHOD} {BASE_URL}{PATH}"
PATH2 = "/api/v3/pet/findByStatus?status=available"
KEY2 = f"{METHOD} {BASE_URL}{PATH2}"

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

def get(path: str, timeout_s: float = 20.0):
    with request.urlopen(BASE+path, timeout=timeout_s) as r:
        return r.status, r.read().decode('utf-8','ignore')

def post(path: str, data: dict, timeout_s: float = 90.0):
    body = parse.urlencode(data, doseq=True).encode()
    req = request.Request(BASE+path, data=body)
    with request.urlopen(req, timeout=timeout_s) as r:
        return r.status, r.read().decode('utf-8','ignore')

def find_spec_sel_for_endpoint(html: str, base_url: str, method: str, path: str):
    # Scan lines to find a preview hx-vals with base/method/path; then capture nearest following spec_id/sel hx-vals
    lines = html.splitlines()
    target_preview = f'"base":"{base_url}"' in html and f'"method":"{method}"' and f'"path":"{path}"'
    spec_id = None
    sel = None
    for i, line in enumerate(lines):
        if 'hx-vals=' in line and '"base":' in line and '"method":' in line and '"path":' in line:
            if base_url in line and method in line and path in line:
                # Look ahead a few lines for spec_id/sel
                for j in range(i, min(i+12, len(lines))):
                    lj = lines[j]
                    if 'hx-vals=' in lj and '"spec_id":' in lj and '"sel":' in lj:
                        ms = re.search(r'"spec_id":"([^"]+)"', lj)
                        mi = re.search(r'"sel":"(\d+)"', lj)
                        if ms and mi:
                            spec_id = ms.group(1)
                            sel = mi.group(1)
                            return spec_id, sel
    return None, None

def capture_sse(run_id: str, max_time: int = 10):
    try:
        cp = subprocess.run([
            "curl", "-sS", "-N", "--max-time", str(max_time),
            f"{BASE}/p/{PID}/nuclei/stream?run_id={run_id}&severity=critical&severity=high&severity=medium&include_low_info=1"
        ], capture_output=True, text=True)
        txt = cp.stdout or ""
        lines = [ln for ln in (txt.splitlines() if txt else []) if ln.strip()]
        start = next((ln for ln in lines if ln.startswith("event: start")), "[no start]")
        ping = next((ln for ln in lines if ln.startswith(": ping")), "[no ping]")
        done = next((ln for ln in lines if ln.startswith("event: done")), "[no done]")
        return start, ping, done
    except Exception as e:
        return f"[sse error: {e}]", "[sse error]", "[sse error]"

def main():
    ensure_server()
    append("\n## Phase 2 — Final Proof (Petstore) – FIXED\n")
    append(f"PID: {PID}  Base: {BASE}  Project: {PID}\n")

    # Before drawer
    st, html = post(f"/p/{PID}/sitemap/endpoint-runs", {"base":BASE_URL,"method":METHOD,"path":PATH}, 20)
    append(f"Before Runs drawer: (status {st}) "+ (html or "")[:200] +"\n")

    # Discover spec/sel from sitemap; if not present, add Petstore spec (YAML raw_text fallback)
    st, sm = get(f"/p/{PID}/sitemap", 30)
    spec_id, sel = find_spec_sel_for_endpoint(sm, BASE_URL, METHOD, PATH)
    if not spec_id:
        try:
            # Try URL import first
            post(f"/p/{PID}/add", {"spec_urls":"https://raw.githubusercontent.com/swagger-api/swagger-petstore/refs/heads/master/src/main/resources/openapi.yaml","input_type":"auto"}, 60)
        except Exception:
            pass
        try:
            # Fallback: fetch YAML and POST as raw_text
            import urllib.request as _rq
            y = _rq.urlopen("https://raw.githubusercontent.com/swagger-api/swagger-petstore/refs/heads/master/src/main/resources/openapi.yaml", timeout=30).read().decode('utf-8','ignore')
            post(f"/p/{PID}/add", {"raw_text": y, "input_type":"openapi"}, 60)
            st, sm = get(f"/p/{PID}/sitemap", 30)
            spec_id, sel = find_spec_sel_for_endpoint(sm, BASE_URL, METHOD, PATH)
        except Exception:
            pass
    if not spec_id:
        # Last resort: add a minimal OAS with just the inventory endpoint
        minimal_spec = {
            "openapi":"3.0.3",
            "info":{"title":"Petstore Proof","version":"1.0.0"},
            "servers":[{"url":BASE_URL}],
            "paths":{PATH:{"get":{"operationId":"inventory","responses":{"200":{"description":"ok"}}}}}
        }
        try:
            post(f"/p/{PID}/add", {"raw_text": json.dumps(minimal_spec), "input_type":"openapi"}, 60)
        except Exception:
            pass
        spec_id = "pasted://Petstore Proof|1.0.0"

    # Prepare queue
    try: post(f"/p/{PID}/queue/clear", {}, 10)
    except Exception: pass
    if spec_id and sel:
        post(f"/p/{PID}/queue_add", {"spec_id":spec_id, "sel":sel}, 20)
        # try duplicate add to prove dedupe
        post(f"/p/{PID}/queue_add", {"spec_id":spec_id, "sel":sel}, 20)
    else:
        # Fallback: add single using constructed minimal spec id
        try:
            post(f"/p/{PID}/queue_add_single", {"spec_id":spec_id, "method":METHOD, "path":PATH}, 20)
            # duplicate to prove dedupe
            post(f"/p/{PID}/queue_add_single", {"spec_id":spec_id, "method":METHOD, "path":PATH}, 20)
            append("Queue add: queued via single-add fallback\n")
        except Exception as e:
            append(f"Queue add fallback error: {e}\n")
    # Queue second endpoint (findByStatus)
    try:
        if spec_id and sel is not None:
            st, sm = get(f"/p/{PID}/sitemap", 30)
            spec2, sel2 = find_spec_sel_for_endpoint(sm, BASE_URL, METHOD, PATH2)
            if spec2 and sel2:
                post(f"/p/{PID}/queue_add", {"spec_id":spec2, "sel":sel2}, 20)
            else:
                post(f"/p/{PID}/queue_add_single", {"spec_id":spec_id, "method":METHOD, "path":PATH2}, 20)
        else:
            post(f"/p/{PID}/queue_add_single", {"spec_id":spec_id, "method":METHOD, "path":PATH2}, 20)
        append("Queue add #2: findByStatus queued\n")
    except Exception as e:
        append(f"Queue add #2 error: {e}\n")

    # Queue summary
    try:
        with request.urlopen(f"{BASE}/p/{PID}/queue/summary", timeout=10) as r:
            qsum = r.read().decode('utf-8','ignore')
        append("Queue summary before scan: "+qsum[:200]+"\n")
        append("keys:\n- "+KEY+"\n- "+KEY2+"\n")
    except Exception:
        pass

    # SSE
    run_id = "run_PROOF_PETSTORE_MULTI_1"
    start, ping, done = capture_sse(run_id, 10)
    append(f"SSE (multi): {start} | {ping} | {done}\n")

    # Scan
    st, body = post(f"/p/{PID}/nuclei/scan", {"severity":"high","severity":"medium","run_id":run_id,"include_low_info":"1"}, 240)
    append("Scan JSON (multi): "+(body or "")[:240]+"\n")

    # Guard second scan
    try:
        st2, body2 = post(f"/p/{PID}/nuclei/scan", {"severity":"high","run_id":run_id}, 20)
        append("Guard second scan (multi): "+(body2 or "")[:200]+"\n")
    except Exception as e:
        append(f"Guard error: {e}\n")

    # Dossier #1 and #2
    safe = re.sub(r"[^A-Za-z0-9._-]+","_", KEY)
    dossier = f"ui_projects/{PID}/endpoints/{safe}.json"
    if os.path.exists(dossier):
        append("Dossier #1: "+dossier+"\n")
        with open(dossier,'r',encoding='utf-8') as f:
            append("Dossier #1 head: "+f.read(200)+"\n")
    else:
        append("Dossier #1 missing: "+dossier+"\n")
    safe2 = re.sub(r"[^A-Za-z0-9._-]+","_", KEY2)
    dossier2 = f"ui_projects/{PID}/endpoints/{safe2}.json"
    if os.path.exists(dossier2):
        append("Dossier #2: "+dossier2+"\n")
        with open(dossier2,'r',encoding='utf-8') as f:
            append("Dossier #2 head: "+f.read(200)+"\n")
    else:
        append("Dossier #2 missing: "+dossier2+"\n")

    # After drawers for both endpoints
    st, html = post(f"/p/{PID}/sitemap/endpoint-runs", {"base":BASE_URL,"method":METHOD,"path":PATH}, 20)
    append(f"Runs drawer #1 (after): (status {st}) "+ (html or "")[:200] +"\n")
    st, html = post(f"/p/{PID}/sitemap/endpoint-runs", {"base":BASE_URL,"method":METHOD,"path":PATH2}, 20)
    append(f"Runs drawer #2 (after): (status {st}) "+ (html or "")[:200] +"\n")

    # /runs page
    try:
        st,html = get(f"/p/{PID}/runs", 15)
        append(f"/runs status: {st} head: "+ (html or "")[:160] +"\n")
    except Exception as e:
        append(f"/runs error: {e}\n")

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

if __name__ == '__main__':
    ensure_server()
    main()


