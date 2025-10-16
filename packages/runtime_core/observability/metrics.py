"""
SecFlow Observability Metrics Collection

This module provides metrics collection for workflow execution, plugin performance,
and system resource usage. Designed for M1 implementation with M2+ scalability.

Key Features:
- Thread-safe metrics collection for concurrent execution
- Plugin execution timing and error tracking
- Workflow performance monitoring
- Resource usage metrics (when available)
- Python 3.14 compatibility with no-GIL mode
"""

import time
import threading
import statistics
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class MetricValue:
    """Container for metric values with metadata."""
    value: Union[float, int]
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class ExecutionMetrics:
    """Container for execution-related metrics."""
    plugin_exec_seconds: List[float] = field(default_factory=list)
    plugin_errors: int = 0
    plugin_retries: int = 0
    workflow_exec_seconds: List[float] = field(default_factory=list)
    workflow_errors: int = 0
    findings_generated: int = 0
    throughput_per_minute: float = 0.0


class MetricsCollector:
    """
    Thread-safe metrics collector for SecFlow observability.
    
    Designed for M1 implementation with M2+ scalability considerations.
    Uses thread-safe operations for concurrent workflow execution.
    """
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize metrics collector.
        
        Args:
            max_history: Maximum number of historical values to keep
        """
        self._lock = threading.RLock()  # Reentrant lock for nested calls
        self._max_history = max_history
        
        # Core metrics storage
        self.metrics = ExecutionMetrics()
        
        # Plugin-specific metrics
        self._plugin_metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'executions': 0,
            'errors': 0,
            'retries': 0,
            'total_time': 0.0,
            'min_time': float('inf'),
            'max_time': 0.0
        })
        
        # Workflow-specific metrics
        self._workflow_metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'executions': 0,
            'errors': 0,
            'total_time': 0.0,
            'findings': 0
        })
        
        # Performance thresholds
        self._performance_thresholds = {
            'plugin_warning_seconds': 10.0,
            'workflow_warning_seconds': 30.0,
            'plugin_error_seconds': 60.0,
            'workflow_error_seconds': 120.0
        }
        
        # Resource usage tracking (placeholder for M2+)
        self._resource_metrics = {
            'memory_usage_mb': deque(maxlen=max_history),
            'cpu_usage_percent': deque(maxlen=max_history)
        }
    
    def record_plugin_exec(self, plugin_name: str, duration: float, 
                          success: bool = True, retry_count: int = 0) -> None:
        """
        Record plugin execution metrics.
        
        Args:
            plugin_name: Name of the plugin executed
            duration: Execution time in seconds
            success: Whether execution was successful
            retry_count: Number of retries attempted
        """
        with self._lock:
            # Add to global metrics
            self.metrics.plugin_exec_seconds.append(duration)
            if len(self.metrics.plugin_exec_seconds) > self._max_history:
                self.metrics.plugin_exec_seconds.pop(0)
            
            if not success:
                self.metrics.plugin_errors += 1
            
            if retry_count > 0:
                self.metrics.plugin_retries += retry_count
            
            # Update plugin-specific metrics
            plugin_metrics = self._plugin_metrics[plugin_name]
            plugin_metrics['executions'] += 1
            plugin_metrics['total_time'] += duration
            plugin_metrics['min_time'] = min(plugin_metrics['min_time'], duration)
            plugin_metrics['max_time'] = max(plugin_metrics['max_time'], duration)
            
            if not success:
                plugin_metrics['errors'] += 1
            
            if retry_count > 0:
                plugin_metrics['retries'] += retry_count
            
            # Log performance warnings
            if duration > self._performance_thresholds['plugin_warning_seconds']:
                logger.warning(f"Slow plugin execution: {plugin_name} took {duration:.2f}s")
            
            if duration > self._performance_thresholds['plugin_error_seconds']:
                logger.error(f"Very slow plugin execution: {plugin_name} took {duration:.2f}s")
    
    def record_workflow_exec(self, workflow_id: str, duration: float, 
                           success: bool = True, findings_count: int = 0) -> None:
        """
        Record workflow execution metrics.
        
        Args:
            workflow_id: ID of the workflow executed
            duration: Total execution time in seconds
            success: Whether workflow completed successfully
            findings_count: Number of findings generated
        """
        with self._lock:
            # Add to global metrics
            self.metrics.workflow_exec_seconds.append(duration)
            if len(self.metrics.workflow_exec_seconds) > self._max_history:
                self.metrics.workflow_exec_seconds.pop(0)
            
            if not success:
                self.metrics.workflow_errors += 1
            
            self.metrics.findings_generated += findings_count
            
            # Update workflow-specific metrics
            workflow_metrics = self._workflow_metrics[workflow_id]
            workflow_metrics['executions'] += 1
            workflow_metrics['total_time'] += duration
            workflow_metrics['findings'] += findings_count
            
            if not success:
                workflow_metrics['errors'] += 1
            
            # Log performance warnings
            if duration > self._performance_thresholds['workflow_warning_seconds']:
                logger.warning(f"Slow workflow execution: {workflow_id} took {duration:.2f}s")
            
            if duration > self._performance_thresholds['workflow_error_seconds']:
                logger.error(f"Very slow workflow execution: {workflow_id} took {duration:.2f}s")
    
    def incr_plugin_error(self, plugin_name: str = "unknown") -> None:
        """Increment plugin error counter."""
        with self._lock:
            self.metrics.plugin_errors += 1
            self._plugin_metrics[plugin_name]['errors'] += 1
    
    def incr_workflow_error(self, workflow_id: str = "unknown") -> None:
        """Increment workflow error counter."""
        with self._lock:
            self.metrics.workflow_errors += 1
            self._workflow_metrics[workflow_id]['errors'] += 1
    
    def record_findings(self, count: int) -> None:
        """Record findings generated."""
        with self._lock:
            self.metrics.findings_generated += count
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics summary.
        
        Returns:
            Dictionary containing aggregated metrics
        """
        with self._lock:
            summary = {
                'global': {
                    'plugin_executions': len(self.metrics.plugin_exec_seconds),
                    'plugin_errors': self.metrics.plugin_errors,
                    'plugin_retries': self.metrics.plugin_retries,
                    'workflow_executions': len(self.metrics.workflow_exec_seconds),
                    'workflow_errors': self.metrics.workflow_errors,
                    'findings_generated': self.metrics.findings_generated,
                    'throughput_per_minute': self._calculate_throughput()
                },
                'performance': {
                    'plugin_exec_avg': statistics.mean(self.metrics.plugin_exec_seconds) if self.metrics.plugin_exec_seconds else 0.0,
                    'plugin_exec_p95': statistics.quantiles(self.metrics.plugin_exec_seconds, n=20)[18] if len(self.metrics.plugin_exec_seconds) >= 20 else 0.0,
                    'workflow_exec_avg': statistics.mean(self.metrics.workflow_exec_seconds) if self.metrics.workflow_exec_seconds else 0.0,
                    'workflow_exec_p95': statistics.quantiles(self.metrics.workflow_exec_seconds, n=20)[18] if len(self.metrics.workflow_exec_seconds) >= 20 else 0.0,
                },
                'plugins': dict(self._plugin_metrics),
                'workflows': dict(self._workflow_metrics),
                'thresholds': self._performance_thresholds
            }
            
            return summary
    
    def _calculate_throughput(self) -> float:
        """Calculate throughput (executions per minute)."""
        if not self.metrics.plugin_exec_seconds:
            return 0.0
        
        # Simple calculation: executions in last minute
        current_time = time.time()
        recent_executions = [
            t for t in self.metrics.plugin_exec_seconds 
            if current_time - t < 60.0
        ]
        
        return len(recent_executions)
    
    def reset_metrics(self) -> None:
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self.metrics = ExecutionMetrics()
            self._plugin_metrics.clear()
            self._workflow_metrics.clear()
            self._resource_metrics['memory_usage_mb'].clear()
            self._resource_metrics['cpu_usage_percent'].clear()
    
    def export_metrics(self, format: str = 'json') -> str:
        """
        Export metrics in specified format.
        
        Args:
            format: Export format ('json', 'prometheus')
            
        Returns:
            Formatted metrics string
        """
        summary = self.get_summary()
        
        if format == 'json':
            return json.dumps(summary, indent=2)
        elif format == 'prometheus':
            return self._export_prometheus(summary)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _export_prometheus(self, summary: Dict[str, Any]) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        # Global metrics
        global_metrics = summary['global']
        lines.append(f"# HELP secflow_plugin_executions_total Total plugin executions")
        lines.append(f"# TYPE secflow_plugin_executions_total counter")
        lines.append(f"secflow_plugin_executions_total {global_metrics['plugin_executions']}")
        
        lines.append(f"# HELP secflow_plugin_errors_total Total plugin errors")
        lines.append(f"# TYPE secflow_plugin_errors_total counter")
        lines.append(f"secflow_plugin_errors_total {global_metrics['plugin_errors']}")
        
        lines.append(f"# HELP secflow_workflow_executions_total Total workflow executions")
        lines.append(f"# TYPE secflow_workflow_executions_total counter")
        lines.append(f"secflow_workflow_executions_total {global_metrics['workflow_executions']}")
        
        lines.append(f"# HELP secflow_findings_generated_total Total findings generated")
        lines.append(f"# TYPE secflow_findings_generated_total counter")
        lines.append(f"secflow_findings_generated_total {global_metrics['findings_generated']}")
        
        return '\n'.join(lines)


# Global metrics collector instance
metrics = MetricsCollector()


def init_metrics() -> MetricsCollector:
    """
    Initialize metrics collection system.
    
    Returns:
        Configured MetricsCollector instance
    """
    logger.info("Initializing SecFlow metrics collection")
    return metrics


def get_metrics() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return metrics
