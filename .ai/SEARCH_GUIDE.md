# Repository Search Guide

Concise navigation guide for the Coordination Pack.
Aligned with `.ai/AGENTS.md`, `.ai/ENTRYPOINTS.md`, `.ai/REPO_BRAIN.md`, and `.ai/REPO_MAP.json`.

## Scope And Terms
- Use canonical terms from `.ai/AGENTS.md`: `Legacy App`, `Orchestrator Track`, `Coordination Pack`.
- Keep evidence labels consistent: `confirmed`, `inferred`, `uncertain`.
- Use this file for search/navigation only; execution rules remain in `.ai/SYSTEM_PROMPT.md` and agent prompts.

## Search Hygiene

Exclude noisy paths unless explicitly required:
- `.venv/`
- `.claude/worktrees/`
- `patterns/community/nuclei-templates/`
- `forChatGPT/`
- `docs/`
- `site/`

Recommended command style:
- Prefer `rg` when available.
- Fallback in this repo shell: `Get-ChildItem ... | Select-String ...`

PowerShell fallback example:
```powershell
Get-ChildItem -Recurse -File -Include *.py |
  Where-Object { $_.FullName -notmatch '\\.venv\\|\\.claude\\worktrees\\|patterns\\community\\|forChatGPT\\|\\docs\\|\\site\\' } |
  Select-String -Pattern "update_endpoint_dossier_by_key|get_endpoint_runs_by_key"
```

## Where To Look First

### Legacy App
- App wiring: `app.py`, `web_routes.py`, `routes/__init__.py`, `api_endpoints.py`
- Storage/state: `store.py`, `core.py`, `config.py`
- Findings pipeline: `utils/findings_normalize.py` -> `findings.py` -> `store._bust_vulns_cache()`
- Endpoint key format: `utils/endpoints.py`
- Nuclei flow: `nuclei_wrapper.py`, `nuclei_integration.py`

### Orchestrator Track
- Historical CLI files still present in `Juhertha/dev`: `tools/run_workflow.py`, `tools/validate_recipe.py`, `tools/workflow_to_mermaid.py`
- Orchestrator packages and sample workflows were moved to `Juhertha/secflow-orchestrator` during Gate D and are absent from `Juhertha/dev` main
- Search orchestrator package code in the orchestrator repo/worktree, not in `Juhertha/dev`

## Entrypoint Reference

Canonical entrypoint inventory is `.ai/ENTRYPOINTS.md`.
Quick confirmed start points:
- `app.py` (Flask dev server)
- `wsgi.py` (WSGI app object)
- `pattern_cli.py`
- `tools/run_workflow.py`
- `tools/validate_recipe.py`
- `tools/workflow_to_mermaid.py`
- `init_asvs.py`

## Review History Lookup

Read review history in this order:
1. `TASK.md`
2. top of `REVIEW.md`
3. `REVIEW_INDEX.md`
4. the specific archive file referenced by the index

Open archive files only when needed for targeted historical lookup.

## Patch-Oriented Search Checklist

1. Read patch scope:
- `.ai/PATCHES/<PatchID>.md`

2. Read review context:
- `.ai/REVIEW.md`

3. Audit call sites:
```powershell
Get-ChildItem -Recurse -File -Include *.py |
  Select-String -Pattern "<function_name>\\("
```

4. Detect duplicate definitions:
```powershell
Select-String -Path <file>.py -Pattern "^def <function_name>\\b"
```

5. Locate tests:
```powershell
Get-ChildItem tests -Recurse -File -Include *.py |
  Select-String -Pattern "<function_name>|<module_name>"
```

## Known Repository-Specific Pitfalls
- `.claude/worktrees/...` duplicates files and pollutes search results.
- For recipe validation history in `Juhertha/dev`, `tools/validate_recipe.py` remains as a file reference; package validator paths were extracted to `Juhertha/secflow-orchestrator`.
- `pytest.ini` is currently malformed; use `pytest -c pyproject.toml` when needed.
- Historical `sys.path` split-portability risk was resolved by P062 before Gate D completed.

## Related Coordination Files
- Shared rules: `.ai/SYSTEM_PROMPT.md`
- Role behavior: `.ai/prompts/CLAUDE_REVIEWER.md`, `.ai/prompts/CODEX_IMPLEMENTER.md`
- Architecture summary: `.ai/REPO_BRAIN.md`
- Machine map and risk IDs: `.ai/REPO_MAP.json`
- GitHub governance (CODEOWNERS, PR template, labels, merge rules): `.ai/GITHUB_SURFACE.md`
- CI workflow triggers and blocking/non-blocking classification: `.ai/CI_SURFACE.md`
