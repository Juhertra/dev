# Repository Brain

## Architecture Overview

### Legacy App (confirmed)
- `app.py` creates Flask app and registers:
  - web blueprint from `web_routes.py`
  - API blueprint from `api_endpoints.py`
- `routes/__init__.py` registers modular route handlers on the web blueprint.
- `store.py` manages project/runtime state and local JSON storage under `ui_projects/`.
- `findings.py` validates and stores findings with schema checks and rolling cap behavior.
- `nuclei_wrapper.py` and `nuclei_integration.py` provide Nuclei scan execution and result conversion.

### Orchestrator Track (extracted)
- Orchestrator packages were extracted to `Juhertha/secflow-orchestrator` during Gate D.
- `packages/runtime_core/`, `packages/storage/`, `packages/wrappers/`, and `packages/workflow_engine/` are absent from `Juhertha/dev` main.
- `tools/run_workflow.py`, `tools/validate_recipe.py`, and `tools/workflow_to_mermaid.py` remain as legacy file references, but their package dependencies now live in `Juhertha/secflow-orchestrator`.

## Execution Flow (Current)

### Legacy App Flow (confirmed)
1. Flask route receives request.
2. Route calls store/runtime helpers and scanner/detector logic.
3. Findings are normalized and appended.
4. Cache invalidation and metrics rebuild hooks execute.
5. UI/API responds from persisted state.

### Orchestrator Track Flow (post-split status)
1. Historical CLI files still exist in `Juhertha/dev`.
2. The orchestrator package implementations they depended on were extracted to `Juhertha/secflow-orchestrator`.
3. `Juhertha/dev` should be treated as legacy-only; active orchestrator work belongs in the orchestrator repo.

## Boundaries and Risks
- Confirmed boundary: `packages.findings` must not import from `packages.runtime_core` or `packages.workflow_engine`.
- Confirmed risk areas:
  - duplicate helper definitions in `store.py`
  - fallback API key behavior in `app.py`
  - committed developer-local config paths
