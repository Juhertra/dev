#!/usr/bin/env python3
"""
Coverage Ratchet Script

Enforces milestone-based coverage thresholds per Source-of-Truth.
Usage: MILESTONE=M0 COVERAGE_PERCENT=18 python scripts/coverage_ratchet.py
"""
import os
import sys

TARGETS = {"M0":18, "M1":80, "M2":82, "M3":84, "M4":86, "M5":88, "M6":90}
mile = os.getenv("MILESTONE", "M0")
got = int(float(os.getenv("COVERAGE_PERCENT","0")))
need = TARGETS.get(mile, 18)
if got < need:
    print(f"Coverage {got}% < target {need}%"); sys.exit(1)
print(f"Coverage OK: {got}% >= {need}%")
