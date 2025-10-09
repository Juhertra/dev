#!/usr/bin/env python3
"""
P4 - Unit Tests for Findings Normalization

Tests the main transforms in utils.findings_normalize.normalize_finding()
to prevent regressions in the findings contract.
"""

import sys
import time
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.findings_normalize import normalize_finding


class TestFindingsNormalize(unittest.TestCase):
    """Test cases for findings normalization."""

    def setUp(self):
        """Set up test fixtures."""
        self.pid = "test_project"
        self.run_id = "test_run_123"
        self.method = "GET"
        self.url = "https://example.com/api/users?limit=10"
        self.status_code = 200

    def test_detector_id_colon_to_underscore_pattern(self):
        """Test colon→underscore transformation for pattern engine detector_id."""
        raw = {
            "detector_id": "pattern:server_tech_disclosure",
            "title": "Test Pattern Finding",
            "severity": "info"
        }
        
        normalized = normalize_finding(
            raw, pid=self.pid, run_id=self.run_id, 
            method=self.method, url=self.url, status_code=self.status_code
        )
        
        self.assertEqual(normalized["detector_id"], "pattern_server_tech_disclosure")
        self.assertNotIn(":", normalized["detector_id"])

    def test_detector_id_colon_to_dot_nuclei(self):
        """Test colon→dot transformation for nuclei detector_id."""
        raw = {
            "detector_id": "nuclei:http-missing-security-headers",
            "title": "Test Nuclei Finding",
            "severity": "info"
        }
        
        normalized = normalize_finding(
            raw, pid=self.pid, run_id=self.run_id,
            method=self.method, url=self.url, status_code=self.status_code
        )
        
        self.assertEqual(normalized["detector_id"], "nuclei.http-missing-security-headers")
        self.assertNotIn(":", normalized["detector_id"])

    def test_numeric_cwe_formatting(self):
        """Test numeric CWE→CWE-### formatting."""
        raw = {
            "detector_id": "test_detector",
            "title": "Test Finding",
            "severity": "medium",
            "cwe": 123  # Numeric CWE
        }
        
        normalized = normalize_finding(
            raw, pid=self.pid, run_id=self.run_id,
            method=self.method, url=self.url, status_code=self.status_code
        )
        
        self.assertEqual(normalized["cwe"], "CWE-123")

    def test_cwe_string_formatting(self):
        """Test CWE string formatting."""
        raw = {
            "detector_id": "test_detector",
            "title": "Test Finding",
            "severity": "medium",
            "cwe": "CWE-456"  # Already formatted
        }
        
        normalized = normalize_finding(
            raw, pid=self.pid, run_id=self.run_id,
            method=self.method, url=self.url, status_code=self.status_code
        )
        
        self.assertEqual(normalized["cwe"], "CWE-456")

    def test_owasp_text_cleanup(self):
        """Test OWASP text cleanup to A##:#### format."""
        raw = {
            "detector_id": "test_detector",
            "title": "Test Finding",
            "severity": "high",
            "owasp": "A05:2021-Security Misconfiguration"  # With extra text
        }
        
        normalized = normalize_finding(
            raw, pid=self.pid, run_id=self.run_id,
            method=self.method, url=self.url, status_code=self.status_code
        )
        
        self.assertEqual(normalized["owasp"], "A05:2021")

    def test_owasp_invalid_format_dropped(self):
        """Test invalid OWASP format is dropped."""
        raw = {
            "detector_id": "test_detector",
            "title": "Test Finding",
            "severity": "high",
            "owasp": "Invalid OWASP Format"  # Invalid format
        }
        
        normalized = normalize_finding(
            raw, pid=self.pid, run_id=self.run_id,
            method=self.method, url=self.url, status_code=self.status_code
        )
        
        self.assertNotIn("owasp", normalized)

    def test_path_extraction_from_url(self):
        """Test path extraction from full URL."""
        raw = {
            "detector_id": "test_detector",
            "title": "Test Finding",
            "severity": "info",
            "url": "https://example.com/api/users?limit=10"
        }
        
        normalized = normalize_finding(
            raw, pid=self.pid, run_id=self.run_id,
            method=self.method, url=self.url, status_code=self.status_code
        )
        
        self.assertEqual(normalized["path"], "/api/users")
        # target_url is not added by normalize_finding, it uses the url parameter

    def test_path_extraction_root_path(self):
        """Test path extraction for root path."""
        raw = {
            "detector_id": "test_detector",
            "title": "Test Finding",
            "severity": "info",
            "url": "https://example.com/"
        }
        
        normalized = normalize_finding(
            raw, pid=self.pid, run_id=self.run_id,
            method="GET", url="https://example.com/", status_code=self.status_code
        )
        
        self.assertEqual(normalized["path"], "/")

    def test_integer_confidence_coercion(self):
        """Test integer confidence coercion."""
        raw = {
            "detector_id": "test_detector",
            "title": "Test Finding",
            "severity": "medium",
            "confidence": "85"  # String confidence
        }
        
        normalized = normalize_finding(
            raw, pid=self.pid, run_id=self.run_id,
            method=self.method, url=self.url, status_code=self.status_code
        )
        
        self.assertEqual(normalized["confidence"], 85)
        self.assertIsInstance(normalized["confidence"], int)

    def test_created_at_int_to_iso_z(self):
        """Test created_at int→ISO Z conversion."""
        current_time = int(time.time())
        raw = {
            "detector_id": "test_detector",
            "title": "Test Finding",
            "severity": "info",
            "created_at": current_time  # Integer timestamp
        }
        
        normalized = normalize_finding(
            raw, pid=self.pid, run_id=self.run_id,
            method=self.method, url=self.url, status_code=self.status_code
        )
        
        self.assertTrue(normalized["created_at"].endswith("Z"))
        self.assertRegex(normalized["created_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_created_at_string_preserved(self):
        """Test created_at string is preserved if already ISO format."""
        iso_time = "2025-10-05T19:30:00Z"
        raw = {
            "detector_id": "test_detector",
            "title": "Test Finding",
            "severity": "info",
            "created_at": iso_time
        }
        
        normalized = normalize_finding(
            raw, pid=self.pid, run_id=self.run_id,
            method=self.method, url=self.url, status_code=self.status_code
        )
        
        self.assertEqual(normalized["created_at"], iso_time)

    def test_required_fields_present(self):
        """Test all required fields are present."""
        raw = {
            "detector_id": "test_detector",
            "title": "Test Finding",
            "severity": "medium"
        }
        
        normalized = normalize_finding(
            raw, pid=self.pid, run_id=self.run_id,
            method=self.method, url=self.url, status_code=self.status_code
        )
        
        # Check required fields
        required_fields = ["detector_id", "path", "method", "url", "status", "created_at", "req", "res"]
        for field in required_fields:
            self.assertIn(field, normalized, f"Required field '{field}' missing")

    def test_req_res_envelopes(self):
        """Test req/res objects are properly created."""
        raw = {
            "detector_id": "test_detector",
            "title": "Test Finding",
            "severity": "info"
        }
        
        normalized = normalize_finding(
            raw, pid=self.pid, run_id=self.run_id,
            method=self.method, url=self.url, status_code=self.status_code
        )
        
        # Check req object
        self.assertIsInstance(normalized["req"], dict)
        self.assertIn("headers", normalized["req"])
        self.assertIn("body", normalized["req"])
        self.assertIn("method", normalized["req"])
        self.assertIn("url", normalized["req"])
        
        # Check res object
        self.assertIsInstance(normalized["res"], dict)
        self.assertIn("headers", normalized["res"])
        self.assertIn("body", normalized["res"])
        self.assertIn("status_code", normalized["res"])

    def test_status_default_open(self):
        """Test status defaults to 'open'."""
        raw = {
            "detector_id": "test_detector",
            "title": "Test Finding",
            "severity": "info"
        }
        
        normalized = normalize_finding(
            raw, pid=self.pid, run_id=self.run_id,
            method=self.method, url=self.url, status_code=self.status_code
        )
        
        self.assertEqual(normalized["status"], "open")

    def test_status_int_converted_to_open(self):
        """Test integer status is converted to 'open'."""
        raw = {
            "detector_id": "test_detector",
            "title": "Test Finding",
            "severity": "info",
            "status": 1  # Integer status
        }
        
        normalized = normalize_finding(
            raw, pid=self.pid, run_id=self.run_id,
            method=self.method, url=self.url, status_code=self.status_code
        )
        
        self.assertEqual(normalized["status"], "open")

    def test_cve_id_validation(self):
        """Test CVE ID validation."""
        raw = {
            "detector_id": "test_detector",
            "title": "Test Finding",
            "severity": "high",
            "cve_id": "CVE-2023-1234"  # Valid CVE
        }
        
        normalized = normalize_finding(
            raw, pid=self.pid, run_id=self.run_id,
            method=self.method, url=self.url, status_code=self.status_code
        )
        
        self.assertEqual(normalized["cve_id"], "CVE-2023-1234")

    def test_cve_id_placeholder_rejected(self):
        """Test CVE placeholder is rejected."""
        raw = {
            "detector_id": "test_detector",
            "title": "Test Finding",
            "severity": "high",
            "cve_id": "CVE-0000-0000"  # Placeholder CVE
        }
        
        normalized = normalize_finding(
            raw, pid=self.pid, run_id=self.run_id,
            method=self.method, url=self.url, status_code=self.status_code
        )
        
        self.assertNotIn("cve_id", normalized)

    def test_subcategory_mapping(self):
        """Test subcategory mapping to valid enum values."""
        raw = {
            "detector_id": "test_detector",
            "title": "Test Finding",
            "severity": "info",
            "subcategory": "Server header disclosed"  # Invalid subcategory
        }
        
        normalized = normalize_finding(
            raw, pid=self.pid, run_id=self.run_id,
            method=self.method, url=self.url, status_code=self.status_code
        )
        
        self.assertEqual(normalized["subcategory"], "misconfig")

    def test_subcategory_valid_preserved(self):
        """Test valid subcategory is preserved."""
        raw = {
            "detector_id": "test_detector",
            "title": "Test Finding",
            "severity": "high",
            "subcategory": "sqli"  # Valid subcategory
        }
        
        normalized = normalize_finding(
            raw, pid=self.pid, run_id=self.run_id,
            method=self.method, url=self.url, status_code=self.status_code
        )
        
        self.assertEqual(normalized["subcategory"], "sqli")


if __name__ == "__main__":
    unittest.main()
