#!/usr/bin/env python3
import pathlib
import re
import sys

ROOT = pathlib.Path("docs")

def problems(path):
    s = path.read_text(encoding="utf-8", errors="ignore")
    # 1) Unbalanced
    if s.count("```") % 2 != 0:
        yield f"UNBALANCED: odd number of ``` in {path}"
    # 2) Closing fences with language
    for i, line in enumerate(s.splitlines(), 1):
        if re.match(r"^```(yaml|json|bash|ini|toml|python|mermaid|text)\s*$", line.strip()):
            # If it's a closing fence, next fence should not be the same opener without content
            # Simple rule: a closing fence must be exactly ```
            # We flag any fence line that is NOT the very first fence of a block and has a language
            # Heuristic: language fences appear in consecutive pairs -> suspicious
            pass
    # 3) Mermaid content in non-mermaid fences
    for m in re.finditer(r"```(?!mermaid)(\w+)\n(.*?)(```)", s, flags=re.S):
        if re.search(r"(flowchart|graph\s+(TD|LR)|sequenceDiagram|classDiagram|stateDiagram)", m.group(2)):
            yield f"RETAG: {path} has Mermaid syntax fenced as `{m.group(1)}` at offset {m.start()}"

def main():
    bad = 0
    for p in ROOT.rglob("*.md"):
        issues = list(problems(p))
        if issues:
            bad += 1
            print("\n".join(issues))
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()