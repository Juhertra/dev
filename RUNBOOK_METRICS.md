# Metrics & Reporting Runbook

This runbook provides operational guidance for the P6 metrics and reporting system.

## Overview

The metrics system provides comprehensive analytics and reporting capabilities for security findings, including:

- **Real-time Metrics Dashboard**: Interactive charts and summary cards
- **Export Functionality**: CSV, JSON, and PDF report generation
- **Cache Management**: Automatic cache invalidation and rebuilding
- **API Access**: Programmatic access to metrics data

## Quick Start

### Access Metrics Dashboard

1. Navigate to `/p/<project_id>/metrics` in your browser
2. View summary cards, charts, and export options
3. Use filters to focus on specific findings

### Export Reports

```bash
# Basic CSV export
python3 scripts/export_findings_report.py --pid your_project_id --format csv

# Filtered export
python3 scripts/export_findings_report.py --pid your_project_id --format csv --status open --owner alice@example.com
```

## Cache Management

### Automatic Cache Rebuilding

Metrics caches are automatically rebuilt when:
- New findings are added via `append_findings()`
- Triage information is updated
- Findings are suppressed or resolved

### Manual Cache Rebuilding

```bash
# Rebuild cache for specific project
python3 -c "from core.analytics import rebuild_metrics_cache; rebuild_metrics_cache('your_project_id')"

# Rebuild all caches
python3 -c "from core.analytics import rebuild_metrics_cache; import os; [rebuild_metrics_cache(pid) for pid in os.listdir('ui_projects') if pid.endswith('.findings.json')]"
```

### Cache Verification

```bash
# Verify metrics cache
./scripts/verify_metrics.sh

# Check cache files
ls ui_projects/*/indexes/metrics_summary.json
```

## Export Commands

### CSV Export

```bash
# Basic export
python3 scripts/export_findings_report.py --pid your_project_id --format csv

# With filters
python3 scripts/export_findings_report.py --pid your_project_id --format csv --status open --tag auth --since 2025-01-01

# Output to specific file
python3 scripts/export_findings_report.py --pid your_project_id --format csv --output /path/to/report.csv
```

### JSON Export

```bash
# Basic export
python3 scripts/export_findings_report.py --pid your_project_id --format json

# With filters
python3 scripts/export_findings_report.py --pid your_project_id --format json --owner alice@example.com --status resolved
```

### PDF Export

```bash
# Basic export (requires reportlab)
python3 scripts/export_findings_report.py --pid your_project_id --format pdf

# Install reportlab if needed
pip install reportlab
```

## API Usage

### Get Metrics Data

```bash
# Basic metrics
curl "http://localhost:5001/p/your_project_id/metrics?format=json"

# With filters
curl "http://localhost:5001/p/your_project_id/metrics?format=json&status=open&owner=alice@example.com"

# HTML view
curl "http://localhost:5001/p/your_project_id/metrics"
```

### Export via API

```bash
# CSV export
curl "http://localhost:5001/p/your_project_id/export?format=csv" -o report.csv

# JSON export
curl "http://localhost:5001/p/your_project_id/export?format=json" -o report.json

# PDF export
curl "http://localhost:5001/p/your_project_id/export?format=pdf" -o report.pdf
```

## Troubleshooting

### Common Issues

#### 1. Metrics Dashboard Not Loading

**Symptoms**: Dashboard shows "Error loading metrics" or blank page

**Diagnosis**:
```bash
# Check if metrics cache exists
ls ui_projects/your_project_id/indexes/metrics_summary.json

# Check server logs for errors
tail -f logs/app.log | grep -i metrics
```

**Solutions**:
- Rebuild metrics cache: `python3 -c "from core.analytics import rebuild_metrics_cache; rebuild_metrics_cache('your_project_id')"`
- Check project has findings: `jq length ui_projects/your_project_id.findings.json`
- Verify server is running: `curl http://localhost:5001/health`

#### 2. Export Scripts Failing

**Symptoms**: Export commands return errors or empty files

**Diagnosis**:
```bash
# Test with dry-run
python3 scripts/export_findings_report.py --pid your_project_id --format csv --dry-run

# Check project findings
jq length ui_projects/your_project_id.findings.json
```

**Solutions**:
- Ensure project has findings
- Check file permissions in `exports/` directory
- Verify required dependencies (reportlab for PDF)

#### 3. Cache Not Updating

**Symptoms**: Metrics show stale data after findings changes

**Diagnosis**:
```bash
# Check cache age
find ui_projects/your_project_id/indexes/metrics_summary.json -mmin +5

# Check cache content
jq '.total_findings' ui_projects/your_project_id/indexes/metrics_summary.json
```

**Solutions**:
- Force cache rebuild: `python3 -c "from core.analytics import rebuild_metrics_cache; rebuild_metrics_cache('your_project_id')"`
- Check if `_bust_vulns_cache()` is being called after `append_findings()`
- Verify findings are being normalized before storage

#### 4. Charts Not Rendering

**Symptoms**: Dashboard loads but charts are blank

**Diagnosis**:
```bash
# Check browser console for JavaScript errors
# Check if Chart.js is loading
curl -s "http://localhost:5001/p/your_project_id/metrics" | grep -i chart
```

**Solutions**:
- Ensure Chart.js CDN is accessible
- Check browser JavaScript console for errors
- Verify metrics data structure: `jq '.trend_30d' ui_projects/your_project_id/indexes/metrics_summary.json`

### Debug Commands

```bash
# Check metrics cache structure
jq '.' ui_projects/your_project_id/indexes/metrics_summary.json

# Verify findings data
jq '.[] | {detector_id, severity, triage: .triage.status}' ui_projects/your_project_id.findings.json

# Test metrics calculation
python3 -c "
from core.analytics import get_metrics
import json
metrics = get_metrics('your_project_id')
print(json.dumps(metrics, indent=2))
"

# Check export script functionality
python3 scripts/export_findings_report.py --pid your_project_id --format csv --dry-run --verbose
```

## Performance Optimization

### Cache Optimization

- Metrics caches are automatically invalidated when findings change
- Cache files are stored in `ui_projects/<pid>/indexes/metrics_summary.json`
- Large projects may benefit from periodic cache rebuilding

### Export Optimization

- Use filters to reduce export size
- CSV exports are fastest for large datasets
- PDF exports require more memory and processing time

### API Optimization

- Use JSON format for programmatic access
- Apply filters to reduce data transfer
- Cache API responses in client applications

## Monitoring

### Key Metrics to Monitor

- **Cache Hit Rate**: Frequency of cache usage vs. rebuilds
- **Export Success Rate**: Percentage of successful exports
- **API Response Time**: Time to generate metrics data
- **Dashboard Load Time**: Time to render metrics dashboard

### Log Monitoring

```bash
# Monitor metrics-related logs
tail -f logs/app.log | grep -i metrics

# Monitor export operations
tail -f logs/app.log | grep -i export

# Monitor cache operations
tail -f logs/app.log | grep -i cache
```

## Maintenance

### Regular Tasks

1. **Weekly**: Verify metrics cache freshness
2. **Monthly**: Review export functionality
3. **Quarterly**: Analyze metrics trends and performance

### Backup Considerations

- Metrics caches can be regenerated from findings data
- Export files should be backed up if needed for compliance
- Consider archiving old export files

## Security Considerations

### Access Control

- Metrics dashboard inherits project access controls
- Export functionality respects project permissions
- API endpoints require proper authentication

### Data Privacy

- Export files may contain sensitive information
- Ensure proper file permissions on export directory
- Consider data retention policies for exported reports

## Integration

### CI/CD Integration

```bash
# Add metrics verification to CI pipeline
./scripts/verify_metrics.sh

# Export metrics for reporting
python3 scripts/export_findings_report.py --pid $PROJECT_ID --format json --output metrics.json
```

### Monitoring Integration

```bash
# Send metrics to monitoring system
curl -X POST "https://monitoring.example.com/metrics" \
  -H "Content-Type: application/json" \
  -d @metrics.json
```

## Support

For additional support:

1. Check this runbook for common issues
2. Review server logs for error details
3. Verify findings data integrity
4. Test with a known working project
5. Contact the development team with specific error messages and logs
