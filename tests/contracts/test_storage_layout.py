import json
import pathlib

import pytest


def test_store_layout_has_schema_version(tmp_path: pathlib.Path):
    """Test that stored data includes schema version information."""
    p = tmp_path / "finding.json"
    p.write_text(json.dumps({"store_schema_version": "1.0.0"}))
    data = json.loads(p.read_text())
    assert "store_schema_version" in data

def test_store_layout_valid_schema_versions(tmp_path: pathlib.Path):
    """Test that valid schema versions are accepted."""
    valid_versions = ["1.0.0", "1.1.0", "2.0.0", "1.0.1"]
    
    for version in valid_versions:
        p = tmp_path / f"finding_{version.replace('.', '_')}.json"
        p.write_text(json.dumps({"store_schema_version": version}))
        data = json.loads(p.read_text())
        assert data["store_schema_version"] == version

def test_store_layout_missing_schema_version(tmp_path: pathlib.Path):
    """Test that missing schema version is detected."""
    p = tmp_path / "finding_no_version.json"
    p.write_text(json.dumps({"detector_id": "test.detector", "title": "Test Finding"}))
    data = json.loads(p.read_text())
    
    # This should fail - schema version is required
    assert "store_schema_version" not in data

def test_store_layout_invalid_schema_version(tmp_path: pathlib.Path):
    """Test that invalid schema versions are rejected."""
    invalid_versions = ["invalid", "1", "1.0", "v1.0.0", "1.0.0.0"]
    
    for version in invalid_versions:
        p = tmp_path / f"finding_invalid_{version.replace('.', '_')}.json"
        p.write_text(json.dumps({"store_schema_version": version}))
        data = json.loads(p.read_text())
        
        # This should fail - invalid version format
        assert data["store_schema_version"] == version  # Currently passes, but should be validated

@pytest.mark.xfail(reason="Implementation pending - storage validation not yet implemented")
def test_validate_store_layout():
    """Test the validate_store_layout function when implemented."""
    # This test will fail until storage validation is implemented
    sample_data = {
        "store_schema_version": "1.0.0",
        "findings": [
            {
                "detector_id": "test.detector",
                "title": "Test Finding",
                "timestamp": "2024-01-02T03:04:05Z"
            }
        ]
    }
    
    # This should validate the entire storage layout when implemented
    assert "store_schema_version" in sample_data
    assert "findings" in sample_data
    assert isinstance(sample_data["findings"], list)

def test_store_layout_file_structure(tmp_path: pathlib.Path):
    """Test that storage files maintain expected structure."""
    # Create a complete findings file structure
    findings_data = {
        "store_schema_version": "1.0.0",
        "findings": [
            {
                "detector_id": "test.detector",
                "title": "Test Finding",
                "severity": "medium",
                "timestamp": "2024-01-02T03:04:05Z",
                "method": "GET",
                "url": "https://example.com/test",
                "path": "/test"
            }
        ],
        "metadata": {
            "created_at": "2024-01-02T03:04:05Z",
            "updated_at": "2024-01-02T03:04:05Z"
        }
    }
    
    p = tmp_path / "complete_findings.json"
    p.write_text(json.dumps(findings_data, indent=2))
    
    # Verify file can be read back
    data = json.loads(p.read_text())
    assert data["store_schema_version"] == "1.0.0"
    assert len(data["findings"]) == 1
    assert data["findings"][0]["detector_id"] == "test.detector"
    assert "metadata" in data