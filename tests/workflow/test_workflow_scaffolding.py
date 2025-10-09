"""
Workflow Engine Tests - M0 Scaffolding

Basic tests for workflow engine scaffolding components.
"""

import pytest
import yaml
from pathlib import Path
import sys

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from packages.workflow_engine.executor import WorkflowExecutor, Workflow, WorkflowNode
    from packages.workflow_engine.validate_recipe import RecipeValidator
except ImportError:
    pytest.skip("Workflow engine packages not available", allow_module_level=True)


class TestWorkflowScaffolding:
    """Test workflow engine scaffolding components."""
    
    def test_workflow_executor_import(self):
        """Test WorkflowExecutor can be imported."""
        assert WorkflowExecutor is not None
        executor = WorkflowExecutor()
        assert executor is not None
    
    def test_recipe_validator_import(self):
        """Test RecipeValidator can be imported."""
        assert RecipeValidator is not None
        validator = RecipeValidator()
        assert validator is not None
    
    def test_workflow_model_creation(self):
        """Test Workflow and WorkflowNode model creation."""
        node = WorkflowNode(
            id="test_node",
            type="test.type",
            config={"param": "value"},
            inputs=["input1"],
            outputs=["output1"]
        )
        
        workflow = Workflow(
            id="test_workflow",
            name="Test Workflow",
            description="Test description",
            nodes=[node]
        )
        
        assert workflow.id == "test_workflow"
        assert workflow.name == "Test Workflow"
        assert len(workflow.nodes) == 1
        assert workflow.nodes[0].id == "test_node"
    
    def test_executor_stub_methods(self):
        """Test executor stub methods work."""
        executor = WorkflowExecutor()
        
        # Test validation stub
        node = WorkflowNode(id="test", type="test", config={}, inputs=[], outputs=[])
        workflow = Workflow(id="test", name="test", description="test", nodes=[node])
        
        result = executor.validate_workflow(workflow)
        assert result is True  # Stub always returns True
    
    def test_validator_stub_methods(self):
        """Test validator stub methods work."""
        validator = RecipeValidator()
        
        # Test YAML validation
        valid, error = validator.validate_yaml_syntax("workflows/sample-linear.yaml")
        assert valid is True
        assert error is None
        
        # Test schema validation
        test_data = {
            "version": "1.0",
            "name": "Test",
            "nodes": []
        }
        valid, error = validator.validate_schema(test_data)
        assert valid is True
        assert error is None


class TestSampleWorkflow:
    """Test the sample workflow recipe."""
    
    def test_sample_workflow_yaml(self):
        """Test sample workflow YAML is valid."""
        sample_path = Path(__file__).parent.parent.parent / "workflows" / "sample-linear.yaml"
        
        with open(sample_path, 'r') as f:
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
        
        with open(sample_path, 'r') as f:
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
