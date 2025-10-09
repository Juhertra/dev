#!/usr/bin/env bash
set -euo pipefail

DATE_UTC=$(date -u +"%Y-%m-%d")
OUT="reports/eod/${DATE_UTC}.md"
mkdir -p reports/eod

echo "# EOD ${DATE_UTC} (UTC)" > "$OUT"
echo "" >> "$OUT"

# --- CI signals (run quietly; collect output) ---
echo "## CI Signals" >> "$OUT"
echo '```console' >> "$OUT"
( set -x
make lint >/dev/null 2>&1 || echo "[warn] lint failed (see CI)"
make type >/dev/null 2>&1 || echo "[warn] type check failed (see CI)"
make unit >/dev/null 2>&1 || echo "[warn] unit tests failed (see CI)"
make health >/dev/null 2>&1 || echo "[warn] docs health failed (see CI)"
) 2>&1 | sed 's/^+ /$ /' >> "$OUT"
echo '```' >> "$OUT"
echo "" >> "$OUT"

# --- Coverage snapshot ---
echo "## Coverage" >> "$OUT"
if command -v pytest >/dev/null 2>&1 && python -c "import pytest_cov" 2>/dev/null; then
  COV_OUTPUT=$(make _eod_local_coverage 2>&1 || true)
  COV_RAW=$(echo "$COV_OUTPUT" | grep -o 'TOTAL.*[0-9]\{1,3\}%' | grep -o '[0-9]\{1,3\}%' | tail -n1 || true)
  COV=${COV_RAW:-unknown}
else
  COV="unknown (pytest-cov not available)"
fi
echo "- TOTAL coverage: **${COV}**" >> "$OUT"
echo "" >> "$OUT"

# --- PR activity via GitHub CLI (optional) ---
echo "## PRs merged today" >> "$OUT"
if command -v gh >/dev/null 2>&1; then
  gh pr list --state merged --search "merged:>${DATE_UTC}T00:00Z" --limit 50 \
    --json number,title,author,mergeCommit \
    | jq -r '.[] | "- #\(.number) \(.title) by @\(.author.login)"' >> "$OUT" || echo "- (none)" >> "$OUT"
else
  echo "- (gh not installed; skip)" >> "$OUT"
fi
echo "" >> "$OUT"

echo "## Open PRs missing required checks" >> "$OUT"
if command -v gh >/dev/null 2>&1; then
  gh pr list --state open --limit 50 --json number,title,headRefName,isDraft \
    | jq -r '.[] | select(.isDraft==false) | "- #\(.number) \(.title) [\(.headRefName)]"' >> "$OUT" || echo "- (none)" >> "$OUT"
else
  echo "- (gh not installed; skip)" >> "$OUT"
fi
echo "" >> "$OUT"

# --- Docs health echo (replicate make health) ---
echo "## Docs Health" >> "$OUT"
echo '```console' >> "$OUT"
( set -x; make health ) 2>&1 | sed 's/^+ /$ /' >> "$OUT" || true
echo '```' >> "$OUT"
echo "" >> "$OUT"

# --- Red/Yellow flags checklist ---
cat >> "$OUT" <<'EOF'
## Red/Yellow Flags
- [ ] Any failing required check (ruff, pyright, import-linter, unit, contracts, docs-health)?
- [ ] Coverage below ratchet target?
- [ ] Contract test failing (finding invariants / storage layout)?
- [ ] Docs health failing (mermaid parity, ASCII blocker)?
- [ ] Security policy change without @security-lead review?
- [ ] Blocked issue idle >24h without owner update?

## Coordinator Decision
- **GO / NO-GO**: <pick one>
- Notes: <short rationale, blockers, reassignment>
EOF

echo "Wrote $OUT"
