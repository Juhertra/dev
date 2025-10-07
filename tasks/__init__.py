"""
Task runner interface for Phase 3 observability.
Provides abstraction for nuclei invocation that can be swapped for async queues later.
"""

from typing import Dict, Any, Optional, Callable


class ScanPlan:
    """Represents a scan execution plan."""
    def __init__(self, 
                 run_id: str,
                 severity_levels: list[str],
                 templates: list[str],
                 endpoints: list[str],
                 project_id: str):
        self.run_id = run_id
        self.severity_levels = severity_levels
        self.templates = templates
        self.endpoints = endpoints
        self.project_id = project_id

class ScanResult:
    """Represents the result of a scan execution."""
    def __init__(self, 
                 run_id: str,
                 success: bool,
                 endpoint_count: int = 0,
                 finding_count: int = 0,
                 duration_ms: int = 0,
                 error: Optional[str] = None):
        self.run_id = run_id
        self.success = success
        self.endpoint_count = endpoint_count
        self.finding_count = finding_count
        self.duration_ms = duration_ms
        self.error = error

def submit_scan(plan: ScanPlan) -> ScanResult:
    """
    Submit a scan task for execution.
    
    Phase 3: Synchronous execution, will be replaced with async task queue later.
    
    Args:
        plan: ScanPlan describing the scan to execute
        
    Returns:
        ScanResult with execution details
    """
    import time
    import logging
    from .nuclei import execute_nuclei_pipeline
    
    logger = logging.getLogger('tasks')
    start_time = time.time()
    
    try:
        logger.info(f"Starting scan execution run_id={plan.run_id} endpoints={len(plan.endpoints)} templates={len(plan.templates)}")
        
        # Execute nuclei pipeline synchronously for now
        result = execute_nuclei_pipeline(
            run_id=plan.run_id,
            severity_levels=plan.severity_levels,
            templates=plan.templates,
            endpoints=plan.endpoints,
            project_id=plan.project_id
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return ScanResult(
            run_id=plan.run_id,
            success=True,
            endpoint_count=len(plan.endpoints),
            finding_count=result.get('findings_count', 0),
            duration_ms=duration_ms
        )
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Scan execution failed run_id={plan.run_id} duration_ms={duration_ms} error=\"{str(e)}\"")
        
        return ScanResult(
            run_id=plan.run_id,
            success=False,
            duration_ms=duration_ms,
            error=str(e)
        )

def run_sync(fn: Callable, *args, **kwargs):
    """Execute task synchronously (placeholder for future async queues)."""
    return fn(*args, **kwargs)

# Export interfaces
__all__ = ["submit_scan", "ScanPlan", "ScanResult", "run_sync"]


