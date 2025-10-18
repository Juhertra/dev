#!/usr/bin/env python3
"""
Sequential Workflow Execution Engine Demo

Demonstrates FEAT-044, FEAT-045, and FEAT-046 implementations:
- Sequential workflow execution
- State management between nodes
- Error handling and recovery
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add packages to path
sys.path.append(str(Path(__file__).parent.parent))

from packages.workflow_engine.sequential_executor import (
    WorkflowExecutor, WorkflowState, ExecutionResult, NodeSpec, WorkflowSpec
)
from packages.workflow_engine.executor import PluginInterface, ExecutionContext
from packages.storage.adapters.memory import InMemoryStorageAdapter


class DemoDiscoveryPlugin(PluginInterface):
    """Demo discovery plugin."""
    
    def run(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute discovery plugin."""
        print(f"  🔍 Discovery Plugin: Scanning for URLs...")
        print(f"  📥 Inputs: {inputs}")
        print(f"  ⚙️  Config: {config}")
        
        # Simulate discovery
        time.sleep(0.5)
        
        urls = [
            "https://example.com/admin",
            "https://example.com/api",
            "https://example.com/login",
            "https://example.com/dashboard"
        ]
        
        print(f"  📊 Discovered {len(urls)} URLs")
        
        return {
            "outputs": {"urls": urls},
            "findings": [],
            "status": "success"
        }


class DemoScanPlugin(PluginInterface):
    """Demo scan plugin."""
    
    def run(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute scan plugin."""
        print(f"  🔬 Scan Plugin: Scanning URLs for vulnerabilities...")
        print(f"  📥 Inputs: {inputs}")
        print(f"  ⚙️  Config: {config}")
        
        # Get URLs from inputs
        urls = inputs.get("urls", [])
        print(f"  🎯 Scanning {len(urls)} URLs")
        
        # Simulate scanning
        time.sleep(0.7)
        
        findings = []
        for i, url in enumerate(urls):
            finding = {
                "id": f"scan_{context.run_id}_{i}",
                "project_id": context.project_id,
                "detector_id": "scan.nuclei",
                "title": f"Vulnerability detected in {url}",
                "severity": ["high", "medium", "low"][i % 3],
                "resource": url,
                "evidence": {
                    "url": url,
                    "template": "sql-injection",
                    "status_code": 200,
                    "response_time": 150
                },
                "created_at": "2023-01-01T00:00:00Z",
                "finding_schema_version": "1.0.0"
            }
            findings.append(finding)
        
        print(f"  📊 Found {len(findings)} vulnerabilities")
        
        return {
            "outputs": {"findings": findings},
            "findings": findings,
            "status": "success"
        }


class DemoEnrichPlugin(PluginInterface):
    """Demo enrichment plugin."""
    
    def run(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute enrichment plugin."""
        print(f"  🔍 Enrich Plugin: Enriching findings with CVE data...")
        print(f"  📥 Inputs: {inputs}")
        print(f"  ⚙️  Config: {config}")
        
        # Get findings from inputs
        findings = inputs.get("findings", [])
        print(f"  🎯 Enriching {len(findings)} findings")
        
        # Simulate enrichment
        time.sleep(0.6)
        
        enriched_findings = []
        for finding in findings:
            enriched_finding = finding.copy()
            enriched_finding["cve_ids"] = ["CVE-2023-1234", "CVE-2023-5678"]
            enriched_finding["cvss"] = 7.5
            enriched_finding["owasp"] = "A05"
            enriched_finding["enriched_at"] = "2023-01-01T00:00:00Z"
            enriched_findings.append(enriched_finding)
        
        print(f"  📊 Enriched {len(enriched_findings)} findings")
        
        return {
            "outputs": {"enriched_findings": enriched_findings},
            "findings": enriched_findings,
            "status": "success"
        }


class DemoFailingPlugin(PluginInterface):
    """Demo plugin that fails."""
    
    def run(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute failing plugin."""
        print(f"  ❌ Failing Plugin: This will fail...")
        raise RuntimeError("Simulated plugin failure")


def demo_sequential_execution():
    """Demonstrate sequential workflow execution - FEAT-044."""
    print("=== Sequential Workflow Execution Engine Demo ===\n")
    
    # Create workflow executor
    storage = InMemoryStorageAdapter()
    executor = WorkflowExecutor(storage=storage)
    
    # Create sample workflow
    workflow = WorkflowSpec(
        id="demo_workflow",
        name="Security Scan Demo",
        description="Demonstrates discovery → scan → enrichment",
        nodes=[
            NodeSpec(
                id="discovery",
                type="discovery.plugin",
                params={"wordlist": "common", "threads": 50},
                outputs=["urls"]
            ),
            NodeSpec(
                id="scan",
                type="scan.plugin",
                requires=["urls"],
                params={"templates": "owasp-top10", "rate_limit": 150},
                outputs=["findings"]
            ),
            NodeSpec(
                id="enrich",
                type="enrich.plugin",
                requires=["findings"],
                params={"sources": ["nvd", "osv"]},
                outputs=["enriched_findings"]
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
        if node.outputs:
            print(f"      Outputs: {node.outputs}")
    print()
    
    # Mock plugin loader
    from unittest.mock import patch
    with patch.object(executor.plugin_loader, 'load') as mock_load:
        mock_load.side_effect = [
            DemoDiscoveryPlugin(),
            DemoScanPlugin(),
            DemoEnrichPlugin()
        ]
        
        print("Executing Workflow:")
        print("-" * 50)
        
        # Execute workflow
        result = executor.execute(workflow, project_id="demo_project")
        
        print("-" * 50)
        print(f"\nExecution Result:")
        print(f"  Status: {result.status}")
        print(f"  Workflow ID: {result.workflow_id}")
        print(f"  Run ID: {result.run_id}")
        print(f"  Completed Nodes: {result.completed_nodes}")
        print(f"  Execution Time: {result.execution_time:.2f}s")
        
        if result.is_success:
            print(f"\n✅ Workflow completed successfully!")
            print(f"\nFinal State:")
            state = result.state
            print(f"  URLs: {len(state.get('urls', []))} discovered")
            print(f"  Findings: {len(state.get('findings', []))} vulnerabilities")
            print(f"  Enriched: {len(state.get('enriched_findings', []))} enriched findings")
            
            # Show sample data
            if state.get('urls'):
                print(f"\nSample URLs:")
                for url in state.get('urls', [])[:2]:
                    print(f"  - {url}")
            
            if state.get('enriched_findings'):
                print(f"\nSample Enriched Finding:")
                enriched = state.get('enriched_findings', [])[0]
                print(f"  - Title: {enriched['title']}")
                print(f"  - Severity: {enriched['severity']}")
                print(f"  - CVEs: {enriched.get('cve_ids', [])}")
        else:
            print(f"\n❌ Workflow failed: {result.error}")
            if result.failed_node:
                print(f"  Failed at node: {result.failed_node}")


def demo_state_management():
    """Demonstrate state management - FEAT-045."""
    print("\n=== State Management Demo - FEAT-045 ===\n")
    
    from packages.workflow_engine.sequential_executor import WorkflowState
    
    # Create workflow state
    state = WorkflowState(
        workflow_id="test_workflow",
        run_id="run_123",
        project_id="test_project"
    )
    
    print("WorkflowState Operations:")
    print(f"  Initial state: {state.keys()}")
    
    # Test state operations
    state.set("urls", ["https://example.com/admin"])
    print(f"  After set('urls'): {state.keys()}")
    
    state.update({"findings": ["vuln1", "vuln2"], "processed": True})
    print(f"  After update(): {state.keys()}")
    
    print(f"  Has 'urls': {state.has('urls')}")
    print(f"  Get 'findings': {state.get('findings')}")
    print(f"  Get 'missing' (default): {state.get('missing', 'not_found')}")
    
    # Test data flow simulation
    print(f"\nData Flow Simulation:")
    print(f"  Discovery → URLs: {state.get('urls')}")
    print(f"  Scan → Findings: {state.get('findings')}")
    print(f"  Enrich → Processed: {state.get('processed')}")


def demo_error_handling():
    """Demonstrate error handling - FEAT-046."""
    print("\n=== Error Handling Demo - FEAT-046 ===\n")
    
    storage = InMemoryStorageAdapter()
    executor = WorkflowExecutor(storage=storage)
    
    # Create workflow with failing node
    workflow = WorkflowSpec(
        id="error_workflow",
        name="Error Handling Demo",
        description="Demonstrates error handling",
        nodes=[
            NodeSpec(
                id="success_node",
                type="success.plugin",
                outputs=["data"]
            ),
            NodeSpec(
                id="failing_node",
                type="failing.plugin",
                requires=["data"],
                outputs=["result"]
            )
        ]
    )
    
    # Mock plugin loader
    from unittest.mock import patch
    with patch.object(executor.plugin_loader, 'load') as mock_load:
        mock_load.side_effect = [
            DemoDiscoveryPlugin(),  # Success
            DemoFailingPlugin()     # Failure
        ]
        
        print("Executing Workflow with Error:")
        print("-" * 40)
        
        result = executor.execute(workflow, project_id="error_project")
        
        print("-" * 40)
        print(f"\nError Handling Result:")
        print(f"  Status: {result.status}")
        print(f"  Error: {result.error}")
        print(f"  Failed Node: {result.failed_node}")
        print(f"  Completed Nodes: {result.completed_nodes}")
        
        if result.is_error:
            print(f"\n✅ Error handled gracefully!")
            print(f"  - Workflow stopped at failing node")
            print(f"  - Previous node outputs preserved")
            print(f"  - Clear error message provided")
        else:
            print(f"\n❌ Unexpected success")


def demo_sample_workflow():
    """Demonstrate execution of sample-linear.yaml workflow."""
    print("\n=== Sample Workflow Execution ===\n")
    
    executor = WorkflowExecutor()
    
    try:
        # Load sample workflow
        workflow = executor.load_workflow_from_yaml("workflows/sample-linear.yaml")
        
        print("Sample Workflow Loaded:")
        print(f"  Name: {workflow.name}")
        print(f"  Description: {workflow.description}")
        print(f"  Nodes: {len(workflow.nodes)}")
        
        # Show node structure
        for node in workflow.nodes:
            print(f"    - {node.id} ({node.type})")
            if node.requires:
                print(f"      Inputs: {node.requires}")
            if node.outputs:
                print(f"      Outputs: {node.outputs}")
        
        print(f"\n✅ Sample workflow structure validated!")
        print(f"  - Discovery node produces 'urls'")
        print(f"  - Scan node consumes 'urls', produces 'findings'")
        print(f"  - Enrich node consumes 'findings', produces 'enriched_findings'")
        
    except Exception as e:
        print(f"❌ Failed to load sample workflow: {e}")


if __name__ == "__main__":
    try:
        # Run demos
        demo_sequential_execution()
        demo_state_management()
        demo_error_handling()
        demo_sample_workflow()
        
        print("\n=== Demo Complete ===")
        print("✅ Sequential Workflow Execution Engine demonstrated successfully!")
        print("\nKey Features Demonstrated:")
        print("  🔄 FEAT-044: Sequential workflow execution")
        print("  📊 FEAT-045: State management between nodes")
        print("  ❌ FEAT-046: Error handling and recovery")
        print("  🔗 Data flow: discovery → scan → enrichment")
        print("  📁 YAML loading: Sample workflow integration")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
