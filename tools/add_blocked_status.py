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

def add_blocked_status():
    """Add 'Blocked' status option to the Status field."""
    print(f"Adding 'Blocked' status option to project {PROJECT_ID}")
    
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
    
    existing_options = [opt["name"] for opt in status_field["options"]]
    print(f"Existing status options: {existing_options}")
    
    if "Blocked" in existing_options:
        print("'Blocked' status already exists")
        return
    
    try:
        # Add the Blocked option
        result = gql("""
          mutation($project:ID!, $field:ID!, $name:String!){
            addProjectV2FieldOption(input:{
              projectId:$project,
              fieldId:$field,
              name:$name
            }){
              option {
                id
                name
              }
            }
          }""", {
            "project": PROJECT_ID,
            "field": status_field["id"],
            "name": "Blocked"
        })
        
        new_option = result["data"]["addProjectV2FieldOption"]["option"]
        print(f"✓ Added 'Blocked' status option: {new_option['name']} (ID: {new_option['id']})")
        
    except Exception as e:
        print(f"✗ Failed to add 'Blocked' status: {e}")
        # Try alternative approach - update the field
        try:
            result = gql("""
              mutation($project:ID!, $field:ID!, $options:[String!]!){
                updateProjectV2FieldOption(input:{
                  projectId:$project,
                  fieldId:$field,
                  options:$options
                }){
                  field {
                    id
                    name
                  }
                }
              }""", {
                "project": PROJECT_ID,
                "field": status_field["id"],
                "options": existing_options + ["Blocked"]
              })
            print(f"✓ Updated Status field with 'Blocked' option")
        except Exception as e2:
            print(f"✗ Alternative approach also failed: {e2}")

if __name__ == "__main__":
    assert REPO and GH_TOKEN and PROJECT_ID, "Missing env: GITHUB_REPOSITORY, GH_TOKEN/PROJECTS_TOKEN, PROJECTS_V2_ID"
    add_blocked_status()
