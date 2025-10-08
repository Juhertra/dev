import sys, re, pathlib
root = pathlib.Path("site")
bad = []
u_box = re.compile(r'[┌┐└┘├┤┬┴┼─│]')
# ASCII art boxes like +------+ and box-draw tables, but EXCLUDE Markdown tables rendered as HTML tables
ascii_box = re.compile(r'^\s*(\+[-+]{3,}\+)\s*$', re.M)

for html in root.rglob("*.html"):
    t = html.read_text("utf-8", errors="ignore")
    # scan only pre/code blocks to avoid CSS/fonts
    pre = re.findall(r'(?is)<pre[^>]*><code[^>]*>(.*?)</code></pre>', t)
    chunk = "\n".join(pre)
    if u_box.search(chunk) or ascii_box.search(chunk):
        bad.append(str(html))

if bad:
    print("ASCII artifacts detected in HTML:")
    for b in bad: print(" -", b)
    sys.exit(1)
print("ASCII blocker: CLEAN")