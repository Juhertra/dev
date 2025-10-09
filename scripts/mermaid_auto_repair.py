import pathlib
import re

DOCS = pathlib.Path("docs")

# Very specific patterns for the issues we found
RE_LABELED_CLOSER = re.compile(r'(?m)^```([A-Za-z0-9_.+-]+)\s*$')  # labeled closers like ```yaml, ```python
RE_TRAILING_SPACE_MERMAID = re.compile(r'(?m)^```mermaid\s+$')  # trailing spaces after mermaid
RE_ZW = re.compile(r'[\u200B\u200C\u200D\u2060\uFEFF]')  # zero-width, BOM

def fix_text(txt: str) -> str:
    changed = False
    
    # 1) Remove zero-width/BOM characters
    if RE_ZW.search(txt):
        txt = RE_ZW.sub('', txt)
        changed = True
    
    # 2) Fix trailing spaces after ```mermaid (but keep the mermaid label)
    if RE_TRAILING_SPACE_MERMAID.search(txt):
        txt = RE_TRAILING_SPACE_MERMAID.sub('```mermaid', txt)
        changed = True
    
    # 3) Fix labeled closers (remove language from closing fences)
    # But be very careful - only fix closers that are NOT mermaid openers
    lines = txt.splitlines()
    out = []
    for i, line in enumerate(lines):
        # Check if this is a labeled closer (but not a mermaid opener)
        if RE_LABELED_CLOSER.match(line) and not line.strip().startswith('```mermaid'):
            out.append('```')
            changed = True
        else:
            out.append(line)
    
    return '\n'.join(out)

def main():
    changed_files = 0
    for md in DOCS.rglob("*.md"):
        orig = md.read_text(encoding="utf-8", errors="ignore")
        fixed = fix_text(orig)
        if fixed != orig:
            md.write_text(fixed, encoding="utf-8")
            changed_files += 1
            print("fixed:", md)
    print(f"changed_files={changed_files}")

if __name__ == "__main__":
    main()