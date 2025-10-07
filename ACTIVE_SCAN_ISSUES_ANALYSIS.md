# Active Scan Issues Analysis

## Issues Identified

### 1. Nuclei Findings Not Appearing in Vulnerabilities Page

**Problem**: After running active scans, nuclei findings are not showing up in the vulnerabilities page despite being stored correctly.

**Root Cause Analysis**:
- ✅ Nuclei findings ARE being stored correctly (verified: 1 nuclei finding exists)
- ✅ Vulnerabilities summary computation works correctly (verified: nuclei finding appears in summary)
- ❌ **ISSUE**: The vulnerabilities page uses cached data (`ui_projects/<pid>/indexes/vulns_summary.json`)
- ❌ **ISSUE**: Cache is not being invalidated after new nuclei scans
- ❌ **ISSUE**: Cache validation may be failing, preventing cache updates

**Files Affected**:
- `routes/vulns.py:25-50` - Cache logic in `vulns_page()`
- `routes/vulns.py:38-50` - Cache validation and fallback logic
- `store.py` - Missing cache invalidation after nuclei scans
- `nuclei_integration.py:530` - `append_findings()` call doesn't trigger cache invalidation

### 2. CVE-0000-0000 Placeholder Still Present

**Problem**: Despite fixing the placeholder CVE logic, existing findings still contain "CVE-0000-0000" values.

**Root Cause Analysis**:
- ✅ New findings correctly use `None` for CVE (verified: nuclei finding has `None`)
- ❌ **ISSUE**: 373 existing findings still have "CVE-0000-0000" placeholder
- ❌ **ISSUE**: No migration/cleanup of existing data
- ❌ **ISSUE**: Vulnerabilities summary computation still filters placeholder but doesn't clean data

**Files Affected**:
- `ui_projects/<pid>.findings.json` - Contains 373 findings with placeholder CVEs
- `routes/vulns.py:174` - Still filters placeholder but doesn't clean source data
- `findings.py:753` - Fixed for new findings but doesn't migrate existing ones

### 3. Active Scan Duration Not Counting Time

**Problem**: Active scan duration shows "00:00:00" instead of actual scan time.

**Root Cause Analysis**:
- ❌ **ISSUE**: No duration calculation in `nuclei_integration.py:scan_project_endpoints()`
- ❌ **ISSUE**: No start/end time tracking in the scan process
- ❌ **ISSUE**: Duration calculation missing from scan result
- ❌ **ISSUE**: Frontend duration counter relies on SSE start time, not actual scan duration

**Files Affected**:
- `nuclei_integration.py:271-578` - Missing duration calculation in `scan_project_endpoints()`
- `routes/nuclei.py:84-85` - Sets same timestamp for start/finish (no duration)
- `templates/active_testing.html:820-832` - Duration counter uses SSE time, not scan time
- `tasks/nuclei.py:87` - Logs duration but doesn't return it properly

### 4. Active Scan Details Not Clear

**Problem**: Users don't understand what's happening during active scans.

**Root Cause Analysis**:
- ❌ **ISSUE**: Limited progress information in SSE stream
- ❌ **ISSUE**: No clear indication of which templates are being used
- ❌ **ISSUE**: No endpoint-by-endpoint progress details
- ❌ **ISSUE**: No clear error reporting if scans fail

**Files Affected**:
- `nuclei_integration.py:607-675` - SSE stream provides minimal progress info
- `templates/active_testing.html:1141-1210` - Limited progress display
- `routes/nuclei.py` - No detailed scan configuration logging

## Solution Plan

### Phase 1: Fix Cache Invalidation (Priority: HIGH)

**Goal**: Ensure nuclei findings appear in vulnerabilities page immediately after scan

**Changes Required**:

1. **Add Cache Invalidation to Nuclei Integration**
   - File: `nuclei_integration.py:530`
   - Add cache invalidation after `append_findings()` call
   - Import and call cache invalidation function

2. **Create Cache Invalidation Function**
   - File: `store.py` (new function)
   - Function: `invalidate_vulns_cache(pid: str)`
   - Remove `ui_projects/<pid>/indexes/vulns_summary.json` if exists

3. **Update Nuclei Routes**
   - File: `routes/nuclei.py:95`
   - Add cache invalidation after successful scan
   - Ensure cache is cleared before saving run document

### Phase 2: Clean Up Existing CVE Placeholders (Priority: MEDIUM)

**Goal**: Remove all "CVE-0000-0000" placeholders from existing findings

**Changes Required**:

1. **Create Migration Script**
   - File: `scripts/migrate_cve_placeholders.py` (new file)
   - Function: `migrate_cve_placeholders(pid: str)`
   - Replace "CVE-0000-0000" with `None` in all findings

2. **Add Migration Endpoint**
   - File: `routes/tools.py` (new endpoint)
   - Route: `POST /p/<pid>/tools/migrate-cve-placeholders`
   - Run migration and return count of updated findings

3. **Update Vulnerabilities Summary**
   - File: `routes/vulns.py:174`
   - Remove placeholder filtering (no longer needed after migration)
   - Simplify CVE logic to just check for truthy values

### Phase 3: Fix Duration Calculation (Priority: MEDIUM)

**Goal**: Show accurate scan duration in active scan interface

**Changes Required**:

1. **Add Duration Tracking to Nuclei Integration**
   - File: `nuclei_integration.py:271`
   - Add `start_time = time.time()` at scan start
   - Calculate `duration_ms = int((time.time() - start_time) * 1000)`
   - Include duration in return result

2. **Update Nuclei Routes**
   - File: `routes/nuclei.py:84-85`
   - Use actual start time from scan process
   - Calculate finish time based on duration
   - Include duration in run document

3. **Update Frontend Duration Display**
   - File: `templates/active_testing.html:820-832`
   - Use scan duration from server response
   - Fall back to SSE duration if scan duration unavailable

### Phase 4: Enhance Scan Details (Priority: LOW)

**Goal**: Provide clear, detailed information about active scans

**Changes Required**:

1. **Enhance SSE Stream**
   - File: `nuclei_integration.py:607-675`
   - Add template information to progress events
   - Include endpoint details in progress updates
   - Add error reporting for failed scans

2. **Improve Progress Display**
   - File: `templates/active_testing.html:1141-1210`
   - Show current template being used
   - Display endpoint being scanned
   - Add error handling and display

3. **Add Scan Configuration Logging**
   - File: `routes/nuclei.py:52-68`
   - Log scan parameters (templates, severity, exclude patterns)
   - Add scan configuration to run document

## Implementation Order

1. **Phase 1** (Cache Invalidation) - Fixes immediate issue with nuclei findings not appearing
2. **Phase 2** (CVE Migration) - Cleans up existing data issues
3. **Phase 3** (Duration Fix) - Improves user experience with accurate timing
4. **Phase 4** (Enhanced Details) - Provides better scan visibility

## Testing Strategy

1. **Cache Invalidation**: Run nuclei scan → verify findings appear immediately in vulnerabilities page
2. **CVE Migration**: Run migration → verify no "CVE-0000-0000" placeholders remain
3. **Duration Fix**: Run scan → verify duration shows actual scan time
4. **Enhanced Details**: Run scan → verify detailed progress information is displayed

## Files to Modify

### High Priority (Phase 1)
- `nuclei_integration.py` - Add cache invalidation
- `store.py` - Add cache invalidation function
- `routes/nuclei.py` - Add cache invalidation call

### Medium Priority (Phase 2)
- `scripts/migrate_cve_placeholders.py` - New migration script
- `routes/tools.py` - Add migration endpoint
- `routes/vulns.py` - Simplify CVE logic

### Medium Priority (Phase 3)
- `nuclei_integration.py` - Add duration tracking
- `routes/nuclei.py` - Update timing logic
- `templates/active_testing.html` - Update duration display

### Low Priority (Phase 4)
- `nuclei_integration.py` - Enhance SSE stream
- `templates/active_testing.html` - Improve progress display
- `routes/nuclei.py` - Add configuration logging
