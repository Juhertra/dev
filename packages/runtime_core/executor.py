#!/usr/bin/env python3
"""
Runtime Core Execution Engine - Enhanced Implementation

This module provides the core runtime execution engine that actually runs
tool/plugin code and manages data persistence, aligned with FEAT-044.

Key Features:
- Plugin execution via StoragePort
- Finding schema validation
- Resource controls and timeouts
- Sandboxing hooks for M2+
- Python 3.14 concurrency preparation
"""

import sys
import time
import logging
import threading
import signal
import subprocess
from typing import Dict, List, Any, Optional, Callable, Union
from pathlib import Path
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, Future, TimeoutError as FutureTimeoutError
import json
import tempfile
import os

# Import existing components
from packages.workflow_engine.executor import (
    PluginInterface, PluginLoader, ExecutionContext, NodeSpec, NodeResult,
    PluginLoadError, WorkflowExecutionError
)
from packages.storage.adapters.memory import InMemoryStorageAdapter
from packages.runtime_core.storage.storage_port import StoragePort

logger = logging.getLogger(__name__)


@dataclass
class ResourceLimits:
    """Resource limits for plugin execution."""
    max_execution_time: float = 300.0  # 5 minutes default
    max_memory_mb: int = 512  # 512MB default
    max_cpu_percent: float = 80.0  # 80% CPU max
    max_output_size_mb: int = 100  # 100MB output max
    sandbox_enabled: bool = False  # M2+ feature


@dataclass
class ExecutionPolicy:
    """Execution policy for plugins."""
    trusted_plugins: List[str] = field(default_factory=list)
    require_sandbox: bool = True  # Default to sandbox for untrusted
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    allow_network: bool = False  # Network access control
    allow_file_system: bool = True  # File system access control


class FindingValidator:
    """Validates findings against schema v1.0.0."""
    
    REQUIRED_FIELDS = {
        "id", "project_id", "detector_id", "title", "severity", 
        "resource", "evidence", "created_at", "finding_schema_version"
    }
    
    VALID_SEVERITIES = {"critical", "high", "medium", "low", "info"}
    
    @classmethod
    def validate_finding(cls, finding: Dict[str, Any]) -> bool:
        """Validate finding against schema v1.0.0."""
        try:
            # Check required fields
            missing_fields = cls.REQUIRED_FIELDS - set(finding.keys())
            if missing_fields:
                logger.error(f"Missing required fields: {missing_fields}")
                return False
            
            # Validate severity
            if finding["severity"] not in cls.VALID_SEVERITIES:
                logger.error(f"Invalid severity: {finding['severity']}")
                return False
            
            # Validate schema version
            if finding["finding_schema_version"] != "1.0.0":
                logger.error(f"Invalid schema version: {finding['finding_schema_version']}")
                return False
            
            # Validate evidence is dict
            if not isinstance(finding["evidence"], dict):
                logger.error("Evidence must be a dictionary")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Finding validation error: {e}")
            return False


class SandboxExecutor:
    """Sandbox execution for untrusted plugins (M2+ preparation)."""
    
    def __init__(self, policy: ExecutionPolicy):
        """Initialize sandbox executor."""
        self.policy = policy
    
    def execute_in_sandbox(self, plugin_code: str, inputs: Dict[str, Any], 
                          config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """
        Execute plugin in sandboxed environment.
        
        For M1, this is a simplified implementation.
        For M2+, this will use proper sandboxing (subprocess, containers, etc.).
        """
        logger.info(f"Executing plugin in sandbox for project {context.project_id}")
        
        if not self.policy.resource_limits.sandbox_enabled:
            logger.warning("Sandbox not enabled - executing in main process")
            return self._execute_directly(plugin_code, inputs, config, context)
        
        # M1: Simple subprocess execution
        # M2+: Proper sandbox with resource limits
        return self._execute_subprocess(plugin_code, inputs, config, context)
    
    def _execute_directly(self, plugin_code: str, inputs: Dict[str, Any], 
                         config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute plugin directly in main process."""
        # This would execute the plugin code directly
        # For M1, we'll use the existing plugin system
        raise NotImplementedError("Direct execution not implemented in M1")
    
    def _execute_subprocess(self, plugin_code: str, inputs: Dict[str, Any], 
                           config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute plugin in subprocess with resource limits."""
        try:
            # Create temporary script file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(plugin_code)
                script_path = f.name
            
            # Prepare environment
            env = os.environ.copy()
            env['PYTHONPATH'] = str(Path(__file__).parent.parent.parent)
            
            # Execute with timeout
            result = subprocess.run(
                [sys.executable, script_path],
                input=json.dumps({"inputs": inputs, "config": config, "context": context.__dict__}),
                capture_output=True,
                text=True,
                timeout=self.policy.resource_limits.max_execution_time,
                env=env
            )
            
            # Clean up
            os.unlink(script_path)
            
            if result.returncode != 0:
                raise RuntimeError(f"Plugin execution failed: {result.stderr}")
            
            return json.loads(result.stdout)
            
        except subprocess.TimeoutExpired:
            logger.error(f"Plugin execution timed out after {self.policy.resource_limits.max_execution_time}s")
            raise TimeoutError("Plugin execution timed out")
        except Exception as e:
            logger.error(f"Sandbox execution error: {e}")
            raise


class RuntimeExecutor:
    """
    Core runtime execution engine for plugin execution.
    
    This is the main class that the Workflow engine uses to execute plugins.
    Handles plugin loading, execution, validation, and storage.
    """
    
    def __init__(self, storage: Optional[StoragePort] = None, 
                 plugin_loader: Optional[PluginLoader] = None,
                 policy: Optional[ExecutionPolicy] = None):
        """Initialize runtime executor."""
        self.storage = storage or InMemoryStorageAdapter()
        self.plugin_loader = plugin_loader or PluginLoader()
        self.policy = policy or ExecutionPolicy()
        self.finding_validator = FindingValidator()
        self.sandbox_executor = SandboxExecutor(self.policy)
        self._lock = threading.Lock()
        
        # M3 preparation: Thread pool for concurrent execution
        self._executor: Optional[ThreadPoolExecutor] = None
        self._prepare_for_concurrency()
    
    def _prepare_for_concurrency(self):
        """Prepare for M3 concurrent execution."""
        # Check Python version for concurrency features
        python_version = sys.version_info
        if python_version >= (3, 14):
            logger.info("Python 3.14+ detected - preparing for free-threaded execution")
            self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="runtime")
            
            # Check for free-threaded mode
            if hasattr(sys, 'get_switch_interval'):
                logger.info("Free-threaded mode available - GIL removed")
            else:
                logger.info("Standard threading mode - GIL present")
        else:
            logger.info(f"Python {python_version.major}.{python_version.minor} - using standard threading")
    
    def run_step(self, step: 'WorkflowStep') -> Dict[str, Any]:
        """
        Execute a single workflow step.
        
        This is the main method that the Workflow engine calls for each step.
        """
        logger.info(f"Executing step: {step.plugin} for project {step.project_id}")
        
        try:
            # Load plugin
            plugin = self.plugin_loader.load(step.plugin)
            
            # Create execution context
            context = ExecutionContext(
                run_id=step.run_id,
                workflow_id=step.workflow_id,
                project_id=step.project_id
            )
            
            # Execute plugin with resource controls
            result = self._execute_with_controls(
                plugin, step.inputs, step.config, context
            )
            
            # Validate and save findings
            self._process_findings(result.get("findings", []), step.project_id)
            
            logger.info(f"Step {step.plugin} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Step {step.plugin} failed: {e}")
            raise WorkflowExecutionError(f"Plugin {step.plugin} failed: {e}")
    
    def _execute_with_controls(self, plugin: PluginInterface, inputs: Dict[str, Any], 
                              config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute plugin with resource controls and timeouts."""
        
        # Check if plugin is trusted
        is_trusted = plugin.__class__.__name__ in self.policy.trusted_plugins
        
        if is_trusted:
            # Execute trusted plugin directly
            return self._execute_trusted(plugin, inputs, config, context)
        else:
            # Execute untrusted plugin with sandboxing
            return self._execute_untrusted(plugin, inputs, config, context)
    
    def _execute_trusted(self, plugin: PluginInterface, inputs: Dict[str, Any], 
                        config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute trusted plugin with basic timeout."""
        result = {}
        exception = None
        
        def target():
            nonlocal result, exception
            try:
                result = plugin.run(inputs, config, context)
            except Exception as e:
                exception = e
        
        # Execute with timeout
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=self.policy.resource_limits.max_execution_time)
        
        if thread.is_alive():
            logger.error(f"Plugin execution timed out after {self.policy.resource_limits.max_execution_time}s")
            raise TimeoutError("Plugin execution timed out")
        
        if exception:
            raise exception
        
        return result
    
    def _execute_untrusted(self, plugin: PluginInterface, inputs: Dict[str, Any], 
                          config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute untrusted plugin with sandboxing."""
        logger.info(f"Executing untrusted plugin {plugin.__class__.__name__} in sandbox")
        
        # For M1, we'll use the existing plugin system with timeout
        # In M2+, this will use proper sandboxing
        result = {}
        exception = None
        
        def target():
            nonlocal result, exception
            try:
                result = plugin.run(inputs, config, context)
            except Exception as e:
                exception = e
        
        # Execute with timeout
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=self.policy.resource_limits.max_execution_time)
        
        if thread.is_alive():
            logger.error(f"Plugin execution timed out after {self.policy.resource_limits.max_execution_time}s")
            raise TimeoutError("Plugin execution timed out")
        
        if exception:
            raise exception
        
        return result
    
    def _process_findings(self, findings: List[Dict[str, Any]], project_id: str):
        """Process and save findings to storage."""
        for finding in findings:
            try:
                # Validate finding schema
                if not self.finding_validator.validate_finding(finding):
                    logger.error(f"Invalid finding schema: {finding.get('id', 'unknown')}")
                    continue
                
                # Save to storage
                with self._lock:  # Thread safety
                    self.storage.save_finding(finding)
                
                logger.debug(f"Saved finding {finding['id']} to storage")
                
            except Exception as e:
                logger.error(f"Failed to process finding {finding.get('id', 'unknown')}: {e}")
    
    def run_in_sandbox(self, plugin: PluginInterface, inputs: Dict[str, Any], 
                      config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """
        Execute plugin in sandboxed environment.
        
        This method provides hooks for M2+ sandboxing implementation.
        """
        logger.info(f"Executing plugin {plugin.__class__.__name__} in sandbox")
        
        # For M1, this is a placeholder
        # In M2+, this will implement proper sandboxing
        return plugin.run(inputs, config, context)
    
    def get_finding(self, project_id: str, finding_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific finding for debugging/QA."""
        try:
            findings = self.storage.list_findings(project_id)
            for finding in findings:
                if finding.get("id") == finding_id:
                    return finding
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve finding {finding_id}: {e}")
            return None
    
    def validate_storage_integrity(self, project_id: str) -> bool:
        """Validate storage integrity for a project."""
        try:
            findings = self.storage.list_findings(project_id)
            
            # Validate all findings
            for finding in findings:
                if not self.finding_validator.validate_finding(finding):
                    logger.error(f"Invalid finding in storage: {finding.get('id')}")
                    return False
            
            logger.info(f"Storage integrity validated for project {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Storage integrity validation failed: {e}")
            return False
    
    def execute_concurrent_steps(self, steps: List['WorkflowStep']) -> List[Dict[str, Any]]:
        """
        Execute multiple steps concurrently (M3 preparation).
        
        This method prepares for M3 concurrent execution using Python 3.14 features.
        """
        if not self._executor:
            logger.warning("Concurrent execution not available - falling back to sequential")
            # Handle errors gracefully in sequential mode
            results = []
            for step in steps:
                try:
                    result = self.run_step(step)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Sequential step execution failed: {e}")
                    results.append({"error": str(e)})
            return results
        
        logger.info(f"Executing {len(steps)} steps concurrently")
        
        # Submit all steps to thread pool
        futures = [
            self._executor.submit(self.run_step, step) 
            for step in steps
        ]
        
        # Collect results
        results = []
        for future in futures:
            try:
                result = future.result(timeout=self.policy.resource_limits.max_execution_time)
                results.append(result)
            except FutureTimeoutError:
                logger.error("Concurrent step execution timed out")
                results.append({"error": "timeout"})
            except Exception as e:
                logger.error(f"Concurrent step execution failed: {e}")
                results.append({"error": str(e)})
        
        return results
    
    def __del__(self):
        """Cleanup thread pool on destruction."""
        if self._executor:
            self._executor.shutdown(wait=True)


# WorkflowStep dataclass for type hints
@dataclass
class WorkflowStep:
    """Represents a single workflow step to be executed."""
    plugin: str
    inputs: Dict[str, Any]
    config: Dict[str, Any]
    project_id: str
    run_id: str
    workflow_id: str


# Example usage and testing
if __name__ == "__main__":
    # Example usage
    runtime = RuntimeExecutor()
    
    # Create a test step
    step = WorkflowStep(
        plugin="echo",
        inputs={"message": "test"},
        config={},
        project_id="test_project",
        run_id="run_123",
        workflow_id="workflow_456"
    )
    
    try:
        result = runtime.run_step(step)
        print(f"Execution result: {result}")
    except Exception as e:
        print(f"Execution failed: {e}")
