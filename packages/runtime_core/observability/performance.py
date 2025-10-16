"""
SecFlow Performance Monitoring

This module provides performance monitoring capabilities for workflow execution,
plugin performance, and system resource usage. Designed for M1 implementation
with M2+ scalability and automated alerting.

Key Features:
- Real-time performance monitoring
- Automated threshold detection and alerting
- Resource usage tracking
- Performance regression detection
- Integration with metrics collection
"""

import time
import threading
import psutil
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceThreshold:
    """Performance threshold configuration."""
    name: str
    component: str  # 'plugin', 'workflow', 'system'
    metric: str  # 'duration', 'memory', 'cpu'
    warning_value: float
    error_value: float
    enabled: bool = True


@dataclass
class PerformanceAlert:
    """Performance alert data."""
    timestamp: float
    threshold_name: str
    component: str
    metric: str
    current_value: float
    threshold_value: float
    severity: str  # 'warning', 'error'
    message: str


class PerformanceMonitor:
    """
    Performance monitoring system for SecFlow.
    
    Monitors workflow and plugin performance, detects threshold breaches,
    and generates alerts for performance issues.
    """
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize performance monitor.
        
        Args:
            max_history: Maximum number of historical values to keep
        """
        self._lock = threading.RLock()
        self._max_history = max_history
        
        # Performance thresholds
        self._thresholds: Dict[str, PerformanceThreshold] = {}
        
        # Alert history
        self._alerts: deque = deque(maxlen=max_history)
        
        # Performance history
        self._performance_history: Dict[str, deque] = {
            'plugin_durations': deque(maxlen=max_history),
            'workflow_durations': deque(maxlen=max_history),
            'memory_usage': deque(maxlen=max_history),
            'cpu_usage': deque(maxlen=max_history)
        }
        
        # Alert callbacks
        self._alert_callbacks: List[Callable[[PerformanceAlert], None]] = []
        
        # Initialize default thresholds
        self._setup_default_thresholds()
    
    def _setup_default_thresholds(self) -> None:
        """Set up default performance thresholds."""
        default_thresholds = [
            PerformanceThreshold(
                name="plugin_warning_duration",
                component="plugin",
                metric="duration",
                warning_value=10.0,
                error_value=60.0
            ),
            PerformanceThreshold(
                name="workflow_warning_duration",
                component="workflow",
                metric="duration",
                warning_value=30.0,
                error_value=120.0
            ),
            PerformanceThreshold(
                name="memory_warning_usage",
                component="system",
                metric="memory",
                warning_value=512.0,  # MB
                error_value=1024.0    # MB
            ),
            PerformanceThreshold(
                name="cpu_warning_usage",
                component="system",
                metric="cpu",
                warning_value=80.0,   # %
                error_value=95.0      # %
            )
        ]
        
        for threshold in default_thresholds:
            self._thresholds[threshold.name] = threshold
    
    def add_threshold(self, threshold: PerformanceThreshold) -> None:
        """
        Add a performance threshold.
        
        Args:
            threshold: Performance threshold configuration
        """
        with self._lock:
            self._thresholds[threshold.name] = threshold
    
    def remove_threshold(self, name: str) -> None:
        """
        Remove a performance threshold.
        
        Args:
            name: Threshold name
        """
        with self._lock:
            self._thresholds.pop(name, None)
    
    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]) -> None:
        """
        Add an alert callback function.
        
        Args:
            callback: Function to call when alerts are generated
        """
        with self._lock:
            self._alert_callbacks.append(callback)
    
    def record_plugin_performance(self, plugin_name: str, duration: float) -> None:
        """
        Record plugin performance metrics.
        
        Args:
            plugin_name: Name of the plugin
            duration: Execution duration in seconds
        """
        with self._lock:
            # Store performance data
            self._performance_history['plugin_durations'].append({
                'timestamp': time.time(),
                'plugin_name': plugin_name,
                'duration': duration
            })
            
            # Check thresholds
            self._check_thresholds('plugin', 'duration', duration, plugin_name)
    
    def record_workflow_performance(self, workflow_id: str, duration: float) -> None:
        """
        Record workflow performance metrics.
        
        Args:
            workflow_id: Workflow identifier
            duration: Execution duration in seconds
        """
        with self._lock:
            # Store performance data
            self._performance_history['workflow_durations'].append({
                'timestamp': time.time(),
                'workflow_id': workflow_id,
                'duration': duration
            })
            
            # Check thresholds
            self._check_thresholds('workflow', 'duration', duration, workflow_id)
    
    def record_system_performance(self) -> Dict[str, float]:
        """
        Record current system performance metrics.
        
        Returns:
            Dictionary of system metrics
        """
        try:
            # Get system metrics
            memory_info = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            metrics = {
                'memory_usage_mb': memory_info.used / (1024 * 1024),
                'memory_percent': memory_info.percent,
                'cpu_percent': cpu_percent
            }
            
            with self._lock:
                # Store performance data
                self._performance_history['memory_usage'].append({
                    'timestamp': time.time(),
                    'memory_mb': metrics['memory_usage_mb'],
                    'memory_percent': metrics['memory_percent']
                })
                
                self._performance_history['cpu_usage'].append({
                    'timestamp': time.time(),
                    'cpu_percent': cpu_percent
                })
                
                # Check thresholds
                self._check_thresholds('system', 'memory', metrics['memory_usage_mb'])
                self._check_thresholds('system', 'cpu', metrics['cpu_percent'])
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to record system performance: {e}")
            return {}
    
    def _check_thresholds(self, component: str, metric: str, value: float, 
                         context: str = "") -> None:
        """
        Check performance thresholds and generate alerts.
        
        Args:
            component: Component type (plugin, workflow, system)
            metric: Metric type (duration, memory, cpu)
            value: Current metric value
            context: Additional context (plugin name, workflow ID, etc.)
        """
        for threshold_name, threshold in self._thresholds.items():
            if (threshold.component == component and 
                threshold.metric == metric and 
                threshold.enabled):
                
                severity = None
                threshold_value = None
                
                if value >= threshold.error_value:
                    severity = "error"
                    threshold_value = threshold.error_value
                elif value >= threshold.warning_value:
                    severity = "warning"
                    threshold_value = threshold.warning_value
                
                if severity:
                    alert = PerformanceAlert(
                        timestamp=time.time(),
                        threshold_name=threshold_name,
                        component=component,
                        metric=metric,
                        current_value=value,
                        threshold_value=threshold_value,
                        severity=severity,
                        message=f"{component} {metric} threshold exceeded: {value:.2f} >= {threshold_value:.2f} ({context})"
                    )
                    
                    self._generate_alert(alert)
    
    def _generate_alert(self, alert: PerformanceAlert) -> None:
        """
        Generate a performance alert.
        
        Args:
            alert: Performance alert data
        """
        with self._lock:
            # Store alert
            self._alerts.append(alert)
            
            # Log alert
            if alert.severity == "error":
                logger.error(alert.message)
            else:
                logger.warning(alert.message)
            
            # Call alert callbacks
            for callback in self._alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance monitoring summary.
        
        Returns:
            Dictionary containing performance metrics and alerts
        """
        with self._lock:
            summary = {
                'thresholds': {
                    name: {
                        'component': t.component,
                        'metric': t.metric,
                        'warning_value': t.warning_value,
                        'error_value': t.error_value,
                        'enabled': t.enabled
                    }
                    for name, t in self._thresholds.items()
                },
                'recent_alerts': [
                    {
                        'timestamp': alert.timestamp,
                        'threshold_name': alert.threshold_name,
                        'component': alert.component,
                        'metric': alert.metric,
                        'current_value': alert.current_value,
                        'threshold_value': alert.threshold_value,
                        'severity': alert.severity,
                        'message': alert.message
                    }
                    for alert in list(self._alerts)[-10:]  # Last 10 alerts
                ],
                'performance_stats': self._calculate_performance_stats()
            }
            
            return summary
    
    def _calculate_performance_stats(self) -> Dict[str, Any]:
        """Calculate performance statistics."""
        stats = {}
        
        # Plugin duration stats
        plugin_durations = [d['duration'] for d in self._performance_history['plugin_durations']]
        if plugin_durations:
            stats['plugin_durations'] = {
                'count': len(plugin_durations),
                'avg': sum(plugin_durations) / len(plugin_durations),
                'min': min(plugin_durations),
                'max': max(plugin_durations)
            }
        
        # Workflow duration stats
        workflow_durations = [d['duration'] for d in self._performance_history['workflow_durations']]
        if workflow_durations:
            stats['workflow_durations'] = {
                'count': len(workflow_durations),
                'avg': sum(workflow_durations) / len(workflow_durations),
                'min': min(workflow_durations),
                'max': max(workflow_durations)
            }
        
        # System stats
        memory_usage = [d['memory_mb'] for d in self._performance_history['memory_usage']]
        if memory_usage:
            stats['memory_usage'] = {
                'count': len(memory_usage),
                'avg': sum(memory_usage) / len(memory_usage),
                'min': min(memory_usage),
                'max': max(memory_usage)
            }
        
        cpu_usage = [d['cpu_percent'] for d in self._performance_history['cpu_usage']]
        if cpu_usage:
            stats['cpu_usage'] = {
                'count': len(cpu_usage),
                'avg': sum(cpu_usage) / len(cpu_usage),
                'min': min(cpu_usage),
                'max': max(cpu_usage)
            }
        
        return stats
    
    def clear_history(self) -> None:
        """Clear performance history (useful for testing)."""
        with self._lock:
            for history in self._performance_history.values():
                history.clear()
            self._alerts.clear()


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    return performance_monitor


def init_performance_monitoring() -> PerformanceMonitor:
    """
    Initialize performance monitoring system.
    
    Returns:
        Configured PerformanceMonitor instance
    """
    logger.info("Initializing SecFlow performance monitoring")
    return performance_monitor
