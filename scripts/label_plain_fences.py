#!/usr/bin/env python3
"""
Label Plain Fences Script

Relabels any plain "```" to an explicit language based on content heuristics:
- yaml: if it starts with {/[ not (→ that's JSON) and has : pairs + no ;
- json: if the first non-space char is { or [
- bash: if it starts with $, # , #!/, or typical shell forms
- python: if it starts with def , class , import
- text: otherwise
"""

import re
import pathlib
import sys

OPEN = re.compile(r'^```\s*$')
CLOSE = re.compile(r'^```\s*$')

def guess_lang(block):
    s = block.lstrip()
    if s.startswith("{") or s.startswith("["):
        return "json"
    if re.search(r'^\s*[\w\-]+\s*:\s*', block, re.M) and ";" not in block:
        return "yaml"
    if re.search(r'^\s*(#!/|# |\$ |cd |ls |echo |export |set -|curl |grep )', block, re.M):
        return "bash"
    if re.search(r'^\s*(def |class |import |from )', block, re.M):
        return "python"
    return "text"

for md in pathlib.Path("docs").rglob("*.md"):
    lines = md.read_text(encoding="utf-8", errors="ignore").splitlines()
    out, i, changed = [], 0, False
    
    while i < len(lines):
        if OPEN.match(lines[i]):
            j = i + 1
            while j < len(lines) and not CLOSE.match(lines[j]):
                j += 1
            if j >= len(lines):
                out.extend(lines[i:])  # leave it; PROMPT 3 handles closures
                break
            block = "\n".join(lines[i+1:j])
            lang = guess_lang(block)
            out.append(f"```{lang}")
            out.extend(lines[i+1:j])
            out.append("```")
            i = j + 1
            changed = True
        else:
            out.append(lines[i])
            i += 1
    
    if changed:
        md.write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"Relabeled: {md}")
