#!/usr/bin/env bash
set -euo pipefail
mkdocs build -q
F=$(rg -N '```mermaid' docs | grep -v 'docs/review/' | wc -l | tr -d ' ')
D=$(rg -N '<div class="mermaid">' -g 'site/**/*.html' | wc -l | tr -d ' ')
TOTAL=$(find site -name "*.html" | wc -l | tr -d ' ')
M1=$(rg -l 'mermaid\.min\.js' site -g '**/*.html' | wc -l | tr -d ' ')
M2=$(rg -l 'mermaid-init\.js' site -g '**/*.html' | wc -l | tr -d ' ')
echo "Mermaid parity: source=$F rendered=$D"
echo "JS coverage: mermaid.min.js=$M1/$TOTAL mermaid-init.js=$M2/$TOTAL"
python scripts/ascii_html_blocker_gate.py || true
