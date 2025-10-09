import html
import pathlib
import re

DOCS = pathlib.Path("docs")
SITE = pathlib.Path("site")

# match an opener that is *exactly* ```mermaid with no trailing spaces
RE_OPEN = re.compile(r'(?m)^```mermaid\s*$')
RE_ANY_FENCE = re.compile(r'(?m)^```(.*?)\s*$')
RE_CLOSE = re.compile(r'(?m)^```\s*$')
RE_ZW = re.compile(r'[\u200B\u200C\u200D\u2060\uFEFF]')  # zero-width, BOM
RE_INIT = re.compile(r'(?m)^%%\{init:.*?\}%%\s*$')

# what 'mermaid-like' content inside <pre><code> looks like
MERMAID_KEY = re.compile(r'\b(flowchart|graph|sequenceDiagram|classDiagram|stateDiagram|stateDiagram-v2|erDiagram|gantt|pie|journey|mindmap|timeline|xychart-beta)\b')

def md_to_html(md: pathlib.Path) -> pathlib.Path:
    rel = md.relative_to(DOCS)
    html = SITE / rel.with_suffix('') / "index.html"
    if rel.name == "index.md":
        html = SITE / rel.parent / "index.html"
    return html

def count_md_blocks(md_text: str):
    # return list of (start_line, end_line, block_text) for mermaid
    out = []
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        if RE_OPEN.match(lines[i]):
            start = i
            i += 1
            # gather until plain ```
            while i < len(lines) and not RE_CLOSE.match(lines[i]):
                i += 1
            end = min(i, len(lines)-1)
            out.append((start+1, end+1, "\n".join(lines[start+1:end])))
        i += 1
    return out

def find_code_looks_like_mermaid(html_text: str):
    # capture code blocks that contain mermaid-ish keywords
    bad = []
    # very simple: pull out code blocks
    for m in re.finditer(r'(?is)<pre[^>]*>\s*<code[^>]*>(.*?)</code>\s*</pre>', html_text):
        raw = m.group(1)
        txt = html.unescape(re.sub(r'<.*?>', '', raw))
        if MERMAID_KEY.search(txt):
            bad.append(txt.strip().splitlines()[:12])  # first lines for context
    return bad

def main():
    broken = []
    for md in DOCS.rglob("*.md"):
        htmlp = md_to_html(md)
        if not htmlp.exists():
            continue
        md_text = md.read_text(encoding="utf-8", errors="ignore")
        html_text = htmlp.read_text(encoding="utf-8", errors="ignore")

        md_blocks = count_md_blocks(md_text)
        rendered = len(re.findall(r'<div class="mermaid">', html_text))
        source = len(md_blocks)

        if source != rendered:
            row = {
                "file": str(md),
                "source": source,
                "rendered": rendered,
                "blocks": md_blocks,
                "html_code_mermaid": find_code_looks_like_mermaid(html_text),
                "has_zw": bool(RE_ZW.search(md_text)),
                "has_trailing_space_openers": any(x.endswith(" ") for x in re.findall(r'(?m)^(```mermaid)\s+$', md_text)),
            }
            broken.append(row)

    if not broken:
        print("Per-file Mermaid parity: CLEAN")
        return

    print("=== Mermaid Per-file Parity Report ===")
    for row in broken:
        print(f"\n- {row['file']}")
        print(f"  source={row['source']} rendered={row['rendered']}")
        if row["has_zw"]:
            print("  HINT: zero-width/BOM characters present")
        if row["has_trailing_space_openers"]:
            print("  HINT: opener has trailing spaces")
        # show suspect code-rendered mermaid
        for idx, snippet in enumerate(row["html_code_mermaid"], 1):
            print(f"  CODE-RENDERED #{idx}:")
            for line in snippet:
                print("    " + line)
        # show block headers with line numbers
        for i,(s,e,body) in enumerate(row["blocks"],1):
            head = ""
            for ln in (l for l in body.splitlines() if l.strip()):
                head = ln; break
            print(f"  src block #{i} lines {s}-{e}: {head[:80]}")

if __name__ == "__main__":
    main()
