"""
Integration Test Configuration for SecFlow

This module provides configuration and utilities for running integration tests.
"""

import pytest
import os
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Integration test configuration
INTEGRATION_TEST_CONFIG = {
    "timeout": 30,
    "performance_threshold": 30,
    "memory_threshold_mb": 500,
    "concurrent_threads": 5,
    "test_data_dir": "tests/data",
    "fixtures_dir": "tests/fixtures"
}

def pytest_configure(config):
    """Configure pytest for integration tests."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "security: mark test as security test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "concurrency: mark test as concurrency test"
    )
    config.addinivalue_line(
        "markers", "python314: mark test as Python 3.14 specific"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection for integration tests."""
    for item in items:
        # Add integration marker to all tests in this directory
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add specific markers based on test name
        if "e2e" in item.name:
            item.add_marker(pytest.mark.e2e)
        if "security" in item.name:
            item.add_marker(pytest.mark.security)
        if "performance" in item.name:
            item.add_marker(pytest.mark.performance)
        if "concurrency" in item.name:
            item.add_marker(pytest.mark.concurrency)
        if "python314" in item.name:
            item.add_marker(pytest.mark.python314)

# Test fixtures
@pytest.fixture(scope="session")
def integration_config():
    """Provide integration test configuration."""
    return INTEGRATION_TEST_CONFIG

@pytest.fixture(scope="session")
def test_data_dir():
    """Provide test data directory."""
    data_dir = Path(INTEGRATION_TEST_CONFIG["test_data_dir"])
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

@pytest.fixture(scope="session")
def fixtures_dir():
    """Provide fixtures directory."""
    fixtures_dir = Path(INTEGRATION_TEST_CONFIG["fixtures_dir"])
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    return fixtures_dir

@pytest.fixture
def temp_workflow_dir(tmp_path):
    """Provide temporary directory for workflow testing."""
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    return workflow_dir

@pytest.fixture
def temp_plugin_dir(tmp_path):
    """Provide temporary directory for plugin testing."""
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()
    return plugin_dir

@pytest.fixture
def temp_storage_dir(tmp_path):
    """Provide temporary directory for storage testing."""
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    return storage_dir

# Test utilities
class IntegrationTestUtils:
    """Utilities for integration tests."""
    
    @staticmethod
    def create_test_environment(base_dir: Path) -> Dict[str, Path]:
        """Create a complete test environment."""
        env = {
            "workflows": base_dir / "workflows",
            "plugins": base_dir / "plugins", 
            "storage": base_dir / "storage",
            "config": base_dir / "config",
            "logs": base_dir / "logs"
        }
        
        for path in env.values():
            path.mkdir(parents=True, exist_ok=True)
        
        return env
    
    @staticmethod
    def cleanup_test_environment(env: Dict[str, Path]):
        """Clean up test environment."""
        import shutil
        for path in env.values():
            if path.exists():
                shutil.rmtree(path)
    
    @staticmethod
    def mock_plugin_execution(plugin_name: str, success: bool = True, findings: List[Dict] = None):
        """Mock plugin execution for testing."""
        if findings is None:
            findings = []
        
        def mock_execute(config: Dict) -> Dict:
            return {
                "success": success,
                "findings": findings,
                "execution_time": 1.0,
                "plugin": plugin_name
            }
        
        return mock_execute
    
    @staticmethod
    def mock_workflow_executor(success: bool = True, findings: List[Dict] = None, error: str = None):
        """Mock workflow executor for testing."""
        if findings is None:
            findings = []
        
        def mock_execute(workflow_config: Dict) -> Dict:
            return {
                "success": success,
                "findings": findings,
                "error": error,
                "execution_time": 2.0,
                "workflow_id": workflow_config.get("name", "test_workflow")
            }
        
        return mock_execute

# Test data fixtures
@pytest.fixture
def sample_workflow_config():
    """Provide sample workflow configuration."""
    return {
        "name": "sample_integration_workflow",
        "version": "1.0",
        "project_id": "integration_test_project",
        "steps": [
            {
                "id": "nuclei_scan",
                "plugin": "nuclei",
                "config": {
                    "target": "http://test-target.com",
                    "templates": "res://templates/nuclei:latest",
                    "rate_limit": 150,
                    "threads": 25
                }
            }
        ]
    }

@pytest.fixture
def sample_plugin_manifest():
    """Provide sample plugin manifest."""
    return {
        "name": "nuclei",
        "version": "1.0.0",
        "binary": "nuclei",
        "capabilities": ["scan"],
        "config_schema": "schemas/nuclei-config.json",
        "defaults": {
            "rate_limit": 150,
            "templates": "res://templates/nuclei:latest",
            "threads": 25,
            "timeout": 30
        },
        "signature": "nuclei_signature_hash_12345"
    }

@pytest.fixture
def sample_findings():
    """Provide sample findings data."""
    return [
        {
            "detector_id": "NUCLEI_SQL_INJECTION_001",
            "timestamp": "2025-10-14T12:00:00Z",
            "severity": "HIGH",
            "title": "SQL Injection Vulnerability",
            "description": "SQL injection vulnerability detected in login form",
            "target": "http://test-target.com/login",
            "metadata": {
                "plugin": "nuclei",
                "template": "sql-injection",
                "workflow_id": "sample_integration_workflow"
            }
        },
        {
            "detector_id": "NUCLEI_XSS_001",
            "timestamp": "2025-10-14T12:01:00Z",
            "severity": "MEDIUM",
            "title": "Cross-Site Scripting",
            "description": "XSS vulnerability detected in search form",
            "target": "http://test-target.com/search",
            "metadata": {
                "plugin": "nuclei",
                "template": "xss",
                "workflow_id": "sample_integration_workflow"
            }
        }
    ]

# Performance testing utilities
@pytest.fixture
def performance_monitor():
    """Provide performance monitoring utilities."""
    import time
    import psutil
    import threading
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.start_memory = None
            self.process = psutil.Process()
        
        def start(self):
            """Start performance monitoring."""
            self.start_time = time.time()
            self.start_memory = self.process.memory_info().rss / 1024 / 1024
        
        def stop(self):
            """Stop performance monitoring and return metrics."""
            if self.start_time is None:
                raise RuntimeError("Performance monitoring not started")
            
            end_time = time.time()
            end_memory = self.process.memory_info().rss / 1024 / 1024
            
            return {
                "execution_time": end_time - self.start_time,
                "memory_start_mb": self.start_memory,
                "memory_end_mb": end_memory,
                "memory_delta_mb": end_memory - self.start_memory
            }
    
    return PerformanceMonitor()

# Concurrency testing utilities
@pytest.fixture
def concurrency_tester():
    """Provide concurrency testing utilities."""
    import threading
    import queue
    import time
    
    class ConcurrencyTester:
        def __init__(self):
            self.results = queue.Queue()
            self.errors = queue.Queue()
        
        def run_concurrent(self, func, args_list, timeout=30):
            """Run function concurrently with multiple argument sets."""
            threads = []
            
            for args in args_list:
                thread = threading.Thread(target=self._run_with_error_handling, args=(func, args))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=timeout)
            
            # Collect results
            results = []
            while not self.results.empty():
                results.append(self.results.get())
            
            errors = []
            while not self.errors.empty():
                errors.append(self.errors.get())
            
            return results, errors
        
        def _run_with_error_handling(self, func, args):
            """Run function with error handling."""
            try:
                result = func(*args)
                self.results.put(result)
            except Exception as e:
                self.errors.put(e)
    
    return ConcurrencyTester()
