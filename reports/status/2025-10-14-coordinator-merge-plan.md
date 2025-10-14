# M0-D5 Coordinator Merge Plan

**Generated**: $(date -u +%F)  
**Coordinator**: M0-D5-FIX-COORD-001  
**Source-of-Truth**: docs/governance/engineering-standards.md, docs/governance/development-conventions.md

---

## Merge Plan Overview

**Objective**: Unblock M0 development by merging critical infrastructure PRs in dependency order

**Strategy**: Follow CI pipeline order (Phase 1 → Phase 2 → Phase 3 → Phase 4) per Engineering Standards

**Gate**: GO when all green ✅

---

## 4 PRs to Merge in Order

### 1. DevEx CI Infrastructure (CRITICAL)
- **PR**: [#47](https://github.com/Juhertra/dev/pull/47) - stabilize ruff (E/F/I) and pyright (basic) for M0
- **Owner**: @devex-lead
- **Priority**: CRITICAL
- **Dependencies**: None (foundational)
- **Phase**: 1 (Code Quality Gates)
- **DoD Checklist**:
  - [ ] All tests pass (`make test`)
  - [ ] No linting errors (`ruff`, `pyright`, `import-linter`)
  - [ ] Code follows project style guidelines
  - [ ] All CI checks pass
  - [ ] Validation evidence pasted in PR comments

**Why First**: Blocks all other development work. Must pass Phase 1 gates before any other PRs can proceed.

### 2. Workflow Stubs/Unskip (HIGH)
- **PR**: [#54](https://github.com/Juhertra/dev/pull/54) - linear v1 scaffolds (executor/validate_recipe stubs + recipes dir)
- **Owner**: @workflow-lead
- **Priority**: HIGH
- **Dependencies**: PR #47 (CI infrastructure)
- **Phase**: 2 (Testing Gates)
- **DoD Checklist**:
  - [ ] Unit tests written for new functionality
  - [ ] Integration tests updated if needed
  - [ ] Contract tests pass
  - [ ] Test coverage doesn't drop below current threshold

**Why Second**: Enables workflow development once CI infrastructure is stable.

### 3. Tools N-1 Samples (MEDIUM)
- **PR**: [#66](https://github.com/Juhertra/dev/pull/66) - add validation tools, sample recipe, and comprehensive tests
- **Owner**: @workflow-lead
- **Priority**: MEDIUM
- **Dependencies**: PR #47 (CI infrastructure), PR #54 (workflow stubs)
- **Phase**: 3 (Integration Gates)
- **DoD Checklist**:
  - [ ] Integration tests updated if needed
  - [ ] Contract tests pass
  - [ ] E2E tests pass (if applicable)
  - [ ] Documentation updated for any API changes

**Why Third**: Completes workflow tooling once basic infrastructure and stubs are in place.

### 4. DevOps Required Checks (HIGH)
- **PR**: [#70](https://github.com/Juhertra/dev/pull/70) - lock Python 3.11.9 + enforce MIN_COV=18 for M0
- **Owner**: @devex-lead
- **Priority**: HIGH
- **Dependencies**: PR #47 (CI infrastructure)
- **Phase**: 4 (End-to-End Gates)
- **DoD Checklist**:
  - [ ] Code coverage meets current milestone threshold
  - [ ] Coverage ratchet enforcement
  - [ ] Performance regression checks
  - [ ] All CI checks pass

**Why Fourth**: Establishes coverage baseline and completes CI configuration once core infrastructure is stable.

---

## Owners & Responsibilities

### @devex-lead (Primary)
- **PRs**: #47, #70
- **Focus**: CI infrastructure, coverage baseline
- **Blocking**: All other development work
- **Deadline**: EOD today

### @workflow-lead (Secondary)
- **PRs**: #54, #66
- **Focus**: Workflow engine, validation tools
- **Dependencies**: CI infrastructure from @devex-lead
- **Deadline**: Tomorrow

---

## Merge Criteria

### Prerequisites
- [ ] All PRs have "Fixes #<FEAT-ID>" links
- [ ] All PRs pass Phase 1 gates (ruff, pyright, import-linter)
- [ ] All PRs have validation evidence in comments
- [ ] All PRs meet DoD checklist requirements

### Merge Order Enforcement
1. **Sequential**: PRs must merge in dependency order
2. **Gate Passing**: Each PR must pass all required CI checks
3. **Review**: Each PR must have required approvals per CODEOWNERS
4. **Documentation**: Each PR must include validation evidence

---

## Risk Mitigation

### Critical Risks
- **CI Infrastructure Failure**: PR #47 must pass or all work stops
- **Coverage Baseline Missing**: PR #70 must establish MIN_COV=18%
- **Dependency Chain**: Each PR blocks the next in sequence

### Mitigation Actions
- **@devex-lead**: Focus exclusively on PRs #47, #70
- **@workflow-lead**: Prepare PRs #54, #66 for merge once CI is stable
- **@coordinator**: Monitor merge order compliance

---

## Success Criteria

### GO Criteria
- [ ] All 4 PRs pass CI checks
- [ ] All PRs have proper "Fixes #" links
- [ ] All PRs include validation evidence
- [ ] Coverage baseline established (MIN_COV=18%)
- [ ] CI infrastructure stable

### NO-GO Criteria
- [ ] Any PR fails Phase 1 gates
- [ ] Coverage baseline not established
- [ ] Missing "Fixes #" links
- [ ] Validation evidence missing

---

## Next Actions

### Immediate (Today)
1. **@devex-lead**: Complete PR #47 (CI infrastructure)
2. **@devex-lead**: Complete PR #70 (coverage baseline)
3. **All PR authors**: Add "Fixes #" links to PR descriptions

### Tomorrow
1. **@workflow-lead**: Complete PR #54 (workflow stubs)
2. **@workflow-lead**: Complete PR #66 (tools samples)
3. **@coordinator**: Verify merge order compliance

---

**Status**: GO when all green ✅  
**Next Review**: After each PR merge