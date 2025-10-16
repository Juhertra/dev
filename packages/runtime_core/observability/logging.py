"""
SecFlow Observability Structured Logging

This module provides structured logging capabilities for workflow execution,
plugin operations, and system events. Designed for M1 implementation with
M2+ scalability and OpenTelemetry integration.

Key Features:
- JSON structured logging with context correlation
- Workflow and plugin execution tracking
- Performance monitoring integration
- Thread-safe logging operations
- Python 3.14 compatibility with no-GIL mode
"""

import logging
import json
import time
import threading
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import sys
import os

# Add trace context support (placeholder for M2+ OpenTelemetry integration)
_trace_context = threading.local()


@dataclass
class LogContext:
    """Container for structured log context."""
    workflow_id: Optional[str] = None
    run_id: Optional[str] = None
    project_id: Optional[str] = None
    plugin_name: Optional[str] = None
    node_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    
    Converts log records to JSON format with context correlation.
    """
    
    def __init__(self, include_trace: bool = True):
        """
        Initialize JSON formatter.
        
        Args:
            include_trace: Whether to include trace context in logs
        """
        super().__init__()
        self.include_trace = include_trace
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON formatted log string
        """
        # Base log data
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "process": record.process
        }
        
        # Add trace context if available
        if self.include_trace and hasattr(_trace_context, 'context'):
            context = _trace_context.context
            if context.workflow_id:
                log_data["workflow_id"] = context.workflow_id
            if context.run_id:
                log_data["run_id"] = context.run_id
            if context.project_id:
                log_data["project_id"] = context.project_id
            if context.plugin_name:
                log_data["plugin_name"] = context.plugin_name
            if context.node_id:
                log_data["node_id"] = context.node_id
            if context.trace_id:
                log_data["trace_id"] = context.trace_id
            if context.span_id:
                log_data["span_id"] = context.span_id
            if context.user_id:
                log_data["user_id"] = context.user_id
            if context.session_id:
                log_data["session_id"] = context.session_id
        
        # Add extra fields from log call
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None
            }
        
        return json.dumps(log_data, ensure_ascii=False)


class StructuredLogger:
    """
    Structured logger with context management.
    
    Provides thread-safe structured logging with context correlation.
    """
    
    def __init__(self, name: str = "secflow"):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name)
        self._lock = threading.RLock()
        
        # Set up JSON formatting
        self._setup_formatter()
    
    def _setup_formatter(self) -> None:
        """Set up JSON formatter for the logger."""
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Add console handler with JSON formatter
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(JsonFormatter())
        self.logger.addHandler(console_handler)
        
        # Set log level
        self.logger.setLevel(logging.INFO)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    def set_context(self, context: LogContext) -> None:
        """
        Set trace context for current thread.
        
        Args:
            context: Log context to set
        """
        with self._lock:
            _trace_context.context = context
    
    def clear_context(self) -> None:
        """Clear trace context for current thread."""
        with self._lock:
            if hasattr(_trace_context, 'context'):
                delattr(_trace_context, 'context')
    
    def _log_with_context(self, level: int, message: str, 
                         extra_fields: Optional[Dict[str, Any]] = None,
                         exc_info: Optional[Any] = None) -> None:
        """
        Log message with context and extra fields.
        
        Args:
            level: Log level
            message: Log message
            extra_fields: Additional fields to include
            exc_info: Exception info
        """
        with self._lock:
            # Create log record with extra fields
            record = self.logger.makeRecord(
                self.logger.name, level, "", 0, message, (), exc_info
            )
            
            if extra_fields:
                record.extra_fields = extra_fields
            
            self.logger.handle(record)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message with context."""
        self._log_with_context(logging.INFO, message, kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with context."""
        self._log_with_context(logging.WARNING, message, kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message with context."""
        self._log_with_context(logging.ERROR, message, kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with context."""
        self._log_with_context(logging.CRITICAL, message, kwargs)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with context."""
        self._log_with_context(logging.DEBUG, message, kwargs)
    
    def exception(self, message: str, **kwargs) -> None:
        """Log exception with traceback."""
        self._log_with_context(logging.ERROR, message, kwargs, exc_info=True)


class WorkflowLogger:
    """
    Specialized logger for workflow execution events.
    
    Provides structured logging for workflow lifecycle events.
    """
    
    def __init__(self, structured_logger: StructuredLogger):
        """
        Initialize workflow logger.
        
        Args:
            structured_logger: Base structured logger
        """
        self.logger = structured_logger
    
    def workflow_started(self, workflow_id: str, workflow_name: str, 
                        project_id: str, run_id: str) -> None:
        """Log workflow start event."""
        self.logger.info(
            "Workflow execution started",
            event_type="workflow_started",
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            project_id=project_id,
            run_id=run_id,
            timestamp=time.time()
        )
    
    def workflow_completed(self, workflow_id: str, duration: float, 
                          success: bool, findings_count: int) -> None:
        """Log workflow completion event."""
        self.logger.info(
            "Workflow execution completed",
            event_type="workflow_completed",
            workflow_id=workflow_id,
            duration_seconds=duration,
            success=success,
            findings_count=findings_count,
            timestamp=time.time()
        )
    
    def workflow_failed(self, workflow_id: str, error: str, duration: float) -> None:
        """Log workflow failure event."""
        self.logger.error(
            "Workflow execution failed",
            event_type="workflow_failed",
            workflow_id=workflow_id,
            error=error,
            duration_seconds=duration,
            timestamp=time.time()
        )
    
    def node_started(self, node_id: str, plugin_name: str, attempt: int = 1) -> None:
        """Log node execution start event."""
        self.logger.info(
            "Node execution started",
            event_type="node_started",
            node_id=node_id,
            plugin_name=plugin_name,
            attempt=attempt,
            timestamp=time.time()
        )
    
    def node_completed(self, node_id: str, plugin_name: str, duration: float, 
                      success: bool, findings_count: int = 0) -> None:
        """Log node execution completion event."""
        self.logger.info(
            "Node execution completed",
            event_type="node_completed",
            node_id=node_id,
            plugin_name=plugin_name,
            duration_seconds=duration,
            success=success,
            findings_count=findings_count,
            timestamp=time.time()
        )
    
    def node_failed(self, node_id: str, plugin_name: str, error: str, 
                   duration: float, attempt: int) -> None:
        """Log node execution failure event."""
        self.logger.error(
            "Node execution failed",
            event_type="node_failed",
            node_id=node_id,
            plugin_name=plugin_name,
            error=error,
            duration_seconds=duration,
            attempt=attempt,
            timestamp=time.time()
        )
    
    def plugin_output(self, plugin_name: str, output: str, 
                     output_type: str = "stdout") -> None:
        """Log plugin output."""
        self.logger.info(
            "Plugin output captured",
            event_type="plugin_output",
            plugin_name=plugin_name,
            output_type=output_type,
            output_length=len(output),
            timestamp=time.time()
        )
    
    def performance_warning(self, component: str, duration: float, 
                           threshold: float) -> None:
        """Log performance warning."""
        self.logger.warning(
            "Performance threshold exceeded",
            event_type="performance_warning",
            component=component,
            duration_seconds=duration,
            threshold_seconds=threshold,
            timestamp=time.time()
        )


# Global logger instances
_structured_logger = StructuredLogger("secflow")
_workflow_logger = WorkflowLogger(_structured_logger)


def init_logging() -> StructuredLogger:
    """
    Initialize structured logging system.
    
    Returns:
        Configured StructuredLogger instance
    """
    logger = logging.getLogger(__name__)
    logger.info("Initializing SecFlow structured logging")
    return _structured_logger


def get_logger() -> StructuredLogger:
    """Get the global structured logger instance."""
    return _structured_logger


def get_workflow_logger() -> WorkflowLogger:
    """Get the global workflow logger instance."""
    return _workflow_logger


def set_log_context(workflow_id: Optional[str] = None,
                   run_id: Optional[str] = None,
                   project_id: Optional[str] = None,
                   plugin_name: Optional[str] = None,
                   node_id: Optional[str] = None,
                   trace_id: Optional[str] = None,
                   span_id: Optional[str] = None,
                   user_id: Optional[str] = None,
                   session_id: Optional[str] = None) -> None:
    """
    Set logging context for current thread.
    
    Args:
        workflow_id: Workflow identifier
        run_id: Run identifier
        project_id: Project identifier
        plugin_name: Plugin name
        node_id: Node identifier
        trace_id: Trace identifier (for M2+ OpenTelemetry)
        span_id: Span identifier (for M2+ OpenTelemetry)
        user_id: User identifier
        session_id: Session identifier
    """
    context = LogContext(
        workflow_id=workflow_id,
        run_id=run_id,
        project_id=project_id,
        plugin_name=plugin_name,
        node_id=node_id,
        trace_id=trace_id,
        span_id=span_id,
        user_id=user_id,
        session_id=session_id
    )
    _structured_logger.set_context(context)


def clear_log_context() -> None:
    """Clear logging context for current thread."""
    _structured_logger.clear_context()
