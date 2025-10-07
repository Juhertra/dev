# Migration Runbook

This runbook provides step-by-step instructions for running the P3 historical migration and P4 regression guardrails.

## Overview

The migration process normalizes all existing findings to the new schema/contract, rebuilds caches, and ensures full consistency across the system.

## Prerequisites

- Python 3.9+
- `jq` command-line JSON processor
- Write access to `ui_projects/` directory
- Backup storage space (recommended: 2x current data size)

## Pre-Migration Checklist

- [ ] **Backup entire `ui_projects/` directory**
- [ ] **Verify disk space** (at least 2x current data size)
- [ ] **Stop active scans** to prevent data corruption
- [ ] **Notify users** of maintenance window
- [ ] **Test scripts** on a small subset first

## Migration Steps

### Step 1: Dry Run (Required)

Always run a dry run first to understand the scope and impact:

```bash
# Test migration on first 10 findings per project
python3 scripts/migrate_legacy_findings.py --dry-run --limit 10

# Test backfill on all projects
python3 scripts/backfill_run_info.py --dry-run

# Test cache rebuild
python3 scripts/rebuild_vulns_caches.py --pid test_project
```

**Expected Output:**
- Migration stats (total, migrated, dropped, duplicates)
- No files modified (dry run)
- No errors or exceptions

**If Issues Found:**
- Review error messages
- Fix data issues before proceeding
- Consider running on smaller subset first

### Step 2: Full Migration

Once dry run is successful, run the full migration:

```bash
# Migrate all findings with automatic backups
python3 scripts/migrate_legacy_findings.py --backup

# Backfill missing Nuclei run info
python3 scripts/backfill_run_info.py

# Rebuild all caches
python3 scripts/rebuild_vulns_caches.py
```

**Expected Output:**
- Backup files created (`.bak.<timestamp>.json`)
- Migration stats showing successful processing
- Cache files rebuilt
- No critical errors

**Monitor For:**
- Disk space usage
- Processing time (may take several minutes for large datasets)
- Error logs

### Step 3: Verification

Run comprehensive verification to ensure migration success:

```bash
# Run full verification suite
./scripts/verify_post_migration.sh
```

**Expected Output:**
- ✅ All checks pass
- No colon detector_ids found
- All required fields present
- Created_at in ISO-Z format
- Cache rebuild successful

**If Verification Fails:**
- Review error messages
- Check specific failing projects
- Consider rollback if critical issues found

### Step 4: Post-Migration Testing

Test the system to ensure everything works correctly:

```bash
# Run test suite
python -m pytest tests/ -v

# Test pre-commit guards
./scripts/pre-commit-guards.sh

# Test a small active scan
# (Use UI to run a quick scan on a test project)
```

## Rollback Procedures

### Automatic Rollback (Recommended)

If migration fails or verification shows issues:

```bash
# Restore from backups
for backup_file in ui_projects/*.findings.bak.*.json; do
    original_file="${backup_file%.bak.*.json}.findings.json"
    mv "$backup_file" "$original_file"
    echo "Restored $original_file"
done

# Rebuild caches from restored data
python3 scripts/rebuild_vulns_caches.py
```

### Manual Rollback

If automatic rollback fails:

1. **Stop the application**
2. **Restore entire `ui_projects/` directory** from pre-migration backup
3. **Restart the application**
4. **Verify system functionality**

## Troubleshooting

### Common Issues

#### Migration Script Fails
```bash
# Check for specific error
python3 scripts/migrate_legacy_findings.py --dry-run --limit 1

# Check file permissions
ls -la ui_projects/

# Check disk space
df -h
```

#### Schema Validation Errors
```bash
# Check specific finding format
jq '.[0]' ui_projects/problem_project.findings.json

# Validate against schema manually
python3 -c "
import json
from utils.schema_validation import validate_json
with open('ui_projects/problem_project.findings.json') as f:
    findings = json.load(f)
validate_json(findings, 'findings.schema.json', 'findings')
"
```

#### Cache Rebuild Fails
```bash
# Check specific project
python3 scripts/rebuild_vulns_caches.py --pid problem_project

# Check findings file exists
ls ui_projects/problem_project.findings.json

# Check findings file is valid JSON
jq '.' ui_projects/problem_project.findings.json > /dev/null
```

#### Verification Script Fails
```bash
# Run individual checks
jq -r '.[-5:][].detector_id' ui_projects/problem_project.findings.json | grep ':'

jq '.[-5:] | map({detector_id, path, created_at})' ui_projects/problem_project.findings.json
```

### Performance Issues

#### Large Datasets
- **Use `--limit` parameter** to process in batches
- **Monitor memory usage** during migration
- **Consider running during off-peak hours**

#### Slow Cache Rebuild
- **Check for corrupted findings files**
- **Verify disk I/O performance**
- **Consider rebuilding caches individually**

## Monitoring and Alerts

### Key Metrics to Monitor

1. **Migration Progress**
   - Files processed vs. total
   - Findings migrated vs. total
   - Duplicates removed

2. **System Health**
   - Disk space usage
   - Memory usage
   - Error rates

3. **Data Integrity**
   - Schema validation success rate
   - Cache rebuild success rate
   - Verification check results

### Alert Thresholds

- **Migration failure rate > 5%**
- **Disk space < 20% free**
- **Memory usage > 80%**
- **Verification failures**

## Post-Migration Tasks

### Immediate (Within 1 hour)

- [ ] **Verify application functionality**
- [ ] **Test active scanning**
- [ ] **Check vulnerability pages**
- [ ] **Monitor error logs**

### Short-term (Within 24 hours)

- [ ] **Monitor system performance**
- [ ] **Check user feedback**
- [ ] **Review error logs**
- [ ] **Update documentation**

### Long-term (Within 1 week)

- [ ] **Performance analysis**
- [ ] **User training if needed**
- [ ] **Document lessons learned**
- [ ] **Plan future migrations**

## Emergency Contacts

- **System Administrator**: [Contact Info]
- **Database Administrator**: [Contact Info]
- **Development Team Lead**: [Contact Info]

## Appendix

### File Locations

- **Migration Scripts**: `scripts/`
- **Test Suite**: `tests/`
- **Findings Data**: `ui_projects/*/findings.json`
- **Cache Files**: `ui_projects/*/indexes/vulns_summary.json`
- **Backup Files**: `ui_projects/*.findings.bak.<timestamp>.json`

### Useful Commands

```bash
# Check migration status
grep -r "SCHEMA_VALIDATION" logs/ | tail -20

# Monitor disk usage
watch -n 5 'df -h | grep ui_projects'

# Check findings count
find ui_projects -name "*.findings.json" -exec jq 'length' {} \; | awk '{sum+=$1} END {print "Total findings:", sum}'

# Verify no colons
find ui_projects -name "*.findings.json" -exec jq -r '.[].detector_id' {} \; | grep ':' | wc -l
```

### Recovery Commands

```bash
# Quick system check
./scripts/verify_post_migration.sh

# Rebuild specific project cache
python3 scripts/rebuild_vulns_caches.py --pid project_id

# Validate specific findings file
python3 -c "
import json
from utils.schema_validation import validate_json
with open('ui_projects/project_id.findings.json') as f:
    findings = json.load(f)
print('Valid:', validate_json(findings, 'findings.schema.json', 'findings'))
"
```
