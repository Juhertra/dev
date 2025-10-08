#!/usr/bin/env python3
import pathlib

bad = []
for p in pathlib.Path('docs').rglob('*.md'):
    s = p.read_text(encoding='utf-8', errors='ignore')
    if s.count('```') % 2:
        bad.append(p)

print('\n'.join(map(str, bad)))
