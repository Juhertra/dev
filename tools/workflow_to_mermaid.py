#!/usr/bin/env python3
"""
Workflow DAG Generator

Converts SecFlow workflow recipe YAML files into Mermaid flowcharts.
Usage: python3 tools/workflow_to_mermaid.py workflows/recipe.yaml
"""

import sys
import yaml
import os
from pathlib import Path

def as_id(n: str) -> str:
    """Convert node ID to valid Mermaid identifier."""
    return n.replace("-", "_").replace(".", "_")

def main(path):
    """Generate Mermaid flowchart from workflow recipe."""
    if not os.path.exists(path):
        print(f"Error: File {path} not found", file=sys.stderr)
        sys.exit(1)
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}", file=sys.stderr)
        sys.exit(1)
    
    nodes = data.get("nodes", [])
    if not nodes:
        print("Error: No nodes found in workflow recipe", file=sys.stderr)
        sys.exit(1)
    
    print("```mermaid")
    print("%%{init: {'theme':'neutral'}}%%")
    print("flowchart LR")
    
    # Define nodes
    for n in nodes:
        nid = as_id(n["id"])
        node_type = n.get("type", "unknown")
        outputs = n.get("outputs", [])
        label = f"{node_type}\\n(outputs: {', '.join(outputs)})"
        print(f'  {nid}["{label}"]')
    
    # Connect by IO sets
    prod_map = {}
    for n in nodes:
        for out in n.get("outputs", []):
            prod_map.setdefault(out, []).append(n["id"])
    
    for n in nodes:
        for inp in n.get("inputs", []):
            for src in prod_map.get(inp, []):
                src_id = as_id(src)
                dst_id = as_id(n["id"])
                print(f"  {src_id} --> {dst_id}")
    
    print("```")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 workflow_to_mermaid.py <recipe.yaml>", file=sys.stderr)
        sys.exit(1)
    
    main(sys.argv[1])
