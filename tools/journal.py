#!/usr/bin/env python3
import os, json, tempfile, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def _journal_path(role: str, when: datetime.datetime):
    return (ROOT / "control" / "journal" / "agents" / role / when.strftime("%Y-%m")
            / f"{role}-{when.strftime('%Y-%m-%d')}.ndjson")

def append_event(role, event, period, title, items=None, links=None, session=None, ts=None):
    now = datetime.datetime.utcnow() if ts is None else ts
    rec = {
        "ts": now.replace(microsecond=0).isoformat()+"Z",
        "session": session or f"{role}-{now.strftime('%Y%m%dT%H%M%SZ')}",
        "role": role, "event": event, "period": period, "title": title,
        "items": items or [], "links": links or []
    }
    fp = _journal_path(role, now); fp.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(rec, separators=(',',':'))+"\n"
    with tempfile.NamedTemporaryFile('w', delete=False, dir=str(fp.parent)) as t:
        t.write(line); tmpname = t.name
    with open(fp, 'a') as out, open(tmpname) as tmp: out.write(tmp.read())
    os.remove(tmpname)

if __name__=="__main__":
    append_event("coordinator","sod","2025-10-18","Kickoff",
                 ["DevEx: enforce required checks","Docs: fix Mermaid parity (6 off)"],
                 ["PR#70","FEAT-020"])
