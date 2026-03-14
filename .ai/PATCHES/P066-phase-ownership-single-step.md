# P066 — Phase Ownership and Single-Step Execution

## Status
- implemented 2026-03-14, approved for PR, awaiting PR creation

## Objective
Prevent agents from executing phases beyond the one they own.

Specific problems solved:
1. Claude must not self-chain from Phase 2 (activation/pre-review) into Phase 3 (implementation) or later.
2. Codex must not self-chain from Phase 7 (merge) into Phase 8 (post-merge state sync).
3. "Continue the active patch" means: execute exactly one next owned phase, then stop and report.
4. Phase ownership must be consolidated and unambiguous in one reference table.
5. Multi-agent mode must not weaken single-phase execution.

No production code, tests, or CI workflows are touched.

## Scope
- In scope:
  - `.ai/RUNBOOK.md`
  - `.ai/AGENTS.md`
  - `.ai/prompts/CLAUDE_REVIEWER.md`
  - `.ai/prompts/CODEX_IMPLEMENTER.md`
  - `.ai/MULTI_AGENT_GUIDE.md` — one targeted addition to RUNBOOK Alignment section
- Out of scope:
  - All production code, tests, CI workflows, GitHub governance files
  - All other `.ai/` files not listed above

## Evidence

- confirmed:
  - `RUNBOOK.md` Phase 2 has no stop signal; after writing the pre-implementation review and updating TASK.md, nothing prevents the same agent from immediately executing Phase 3.
  - `RUNBOOK.md` Phase 7 has no stop signal; the owner is "operator or explicitly authorized implementer" but there is no rule prohibiting Codex from proceeding to Phase 8 (reviewer-owned).
  - No single-phase execution rule exists in any coordination file. "Continue the active patch" is undefined — it can be read as "execute all remaining owned phases."
  - Phase ownership is declared inline within each phase block. There is no consolidated ownership table; an agent must scan all eight phases to determine ownership.
  - `MULTI_AGENT_GUIDE.md` RUNBOOK Alignment section notes which phases allow read-only sub-agent support but does not state that single-phase execution applies in multi-agent mode.
- inferred:
  - The absence of a single-phase rule is the root cause of multi-phase creep; individual stop signals at phase boundaries are a symptom fix; the rule itself is the root fix.
  - Consolidating ownership into a table reduces the risk of an agent misidentifying the next owned phase when phases are interleaved reviewer/implementer.
- uncertain:
  - Whether "exactly one phase per operator instruction" is too restrictive for coordination-only tasks (e.g. State Sync + read) — mitigated by scoping the rule to phases that produce writes, which is every phase except Phase 1.

## Planned Changes

### 1. `.ai/RUNBOOK.md`

**a) Add Phase Ownership Table** — new section immediately before `## Phase Order`:

A condensed ownership reference so any agent can determine in one read whether it owns the next phase:

```
| Phase | Name | Owner |
|---|---|---|
| 1 | State Sync | reviewer |
| 2 | Patch Activation | reviewer |
| 3 | Implementation | implementer |
| 4 | Post-Implementation Review (PR Readiness) | reviewer |
| 5 | PR Open | operator / authorized implementer |
| 6 | Post-Implementation Review (Merge Readiness) | reviewer |
| 7 | Approval and Merge | operator / authorized implementer |
| 8 | Post-Merge State Sync | reviewer |
```

**b) Add One-Phase Execution Rule** — new mandatory gate item:

```
- One-phase gate:
  - Each operator instruction executes exactly one RUNBOOK phase, then stops and reports.
  - An agent must not self-chain into the next phase even if it owns that phase.
  - Multi-phase execution requires a separate explicit operator instruction per phase.
```

**c) Add stop signals to Phase 2 and Phase 7** — targeted inline additions:

Phase 2 — after the Actions list, add:
> **Stop.** After pre-implementation review is written and `TASK.md` is updated, report and wait. Do not proceed to Phase 3 without a new operator instruction.

Phase 7 — after the Notes list, add:
> **Stop.** After merge is confirmed or the exact blocker is reported, stop. Do not proceed to Phase 8 without a new operator instruction.

### 2. `.ai/AGENTS.md`

Add to **Hard Constraints**:
> - Execute exactly one RUNBOOK phase per operator instruction. Stop and report after the phase is complete. Do not self-chain into the next phase.

### 3. `.ai/prompts/CLAUDE_REVIEWER.md`

Add to **Default Posture**:
> - Execute only the single RUNBOOK phase explicitly instructed. After completing Phase 2 (patch activation and pre-implementation review), stop and report. Do not proceed to Phase 3 or later without a new operator instruction.

### 4. `.ai/prompts/CODEX_IMPLEMENTER.md`

Add to **Execution Discipline** (after the pre-review enforcement block):
> - Execute only the single RUNBOOK phase explicitly instructed. After completing Phase 7 (merge confirmed or blocker reported), stop and report. Do not proceed to Phase 8 (post-merge state sync) or any reviewer-owned phase.

### 5. `.ai/MULTI_AGENT_GUIDE.md`

Add one sentence to the **RUNBOOK Alignment** section (after the opening paragraph):
> The one-phase execution rule applies in multi-agent mode. Sub-agent parallel reads within a phase are permitted, but the coordinator executes exactly one phase per operator instruction and stops. Multi-agent mode does not permit phase chaining.

## Validation
- Coordination-only patch: no commands to run.
- Expected result: all five files updated; no production file touched; diff is `.ai/` only.
- Spot-check: each changed file contains the new stop/ownership language at the expected location.

## Risks
- inferred: "exactly one phase" may be read as blocking legitimate combined reads (e.g. State Sync reads multiple files). Mitigated — Phase 1 is read-only; the rule targets phases that produce writes.
- inferred: agents may still multi-phase if the operator instruction is ambiguous (e.g. "continue"). Mitigated by requiring the one-phase rule to apply even to "continue" instructions, and by the ownership table making the next owned phase unambiguous.

## Rollback
- Revert the five `.ai/` file edits. No production state to restore.

## Acceptance Criteria
- [ ] `RUNBOOK.md`: phase ownership table present; one-phase gate in Mandatory Gates; stop signals on Phase 2 and Phase 7.
- [ ] `AGENTS.md`: one-phase execution in Hard Constraints.
- [ ] `CLAUDE_REVIEWER.md`: Default Posture explicitly stops after Phase 2.
- [ ] `CODEX_IMPLEMENTER.md`: Execution Discipline explicitly stops after Phase 7; prohibits self-chain into Phase 8.
- [ ] `MULTI_AGENT_GUIDE.md`: RUNBOOK Alignment confirms one-phase rule applies in multi-agent mode.
- [ ] No production files modified.
