# Security Toolkit Runbook

## Environment Variables

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `LOG_LEVEL` | `INFO` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) | No |
| `ENABLE_METRICS` | `false` | Enable Prometheus metrics collection | No |
| `SECRET_KEY` | `dev-key-change-me` | Flask session secret key | Yes (prod) |
| `API_KEYS` | `test-key-123` | Comma-separated API keys | No |
| `NUCLEI_TEMPLATES_DIR` | `~/.local/share/nuclei/templates` | Nuclei templates directory | No |
| `EXPLICIT_PORT` | `5001` | Application port | No |
| `FEATURE_DEBUG_MODE` | `false` | Enable debug features | No |

## Port Configuration

### Default Ports
- **Development**: `5001` (Flask dev server)
- **Alternative**: `5000` (if 5001 busy)
- **Production**: `8080` (behind reverse proxy)
- **HTTPS**: `443` (with SSL termination)

### Port Conflict Resolution
```bash
# Check port availability
netstat -tlnp | grep :5001

# Kill process using port
sudo lsof -ti:5001 | xargs kill -9

# Use alternative port
export EXPLICIT_PORT=8080
python app.py
```

## Startup Commands

### Development
```bash
# Basic startup
python app.py

# With debug logging
LOG_LEVEL=DEBUG python app.py

# With metrics enabled
ENABLE_METRICS=true python app.py

# Custom port
EXPLICIT_PORT=8080 python app.py
```

### Production
```bash
# Using gunicorn
gunicorn -w 4 -b 0.0.0.0:8080 wsgi:app

# Using systemd
sudo systemctl start security-toolkit
sudo systemctl enable security-toolkit

# Using Docker
docker run -p 8080:8080 -e SECRET_KEY=your-secret security-toolkit
```

## Log Locations

### Application Logs
```bash
# Main application log
tail -f logs/app.log

# Request logs (if structured logging enabled)
tail -f logs/requests.log | jq '.'

# Error logs
tail -f logs/error.log

# Cache logs
tail -f logs/cache.log | grep -E "(HIT|MISS)"
```

### System Logs
```bash
# Systemd service logs
journalctl -u security-toolkit -f

# Docker logs
docker logs -f security-toolkit-container

# Nginx logs (if using reverse proxy)
tail -f /var/log/nginx/security-toolkit.log
```

## Smoke Test Steps

### Quick Health Check
```bash
# 1. Check if app is running
curl -f http://localhost:5001/ || echo "❌ App not responding"

# 2. Check API health
curl -f http://localhost:5001/api/v1/metrics \
  -H "X-API-Key: test-key-123" || echo "❌ API not responding"

# 3. Check project creation
curl -X POST http://localhost:5001/p/create \
  -d "name=Smoke Test" || echo "❌ Project creation failed"

# 4. Check drawer functionality
curl -X POST http://localhost:5001/p/default/sitemap/endpoint-preview \
  -d "url=https://httpbin.org/get&method=GET" || echo "❌ Drawer failed"

# 5. Check findings contract compliance (P4)
python -m pytest tests/test_findings_normalize.py -v || echo "❌ Findings normalization tests failed"

# 6. Check SSE contract compliance (P4)
python -m pytest tests/test_sse_stream.py -v || echo "❌ SSE contract tests failed"
```

### Comprehensive Smoke Test
```bash
# Run automated smoke test
python tools/smoke.py

# Run P4 regression tests
python -m pytest tests/ -v

# Run pre-commit guards
./scripts/pre-commit-guards.sh

# Expected output:
# ✅ Project created successfully
# ✅ Endpoints queued successfully  
# ✅ Scan started successfully
# ✅ SSE stream connected
# ✅ Dossier files created
# ✅ Findings contract compliance verified
# ✅ SSE contract compliance verified
# ✅ Pre-commit guards passed
# ✅ Smoke test completed successfully
```

## Troubleshooting Commands

### Application Issues
```bash
# Check Python dependencies
pip list | grep -E "(flask|nuclei|requests)"

# Check Nuclei installation
nuclei --version || echo "❌ Nuclei not installed"

# Check file permissions
ls -la ui_projects/ || echo "❌ ui_projects directory missing"

# Check JSON file integrity
find ui_projects -name "*.json" -exec jq '.' {} \; 2>&1 | grep -v "parse error" | wc -l

# Check cache status
python -c "from cache import get_cache_stats; print(get_cache_stats())"
```

### Performance Issues
```bash
# Check memory usage
ps aux | grep python | grep app.py

# Check disk usage
du -sh ui_projects/

# Check open file descriptors
lsof -p $(pgrep -f "python.*app.py") | wc -l

# Check network connections
netstat -an | grep :5001
```

### Database Issues (if using SQLite)
```bash
# Check database integrity
sqlite3 security_toolkit.db "PRAGMA integrity_check;"

# Check database size
ls -lh security_toolkit.db

# Check table counts
sqlite3 security_toolkit.db "SELECT name, COUNT(*) FROM sqlite_master WHERE type='table';"
```

### P4 Regression Guardrails Issues
```bash
# Check findings contract compliance
python -m pytest tests/test_findings_normalize.py -v

# Check SSE contract compliance  
python -m pytest tests/test_sse_stream.py -v

# Check contract tests
python -m pytest tests/test_append_and_cache.py -v

# Run pre-commit guards manually
./scripts/pre-commit-guards.sh

# Check for colon detector_ids
jq -r '.[].detector_id' ui_projects/*/findings.json | grep ':' || echo "No colons found ✅"

# Verify schema validation logs
grep -E "SCHEMA_VALIDATION_(OK|FAIL)" logs/app.log | tail -10

# Check findings normalization
python -c "
from utils.findings_normalize import normalize_finding
import json
raw = {'detector_id': 'test:colon', 'title': 'Test', 'severity': 'info', 'method': 'GET', 'url': 'https://example.com/test'}
norm = normalize_finding(raw, pid='test', run_id='test', method='GET', url='https://example.com/test')
print('Normalized detector_id:', norm['detector_id'])
"
```

## Monitoring Commands

### Real-time Monitoring
```bash
# Monitor HTTP requests
tail -f logs/app.log | grep -E "(duration_ms|status=)"

# Monitor cache performance
tail -f logs/cache.log | grep -E "(CACHE_HIT|CACHE_MISS)"

# Monitor SSE streams
tail -f logs/sse.log | grep -E "(stream_started|stream_ended)"

# Monitor Nuclei scans
tail -f logs/nuclei.log | grep -E "(scan_started|scan_completed)"
```

### Metrics Collection (if enabled)
```bash
# Prometheus metrics endpoint
curl http://localhost:5001/api/v1/metrics

# Key metrics to watch
curl -s http://localhost:5001/api/v1/metrics | grep -E "(http_requests_total|cache_hits_total|nuclei_scans_total)"
```

## Backup & Recovery

### Backup Commands
```bash
# Full backup
tar -czf "backup_$(date +%Y%m%d_%H%M%S).tar.gz" ui_projects/ logs/ security_toolkit.db

# Incremental backup (only changes)
rsync -av --link-dest=../last_backup/ ui_projects/ backup_$(date +%Y%m%d)/

# Database backup (if using SQLite)
sqlite3 security_toolkit.db ".backup backup_$(date +%Y%m%d).db"
```

### Recovery Commands
```bash
# Restore from backup
tar -xzf backup_20240115_143022.tar.gz

# Restore database
sqlite3 security_toolkit.db ".restore backup_20240115.db"

# Verify restoration
python -c "from store import list_projects; print(f'Projects: {len(list_projects())}')"
```

## Maintenance Tasks

### Daily Maintenance
```bash
# Clean old log files (older than 30 days)
find logs/ -name "*.log" -mtime +30 -delete

# Clean old cache files
find /tmp -name "nuclei-*" -mtime +7 -delete

# Check disk space
df -h | grep -E "(ui_projects|logs)"
```

### Weekly Maintenance
```bash
# Validate JSON file integrity
find ui_projects -name "*.json" -exec jq '.' {} \; 2>&1 | grep "parse error" | wc -l

# Check for orphaned files
find ui_projects -name "*.json" -exec basename {} \; | sort | uniq -c | sort -nr

# Update Nuclei templates
nuclei -update-templates
```

### Monthly Maintenance
```bash
# Archive old projects (older than 1 year)
find ui_projects -name "*.json" -mtime +365 -exec mv {} archive/ \;

# Database maintenance (if using SQLite)
sqlite3 security_toolkit.db "VACUUM;"

# Security updates
pip list --outdated | grep -E "(flask|requests|nuclei)"
```

## Emergency Procedures

### Service Down
```bash
# 1. Check if process is running
ps aux | grep "python.*app.py"

# 2. Check port availability
netstat -tlnp | grep :5001

# 3. Check logs for errors
tail -100 logs/error.log

# 4. Restart service
sudo systemctl restart security-toolkit
# OR
pkill -f "python.*app.py" && python app.py &
```

### Data Corruption
```bash
# 1. Stop service
sudo systemctl stop security-toolkit

# 2. Restore from latest backup
tar -xzf backup_latest.tar.gz

# 3. Validate data integrity
python tools/validate_data.py

# 4. Restart service
sudo systemctl start security-toolkit
```

### High Memory Usage
```bash
# 1. Check memory usage
ps aux --sort=-%mem | head -10

# 2. Clear cache
python -c "from cache import invalidate_cache; invalidate_cache()"

# 3. Restart service
sudo systemctl restart security-toolkit

# 4. Monitor memory usage
watch -n 5 'ps aux | grep python | grep app.py'
```

## Configuration Files

### Application Config (`app_config.json`)
```json
{
  "cache_ttl": 300,
  "nuclei_templates_dir": "~/.local/share/nuclei/templates",
  "enable_metrics": false,
  "debug_mode": false,
  "max_file_size": 10485760,
  "retention_days": 90
}
```

### Systemd Service (`/etc/systemd/system/security-toolkit.service`)
```ini
[Unit]
Description=Security Toolkit
After=network.target

[Service]
Type=simple
User=security-toolkit
WorkingDirectory=/opt/security-toolkit
ExecStart=/opt/security-toolkit/venv/bin/python app.py
Restart=always
RestartSec=10
Environment=LOG_LEVEL=INFO
Environment=ENABLE_METRICS=true

[Install]
WantedBy=multi-user.target
```

### Nginx Config (`/etc/nginx/sites-available/security-toolkit`)
```nginx
server {
    listen 80;
    server_name security-toolkit.example.com;
    
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /api/v1/metrics {
        allow 127.0.0.1;
        deny all;
        proxy_pass http://127.0.0.1:5001;
    }
}
```
