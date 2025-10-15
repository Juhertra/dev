# Workflow — Coverage Snapshot (PR #72 - Locked Exports)

## Coverage Summary
- **Coverage**: **18%** (M0 baseline met)
- **Statements**: 11,236 total
- **Missed**: 9,234 statements
- **Ratchet**: ✅ **PASS**

## Coverage Command
```bash
coverage run -m pytest -q && coverage report -m
```

## Workflow Engine Package Coverage (Locked Exports)
- **packages/workflow_engine/__init__.py**: 100% (3 statements) ✅
- **packages/workflow_engine/executor.py**: 88% (24 statements, 3 missed) ✅
- **packages/workflow_engine/validate_recipe.py**: 48% (46 statements, 24 missed) ✅

## Locked Exports Configuration
```python
# packages/workflow_engine/__init__.py
from .executor import WorkflowExecutor
from .validate_recipe import RecipeValidator
__all__ = ["WorkflowExecutor", "RecipeValidator"]
```

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

## Sanity Commands Results
```bash
# Workflow Tests
$ pytest -q tests/workflow
........                                                                 [100%]
8 passed in 0.07s

# Contract Tests  
$ pytest -q tests/contracts
....Xsssssss......X...........                                           [100%]
21 passed, 7 skipped, 2 xpassed in 0.12s

# Coverage Collection
$ coverage run -m pytest -q && coverage report -m
126 passed, 8 skipped, 2 xpassed in 3.12s
TOTAL                                           11236   9234    18%
```

## Status
✅ **M0 THRESHOLD MET WITH LOCKED EXPORTS** - Ready for CI verification

**Exports locked to match CI layout - green state preserved**

---
**Generated**: 2025-10-15  
**Coverage**: 18% (M0 baseline)  
**Status**: ✅ GREEN AND LOCKED