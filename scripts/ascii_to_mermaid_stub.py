import re, sys, pathlib
root = pathlib.Path("docs")
boxes = re.compile(r'[┌┐└┘├┤┬┴┼─│]|^\s*(\+[-+]{3,}\+|\|[^\n]*\|)\s*$', re.M)

def stub(block):
    # naive extraction: capture words inside ASCII boxes or table cells
    labels = []
    for line in block.splitlines():
        parts = re.findall(r'\|([^|]+)\|', line)
        if parts:
            for p in parts:
                p = re.sub(r'[^A-Za-z0-9 _:/.-]', '', p).strip()
                if p and p not in labels: labels.append(p)
    if not labels:
        # fallback: words between +---+ style lines
        toks = re.findall(r'[A-Za-z0-9][A-Za-z0-9 _:/.-]{2,}', block)
        labels = sorted(set(toks))[:6]
    out = ["%%{init: {\"theme\":\"neutral\"}}%%", "flowchart LR"]
    for i, lbl in enumerate(labels, 1):
        out.append(f'  n{i}["{lbl}"]')
    for i in range(1, len(labels)):
        out.append(f'  n{i} --> n{i+1}')
    return "```mermaid\n" + "\n".join(out) + "\n```"

for md in root.rglob("*.md"):
    text = md.read_text("utf-8")
    for m in re.finditer(r'```(text|ascii)?\n(.*?)\n```', text, flags=re.S):
        block = m.group(2)
        if boxes.search(block):
            s = stub(block)
            print(f"\n=== {md} ===")
            print(s)
