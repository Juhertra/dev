# Repository Context

## Identity
- Name: `secflow` (confirmed, `pyproject.toml`).
- Version: `0.0.1` (confirmed, `pyproject.toml`).
- Python target: `3.11.9` (confirmed, `.python-version`, CI).
- Primary remote: `https://github.com/Juhertra/dev.git` (confirmed).

## Co-Resident Tracks

### Legacy App (confirmed)
- Framework: Flask.
- Purpose: web/API security testing workflow with findings storage, scanning integrations, triage UI, and reporting.
- Main runtime files: `app.py`, `wsgi.py`, `web_routes.py`, `routes/`, `findings.py`, `store.py`, `nuclei_integration.py`.

### Orchestrator Track (extracted - confirmed, 2026-03-15)
- Extracted repo: `Juhertha/secflow-orchestrator` (Gate D complete).
- Status in `Juhertha/dev` main: orchestrator package paths are absent; `Juhertha/dev` is legacy-only.

## Toolchain
- Packaging: Poetry (`pyproject.toml`), plus `requirements.txt` for docs-oriented installs.
- Build/test runner: `Makefile` (`lint`, `type`, `imports`, `unit`, `test`, `health`).
- CI: GitHub Actions under `.github/workflows/`.
- Architecture boundary check: `.importlinter` (`packages.findings` isolation).

## Split Status
- Split lifecycle is complete (Gates A-E, 2026-03-17).
- `Juhertha/dev` remains the legacy repo; `Juhertha/secflow-orchestrator` is the orchestrator repo.

## Confirmed Risk Areas
- Duplicate helper definitions exist in `store.py`.
- `app.py` includes fallback API key behavior.
- `app_config.json` contains developer-local paths and is committed.
- Dependency declarations appear incomplete for some runtime imports.
