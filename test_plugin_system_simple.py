#!/usr/bin/env python3
"""
Simple Plugin System Test Script

This script tests the dynamic plugin loader and real tool integration
without the complex workflow execution.
"""

import sys
import json
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent))

from packages.plugins.loader import DynamicPluginLoader, PluginLoader


def test_dynamic_plugin_loading():
    """Test dynamic plugin loading capabilities."""
    print("=== Testing Dynamic Plugin Loading ===")
    
    # Initialize dynamic loader
    dynamic_loader = DynamicPluginLoader(enable_security=False)
    
    # Discover plugins
    discovered = dynamic_loader.discover_plugins()
    print(f"Discovered {len(discovered)} plugins:")
    for plugin in discovered:
        print(f"  - {plugin}")
    
    # Test loading real Nuclei plugin
    print("\n--- Testing Real Nuclei Plugin ---")
    real_nuclei = dynamic_loader.load_plugin_by_name('packages.plugins.scan.real_nuclei')
    
    if real_nuclei:
        print(f"✅ Loaded real Nuclei plugin: {real_nuclei.get_name()} v{real_nuclei.get_version()}")
        
        # Test execution with golden samples
        print("Testing execution with golden samples...")
        result = dynamic_loader.execute_plugin('packages.plugins.scan.real_nuclei', {
            'targets': ['https://example.com'],
            'use_golden_samples': True
        })
        
        if result['success']:
            findings = result['output']['results']['findings']
            print(f"✅ Found {len(findings)} vulnerabilities")
            print(f"   Execution method: {result['output']['results']['method']}")
            print(f"   Real tool available: {result['output']['metadata']['real_tool_available']}")
        else:
            print(f"❌ Execution failed: {result['error']}")
    else:
        print("❌ Failed to load real Nuclei plugin")


def test_standard_plugin_loader():
    """Test standard plugin loader."""
    print("\n=== Testing Standard Plugin Loader ===")
    
    loader = PluginLoader()
    plugins = loader.get_available_plugins()
    
    print(f"Available plugins: {len(plugins)}")
    for plugin_id, info in plugins.items():
        print(f"  {plugin_id}: {info['name']} v{info['version']} ({info['type']})")
    
    # Test execution
    print("\n--- Testing Plugin Execution ---")
    
    # Test discovery
    discovery_result = loader.execute_plugin("discovery.ferox", {
        "target": "https://example.com"
    })
    
    if discovery_result['success']:
        urls = discovery_result['output']['results']['urls']
        print(f"✅ Discovery: Found {len(urls)} URLs")
        
        # Test scanning
        scan_result = loader.execute_plugin("scan.nuclei", {
            "targets": ["https://example.com"]
        })
        
        if scan_result['success']:
            findings = scan_result['output']['results']['findings']
            print(f"✅ Scanning: Found {len(findings)} vulnerabilities")
            
            # Test enrichment
            enrichment_result = loader.execute_plugin("enricher.cve_mapper", {
                "findings": findings
            })
            
            if enrichment_result['success']:
                enriched = enrichment_result['output']['results']['enriched_findings']
                stats = enrichment_result['output']['results']['statistics']
                print(f"✅ Enrichment: Processed {stats['enriched_findings']} findings")
                print(f"   CVE mapped: {stats['cve_mapped']}")
                print(f"   Severity upgraded: {stats['severity_upgraded']}")
            else:
                print(f"❌ Enrichment failed: {enrichment_result['error']}")
        else:
            print(f"❌ Scanning failed: {scan_result['error']}")
    else:
        print(f"❌ Discovery failed: {discovery_result['error']}")


def test_plugin_security():
    """Test plugin security features."""
    print("\n=== Testing Plugin Security ===")
    
    # Test with security enabled
    secure_loader = DynamicPluginLoader(enable_security=True)
    
    # Test plugin signature verification
    real_nuclei = secure_loader.load_plugin_by_name('packages.plugins.scan.real_nuclei')
    
    if real_nuclei:
        print(f"✅ Plugin loaded with security enabled: {real_nuclei.get_name()}")
        
        # Test signature verification
        signature_valid = real_nuclei.verify_signature()
        print(f"✅ Signature verification: {'PASSED' if signature_valid else 'FAILED'}")
        
        # Test metadata
        metadata = real_nuclei.get_metadata()
        print(f"✅ Plugin metadata:")
        print(f"   Name: {metadata.name}")
        print(f"   Version: {metadata.version}")
        print(f"   Type: {metadata.plugin_type}")
        print(f"   Capabilities: {metadata.capabilities}")
        print(f"   Signed: {metadata.signature is not None}")
    else:
        print("❌ Failed to load plugin with security enabled")


def main():
    """Main test function."""
    print("SecFlow Plugin System Test")
    print("=" * 50)
    
    try:
        # Test dynamic plugin loading
        test_dynamic_plugin_loading()
        
        # Test standard plugin loader
        test_standard_plugin_loader()
        
        # Test plugin security
        test_plugin_security()
        
        print("\n" + "=" * 50)
        print("🎉 All plugin system tests completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
