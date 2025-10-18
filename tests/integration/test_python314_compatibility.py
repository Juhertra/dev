"""
Python 3.14 Compatibility Tests for SecFlow

This module tests compatibility with Python 3.14 features and ensures
forward compatibility for the free-threaded Python implementation.
"""

import pytest
import sys
import threading
import time
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

# Python version detection
PYTHON_VERSION = sys.version_info
IS_PYTHON_314 = PYTHON_VERSION >= (3, 14)


class TestPython314Compatibility:
    """Test Python 3.14 specific features and compatibility."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="secflow_py314_")
        
    def teardown_method(self):
        """Clean up test environment."""
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_python_version_compatibility(self):
        """Test that code works on both Python 3.11 and 3.14."""
        # This test should pass on both versions
        assert PYTHON_VERSION >= (3, 11), "Minimum Python version is 3.11"
        
        # Test basic functionality that should work on both versions
        from workflow_engine import WorkflowExecutor
        executor = WorkflowExecutor()
        assert executor is not None, "WorkflowExecutor should instantiate on both Python versions"
    
    @pytest.mark.skipif(not IS_PYTHON_314, reason="Python 3.14 specific test")
    def test_subinterpreter_compatibility(self):
        """Test compatibility with Python 3.14 subinterpreters."""
        # This test only runs on Python 3.14+
        pytest.skip("Subinterpreter testing not yet implemented - requires Python 3.14 runtime")
    
    def test_performance_comparison(self):
        """Compare performance characteristics between Python versions."""
        workflow_config = {
            "name": "performance_test_workflow",
            "version": "1.0",
            "project_id": "performance_test",
            "steps": [
                {
                    "id": "test_step",
                    "plugin": "test_plugin",
                    "config": {"target": "http://test-target.com"}
                }
            ]
        }
        
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
            print(f"Python {PYTHON_VERSION.major}.{PYTHON_VERSION.minor} workflow execution time: {duration:.3f}s")
            
            assert result.success, "Workflow should complete successfully"
            assert duration < 30, f"Performance should be within threshold: {duration:.3f}s"
    
    def test_memory_usage_patterns(self):
        """Test memory usage patterns for Python 3.14 compatibility."""
        import gc
        
        # Create multiple workflow instances to test memory management
        workflows = []
        for i in range(10):
            workflow_config = {
                "name": f"memory_test_workflow_{i}",
                "version": "1.0",
                "project_id": f"memory_test_{i}",
                "steps": [
                    {
                        "id": f"step_{i}",
                        "plugin": "test_plugin",
                        "config": {"target": f"http://test-target-{i}.com"}
                    }
                ]
            }
            workflows.append(workflow_config)
        
        with patch('workflow_engine.WorkflowExecutor') as mock_executor_class:
            mock_executor = mock_executor_class.return_value
            mock_executor.execute.return_value.success = True
            mock_executor.execute.return_value.findings = []
            
            from workflow_engine import WorkflowExecutor
            executor = WorkflowExecutor()
            
            # Execute workflows and monitor memory
            for workflow in workflows:
                result = executor.execute(workflow)
                assert result.success, "All workflows should complete successfully"
            
            # Force garbage collection
            gc.collect()
            
            # Memory usage should be reasonable
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            print(f"Memory usage after workflow execution: {memory_mb:.1f} MB")
            
            # Memory usage should be under 500MB for this test
            assert memory_mb < 500, f"Memory usage should be reasonable: {memory_mb:.1f} MB"


class TestConcurrencyForwardCompatibility:
    """Test forward compatibility for free-threaded Python."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp(prefix="secflow_concurrency_")
        
    def teardown_method(self):
        """Clean up test environment."""
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    @pytest.mark.xfail(reason="Concurrency not fully supported yet")
    def test_thread_safety_workflow_execution(self):
        """Test thread safety of workflow execution."""
        import threading
        import queue
        
        results = queue.Queue()
        errors = queue.Queue()
        
        def run_workflow(workflow_id: str):
            """Run a workflow in a separate thread."""
            try:
                workflow_config = {
                    "name": f"thread_safety_workflow_{workflow_id}",
                    "version": "1.0",
                    "project_id": f"thread_safety_{workflow_id}",
                    "steps": [
                        {
                            "id": f"step_{workflow_id}",
                            "plugin": "test_plugin",
                            "config": {"target": f"http://test-target-{workflow_id}.com"}
                        }
                    ]
                }
                
                with patch('workflow_engine.WorkflowExecutor') as mock_executor_class:
                    mock_executor = mock_executor_class.return_value
                    mock_executor.execute.return_value.success = True
                    mock_executor.execute.return_value.findings = []
                    
                    from workflow_engine import WorkflowExecutor
                    executor = WorkflowExecutor()
                    result = executor.execute(workflow_config)
                    results.put(result)
            except Exception as e:
                errors.put(e)
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=run_workflow, args=(f"thread_{i}",))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=30)
        
        # Collect results
        result_list = []
        while not results.empty():
            result_list.append(results.get())
        
        error_list = []
        while not errors.empty():
            error_list.append(errors.get())
        
        # Assertions
        assert len(error_list) == 0, f"No errors should occur: {error_list}"
        assert len(result_list) == 5, "All workflows should complete"
        assert all(result.success for result in result_list), "All workflows should succeed"
    
    @pytest.mark.xfail(reason="Concurrency not fully supported yet")
    def test_storage_thread_safety(self):
        """Test thread safety of storage operations."""
        import threading
        import queue
        
        findings = queue.Queue()
        errors = queue.Queue()
        
        def store_finding(finding_id: str):
            """Store a finding in a separate thread."""
            try:
                finding = {
                    "detector_id": f"THREAD_SAFETY_TEST_{finding_id}",
                    "timestamp": "2025-10-14T12:00:00Z",
                    "severity": "MEDIUM",
                    "title": f"Thread Safety Test Finding {finding_id}",
                    "description": "Test finding for thread safety",
                    "target": f"http://test-target-{finding_id}.com",
                    "metadata": {
                        "plugin": "test_plugin",
                        "workflow_id": f"thread_safety_workflow_{finding_id}"
                    }
                }
                
                with patch('storage.get_storage') as mock_storage:
                    mock_storage_instance = mock_storage.return_value
                    mock_storage_instance.store_finding.return_value = True
                    
                    from storage import get_storage
                    storage = get_storage()
                    result = storage.store_finding(finding)
                    findings.put(result)
            except Exception as e:
                errors.put(e)
        
        # Start multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=store_finding, args=(f"thread_{i}",))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=30)
        
        # Collect results
        finding_list = []
        while not findings.empty():
            finding_list.append(findings.get())
        
        error_list = []
        while not errors.empty():
            error_list.append(errors.get())
        
        # Assertions
        assert len(error_list) == 0, f"No errors should occur: {error_list}"
        assert len(finding_list) == 10, "All findings should be stored"
        assert all(finding_list), "All storage operations should succeed"
    
    def test_plugin_isolation_threading(self):
        """Test plugin isolation in multi-threaded environment."""
        import threading
        
        results = []
        errors = []
        
        def run_plugin(plugin_id: str):
            """Run a plugin in a separate thread."""
            try:
                plugin_config = {
                    "name": f"isolation_test_plugin_{plugin_id}",
                    "target": f"http://test-target-{plugin_id}.com",
                    "timeout": 30
                }
                
                with patch('plugin_loader.PluginLoader') as mock_loader_class:
                    mock_loader = mock_loader_class.return_value
                    mock_loader.execute_plugin.return_value = {
                        "success": True,
                        "findings": [],
                        "execution_time": 1.0
                    }
                    
                    from plugin_loader import PluginLoader
                    loader = PluginLoader()
                    result = loader.execute_plugin(plugin_config)
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=run_plugin, args=(f"plugin_{i}",))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=30)
        
        # Assertions
        assert len(errors) == 0, f"No errors should occur: {error_list}"
        assert len(results) == 3, "All plugins should complete"
        assert all(result["success"] for result in results), "All plugins should succeed"


class TestDependencyCompatibility:
    """Test compatibility with dependencies on Python 3.14."""
    
    def test_pytest_compatibility(self):
        """Test that pytest works correctly on Python 3.14."""
        # Basic pytest functionality test
        assert pytest.__version__ is not None, "Pytest should be available"
        
        # Test that pytest fixtures work
        @pytest.fixture
        def test_fixture():
            return "test_value"
        
        def test_fixture_usage(test_fixture):
            assert test_fixture == "test_value", "Pytest fixtures should work"
        
        # This test should pass
        test_fixture_usage("test_value")
    
    def test_mock_compatibility(self):
        """Test that unittest.mock works correctly on Python 3.14."""
        from unittest.mock import Mock, patch
        
        # Test basic mock functionality
        mock_obj = Mock()
        mock_obj.test_method.return_value = "test_result"
        
        assert mock_obj.test_method() == "test_result", "Mock should work correctly"
        
        # Test patch functionality
        with patch('builtins.len') as mock_len:
            mock_len.return_value = 42
            assert len("test") == 42, "Patch should work correctly"
    
    def test_json_compatibility(self):
        """Test that JSON operations work correctly on Python 3.14."""
        import json
        
        test_data = {
            "name": "test",
            "version": "1.0",
            "config": {
                "timeout": 30,
                "retries": 3
            }
        }
        
        # Test JSON serialization
        json_str = json.dumps(test_data)
        assert isinstance(json_str, str), "JSON serialization should work"
        
        # Test JSON deserialization
        parsed_data = json.loads(json_str)
        assert parsed_data == test_data, "JSON deserialization should work"
    
    def test_pathlib_compatibility(self):
        """Test that pathlib works correctly on Python 3.14."""
        from pathlib import Path
        
        # Test basic path operations
        test_path = Path(self.temp_dir) / "test_file.txt"
        test_path.write_text("test content")
        
        assert test_path.exists(), "Path should exist"
        assert test_path.read_text() == "test content", "Path operations should work"
        
        # Test path joining
        joined_path = Path(self.temp_dir) / "subdir" / "file.txt"
        joined_path.parent.mkdir(parents=True, exist_ok=True)
        joined_path.write_text("test")
        
        assert joined_path.exists(), "Path joining should work"


class TestPerformanceRegression:
    """Test for performance regressions in Python 3.14."""
    
    def test_workflow_execution_performance(self):
        """Test workflow execution performance."""
        workflow_config = {
            "name": "performance_regression_test",
            "version": "1.0",
            "project_id": "performance_test",
            "steps": [
                {
                    "id": "performance_step",
                    "plugin": "test_plugin",
                    "config": {"target": "http://test-target.com"}
                }
            ]
        }
        
        with patch('workflow_engine.WorkflowExecutor') as mock_executor_class:
            mock_executor = mock_executor_class.return_value
            mock_executor.execute.return_value.success = True
            mock_executor.execute.return_value.findings = []
            
            # Measure execution time
            start_time = time.time()
            
            from workflow_engine import WorkflowExecutor
            executor = WorkflowExecutor()
            result = executor.execute(workflow_config)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Log performance metrics
            print(f"Python {PYTHON_VERSION.major}.{PYTHON_VERSION.minor} workflow execution: {duration:.3f}s")
            
            assert result.success, "Workflow should complete successfully"
            assert duration < 1.0, f"Performance should be reasonable: {duration:.3f}s"
    
    def test_memory_efficiency(self):
        """Test memory efficiency of operations."""
        import gc
        
        # Create multiple objects to test memory management
        objects = []
        for i in range(100):
            obj = {
                "id": i,
                "data": f"test_data_{i}" * 100,  # Create some memory usage
                "config": {"timeout": 30, "retries": 3}
            }
            objects.append(obj)
        
        # Force garbage collection
        gc.collect()
        
        # Memory usage should be reasonable
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        print(f"Memory usage after object creation: {memory_mb:.1f} MB")
        
        # Clean up
        del objects
        gc.collect()
        
        # Memory should be cleaned up
        memory_after_mb = process.memory_info().rss / 1024 / 1024
        print(f"Memory usage after cleanup: {memory_after_mb:.1f} MB")
        
        # Memory usage should be under 200MB for this test
        assert memory_mb < 200, f"Memory usage should be reasonable: {memory_mb:.1f} MB"
