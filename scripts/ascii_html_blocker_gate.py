import sys, re, pathlib
root = pathlib.Path("site")
bad = []
# Unicode box drawing characters
u_box = re.compile(r'[┌┐└┘├┤┬┴┼─│]')
# ASCII art patterns: +---+ style boxes
ascii_box = re.compile(r'^\s*\+[-+]{3,}\+\s*$', re.M)

for html in root.rglob("*.html"):
    t = html.read_text("utf-8", errors="ignore")
    # focus on pre/code blocks to avoid CSS false positives
    pre = re.findall(r'<pre[^>]*><code[^>]*>(.*?)</code></pre>', t, flags=re.S|re.I)
    chunk = "\n".join(pre) if pre else t
    
    # Check for Unicode box drawing
    if u_box.search(chunk):
        bad.append(str(html))
        continue
    
    # Check for ASCII art (but not simple tables)
    if ascii_box.search(chunk):
        bad.append(str(html))
        continue

if bad:
    print("ASCII artifacts detected in HTML:")
    for b in bad: print(" -", b)
    sys.exit(1)
print("ASCII blocker: CLEAN")
