"""
SecFlow Observability Integration

This module provides integration hooks for metrics collection and structured logging
in workflow execution. Integrates with WorkflowExecutor and NodeExecutor to provide
comprehensive observability.

Key Features:
- Workflow execution metrics collection
- Plugin execution timing and error tracking
- Structured logging with context correlation
- Performance monitoring and alerting
- Thread-safe operations for concurrent execution
"""

import time
import threading
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
import sys
import os

# Add the packages directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from packages.runtime_core.observability.metrics import get_metrics, MetricsCollector
from packages.runtime_core.observability.logging import (
    get_logger, get_workflow_logger, set_log_context, clear_log_context
)


class ObservabilityHooks:
    """
    Observability hooks for workflow execution.
    
    Provides metrics collection and structured logging integration
    for WorkflowExecutor and NodeExecutor.
    """
    
    def __init__(self):
        """Initialize observability hooks."""
        self.metrics = get_metrics()
        self.logger = get_logger()
        self.workflow_logger = get_workflow_logger()
        self._lock = threading.RLock()
    
    @contextmanager
    def workflow_execution_context(self, workflow_id: str, workflow_name: str, 
                                 project_id: str, run_id: str):
        """
        Context manager for workflow execution observability.
        
        Args:
            workflow_id: Workflow identifier
            workflow_name: Workflow name
            project_id: Project identifier
            run_id: Run identifier
        """
        start_time = time.time()
        
        # Set logging context
        set_log_context(
            workflow_id=workflow_id,
            run_id=run_id,
            project_id=project_id
        )
        
        # Log workflow start
        self.workflow_logger.workflow_started(
            workflow_id, workflow_name, project_id, run_id
        )
        
        try:
            yield
        except Exception as e:
            # Log workflow failure
            duration = time.time() - start_time
            self.workflow_logger.workflow_failed(
                workflow_id, str(e), duration
            )
            
            # Record metrics
            self.metrics.record_workflow_exec(
                workflow_id, duration, success=False
            )
            
            raise
        finally:
            # Clear logging context
            clear_log_context()
    
    @contextmanager
    def node_execution_context(self, node_id: str, plugin_name: str, 
                              workflow_id: str, attempt: int = 1):
        """
        Context manager for node execution observability.
        
        Args:
            node_id: Node identifier
            plugin_name: Plugin name
            workflow_id: Workflow identifier
            attempt: Attempt number
        """
        start_time = time.time()
        
        # Set logging context
        set_log_context(
            workflow_id=workflow_id,
            node_id=node_id,
            plugin_name=plugin_name
        )
        
        # Log node start
        self.workflow_logger.node_started(node_id, plugin_name, attempt)
        
        try:
            yield
        except Exception as e:
            # Log node failure
            duration = time.time() - start_time
            self.workflow_logger.node_failed(
                node_id, plugin_name, str(e), duration, attempt
            )
            
            # Record metrics
            self.metrics.record_plugin_exec(
                plugin_name, duration, success=False, retry_count=attempt-1
            )
            
            raise
        finally:
            # Clear logging context
            clear_log_context()
    
    def record_node_success(self, node_id: str, plugin_name: str, 
                           duration: float, findings_count: int = 0) -> None:
        """
        Record successful node execution.
        
        Args:
            node_id: Node identifier
            plugin_name: Plugin name
            duration: Execution duration
            findings_count: Number of findings generated
        """
        # Log node completion
        self.workflow_logger.node_completed(
            node_id, plugin_name, duration, success=True, findings_count=findings_count
        )
        
        # Record metrics
        self.metrics.record_plugin_exec(
            plugin_name, duration, success=True
        )
        
        if findings_count > 0:
            self.metrics.record_findings(findings_count)
    
    def record_workflow_success(self, workflow_id: str, duration: float, 
                               findings_count: int) -> None:
        """
        Record successful workflow execution.
        
        Args:
            workflow_id: Workflow identifier
            duration: Total execution duration
            findings_count: Total findings generated
        """
        # Log workflow completion
        self.workflow_logger.workflow_completed(
            workflow_id, duration, success=True, findings_count=findings_count
        )
        
        # Record metrics
        self.metrics.record_workflow_exec(
            workflow_id, duration, success=True, findings_count=findings_count
        )
    
    def log_plugin_output(self, plugin_name: str, output: str, 
                         output_type: str = "stdout") -> None:
        """
        Log plugin output.
        
        Args:
            plugin_name: Plugin name
            output: Output content
            output_type: Type of output (stdout, stderr, etc.)
        """
        self.workflow_logger.plugin_output(plugin_name, output, output_type)
    
    def incr_plugin_error(self, plugin_name: str = "unknown") -> None:
        """Increment plugin error counter."""
        self.metrics.incr_plugin_error(plugin_name)
    
    def incr_workflow_error(self, workflow_id: str = "unknown") -> None:
        """Increment workflow error counter."""
        self.metrics.incr_workflow_error(workflow_id)
    
    def check_performance_thresholds(self, component: str, duration: float) -> None:
        """
        Check performance thresholds and log warnings.
        
        Args:
            component: Component name (plugin or workflow)
            duration: Execution duration
        """
        summary = self.metrics.get_summary()
        thresholds = summary.get('thresholds', {})
        
        if component == 'plugin':
            warning_threshold = thresholds.get('plugin_warning_seconds', 10.0)
            if duration > warning_threshold:
                self.workflow_logger.performance_warning(
                    component, duration, warning_threshold
                )
        elif component == 'workflow':
            warning_threshold = thresholds.get('workflow_warning_seconds', 30.0)
            if duration > warning_threshold:
                self.workflow_logger.performance_warning(
                    component, duration, warning_threshold
                )


# Global observability hooks instance
observability_hooks = ObservabilityHooks()


def get_observability_hooks() -> ObservabilityHooks:
    """Get the global observability hooks instance."""
    return observability_hooks


def init_observability() -> ObservabilityHooks:
    """
    Initialize observability system.
    
    Returns:
        Configured ObservabilityHooks instance
    """
    logger = get_logger()
    logger.info("Initializing SecFlow observability integration")
    return observability_hooks
