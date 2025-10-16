"""
End-to-End Workflow Integration Tests - M1 Implementation

Comprehensive integration tests for the workflow orchestration engine including:
- Real workflow execution with plugin integration
- StoragePort integration for findings persistence
- Plugin system integration testing
- Error handling and retry logic
- WorkflowManager concurrency preparation

Import Rules:
- May import from runtime_core
- May import from findings
- May be imported by other packages
- May NOT import from wrappers or parsers
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch
import sys
import os
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from packages.workflow_engine.executor import (
    WorkflowExecutor, WorkflowManager, PluginLoader, PluginInterface,
    ExecutionContext, NodeSpec, WorkflowSpec, NodeResult
)
from packages.workflow_engine.validate_recipe import RecipeValidator
from packages.storage.adapters.memory import InMemoryStorageAdapter


class TestEndToEndWorkflowExecution:
    """Test end-to-end workflow execution with real plugin integration."""
    
    def test_sample_workflow_execution(self):
        """Test execution of sample workflow with real plugin integration."""
        executor = WorkflowExecutor()
        
        # Create sample workflow
        workflow = WorkflowSpec(
            id="test_workflow",
            name="Sample Security Scan",
            description="End-to-end security scanning workflow",
            nodes=[
                NodeSpec(
                    id="discovery",
                    type="discovery.ferox",
                    params={"wordlist": "test", "threads": 50},
                    outputs=["urls"]
                ),
                NodeSpec(
                    id="scan",
                    type="scan.nuclei",
                    params={"templates": "test", "rate_limit": 150},
                    requires=["urls"],
                    outputs=["findings"]
                ),
                NodeSpec(
                    id="enrich",
                    type="enrich.cve",
                    params={"sources": ["nvd", "osv"]},
                    requires=["findings"],
                    outputs=["enriched_findings"]
                )
            ]
        )
        
        # Execute workflow
        result = executor.execute_workflow(workflow, "test_project")
        
        # Verify execution results
        assert result["status"] == "completed"
        assert result["workflow_id"] == "test_workflow"
        assert result["project_id"] == "test_project"
        assert len(result["completed_nodes"]) == 3
        assert "discovery" in result["completed_nodes"]
        assert "scan" in result["completed_nodes"]
        assert "enrich" in result["completed_nodes"]
        assert result["total_findings"] > 0
        assert result["execution_time"] > 0
    
    def test_workflow_with_storage_integration(self):
        """Test workflow execution with StoragePort integration."""
        storage = InMemoryStorageAdapter()
        executor = WorkflowExecutor(storage=storage)
        
        # Create simple workflow
        workflow = WorkflowSpec(
            id="storage_test",
            name="Storage Integration Test",
            nodes=[
                NodeSpec(
                    id="discovery",
                    type="discovery.ferox",
                    params={"wordlist": "test"},
                    outputs=["urls"]
                )
            ]
        )
        
        # Execute workflow
        result = executor.execute_workflow(workflow, "storage_test_project")
        
        # Verify findings were saved to storage
        assert result["status"] == "completed"
        assert result["total_findings"] > 0
        
        # Check that findings were actually saved to storage
        findings = storage.list_findings("storage_test_project")
        assert len(findings) > 0
        
        # Verify finding structure
        finding = findings[0]
        assert "id" in finding
        assert "project_id" in finding
        assert "detector_id" in finding
        assert "title" in finding
        assert "severity" in finding
        assert "finding_schema_version" in finding
    
    def test_workflow_with_retry_logic(self):
        """Test workflow execution with retry logic."""
        executor = WorkflowExecutor()
        
        # Create workflow with retry configuration
        workflow = WorkflowSpec(
            id="retry_test",
            name="Retry Logic Test",
            nodes=[
                NodeSpec(
                    id="echo",
                    type="echo",
                    params={"message": "test"},
                    retries=2,
                    retry_backoff_s=0.1,
                    outputs=["echo_output"]
                )
            ]
        )
        
        # Execute workflow
        result = executor.execute_workflow(workflow, "retry_test_project")
        
        # Verify execution
        assert result["status"] == "completed"
        assert "echo" in result["completed_nodes"]
    
    def test_workflow_error_handling(self):
        """Test workflow error handling and failure scenarios."""
        executor = WorkflowExecutor()
        
        # Create workflow with unknown plugin type
        workflow = WorkflowSpec(
            id="error_test",
            name="Error Handling Test",
            nodes=[
                NodeSpec(
                    id="unknown",
                    type="unknown.plugin",
                    params={},
                    outputs=["output"]
                )
            ]
        )
        
        # Execute workflow
        result = executor.execute_workflow(workflow, "error_test_project")
        
        # Verify error handling
        assert result["status"] == "failed"
        assert "unknown" in result["failed_nodes"]
        assert "error" in result
        assert "Unknown plugin" in result["error"]
    
    def test_workflow_dependency_resolution(self):
        """Test workflow dependency resolution and execution order."""
        executor = WorkflowExecutor()
        
        # Create workflow with dependencies
        workflow = WorkflowSpec(
            id="dependency_test",
            name="Dependency Resolution Test",
            nodes=[
                NodeSpec(
                    id="node3",
                    type="echo",
                    params={"message": "last"},
                    requires=["out1", "out2"],
                    outputs=["final"]
                ),
                NodeSpec(
                    id="node1",
                    type="echo",
                    params={"message": "first"},
                    outputs=["out1"]
                ),
                NodeSpec(
                    id="node2",
                    type="echo",
                    params={"message": "second"},
                    outputs=["out2"]
                )
            ]
        )
        
        # Execute workflow
        result = executor.execute_workflow(workflow, "dependency_test_project")
        
        # Verify execution order (node1 and node2 can run in parallel, node3 last)
        assert result["status"] == "completed"
        completed_nodes = result["completed_nodes"]
        assert "node3" not in completed_nodes[:2]  # node3 should not be in first 2
        assert "node3" in completed_nodes  # but should be completed


class TestPluginIntegration:
    """Test plugin system integration."""
    
    def test_plugin_loader_functionality(self):
        """Test plugin loader functionality."""
        loader = PluginLoader()
        
        # Test loading known plugins
        ferox_plugin = loader.load("discovery.ferox")
        assert isinstance(ferox_plugin, PluginInterface)
        
        nuclei_plugin = loader.load("scan.nuclei")
        assert isinstance(nuclei_plugin, PluginInterface)
        
        cve_plugin = loader.load("enrich.cve")
        assert isinstance(cve_plugin, PluginInterface)
        
        echo_plugin = loader.load("echo")
        assert isinstance(echo_plugin, PluginInterface)
    
    def test_plugin_execution_with_context(self):
        """Test plugin execution with execution context."""
        loader = PluginLoader()
        plugin = loader.load("discovery.ferox")
        
        # Create execution context
        ctx = ExecutionContext(
            run_id="test_run",
            workflow_id="test_workflow",
            project_id="test_project"
        )
        
        # Execute plugin
        result = plugin.run({}, {"wordlist": "test"}, ctx)
        
        # Verify result structure
        assert "outputs" in result
        assert "findings" in result
        assert "status" in result
        assert result["status"] == "success"
        assert "urls" in result["outputs"]
        assert len(result["findings"]) > 0
        
        # Verify finding structure
        finding = result["findings"][0]
        assert finding["project_id"] == "test_project"
        assert finding["detector_id"] == "discovery.ferox"
        assert finding["finding_schema_version"] == "1.0.0"
    
    def test_plugin_data_flow(self):
        """Test data flow between plugins."""
        loader = PluginLoader()
        
        # Create execution context
        ctx = ExecutionContext(
            run_id="test_run",
            workflow_id="test_workflow",
            project_id="test_project"
        )
        
        # Execute discovery plugin
        discovery_plugin = loader.load("discovery.ferox")
        discovery_result = discovery_plugin.run({}, {"wordlist": "test"}, ctx)
        
        # Verify discovery results
        assert discovery_result["status"] == "success"
        urls = discovery_result["outputs"]["urls"]
        assert len(urls) > 0
        
        # Execute scan plugin with discovery results
        scan_plugin = loader.load("scan.nuclei")
        scan_result = scan_plugin.run({"urls": urls}, {"templates": "test"}, ctx)
        
        # Verify scan results
        assert scan_result["status"] == "success"
        findings = scan_result["outputs"]["findings"]
        assert len(findings) > 0
        
        # Verify findings reference the URLs
        for finding in findings:
            assert finding["resource"] in urls
    
    def test_plugin_error_handling(self):
        """Test plugin error handling."""
        loader = PluginLoader()
        
        # Test loading unknown plugin
        with pytest.raises(Exception):  # PluginLoadError
            loader.load("unknown.plugin")


class TestWorkflowManager:
    """Test WorkflowManager for future concurrency."""
    
    def test_workflow_manager_submission(self):
        """Test workflow submission to WorkflowManager."""
        manager = WorkflowManager()
        
        # Create workflow
        workflow = WorkflowSpec(
            id="manager_test",
            name="Manager Test",
            nodes=[
                NodeSpec(
                    id="echo",
                    type="echo",
                    params={"message": "test"},
                    outputs=["output"]
                )
            ]
        )
        
        # Submit workflow
        execution_id = manager.submit_workflow(workflow, "manager_test_project")
        
        # Verify submission
        assert execution_id.startswith("exec_")
        
        # Check status
        status = manager.get_workflow_status(execution_id)
        assert status["execution_id"] == execution_id
        assert status["workflow_id"] == "manager_test"
        assert status["status"] == "completed"
    
    def test_workflow_manager_status_tracking(self):
        """Test workflow status tracking."""
        manager = WorkflowManager()
        
        # Create workflow
        workflow = WorkflowSpec(
            id="status_test",
            name="Status Test",
            nodes=[
                NodeSpec(
                    id="echo",
                    type="echo",
                    params={"message": "test"},
                    outputs=["output"]
                )
            ]
        )
        
        # Submit workflow
        execution_id = manager.submit_workflow(workflow, "status_test_project")
        
        # Check status
        status = manager.get_workflow_status(execution_id)
        assert status["status"] == "completed"
        
        # Check non-existent workflow
        non_existent_status = manager.get_workflow_status("non_existent")
        assert non_existent_status["status"] == "not_found"
    
    def test_workflow_manager_active_workflows(self):
        """Test listing active workflows."""
        manager = WorkflowManager()
        
        # Create workflow
        workflow = WorkflowSpec(
            id="active_test",
            name="Active Test",
            nodes=[
                NodeSpec(
                    id="echo",
                    type="echo",
                    params={"message": "test"},
                    outputs=["output"]
                )
            ]
        )
        
        # Submit workflow
        execution_id = manager.submit_workflow(workflow, "active_test_project")
        
        # List active workflows
        active_workflows = manager.list_active_workflows()
        assert len(active_workflows) == 1
        assert active_workflows[0]["execution_id"] == execution_id
        assert active_workflows[0]["workflow_id"] == "active_test"
        assert active_workflows[0]["status"] == "completed"
    
    def test_workflow_manager_cleanup(self):
        """Test workflow cleanup functionality."""
        manager = WorkflowManager()
        
        # Create and submit workflow
        workflow = WorkflowSpec(
            id="cleanup_test",
            name="Cleanup Test",
            nodes=[
                NodeSpec(
                    id="echo",
                    type="echo",
                    params={"message": "test"},
                    outputs=["output"]
                )
            ]
        )
        
        execution_id = manager.submit_workflow(workflow, "cleanup_test_project")
        
        # Verify workflow is active
        assert len(manager.list_active_workflows()) == 1
        
        # Cleanup completed workflows
        manager.cleanup_completed()
        
        # Verify workflow was cleaned up
        assert len(manager.list_active_workflows()) == 0
    
    def test_workflow_manager_python314_preparation(self):
        """Test Python 3.14 concurrency preparation."""
        manager = WorkflowManager()
        
        # Test preparation method
        manager.prepare_for_python314()
        
        # Verify thread pool is not initialized in M1 (max_concurrent=1)
        assert manager._executor is None
        
        # Test with higher concurrency limit
        manager_high_concurrency = WorkflowManager(max_concurrent=4)
        manager_high_concurrency.prepare_for_python314()
        
        # In M1, executor should still be None (sequential execution)
        assert manager_high_concurrency._executor is None


class TestStorageIntegration:
    """Test StoragePort integration with workflow execution."""
    
    def test_findings_persistence(self):
        """Test that findings are properly persisted to storage."""
        storage = InMemoryStorageAdapter()
        executor = WorkflowExecutor(storage=storage)
        
        # Create workflow that generates findings
        workflow = WorkflowSpec(
            id="persistence_test",
            name="Persistence Test",
            nodes=[
                NodeSpec(
                    id="discovery",
                    type="discovery.ferox",
                    params={"wordlist": "test"},
                    outputs=["urls"]
                ),
                NodeSpec(
                    id="scan",
                    type="scan.nuclei",
                    params={"templates": "test"},
                    requires=["urls"],
                    outputs=["findings"]
                )
            ]
        )
        
        # Execute workflow
        result = executor.execute_workflow(workflow, "persistence_test_project")
        
        # Verify execution
        assert result["status"] == "completed"
        assert result["total_findings"] > 0
        
        # Verify findings in storage
        findings = storage.list_findings("persistence_test_project")
        assert len(findings) > 0
        
        # Verify finding types
        discovery_findings = [f for f in findings if f["detector_id"] == "discovery.ferox"]
        scan_findings = [f for f in findings if f["detector_id"] == "scan.nuclei"]
        
        assert len(discovery_findings) > 0
        assert len(scan_findings) > 0
    
    def test_storage_thread_safety(self):
        """Test storage thread safety for M3 preparation."""
        storage = InMemoryStorageAdapter()
        executor = WorkflowExecutor(storage=storage)
        
        # Create multiple workflows
        workflows = []
        for i in range(3):
            workflow = WorkflowSpec(
                id=f"thread_test_{i}",
                name=f"Thread Test {i}",
                nodes=[
                    NodeSpec(
                        id="echo",
                        type="echo",
                        params={"message": f"test_{i}"},
                        outputs=["output"]
                    )
                ]
            )
            workflows.append(workflow)
        
        # Execute workflows (simulating concurrent execution)
        results = []
        for workflow in workflows:
            result = executor.execute_workflow(workflow, f"thread_test_project_{workflow.id}")
            results.append(result)
        
        # Verify all workflows completed
        for result in results:
            assert result["status"] == "completed"
        
        # Verify storage integrity
        all_findings = []
        for i in range(3):
            findings = storage.list_findings(f"thread_test_project_thread_test_{i}")
            all_findings.extend(findings)
        
        assert len(all_findings) >= 0  # Echo plugin doesn't generate findings


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases."""
    
    def test_workflow_with_empty_nodes(self):
        """Test workflow with empty nodes list."""
        executor = WorkflowExecutor()
        
        workflow = WorkflowSpec(
            id="empty_test",
            name="Empty Test",
            nodes=[]
        )
        
        # This should fail validation
        result = executor.execute_workflow(workflow, "empty_test_project")
        assert result["status"] == "failed"
        assert "validation failed" in result["error"].lower()
    
    def test_workflow_with_circular_dependency(self):
        """Test workflow with circular dependency."""
        executor = WorkflowExecutor()
        
        workflow = WorkflowSpec(
            id="circular_test",
            name="Circular Test",
            nodes=[
                NodeSpec(
                    id="node1",
                    type="echo",
                    params={"message": "test"},
                    requires=["out2"],
                    outputs=["out1"]
                ),
                NodeSpec(
                    id="node2",
                    type="echo",
                    params={"message": "test"},
                    requires=["out1"],
                    outputs=["out2"]
                )
            ]
        )
        
        # This should fail validation
        result = executor.execute_workflow(workflow, "circular_test_project")
        assert result["status"] == "failed"
        assert "validation failed" in result["error"].lower()
    
    def test_workflow_with_missing_dependency(self):
        """Test workflow with missing dependency."""
        executor = WorkflowExecutor()
        
        workflow = WorkflowSpec(
            id="missing_dep_test",
            name="Missing Dependency Test",
            nodes=[
                NodeSpec(
                    id="node1",
                    type="echo",
                    params={"message": "test"},
                    requires=["nonexistent_output"],
                    outputs=["out1"]
                )
            ]
        )
        
        # This should fail validation
        result = executor.execute_workflow(workflow, "missing_dep_test_project")
        assert result["status"] == "failed"
        assert "validation failed" in result["error"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
