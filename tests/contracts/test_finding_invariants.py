import re

import pytest

DETECTOR_RE = re.compile(r"^[A-Za-z0-9_.-]+$")

def test_detector_id_regex_valid(sample_finding_json={"detector_id": "EXAMPLE_1", "timestamp": "2024-01-02T03:04:05Z"}):
    """Test that valid detector IDs match the expected regex pattern."""
    assert DETECTOR_RE.match(sample_finding_json["detector_id"])
    assert sample_finding_json["timestamp"].endswith("Z")

def test_detector_id_regex_invalid():
    """Test that invalid detector IDs are rejected."""
    invalid_findings = [
        {"detector_id": "invalid:id", "timestamp": "2024-01-02T03:04:05Z"},  # colon not allowed
        {"detector_id": "invalid@id", "timestamp": "2024-01-02T03:04:05Z"},  # @ not allowed
        {"detector_id": "invalid id", "timestamp": "2024-01-02T03:04:05Z"},  # space not allowed
        {"detector_id": "", "timestamp": "2024-01-02T03:04:05Z"},  # empty not allowed
    ]
    
    for finding in invalid_findings:
        assert not DETECTOR_RE.match(finding["detector_id"]), f"Should reject detector_id: {finding['detector_id']}"

def test_timestamp_format_valid():
    """Test that valid UTC timestamps are accepted."""
    valid_timestamps = [
        "2024-01-02T03:04:05Z",
        "2024-12-31T23:59:59Z",
        "2023-06-15T12:30:45Z"
    ]
    
    for timestamp in valid_timestamps:
        assert timestamp.endswith("Z"), f"Should accept timestamp: {timestamp}"

def test_timestamp_format_invalid():
    """Test that invalid timestamp formats are rejected."""
    import re
    
    # Define a proper ISO 8601 UTC timestamp pattern
    iso8601_utc_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
    
    invalid_timestamps = [
        "2024-01-02T03:04:05",  # missing Z
        "2024/01/02T03:04:05Z",  # wrong date separator
        "2024-01-02 03:04:05Z",  # space instead of T
        "not-a-timestamp",  # completely invalid
        "2024-01-02T03:04:05+00:00",  # timezone format instead of Z
        "2024-01-02T03:04:05.123Z",  # milliseconds not allowed in basic format
    ]
    
    for timestamp in invalid_timestamps:
        assert not iso8601_utc_pattern.match(timestamp), f"Should reject timestamp: {timestamp}"

@pytest.mark.xfail(reason="Implementation pending - finding validation not yet implemented")
def test_finding_schema_validation():
    """Test that findings conform to expected schema structure."""
    # This test will fail until schema validation is implemented
    sample_finding = {
        "detector_id": "test.detector",
        "title": "Test Finding",
        "severity": "medium",
        "timestamp": "2024-01-02T03:04:05Z",
        "method": "GET",
        "url": "https://example.com/test",
        "path": "/test"
    }
    
    # This should validate against a schema when implemented
    assert "detector_id" in sample_finding
    assert "timestamp" in sample_finding
    assert sample_finding["timestamp"].endswith("Z")
    assert DETECTOR_RE.match(sample_finding["detector_id"])