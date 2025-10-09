import pathlib
import re

root = pathlib.Path("docs")
OPEN = re.compile(r'^```([a-zA-Z0-9_\-+.]+)?\s*$')
CLOSE = re.compile(r'^```\s*$')
changed = False

for md in root.rglob("*.md"):
    lines = md.read_text(encoding="utf-8").splitlines()
    out, stack = [], []
    for i, line in enumerate(lines):
        m = OPEN.match(line)
        if m:
            lang = (m.group(1) or "").strip()
            # strip trailing spaces, normalize mermaid opener
            if lang == "mermaid" and line.rstrip() != "```mermaid":
                line = "```mermaid"
                changed = True
            stack.append((lang, i))
            out.append(line)
            continue
        # normalize any closing fence to plain ```
        if line.startswith("```") and not CLOSE.match(line):
            out.append("```"); changed = True
            continue
        out.append(line)

    # close unclosed fence at EOF
    if stack and not CLOSE.match(out[-1] if out else ""):
        out.append("```"); changed = True

    if changed:
        md.write_text("\n".join(out) + "\n", encoding="utf-8")
        changed = False
print("OK")
