#!/usr/bin/env python3
import pathlib
import re
import sys

SITE = pathlib.Path("site")
# More specific patterns for actual ASCII diagrams, not HTML/CSS
BAD = re.compile(r"[│─┌┐└┘├┤┬┴┼]|\+\-{3,}\+|\|\s+\|")

def main():
    offenders = []
    for f in SITE.rglob("*.html"):
        txt = f.read_text(encoding="utf-8", errors="ignore")
        # Only check the content area, not HTML/CSS
        content_match = re.search(r'<main[^>]*>(.*?)</main>', txt, re.DOTALL)
        if content_match:
            content = content_match.group(1)
            if BAD.search(content):
                offenders.append(str(f))
        else:
            # Fallback: check entire file but exclude obvious HTML/CSS
            if BAD.search(txt) and not re.search(r'<style|href=|src=', txt):
                offenders.append(str(f))
    
    if offenders:
        print("❌ ASCII artifacts in HTML:")
        for o in offenders[:50]:
            print(" -", o)
        sys.exit(1)
    print("✅ No ASCII artifacts in HTML")
    return 0

if __name__ == "__main__":
    sys.exit(main())
