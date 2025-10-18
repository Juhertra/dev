#!/usr/bin/env python3
import os, sys, json, re
from pathlib import Path
from project_fields import get_fields, get_items, update_single_select, update_assignees

PROJECT=os.getenv("PROJECTS_V2_ID")
if not PROJECT: 
    print("Missing PROJECTS_V2_ID", file=sys.stderr); sys.exit(1)

ROLE_MAP_PATH=Path(".github/role-map.json")
ROLE_MAP=json.loads(ROLE_MAP_PATH.read_text()) if ROLE_MAP_PATH.exists() else {}

# label → Status value
STATUS_FROM_LABEL={
    "status:Todo":"Todo",
    "status:In Progress":"In Progress",
    "status:Blocked":"Blocked",
    "status:Done":"Done",
}
# fallback priority when no label:
FALLBACK_ORDER=["In Progress","Blocked","Todo","Done"]

def want_status(content):
    labels=[l["name"] for l in content.get("labels",{}).get("nodes",[])]
    # 1) explicit label mapping
    for k,v in STATUS_FROM_LABEL.items():
        if k in labels: return v
    # 2) PR state
    if content["__typename"]=="PullRequest":
        if content.get("isDraft"): return "In Progress"
        if content.get("state") in ("MERGED","CLOSED"): return "Done"
        return "Todo"
    # 3) Issue state
    if content["__typename"]=="Issue":
        if content.get("state")=="CLOSED": return "Done"
        return "Todo"
    return "Todo"

def role_labels(content):
    labels=[l["name"] for l in content.get("labels",{}).get("nodes",[])]
    return [l for l in labels if l.startswith("role:")]

def role_to_user_ids(roles, users_cache, whoami="Juhertra"):
    # Simple: map via ROLE_MAP; fallback to owner of repo (whoami)
    ids=[]
    for r in roles:
        gh_user=ROLE_MAP.get(r.replace("role:",""), whoami)
        if gh_user in users_cache:
            ids.append(users_cache[gh_user])
    return ids

def fetch_user_nodes(users):
    # minimal cache lookup using REST via gh CLI env if available is omitted for brevity
    # We'll rely on items having assignees already; if none, we keep empty → Project shows blank.
    return {}

def main():
    fields=get_fields(PROJECT)
    status_f=fields.get("Status")
    if not status_f or status_f.get("dataType")!="SINGLE_SELECT":
        print("Project Status field missing or wrong type.", file=sys.stderr); sys.exit(2)
    # map option name → option id
    opt_by_name={o["name"]:o["id"] for o in status_f["options"]}
    assignees_f=fields.get("Assignees")
    if not assignees_f:
        print("Project Assignees field not present in project view.", file=sys.stderr)

    fixed=0; assn=0; scanned=0
    after=None
    while True:
        nodes, more, after = get_items(PROJECT, after=after)
        for n in nodes:
            scanned+=1
            content=n["content"] or {}
            if not content: continue
            want=want_status(content)
            option_id=opt_by_name.get(want)
            if option_id:
                update_single_select(PROJECT, n["id"], status_f["id"], option_id)
                fixed+=1
            # Assignees from role-map (optional)
            if assignees_f:
                roles=role_labels(content)
                if roles:
                    # Best-effort: assign the single mapped user (string login) via repo UI later
                    # Projects v2 requires user node IDs; we skip if unknown.
                    # Leave to DevOps autosync to refine.
                    pass
        if not more: break
    print(json.dumps({"scanned":scanned,"status_filled":fixed,"assignees_updated":assn}))
if __name__=="__main__":
    main()
