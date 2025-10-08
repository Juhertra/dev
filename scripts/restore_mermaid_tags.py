#!/usr/bin/env python3
import re, sys, pathlib

ROOT = pathlib.Path("docs")
MERMAID_PATTERNS = [
    r'flowchart\s+',
    r'graph\s+(TD|LR|TB|RL)',
    r'sequenceDiagram',
    r'classDiagram',
    r'stateDiagram',
    r'journey',
    r'gantt',
    r'pie',
    r'gitgraph'
]

def fix_mermaid_tags(p: pathlib.Path) -> bool:
    content = p.read_text(encoding="utf-8")
    lines = content.splitlines()
    changed = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == '```':
            # Found a code block opener, check if next lines contain Mermaid syntax
            j = i + 1
            while j < len(lines) and lines[j].strip() != '```':
                for pattern in MERMAID_PATTERNS:
                    if re.search(pattern, lines[j]):
                        # This is a Mermaid diagram, fix the opener
                        lines[i] = '```mermaid'
                        changed = True
                        break
                if changed:
                    break
                j += 1
        i += 1
    
    if changed:
        p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return changed

def main():
    edited = 0
    for f in ROOT.rglob("*.md"):
        if fix_mermaid_tags(f):
            edited += 1
            print(f"[restored] {f}")
    if edited == 0:
        print("No Mermaid tags to restore.")
    else:
        print(f"Restored Mermaid tags in {edited} files.")

if __name__ == "__main__":
    main()
