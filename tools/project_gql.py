#!/usr/bin/env python3
import os, requests, json

GQL_URL = "https://api.github.com/graphql"
TOKEN = os.getenv("PROJECTS_TOKEN") or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
HDR = {"Authorization": f"bearer {TOKEN}"}

def gql(query, variables):
    r = requests.post(GQL_URL, json={"query": query, "variables": variables}, headers=HDR, timeout=90)
    r.raise_for_status()
    j = r.json()
    if "errors" in j:
        raise RuntimeError(j["errors"])
    return j["data"]

def get_project_fields(project_id):
    q = """
    query($id:ID!){
      node(id:$id){
        ... on ProjectV2 {
          id
          fields(first:100){
            nodes{
              id
              name
              dataType
              ... on ProjectV2SingleSelectField { options { id name } }
            }
          }
        }
      }
    }"""
    data = gql(q, {"id": project_id})
    fields = data["node"]["fields"]["nodes"]
    by_name = {f["name"].lower(): f for f in fields}
    return by_name

def iter_items(project_id, after=None, first=50):
    q = """
    query($id:ID!,$first:Int!,$after:String){
      node(id:$id){
        ... on ProjectV2{
          items(first:$first, after:$after){
            pageInfo{ hasNextPage endCursor }
            nodes{
              id
              fieldValues(first:50){
                nodes{
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    field { ... on ProjectV2SingleSelectField { id name } }
                    name
                  }
                }
              }
              content{
                __typename
                ... on Issue{
                  id number state
                  repository { owner{login} name }
                  labels(first:50){ nodes{ name } }
                  assignees(first:10){ nodes{ login id } }
                }
                ... on PullRequest{
                  id number state isDraft merged
                  repository { owner{login} name }
                  labels(first:50){ nodes{ name } }
                  assignees(first:10){ nodes{ login id } }
                }
              }
            }
          }
        }
      }
    }"""
    data = gql(q, {"id": project_id, "first": first, "after": after})
    items = data["node"]["items"]
    return items["nodes"], items["pageInfo"]["hasNextPage"], items["pageInfo"]["endCursor"]

def update_single_select(project_id, item_id, field_id, option_id):
    q = """
    mutation($p:ID!,$i:ID!,$f:ID!,$o:String!){
      updateProjectV2ItemFieldValue(input:{
        projectId:$p, itemId:$i, fieldId:$f,
        value:{singleSelectOptionId:$o}
      }){ projectV2Item { id } }
    }"""
    return gql(q, {"p": project_id, "i": item_id, "f": field_id, "o": option_id})
