# Multi-Agent Guide

## Purpose

This guide defines how Codex multi-agent mode is used in this repository.

`.ai/` remains the authoritative workflow system. `.codex/config.toml` is a local extension layer and must not expand scope beyond `.ai/`.

Authority order:
- `.ai/TASK.md` (live task state; names the active patch file)
- active patch file under `.ai/PATCHES/`
- `.ai/RUNBOOK.md`
- `.ai/AGENTS.md`
- `.ai/SYSTEM_PROMPT.md`
- `.ai/CHANGE_BOUNDARIES.md`
- `.ai/MEMORY.md`
- `.ai/SEARCH_GUIDE.md`
- `.ai/ENTRYPOINTS.md`
- `.ai/REVIEW.md`
- `.codex/config.toml`

## Core Principle

**Default mode is single-agent. Multi-agent is an optimization for clearly beneficial, read-heavy tasks only.**

**One coordinator. Multiple readers.**

The coordinator is the only agent that may write `.ai/*`, `.codex/*`, or production files. Spawned agents are read-only and return structured findings.

No two agents may work toward edits on overlapping production files at the same time. If overlap appears, stop parallel work and continue single-agent under the coordinator.

## Roles

### Coordinator
- One active coordinator per session.
- Owns all writes to `.ai/*`, `.codex/*`, production code, and Git/GitHub state.
- Determines the current RUNBOOK phase from `.ai/TASK.md` and `.ai/REVIEW.md`.
- May spawn read-only sub-agents for narrow, read-heavy tasks.

### Explorer
- Read-only codebase exploration: caller lookup, import tracing, file discovery, repo-map checks.
- Tools: `read`, `grep`, `glob`, `bash_readonly`.

### CI Analyst
- Read-only CI and PR inspection: check status, run logs, merge state.
- Tools: `gh_read`, `bash_readonly`.

### Triage Analyst
- Read-only test-failure triage across tests and imported production modules.
- Tools: `read`, `grep`, `glob`.

## Safe Use

**Spawning is optional.** Only spawn a sub-agent when the benefit is clear: the task is genuinely read-heavy, independent of coordinator state, and would take materially longer as a single serial operation. When in doubt, do not spawn.

Approved parallel patterns:
- codebase exploration
- repo-map verification
- CI log fetch
- PR status check
- test failure triage
- independent grep/glob searches

Never parallelised:
- patch implementation
- any write to `.ai/*`
- any write to `.codex/*`
- any production-code edit
- overlapping edit planning for the same production area
- branch creation
- PR open
- merge without explicit operator authorization
- split gate execution

## Single-Writer Files

Coordinator-only files include:
- `.ai/TASK.md`
- `.ai/REVIEW.md`
- `.ai/MEMORY.md`
- `.ai/DECISIONS.md`
- `.ai/REPO_BRAIN.md`
- `.ai/REPO_MAP.json`
- `.ai/CI_SURFACE.md`
- `.ai/AGENTS.md`
- `.ai/SYSTEM_PROMPT.md`
- `.ai/RUNBOOK.md`
- `.ai/MULTI_AGENT_GUIDE.md`
- `.ai/GITHUB_WORKFLOW.md`
- `.ai/CHANGE_BOUNDARIES.md`
- `.ai/PATCHES/*.md`
- `.ai/PATCH_INBOX.md` (coordinator-only; no sub-agent may read or write it)
- `.ai/prompts/*.md`
- `.codex/config.toml`

## Spawning Pattern

When the coordinator spawns a sub-agent:
1. Define a narrow task with explicit files and output format.
2. Provide only the needed `.ai/*` context files.
3. Instruct: read-only, no writes, return findings only.
4. Use `.ai/SEARCH_GUIDE.md` exclusions unless the task explicitly requires noisy paths.
5. Integrate findings and make all write decisions serially in the coordinator.

**Findings-only rule:** spawned agents return raw findings (file paths, line numbers, log excerpts, structured data). They do not make decisions, draw patch conclusions, or update coordination state. All decisions and state updates are the coordinator's sole responsibility.

## Claude Subagents

Claude project subagents are defined in `.claude/agents/`. They are read-only analysis agents and may return findings only. The coordinator remains responsible for all writes.

Current Claude subagents:
- `.claude/agents/repo-explorer.md` -- codebase exploration, call-site discovery, import tracing
- `.claude/agents/ci-analyst.md` -- workflow file inspection, check-definition mapping, blocker analysis
- `.claude/agents/test-triage.md` -- test failure triage, fixture/config drift, root cause analysis

### Tool surface compatibility

Claude subagents and Codex roles do not need to have identical tool surfaces. Claude subagents may be narrower than similarly named Codex roles. This is acceptable when the Claude role remains read-only and observational. Codex retains broader read-only CI/log/GitHub inspection capability where needed.

**CI analysis specifically:**
- Claude `ci-analyst` (Read/Grep/Glob only) -- narrow workflow file and check-definition analysis.
- Codex `ci_analyst` (`gh_read`, `bash_readonly`) -- runtime log fetch, check-state inspection, PR merge-state queries.
- These roles are complementary. They are not required to be tool-identical.

## RUNBOOK Alignment

Multi-agent mode does not change the RUNBOOK phases.
The one-phase gate still applies in multi-agent mode: sub-agent parallel reads may support a phase, but the coordinator executes exactly one owned RUNBOOK phase per operator instruction and then stops.

- State Sync: read-only CI/status fetch may run in parallel with coordinator reading `.ai/*`.
- Patch Activation: read-only exploration may support scope reading.
- Implementation: single implementer only.
- Post-Implementation Review: read-only diff/CI inspection may support the coordinator.
- PR Open: coordinator only, explicit operator authorization required.
- Approval and Merge: coordinator only, explicit operator authorization required. Self-approval restrictions may still require admin merge handling.
- Post-Merge State Sync: read-only CI confirmation may support the coordinator.

## Safety Reminders

- Use `confirmed`, `inferred`, and `uncertain` consistently with `.ai/AGENTS.md`.
- Do not modify production code unless a patch is explicitly authorized and in scope.
- Do not modify `.ai/*` or `.codex/*` from sub-agents.
- Do not push, create PRs, or merge without explicit operator authorization.
- Do not execute split gates A-E without explicit per-gate authorization.
- During an active production patch, do not perform broad `.ai` normalization or multi-agent refactors unless explicitly requested.
