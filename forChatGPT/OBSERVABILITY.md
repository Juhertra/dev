# Observability Specification

## Logging Fields Specification

### Request Logs (`app/logging_conf.py:13-36`)

**Standard Fields**:
```json
{
  "level": "INFO",
  "logger": "flask.request",
  "message": "Request completed",
  "request_id": "req-123e4567-e89b-12d3-a456-426614174000",
  "duration_ms": 245,
  "path": "/p/test-project/sitemap",
  "method": "GET",
  "status": 200,
  "user_agent": "Mozilla/5.0...",
  "ip": "192.168.1.100"
}
```

**Error Request Example**:
```json
{
  "level": "ERROR",
  "logger": "flask.request",
  "message": "Request failed",
  "request_id": "req-456e7890-e89b-12d3-a456-426614174001",
  "duration_ms": 1200,
  "path": "/p/test-project/nuclei/scan",
  "method": "POST",
  "status": 500,
  "error": "Nuclei binary not found",
  "stack_trace": "Traceback (most recent call last)..."
}
```

### Domain Logs

#### Run Logs (`app/specialized_loggers.py:15-25`)
```json
{
  "level": "INFO",
  "logger": "runs.scan",
  "message": "Scan started",
  "run_id": "run-20240115-1045",
  "project_id": "proj-123",
  "endpoints_count": 12,
  "templates": ["http-methods", "sqli-auth"],
  "severity_filter": ["medium", "high"],
  "duration_ms": 0
}
```

#### Cache Logs (`cache.py:29-49`)
```json
{
  "level": "DEBUG",
  "logger": "cache.operation",
  "message": "Cache miss",
  "cache_key": "build_site_map:('proj-123',):{}",
  "function": "build_site_map",
  "ttl_seconds": 300,
  "computation_time_ms": 45
}
```

#### SSE Logs (`routes/nuclei.py:235-250`)
```json
{
  "level": "INFO",
  "logger": "sse.stream",
  "message": "SSE stream started",
  "run_id": "run-20240115-1045",
  "client_ip": "192.168.1.100",
  "stream_duration_ms": 0,
  "events_sent": 0
}
```

## Metrics Catalog

### Counters

| Metric Name | Labels | Function | Description |
|-------------|--------|----------|-------------|
| `flask_http_requests_total` | `method`, `endpoint`, `status` | `metrics.py:record_http_request()` | Total HTTP requests |
| `flask_cache_hits_total` | `keyspace` | `metrics.py:record_cache_hit()` | Cache hits by namespace |
| `flask_cache_misses_total` | `keyspace` | `metrics.py:record_cache_miss()` | Cache misses by namespace |
| `flask_drawer_requests_total` | `kind` | `metrics.py:record_drawer_request()` | Drawer open requests |
| `flask_nuclei_scans_total` | `severity`, `success` | `metrics.py:record_nuclei_scan()` | Nuclei scan executions |
| `flask_sse_streams_total` | `project_id` | `metrics.py:record_sse_stream()` | SSE stream connections |
| `flask_findings_created_total` | `severity`, `detector` | `metrics.py:record_finding_created()` | New findings created |

### Histograms

| Metric Name | Labels | Function | Description |
|-------------|--------|----------|-------------|
| `flask_http_request_duration_ms` | `method`, `endpoint` | `metrics.py:record_http_request()` | Request duration |
| `flask_drawer_duration_ms` | `kind` | `metrics.py:record_drawer_request()` | Drawer response time |
| `flask_sse_stream_duration_ms` | `project_id` | `metrics.py:record_sse_stream()` | SSE stream duration |
| `flask_nuclei_scan_duration_ms` | `severity` | `metrics.py:record_nuclei_scan()` | Scan execution time |

### Gauges

| Metric Name | Labels | Function | Description |
|-------------|--------|----------|-------------|
| `flask_active_sse_streams` | `project_id` | `metrics.py:update_active_streams()` | Currently active SSE streams |
| `flask_cache_size_bytes` | `keyspace` | `metrics.py:update_cache_size()` | Cache memory usage |
| `flask_projects_total` | - | `metrics.py:update_project_count()` | Total number of projects |

## Cache Keys Registry

### Key Format: `{function_name}:{args}:{kwargs}`

| Function | Key Pattern | TTL | Invalidation Triggers |
|----------|-------------|-----|----------------------|
| `build_site_map` | `build_site_map:('{pid}',):{}` | 300s | Project spec changes, findings updates |
| `count_findings_cached` | `count_findings:('{pid}',):{}` | 60s | Findings added/removed/triaged |
| `get_endpoint_runs_by_key` | `get_endpoint_runs_by_key:('{pid}', '{key}'):{}` | 300s | New runs completed for endpoint |
| `list_runs` | `list_runs:('{pid}',):{}` | 60s | New runs added, runs deleted |

### Cache Invalidation Points

**Automatic Invalidation** (`cache.py:51-60`):
```python
def invalidate_cache(pattern: str = None):
    """Invalidate cache entries matching pattern"""
    if pattern:
        keys_to_remove = [key for key in _cache.keys() if pattern in key]
        for key in keys_to_remove:
            del _cache[key]
        logger.info(f"Invalidated {len(keys_to_remove)} cache entries matching '{pattern}'")
    else:
        _cache.clear()
        logger.info("Cleared entire cache")
```

**Trigger Points**:
- `findings.py:append_findings()` → invalidate `count_findings_cached`
- `store.py:append_run()` → invalidate `list_runs`, `get_endpoint_runs_by_key`
- `store.py:update_endpoint_dossier_by_key()` → invalidate `build_site_map`
- Project spec changes → invalidate `build_site_map`

## Prometheus Query Examples

**Request Rate by Endpoint**:
```promql
sum(rate(flask_http_requests_total[5m])) by (endpoint)
```

**Cache Hit Ratio**:
```promql
sum(rate(flask_cache_hits_total[5m])) / sum(rate(flask_cache_misses_total[5m]))
```

**95th Percentile Response Time**:
```promql
histogram_quantile(0.95, flask_http_request_duration_ms_bucket)
```

**Active SSE Streams**:
```promql
sum(flask_active_sse_streams)
```

**Error Rate by Endpoint**:
```promql
sum(rate(flask_http_requests_total{status=~"5.."}[5m])) by (endpoint) / 
sum(rate(flask_http_requests_total[5m])) by (endpoint)
```

## Log Aggregation Setup

**ELK Stack Configuration** (`logstash/pipeline.conf`):
```ruby
input {
  file {
    path => "/var/log/security-toolkit/*.log"
    codec => "json"
  }
}

filter {
  if [logger] == "flask.request" {
    mutate {
      add_field => { "service" => "security-toolkit" }
      add_field => { "component" => "web" }
    }
  }
  
  if [logger] =~ /^runs\./ {
    mutate {
      add_field => { "service" => "security-toolkit" }
      add_field => { "component" => "scanner" }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "security-toolkit-%{+YYYY.MM.dd}"
  }
}
```

**Grafana Dashboard Queries**:
- **Request Volume**: `sum(rate(flask_http_requests_total[1m]))`
- **Error Rate**: `sum(rate(flask_http_requests_total{status=~"5.."}[5m])) / sum(rate(flask_http_requests_total[5m]))`
- **Cache Performance**: `sum(rate(flask_cache_hits_total[5m])) / (sum(rate(flask_cache_hits_total[5m])) + sum(rate(flask_cache_misses_total[5m])))`
- **Active Scans**: `sum(flask_active_sse_streams)`
