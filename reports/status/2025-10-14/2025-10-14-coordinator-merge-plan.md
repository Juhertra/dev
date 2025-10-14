# Coordinator Merge Plan - 2025-10-14

**Generated**: $(date -u +%F) (UTC)  
**Coordinator**: Merge Train & Linkage  
**Source-of-Truth**: reports/status/2025-10-14-*, DevEx/DevOps reports

---

## Merge Train Status

### 🚂 **Merge Order Enforced**
1. **#71** (DevEx CI) → **#72** (Workflow unskip) → **#73** (Tools N-1) → **#68** (Runtime StoragePort) → **#67** (Python pin)

### 🚨 **Current Status: STOPPED**
- **Position**: #71 (first in train)
- **Status**: 🔴 RED - All gates failing
- **Owner**: @devex-lead
- **Action**: Fix failing checks before proceeding

---

## PRs Merged

### ✅ **None Merged**
- **Reason**: Merge train stopped at first PR due to failing gates
- **Status**: Waiting for @devex-lead to fix PR #71

---

## PRs Still Open

### 🚂 **Merge Train PRs**
1. **#71** - feat(devex): close CI gaps per Source-of-Truth
   - **Status**: 🔴 RED (all gates failing)
   - **Owner**: @devex-lead
   - **Blocker**: ruff, pyright, imports, unit, coverage, contracts, docs-health all failing
   - **ETA**: Unknown (depends on @devex-lead)

2. **#72** - fix(workflow): make scaffold importable to unskip tests
   - **Status**: ⏸️ FROZEN (waiting on #71)
   - **Owner**: @workflow-lead
   - **Dependencies**: #71 must merge first
   - **ETA**: After #71 merges

3. **#73** - feat: Add N-1 golden samples for Nuclei, Feroxbuster, Katana
   - **Status**: ⏸️ FROZEN (waiting on #71, #72)
   - **Owner**: @tools-lead
   - **Dependencies**: #71, #72 must merge first
   - **ETA**: After #71, #72 merge

4. **#68** - feat(runtime): implement StoragePort interface + finding schema v1.0.0
   - **Status**: ⏸️ FROZEN (waiting on #71)
   - **Owner**: @runtime-lead
   - **Dependencies**: #71 must merge first
   - **ETA**: After #71 merges

5. **#67** - chore(devex): fix Python version to 3.11.9 for pytest compatibility
   - **Status**: ⏸️ FROZEN (waiting on #71)
   - **Owner**: @devex-lead
   - **Dependencies**: #71 must merge first
   - **ETA**: After #71 merges

### 🔒 **Frozen PRs (Not in Train)**
6. **#75** - devops(ci): pin Python 3.11.9 and add pip caching
7. **#70** - devops(ci): lock Python 3.11.9 + enforce MIN_COV=18 for M0
8. **#69** - devops(ci): lock Python 3.11.9 + add coverage measurement with M0 baseline ratchet
9. **#66** - feat(workflow): add validation tools, sample recipe, and comprehensive tests
10. **#65** - feat(runtime): scaffold workspace packages + import architecture contracts
11. **#64** - devops(ci): enforce job order & caches; ensure nightly EOD workflow exists
12. **#60** - chore(observability): logging/metrics stubs + perf-budget placeholder script
13. **#58** - docs: link governance from start-here; prep api docs area
14. **#57** - docs: fix mermaid parity (fences/tables) and restrict health scan to docs/
15. **#54** - feat(workflow): linear v1 scaffolds (executor/validate_recipe stubs + recipes dir)
16. **#50** - feat(devex): add PR FEAT link check workflow
17. **#47** - chore(devex): stabilize ruff (E/F/I) and pyright (basic) for M0
18. **#44** - chore(devex): fix unit infra + baseline coverage
19. **#43** - devex(governance): add CODEOWNERS + PR template; verify CI order
20. **#42** - M0-D2-DEVEX-001: Stabilize test toolchain & CI signals
21. **#1** - Test: Branch Protection Validation

---

## Blockers

### 🔴 **Critical Blockers**
1. **PR #71 All Gates Failing** → @devex-lead
   - **Issue**: ruff, pyright, imports, unit, coverage, contracts, docs-health all failing
   - **Impact**: Blocks entire merge train
   - **Action**: Fix all failing checks
   - **ETA**: Unknown

### 🟡 **Dependency Blockers**
2. **Merge Train Dependencies** → All leads
   - **Issue**: PRs #72, #73, #68, #67 waiting on #71
   - **Impact**: Delays all development work
   - **Action**: Wait for #71 to merge
   - **ETA**: After #71 fixes

### 🟢 **Process Blockers**
3. **PR Linkage Complete** → @coordinator
   - **Issue**: All merge train PRs now have "Fixes #" links
   - **Impact**: None (resolved)
   - **Action**: Complete
   - **ETA**: Complete

---

## Actions Taken

### ✅ **Completed**
1. **Merge Order Enforced**: #71 → #72 → #73 → #68 → #67
2. **PRs Edited**: All merge train PRs now include "Fixes #" links
3. **Merge Train Frozen**: All PRs except train are frozen
4. **Owner Notified**: @devex-lead pinged about failing gates

### ⏸️ **In Progress**
1. **CI Fixes**: @devex-lead working on PR #71 failing checks
2. **Merge Train**: Waiting for gates to turn green

### 📋 **Pending**
1. **Merge PR #71**: After @devex-lead fixes failing checks
2. **Continue Train**: #72 → #73 → #68 → #67
3. **Verify Main**: Ensure all checks green on main after train

---

## Next Actions

### Immediate (Today)
1. **@devex-lead**: Fix all failing checks in PR #71
   - ruff, pyright, imports, unit, coverage, contracts, docs-health
2. **@coordinator**: Monitor PR #71 status

### After #71 Merges
1. **@workflow-lead**: Merge PR #72 (workflow unskip)
2. **@tools-lead**: Merge PR #73 (tools N-1 samples)
3. **@runtime-lead**: Merge PR #68 (StoragePort + schema)
4. **@devex-lead**: Merge PR #67 (Python pin)

### After Merge Train
1. **@coordinator**: Verify all checks green on main
2. **@coordinator**: Unfreeze remaining PRs
3. **@coordinator**: Generate final status report

---

## Success Criteria

### Merge Train Success
- [ ] PR #71 merges successfully (all gates green)
- [ ] PRs #72, #73, #68, #67 merge in sequence
- [ ] All checks green on main after train
- [ ] All PRs have "Fixes #" links

### Failure Conditions
- [ ] Any PR fails CI checks (current state)
- [ ] Merge train breaks dependency order
- [ ] Main branch checks fail after merge

---

## Status Summary

**Current State**: 🔴 **MERGE TRAIN STOPPED**
**Reason**: PR #71 has all gates failing
**Owner**: @devex-lead
**Next Action**: Fix failing checks in PR #71
**ETA**: Unknown (depends on @devex-lead)

**Merge Train Progress**: 0/5 PRs merged
**PR Linkage**: ✅ 100% complete
**Merge Order**: ✅ Enforced
**Gates Status**: 🔴 All failing

---

**Report**: `reports/status/$(date -u +%F)/$(date -u +%F)-coordinator-merge-plan.md`
