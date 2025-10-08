#!/usr/bin/env python3
import pathlib, re, sys, subprocess

SRC = pathlib.Path("docs")
SITE = pathlib.Path("site")

def count_source():
    txt = "\n".join(p.read_text(encoding="utf-8", errors="ignore")
                    for p in SRC.rglob("*.md"))
    return len(re.findall(r"^``` *mermaid\s*$", txt, flags=re.M))

def count_rendered():
    txt = "\n".join(p.read_text(encoding="utf-8", errors="ignore")
                    for p in SITE.rglob("*.html"))
    return len(re.findall(r'<div class="mermaid">', txt))

def main():
    # Build first
    subprocess.run(["mkdocs", "build", "-q"], check=True)
    src = count_source()
    out = count_rendered()
    print(f"Mermaid parity — source:{src} rendered:{out}")
    if out < src:
        print("❌ Parity mismatch: some Mermaid blocks are not rendering.")
        sys.exit(1)
    print("✅ Parity OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())