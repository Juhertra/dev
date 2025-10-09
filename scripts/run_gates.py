#!/usr/bin/env python3
"""
Gate Runner - Run all documentation quality gates

This script runs all the documentation quality gates in sequence:
1. Mermaid Parity Gate
2. ASCII HTML Blocker Gate

Returns 0 if all gates pass, 1 if any gate fails.
"""

import os
import subprocess
import sys


def run_gate(script_name, description):
    """Run a single gate script."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(['python3', script_name], 
                              capture_output=True, text=True, cwd=os.getcwd())
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error running {script_name}: {e}")
        return False


def main():
    """Run all gates."""
    print("🚀 Documentation Quality Gates")
    print("=" * 60)
    
    gates = [
        ('scripts/mermaid_parity_gate.py', 'Mermaid Parity Gate'),
        ('scripts/ascii_html_blocker_gate.py', 'ASCII HTML Blocker Gate'),
    ]
    
    all_passed = True
    
    for script, description in gates:
        if not run_gate(script, description):
            all_passed = False
    
    print(f"\n{'='*60}")
    if all_passed:
        print("🎉 ALL GATES PASSED!")
        print("Documentation quality is maintained.")
        return 0
    else:
        print("❌ SOME GATES FAILED!")
        print("Please fix the issues above before proceeding.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
