#!/usr/bin/env python3
import os, json, requests, sys
from project_gql import (
  get_project_id_by_title, get_status_field, get_or_create_text_field,
  iter_items, set_status_field, set_text_field
)

TITLE = os.getenv("PROJECT_TITLE","SecFlow")
TOKEN = os.getenv("PROJECTS_TOKEN") or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
if not TOKEN: raise SystemExit("Missing token")
REST = "https://api.github.com"
HDR = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github+json"}

LABELS = ["status:Todo","status:In Progress","status:Blocked","status:Done"]
MAP = {"todo":"status:Todo","in progress":"status:In Progress","blocked":"status:Blocked","done":"status:Done"}
AGENT_FIELD_NAME = os.getenv("AGENT_FIELD_NAME","Agent Role")

def ensure_label(owner, repo, name):
    requests.post(f"{REST}/repos/{owner}/{repo}/labels",
                  headers=HDR, json={"name":name, "color":"ededed"})

def add_label(owner, repo, num, name):
    requests.post(f"{REST}/repos/{owner}/{repo}/issues/{num}/labels",
                  headers=HDR, json={"labels":[name]})

def decide_status(content):
    labels = [l["name"] for l in content["labels"]["nodes"]]
    for l in LABELS:
        if l in labels:
            return l  # explicit
    if content["__typename"]=="PullRequest":
        if content.get("isDraft"): return "status:In Progress"
        if content.get("merged") or content.get("state")=="CLOSED": return "status:Done"
        return "status:Todo"
    if content["__typename"]=="Issue":
        return "status:Done" if content.get("state")=="CLOSED" else "status:Todo"
    return "status:Todo"

def first_role_label(content):
    labels = [l["name"] for l in content["labels"]["nodes"]]
    roles = [x for x in labels if x.startswith("role:")]
    if roles:
        # keep the label's role part (after "role:")
        return roles[0].split(":",1)[1]
    return None

def main(mode="report", comment_path=None):
    fix = (mode=="fix")
    project_id = get_project_id_by_title(TITLE)
    status_field_id, status_opts = get_status_field(project_id)
    agent_field_id = get_or_create_text_field(project_id, AGENT_FIELD_NAME)

    touched = []; violations=[]; agent_updates=0
    stats = {"scanned":0,"labels_added":0,"field_set":0,"agent_field_set":0}

    for it in iter_items(project_id):
        stats["scanned"]+=1
        c = it.get("content")
        if not c: continue
        owner = c["repository"]["owner"]["login"]; repo = c["repository"]["name"]; num = c["number"]

        want_label = decide_status(c)
        want_field = want_label.split(":",1)[1]  # "Todo" etc.

        # current label/field
        has = [n["name"] for n in c["labels"]["nodes"]]
        has_status_label = any(n in LABELS for n in has)
        fv = it["fieldValues"]["nodes"]
        current_status_field = None
        current_agent_text = None
        for n in fv:
            if n["__typename"]=="ProjectV2ItemFieldSingleSelectValue" and n["field"]["name"].lower()=="status":
                current_status_field = n.get("name")
            if n["__typename"]=="ProjectV2ItemFieldTextValue" and n["field"]["name"]==AGENT_FIELD_NAME:
                current_agent_text = n.get("text")

        # build violations for visibility (status only)
        if not has_status_label or (current_status_field or "").lower() != want_field.lower():
            violations.append({
                "repo":f"{owner}/{repo}","number":num,
                "want_label":want_label,"want_field":want_field,
                "current_field":current_status_field,"has_label":has_status_label
            })

        if fix:
            # ensure status label
            if want_label not in has:
                ensure_label(owner, repo, want_label)
                add_label(owner, repo, num, want_label)
                stats["labels_added"]+=1

            # set Project Status field
            opt_id = status_opts.get(want_field.lower())
            if opt_id:
                set_status_field(project_id, it["id"], status_field_id, opt_id)
                stats["field_set"]+=1
                touched.append({"repo":f"{owner}/{repo}","number":num,"status_to":want_field})

            # set Agent Role text field if a role label exists
            role = first_role_label(c)
            if role and (current_agent_text or "") != role:
                set_text_field(project_id, it["id"], agent_field_id, role)
                stats["agent_field_set"] += 1
                agent_updates += 1
                touched.append({"repo":f"{owner}/{repo}","number":num,"agent_role_to":role})

    res = {"summary":stats, "violations":violations[:200], "touched":touched[:200]}
    out = json.dumps(res, indent=2)
    if comment_path:
        with open(comment_path,"w") as f: f.write(out)
    print(out)

if __name__=="__main__":
    mode = sys.argv[1] if len(sys.argv)>1 else "report"
    comment = sys.argv[2] if len(sys.argv)>2 else None
    main(mode, comment)