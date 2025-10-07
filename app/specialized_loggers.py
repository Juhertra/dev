"""
Specialized loggers for Phase 3 structured logging.
Provides structured logging for cache, runs, SSE operations.
"""

import logging
from typing import Any, Dict, Optional

# Create specialized loggers
cache_logger = logging.getLogger('cache')
runs_logger = logging.getLogger('runs')
sse_logger = logging.getLogger('sse')

def setup_specialized_loggers():
    """Initialize specialized loggers with proper formatting."""
    # Ensure the parent logging configuration is already set up
    loggers = [cache_logger, runs_logger, sse_logger]
    
    for logger in loggers:
        if not logger.handlers:
            # Use the existing JSON formatter from the parent
            logger.setLevel(logging.INFO)
            logger.propagate = True  # Use parent handlers

def log_cache_hit(key: str, keyspace: str):
    """Log cache hit with structured format."""
    cache_logger.info(
        f"CACHE HIT key={key}",
        extra={
            "operation": "cache_hit",
            "cache_key": key,
            "keyspace": keyspace
        }
    )

def log_cache_miss(key: str, keyspace: str):
    """Log cache miss with structured format.""" 
    cache_logger.info(
        f"CACHE MISS key={key}",
        extra={
            "operation": "cache_miss", 
            "cache_key": key,
            "keyspace": keyspace
        }
    )

def log_runs_index(pid: str, count: int):
    """Log runs index access with structured format."""
    runs_logger.info(
        f'RUNS_INDEX pid="{pid}" count={count}',
        extra={
            "operation": "runs_index",
            "project_id": pid,
            "run_count": count
        }
    )

def log_sse_operation(operation: str, run_id: str, endpoints: Optional[int] = None, additional_data: Optional[Dict[str, Any]] = None):
    """
    Log SSE operations with structured format.
    
    Args:
        operation: Type of SSE operation (start, heartbeat, done, error)
        run_id: Unique run identifier
        endpoints: Number of endpoints being processed (optional)
        additional_data: Additional structured data (optional)
    """
    message = f"SSE {operation} run_id={run_id}"
    if endpoints is not None:
        message += f" endpoints={endpoints}"
    
    extra = {
        "operation": "sse",
        "sse_operation": operation,
        "run_id": run_id
    }
    
    if endpoints is not None:
        extra["endpoints"] = endpoints
    
    if additional_data:
        extra.update(additional_data)
    
    sse_logger.info(message, extra=extra)

def log_scan_completion(run_id: str, endpoint_count: int, finding_count: int, duration_ms: int):
    """Log scan completion with performance metrics."""
    sse_logger.info(
        f"SCAN_COMPLETE run_id={run_id} endpoints={endpoint_count} findings={finding_count} duration_ms={duration_ms}",
        extra={
            "operation": "scan_complete",
            "run_id": run_id,
            "endpoint_count": endpoint_count,
            "finding_count": finding_count,
            "duration_ms": duration_ms
        }
    )

def log_custom_operation(logger_name: str, message: str, extra: Optional[Dict[str, Any]] = None):
    """
    Log custom structured message to specified logger.
    
    Args:
        logger_name: Name of logger to use
        message: Log message
        extra: Additional structured data
    """
    logger = logging.getLogger(logger_name)
    logger.info(message, extra=extra or {})

# Initialize loggers when module is imported
setup_specialized_loggers()

__all__ = [
    'cache_logger',
    'runs_logger', 
    'sse_logger',
    'setup_specialized_loggers',
    'log_cache_hit',
    'log_cache_miss',
    'log_runs_index',
    'log_sse_operation',
    'log_scan_completion',
    'log_custom_operation'
]
