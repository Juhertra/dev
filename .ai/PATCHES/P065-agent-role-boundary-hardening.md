# P065 — Agent Role Boundary Hardening

## Status
- pending (not yet activated)

## Objective
Harden coordination-pack role boundaries to:
1. Prevent Claude (reviewer) from performing implementation or remote-mutation phases by default.
2. Prevent the "single active agent" clause from silently collapsing reviewer/implementer roles.
3. Designate split-gate execution (B–E git/remote operations) as Codex/operator-only.
4. Keep all changes minimal and internally consistent with the existing workflow.

No production code, tests, or CI workflows are touched.

## Scope
- In scope:
  - `.ai/AGENTS.md`
  - `.ai/RUNBOOK.md`
  - `.ai/prompts/CLAUDE_REVIEWER.md`
  - `.ai/prompts/CODEX_IMPLEMENTER.md`
  - `.ai/CHANGE_BOUNDARIES.md` — one targeted addition for split-gate execution ownership
- Out of scope:
  - All production code, tests, CI workflows, GitHub governance files
  - `.ai/REVIEW.md`, `.ai/TASK.md` (managed by workflow, not patch content)
  - All other `.ai/` files not listed above

## Evidence
- confirmed:
  - `AGENTS.md` line 37 allows single-agent role collapse unconditionally with no explicit operator declaration.
  - `CLAUDE_REVIEWER.md` "Default Posture" does not prohibit remote mutations (git push, tag creation, PR creation, bundle operations); only "production code modification" and "patch execution" are called out.
  - `RUNBOOK.md` does not designate split-gate execution phases as Codex/operator-only; Phase 3 says owner is "implementer role" but Phase 5 (PR Open) is the only phase that names operator explicitly.
  - `CODEX_IMPLEMENTER.md` already says "Do not execute split gates (A–E) without separate, explicit user authorization per gate" but does not address collapsed-mode behavior.
- inferred:
  - The absence of an explicit remote-mutation prohibition in CLAUDE_REVIEWER.md allowed Gate B git operations (tag push, bundle) to be executed by the reviewer agent without a per-operation objection.
  - Implicit role collapse has the practical effect of bypassing the pre/post review separation because one agent writes and then reviews its own work.
- uncertain:
  - Whether Codex is always available in a given session; if not, operator must act as implementer for execution phases.

## Planned Changes

### 1. `.ai/AGENTS.md`
Replace the single-sentence single-agent clause (current line 37):
> "A single agent may perform both roles when only one agent is active; it must apply both prompt files in that case."

With a hardened block:
> Single-agent sessions require explicit operator declaration of role collapse.
> Even in collapsed mode:
> - The agent must apply both prompt files.
> - Claude's default posture (reviewer) governs unless the operator explicitly invokes implementer role for a specific phase.
> - Split-gate execution phases (B–E git/remote operations) remain Codex/operator-only regardless of collapse.

### 2. `.ai/prompts/CLAUDE_REVIEWER.md`
Add two items to the "Default Posture" list:
- "Do not perform remote mutations (git push, tag creation, branch creation, PR creation, merge, or bundle operations) without explicit per-operation operator authorization. A gate authorization does not imply authorization for Claude to execute its git/remote operations."
- "Do not execute split-gate phases (B–E). Claude's role at each gate is limited to pre-gate review; execution of git and remote operations is Codex/operator-only."

### 3. `.ai/prompts/CODEX_IMPLEMENTER.md`
Add one item to the "Scope Guards" list:
- "In single-agent (collapsed) mode, split-gate execution phases (B–E) must be explicitly invoked by the operator as implementer-role tasks. Collapse does not automatically authorize execution; each gate still requires its own per-gate authorization."

### 4. `.ai/RUNBOOK.md`
Two targeted additions:

a) After Phase 3 "Owner: implementer role." add:
> "In single-agent (collapsed) mode, the operator must explicitly invoke implementer role before implementation begins. Collapse does not transfer ownership automatically."

b) Add a new Mandatory Gate item in the "Mandatory Gates" section:
> "- Role gate:
>   - Claude (reviewer) must not own implementation or remote-mutation phases by default.
>   - Role collapse requires explicit operator declaration per session.
>   - Split-gate execution (B–E git/remote operations) is Codex/operator-only in all modes."

### 5. `.ai/CHANGE_BOUNDARIES.md`
Add one line to the "No Active Production Patch" section:
> "Split-gate execution phases (B–E git/remote operations) are treated as remote mutations; Codex/operator-only regardless of role-collapse mode."

## Validation
- Coordination-only patch: no commands to run.
- Expected result: all five files updated; no production file touched; diff is `.ai/` only.
- Spot-check: grep each changed file for the new explicit prohibitions to confirm they are present.

## Risks
- inferred: Overly tight wording could block legitimate single-agent sessions. Mitigated by scoping restrictions to remote-mutation and split-gate execution only, not to all implementer tasks.
- inferred: Wording inconsistency with future prompts if additional agent roles are added. Mitigated by anchoring rules to existing terms (`confirmed`, canonical role names).

## Rollback
- Revert the five `.ai/` file edits. No production state to restore.

## Acceptance Criteria
- [ ] `AGENTS.md`: single-agent clause requires explicit operator declaration; split-gate execution designated Codex/operator-only.
- [ ] `CLAUDE_REVIEWER.md`: Default Posture explicitly prohibits remote mutations and split-gate execution without per-operation authorization.
- [ ] `CODEX_IMPLEMENTER.md`: Scope Guards explicitly address collapsed-mode split-gate authorization.
- [ ] `RUNBOOK.md`: Phase 3 notes collapsed-mode operator declaration; Mandatory Gates includes role gate for remote mutations and split-gate execution.
- [ ] `CHANGE_BOUNDARIES.md`: split-gate execution designated as remote mutation / Codex-operator-only.
- [ ] No production files modified.
