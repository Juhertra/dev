---
title: "SecFlow — Migration & Implementation Phases"
author: "Hernan Trajtemberg, Lead Security Engineer"
codename: "SecFlow"
version: "1.0"
date: "2025-10-06"
---

# 20 — Migration & Implementation Phases

## 🧭 Overview

The migration plan defines a **controlled, four-phase rollout** of SecFlow's refactored architecture — from scaffolding and core model setup to the full orchestration of tools, UI, and enrichment.

This plan emphasizes:
- **Incremental refactoring** (no big-bang rewrite)
- **Zero architectural drift** (guardrails first)
- **Progressive integration** (tools, plugins, UI)
- **Data isolation and cleanup** (garbage collector enabled)

---

## 📦 Phase 0 — Foundation & Guardrails (Week 1)

### Objective
Establish the new repository structure and enforce architectural discipline before any migration work.

### Tasks
- Create **mono-repo scaffold** under `/src/SecFlow/`
- Add **dev environment setup** via `Makefile`, `pyproject.toml`, and Poetry
- Enable **static analysis tooling**:
  - `ruff` for linting  
  - `pyright` for typing  
  - `import-linter` for import boundaries
- Setup **unit testing** scaffold: `/tests/core`, `/tests/wrappers`, `/tests/plugins`
- Define `.github/workflows/ci.yml` for matrix builds (Python 3.10–3.12)
- Establish base **docs/architecture/** folder for ongoing documentation

### Expected Deliverables
- Working mono-repo with guardrails
- CI passing with lint/type/test checks
- Developer guide for environment setup (`docs/dev-setup.md`)

### Example Command
```bash
make init
make lint
make test
```python

## 🧱 Phase 1 — Core Models & Data Persistence (Week 2)

### Objective
Move fundamental entities (Projects, Findings, Resources, Runs) into modular core-lib and storage packages.

### Tasks
- Create `core-lib/` package:
  - Models for Project, Finding, Resource, Run
  - Pydantic schemas for DTOs
- Create `storage/` package:
  - Database adapters for SQLite (local) and PostgreSQL (production)
  - Repository interfaces (IProjectRepo, IFindingsRepo, etc.)
  - Alembic or SQLModel migrations
- Implement CRUD API endpoints:
  - `/api/v1/projects`
  - `/api/v1/findings`
  - `/api/v1/resources`
- Add test fixtures for sample data

### Expected Deliverables
- Persistent data layer
- Core models validated by schema
- Functional CRUD endpoints
- 80%+ test coverage on models and repos

### Example Model
```python
class Project(BaseModel):
    id: UUID
    name: str
    owner: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
```python

## ⚙️ Phase 2 — Findings Engine, Wrappers & Workflow (Week 3)

### Objective
Integrate scanning tools (Nuclei, Feroxbuster, Katana, etc.) into the new workflow engine and plugin registry.

### Tasks
- Implement `findings-engine/`:
  - Normalization layer for all scanners
  - Parser adapters for each tool
- Implement `wrappers/`:
  - NucleiWrapper, FeroxWrapper, ZAPWrapper
  - Each using standardized manifest + sandbox
- Create `plugins/` package:
  - Detection and enrichment plugins (e.g., CVEMapper, RiskScorer)
- Build workflow engine with DAG executor:
  - YAML recipe parsing
  - Input/output data mapping
  - Caching and persistence
- Integrate tool registry UI in web frontend

### Expected Deliverables
- Tool registry and manifest system
- Workflow DAG execution engine
- Normalized findings output (JSON schema compliant)
- Risk engine integration (Phase 1 of enrichment)

### Example Wrapper Interface
```python
class ToolWrapper(Protocol):
    def prepare(self, config: Dict[str, Any]) -> None:
        """Prepare tool with configuration."""
        pass
    
    def run(self) -> ToolOutput:
        """Execute tool and return output."""
        pass
    
    def parse_output(self, raw: str) -> List[Finding]:
        """Parse raw output into findings."""
        pass
```python

## 🌐 Phase 3 — API, Worker, and Triage UI (Week 4)

### Objective
Deliver full orchestration capability through APIs, background workers, and a lightweight HTMX/React UI.

### Tasks
- Create `web-api/`:
  - REST endpoints for workflows, findings, triage
  - WebSocket for live updates
- Create `worker/`:
  - Celery/asyncio-based job processor
  - Queues for workflow nodes and enrichment
- Create `triage-ui/`:
  - Interactive HTMX dashboard for findings triage
  - Tabs: "Projects", "Findings", "Tools", "Metrics"
- Implement user auth & RBAC
  - JWT + role middleware
- Add audit logging for all changes
- Integrate observability stack (Prometheus, OpenTelemetry)

### Expected Deliverables
- Full end-to-end scan → finding → triage pipeline
- Live progress dashboard
- Role-based access and logging
- Metrics export for dashboards

### Example Endpoint
```python
@app.post("/api/v1/workflows/run")
async def run_workflow(workflow_id: str):
    job_id = await worker.enqueue(workflow_id)
    return {"status": "queued", "job_id": job_id}
```yaml

## 🧹 Phase 4 — Garbage Collection, AI, and Advanced Analytics (Week 5+)

### Objective
Introduce garbage collection, retention policy enforcement, and AI-assisted triage.

### Tasks
- Implement GarbageCollector service:
  - Sweep orphaned runs and findings
  - Archive logs >30 days
- Introduce CVE/CWE/PoC Enrichment
  - Integration with NVD, OSV, ExploitDB
- Deploy AI assistant for:
  - Finding summaries
  - Risk triage automation
  - Workflow suggestions
- Add cross-project analytics dashboard
- Implement export formats (PDF, CSV, JSON)

### Expected Deliverables
- Fully production-ready orchestration platform
- Retention-safe data lifecycle
- AI triage beta enabled
- Analytics module complete

## 📈 Migration Timeline Overview

| Week | Phase | Key Deliverables |
|------|-------|------------------|
| 1 | Phase 0 — Scaffold | Repo, linting, CI/CD, guardrails |
| 2 | Phase 1 — Core | Models, DB, CRUD API |
| 3 | Phase 2 — Engine | Wrappers, Plugins, Workflow |
| 4 | Phase 3 — API/UI | Worker, Triage UI, Auth |
| 5+ | Phase 4 — AI/GC | Retention, Enrichment, Analytics |

## 🚀 Deployment Strategy

- Branch-per-phase workflow (`feature/phase-1-core`, etc.)
- Pre-merge CI enforcement for all phases
- Feature flags for new modules
- Nightly build for cross-validation
- Docker-compose dev stack for quick testing

### Example Command
```bash
docker compose up -d
pytest --maxfail=1 --disable-warnings
```

## 🧠 Key Success Metrics

| Metric | Target |
|--------|--------|
| Test Coverage | >90% for core-lib & storage |
| CI Lint Pass Rate | 100% |
| Workflow Execution Latency | <300ms/node avg |
| Risk Score Accuracy | ±5% of reference |
| Mean Time to Deploy | <10 min via CI/CD |

## 🔮 Next Steps

After migration completion:
- Freeze legacy JSON-store modules.
- Enable CVE/PoC enrichment.
- Integrate AI triage assistant.
- Conduct internal red-team testing.
- Prepare open-source release structure.

---

**Next:** [CI/CD & Testing Strategy](21-ci-cd-and-testing-strategy.md)
