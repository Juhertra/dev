"""
Metrics collection for Phase 3 observability.
Provides counters and histograms for performance monitoring.
"""

import os
from typing import Dict, Any
import time

# Simple in-memory metrics store (can be swapped for Prometheus later)
_metrics: Dict[str, Any] = {
    'counters': {},
    'histograms': {},
    'gauges': {}
}

def _get_or_create_counter(name: str) -> Dict[str, int]:
    """Get or create a counter metric."""
    if name not in _metrics['counters']:
        _metrics['counters'][name] = {}
    return _metrics['counters'][name]

def _get_or_create_histogram(name: str) -> Dict[str, list]:
    """Get or create a histogram metric."""
    if name not in _metrics['histograms']:
        _metrics['histograms'][name] = {}
    return _metrics['histograms'][name]

def record_cache_hit(keyspace: str):
    """Record a cache hit."""
    if not should_collect_metrics():
        return
    
    counters = _get_or_create_counter('cache_hits_total')
    if keyspace not in counters:
        counters[keyspace] = 0
    counters[keyspace] += 1

def record_cache_miss(keyspace: str):
    """Record a cache miss."""
    if not should_collect_metrics():
        return
    
    counters = _get_or_create_counter('cache_misses_total')
    if keyspace not in counters:
        counters[keyspace] = 0
    counters[keyspace] += 1

def record_drawer_request(kind: str):
    """Record drawer request metrics (preview, runs, findings)."""
    if not should_collect_metrics():
        return
    
    counters = _get_or_create_counter('drawer_requests_total')
    if kind not in counters:
        counters[kind] = 0
    counters[kind] += 1

def record_nuclei_scan(severity: str, endpoints_count: int = 1):
    """Record nuclei scan metrics."""
    if not should_collect_metrics():
        return
    
    counters = _get_or_create_counter('nuclei_scans_total')
    # Use severity as label, endpoints_count as increment amount
    key = f"{severity}:{endpoints_count}"
    if key not in counters:
        counters[key] = 0
    counters[key] += endpoints_count

def record_http_request(path: str, method: str, status: int):
    """Record HTTP request metrics."""
    if not should_collect_metrics():
        return
    
    # Remove dynamic parts for aggregation
    normalized_path = path.replace('<pid>', 'PID').replace('<spec_id>', 'SPEC')
    
    # HTTP request counter
    counters = _get_or_create_counter('http_requests_total')
    key = f"{normalized_path}:{method}:{status}"
    if key not in counters:
        counters[key] = 0
    counters[key] += 1
    
    # Request duration histogram (simplified)
    histograms = _get_or_create_histogram('http_request_duration_ms')
    if normalized_path not in histograms:
        histograms[normalized_path] = []
    histograms[normalized_path].append(time.time())

def record_drawer_render(kind: str):
    """Record drawer render metrics."""
    if not should_collect_metrics():
        return
    
    counters = _get_or_create_counter('drawer_renders_total')
    if kind not in counters:
        counters[kind] = 0
    counters[kind] += 1

def record_scan_run(severity: str):
    """Record scan run metrics."""
    if not should_collect_metrics():
        return
    
    counters = _get_or_create_counter('scan_runs_total')
    if severity not in counters:
        counters[severity] = 0
    counters[severity] += 1

def record_run_findings(severity: str, count: int):
    """Record findings metrics."""
    if not should_collect_metrics():
        return
    
    counters = _get_or_create_counter('run_findings_total')
    if severity not in counters:
        counters[severity] = 0
    counters[severity] += count

def should_collect_metrics() -> bool:
    """Check if metrics collection is enabled."""
    return os.environ.get('ENABLE_METRICS', '0') == '1'

def get_metrics_summary() -> Dict[str, Any]:
    """Get metrics summary for debugging."""
    if not should_collect_metrics():
        return {"enabled": False}
    
    return {
        "enabled": True,
        "counters": _metrics['counters'],
        "histograms": {k: {"count": len(v), "keys": list(v.keys())} for k, v in _metrics['histograms'].items()},
        "total_metrics": len(_metrics['counters']) + len(_metrics['histograms'])
    }

def export_prometheus_metrics() -> str:
    """
    Export metrics in Prometheus text format.
    Called by /metrics endpoint when ENABLE_METRICS=1.
    """
    if not should_collect_metrics():
        return "# Metrics disabled\n"
    
    lines = []
    
    # Export counters
    for metric_name, labels_dict in _metrics['counters'].items():
        for labels_str, value in labels_dict.items():
            # Parse labels_str into Prometheus format
            line = f"{metric_name}{{{labels_str}}} {value}"
            lines.append(line)
    
    # Export histograms (simplified)
    for metric_name, buckets_dict in _metrics['histograms'].items():
        for label, values in buckets_dict.items():
            count = len(values)
            line = f"{metric_name}_count{{{label}}} {count}"
            lines.append(line)
    
    return "\n".join(lines) + "\n"

# Export functions for easy import
__all__ = [
    'record_cache_hit',
    'record_cache_miss', 
    'record_http_request',
    'record_drawer_render',
    'record_scan_run',
    'record_run_findings',
    'record_drawer_request',
    'record_nuclei_scan',
    'should_collect_metrics',
    'get_metrics_summary',
    'export_prometheus_metrics'
]