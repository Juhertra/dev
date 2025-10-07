# Phase 4A Active Scan Fixes

## Overview
This document outlines the fixes needed for active scan functionality, specifically addressing nuclei findings not appearing in vulnerabilities page, CVE placeholder issues, duration calculation problems, and scan detail visibility.

## Issues Summary

### 1. Nuclei Findings Not Appearing in Vulnerabilities Page
- **Root Cause**: Cache invalidation missing after nuclei scans
- **Impact**: Users don't see scan results immediately
- **Priority**: HIGH

### 2. CVE-0000-0000 Placeholder Still Present
- **Root Cause**: No migration of existing data
- **Impact**: Confusing placeholder CVEs in UI
- **Priority**: MEDIUM

### 3. Active Scan Duration Not Counting Time
- **Root Cause**: Missing duration calculation in scan process
- **Impact**: Users can't track scan performance
- **Priority**: MEDIUM

### 4. Active Scan Details Not Clear
- **Root Cause**: Limited progress information in SSE stream
- **Impact**: Users don't understand scan progress
- **Priority**: LOW

## Implementation Plan

### Phase 1: Cache Invalidation Fix (HIGH PRIORITY)

**Files to Modify**:
- `nuclei_integration.py` - Add cache invalidation after `append_findings()`
- `store.py` - Add `invalidate_vulns_cache()` function
- `routes/nuclei.py` - Add cache invalidation call after successful scan

**Implementation**:
```python
# In nuclei_integration.py:530
if converted_findings:
    append_findings(pid, converted_findings)
    # Add cache invalidation
    from store import invalidate_vulns_cache
    invalidate_vulns_cache(pid)
```

### Phase 2: CVE Placeholder Migration (MEDIUM PRIORITY)

**Files to Create/Modify**:
- `scripts/migrate_cve_placeholders.py` - New migration script
- `routes/tools.py` - Add migration endpoint
- `routes/vulns.py` - Simplify CVE filtering logic

**Implementation**:
```python
# Migration script
def migrate_cve_placeholders(pid: str):
    findings = get_findings(pid)
    updated = 0
    for finding in findings:
        if finding.get('cve_id') == 'CVE-0000-0000':
            finding['cve_id'] = None
            updated += 1
    if updated > 0:
        clear_findings(pid)
        append_findings(pid, findings)
    return updated
```

### Phase 3: Duration Calculation Fix (MEDIUM PRIORITY)

**Files to Modify**:
- `nuclei_integration.py` - Add duration tracking
- `routes/nuclei.py` - Update timing logic
- `templates/active_testing.html` - Update duration display

**Implementation**:
```python
# In nuclei_integration.py:271
def scan_project_endpoints(self, pid: str, ...):
    start_time = time.time()
    # ... scan logic ...
    duration_ms = int((time.time() - start_time) * 1000)
    return {
        "success": True,
        "findings_count": len(converted_findings),
        "duration_ms": duration_ms,
        # ... other fields ...
    }
```

### Phase 4: Enhanced Scan Details (LOW PRIORITY)

**Files to Modify**:
- `nuclei_integration.py` - Enhance SSE stream with template info
- `templates/active_testing.html` - Improve progress display
- `routes/nuclei.py` - Add configuration logging

## Testing Checklist

- [ ] Run nuclei scan → verify findings appear immediately in vulnerabilities page
- [ ] Run CVE migration → verify no "CVE-0000-0000" placeholders remain
- [ ] Run scan → verify duration shows actual scan time
- [ ] Run scan → verify detailed progress information is displayed

## Success Criteria

1. **Cache Invalidation**: Nuclei findings appear in vulnerabilities page immediately after scan
2. **CVE Migration**: No placeholder CVEs in existing data
3. **Duration Fix**: Accurate scan duration displayed in UI
4. **Enhanced Details**: Clear progress information during scans

## Risk Assessment

- **Low Risk**: Cache invalidation and duration fixes
- **Medium Risk**: CVE migration (data modification)
- **Low Risk**: Enhanced scan details (UI improvements)

## Rollback Plan

- Cache invalidation: Remove invalidation calls
- CVE migration: Restore from backup if needed
- Duration fix: Revert to previous timing logic
- Enhanced details: Revert to previous progress display
