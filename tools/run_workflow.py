#!/usr/bin/env python3
"""
Workflow Runner Tool - Enhanced M1 Implementation

Executes SecFlow workflow recipes with comprehensive orchestration:
- Dry-run mode for analysis
- Actual execution with retry/backoff
- Plugin integration support
- Golden sample data for M1 testing
- StoragePort integration for findings persistence

Usage:
    python tools/run_workflow.py <recipe.yaml> [--dry-run]
    python tools/run_workflow.py <recipe.yaml> --execute
    python tools/run_workflow.py --test-sample
"""

import sys
import argparse
import json
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.workflow_engine.executor import WorkflowExecutor, WorkflowManager
from packages.workflow_engine.validate_recipe import RecipeValidator


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Execute SecFlow workflow recipes")
    parser.add_argument("recipe_path", nargs="?", help="Path to recipe YAML file")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without running tools")
    parser.add_argument("--execute", action="store_true", help="Actually execute the workflow")
    parser.add_argument("--test-sample", action="store_true", help="Test with sample workflow")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--project-id", default="test_project", help="Project ID for findings storage")
    parser.add_argument("--parallel", action="store_true", help="Use parallel execution (M3 preparation)")
    
    args = parser.parse_args()
    
    if args.test_sample:
        return test_sample_workflow(args.json, args.verbose, args.project_id)
    
    if not args.recipe_path:
        parser.print_help()
        return 1
    
    if not Path(args.recipe_path).exists():
        print(f"❌ Recipe file not found: {args.recipe_path}")
        return 1
    
    # Determine execution mode
    if args.dry_run:
        return dry_run_workflow(args.recipe_path, args.json, args.verbose)
    elif args.execute:
        return execute_workflow(args.recipe_path, args.json, args.verbose, args.project_id, args.parallel)
    else:
        # Default to dry-run if no mode specified
        return dry_run_workflow(args.recipe_path, args.json, args.verbose)


def test_sample_workflow(json_output: bool, verbose: bool, project_id: str):
    """Test with sample workflow."""
    print("🧪 Testing with sample workflow...")
    
    validator = RecipeValidator()
    executor = WorkflowExecutor()
    
    # Create and validate sample recipe
    recipe = validator.create_test_recipe("linear")
    validation_result = validator.validate(recipe)
    
    if not validation_result["ok"]:
        print("❌ Sample recipe validation failed:")
        for error in validation_result["errors"]:
            print(f"   • {error}")
        return 1
    
    print("✅ Sample recipe validation passed")
    
    # Test dry-run
    dry_run_result = executor.dry_run(recipe)
    print(f"🔍 Dry-run result: {dry_run_result}")
    
    # Test execution
    try:
        workflow = executor.load_workflow_from_yaml("workflows/sample-linear.yaml")
        execution_result = executor.execute_workflow(workflow, project_id)
        
        if json_output:
            print(json.dumps({
                "validation": validation_result,
                "dry_run": dry_run_result,
                "execution": execution_result
            }, indent=2))
        else:
            print_execution_result(execution_result, verbose)
        
        return 0 if execution_result.get("status") == "completed" else 1
        
    except Exception as e:
        print(f"❌ Sample workflow execution failed: {e}")
        return 1


def dry_run_workflow(recipe_path: str, json_output: bool, verbose: bool):
    """Perform dry-run analysis of workflow."""
    print(f"🔍 DRY RUN: {recipe_path}")
    
    try:
        executor = WorkflowExecutor()
        
        # Load recipe
        with open(recipe_path, 'r') as f:
            import yaml
            recipe_data = yaml.safe_load(f)
        
        # Perform dry-run
        result = executor.dry_run(recipe_data)
        
        if json_output:
            print(json.dumps(result, indent=2))
        else:
            print_dry_run_result(result, recipe_data, verbose)
        
        return 0 if result["ok"] else 1
        
    except Exception as e:
        print(f"❌ Dry-run failed: {e}")
        return 1


def execute_workflow(recipe_path: str, json_output: bool, verbose: bool, project_id: str, parallel: bool):
    """Execute workflow with actual orchestration."""
    print(f"🚀 EXECUTING: {recipe_path}")
    
    try:
        if parallel:
            # Use WorkflowManager for parallel execution (M3 preparation)
            manager = WorkflowManager()
            manager.prepare_for_python314()
            
            executor = WorkflowExecutor()
            workflow = executor.load_workflow_from_yaml(recipe_path)
            
            execution_id = manager.submit_workflow(workflow, project_id)
            result = manager.get_workflow_status(execution_id)
            
            print(f"📋 Execution ID: {execution_id}")
        else:
            # Sequential execution
            executor = WorkflowExecutor()
            workflow = executor.load_workflow_from_yaml(recipe_path)
            
            start_time = time.time()
            result = executor.execute_workflow(workflow, project_id)
            execution_time = time.time() - start_time
            
            result["execution_time_seconds"] = execution_time
        
        if json_output:
            print(json.dumps(result, indent=2))
        else:
            print_execution_result(result, verbose)
        
        return 0 if result.get("status") == "completed" else 1
        
    except Exception as e:
        print(f"❌ Execution error: {e}")
        return 1


def print_dry_run_result(result: dict, recipe_data: dict, verbose: bool):
    """Print dry-run results."""
    if result["ok"]:
        print("✅ Dry-run analysis PASSED")
        print(f"   Workflow: {recipe_data.get('name', 'Unknown')}")
        print(f"   Nodes: {result['nodes']}")
        print(f"   Execution order: {' → '.join(result['execution_order'])}")
        
        if verbose:
            print(f"   Validation errors: {result.get('validation_errors', [])}")
    else:
        print("❌ Dry-run analysis FAILED")
        print(f"   Validation errors: {result.get('validation_errors', [])}")


def print_execution_result(result: dict, verbose: bool):
    """Print execution results."""
    status = result.get("status", "unknown")
    workflow_id = result.get("workflow_id", "unknown")
    project_id = result.get("project_id", "unknown")
    
    if status == "completed":
        print("✅ Workflow execution COMPLETED")
        print(f"   Workflow: {workflow_id}")
        print(f"   Project: {project_id}")
        print(f"   Completed nodes: {len(result.get('completed_nodes', []))}")
        print(f"   Total findings: {result.get('total_findings', 0)}")
        print(f"   Execution time: {result.get('execution_time', 0):.2f}s")
        
        if verbose:
            completed_nodes = result.get("completed_nodes", [])
            if completed_nodes:
                print(f"   Node execution order: {' → '.join(completed_nodes)}")
    
    elif status == "failed":
        print("❌ Workflow execution FAILED")
        print(f"   Workflow: {workflow_id}")
        print(f"   Project: {project_id}")
        print(f"   Error: {result.get('error', 'Unknown error')}")
        print(f"   Failed node: {result.get('failed_node', 'Unknown')}")
        print(f"   Completed nodes: {len(result.get('completed_nodes', []))}")
        print(f"   Total findings: {result.get('total_findings', 0)}")
        
        if verbose:
            completed_nodes = result.get("completed_nodes", [])
            failed_nodes = result.get("failed_nodes", [])
            if completed_nodes:
                print(f"   Completed: {' → '.join(completed_nodes)}")
            if failed_nodes:
                print(f"   Failed: {' → '.join(failed_nodes)}")
    
    elif status == "partial":
        print("⚠️  Workflow execution PARTIAL")
        print(f"   Workflow: {workflow_id}")
        print(f"   Project: {project_id}")
        print(f"   Completed nodes: {len(result.get('completed_nodes', []))}")
        print(f"   Failed nodes: {len(result.get('failed_nodes', []))}")
        print(f"   Total findings: {result.get('total_findings', 0)}")
        
        if verbose:
            completed_nodes = result.get("completed_nodes", [])
            failed_nodes = result.get("failed_nodes", [])
            if completed_nodes:
                print(f"   Completed: {' → '.join(completed_nodes)}")
            if failed_nodes:
                print(f"   Failed: {' → '.join(failed_nodes)}")
    
    else:
        print(f"❓ Workflow execution status: {status}")


if __name__ == "__main__":
    sys.exit(main())