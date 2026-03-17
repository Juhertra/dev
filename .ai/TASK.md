# Current Task

## Status
The coordination pack is complete. All `.ai/` files are consistent, evidence-labeled, and patch-ready.

**Split lifecycle complete (2026-03-17).** Gates A-E all complete. `Juhertha/dev` is legacy-only. `Juhertha/secflow-orchestrator` is the orchestrator repo.

**Gate C - complete (2026-03-14).** PR `#114` merged. Merge commit `0f8f8a25d3e8cce4d4837d650df935814e141d61`.

**Gate D - complete (2026-03-15).** `Juhertra/secflow-orchestrator` created, rewritten history pushed, RSA key pair rotated, smoke checks completed. `lint-imports` remained deferred to Gate E.
- Working clone: `D:\Lab\dev\.worktrees\gate-d-orchestrator`

**P069 - Residual Orchestrator Cleanup Before Gate D: completed and merged (PR #115, confirmed 2026-03-14). Merge commit `ce4f564cae7da66095e8fac82afc8468809d3e2e`.**

**P070 - Orchestrator CI Baseline and Import-Linter Configuration: completed and merged (PR `Juhertra/secflow-orchestrator#1`, merge commit `0afa816c`, confirmed 2026-03-15).**

**P071 - Orchestrator pyproject.toml Dependency Trim: completed and merged (PR `Juhertra/secflow-orchestrator#2`, merge commit `ab681e33dc166f42cbdb9cd4bc345bf30174f83c`, confirmed 2026-03-15).**

**P072 - Key Path Hardening in security/: completed and merged (PR `Juhertra/secflow-orchestrator#3`, merge commit `b548cd6c6227da867b4db9ab03c36939ffaa0e34`, confirmed 2026-03-15).**

**P073 - Remove Residual Orchestrator Tests from Juhertra/dev main: completed and merged (PR `Juhertha/dev#116`, merge commit `e0b468a496e4ade3d28ce7851824ccc4236ae23c`, confirmed 2026-03-17). Deleted `tests/workflow/test_workflow_scaffolding.py`, `test_workflow_execution.py`, `test_workflow_integration.py`. Merged via operator-authorized `--admin` squash override.**

**P074 - Remove cryptography dep from Juhertha/dev pyproject.toml: completed and merged (PR `Juhertha/dev#118`, merge commit `b0830c73d99c6c1e1033ff8a70ff9f92bd8fbf66`, confirmed 2026-03-17). Removed `cryptography = "^43.0"`; `pyyaml` retained (active legacy use). Merged via operator-authorized `--admin` squash override.**

**P075 - CI Workflow Repair (security-monitoring.yml, security-scan.yml): completed and merged (PR `Juhertha/dev#117`, merge commit `aa4d57a2de26822840f865974e48e053f282a6a6`, confirmed 2026-03-17). Fixed upload/download-artifact@v3->v4; added continue-on-error to comment steps. Merged via operator-authorized `--admin` squash override.**

## Active Patch

**P076** â€” Split Lifecycle Close: normalize stale coordination-pack facts; record Gates Aâ€“E complete.
Status: **Phase 3 complete - implementation applied; ready for Phase 4 review.**
Spec: `.ai/PATCHES/P076-split-lifecycle-close.md`
Scope: `.ai/` files only â€” `CONTEXT.md`, `ENTRYPOINTS.md`, `SEARCH_GUIDE.md`, `PLAN.md`, `MEMORY.md`, `REPO_BRAIN.md`, `REPO_MAP.json`, `TASK.md`.
- Implementation summary: recorded in `REVIEW.md` under `## Implementation Summary - P076`

**Gate E - Readiness analysis complete (2026-03-15). Ready to begin.**
Gate E is executed as discrete numbered patches, not as a single gate.
See `archive/REVIEW-archive-003.md` `## Gate E Readiness Analysis` for full evidence basis.

Patch execution order:

**Batch A - Orchestrator baseline (sequential):**
- **P070** (`secflow-orchestrator`): CI baseline + `.importlinter` - completed and merged (PR `#1`, 2026-03-15).
- **P071** (`secflow-orchestrator`): remove `flask` from `pyproject.toml` - completed and merged (PR `#2`, 2026-03-15).

**Batch B - Orchestrator security (after P070 CI):**
- **P072** (`secflow-orchestrator`): key path hardening in `security/plugin_loader.py` and `security/create_sample_plugins.py` - **completed and merged (PR `#3`, 2026-03-15).**

**Batch C - Legacy cleanup (independent; can proceed at any time):**
- **P073** (`Juhertha/dev`): remove residual orchestrator tests from `main` â€” **completed and merged (PR `#116`, 2026-03-17).**
- **P074** (`Juhertha/dev`): remove `cryptography` dep (scope narrowed; `pyyaml` retained, active use confirmed) â€” **completed and merged (PR `#118`, 2026-03-17).**
- **P075** (`Juhertha/dev`): CI workflow audit â€” **completed and merged (PR `#117`, 2026-03-17).**

**Batch C complete. All 3 patches merged.**

## Standing Rules
- Separate `confirmed` from `inferred` and `uncertain`.
- Keep terminology aligned with canonical terms in `.ai/AGENTS.md`.
- Do not modify production code unless a patch is explicitly authorized and in scope.
