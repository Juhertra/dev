#!/usr/bin/env python3
"""
Tests for Runtime Core Execution Engine

Tests the core runtime execution engine that runs tool/plugin code
and manages data persistence.
"""

import pytest
import time
import threading
import tempfile
import os
from unittest.mock import Mock, patch
from typing import Dict, Any, List

# Add packages to path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from packages.runtime_core.executor import (
    RuntimeExecutor, WorkflowStep, ResourceLimits, ExecutionPolicy,
    FindingValidator, SandboxExecutor, PluginLoadError, WorkflowExecutionError
)
from packages.workflow_engine.executor import PluginInterface, ExecutionContext
from packages.storage.adapters.memory import InMemoryStorageAdapter


class DummyPluginSuccess(PluginInterface):
    """Dummy plugin that always succeeds."""
    
    def run(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Return a successful result with findings."""
        finding = {
            "id": "TEST-1",
            "project_id": context.project_id,
            "detector_id": "test.plugin",
            "title": "Test finding",
            "severity": "low",
            "resource": "test://resource",
            "evidence": {"test": "data"},
            "created_at": "2023-01-01T00:00:00Z",
            "finding_schema_version": "1.0.0"
        }
        
        return {
            "outputs": {"data": "ok"},
            "findings": [finding],
            "status": "success"
        }


class DummyPluginFail(PluginInterface):
    """Dummy plugin that always fails."""
    
    def run(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Raise an exception."""
        raise RuntimeError("Plugin execution failed")


class DummyPluginTimeout(PluginInterface):
    """Dummy plugin that takes too long."""
    
    def run(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Sleep for a long time."""
        time.sleep(2)  # Longer than test timeout
        return {"outputs": {"data": "timeout"}, "findings": [], "status": "success"}


class DummyPluginInvalidFinding(PluginInterface):
    """Dummy plugin that returns invalid findings."""
    
    def run(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Return invalid finding."""
        invalid_finding = {
            "id": "INVALID-1",
            "project_id": context.project_id,
            "detector_id": "test.plugin",
            "title": "Invalid finding",
            "severity": "invalid_severity",  # Invalid severity
            "resource": "test://resource",
            "evidence": {"test": "data"},
            "created_at": "2023-01-01T00:00:00Z",
            "finding_schema_version": "1.0.0"
        }
        
        return {
            "outputs": {"data": "invalid"},
            "findings": [invalid_finding],
            "status": "success"
        }


class TestRuntimeExecutor:
    """Test RuntimeExecutor core functionality."""
    
    def test_runtime_executor_initialization(self):
        """Test RuntimeExecutor initialization."""
        storage = InMemoryStorageAdapter()
        policy = ExecutionPolicy()
        runtime = RuntimeExecutor(storage=storage, policy=policy)
        
        assert runtime.storage is storage
        assert runtime.policy is policy
        assert runtime.finding_validator is not None
        assert runtime.sandbox_executor is not None
    
    def test_run_step_success(self):
        """Test successful step execution."""
        storage = InMemoryStorageAdapter()
        runtime = RuntimeExecutor(storage=storage)
        
        # Mock plugin loader to return our dummy plugin
        with patch.object(runtime.plugin_loader, 'load', return_value=DummyPluginSuccess()):
            step = WorkflowStep(
                plugin="dummy.success",
                inputs={"test": "input"},
                config={"param": "value"},
                project_id="test_project",
                run_id="run_123",
                workflow_id="workflow_456"
            )
            
            result = runtime.run_step(step)
            
            assert result["status"] == "success"
            assert result["outputs"]["data"] == "ok"
            assert len(result["findings"]) == 1
            
            # Check finding was saved in storage
            findings = storage.list_findings("test_project")
            assert len(findings) == 1
            assert findings[0]["id"] == "TEST-1"
    
    def test_run_step_failure(self):
        """Test step execution failure."""
        storage = InMemoryStorageAdapter()
        runtime = RuntimeExecutor(storage=storage)
        
        # Mock plugin loader to return failing plugin
        with patch.object(runtime.plugin_loader, 'load', return_value=DummyPluginFail()):
            step = WorkflowStep(
                plugin="dummy.fail",
                inputs={"test": "input"},
                config={},
                project_id="test_project",
                run_id="run_123",
                workflow_id="workflow_456"
            )
            
            with pytest.raises(WorkflowExecutionError):
                runtime.run_step(step)
            
            # Check no findings were saved on failure
            findings = storage.list_findings("test_project")
            assert len(findings) == 0
    
    def test_run_step_timeout(self):
        """Test step execution timeout."""
        storage = InMemoryStorageAdapter()
        policy = ExecutionPolicy()
        policy.resource_limits.max_execution_time = 0.1  # Very short timeout
        runtime = RuntimeExecutor(storage=storage, policy=policy)
        
        # Mock plugin loader to return timeout plugin
        with patch.object(runtime.plugin_loader, 'load', return_value=DummyPluginTimeout()):
            step = WorkflowStep(
                plugin="dummy.timeout",
                inputs={"test": "input"},
                config={},
                project_id="test_project",
                run_id="run_123",
                workflow_id="workflow_456"
            )
            
            with pytest.raises(WorkflowExecutionError, match="Plugin execution timed out"):
                runtime.run_step(step)
    
    def test_run_step_invalid_finding(self):
        """Test step execution with invalid findings."""
        storage = InMemoryStorageAdapter()
        runtime = RuntimeExecutor(storage=storage)
        
        # Mock plugin loader to return plugin with invalid findings
        with patch.object(runtime.plugin_loader, 'load', return_value=DummyPluginInvalidFinding()):
            step = WorkflowStep(
                plugin="dummy.invalid",
                inputs={"test": "input"},
                config={},
                project_id="test_project",
                run_id="run_123",
                workflow_id="workflow_456"
            )
            
            result = runtime.run_step(step)
            
            # Should succeed but invalid finding should not be saved
            assert result["status"] == "success"
            
            # Check no findings were saved due to validation failure
            findings = storage.list_findings("test_project")
            assert len(findings) == 0
    
    def test_get_finding(self):
        """Test finding retrieval for debugging."""
        storage = InMemoryStorageAdapter()
        runtime = RuntimeExecutor(storage=storage)
        
        # Add a test finding
        test_finding = {
            "id": "DEBUG-1",
            "project_id": "test_project",
            "detector_id": "test.plugin",
            "title": "Debug finding",
            "severity": "info",
            "resource": "test://resource",
            "evidence": {"debug": "data"},
            "created_at": "2023-01-01T00:00:00Z",
            "finding_schema_version": "1.0.0"
        }
        storage.save_finding(test_finding)
        
        # Retrieve finding
        found = runtime.get_finding("test_project", "DEBUG-1")
        assert found is not None
        assert found["id"] == "DEBUG-1"
        
        # Test non-existent finding
        not_found = runtime.get_finding("test_project", "NONEXISTENT")
        assert not_found is None
    
    def test_validate_storage_integrity(self):
        """Test storage integrity validation."""
        storage = InMemoryStorageAdapter()
        runtime = RuntimeExecutor(storage=storage)
        
        # Add valid finding
        valid_finding = {
            "id": "VALID-1",
            "project_id": "test_project",
            "detector_id": "test.plugin",
            "title": "Valid finding",
            "severity": "medium",
            "resource": "test://resource",
            "evidence": {"valid": "data"},
            "created_at": "2023-01-01T00:00:00Z",
            "finding_schema_version": "1.0.0"
        }
        storage.save_finding(valid_finding)
        
        # Validate integrity
        is_valid = runtime.validate_storage_integrity("test_project")
        assert is_valid is True
        
        # Add invalid finding
        invalid_finding = {
            "id": "INVALID-2",
            "project_id": "test_project",
            "detector_id": "test.plugin",
            "title": "Invalid finding",
            "severity": "invalid",  # Invalid severity
            "resource": "test://resource",
            "evidence": {"invalid": "data"},
            "created_at": "2023-01-01T00:00:00Z",
            "finding_schema_version": "1.0.0"
        }
        storage.save_finding(invalid_finding)
        
        # Validate integrity should fail
        is_valid = runtime.validate_storage_integrity("test_project")
        assert is_valid is False


class TestFindingValidator:
    """Test FindingValidator functionality."""
    
    def test_validate_finding_success(self):
        """Test successful finding validation."""
        finding = {
            "id": "TEST-1",
            "project_id": "test_project",
            "detector_id": "test.plugin",
            "title": "Test finding",
            "severity": "high",
            "resource": "test://resource",
            "evidence": {"test": "data"},
            "created_at": "2023-01-01T00:00:00Z",
            "finding_schema_version": "1.0.0"
        }
        
        is_valid = FindingValidator.validate_finding(finding)
        assert is_valid is True
    
    def test_validate_finding_missing_fields(self):
        """Test finding validation with missing fields."""
        finding = {
            "id": "TEST-1",
            "project_id": "test_project",
            "detector_id": "test.plugin",
            "title": "Test finding",
            "severity": "high",
            "resource": "test://resource",
            "evidence": {"test": "data"},
            "created_at": "2023-01-01T00:00:00Z"
            # Missing finding_schema_version
        }
        
        is_valid = FindingValidator.validate_finding(finding)
        assert is_valid is False
    
    def test_validate_finding_invalid_severity(self):
        """Test finding validation with invalid severity."""
        finding = {
            "id": "TEST-1",
            "project_id": "test_project",
            "detector_id": "test.plugin",
            "title": "Test finding",
            "severity": "invalid_severity",
            "resource": "test://resource",
            "evidence": {"test": "data"},
            "created_at": "2023-01-01T00:00:00Z",
            "finding_schema_version": "1.0.0"
        }
        
        is_valid = FindingValidator.validate_finding(finding)
        assert is_valid is False
    
    def test_validate_finding_invalid_schema_version(self):
        """Test finding validation with invalid schema version."""
        finding = {
            "id": "TEST-1",
            "project_id": "test_project",
            "detector_id": "test.plugin",
            "title": "Test finding",
            "severity": "high",
            "resource": "test://resource",
            "evidence": {"test": "data"},
            "created_at": "2023-01-01T00:00:00Z",
            "finding_schema_version": "2.0.0"  # Invalid version
        }
        
        is_valid = FindingValidator.validate_finding(finding)
        assert is_valid is False


class TestResourceLimits:
    """Test ResourceLimits functionality."""
    
    def test_resource_limits_defaults(self):
        """Test default resource limits."""
        limits = ResourceLimits()
        
        assert limits.max_execution_time == 300.0
        assert limits.max_memory_mb == 512
        assert limits.max_cpu_percent == 80.0
        assert limits.max_output_size_mb == 100
        assert limits.sandbox_enabled is False
    
    def test_resource_limits_custom(self):
        """Test custom resource limits."""
        limits = ResourceLimits(
            max_execution_time=60.0,
            max_memory_mb=1024,
            max_cpu_percent=90.0,
            max_output_size_mb=200,
            sandbox_enabled=True
        )
        
        assert limits.max_execution_time == 60.0
        assert limits.max_memory_mb == 1024
        assert limits.max_cpu_percent == 90.0
        assert limits.max_output_size_mb == 200
        assert limits.sandbox_enabled is True


class TestExecutionPolicy:
    """Test ExecutionPolicy functionality."""
    
    def test_execution_policy_defaults(self):
        """Test default execution policy."""
        policy = ExecutionPolicy()
        
        assert policy.trusted_plugins == []
        assert policy.require_sandbox is True
        assert policy.resource_limits is not None
        assert policy.allow_network is False
        assert policy.allow_file_system is True
    
    def test_execution_policy_custom(self):
        """Test custom execution policy."""
        limits = ResourceLimits(max_execution_time=120.0)
        policy = ExecutionPolicy(
            trusted_plugins=["echo", "test"],
            require_sandbox=False,
            resource_limits=limits,
            allow_network=True,
            allow_file_system=False
        )
        
        assert policy.trusted_plugins == ["echo", "test"]
        assert policy.require_sandbox is False
        assert policy.resource_limits.max_execution_time == 120.0
        assert policy.allow_network is True
        assert policy.allow_file_system is False


class TestConcurrentExecution:
    """Test concurrent execution functionality (M3 preparation)."""
    
    def test_execute_concurrent_steps(self):
        """Test concurrent step execution."""
        storage = InMemoryStorageAdapter()
        runtime = RuntimeExecutor(storage=storage)
        
        # Create multiple steps
        steps = [
            WorkflowStep(
                plugin="dummy.success",
                inputs={"test": f"input_{i}"},
                config={},
                project_id="test_project",
                run_id=f"run_{i}",
                workflow_id="workflow_456"
            )
            for i in range(3)
        ]
        
        # Mock plugin loader to return our dummy plugin
        with patch.object(runtime.plugin_loader, 'load', return_value=DummyPluginSuccess()):
            results = runtime.execute_concurrent_steps(steps)
            
            assert len(results) == 3
            for result in results:
                assert result["status"] == "success"
                assert result["outputs"]["data"] == "ok"
    
    def test_execute_concurrent_steps_with_failure(self):
        """Test concurrent step execution with some failures."""
        storage = InMemoryStorageAdapter()
        runtime = RuntimeExecutor(storage=storage)
        
        # Create steps with mixed success/failure
        steps = [
            WorkflowStep(
                plugin="dummy.success",
                inputs={"test": "input_1"},
                config={},
                project_id="test_project",
                run_id="run_1",
                workflow_id="workflow_456"
            ),
            WorkflowStep(
                plugin="dummy.fail",
                inputs={"test": "input_2"},
                config={},
                project_id="test_project",
                run_id="run_2",
                workflow_id="workflow_456"
            )
        ]
        
        # Mock plugin loader to return different plugins
        def mock_load(plugin_name):
            if plugin_name == "dummy.success":
                return DummyPluginSuccess()
            elif plugin_name == "dummy.fail":
                return DummyPluginFail()
            else:
                raise PluginLoadError(f"Unknown plugin: {plugin_name}")
        
        with patch.object(runtime.plugin_loader, 'load', side_effect=mock_load):
            results = runtime.execute_concurrent_steps(steps)
            
            assert len(results) == 2
            assert results[0]["status"] == "success"
            assert "error" in results[1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
