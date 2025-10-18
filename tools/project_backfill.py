#!/usr/bin/env python3
import os, sys, json, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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

def gql(query, variables):
    payload = {"query": query, "variables": variables}
    return http("POST", "/graphql", payload, headers={"Content-Type":"application/json"})

def backfill_project():
    """Backfill all existing issues and PRs to the project board."""
    print(f"Backfilling project {PROJECT_ID} for repository {REPO}")
    
    owner, repo_name = REPO.split("/")
    
    # Get Status field info using a simpler query
    fields_resp = gql("""
      query($project: ID!) {
        node(id: $project) {
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
      }
    """, {"project": PROJECT_ID})
    
    status_field = None
    for field in fields_resp["data"]["node"]["fields"]["nodes"]:
        if field and field.get("name") == "Status":
            status_field = field
            break
    
    if not status_field:
        print("No Status field found in project")
        return
    
    print(f"Status field options: {[opt['name'] for opt in status_field['options']]}")
    
    # Helper function to find status option
    def find_status_option(name):
        for opt in status_field["options"]:
            if opt["name"].lower() == name.lower():
                return opt
        return None
    
    todo_opt = find_status_option("Todo")
    inprog_opt = find_status_option("In Progress")
    blocked_opt = find_status_option("Blocked")
    done_opt = find_status_option("Done")
    
    # Backfill issues
    print("\n=== Backfilling Issues ===")
    issues_count = 0
    page = 1
    per_page = 100
    
    while True:
        issues = http("GET", f"/repos/{owner}/{repo_name}/issues?state=open&per_page={per_page}&page={page}")
        if not issues:
            break
            
        for issue in issues:
            if issue.get("pull_request"):  # Skip PRs in issues list
                continue
                
            labels = [label["name"] for label in issue.get("labels", [])]
            
            # Add to project
            try:
                add_resp = gql("""
                  mutation($project: ID!, $content: ID!) {
                    addProjectV2ItemById(input: {projectId: $project, contentId: $content}) {
                      item {
                        id
                      }
                    }
                  }
                """, {"project": PROJECT_ID, "content": issue["node_id"]})
                
                item_id = add_resp["data"]["addProjectV2ItemById"]["item"]["id"]
                
                # Determine status
                target_opt = todo_opt  # default
                if "status:Blocked" in labels:
                    target_opt = blocked_opt or target_opt
                elif "status:In Progress" in labels:
                    target_opt = inprog_opt or target_opt
                elif issue["state"] == "closed":
                    target_opt = done_opt or target_opt
                
                # Set status
                if target_opt:
                    gql("""
                      mutation($project: ID!, $item: ID!, $field: ID!, $option: ID!) {
                        updateProjectV2ItemFieldValue(input: {
                          projectId: $project,
                          itemId: $item,
                          fieldId: $field,
                          value: {
                            singleSelectOptionId: $option
                          }
                        }) {
                          clientMutationId
                        }
                      }
                    """, {
                        "project": PROJECT_ID,
                        "item": item_id,
                        "field": status_field["id"],
                        "option": target_opt["id"]
                    })
                
                print(f"✓ Added Issue #{issue['number']}: {issue['title'][:50]}... (Status: {target_opt['name']})")
                issues_count += 1
                
            except Exception as e:
                print(f"✗ Failed to add Issue #{issue['number']}: {e}")
        
        page += 1
    
    # Backfill PRs
    print("\n=== Backfilling Pull Requests ===")
    prs_count = 0
    page = 1
    
    while True:
        prs = http("GET", f"/repos/{owner}/{repo_name}/pulls?state=open&per_page={per_page}&page={page}")
        if not prs:
            break
            
        for pr in prs:
            labels = [label["name"] for label in pr.get("labels", [])]
            
            # Add to project
            try:
                add_resp = gql("""
                  mutation($project: ID!, $content: ID!) {
                    addProjectV2ItemById(input: {projectId: $project, contentId: $content}) {
                      item {
                        id
                      }
                    }
                  }
                """, {"project": PROJECT_ID, "content": pr["node_id"]})
                
                item_id = add_resp["data"]["addProjectV2ItemById"]["item"]["id"]
                
                # Determine status
                target_opt = todo_opt  # default
                if "status:Blocked" in labels:
                    target_opt = blocked_opt or target_opt
                elif "status:In Progress" in labels or pr.get("draft"):
                    target_opt = inprog_opt or target_opt
                elif pr.get("merged_at") or pr["state"] == "closed":
                    target_opt = done_opt or target_opt
                
                # Set status
                if target_opt:
                    gql("""
                      mutation($project: ID!, $item: ID!, $field: ID!, $option: ID!) {
                        updateProjectV2ItemFieldValue(input: {
                          projectId: $project,
                          itemId: $item,
                          fieldId: $field,
                          value: {
                            singleSelectOptionId: $option
                          }
                        }) {
                          clientMutationId
                        }
                      }
                    """, {
                        "project": PROJECT_ID,
                        "item": item_id,
                        "field": status_field["id"],
                        "option": target_opt["id"]
                    })
                
                draft_status = " (DRAFT)" if pr.get("draft") else ""
                print(f"✓ Added PR #{pr['number']}: {pr['title'][:50]}...{draft_status} (Status: {target_opt['name']})")
                prs_count += 1
                
            except Exception as e:
                print(f"✗ Failed to add PR #{pr['number']}: {e}")
        
        page += 1
    
    print(f"\n=== Backfill Complete ===")
    print(f"Issues added: {issues_count}")
    print(f"PRs added: {prs_count}")
    print(f"Total items: {issues_count + prs_count}")
    
    return {"issues": issues_count, "prs": prs_count, "total": issues_count + prs_count}

if __name__ == "__main__":
    assert REPO and GH_TOKEN and PROJECT_ID, "Missing env: GITHUB_REPOSITORY, GH_TOKEN/PROJECTS_TOKEN, PROJECTS_V2_ID"
    backfill_project()