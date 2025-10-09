"""
Parser contract tests for tool wrappers.

This module contains parametrized tests that validate parser contracts
across different tool versions using golden samples.
"""

import pytest
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Test configuration
GOLDEN_SAMPLES_DIR = Path(__file__).parent.parent / "golden_samples"
SUPPORTED_TOOLS = ["nuclei", "feroxbuster", "katana"]
SUPPORTED_VERSIONS = {
    "nuclei": ["v3.0.x", "v2.9.x"],
    "feroxbuster": ["v2.10.x", "v2.9.x"],
    "katana": ["v1.0.x", "v0.0.x"]
}


def load_golden_sample(tool: str, version: str, sample_type: str = "output") -> Optional[Dict[str, Any]]:
    """
    Load golden sample from file.
    
    Args:
        tool: Tool name (nuclei, feroxbuster, katana)
        version: Version string (v3.0.x, etc.)
        sample_type: Sample type (output, output-verbose, output-error)
        
    Returns:
        Dict containing sample data or None if not found
    """
    sample_path = GOLDEN_SAMPLES_DIR / tool / version / f"{sample_type}.json"
    
    if not sample_path.exists():
        logger.warning(f"Golden sample not found: {sample_path}")
        return None
    
    try:
        with open(sample_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load golden sample {sample_path}: {e}")
        return None


def get_available_samples() -> List[tuple]:
    """
    Get list of available golden samples for testing.
    
    Returns:
        List of (tool, version) tuples for available samples
    """
    available_samples = []
    
    for tool in SUPPORTED_TOOLS:
        tool_dir = GOLDEN_SAMPLES_DIR / tool
        if not tool_dir.exists():
            continue
            
        for version_dir in tool_dir.iterdir():
            if version_dir.is_dir():
                version = version_dir.name
                if version in SUPPORTED_VERSIONS.get(tool, []):
                    # Check if basic output sample exists
                    if (version_dir / "output.json").exists():
                        available_samples.append((tool, version))
    
    return available_samples


# Parametrized test for parser contracts
@pytest.mark.parametrize("tool,version", get_available_samples())
def test_parser_contract(tool: str, version: str):
    """
    Test parser contract for specific tool and version.
    
    This test validates that wrappers can parse outputs from all supported
    versions without breaking changes.
    """
    # Skip if no samples available (placeholder for M2)
    if not get_available_samples():
        pytest.skip("No golden samples available - to be added in M2")
    
    # Load golden sample
    sample = load_golden_sample(tool, version)
    if sample is None:
        pytest.skip(f"No golden sample available for {tool} {version}")
    
    # Import appropriate wrapper (will be implemented in M2)
    try:
        if tool == "nuclei":
            from packages.wrappers.nuclei import NucleiWrapper
            wrapper = NucleiWrapper({})
        elif tool == "feroxbuster":
            from packages.wrappers.feroxbuster import FeroxWrapper
            wrapper = FeroxWrapper({})
        elif tool == "katana":
            from packages.wrappers.katana import KatanaWrapper
            wrapper = KatanaWrapper({})
        else:
            pytest.skip(f"Wrapper not implemented for {tool}")
    except ImportError:
        pytest.skip(f"Wrapper not available for {tool} - to be implemented in M2")
    
    # Test parsing
    try:
        # Create mock ToolOutput
        from packages.wrappers.base import ToolOutput
        tool_output = ToolOutput(
            raw_output=json.dumps(sample),
            exit_code=0,
            stderr="",
            execution_time_ms=1000
        )
        
        # Parse output
        findings = wrapper.parse_output(tool_output)
        
        # Validate findings
        assert isinstance(findings, list), f"Expected list of findings, got {type(findings)}"
        assert len(findings) > 0, f"No findings parsed from {tool} {version} sample"
        
        # Validate finding structure
        for finding in findings:
            assert hasattr(finding, 'title'), "Finding missing title"
            assert hasattr(finding, 'severity'), "Finding missing severity"
            assert hasattr(finding, 'path'), "Finding missing path"
            assert hasattr(finding, 'detector_id'), "Finding missing detector_id"
            assert hasattr(finding, 'evidence'), "Finding missing evidence"
            
            # Validate detector_id matches tool
            assert finding.detector_id == tool, f"Expected detector_id '{tool}', got '{finding.detector_id}'"
            
            # Validate severity is valid
            valid_severities = ["critical", "high", "medium", "low", "info"]
            assert finding.severity in valid_severities, f"Invalid severity: {finding.severity}"
        
        logger.info(f"✅ Parser contract passed for {tool} {version}: {len(findings)} findings")
        
    except Exception as e:
        pytest.fail(f"Parser contract failed for {tool} {version}: {str(e)}")


def test_parser_performance_benchmark():
    """
    Test parser performance meets baseline requirements.
    
    Baseline: ≥1000 findings/sec parsing performance
    """
    # Skip if no samples available
    if not get_available_samples():
        pytest.skip("No golden samples available - to be added in M2")
    
    # This will be implemented in M2 with actual performance testing
    pytest.skip("Performance benchmark to be implemented in M2")


def test_parser_error_handling():
    """
    Test parser error handling with malformed inputs.
    """
    # Skip if no samples available
    if not get_available_samples():
        pytest.skip("No golden samples available - to be added in M2")
    
    # This will be implemented in M2 with error case testing
    pytest.skip("Error handling tests to be implemented in M2")


def test_parser_version_compatibility():
    """
    Test parser compatibility across different tool versions.
    """
    # Skip if no samples available
    if not get_available_samples():
        pytest.skip("No golden samples available - to be added in M2")
    
    # This will be implemented in M2 with cross-version testing
    pytest.skip("Version compatibility tests to be implemented in M2")


# Placeholder test for M0 scaffolding
@pytest.mark.skip(reason="golden samples to be added in M2")
def test_parser_contract_placeholder():
    """
    Placeholder test to ensure contract test skeleton runs without failures.
    
    This test will be replaced with actual parser contract tests in M2
    when golden samples and wrapper implementations are available.
    """
    assert True


# Test golden samples directory structure
def test_golden_samples_structure():
    """
    Test that golden samples directory structure is properly set up.
    """
    assert GOLDEN_SAMPLES_DIR.exists(), f"Golden samples directory not found: {GOLDEN_SAMPLES_DIR}"
    
    for tool in SUPPORTED_TOOLS:
        tool_dir = GOLDEN_SAMPLES_DIR / tool
        assert tool_dir.exists(), f"Tool directory not found: {tool_dir}"
        
        # Check for README
        readme_path = tool_dir / "README.md"
        assert readme_path.exists(), f"README not found for {tool}: {readme_path}"
        
        # Check README content
        with open(readme_path, 'r') as f:
            content = f.read()
            assert tool in content, f"README for {tool} doesn't mention tool name"
            assert "Version Policy" in content, f"README for {tool} missing version policy"


# Test manifest validation
def test_manifest_validation():
    """
    Test that tool manifests can be validated.
    """
    try:
        from packages.wrappers.manifest import ManifestValidator, NUCLEI_MANIFEST_TEMPLATE
        
        validator = ManifestValidator()
        validator.validate_manifest(NUCLEI_MANIFEST_TEMPLATE)
        
        logger.info("✅ Manifest validation test passed")
        
    except ImportError:
        pytest.skip("Manifest module not available")
    except Exception as e:
        pytest.fail(f"Manifest validation failed: {str(e)}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
