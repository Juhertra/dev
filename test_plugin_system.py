#!/usr/bin/env python3
"""
SecFlow Plugin System Test Script

This script tests the complete plugin system including:
- Plugin loading and registration
- Discovery phase (Feroxbuster)
- Scanning phase (Nuclei)
- Enrichment phase (CVE Mapper)
- End-to-end pipeline validation
"""

import sys
import json
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent))

from packages.plugins.loader import execute_plugin, list_available_plugins


def test_plugin_registration():
    """Test plugin registration and availability."""
    print("=== Testing Plugin Registration ===")
    
    plugins = list_available_plugins()
    print(f"Available plugins: {len(plugins)}")
    
    for plugin_id, info in plugins.items():
        print(f"  {plugin_id}: {info['name']} v{info['version']} ({info['type']})")
    
    expected_plugins = ['discovery.ferox', 'scan.nuclei', 'enricher.cve_mapper']
    for expected in expected_plugins:
        if expected not in plugins:
            print(f"❌ Missing expected plugin: {expected}")
            return False
    
    print("✅ All expected plugins registered")
    return True


def test_discovery_phase():
    """Test Feroxbuster discovery plugin."""
    print("\n=== Testing Discovery Phase ===")
    
    config = {
        "target": "https://example.com",
        "threads": 50,
        "timeout": 10
    }
    
    result = execute_plugin("discovery.ferox", config)
    
    if not result['success']:
        print(f"❌ Discovery failed: {result['error']}")
        return False, []
    
    output = result['output']
    urls = output['results']['urls']
    
    print(f"✅ Discovered {len(urls)} URLs")
    print(f"   Execution time: {output['results']['execution_time_ms']}ms")
    print(f"   Sample URLs: {[url['url'] for url in urls[:3]]}")
    
    return True, urls


def test_scanning_phase(target_urls):
    """Test Nuclei scanning plugin."""
    print("\n=== Testing Scanning Phase ===")
    
    config = {
        "targets": [url['url'] for url in target_urls[:3]],  # Use first 3 URLs
        "templates": "res://templates/nuclei:latest",
        "threads": 25,
        "rate_limit": 150
    }
    
    result = execute_plugin("scan.nuclei", config)
    
    if not result['success']:
        print(f"❌ Scanning failed: {result['error']}")
        return False, []
    
    output = result['output']
    findings = output['results']['findings']
    
    print(f"✅ Found {len(findings)} vulnerabilities")
    print(f"   Execution time: {output['results']['execution_time_ms']}ms")
    
    # Show severity breakdown
    severity_counts = {}
    for finding in findings:
        severity = finding.get('severity', 'unknown')
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    print(f"   Severity breakdown: {severity_counts}")
    print(f"   Sample finding: {findings[0]['title']} ({findings[0]['severity']})")
    
    return True, findings


def test_enrichment_phase(findings):
    """Test CVE enrichment plugin."""
    print("\n=== Testing Enrichment Phase ===")
    
    config = {
        "findings": findings,
        "severity_threshold": "low"
    }
    
    result = execute_plugin("enricher.cve_mapper", config)
    
    if not result['success']:
        print(f"❌ Enrichment failed: {result['error']}")
        return False
    
    output = result['output']
    enriched_findings = output['results']['enriched_findings']
    stats = output['results']['statistics']
    
    print(f"✅ Enriched {stats['enriched_findings']} findings")
    print(f"   Execution time: {output['results']['execution_time_ms']}ms")
    print(f"   CVE mapped: {stats['cve_mapped']}")
    print(f"   Severity upgraded: {stats['severity_upgraded']}")
    
    # Show enriched finding example
    enriched = enriched_findings[0]
    if 'cve_details' in enriched:
        cve = enriched['cve_details']
        print(f"   Sample CVE: {cve['cve_id']} ({cve['severity']}) - CVSS {cve['cvss_score']}")
    
    return True


def test_end_to_end_pipeline():
    """Test complete end-to-end security pipeline."""
    print("\n=== Testing End-to-End Pipeline ===")
    
    # Step 1: Discovery
    success, urls = test_discovery_phase()
    if not success:
        return False
    
    # Step 2: Scanning
    success, findings = test_scanning_phase(urls)
    if not success:
        return False
    
    # Step 3: Enrichment
    success = test_enrichment_phase(findings)
    if not success:
        return False
    
    print("\n✅ End-to-end pipeline completed successfully")
    return True


def main():
    """Main test function."""
    print("SecFlow Plugin System Test")
    print("=" * 50)
    
    try:
        # Test plugin registration
        if not test_plugin_registration():
            sys.exit(1)
        
        # Test end-to-end pipeline
        if not test_end_to_end_pipeline():
            sys.exit(1)
        
        print("\n" + "=" * 50)
        print("🎉 All tests passed! Plugin system is operational.")
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
