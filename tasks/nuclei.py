"""Nuclei task wrappers (sync for Phase 1)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def scan_project_endpoints(pid: str, templates: Optional[List[str]] = None, severity: Optional[List[str]] = None, exclude_patterns: Optional[List[str]] = None, run_id: Optional[str] = None) -> Dict[str, Any]:
    """Pass-through to existing nuclei_integration. Synchronous in Phase 1.
    
    Args:
        pid: Project ID
        templates: List of template names to run
        severity: List of severity levels to include
        exclude_patterns: List of patterns to exclude
        run_id: Unique run identifier
        
    Returns:
        Dict with scan results and metadata
    """
    from nuclei_integration import nuclei_integration
    
    logger = logging.getLogger('tasks.nuclei')
    logger.info(f"Executing nuclei scan run_id={run_id} project={pid} templates={len(templates or [])} severity={speverity}")
    
    result = nuclei_integration.scan_project_endpoints(
        pid=pid,
        templates=templates,
        severity=severity,
        exclude_patterns=exclude_patterns,
        run_id=run_id,
    )
    
    logger.info(f"Nuclei scan completed run_id={run_id} findings={result.get('findings_count', 0)}")
    return result


def execute_nuclei_pipeline(run_id: str,
                           severity_levels: List[str],
                           templates: List[str], 
                           endpoints: List[str],
                           project_id: str) -> Dict[str, Any]:
    """
    Execute nuclei scan pipeline with standardized parameters.
    
    Phase 3: Task runner seam implementation.
    
    Args:
        run_id: Unique identifier for this run
        severity_levels: List of severity levels (critical, high, medium, low, info)
        templates: List of template names/tags to execute
        endpoints: List of endpoint URLs to scan
        project_id: Project identifier
        
    Returns:
        Dict with pipeline execution results
    """
    logger = logging.getLogger('tasks.nuclei')
    
    try:
        # Convert endpoint list to project-endpoint format expected by nuclei integration
        logger.info(f"Starting nuclei pipeline run_id={run_id} endpoints={len(endpoints)} templates={len(templates)}")
        
        # Execute the scan using existing integration
        result = scan_project_endpoints(
            pid=project_id,
            templates=templates,
            severity=severity_levels,
            run_id=run_id
        )
        
        # Log SSE operations for observability
        from app.specialized_loggers import log_scan_completion, log_sse_operation
        
        log_sse_operation("start", run_id, len(endpoints))
        log_sse_operation("complete", run_id, len(endpoints))
        
        # Record metrics
        from metrics import record_run_findings, record_scan_run
        for severity in severity_levels:
            record_scan_run(severity)
            
        findings_count = result.get('findings_count', 0)
        if findings_count > 0:
            # Record findings by severity (simplified - assume medium if severity info not available)
            record_run_findings('medium', findings_count)
        
        log_scan_completion(run_id, len(endpoints), findings_count, result.get('duration_ms', 0))
        
        return result
        
    except Exception as e:
        logger.error(f"Nuclei pipeline failed run_id={run_id} error=\"{str(e)}\"")
        from app.specialized_loggers import log_sse_operation
        log_sse_operation("error", run_id, len(endpoints), {"error": str(e)})
        
        # Return error result in expected format
        return {
            'run_id': run_id,
            'success': False,
            'error': str(e),
            'findings_count': 0,
            'endpoints_scanned': 0,
            'duration_ms': 0
        }


__all__ = ["scan_project_endpoints"]


