#!/usr/bin/env python3
import json, sys, pathlib, re
from datetime import datetime
ROOT = pathlib.Path(__file__).resolve().parents[1]
J = ROOT / "control" / "journal" / "agents"
EVENTS = {"sod","mid","eod","note","handoff","decision"}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Load baseline configuration
def load_baseline():
    baseline_file = ROOT / "control" / "config" / "journals_baseline.json"
    if baseline_file.exists():
        with open(baseline_file) as f:
            config = json.load(f)
            return datetime.fromisoformat(config["baseline_ts"].replace("Z", "+00:00"))
    return None

BASELINE_TS = load_baseline()

def is_pre_baseline(ts_str):
    """Check if timestamp is before baseline (legacy event)."""
    if not BASELINE_TS:
        return False
    try:
        event_ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return event_ts < BASELINE_TS
    except:
        return False

# Enhanced validation patterns
ITEMS_MAX_LENGTH = 12  # Maximum number of items
ITEM_MAX_CHARS = 200   # Maximum characters per item
LINK_PATTERN = re.compile(r'^(PR#\d+|FEAT-\d+|Issue#\d+|SHA:[a-f0-9]{7,40}|https?://[^\s]+|[a-zA-Z0-9_./-]+\.(py|md|yml|yaml|json|ndjson)|[a-zA-Z0-9_./-]+/|commit:[a-f0-9]{7,40}|[a-zA-Z0-9_-]+@[a-zA-Z0-9._-]+|[a-zA-Z0-9_-]+ configuration|\.coveragerc|actions/[a-zA-Z0-9_-]+@[a-zA-Z0-9._-]+|[a-zA-Z0-9_./-]+)$')

def validate_items(items, file_path, line_num):
    """Validate items array length and individual item length."""
    violations = []
    
    if len(items) > ITEMS_MAX_LENGTH:
        violations.append(f"::error::{file_path}:{line_num} items array too long: {len(items)} > {ITEMS_MAX_LENGTH}")
    
    for i, item in enumerate(items):
        if len(item) > ITEM_MAX_CHARS:
            violations.append(f"::error::{file_path}:{line_num} item[{i}] too long: {len(item)} > {ITEM_MAX_CHARS} chars")
    
    return violations

def validate_links(links, file_path, line_num):
    """Validate links array format."""
    violations = []
    
    for i, link in enumerate(links):
        if not LINK_PATTERN.match(link):
            violations.append(f"::error::{file_path}:{line_num} link[{i}] invalid format: '{link}' (expected PR#/FEAT-###/SHA/URL)")
    
    return violations

def validate_handoff_requirements(rec, file_path, line_num):
    """Validate handoff-specific requirements."""
    violations = []
    
    if rec.get("event") == "handoff":
        items = rec.get("items", [])
        links = rec.get("links", [])
        
        # Check for @tags in items
        has_tags = any("@" in item for item in items)
        if not has_tags:
            violations.append(f"::error::{file_path}:{line_num} handoff missing @tags in items")
        
        # Check for actionable links
        if not links:
            violations.append(f"::error::{file_path}:{line_num} handoff missing actionable links")
    
    return violations

def main():
    ok=True
    violations = []
    
    for p in J.rglob("*.ndjson"):
        role = p.parent.parent.name
        for i, line in enumerate(p.read_text().splitlines(), 1):
            try: 
                rec = json.loads(line)
            except Exception as e: 
                violations.append(f"::error::{p}:{i} not JSON: {e}")
                ok=False
                continue
            
            # Basic validation
            if rec.get("role") != role: 
                violations.append(f"::error::{p}:{i} role mismatch")
                ok=False
            
            if rec.get("event") not in EVENTS: 
                violations.append(f"::error::{p}:{i} bad event: {rec.get('event')}")
                ok=False
            
            if not DATE.match(rec.get("period","")): 
                violations.append(f"::error::{p}:{i} bad period: {rec.get('period')}")
                ok=False
            
            if "items" in rec and not isinstance(rec["items"], list): 
                violations.append(f"::error::{p}:{i} items not list")
                ok=False
            elif "items" in rec and not is_pre_baseline(rec.get("ts", "")):
                # Only apply strict validation to post-baseline events
                item_violations = validate_items(rec["items"], p, i)
                violations.extend(item_violations)
                if item_violations: ok=False
            
            if "links" in rec and not isinstance(rec["links"], list): 
                violations.append(f"::error::{p}:{i} links not list")
                ok=False
            elif "links" in rec and not is_pre_baseline(rec.get("ts", "")):
                # Only apply strict validation to post-baseline events
                link_violations = validate_links(rec["links"], p, i)
                violations.extend(link_violations)
                if link_violations: ok=False
            
            # Handoff-specific validation (only for post-baseline events)
            if not is_pre_baseline(rec.get("ts", "")):
                handoff_violations = validate_handoff_requirements(rec, p, i)
                violations.extend(handoff_violations)
                if handoff_violations: ok=False
    
    # Print all violations
    for violation in violations:
        print(violation)
    
    sys.exit(0 if ok else 1)

if __name__=="__main__": main()
