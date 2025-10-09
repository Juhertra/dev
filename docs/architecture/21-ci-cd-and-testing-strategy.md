---
title: "SecFlow — CI/CD and Testing Strategy"
author: "Hernan Trajtemberg, Lead Security Engineer"
codename: "SecFlow"
version: "1.0"
date: "2025-10-06"
---

# 21 — CI/CD and Testing Strategy

## 🧭 Overview

The CI/CD and testing strategy ensures SecFlow maintains high reliability, reproducibility, and security compliance across all modules.  
It defines automated pipelines for build validation, testing, linting, packaging, and deployment to staging and production.

SecFlow's architecture enables modular CI pipelines for **packages** (core-lib, storage, wrappers, plugins) and **apps** (web-api, worker, triage-ui).

---

## ⚙️ CI/CD Architecture Diagram

```mermaid
%%{init: {"theme":"neutral"}}%%
flowchart TD
    A["Developer"]
    B["Commit / PR → GitHub Repository"]
    C["GitHub Actions CI Workflow<br/>- Lint (Ruff)<br/>- Type Check (Pyright)<br/>- Test (Pytest Matrix)<br/>- Build (Poetry / Docker)"]
    D["Artifacts Published → Container Registry"]
    E["CD Pipeline (Staging → Production)"]
    
    A --> B
    B --> C
    C --> D
    D --> E
```

---

## 🧱 CI Pipeline Structure

### Files
```
.github/
```

```mermaid
%%{init: {"theme":"neutral"}}%%
flowchart TD
    A["workflows/"]
    B["ci.yml<br/>(Main build & test pipeline)"]
    C["lint.yml<br/>(Fast linting PR checks)"]
    D["deploy.yml<br/>(CD pipeline to staging/prod)"]
    E["nightly.yml<br/>(Nightly validation builds)"]
    F["security-scan.yml<br/>(Dependency & container scanning)"]
    
    A --> B
    A --> C
    A --> D
    A --> E
    A --> F
```

### Environments
- **dev** → local or containerized build  
- **staging** → auto-deployed for QA validation  
- **production** → manual approval required  

---

## 🧪 Test Taxonomy

| Level | Scope | Example |
|--------|--------|---------|
| **Unit Tests** | Function-level logic validation | Testing CVSS normalization, config parsing |
| **Integration Tests** | Module interoperability | NucleiWrapper + FindingsEngine |
| **Functional Tests** | End-to-end system behavior | Workflow execution pipeline |
| **Regression Tests** | Legacy feature coverage | Old project import/export |
| **Performance Tests** | Latency and scalability | Parallel scan runs |
| **Security Tests** | Dependency & vulnerability checks | Pip-audit, Trivy |

---

## 🧩 Test Framework Stack

| Tool | Purpose |
|------|----------|
| **pytest** | Primary test runner |
| **pytest-asyncio** | Async tests for API and worker |
| **pytest-cov** | Coverage reports |
| **tox** | Matrix execution (Python 3.10–3.12) |
| **httpx** | HTTP API test client |
| **sqlite-memory** | Fast ephemeral DB backend for testing |
| **faker** | Generate synthetic test data |
| **pytest-docker** | Integration tests for containerized tools |

---

## 🧱 Test Folder Structure

```
tests/
```

```mermaid
%%{init: {"theme":"neutral"}}%%
flowchart TD
    A["tests/"]
    B["core/"]
    C["test_models.py"]
    D["test_utils.py"]
    E["test_ports.py"]
    F["wrappers/"]
    G["test_nuclei_wrapper.py"]
    H["test_ferox_wrapper.py"]
    I["test_zap_wrapper.py"]
    J["plugins/"]
    K["test_cve_enrichment.py"]
    L["test_risk_scoring.py"]
    M["api/"]
    N["test_projects_api.py"]
    O["test_findings_api.py"]
    P["test_workflow_api.py"]
    Q["e2e/"]
    R["test_workflow_dag_execution.py"]
    
    A --> B
    A --> F
    A --> J
    A --> M
    A --> Q
    B --> C
    B --> D
    B --> E
    F --> G
    F --> H
    F --> I
    J --> K
    J --> L
    M --> N
    M --> O
    M --> P
    Q --> R
```

---

## 🧮 CI Matrix Configuration Example

```
# .github/workflows/ci.yml
name: CI
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build-test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [ "3.10", "3.11", "3.12" ]
        database: [ "sqlite", "postgres" ]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install poetry
      - run: poetry install
      - run: make lint
      - run: make test DB=${{ matrix.database }}
      - run: pytest --cov=src --cov-report=xml
```

## 🧠 Deployment Pipeline

### Staging Pipeline (Continuous Deployment)
- Triggered on merge to main
- Deploys to staging environment automatically
- Runs post-deploy smoke tests:
  - `/healthz` endpoint
  - Workflow execution sanity test

### Production Pipeline
- Requires manual approval (`workflow_dispatch`)
- Signs Docker images before publishing
- Deploys to Kubernetes or Docker Swarm cluster
- Monitors deployment via Prometheus metrics

### Example job snippet:
```
- name: Deploy to Staging
  run: |
    docker-compose -f docker-compose.staging.yml up -d
    pytest tests/e2e/ --maxfail=1
```

## 🧰 Build Artifacts & Packages

| Type | Output | Destination |
|------|--------|-------------|
| Python Wheels | `dist/*.whl` | PyPI private index |
| Docker Images | `SecFlow-api`, `SecFlow-worker` | Container registry |
| Reports | `coverage.xml`, `lint.txt`, `typecheck.json` | GitHub artifacts |
| Documentation | mkdocs `site/` | GitHub Pages |

## 🧠 Quality Gates

| Check | Tool | Threshold |
|-------|------|-----------|
| Linting | Ruff | No errors |
| Type Checking | Pyright | 100% coverage |
| Test Coverage | Pytest + Coverage | > 90% |
| Dependency Scan | Pip-audit / Trivy | 0 Critical |
| Build Size | Docker | < 400 MB per image |

Failed gates block merges automatically.

## 🧪 Continuous Security Testing

- **Dependency Auditing:** via pip-audit and Safety
- **Container Scanning:** via Trivy in CI
- **Secrets Detection:** via gitleaks pre-commit hook
- **Infrastructure Scan:** via tfsec (for IaC configs)

```
pip install pip-audit safety gitleaks trivy
make security-scan
```

## 🔄 Regression & Replay Testing

Each workflow run can be recorded and replayed for regression tests.
This ensures stability across version upgrades.

### Example:
```
pytest tests/e2e/test_workflow_dag_execution.py --record
pytest --replay last-run
```

Replay data is stored under `/tests/artifacts/replays/`.

## 🧰 Local Developer Testing

Developers can run lightweight tests locally:

```
make test
pytest -k "not e2e"
```

With Docker-enabled integration tests:
```
make test-docker
```

## 📊 Metrics & Reporting

After each CI build:
- Coverage report published to Codecov
- Lint/type results annotated in GitHub PR
- Performance metrics logged to Prometheus

### Example coverage badge:
```
[![Coverage](https://img.shields.io/badge/coverage-93%25-brightgreen)](https://codecov.io/gh/SecFlow)
```

## 🧱 Disaster Recovery & Rollback

Every deployment is versioned:
- Docker image tags = `vX.Y.Z-buildhash`

### Rollback command:
```
docker pull SecFlow-api:v1.3.2
docker compose up -d --no-build
```

- Database snapshots every 6h during staging deployment

## 🔒 Contract Testing

Contract tests ensure data integrity and API compatibility across system boundaries. They validate invariants that must hold true regardless of implementation changes.

### Contract Test Categories

| Category | Purpose | Location | Example |
|----------|---------|----------|---------|
| **Finding Invariants** | Validate finding data structure | `tests/contracts/test_finding_invariants.py` | Detector ID regex, UTC timestamps |
| **Storage Layout** | Validate data persistence format | `tests/contracts/test_storage_layout.py` | Schema version, file structure |

### Finding Invariants Contract

**Purpose:** Ensure findings conform to expected data structure and format requirements.

**Key Validations:**
- Detector IDs match pattern: `^[A-Za-z0-9_.-]+$`
- Timestamps are ISO 8601 UTC format ending with 'Z'
- Required fields are present and properly typed

**Test Structure:**
```python
# Positive cases - valid data should pass
def test_detector_id_regex_valid():
    assert DETECTOR_RE.match("EXAMPLE_1")

# Negative cases - invalid data should fail  
def test_detector_id_regex_invalid():
    assert not DETECTOR_RE.match("invalid:id")

# Future implementation stubs
@pytest.mark.xfail(reason="Implementation pending")
def test_finding_schema_validation():
    # Will pass when schema validation is implemented
```

### Storage Layout Contract

**Purpose:** Ensure data persistence maintains expected structure and versioning.

**Key Validations:**
- Schema version field present and valid format
- File structure supports expected operations
- Backward compatibility for data migration

**Test Structure:**
```python
# Happy path - valid storage layout
def test_store_layout_has_schema_version(tmp_path):
    data = {"store_schema_version": "1.0.0"}
    assert "store_schema_version" in data

# Edge cases - missing or invalid versions
def test_store_layout_missing_schema_version(tmp_path):
    data = {"detector_id": "test"}
    assert "store_schema_version" not in data
```

### Contract Test Execution

Run contract tests independently:
```bash
# Run all contract tests
pytest tests/contracts/ -q

# Run specific contract category
pytest tests/contracts/test_finding_invariants.py -q
pytest tests/contracts/test_storage_layout.py -q
```

### Contract Test Principles

1. **Fail Fast:** Contract tests should fail immediately when invariants are violated
2. **Implementation Agnostic:** Tests validate contracts, not implementation details
3. **Future-Proof:** Use `@pytest.mark.xfail` for pending implementations
4. **Comprehensive Coverage:** Include both positive and negative test cases
5. **Clear Documentation:** Each test explains the contract being validated

### Integration with CI/CD

Contract tests run in the main CI pipeline:
```yaml
- name: Run Contract Tests
  run: pytest tests/contracts/ --tb=short
```

They provide early warning when:
- Data format changes break compatibility
- Schema evolution violates existing contracts
- New implementations don't meet contract requirements

## 🔮 Future Enhancements

- Integration with GitHub Advanced Security (code scanning)
- Dynamic Test Selection (test impacted code only)
- Chaos Testing on worker queue reliability
- Parallelized build matrix using GitHub Actions caching

---

**Next:** [Developer Experience & Documentation Plan](22-developer-experience-and-docs.md)
```
```
```
```
```
```
```
```
```
```
```
```
```
```
```
```
```
```
```
```