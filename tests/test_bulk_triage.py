#!/usr/bin/env python3
"""
Tests for bulk triage operations in Vulnerabilities Hub.

Tests cover:
- Bulk status changes
- Owner assignment
- Tag add/remove operations
- Suppression/unsuppression
- Edge cases and error handling
- Performance with large selections
"""

import json
import os

# Add the project root to the path
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes.vulns import _apply_bulk_actions


class TestBulkTriageOperations(unittest.TestCase):
    """Test suite for bulk triage functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_pid = "test_project"
        self.temp_dir = tempfile.mkdtemp()
        self.findings_file = os.path.join(self.temp_dir, f"{self.test_pid}.findings.json")
        
        # Create sample findings data
        self.sample_findings = [
            {
                "detector_id": "test.detector.1",
                "severity": "high",
                "method": "GET",
                "url": "https://example.com/test1",
                "path": "/test1",
                "title": "Test Vulnerability 1",
                "confidence": 80,
                "status": "open",
                "req": {"method": "GET", "url": "https://example.com/test1"},
                "res": {"status_code": 200},
                "created_at": "2024-01-01T00:00:00Z",
                "triage": {
                    "status": "open",
                    "tags": ["test"],
                    "notes": []
                }
            },
            {
                "detector_id": "test.detector.2", 
                "severity": "medium",
                "method": "POST",
                "url": "https://example.com/test2",
                "path": "/test2",
                "title": "Test Vulnerability 2",
                "confidence": 70,
                "status": "open",
                "req": {"method": "POST", "url": "https://example.com/test2"},
                "res": {"status_code": 200},
                "created_at": "2024-01-01T00:00:00Z",
                "triage": {
                    "status": "open",
                    "tags": [],
                    "notes": []
                }
            },
            {
                "detector_id": "test.detector.3",
                "severity": "low",
                "method": "GET", 
                "url": "https://example.com/test3",
                "path": "/test3",
                "title": "Test Vulnerability 3",
                "confidence": 60,
                "status": "open",
                "req": {"method": "GET", "url": "https://example.com/test3"},
                "res": {"status_code": 200},
                "created_at": "2024-01-01T00:00:00Z"
                # No triage section - should be initialized
            }
        ]
        
        # Write sample findings to file
        with open(self.findings_file, 'w') as f:
            json.dump(self.sample_findings, f, indent=2)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.findings_file):
            os.remove(self.findings_file)
        os.rmdir(self.temp_dir)
    
    @patch('findings.get_findings')
    @patch('store._bust_vulns_cache')
    def test_bulk_status_change(self, mock_bust_cache, mock_get_findings):
        """Test bulk status changes."""
        mock_get_findings.return_value = self.sample_findings.copy()
        
        # Test setting status to 'in_progress' for indices 0 and 1
        indices = [0, 1]
        actions = [{"action": "set_status", "value": "in_progress"}]
        
        result = _apply_bulk_actions(self.test_pid, indices, actions)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 2)
        
        # Verify findings were updated
        updated_findings = mock_get_findings.return_value
        self.assertEqual(updated_findings[0]['triage']['status'], 'in_progress')
        self.assertEqual(updated_findings[1]['triage']['status'], 'in_progress')
        # Finding 2 doesn't have triage initially, so it should remain unchanged
        self.assertNotIn('triage', updated_findings[2])
    
    @patch('findings.get_findings')
    @patch('store._bust_vulns_cache')
    def test_bulk_owner_assignment(self, mock_bust_cache, mock_get_findings):
        """Test bulk owner assignment."""
        mock_get_findings.return_value = self.sample_findings.copy()
        
        indices = [0, 2]
        actions = [{"action": "set_owner", "value": "security@example.com"}]
        
        result = _apply_bulk_actions(self.test_pid, indices, actions)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 2)
        
        # Verify findings were updated
        updated_findings = mock_get_findings.return_value
        self.assertEqual(updated_findings[0]['triage']['owner'], 'security@example.com')
        self.assertEqual(updated_findings[2]['triage']['owner'], 'security@example.com')
        self.assertNotIn('owner', updated_findings[1]['triage'])  # Unchanged
    
    @patch('findings.get_findings')
    @patch('store._bust_vulns_cache')
    def test_bulk_tag_operations(self, mock_bust_cache, mock_get_findings):
        """Test bulk tag add/remove operations."""
        mock_get_findings.return_value = self.sample_findings.copy()
        
        # Test adding tags
        indices = [0, 1, 2]
        actions = [
            {"action": "add_tag", "value": "critical"},
            {"action": "add_tag", "value": "auth"}
        ]
        
        result = _apply_bulk_actions(self.test_pid, indices, actions)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 3)
        
        # Verify findings were updated
        updated_findings = mock_get_findings.return_value
        self.assertIn('critical', updated_findings[0]['triage']['tags'])
        self.assertIn('auth', updated_findings[0]['triage']['tags'])
        self.assertIn('test', updated_findings[0]['triage']['tags'])  # Original tag preserved
        
        # Test removing tags
        actions = [{"action": "remove_tag", "value": "test"}]
        
        result = _apply_bulk_actions(self.test_pid, [0], actions)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 1)
        
        # Verify tag was removed
        updated_findings = mock_get_findings.return_value
        self.assertNotIn('test', updated_findings[0]['triage']['tags'])
        self.assertIn('critical', updated_findings[0]['triage']['tags'])
    
    @patch('findings.get_findings')
    @patch('store._bust_vulns_cache')
    def test_bulk_suppression(self, mock_bust_cache, mock_get_findings):
        """Test bulk suppression operations."""
        mock_get_findings.return_value = self.sample_findings.copy()
        
        # Test temporary suppression
        until_time = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        indices = [0, 1]
        actions = [{
            "action": "suppress",
            "value": {
                "reason": "False positive in test environment",
                "until": until_time,
                "scope": "this"
            }
        }]
        
        result = _apply_bulk_actions(self.test_pid, indices, actions)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 2)
        
        # Verify findings were updated
        updated_findings = mock_get_findings.return_value
        self.assertEqual(updated_findings[0]['triage']['suppress']['reason'], 
                        "False positive in test environment")
        self.assertEqual(updated_findings[0]['triage']['suppress']['until'], until_time)
        self.assertEqual(updated_findings[0]['triage']['suppress']['scope'], 'this')
        
        # Test permanent suppression
        actions = [{
            "action": "suppress",
            "value": {
                "reason": "Permanent false positive",
                "scope": "detector"
            }
        }]
        
        result = _apply_bulk_actions(self.test_pid, [2], actions)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 1)
        
        # Verify permanent suppression (no until field)
        updated_findings = mock_get_findings.return_value
        self.assertEqual(updated_findings[2]['triage']['suppress']['reason'], 
                        "Permanent false positive")
        self.assertNotIn('until', updated_findings[2]['triage']['suppress'])
    
    @patch('findings.get_findings')
    @patch('store._bust_vulns_cache')
    def test_multiple_actions(self, mock_bust_cache, mock_get_findings):
        """Test applying multiple actions in one bulk operation."""
        mock_get_findings.return_value = self.sample_findings.copy()
        
        indices = [0, 1]
        actions = [
            {"action": "set_status", "value": "in_progress"},
            {"action": "set_owner", "value": "dev@example.com"},
            {"action": "add_tag", "value": "urgent"}
        ]
        
        result = _apply_bulk_actions(self.test_pid, indices, actions)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 2)
        
        # Verify all actions were applied
        updated_findings = mock_get_findings.return_value
        for idx in indices:
            self.assertEqual(updated_findings[idx]['triage']['status'], 'in_progress')
            self.assertEqual(updated_findings[idx]['triage']['owner'], 'dev@example.com')
            self.assertIn('urgent', updated_findings[idx]['triage']['tags'])
    
    @patch('findings.get_findings')
    def test_invalid_indices(self, mock_get_findings):
        """Test handling of invalid indices."""
        mock_get_findings.return_value = self.sample_findings.copy()
        
        # Test negative indices
        indices = [-1, 0]
        actions = [{"action": "set_status", "value": "open"}]
        
        result = _apply_bulk_actions(self.test_pid, indices, actions)
        
        self.assertFalse(result['success'])
        self.assertIn('Invalid indices', result['error'])
        
        # Test out-of-range indices
        indices = [0, 999]
        actions = [{"action": "set_status", "value": "open"}]
        
        result = _apply_bulk_actions(self.test_pid, indices, actions)
        
        self.assertFalse(result['success'])
        self.assertIn('Invalid indices', result['error'])
    
    @patch('findings.get_findings')
    def test_empty_findings(self, mock_get_findings):
        """Test handling of empty findings list."""
        mock_get_findings.return_value = []
        
        indices = [0]
        actions = [{"action": "set_status", "value": "open"}]
        
        result = _apply_bulk_actions(self.test_pid, indices, actions)
        
        self.assertFalse(result['success'])
        self.assertIn('No findings found', result['error'])
    
    @patch('findings.get_findings')
    @patch('store._bust_vulns_cache')
    def test_triage_initialization(self, mock_bust_cache, mock_get_findings):
        """Test that triage section is initialized for findings without it."""
        mock_get_findings.return_value = self.sample_findings.copy()
        
        # Finding at index 2 has no triage section
        indices = [2]
        actions = [{"action": "set_status", "value": "resolved"}]
        
        result = _apply_bulk_actions(self.test_pid, indices, actions)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 1)
        
        # Verify triage was initialized
        updated_findings = mock_get_findings.return_value
        self.assertIn('triage', updated_findings[2])
        self.assertEqual(updated_findings[2]['triage']['status'], 'resolved')
        self.assertEqual(updated_findings[2]['triage']['tags'], [])
        self.assertEqual(updated_findings[2]['triage']['notes'], [])
    
    @patch('findings.get_findings')
    @patch('store._bust_vulns_cache')
    def test_large_batch_performance(self, mock_bust_cache, mock_get_findings):
        """Test performance with large selections (batching)."""
        # Create a large number of findings
        large_findings = []
        for i in range(1000):
            finding = {
                "detector_id": f"test.detector.{i}",
                "severity": "medium",
                "method": "GET",
                "url": f"https://example.com/test{i}",
                "path": f"/test{i}",
                "title": f"Test Vulnerability {i}",
                "confidence": 70,
                "status": "open",
                "req": {"method": "GET", "url": f"https://example.com/test{i}"},
                "res": {"status_code": 200},
                "created_at": "2024-01-01T00:00:00Z",
                "triage": {"status": "open", "tags": [], "notes": []}
            }
            large_findings.append(finding)
        
        mock_get_findings.return_value = large_findings
        
        # Test with 500 indices (should be processed in 2 batches of 250)
        indices = list(range(500))
        actions = [{"action": "set_status", "value": "in_progress"}]
        
        start_time = time.time()
        result = _apply_bulk_actions(self.test_pid, indices, actions)
        duration = time.time() - start_time
        
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 500)
        
        # Should complete in reasonable time (< 2 seconds as per requirements)
        self.assertLess(duration, 2.0, f"Bulk operation took {duration:.2f}s, expected < 2s")
        
        # Verify all findings were updated
        updated_findings = mock_get_findings.return_value
        for i in range(500):
            self.assertEqual(updated_findings[i]['triage']['status'], 'in_progress')
        
        # Verify unchanged findings
        for i in range(500, 1000):
            self.assertEqual(updated_findings[i]['triage']['status'], 'open')
    
    @patch('findings.get_findings')
    @patch('store._bust_vulns_cache')
    def test_invalid_action_types(self, mock_bust_cache, mock_get_findings):
        """Test handling of invalid action types."""
        mock_get_findings.return_value = self.sample_findings.copy()
        
        indices = [0]
        actions = [
            {"action": "invalid_action", "value": "test"},
            {"action": "set_status", "value": "invalid_status"}
        ]
        
        result = _apply_bulk_actions(self.test_pid, indices, actions)
        
        # Should succeed but skip invalid actions
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 1)
        
        # Verify only valid action was applied
        updated_findings = mock_get_findings.return_value
        self.assertEqual(updated_findings[0]['triage']['status'], 'open')  # Unchanged due to invalid status


if __name__ == '__main__':
    unittest.main()
