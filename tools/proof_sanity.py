import os
import re

ROOT = os.path.dirname(os.path.dirname(__file__))

PATTERNS = [
    re.compile(r"decode\((utf|UTF)\b"),
    re.compile(r"encode\((utf|UTF)\b"),
    re.compile(r"encoding\s*=\s*(utf|UTF)\b"),
]

def scan():
    hits = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        # Skip venv
        if os.path.basename(dirpath) == 'venv' or '/venv/' in dirpath:
            dirnames[:] = []
            continue
        for fn in filenames:
            if not fn.endswith(('.py','.html','.js','.txt','.md')):
                continue
            path = os.path.join(dirpath, fn)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f, 1):
                        for pat in PATTERNS:
                            if pat.search(line):
                                hits.append((path, i, line.strip()))
            except Exception:
                pass
    return hits

def append(md: str):
    with open(os.path.join(ROOT, 'DEBUG_RUN.md'), 'a', encoding='utf-8') as f:
        f.write(md)

def main():
    hits = scan()
    append('\n## Phase 2 — sanity (utf NameError check)\n')
    if not hits:
        append('No suspicious utf usages found.\n')
    else:
        append('Suspicious utf usages (file:line:excerpt):\n')
        for p, ln, ex in hits:
            append(f'- {os.path.relpath(p, ROOT)}:{ln}: {ex}\n')

if __name__ == '__main__':
    main()


