#!/usr/bin/env python3
import os, requests, json

GQL = "https://api.github.com/graphql"
TOKEN = os.getenv("PROJECTS_TOKEN") or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
if not TOKEN:
    raise SystemExit("Missing token in PROJECTS_TOKEN/GH_TOKEN/GITHUB_TOKEN")

HDR = {"Authorization": f"bearer {TOKEN}"}

def gql(query, variables):
    r = requests.post(GQL, json={"query": query, "variables": variables}, headers=HDR, timeout=120)
    r.raise_for_status()
    j = r.json()
    if "errors" in j and j["errors"]:
        raise RuntimeError(json.dumps(j["errors"], indent=2))
    return j["data"]

def get_project_id_by_title(title):
    # Resolve under current viewer (user-owned Projects v2)
    me = requests.get("https://api.github.com/user", headers={"Authorization": f"token {TOKEN}"}).json()["login"]
    q = """
    query($login:String!){
      user(login:$login){
        projectsV2(first:100){ nodes{ id title number } }
      }
    }"""
    d = gql(q, {"login": me})
    for n in d["user"]["projectsV2"]["nodes"]:
        if n["title"] == title:
            return n["id"]
    raise SystemExit(f'Project titled "{title}" not found under user {me}')

def get_status_field(project_id):
    q = """
    query($id:ID!){
      node(id:$id){
        ... on ProjectV2{
          fields(first:100){
            nodes{
              __typename
              ... on ProjectV2Field {
                id name dataType
              }
              ... on ProjectV2SingleSelectField { 
                id name dataType
                options { id name } 
              }
            }
          }
        }
      }
    }"""
    d = gql(q, {"id": project_id})
    for f in d["node"]["fields"]["nodes"]:
        if f["dataType"] == "SINGLE_SELECT" and f["name"].lower() == "status":
            opt = {o["name"].lower(): o["id"] for o in f["options"]}
            return f["id"], opt
    raise SystemExit('Project "Status" field not found')

def get_or_create_text_field(project_id, name):
    q = """
    query($id:ID!){
      node(id:$id){
        ... on ProjectV2{
          fields(first:100){
            nodes{
              __typename
              ... on ProjectV2Field {
                id name dataType
              }
            }
          }
        }
      }
    }"""
    d = gql(q, {"id": project_id})
    for f in d["node"]["fields"]["nodes"]:
        if f.get("dataType") == "TEXT" and f.get("name") == name:
            return f["id"]
    # create text field
    m = """
    mutation($pid:ID!,$name:String!){
      createProjectV2Field(input:{projectId:$pid, dataType:TEXT, name:$name}){
        projectV2Field{
          ... on ProjectV2Field {
            id name dataType
          }
        }
      }
    }"""
    r = gql(m, {"pid": project_id, "name": name})
    return r["createProjectV2Field"]["projectV2Field"]["id"]

def iter_items(project_id):
    q = """
    query($id:ID!, $after:String){
      node(id:$id){
        ... on ProjectV2{
          items(first:50, after:$after){
            pageInfo{ hasNextPage endCursor }
            nodes{
              id
              fieldValues(first:50){
                nodes{
                  __typename
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    field { ... on ProjectV2SingleSelectField { id name } }
                    name
                  }
                  ... on ProjectV2ItemFieldTextValue {
                    field { 
                      ... on ProjectV2Field { id name }
                    }
                    text
                  }
                }
              }
              content{
                __typename
                ... on Issue{
                  id number state title body
                  repository{ owner{login} name }
                  labels(first:100){ nodes{ name } }
                }
                ... on PullRequest{
                  id number state isDraft merged title body
                  repository{ owner{login} name }
                  labels(first:100){ nodes{ name } }
                }
              }
            }
          }
        }
      }
    }"""
    after=None
    while True:
        d = gql(q, {"id": project_id, "after": after})
        items = d["node"]["items"]
        for n in items["nodes"]:
            yield n
        if not items["pageInfo"]["hasNextPage"]:
            break
        after = items["pageInfo"]["endCursor"]

def set_status_field(project_id, item_id, field_id, option_id):
    q = """
    mutation($p:ID!,$i:ID!,$f:ID!,$o:String!){
      updateProjectV2ItemFieldValue(input:{
        projectId:$p, itemId:$i, fieldId:$f,
        value:{singleSelectOptionId:$o}
      }){
        projectV2Item{ id }
      }
    }"""
    return gql(q, {"p": project_id, "i": item_id, "f": field_id, "o": option_id})

def set_text_field(project_id, item_id, field_id, text_value):
    q = """
    mutation($p:ID!,$i:ID!,$f:ID!,$t:String!){
      updateProjectV2ItemFieldValue(input:{
        projectId:$p, itemId:$i, fieldId:$f,
        value:{text:$t}
      }){
        projectV2Item{ id }
      }
    }"""
    return gql(q, {"p": project_id, "i": item_id, "f": field_id, "t": text_value})