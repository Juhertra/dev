# P040 — Gate A Preflight Inventory

Generated: 2026-03-14
Status: Gate A deliverable — read-only inventory. No mutations performed.
Authorization: explicit operator authorization 2026-03-14.

---

## 1. Branch Inventory (confirmed, 2026-03-14)

### Local branches

| Branch | Notes |
|---|---|
| `main` | Active development branch — base for all P0xx patches |
| `master` | Pre-existing; `origin/HEAD` still points here (discrepancy — see §4) |
| `fix/P062-syspath-elimination` | Merged (PR #108); safe to delete |
| `feat/P050-ci-and-branch-protection-alignment` | Merged (PR #103); safe to delete |
| `feat/P060-coordination-pack-refresh` | Merged (PR #104); safe to delete |
| `feat/P061-ci-workflow-repair` | Merged (PR #105); safe to delete |
| `feature/P010-legacy-store-dedup` | Merged (PR #101); safe to delete |
| `feature/P020-config-and-secrets-hygiene` | Merged (PR #102); safe to delete |
| `fix/P063-executor-defects` | Superseded by v2; safe to delete |
| `fix/P063-executor-defects-v2` | Merged (PR #106); safe to delete |
| `fix/P064-test-suite-repair` | Merged (PR #107); safe to delete |
| `claude/strange-booth` | Purpose unknown; review before deletion |
| `tmp/p020-ops` | Temporary ops branch; likely safe to delete |

### Remote-only branches (origin)

| Branch | Notes |
|---|---|
| `board-smoke-test-pr` | Old smoke test; review before deletion |
| `chore/devops-ci-lock-py3119+cov` | Old CI work; merged or stale |
| `chore/devops-enforce-required-checks` | Old CI work; merged or stale |
| `chore/eod-20251009` | EOD snapshot; safe to delete |
| `chore/m0-d2-devex-ci-toolchain` | M0 sprint work; merged or stale |
| `chore/m0-d3-devex-unit-infra` | M0 sprint work; merged or stale |
| `chore/m0-d4-ci-audit` | M0 sprint work; merged or stale |
| `chore/m0-d4-observability-stubs` | M0 sprint work; merged or stale |
| `chore/m0-d5-devex-python-version-fix` | M0 sprint work; merged or stale |
| `chore/m0-d5-fix-devops-lock-ci-001` | M0 sprint work; merged or stale |
| `chore/m0-devex-pr-templates-and-ci` | M0 sprint work; merged or stale |
| `docs/m0-d4-governance-and-api-prep` | M0 docs work; merged or stale |
| `docs/shared-state-guide` | Shared state docs; review before deletion |
| `feat/coordinator-context-alias-shim` | Context shim; review before deletion |
| `feat/m0-d4-devex-lint-type` | M0 lint/type work; merged or stale |
| `feat/m0-d4-devex-pr-feat-linkage` | M0 PR linkage; merged or stale |
| `feat/m0-d4-security-audit-tighten` | M0 security work; merged or stale |
| `feat/m0-d4-tools-scaffold` | M0 tools scaffold; merged or stale |
| `feat/m0-d4-workflow-scaffold` | M0 workflow scaffold; merged or stale |
| `feat/m0-d4-workflow-tools-and-samples` | M0 workflow tools; merged or stale |
| `feat/m0-d5-ci-gates` | M0 CI gates; merged or stale |
| `feat/m0-d5-tools-n-1-samples` | M0 tools samples; merged or stale |
| `feat/m0-d5-tools-n-1-samples-clean` | M0 tools samples clean; merged or stale |
| `feat/m0-d5-workflow-imports` | M0 workflow imports; merged or stale |
| `fix/m0-d4-docs-mermaid-parity` | M0 docs fix; merged or stale |
| `fix/observability-journal-shape` | Observability fix; review before deletion |
| `secflow/shared-state-bootstrap` | Shared state bootstrap; review — may relate to orchestrator |
| `test-branch-protection` | Test branch; safe to delete |
| `test-project-sync` | Test branch; safe to delete |

---

## 2. Tag Inventory (confirmed, 2026-03-14)

| Tag | Commit | Date | Message |
|---|---|---|---|
| `v0.1.0` | `a2b71422` | 2025-10-16 | M0-D6 closeout complete |

**Note:** Only one tag exists. Gate B will create `split-baseline-<YYYYMMDD-HHMM>` before any mutations.

---

## 3. Keep/Move Matrix (confirmed + inferred + uncertain)

### Keep in legacy repo (`Juhertha/dev`) — confirmed

| Path | Reason |
|---|---|
| `app.py`, `wsgi.py`, `web_routes.py` | Flask app entrypoints |
| `routes/` | Legacy web route handlers |
| `findings.py`, `store.py` | Legacy state and persistence |
| `nuclei_integration.py`, `nuclei_wrapper.py` | Nuclei scan execution |
| `analytics_core/` | Legacy analytics |
| `detectors/` | Pattern/detection engine |
| `templates/`, `static/` | Web UI assets |
| `app/` | Flask middleware and settings |
| `tests/test_append_and_cache.py` | Legacy test |
| `tests/test_bulk_triage.py` | Legacy test |
| `tests/test_config_and_api_keys.py` | Legacy test |
| `tests/test_export.py` | Legacy test |
| `tests/test_findings_normalize.py` | Legacy test |
| `tests/test_metrics.py` | Legacy test |
| `tests/test_sse_stream.py` | Legacy test |
| `tests/test_store_dossier_helpers.py` | Legacy test |
| `tests/test_triage_migration.py` | Legacy test |
| `tests/test_triage_routes.py` | Legacy test |
| `tests/test_ui_metrics.py` | Legacy test |
| `tests/test_vulns_summary_triage.py` | Legacy test |

### Move to orchestrator repo (`Juhertha/secflow-orchestrator`) — confirmed

| Path | Reason |
|---|---|
| `packages/runtime_core/` | Orchestrator runtime core |
| `packages/workflow_engine/` | Workflow execution engine |
| `packages/wrappers/` | Tool wrapper protocol |
| `workflows/` | Workflow YAML definitions |
| `tools/run_workflow.py` | Orchestrator CLI |
| `tools/validate_recipe.py` | Orchestrator CLI |
| `tools/workflow_to_mermaid.py` | Orchestrator tooling |
| `tests/workflow/` | Workflow tests |
| `tests/integration/` | Orchestrator integration tests |
| `tests/runtime_core/` | Runtime core tests |
| `tests/e2e/` | End-to-end orchestrator tests |
| `tests/test_observability.py` | Observability tests (runtime_core) |
| `docs/architecture/05-orchestration-and-workflow-engine.md` | Orchestrator architecture doc |

### UNRESOLVED ownership — explicit decision required before Gate C

| Path | Reason unresolved |
|---|---|
| `packages/storage/` | Used by both tracks; `InMemoryStorageAdapter` imported by `executor.py` |
| `packages/findings/` | Models/schemas; could be shared or duplicated |
| `packages/plugins/` | Plugin loader/security used by orchestrator; security audit in legacy |
| `security/` | `signing.py`, `sandbox.py` used by plugin system (orchestrator); audit tooling (legacy) |
| `tests/test_security.py` | Tests `security/signing.py` — follows `security/` ownership decision |
| `tests/test_plugin_security.py` | Tests plugin verifier — follows `packages/plugins/` decision |
| `tests/test_plugin_loader.py` | Tests plugin loader — follows `packages/plugins/` decision |
| `tools/` (non-workflow scripts) | `plugin_sandbox.py`, `plugin_security_audit.py`, etc. — follows `security/`/`packages/plugins/` |
| `docs/architecture/` (most files) | Span both tracks; may need duplication or a shared repo |
| `pyproject.toml` | Both tracks currently share one package definition; must be split |
| `.github/workflows/` | Currently covers both tracks; must be split per repo |
| `.github/CODEOWNERS` | Must be split per repo |

### Open questions from split plan (§10) — still unresolved

1. Should `Juhertha/dev` be renamed to `dev-legacy`, or kept as-is?
2. Should `Juhertha/secflow-orchestrator` be private or public?
3. Who are initial maintainers for each repo?
4. Final ownership for `packages/storage`, `packages/findings`, and shared docs?

---

## 4. Pre-Existing Discrepancy (confirmed)

`origin/HEAD` → `origin/master`, but all active development and branch protection targets `main`.
**Action required at Gate E:** update `origin/HEAD` to point to `main` (or `master` → legacy default branch if renamed).

---

## 5. Gate B–E Command Checklist

All commands below are **planning-only**. Execution requires explicit per-gate authorization.

### Gate B — Backup and Safety Baseline

```bash
# Fetch all refs and tags
git fetch --all --tags

# Create annotated baseline tag (substitute actual timestamp)
git tag split-baseline-YYYYMMDD-HHMM -m "Pre-split safety baseline"
git push origin split-baseline-YYYYMMDD-HHMM

# Create full bundle backup
git bundle create dev-pre-split-YYYYMMDD-HHMM.bundle --all

# Verify bundle integrity
git bundle verify dev-pre-split-YYYYMMDD-HHMM.bundle
# Restore test in temp dir
git clone dev-pre-split-YYYYMMDD-HHMM.bundle /tmp/dev-restore-test
```

Exit: bundle verify passes and restore clone is healthy.

### Gate C — Legacy Hard-Boundary Branch

**Prerequisite:** unresolved ownership decisions (§3) must be resolved in writing before this gate.

```bash
# Create branch from main
git checkout -b split/legacy-hard-boundary main

# Remove orchestrator-only paths (adjust based on resolved ownership)
git rm -r packages/runtime_core/ packages/workflow_engine/ packages/wrappers/ workflows/
git rm tools/run_workflow.py tools/validate_recipe.py tools/workflow_to_mermaid.py
git rm -r tests/workflow/ tests/integration/ tests/runtime_core/ tests/e2e/
git rm tests/test_observability.py

# Commit, push, open PR
git commit -m "split(legacy): remove orchestrator-only paths"
git push origin split/legacy-hard-boundary
gh pr create --base main --title "split(legacy): hard-boundary branch"
```

Exit: CI green on legacy branch; no orchestrator path imports remain.

### Gate D — Orchestrator History Extraction

**Prerequisite:** Gate C approved and merged.

```bash
# Mirror clone
git clone --mirror https://github.com/Juhertha/dev.git dev-mirror
cd dev-mirror

# Install git-filter-repo if not present
pip install git-filter-repo

# Filter to orchestrator paths (adjust based on resolved ownership)
git filter-repo \
  --path packages/runtime_core/ \
  --path packages/workflow_engine/ \
  --path packages/wrappers/ \
  --path workflows/ \
  --path tools/run_workflow.py \
  --path tools/validate_recipe.py \
  --path tools/workflow_to_mermaid.py \
  --path tests/workflow/ \
  --path tests/integration/ \
  --path tests/runtime_core/ \
  --path tests/e2e/

# Create new orchestrator repo and push
gh repo create Juhertha/secflow-orchestrator --private
git remote add orchestrator https://github.com/Juhertha/secflow-orchestrator.git
git push orchestrator --all
git push orchestrator --tags
```

Exit: orchestrator repo builds and tests pass independently.

### Gate E — Governance and Cutover

```bash
# Update origin/HEAD to main (or legacy default branch)
git remote set-head origin main

# Per-repo: configure branch protection, CODEOWNERS, CI workflows
# Legacy repo: keep/update .github/workflows/ for legacy-only checks
# Orchestrator repo: create new .github/workflows/ for orchestrator checks

# Split release naming
# Legacy: tag prefix legacy-v*
# Orchestrator: tag prefix orch-v*

# Update READMEs with ownership and cross-links
```

Exit: contributors can route work unambiguously; no mixed-path PR checks.

---

## 6. Staleness Warning

This inventory was captured 2026-03-14. If branch/remote state changes before Gate B is authorized, regenerate §1–2 before proceeding.
