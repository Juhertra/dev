#!/usr/bin/env python3
import pathlib
import re
import sys

ROOT = pathlib.Path("docs")
FILES = list(ROOT.rglob("*.md"))

OPEN_RE = re.compile(r"^```([a-zA-Z0-9_\-\+\.]*)\s*$")
CLOSE_RE = re.compile(r"^```\s*$")

def fix_file(p: pathlib.Path) -> bool:
    lines = p.read_text(encoding="utf-8").splitlines()
    stack = []
    changed = False

    for i, line in enumerate(lines):
        m = OPEN_RE.match(line)
        if m:
            lang = m.group(1)  # may be ''
            stack.append((i, lang))
            continue
        if CLOSE_RE.match(line):
            if stack:
                stack.pop()
            else:
                # stray closing fence — leave it (don't guess)
                pass

    # If still open blocks at EOF — close them
    if stack:
        lines.append("```")
        changed = True

    # Normalize obvious wrong closers: lines that close with a language
    for i, line in enumerate(lines):
        if line.startswith("```") and not CLOSE_RE.match(line):
            # If this is a closing line that mistakenly includes a language,
            # detect by looking ahead for the next opener before a closer.
            # Safe heuristic: if the previous non-empty line looks like content,
            # and the next non-empty line is a heading/paragraph, treat as closer.
            prev = next((lines[j].strip() for j in range(i-1, -1, -1) if lines[j].strip()), "")
            nxt  = next((lines[j].strip() for j in range(i+1, len(lines)) if lines[j].strip()), "")
            if prev and (nxt.startswith("#") or not nxt.startswith("```")):
                lines[i] = "```"
                changed = True

    if changed:
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return changed

def main():
    edited = 0
    for f in FILES:
        if fix_file(f):
            edited += 1
            print(f"[fixed] {f}")
    if edited == 0:
        print("No fence issues found.")
    else:
        print(f"Repaired fences in {edited} files.")

if __name__ == "__main__":
    sys.exit(main())
