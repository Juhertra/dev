SHARED-STATE CONTRACT v1.1 — Journals ⇄ GitHub Board

• Append-only journals live under /control/journal/agents/<role>/<YYYY-MM>/<role>-<YYYY-MM-DD>.ndjson. Never edit old lines.

• Event types: sod | mid | eod | note | handoff | decision
  - handoff = a task for another role. Must include:
    - items[]: at least one @role tag (e.g., "@devex-lead") and a short action
    - links[]: at least one actionable reference (PR#123, FEAT-456, Issue#789, URL)

• Board linkage:
  - New handoff events (post-baseline) are auto-converted into GitHub Issues (label: from:journal).
  - Project Sync adds those Issues/PRs to the Projects (v2) board.
  - PRs MUST include “Fixes #<issue>” to auto-close the Issue on merge.
  - Status can be driven by labels: status:Todo | status:In Progress | status:Blocked | status:Done.

• Don’t manually drag cards. Use:
  - Journals (handoff/decision) to create/route work.
  - Labels + PR lifecycle to move board status.
