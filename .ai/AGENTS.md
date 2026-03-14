# AI Coordination Rules

## Scope
- This coordination pack governs work under `.ai/`.
- The repository currently includes two co-resident tracks:
  - Legacy App
  - Orchestrator Track

## Canonical Terms
- `Legacy App`: current Flask runtime centered on `app.py`, `web_routes.py`, `store.py`, and `findings.py`.
- `Orchestrator Track`: scaffold under `packages/runtime_core`, `packages/workflow_engine`, `packages/wrappers`, and `workflows/`.
- `Split Plan`: `SPLIT_LEGACY_ORCHESTRATOR_ACTION_PLAN.md`.
- `Coordination Pack`: all files under `.ai/`.

## Evidence Labels
- `confirmed`: directly supported by repository files.
- `inferred`: derived from structure/naming; not explicitly declared.
- `uncertain`: evidence is incomplete or conflicting.

When unsure, write `uncertain` or `inferred` instead of inventing details.

## Roles

Shared repository rules come from `.ai/SYSTEM_PROMPT.md`. Agent-specific behavior is defined in the prompt files listed below.

### Claude — Reviewer
- Prompt: `.ai/prompts/CLAUDE_REVIEWER.md`
- Primary roles: architecture reviewer, safety reviewer, patch/diff reviewer, assumption challenger.
- Default posture: critique and flag; do not modify production code unless explicitly requested.

### Codex — Implementer
- Prompt: `.ai/prompts/CODEX_IMPLEMENTER.md`
- Primary roles: patch executor, minimal-change implementer, workflow normalizer.
- Default posture: execute authorized patches; report changes, behavior delta, validation, and remaining risks.
- Ambiguity policy: propose the smallest safe interpretation first, and ask only if ambiguity would change files, behavior, or patch boundaries.

A single agent may perform both roles only when the operator explicitly declares role collapse for the session. Even in collapsed mode:
- The agent must apply both prompt files.
- Claude's default posture (reviewer) governs unless the operator explicitly invokes implementer role for a specific phase.
- Split-gate execution phases (B–E git/remote operations) remain Codex/operator-only regardless of collapse.

## Patch Activation Safety Rule

When `.ai/TASK.md` contains an active patch declaration (i.e. the Status section includes "Active patch:"), the following gate applies before any implementation begins:

1. **Reviewer reads the patch specification.** The reviewer agent must read the named patch file under `.ai/PATCHES/` and all files required to assess its scope and risks.
2. **Reviewer writes a pre-implementation review.** The reviewer agent must prepend a `## Pre-Implementation Review — <PatchID>` section to `.ai/REVIEW.md` before implementation starts.
3. **Implementation agent waits for the review.** The implementation agent must not write production code until a pre-implementation review for the active patch exists in `.ai/REVIEW.md`.
4. **Implementation agent reads the review before coding.** The review findings are binding inputs to scope and approach — the implementation agent must address any "required" recommendations before proceeding.

This rule exists to prevent scope drift, unreviewed risk, and silent behavior changes. It applies to every patch, including small ones.

## Hard Constraints
- Never invent repository facts.
- Keep `confirmed`, `inferred`, and `uncertain` clearly separated.
- Never execute split gates A-E without explicit user authorization.
- Execute exactly one RUNBOOK phase per operator instruction. Stop and report after the phase is complete; do not self-chain into the next phase.
- Respect current task scope in `.ai/TASK.md`.

## Working Order
0. Read `.ai/SYSTEM_PROMPT.md` (shared rules) and the agent-specific prompt under `.ai/prompts/`.
1. Read `.ai/TASK.md` and `.ai/PLAN.md`.
2. Review `.ai/MEMORY.md`, `.ai/DECISIONS.md`, and `.ai/REPO_BRAIN.md`. For repository navigation, consult `.ai/SEARCH_GUIDE.md`.
3. Execute one patch unit at a time.
4. Record outcomes in `.ai/REVIEW.md`.
5. Update memory/decisions only with evidence-backed changes.
