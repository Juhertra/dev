#!/usr/bin/env python3
"""
CI Gate Script for Mermaid Documentation
Runs both Mermaid parity and ASCII artifact checks
"""
import subprocess
import sys

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"🔍 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            if result.stdout.strip():
                print(f"   {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} - FAILED")
            if result.stdout.strip():
                print(f"   {result.stdout.strip()}")
            if result.stderr.strip():
                print(f"   Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False

def main():
    print("🚀 Running Mermaid Documentation CI Gates")
    print("=" * 50)
    
    # Build the documentation first
    if not run_command("mkdocs build", "Building documentation"):
        print("❌ Build failed - cannot proceed with validation")
        sys.exit(1)
    
    # Run Mermaid parity check
    parity_ok = run_command("python scripts/mermaid_parity.py", "Mermaid parity check")
    
    # Run ASCII artifact check
    ascii_ok = run_command("python scripts/block_ascii_html.py", "ASCII artifact check")
    
    print("=" * 50)
    if parity_ok and ascii_ok:
        print("🎉 All CI gates passed!")
        sys.exit(0)
    else:
        print("💥 CI gates failed - PR should be blocked")
        sys.exit(1)

if __name__ == "__main__":
    main()
