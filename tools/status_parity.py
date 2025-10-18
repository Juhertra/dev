#!/usr/bin/env python3
import os, sys, json, time, requests, re
from project_gql import get_project_fields, iter_items, update_single_select

PROJECT = os.getenv("PROJECTS_V2_ID")
TOKEN = os.getenv("PROJECTS_TOKEN") or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
REPO  = os.getenv("GITHUB_REPOSITORY") or os.getenv("REPO")
if not (PROJECT and TOKEN): 
    print("Missing PROJECTS_V2_ID or token", file=sys.stderr); sys.exit(1)

REST = "https://api.github.com"
HDR  = {"Authorization": f"token {TOKEN}", "Accept":"application/vnd.github+json"}

STATUS_LABELS = {"Todo":"status:Todo","In Progress":"status:In Progress","Blocked":"status:Blocked","Done":"status:Done"}

def ensure_label(owner, repo, name):
    # create if missing; ignore if exists
    requests.post(f"{REST}/repos/{owner}/{repo}/labels", headers=HDR, json={"name":name, "color":"ededed"})

def add_labels(owner, repo, num, labels):
    requests.post(f"{REST}/repos/{owner}/{repo}/issues/{num}/labels", headers=HDR, json={"labels":labels})

def compute_desired_status(content):
    labels = [l["name"] for l in content["labels"]["nodes"]]
    # label wins if present
    for k in STATUS_LABELS.values():
        if k in labels:
            return k.split(":",1)[1]
    if content["__typename"]=="PullRequest":
        if content.get("isDraft"): return "In Progress"
        if content.get("state") in ("MERGED","CLOSED"): return "Done"
        return "Todo"
    if content["__typename"]=="Issue":
        return "Done" if content.get("state")=="CLOSED" else "Todo"
    return "Todo"

def main():
    fields = get_project_fields(PROJECT)
    # find Status field case-insensitively, tolerate "In progress" vs "In Progress"
    status_f = None
    for k,v in fields.items():
        if v["dataType"]=="SINGLE_SELECT" and k.strip().lower()=="status":
            status_f = v; break
    if not status_f:
        print("Project Status field not found on this project view.", file=sys.stderr); sys.exit(2)
    opt_by_name = {o["name"].lower(): o["id"] for o in status_f["options"]}

    fixed_field=0; fixed_label=0; scanned=0
    after=None
    while True:
        nodes, more, after = iter_items(PROJECT, after=after, first=50)
        for it in nodes:
            scanned+=1
            content = it.get("content")
            if not content: continue
            owner = content["repository"]["owner"]["login"]; repo = content["repository"]["name"]; num = content["number"]

            want = compute_desired_status(content)              # "Todo" / "In Progress" / "Blocked" / "Done"
            # 1) ensure label
            want_label = STATUS_LABELS[want]
            existing = [l["name"] for l in content["labels"]["nodes"]]
            if want_label not in existing:
                ensure_label(owner, repo, want_label)
                add_labels(owner, repo, num, [want_label])
                fixed_label+=1

            # 2) ensure project field
            want_opt = opt_by_name.get(want.lower()) or opt_by_name.get(want)  # tolerate case
            if want_opt:
                update_single_select(PROJECT, it["id"], status_f["id"], want_opt)
                fixed_field+=1

        if not more: break

    print(json.dumps({
        "scanned": scanned,
        "project_status_field_updates": fixed_field,
        "status_labels_added": fixed_label
    }))
if __name__=="__main__":
    main()
