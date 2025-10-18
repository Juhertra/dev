#!/usr/bin/env python3
import os, json, requests, sys

GQL="https://api.github.com/graphql"
TOKEN=os.getenv("PROJECTS_TOKEN") or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
HDR={"Authorization": f"bearer {TOKEN}"}

def gql(q, v):
    r=requests.post(GQL, json={"query":q, "variables":v}, headers=HDR, timeout=60)
    r.raise_for_status()
    j=r.json()
    if 'errors' in j:
        raise RuntimeError(j['errors'])
    return j['data']

def get_fields(project_id):
    q="""
    query($id:ID!){
      node(id:$id){
        ... on ProjectV2{
          id
          fields(first:100){
            nodes{
              ... on ProjectV2SingleSelectField {
                id
                name
                dataType
                options { id name }
              }
            }
          }
        }
      }
    }
    """
    data=gql(q,{"id":project_id})
    nodes=data["node"]["fields"]["nodes"]
    by_name={n["name"]:n for n in nodes if n}
    return by_name

def get_items(project_id, after=None, first=50):
    q="""
    query($id:ID!,$first:Int!,$after:String){
      node(id:$id){
        ... on ProjectV2{
          items(first:$first, after:$after){
            pageInfo{ hasNextPage endCursor }
            nodes{
              id
              content{
                __typename
                ... on Issue{
                  id number state isPinned
                  labels(first:50){ nodes{ name } }
                  assignees(first:10){ nodes{ id login } }
                }
                ... on PullRequest{
                  id number state isDraft
                  labels(first:50){ nodes{ name } }
                  assignees(first:10){ nodes{ id login } }
                }
              }
            }
          }
        }
      }
    }
    """
    data=gql(q,{"id":project_id,"first":first,"after":after})
    p=data["node"]["items"]
    return p["nodes"], p["pageInfo"]["hasNextPage"], p["pageInfo"]["endCursor"]

def add_to_project(project_id, content_id):
    q="""
    mutation($projectId:ID!,$contentId:ID!){
      addProjectV2ItemById(input:{projectId:$projectId, contentId:$contentId}){
        item{ id }
      }
    }
    """
    return gql(q,{"projectId":project_id,"contentId":content_id})

def update_single_select(project_id, item_id, field_id, option_id):
    q="""
    mutation($projectId:ID!,$itemId:ID!,$fieldId:ID!,$optionId:String!){
      updateProjectV2ItemFieldValue(input:{
        projectId:$projectId, itemId:$itemId, fieldId:$fieldId,
        value:{ singleSelectOptionId:$optionId }
      }){ projectV2Item{ id } }
    }
    """
    gql(q,{"projectId":project_id,"itemId":item_id,"fieldId":field_id,"optionId":option_id})

def update_assignees(project_id, item_id, field_id, user_ids):
    q="""
    mutation($projectId:ID!,$itemId:ID!,$fieldId:ID!,$userIds:[ID!]!){
      updateProjectV2ItemFieldValue(input:{
        projectId:$projectId, itemId:$itemId, fieldId:$fieldId,
        value:{ userIds:$userIds }
      }){ projectV2Item{ id } }
    }
    """
    gql(q,{"projectId":project_id,"itemId":item_id,"fieldId":field_id,"userIds":user_ids})
