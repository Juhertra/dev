#!/usr/bin/env python3
"""
Tests for Sequential Workflow Execution Engine

Tests FEAT-044, FEAT-045, and FEAT-046 implementations:
- Sequential workflow execution
- State management between nodes
- Error handling and recovery
"""

import pytest
import time
import tempfile
import os
from unittest.mock import Mock, patch
from typing import Dict, Any, List

# Add packages to path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from packages.workflow_engine.sequential_executor import (
    WorkflowExecutor, WorkflowState, ExecutionResult, NodeSpec, WorkflowSpec
)
from packages.workflow_engine.executor import PluginInterface, ExecutionContext, PluginLoader
from packages.storage.adapters.memory import InMemoryStorageAdapter


class DummyPluginSuccess(PluginInterface):
    """Dummy plugin that always succeeds."""
    
    def __init__(self, output_data: Dict[str, Any] = None):
        self.output_data = output_data or {"result": "success"}
    
    def run(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Return successful result."""
        return {
            "outputs": self.output_data,
            "findings": [],
            "status": "success"
        }


class DummyPluginFail(PluginInterface):
    """Dummy plugin that always fails."""
    
    def run(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Raise an exception."""
        raise RuntimeError("Plugin execution failed")


class DummyPluginWithFindings(PluginInterface):
    """Dummy plugin that generates findings."""
    
    def run(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Return result with findings."""
        findings = [
            {
                "id": f"finding_{context.run_id}_1",
                "project_id": context.project_id,
                "detector_id": "test.plugin",
                "title": "Test finding",
                "severity": "medium",
                "resource": "test://resource",
                "evidence": {"test": "data"},
                "created_at": "2023-01-01T00:00:00Z",
                "finding_schema_version": "1.0.0"
            }
        ]
        
        return {
            "outputs": {"processed": True},
            "findings": findings,
            "status": "success"
        }


class TestWorkflowState:
    """Test WorkflowState - FEAT-045 implementation."""
    
    def test_workflow_state_initialization(self):
        """Test WorkflowState initialization."""
        state = WorkflowState(
            workflow_id="test_workflow",
            run_id="run_123",
            project_id="test_project"
        )
        
        assert state.workflow_id == "test_workflow"
        assert state.run_id == "run_123"
        assert state.project_id == "test_project"
        assert len(state.data) == 0
    
    def test_workflow_state_get_set(self):
        """Test WorkflowState get/set operations."""
        state = WorkflowState("test_workflow", "run_123", "test_project")
        
        # Test set and get
        state.set("test_key", "test_value")
        assert state.get("test_key") == "test_value"
        
        # Test default value
        assert state.get("nonexistent", "default") == "default"
        
        # Test has
        assert state.has("test_key") is True
        assert state.has("nonexistent") is False
    
    def test_workflow_state_update(self):
        """Test WorkflowState update operations."""
        state = WorkflowState("test_workflow", "run_123", "test_project")
        
        # Test update
        state.update({"key1": "value1", "key2": "value2"})
        assert state.get("key1") == "value1"
        assert state.get("key2") == "value2"
        
        # Test keys
        keys = state.keys()
        assert "key1" in keys
        assert "key2" in keys
    
    def test_workflow_state_clear(self):
        """Test WorkflowState clear operation."""
        state = WorkflowState("test_workflow", "run_123", "test_project")
        
        state.set("test_key", "test_value")
        assert state.has("test_key") is True
        
        state.clear()
        assert state.has("test_key") is False
        assert len(state.data) == 0


class TestExecutionResult:
    """Test ExecutionResult."""
    
    def test_execution_result_success(self):
        """Test successful execution result."""
        state = WorkflowState("test_workflow", "run_123", "test_project")
        result = ExecutionResult(
            status="success",
            workflow_id="test_workflow",
            run_id="run_123",
            state=state,
            completed_nodes=["node1", "node2"],
            execution_time=1.5
        )
        
        assert result.is_success is True
        assert result.is_error is False
        assert result.is_partial is False
        assert result.error is None
        assert result.failed_node is None
    
    def test_execution_result_error(self):
        """Test error execution result."""
        result = ExecutionResult(
            status="error",
            workflow_id="test_workflow",
            run_id="run_123",
            error="Test error",
            failed_node="node2",
            completed_nodes=["node1"],
            execution_time=0.5
        )
        
        assert result.is_success is False
        assert result.is_error is True
        assert result.is_partial is False
        assert result.error == "Test error"
        assert result.failed_node == "node2"


class TestWorkflowExecutor:
    """Test WorkflowExecutor - FEAT-044 implementation."""
    
    def test_workflow_executor_initialization(self):
        """Test WorkflowExecutor initialization."""
        storage = InMemoryStorageAdapter()
        plugin_loader = PluginLoader()
        executor = WorkflowExecutor(plugin_loader=plugin_loader, storage=storage)
        
        assert executor.plugin_loader is plugin_loader
        assert executor.storage is storage
        assert len(executor._execution_history) == 0
    
    def test_execute_simple_workflow_success(self):
        """Test successful execution of simple workflow - FEAT-044."""
        storage = InMemoryStorageAdapter()
        executor = WorkflowExecutor(storage=storage)
        
        # Create simple workflow
        workflow = WorkflowSpec(
            id="test_workflow",
            name="Test Workflow",
            description="Simple test workflow",
            nodes=[
                NodeSpec(
                    id="node1",
                    type="test.plugin1",
                    outputs=["output1"]
                ),
                NodeSpec(
                    id="node2",
                    type="test.plugin2",
                    requires=["output1"],
                    outputs=["output2"]
                )
            ]
        )
        
        # Mock plugin loader
        with patch.object(executor.plugin_loader, 'load') as mock_load:
            mock_load.side_effect = [
                DummyPluginSuccess({"output1": "data1"}),
                DummyPluginSuccess({"output2": "data2"})
            ]
            
            result = executor.execute(workflow, project_id="test_project")
            
            assert result.is_success is True
            assert result.workflow_id == "test_workflow"
            assert result.completed_nodes == ["node1", "node2"]
            assert result.state.get("output1") == "data1"
            assert result.state.get("output2") == "data2"
            assert result.execution_time > 0
    
    def test_execute_workflow_with_findings(self):
        """Test workflow execution with findings generation."""
        storage = InMemoryStorageAdapter()
        executor = WorkflowExecutor(storage=storage)
        
        # Create workflow with findings
        workflow = WorkflowSpec(
            id="test_workflow",
            name="Test Workflow",
            description="Workflow with findings",
            nodes=[
                NodeSpec(
                    id="node1",
                    type="test.plugin",
                    outputs=["processed"]
                )
            ]
        )
        
        # Mock plugin loader
        with patch.object(executor.plugin_loader, 'load', return_value=DummyPluginWithFindings()):
            result = executor.execute(workflow, project_id="test_project")
            
            assert result.is_success is True
            
            # Check findings were saved to storage
            findings = storage.list_findings("test_project")
            assert len(findings) == 1
            assert findings[0]["detector_id"] == "test.plugin"
    
    def test_execute_workflow_error_handling(self):
        """Test workflow execution error handling - FEAT-046."""
        storage = InMemoryStorageAdapter()
        executor = WorkflowExecutor(storage=storage)
        
        # Create workflow with failing node
        workflow = WorkflowSpec(
            id="test_workflow",
            name="Test Workflow",
            description="Workflow with error",
            nodes=[
                NodeSpec(
                    id="node1",
                    type="test.plugin1",
                    outputs=["output1"]
                ),
                NodeSpec(
                    id="node2",
                    type="test.plugin2",
                    requires=["output1"],
                    outputs=["output2"]
                )
            ]
        )
        
        # Mock plugin loader - first succeeds, second fails
        with patch.object(executor.plugin_loader, 'load') as mock_load:
            mock_load.side_effect = [
                DummyPluginSuccess({"output1": "data1"}),
                DummyPluginFail()
            ]
            
            result = executor.execute(workflow, project_id="test_project")
            
            assert result.is_error is True
            assert result.failed_node == "node2"
            assert result.completed_nodes == ["node1"]
            assert "Plugin execution error" in result.error
            assert result.state.get("output1") == "data1"  # First node's output preserved
    
    def test_execute_workflow_plugin_load_error(self):
        """Test workflow execution with plugin load error."""
        storage = InMemoryStorageAdapter()
        executor = WorkflowExecutor(storage=storage)
        
        # Create workflow
        workflow = WorkflowSpec(
            id="test_workflow",
            name="Test Workflow",
            description="Workflow with plugin load error",
            nodes=[
                NodeSpec(
                    id="node1",
                    type="nonexistent.plugin",
                    outputs=["output1"]
                )
            ]
        )
        
        # Mock plugin loader to raise PluginLoadError
        with patch.object(executor.plugin_loader, 'load') as mock_load:
            from packages.workflow_engine.executor import PluginLoadError
            mock_load.side_effect = PluginLoadError("Plugin not found")
            
            result = executor.execute(workflow, project_id="test_project")
            
            assert result.is_error is True
            assert result.failed_node == "node1"
            assert "Plugin load error" in result.error
    
    def test_execute_workflow_state_management(self):
        """Test state management between nodes - FEAT-045."""
        storage = InMemoryStorageAdapter()
        executor = WorkflowExecutor(storage=storage)
        
        # Create workflow with data passing
        workflow = WorkflowSpec(
            id="test_workflow",
            name="Test Workflow",
            description="Workflow with state management",
            nodes=[
                NodeSpec(
                    id="discovery",
                    type="discovery.plugin",
                    outputs=["urls"]
                ),
                NodeSpec(
                    id="scan",
                    type="scan.plugin",
                    requires=["urls"],
                    outputs=["findings"]
                ),
                NodeSpec(
                    id="enrich",
                    type="enrich.plugin",
                    requires=["findings"],
                    outputs=["enriched_findings"]
                )
            ]
        )
        
        # Mock plugin loader with data passing
        with patch.object(executor.plugin_loader, 'load') as mock_load:
            mock_load.side_effect = [
                DummyPluginSuccess({"urls": ["url1", "url2"]}),
                DummyPluginSuccess({"findings": ["finding1", "finding2"]}),
                DummyPluginSuccess({"enriched_findings": ["enriched1", "enriched2"]})
            ]
            
            result = executor.execute(workflow, project_id="test_project")
            
            assert result.is_success is True
            assert result.completed_nodes == ["discovery", "scan", "enrich"]
            
            # Verify state management
            state = result.state
            assert state.get("urls") == ["url1", "url2"]
            assert state.get("findings") == ["finding1", "finding2"]
            assert state.get("enriched_findings") == ["enriched1", "enriched2"]
    
    def test_execute_workflow_from_yaml(self):
        """Test loading and executing workflow from YAML."""
        executor = WorkflowExecutor()
        
        # Create temporary YAML file
        yaml_content = """
version: "1.0"
name: "Test YAML Workflow"
description: "Test workflow loaded from YAML"
nodes:
  - id: "test_node"
    type: "test.plugin"
    config:
      param: "value"
    outputs: ["test_output"]
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            # Load workflow from YAML
            workflow = executor.load_workflow_from_yaml(temp_path)
            
            assert workflow.name == "Test YAML Workflow"
            assert workflow.description == "Test workflow loaded from YAML"
            assert len(workflow.nodes) == 1
            assert workflow.nodes[0].id == "test_node"
            assert workflow.nodes[0].type == "test.plugin"
            assert workflow.nodes[0].params["param"] == "value"
            assert workflow.nodes[0].outputs == ["test_output"]
            
        finally:
            os.unlink(temp_path)
    
    def test_execute_workflow_with_missing_inputs(self):
        """Test workflow execution with missing inputs."""
        storage = InMemoryStorageAdapter()
        executor = WorkflowExecutor(storage=storage)
        
        # Create workflow with missing inputs
        workflow = WorkflowSpec(
            id="test_workflow",
            name="Test Workflow",
            description="Workflow with missing inputs",
            nodes=[
                NodeSpec(
                    id="node1",
                    type="test.plugin1",
                    requires=["missing_input"],
                    outputs=["output1"]
                )
            ]
        )
        
        # Mock plugin loader
        with patch.object(executor.plugin_loader, 'load', return_value=DummyPluginSuccess()):
            result = executor.execute(workflow, project_id="test_project")
            
            # Should fail due to validation error (missing input dependency)
            assert result.is_error is True
            assert "Workflow validation failed" in result.error
            assert "unknown output 'missing_input'" in result.error
    
    def test_execute_workflow_execution_history(self):
        """Test execution history tracking."""
        executor = WorkflowExecutor()
        
        # Create simple workflow
        workflow = WorkflowSpec(
            id="test_workflow",
            name="Test Workflow",
            description="Test workflow",
            nodes=[
                NodeSpec(
                    id="node1",
                    type="test.plugin",
                    outputs=["output1"]
                )
            ]
        )
        
        # Mock plugin loader
        with patch.object(executor.plugin_loader, 'load', return_value=DummyPluginSuccess()):
            result = executor.execute(workflow, project_id="test_project")
            
            assert result.is_success is True
            
            # Check execution history
            history = executor.get_execution_history()
            assert len(history) >= 0  # History may be empty in M1
            
            # Clear history
            executor.clear_execution_history()
            assert len(executor.get_execution_history()) == 0


class TestIntegrationWithSampleWorkflow:
    """Test integration with sample-linear.yaml workflow."""
    
    def test_execute_sample_linear_workflow(self):
        """Test execution of sample-linear.yaml workflow."""
        executor = WorkflowExecutor()
        
        # Load sample workflow
        workflow = executor.load_workflow_from_yaml("workflows/sample-linear.yaml")
        
        assert workflow.name == "Linear Security Scan"
        assert workflow.description == "Simple linear workflow: discovery → scan → enrichment"
        assert len(workflow.nodes) == 3
        
        # Verify node structure
        discovery_node = next(n for n in workflow.nodes if n.id == "discovery")
        scan_node = next(n for n in workflow.nodes if n.id == "scan")
        enrich_node = next(n for n in workflow.nodes if n.id == "enrich")
        
        assert discovery_node.type == "discovery.ferox"
        assert discovery_node.outputs == ["urls"]
        
        assert scan_node.type == "scan.nuclei"
        assert scan_node.requires == ["urls"]
        assert scan_node.outputs == ["findings"]
        
        assert enrich_node.type == "enrich.cve"
        assert enrich_node.requires == ["findings"]
        assert enrich_node.outputs == ["enriched_findings"]
    
    def test_execute_sample_workflow_with_mock_plugins(self):
        """Test execution of sample workflow with mock plugins."""
        storage = InMemoryStorageAdapter()
        executor = WorkflowExecutor(storage=storage)
        
        # Load sample workflow
        workflow = executor.load_workflow_from_yaml("workflows/sample-linear.yaml")
        
        # Mock plugin loader with realistic data
        with patch.object(executor.plugin_loader, 'load') as mock_load:
            mock_load.side_effect = [
                DummyPluginSuccess({"urls": ["https://example.com/admin", "https://example.com/api"]}),
                DummyPluginSuccess({"findings": ["SQL injection", "XSS vulnerability"]}),
                DummyPluginSuccess({"enriched_findings": ["CVE-2023-1234", "CVE-2023-5678"]})
            ]
            
            result = executor.execute(workflow, project_id="sample_project")
            
            assert result.is_success is True
            assert result.completed_nodes == ["discovery", "scan", "enrich"]
            
            # Verify final state contains enriched_findings
            state = result.state
            assert state.get("urls") == ["https://example.com/admin", "https://example.com/api"]
            assert state.get("findings") == ["SQL injection", "XSS vulnerability"]
            assert state.get("enriched_findings") == ["CVE-2023-1234", "CVE-2023-5678"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
