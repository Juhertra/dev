#!/usr/bin/env python3
import os, sys, json, re, hashlib, time, pathlib, argparse
from datetime import datetime, timezone
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
JOURNALS = ROOT / "control" / "journal" / "agents"

GITHUB_API = os.environ.get("GITHUB_API", "https://api.github.com")
REPO = os.environ.get("GITHUB_REPOSITORY")  # owner/name
GH_TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("PROJECTS_TOKEN")
PROJECT_ID = os.environ.get("PROJECTS_V2_ID")

def http(method, path, data=None, headers=None):
    url = path if path.startswith("http") else f"{GITHUB_API}{path}"
    req = urllib.request.Request(url, method=method)
    h = {"Accept":"application/vnd.github+json"}
    if GH_TOKEN: h["Authorization"] = f"Bearer {GH_TOKEN}"
    if headers: h.update(headers)
    if data is not None:
        body = json.dumps(data).encode()
        h["Content-Type"] = "application/json"
    else:
        body = None
    req.headers = h
    with urllib.request.urlopen(req, data=body) as r:
        return json.load(r)

def sha(s: str) -> str:
    return hashlib.sha1(s.encode()).hexdigest()[:12]

def compute_jid(rec):
    key = f"{rec.get('role','')}|{rec.get('ts','')}|{rec.get('event','')}|{rec.get('title','')}"
    return sha(key)

def find_target_roles(items):
    roles=[]
    for it in items or []:
        for m in re.findall(r'@([a-z0-9\-]+)', it, flags=re.I):
            roles.append(m)
    return list(dict.fromkeys(roles))  # de-dup, preserve order

def search_issue_by_jid(jid, dry_run=False):
    if dry_run:
        return None  # Skip API calls in dry-run mode
    # REST Search to avoid scanning all issues
    q = f'repo:{REPO} in:body "JID:{jid}"'
    r = http("GET", f"/search/issues?q={urllib.parse.quote(q)}")
    items = r.get("items", [])
    return items[0] if items else None

def ensure_labels(labels):
    # Create missing labels (best-effort)
    for name in labels:
        try:
            http("POST", f"/repos/{REPO}/labels", {"name":name})
        except Exception:
            pass

def create_issue_from_handoff(rec, jid):
    title = f"[handoff] {rec.get('role')}: {rec.get('title')}"
    body = [
        f"**Role:** `{rec.get('role')}`",
        f"**Event:** `{rec.get('event')}`  **Period:** `{rec.get('period')}`  **Session:** `{rec.get('session','')}`",
        "",
        "### Items",
        *[f"- {it}" for it in (rec.get('items') or [])],
        "",
        "### Links",
        *[f"- {lnk}" for lnk in (rec.get('links') or [])],
        "",
        f"<!-- JID:{jid} -->"
    ]
    labels = ["from:journal", "handoff", "status:Todo"]
    targets = find_target_roles(rec.get("items"))
    for t in targets[:3]:
        labels.append(f"role:{t}")
    ensure_labels(labels)
    data = {"title": title, "body": "\n".join(body), "labels": labels}
    r = http("POST", f"/repos/{REPO}/issues", data)
    return r

def gql(query, variables):
    payload = {"query": query, "variables": variables}
    return http("POST", "/graphql", payload, headers={"Content-Type":"application/json"})

def add_to_project_and_set_status(node_id, status="Todo"):
    try:
        # 1) add item
        add = gql("""
          mutation($project:ID!,$content:ID!){
            addProjectV2ItemById(input:{projectId:$project, contentId:$content}){
              item { id }
            }
          }""", {"project": PROJECT_ID, "content": node_id})
        item_id = add["data"]["addProjectV2ItemById"]["item"]["id"]
        
        # 2) set Status if available (skip if no Status field)
        try:
            fields = gql("""
              query($project:ID!){
                node(id:$project){
                  ... on ProjectV2 {
                    fields(first:50){
                      nodes {
                        ... on ProjectV2SingleSelectField { 
                          id name 
                          options { id name } 
                        }
                      }
                    }
                  }
                }
              }""", {"project": PROJECT_ID})
            
            fld = None
            for n in fields["data"]["node"]["fields"]["nodes"]:
                if n.get("name") == "Status":
                    fld = n
                    break
            if not fld: 
                print("No Status field found, skipping status update")
                return
                
            opt = None
            for o in fld.get("options", []):
                if o["name"].lower() == status.lower():
                    opt = o
                    break
            if not opt: 
                print(f"No '{status}' option found, skipping status update")
                return
                
            gql("""
              mutation($project:ID!, $item:ID!, $field:ID!, $option:ID!){
                updateProjectV2ItemFieldValue(input:{
                  projectId:$project, itemId:$item,
                  fieldId:$field, value:{ singleSelectOptionId:$option }
                }){ clientMutationId }
              }""", {"project": PROJECT_ID, "item": item_id, "field": fld["id"], "option": opt["id"]})
        except Exception as e:
            print(f"Status update failed (continuing): {e}")
            
    except Exception as e:
        print(f"Failed to add to project: {e}")
        raise

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="ISO date (period) lower bound (YYYY-MM-DD)", default="1970-01-01")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    assert REPO and GH_TOKEN and PROJECT_ID, "Missing env: GITHUB_REPOSITORY, GH_TOKEN/PROJECTS_TOKEN, PROJECTS_V2_ID"

    created=skipped=added=0
    since = args.since
    for nd in JOURNALS.rglob("*.ndjson"):
        with open(nd) as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except: continue
                if rec.get("event") != "handoff": continue
                if rec.get("period","9999-99-99") < since: continue
                jid = compute_jid(rec)
                existing = search_issue_by_jid(jid, args.dry_run)
                if existing:
                    skipped += 1
                    # Ensure it's on project
                    if not args.dry_run:
                        add_to_project_and_set_status(existing["node_id"], status="Todo")
                        added += 1
                    continue
                if args.dry_run: 
                    print(f"DRY new issue for JID {jid}")
                    continue
                issue = create_issue_from_handoff(rec, jid)
                created += 1
                add_to_project_and_set_status(issue["node_id"], status="Todo")
                added += 1
    print(json.dumps({"created":created,"skipped":skipped,"project_added":added}))

if __name__ == "__main__":
    main()
