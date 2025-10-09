#!/usr/bin/env python3
"""
Workflow Runner Tool

Executes SecFlow workflow recipes.
Usage: python3 tools/run_workflow.py <recipe.yaml> [--dry-run]
"""

import sys
import yaml
import os
import argparse
from pathlib import Path

# Add packages to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from packages.workflow_engine.executor import WorkflowExecutor, Workflow, WorkflowNode
except ImportError:
    print("Warning: Could not import WorkflowExecutor from packages.workflow_engine")
    WorkflowExecutor = None
    Workflow = None
    WorkflowNode = None


def load_workflow(recipe_path):
    """Load workflow from YAML file."""
    with open(recipe_path, 'r', encoding='utf-8') as f:
        recipe_data = yaml.safe_load(f)
    
    # Convert to Workflow model if available
    if Workflow and WorkflowNode:
        nodes = []
        for node_data in recipe_data.get('nodes', []):
            node = WorkflowNode(
                id=node_data['id'],
                type=node_data['type'],
                config=node_data.get('config', {}),
                inputs=node_data.get('inputs', []),
                outputs=node_data.get('outputs', [])
            )
            nodes.append(node)
        
        workflow = Workflow(
            id=f"workflow_{recipe_data['name'].lower().replace(' ', '_')}",
            name=recipe_data['name'],
            description=recipe_data.get('description', ''),
            nodes=nodes
        )
        return workflow, recipe_data
    else:
        return recipe_data, recipe_data


def dry_run_workflow(workflow_data):
    """Simulate workflow execution without actually running tools."""
    print(f"🔍 DRY RUN: {workflow_data['name']}")
    print(f"📝 Description: {workflow_data.get('description', 'N/A')}")
    print(f"📊 Nodes: {len(workflow_data.get('nodes', []))}")
    print()
    
    nodes = workflow_data.get('nodes', [])
    for i, node in enumerate(nodes, 1):
        print(f"  {i}. {node['id']} ({node['type']})")
        if node.get('inputs'):
            print(f"     📥 Inputs: {', '.join(node['inputs'])}")
        if node.get('outputs'):
            print(f"     📤 Outputs: {', '.join(node['outputs'])}")
        if node.get('config'):
            print(f"     ⚙️  Config: {node['config']}")
        print()
    
    # Show retry configuration
    retry_config = workflow_data.get('retry', {})
    if retry_config:
        print("🔄 Retry Configuration:")
        print(f"   Max attempts: {retry_config.get('max_attempts', 1)}")
        print(f"   Backoff factor: {retry_config.get('backoff_factor', 1.0)}")
        print(f"   Base delay: {retry_config.get('base_delay', 1.0)}s")
        print()
    
    # Show state configuration
    state_config = workflow_data.get('state', {})
    if state_config:
        print("💾 State Configuration:")
        print(f"   Checkpoint interval: {state_config.get('checkpoint_interval', 0)}s")
        print(f"   Resume on failure: {state_config.get('resume_on_failure', False)}")
        print(f"   Cache intermediate: {state_config.get('cache_intermediate', False)}")
        print()
    
    print("✅ Dry run completed - no actual execution performed")


def execute_workflow(workflow, recipe_data):
    """Execute workflow using WorkflowExecutor."""
    if not WorkflowExecutor:
        print("❌ WorkflowExecutor not available - cannot execute workflow", file=sys.stderr)
        return 1
    
    executor = WorkflowExecutor()
    
    # Validate workflow
    if not executor.validate_workflow(workflow):
        print("❌ Workflow validation failed", file=sys.stderr)
        return 1
    
    print(f"🚀 Executing workflow: {workflow.name}")
    
    # Execute workflow
    result = executor.execute_workflow(workflow)
    
    if result.get('status') == 'not_implemented':
        print("⚠️  Workflow execution not implemented yet (M3)")
        print("   This is expected for M0 scaffolding")
        return 0
    
    print(f"✅ Workflow execution completed: {result}")
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Execute SecFlow workflow recipes')
    parser.add_argument('recipe', help='Path to workflow recipe YAML file')
    parser.add_argument('--dry-run', action='store_true', help='Simulate execution without running tools')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.recipe):
        print(f"Error: Recipe file {args.recipe} not found", file=sys.stderr)
        return 1
    
    try:
        workflow, recipe_data = load_workflow(args.recipe)
        
        if args.dry_run:
            dry_run_workflow(recipe_data)
            return 0
        else:
            return execute_workflow(workflow, recipe_data)
            
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
