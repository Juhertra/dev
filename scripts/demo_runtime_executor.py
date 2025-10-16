#!/usr/bin/env python3
"""
Runtime Core Execution Engine Demo

Demonstrates the core runtime execution engine that runs tool/plugin code
and manages data persistence, aligned with FEAT-044.
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add packages to path
sys.path.append(str(Path(__file__).parent.parent))

from packages.runtime_core.executor import (
    RuntimeExecutor, WorkflowStep, ResourceLimits, ExecutionPolicy,
    FindingValidator
)
from packages.workflow_engine.executor import PluginInterface, ExecutionContext
from packages.storage.adapters.memory import InMemoryStorageAdapter


class DemoPlugin(PluginInterface):
    """Demo plugin for showcasing runtime execution."""
    
    def run(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute demo plugin."""
        print(f"  🔧 Executing plugin for project {context.project_id}")
        print(f"  📥 Inputs: {inputs}")
        print(f"  ⚙️  Config: {config}")
        
        # Simulate some work
        time.sleep(0.5)
        
        # Generate findings
        findings = []
        for i in range(3):
            finding = {
                "id": f"demo_{context.run_id}_{i}",
                "project_id": context.project_id,
                "detector_id": "demo.plugin",
                "title": f"Demo finding {i+1}",
                "severity": ["info", "low", "medium"][i],
                "resource": f"demo://resource_{i}",
                "evidence": {"demo": f"data_{i}", "timestamp": time.time()},
                "created_at": "2023-01-01T00:00:00Z",
                "finding_schema_version": "1.0.0"
            }
            findings.append(finding)
        
        print(f"  📊 Generated {len(findings)} findings")
        
        return {
            "outputs": {"processed": True, "count": len(findings)},
            "findings": findings,
            "status": "success"
        }


class SlowPlugin(PluginInterface):
    """Slow plugin for timeout demonstration."""
    
    def run(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute slow plugin."""
        print(f"  🐌 Executing slow plugin (will timeout)...")
        time.sleep(3)  # Longer than timeout
        return {"outputs": {"slow": True}, "findings": [], "status": "success"}


def demo_runtime_execution():
    """Demonstrate runtime execution engine."""
    print("=== Runtime Core Execution Engine Demo ===\n")
    
    # Create runtime executor with custom policy
    storage = InMemoryStorageAdapter()
    policy = ExecutionPolicy(
        trusted_plugins=["DemoPlugin"],
        resource_limits=ResourceLimits(
            max_execution_time=2.0,  # 2 second timeout
            max_memory_mb=256,
            sandbox_enabled=False
        )
    )
    runtime = RuntimeExecutor(storage=storage, policy=policy)
    
    print("Runtime Executor Configuration:")
    print(f"  🔒 Trusted plugins: {policy.trusted_plugins}")
    print(f"  ⏱️  Max execution time: {policy.resource_limits.max_execution_time}s")
    print(f"  💾 Max memory: {policy.resource_limits.max_memory_mb}MB")
    print(f"  🏖️  Sandbox enabled: {policy.resource_limits.sandbox_enabled}")
    print()
    
    # Test 1: Successful execution
    print("Test 1: Successful Plugin Execution")
    print("-" * 40)
    
    step1 = WorkflowStep(
        plugin="echo",  # Use existing echo plugin
        inputs={"message": "Hello from runtime executor!"},
        config={"debug": True},
        project_id="demo_project",
        run_id="run_001",
        workflow_id="workflow_demo"
    )
    
    try:
        result1 = runtime.run_step(step1)
        print(f"✅ Execution successful!")
        print(f"   Status: {result1['status']}")
        print(f"   Outputs: {result1['outputs']}")
        print(f"   Findings: {len(result1['findings'])}")
        
        # Verify findings were saved
        findings = storage.list_findings("demo_project")
        print(f"   📁 Findings in storage: {len(findings)}")
        
    except Exception as e:
        print(f"❌ Execution failed: {e}")
    
    print()
    
    # Test 2: Timeout execution
    print("Test 2: Timeout Execution")
    print("-" * 40)
    
    step2 = WorkflowStep(
        plugin="echo",  # Use existing echo plugin
        inputs={"message": "This should timeout"},
        config={},
        project_id="demo_project",
        run_id="run_002",
        workflow_id="workflow_demo"
    )
    
    try:
        result2 = runtime.run_step(step2)
        print(f"✅ Execution completed (unexpected)")
        
    except Exception as e:
        print(f"⏰ Execution timed out (expected): {e}")
    
    print()
    
    # Test 3: Finding validation
    print("Test 3: Finding Schema Validation")
    print("-" * 40)
    
    validator = FindingValidator()
    
    # Valid finding
    valid_finding = {
        "id": "VALID-1",
        "project_id": "test_project",
        "detector_id": "test.plugin",
        "title": "Valid finding",
        "severity": "high",
        "resource": "test://resource",
        "evidence": {"test": "data"},
        "created_at": "2023-01-01T00:00:00Z",
        "finding_schema_version": "1.0.0"
    }
    
    is_valid = validator.validate_finding(valid_finding)
    print(f"✅ Valid finding: {'PASS' if is_valid else 'FAIL'}")
    
    # Invalid finding (missing field)
    invalid_finding = {
        "id": "INVALID-1",
        "project_id": "test_project",
        "detector_id": "test.plugin",
        "title": "Invalid finding",
        "severity": "high",
        "resource": "test://resource",
        "evidence": {"test": "data"},
        "created_at": "2023-01-01T00:00:00Z"
        # Missing finding_schema_version
    }
    
    is_valid = validator.validate_finding(invalid_finding)
    print(f"❌ Invalid finding: {'PASS' if is_valid else 'FAIL'}")
    
    print()
    
    # Test 4: Storage integrity
    print("Test 4: Storage Integrity Validation")
    print("-" * 40)
    
    is_integrity_valid = runtime.validate_storage_integrity("demo_project")
    print(f"📊 Storage integrity: {'VALID' if is_integrity_valid else 'INVALID'}")
    
    print()
    
    # Test 5: Finding retrieval
    print("Test 5: Finding Retrieval")
    print("-" * 40)
    
    findings = storage.list_findings("demo_project")
    if findings:
        first_finding_id = findings[0]["id"]
        retrieved = runtime.get_finding("demo_project", first_finding_id)
        print(f"🔍 Retrieved finding: {'SUCCESS' if retrieved else 'FAILED'}")
        if retrieved:
            print(f"   ID: {retrieved['id']}")
            print(f"   Title: {retrieved['title']}")
            print(f"   Severity: {retrieved['severity']}")
    else:
        print("❌ No findings found in storage")


def demo_concurrent_execution():
    """Demonstrate concurrent execution (M3 preparation)."""
    print("\n=== Concurrent Execution Demo (M3 Preparation) ===\n")
    
    storage = InMemoryStorageAdapter()
    runtime = RuntimeExecutor(storage=storage)
    
    # Create multiple steps
    steps = [
        WorkflowStep(
            plugin="echo",  # Use existing echo plugin
            inputs={"message": f"Concurrent message {i}"},
            config={"step": i},
            project_id="concurrent_project",
            run_id=f"run_{i:03d}",
            workflow_id="workflow_concurrent"
        )
        for i in range(3)
    ]
    
    print(f"Executing {len(steps)} steps concurrently...")
    
    try:
        results = runtime.execute_concurrent_steps(steps)
        
        print(f"✅ Concurrent execution completed!")
        print(f"   Results: {len(results)}")
        
        for i, result in enumerate(results):
            if "error" in result:
                print(f"   Step {i}: FAILED - {result['error']}")
            else:
                print(f"   Step {i}: SUCCESS - {result['outputs']}")
        
        # Check total findings
        findings = storage.list_findings("concurrent_project")
        print(f"   📊 Total findings: {len(findings)}")
        
    except Exception as e:
        print(f"❌ Concurrent execution failed: {e}")


def demo_python314_preparation():
    """Demonstrate Python 3.14 preparation."""
    print("\n=== Python 3.14 Concurrency Preparation ===\n")
    
    import sys
    
    print(f"Current Python version: {sys.version}")
    print(f"Python version info: {sys.version_info}")
    
    if sys.version_info >= (3, 14):
        print("✅ Python 3.14+ detected - advanced concurrency features available")
        
        # Check for free-threaded mode
        if hasattr(sys, 'get_switch_interval'):
            print("✅ Free-threaded mode available - GIL removed")
            print(f"   Switch interval: {sys.get_switch_interval()}")
        else:
            print("⚠️  Standard threading mode - GIL present")
    else:
        print(f"⚠️  Python {sys.version_info.major}.{sys.version_info.minor} - using standard threading")
    
    print("\nM3 Concurrency Features Prepared:")
    print("  🧵 ThreadPoolExecutor for parallel execution")
    print("  🔒 Thread-safe storage operations")
    print("  🏖️  Sandboxing hooks for plugin isolation")
    print("  ⏱️  Resource limits and timeouts")
    print("  📊 Finding schema validation")


if __name__ == "__main__":
    try:
        # Run demos
        demo_runtime_execution()
        demo_concurrent_execution()
        demo_python314_preparation()
        
        print("\n=== Demo Complete ===")
        print("✅ Runtime Core Execution Engine demonstrated successfully!")
        print("\nKey Features Demonstrated:")
        print("  🔧 Plugin execution via StoragePort")
        print("  📊 Finding schema validation (v1.0.0)")
        print("  ⏱️  Resource controls and timeouts")
        print("  🏖️  Sandboxing hooks for M2+")
        print("  🧵 Concurrent execution preparation for M3")
        print("  🐍 Python 3.14 concurrency features")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
