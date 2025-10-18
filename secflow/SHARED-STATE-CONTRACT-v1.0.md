SHARED-STATE CONTRACT v1.0 — MUST FOLLOW

• Append events via /tools/journal.py (never edit existing lines):
  - event: sod | mid | eod | note | handoff | decision
  - period: logical day being reported (YYYY-MM-DD)
  - title: concise action/result
  - items: concrete bullets (what/why/next)
  - links: PR#/FEAT-###/commit/build URLs

• Use “handoff” to push work to another role; @tag them and include links they need.
• Never write directly under /reports/daily/**; CI will regenerate those files.
• When you merge/close or make a policy change, log a “decision” with rationale + artifacts.