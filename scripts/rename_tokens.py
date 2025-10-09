#!/usr/bin/env python3
import argparse
import pathlib
import re
import sys
from typing import Iterable

DEFAULT_EXTS = {
    ".md",".mdx",".py",".yml",".yaml",".toml",".ini",".cfg",".conf",
    ".json",".js",".ts",".tsx",".jsx",".html",".css",".txt",".jinja",".j2"
}
EXCLUDE_DIRS = {".git","venv",".venv","site","node_modules","dist","build","__pycache__",".mypy_cache",".pytest_cache"}

PATTERNS = [
    (re.compile(r"\bFINANCE\b"), "SECFLOW"),
    (re.compile(r"\bFinance\b"), "SecFlow"),
    (re.compile(r"\bfinance\b"), "secflow"),
]

def iter_files(root: pathlib.Path, exts: set[str]) -> Iterable[pathlib.Path]:
    for p in root.rglob("*"):
        if p.is_dir():
            if p.name in EXCLUDE_DIRS: 
                # skip whole subtree
                for _ in p.rglob("*"): 
                    pass
            continue
        if p.suffix in exts:
            # skip binary-ish by size heuristic (optional)
            if p.stat().st_size > 2_000_000: 
                continue
            yield p

def replace_text(text: str):
    total = 0
    for rx, repl in PATTERNS:
        text, n = rx.subn(repl, text)
        total += n
    return text, total

def main():
    ap = argparse.ArgumentParser(description="Safe whole-word token rename (content only).")
    ap.add_argument("--root", default="dev", help="project root (default: dev)")
    ap.add_argument("--write", action="store_true", help="apply changes (default: dry-run)")
    ap.add_argument("--ext", nargs="*", default=sorted(DEFAULT_EXTS), help="file extensions to include")
    args = ap.parse_args()

    root = pathlib.Path(args.root).resolve()
    if not root.exists():
        print(f"ERROR: root not found: {root}", file=sys.stderr); sys.exit(2)

    changed_files = 0
    total_replacements = 0
    findings = []

    for f in iter_files(root, set(args.ext)):
        try:
            s = f.read_text(encoding="utf-8")
        except Exception:
            continue
        new_s, n = replace_text(s)
        if n:
            findings.append((f, n))
            total_replacements += n
            if args.write:
                f.write_text(new_s, encoding="utf-8")
                changed_files += 1

    if findings:
        print("Rename findings:")
        for f, n in sorted(findings, key=lambda x: str(x[0])):
            print(f"  {f}  (+{n})")
    else:
        print("No matching tokens found.")

    mode = "APPLIED" if args.write else "DRY-RUN"
    print(f"\nSummary: {mode} replacements={total_replacements} files_changed={changed_files if args.write else 0}")
    sys.exit(0)

if __name__ == "__main__":
    main()
