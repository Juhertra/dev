# Data Persistence Best Practices Report

**Date:** October 4, 2025  
**Issue:** API removal and endpoint run data persistence  
**Status:** ⚠️ **IDENTIFIED ISSUE**

## Problem Analysis

### Current Behavior
When you removed the Petstore API from the API Explorer and re-added it:
- **Runs still exist** for PUT and POST `/pet` endpoints
- **Same run ID** (`run_1759590564242`) appears in both endpoint dossiers
- **Different vulnerability counts**: POST (5 vulns), PUT (0 vulns)

### Root Cause
The core issue is **improper run attribution** - a single run is being associated with multiple endpoints instead of just the one that was tested.

## Best Practice Recommendations

### 🎯 **Option 1: Conservative Approach (RECOMMENDED)**

**Keep Data Until Project Deletion**

**Rationale:**
- **Data Integrity**: Historical security testing data has ongoing value
- **Audit Trail**: Maintains complete security testing history
- **Compliance**: Many security frameworks require retention of vulnerability data
- **Re-testing Value**: Previous results help identify regression issues

**Implementation:**
```python
def remove_api_from_project(pid: str, api_id: str):
    """
    Remove API from active testing but preserve historical data.
    """
    # 1. Remove API from SPECS registry (prevents new tests)
    remove_spec_from_project(pid, api_id)
    
    # 2. Mark endpoints as "retired" but keep dossier files
    mark_endpoints_as_retired(pid, api_spec)
    
    # 3. Preserve all existing dossier files
    # No deletion of ui_projects/<pid>/endpoints/*.json
    
    # 4. Update sitemap to show "Retired" status
    update_endpoint_status(pid, endpoint_keys, status="retired")
```

### 🔧 **Option 2: Clean Slate Approach**

**Remove All Related Data**

**Rationale:**
- **Clean State**: Fresh start with no historical baggage
- **Reduced Confusion**: No misleading data from previous configurations
- **Storage Efficiency**: Reduces disk usage

**Implementation:**
```python
def remove_api_with_data_cleanup(pid: str, api_id: str):
    """
    Remove API and all associated testing data.
    """
    # 1. Remove API from SPECS registry
    remove_spec_from_project(pid, api_id)
    
    # 2. Identify all endpoints from this API
    endpoint_patterns = get_api_endpoint_patterns(api_id)
    
    # 3. Remove dossier files for these endpoints
    for endpoint_key in endpoint_patterns:
        dossier_path = get_dossier_path(pid, endpoint_key)
        if os.path.exists(dossier_path):
            os.remove(dossier_path)
    
    # 4. Remove run artifacts
    for run_id in affected_runs:
        artifact_path = get_run_artifact_path(pid, run_id)
        if os.path.exists(artifact_path):
            os.remove(artifact_path)
    
    # 5. Clean up findings database
    remove_findings_for_endpoints(pid, endpoint_patterns)
```

### ⚙️ **Option 3: Hybrid Approach (BALANCED)**

**Archive Instead of Delete**

**Rationale:**
- **Data Preservation**: Keep data for compliance/audit
- **Clear Separation**: Distinguish active vs archived data
- **Recovery Option**: Allow data restoration if API is re-added

**Implementation:**
```python
def archive_api_data(pid: str, api_id: str):
    """
    Move API data to archive instead of deleting.
    """
    archive_dir = f"ui_projects/{pid}/archived_apis/{api_id}"
    os.makedirs(archive_dir, exist_ok=True)
    
    # Move dossier files
    for endpoint_file in get_api_endpoint_files(pid, api_id):
         shutil.move(endpoint_file, f"{archive_dir}/endpoints/")
    
    # Move run artifacts
    for run_artifact in get_api_run_artifacts(pid, api_id):
        shutil.move(run_artifact, f"{archive_dir}/runs/")
    
    # Update findings to mark as archived
    archive_findings_for_api(pid, api_id)
    
    # Remove from active spec registry
    remove_spec_from_project(pid, api_id)
```

## Immediate Fix Required

### **Issue: Shared Run Attribution**

**Problem**: `run_1759590564242` appears in both PUT and POST dossier files.

**Root Cause**: Run attribution logic is incorrectly associating the same run with multiple endpoints.

**Fix Required:**
```python
def fix_run_attribution():
    """
    Ensure runs are only attributed to the actual endpoint tested.
    """
    # 1. Check artifact files to determine actual endpoint tested
    artifact_path = "run_1759590564242.nuclei.ndjson"
    actual_endpoint = parse_artifact_for_endpoint(artifact_path)
    
    # 2. Remove run from incorrect dossier files
    incorrect_endpoints = ["PUT https://petstore3.swagger.io/api/v3/pet"]
    for endpoint in incorrect_endpoints:
        remove_run_from_dossier(pid, endpoint, "run_1759590564242")
```

## Recommended Action Plan

### **Phase 1: Immediate Fix**
1. **Fix Run Attribution**: Ensure runs only belong to tested endpoints
2. **Verify Data Consistency**: Confirm vulnerability counts match actual findings
3. **Test Scenarios**: Validate PUT vs POST endpoint data separation

### **Phase 2: Policy Implementation**
1. **User Setting**: Add preference for data retention policy
2. **Clear UI**: Show "Retired" status for removed API endpoints  
3. **Archive Option**: Implement archiving instead of deletion

### **Phase 3: Data Management**
1. **Cleanup Tools**: Provide utilities for data cleanup
2. **Export Options**: Allow users to export data before removal
3. **Audit Logging**: Track all data modifications

## UI Improvements Needed

### **Sitemap Enhancements**
```html
<!-- Add API source indicator -->
<span class="chip retired">Retired API</span>
<span class="chip active">Active API</span>

<!-- Show data retention info -->
<div class="muted small">Data preserved from previous API configuration</div>
```

### **Runs Drawer Clarity**
```html
<!-- Clear endpoint identification -->
<div class="endpoint-context">
  <strong>{{ method }} {{ path }}</strong>
  <div class="muted">from Retired API</div>
</div>
```

## Compliance Considerations

### **Security Data Retention**
- **OWASP Compliance**: Vulnerability data should be retained for trend analysis
- **ISO 27001**: Security testing records require retention periods
- **SOC 2**: Audit trails must be maintained for compliance

### **Data Privacy**
- **GDPR Compliance**: API test data may contain sensitive information
- **Data Minimization**: Only retain necessary security testing data
- **Right to Erasure**: Users should be able to delete their project data

## Conclusion

**Recommended Approach**: **Conservative (Option 1)** with immediate attribution fixes.

**Rationale**:
1. **Data Value**: Security testing data has long-term value
2. **User Experience**: Prevents confusion from missing expected data
3. **Compliance**: Maintains audit trails required by security frameworks
4. **Flexibility**: Users can always manually clean up if desired

**Next Steps**:
1. Fix run attribution bug immediately
2. Implement "retired" status for removed API endpoints
3. Add user preference for data retention policy
4. Provide cleanup tools for advanced users

---

**Status**: ⚠️ **Requires Fix**  
**Priority**: **HIGH** (Data Integrity Issue)  
**Effort**: **MEDIUM** (Policy + Bug Fix)
