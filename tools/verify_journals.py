#!/usr/bin/env python3
import json, sys, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[1]
J = ROOT / "control" / "journal" / "agents"
EVENTS = {"sod","mid","eod","note","handoff","decision"}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def main():
    ok=True
    for p in J.rglob("*.ndjson"):
        role = p.parent.parent.name
        for i, line in enumerate(p.read_text().splitlines(), 1):
            try: rec=json.loads(line)
            except Exception as e: print(f"::error::{p}:{i} not JSON: {e}"); ok=False; continue
            if rec.get("role")!=role: print(f"::error::{p}:{i} role mismatch"); ok=False
            if rec.get("event") not in EVENTS: print(f"::error::{p}:{i} bad event"); ok=False
            if not DATE.match(rec.get("period","")): print(f"::error::{p}:{i} bad period"); ok=False
            if "items" in rec and not isinstance(rec["items"], list): print(f"::error::{p}:{i} items not list"); ok=False
            if "links" in rec and not isinstance(rec["links"], list): print(f"::error::{p}:{i} links not list"); ok=False
    sys.exit(0 if ok else 1)

if __name__=="__main__": main()
