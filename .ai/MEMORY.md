# Memory

## Durable Confirmed Facts

### Repository Identity
- Package name is `secflow`, version `0.0.1`.
- Python target is 3.11 (`.python-version` is `3.11.9`).
- `Juhertha/dev` is now legacy-only; the Orchestrator Track was extracted to `Juhertha/secflow-orchestrator`.
- Split lifecycle is complete (Gates A-E, 2026-03-17).
- Durable split fact: `Juhertha/dev` is the legacy repo; `Juhertha/secflow-orchestrator` is the orchestrator repo.

### Confirmed Entrypoints
Full inventory is in `.ai/ENTRYPOINTS.md`. Key entries:
- `app.py` — Flask development server (port 5001).
- `wsgi.py` — WSGI production entrypoint; no CLI.
- `pattern_cli.py` — pattern management CLI.
- `tools/run_workflow.py` — orchestrator CLI; `--dry-run` flag; handles `not_implemented`.
- `tools/validate_recipe.py` — recipe validation CLI; real DAG dependency checking at lines 54–63.
- `tools/workflow_to_mermaid.py` — converts YAML recipe to Mermaid diagram.
- `init_asvs.py` — ASVS Nuclei template setup script.
- All files under `scripts/` — operational, migration, and CI scripts.

### Confirmed Makefile Commands
- `make test` — full test suite.
- `make unit` — unit tests only.
- `make quick-test` — fast subset (used in pre-commit).
- `make coverage` — coverage report.
- `make lint` — Ruff linting.
- `make type` — Pyright type checking.
- `make imports` — import-linter boundary check.
- `make health` — application health check.

### Confirmed Key Config Files
- `pyproject.toml` — package metadata, dependencies, Poetry config.
- `.python-version` — pins Python to `3.11.9`.
- `app_config.json` — developer-local; gitignored in current working tree.
- `.importlinter` — enforces `packages.findings` isolation boundary.
- `.ruff.toml` — Ruff config; `select = []` (defaults only).
- `pyrightconfig.json` — `typeCheckingMode = "basic"`; 58 checks explicitly disabled.
- `.pre-commit-config.yaml` — ruff, ruff-format, pyright, pytest quick-test, docs-health.
- `scripts/coverage_ratchet.py` — milestone coverage targets M0=18% through M6=90%.

### Confirmed GitHub / CI Facts
- Default branch: `master` (`confirmed`, live API 2026-03-07).
- `main` branch protection is enabled (`confirmed`, live API 2026-03-07):
  - required checks (`strict: true`): `pyright`, `imports`, `contracts`, `docs-health`
  - required approving reviews: `1`
  - `enforce_admins: false`
- `master` is not protected (`confirmed`, live API 2026-03-07 returns `404 Branch not protected`).
- CODEOWNERS `/*` rule: all root files require review from `@devex-lead`. Other CODEOWNERS paths use `/secflow/` prefix that does not match actual layout — those rules do not fire.
- Required-check contexts `Compile Reports`, `Journals Lint`, `ruff (3.11.9)`, `unit (3.11.9)`, and `coverage (3.11.9)` are not in the current `main` required list (`confirmed`, live API 2026-03-07).
- Python 3.12 matrix runs are explicitly non-blocking (`continue-on-error: true`).
- `docs-validate.yml` and `security-monitoring.yml` target branch `main`, not `master` — those workflows do not fire on PRs to `master`.
- Pre-merge local commands: `make lint`, `make type`, `make imports`, `make unit`, `make coverage`, `make health`, `pytest -q tests/contracts`.
- Full reference: `.ai/GITHUB_SURFACE.md`, `.ai/CI_SURFACE.md`.
- Governance cleanup snapshot on 2026-03-07 (live verified):
  - PRs `#87`, `#89`, `#90`, `#92`, `#97` were closed as stale historical PRs.
  - Issues `#91`, `#93`, `#94`, `#95`, `#96`, `#98`, `#99` were closed as historical workflow/board artifacts.
  - PR `#101` (P010) merged 2026-03-07 via admin bypass.
  - PR `#102` (P020) merged 2026-03-07 via admin bypass.
  - PR `#103` (P050) merged 2026-03-07 (confirmed via API).
  - CI debt issues `#48`, `#49`, `#63` remained open.

### Confirmed Runtime Facts
- Legacy API blueprint is registered at `/api/v1` in `api_endpoints.py:20`.
- Runtime project data is stored under `ui_projects/` via `store.py` (`STORE_DIR`).
- Findings storage uses a rolling cap (`MAX_FINDINGS = 2000`).
- Import-linter enforces that `packages.findings` does not import `packages.runtime_core` or `packages.workflow_engine`.
- Historical orchestrator fact: `packages/workflow_engine/executor.py` and `packages/workflow_engine/validate_recipe.py` were confirmed M1 implementations before the split; those package paths were later extracted to `Juhertha/secflow-orchestrator` and are absent from `Juhertha/dev` main.
- Historical validation fact: P030 objectives were already met before extraction; active orchestrator execution/validation now belongs in `Juhertha/secflow-orchestrator`.

## Open Questions
1. `packages/storage/` ownership: resolved - moved to `Juhertha/secflow-orchestrator`.
2. `packages/findings/` ownership: resolved - moved to `Juhertha/secflow-orchestrator`.
3. `Juhertra/dev` rename question: resolved - repo remains `Juhertha/dev`.
4. Orchestrator repo visibility: resolved - `Juhertha/secflow-orchestrator` is public.
5. Whether `ui_projects/` runtime data should move to a local-only/ignored model (partial: `app_config.json` resolved by P020).
