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

def fix_project_status():
    """Fix Status field for all items in the project board."""
    print(f"Fixing Status field for project {PROJECT_ID}")
    
    # Get all items in the project
    items_resp = gql("""
      query($project:ID!){
        node(id:$project){
          ... on ProjectV2 {
            items(first:100){
              nodes {
                id
                content {
                  ... on Issue {
                    id
                    number
                    title
                    labels(first:20) {
                      nodes { name }
                    }
                  }
                  ... on PullRequest {
                    id
                    number
                    title
                    labels(first:20) {
                      nodes { name }
                    }
                  }
                }
              }
            }
          }
        }
      }""", {"project": PROJECT_ID})
    
    items = items_resp["data"]["node"]["items"]["nodes"]
    print(f"Found {len(items)} items in project")
    
    # Get Status field info
    fields_resp = gql("""
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
    
    status_field = None
    for field in fields_resp["data"]["node"]["fields"]["nodes"]:
        if field.get("name") == "Status":
            status_field = field
            break
    
    if not status_field:
        print("No Status field found in project")
        return
    
    print(f"Status field options: {[opt['name'] for opt in status_field['options']]}")
    
    fixed_count = 0
    for item in items:
        content = item["content"]
        if not content:
            continue
            
        labels = [label["name"] for label in content.get("labels", {}).get("nodes", [])]
        
        # Determine status from labels
        status_value = "Todo"  # default
        if "status:In Progress" in labels:
            status_value = "In Progress"
        elif "status:Blocked" in labels:
            status_value = "Blocked"
        elif "status:Done" in labels:
            status_value = "Done"
        elif "status:Todo" in labels:
            status_value = "Todo"
        
        # Find the status option
        status_option = None
        for opt in status_field["options"]:
            if opt["name"] == status_value:
                status_option = opt
                break
        
        if status_option:
            try:
                gql("""
                  mutation($project:ID!, $item:ID!, $field:ID!, $option:ID!){
                    updateProjectV2ItemFieldValue(input:{
                      projectId:$project, itemId:$item,
                      fieldId:$field, value:{ singleSelectOptionId:$option }
                    }){ clientMutationId }
                  }""", {
                    "project": PROJECT_ID,
                    "item": item["id"],
                    "field": status_field["id"],
                    "option": status_option["id"]
                })
                
                content_type = "Issue" if "Issue" in str(type(content)) else "PR"
                content_num = content.get("number", "?")
                print(f"✓ Set Status='{status_value}' for {content_type} #{content_num}")
                fixed_count += 1
                
            except Exception as e:
                print(f"✗ Failed to update {content.get('number', '?')}: {e}")
    
    print(f"\nFixed {fixed_count} items")

if __name__ == "__main__":
    assert REPO and GH_TOKEN and PROJECT_ID, "Missing env: GITHUB_REPOSITORY, GH_TOKEN/PROJECTS_TOKEN, PROJECTS_V2_ID"
    fix_project_status()
