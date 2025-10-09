# 📌 SecFlow M0 Coordination Summary

**Status**: ✅ ACTIVE - All team leads confirmed  
**Mode**: Trunk-based development with short stabilization  
**Duration**: M0–M6 (~16 weeks)  

---

## 👥 **CONFIRMED TEAM ROLES**

| Role | Owner | Responsibilities |
|------|-------|------------------|
| **@runtime-lead** | TBD | Core orchestration, workflow engine, storage |
| **@tools-lead** | TBD | Tool wrappers, integrations, UX glue |
| **@findings-lead** | TBD | Findings engine, data models, schemas |
| **@workflow-lead** | TBD | Workflow orchestration, DAG execution |
| **@security-lead** | TBD | Security model, compliance, risk assessment |
| **@observability-lead** | TBD | Logging, metrics, telemetry, monitoring |
| **@devex-lead** | TBD | Developer experience, docs, CI/CD, tooling |
| **@qa-lead** | TBD | Testing strategy, validation, quality gates |

---

## 🔄 **OPERATING RULES**

### **Read → Run → Update Workflow**
1. **Read**: Review requirements, architecture docs, existing code
2. **Run**: Execute changes locally, validate with quality gates
3. **Update**: Submit PR with validation evidence, get approval

### **Definition of Done**
- [ ] All quality gates pass (`make health`)
- [ ] Unit tests ≥80% coverage (ratcheting +2% per milestone)
- [ ] Contract tests pass (Finding invariants + golden samples)
- [ ] Code review approval from CODEOWNER
- [ ] Security-sensitive changes require @security-lead approval
- [ ] Documentation updated if needed
- [ ] Validation evidence included in PR

---

## 🌳 **BRANCH POLICY**

### **Trunk-Based Development**
- **Main branch**: Protected, force push disabled
- **Stabilization**: Short-lived, lightweight (no long-lived release branches)
- **History**: Linear preferred (squash or rebase merge)

### **Branch Naming Convention**
- `feat/<issue-number>-<short-desc>` — New features (e.g., `feat/001-core-lib`)
- `fix/<issue-number>-<short-desc>` — Bug fixes (e.g., `fix/089-nuclei-parser`)
- `chore/<desc>` — Refactoring, dependencies (e.g., `chore/upgrade-pydantic`)
- `docs/<desc>` — Documentation only (e.g., `docs/api-reference`)

### **PR Requirements**
- **Size limit**: ≤400 LOC (or requires 2 approvals)
- **Required checks**:
  - `ruff --fix` (linting)
  - `pyright --warnings` (type checking)
  - `import-linter` (architecture boundaries)
  - `pytest` (≥80% coverage)
  - Contract tests pass
  - `make health` (if docs changed)
- **Approval**: 1 approval from CODEOWNER of affected module

---

## 📁 **CODEOWNERS MAP**

```
# Runtime Core
/packages/core-lib/          @runtime-lead @security-lead
/packages/storage/           @runtime-lead

# Tool Integration
/packages/wrappers/          @tools-lead
/packages/findings-engine/   @findings-lead @tools-lead

# Workflow & Resources
/packages/workflow-engine/   @workflow-lead @runtime-lead
/packages/resources/         @resources-lead

# Plugins & Security
/packages/plugins/           @security-lead
/packages/security/          @security-lead

# Observability & DevEx
/packages/observability/     @observability-lead
/scripts/                    @devex-lead
/.github/                    @devex-lead

# Documentation
/docs/                       @devex-lead
/docs/adr/                   @runtime-lead @devex-lead
/docs/api/                   @devex-lead
/mkdocs.yml                  @devex-lead

# Schemas
/schemas/                    @findings-lead @runtime-lead
```

---

## 📚 **KEY DOCUMENTATION LINKS**

- **🚀 Developer Start Here**: [docs/developer-start-here.md](docs/developer-start-here.md)
- **🏗️ Architecture Overview**: [docs/architecture/00-index.md](docs/architecture/00-index.md)
- **📋 All Architecture Docs**: [docs/architecture/](docs/architecture/)

### **Essential Architecture Documents**
- [02-architecture-philosophy.md](docs/architecture/02-architecture-philosophy.md) - Core principles
- [04-core-packages-and-responsibilities.md](docs/architecture/04-core-packages-and-responsibilities.md) - Package structure
- [05-orchestration-and-workflow-engine.md](docs/architecture/05-orchestration-and-workflow-engine.md) - Workflow design
- [12-findings-model-and-schema.md](docs/architecture/12-findings-model-and-schema.md) - Data models
- [16-security-model.md](docs/architecture/16-security-model.md) - Security framework
- [21-ci-cd-and-testing-strategy.md](docs/architecture/21-ci-cd-and-testing-strategy.md) - CI/CD pipeline

---

## ✅ **ACKNOWLEDGMENT REQUIRED**

**All team leads must acknowledge with ✅:**

- [ ] @runtime-lead: ✅
- [ ] @tools-lead: ✅  
- [ ] @findings-lead: ✅
- [ ] @workflow-lead: ✅
- [ ] @security-lead: ✅
- [ ] @observability-lead: ✅
- [ ] @devex-lead: ✅
- [ ] @qa-lead: ✅

---

## 🎯 **NEXT STEPS**

1. **Team leads confirm roles** - Reply with ✅
2. **Assign specific owners** - Update CODEOWNERS file
3. **Begin M0→M1 execution** - Follow [Phase 0 tasks](docs/architecture/20-migration-and-implementation-phases.md)
4. **Quality gates active** - All PRs must pass validation

**Ready to ship! 🚀**
