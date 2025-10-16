#!/usr/bin/env python3
"""
Workflow Execution Engine Demo

Demonstrates the M1 workflow execution engine with sequential execution,
StoragePort integration, and retry logic.
"""

import sys
import os
from pathlib import Path

# Add packages to path
sys.path.append(str(Path(__file__).parent))

from packages.workflow_engine.executor import WorkflowExecutor, WorkflowSpec, NodeSpec
from packages.storage.adapters.memory import InMemoryStorageAdapter


def demo_workflow_execution():
    """Demonstrate workflow execution with data passing."""
    print("=== Workflow Execution Engine Demo ===\n")
    
    # Create workflow executor
    storage = InMemoryStorageAdapter()
    executor = WorkflowExecutor(storage)
    
    # Create a simple workflow: discovery -> scan -> enrich
    workflow = WorkflowSpec(
        id="demo_workflow",
        name="Security Scan Demo",
        description="Demonstrates discovery, scanning, and enrichment",
        nodes=[
            NodeSpec(
                id="discovery",
                type="discovery.ferox",
                params={"wordlist": "common", "threads": 50}
            ),
            NodeSpec(
                id="scan",
                type="scan.nuclei",
                requires=["discovery"],
                params={"templates": "owasp-top10", "rate_limit": 150}
            ),
            NodeSpec(
                id="enrich",
                type="enrich.cve",
                requires=["scan"],
                params={"sources": ["nvd", "osv"]}
            )
        ]
    )
    
    print("Workflow Definition:")
    print(f"  ID: {workflow.id}")
    print(f"  Name: {workflow.name}")
    print(f"  Description: {workflow.description}")
    print(f"  Nodes: {len(workflow.nodes)}")
    for node in workflow.nodes:
        print(f"    - {node.id} ({node.type})")
        if node.requires:
            print(f"      Requires: {node.requires}")
        if node.params:
            print(f"      Params: {node.params}")
    print()
    
    # Validate workflow
    print("Validating workflow...")
    is_valid = executor.validate_workflow(workflow)
    print(f"  Validation: {'✅ PASSED' if is_valid else '❌ FAILED'}")
    
    if not is_valid:
        print("Workflow validation failed. Exiting.")
        return
    
    # Execute workflow
    print("\nExecuting workflow...")
    result = executor.execute_workflow(workflow)
    
    print(f"\nExecution Result:")
    print(f"  Status: {result['status']}")
    print(f"  Workflow ID: {result['workflow_id']}")
    print(f"  Completed Nodes: {result['completed_nodes']}")
    print(f"  Failed Nodes: {result['failed_nodes']}")
    
    if result['status'] == 'completed':
        print("\n✅ Workflow completed successfully!")
        print("\nData Flow Summary:")
        print("  discovery -> scan -> enrich")
        print("  URLs discovered -> Findings generated -> CVE enrichment")
    else:
        print(f"\n❌ Workflow failed: {result.get('error', 'Unknown error')}")
    
    return result


def demo_workflow_validation():
    """Demonstrate workflow validation features."""
    print("\n=== Workflow Validation Demo ===\n")
    
    executor = WorkflowExecutor()
    
    # Test 1: Valid workflow
    print("Test 1: Valid linear workflow")
    valid_workflow = WorkflowSpec(
        id="valid",
        name="Valid Workflow",
        nodes=[
            NodeSpec(id="node1", type="test.type1"),
            NodeSpec(id="node2", type="test.type2", requires=["node1"]),
            NodeSpec(id="node3", type="test.type3", requires=["node2"])
        ]
    )
    is_valid = executor.validate_workflow(valid_workflow)
    print(f"  Result: {'✅ VALID' if is_valid else '❌ INVALID'}")
    
    # Test 2: Cycle detection
    print("\nTest 2: Cycle detection")
    cyclic_workflow = WorkflowSpec(
        id="cyclic",
        name="Cyclic Workflow",
        nodes=[
            NodeSpec(id="node1", type="test.type1", requires=["node2"]),
            NodeSpec(id="node2", type="test.type2", requires=["node1"])
        ]
    )
    is_valid = executor.validate_workflow(cyclic_workflow)
    print(f"  Result: {'✅ VALID' if is_valid else '❌ INVALID (cycle detected)'}")
    
    # Test 3: Duplicate IDs
    print("\nTest 3: Duplicate node IDs")
    duplicate_workflow = WorkflowSpec(
        id="duplicate",
        name="Duplicate IDs",
        nodes=[
            NodeSpec(id="duplicate", type="test.type1"),
            NodeSpec(id="duplicate", type="test.type2")
        ]
    )
    is_valid = executor.validate_workflow(duplicate_workflow)
    print(f"  Result: {'✅ VALID' if is_valid else '❌ INVALID (duplicate IDs)'}")
    
    # Test 4: Unknown dependencies
    print("\nTest 4: Unknown dependencies")
    unknown_deps_workflow = WorkflowSpec(
        id="unknown",
        name="Unknown Dependencies",
        nodes=[
            NodeSpec(id="node1", type="test.type1", requires=["nonexistent"])
        ]
    )
    is_valid = executor.validate_workflow(unknown_deps_workflow)
    print(f"  Result: {'✅ VALID' if is_valid else '❌ INVALID (unknown dependencies)'}")


def demo_dry_run():
    """Demonstrate dry run functionality."""
    print("\n=== Dry Run Demo ===\n")
    
    executor = WorkflowExecutor()
    
    # Test dry run with valid workflow
    recipe = {
        "version": "1.0",
        "name": "Dry Run Test",
        "description": "Testing dry run functionality",
        "nodes": [
            {
                "id": "prepare",
                "type": "echo",
                "config": {"message": "preparing"}
            },
            {
                "id": "execute",
                "type": "echo",
                "inputs": ["prepare"],
                "config": {"message": "executing"}
            },
            {
                "id": "cleanup",
                "type": "echo",
                "inputs": ["execute"],
                "config": {"message": "cleaning up"}
            }
        ]
    }
    
    print("Dry Run Test:")
    print("  Recipe: prepare -> execute -> cleanup")
    
    result = executor.dry_run(recipe)
    
    print(f"\nDry Run Result:")
    print(f"  Valid: {'✅ YES' if result['ok'] else '❌ NO'}")
    print(f"  Nodes: {result['nodes']}")
    print(f"  Execution Order: {result['execution_order']}")
    if result['validation_errors']:
        print(f"  Errors: {result['validation_errors']}")


if __name__ == "__main__":
    try:
        # Run demos
        demo_workflow_execution()
        demo_workflow_validation()
        demo_dry_run()
        
        print("\n=== Demo Complete ===")
        print("✅ All workflow execution features demonstrated successfully!")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
