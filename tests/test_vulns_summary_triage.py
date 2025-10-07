#!/usr/bin/env python3
"""
P5 - Vulns Summary Triage Tests

Test the vulns summary computation with triage and suppression handling.
"""

import unittest
import json
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from routes.vulns import _compute_vulns_summary


class TestVulnsSummaryTriage(unittest.TestCase):
    """Test vulns summary computation with triage."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.pid = "test_project"
        
        # Ensure ui_projects directory exists
        os.makedirs("ui_projects", exist_ok=True)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
        if os.path.exists("ui_projects"):
            shutil.rmtree("ui_projects")
    
    def create_test_findings(self, findings_data):
        """Create test findings file."""
        findings_file = f"ui_projects/{self.pid}.findings.json"
        with open(findings_file, 'w') as f:
            json.dump(findings_data, f)
        return findings_file
    
    @patch('findings.get_findings')
    def test_vulns_summary_with_triage_status_counts(self, mock_get_findings):
        """Test vulns summary includes triage status counts."""
        # Create test findings with different triage statuses
        test_findings = [
            {
                "detector_id": "test.detector1",
                "title": "Test Finding 1",
                "severity": "high",
                "method": "GET",
                "url": "https://example.com/api/users",
                "path": "/api/users",
                "created_at": "2025-01-15T10:00:00Z",
                "triage": {
                    "status": "open",
                    "tags": [],
                    "notes": []
                }
            },
            {
                "detector_id": "test.detector1",
                "title": "Test Finding 1",
                "severity": "high",
                "method": "GET",
                "url": "https://example.com/api/users",
                "path": "/api/users",
                "created_at": "2025-01-15T11:00:00Z",
                "triage": {
                    "status": "in_progress",
                    "tags": [],
                    "notes": []
                }
            },
            {
                "detector_id": "test.detector1",
                "title": "Test Finding 1",
                "severity": "high",
                "method": "GET",
                "url": "https://example.com/api/users",
                "path": "/api/users",
                "created_at": "2025-01-15T12:00:00Z",
                "triage": {
                    "status": "resolved",
                    "tags": [],
                    "notes": []
                }
            }
        ]
        
        mock_get_findings.return_value = test_findings
        
        # Compute vulns summary
        summary = _compute_vulns_summary(self.pid)
        
        # Verify summary structure
        self.assertEqual(len(summary), 1)
        group = summary[0]
        
        # Verify triage status counts
        self.assertIn('counts_by_status', group)
        counts = group['counts_by_status']
        self.assertEqual(counts['open'], 1)
        self.assertEqual(counts['in_progress'], 1)
        self.assertEqual(counts['resolved'], 1)
        self.assertEqual(counts['risk_accepted'], 0)
        self.assertEqual(counts['false_positive'], 0)
        
        # Verify total occurrences (all findings counted)
        self.assertEqual(group['occurrences'], 3)
    
    @patch('findings.get_findings')
    def test_vulns_summary_with_suppressed_findings(self, mock_get_findings):
        """Test vulns summary excludes suppressed findings from counts."""
        # Create test findings with suppression
        future_time = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        
        test_findings = [
            {
                "detector_id": "test.detector1",
                "title": "Test Finding 1",
                "severity": "high",
                "method": "GET",
                "url": "https://example.com/api/users",
                "path": "/api/users",
                "created_at": "2025-01-15T10:00:00Z",
                "triage": {
                    "status": "open",
                    "tags": [],
                    "notes": [],
                    "suppress": {
                        "reason": "False positive",
                        "until": future_time,
                        "scope": "this"
                    }
                }
            },
            {
                "detector_id": "test.detector1",
                "title": "Test Finding 1",
                "severity": "high",
                "method": "GET",
                "url": "https://example.com/api/users",
                "path": "/api/users",
                "created_at": "2025-01-15T11:00:00Z",
                "triage": {
                    "status": "in_progress",
                    "tags": [],
                    "notes": []
                }
            }
        ]
        
        mock_get_findings.return_value = test_findings
        
        # Compute vulns summary
        summary = _compute_vulns_summary(self.pid)
        
        # Verify summary structure
        self.assertEqual(len(summary), 1)
        group = summary[0]
        
        # Verify suppressed finding is excluded from occurrences
        self.assertEqual(group['occurrences'], 1)  # Only non-suppressed finding
        
        # Verify suppression flag is set
        self.assertTrue(group['has_suppressed'])
        
        # Verify triage status counts (suppressed finding still counted in status)
        counts = group['counts_by_status']
        self.assertEqual(counts['open'], 1)  # Suppressed finding still counted
        self.assertEqual(counts['in_progress'], 1)
    
    @patch('findings.get_findings')
    def test_vulns_summary_with_expired_suppression(self, mock_get_findings):
        """Test vulns summary includes findings with expired suppression."""
        # Create test findings with expired suppression
        past_time = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        
        test_findings = [
            {
                "detector_id": "test.detector1",
                "title": "Test Finding 1",
                "severity": "high",
                "method": "GET",
                "url": "https://example.com/api/users",
                "path": "/api/users",
                "created_at": "2025-01-15T10:00:00Z",
                "triage": {
                    "status": "open",
                    "tags": [],
                    "notes": [],
                    "suppress": {
                        "reason": "Temporary suppression",
                        "until": past_time,
                        "scope": "this"
                    }
                }
            }
        ]
        
        mock_get_findings.return_value = test_findings
        
        # Compute vulns summary
        summary = _compute_vulns_summary(self.pid)
        
        # Verify summary structure
        self.assertEqual(len(summary), 1)
        group = summary[0]
        
        # Verify expired suppression is not active
        self.assertEqual(group['occurrences'], 1)  # Finding is counted
        self.assertFalse(group['has_suppressed'])  # No active suppression
    
    @patch('findings.get_findings')
    def test_vulns_summary_with_permanent_suppression(self, mock_get_findings):
        """Test vulns summary handles permanent suppression (no until date)."""
        test_findings = [
            {
                "detector_id": "test.detector1",
                "title": "Test Finding 1",
                "severity": "high",
                "method": "GET",
                "url": "https://example.com/api/users",
                "path": "/api/users",
                "created_at": "2025-01-15T10:00:00Z",
                "triage": {
                    "status": "false_positive",
                    "tags": [],
                    "notes": [],
                    "suppress": {
                        "reason": "Permanent false positive",
                        "scope": "this"
                        # No 'until' field = permanent suppression
                    }
                }
            }
        ]
        
        mock_get_findings.return_value = test_findings
        
        # Compute vulns summary
        summary = _compute_vulns_summary(self.pid)
        
        # Verify summary structure
        self.assertEqual(len(summary), 1)
        group = summary[0]
        
        # Verify permanent suppression is active
        self.assertEqual(group['occurrences'], 0)  # Finding is not counted
        self.assertTrue(group['has_suppressed'])  # Suppression is active
    
    @patch('findings.get_findings')
    def test_vulns_summary_with_invalid_suppression_timestamp(self, mock_get_findings):
        """Test vulns summary handles invalid suppression timestamps."""
        test_findings = [
            {
                "detector_id": "test.detector1",
                "title": "Test Finding 1",
                "severity": "high",
                "method": "GET",
                "url": "https://example.com/api/users",
                "path": "/api/users",
                "created_at": "2025-01-15T10:00:00Z",
                "triage": {
                    "status": "open",
                    "tags": [],
                    "notes": [],
                    "suppress": {
                        "reason": "Invalid timestamp",
                        "until": "invalid-timestamp",
                        "scope": "this"
                    }
                }
            }
        ]
        
        mock_get_findings.return_value = test_findings
        
        # Compute vulns summary
        summary = _compute_vulns_summary(self.pid)
        
        # Verify summary structure
        self.assertEqual(len(summary), 1)
        group = summary[0]
        
        # Verify invalid timestamp is treated as not suppressed
        self.assertEqual(group['occurrences'], 1)  # Finding is counted
        self.assertFalse(group['has_suppressed'])  # No active suppression
    
    @patch('findings.get_findings')
    def test_vulns_summary_without_triage(self, mock_get_findings):
        """Test vulns summary handles findings without triage fields."""
        test_findings = [
            {
                "detector_id": "test.detector1",
                "title": "Test Finding 1",
                "severity": "high",
                "method": "GET",
                "url": "https://example.com/api/users",
                "path": "/api/users",
                "created_at": "2025-01-15T10:00:00Z"
                # No triage field
            }
        ]
        
        mock_get_findings.return_value = test_findings
        
        # Compute vulns summary
        summary = _compute_vulns_summary(self.pid)
        
        # Verify summary structure
        self.assertEqual(len(summary), 1)
        group = summary[0]
        
        # Verify default triage status counts
        counts = group['counts_by_status']
        self.assertEqual(counts['open'], 1)  # Default status
        self.assertEqual(counts['in_progress'], 0)
        self.assertEqual(counts['resolved'], 0)
        
        # Verify no suppression
        self.assertFalse(group['has_suppressed'])
        self.assertEqual(group['occurrences'], 1)
    
    @patch('findings.get_findings')
    def test_vulns_summary_multiple_groups(self, mock_get_findings):
        """Test vulns summary with multiple vulnerability groups."""
        test_findings = [
            {
                "detector_id": "test.detector1",
                "title": "Test Finding 1",
                "severity": "high",
                "method": "GET",
                "url": "https://example.com/api/users",
                "path": "/api/users",
                "created_at": "2025-01-15T10:00:00Z",
                "triage": {"status": "open", "tags": [], "notes": []}
            },
            {
                "detector_id": "test.detector2",
                "title": "Test Finding 2",
                "severity": "medium",
                "method": "POST",
                "url": "https://example.com/api/login",
                "path": "/api/login",
                "created_at": "2025-01-15T11:00:00Z",
                "triage": {"status": "in_progress", "tags": [], "notes": []}
            }
        ]
        
        mock_get_findings.return_value = test_findings
        
        # Compute vulns summary
        summary = _compute_vulns_summary(self.pid)
        
        # Verify two groups
        self.assertEqual(len(summary), 2)
        
        # Verify each group has correct counts
        group1 = next(g for g in summary if g['detector_id'] == 'test.detector1')
        group2 = next(g for g in summary if g['detector_id'] == 'test.detector2')
        
        self.assertEqual(group1['counts_by_status']['open'], 1)
        self.assertEqual(group2['counts_by_status']['in_progress'], 1)


if __name__ == '__main__':
    unittest.main()
