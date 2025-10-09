import re
from urllib import parse, request

BASE = "http://127.0.0.1:5010"
PIDS = [
    "aa05ff93-104f-463f-aaca-adab848ce6c5",
    "ec4c0976-fd94-463c-8ada-0705fe12b944",
]

def append(s):
    with open("DEBUG_RUN.md","a",encoding="utf-8") as f: f.write(s)

def get(url, t=20):
    with request.urlopen(BASE+url, timeout=t) as r:
        return r.status, r.read().decode('utf-8','ignore')

def post(url, data, t=20):
    body = parse.urlencode(data, doseq=True).encode()
    req = request.Request(BASE+url, data=body)
    with request.urlopen(req, timeout=t) as r:
        return r.status, r.read().decode('utf-8','ignore')

def count_ids(html):
    gi = len(re.findall(r'id="global-indicator"', html))
    pb = len(re.findall(r'id="panel-body"', html))
    return gi, pb

def non_empty_drawer(pid):
    samples = []
    # Explorer drawer
    samples.append(post(f"/p/{pid}/op_details", {"spec_id":"", "index":"0"})[1][:160])
    # Queue item details (may be empty)
    samples.append(post(f"/p/{pid}/queue/item_details", {"qid":"0"})[1][:160])
    # Findings sample drawer
    samples.append(get(f"/p/{pid}/findings")[1][:160])
    return samples

def main():
    append("\n## UI Indicators & Drawers Proof\n")
    for pid in PIDS:
        try:
            st, home = get(f"/p/{pid}")
            st_smap, smap = get(f"/p/{pid}/sitemap")
            st_queue, q = get(f"/p/{pid}/queue")
            st_active, act = get(f"/p/{pid}/active-testing")
            gi1, pb1 = count_ids(home)
            gi2, pb2 = count_ids(smap)
            gi3, pb3 = count_ids(q)
            gi4, pb4 = count_ids(act)
            append(f"PID {pid} indicators: home({gi1}/{pb1}) sitemap({gi2}/{pb2}) queue({gi3}/{pb3}) active({gi4}/{pb4})\n")
            try:
                stdr, runs = post(f"/p/{pid}/sitemap/endpoint-runs", {"base":"https://example.com","method":"GET","path":"/ping"})
                excerpt = (runs or "")[:200]
                append(f"Drawer excerpt (sitemap runs): status={stdr} {excerpt}\n")
            except Exception:
                pass
        except Exception as e:
            append(f"PID {pid} error: {e}\n")

if __name__ == '__main__':
    main()


