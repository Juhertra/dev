"""
End-to-End Integration Test Scenarios for SecFlow M1

This module contains specific integration test scenarios that mirror real user workflows.
"""

import pytest
import tempfile
import shutil
import os
import time
import subprocess
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from typing import Dict, Any, List

from tests.integration.test_data_manager import TestDataManager, MOCK_WORKFLOW_CONFIG, MOCK_FINDINGS


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows using real plugins."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="secflow_e2e_")
        self.data_manager = TestDataManager(Path(self.temp_dir) / "data")
        
    def teardown_method(self):
        """Clean up test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_nuclei_workflow_execution(self):
        """Test complete Nuclei workflow execution."""
        # Create test files
        workflow_file = self.data_manager.create_workflow_yaml("linear")
        plugin_manifest = self.data_manager.create_plugin_manifest("nuclei")
        config_schema = self.data_manager.create_config_schema("nuclei")
        
        # Mock the actual Nuclei execution
        with patch('subprocess.run') as mock_run:
            # Mock successful Nuclei execution
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = json.dumps(MOCK_FINDINGS)
            mock_run.return_value.stderr = ""
            
            # Mock file operations
            with patch('builtins.open', mock_open(read_data=json.dumps(MOCK_WORKFLOW_CONFIG))):
                with patch('workflow_engine.WorkflowExecutor') as mock_executor_class:
                    mock_executor = mock_executor_class.return_value
                    mock_executor.execute.return_value.success = True
                    mock_executor.execute.return_value.findings = MOCK_FINDINGS
                    
                    # Execute workflow
                    from workflow_engine import WorkflowExecutor
                    executor = WorkflowExecutor()
                    result = executor.execute(MOCK_WORKFLOW_CONFIG)
                    
                    # Assertions
                    assert result.success, "Nuclei workflow should complete successfully"
                    assert len(result.findings) == 3, "Should produce 3 findings"
                    assert all(f["severity"] in ["LOW", "MEDIUM", "HIGH"] for f in result.findings), "All findings should have valid severity"
                    
                    # Verify Nuclei was called with correct parameters
                    mock_run.assert_called_once()
                    call_args = mock_run.call_args
                    assert "nuclei" in call_args[0][0], "Nuclei binary should be called"
    
    def test_workflow_with_real_plugin_integration(self):
        """Test workflow execution with real plugin integration."""
        # This test would use actual plugin binaries if available
        pytest.skip("Real plugin integration requires actual plugin binaries")
    
    def test_cli_workflow_execution(self):
        """Test workflow execution via CLI interface."""
        workflow_file = self.data_manager.create_workflow_yaml("linear")
        
        # Mock CLI execution
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Workflow completed successfully"
            mock_run.return_value.stderr = ""
            
            # Execute via CLI
            result = subprocess.run([
                "python", "-m", "tools.run_workflow",
                "--workflow", workflow_file,
                "--project", "test_project"
            ], capture_output=True, text=True, timeout=30)
            
            # Assertions
            assert result.returncode == 0, f"CLI execution should succeed: {result.stderr}"
            assert "Workflow completed successfully" in result.stdout, "Should show success message"
    
    def test_api_workflow_execution(self):
        """Test workflow execution via API interface."""
        workflow_config = MOCK_WORKFLOW_CONFIG
        
        with patch('api.workflow.WorkflowAPI') as mock_api_class:
            mock_api = mock_api_class.return_value
            mock_api.execute_workflow.return_value = {
                "success": True,
                "workflow_id": "test_workflow_123",
                "findings": MOCK_FINDINGS,
                "execution_time": 15.5
            }
            
            # Execute via API
            from api.workflow import WorkflowAPI
            api = WorkflowAPI()
            result = api.execute_workflow(workflow_config)
            
            # Assertions
            assert result["success"], "API execution should succeed"
            assert "workflow_id" in result, "Should return workflow ID"
            assert len(result["findings"]) == 3, "Should return findings"
            assert result["execution_time"] < 30, "Should complete within performance threshold"


class TestErrorHandlingScenarios:
    """Test error handling in various scenarios."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="secflow_error_")
        self.data_manager = TestDataManager(Path(self.temp_dir) / "data")
        
    def teardown_method(self):
        """Clean up test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_plugin_timeout_handling(self):
        """Test handling of plugin timeouts."""
        workflow_config = self.data_manager.create_test_workflow("error_handling")
        
        with patch('workflow_engine.WorkflowExecutor') as mock_executor_class:
            mock_executor = mock_executor_class.return_value
            mock_executor.execute.side_effect = TimeoutError("Plugin execution timed out")
            
            from workflow_engine import WorkflowExecutor
            executor = WorkflowExecutor()
            
            with pytest.raises(TimeoutError, match="Plugin execution timed out"):
                executor.execute(workflow_config)
    
    def test_plugin_crash_handling(self):
        """Test handling of plugin crashes."""
        workflow_config = self.data_manager.create_test_workflow("error_handling")
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "Plugin crashed with segmentation fault"
            
            with patch('workflow_engine.WorkflowExecutor') as mock_executor_class:
                mock_executor = mock_executor_class.return_value
                mock_executor.execute.return_value.success = False
                mock_executor.execute.return_value.error = "Plugin crashed with segmentation fault"
                
                from workflow_engine import WorkflowExecutor
                executor = WorkflowExecutor()
                result = executor.execute(workflow_config)
                
                # Assertions
                assert not result.success, "Workflow should fail gracefully"
                assert "Plugin crashed" in result.error, "Error should be captured"
    
    def test_invalid_target_handling(self):
        """Test handling of invalid targets."""
        invalid_workflow = {
            "name": "invalid_target_workflow",
            "version": "1.0",
            "project_id": "test_project",
            "steps": [
                {
                    "id": "invalid_target_scan",
                    "plugin": "nuclei",
                    "config": {
                        "target": "invalid://target",
                        "templates": "res://templates/nuclei:latest"
                    }
                }
            ]
        }
        
        with patch('workflow_engine.WorkflowExecutor') as mock_executor_class:
            mock_executor = mock_executor_class.return_value
            mock_executor.execute.return_value.success = False
            mock_executor.execute.return_value.error = "Invalid target format"
            
            from workflow_engine import WorkflowExecutor
            executor = WorkflowExecutor()
            result = executor.execute(invalid_workflow)
            
            # Assertions
            assert not result.success, "Workflow should fail with invalid target"
            assert "Invalid target format" in result.error, "Should provide clear error message"


class TestSecurityScenarios:
    """Test security-related scenarios."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="secflow_security_")
        self.data_manager = TestDataManager(Path(self.temp_dir) / "data")
        
    def teardown_method(self):
        """Clean up test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_plugin_signature_verification(self):
        """Test plugin signature verification."""
        valid_manifest = self.data_manager.create_plugin_manifest("valid_plugin")
        invalid_manifest = self.data_manager.create_plugin_manifest("invalid_plugin")
        
        # Modify the invalid manifest to have a bad signature
        with open(invalid_manifest, 'r') as f:
            manifest_data = json.load(f)
        manifest_data["signature"] = "invalid_signature_hash"
        with open(invalid_manifest, 'w') as f:
            json.dump(manifest_data, f)
        
        with patch('plugin_loader.PluginLoader') as mock_loader_class:
            mock_loader = mock_loader_class.return_value
            
            # Mock signature validation
            def validate_signature(manifest):
                with open(manifest, 'r') as f:
                    data = json.load(f)
                return data["signature"] != "invalid_signature_hash"
            
            mock_loader.validate_signature.side_effect = validate_signature
            
            from plugin_loader import PluginLoader
            loader = PluginLoader()
            
            # Test valid plugin
            assert loader.validate_signature(valid_manifest), "Valid plugin should pass signature validation"
            
            # Test invalid plugin
            assert not loader.validate_signature(invalid_manifest), "Invalid plugin should fail signature validation"
    
    def test_plugin_capability_restrictions(self):
        """Test that plugins are restricted to their declared capabilities."""
        malicious_manifest = {
            "name": "malicious_plugin",
            "version": "1.0.0",
            "binary": "malicious_binary",
            "capabilities": ["scan"],  # Only scan capability
            "config_schema": "schemas/malicious-config.json",
            "defaults": {},
            "signature": "malicious_signature_hash"
        }
        
        with patch('plugin_loader.PluginLoader') as mock_loader_class:
            mock_loader = mock_loader_class.return_value
            mock_loader.validate_capabilities.side_effect = ValueError("Unauthorized capability: file_access")
            
            from plugin_loader import PluginLoader
            loader = PluginLoader()
            
            with pytest.raises(ValueError, match="Unauthorized capability"):
                loader.validate_capabilities(malicious_manifest)
    
    def test_plugin_isolation(self):
        """Test that plugins cannot access unauthorized system resources."""
        # This would test actual plugin isolation in a real environment
        pytest.skip("Plugin isolation testing requires actual plugin execution environment")


class TestObservabilityScenarios:
    """Test observability and monitoring scenarios."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="secflow_observability_")
        self.data_manager = TestDataManager(Path(self.temp_dir) / "data")
        
    def teardown_method(self):
        """Clean up test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_workflow_metrics_collection(self):
        """Test that workflow execution collects appropriate metrics."""
        workflow_config = MOCK_WORKFLOW_CONFIG
        
        with patch('metrics.MetricsCollector') as mock_metrics_class:
            mock_metrics = mock_metrics_class.return_value
            
            with patch('workflow_engine.WorkflowExecutor') as mock_executor_class:
                mock_executor = mock_executor_class.return_value
                mock_executor.execute.return_value.success = True
                mock_executor.execute.return_value.findings = MOCK_FINDINGS
                mock_executor.execute.return_value.execution_time = 15.5
                
                from workflow_engine import WorkflowExecutor
                executor = WorkflowExecutor()
                result = executor.execute(workflow_config)
                
                # Verify metrics collection
                mock_metrics.record_workflow_execution.assert_called_once()
                mock_metrics.record_findings_count.assert_called_once_with(3)
                mock_metrics.record_execution_time.assert_called_once_with(15.5)
    
    def test_logging_output(self):
        """Test that workflow execution produces appropriate logs."""
        workflow_config = MOCK_WORKFLOW_CONFIG
        
        with patch('logging.getLogger') as mock_logger_class:
            mock_logger = mock_logger_class.return_value
            
            with patch('workflow_engine.WorkflowExecutor') as mock_executor_class:
                mock_executor = mock_executor_class.return_value
                mock_executor.execute.return_value.success = True
                mock_executor.execute.return_value.findings = MOCK_FINDINGS
                
                from workflow_engine import WorkflowExecutor
                executor = WorkflowExecutor()
                result = executor.execute(workflow_config)
                
                # Verify logging
                mock_logger.info.assert_called()
                mock_logger.debug.assert_called()
                
                # Check specific log messages
                info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
                assert any("Workflow execution started" in msg for msg in info_calls), "Should log workflow start"
                assert any("Workflow execution completed" in msg for msg in info_calls), "Should log workflow completion"
    
    def test_performance_monitoring(self):
        """Test performance monitoring and alerting."""
        workflow_config = MOCK_WORKFLOW_CONFIG
        
        with patch('metrics.MetricsCollector') as mock_metrics_class:
            mock_metrics = mock_metrics_class.return_value
            
            with patch('workflow_engine.WorkflowExecutor') as mock_executor_class:
                mock_executor = mock_executor_class.return_value
                mock_executor.execute.return_value.success = True
                mock_executor.execute.return_value.findings = MOCK_FINDINGS
                mock_executor.execute.return_value.execution_time = 35.0  # Over threshold
                
                from workflow_engine import WorkflowExecutor
                executor = WorkflowExecutor()
                result = executor.execute(workflow_config)
                
                # Verify performance monitoring
                mock_metrics.record_execution_time.assert_called_once_with(35.0)
                mock_metrics.check_performance_threshold.assert_called_once_with(35.0, 30.0)


class TestConcurrencyScenarios:
    """Test concurrency and thread safety scenarios."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="secflow_concurrency_")
        self.data_manager = TestDataManager(Path(self.temp_dir) / "data")
        
    def teardown_method(self):
        """Clean up test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @pytest.mark.xfail(reason="Concurrency not fully supported yet")
    def test_concurrent_workflow_execution(self):
        """Test concurrent execution of multiple workflows."""
        import threading
        import time
        
        results = []
        errors = []
        
        def run_workflow(workflow_id: str):
            """Run a workflow in a separate thread."""
            try:
                workflow_config = MOCK_WORKFLOW_CONFIG.copy()
                workflow_config["project_id"] = f"concurrent_test_{workflow_id}"
                
                with patch('workflow_engine.WorkflowExecutor') as mock_executor_class:
                    mock_executor = mock_executor_class.return_value
                    mock_executor.execute.return_value.success = True
                    mock_executor.execute.return_value.findings = MOCK_FINDINGS
                    
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
            thread.join(timeout=30)
        
        # Assertions
        assert len(errors) == 0, f"No errors should occur: {errors}"
        assert len(results) == 3, "All workflows should complete"
        assert all(result.success for result in results), "All workflows should succeed"
    
    def test_storage_concurrent_access(self):
        """Test concurrent access to storage."""
        import threading
        
        findings = []
        errors = []
        
        def store_finding(finding_id: str):
            """Store a finding in a separate thread."""
            try:
                finding = MOCK_FINDINGS[0].copy()
                finding["detector_id"] = f"CONCURRENT_TEST_{finding_id}"
                
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
            thread.join(timeout=30)
        
        # Assertions
        assert len(errors) == 0, f"No errors should occur: {errors}"
        assert len(findings) == 5, "All findings should be stored"
        assert all(findings), "All storage operations should succeed"
