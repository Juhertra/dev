# Runbook - Patch Workflow

Concise operational workflow for `.ai` patch execution.

Authoritative files:
- `.ai/AGENTS.md`
- `.ai/SYSTEM_PROMPT.md`
- `.ai/prompts/CLAUDE_REVIEWER.md`
- `.ai/prompts/CODEX_IMPLEMENTER.md`
- `.ai/CHANGE_BOUNDARIES.md`
- `.ai/SEARCH_GUIDE.md`
- `.ai/GITHUB_WORKFLOW.md`

## Phase Order

1. State Sync
- Owner: reviewer role.
- Read: `TASK.md`, `REVIEW.md`, active patch file (if any).
- Output: current state only; no patch activation unless explicitly authorized.

2. Patch Activation
- Trigger: explicit operator authorization for a specific patch ID.
- Owner: reviewer role.
- Actions:
  - Read patch spec and scope files.
  - Prepend `## Pre-Implementation Review - P0xx` to `REVIEW.md`.
  - Update `TASK.md` with `Active patch: P0xx`.

3. Implementation
- Owner: implementer role. In single-agent (collapsed) mode, the operator must explicitly invoke implementer role before implementation begins. Collapse does not transfer ownership automatically.
- Preconditions:
  - Active patch is declared in `TASK.md`.
  - Matching pre-implementation review exists in `REVIEW.md`.
- Actions:
  - Apply only patch-planned file changes.
  - Keep diff minimal.
  - Prepend `## Implementation Summary - P0xx` to `REVIEW.md`.

4. Post-Implementation Review (PR Readiness)
- Owner: reviewer role.
- Actions:
  - Review working diff/commit for scope and correctness.
  - Prepend `## Post-Implementation Review - P0xx` to `REVIEW.md`.
  - Verdict must be explicit: `approved for PR` or blocked with required fixes.

5. PR Open
- Owner: operator or explicitly authorized implementer.
- Rules:
  - One patch = one branch = one PR.
  - Naming follows `.ai/GITHUB_WORKFLOW.md`.
  - PR scope must match patch scope only.

6. Post-Implementation Review (Merge Readiness)
- Owner: reviewer role.
- Actions:
  - Review PR diff, checks, and merge state.
  - Prepend `## Post-Implementation Review - P0xx (PR #xxx, CI confirmed)` to `REVIEW.md`.
  - Verdict must be explicit: `approved for merge` or blocked with exact blocker.

7. Approval and Merge
- Owner: operator or explicitly authorized implementer.
- Notes:
  - Approval may be impossible for PR author (self-approval restriction).
  - If standard merge is blocked by branch policy, report exact blocker and required manual action.

8. Post-Merge State Sync
- Owner: reviewer role.
- Actions:
  - Confirm merged state via GitHub.
  - Update `TASK.md` patch status.
  - Keep next candidate list accurate.

## Mandatory Gates

- Pre-review gate:
  - Implementation must not start before `Pre-Implementation Review - P0xx` exists.
- Scope gate:
  - Edit only files listed in patch `Planned Changes`.
  - If another file is required, stop and request scope update first.
- Evidence gate:
  - Use `confirmed` only for directly verified facts; otherwise use `inferred` or `uncertain`.
- Authorization gate:
  - No remote mutation (push/review/merge/settings) without explicit operator authorization.
  - No split Gate A-E actions without explicit gate authorization.
- Role gate:
  - Claude (reviewer) must not own implementation or remote-mutation phases by default.
  - Role collapse requires explicit operator declaration per session.
  - Split-gate execution (B–E git/remote operations) is Codex/operator-only in all modes.
- CI gate:
  - Use required checks from live branch protection and `.ai/CI_SURFACE.md`.
- Log gate:
  - `REVIEW.md` is append-only history with newest entries first (prepend new entries; do not rewrite old ones).

## Coordination-Only Rule

When task scope is coordination-only or no production patch is active:
- Edit `.ai/*` only.
- Do not modify production code.

## Quick Checklist

Before implementation:
- Active patch confirmed in `TASK.md`.
- Pre-implementation review exists.
- Patch scope and boundaries are clear.

Before PR:
- Diff matches patch scope only.
- Required validation evidence is recorded in `REVIEW.md`.

Before merge:
- Merge readiness review completed.
- Exact blockers resolved or explicitly escalated.