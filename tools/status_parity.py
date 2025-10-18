#!/usr/bin/env python3
import os, sys, json
from project_gql import gql, get_project_fields, iter_items, update_single_select

def get_status_labels(labels):
    """Extract status:* labels from a list of label names."""
    return [label["name"] for label in labels if label["name"].startswith("status:")]

def compute_desired_status(content, labels):
    """Compute the desired status based on content state and labels."""
    status_labels = get_status_labels(labels)
    
    # Priority order: explicit status labels > content state
    if "status:Done" in status_labels:
        return "Done"
    elif "status:In Progress" in status_labels:
        return "In Progress"
    elif "status:Blocked" in status_labels:
        return "Blocked"
    elif "status:Todo" in status_labels:
        return "Todo"
    
    # Fallback to content state
    if content["__typename"] == "PullRequest":
        if content["merged"]:
            return "Done"
        elif content["isDraft"]:
            return "Todo"
        elif content["state"] == "OPEN":
            return "In Progress"
        else:
            return "Done"
    elif content["__typename"] == "Issue":
        if content["state"] == "CLOSED":
            return "Done"
        else:
            return "Todo"
    
    return "Todo"

def sync_project_status(project_id):
    """Sync status field and labels for all items in the project."""
    print(f"Syncing project {project_id}...")
    
    # Get project fields
    fields = get_project_fields(project_id)
    status_field = fields.get("status")
    if not status_field:
        print("No 'Status' field found in project")
        return {"error": "No Status field found"}
    
    # Get status field options
    status_options = {opt["name"]: opt["id"] for opt in status_field["options"]}
    print(f"Status options: {list(status_options.keys())}")
    
    stats = {
        "total_items": 0,
        "updated_status": 0,
        "updated_labels": 0,
        "errors": 0,
        "status_counts": {},
        "label_counts": {}
    }
    
    # Iterate through all items
    after = None
    while True:
        items, has_next, after = iter_items(project_id, after=after)
        
        for item in items:
            stats["total_items"] += 1
            content = item["content"]
            
            if not content:
                continue
                
            labels = content["labels"]["nodes"]
            desired_status = compute_desired_status(content, labels)
            
            # Update status counts
            stats["status_counts"][desired_status] = stats["status_counts"].get(desired_status, 0) + 1
            
            # Update label counts
            for label in labels:
                label_name = label["name"]
                stats["label_counts"][label_name] = stats["label_counts"].get(label_name, 0) + 1
            
            # Check current status field value
            current_status = None
            for field_value in item["fieldValues"]["nodes"]:
                if field_value.get("field", {}).get("name", "").lower() == "status":
                    current_status = field_value.get("name")
                    break
            
            # Update status field if needed
            if current_status != desired_status:
                if desired_status in status_options:
                    try:
                        update_single_select(
                            project_id, 
                            item["id"], 
                            status_field["id"], 
                            status_options[desired_status]
                        )
                        stats["updated_status"] += 1
                        print(f"Updated {content['__typename']} #{content['number']}: {current_status} -> {desired_status}")
                    except Exception as e:
                        print(f"Error updating status for {content['__typename']} #{content['number']}: {e}")
                        stats["errors"] += 1
                else:
                    print(f"Warning: Status '{desired_status}' not found in project options")
                    stats["errors"] += 1
        
        if not has_next:
            break
    
    return stats

def main():
    project_id = os.getenv("PROJECTS_V2_ID")
    if not project_id:
        print("Error: PROJECTS_V2_ID environment variable not set")
        sys.exit(1)
    
    print(f"Starting status parity sync for project {project_id}")
    stats = sync_project_status(project_id)
    
    print("\n=== SYNC RESULTS ===")
    print(json.dumps(stats, indent=2))
    
    return stats

if __name__ == "__main__":
    main()
