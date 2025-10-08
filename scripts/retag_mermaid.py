#!/usr/bin/env python3
import pathlib, re

ROOT = pathlib.Path("docs")
FILES = list(ROOT.rglob("*.md"))

MERMAID_HINTS = (
    r"\bflowchart\b",
    r"\bgraph\s+(TD|LR)\b",
    r"\bsequenceDiagram\b",
    r"\bclassDiagram\b",
    r"\berDiagram\b",
    r"\bstateDiagram(-v2)?\b",
    r"\bgantt\b",
)

OPEN_ANY = re.compile(r"^```(text|python|yaml|json|ini|toml)?\s*$", re.I)
HINT_RE = re.compile("|".join(MERMAID_HINTS), re.I)

def retag_file(path: pathlib.Path) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines()
    out, in_block, opener_idx, opener_lang = [], False, None, None
    changed = False

    for i, line in enumerate(lines):
        m = OPEN_ANY.match(line)
        if m and not in_block:
            in_block = True
            opener_idx = len(out)
            opener_lang = (m.group(1) or "").lower()
            out.append(line)
            continue

        if in_block and line.strip() == "```":
            # Decide if this block is mermaid
            block = out[opener_idx+1:]  # content after opener
            block.append(line)          # include this closer temporarily
            content = "\n".join(block[:-1])
            is_mermaid = bool(HINT_RE.search(content))
            if is_mermaid and opener_lang != "mermaid":
                out[opener_idx] = "```mermaid"
                changed = True
            out[-0:] = []  # no-op
            out.append(line)
            in_block = False
            opener_idx = None
            opener_lang = None
            continue

        out.append(line)

    if changed:
        path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changed

def main():
    edited = 0
    for f in FILES:
        if retag_file(f):
            edited += 1
            print(f"[retagged] {f}")
    print(f"Retagged {edited} files.")

if __name__ == "__main__":
    main()
