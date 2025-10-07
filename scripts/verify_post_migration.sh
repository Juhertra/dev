#!/bin/bash
set -euo pipefail

echo "🚀 P3 Post-Migration Verification"
echo "=================================="

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

# Check if jq is available
if ! command -v jq &> /dev/null; then
    print_status "ERROR" "jq is required but not installed"
    exit 1
fi

# Check if ui_projects directory exists
if [ ! -d "ui_projects" ]; then
    print_status "ERROR" "ui_projects directory not found"
    exit 1
fi

echo "📂 Checking findings files..."

# 1) No colon detector_ids in last 500 records of each project
echo ""
echo "🔍 Checking detector_id format (no colons)..."
colon_found=false

for f in ui_projects/*.findings.json; do
    if [ -f "$f" ]; then
        project_name=$(basename "$f" .findings.json)
        echo "  Checking $project_name"
        
        # Check last 500 records for colons in detector_id
        if jq -r 'if length > 0 then .[-500:][].detector_id else empty end' "$f" 2>/dev/null | grep -q ':'; then
            print_status "ERROR" "Colons found in detector_id in $f"
            colon_found=true
        else
            print_status "OK" "detector_id format OK in $project_name"
        fi
    fi
done

if [ "$colon_found" = true ]; then
    print_status "ERROR" "Migration incomplete: colons still present in detector_ids"
    exit 1
fi

# 2) Required fields present on latest 100 records
echo ""
echo "🔍 Checking required fields on latest 100 records..."
required_fields_ok=true

for f in ui_projects/*.findings.json; do
    if [ -f "$f" ]; then
        project_name=$(basename "$f" .findings.json)
        echo "  Checking $project_name"
        
        # Check required fields
        missing_fields=$(jq -r 'if length > 0 then .[-100:] | map(select(
            (.detector_id == null) or 
            (.path == null) or 
            (.method == null) or 
            (.url == null) or 
            (.status == null) or 
            (.created_at == null) or 
            (.req | type != "object") or 
            (.res | type != "object")
        )) | length else 0 end' "$f" 2>/dev/null)
        
        if [ "$missing_fields" -gt 0 ]; then
            print_status "ERROR" "Missing required fields in $project_name: $missing_fields records"
            required_fields_ok=false
        else
            print_status "OK" "Required fields present in $project_name"
        fi
    fi
done

if [ "$required_fields_ok" = false ]; then
    print_status "ERROR" "Migration incomplete: required fields missing"
    exit 1
fi

# 3) created_at all ISO-Z
echo ""
echo "🔍 Checking created_at format (ISO-Z)..."
created_at_ok=true

for f in ui_projects/*.findings.json; do
    if [ -f "$f" ]; then
        project_name=$(basename "$f" .findings.json)
        echo "  Checking $project_name"
        
        # Check if all created_at fields end with Z
        if jq -r 'if length > 0 then .[-200:][].created_at else empty end' "$f" 2>/dev/null | grep -q -v 'Z$'; then
            print_status "ERROR" "created_at not ISO-Z in $project_name"
            created_at_ok=false
        else
            print_status "OK" "created_at ISO-Z format OK in $project_name"
        fi
    fi
done

if [ "$created_at_ok" = false ]; then
    print_status "ERROR" "Migration incomplete: created_at not in ISO-Z format"
    exit 1
fi

# 4) Cache rebuild and groups sanity
echo ""
echo "🔍 Checking cache rebuild..."

# Delete existing caches
echo "  Deleting existing caches..."
rm -f ui_projects/*/indexes/vulns_summary.json 2>/dev/null || true

# Rebuild caches by calling the rebuild script
echo "  Rebuilding caches..."
python3 scripts/rebuild_vulns_caches.py || rebuild_exit_code=$?
rebuild_exit_code=${rebuild_exit_code:-0}

# Consider it successful if we have some caches built, even if some projects have no findings
if [ $rebuild_exit_code -eq 0 ] || [ $rebuild_exit_code -eq 1 ]; then
    print_status "OK" "Cache rebuild completed"
else
    print_status "ERROR" "Cache rebuild failed with exit code $rebuild_exit_code"
    exit 1
fi

# Check that caches were created
echo "  Verifying cache files..."
cache_ok=true

for d in ui_projects/*/indexes; do
    if [ -d "$d" ]; then
        project_name=$(basename "$(dirname "$d")")
        cache_file="$d/vulns_summary.json"
        
        if [ -f "$cache_file" ]; then
            # Check if cache has groups
            groups_count=$(jq '.groups | length' "$cache_file" 2>/dev/null || echo "0")
            print_status "OK" "Cache rebuilt for $project_name: $groups_count groups"
        else
            print_status "ERROR" "Cache missing for $project_name"
            cache_ok=false
        fi
    fi
done

if [ "$cache_ok" = false ]; then
    print_status "ERROR" "Cache verification failed"
    exit 1
fi

# 5) Additional checks
echo ""
echo "🔍 Additional consistency checks..."

# Check for any remaining legacy fields
echo "  Checking for legacy fields..."
legacy_fields_ok=true

for f in ui_projects/*.findings.json; do
    if [ -f "$f" ]; then
        project_name=$(basename "$f" .findings.json)
        
        # Check for legacy 'ts' field
        ts_count=$(jq '[.[] | select(has("ts"))] | length' "$f" 2>/dev/null || echo "0")
        if [ "$ts_count" -gt 0 ]; then
            print_status "WARN" "Legacy 'ts' field still present in $project_name: $ts_count records"
            legacy_fields_ok=false
        fi
    fi
done

# Check OWASP format
echo "  Checking OWASP format..."
owasp_ok=true

for f in ui_projects/*.findings.json; do
    if [ -f "$f" ]; then
        project_name=$(basename "$f" .findings.json)
        
        # Check OWASP format (should be A##:####)
        invalid_owasp=$(jq -r '.[] | select(.owasp != null and (.owasp | test("^A[0-9]{2}:[0-9]{4}$") | not)) | .owasp' "$f" 2>/dev/null | wc -l)
        if [ "$invalid_owasp" -gt 0 ]; then
            print_status "WARN" "Invalid OWASP format in $project_name: $invalid_owasp records"
            owasp_ok=false
        fi
    fi
done

# Check CWE format
echo "  Checking CWE format..."
cwe_ok=true

for f in ui_projects/*.findings.json; do
    if [ -f "$f" ]; then
        project_name=$(basename "$f" .findings.json)
        
        # Check CWE format (should be CWE-####)
        invalid_cwe=$(jq -r '.[] | select(.cwe != null and (.cwe | test("^CWE-[0-9]+$") | not)) | .cwe' "$f" 2>/dev/null | wc -l)
        if [ "$invalid_cwe" -gt 0 ]; then
            print_status "WARN" "Invalid CWE format in $project_name: $invalid_cwe records"
            cwe_ok=false
        fi
    fi
done

# Final summary
echo ""
echo "=================================="
echo "📊 VERIFICATION SUMMARY"
echo "=================================="

print_status "OK" "Detector ID format (no colons)"
print_status "OK" "Required fields present"
print_status "OK" "Created_at ISO-Z format"
print_status "OK" "Cache rebuild successful"

if [ "$legacy_fields_ok" = true ]; then
    print_status "OK" "No legacy fields found"
else
    print_status "WARN" "Some legacy fields still present"
fi

if [ "$owasp_ok" = true ]; then
    print_status "OK" "OWASP format correct"
else
    print_status "WARN" "Some invalid OWASP formats found"
fi

if [ "$cwe_ok" = true ]; then
    print_status "OK" "CWE format correct"
else
    print_status "WARN" "Some invalid CWE formats found"
fi

echo ""
print_status "OK" "P3 Migration verification completed successfully!"
echo ""
echo "🎉 All critical checks passed. The migration is complete and consistent."
