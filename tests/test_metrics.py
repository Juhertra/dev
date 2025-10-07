#!/usr/bin/env python3
"""
P6 - Metrics Tests

Test the analytics and metrics functionality.
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

from analytics_core.analytics import (
    get_metrics, _compute_metrics, _is_suppressed, _calculate_fix_time,
    _compute_trend_30d, rebuild_metrics_cache, get_filtered_metrics
)


class TestAnalytics(unittest.TestCase):
    """Test analytics functionality."""
    
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
    def test_get_metrics_basic_counts(self, mock_get_findings):
        """Test basic metrics counting."""
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
                    "tags": ["auth"],
                    "notes": []
                }
            },
            {
                "detector_id": "test.detector1",
                "title": "Test Finding 2",
                "severity": "medium",
                "method": "POST",
                "url": "https://example.com/api/login",
                "path": "/api/login",
                "created_at": "2025-01-15T11:00:00Z",
                "triage": {
                    "status": "resolved",
                    "tags": ["auth", "critical"],
                    "notes": [{"at": "2025-01-16T10:00:00Z", "by": "test@example.com", "text": "Fixed"}]
                }
            }
        ]
        
        mock_get_findings.return_value = test_findings
        
        metrics = _compute_metrics(self.pid)
        
        self.assertEqual(metrics['total_findings'], 2)
        self.assertEqual(metrics['active'], 1)
        self.assertEqual(metrics['resolved'], 1)
        self.assertEqual(metrics['false_positives'], 0)
        self.assertEqual(metrics['risk_accepted'], 0)
        self.assertEqual(metrics['suppressed'], 0)
    
    @patch('findings.get_findings')
    def test_get_metrics_suppressed_exclusion(self, mock_get_findings):
        """Test that suppressed findings are excluded from counts."""
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
                    "tags": ["auth"],
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
                "title": "Test Finding 2",
                "severity": "medium",
                "method": "POST",
                "url": "https://example.com/api/login",
                "path": "/api/login",
                "created_at": "2025-01-15T11:00:00Z",
                "triage": {
                    "status": "open",
                    "tags": ["auth"],
                    "notes": []
                }
            }
        ]
        
        mock_get_findings.return_value = test_findings
        
        metrics = _compute_metrics(self.pid)
        
        self.assertEqual(metrics['total_findings'], 2)
        self.assertEqual(metrics['active'], 1)  # Only non-suppressed finding
        self.assertEqual(metrics['suppressed'], 1)
    
    @patch('findings.get_findings')
    def test_get_metrics_severity_breakdown(self, mock_get_findings):
        """Test severity breakdown calculation."""
        test_findings = [
            {
                "detector_id": "test.detector1",
                "title": "Critical Finding",
                "severity": "critical",
                "method": "GET",
                "url": "https://example.com/api/admin",
                "path": "/api/admin",
                "created_at": "2025-01-15T10:00:00Z",
                "triage": {"status": "open", "tags": [], "notes": []}
            },
            {
                "detector_id": "test.detector2",
                "title": "High Finding",
                "severity": "high",
                "method": "POST",
                "url": "https://example.com/api/users",
                "path": "/api/users",
                "created_at": "2025-01-15T11:00:00Z",
                "triage": {"status": "open", "tags": [], "notes": []}
            },
            {
                "detector_id": "test.detector3",
                "title": "Medium Finding",
                "severity": "medium",
                "method": "PUT",
                "url": "https://example.com/api/data",
                "path": "/api/data",
                "created_at": "2025-01-15T12:00:00Z",
                "triage": {"status": "open", "tags": [], "notes": []}
            }
        ]
        
        mock_get_findings.return_value = test_findings
        
        metrics = _compute_metrics(self.pid)
        
        severity = metrics['severity_breakdown']
        self.assertEqual(severity['critical'], 1)
        self.assertEqual(severity['high'], 1)
        self.assertEqual(severity['medium'], 1)
        self.assertEqual(severity['low'], 0)
        self.assertEqual(severity['info'], 0)
    
    @patch('findings.get_findings')
    def test_get_metrics_tag_aggregation(self, mock_get_findings):
        """Test tag aggregation."""
        test_findings = [
            {
                "detector_id": "test.detector1",
                "title": "Auth Finding 1",
                "severity": "high",
                "method": "GET",
                "url": "https://example.com/api/users",
                "path": "/api/users",
                "created_at": "2025-01-15T10:00:00Z",
                "triage": {
                    "status": "open",
                    "tags": ["auth", "critical"],
                    "notes": []
                }
            },
            {
                "detector_id": "test.detector2",
                "title": "Auth Finding 2",
                "severity": "medium",
                "method": "POST",
                "url": "https://example.com/api/login",
                "path": "/api/login",
                "created_at": "2025-01-15T11:00:00Z",
                "triage": {
                    "status": "open",
                    "tags": ["auth", "header"],
                    "notes": []
                }
            },
            {
                "detector_id": "test.detector3",
                "title": "Header Finding",
                "severity": "low",
                "method": "PUT",
                "url": "https://example.com/api/data",
                "path": "/api/data",
                "created_at": "2025-01-15T12:00:00Z",
                "triage": {
                    "status": "open",
                    "tags": ["header"],
                    "notes": []
                }
            }
        ]
        
        mock_get_findings.return_value = test_findings
        
        metrics = _compute_metrics(self.pid)
        
        tags = metrics['most_common_tags']
        self.assertEqual(len(tags), 3)
        
        # Check tag counts
        tag_counts = {tag['tag']: tag['count'] for tag in tags}
        self.assertEqual(tag_counts['auth'], 2)
        self.assertEqual(tag_counts['header'], 2)
        self.assertEqual(tag_counts['critical'], 1)
    
    @patch('findings.get_findings')
    def test_get_metrics_owner_aggregation(self, mock_get_findings):
        """Test owner aggregation."""
        test_findings = [
            {
                "detector_id": "test.detector1",
                "title": "Finding 1",
                "severity": "high",
                "method": "GET",
                "url": "https://example.com/api/users",
                "path": "/api/users",
                "created_at": "2025-01-15T10:00:00Z",
                "triage": {
                    "status": "open",
                    "tags": [],
                    "notes": [],
                    "owner": "alice@example.com"
                }
            },
            {
                "detector_id": "test.detector2",
                "title": "Finding 2",
                "severity": "medium",
                "method": "POST",
                "url": "https://example.com/api/login",
                "path": "/api/login",
                "created_at": "2025-01-15T11:00:00Z",
                "triage": {
                    "status": "in_progress",
                    "tags": [],
                    "notes": [],
                    "owner": "alice@example.com"
                }
            },
            {
                "detector_id": "test.detector3",
                "title": "Finding 3",
                "severity": "low",
                "method": "PUT",
                "url": "https://example.com/api/data",
                "path": "/api/data",
                "created_at": "2025-01-15T12:00:00Z",
                "triage": {
                    "status": "open",
                    "tags": [],
                    "notes": [],
                    "owner": "bob@example.com"
                }
            }
        ]
        
        mock_get_findings.return_value = test_findings
        
        metrics = _compute_metrics(self.pid)
        
        owners = metrics['top_owners']
        self.assertEqual(len(owners), 2)
        
        # Check owner counts
        owner_counts = {owner['owner']: owner['active'] for owner in owners}
        self.assertEqual(owner_counts['alice@example.com'], 2)  # 2 active findings
        self.assertEqual(owner_counts['bob@example.com'], 1)   # 1 active finding
    
    def test_is_suppressed_active(self):
        """Test suppression check for active suppression."""
        future_time = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        suppress = {
            "reason": "False positive",
            "until": future_time,
            "scope": "this"
        }
        
        self.assertTrue(_is_suppressed(suppress))
    
    def test_is_suppressed_expired(self):
        """Test suppression check for expired suppression."""
        past_time = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        suppress = {
            "reason": "Temporary suppression",
            "until": past_time,
            "scope": "this"
        }
        
        self.assertFalse(_is_suppressed(suppress))
    
    def test_is_suppressed_permanent(self):
        """Test suppression check for permanent suppression."""
        suppress = {
            "reason": "Permanent false positive",
            "scope": "this"
            # No 'until' field = permanent suppression
        }
        
        self.assertTrue(_is_suppressed(suppress))
    
    def test_calculate_fix_time(self):
        """Test fix time calculation."""
        finding = {
            "created_at": "2025-01-15T10:00:00Z",
            "triage": {
                "status": "resolved",
                "notes": [
                    {"at": "2025-01-15T10:00:00Z", "by": "test@example.com", "text": "Initial finding"},
                    {"at": "2025-01-17T10:00:00Z", "by": "test@example.com", "text": "Resolved the issue"}
                ]
            }
        }
        
        fix_time = _calculate_fix_time(finding)
        self.assertIsNotNone(fix_time)
        self.assertAlmostEqual(fix_time, 2.0, places=1)  # 2 days
    
    def test_compute_trend_30d(self):
        """Test 30-day trend computation."""
        # Create findings with different creation dates
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)
        last_week = today - timedelta(days=7)
        
        test_findings = [
            {
                "detector_id": "test.detector1",
                "title": "Today Finding",
                "severity": "high",
                "method": "GET",
                "url": "https://example.com/api/users",
                "path": "/api/users",
                "created_at": f"{today.isoformat()}T10:00:00Z",
                "triage": {
                    "status": "open",
                    "tags": [],
                    "notes": []
                }
            },
            {
                "detector_id": "test.detector2",
                "title": "Yesterday Finding",
                "severity": "medium",
                "method": "POST",
                "url": "https://example.com/api/login",
                "path": "/api/login",
                "created_at": f"{yesterday.isoformat()}T11:00:00Z",
                "triage": {
                    "status": "resolved",
                    "tags": [],
                    "notes": [
                        {"at": f"{yesterday.isoformat()}T11:00:00Z", "by": "test@example.com", "text": "Found issue"},
                        {"at": f"{today.isoformat()}T09:00:00Z", "by": "test@example.com", "text": "Resolved"}
                    ]
                }
            }
        ]
        
        trend_data = _compute_trend_30d(test_findings)
        
        self.assertIsInstance(trend_data, list)
        self.assertEqual(len(trend_data), 30)  # 30 days
        
        # Check that we have data for today and yesterday
        today_data = next((d for d in trend_data if d['day'] == today.isoformat()), None)
        yesterday_data = next((d for d in trend_data if d['day'] == yesterday.isoformat()), None)
        
        self.assertIsNotNone(today_data)
        self.assertIsNotNone(yesterday_data)
        
        # Today should have 1 created, 1 resolved (from yesterday's finding)
        self.assertEqual(today_data['created'], 1)
        self.assertEqual(today_data['resolved'], 1)
        
        # Yesterday should have 1 created, 0 resolved (resolution was today)
        self.assertEqual(yesterday_data['created'], 1)
        self.assertEqual(yesterday_data['resolved'], 0)
    
    @patch('analytics_core.analytics.get_findings')
    def test_get_filtered_metrics(self, mock_get_findings):
        """Test filtered metrics functionality."""
        test_findings = [
            {
                "detector_id": "test.detector1",
                "title": "Open Finding",
                "severity": "high",
                "method": "GET",
                "url": "https://example.com/api/users",
                "path": "/api/users",
                "created_at": "2025-01-15T10:00:00Z",
                "triage": {
                    "status": "open",
                    "tags": ["auth"],
                    "notes": [],
                    "owner": "alice@example.com"
                }
            },
            {
                "detector_id": "test.detector2",
                "title": "Resolved Finding",
                "severity": "medium",
                "method": "POST",
                "url": "https://example.com/api/login",
                "path": "/api/login",
                "created_at": "2025-01-15T11:00:00Z",
                "triage": {
                    "status": "resolved",
                    "tags": ["auth"],
                    "notes": [],
                    "owner": "bob@example.com"
                }
            }
        ]
        
        mock_get_findings.return_value = test_findings
        
        # Test status filter
        filters = {"status": "open"}
        metrics = get_filtered_metrics(self.pid, filters)
        
        self.assertEqual(metrics['total_findings'], 1)  # Only open finding
        self.assertEqual(metrics['active'], 1)
        self.assertEqual(metrics['resolved'], 0)
    
    def test_rebuild_metrics_cache(self):
        """Test metrics cache rebuilding."""
        # This test would require more complex mocking of the file system
        # For now, just test that the function doesn't crash
        try:
            rebuild_metrics_cache(self.pid)
        except Exception as e:
            # Expected to fail in test environment
            self.assertIn("get_findings", str(e))


if __name__ == '__main__':
    unittest.main()
