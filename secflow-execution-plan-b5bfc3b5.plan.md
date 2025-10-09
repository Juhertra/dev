<!-- b5bfc3b5-9741-4bde-94f4-4681762c1191 0b33d5c5-1e5f-476c-b3a4-28cf764944d0 -->
# SecFlow Execution Plan — Runtime Skeleton & Quality Gates

**Mode**: Planning only — no file modifications  
**Audience**: Small team (2-5 developers)  
**Duration**: M0–M6 (~16 weeks)  
**Branch Model**: Trunk-based (main protected, short-lived feat/*)

---

## 1. Branch Protection & Workflow Specification

### Main Branch Rules
- **Protected**: Yes
- **Required checks before merge**:
  - `make health` (Mermaid parity + ASCII blocker + fence hygiene)
  - `make gates` (all quality gates)
  - Unit tests (pytest with 80%+ coverage)
  - Pre-commit guards (findings contract, schema validation)
  - 1 approval from CODEOWNER of affected module
- **No direct commits**: Force push disabled, requires PR
- **Linear history preferred**: Squash or rebase merge

### Feature Branch Naming
- `feat/<issue-number>-<short-desc>` — New features (e.g., `feat/42-resource-registry`)
- `fix/<issue-number>-<short-desc>` — Bug fixes (e.g., `fix/89-nuclei-parser`)
- `chore/<desc>` — Refactoring, dependency updates (e.g., `chore/upgrade-pydantic`)
- `docs/<desc>` — Documentation only (e.g., `docs/api-reference`)

### Release Branch Policy
- **When**: At end of each milestone (M1, M2, M3, etc.)
- **Format**: `release/1.0`, `release/1.1`, etc.
- **Purpose**: Stabilization, backports, hotfixes
- **Lifetime**: Keep until next major release

### Tagging Policy
- **Semantic versioning**: `v1.0.0`, `v1.1.0`, `v1.1.1`
- **Tag on main**: After merge from release branch
- **Annotated tags**: Include changelog excerpt
- **Milestone tags**: `M1-complete`, `M2-complete` for tracking

### Workflow Summary
```
main (protected)
  ├── feat/123-tool-wrapper → PR → squash merge
  ├── feat/124-findings-engine → PR → squash merge
  └── release/1.0 (cut at M3 end)
      └── v1.0.0 tag
```

---

## 2. Milestone Plan (M0–M6)

### M0: Pre-Flight & Planning (Week 1)
**Scope**: Plan validation, repo audit, team alignment  
**Exit Criteria**:
- ✅ This execution plan reviewed and approved
- ✅ Current repo state documented (findings.py, nuclei_integration.py, etc.)
- ✅ Team aligned on SecFlow terminology (no "finance" tokens)
- ✅ CODEOWNERS drafted and merged
- ✅ GitHub issues created (20-40 items)

**Risks**:
- Legacy code coupling too deep → Mitigation: Start with facades/adapters
- Undiscovered dependencies → Mitigation: Dependency audit script

**Week-by-Week**:
- Week 1 Day 1-2: Review arch docs, validate Mermaid gates
- Week 1 Day 3-4: Create issue backlog, assign owners
- Week 1 Day 5: M0 checkpoint meeting, approve plan

---

### M1: Runtime Skeleton (Weeks 2-4)
**Scope**: Core packages scaffold, port interfaces, base storage layer  
**Exit Criteria**:
- ✅ `packages/core-lib/` created with models (Finding, Project, Run, Resource)
- ✅ Port interfaces defined (StoragePort, ToolPort, ResourcePort, FindingsPort)
- ✅ `packages/storage/` with in-memory and file-backed adapters
- ✅ Unit tests for all models and ports (80%+ coverage)
- ✅ CI green with type checking (pyright), linting (ruff), tests (pytest)

**Risks**:
- Port abstraction too complex → Mitigation: Start with 2-3 concrete methods, iterate
- Breaking existing code → Mitigation: Parallel implementation, keep legacy paths

**Week-by-Week**:
- Week 2: Core models and Pydantic schemas (`finding.py`, `project.py`, `run.py`, `resource.py`)
- Week 3: Port interfaces and in-memory adapters
- Week 4: File-backed storage adapter (compatible with current `ui_projects/` structure)

**Validation**:
```bash
make test-core
make type-check
make lint
```

---

### M2: Tool Wrappers & Findings Engine (Weeks 5-8)
**Scope**: Standardized tool wrappers, findings normalization, parser adapters  
**Exit Criteria**:
- ✅ `packages/wrappers/` with Nuclei, Feroxbuster, Katana wrappers
- ✅ `packages/findings-engine/` with normalization layer
- ✅ Parser adapters for each tool (JSON → Finding model)
- ✅ Tool manifests defined (YAML or JSON descriptors)
- ✅ Integration tests for each wrapper

**Risks**:
- Parser brittleness (tool output changes) → Mitigation: Schema validation + fallback
- Performance overhead → Mitigation: Benchmark each parser, cache results

**Week-by-Week**:
- Week 5: Abstract ToolWrapper protocol + NucleiWrapper
- Week 6: FeroxWrapper, KatanaWrapper, ZAPWrapper skeletons
- Week 7: Findings normalization layer (migrate `utils/findings_normalize.py`)
- Week 8: Integration tests + performance benchmarks

**Validation**:
```bash
make test-wrappers
make test-findings-engine
python scripts/benchmark_parsers.py
```

---

### M3: Workflow Engine & Resource Registry (Weeks 9-11)
**Scope**: DAG execution, YAML recipe parsing, resource management  
**Exit Criteria**:
- ✅ `packages/workflow-engine/` with DAG executor
- ✅ YAML recipe parser (validate against schema)
- ✅ `packages/resource-registry/` with wordlist/payload management
- ✅ Workflow runs persisted to storage
- ✅ CI includes workflow validation gate

**Risks**:
- DAG complexity explosion → Mitigation: Start with linear chains, add parallelism later
- Resource loading performance → Mitigation: Lazy loading + caching

**Week-by-Week**:
- Week 9: Workflow recipe schema + parser
- Week 10: DAG executor (topological sort, node execution)
- Week 11: Resource registry (load, cache, share across runs)

**Validation**:
```bash
make test-workflows
python tools/validate_recipe.py workflows/sample.yaml
make bench-resources
```

**Add staging deploy**: By end of M3, add GitHub Actions workflow for staging deployment

---

### M4: Plugin System & Enrichment (Weeks 12-13)
**Scope**: Plugin loader, CVE/CWE enrichment, risk scoring  
**Exit Criteria**:
- ✅ `packages/plugins/` with dynamic loader
- ✅ Sample plugins: CVEMapper, CWEEnricher, RiskScorer
- ✅ Plugin manifest validation
- ✅ Plugin sandboxing (subprocess isolation)
- ✅ Unit tests for each plugin

**Risks**:
- Plugin security vulnerabilities → Mitigation: Sandboxing, input validation, manifest signing
- Plugin performance impact → Mitigation: Timeout limits, async execution

**Week-by-Week**:
- Week 12: Plugin loader + manifest schema
- Week 13: CVE/CWE enrichment plugins + risk scorer

**Validation**:
```bash
make test-plugins
python tools/plugin_security_audit.py
```

---

### M5: Observability & Error Handling (Week 14)
**Scope**: Structured logging, metrics, error recovery  
**Exit Criteria**:
- ✅ `packages/observability/` with OpenTelemetry integration
- ✅ Structured logging (JSON output)
- ✅ Metrics endpoints (Prometheus format)
- ✅ Error handling patterns (retry, circuit breaker)
- ✅ Observability runbook

**Risks**:
- Logging overhead → Mitigation: Log levels, sampling
- Metrics explosion → Mitigation: Cardinality limits

**Week-by-Week**:
- Week 14 Day 1-2: Logging setup
- Week 14 Day 3-4: Metrics + Prometheus endpoint
- Week 14 Day 5: Error recovery patterns + runbook

**Validation**:
```bash
make test-observability
curl localhost:9090/metrics
```

---

### M6: API Docs & Migration Polish (Weeks 15-16)
**Scope**: mkdocstrings API reference, migration guide, final polish  
**Exit Criteria**:
- ✅ mkdocstrings integrated (auto-generate API docs from docstrings)
- ✅ API reference section in MkDocs nav
- ✅ Migration guide for legacy code
- ✅ All Mermaid/ASCII gates green
- ✅ Final release `v1.0.0` tagged

**Risks**:
- mkdocstrings breaks Mermaid gates → Mitigation: Test in isolation first
- Incomplete docstrings → Mitigation: Linting rule for missing docstrings

**Week-by-Week**:
- Week 15: mkdocstrings setup + docstring audit
- Week 16: Migration guide + final polish

**Validation**:
```bash
make health
make docs
make validate-docstrings
```

---

## 3. Issue Backlog (20-40 Items)

### Runtime Core (Owner: @runtime-lead)

**FEAT-001**: Create core-lib package structure  
**Labels**: feat, M1, core  
**Estimate**: 2d  
**Folders**: `packages/core-lib/`, `packages/core-lib/models/`, `packages/core-lib/ports/`  
**Acceptance**: 
- Finding, Project, Run, Resource models defined with Pydantic
- Type checking passes (pyright)
- Unit tests for all models (80%+ coverage)
**Done Signal**: `make test-core` green

---

**FEAT-002**: Define port interfaces (StoragePort, ToolPort, ResourcePort)  
**Labels**: feat, M1, core  
**Estimate**: 2d  
**Folders**: `packages/core-lib/ports/`  
**Acceptance**:
- Protocol classes for each port with abstract methods
- Docstrings explaining contract
- Example implementation (mock or in-memory)
**Done Signal**: pyright validates Protocol usage

---

**FEAT-003**: Implement in-memory storage adapter  
**Labels**: feat, M1, storage  
**Estimate**: 1d  
**Folders**: `packages/storage/adapters/`  
**Acceptance**:
- In-memory dict-based storage for all models
- Implements StoragePort interface
- Thread-safe (use locks)
**Done Signal**: Unit tests pass

---

**FEAT-004**: Implement file-backed storage adapter  
**Labels**: feat, M1, storage  
**Estimate**: 3d  
**Folders**: `packages/storage/adapters/`  
**Acceptance**:
- JSON file storage compatible with `ui_projects/` structure
- Atomic writes (temp file + rename)
- Backward compatible with existing findings.json
**Done Signal**: Integration test with real files

---

**FEAT-005**: Add Finding model validation  
**Labels**: feat, M1, core  
**Estimate**: 1d  
**Folders**: `packages/core-lib/models/finding.py`  
**Acceptance**:
- Pydantic validators for detector_id format (no colons)
- Timestamp format validation (ISO 8601 + Z)
- Severity enum validation
**Done Signal**: Validation tests pass

---

### Tool Wrappers (Owner: @tools-lead)

**FEAT-006**: Create abstract ToolWrapper protocol  
**Labels**: feat, M2, wrappers  
**Estimate**: 2d  
**Folders**: `packages/wrappers/base.py`  
**Acceptance**:
- Protocol with prepare(), run(), parse_output() methods
- ToolOutput dataclass defined
- Error handling base class
**Done Signal**: Type checking validates protocol usage

---

**FEAT-007**: Implement NucleiWrapper  
**Labels**: feat, M2, wrappers  
**Estimate**: 3d  
**Folders**: `packages/wrappers/nuclei.py`  
**Acceptance**:
- Wraps existing `nuclei_integration.py` logic
- Implements ToolWrapper protocol
- Parser handles JSON output → Finding model
- Handles template selection
**Done Signal**: Integration test with real Nuclei scan

---

**FEAT-008**: Implement FeroxWrapper  
**Labels**: feat, M2, wrappers  
**Estimate**: 2d  
**Folders**: `packages/wrappers/feroxbuster.py`  
**Acceptance**:
- JSON output parsing
- Endpoint discovery → Resource model
- Rate limiting support
**Done Signal**: Integration test

---

**FEAT-009**: Implement KatanaWrapper  
**Labels**: feat, M2, wrappers  
**Estimate**: 2d  
**Folders**: `packages/wrappers/katana.py`  
**Acceptance**:
- Crawl output parsing
- Endpoint extraction
- Depth control
**Done Signal**: Integration test

---

**FEAT-010**: Create tool manifest schema  
**Labels**: feat, M2, wrappers  
**Estimate**: 1d  
**Folders**: `packages/wrappers/manifest.py`, `schemas/tool-manifest.json`  
**Acceptance**:
- YAML/JSON schema for tool descriptors
- Fields: name, version, command, parser, inputs, outputs
- Validation using JSON schema
**Done Signal**: Schema validation passes

---

### Findings Engine (Owner: @findings-lead)

**FEAT-011**: Migrate normalization layer  
**Labels**: feat, M2, findings  
**Estimate**: 2d  
**Folders**: `packages/findings-engine/normalize.py`  
**Acceptance**:
- Move logic from `utils/findings_normalize.py`
- Use Finding model from core-lib
- Preserve all normalization rules
**Done Signal**: Existing tests pass with new module

---

**FEAT-012**: Create parser adapters registry  
**Labels**: feat, M2, findings  
**Estimate**: 2d  
**Folders**: `packages/findings-engine/parsers/`  
**Acceptance**:
- Registry maps tool → parser class
- Each parser: NucleiParser, PatternEngineParser, etc.
- Parser protocol defined
**Done Signal**: Registry loads all parsers

---

**FEAT-013**: Add enrichment hooks  
**Labels**: feat, M2, findings  
**Estimate**: 2d  
**Folders**: `packages/findings-engine/enrichment.py`  
**Acceptance**:
- Hook system for post-processing findings
- CVE/CWE lookup hook
- Evidence anchor extraction hook
**Done Signal**: Hook tests pass

---

### Workflow Engine (Owner: @workflow-lead)

**FEAT-014**: Create workflow recipe schema  
**Labels**: feat, M3, workflow  
**Estimate**: 2d  
**Folders**: `packages/workflow-engine/schema.py`, `schemas/workflow-recipe.json`  
**Acceptance**:
- YAML schema for workflow recipes
- Fields: name, nodes, edges, inputs, outputs
- JSON schema validation
**Done Signal**: Sample recipes validate

---

**FEAT-015**: Implement DAG executor  
**Labels**: feat, M3, workflow  
**Estimate**: 4d  
**Folders**: `packages/workflow-engine/executor.py`  
**Acceptance**:
- Topological sort for node execution order
- Execute nodes in dependency order
- Handle parallel execution (asyncio)
- Store intermediate results
**Done Signal**: Sample workflow executes

---

**FEAT-016**: Add workflow persistence  
**Labels**: feat, M3, workflow  
**Estimate**: 2d  
**Folders**: `packages/workflow-engine/persistence.py`  
**Acceptance**:
- Save workflow state to storage
- Resume from checkpoint
- Store node outputs
**Done Signal**: Resume test passes

---

### Resource Registry (Owner: @resources-lead)

**FEAT-017**: Create ResourceRegistry interface  
**Labels**: feat, M3, resources  
**Estimate**: 2d  
**Folders**: `packages/resources/registry.py`  
**Acceptance**:
- Methods: load(), list(), cache(), evict()
- Resource types: wordlist, payload, template
- Lazy loading + caching
**Done Signal**: Interface tests pass

---

**FEAT-018**: Implement wordlist provider  
**Labels**: feat, M3, resources  
**Estimate**: 2d  
**Folders**: `packages/resources/providers/wordlist.py`  
**Acceptance**:
- Load wordlists from disk or URL
- Cache in memory
- Support common formats (txt, csv)
**Done Signal**: Load test wordlist

---

**FEAT-019**: Implement template provider  
**Labels**: feat, M3, resources  
**Estimate**: 2d  
**Folders**: `packages/resources/providers/template.py`  
**Acceptance**:
- Load Nuclei templates
- Parse template metadata
- Cache templates
**Done Signal**: Load community templates

---

### Plugin System (Owner: @plugins-lead)

**FEAT-020**: Create plugin loader  
**Labels**: feat, M4, plugins  
**Estimate**: 3d  
**Folders**: `packages/plugins/loader.py`  
**Acceptance**:
- Discover plugins in plugins/ directory
- Load plugin manifest
- Validate plugin signature
- Import plugin module
**Done Signal**: Load sample plugin

---

**FEAT-021**: Implement CVEMapper plugin  
**Labels**: feat, M4, plugins  
**Estimate**: 2d  
**Folders**: `packages/plugins/enrichers/cve_mapper.py`  
**Acceptance**:
- Match CVE IDs from finding evidence
- Query CVE database (local or API)
- Enrich finding with CVE metadata
**Done Signal**: CVE enrichment test

---

**FEAT-022**: Implement RiskScorer plugin  
**Labels**: feat, M4, plugins  
**Estimate**: 2d  
**Folders**: `packages/plugins/scorers/risk_scorer.py`  
**Acceptance**:
- Calculate risk score from severity, confidence, context
- Configurable weights
- Output numeric score 0-100
**Done Signal**: Risk score tests

---

**FEAT-023**: Add plugin sandboxing  
**Labels**: feat, M4, plugins, security  
**Estimate**: 3d  
**Folders**: `packages/plugins/sandbox.py`  
**Acceptance**:
- Execute plugins in subprocess
- Resource limits (CPU, memory, time)
- Capture stdout/stderr
**Done Signal**: Sandbox violation test

---

### Observability (Owner: @devex-lead)

**FEAT-024**: Setup structured logging  
**Labels**: feat, M5, observability  
**Estimate**: 2d  
**Folders**: `packages/observability/logging.py`  
**Acceptance**:
- JSON log output
- Log levels configurable
- Context fields (request_id, user_id, etc.)
**Done Signal**: Log parsing test

---

**FEAT-025**: Add Prometheus metrics  
**Labels**: feat, M5, observability  
**Estimate**: 2d  
**Folders**: `packages/observability/metrics.py`  
**Acceptance**:
- Metrics: request_count, tool_execution_duration, findings_total
- Prometheus endpoint at /metrics
- Labels for tool, severity, status
**Done Signal**: Metrics endpoint returns data

---

**FEAT-026**: Implement error recovery patterns  
**Labels**: feat, M5, observability  
**Estimate**: 2d  
**Folders**: `packages/observability/recovery.py`  
**Acceptance**:
- Retry decorator with exponential backoff
- Circuit breaker for external services
- Dead letter queue for failed tasks
**Done Signal**: Recovery tests pass

---

### Documentation (Owner: @devex-lead)

**FEAT-027**: Integrate mkdocstrings  
**Labels**: feat, M6, docs  
**Estimate**: 2d  
**Folders**: `docs/api/`, `mkdocs.yml`  
**Acceptance**:
- mkdocstrings plugin added to requirements
- API reference section in nav
- Auto-generate docs from docstrings
- Mermaid gates still green
**Done Signal**: `make docs` builds successfully

---

**FEAT-028**: Add docstring coverage gate  
**Labels**: chore, M6, docs  
**Estimate**: 1d  
**Folders**: `scripts/docstring_coverage.py`  
**Acceptance**:
- Script checks all public classes/functions have docstrings
- CI fails if coverage < 90%
- Exclude test files
**Done Signal**: Gate passes in CI

---

**FEAT-029**: Write migration guide  
**Labels**: docs, M6  
**Estimate**: 2d  
**Folders**: `docs/migration-guide.md`  
**Acceptance**:
- Document how to migrate from legacy code
- Code examples for common patterns
- Troubleshooting section
**Done Signal**: Guide reviewed by team

---

### CI/CD (Owner: @devex-lead)

**FEAT-030**: Create staging deploy workflow  
**Labels**: chore, M3, ci  
**Estimate**: 3d  
**Folders**: `.github/workflows/deploy-staging.yml`  
**Acceptance**:
- Trigger on merge to main
- Build Docker image
- Push to staging environment
- Smoke tests after deploy
**Done Signal**: Staging deploy succeeds

---

**FEAT-031**: Add import-linter gate  
**Labels**: chore, M1, ci  
**Estimate**: 1d  
**Folders**: `.github/workflows/ci.yml`, `.importlinter`  
**Acceptance**:
- CI runs import-linter
- Enforce layer boundaries (core → storage, not reverse)
- Fail on violations
**Done Signal**: Import violations detected

---

**FEAT-032**: Add performance benchmarks  
**Labels**: chore, M2, ci  
**Estimate**: 2d  
**Folders**: `scripts/benchmarks/`, `.github/workflows/benchmark.yml`  
**Acceptance**:
- Benchmark parser performance
- Store results in GitHub Pages
- Alert on regressions
**Done Signal**: Benchmark runs in CI

---

### Testing (Owner: @qa-lead)

**FEAT-033**: Create integration test fixtures  
**Labels**: test, M1  
**Estimate**: 2d  
**Folders**: `tests/fixtures/`  
**Acceptance**:
- Sample findings.json files
- Sample Nuclei scan output
- Sample workflow recipes
**Done Signal**: Tests use fixtures

---

**FEAT-034**: Add contract tests for ports  
**Labels**: test, M1  
**Estimate**: 2d  
**Folders**: `tests/contracts/`  
**Acceptance**:
- Test each adapter implements port correctly
- Use property-based testing (hypothesis)
- Ensure consistency across adapters
**Done Signal**: Contract tests pass

---

**FEAT-035**: Create end-to-end test suite  
**Labels**: test, M3  
**Estimate**: 3d  
**Folders**: `tests/e2e/`  
**Acceptance**:
- Full workflow: import project → run scan → triage findings
- Use real tools (Nuclei, Feroxbuster)
- Verify findings stored correctly
**Done Signal**: E2E tests pass

---

### Refactoring (Owner: @runtime-lead)

**CHORE-036**: Migrate findings.py to core-lib  
**Labels**: chore, M1  
**Estimate**: 3d  
**Folders**: `findings.py` → `packages/core-lib/legacy_compat.py`  
**Acceptance**:
- Create compatibility layer
- Existing routes still work
- New code uses core-lib models
**Done Signal**: All tests pass

---

**CHORE-037**: Migrate nuclei_integration.py to wrappers  
**Labels**: chore, M2  
**Estimate**: 3d  
**Folders**: `nuclei_integration.py` → `packages/wrappers/nuclei.py`  
**Acceptance**:
- Extract reusable logic into wrapper
- Routes use new wrapper
- Legacy code deprecated
**Done Signal**: Nuclei scans work

---

**CHORE-038**: Migrate store.py to storage package  
**Labels**: chore, M1  
**Estimate**: 3d  
**Folders**: `store.py` → `packages/storage/adapters/file_backed.py`  
**Acceptance**:
- File storage implements StoragePort
- Existing data compatible
- Routes use storage adapter
**Done Signal**: Data reads/writes work

---

### Security (Owner: @security-lead)

**FEAT-039**: Add secrets management  
**Labels**: feat, security, M4  
**Estimate**: 2d  
**Folders**: `packages/security/secrets.py`  
**Acceptance**:
- Load secrets from environment or vault
- Encrypt sensitive data at rest
- Audit log for secret access
**Done Signal**: Secrets test passes

---

**FEAT-040**: Implement RBAC middleware  
**Labels**: feat, security, M3  
**Estimate**: 3d  
**Folders**: `packages/security/rbac.py`  
**Acceptance**:
- Role definitions: admin, analyst, viewer
- Permission checks on routes
- JWT authentication
**Done Signal**: RBAC test suite passes

---

## 4. CI Pipeline Outline

### Job: `lint-and-type`
**Trigger**: On push to any branch  
**Duration**: ~2 min  
**Steps**:
1. Checkout code
2. Setup Python 3.11
3. Install dependencies (Poetry)
4. Run ruff (linter)
5. Run pyright (type checker)
6. Run import-linter (architecture boundaries)

**Required to pass**: Yes (blocks merge)

---

### Job: `unit-tests`
**Trigger**: On push to any branch  
**Duration**: ~5 min  
**Steps**:
1. Checkout code
2. Setup Python 3.11
3. Install dependencies
4. Run pytest with coverage
5. Upload coverage to Codecov
6. Fail if coverage < 80%

**Required to pass**: Yes (blocks merge)

---

### Job: `contract-tests`
**Trigger**: On push to any branch  
**Duration**: ~3 min  
**Steps**:
1. Run findings contract tests (`test_findings_normalize.py`)
2. Run SSE stream tests (`test_sse_stream.py`)
3. Run port contract tests (`tests/contracts/`)
4. Fail on any violation

**Required to pass**: Yes (blocks merge)

---

### Job: `docs-validation`
**Trigger**: On push to any branch touching `docs/**`  
**Duration**: ~3 min  
**Steps**:
1. Run `make health` (Mermaid parity, ASCII blocker, fence hygiene)
2. Build MkDocs site
3. Check for broken links
4. Fail if DQI < 99

**Required to pass**: Yes (blocks merge for docs changes)

---

### Job: `integration-tests`
**Trigger**: On push to main or PR to main  
**Duration**: ~10 min  
**Steps**:
1. Setup test environment (Docker Compose)
2. Run tool wrapper integration tests
3. Run workflow engine integration tests
4. Run E2E tests
5. Teardown

**Required to pass**: No (informational for now)

---

### Job: `security-scan`
**Trigger**: On push to main  
**Duration**: ~5 min  
**Steps**:
1. Run Bandit (Python security linter)
2. Run Safety (dependency vulnerability scan)
3. Run Trivy (container scan if Docker images present)
4. Post results to GitHub Security tab

**Required to pass**: No (advisory)

---

### Job: `deploy-staging`
**Trigger**: On merge to main (after M3)  
**Duration**: ~8 min  
**Steps**:
1. Build Docker image
2. Push to container registry
3. Deploy to staging environment
4. Run smoke tests
5. Notify team on Slack

**Required to pass**: No (does not block merge)

---

## 5. CODEOWNERS Map

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
/packages/plugins/           @plugins-lead @security-lead
/packages/security/          @security-lead

# Observability & DevEx
/packages/observability/     @devex-lead
/scripts/                    @devex-lead
/.github/                    @devex-lead

# Documentation
/docs/                       @devex-lead
/mkdocs.yml                  @devex-lead

# Legacy Code (transitional)
/findings.py                 @runtime-lead @findings-lead
/nuclei_integration.py       @tools-lead
/store.py                    @runtime-lead

# Routes (web-facing)
/routes/                     @runtime-lead @security-lead

# Tests
/tests/                      @qa-lead

# Root config
/pyproject.toml              @devex-lead
/Makefile                    @devex-lead
```

**Approval Requirements**:
- Changes to `packages/core-lib/`: Require 1 approval from @runtime-lead or @security-lead
- Changes to `.github/workflows/`: Require 1 approval from @devex-lead
- Changes to `docs/`: Require 1 approval from @devex-lead
- All other changes: Require 1 approval from any CODEOWNER of affected area

---

## 6. Docs Plan — mkdocstrings Integration

### Goal
Add auto-generated API reference docs from Python docstrings without breaking existing Mermaid/ASCII gates.

### Approach
1. **Install mkdocstrings**: Add `mkdocstrings[python]` to requirements.txt
2. **Configure plugin**: Add to `mkdocs.yml` plugins section
3. **Create API section**: New nav section "API Reference"
4. **Generate stubs**: Create markdown files that invoke mkdocstrings
5. **Test isolation**: Build docs in CI before and after to ensure gates green

### mkdocs.yml Changes
```yaml
plugins:
  - search
  - mkdocstrings:
      handlers:
        python:
          paths: [packages]
          options:
            docstring_style: google
            show_root_heading: true
            show_source: true
```

### Nav Structure
```yaml
nav:
  - Developer Start Here: developer-start-here.md
  - Overview: ...
  - Architecture: ...
  - API Reference:
      - Core Models: api/core-models.md
      - Ports: api/ports.md
      - Storage: api/storage.md
      - Wrappers: api/wrappers.md
      - Findings Engine: api/findings-engine.md
      - Workflow Engine: api/workflow-engine.md
      - Plugins: api/plugins.md
      - Observability: api/observability.md
  - Review & Validation: ...
```

### Example API Page (`docs/api/core-models.md`)
```markdown
# Core Models

::: packages.core_lib.models.finding
    options:
      show_root_heading: true
      members:
        - Finding
        - FindingMetadata

::: packages.core_lib.models.project
    options:
      show_root_heading: true
      members:
        - Project
```

### Validation Steps
1. Run `make health` before mkdocstrings changes (baseline)
2. Add mkdocstrings configuration
3. Generate one API page
4. Run `make health` again (should still pass)
5. Build docs: `mkdocs build`
6. Check for Mermaid rendering in API pages (should not conflict)

### Docstring Standards
- **Style**: Google-style docstrings
- **Required fields**: Description, Args, Returns, Raises, Example
- **Linting**: Add `pydocstyle` or `darglint` to CI

### Rollout Plan
- M6 Week 15: Setup mkdocstrings + core-lib API docs
- M6 Week 16: Add remaining packages API docs
- Post-M6: Add interactive examples (later phase)

---

## 7. Risk Log — Top 10 Risks & Mitigations

### Risk 1: Legacy Code Coupling Too Deep
**Impact**: High | **Probability**: Medium  
**Mitigation**:
- Create compatibility shims for existing routes
- Run parallel implementations (old + new) during transition
- Gradual deprecation with feature flags

---

### Risk 2: Tool Output Parser Brittleness
**Impact**: High | **Probability**: High  
**Mitigation**:
- Schema validation on all parsed output
- Fallback to raw output capture if parsing fails
- Version pinning for external tools
- Parser test suite with real tool outputs

---

### Risk 3: Plugin Security Vulnerabilities
**Impact**: Critical | **Probability**: Medium  
**Mitigation**:
- Subprocess sandboxing with resource limits
- Input validation on all plugin inputs
- Manifest signing/verification
- Plugin security audit before loading

---

### Risk 4: Performance Degradation (Abstraction Overhead)
**Impact**: Medium | **Probability**: Medium  
**Mitigation**:
- Benchmarking in CI for critical paths
- Caching at every layer (findings, resources, templates)
- Async execution for I/O-bound operations
- Profile before optimizing

---

### Risk 5: Workflow DAG Complexity Explosion
**Impact**: Medium | **Probability**: Low  
**Mitigation**:
- Start with linear workflows (chain of tools)
- Add parallelism only when needed
- Workflow validation schema (max depth, max nodes)
- Workflow visualization tool for debugging

---

### Risk 6: Storage Migration Data Loss
**Impact**: Critical | **Probability**: Low  
**Mitigation**:
- Backup before migration (automated script)
- Dry-run mode for all migration scripts
- Rollback capability (restore from backup)
- Validation checks post-migration

---

### Risk 7: mkdocstrings Breaks Mermaid Rendering
**Impact**: Medium | **Probability**: Low  
**Mitigation**:
- Test in isolation before merging
- Keep Mermaid and API docs in separate pages
- CI gate checks both before/after
- Rollback plan if gates fail

---

### Risk 8: Team Knowledge Gaps (New Architecture)
**Impact**: Medium | **Probability**: Medium  
**Mitigation**:
- Pair programming for first few PRs
- Architecture review sessions (weekly)
- Documentation-first approach (write docs before code)
- Code review checklist with architecture patterns

---

### Risk 9: Secrets Handling Vulnerabilities
**Impact**: Critical | **Probability**: Low  
**Mitigation**:
- Never commit secrets (git-secrets hook)
- Use environment variables or vault
- Encrypt secrets at rest
- Audit log for all secret access
- Secrets rotation policy

---

### Risk 10: CI Pipeline Flakiness
**Impact**: Low | **Probability**: Medium  
**Mitigation**:
- Retry failed tests (max 2 retries)
- Isolate tests (no shared state)
- Mock external dependencies
- Timeout limits on all tests
- Periodic cleanup of test artifacts

---

## 8. Glossary — SecFlow Domain Terms

**SecFlow**: The security toolkit orchestration framework (formerly "finance" — all tokens renamed)

**Finding**: A security vulnerability or issue detected by a tool. Core entity with standardized schema.

**Detector**: A tool or pattern that produces findings (e.g., Nuclei template, custom regex pattern)

**Detector ID**: Unique identifier for a detector. Format: `tool.name` or `tool_name` (no colons).

**Run**: An execution of one or more tools against endpoints. Has unique run_id, timestamps, metadata.

**Endpoint**: A target URL + HTTP method combination (e.g., `GET https://api.example.com/users`)

**Dossier**: Aggregated metadata for an endpoint (last run, worst severity, coverage info)

**Project**: A logical grouping of endpoints, findings, and runs. Isolated storage per project.

**Workflow**: A DAG of tool executions with input/output mappings. Defined in YAML recipes.

**Recipe**: YAML file defining a workflow (nodes, edges, inputs, outputs)

**Resource**: Reusable asset (wordlist, payload, template) managed by resource registry

**Port**: Abstract interface (Protocol) defining a contract for adapters to implement

**Adapter**: Concrete implementation of a port (e.g., FileBackedStorageAdapter implements StoragePort)

**Wrapper**: Standardized interface around an external tool (e.g., NucleiWrapper)

**Plugin**: Dynamically loaded module for enrichment, detection, or scoring

**Enrichment**: Post-processing of findings to add metadata (CVE IDs, risk scores, remediation hints)

**Normalization**: Standardizing raw tool output into the Finding schema

**Triage**: Process of reviewing and categorizing findings (status: open, in_progress, resolved, etc.)

**Cache**: In-memory or disk-based storage for frequently accessed data (findings, templates, resources)

**SSE (Server-Sent Events)**: Real-time streaming protocol for live scan progress updates

**Quality Gates**: CI checks that must pass before merge (linting, tests, docs validation)

**Mermaid Parity**: CI gate ensuring all diagrams are Mermaid (no ASCII art)

**ASCII Blocker**: CI gate preventing ASCII diagrams from being committed

**Fence Hygiene**: CI gate checking markdown code fence formatting

**DQI (Documentation Quality Index)**: Score (0-100) measuring documentation completeness and quality

**Run Attribution**: Linking findings to the specific run that discovered them

**Suppression**: Temporarily or permanently hiding a finding (with reason and scope)

**Bulk Triage**: Applying triage actions to multiple findings at once

**Metrics Dashboard**: Analytics UI showing finding trends, severity distribution, etc.

**Telemetry**: Observability data (logs, metrics, traces) for monitoring system health

**Sandbox**: Isolated execution environment for plugins (subprocess with resource limits)

---

## GitHub Issues — Paste-Ready Format

```markdown
### Runtime Core

- [ ] **FEAT-001**: Create core-lib package structure [feat, M1, core] — 2d
- [ ] **FEAT-002**: Define port interfaces (StoragePort, ToolPort, ResourcePort) [feat, M1, core] — 2d
- [ ] **FEAT-003**: Implement in-memory storage adapter [feat, M1, storage] — 1d
- [ ] **FEAT-004**: Implement file-backed storage adapter [feat, M1, storage] — 3d
- [ ] **FEAT-005**: Add Finding model validation [feat, M1, core] — 1d

### Tool Wrappers

- [ ] **FEAT-006**: Create abstract ToolWrapper protocol [feat, M2, wrappers] — 2d
- [ ] **FEAT-007**: Implement NucleiWrapper [feat, M2, wrappers] — 3d
- [ ] **FEAT-008**: Implement FeroxWrapper [feat, M2, wrappers] — 2d
- [ ] **FEAT-009**: Implement KatanaWrapper [feat, M2, wrappers] — 2d
- [ ] **FEAT-010**: Create tool manifest schema [feat, M2, wrappers] — 1d

### Findings Engine

- [ ] **FEAT-011**: Migrate normalization layer [feat, M2, findings] — 2d
- [ ] **FEAT-012**: Create parser adapters registry [feat, M2, findings] — 2d
- [ ] **FEAT-013**: Add enrichment hooks [feat, M2, findings] — 2d

### Workflow Engine

- [ ] **FEAT-014**: Create workflow recipe schema [feat, M3, workflow] — 2d
- [ ] **FEAT-015**: Implement DAG executor [feat, M3, workflow] — 4d
- [ ] **FEAT-016**: Add workflow persistence [feat, M3, workflow] — 2d

### Resource Registry

- [ ] **FEAT-017**: Create ResourceRegistry interface [feat, M3, resources] — 2d
- [ ] **FEAT-018**: Implement wordlist provider [feat, M3, resources] — 2d
- [ ] **FEAT-019**: Implement template provider [feat, M3, resources] — 2d

### Plugin System

- [ ] **FEAT-020**: Create plugin loader [feat, M4, plugins] — 3d
- [ ] **FEAT-021**: Implement CVEMapper plugin [feat, M4, plugins] — 2d
- [ ] **FEAT-022**: Implement RiskScorer plugin [feat, M4, plugins] — 2d
- [ ] **FEAT-023**: Add plugin sandboxing [feat, M4, plugins, security] — 3d

### Observability

- [ ] **FEAT-024**: Setup structured logging [feat, M5, observability] — 2d
- [ ] **FEAT-025**: Add Prometheus metrics [feat, M5, observability] — 2d
- [ ] **FEAT-026**: Implement error recovery patterns [feat, M5, observability] — 2d

### Documentation

- [ ] **FEAT-027**: Integrate mkdocstrings [feat, M6, docs] — 2d
- [ ] **FEAT-028**: Add docstring coverage gate [chore, M6, docs] — 1d
- [ ] **FEAT-029**: Write migration guide [docs, M6] — 2d

### CI/CD

- [ ] **FEAT-030**: Create staging deploy workflow [chore, M3, ci] — 3d
- [ ] **FEAT-031**: Add import-linter gate [chore, M1, ci] — 1d
- [ ] **FEAT-032**: Add performance benchmarks [chore, M2, ci] — 2d

### Testing

- [ ] **FEAT-033**: Create integration test fixtures [test, M1] — 2d
- [ ] **FEAT-034**: Add contract tests for ports [test, M1] — 2d
- [ ] **FEAT-035**: Create end-to-end test suite [test, M3] — 3d

### Refactoring

- [ ] **CHORE-036**: Migrate findings.py to core-lib [chore, M1] — 3d
- [ ] **CHORE-037**: Migrate nuclei_integration.py to wrappers [chore, M2] — 3d
- [ ] **CHORE-038**: Migrate store.py to storage package [chore, M1] — 3d

### Security

- [ ] **FEAT-039**: Add secrets management [feat, security, M4] — 2d
- [ ] **FEAT-040**: Implement RBAC middleware [feat, security, M3] — 3d
```

---

## Ready to Start M1 — Checklist

Before starting M1 implementation, ensure:

- [ ] This execution plan reviewed and approved by team
- [ ] CODEOWNERS file created and merged to main
- [ ] Branch protection rules configured on GitHub
- [ ] All 40 issues created in GitHub project board
- [ ] Team roles assigned (@runtime-lead, @tools-lead, etc.)
- [ ] Development environment setup documented
- [ ] CI workflow skeletons added (even if jobs are empty initially)
- [ ] Kickoff meeting scheduled (review architecture docs)
- [ ] Mermaid/ASCII gates currently green (`make health` passes)
- [ ] Poetry/pyproject.toml skeleton exists or planned for first PR
- [ ] Slack/Discord channel created for team coordination
- [ ] Documentation repo backup created (in case of rollback)

**Once checklist complete**: Open first PR for `FEAT-001` (Create core-lib package structure)

---

## Notes

- All tasks kept to ≤2 days effort (split larger work across issues)
- Every task has acceptance criteria and "done" signal
- Documentation changes require `make health` to pass
- Security-sensitive changes require @security-lead review
- Prefer explicit interfaces (ports) before implementations
- Test coverage requirement: 80%+ on all new code
- No breaking changes to existing routes during migration (compatibility layers)
- Migration from legacy code happens gradually (parallel implementations)
- Plugin system designed for security from day 1 (sandboxing, validation)
- Observability built-in (not bolted on later)

**End of Plan**


### To-dos

- [ ] Complete M0: Pre-flight & Planning (validate plan, create issues, assign owners)
- [ ] Complete M1: Runtime Skeleton (core-lib, ports, storage adapters)
- [ ] Complete M2: Tool Wrappers & Findings Engine (standardize tool integration)
- [ ] Complete M3: Workflow Engine & Resource Registry (DAG execution, staging deploy)
- [ ] Complete M4: Plugin System & Enrichment (CVE/CWE mapper, sandboxing)
- [ ] Complete M5: Observability & Error Handling (logging, metrics, recovery)
- [ ] Complete M6: API Docs & Migration Polish (mkdocstrings, migration guide, v1.0.0)