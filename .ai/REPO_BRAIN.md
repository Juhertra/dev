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

### Orchestrator Track (confirmed M1 partial)
- `packages/runtime_core/storage/storage_port.py` defines `StoragePort` protocol.
- `packages/storage/adapters/memory.py` provides in-memory adapter implementation.
- `packages/wrappers/base.py` provides tool wrapper protocol/ABC.
- `packages/workflow_engine/executor.py` is an M1 implementation (825 lines): `execute_workflow()` returns `{"status": "completed"}` with full node execution, retry logic, and StoragePort integration (confirmed, read 2026-03-07).
- `packages/workflow_engine/validate_recipe.py` is an M1 implementation (445 lines): `RecipeValidator` runs a 6-step pipeline - schema, pydantic, DAG cycle detection, references, node types, configurations (confirmed, read 2026-03-07).
- `tools/run_workflow.py` and `tools/validate_recipe.py` are full CLIs. `run_workflow.py` supports `--dry-run`, `--execute`, `--parallel`, and `--test-sample` modes. `validate_recipe.py` performs real DAG dependency checking (confirmed, read 2026-03-07).

## Execution Flow (Current)

### Legacy App Flow (confirmed)
1. Flask route receives request.
2. Route calls store/runtime helpers and scanner/detector logic.
3. Findings are normalized and appended.
4. Cache invalidation and metrics rebuild hooks execute.
5. UI/API responds from persisted state.

### Orchestrator Track Flow (confirmed + inferred)
1. CLI loads workflow YAML.
2. Recipe checks run via tool and package validation paths.
3. Package executor is an M1 implementation; `execute_workflow()` returns `{"status": "completed"}` with `completed_nodes`, `total_findings`, and `execution_time` (confirmed, read 2026-03-07).

## Boundaries and Risks
- Confirmed boundary: `packages.findings` must not import from `packages.runtime_core` or `packages.workflow_engine`.
- Confirmed risk areas:
  - duplicate helper definitions in `store.py`
  - fallback API key behavior in `app.py`
  - committed developer-local config paths
  - `sys.path` manipulation in orchestrator-related modules/scripts
