#!/usr/bin/env python3
"""
SecFlow Observability Budget Framework
Based on docs/architecture/17-observability-logging-and-metrics.md

This script defines the complete metrics set and log volume budgets
for M5 implementation of the observability layer.
"""

# Core Metrics Set (from architecture spec)
CORE_METRICS = {
    # API Layer Metrics
    "secflow_requests_total": {
        "type": "Counter",
        "description": "Total API requests handled",
        "budget": "< 10K requests/hour",
        "labels": ["method", "endpoint", "status_code"]
    },
    
    # Workflow Metrics
    "secflow_active_workflows": {
        "type": "Gauge", 
        "description": "Currently running workflows",
        "budget": "< 50 concurrent workflows",
        "labels": ["project", "workflow_type"]
    },
    
    # Findings Metrics
    "secflow_findings_generated_total": {
        "type": "Counter",
        "description": "Findings created",
        "budget": "< 1K findings/hour",
        "labels": ["project", "severity", "tool"]
    },
    
    # Performance Metrics
    "secflow_task_duration_seconds": {
        "type": "Histogram",
        "description": "Time taken by async tasks",
        "budget": "P95 < 300s, P99 < 600s",
        "buckets": [1, 5, 15, 30, 60, 120, 300, 600, 1800],
        "labels": ["task_type", "project"]
    },
    
    # System Metrics
    "secflow_gc_bytes_reclaimed_total": {
        "type": "Counter",
        "description": "GC reclaimed bytes",
        "budget": "> 80% efficiency",
        "labels": ["gc_type"]
    },
    
    # Sandbox Metrics
    "secflow_sandbox_executions_total": {
        "type": "Counter",
        "description": "Number of sandbox runs",
        "budget": "< 5K executions/hour",
        "labels": ["tool", "project"]
    },
    
    # Error Metrics
    "secflow_tool_failures_total": {
        "type": "Counter",
        "description": "Failed tool executions",
        "budget": "< 5% failure rate",
        "labels": ["tool", "error_type", "project"]
    },
    
    # Queue Metrics
    "secflow_worker_queue_depth": {
        "type": "Gauge",
        "description": "Pending Celery tasks",
        "budget": "< 100 pending tasks",
        "labels": ["queue_name"]
    },
    
    # Enrichment Metrics
    "secflow_cve_enrichment_latency_seconds": {
        "type": "Histogram",
        "description": "Time per CVE query",
        "budget": "P95 < 2s, P99 < 5s",
        "buckets": [0.1, 0.5, 1, 2, 5, 10],
        "labels": ["enrichment_type"]
    }
}

# Log Volume Budget Framework
LOG_VOLUME_BUDGET = {
    "per_service_hourly": "100MB",
    "per_service_daily": "2.4GB", 
    "total_system_daily": "10GB",
    "retention_hot": "7 days",
    "retention_cold": "30 days",
    "compression_ratio": "3:1"
}

# Log Level Distribution Budget
LOG_LEVEL_BUDGET = {
    "DEBUG": "0% (production disabled)",
    "INFO": "60% (system lifecycle)",
    "WARNING": "25% (recoverable issues)", 
    "ERROR": "10% (user operation failures)",
    "CRITICAL": "5% (irrecoverable errors)"
}

# Trace Context Budget
TRACE_BUDGET = {
    "coverage": "100%",
    "overhead_per_operation": "< 1ms",
    "context_fields": ["trace_id", "span_id", "project", "workflow_id"],
    "retention": "7 days"
}

# Prometheus Endpoint Budget
PROMETHEUS_BUDGET = {
    "response_size": "< 1MB",
    "scrape_interval": "15s",
    "retention": "15 days",
    "cardinality_limit": "10K series",
    "histogram_buckets": "< 20 per metric"
}

# Grafana Dashboard Budget
DASHBOARD_BUDGET = {
    "panels_per_dashboard": "< 20",
    "refresh_interval": "30s",
    "query_timeout": "30s",
    "max_series_per_query": "1000"
}

# Alerting Budget
ALERTING_BUDGET = {
    "max_alerts": "50",
    "evaluation_interval": "1m",
    "alert_evaluation_time": "< 1s",
    "notification_channels": "< 10"
}

def print_budget_summary():
    """Print comprehensive budget summary for M5 implementation."""
    print("=== SecFlow Observability Budget Framework ===")
    print(f"Core Metrics: {len(CORE_METRICS)} defined")
    print(f"Log Volume: {LOG_VOLUME_BUDGET['per_service_hourly']}/hour per service")
    print(f"Trace Coverage: {TRACE_BUDGET['coverage']}")
    print(f"Prometheus Response: {PROMETHEUS_BUDGET['response_size']}")
    print(f"Dashboard Panels: {DASHBOARD_BUDGET['panels_per_dashboard']} max")
    print(f"Alerting Rules: {ALERTING_BUDGET['max_alerts']} max")
    print("\n✅ Budget framework ready for M5 implementation")

if __name__ == "__main__":
    print_budget_summary()
