#!/usr/bin/env python3
"""
P6 - Metrics Telemetry Logger

Simple metrics telemetry logging for observability.
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def log_metrics_telemetry(pid: str, event_type: str, data: Dict[str, Any]) -> None:
    """
    Log metrics telemetry to project-specific log file.
    
    Args:
        pid: Project ID
        event_type: Type of event (TRIAGE_UPDATE, METRICS_REBUILD_OK, etc.)
        data: Event data
    """
    try:
        log_dir = f"ui_projects/{pid}/logs"
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, "metrics.log")
        
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'event_type': event_type,
            'pid': pid,
            'data': data
        }
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        logger.debug(f"METRICS_TELEMETRY pid={pid} event={event_type}")
        
    except Exception as e:
        logger.warning(f"METRICS_TELEMETRY_ERROR pid={pid} error={str(e)}")


def log_triage_update(pid: str, finding_index: int, changes: Dict[str, Any]) -> None:
    """Log triage update event."""
    log_metrics_telemetry(pid, "TRIAGE_UPDATE", {
        'finding_index': finding_index,
        'changes': changes
    })


def log_metrics_rebuild(pid: str, success: bool, total_findings: int = 0, error: str = None) -> None:
    """Log metrics rebuild event."""
    data = {
        'success': success,
        'total_findings': total_findings
    }
    if error:
        data['error'] = error
    
    event_type = "METRICS_REBUILD_OK" if success else "METRICS_REBUILD_FAIL"
    log_metrics_telemetry(pid, event_type, data)


def log_export_generated(pid: str, format_type: str, filters: Dict[str, Any], file_size: int) -> None:
    """Log export generation event."""
    log_metrics_telemetry(pid, "EXPORT_GENERATED", {
        'format': format_type,
        'filters': filters,
        'file_size_bytes': file_size
    })


def log_sla_metrics_update(pid: str, sla_data: Dict[str, Any]) -> None:
    """Log SLA metrics update event."""
    log_metrics_telemetry(pid, "SLA_METRICS_UPDATED", sla_data)
