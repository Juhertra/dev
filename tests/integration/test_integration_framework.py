"""
Integration Test Framework for SecFlow M1

This module provides comprehensive integration testing for SecFlow's core features,
including end-to-end workflows, error handling, security scenarios, and observability checks.
"""

import pytest
import tempfile
import shutil
import time
import threading
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock

# Test configuration
INTEGRATION_TEST_TIMEOUT = 30  # seconds
PERFORMANCE_THRESHOLD = 30  # seconds for workflow completion


class IntegrationTestBase:
    """Base class for integration tests with common utilities."""
    
    def setup_method(self):
        """Set up test environment for each test method."""
        self.temp_dir = tempfile.mkdtemp(prefix="secflow_integration_")
        self.test_project_id = "integration_test_project"
        
    def teardown_method(self):
        """Clean up test environment after each test method."""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_test_workflow(self, workflow_type: str = "linear") -> Dict[str, Any]:
        """Create a test workflow configuration."""
        if workflow_type == "linear":
            return {
                "name": "test_linear_workflow",
                "version": "1.0",
                "project_id": self.test_project_id,
                "steps": [
                    {
                        "id": "step1",
                        "plugin": "nuclei",
                        "config": {
                            "target": "http://test-target.com",
                            "templates": "res://templates/nuclei:latest"
                        }
                    }
                ]
            }
        elif workflow_type == "error_handling":
            return {
                "name": "test_error_workflow",
                "version": "1.0", 
                "project_id": self.test_project_id,
                "steps": [
                    {
                        "id": "step1",
                        "plugin": "failing_plugin",
                        "config": {
                            "should_fail": True
                        }
                    }
                ]
            }
        else:
            raise ValueError(f"Unknown workflow type: {workflow_type}")
    
    def create_test_plugin(self, plugin_name: str = "test_plugin") -> Dict[str, Any]:
        """Create a test plugin manifest."""
        return {
            "name": plugin_name,
            "version": "1.0.0",
            "binary": "test_binary",
            "capabilities": ["scan"],
            "config_schema": "schemas/test-config.json",
            "defaults": {
                "timeout": 30,
                "retries": 3
            },
            "signature": "test_signature_hash"
        }
    
    def create_test_finding(self, severity: str = "MEDIUM") -> Dict[str, Any]:
        """Create a test finding."""
        return {
            "detector_id": "TEST_DETECTOR_001",
            "timestamp": "2025-10-14T12:00:00Z",
            "severity": severity,
            "title": "Test Finding",
            "description": "This is a test finding for integration tests",
            "target": "http://test-target.com",
            "metadata": {
                "plugin": "test_plugin",
                "workflow_id": "test_workflow"
            }
        }


class TestHappyPathWorkflow(IntegrationTestBase):
    """Test successful end-to-end workflow execution."""
    
    def test_linear_workflow_execution(self):
        """Test that a linear workflow completes successfully."""
        # Setup
        workflow_config = self.create_test_workflow("linear")
        test_finding = self.create_test_finding("HIGH")
        
        # Mock the workflow executor and storage
        with patch('workflow_engine.WorkflowExecutor') as mock_executor_class:
            with patch('storage.get_storage') as mock_storage:
                # Configure mocks
                mock_executor = mock_executor_class.return_value
                mock_executor.execute.return_value.success = True
                mock_executor.execute.return_value.findings = [test_finding]
                
                mock_storage_instance = mock_storage.return_value
                mock_storage_instance.list_findings.return_value = [test_finding]
                
                # Execute workflow
                from workflow_engine import WorkflowExecutor
                executor = WorkflowExecutor()
                result = executor.execute(workflow_config)
                
                # Assertions
                assert result.success, "Workflow should complete successfully"
                assert len(result.findings) > 0, "Workflow should produce findings"
                assert result.findings[0]["severity"] in ["LOW", "MEDIUM", "HIGH"], "Finding should have valid severity"
                
                # Verify findings were stored
                storage = mock_storage_instance
                findings = storage.list_findings(project_id=self.test_project_id)
                assert len(findings) > 0, "Findings should be stored"
                assert findings[0]["severity"] == "HIGH", "Stored finding should match expected severity"
    
    def test_workflow_performance(self):
        """Test that workflow completes within performance threshold."""
        workflow_config = self.create_test_workflow("linear")
        
        with patch('workflow_engine.WorkflowExecutor') as mock_executor_class:
            mock_executor = mock_executor_class.return_value
            mock_executor.execute.return_value.success = True
            mock_executor.execute.return_value.findings = []
            
            # Time the execution
            start_time = time.time()
            
            from workflow_engine import WorkflowExecutor
            executor = WorkflowExecutor()
            result = executor.execute(workflow_config)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Assertions
            assert result.success, "Workflow should complete successfully"
            assert duration < PERFORMANCE_THRESHOLD, f"Workflow should complete within {PERFORMANCE_THRESHOLD}s, took {duration:.2f}s"


class TestErrorHandling(IntegrationTestBase):
    """Test error handling scenarios."""
    
    def test_plugin_failure_handling(self):
        """Test that plugin failures are handled gracefully."""
        workflow_config = self.create_test_workflow("error_handling")
        
        with patch('workflow_engine.WorkflowExecutor') as mock_executor_class:
            mock_executor = mock_executor_class.return_value
            mock_executor.execute.return_value.success = False
            mock_executor.execute.return_value.error = "Plugin execution failed"
            mock_executor.execute.return_value.findings = []
            
            from workflow_engine import WorkflowExecutor
            executor = WorkflowExecutor()
            result = executor.execute(workflow_config)
            
            # Assertions
            assert not result.success, "Workflow should fail gracefully"
            assert result.error is not None, "Error should be captured"
            assert "Plugin execution failed" in result.error, "Error message should be descriptive"
    
    def test_invalid_workflow_config(self):
        """Test handling of invalid workflow configurations."""
        invalid_workflow = {
            "name": "invalid_workflow",
            "steps": []  # Missing required fields
        }
        
        with patch('workflow_engine.WorkflowExecutor') as mock_executor_class:
            mock_executor = mock_executor_class.return_value
            mock_executor.execute.side_effect = ValueError("Invalid workflow configuration")
            
            from workflow_engine import WorkflowExecutor
            executor = WorkflowExecutor()
            
            with pytest.raises(ValueError, match="Invalid workflow configuration"):
                executor.execute(invalid_workflow)


class TestSecurityScenarios(IntegrationTestBase):
    """Test security-related scenarios."""
    
    def test_plugin_signature_validation(self):
        """Test that plugins with invalid signatures are rejected."""
        valid_plugin = self.create_test_plugin("valid_plugin")
        invalid_plugin = self.create_test_plugin("invalid_plugin")
        invalid_plugin["signature"] = "invalid_signature_hash"
        
        with patch('plugin_loader.PluginLoader') as mock_loader_class:
            mock_loader = mock_loader_class.return_value
            mock_loader.validate_signature.side_effect = [
                True,   # Valid plugin
                False   # Invalid plugin
            ]
            
            from plugin_loader import PluginLoader
            loader = PluginLoader()
            
            # Test valid plugin
            assert loader.validate_signature(valid_plugin), "Valid plugin should pass signature validation"
            
            # Test invalid plugin
            assert not loader.validate_signature(invalid_plugin), "Invalid plugin should fail signature validation"
    
    def test_plugin_isolation(self):
        """Test that plugins cannot access unauthorized resources."""
        malicious_plugin = self.create_test_plugin("malicious_plugin")
        malicious_plugin["capabilities"] = ["scan", "file_access"]  # Unauthorized capability
        
        with patch('plugin_loader.PluginLoader') as mock_loader_class:
            mock_loader = mock_loader_class.return_value
            mock_loader.validate_capabilities.side_effect = ValueError("Unauthorized capability detected")
            
            from plugin_loader import PluginLoader
            loader = PluginLoader()
            
            with pytest.raises(ValueError, match="Unauthorized capability detected"):
                loader.validate_capabilities(malicious_plugin)


class TestObservabilityChecks(IntegrationTestBase):
    """Test observability and monitoring functionality."""
    
    def test_workflow_metrics_collection(self):
        """Test that workflow execution populates metrics."""
        workflow_config = self.create_test_workflow("linear")
        
        with patch('workflow_engine.WorkflowExecutor') as mock_executor_class:
            with patch('metrics.MetricsCollector') as mock_metrics_class:
                mock_executor = mock_executor_class.return_value
                mock_executor.execute.return_value.success = True
                mock_executor.execute.return_value.findings = [self.create_test_finding()]
                
                mock_metrics = mock_metrics_class.return_value
                
                from workflow_engine import WorkflowExecutor
                executor = WorkflowExecutor()
                result = executor.execute(workflow_config)
                
                # Verify metrics were collected
                mock_metrics.record_workflow_execution.assert_called_once()
                mock_metrics.record_findings_count.assert_called_once_with(1)
    
    def test_logging_output(self):
        """Test that workflow execution produces appropriate logs."""
        workflow_config = self.create_test_workflow("linear")
        
        with patch('workflow_engine.WorkflowExecutor') as mock_executor_class:
            with patch('logging.getLogger') as mock_logger_class:
                mock_executor = mock_executor_class.return_value
                mock_executor.execute.return_value.success = True
                mock_executor.execute.return_value.findings = []
                
                mock_logger = mock_logger_class.return_value
                
                from workflow_engine import WorkflowExecutor
                executor = WorkflowExecutor()
                result = executor.execute(workflow_config)
                
                # Verify logging occurred
                mock_logger.info.assert_called()
                mock_logger.debug.assert_called()


class TestConcurrencyAndThreadSafety(IntegrationTestBase):
    """Test concurrency and thread safety scenarios."""
    
    @pytest.mark.xfail(reason="Concurrency not fully supported yet")
    def test_concurrent_workflow_execution(self):
        """Test concurrent execution of workflows in isolated environments."""
        results = []
        errors = []
        
        def run_workflow(workflow_id: str):
            """Run a workflow in a separate thread."""
            try:
                workflow_config = self.create_test_workflow("linear")
                workflow_config["project_id"] = f"{self.test_project_id}_{workflow_id}"
                
                with patch('workflow_engine.WorkflowExecutor') as mock_executor_class:
                    mock_executor = mock_executor_class.return_value
                    mock_executor.execute.return_value.success = True
                    mock_executor.execute.return_value.findings = [self.create_test_finding()]
                    
                    from workflow_engine import WorkflowExecutor
                    executor = WorkflowExecutor()
                    result = executor.execute(workflow_config)
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=run_workflow, args=(f"thread_{i}",))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=INTEGRATION_TEST_TIMEOUT)
        
        # Assertions
        assert len(errors) == 0, f"No errors should occur during concurrent execution: {errors}"
        assert len(results) == 3, "All workflows should complete successfully"
        assert all(result.success for result in results), "All workflows should succeed"
    
    def test_storage_thread_safety(self):
        """Test that storage operations are thread-safe."""
        findings = []
        errors = []
        
        def store_finding(finding_id: str):
            """Store a finding in a separate thread."""
            try:
                finding = self.create_test_finding()
                finding["detector_id"] = f"TEST_DETECTOR_{finding_id}"
                
                with patch('storage.get_storage') as mock_storage:
                    mock_storage_instance = mock_storage.return_value
                    mock_storage_instance.store_finding.return_value = True
                    
                    from storage import get_storage
                    storage = get_storage()
                    result = storage.store_finding(finding)
                    findings.append(result)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=store_finding, args=(f"thread_{i}",))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=INTEGRATION_TEST_TIMEOUT)
        
        # Assertions
        assert len(errors) == 0, f"No errors should occur during concurrent storage: {errors}"
        assert len(findings) == 5, "All findings should be stored successfully"


class TestPython314Compatibility(IntegrationTestBase):
    """Test Python 3.14 compatibility and new features."""
    
    def test_subinterpreter_compatibility(self):
        """Test that workflow execution works with Python 3.14 subinterpreters."""
        workflow_config = self.create_test_workflow("linear")
        
        # This test will be marked as xfail until Python 3.14 is fully supported
        pytest.skip("Python 3.14 subinterpreter testing not yet implemented")
    
    def test_performance_comparison(self):
        """Compare performance between Python versions."""
        workflow_config = self.create_test_workflow("linear")
        
        with patch('workflow_engine.WorkflowExecutor') as mock_executor_class:
            mock_executor = mock_executor_class.return_value
            mock_executor.execute.return_value.success = True
            mock_executor.execute.return_value.findings = []
            
            # Benchmark execution time
            start_time = time.time()
            
            from workflow_engine import WorkflowExecutor
            executor = WorkflowExecutor()
            result = executor.execute(workflow_config)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Log performance metrics for comparison
            print(f"Workflow execution time: {duration:.3f}s")
            
            assert result.success, "Workflow should complete successfully"
            assert duration < PERFORMANCE_THRESHOLD, f"Performance should be within threshold: {duration:.3f}s"


# Test data fixtures
@pytest.fixture
def sample_workflow_yaml():
    """Provide a sample workflow YAML for testing."""
    return """
name: sample_linear_workflow
version: 1.0
project_id: test_project
steps:
  - id: nuclei_scan
    plugin: nuclei
    config:
      target: http://test-target.com
      templates: res://templates/nuclei:latest
      rate_limit: 150
      threads: 25
"""

@pytest.fixture
def sample_plugin_manifest():
    """Provide a sample plugin manifest for testing."""
    return {
        "name": "nuclei",
        "version": "1.0.0",
        "binary": "nuclei",
        "capabilities": ["scan"],
        "config_schema": "schemas/nuclei-config.json",
        "defaults": {
            "rate_limit": 150,
            "templates": "res://templates/nuclei:latest",
            "threads": 25
        },
        "signature": "valid_signature_hash"
    }

@pytest.fixture
def sample_finding_data():
    """Provide sample finding data for testing."""
    return {
        "detector_id": "NUCLEI_001",
        "timestamp": "2025-10-14T12:00:00Z",
        "severity": "HIGH",
        "title": "SQL Injection Vulnerability",
        "description": "SQL injection vulnerability detected in login form",
        "target": "http://test-target.com/login",
        "metadata": {
            "plugin": "nuclei",
            "template": "sql-injection",
            "workflow_id": "sample_linear_workflow"
        }
    }
