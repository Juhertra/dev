# Security Toolkit

A comprehensive security testing platform with automated vulnerability detection and management.

## Features

- **Pattern Engine**: Custom regex-based vulnerability detection
- **Nuclei Integration**: Automated security scanning with Nuclei templates
- **Real-time Scanning**: Server-Sent Events (SSE) for live scan progress
- **Vulnerability Management**: Centralized findings storage and analysis
- **Metrics & Reporting**: Analytics dashboard with trend visualization and export capabilities
- **API Explorer**: Interactive API testing interface

## Findings Contract

The findings system uses a strict data contract to ensure consistency and reliability across all vulnerability detection sources.

### Required Fields

All findings must contain these required fields:

- `detector_id`: Unique identifier (no colons allowed)
- `title`: Human-readable finding title
- `severity`: One of `critical`, `high`, `medium`, `low`, `info`
- `path`: URL path component (extracted from full URL)
- `method`: HTTP method (`GET`, `POST`, etc.)
- `url`: Full target URL
- `status`: Finding status (defaults to `"open"`)
- `created_at`: ISO 8601 timestamp with Z suffix (`YYYY-MM-DDTHH:MM:SSZ`)
- `confidence`: Integer confidence score (0-100)
- `req`: HTTP request object with `headers`, `body`, `method`, `url`
- `res`: HTTP response object with `headers`, `body`, `status_code`

### Field Formats

#### Detector ID
- **Pattern Engine**: `pattern_name` (colons converted to underscores)
- **Nuclei**: `nuclei.template-name` (colons converted to dots)
- **Validation**: Must match `^[A-Za-z0-9][A-Za-z0-9._-]*$`

#### Classification Fields
- **OWASP**: Must match `^A\d{2}:\d{4}$` (e.g., `A05:2021`)
- **CWE**: Must match `^CWE-\d+$` (e.g., `CWE-200`)
- **CVE**: Must match `^CVE-\d{4}-\d+$` (placeholders like `CVE-0000-0000` are rejected)

#### Timestamps
- **Format**: ISO 8601 UTC with Z suffix
- **Example**: `2025-10-05T19:30:00Z`
- **Conversion**: Integer timestamps are automatically converted

### Normalization

All findings must be normalized using `utils.findings_normalize.normalize_finding()` before storage:

```python
from utils.findings_normalize import normalize_finding

normalized = normalize_finding(
    raw_finding,
    pid=project_id,
    run_id=run_id,
    method=method,
    url=url,
    status_code=status_code
)
```

## Metrics & Reporting

The platform includes comprehensive analytics and reporting capabilities for security findings.

### Metrics Dashboard

Access the metrics dashboard at `/p/<project_id>/metrics` to view:

- **Summary Cards**: Total findings, active, resolved, false positives, average fix time
- **Trend Charts**: 30-day finding trends with interactive visualization
- **Severity Breakdown**: Distribution of findings by severity level
- **Top Tags**: Most common vulnerability tags
- **Top Owners**: Findings ownership distribution

### Export Functionality

Export findings reports in multiple formats:

```bash
# CSV export
python3 scripts/export_findings_report.py --pid your_project_id --format csv

# JSON export
python3 scripts/export_findings_report.py --pid your_project_id --format json

# PDF export (requires reportlab)
python3 scripts/export_findings_report.py --pid your_project_id --format pdf
```

### Export Filters

Apply filters to exported reports:

```bash
# Filter by status
python3 scripts/export_findings_report.py --pid your_project_id --format csv --status open

# Filter by owner
python3 scripts/export_findings_report.py --pid your_project_id --format csv --owner alice@example.com

# Filter by tag
python3 scripts/export_findings_report.py --pid your_project_id --format csv --tag auth

# Filter by date
python3 scripts/export_findings_report.py --pid your_project_id --format csv --since 2025-01-01
```

### Metrics API

Access metrics programmatically:

```bash
# Get metrics as JSON
curl "http://localhost:5001/p/your_project_id/metrics?format=json"

# Get metrics with filters
curl "http://localhost:5001/p/your_project_id/metrics?format=json&status=open&owner=alice@example.com"
```

### Cache Management

Metrics are automatically cached and rebuilt when findings change:

```bash
# Rebuild metrics cache for specific project
python3 -c "from core.analytics import rebuild_metrics_cache; rebuild_metrics_cache('your_project_id')"

# Verify metrics cache
./scripts/verify_metrics.sh
```

## Bulk Triage Operations (P7)

The Vulnerabilities Hub supports efficient bulk triage operations using HTMX and partials for seamless user experience.

### Features

- **HTMX Integration**: Real-time partial updates without page reloads
- **Responsive Design**: Mobile-friendly sticky bulk action bar
- **Accessibility**: Full keyboard navigation and screen reader support
- **Progressive Enhancement**: Works without JavaScript, enhanced with it

### Bulk Actions Available

- **Set Status**: Change triage status (open, in_progress, risk_accepted, false_positive, resolved)
- **Set Owner**: Assign ownership to findings
- **Add/Remove Tags**: Manage categorization tags
- **Suppress**: Temporarily or permanently suppress findings

### Using Bulk Triage

1. Navigate to the Vulnerabilities Hub: `/p/<project_id>/vulns`
2. Select vulnerabilities using the checkboxes
3. Use the bulk action bar to apply changes:
   - Select status from dropdown
   - Enter owner email
   - Add or remove tags
   - Set suppression duration and reason
4. Click "Apply" to execute bulk operations

### Technical Implementation

**HTMX Integration**:
- `hx-post="/p/<pid>/vulns/bulk"` for bulk operations
- `hx-target="#vulns-list"` for partial list updates
- `hx-vals="js:window.VulnsBulk.buildPayload(action)"` for dynamic payloads
- Automatic selection clearing after server refresh

**File Structure**:
```
templates/_partials/
├── vulns_table.html      # Extracted vulnerabilities table
└── vulns_bulkbar.html    # Bulk action bar with HTMX

static/
├── js/vulns-bulk.js      # Minimal selection model
└── css/vulns-bulk.css    # Responsive bulk bar styles
```

### Bulk API Endpoint

For programmatic access, use the bulk API:

```bash
# Bulk status change
curl -X POST "http://localhost:5001/p/your_project_id/vulns/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "indices": [0, 1, 2],
    "actions": [
      {"action": "set_status", "value": "in_progress"},
      {"action": "set_owner", "value": "security@example.com"},
      {"action": "add_tag", "value": "urgent"}
    ]
  }'

# Bulk suppression
curl -X POST "http://localhost:5001/p/your_project_id/vulns/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "indices": [5, 6, 7],
    "actions": [
      {
        "action": "suppress",
        "value": {
          "reason": "False positive in test environment",
          "until": "2025-02-01T00:00:00Z",
          "scope": "this"
        }
      }
    ]
  }'
```

### Performance Considerations

- Large selections are automatically batched (250 items per batch)
- Operations complete in < 2 seconds for 5,000 items locally
- Cache is rebuilt once after all operations complete
- Concurrent edits use optimistic locking (last write wins)
- Only swaps `#vulns-list` container (no DOM churn)

### Supported Actions

| Action | Value Type | Description |
|--------|------------|-------------|
| `set_status` | string | Set triage status (open, in_progress, risk_accepted, false_positive, resolved) |
| `set_owner` | string | Assign owner email/handle |
| `add_tag` | string | Add categorization tag |
| `remove_tag` | string | Remove existing tag |
| `suppress` | object | Suppress finding with reason, duration, and scope |

### Suppression Options

- **Duration**: 1 day, 7 days, 30 days, or permanent
- **Scope**: `this` (single finding), `endpoint` (all findings on endpoint), `detector` (all findings from detector)
- **Reason**: Required text explanation

### Accessibility Features

- **Keyboard Navigation**: Tab through controls, Space toggles checkboxes, Enter activates buttons
- **ARIA Labels**: All interactive elements have descriptive labels
- **Focus Management**: Visible focus states with proper contrast
- **Screen Reader Support**: Semantic HTML structure with proper announcements

## How to Run Migration

The P3 migration scripts normalize all existing findings to the new contract:

### Dry Run (Recommended First)
```bash
# Test migration without making changes
python3 scripts/migrate_legacy_findings.py --dry-run --limit 10

# Test backfill without making changes
python3 scripts/backfill_run_info.py --dry-run
```

### Full Migration
```bash
# Migrate all findings with backup
python3 scripts/migrate_legacy_findings.py --backup

# Backfill missing Nuclei run info
python3 scripts/backfill_run_info.py

# Rebuild all caches
python3 scripts/rebuild_vulns_caches.py

# Verify migration success
./scripts/verify_post_migration.sh
```

### Project-Specific Migration
```bash
# Migrate specific project only
python3 scripts/migrate_legacy_findings.py --pid your_project_id --backup
```

## How to Run Tests

The P4 test suite ensures contract compliance and prevents regressions:

### Unit Tests
```bash
# Test findings normalization
python -m pytest tests/test_findings_normalize.py -v

# Test full contract (normalize → append → cache → summary)
python -m pytest tests/test_append_and_cache.py -v

# Test SSE stream contract
python -m pytest tests/test_sse_stream.py -v

# Test metrics and analytics
python -m pytest tests/test_metrics.py -v

# Test export functionality
python -m pytest tests/test_export.py -v

# Test UI metrics
python -m pytest tests/test_ui_metrics.py -v
```

### All Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=term-missing
```

### Pre-commit Guards
```bash
# Run pre-commit checks manually
./scripts/pre-commit-guards.sh
```

## Development Guidelines

### Adding New Findings

1. **Always use `normalize_finding()`** before calling `append_findings()`
2. **Ensure all required fields** are present
3. **Call `_bust_vulns_cache()`** after `append_findings()`
4. **For SSE events**, include `"stored": true` in finding events

### SSE Contract

Server-Sent Events must follow this contract:

```javascript
// Start event
event: start
data: {"run_id": "...", "total_endpoints": 10}

// Progress event
event: progress
data: {"processed": 5, "total": 10, "endpoint": {"method": "GET", "path": "/api"}, "template_id": "...", "detector_source": "nuclei"}

// Finding event (MUST have stored: true)
event: finding
data: {"stored": true, "detector_id": "...", "severity": "...", "endpoint_key": "GET /api", "title": "...", "created_at": "2025-10-05T19:30:00Z", "source": "nuclei"}

// Done event
event: done
data: {"run_id": "...", "duration_ms": 5000, "endpoints_processed": 10, "findings": 3}
```

### Error Handling

- **Storage failures** should emit `event: error` instead of `event: finding`
- **Invalid findings** should be logged and dropped, not crash the system
- **Cache failures** should be logged as warnings, not errors

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Pattern Engine │    │   Nuclei Scanner │    │   Legacy Detectors │
└─────────┬───────┘    └─────────┬────────┘    └─────────┬───────┘
          │                      │                       │
          └──────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │   normalize_finding()     │
                    │   (Single Source of Truth)│
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │     append_findings()     │
                    │   (Schema Validation)     │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │   _bust_vulns_cache()    │
                    │   (Cache Invalidation)   │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │   SSE Event: finding     │
                    │   {"stored": true, ...}  │
                    └───────────────────────────┘
```

## Troubleshooting

### Common Issues

1. **Schema Validation Failures**
   - Check that all required fields are present
   - Verify field formats (detector_id, created_at, etc.)
   - Use `normalize_finding()` to fix common issues

2. **Cache Not Updating**
   - Ensure `_bust_vulns_cache()` is called after `append_findings()`
   - Check that cache files exist in `ui_projects/*/indexes/`

3. **SSE Events Not Showing**
   - Verify `"stored": true` is present in finding events
   - Check that findings are actually stored before emitting SSE

### Debug Commands

```bash
# Check findings schema compliance
jq '.[] | {detector_id, path, created_at, req: has("req"), res: has("res")}' ui_projects/*/findings.json

# Verify no colon detector_ids
jq -r '.[].detector_id' ui_projects/*/findings.json | grep ':' || echo "No colons found ✅"

# Check cache files
ls ui_projects/*/indexes/vulns_summary.json
```

## Contributing

1. **Follow the findings contract** - use `normalize_finding()` for all new findings
2. **Write tests** - ensure new features have corresponding tests
3. **Run pre-commit guards** - use `./scripts/pre-commit-guards.sh` before committing
4. **Update documentation** - keep this README current with any contract changes

## License

[Add your license information here]
