# M0-D6 Critical Issues Action Plan

## 🚨 **Critical Issues Blocking M0-D6 Completion**

Based on analysis of [GitHub Issues](https://github.com/Juhertra/dev), the following issues must be resolved for M0-D6 readiness:

### **Issue #74: jsonschema dependency missing in manifest validation**
**Priority**: CRITICAL  
**Impact**: Contract tests failing  
**Blocks**: #45 (DevEx stabilization)

#### **Root Cause**
```python
# packages/wrappers/manifest.py:166
jsonschema.validate(manifest_data, self.schema)
# NameError: name 'jsonschema' is not defined
```

#### **Fix Required**
```python
# Add missing import at top of packages/wrappers/manifest.py
import jsonschema
```

#### **Verification**
```bash
pytest -q tests/contracts/test_parser_contracts.py::test_manifest_validation
```

---

### **Issue #62: import-linter command not found in CI**
**Priority**: CRITICAL  
**Impact**: Import linting step fails  
**Blocks**: #45 (DevEx stabilization)

#### **Root Cause**
```bash
# CI Error
/home/runner/work/_temp/8b05e6ea-f9f5-47cb-b41a-ea3f2bf3ae01.sh: line 1: import-linter: command not found
```

#### **Fix Required**
Verify all workflows use standardized installation:
```yaml
- name: Install dev deps
  run: |
    python -m pip install --upgrade pip
    pip install -e ".[dev]"
```

#### **Verification**
```bash
# Check imports workflow
gh workflow run imports.yml
```

---

### **Issue #61: Flask dependency missing in CI environment**
**Priority**: CRITICAL  
**Impact**: Multiple test files failing  
**Blocks**: #45 (DevEx stabilization)

#### **Root Cause**
```python
# Multiple test files
from flask import Blueprint
# ModuleNotFoundError: No module named 'flask'
```

#### **Affected Tests**
- tests/test_bulk_triage.py
- tests/test_triage_routes.py  
- tests/test_vulns_summary_triage.py
- tests/test_append_and_cache.py

#### **Fix Required**
Ensure Flask is in dev dependencies (already present in pyproject.toml):
```toml
[tool.poetry.group.dev.dependencies]
flask = "^3.0.0"  # Already present
```

#### **Verification**
```bash
pytest -q tests/test_bulk_triage.py tests/test_triage_routes.py
```

## 🎯 **Implementation Plan**

### **Step 1: Fix jsonschema Import (5 minutes)**
```bash
# Add import to packages/wrappers/manifest.py
echo "import jsonschema" >> packages/wrappers/manifest.py
```

### **Step 2: Verify CI Dependencies (10 minutes)**
```bash
# Check all workflows have standardized installation
grep -r "pip install -e" .github/workflows/
```

### **Step 3: Test All Fixes (15 minutes)**
```bash
# Run full test suite
make lint && make type && make imports && pytest -q
```

### **Step 4: CI Validation (20 minutes)**
```bash
# Trigger CI runs for all workflows
gh workflow run ruff.yml
gh workflow run pyright.yml
gh workflow run imports.yml
gh workflow run unit.yml
gh workflow run coverage.yml
gh workflow run contracts.yml
gh workflow run docs-health.yml
```

## 📊 **Success Criteria**

### **All Issues Resolved When:**
1. ✅ `pytest tests/contracts` passes without jsonschema errors
2. ✅ `import-linter` runs successfully in CI
3. ✅ All Flask-dependent tests pass in CI
4. ✅ All 7 CI workflows show SUCCESS status
5. ✅ Coverage remains at 18% (M0 threshold)

### **M0-D6 Ready When:**
- **CI Health**: 100% (7/7 checks passing)
- **Test Suite**: 100% (all tests passing)
- **Dependencies**: 100% (all required packages available)
- **Coverage**: 18% (M0 baseline maintained)

## 🚀 **Expected Timeline**

- **Fix Implementation**: 30 minutes
- **CI Validation**: 20 minutes  
- **Total Time**: 50 minutes
- **M0-D6 Completion**: Same day

## 📋 **Post-Fix Actions**

1. **Close Issues**: #74, #62, #61
2. **Update Status**: Mark #45 as resolved
3. **Document**: Update M0-D6 completion report
4. **Celebrate**: 🎉 M0-D6 DevEx mission accomplished!
