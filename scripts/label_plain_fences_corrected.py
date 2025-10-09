#!/usr/bin/env python3
"""
Label Plain Fences Script (Corrected)

Relabels any plain "```" to an explicit language based on content heuristics.
This version is more careful about preserving mermaid fences.
"""

import pathlib
import re

OPEN = re.compile(r'^```\s*$')
CLOSE = re.compile(r'^```\s*$')

def guess_lang(block):
    s = block.lstrip()
    
    # Check for mermaid-specific patterns first
    if re.search(r'^\s*(flowchart|graph|sequenceDiagram|classDiagram|stateDiagram|gantt|pie|gitgraph)', block, re.M):
        return "mermaid"
    
    # Check for JSON
    if s.startswith("{") or s.startswith("["):
        return "json"
    
    # Check for YAML (key: value pairs, no semicolons)
    if re.search(r'^\s*[\w\-]+\s*:\s*', block, re.M) and ";" not in block:
        return "yaml"
    
    # Check for bash/shell
    if re.search(r'^\s*(#!/|# |\$ |cd |ls |echo |export |set -|curl |grep |mkdir |rm |cp |mv )', block, re.M):
        return "bash"
    
    # Check for Python
    if re.search(r'^\s*(def |class |import |from |if |for |while |try |except )', block, re.M):
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
