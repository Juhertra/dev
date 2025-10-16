"""
Workflow Engine Scaffolding Tests - Enhanced M1 Implementation

Tests for the workflow engine scaffolding including:
- Import resolution and module availability
- Basic model creation and validation
- Sample workflow structure and configuration
- Enhanced validation and execution capabilities
"""

import pytest
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from packages.workflow_engine.executor import (
    WorkflowExecutor, WorkflowSpec, NodeSpec, ExecutionContext,
    NodeExecutor, NodeResult
)
from packages.workflow_engine.validate_recipe import (
    RecipeValidator, Workflow, WorkflowNode, RetryConfig, StateConfig
)


class TestWorkflowScaffolding:
    """Test workflow engine scaffolding components."""
    
    def test_import_resolution(self):
        """Test that all workflow engine modules can be imported."""
        # Test executor imports
        assert WorkflowExecutor is not None
        assert WorkflowSpec is not None
        assert NodeSpec is not None
        assert ExecutionContext is not None
        assert NodeExecutor is not None
        assert NodeResult is not None
        
        # Test validator imports
        assert RecipeValidator is not None
        assert Workflow is not None
        assert WorkflowNode is not None
        assert RetryConfig is not None
        assert StateConfig is not None
    
    def test_model_creation(self):
        """Test creation of workflow models."""
        # Test WorkflowNode creation
        node = WorkflowNode(
            id="test_node",
            type="echo",
            config={"message": "test"},
            inputs=["input1"],
            outputs=["output1"]
        )
        
        assert node.id == "test_node"
        assert node.type == "echo"
        assert node.config["message"] == "test"
        assert node.inputs == ["input1"]
        assert node.outputs == ["output1"]
        
        # Test RetryConfig creation
        retry = RetryConfig(
            max_attempts=3,
            backoff_factor=2.0,
            base_delay=5.0
        )
        
        assert retry.max_attempts == 3
        assert retry.backoff_factor == 2.0
        assert retry.base_delay == 5.0
        
        # Test StateConfig creation
        state = StateConfig(
            checkpoint_interval=30,
            resume_on_failure=True,
            cache_intermediate=True
        )
        
        assert state.checkpoint_interval == 30
        assert state.resume_on_failure is True
        assert state.cache_intermediate is True
        
        # Test Workflow creation
        workflow = Workflow(
            version="1.0",
            name="Test Workflow",
            description="Test description",
            nodes=[node],
            retry=retry,
            state=state
        )
        
        assert workflow.version == "1.0"
        assert workflow.name == "Test Workflow"
        assert workflow.description == "Test description"
        assert len(workflow.nodes) == 1
        assert workflow.retry == retry
        assert workflow.state == state
    
    def test_executor_initialization(self):
        """Test WorkflowExecutor initialization."""
        executor = WorkflowExecutor()
        
        assert executor is not None
        assert executor.storage is not None
        assert executor.node_executor is not None
        assert isinstance(executor.active_workflows, dict)
    
    def test_validator_initialization(self):
        """Test RecipeValidator initialization."""
        validator = RecipeValidator()
        
        assert validator is not None
        assert validator.logger is not None
    
    def test_sample_workflow_structure(self):
        """Test sample workflow structure and configuration."""
        validator = RecipeValidator()
        recipe = validator.create_test_recipe("linear")
        
        # Test basic structure
        assert recipe["version"] == "1.0"
        assert recipe["name"] == "Test Linear Workflow"
        assert recipe["description"] == "Test workflow for validation"
        assert len(recipe["nodes"]) == 3
        
        # Test node structure
        nodes = recipe["nodes"]
        assert nodes[0]["id"] == "discovery"
        assert nodes[0]["type"] == "discovery.ferox"
        assert "wordlist" in nodes[0]["config"]
        assert nodes[0]["outputs"] == ["urls"]
        
        assert nodes[1]["id"] == "scan"
        assert nodes[1]["type"] == "scan.nuclei"
        assert nodes[1]["inputs"] == ["urls"]
        assert nodes[1]["outputs"] == ["findings"]
        
        assert nodes[2]["id"] == "enrich"
        assert nodes[2]["type"] == "enrich.cve"
        assert nodes[2]["inputs"] == ["findings"]
        assert nodes[2]["outputs"] == ["enriched_findings"]
        
        # Test retry configuration
        retry_config = recipe["retry"]
        assert retry_config["max_attempts"] == 3
        assert retry_config["backoff_factor"] == 2.0
        assert retry_config["base_delay"] == 5.0
        
        # Test state configuration
        state_config = recipe["state"]
        assert state_config["checkpoint_interval"] == 30
        assert state_config["resume_on_failure"] is True
        assert state_config["cache_intermediate"] is True
    
    def test_sample_workflow_validation(self):
        """Test validation of sample workflow."""
        validator = RecipeValidator()
        recipe = validator.create_test_recipe("linear")
        
        result = validator.validate(recipe)
        
        assert result["ok"] is True
        assert result["nodes"] == 3
        assert len(result["execution_order"]) == 3
        assert result["execution_order"] == ["discovery", "scan", "enrich"]
        
        # Test validation details
        details = result["validation_details"]
        assert details["schema"] == "passed"
        assert details["pydantic"] == "passed"
        assert details["dag"] == "passed"
        assert details["references"] == "passed"
        assert details["node_types"] == "passed"
        assert details["configurations"] == "passed"
    
    def test_sample_workflow_execution(self):
        """Test execution of sample workflow."""
        executor = WorkflowExecutor()
        validator = RecipeValidator()
        
        recipe = validator.create_test_recipe("linear")
        workflow = executor._to_spec(recipe)
        
        result = executor.execute_workflow(workflow)
        
        assert result["status"] == "completed"
        assert len(result["completed_nodes"]) == 3
        assert "discovery" in result["completed_nodes"]
        assert "scan" in result["completed_nodes"]
        assert "enrich" in result["completed_nodes"]
        assert len(result["failed_nodes"]) == 0
    
    def test_dry_run_functionality(self):
        """Test dry-run functionality."""
        executor = WorkflowExecutor()
        validator = RecipeValidator()
        
        recipe = validator.create_test_recipe("linear")
        
        # Test executor dry-run
        dry_result = executor.dry_run(recipe)
        assert dry_result["ok"] is True
        assert dry_result["nodes"] == 3
        assert len(dry_result["execution_order"]) == 3
        
        # Test validator dry-run
        validation_result = validator.validate(recipe)
        assert validation_result["ok"] is True
        assert validation_result["nodes"] == 3
    
    def test_stub_implementations(self):
        """Test stub implementations for M1."""
        executor = WorkflowExecutor()
        
        # Test that plugin loader is available
        assert executor.plugin_loader is not None
        assert executor.storage is not None
        
        # Test loading known plugins
        ferox_plugin = executor.plugin_loader.load("discovery.ferox")
        assert ferox_plugin is not None
        
        nuclei_plugin = executor.plugin_loader.load("scan.nuclei")
        assert nuclei_plugin is not None
        
        # Test stub execution
        ctx = ExecutionContext(run_id="test", workflow_id="test", project_id="test_project")
        
        # Test echo stub
        echo_plugin = executor.plugin_loader.load("echo")
        result = echo_plugin.run({}, {"message": "test"}, ctx)
        assert result["status"] == "success"
        assert "echo" in result["outputs"]
        
        # Test discovery stub
        discovery_plugin = executor.plugin_loader.load("discovery.ferox")
        result = discovery_plugin.run({}, {}, ctx)
        assert result["status"] == "success"
        assert "urls" in result["outputs"]
        assert isinstance(result["outputs"]["urls"], list)
    
    def test_error_handling(self):
        """Test error handling in scaffolding."""
        validator = RecipeValidator()
        
        # Test invalid recipe
        invalid_recipe = validator.create_test_recipe("invalid")
        result = validator.validate(invalid_recipe)
        
        assert result["ok"] is False
        assert len(result["errors"]) > 0
        
        # Test missing required fields
        incomplete_recipe = {"version": "1.0"}
        result = validator.validate(incomplete_recipe)
        
        assert result["ok"] is False
        assert "Missing required fields" in str(result["errors"])
    
    def test_execution_context(self):
        """Test execution context functionality."""
        ctx = ExecutionContext(
            run_id="test_run",
            workflow_id="test_workflow",
            project_id="test_project",
            vars={"test_var": "test_value"},
            artifacts={"test_artifact": "test_uri"}
        )
        
        assert ctx.run_id == "test_run"
        assert ctx.workflow_id == "test_workflow"
        assert ctx.vars["test_var"] == "test_value"
        assert ctx.artifacts["test_artifact"] == "test_uri"
    
    def test_node_result(self):
        """Test node result functionality."""
        # Test successful result
        success_result = NodeResult(
            node_id="test_node",
            status="ok",
            output={"result": "success"},
            attempts=1
        )
        
        assert success_result.node_id == "test_node"
        assert success_result.status == "ok"
        assert success_result.output["result"] == "success"
        assert success_result.attempts == 1
        assert success_result.error is None
        
        # Test failed result
        failed_result = NodeResult(
            node_id="test_node",
            status="error",
            error="Test error",
            attempts=3
        )
        
        assert failed_result.node_id == "test_node"
        assert failed_result.status == "error"
        assert failed_result.error == "Test error"
        assert failed_result.attempts == 3
        assert failed_result.output is None


class TestSampleWorkflow:
    """Test the sample workflow recipe."""
    
    def test_sample_workflow_yaml(self):
        """Test sample workflow YAML is valid."""
        sample_path = Path(__file__).parent.parent.parent / "workflows" / "sample-linear.yaml"
        
        if not sample_path.exists():
            pytest.skip("Sample workflow file not found")
        
        with open(sample_path, 'r') as f:
            import yaml
            data = yaml.safe_load(f)
        
        assert data['version'] == "1.0"
        assert data['name'] == "Linear Security Scan"
        assert len(data['nodes']) == 3
        
        # Check node structure
        node_ids = [node['id'] for node in data['nodes']]
        assert 'discovery' in node_ids
        assert 'scan' in node_ids
        assert 'enrich' in node_ids
    
    def test_sample_workflow_dag(self):
        """Test sample workflow DAG structure."""
        sample_path = Path(__file__).parent.parent.parent / "workflows" / "sample-linear.yaml"
        
        if not sample_path.exists():
            pytest.skip("Sample workflow file not found")
        
        with open(sample_path, 'r') as f:
            import yaml
            data = yaml.safe_load(f)
        
        nodes = data['nodes']
        
        # Check linear flow: discovery -> scan -> enrich
        discovery_node = next(n for n in nodes if n['id'] == 'discovery')
        scan_node = next(n for n in nodes if n['id'] == 'scan')
        enrich_node = next(n for n in nodes if n['id'] == 'enrich')
        
        assert 'urls' in discovery_node['outputs']
        assert 'urls' in scan_node['inputs']
        assert 'findings' in scan_node['outputs']
        assert 'findings' in enrich_node['inputs']
        assert 'enriched_findings' in enrich_node['outputs']
    
    def test_sample_workflow_retry_state_config(self):
        """Test sample workflow retry and state configuration."""
        sample_path = Path(__file__).parent.parent.parent / "workflows" / "sample-linear.yaml"
        
        if not sample_path.exists():
            pytest.skip("Sample workflow file not found")
        
        with open(sample_path, 'r') as f:
            import yaml
            data = yaml.safe_load(f)
        
        # Check retry configuration
        retry_config = data.get('retry', {})
        assert retry_config['max_attempts'] == 3
        assert retry_config['backoff_factor'] == 2.0
        assert retry_config['base_delay'] == 5.0
        
        # Check state configuration
        state_config = data.get('state', {})
        assert state_config['checkpoint_interval'] == 30
        assert state_config['resume_on_failure'] is True
        assert state_config['cache_intermediate'] is True