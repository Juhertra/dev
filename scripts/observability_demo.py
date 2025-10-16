#!/usr/bin/env python3
"""
SecFlow Observability Demo

This script demonstrates the complete observability implementation for M1,
including metrics collection, structured logging, and performance monitoring.

Usage:
    python scripts/observability_demo.py
"""

import time
import random
import sys
import os

# Add the packages directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from packages.runtime_core.observability.metrics import get_metrics
from packages.runtime_core.observability.logging import (
    get_logger, get_workflow_logger, set_log_context, clear_log_context
)
from packages.runtime_core.observability.integration import get_observability_hooks
from packages.runtime_core.observability.performance import get_performance_monitor


def simulate_plugin_execution(plugin_name: str, duration: float, success: bool = True) -> None:
    """Simulate plugin execution with observability."""
    hooks = get_observability_hooks()
    
    with hooks.node_execution_context(f"node_{plugin_name}", plugin_name, "demo_workflow", 1):
        # Simulate execution time
        time.sleep(duration)
        
        # Record success
        hooks.record_node_success(f"node_{plugin_name}", plugin_name, duration, 
                                 findings_count=random.randint(0, 5))
        
        if not success:
            raise Exception(f"Plugin {plugin_name} failed")


def simulate_workflow_execution() -> None:
    """Simulate complete workflow execution with observability."""
    hooks = get_observability_hooks()
    metrics = get_metrics()
    performance_monitor = get_performance_monitor()
    
    workflow_id = "demo_workflow"
    workflow_name = "Observability Demo Workflow"
    project_id = "demo_project"
    run_id = f"run_{int(time.time())}"
    
    with hooks.workflow_execution_context(workflow_id, workflow_name, project_id, run_id):
        # Simulate multiple plugin executions
        plugins = [
            ("nuclei", 2.5, True),
            ("feroxbuster", 1.8, True),
            ("gobuster", 3.2, True),
            ("slow_plugin", 15.0, True),  # This will trigger performance warning
            ("failing_plugin", 0.5, False)  # This will fail
        ]
        
        total_findings = 0
        
        for plugin_name, duration, success in plugins:
            try:
                simulate_plugin_execution(plugin_name, duration, success)
                total_findings += random.randint(1, 3)
                
                # Record system performance
                system_metrics = performance_monitor.record_system_performance()
                print(f"System metrics: {system_metrics}")
                
            except Exception as e:
                print(f"Plugin {plugin_name} failed: {e}")
                hooks.incr_plugin_error(plugin_name)
        
        # Record workflow success
        hooks.record_workflow_success(workflow_id, time.time(), total_findings)


def demonstrate_metrics_collection() -> None:
    """Demonstrate metrics collection capabilities."""
    print("\n=== Metrics Collection Demo ===")
    
    metrics = get_metrics()
    
    # Record some test metrics
    metrics.record_plugin_exec("test_plugin_1", 1.5, success=True)
    metrics.record_plugin_exec("test_plugin_2", 2.3, success=True)
    metrics.record_plugin_exec("test_plugin_3", 0.8, success=False)
    
    metrics.record_workflow_exec("test_workflow_1", 5.2, success=True, findings_count=3)
    metrics.record_workflow_exec("test_workflow_2", 8.1, success=True, findings_count=7)
    
    # Get metrics summary
    summary = metrics.get_summary()
    print("Metrics Summary:")
    print(f"  Plugin executions: {summary['global']['plugin_executions']}")
    print(f"  Plugin errors: {summary['global']['plugin_errors']}")
    print(f"  Workflow executions: {summary['global']['workflow_executions']}")
    print(f"  Findings generated: {summary['global']['findings_generated']}")
    
    # Export metrics in different formats
    print("\nPrometheus Export:")
    print(metrics.export_metrics('prometheus'))


def demonstrate_structured_logging() -> None:
    """Demonstrate structured logging capabilities."""
    print("\n=== Structured Logging Demo ===")
    
    logger = get_logger()
    workflow_logger = get_workflow_logger()
    
    # Set logging context
    set_log_context(
        workflow_id="demo_workflow",
        run_id="demo_run",
        project_id="demo_project",
        plugin_name="demo_plugin"
    )
    
    # Log various events
    logger.info("Starting observability demo", demo_mode=True)
    logger.warning("This is a warning message", warning_type="demo")
    logger.error("This is an error message", error_code="DEMO_ERROR")
    
    # Log workflow events
    workflow_logger.workflow_started("demo_workflow", "Demo Workflow", "demo_project", "demo_run")
    workflow_logger.node_started("demo_node", "demo_plugin", 1)
    workflow_logger.node_completed("demo_node", "demo_plugin", 1.5, success=True, findings_count=2)
    workflow_logger.workflow_completed("demo_workflow", 5.0, success=True, findings_count=2)
    
    # Clear context
    clear_log_context()


def demonstrate_performance_monitoring() -> None:
    """Demonstrate performance monitoring capabilities."""
    print("\n=== Performance Monitoring Demo ===")
    
    performance_monitor = get_performance_monitor()
    
    # Record some performance data
    performance_monitor.record_plugin_performance("fast_plugin", 0.5)
    performance_monitor.record_plugin_performance("slow_plugin", 15.0)  # Triggers warning
    performance_monitor.record_plugin_performance("very_slow_plugin", 65.0)  # Triggers error
    
    performance_monitor.record_workflow_performance("fast_workflow", 5.0)
    performance_monitor.record_workflow_performance("slow_workflow", 45.0)  # Triggers warning
    
    # Record system performance
    system_metrics = performance_monitor.record_system_performance()
    print(f"System performance: {system_metrics}")
    
    # Get performance summary
    summary = performance_monitor.get_performance_summary()
    print(f"\nPerformance Summary:")
    print(f"  Recent alerts: {len(summary['recent_alerts'])}")
    print(f"  Performance stats: {summary['performance_stats']}")


def main():
    """Main demo function."""
    print("SecFlow Observability Demo")
    print("=" * 50)
    
    # Initialize observability
    print("Initializing observability system...")
    
    # Demonstrate individual components
    demonstrate_metrics_collection()
    demonstrate_structured_logging()
    demonstrate_performance_monitoring()
    
    # Demonstrate integrated workflow execution
    print("\n=== Integrated Workflow Execution Demo ===")
    simulate_workflow_execution()
    
    # Final metrics summary
    print("\n=== Final Metrics Summary ===")
    metrics = get_metrics()
    summary = metrics.get_summary()
    
    print("Final Metrics:")
    print(f"  Total plugin executions: {summary['global']['plugin_executions']}")
    print(f"  Total plugin errors: {summary['global']['plugin_errors']}")
    print(f"  Total workflow executions: {summary['global']['workflow_executions']}")
    print(f"  Total findings generated: {summary['global']['findings_generated']}")
    print(f"  Throughput per minute: {summary['global']['throughput_per_minute']:.2f}")
    
    print("\nPerformance Statistics:")
    perf_stats = summary['performance']
    print(f"  Average plugin execution time: {perf_stats['plugin_exec_avg']:.2f}s")
    print(f"  P95 plugin execution time: {perf_stats['plugin_exec_p95']:.2f}s")
    print(f"  Average workflow execution time: {perf_stats['workflow_exec_avg']:.2f}s")
    print(f"  P95 workflow execution time: {perf_stats['workflow_exec_p95']:.2f}s")
    
    print("\nObservability demo completed successfully!")


if __name__ == "__main__":
    main()
