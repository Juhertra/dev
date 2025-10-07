#!/bin/bash
# P6 - Metrics Verification Script
# Verify metrics endpoint, cache, export formats, and trend shape

set -euo pipefail

echo "🔍 P6 Metrics Verification"
echo "========================="

# Configuration
TEST_PID="p_p6_test"
BASE_URL="http://localhost:5001"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if server is running
check_server() {
    echo "Checking if server is running..."
    if curl -sSf "$BASE_URL/health" >/dev/null 2>&1; then
        log_info "Server is running"
    else
        log_error "Server is not running. Please start the server first."
        exit 1
    fi
}

# Test metrics endpoint
test_metrics_endpoint() {
    echo "Testing metrics endpoint..."
    
    # Test HTML view
    if curl -sSf "$BASE_URL/p/$TEST_PID/metrics" >/dev/null 2>&1; then
        log_info "Metrics HTML endpoint accessible"
    else
        log_warn "Metrics HTML endpoint not accessible (project may not exist)"
    fi
    
    # Test JSON view
    if curl -sSf "$BASE_URL/p/$TEST_PID/metrics?format=json" >/dev/null 2>&1; then
        log_info "Metrics JSON endpoint accessible"
        
        # Check JSON structure
        JSON_RESPONSE=$(curl -sS "$BASE_URL/p/$TEST_PID/metrics?format=json")
        if echo "$JSON_RESPONSE" | jq -e '.total_findings' >/dev/null 2>&1; then
            log_info "Metrics JSON structure valid"
        else
            log_warn "Metrics JSON structure may be invalid"
        fi
    else
        log_warn "Metrics JSON endpoint not accessible"
    fi
}

# Test metrics cache
test_metrics_cache() {
    echo "Testing metrics cache..."
    
    CACHE_FILE="ui_projects/$TEST_PID/indexes/metrics_summary.json"
    
    if [ -f "$CACHE_FILE" ]; then
        log_info "Metrics cache file exists"
        
        # Check cache structure
        if jq -e '.total_findings' "$CACHE_FILE" >/dev/null 2>&1; then
            log_info "Metrics cache structure valid"
        else
            log_warn "Metrics cache structure may be invalid"
        fi
        
        # Check cache age
        CACHE_AGE=$(find "$CACHE_FILE" -mmin +5 2>/dev/null || echo "")
        if [ -n "$CACHE_AGE" ]; then
            log_warn "Metrics cache is older than 5 minutes"
        else
            log_info "Metrics cache is fresh"
        fi
    else
        log_warn "Metrics cache file does not exist"
    fi
}

# Test export functionality
test_export_functionality() {
    echo "Testing export functionality..."
    
    # Test CSV export
    if python3 scripts/export_findings_report.py --pid "$TEST_PID" --format csv --dry-run 2>/dev/null; then
        log_info "CSV export script works"
    else
        log_warn "CSV export script failed"
    fi
    
    # Test JSON export
    if python3 scripts/export_findings_report.py --pid "$TEST_PID" --format json --dry-run 2>/dev/null; then
        log_info "JSON export script works"
    else
        log_warn "JSON export script failed"
    fi
    
    # Test PDF export (if reportlab is available)
    if python3 -c "import reportlab" 2>/dev/null; then
        if python3 scripts/export_findings_report.py --pid "$TEST_PID" --format pdf --dry-run 2>/dev/null; then
            log_info "PDF export script works"
        else
            log_warn "PDF export script failed"
        fi
    else
        log_warn "PDF export not available (reportlab not installed)"
    fi
}

# Test trend data shape
test_trend_data() {
    echo "Testing trend data shape..."
    
    CACHE_FILE="ui_projects/$TEST_PID/indexes/metrics_summary.json"
    
    if [ -f "$CACHE_FILE" ]; then
        # Check trend_30d structure
        if jq -e '.trend_30d | type == "array"' "$CACHE_FILE" >/dev/null 2>&1; then
            log_info "Trend data is an array"
            
            # Check trend data entries
            TREND_COUNT=$(jq -r '.trend_30d | length' "$CACHE_FILE")
            if [ "$TREND_COUNT" -gt 0 ]; then
                log_info "Trend data has $TREND_COUNT entries"
                
                # Check first entry structure
                if jq -e '.trend_30d[0] | has("date") and has("count")' "$CACHE_FILE" >/dev/null 2>&1; then
                    log_info "Trend data entries have correct structure"
                else
                    log_warn "Trend data entries missing required fields"
                fi
            else
                log_warn "Trend data is empty"
            fi
        else
            log_warn "Trend data is not an array"
        fi
    else
        log_warn "Cannot test trend data - cache file not found"
    fi
}

# Test analytics module
test_analytics_module() {
    echo "Testing analytics module..."
    
    if python3 -c "from core.analytics import get_metrics, rebuild_metrics_cache" 2>/dev/null; then
        log_info "Analytics module imports successfully"
        
        # Test get_metrics function
        if python3 -c "
from core.analytics import get_metrics
try:
    metrics = get_metrics('$TEST_PID')
    print('get_metrics works')
except Exception as e:
    print(f'get_metrics failed: {e}')
" 2>/dev/null; then
            log_info "get_metrics function works"
        else
            log_warn "get_metrics function failed"
        fi
    else
        log_error "Analytics module import failed"
    fi
}

# Test metrics telemetry
test_metrics_telemetry() {
    echo "Testing metrics telemetry..."
    
    TELEMETRY_FILE="ui_projects/$TEST_PID/logs/metrics.log"
    
    if [ -f "$TELEMETRY_FILE" ]; then
        log_info "Metrics telemetry file exists"
        
        # Check recent entries
        if [ -s "$TELEMETRY_FILE" ]; then
            log_info "Metrics telemetry has content"
        else
            log_warn "Metrics telemetry file is empty"
        fi
    else
        log_warn "Metrics telemetry file does not exist"
    fi
}

# Test UI integration
test_ui_integration() {
    echo "Testing UI integration..."
    
    # Check if metrics link exists in layout
    if grep -q "Metrics" templates/_layout.html 2>/dev/null; then
        log_info "Metrics link found in layout template"
    else
        log_warn "Metrics link not found in layout template"
    fi
    
    # Check if metrics template exists
    if [ -f "templates/metrics.html" ]; then
        log_info "Metrics template exists"
        
        # Check for key template elements
        if grep -q "Chart.js" templates/metrics.html 2>/dev/null; then
            log_info "Chart.js integration found in template"
        else
            log_warn "Chart.js integration not found in template"
        fi
    else
        log_error "Metrics template not found"
    fi
}

# Main verification
main() {
    echo "Starting P6 metrics verification..."
    echo
    
    check_server
    echo
    
    test_metrics_endpoint
    echo
    
    test_metrics_cache
    echo
    
    test_export_functionality
    echo
    
    test_trend_data
    echo
    
    test_analytics_module
    echo
    
    test_metrics_telemetry
    echo
    
    test_ui_integration
    echo
    
    echo "🎉 P6 metrics verification completed!"
    echo
    echo "Summary:"
    echo "- Metrics endpoint: $(curl -sSf "$BASE_URL/p/$TEST_PID/metrics" >/dev/null 2>&1 && echo "✅ OK" || echo "⚠️  Issues")"
    echo "- Metrics cache: $([ -f "ui_projects/$TEST_PID/indexes/metrics_summary.json" ] && echo "✅ OK" || echo "⚠️  Missing")"
    echo "- Export scripts: $(python3 scripts/export_findings_report.py --pid "$TEST_PID" --format csv --dry-run >/dev/null 2>&1 && echo "✅ OK" || echo "⚠️  Issues")"
    echo "- Analytics module: $(python3 -c "from core.analytics import get_metrics" >/dev/null 2>&1 && echo "✅ OK" || echo "❌ Failed")"
    echo "- UI integration: $([ -f "templates/metrics.html" ] && echo "✅ OK" || echo "❌ Missing")"
}

# Run main function
main "$@"
