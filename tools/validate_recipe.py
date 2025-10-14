#!/usr/bin/env python3
"""
Recipe Validation Tool

Validates SecFlow workflow recipe YAML files.
Usage: python3 tools/validate_recipe.py <recipe.yaml>
"""

import sys
import yaml
import os
from pathlib import Path

# Add packages to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from packages.workflow_engine.validator import RecipeValidator, RecipeValidationError
except ImportError:
    print("Warning: Could not import RecipeValidator from packages.workflow_engine")
    RecipeValidator = None
    RecipeValidationError = Exception


def main(recipe_path):
    """Validate workflow recipe."""
    if not os.path.exists(recipe_path):
        print(f"Error: Recipe file {recipe_path} not found", file=sys.stderr)
        return 1
    
    try:
        # Basic YAML validation
        with open(recipe_path, 'r', encoding='utf-8') as f:
            recipe_data = yaml.safe_load(f)
        
        print(f"✅ YAML syntax valid: {recipe_path}")
        
        # Schema validation
        required_fields = ['version', 'name', 'nodes']
        for field in required_fields:
            if field not in recipe_data:
                print(f"❌ Missing required field: {field}", file=sys.stderr)
                return 1
        
        print(f"✅ Schema validation passed: {recipe_data['name']}")
        
        # DAG validation
        nodes = recipe_data.get('nodes', [])
        if not nodes:
            print("❌ No nodes found in workflow", file=sys.stderr)
            return 1
        
        # Check for circular dependencies and unresolved inputs
        node_ids = [node['id'] for node in nodes]
        all_outputs = []
        for node in nodes:
            all_outputs.extend(node.get('outputs', []))
        
        for node in nodes:
            for inp in node.get('inputs', []):
                if inp not in all_outputs:
                    print(f"❌ Unresolved input '{inp}' in node {node['id']}", file=sys.stderr)
                    return 1
        
        print(f"✅ DAG validation passed: {len(nodes)} nodes")
        
        # Use RecipeValidator if available
        if RecipeValidator:
            validator = RecipeValidator()
            valid, error = validator.validate_recipe(recipe_path)
            if not valid:
                print(f"❌ RecipeValidator error: {error}", file=sys.stderr)
                return 1
            print("✅ RecipeValidator validation passed")
        
        print(f"🎯 Recipe validation successful: {recipe_data['name']}")
        return 0
        
    except yaml.YAMLError as e:
        print(f"❌ YAML parsing error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Validation error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 tools/validate_recipe.py <recipe.yaml>", file=sys.stderr)
        sys.exit(1)
    
    sys.exit(main(sys.argv[1]))
