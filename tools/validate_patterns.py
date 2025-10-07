#!/usr/bin/env python3
import json
import sys
import glob
import os

def main() -> int:
    base = os.path.dirname(os.path.dirname(__file__))
    pattern_glob = os.path.join(base, 'detectors', 'patterns', '**', '*.json')
    errors = 0
    for path in glob.glob(pattern_glob, recursive=True):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                json.load(f)
        except json.JSONDecodeError as e:
            print(f"[ERROR] {path}:{e.lineno}:{e.colno} {e.msg}")
            errors += 1
        except Exception as e:
            print(f"[ERROR] {path}: cannot open file: {e}")
            errors += 1
    if errors:
        return 1
    print("All pattern JSON files valid.")
    return 0

if __name__ == '__main__':
    sys.exit(main())


