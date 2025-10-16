#!/usr/bin/env python3
"""
Recipe Validation Tool - Enhanced M1 Implementation

This tool validates workflow recipes with comprehensive checks:
- YAML syntax validation
- Schema validation
- DAG structure validation
- Reference consistency validation
- Node type validation
- Configuration validation

Usage:
    python tools/validate_recipe.py <recipe.yaml>
    python tools/validate_recipe.py --test-valid
    python tools/validate_recipe.py --test-invalid
"""

import sys
import argparse
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.workflow_engine.validate_recipe import RecipeValidator, RecipeValidationError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Validate workflow recipes")
    parser.add_argument("recipe_path", nargs="?", help="Path to recipe YAML file")
    parser.add_argument("--test-valid", action="store_true", help="Test with valid recipe")
    parser.add_argument("--test-invalid", action="store_true", help="Test with invalid recipe")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    validator = RecipeValidator()
    
    if args.test_valid:
        # Test with valid recipe
        recipe = validator.create_test_recipe("linear")
        result = validator.validate(recipe)
        print("Testing with valid recipe:")
        print_result(result, args.json, args.verbose)
        return 0 if result["ok"] else 1
    
    elif args.test_invalid:
        # Test with invalid recipe
        recipe = validator.create_test_recipe("invalid")
        result = validator.validate(recipe)
        print("Testing with invalid recipe:")
        print_result(result, args.json, args.verbose)
        return 0 if not result["ok"] else 1
    
    elif args.recipe_path:
        # Validate specified recipe file
        result = validator.validate_file(args.recipe_path)
        print(f"Validating recipe: {args.recipe_path}")
        print_result(result, args.json, args.verbose)
        return 0 if result["ok"] else 1
    
    else:
        parser.print_help()
        return 1


def print_result(result: dict, json_output: bool, verbose: bool):
    """Print validation results."""
    if json_output:
        print(json.dumps(result, indent=2))
        return
    
    if result["ok"]:
        print("✅ Recipe validation PASSED")
        print(f"   Workflow: {result.get('workflow_name', 'Unknown')}")
        print(f"   Nodes: {result['nodes']}")
        print(f"   Execution order: {' → '.join(result['execution_order'])}")
        
        if verbose and result.get("validation_details"):
            print("\nValidation details:")
            for check, status in result["validation_details"].items():
                print(f"   {check}: {status}")
    else:
        print("❌ Recipe validation FAILED")
        print(f"   Errors: {len(result['errors'])}")
        for error in result["errors"]:
            print(f"   • {error}")
        
        if result.get("warnings"):
            print(f"   Warnings: {len(result['warnings'])}")
            for warning in result["warnings"]:
                print(f"   ⚠ {warning}")


if __name__ == "__main__":
    sys.exit(main())