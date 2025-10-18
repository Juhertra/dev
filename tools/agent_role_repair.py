#!/usr/bin/env python3
import os, json, requests, sys, re, yaml
from project_gql import (
  get_project_id_by_title, get_or_create_text_field,
  iter_items, set_text_field
)

TITLE = os.getenv("PROJECT_TITLE","SecFlow")
TOKEN = os.getenv("PROJECTS_TOKEN") or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
if not TOKEN: raise SystemExit("Missing token")
REST = "https://api.github.com"
HDR = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github+json"}
AGENT_FIELD_NAME = os.getenv("AGENT_FIELD_NAME","Agent Role")

def add_label(owner, repo, num, name):
    """Add a label to an issue/PR"""
    try:
        requests.post(f"{REST}/repos/{owner}/{repo}/issues/{num}/labels",
                      headers=HDR, json={"labels":[name]})
        return True
    except Exception as e:
        print(f"Failed to add label {name} to {owner}/{repo}#{num}: {e}")
        return False

def remove_label(owner, repo, num, name):
    """Remove a label from an issue/PR"""
    try:
        requests.delete(f"{REST}/repos/{owner}/{repo}/issues/{num}/labels/{name}",
                        headers=HDR)
        return True
    except Exception as e:
        print(f"Failed to remove label {name} from {owner}/{repo}#{num}: {e}")
        return False

def create_label(name, description="", color="ededed"):
    """Create a label if it doesn't exist"""
    try:
        requests.post(f"{REST}/repos/Juhertra/dev/labels",
                      headers=HDR, json={"name":name, "description":description, "color":color})
        return True
    except Exception as e:
        if "already exists" in str(e).lower():
            return True  # Label already exists
        print(f"Failed to create label {name}: {e}")
        return False

def compute_role_from_evidence(content, area_role_map):
    """
    Compute role from evidence using deterministic rules.
    Evidence order (strongest → weakest):
    1. Owner section → first @<role> mention
    2. Handoff titles → recipient role
    3. Explicit role:* labels → first one
    4. Area→Role map (fallback only)
    
    Returns (role, reason) or (None, "no_evidence")
    """
    title = content.get("title", "")
    body = content.get("body", "")
    labels = [l["name"] for l in content["labels"]["nodes"]]
    
    # Evidence 1: Owner section (STRONGEST)
    # Look for Owner section followed by @role (may be on different lines)
    owner_match = re.search(r'Owner.*?@([a-z-]+)', body, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    if owner_match:
        role = owner_match.group(1)
        # Validate it's a role tag (ends with -lead or is coordinator)
        if role.endswith('-lead') or role == 'coordinator':
            return role, "owner section"
    
    # Evidence 2: Handoff title pattern
    # ^\[handoff\]\s*(?<role>[a-z-]+): → use <role>
    handoff_match = re.search(r'^\[handoff\]\s*([a-z-]+):', title, re.IGNORECASE)
    if handoff_match:
        role = handoff_match.group(1)
        return role, "handoff title"
    
    # Evidence 3: Body Role line
    # ^Role:\s*(?<role>[a-z-]+) (case-insensitive)
    role_match = re.search(r'^Role:\s*([a-z-]+)', body, re.IGNORECASE | re.MULTILINE)
    if role_match:
        role = role_match.group(1)
        return role, "body role"
    
    # Evidence 4: Existing role:* labels
    role_labels = [l for l in labels if l.startswith("role:")]
    if len(role_labels) == 1:
        role = role_labels[0].split(":", 1)[1]
        return role, "single role label"
    elif len(role_labels) > 1:
        # Multiple role labels - check context
        title_body = (title + " " + body).lower()
        
        # Try to find the most relevant role based on context
        for role_label in role_labels:
            role = role_label.split(":", 1)[1]
            if role in title_body:
                return role, f"contextual role label ({role_label})"
        
        # If no context match, return first one but mark as ambiguous
        role = role_labels[0].split(":", 1)[1]
        return role, f"ambiguous role labels ({', '.join(role_labels)})"
    
    # Evidence 5: Area→Role map (FALLBACK ONLY)
    title_body = (title + " " + body).lower()
    for area, role in area_role_map.items():
        if area.lower() in title_body:
            return role, f"area mapping ({area})"
    
    return None, "no evidence"

def load_area_role_map(map_path):
    """Load area-to-role mapping from YAML file"""
    try:
        with open(map_path, 'r') as f:
            data = yaml.safe_load(f)
            return data.get('area_to_role', {})
    except Exception as e:
        print(f"Warning: Could not load area-role map from {map_path}: {e}")
        return {}

def normalize_role(role):
    """Normalize role name to standard format"""
    if not role:
        return None
    
    # Convert to lowercase and ensure proper format
    role = role.lower().strip()
    
    # Map common variations
    role_map = {
        'devx': 'devex-lead',
        'devx-lead': 'devex-lead',
        'dev': 'devex-lead',
        'dev-lead': 'devex-lead',
        'coord': 'coordinator',
        'sec': 'security-lead',
        'sec-lead': 'security-lead',
        'run': 'runtime-lead',
        'run-lead': 'runtime-lead',
        'tool': 'tools-lead',
        'tool-lead': 'tools-lead',
        'obs': 'observability-lead',
        'obs-lead': 'observability-lead',
        'doc': 'docs-lead',
        'doc-lead': 'docs-lead',
        'ops': 'devops-lead',
        'ops-lead': 'devops-lead'
    }
    
    return role_map.get(role, role)

def main():
    dry_run = "--dry-run" in sys.argv
    apply_mode = "--apply" in sys.argv
    report_path = None
    area_map_path = None
    project_id = None
    
    # Parse command line arguments
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--report" and i + 1 < len(sys.argv):
            report_path = sys.argv[i + 1]
            i += 2
        elif arg == "--area-map" and i + 1 < len(sys.argv):
            area_map_path = sys.argv[i + 1]
            i += 2
        elif arg == "--project" and i + 1 < len(sys.argv):
            project_id = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    if not dry_run and not apply_mode:
        print("Usage: python tools/agent_role_repair.py [--dry-run|--apply] [--report <path>] [--area-map <path>] [--project <id>]")
        sys.exit(1)
    
    # Load area-role mapping
    area_role_map = {}
    if area_map_path:
        area_role_map = load_area_role_map(area_map_path)
    
    # Get project ID
    if not project_id:
        project_id = get_project_id_by_title(TITLE)
    
    agent_field_id = get_or_create_text_field(project_id, AGENT_FIELD_NAME)
    
    stats = {
        "scanned": 0,
        "agent_role_set": 0,
        "agent_role_cleared": 0,
        "labels_added": 0,
        "conflicts_found": 0,
        "ambiguous": [],
        "no_evidence": [],
        "samples": [],
        "conflicts": []
    }
    
    for it in iter_items(project_id):
        c = it.get("content")
        if not c: continue
        
        stats["scanned"] += 1
        owner = c["repository"]["owner"]["login"]
        repo = c["repository"]["name"]
        num = c["number"]
        
        # Get current agent role value
        fv = it["fieldValues"]["nodes"]
        current_agent_text = None
        for n in fv:
            if n["__typename"]=="ProjectV2ItemFieldTextValue" and n["field"]["name"]==AGENT_FIELD_NAME:
                current_agent_text = n.get("text")
        
        # Compute role from evidence
        computed_role, reason = compute_role_from_evidence(c, area_role_map)
        normalized_role = normalize_role(computed_role)
        
        # Get current role labels
        labels = [l["name"] for l in c["labels"]["nodes"]]
        current_role_labels = [l for l in labels if l.startswith("role:")]
        
        # Determine what to do
        action_taken = None
        new_agent_role = None
        label_changes = []
        conflict_detected = False
        
        if normalized_role:
            # We have evidence for a role
            if normalized_role != current_agent_text:
                new_agent_role = normalized_role
                if current_agent_text:
                    action_taken = "replaced"
                else:
                    action_taken = "set"
            
            # Check for conflicts with existing role labels
            expected_label = f"role:{normalized_role}"
            if current_role_labels and expected_label not in current_role_labels:
                # Conflict detected - don't change labels, just log
                conflict_detected = True
                stats["conflicts_found"] += 1
                stats["conflicts"].append({
                    "id": f"#{num}",
                    "title": c["title"][:50] + "..." if len(c["title"]) > 50 else c["title"],
                    "computed_role": normalized_role,
                    "existing_labels": current_role_labels,
                    "reason": reason
                })
            elif not current_role_labels:
                # No existing role labels - add the correct one
                label_changes.append(f"add:{expected_label}")
        
        elif current_agent_text:
            # No evidence but currently has a role - clear it
            new_agent_role = None
            action_taken = "cleared"
            stats["no_evidence"].append(f"#{num}")
        
        # Track ambiguous cases
        if "ambiguous" in reason:
            stats["ambiguous"].append(f"#{num}")
        
        # Apply changes if not dry run
        if apply_mode and not dry_run:
            if new_agent_role != current_agent_text:
                if new_agent_role:
                    set_text_field(project_id, it["id"], agent_field_id, new_agent_role)
                    if action_taken == "set":
                        stats["agent_role_set"] += 1
                    elif action_taken == "replaced":
                        stats["agent_role_set"] += 1
                else:
                    set_text_field(project_id, it["id"], agent_field_id, "")
                    stats["agent_role_cleared"] += 1
            
            # Apply label changes (only if no conflict)
            if not conflict_detected:
                for change in label_changes:
                    if change.startswith("add:"):
                        label_name = change[4:]
                        create_label(label_name)  # Ensure it exists
                        add_label(owner, repo, num, label_name)
                        stats["labels_added"] += 1
        
        # Add to samples if there was a change or it's interesting
        if action_taken or normalized_role or len(current_role_labels) > 1:
            sample = {
                "id": f"#{num}",
                "title": c["title"][:50] + "..." if len(c["title"]) > 50 else c["title"],
                "agent_role_to": normalized_role,
                "from_labels": current_role_labels,
                "reason": reason,
                "action": action_taken
            }
            stats["samples"].append(sample)
    
    # Limit samples to most interesting ones
    stats["samples"] = stats["samples"][:20]
    
    # Write report
    if report_path:
        with open(report_path, "w") as f:
            json.dump(stats, f, indent=2)
    
    # Write conflicts report
    if stats["conflicts"]:
        os.makedirs("reports/devex", exist_ok=True)
        with open("reports/devex/agent-role-conflicts.json", "w") as f:
            json.dump(stats["conflicts"], f, indent=2)
    
    # Print summary
    mode = "DRY RUN" if dry_run else "APPLIED"
    print(f"\n=== Agent Role Repair {mode} ===")
    print(f"Scanned: {stats['scanned']} items")
    print(f"Agent Role set: {stats['agent_role_set']}")
    print(f"Agent Role cleared: {stats['agent_role_cleared']}")
    print(f"Labels added: {stats['labels_added']}")
    print(f"Conflicts found: {stats['conflicts_found']}")
    print(f"Ambiguous: {len(stats['ambiguous'])} items")
    print(f"No evidence: {len(stats['no_evidence'])} items")
    
    if stats['ambiguous']:
        print(f"\nAmbiguous items: {', '.join(stats['ambiguous'])}")
    if stats['no_evidence']:
        print(f"No evidence items: {', '.join(stats['no_evidence'])}")
    if stats['conflicts']:
        print(f"\nConflicts detected (see reports/devex/agent-role-conflicts.json):")
        for conflict in stats['conflicts'][:5]:  # Show first 5
            print(f"  {conflict['id']}: computed={conflict['computed_role']}, existing={conflict['existing_labels']}")

if __name__ == "__main__":
    main()
