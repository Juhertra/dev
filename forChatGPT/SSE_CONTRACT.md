# SSE Contract - Active Testing Event Stream

## Event Stream Specification

**Endpoint**: `GET /p/<pid>/nuclei/stream`  
**Content-Type**: `text/event-stream`  
**Cache-Control**: `no-cache`  
**Connection**: `keep-alive`

## Headers Set by Server

```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no  # Disable nginx buffering
```

## Event Types

| Event Type | Description | Fields | Client Behavior |
|------------|-------------|--------|-----------------|
| `start` | Scan initialization | `run_id`, `endpoints`, `templates` | Show progress UI, enable cancel |
| `progress` | Per-endpoint progress | `current`, `total`, `endpoint` | Update progress bar, show current URL |
| `finding` | Vulnerability discovered | `detector_id`, `severity`, `url`, `title` | Add to live findings list |
| `done` | Scan completion | `run_id`, `findings_count`, `duration_ms` | Show summary, enable new scan |
| `error` | Scan failure | `run_id`, `error`, `retry_after` | Show error, offer retry |
| `heartbeat` | Keep-alive (every 30s) | `timestamp` | Reset timeout timer |

## Event Field Specifications

### `start` Event
```json
{
  "run_id": "run-20240115-1045-test-project",
  "endpoints": 12,
  "templates": ["http-methods", "sqli-auth"],
  "estimated_duration": "2-4 minutes"
}
```

### `progress` Event
```json
{
  "current": 3,
  "total": 12,
  "endpoint": {
    "method": "GET",
    "url": "https://api.example.com/users",
    "status": "scanning"
  },
  "elapsed_ms": 45000
}
```

### `finding` Event
```json
{
  "event": "finding",
  "stored": true,
  "detector_id": "nuclei.http-methods",
  "severity": "medium",
  "endpoint_key": "GET https://api.example.com/users",
  "title": "HTTP Method Disclosure",
  "created_at": "2024-01-15T10:45:30Z",
  "source": "nuclei"
}
```

**⚠️ CRITICAL**: The `finding` event **MUST** include `"stored": true` to indicate the finding has been successfully persisted to storage. Events without this flag will be rejected by the P4 regression guardrails.

### `done` Event
```json
{
  "run_id": "run-20240115-1045-test-project",
  "findings_count": 5,
  "endpoints_scanned": 12,
  "duration_ms": 120000,
  "success": true
}
```

### `error` Event
```json
{
  "run_id": "run-20240115-1045-test-project",
  "error": "Nuclei binary not found",
  "retry_after": 30,
  "severity": "fatal"
}
```

### `heartbeat` Event
```json
{
  "timestamp": "2024-01-15T10:45:30Z",
  "status": "active"
}
```

## Retry & Timeout Behavior

**Client Timeout**: 5 minutes of no events → reconnect  
**Server Timeout**: 10 minutes of inactivity → close connection  
**Retry Strategy**: Exponential backoff (1s, 2s, 4s, 8s, max 30s)  
**Idempotency**: Use `run_id` to prevent duplicate processing

## Sample Event Stream (20 lines)

```
event: start
data: {"run_id": "run-20240115-1045", "endpoints": 3, "templates": ["http-methods"], "estimated_duration": "1-2 minutes"}

event: progress
data: {"current": 1, "total": 3, "endpoint": {"method": "GET", "url": "https://httpbin.org/get", "status": "scanning"}, "elapsed_ms": 5000}

event: finding
data: {"event": "finding", "stored": true, "detector_id": "nuclei.http-methods", "severity": "info", "endpoint_key": "GET https://httpbin.org/get", "title": "HTTP Methods Allowed", "created_at": "2024-01-15T10:45:35Z", "source": "nuclei"}

event: progress
data: {"current": 2, "total": 3, "endpoint": {"method": "POST", "url": "https://httpbin.org/post", "status": "scanning"}, "elapsed_ms": 15000}

event: progress
data: {"current": 3, "total": 3, "endpoint": {"method": "PUT", "url": "https://httpbin.org/put", "status": "scanning"}, "elapsed_ms": 25000}

event: finding
data: {"event": "finding", "stored": true, "detector_id": "nuclei.http-methods", "severity": "medium", "endpoint_key": "PUT https://httpbin.org/put", "title": "Unsafe HTTP Method", "created_at": "2024-01-15T10:45:50Z", "source": "nuclei"}

event: done
data: {"run_id": "run-20240115-1045", "findings_count": 2, "endpoints_scanned": 3, "duration_ms": 30000, "success": true}
```

## Implementation Notes

**Server-Side** (`routes/nuclei.py:235-250`):
- Stream starts immediately after scan submission
- Events are flushed immediately (no buffering)
- Connection closed on scan completion or error
- **P4 Requirement**: Finding events MUST include `"stored": true` after successful persistence

**Client-Side** (`templates/active_testing.html:45-65`):
- EventSource auto-reconnects on connection loss
- Progress updates trigger DOM manipulation
- Finding events append to live results list
- **P4 Requirement**: Only process finding events with `"stored": true`

## P4 Regression Guardrails

The P4 implementation enforces strict SSE contract compliance:

### Pre-commit Guards
- **Colon Detection**: Fails if `detector_id` contains colons
- **Stored Flag**: Fails if `event: finding` lacks `"stored": true`
- **Schema Validation**: Validates SSE event structure against JSON schema

### Test Suite
- **Unit Tests**: 18 tests covering normalization transformations
- **Contract Tests**: 5 tests ensuring schema compliance
- **SSE Tests**: 5 tests validating streaming contracts

### CI/CD Integration
- **GitHub Actions**: Automated enforcement on every PR
- **Pre-commit Hooks**: Local validation before commits
- **Comprehensive Coverage**: 29 tests ensuring contract compliance

### Usage
```bash
# Run all P4 tests
python -m pytest tests/ -v

# Run pre-commit guards
./scripts/pre-commit-guards.sh

# Check SSE contract compliance
python -m pytest tests/test_sse_stream.py -v
```
