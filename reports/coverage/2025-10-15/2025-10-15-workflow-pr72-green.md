# Workflow — Coverage Snapshot (PR #72)

## Coverage Summary
- **Coverage**: **18%** (M0 baseline met)
- **Statements**: 11,236 total
- **Missed**: 9,234 statements
- **Ratchet**: ✅ **PASS**

## Coverage Command
```bash
coverage run -m pytest -q && coverage report -m
```

## Workflow Engine Package Coverage
- **packages/workflow_engine/__init__.py**: 100% (3 statements)
- **packages/workflow_engine/executor.py**: 88% (24 statements, 3 missed)
- **packages/workflow_engine/validate_recipe.py**: 48% (46 statements, 24 missed)

## Coverage Configuration
```toml
[tool.coverage.run]
source = ["."]  # Fixed from ["secflow"]
omit = [
    "*/migrations/*",
    "*/e2e/*", 
    "*/examples/*",
    "*/tests/*",
    "*/venv/*",
    "*/env/*",
    "*/__pycache__/*"
]
```

## Ratchet Validation
```bash
$ MILESTONE=M0 COVERAGE_PERCENT=18 python scripts/coverage_ratchet.py
Coverage OK: 18% >= 18%
```

## Status
✅ **M0 THRESHOLD MET** - Ready for CI verification

---
**Generated**: 2025-10-15  
**Coverage**: 18% (M0 baseline)  
**Status**: ✅ READY FOR CI