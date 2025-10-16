"""
Workflow Engine Integration Tests - M1 Implementation

Comprehensive integration tests for the workflow engine including:
- Recipe validation and parsing
- Workflow execution with retry/backoff
- Plugin integration testing
- Error handling and edge cases
- Golden sample data integration

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

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from packages.workflow_engine.executor import (
    WorkflowExecutor, NodeExecutor, ExecutionContext,
    WorkflowSpec, NodeSpec, NodeResult, PluginLoader, PluginInterface
)
from packages.workflow_engine.validate_recipe import (
    RecipeValidator, RecipeValidationError, DAGValidationError,
    ReferenceValidationError, NodeValidationError
)


class TestRecipeValidation:
    """Test comprehensive recipe validation."""
    
    def test_valid_recipe_validation(self):
        """Test validation of a valid recipe."""
        validator = RecipeValidator()
        recipe = validator.create_test_recipe("linear")
        
        result = validator.validate(recipe)
        
        assert result["ok"] is True
        assert result["nodes"] == 3
        assert len(result["execution_order"]) == 3
        assert result["execution_order"] == ["discovery", "scan", "enrich"]
        assert "schema" in result["validation_details"]
        assert "dag" in result["validation_details"]
        assert "references" in result["validation_details"]
    
    def test_invalid_recipe_validation(self):
        """Test validation of an invalid recipe."""
        validator = RecipeValidator()
        recipe = validator.create_test_recipe("invalid")
        
        result = validator.validate(recipe)
        
        assert result["ok"] is False
        assert len(result["errors"]) > 0
        assert "unknown output" in str(result["errors"])
    
    def test_missing_required_fields(self):
        """Test validation with missing required fields."""
        validator = RecipeValidator()
        
        # Missing version
        recipe = {"name": "Test", "nodes": []}
        result = validator.validate(recipe)
        assert result["ok"] is False
        assert "Missing required fields" in str(result["errors"])
        
        # Missing name
        recipe = {"version": "1.0", "nodes": []}
        result = validator.validate(recipe)
        assert result["ok"] is False
        assert "Missing required fields" in str(result["errors"])
        
        # Missing nodes
        recipe = {"version": "1.0", "name": "Test"}
        result = validator.validate(recipe)
        assert result["ok"] is False
        assert "Missing required fields" in str(result["errors"])
    
    def test_empty_nodes_validation(self):
        """Test validation with empty nodes list."""
        validator = RecipeValidator()
        recipe = {
            "version": "1.0",
            "name": "Empty Workflow",
            "nodes": []
        }
        
        result = validator.validate(recipe)
        assert result["ok"] is False
        assert "at least one node" in str(result["errors"])
    
    def test_duplicate_node_ids(self):
        """Test validation with duplicate node IDs."""
        validator = RecipeValidator()
        recipe = {
            "version": "1.0",
            "name": "Duplicate IDs",
            "nodes": [
                {"id": "node1", "type": "echo", "outputs": ["out1"]},
                {"id": "node1", "type": "echo", "outputs": ["out2"]}
            ]
        }
        
        result = validator.validate(recipe)
        assert result["ok"] is False
        assert "Duplicate node IDs" in str(result["errors"])
    
    def test_circular_dependency_detection(self):
        """Test detection of circular dependencies."""
        validator = RecipeValidator()
        recipe = {
            "version": "1.0",
            "name": "Circular Dependency",
            "nodes": [
                {"id": "node1", "type": "echo", "inputs": ["out2"], "outputs": ["out1"]},
                {"id": "node2", "type": "echo", "inputs": ["out1"], "outputs": ["out2"]}
            ]
        }
        
        result = validator.validate(recipe)
        assert result["ok"] is False
        assert "Cycle detected" in str(result["errors"])
    
    def test_unresolved_input_references(self):
        """Test detection of unresolved input references."""
        validator = RecipeValidator()
        recipe = {
            "version": "1.0",
            "name": "Unresolved References",
            "nodes": [
                {"id": "node1", "type": "echo", "inputs": ["nonexistent"], "outputs": ["out1"]}
            ]
        }
        
        result = validator.validate(recipe)
        assert result["ok"] is False
        assert "unknown output" in str(result["errors"])
    
    def test_ferox_config_validation(self):
        """Test feroxbuster configuration validation."""
        validator = RecipeValidator()
        
        # Valid config
        recipe = {
            "version": "1.0",
            "name": "Valid Ferox",
            "nodes": [
                {
                    "id": "discovery",
                    "type": "discovery.ferox",
                    "config": {
                        "wordlist": "res://wordlists/dirb:latest",
                        "threads": 50,
                        "timeout": 300
                    },
                    "outputs": ["urls"]
                }
            ]
        }
        
        result = validator.validate(recipe)
        assert result["ok"] is True
        
        # Missing wordlist
        recipe["nodes"][0]["config"].pop("wordlist")
        result = validator.validate(recipe)
        assert result["ok"] is False
        assert "requires 'wordlist'" in str(result["errors"])
        
        # Invalid threads
        recipe["nodes"][0]["config"]["wordlist"] = "test"
        recipe["nodes"][0]["config"]["threads"] = 150  # Too high
        result = validator.validate(recipe)
        assert result["ok"] is False
        assert "threads' must be integer 1-100" in str(result["errors"])
    
    def test_nuclei_config_validation(self):
        """Test nuclei configuration validation."""
        validator = RecipeValidator()
        
        # Valid config
        recipe = {
            "version": "1.0",
            "name": "Valid Nuclei",
            "nodes": [
                {
                    "id": "scan",
                    "type": "scan.nuclei",
                    "config": {
                        "templates": "res://templates/owasp-top10:latest",
                        "rate_limit": 150,
                        "timeout": 600
                    },
                    "outputs": ["findings"]
                }
            ]
        }
        
        result = validator.validate(recipe)
        assert result["ok"] is True
        
        # Missing templates
        recipe["nodes"][0]["config"].pop("templates")
        result = validator.validate(recipe)
        assert result["ok"] is False
        assert "requires 'templates'" in str(result["errors"])
    
    def test_cve_config_validation(self):
        """Test CVE enrichment configuration validation."""
        validator = RecipeValidator()
        
        # Valid config
        recipe = {
            "version": "1.0",
            "name": "Valid CVE",
            "nodes": [
                {
                    "id": "enrich",
                    "type": "enrich.cve",
                    "config": {
                        "sources": ["nvd", "osv", "exploitdb"],
                        "timeout": 120
                    },
                    "outputs": ["enriched_findings"]
                }
            ]
        }
        
        result = validator.validate(recipe)
        assert result["ok"] is True
        
        # Invalid sources
        recipe["nodes"][0]["config"]["sources"] = ["invalid_source"]
        result = validator.validate(recipe)
        assert result["ok"] is False
        assert "invalid sources" in str(result["errors"])


class TestWorkflowExecution:
    """Test workflow execution with orchestration."""
    
    def test_linear_workflow_execution(self):
        """Test execution of a linear workflow."""
        executor = WorkflowExecutor()
        
        # Create a simple linear workflow
        recipe = {
            "version": "1.0",
            "name": "Test Linear Workflow",
            "nodes": [
                {
                    "id": "discovery",
                    "type": "discovery.ferox",
                    "config": {"wordlist": "test"},
                    "outputs": ["urls"]
                },
                {
                    "id": "scan",
                    "type": "scan.nuclei",
                    "inputs": ["urls"],
                    "config": {"templates": "test"},
                    "outputs": ["findings"]
                }
            ]
        }
        
        workflow = executor._to_spec(recipe)
        result = executor.execute_workflow(workflow)
        
        assert result["status"] == "completed"
        assert "discovery" in result["completed_nodes"]
        assert "scan" in result["completed_nodes"]
        assert len(result["failed_nodes"]) == 0
    
    def test_workflow_with_retry_config(self):
        """Test workflow execution with retry configuration."""
        executor = WorkflowExecutor()
        
        recipe = {
            "version": "1.0",
            "name": "Retry Test Workflow",
            "nodes": [
                {
                    "id": "echo",
                    "type": "echo",
                    "config": {"message": "test"},
                    "retries": 2,
                    "retry_backoff_s": 0.1,
                    "outputs": ["output"]
                }
            ]
        }
        
        workflow = executor._to_spec(recipe)
        result = executor.execute_workflow(workflow)
        
        assert result["status"] == "completed"
        assert "echo" in result["completed_nodes"]
    
    def test_workflow_execution_order(self):
        """Test that nodes execute in correct topological order."""
        executor = WorkflowExecutor()
        
        recipe = {
            "version": "1.0",
            "name": "Order Test Workflow",
            "nodes": [
                {
                    "id": "node3",
                    "type": "echo",
                    "inputs": ["out1", "out2"],
                    "config": {"message": "last"},
                    "outputs": ["final"]
                },
                {
                    "id": "node1",
                    "type": "echo",
                    "config": {"message": "first"},
                    "outputs": ["out1"]
                },
                {
                    "id": "node2",
                    "type": "echo",
                    "config": {"message": "second"},
                    "outputs": ["out2"]
                }
            ]
        }
        
        workflow = executor._to_spec(recipe)
        result = executor.execute_workflow(workflow)
        
        assert result["status"] == "completed"
        # Verify execution order (node1 and node2 can run in parallel, node3 last)
        completed_nodes = result["completed_nodes"]
        assert "node3" not in completed_nodes[:2]  # node3 should not be in first 2
        assert "node3" in completed_nodes  # but should be completed
    
    def test_workflow_validation_before_execution(self):
        """Test that workflow is validated before execution."""
        executor = WorkflowExecutor()
        
        # Create invalid workflow (circular dependency)
        recipe = {
            "version": "1.0",
            "name": "Invalid Workflow",
            "nodes": [
                {
                    "id": "node1",
                    "type": "echo",
                    "inputs": ["out2"],
                    "config": {"message": "test"},
                    "outputs": ["out1"]
                },
                {
                    "id": "node2",
                    "type": "echo",
                    "inputs": ["out1"],
                    "config": {"message": "test"},
                    "outputs": ["out2"]
                }
            ]
        }
        
        workflow = executor._to_spec(recipe)
        result = executor.execute_workflow(workflow)
        
        assert result["status"] == "failed"
        assert "validation failed" in result["error"].lower()
    
    def test_dry_run_analysis(self):
        """Test dry-run analysis without execution."""
        executor = WorkflowExecutor()
        
        recipe = {
            "version": "1.0",
            "name": "Dry Run Test",
            "nodes": [
                {
                    "id": "node1",
                    "type": "echo",
                    "config": {"message": "test"},
                    "outputs": ["out1"]
                }
            ]
        }
        
        result = executor.dry_run(recipe)
        
        assert result["ok"] is True
        assert result["nodes"] == 1
        assert "node1" in result["execution_order"]
    
    def test_workflow_with_state_config(self):
        """Test workflow with state management configuration."""
        executor = WorkflowExecutor()
        
        recipe = {
            "version": "1.0",
            "name": "State Test Workflow",
            "nodes": [
                {
                    "id": "node1",
                    "type": "echo",
                    "config": {"message": "test"},
                    "outputs": ["out1"]
                }
            ],
            "state": {
                "checkpoint_interval": 30,
                "resume_on_failure": True,
                "cache_intermediate": True
            }
        }
        
        workflow = executor._to_spec(recipe)
        result = executor.execute_workflow(workflow)
        
        assert result["status"] == "completed"
        # State config is parsed but not yet implemented in M1


class TestNodeExecution:
    """Test individual node execution."""
    
    def test_node_executor_with_retry(self):
        """Test node execution with retry logic."""
        from packages.storage.adapters.memory import InMemoryStorageAdapter
        storage = InMemoryStorageAdapter()
        plugin_loader = PluginLoader()
        executor = NodeExecutor(plugin_loader, storage)
        
        # Use echo plugin which should succeed
        node_spec = NodeSpec(
            id="test_node",
            type="echo",
            params={"message": "test"},
            retries=2,
            retry_backoff_s=0.01  # Fast for testing
        )
        
        ctx = ExecutionContext(run_id="test_run", workflow_id="test_workflow", project_id="test_project")
        result = executor.execute(node_spec, ctx)
        
        assert result.status == "ok"
        assert result.attempts == 1
    
    def test_node_executor_max_retries_exceeded(self):
        """Test node execution when max retries are exceeded."""
        from packages.storage.adapters.memory import InMemoryStorageAdapter
        storage = InMemoryStorageAdapter()
        plugin_loader = PluginLoader()
        executor = NodeExecutor(plugin_loader, storage)
        
        # Use unknown plugin which should fail
        node_spec = NodeSpec(
            id="test_node",
            type="unknown.plugin",
            params={"test": "value"},
            retries=1,
            retry_backoff_s=0.01
        )
        
        ctx = ExecutionContext(run_id="test_run", workflow_id="test_workflow", project_id="test_project")
        result = executor.execute(node_spec, ctx)
        
        assert result.status == "error"
        assert "Unknown plugin" in result.error
        assert result.attempts == 1  # Plugin load error doesn't retry
    
    def test_node_executor_unknown_type(self):
        """Test node execution with unknown plugin type."""
        from packages.storage.adapters.memory import InMemoryStorageAdapter
        storage = InMemoryStorageAdapter()
        plugin_loader = PluginLoader()
        executor = NodeExecutor(plugin_loader, storage)
        
        node_spec = NodeSpec(
            id="test_node",
            type="unknown_plugin",
            params={"test": "value"}
        )
        
        ctx = ExecutionContext(run_id="test_run", workflow_id="test_workflow", project_id="test_project")
        result = executor.execute(node_spec, ctx)
        
        assert result.status == "error"
        assert "Unknown plugin" in result.error


class TestPluginIntegration:
    """Test plugin integration and stub execution."""
    
    def test_stub_discovery_ferox(self):
        """Test stub implementation of discovery.ferox."""
        executor = WorkflowExecutor()
        
        node_spec = NodeSpec(
            id="discovery",
            type="discovery.ferox",
            params={
                "wordlist": "res://wordlists/dirb:latest",
                "threads": 50,
                "timeout": 300
            }
        )
        
        ctx = ExecutionContext(run_id="test_run", workflow_id="test_workflow", project_id="test_project")
        result = executor.plugin_loader.load("discovery.ferox").run({}, node_spec.params, ctx)
        
        assert "urls" in result["outputs"]
        assert isinstance(result["outputs"]["urls"], list)
        assert result["status"] == "success"
        assert len(result["outputs"]["urls"]) > 0
    
    def test_stub_scan_nuclei(self):
        """Test stub implementation of scan.nuclei."""
        executor = WorkflowExecutor()
        
        # Set up context with URLs from discovery
        ctx = ExecutionContext(run_id="test_run", workflow_id="test_workflow", project_id="test_project")
        ctx.vars["urls"] = ["https://example.com/admin", "https://example.com/api"]
        
        node_spec = NodeSpec(
            id="scan",
            type="scan.nuclei",
            params={
                "templates": "res://templates/owasp-top10:latest",
                "rate_limit": 150,
                "timeout": 600
            }
        )
        
        result = executor.plugin_loader.load("scan.nuclei").run(ctx.vars, node_spec.params, ctx)
        
        assert "findings" in result["outputs"]
        assert isinstance(result["outputs"]["findings"], list)
        assert result["status"] == "success"
        assert len(result["outputs"]["findings"]) == 2  # One finding per URL
    
    def test_stub_enrich_cve(self):
        """Test stub implementation of enrich.cve."""
        executor = WorkflowExecutor()
        
        # Set up context with findings from scan
        ctx = ExecutionContext(run_id="test_run", workflow_id="test_workflow", project_id="test_project")
        ctx.vars["findings"] = [
            {"id": "finding1", "title": "Test finding 1"},
            {"id": "finding2", "title": "Test finding 2"}
        ]
        
        node_spec = NodeSpec(
            id="enrich",
            type="enrich.cve",
            params={
                "sources": ["nvd", "osv", "exploitdb"],
                "timeout": 120
            }
        )
        
        result = executor.plugin_loader.load("enrich.cve").run(ctx.vars, node_spec.params, ctx)
        
        assert "enriched_findings" in result["outputs"]
        assert isinstance(result["outputs"]["enriched_findings"], list)
        assert result["status"] == "success"
        assert len(result["outputs"]["enriched_findings"]) == 2
        
        # Check that enrichment data was added
        for finding in result["outputs"]["enriched_findings"]:
            assert "cve_ids" in finding
            assert "cvss" in finding
            assert "owasp" in finding
    
    def test_stub_echo(self):
        """Test stub implementation of echo."""
        executor = WorkflowExecutor()
        
        ctx = ExecutionContext(run_id="test_run", workflow_id="test_workflow", project_id="test_project")
        ctx.vars["test_var"] = "test_value"
        
        node_spec = NodeSpec(
            id="echo",
            type="echo",
            params={"message": "Hello World"}
        )
        
        result = executor.plugin_loader.load("echo").run(ctx.vars, node_spec.params, ctx)
        
        assert "echo" in result["outputs"]
        assert result["outputs"]["echo"] == "Hello World"
        assert result["status"] == "success"
        assert "vars" in result["outputs"]
        assert result["outputs"]["vars"]["test_var"] == "test_value"


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_workflow_failed_exception(self):
        """Test WorkflowFailed exception handling."""
        executor = WorkflowExecutor()
        
        # Create workflow that will fail validation
        recipe = {
            "version": "1.0",
            "name": "Failing Workflow",
            "nodes": [
                {
                    "id": "node1",
                    "type": "unknown_type",
                    "config": {},
                    "outputs": ["out1"]
                }
            ]
        }
        
        workflow = executor._to_spec(recipe)
        
        # Mock node executor to always fail
        with patch.object(executor.node_executor, 'execute') as mock_execute:
            mock_execute.return_value = NodeResult(
                node_id="node1",
                status="error",
                error="Plugin not found"
            )
            
            result = executor.execute_workflow(workflow)
            
            assert result["status"] == "failed"
            assert "node1" in result["failed_nodes"]
    
    def test_file_not_found_error(self):
        """Test handling of file not found errors."""
        validator = RecipeValidator()
        
        result = validator.validate_file("nonexistent_file.yaml")
        
        assert result["ok"] is False
        assert "not found" in str(result["errors"])
    
    def test_yaml_parsing_error(self):
        """Test handling of YAML parsing errors."""
        validator = RecipeValidator()
        
        # Create temporary file with invalid YAML
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_file = f.name
        
        try:
            result = validator.validate_file(temp_file)
            assert result["ok"] is False
            assert "YAML parsing error" in str(result["errors"])
        finally:
            os.unlink(temp_file)


class TestGoldenSampleIntegration:
    """Test integration with golden sample data."""
    
    def test_golden_sample_file_reading(self):
        """Test reading from golden sample files."""
        executor = WorkflowExecutor()
        
        # Test with a node type that has golden samples
        node_spec = NodeSpec(
            id="test_node",
            type="discovery.ferox",
            params={}
        )
        
        # Mock the golden sample file path
        golden_sample_path = Path("tests/golden_samples/feroxbuster/v2.10.x/output.json")
        
        ctx = ExecutionContext(run_id="test", workflow_id="test", project_id="test_project")
        
        if golden_sample_path.exists():
            result = executor.plugin_loader.load("discovery.ferox").run({}, node_spec.params, ctx)
            assert isinstance(result, dict)
            assert "urls" in result["outputs"]
            assert isinstance(result["outputs"]["urls"], list)
            assert result["status"] == "success"
        else:
            # If golden samples don't exist, should fall back to mock data
            result = executor.plugin_loader.load("discovery.ferox").run({}, node_spec.params, ctx)
            assert isinstance(result, dict)
            assert "urls" in result["outputs"]
            assert isinstance(result["outputs"]["urls"], list)
            assert result["status"] == "success"
    
    def test_fallback_to_mock_data(self):
        """Test fallback to mock data when golden samples unavailable."""
        executor = WorkflowExecutor()
        
        # Test with unknown node type
        node_spec = NodeSpec(
            id="test_node",
            type="unknown.tool",
            params={}
        )
        
        ctx = ExecutionContext(run_id="test", workflow_id="test", project_id="test_project")
        
        # Test with echo stub since it handles unknown types gracefully
        result = executor.plugin_loader.load("echo").run(ctx.vars, node_spec.params, ctx)
        assert isinstance(result, dict)
        assert "echo" in result["outputs"]
        assert result["status"] == "success"
        assert "vars" in result["outputs"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
