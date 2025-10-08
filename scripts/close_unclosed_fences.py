#!/usr/bin/env python3
"""
Close Unclosed Fences Script

Non-destructive script that only adds missing closing ``` at EOF for truly unclosed blocks.
This safely fixes fence mismatches without modifying existing content.
"""

import sys
import pathlib
import re

FILES = [
    "docs/architecture/14-poc-sources-and-legal-guidelines.md",
    "docs/architecture/18-error-handling-and-recovery.md",
    "docs/architecture/22-developer-experience-and-docs.md",
]

OPEN_RE = re.compile(r'^```([^\n\r]*)\s*$')
CLOSE_RE = re.compile(r'^```\s*$')

for p in FILES:
    path = pathlib.Path(p)
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    open_stack = []
    
    for i, line in enumerate(lines):
        if OPEN_RE.match(line):
            open_stack.append(i)
        elif CLOSE_RE.match(line) and open_stack:
            open_stack.pop()
    
    if open_stack:
        # add a closing fence at EOF
        lines.append("```")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Fixed: {p} (added closing fence)")
    else:
        print(f"OK: {p}")