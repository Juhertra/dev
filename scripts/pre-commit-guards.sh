#!/bin/bash
# P4/P5 - Pre-commit Guards for Findings Contract
# Prevents regressions in the findings contract by checking for:
# 1. Colon detector_ids
# 2. Non-stored SSE finding events
# 3. Schema validation
# 4. Triage status validation (P5)

set -euo pipefail

echo "🔍 P4/P5 Pre-commit Guards - Findings Contract Validation"
echo "========================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    if [ "$status" = "OK" ]; then
        echo -e "${GREEN}✅ $message${NC}"
    elif [ "$status" = "WARN" ]; then
        echo -e "${YELLOW}⚠️  $message${NC}"
    else
        echo -e "${RED}❌ $message${NC}"
    fi
}

# Get list of staged files (or all files if not in git repo)
if git rev-parse --git-dir > /dev/null 2>&1; then
    STAGED_FILES=$(git diff --cached --name-only | grep -E '\.(py|js|html)$' || true)
else
    # Not in git repo, check all relevant files
    STAGED_FILES=$(find . -name "*.py" -o -name "*.js" -o -name "*.html" | head -20 || true)
fi

if [ -z "$STAGED_FILES" ]; then
    print_status "OK" "No relevant files staged for commit"
    exit 0
fi

echo "📂 Checking staged files:"
echo "$STAGED_FILES"
echo ""

# 1) Check for colon detector_ids
echo "🔍 Checking for colon detector_ids..."
colon_found=false

for file in $STAGED_FILES; do
    if [ -f "$file" ]; then
        # Check for colon patterns in detector_id literals or patterns
        if grep -n -E "(detector_id.*:|'[^']*:[^']*'|\"[^\"]*:[^\"]*\")" "$file" | grep -v -E "(nuclei_integration|normalize_finding)" | grep -q ":"; then
            print_status "ERROR" "Colon found in detector_id in $file"
            echo "   This violates the findings contract. Use normalize_finding() to convert colons."
            colon_found=true
        fi
    fi
done

if [ "$colon_found" = true ]; then
    print_status "ERROR" "Pre-commit failed: Colon detector_ids found"
    echo ""
    echo "💡 Fix: Use normalize_finding() to convert detector_ids:"
    echo "   - pattern:name → pattern_name"
    echo "   - nuclei:name → nuclei.name"
    exit 1
fi

print_status "OK" "No colon detector_ids found"

# 2) Check for non-stored SSE finding events
echo ""
echo "🔍 Checking for non-stored SSE finding events..."
non_stored_found=false

for file in $STAGED_FILES; do
    if [ -f "$file" ]; then
        # Check for SSE finding events without stored:true
        if grep -n -A5 -B5 "event: finding" "$file" | grep -q "stored.*false\|stored.*0"; then
            print_status "ERROR" "Non-stored SSE finding event found in $file"
            echo "   This violates the storage contract. SSE finding events must have stored:true"
            non_stored_found=true
        fi
        
        # Check for SSE finding events without stored field
        if grep -n -A10 "event: finding" "$file" | grep -q "event: finding" && ! grep -n -A10 "event: finding" "$file" | grep -q "stored.*true"; then
            print_status "ERROR" "SSE finding event without stored:true found in $file"
            echo "   This violates the storage contract. SSE finding events must have stored:true"
            non_stored_found=true
        fi
    fi
done

if [ "$non_stored_found" = true ]; then
    print_status "ERROR" "Pre-commit failed: Non-stored SSE finding events found"
    echo ""
    echo "💡 Fix: Ensure SSE finding events have stored:true:"
    echo "   event: finding"
    echo "   data: {\"stored\": true, \"detector_id\": \"...\", ...}"
    exit 1
fi

print_status "OK" "All SSE finding events have stored:true"

# 3) Schema validation smoke test
echo ""
echo "🔍 Running schema validation smoke test..."

# Create temp test findings
TEMP_FINDINGS='[
  {
    "detector_id": "test_detector",
    "title": "Test Finding",
    "severity": "info",
    "path": "/test",
    "method": "GET",
    "url": "https://example.com/test",
    "status": "open",
    "created_at": "2025-10-05T19:30:00Z",
    "confidence": 50,
    "req": {"headers": {}, "body": "", "method": "GET", "url": "https://example.com/test"},
    "res": {"headers": {}, "body": "", "status_code": 200}
  },
  {
    "detector_id": "nuclei.test-template",
    "title": "Nuclei Test Finding",
    "severity": "medium",
    "path": "/api/test",
    "method": "POST",
    "url": "https://example.com/api/test",
    "status": "open",
    "created_at": "2025-10-05T19:30:00Z",
    "confidence": 75,
    "req": {"headers": {}, "body": "{}", "method": "POST", "url": "https://example.com/api/test"},
    "res": {"headers": {}, "body": "{}", "status_code": 200}
  }
]'

# Validate against schema
if python3 -c "
import json
import sys
sys.path.insert(0, '.')
from utils.schema_validation import validate_json

try:
    findings = json.loads('$TEMP_FINDINGS')
    if validate_json(findings, 'findings.schema.json', 'findings'):
        print('Schema validation passed')
        sys.exit(0)
    else:
        print('Schema validation failed')
        sys.exit(1)
except Exception as e:
    print(f'Schema validation error: {e}')
    sys.exit(1)
"; then
    print_status "OK" "Schema validation smoke test passed"
else
    print_status "ERROR" "Schema validation smoke test failed"
    echo ""
    echo "💡 Fix: Ensure findings.schema.json is valid and test findings conform to it"
    exit 1
fi

# 4) Check for direct append_findings calls without normalize_finding
echo ""
echo "🔍 Checking for direct append_findings calls without normalize_finding..."
direct_append_found=false

for file in $STAGED_FILES; do
    if [ -f "$file" ]; then
        # Check for append_findings calls that don't use normalize_finding
        if grep -n "append_findings" "$file" | grep -v "normalize_finding" | grep -q "append_findings"; then
            print_status "WARN" "Direct append_findings call found in $file"
            echo "   Consider using normalize_finding() to ensure contract compliance"
            direct_append_found=true
        fi
    fi
done

if [ "$direct_append_found" = true ]; then
    print_status "WARN" "Direct append_findings calls found (not blocking)"
    echo ""
    echo "💡 Recommendation: Use normalize_finding() before append_findings() for contract compliance"
fi

# 5) Check for missing cache bust calls
echo ""
echo "🔍 Checking for missing cache bust calls..."
missing_cache_bust=false

for file in $STAGED_FILES; do
    if [ -f "$file" ]; then
        # Check for append_findings without _bust_vulns_cache
        if grep -n "append_findings" "$file" | grep -q "append_findings" && ! grep -n -A5 -B5 "append_findings" "$file" | grep -q "_bust_vulns_cache"; then
            print_status "WARN" "append_findings without cache bust found in $file"
            echo "   Consider calling _bust_vulns_cache() after append_findings()"
            missing_cache_bust=true
        fi
    fi
done

if [ "$missing_cache_bust" = true ]; then
    print_status "WARN" "Missing cache bust calls found (not blocking)"
    echo ""
    echo "💡 Recommendation: Call _bust_vulns_cache() after append_findings() for cache consistency"
fi

# 6) Triage status validation (P5)
echo ""
echo "🔍 Checking triage status validation..."

# Check for invalid triage status values
invalid_triage_found=false

for file in $STAGED_FILES; do
    if [ -f "$file" ]; then
        # Check for invalid triage status values in code
        if grep -n -E "(triage.*status.*:|status.*=.*['\"])" "$file" | grep -v -E "(open|in_progress|risk_accepted|false_positive|resolved)" | grep -q -E "(status.*=.*['\"])"; then
            print_status "ERROR" "Invalid triage status found in $file"
            echo "   Valid statuses: open, in_progress, risk_accepted, false_positive, resolved"
            invalid_triage_found=true
        fi
        
        # Check for triage status enum violations in string literals
        if grep -n -E "['\"](new|pending|closed|fixed|duplicate|wontfix)['\"]" "$file" | grep -q -E "(status|triage)"; then
            print_status "ERROR" "Invalid triage status enum value found in $file"
            echo "   Valid statuses: open, in_progress, risk_accepted, false_positive, resolved"
            invalid_triage_found=true
        fi
    fi
done

if [ "$invalid_triage_found" = true ]; then
    print_status "ERROR" "Pre-commit failed: Invalid triage status found"
    echo ""
    echo "💡 Fix: Use valid triage status values:"
    echo "   - open"
    echo "   - in_progress"
    echo "   - risk_accepted"
    echo "   - false_positive"
    echo "   - resolved"
    exit 1
fi

print_status "OK" "Triage status validation passed"

# Final summary
echo ""
echo "======================================================"
print_status "OK" "Pre-commit guards passed successfully!"
echo ""
echo "🎉 All findings contract validations passed."
echo "   Your changes maintain contract compliance."
echo "   ✅ Colon detector_ids checked"
echo "   ✅ SSE storage contract verified"
echo "   ✅ Schema validation verified"
echo "   ✅ Triage status validation verified"
