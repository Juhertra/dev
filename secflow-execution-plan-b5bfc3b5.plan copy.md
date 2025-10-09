<!-- b5bfc3b5-9741-4bde-94f4-4681762c1191 dd43b398-9e67-4fed-9d03-0405fdba05b3 -->
# SecFlow Execution Plan — Runtime Skeleton & Quality Gates (FINAL)

**Status**: ✅ APPROVED — Ready for M0→M1 execution

**Mode**: Planning complete — awaiting green-light for implementation

**Audience**: Small team (2-5 developers)

**Duration**: M0–M6 (~16 weeks)

**Branch Model**: Trunk-based with lightweight stabilization

**Runtime**: Python 3.11+ (Linux primary, macOS dev, Windows best-effort)

---

## 1. Branch Protection & Workflow Specification

### Main Branch Rules

- **Protected**: Yes, force push disabled
- **Required checks before merge**:
  - `ruff --fix` (linting with auto-fix)
  - `pyright --warnings` (type checking)
  - `import-linter` (architecture boundaries)
  - `pytest` (≥80% line coverage, ratchet +2% per milestone)
  - Contract tests pass (Finding invariants + golden samples + ports)
  - `make health` if docs changed (Mermaid parity + ASCII blocker + fence hygiene)
  - 1 approval from CODEOWNER of affected module
  - Security-sensitive changes also require @security-lead approval
- **Linear history**: Squash or rebase merge only

### Feature Branch Naming (Trunk-Based)

- `feat/<issue-number>-<short-desc>` — New features (e.g., `feat/001-core-lib`)
- `fix/<issue-number>-<short-desc>` — Bug fixes (e.g., `fix/089-nuclei-parser`)
- `chore/<desc>` — Refactoring, dependencies (e.g., `chore/upgrade-pydantic`)
- `docs/<desc>` — Documentation only (e.g., `docs/api-reference`)

### Release Discipline (Lightweight Stabilization)

- **Primary approach**: Lightweight stabilization windows on main + annotated tags
- **Tags**: `v0.1.0`, `v1.0.0`, etc. (semantic versioning) tagged from main
- **No long-lived release branches**: Hotfix off tag if needed (rare)
- **Milestone tags**: `M1-complete`, `M2-complete`, etc. for tracking
- **Why**: Keeps flow simple, avoids drift, enables point fixes when needed

### Workflow Summary

```
main (protected, trunk)
  ├── feat/001-core-lib → PR → squash merge
  ├── feat/002-finding-schema → PR → squash merge → M1-complete tag
  ├── feat/007-nuclei-wrapper → PR → squash merge
  └── stabilization window → v1.0.0 tag
      └── hotfix/critical-bug (if needed, off v1.0.0 tag)
```

### Definition of Done (PR Template)

Every PR must satisfy:

- ✅ `ruff --fix` + `pyright --warnings` pass (no errors)
- ✅ `pytest` ≥80% line coverage on new code (ratchet +2% per milestone)
- ✅ Contract tests pass (Finding invariants + golden samples + port contracts)
- ✅ `make health` if docs changed
- ✅ Public APIs have Google-style docstrings with examples
- ✅ Test fixture or golden sample for new parsers
- ✅ ADR updated if schema/ports/workflow semantics changed
- ✅ Conventional Commits format (e.g., `feat(wrapper): add nuclei parser`)
- ✅ PR size ≤400 LOC (>400 requires two owner approvals)
- ✅ Pre-commit hooks pass (10s quick test + ruff + pyright)

---

## 2. Milestone Plan (M0–M6) — Exit Criteria & Owners

### M0: Pre-Flight & Planning (Week 1)

**Scope**: Plan approval, repo audit, team alignment, M0 "GO" checklist

**Exit Criteria**:

- ✅ This execution plan approved with all final tweaks
- ✅ Open questions confirmed (Poetry, Python 3.11, Docker Compose, tool matrix)
- ✅ Branch protection on main with required checks
- ✅ CODEOWNERS merged; roles assigned
- ✅ Issue board created (FEAT-001…040)
- ✅ `pyproject.toml` + Poetry skeleton committed
- ✅ CI jobs stubbed (even if empty)
- ✅ Gates green on current docs (`make health` passes)
- ✅ Coverage baseline captured (current %)
- ✅ Pre-commit hooks configured (ruff --fix, pyright, quick test)
- ✅ `make scaffold-package` utility ready

**Owners**: @runtime-lead, @devex-lead

**Deliverables**:

- `.github/CODEOWNERS`, `.github/pull_request_template.md`
- `pyproject.toml` (Poetry workspace with packages/)
- `.github/workflows/ci.yml` (job stubs)
- `.pre-commit-config.yaml` (ruff, pyright, quick test)
- `Makefile` with `scaffold-package` target
- GitHub issue board with 40 issues

**Week-by-Week**:

- Week 1 Day 1-2: Final plan review, open questions confirmed
- Week 1 Day 3: CODEOWNERS, PR template, pyproject.toml skeleton
- Week 1 Day 4: CI stubs, pre-commit hooks, Makefile targets
- Week 1 Day 5: M0 checkpoint meeting, "GO" checklist complete

---

### M1: Runtime Skeleton + Vertical Slice (Weeks 2-4)

**Scope**: Core packages, Finding schema v1.0, port interfaces, storage adapter, vertical slice demo

**Exit Criteria**:

- ✅ **Vertical slice demo**: NucleiWrapper → normalize → store (file adapter) → show 1 finding via CLI
- ✅ E2E smoke test (`tests/e2e/test_vertical_slice.py`) proves slice end-to-end
- ✅ `packages/core-lib/` with Finding, Project, Run, Resource models
- ✅ `schemas/finding.json` v1.0 with `finding_schema_version` field
- ✅ Port interfaces: StoragePort (atomic writes + `validate_store_layout()`), ToolPort, ResourcePort, FindingsPort
- ✅ In-memory + file-backed storage adapters
- ✅ Finding model invariants enforced: `detector_id` regex `^[A-Za-z0-9_.-]+$`, UTC Z timestamps
- ✅ Contract test loads real tool samples, asserts invariants fail fast
- ✅ Migration stub: `scripts/migrate_store_v1_to_v2.py` (no-op, ready for later)
- ✅ CI green: ruff → pyright → import-linter → unit → contracts → docs → e2e (informational)
- ✅ Coverage ≥80% (baseline captured in M0)
- ✅ Docstring coverage ≥60%

**Owners**: @runtime-lead, @findings-lead

**Deliverables**:

- `packages/core-lib/models/finding.py` with invariants
- `packages/core-lib/ports/storage_port.py` with `validate_store_layout()`
- `packages/storage/adapters/memory.py`, `packages/storage/adapters/file_backed.py`
- `schemas/finding.json` v1.0 (SemVer + schema version in persisted JSON)
- `tests/e2e/test_vertical_slice.py` (Hello SecFlow demo)
- `tests/contracts/test_finding_invariants.py` (detector_id regex, UTC Z timestamps)
- `scripts/migrate_store_v1_to_v2.py` (stub)
- `docs/adr/001-finding-schema-versioning.md`
- `docs/adr/002-storage-contract-hardening.md`

**Risks**:

- Vertical slice too ambitious → Mitigation: Hardcode Nuclei sample, simplest CLI
- Storage contract too rigid → Mitigation: `validate_store_layout()` warns first, fails only on critical

**Week-by-Week**:

- Week 2: Core models, Finding schema v1.0, Finding invariants + contract test
- Week 3: Port interfaces (StoragePort with atomic writes), in-memory adapter
- Week 4: File-backed adapter, vertical slice demo + E2E smoke test

**Validation**:

```bash
make test-core
make test-contracts
make test-e2e-vertical-slice
python cli/hello_secflow.py --sample data/nuclei_sample.json
```

---

### M2: Tool Wrappers & Parsers (Weeks 5-8)

**Scope**: Standardized tool wrappers with golden samples, parser contracts, manifest with version checks

**Exit Criteria**:

- ✅ 3 first-class wrappers: NucleiWrapper, FeroxWrapper, KatanaWrapper
- ✅ ZAPWrapper skeleton (full parser deferred to M4+)
- ✅ Tool manifests with `min_version` field + version probe step (fail early if too old)
- ✅ Version checks cached across a run
- ✅ Golden samples: `tests/golden_samples/<tool>/<version>/output.json` (current + N-1)
- ✅ Contract tests validate parsing across versions
- ✅ Passthrough fallback on parse error (store raw output + log warning)
- ✅ Parser benchmark: ≥1000 findings/sec baseline
- ✅ Coverage ≥82% (ratchet +2% from M1)

**Owners**: @tools-lead, @findings-lead

**Deliverables**:

- `packages/wrappers/base.py` (ToolWrapper protocol: prepare/run/parse_output)
- `packages/wrappers/nuclei.py`, `feroxbuster.py`, `katana.py` (first-class)
- `packages/wrappers/zap.py` (skeleton only)
- `packages/wrappers/manifest.py` (tool manifest with `min_version`, version probe)
- `tests/golden_samples/nuclei/v2.9.x/`, `v3.0.x/`, etc.
- `tests/contracts/test_parser_contracts.py` (validate across golden samples)
- `scripts/benchmark_parsers.py` (≥1000 findings/sec)
- `docs/adr/003-tool-version-checks.md`

**Parser Guardrails**:

- Commit **golden samples** of real tool outputs (≥2 versions per tool)
- Contract tests validate parsing across current + N-1 samples
- **Passthrough fallback**: On parse error, store raw output + log warning, never fail scan
- **Version probe**: Check tool version on first run, cache result, fail if `< min_version`

**Risks**:

- Tool version skew → Mitigation: Version probe + min_version enforcement
- Parse brittleness → Mitigation: Golden samples + fallback

**Week-by-Week**:

- Week 5: ToolWrapper protocol + NucleiWrapper + golden samples + version probe
- Week 6: FeroxWrapper, KatanaWrapper + golden samples
- Week 7: ZAPWrapper skeleton + parser benchmarks
- Week 8: Contract tests, passthrough fallback testing, integration tests

**Validation**:

```bash
make test-wrappers
make test-parser-contracts
python scripts/benchmark_parsers.py --threshold 1000
```

---

### M3: Workflow Engine (Linear v1) (Weeks 9-11)

**Scope**: Linear workflow execution (no parallelism), YAML spec, persistence

**Exit Criteria**:

- ✅ 2 example workflows run end-to-end with metrics/logs
- ✅ YAML workflow schema validated on load (max depth, max nodes)
- ✅ Linear executor only (no DAG parallelism yet)
- ✅ Feature flag: `enable_parallel_execution: false` (config + env override)
- ✅ Run state persistence (checkpoints, resume capability)
- ✅ Timeouts/retries per node (exponential backoff)
- ✅ Workflow metrics: duration, node execution time, failures
- ✅ **Docker Compose staging deploy** workflow (CI job)
- ✅ Coverage ≥84% (ratchet +2% from M2)

**Owners**: @workflow-lead, @runtime-lead

**Deliverables**:

- `packages/workflow-engine/executor.py` (linear executor, topological sort)
- `packages/workflow-engine/persistence.py` (checkpoints, resume)
- `schemas/workflow-recipe.json` (YAML schema with max depth/nodes)
- `packages/core-lib/feature_flags.py` (config-driven flags)
- `workflows/sample-nuclei-only.yaml`, `sample-discovery-scan.yaml`
- `.github/workflows/deploy-staging.yml` (Docker Compose)
- `docker-compose.staging.yml` (staging environment)
- `docs/adr/004-workflow-linear-only.md`

**Workflow Scope**:

- **Linear chains only** in M3 (no DAG parallelism)
- Feature-flag parallelism for future (`enable_parallel_execution: false`)
- Cap DAG depth via config (e.g., `max_depth: 10`)
- Validate workflow on load (reject if too complex)

**Risks**:

- Workflow state corruption → Mitigation: Atomic writes, checksums
- Staging deploy complexity → Mitigation: Docker Compose first (simpler)

**Week-by-Week**:

- Week 9: Workflow recipe schema + parser + validation (max depth/nodes)
- Week 10: Linear executor + feature flags + timeouts/retries
- Week 11: State persistence + example workflows + Docker Compose staging deploy

**Validation**:

```bash
make test-workflows
python tools/validate_recipe.py workflows/sample-linear.yaml
python tools/run_workflow.py workflows/sample-linear.yaml --dry-run
make deploy-staging  # CI job
```

---

### M4: Plugin System & Policies (Weeks 12-13)

**Scope**: Plugin loader with security policies, sandboxing, sample plugins

**Exit Criteria**:

- ✅ Plugins load under policy; mis-policy fails gracefully
- ✅ 2 sample plugins operational: CVEMapper, RiskScorer
- ✅ **Plugin sandbox**: subprocess with time/mem limits, deny-by-default FS/network (configurable allowlist)
- ✅ Policy file required per plugin (`plugin_policy.yaml`)
- ✅ Manifest signing placeholder (stub for future PKI)
- ✅ `tools/plugin_security_audit.py` check in CI (advisory first)
- ✅ Coverage ≥86% (ratchet +2% from M3)

**Owners**: @security-lead, @runtime-lead

**Deliverables**:

- `packages/plugins/loader.py` (dynamic loader + policy enforcer)
- `packages/plugins/sandbox.py` (subprocess isolation, deny-by-default FS/network)
- `schemas/plugin-manifest.json` (with `policy_file`, `signature` stub)
- `schemas/plugin-policy.yaml` (allow_network, allow_files, max_cpu_seconds, etc.)
- `packages/plugins/enrichers/cve_mapper.py` + `cve_mapper_policy.yaml`
- `packages/plugins/scorers/risk_scorer.py` + `risk_scorer_policy.yaml`
- `tools/plugin_security_audit.py` (CI advisory check)
- `docs/adr/005-plugin-security-policies.md`

**Plugin Security Baseline**:

- **Mandatory policy file** per plugin (refuse load if absent)
- **Deny-by-default**: No FS writes, no network (must explicitly allow in policy)
- **Sandbox enforcement**: subprocess with resource limits (ulimit, cgroups if available)
- **Manifest signing**: Placeholder for future (stub in manifest, not enforced yet)
- **Security audit**: CI job runs `tools/plugin_security_audit.py` (advisory, doesn't block)

**Risks**:

- Plugin security vulnerabilities → Mitigation: Deny-by-default, mandatory policy, audit
- Plugin performance impact → Mitigation: Timeout limits, async execution

**Week-by-Week**:

- Week 12: Plugin loader + policy enforcer + sandbox (deny-by-default)
- Week 13: CVEMapper, RiskScorer + policy files + security audit tool

**Validation**:

```bash
make test-plugins
python tools/plugin_security_audit.py  # CI advisory check
python tools/test_plugin_sandbox.py --plugin bad_plugin --expect-fail
```

---

### M5: Observability & Resilience (Week 14)

**Scope**: Structured logging, Prometheus metrics, error recovery, performance budgets

**Exit Criteria**:

- ✅ Dashboard shows runs and error rates
- ✅ CI perf asserts stable (meet budgets)
- ✅ Prometheus metrics endpoint operational (`/metrics`)
- ✅ Circuit breaker + exponential backoff patterns
- ✅ Perf budgets enforced: parse throughput ≥1000/s, per-wrapper wall time, log volume ≤10MB
- ✅ Coverage ≥88% (ratchet +2% from M4)

**Owners**: @runtime-lead, @observability-lead

**Deliverables**:

- `packages/observability/logging.py` (JSON, structured fields: run_id, request_id)
- `packages/observability/metrics.py` (Prometheus endpoint)
- `packages/observability/recovery.py` (retry decorator, circuit breaker)
- `scripts/check_perf_budgets.py` (CI enforcer)
- `docs/observability-runbook.md`

**Observability Budgets**:

- **Parse throughput**: ≥1000 findings/sec (CI fails if below)
- **Per-wrapper wall time**: Define per tool (e.g., Nuclei ≤5min for 100 endpoints)
- **Log volume**: ≤10MB per run (prevents log spam)
- **CI perf asserts**: Fail if budgets violated

**Risks**:

- Logging overhead → Mitigation: Sampling, log levels, budget enforcement
- Metrics explosion → Mitigation: Cardinality limits

**Week-by-Week**:

- Week 14 Day 1-2: Logging (JSON, structured fields)
- Week 14 Day 3-4: Prometheus metrics + dashboard
- Week 14 Day 5: Error recovery + budgets + CI asserts

**Validation**:

```bash
make test-observability
curl localhost:9090/metrics
python scripts/check_perf_budgets.py
```

---

### M6: DevEx & Docs (Weeks 15-16)

**Scope**: mkdocstrings API reference, tutorials, migration guide, 90% docstring coverage

**Exit Criteria**:

- ✅ New dev can build, run, and extend a wrapper in <1 hour
- ✅ mkdocstrings integrated without breaking Mermaid gates
- ✅ API reference section complete (`docs/api/**`)
- ✅ Docstring coverage ≥90% (with per-module allowlist)
- ✅ Migration guide for schema changes
- ✅ Tutorials: "Your First Wrapper", "Writing a Plugin", "Workflow Basics"
- ✅ Coverage ≥90% (ratchet +2% from M5)

**Owners**: @devex-lead, @findings-lead

**Deliverables**:

- `docs/api/` (isolated API pages, no Mermaid conflicts)
- `mkdocs.yml` (mkdocstrings plugin configured)
- `docs/tutorials/first-wrapper.md`, `writing-plugin.md`, `workflow-basics.md`
- `docs/migration-guide.md` (schema evolution, storage migrations)
- `scripts/docstring_coverage.py` (≥90% with allowlist)
- `docs/adr/006-mkdocstrings-integration.md`

**Docs Plan**:

- **Isolate API pages**: `docs/api/**` (no Mermaid diagrams here)
- **Keep Mermaid pages separate**: Architecture docs stay in `docs/architecture/**`
- **Docstring coverage gate**: ≥90% at M6, per-module allowlist to unblock early work
- **Validation**: Build docs before/after mkdocstrings, ensure `make health` still green

**Docstrings Coverage Ramp**:

- M1/M2: 60% (avoid early friction)
- M3/M4: 75%
- M5/M6: 90% (enforced by CI gate with per-module allowlist)

**Risks**:

- mkdocstrings breaks Mermaid gates → Mitigation: Isolate API pages, test before/after
- Incomplete docstrings → Mitigation: Coverage gate + allowlist

**Week-by-Week**:

- Week 15: mkdocstrings setup + API reference + docstring audit
- Week 16: Tutorials + migration guide + final polish

**Validation**:

```bash
make health
make docs
make validate-docstrings --threshold 90
```

---

## 3. Finding Schema Versioning & Invariants

### Schema SemVer

- `schemas/finding.json` with **`finding_schema_version`** field (SemVer)
- Example: `"finding_schema_version": "1.0.0"`
- Increment: Major (breaking), Minor (additive), Patch (docs only)

### Finding Model Invariants (CI Gate)

**Enforced**:

- `detector_id` regex: `^[A-Za-z0-9_.-]+$` (no colons)
- Timestamps: ISO 8601 UTC with Z suffix (e.g., `2025-10-08T19:30:00Z`)

**Contract Test**:

- `tests/contracts/test_finding_invariants.py`
- Loads real tool samples (Nuclei, Feroxbuster, etc.)
- Asserts invariants fail fast on violation
- CI fails if any sample violates invariants

### Compatibility Matrix

- `docs/finding_schema_compat.md` tracks parser/enricher versions

---

## 4. Storage Contract Hardening

### StoragePort Extensions

**Required methods**:

- `atomic_write(path, data)` — Atomic writes (temp file + rename)
- `validate_store_layout()` — Check storage structure, warn/fail on issues
- `get_schema_version()` — Return current schema version

### Schema Version in Persisted JSON

All stored findings include:

```json
{
  "store_schema_version": "1.0.0",
  "findings": [...]
}
```

### Migration Stub

- `scripts/migrate_store_v1_to_v2.py` (no-op now, used later)
- Template for future schema migrations

---

## 5. CI Pipeline — Job Order & Thresholds

### Job Order (Optimized)

1. **ruff** (--fix) — ~30s
2. **pyright** (--warnings) — ~1min
3. **import-linter** — ~30s
4. **unit-tests** (pytest + coverage) — ~3min
5. **contract-tests** (Finding invariants + golden samples + ports) — ~2min
6. **docs-validation** (make health if docs changed) — ~3min
7. **e2e-tests** (vertical slice + workflows, informational) — ~5min

### Caching

- **pip cache**: `~/.cache/pip` (key: `pyproject.toml` hash)
- **pytest cache**: `.pytest_cache` (key: branch + commit)
- **mkdocs cache**: `site/` (key: `docs/**` hash)

### Coverage Ratcheting

- **Baseline**: Capture in M0 (current %)
- **M1**: ≥80%
- **M2**: ≥82% (+2%)
- **M3**: ≥84% (+2%)
- **M4**: ≥86% (+2%)
- **M5**: ≥88% (+2%)
- **M6**: ≥90% (+2%)
- **CI fails if coverage decreases >2%**

---

## 6. CODEOWNERS Map

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

# Legacy Code (transitional)
/findings.py                 @runtime-lead @findings-lead
/nuclei_integration.py       @tools-lead
/store.py                    @runtime-lead

# Routes (web-facing)
/routes/                     @runtime-lead @security-lead

# Tests
/tests/                      @qa-lead
/tests/golden_samples/       @tools-lead @qa-lead

# Root config
/pyproject.toml              @devex-lead
/Makefile                    @devex-lead

# Global fallback
*                            @runtime-lead
```

**Approval Requirements**:

- **Touched areas**: 1 approval from CODEOWNER of affected module
- **Security-sensitive**: Also ping @security-lead (plugins, auth, secrets)
- **PR size >400 LOC**: 2 owner approvals
- **Global fallback**: @runtime-lead reviews if no specific owner

---

## 7. Dev Ergonomics — Fast Feedback

### Pre-Commit Hooks (10s target)

`.pre-commit-config.yaml`:

- `ruff --fix` (auto-fix linting)
- `pyright --warnings` (type checking)
- `make quick-test` (unit + vertical slice only, ~10s)

### Quick Test Target

`Makefile`:

```makefile
quick-test:
	pytest tests/unit/ tests/e2e/test_vertical_slice.py -x --ff
```

### Scaffold Utility

`Makefile`:

```makefile
scaffold-package:
	@echo "Creating package: $(name)"
	mkdir -p packages/$(name)/$(name)
	mkdir -p packages/$(name)/tests
	touch packages/$(name)/$(name)/__init__.py
	echo "# $(name)" > packages/$(name)/README.md
	echo "# Tests for $(name)" > packages/$(name)/tests/test_$(name).py
	@echo "✅ Package $(name) scaffolded"
```

Usage:

```bash
make scaffold-package name=my-new-package
```

---

## 8. Issue Backlog (40 Items) — M1 Focus

### M1: Runtime Skeleton + Vertical Slice (10 issues)

**FEAT-001**: Create core-lib package structure

**Labels**: feat, M1, core

**Owner**: @runtime-lead

**Estimate**: 2d

**Folders**: `packages/core-lib/models/`, `packages/core-lib/ports/`

**Acceptance**:

- Finding, Project, Run, Resource models with Pydantic
- Finding invariants enforced (detector_id regex, UTC Z timestamps)
- Type checking passes (pyright)
- Unit tests ≥80% coverage

**Done Signal**: `make test-core` green

---

**FEAT-002**: Create Finding schema v1.0 with invariants

**Labels**: feat, M1, schema

**Owner**: @findings-lead

**Estimate**: 2d

**Folders**: `schemas/finding.json`, `tests/contracts/test_finding_invariants.py`

**Acceptance**:

- JSON Schema with `finding_schema_version` field
- Validator function enforces detector_id regex + UTC Z timestamps
- Contract test loads real tool samples, asserts invariants
- Compatibility matrix started (`docs/finding_schema_compat.md`)

**Done Signal**: Contract test passes with real samples

---

**FEAT-003**: Define port interfaces with storage hardening

**Labels**: feat, M1, core

**Owner**: @runtime-lead

**Estimate**: 2d

**Folders**: `packages/core-lib/ports/`

**Acceptance**:

- StoragePort: `atomic_write()`, `validate_store_layout()`, `get_schema_version()`
- ToolPort, ResourcePort, FindingsPort protocols
- Docstrings with examples

**Done Signal**: pyright validates protocol usage

---

**FEAT-004**: Implement in-memory storage adapter

**Labels**: feat, M1, storage

**Owner**: @runtime-lead

**Estimate**: 1d

**Folders**: `packages/storage/adapters/memory.py`

**Acceptance**:

- In-memory dict-based storage
- Implements StoragePort (atomic_write, validate_store_layout)
- Thread-safe
- Contract tests pass

**Done Signal**: `pytest tests/contracts/test_storage_port.py` green

---

**FEAT-005**: Implement file-backed storage adapter

**Labels**: feat, M1, storage

**Owner**: @runtime-lead

**Estimate**: 3d

**Folders**: `packages/storage/adapters/file_backed.py`

**Acceptance**:

- JSON file storage compatible with `ui_projects/` structure
- Atomic writes (temp file + rename)
- `validate_store_layout()` checks structure
- Schema version in persisted JSON
- Backward compatible with existing findings.json

**Done Signal**: Integration test with real files

---

**FEAT-006**: Create vertical slice demo + E2E smoke test

**Labels**: feat, M1, e2e

**Owner**: @runtime-lead

**Estimate**: 2d

**Folders**: `cli/hello_secflow.py`, `tests/e2e/test_vertical_slice.py`, `data/nuclei_sample.json`

**Acceptance**:

- Runnable CLI: NucleiWrapper → normalize → store (file adapter) → show 1 finding
- E2E smoke test proves slice end-to-end
- Hardcoded Nuclei sample (simplest possible)
- CI runs E2E test (informational)

**Done Signal**: `python cli/hello_secflow.py --sample data/nuclei_sample.json` works

---

**FEAT-007**: Add migration stub

**Labels**: chore, M1, storage

**Owner**: @runtime-lead

**Estimate**: 0.5d

**Folders**: `scripts/migrate_store_v1_to_v2.py`

**Acceptance**:

- No-op stub (template for future migrations)
- Dry-run mode + backup capability
- Documentation for migration process

**Done Signal**: Script runs, does nothing (as expected)

---

**FEAT-008**: Setup CI pipeline with job order

**Labels**: infra, M1, ci

**Owner**: @devex-lead

**Estimate**: 2d

**Folders**: `.github/workflows/ci.yml`

**Acceptance**:

- Job order: ruff → pyright → import-linter → unit → contracts → docs → e2e
- Pip + pytest caching enabled
- Coverage baseline captured
- Coverage ratchet: M1 ≥80%

**Done Signal**: CI runs successfully on main

---

**FEAT-009**: Create CODEOWNERS + PR template

**Labels**: chore, M1, infra

**Owner**: @devex-lead

**Estimate**: 0.5d

**Folders**: `.github/CODEOWNERS`, `.github/pull_request_template.md`

**Acceptance**:

- Ownership map matches section 6
- PR template includes DoD checklist
- Global fallback to @runtime-lead

**Done Signal**: Test PR triggers correct owner review

---

**FEAT-010**: Setup pre-commit hooks + quick-test

**Labels**: chore, M1, infra

**Owner**: @devex-lead

**Estimate**: 1d

**Folders**: `.pre-commit-config.yaml`, `Makefile`

**Acceptance**:

- Pre-commit: ruff --fix, pyright --warnings, make quick-test
- Quick-test: unit + vertical slice only (~10s)
- `make scaffold-package` utility ready

**Done Signal**: Pre-commit runs in <10s

---

## 9. M0 "GO" Checklist — Start M1 When Complete

Before starting M1 implementation, ensure:

- [ ] ✅ This execution plan approved with all final tweaks incorporated
- [ ] ✅ Open questions confirmed: Poetry, Python 3.11, Docker Compose, tool matrix
- [ ] ✅ Branch protection on main with required checks configured
- [ ] ✅ CODEOWNERS merged; roles assigned (@runtime-lead, @tools-lead, etc.)
- [ ] ✅ Issue board created from backlog (FEAT-001…040)
- [ ] ✅ `pyproject.toml` + Poetry skeleton committed (monorepo workspace)
- [ ] ✅ CI job stubs added (even if empty initially)
- [ ] ✅ Gates green on current docs (`make health` passes)
- [ ] ✅ Coverage baseline captured (document current %)
- [ ] ✅ Pre-commit hooks configured (ruff --fix, pyright, quick-test)
- [ ] ✅ `make scaffold-package` utility ready
- [ ] ✅ Kickoff meeting scheduled (review architecture docs)
- [ ] ✅ Slack/Discord channel created for team coordination
- [ ] ✅ Documentation repo backup created (in case of rollback)

**Once checklist complete**: 🚀 **GREEN-LIGHT M1 EXECUTION**

---

## 10. Open Questions — CONFIRMED

1. ✅ **Packaging**: Poetry + single `pyproject.toml` at repo root (monorepo workspace)
2. ✅ **Runtime target**: Minimum Python 3.11 (matches CI matrix)
3. ✅ **OS support**: Linux primary; macOS dev-only; Windows best-effort (WSL2)
4. ✅ **Staging deploy**: Docker Compose first (template both, wire at M3)
5. ✅ **Tooling matrix**: First-class: Nuclei, Feroxbuster, Katana (M2); ZAP skeleton only

---

## 11. Summary of Final Tweaks Incorporated

1. ✅ **Branching**: Lightweight stabilization windows + tags (no long-lived release branches)
2. ✅ **Vertical slice demo**: Hello SecFlow at M1 end + E2E smoke test
3. ✅ **Storage contract hardening**: `validate_store_layout()`, atomic writes, schema version
4. ✅ **Findings invariants**: detector_id regex + UTC Z timestamps enforced in contract test
5. ✅ **Wrappers & manifests**: `min_version` field + version probe (cached across run)
6. ✅ **CI gates**: Job order optimized, coverage ratchet +2% per milestone
7. ✅ **Docs & mkdocstrings**: Isolated API pages, docstring coverage ≥90% at M6 with allowlist
8. ✅ **Security & plugins**: Deny-by-default sandbox, mandatory policy, security audit (advisory)
9. ✅ **CODEOWNERS**: Global fallback (@runtime-lead), security-sensitive ping @security-lead
10. ✅ **Dev ergonomics**: Pre-commit hooks (<10s), quick-test, scaffold-package utility
11. ✅ **Open questions**: All confirmed (Poetry, Python 3.11, Docker Compose, tool matrix)

---

## 12. Next Steps — M0 Wrap-Up → M1 Kickoff

**Immediate actions**:

1. Complete M0 "GO" checklist (Week 1)
2. Kickoff meeting: Review architecture docs, assign M1 issues
3. First PR: `FEAT-001` (Create core-lib package structure)
4. Daily standups during M1 (15min sync)
5. M1 checkpoint: End of Week 4 (demo vertical slice)

**After M1**:

- Tag `M1-complete` on main
- Retro: What worked, what to improve
- Assign M2 issues (tool wrappers)

**Final note**: This plan is **production-ready** and **approved for execution**. All final tweaks incorporated. Ready to green-light M0→M1.

**END OF PLAN** ✅

### To-dos

- [ ] Complete M0: Pre-flight & Planning (validate plan, create issues, assign owners)
- [ ] Complete M1: Runtime Skeleton (core-lib, ports, storage adapters)
- [ ] Complete M2: Tool Wrappers & Findings Engine (standardize tool integration)
- [ ] Complete M3: Workflow Engine & Resource Registry (DAG execution, staging deploy)
- [ ] Complete M4: Plugin System & Enrichment (CVE/CWE mapper, sandboxing)
- [ ] Complete M5: Observability & Error Handling (logging, metrics, recovery)
- [ ] Complete M6: API Docs & Migration Polish (mkdocstrings, migration guide, v1.0.0)