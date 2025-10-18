#!/usr/bin/env python3
import json, datetime, pathlib, collections
ROOT = pathlib.Path(__file__).resolve().parents[1]
AGENTS = ROOT / "control" / "journal" / "agents"
OUTROOT = ROOT / "reports" / "daily"
ORDER = {"sod":0,"mid":1,"note":2,"handoff":3,"decision":4,"eod":5}

def load(period):
    entries=[]
    for role_dir in AGENTS.glob("*"):
        f = role_dir / period[:7] / f"{role_dir.name}-{period}.ndjson"
        if not f.exists(): continue
        for line in f.read_text().splitlines():
            try:
                rec=json.loads(line)
                if rec.get("period")==period: entries.append(rec)
            except Exception: pass
    entries.sort(key=lambda r:(ORDER.get(r.get("event","note"),9), r.get("ts","")))
    return entries

def render(period, entries):
    s=[f"# Status — {period}\n"]
    by=collections.defaultdict(list)
    for e in entries: by[e["event"]].append(e)
    for sec in ["sod","mid","note","handoff","decision","eod"]:
        if by[sec]:
            s.append(f"\n## {sec.upper()}\n")
            for r in by[sec]:
                bullets = "\n- ".join(r["items"]) if r["items"] else "—"
                s.append(f"**{r['role']}** — {r['title']}\n- {bullets}")
    return "\n".join(s)

def write(period, text):
    d = OUTROOT / period[:4] / period[5:7] / period[8:10]
    d.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    (d / f"compiled-{ts}.md").write_text(text)
    (d / "compiled.md").write_text(text)
    (d / "latest.md").write_text(text)

if __name__=="__main__":
    import sys
    period = sys.argv[1] if len(sys.argv)>1 else datetime.datetime.utcnow().strftime("%Y-%m-%d")
    write(period, render(period, load(period)))
