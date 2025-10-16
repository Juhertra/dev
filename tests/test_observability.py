"""
SecFlow Observability Tests

Test suite for observability metrics collection and structured logging.
Tests thread safety, performance monitoring, and integration hooks.
"""

import pytest
import time
import threading
import json
from unittest.mock import patch, MagicMock
from io import StringIO
import sys
import os

# Add the packages directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from packages.runtime_core.observability.metrics import MetricsCollector, ExecutionMetrics
from packages.runtime_core.observability.logging import (
    StructuredLogger, WorkflowLogger, JsonFormatter, LogContext
)
from packages.runtime_core.observability.integration import ObservabilityHooks


class TestMetricsCollector:
    """Test suite for MetricsCollector."""
    
    def test_metrics_collector_initialization(self):
        """Test MetricsCollector initialization."""
        mc = MetricsCollector()
        assert isinstance(mc.metrics, ExecutionMetrics)
        assert mc.metrics.plugin_errors == 0
        assert mc.metrics.workflow_errors == 0
        assert mc.metrics.findings_generated == 0
    
    def test_record_plugin_exec(self):
        """Test plugin execution recording."""
        mc = MetricsCollector()
        
        # Record successful execution
        mc.record_plugin_exec("test_plugin", 1.5, success=True)
        assert len(mc.metrics.plugin_exec_seconds) == 1
        assert mc.metrics.plugin_exec_seconds[0] == 1.5
        assert mc.metrics.plugin_errors == 0
        
        # Record failed execution
        mc.record_plugin_exec("test_plugin", 2.0, success=False)
        assert len(mc.metrics.plugin_exec_seconds) == 2
        assert mc.metrics.plugin_errors == 1
        
        # Check plugin-specific metrics
        plugin_metrics = mc._plugin_metrics["test_plugin"]
        assert plugin_metrics['executions'] == 2
        assert plugin_metrics['errors'] == 1
        assert plugin_metrics['total_time'] == 3.5
        assert plugin_metrics['min_time'] == 1.5
        assert plugin_metrics['max_time'] == 2.0
    
    def test_record_workflow_exec(self):
        """Test workflow execution recording."""
        mc = MetricsCollector()
        
        # Record successful workflow
        mc.record_workflow_exec("test_workflow", 10.0, success=True, findings_count=5)
        assert len(mc.metrics.workflow_exec_seconds) == 1
        assert mc.metrics.workflow_exec_seconds[0] == 10.0
        assert mc.metrics.workflow_errors == 0
        assert mc.metrics.findings_generated == 5
        
        # Check workflow-specific metrics
        workflow_metrics = mc._workflow_metrics["test_workflow"]
        assert workflow_metrics['executions'] == 1
        assert workflow_metrics['errors'] == 0
        assert workflow_metrics['total_time'] == 10.0
        assert workflow_metrics['findings'] == 5
    
    def test_get_summary(self):
        """Test metrics summary generation."""
        mc = MetricsCollector()
        
        # Add some test data
        mc.record_plugin_exec("plugin1", 1.0, success=True)
        mc.record_plugin_exec("plugin2", 2.0, success=False)
        mc.record_workflow_exec("workflow1", 5.0, success=True, findings_count=3)
        
        summary = mc.get_summary()
        
        assert summary['global']['plugin_executions'] == 2
        assert summary['global']['plugin_errors'] == 1
        assert summary['global']['workflow_executions'] == 1
        assert summary['global']['findings_generated'] == 3
        
        assert 'performance' in summary
        assert 'plugins' in summary
        assert 'workflows' in summary
        assert 'thresholds' in summary
    
    def test_reset_metrics(self):
        """Test metrics reset functionality."""
        mc = MetricsCollector()
        
        # Add some data
        mc.record_plugin_exec("test_plugin", 1.0, success=True)
        mc.record_workflow_exec("test_workflow", 5.0, success=True)
        
        # Reset metrics
        mc.reset_metrics()
        
        assert len(mc.metrics.plugin_exec_seconds) == 0
        assert len(mc.metrics.workflow_exec_seconds) == 0
        assert mc.metrics.plugin_errors == 0
        assert mc.metrics.workflow_errors == 0
        assert len(mc._plugin_metrics) == 0
        assert len(mc._workflow_metrics) == 0
    
    def test_thread_safety(self):
        """Test thread safety of metrics collection."""
        mc = MetricsCollector()
        results = []
        
        def record_metrics(plugin_name: str, duration: float):
            mc.record_plugin_exec(plugin_name, duration, success=True)
            results.append(f"{plugin_name}:{duration}")
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(
                target=record_metrics, 
                args=(f"plugin_{i}", float(i))
            )
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(mc.metrics.plugin_exec_seconds) == 10
        assert len(results) == 10
        assert mc.metrics.plugin_errors == 0


class TestStructuredLogger:
    """Test suite for StructuredLogger."""
    
    def test_json_formatter(self):
        """Test JSON formatter."""
        formatter = JsonFormatter()
        record = MagicMock()
        
        # Mock log record
        record.created = time.time()
        record.levelname = "INFO"
        record.name = "test_logger"
        record.getMessage.return_value = "Test message"
        record.module = "test_module"
        record.funcName = "test_function"
        record.lineno = 42
        record.thread = 12345
        record.process = 67890
        record.exc_info = None
        
        # Format the record
        formatted = formatter.format(record)
        
        # Parse JSON
        log_data = json.loads(formatted)
        
        assert log_data['level'] == "INFO"
        assert log_data['message'] == "Test message"
        assert log_data['module'] == "test_module"
        assert log_data['function'] == "test_function"
        assert log_data['line'] == 42
    
    def test_structured_logger(self):
        """Test StructuredLogger functionality."""
        # Capture output
        output = StringIO()
        
        with patch('sys.stdout', output):
            logger = StructuredLogger("test_logger")
            
            # Set context
            context = LogContext(
                workflow_id="test_workflow",
                run_id="test_run",
                plugin_name="test_plugin"
            )
            logger.set_context(context)
            
            # Log a message
            logger.info("Test message", extra_field="extra_value")
            
            # Get output
            log_output = output.getvalue()
            
            # Parse JSON
            log_data = json.loads(log_output.strip())
            
            assert log_data['message'] == "Test message"
            assert log_data['workflow_id'] == "test_workflow"
            assert log_data['run_id'] == "test_run"
            assert log_data['plugin_name'] == "test_plugin"
            assert log_data['extra_field'] == "extra_value"
    
    def test_workflow_logger(self):
        """Test WorkflowLogger functionality."""
        output = StringIO()
        
        with patch('sys.stdout', output):
            structured_logger = StructuredLogger("test_logger")
            workflow_logger = WorkflowLogger(structured_logger)
            
            # Log workflow events
            workflow_logger.workflow_started(
                "workflow_1", "Test Workflow", "project_1", "run_1"
            )
            
            workflow_logger.node_started("node_1", "plugin_1", 1)
            
            workflow_logger.node_completed(
                "node_1", "plugin_1", 1.5, success=True, findings_count=2
            )
            
            workflow_logger.workflow_completed(
                "workflow_1", 5.0, success=True, findings_count=2
            )
            
            # Get output
            log_output = output.getvalue()
            log_lines = log_output.strip().split('\n')
            
            # Verify all events were logged
            assert len(log_lines) == 4
            
            # Parse first log entry
            log_data = json.loads(log_lines[0])
            assert log_data['event_type'] == "workflow_started"
            assert log_data['workflow_id'] == "workflow_1"
            assert log_data['workflow_name'] == "Test Workflow"


class TestObservabilityHooks:
    """Test suite for ObservabilityHooks."""
    
    def test_workflow_execution_context(self):
        """Test workflow execution context manager."""
        hooks = ObservabilityHooks()
        output = StringIO()
        
        with patch('sys.stdout', output):
            with hooks.workflow_execution_context(
                "workflow_1", "Test Workflow", "project_1", "run_1"
            ):
                # Simulate workflow execution
                time.sleep(0.01)
            
            # Get output
            log_output = output.getvalue()
            log_lines = log_output.strip().split('\n')
            
            # Should have workflow started and completed logs
            assert len(log_lines) >= 2
            
            # Parse logs
            start_log = json.loads(log_lines[0])
            complete_log = json.loads(log_lines[-1])
            
            assert start_log['event_type'] == "workflow_started"
            assert complete_log['event_type'] == "workflow_completed"
            assert complete_log['success'] == True
    
    def test_node_execution_context(self):
        """Test node execution context manager."""
        hooks = ObservabilityHooks()
        output = StringIO()
        
        with patch('sys.stdout', output):
            with hooks.node_execution_context(
                "node_1", "plugin_1", "workflow_1", 1
            ):
                # Simulate node execution
                time.sleep(0.01)
            
            # Get output
            log_output = output.getvalue()
            log_lines = log_output.strip().split('\n')
            
            # Should have node started and completed logs
            assert len(log_lines) >= 2
            
            # Parse logs
            start_log = json.loads(log_lines[0])
            complete_log = json.loads(log_lines[-1])
            
            assert start_log['event_type'] == "node_started"
            assert complete_log['event_type'] == "node_completed"
            assert complete_log['success'] == True
    
    def test_error_handling(self):
        """Test error handling in context managers."""
        hooks = ObservabilityHooks()
        output = StringIO()
        
        with patch('sys.stdout', output):
            try:
                with hooks.workflow_execution_context(
                    "workflow_1", "Test Workflow", "project_1", "run_1"
                ):
                    raise ValueError("Test error")
            except ValueError:
                pass
            
            # Get output
            log_output = output.getvalue()
            log_lines = log_output.strip().split('\n')
            
            # Should have workflow started and failed logs
            assert len(log_lines) >= 2
            
            # Parse logs
            start_log = json.loads(log_lines[0])
            failed_log = json.loads(log_lines[-1])
            
            assert start_log['event_type'] == "workflow_started"
            assert failed_log['event_type'] == "workflow_failed"
            assert failed_log['error'] == "Test error"


class TestPerformanceMonitoring:
    """Test suite for performance monitoring."""
    
    def test_performance_thresholds(self):
        """Test performance threshold checking."""
        hooks = ObservabilityHooks()
        output = StringIO()
        
        with patch('sys.stdout', output):
            # Test plugin performance warning
            hooks.check_performance_thresholds("plugin", 15.0)
            
            # Test workflow performance warning
            hooks.check_performance_thresholds("workflow", 45.0)
            
            # Get output
            log_output = output.getvalue()
            log_lines = log_output.strip().split('\n')
            
            # Should have performance warnings
            assert len(log_lines) >= 2
            
            # Parse logs
            plugin_warning = json.loads(log_lines[0])
            workflow_warning = json.loads(log_lines[1])
            
            assert plugin_warning['event_type'] == "performance_warning"
            assert plugin_warning['component'] == "plugin"
            assert plugin_warning['duration_seconds'] == 15.0
            
            assert workflow_warning['event_type'] == "performance_warning"
            assert workflow_warning['component'] == "workflow"
            assert workflow_warning['duration_seconds'] == 45.0


def test_integration_workflow():
    """Integration test for complete workflow observability."""
    hooks = ObservabilityHooks()
    output = StringIO()
    
    with patch('sys.stdout', output):
        # Simulate complete workflow execution
        with hooks.workflow_execution_context(
            "integration_workflow", "Integration Test", "test_project", "test_run"
        ):
            # Simulate multiple nodes
            for i in range(3):
                with hooks.node_execution_context(
                    f"node_{i}", f"plugin_{i}", "integration_workflow", 1
                ):
                    time.sleep(0.01)
                
                hooks.record_node_success(f"node_{i}", f"plugin_{i}", 0.01, 1)
            
            hooks.record_workflow_success("integration_workflow", 0.03, 3)
        
        # Get output
        log_output = output.getvalue()
        log_lines = log_output.strip().split('\n')
        
        # Should have workflow start, 3 node pairs, and workflow complete
        assert len(log_lines) >= 8
        
        # Verify metrics
        summary = hooks.metrics.get_summary()
        assert summary['global']['plugin_executions'] == 3
        assert summary['global']['workflow_executions'] == 1
        assert summary['global']['findings_generated'] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
