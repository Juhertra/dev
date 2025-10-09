#!/usr/bin/env python3
"""
Initialize ASVS template support for Nuclei wrapper.
Run this script to register ASVS templates if you have them installed.
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from nuclei_integration import nuclei_integration


def main():
    """Initialize ASVS template support."""
    
    # Common ASVS template locations
    asvs_paths = [
        "/opt/owasp-asvs-nuclei",
        "/opt/owasp-asvs-security-evaluation-templates-with-nuclei",
        os.path.expanduser("~/owasp-asvs-nuclei"),
        os.path.expanduser("~/owasp-asvs-security-evaluation-templates-with-nuclei"),
        "./asvs-templates"
    ]
    
    print("🔍 Looking for ASVS template directories...")
    
    found_paths = []
    for path in asvs_paths:
        if os.path.isdir(path):
            print(f"✅ Found ASVS templates at: {path}")
            found_paths.append(path)
        else:
            print(f"❌ Not found: {path}")
    
    if not found_paths:
        print("\n📋 To use ASVS templates:")
        print("1. Clone the ASVS repository:")
        print("   git clone https://github.com/OWASP/owasp-asvs-security-evaluation-templates-with-nuclei.git")
        print("2. Place it in one of these locations:")
        for path in asvs_paths:
            print(f"   - {path}")
        print("3. Run this script again")
        return
    
    # Register found paths
    for path in found_paths:
        try:
            nuclei_integration.nuclei.register_template_dir(path, source="asvs")
            print(f"✅ Registered ASVS templates from: {path}")
        except Exception as e:
            print(f"❌ Failed to register {path}: {e}")
    
    # Test the integration
    print("\n🧪 Testing template integration...")
    try:
        templates = nuclei_integration.nuclei.list_templates(all_templates=True)
        nuclei_count = len([t for t in templates if t.get("source") == "nuclei"])
        asvs_count = len([t for t in templates if t.get("source") == "asvs"])
        
        print("📊 Template counts:")
        print(f"   - Nuclei templates: {nuclei_count}")
        print(f"   - ASVS templates: {asvs_count}")
        print(f"   - Total: {len(templates)}")
        
        if asvs_count > 0:
            print("\n🎉 ASVS integration successful!")
            print("You can now use ASVS templates in Active Testing.")
        else:
            print("\n⚠️  No ASVS templates found. Check the directory structure.")
            
    except Exception as e:
        print(f"❌ Error testing integration: {e}")

if __name__ == "__main__":
    main()
