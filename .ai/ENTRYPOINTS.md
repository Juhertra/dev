# Entrypoints

Evidence policy matches REPO_MAP.json: confirmed / inferred / uncertain.

---

## Primary Entrypoints Summary

| Path | Kind | Track | Start Hint | Confidence |
|---|---|---|---|---|
| `app.py` | Flask dev server | Legacy App | `python app.py` | confirmed |
| `wsgi.py` | WSGI entrypoint | Legacy App | WSGI server points at `wsgi:app` | confirmed |
| `pattern_cli.py` | CLI | Legacy App | `python pattern_cli.py` | confirmed |
| `tools/run_workflow.py` | CLI | Orchestrator | `python tools/run_workflow.py <recipe.yaml> [--dry-run]` | confirmed |
| `tools/validate_recipe.py` | CLI | Orchestrator | `python tools/validate_recipe.py <recipe.yaml>` | confirmed |
| `tools/workflow_to_mermaid.py` | CLI / utility | Orchestrator | `python tools/workflow_to_mermaid.py <recipe.yaml>` | confirmed |
| `init_asvs.py` | Setup script | Legacy App | `python init_asvs.py` | confirmed |

---

## Execution Flow Overview

### Legacy App Flow (confirmed)
1. WSGI server or `python app.py` calls `create_app()` in `app.py`.
2. `create_app()` registers `web_bp` (from `web_routes.py`) and `api_bp` (from `api_endpoints.py`; prefix `/api/v1`).
3. `routes/__init__.py` registers 12 modular route handlers on `web_bp`.
4. Flask route receives a request and calls helpers in `store.py`, `findings.py`, or scanner modules.
5. Findings are normalized via `normalize_finding()` then written via `append_findings()`.
6. Cache-bust (`_bust_vulns_cache()`) and metrics-rebuild hooks execute after write.
7. UI/API responds from persisted state in `ui_projects/`.

### Orchestrator Track Flow (historical / post-split)
1. Historical CLI files (`tools/run_workflow.py`, `tools/validate_recipe.py`, `tools/workflow_to_mermaid.py`) still exist in `Juhertha/dev`.
2. The orchestrator package implementations they depended on were extracted to `Juhertha/secflow-orchestrator` during Gate D.
3. `Juhertha/dev` no longer carries `packages/runtime_core/`, `packages/storage/`, `packages/wrappers/`, or `packages/workflow_engine/` on `main`.
4. Treat these CLIs as file references only in `Juhertha/dev`; active orchestrator execution and validation live in `Juhertha/secflow-orchestrator`.

---

## Non-Entrypoint Rule

The following are **package modules** — they are imported by other code and are not intended for direct invocation.

Historical note: orchestrator package modules under `packages/runtime_core/`, `packages/storage/`, `packages/wrappers/`, and `packages/workflow_engine/` were extracted to `Juhertha/secflow-orchestrator` and are absent from `Juhertha/dev` main.

- `store.py`, `findings.py`, `core.py`, `cache.py`, `config.py`, `nuclei_wrapper.py`, `nuclei_integration.py`
- `utils/findings_normalize.py` (has a `__main__` block, but it only runs `doctest.testmod()` — not a CLI)
- `utils/dossier_management.py` (has a `__main__` block, but it runs a hardcoded one-off test — not a general CLI)
- `packages/wrappers/manifest.py` (has a `__main__` block, but it runs example usage — not a general CLI)

These files should be imported, not executed directly. The `__main__` guards present in some are development or doctest artifacts.

---

## 1. Legacy App — Runtime Entrypoints

### `app.py`
- **Kind:** Flask development server
- **Start:** `python app.py` (binds port 5001)
- **Role:** Application factory (`create_app()`); registers `web_bp` from `web_routes.py` and `api_bp` from `api_endpoints.py`; dev-only fallback API key `test-key-123`.
- **sys.path:** None.
- **Confidence:** confirmed

### `wsgi.py`
- **Kind:** WSGI production entrypoint
- **Start:** Point WSGI server (e.g. gunicorn) at `wsgi:app`
- **Role:** Imports `create_app` from `app.py`; creates and exposes the application object for production servers.
- **sys.path:** None.
- **Confidence:** confirmed

---

## 2. CLI Entrypoints (argparse, direct invocation)

### `pattern_cli.py`
- **Kind:** CLI
- **Start:** `python pattern_cli.py`
- **Role:** Pattern management CLI for the Legacy App.
- **sys.path:** `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` at line 10 — inserts own directory (not repo root).
- **Confidence:** confirmed

### `tools/run_workflow.py`
- **Kind:** Orchestrator CLI
- **Start:** `python tools/run_workflow.py <recipe.yaml> [--dry-run]`
- **Role:** Loads a workflow YAML and calls `packages/workflow_engine/executor.py`; handles `not_implemented` status gracefully (lines 113–116).
- **sys.path:** `sys.path.insert(0, str(Path(__file__).parent.parent))` at line 16 — inserts repo root. **Split-sensitive.**
- **Confidence:** confirmed

### `tools/validate_recipe.py`
- **Kind:** Orchestrator CLI
- **Start:** `python tools/validate_recipe.py <recipe.yaml>`
- **Role:** Validates a workflow YAML recipe. Contains real DAG dependency checking at lines 54–63 (checks unresolved inputs against all node outputs). Distinct from the scaffold-level stub in `packages/workflow_engine/validate_recipe.py`.
- **sys.path:** `sys.path.insert(0, str(Path(__file__).parent.parent))` at line 15 — inserts repo root. **Split-sensitive.**
- **Confidence:** confirmed

### `tools/workflow_to_mermaid.py`
- **Kind:** CLI / utility
- **Start:** `python tools/workflow_to_mermaid.py <recipe.yaml>`
- **Role:** Converts a YAML workflow recipe to a Mermaid flowchart diagram.
- **sys.path:** Not confirmed.
- **Confidence:** confirmed (has `__main__` guard; role inferred from name and usage in CI gate)

### `tools/run_scan.py`
- **Kind:** CLI
- **Start:** `python tools/run_scan.py`
- **Role:** Scan runner; exact argparse interface not confirmed.
- **sys.path:** Not confirmed.
- **Confidence:** inferred (has `__main__` guard; detailed interface not read)

### `init_asvs.py`
- **Kind:** Setup script
- **Start:** `python init_asvs.py`
- **Role:** Registers ASVS Nuclei templates into the application.
- **sys.path:** `sys.path.insert(0, os.path.dirname(__file__))` at line 11 — inserts own directory.
- **Confidence:** confirmed

---

## 3. Scripts (operational, one-time, or CI)

All scripts in `scripts/` use `sys.path.insert` to add the repo root. All are **split-sensitive** if the split changes the repo root layout.

| File | Role | Confidence |
|---|---|---|
| `scripts/export_findings_report.py` | Exports findings report (P6 export CLI) | confirmed |
| `scripts/migrate_legacy_findings.py` | Migrates legacy findings data (P3) | confirmed |
| `scripts/rebuild_vulns_caches.py` | Rebuilds vulnerability caches (P3) | confirmed |
| `scripts/backfill_run_info.py` | Backfills missing Nuclei run info (P3) | confirmed |
| `scripts/backfill_triage_defaults.py` | Backfills triage default values | confirmed |
| `scripts/migrate_cve_placeholders.py` | One-time CVE placeholder cleanup | confirmed |
| `scripts/benchmark_parsers.py` | Parser performance benchmark (M2 target) | confirmed |
| `scripts/ci_gate.py` | CI gate check for Mermaid docs | confirmed |
| `scripts/coverage_ratchet.py` | Enforces milestone coverage targets (M0=18% … M6=90%) | confirmed |
| `scripts/demo_inmemory_store.py` | Development demo for in-memory storage adapter | confirmed |

---

## 4. Package Modules — Imported, Not Directly Executed

These are historical package-module references for the extracted Orchestrator Track. They are not present on `Juhertha/dev` main and were moved to `Juhertha/secflow-orchestrator`.

| Module | Role | Confidence |
|---|---|---|
| `packages/runtime_core/storage/storage_port.py` | Moved to `Juhertha/secflow-orchestrator`; absent from `Juhertha/dev` main | confirmed |
| `packages/storage/adapters/memory.py` | Moved to `Juhertha/secflow-orchestrator`; absent from `Juhertha/dev` main | confirmed |
| `packages/wrappers/base.py` | Moved to `Juhertha/secflow-orchestrator`; absent from `Juhertha/dev` main | confirmed |
| `packages/workflow_engine/executor.py` | Moved to `Juhertha/secflow-orchestrator`; absent from `Juhertha/dev` main | confirmed |
| `packages/workflow_engine/validate_recipe.py` | Moved to `Juhertha/secflow-orchestrator`; absent from `Juhertha/dev` main | confirmed |
| `store.py` | Project/runtime state; JSON storage under `ui_projects/`; `RUNTIMES` in-process dict | confirmed |
| `findings.py` | Finding validation and storage; `normalize_finding()` → `append_findings()` pipeline | confirmed |
| `core.py` | Atomic JSON read/write helpers | confirmed |
| `cache.py` | In-process TTL dict; `cached()` decorator | confirmed |
| `config.py` | Reads/writes `app_config.json` | confirmed |
| `nuclei_wrapper.py` | Nuclei binary subprocess wrapper; `NucleiResult` dataclass | confirmed |
| `nuclei_integration.py` | Converts Nuclei results to findings; CVE validation | confirmed |

---

## 5. Utility `__main__` Guards — Not General CLIs

These files have `if __name__ == "__main__"` blocks but are not general-purpose CLIs.

| File | Behavior | Confidence |
|---|---|---|
| `utils/findings_normalize.py` | Runs `doctest.testmod()` — doctest runner only | confirmed |
| `utils/dossier_management.py` | Runs a hardcoded one-off test with a specific UUID project ID — not a general CLI | confirmed |
| `packages/wrappers/manifest.py` | Runs example usage — not a general CLI | confirmed |

---

## 6. Development / Proof-of-Concept Scripts

These scripts exist for development verification and are not part of the operational workflow.

| File | Role | Confidence |
|---|---|---|
| `tools/prove_runs_and_sse.py` | Proof script for run and SSE behavior | inferred |
| `tools/phase1_verify.py` | Phase 1 verification script | inferred |
| `tools/petstore_proof.py` | Petstore API proof script | inferred |
| `tools/proof_final.py` | Final proof verification | inferred |
| `tools/proof_phase2.py` | Phase 2 proof verification | inferred |

---

## 7. Test and Quality Commands (Makefile)

Not direct entrypoints but the canonical way to invoke tests and quality checks.

| Command | Role | Confidence |
|---|---|---|
| `make test` | Full test suite | confirmed |
| `make unit` | Unit tests only | confirmed |
| `make quick-test` | Fast subset (used in pre-commit) | confirmed |
| `make coverage` | Test coverage report | confirmed |
| `make lint` | Ruff linting | confirmed |
| `make type` | Pyright type checking | confirmed |
| `make imports` | import-linter boundary check | confirmed |
| `make health` | Application health check | confirmed |

---

## Split-Sensitivity Summary

Split lifecycle is complete (Gates A-E, 2026-03-17).

- `Juhertha/dev` is now legacy-only.
- Orchestrator packages were extracted to `Juhertha/secflow-orchestrator`.
- Pre-split `sys.path` portability risk was resolved by P062 before Gate D completed.
- Residual historical CLI files in `Juhertha/dev` should be treated as file references, not active orchestrator entrypoints.
