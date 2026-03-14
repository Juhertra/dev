# Change Boundaries

Practical edit-scope rules for patch execution and PR readiness.

Evidence labels follow `.ai/AGENTS.md`: `confirmed`, `inferred`, `uncertain`.

## Authoritative Inputs
- Active patch scope: `.ai/PATCHES/<PatchID>.md` (`Planned Changes` is authoritative).
- Active workflow status: `.ai/TASK.md`.
- Search/noise handling: `.ai/SEARCH_GUIDE.md`.
- PR/branch conventions: `.ai/GITHUB_WORKFLOW.md`.
- GitHub/CI behavior: `.ai/GITHUB_SURFACE.md`, `.ai/CI_SURFACE.md`.

## Core Scope Rule
During a production patch:
1. Edit only files explicitly listed in the active patch `Planned Changes`.
2. Allow direct support files only when required to satisfy acceptance criteria:
   - targeted tests
   - minimal docs/user-facing setup notes
3. Do not expand scope silently. If another file is required, stop and request scope update first.

## No Active Production Patch
If no production patch is active, work is coordination-only:
- Edit `.ai/*` only.
- Do not edit runtime code, tests, CI workflows, or GitHub governance files unless explicitly instructed.
- Split-gate execution phases (B–E git/remote operations) are treated as remote mutations; they are Codex/operator-only regardless of role-collapse mode.

## Protected and High-Risk Paths

### Protected (explicit user authorization required)
- `.github/workflows/*.yml`
- `.github/CODEOWNERS`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/ISSUE_TEMPLATE/*.yml`
- `SPLIT_LEGACY_ORCHESTRATOR_ACTION_PLAN.md`

### High-risk runtime/config files (keep edits minimal and patch-justified)
- `app.py`, `api_endpoints.py` (auth/runtime entry behavior)
- `store.py`, `findings.py`, `config.py` (state and persistence)
- `pyproject.toml`, `Makefile`, `.importlinter`, `.ruff.toml`, `pyrightconfig.json`, `.pre-commit-config.yaml` (repo-wide toolchain impact)

If touching high-risk files, include targeted validation evidence in PR notes and `REVIEW.md`.

## .ai File Boundary During Production Patches
- Allowed:
  - `.ai/REVIEW.md` append/prepend session review entries (never delete existing history).
  - Read other `.ai/*` for context.
- Not allowed unless explicitly requested:
  - broad `.ai` normalization/refactors during a production patch.

## Scope Creep Signals (Stop And Confirm)
- Editing files outside active patch scope without prior authorization.
- Refactors/reorganizations not required by acceptance criteria.
- Touching CI/governance files as part of an unrelated product patch.
- Bundling unrelated fixes into the same branch/PR.

## PR Hygiene Boundary
- PR must contain only patch-intended files.
- Exclude local noise:
  - `__pycache__/`
  - `*.pyc`
  - `.claude/worktrees/`
  - unrelated `.ai/*` files unless the task explicitly includes them.

Useful checks before PR:
```powershell
git status --short
git diff --cached --name-only
git log --oneline origin/main..HEAD
```

## Risk-Area Reminder (from `REPO_MAP.json`)
- `R001`: legacy storage helper duplication risk.
- `R002`: auth default/API key fallback risk.
- `R003`: local config hygiene risk.
- `R006/R007`: sys.path and split-portability risk.

If a patch touches any listed risk area, include explicit validation for that behavior.
