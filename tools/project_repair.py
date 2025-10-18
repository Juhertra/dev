#!/usr/bin/env python3
import os, sys, json, time, urllib.request, urllib.parse

API = "https://api.github.com"
REPO = os.environ["GITHUB_REPOSITORY"]          # owner/name
TOKEN = os.environ["PROJECTS_TOKEN"]
PROJECT = os.environ["PROJECTS_V2_ID"]          # PVT_...
ROLEMAP_PATH = ".github/role-map.json"

def http(method, path, data=None, headers=None, is_graphql=False):
    url = path if path.startswith("http") else (API + path)
    req = urllib.request.Request(url, method=method)
    h = {"Accept":"application/vnd.github+json","Authorization":f"Bearer {TOKEN}"}
    if headers: h.update(headers)
    if data is not None:
        body = json.dumps(data).encode()
        h["Content-Type"] = "application/json"
    else:
        body = None
    req.headers = h
    with urllib.request.urlopen(req, data=body) as r:
        return json.load(r)

def gql(query, variables):
    payload = {"query": query, "variables": variables}
    return http("POST", "/graphql", payload, headers={"Content-Type":"application/json"}, is_graphql=True)

def get_status_field(project_id):
    q = """
    query($id: ID!) {
      node(id: $id) {
        ... on ProjectV2 {
          fields(first: 50) {
            nodes {
              ... on ProjectV2SingleSelectField {
                id
                name
                options {
                  id
                  name
                }
              }
            }
          }
        }
      }
    }"""
    r = gql(q, {"id":project_id})
    if "errors" in r:
        print(f"GraphQL errors: {r['errors']}")
        return None
    fields = r["data"]["node"]["fields"]["nodes"]
    st = next((f for f in fields if f and f.get("name")=="Status"), None)
    return st

def add_to_project(node_id):
    m = """
    mutation($pid:ID!,$cid:ID!){
      addProjectV2ItemById(input:{projectId:$pid, contentId:$cid}){
        item { id }
      }
    }"""
    try:
        r = gql(m, {"pid": PROJECT, "cid": node_id})
        return r["data"]["addProjectV2ItemById"]["item"]["id"]
    except Exception as e:
        # Already exists or other benign issues: ignore
        return None

def set_status(item_id, field_id, option_id):
    m = """
    mutation($pid:ID!,$iid:ID!,$fid:ID!,$oid:ID!){
      updateProjectV2ItemFieldValue(input:{
        projectId:$pid, itemId:$iid, fieldId:$fid,
        value:{ singleSelectOptionId:$oid }
      }){ clientMutationId }
    }"""
    gql(m, {"pid": PROJECT, "iid": item_id, "fid": field_id, "oid": option_id})

def list_all_issues(state="all"):
    out=[]; page=1
    while True:
        res = http("GET", f"/repos/{REPO}/issues?state={state}&per_page=100&page={page}")
        if not res: break
        out.extend([i for i in res if "pull_request" not in i])
        page+=1
    return out

def list_all_prs(state="all"):
    out=[]; page=1
    while True:
        res = http("GET", f"/repos/{REPO}/pulls?state={state}&per_page=100&page={page}")
        if not res: break
        out.extend(res); page+=1
    return out

def ensure_assignees(number, names):
    if not names: return
    http("PATCH", f"/repos/{REPO}/issues/{number}", {"assignees": names})

def infer_status_from_labels_and_state(labels, gh_state, is_pr, is_draft=False, merged=False):
    labs = set([l["name"] if isinstance(l, dict) else l for l in labels or []])
    if "status:Blocked" in labs: return "Blocked"
    if "status:In Progress" in labs: return "In Progress"
    if is_pr and is_draft: return "In Progress"
    if gh_state == "closed" or merged: return "Done"
    return "Todo"

def first_role_from_labels(labels):
    labs = [l["name"] if isinstance(l, dict) else l for l in labels or []]
    for l in labs:
        if l.startswith("role:"): return l.split("role:",1)[1]
    return None

def role_labels(labels):
    return [ (l["name"] if isinstance(l,dict) else l)[5:]
             for l in labels or [] if (l if isinstance(l,str) else l["name"]).startswith("role:") ]

def load_role_map():
    try:
        with open(ROLEMAP_PATH) as f:
            return json.load(f)
    except Exception:
        return {}

def status_option_id(status_field, name):
    if not status_field: return None
    for o in status_field.get("options", []):
        if o["name"].lower()==name.lower():
            return o["id"]
    return None

def get_node_id_for_issue(number):
    return http("GET", f"/repos/{REPO}/issues/{number}")["node_id"]

def get_node_id_for_pr(number):
    return http("GET", f"/repos/{REPO}/pulls/{number}")["node_id"]

def get_or_create_item(node_id):
    # Add; if it already exists, GitHub returns item or throws; either way, we don't need the ID to update status via itemId.
    # We need itemId; since GraphQL doesn't easily list by content, re-adding returns item id reliably.
    m = """
    mutation($pid:ID!,$cid:ID!){
      addProjectV2ItemById(input:{projectId:$pid, contentId:$cid}){
        item { id }
      }
    }"""
    r = gql(m, {"pid": PROJECT, "cid": node_id})
    return r["data"]["addProjectV2ItemById"]["item"]["id"]

def main():
    rolemap = load_role_map()
    status_field = get_status_field(PROJECT)
    todo = status_option_id(status_field,"Todo")
    inprog = status_option_id(status_field,"In Progress")
    blocked = status_option_id(status_field,"Blocked")
    done = status_option_id(status_field,"Done")

    fixed=0; assigned=0; closed=0

    # Issues
    for it in list_all_issues("all"):
        number = it["number"]
        node_id = it["node_id"]
        labels = it.get("labels",[])
        state = it["state"]
        st = infer_status_from_labels_and_state(labels, state, is_pr=False)
        # ensure project item exists
        item_id = get_or_create_item(node_id)
        # set status
        target = {"Todo":todo,"In Progress":inprog,"Blocked":blocked,"Done":done}.get(st)
        if target: set_status(item_id, status_field["id"], target); fixed+=1
        # assignees
        roles = role_labels(labels)
        users = [rolemap.get(r,"") for r in roles if rolemap.get(r,"")]
        if users:
            ensure_assignees(number, users); assigned+=1
        # close if status:Done label exists but issue is open
        if any((l["name"] if isinstance(l,dict) else l)=="status:Done" for l in labels) and state!="closed":
            http("PATCH", f"/repos/{REPO}/issues/{number}", {"state":"closed"}); closed+=1

    # PRs
    for pr in list_all_prs("all"):
        number = pr["number"]
        node_id = pr["node_id"]
        labels = pr.get("labels",[])
        state = pr["state"]     # open/closed
        draft = pr.get("draft", False)
        merged = bool(pr.get("merged_at"))
        st = infer_status_from_labels_and_state(labels, state, is_pr=True, is_draft=draft, merged=merged)
        item_id = get_or_create_item(node_id)
        target = {"Todo":todo,"In Progress":inprog,"Blocked":blocked,"Done":done}.get(st)
        if target: set_status(item_id, status_field["id"], target); fixed+=1
        # reviewer/assignee for PR (assign as issue)
        roles = role_labels(labels)
        users = [rolemap.get(r,"") for r in roles if rolemap.get(r,"")]
        if users:
            ensure_assignees(number, users); assigned+=1

    print(json.dumps({"fixed_status":fixed,"updated_assignees":assigned,"closed_done":closed}))
if __name__ == "__main__":
    main()
