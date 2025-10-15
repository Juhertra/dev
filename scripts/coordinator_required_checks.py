#!/usr/bin/env python3
"""
Coordinator Required Checks Script

This script checks that all required CI checks are passing for a PR.
It includes alias mapping to handle legacy workflow names during the transition period.

Usage:
    python scripts/coordinator_required_checks.py [PR_NUMBER]

The script will:
1. Fetch PR status from GitHub API
2. Normalize workflow names using alias mapping
3. Check that all required checks are present and passing
4. Report any missing or failing checks
"""

import os
import sys
import json
import subprocess
from typing import Dict, List, Set

# Required checks as defined in Source of Truth (SoT)
EXPECTED = ["ruff", "pyright", "imports", "unit", "coverage", "contracts", "docs-health"]

# Alias mapping for legacy workflow names during transition period
# This will be removed once all PRs emit canonical names
ALIASES = {
    "findings-contract-tests": "contracts",
    "test": "unit",
}

def normalize(name: str) -> str:
    """Normalize workflow name using alias mapping."""
    return ALIASES.get(name, name)

def get_pr_status(pr_number: str) -> Dict[str, str]:
    """Fetch PR status from GitHub API."""
    try:
        # Use gh CLI to get PR status
        cmd = ["gh", "pr", "view", pr_number, "--json", "statusCheckRollup"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        data = json.loads(result.stdout)
        statuses = {}
        
        for check in data.get("statusCheckRollup", []):
            name = check.get("name", "")
            conclusion = check.get("conclusion", "")
            statuses[name] = conclusion
            
        return statuses
        
    except subprocess.CalledProcessError as e:
        print(f"Error fetching PR status: {e}")
        print(f"stderr: {e.stderr}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        sys.exit(1)

def check_required_checks(pr_number: str) -> bool:
    """Check that all required checks are present and passing."""
    print(f"Checking required checks for PR #{pr_number}")
    print(f"Expected checks: {EXPECTED}")
    print(f"Alias mapping: {ALIASES}")
    print()
    
    # Get raw status from GitHub API
    raw_context_statuses = get_pr_status(pr_number)
    print(f"Raw contexts: {list(raw_context_statuses.keys())}")
    
    # Normalize using alias mapping
    normalized = {normalize(c): status for c, status in raw_context_statuses.items()}
    print(f"Normalized contexts: {list(normalized.keys())}")
    
    # Find missing and failing checks
    missing = [c for c in EXPECTED if c not in normalized]
    failing = [c for c, s in normalized.items() if c in EXPECTED and s != "SUCCESS"]
    
    print()
    print("=== CHECK RESULTS ===")
    
    # Report missing checks
    if missing:
        print(f"❌ MISSING CHECKS: {missing}")
        print("   These required checks are not present in the PR status.")
    else:
        print("✅ All required checks are present")
    
    # Report failing checks
    if failing:
        print(f"❌ FAILING CHECKS: {failing}")
        print("   These checks are present but not passing.")
    else:
        print("✅ All present checks are passing")
    
    # Report successful checks
    successful = [c for c, s in normalized.items() if c in EXPECTED and s == "SUCCESS"]
    if successful:
        print(f"✅ PASSING CHECKS: {successful}")
    
    # Report unknown checks (not in EXPECTED and not aliased)
    unknown = [c for c in raw_context_statuses.keys() if normalize(c) not in EXPECTED]
    if unknown:
        print(f"ℹ️  UNKNOWN CHECKS: {unknown}")
        print("   These checks are present but not in the required list.")
    
    print()
    
    # Overall result
    if missing or failing:
        print("❌ PR NOT READY FOR MERGE")
        print("   Missing or failing required checks must be resolved.")
        return False
    else:
        print("✅ PR READY FOR MERGE")
        print("   All required checks are present and passing.")
        return True

def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/coordinator_required_checks.py [PR_NUMBER]")
        sys.exit(1)
    
    pr_number = sys.argv[1]
    
    # Validate PR number
    try:
        int(pr_number)
    except ValueError:
        print(f"Error: '{pr_number}' is not a valid PR number")
        sys.exit(1)
    
    success = check_required_checks(pr_number)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
