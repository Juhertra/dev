"""
Workflow Execution Engine Tests - M1 Implementation

Tests for the workflow execution engine with StoragePort integration.
"""

import pytest
import yaml
import tempfile
import os
from pathlib import Path
import sys
from datetime import datetime

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from packages.workflow_engine.executor import (
        WorkflowExecutor, Workflow, WorkflowNode, NodeExecutor,
        WorkflowSpec, NodeSpec, ExecutionContext, NodeResult,
        validate_workflow, PluginLoader, PluginInterface
    )
    from packages.storage.adapters.memory import InMemoryStorageAdapter
except ImportError:
    pytest.skip("Workflow engine packages not available", allow_module_level=True)


class TestWorkflowExecutionEngine:
    """Test workflow execution engine functionality."""
    
    def test_workflow_executor_initialization(self):
        """Test WorkflowExecutor initialization."""
        executor = WorkflowExecutor()
        assert executor is not None
        assert executor.storage is not None
        assert executor.node_executor is not None
        assert len(executor.active_workflows) == 0
    
    def test_workflow_executor_with_custom_storage(self):
        """Test WorkflowExecutor with custom storage."""
        storage = InMemoryStorageAdapter()
        executor = WorkflowExecutor(storage)
        assert executor.storage is storage
    
    def test_load_workflow_from_yaml(self):
        """Test loading workflow from YAML file."""
        # Create temporary YAML file
        yaml_content = """
version: "1.0"
name: "Test Workflow"
description: "Test workflow for unit testing"
nodes:
  - id: "test_node"
    type: "test.type"
    config:
      param: "value"
    outputs: ["test_output"]
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            executor = WorkflowExecutor()
            workflow = executor.load_workflow_from_yaml(temp_path)
            
            assert workflow.name == "Test Workflow"
            assert workflow.description == "Test workflow for unit testing"
            assert len(workflow.nodes) == 1
            assert workflow.nodes[0].id == "test_node"
            assert workflow.nodes[0].type == "test.type"
            assert workflow.nodes[0].params["param"] == "value"
            
        finally:
            os.unlink(temp_path)
    
    def test_workflow_validation_success(self):
        """Test successful workflow validation."""
        executor = WorkflowExecutor()
        
        # Create valid workflow using new dataclass approach
        node1 = NodeSpec(id="node1", type="test.type1", outputs=["out1"])
        node2 = NodeSpec(id="node2", type="test.type2", requires=["out1"])
        
        workflow = WorkflowSpec(
            id="test_workflow",
            name="Test Workflow",
            nodes=[node1, node2]
        )
        
        assert executor.validate_workflow(workflow) is True
    
    def test_workflow_validation_duplicate_ids(self):
        """Test workflow validation with duplicate node IDs."""
        executor = WorkflowExecutor()
        
        node1 = NodeSpec(id="duplicate", type="test.type1")
        node2 = NodeSpec(id="duplicate", type="test.type2")
        
        workflow = WorkflowSpec(
            id="test_workflow",
            name="Test Workflow",
            nodes=[node1, node2]
        )
        
        assert executor.validate_workflow(workflow) is False
    
    def test_workflow_validation_unresolved_inputs(self):
        """Test workflow validation with unresolved inputs."""
        executor = WorkflowExecutor()
        
        node = NodeSpec(
            id="node1",
            type="test.type",
            requires=["nonexistent_output"]
        )
        
        workflow = WorkflowSpec(
            id="test_workflow",
            name="Test Workflow",
            nodes=[node]
        )
        
        assert executor.validate_workflow(workflow) is False
    
    def test_workflow_validation_cycle_detection(self):
        """Test workflow validation with cycle detection."""
        executor = WorkflowExecutor()
        
        # Create cycle: node1 -> node2 -> node1
        node1 = NodeSpec(id="node1", type="test.type1", requires=["node2"])
        node2 = NodeSpec(id="node2", type="test.type2", requires=["node1"])
        
        workflow = WorkflowSpec(
            id="test_workflow",
            name="Test Workflow",
            nodes=[node1, node2]
        )
        
        assert executor.validate_workflow(workflow) is False
    
    def test_execution_order_calculation(self):
        """Test execution order calculation."""
        # Create linear workflow: node1 -> node2 -> node3
        node1 = NodeSpec(id="node1", type="test.type1", outputs=["out1"])
        node2 = NodeSpec(id="node2", type="test.type2", requires=["out1"], outputs=["out2"])
        node3 = NodeSpec(id="node3", type="test.type3", requires=["out2"])
        
        workflow = WorkflowSpec(
            id="test_workflow",
            name="Test Workflow",
            nodes=[node1, node2, node3]
        )
        
        execution_order = validate_workflow(workflow)
        assert execution_order == ["node1", "node2", "node3"]
    
    def test_execution_order_branching(self):
        """Test execution order with branching workflow."""
        # Create branching workflow: node1 -> [node2, node3] -> node4
        node1 = NodeSpec(id="node1", type="test.type1", outputs=["out1"])
        node2 = NodeSpec(id="node2", type="test.type2", requires=["out1"], outputs=["out2"])
        node3 = NodeSpec(id="node3", type="test.type3", requires=["out1"], outputs=["out3"])
        node4 = NodeSpec(id="node4", type="test.type4", requires=["out2", "out3"])
        
        workflow = WorkflowSpec(
            id="test_workflow",
            name="Test Workflow",
            nodes=[node1, node2, node3, node4]
        )
        
        execution_order = validate_workflow(workflow)
        assert "node1" in execution_order
        assert "node2" in execution_order
        assert "node3" in execution_order
        assert "node4" in execution_order
        assert execution_order.index("node1") < execution_order.index("node2")
        assert execution_order.index("node1") < execution_order.index("node3")
        assert execution_order.index("node2") < execution_order.index("node4")
        assert execution_order.index("node3") < execution_order.index("node4")


class TestNodeExecutor:
    """Test node execution functionality."""
    
    def test_node_executor_initialization(self):
        """Test NodeExecutor initialization."""
        from packages.storage.adapters.memory import InMemoryStorageAdapter
        storage = InMemoryStorageAdapter()
        plugin_loader = PluginLoader()
        executor = NodeExecutor(plugin_loader, storage)
        assert executor.plugin_loader is not None
        assert executor.storage is not None
    
    def test_node_execution_success(self):
        """Test successful node execution."""
        from packages.storage.adapters.memory import InMemoryStorageAdapter
        storage = InMemoryStorageAdapter()
        plugin_loader = PluginLoader()
        executor = NodeExecutor(plugin_loader, storage)
        
        node = NodeSpec(id="test_node", type="echo", params={"message": "test"})
        ctx = ExecutionContext(run_id="run_1", workflow_id="wf_1", project_id="test_project")
        
        result = executor.execute(node, ctx)
        
        assert result.status == "ok"
        assert result.node_id == "test_node"
        assert result.attempts == 1
    
    def test_node_execution_unknown_type(self):
        """Test node execution with unknown type."""
        from packages.storage.adapters.memory import InMemoryStorageAdapter
        storage = InMemoryStorageAdapter()
        plugin_loader = PluginLoader()
        executor = NodeExecutor(plugin_loader, storage)
        
        node = NodeSpec(id="test_node", type="unknown.type")
        ctx = ExecutionContext(run_id="run_1", workflow_id="wf_1", project_id="test_project")
        
        result = executor.execute(node, ctx)
        
        assert result.status == "error"
        assert result.node_id == "test_node"
        assert "Unknown plugin" in result.error
    
    def test_node_execution_with_retry(self):
        """Test node execution with retry logic."""
        from packages.storage.adapters.memory import InMemoryStorageAdapter
        storage = InMemoryStorageAdapter()
        plugin_loader = PluginLoader()
        executor = NodeExecutor(plugin_loader, storage)
        
        # Use echo plugin which should succeed
        node = NodeSpec(id="test_node", type="echo", params={"message": "test"}, retries=2, retry_backoff_s=0.1)
        ctx = ExecutionContext(run_id="run_1", workflow_id="wf_1", project_id="test_project")
        
        result = executor.execute(node, ctx)
        
        assert result.status == "ok"
        assert result.node_id == "test_node"
        assert result.attempts == 1


class TestStorageIntegration:
    """Test StoragePort integration with workflow execution."""
    
    def test_workflow_data_passing(self):
        """Test data passing between nodes via ExecutionContext."""
        executor = WorkflowExecutor()
        
        # Create workflow with data passing
        node1 = NodeSpec(id="discovery", type="discovery.ferox", outputs=["urls"])
        node2 = NodeSpec(id="scan", type="scan.nuclei", requires=["urls"])
        
        workflow = WorkflowSpec(
            id="test_workflow",
            name="Test Workflow",
            nodes=[node1, node2]
        )
        
        # Execute workflow
        result = executor.execute_workflow(workflow)
        
        assert result["status"] == "completed"
        assert "discovery" in result["completed_nodes"]
        assert "scan" in result["completed_nodes"]
    
    def test_workflow_state_tracking(self):
        """Test workflow state tracking during execution."""
        executor = WorkflowExecutor()
        
        node = NodeSpec(id="test_node", type="echo", params={"message": "test"})
        
        workflow = WorkflowSpec(
            id="test_workflow",
            name="Test Workflow",
            nodes=[node]
        )
        
        # Execute workflow
        result = executor.execute_workflow(workflow)
        
        assert result["status"] == "completed"
        
        # Check workflow state
        status = executor.get_workflow_status("test_workflow")
        assert status["workflow_id"] == "test_workflow"


class TestDryRun:
    """Test dry run functionality."""
    
    def test_dry_run_success(self):
        """Test successful dry run."""
        executor = WorkflowExecutor()
        
        recipe = {
            "version": "1.0",
            "name": "Test Workflow",
            "description": "Test",
            "nodes": [
                {
                    "id": "node1",
                    "type": "test.type1",
                    "config": {},
                    "outputs": ["out1"]
                },
                {
                    "id": "node2",
                    "type": "test.type2",
                    "inputs": ["out1"],
                    "config": {}
                }
            ]
        }
        
        result = executor.dry_run(recipe)
        
        assert result["ok"] is True
        assert result["nodes"] == 2
        assert "node1" in result["execution_order"]
        assert "node2" in result["execution_order"]
        assert result["execution_order"].index("node1") < result["execution_order"].index("node2")
        assert len(result["validation_errors"]) == 0
    
    def test_dry_run_validation_failure(self):
        """Test dry run with validation failure."""
        executor = WorkflowExecutor()
        
        recipe = {
            "version": "1.0",
            "name": "Test Workflow",
            "description": "Test",
            "nodes": [
                {
                    "id": "node1",
                    "type": "test.type1",
                    "inputs": ["nonexistent_output"],
                    "config": {}
                }
            ]
        }
        
        result = executor.dry_run(recipe)
        
        assert result["ok"] is False
        assert result["nodes"] == 1
        assert len(result["execution_order"]) == 0
        assert len(result["validation_errors"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
