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

```text
┌─────────────────────────────────────────────┐
|                Developer                    |
|─────────────────────────────────────────────│
| Commit / PR → GitHub Repository             |
| ↓                                           |
| GitHub Actions CI Workflow                 |
| - Lint (Ruff)                               |
| - Type Check (Pyright)                      |
| - Test (Pytest Matrix)                     |
| - Build (Poetry / Docker)                   |
| ↓                                           |
| Artifacts Published → Container Registry    |
| ↓                                           |
| CD Pipeline (Staging → Production)         |
└─────────────────────────────────────────────┘
```yaml

---

## 🧱 CI Pipeline Structure

### Files
```text
.github/
├── workflows/
│   ├── ci.yml           # Main build & test pipeline
│   ├── lint.yml         # Fast linting PR checks
│   ├── deploy.yml       # CD pipeline to staging/prod
│   ├── nightly.yml      # Nightly validation builds
│   └── security-scan.yml # Dependency & container scanning
```yaml

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

```text
tests/
├── core/
│   ├── test_models.py
│   ├── test_utils.py
│   └── test_ports.py
├── wrappers/
│   ├── test_nuclei_wrapper.py
│   ├── test_ferox_wrapper.py
│   └── test_zap_wrapper.py
├── plugins/
│   ├── test_cve_enrichment.py
│   └── test_risk_scoring.py
├── api/
│   ├── test_projects_api.py
│   ├── test_findings_api.py
│   └── test_workflow_api.py
└── e2e/
    └── test_workflow_dag_execution.py
```yaml

---

## 🧮 CI Matrix Configuration Example

```yaml
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
```yaml

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
```yaml
- name: Deploy to Staging
  run: |
    docker-compose -f docker-compose.staging.yml up -d
    pytest tests/e2e/ --maxfail=1
```yaml

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

```bash
pip install pip-audit safety gitleaks trivy
make security-scan
```text

## 🔄 Regression & Replay Testing

Each workflow run can be recorded and replayed for regression tests.
This ensures stability across version upgrades.

### Example:
```bash
pytest tests/e2e/test_workflow_dag_execution.py --record
pytest --replay last-run
```bash

Replay data is stored under `/tests/artifacts/replays/`.

## 🧰 Local Developer Testing

Developers can run lightweight tests locally:

```bash
make test
pytest -k "not e2e"
```bash

With Docker-enabled integration tests:
```bash
make test-docker
```text

## 📊 Metrics & Reporting

After each CI build:
- Coverage report published to Codecov
- Lint/type results annotated in GitHub PR
- Performance metrics logged to Prometheus

### Example coverage badge:
```text
[![Coverage](https://img.shields.io/badge/coverage-93%25-brightgreen)](https://codecov.io/gh/SecFlow)
```text

## 🧱 Disaster Recovery & Rollback

Every deployment is versioned:
- Docker image tags = `vX.Y.Z-buildhash`

### Rollback command:
```bash
docker pull SecFlow-api:v1.3.2
docker compose up -d --no-build
```

- Database snapshots every 6h during staging deployment

## 🔮 Future Enhancements

- Integration with GitHub Advanced Security (code scanning)
- Dynamic Test Selection (test impacted code only)
- Chaos Testing on worker queue reliability
- Parallelized build matrix using GitHub Actions caching

---

**Next:** [Developer Experience & Documentation Plan](22-developer-experience-and-docs.md)
