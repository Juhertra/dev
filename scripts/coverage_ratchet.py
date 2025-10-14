#!/usr/bin/env python3
"""
Coverage Ratchet Script

Enforces milestone-based coverage thresholds per Source-of-Truth.
Usage: MILESTONE=M0 COVERAGE_PERCENT=18 python scripts/coverage_ratchet.py
"""
import os
import sys

# Milestone coverage thresholds per Engineering Standards
target = {"M0":18, "M1":80, "M2":82, "M3":84, "M4":86, "M5":88, "M6":90}.get(os.getenv("MILESTONE","M0"),18)
cov = int(os.getenv("COVERAGE_PERCENT","0"))

if cov < target: 
    print(f"Coverage {cov}% < target {target}%")
    sys.exit(1)
print(f"Coverage OK: {cov}% >= {target}%")
