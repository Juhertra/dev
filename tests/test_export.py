#!/usr/bin/env python3
"""
P6 - Export Tests

Test the export functionality for findings reports.
"""

import unittest
import json
import os
import tempfile
import shutil
import csv
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.export_findings_report import (
    export_csv, export_json, export_pdf, _apply_filters
)


class TestExport(unittest.TestCase):
    """Test export functionality."""
    
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
    
    @patch('scripts.export_findings_report.get_findings')
    def test_export_csv_basic(self, mock_get_findings):
        """Test basic CSV export."""
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
                    "owner": "alice@example.com"
                }
            }
        ]
        
        mock_get_findings.return_value = test_findings
        
        output_file = os.path.join(self.test_dir, "test_export.csv")
        export_csv(self.pid, {}, output_file)
        
        # Verify file was created
        self.assertTrue(os.path.exists(output_file))
        
        # Verify CSV content
        with open(output_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['title'], 'Test Finding 1')
        self.assertEqual(rows[0]['severity'], 'high')
        self.assertEqual(rows[0]['triage_status'], 'open')
        self.assertEqual(rows[0]['triage_owner'], 'alice@example.com')
    
    @patch('scripts.export_findings_report.get_findings')
    def test_export_csv_empty(self, mock_get_findings):
        """Test CSV export with no findings."""
        mock_get_findings.return_value = []
        
        output_file = os.path.join(self.test_dir, "empty_export.csv")
        export_csv(self.pid, {}, output_file)
        
        # Verify file was created
        self.assertTrue(os.path.exists(output_file))
        
        # Verify CSV content
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('No findings found', content)
    
    @patch('scripts.export_findings_report.get_findings')
    @patch('scripts.export_findings_report.get_metrics')
    def test_export_json_basic(self, mock_get_metrics, mock_get_findings):
        """Test basic JSON export."""
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
            }
        ]
        
        mock_findings = MagicMock()
        mock_findings.return_value = test_findings
        mock_get_findings.return_value = test_findings
        
        mock_metrics = {
            'total_findings': 1,
            'active': 1,
            'resolved': 0
        }
        mock_get_metrics.return_value = mock_metrics
        
        output_file = os.path.join(self.test_dir, "test_export.json")
        export_json(self.pid, {}, output_file)
        
        # Verify file was created
        self.assertTrue(os.path.exists(output_file))
        
        # Verify JSON content
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        self.assertIn('export_info', data)
        self.assertIn('metrics', data)
        self.assertIn('findings', data)
        
        self.assertEqual(data['export_info']['project_id'], self.pid)
        self.assertEqual(data['export_info']['total_findings'], 1)
        self.assertEqual(len(data['findings']), 1)
        self.assertEqual(data['findings'][0]['title'], 'Test Finding 1')
    
    @patch('scripts.export_findings_report.get_findings')
    @patch('scripts.export_findings_report.get_metrics')
    def test_export_pdf_basic(self, mock_get_metrics, mock_get_findings):
        """Test basic PDF export."""
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
            }
        ]
        
        mock_get_findings.return_value = test_findings
        
        mock_metrics = {
            'total_findings': 1,
            'active': 1,
            'resolved': 0,
            'false_positives': 0,
            'risk_accepted': 0,
            'suppressed': 0,
            'avg_fix_time_days': 0
        }
        mock_get_metrics.return_value = mock_metrics
        
        output_file = os.path.join(self.test_dir, "test_export.pdf")
        
        try:
            export_pdf(self.pid, {}, output_file)
            
            # Verify file was created
            self.assertTrue(os.path.exists(output_file))
            
            # Verify PDF has content (basic check)
            file_size = os.path.getsize(output_file)
            self.assertGreater(file_size, 1000)  # Should be at least 1KB
            
        except SystemExit:
            # Skip test if reportlab is not available
            self.skipTest("reportlab not available")
    
    def test_apply_filters_status(self):
        """Test status filtering."""
        test_findings = [
            {
                "detector_id": "test.detector1",
                "title": "Open Finding",
                "severity": "high",
                "triage": {"status": "open", "tags": [], "notes": []}
            },
            {
                "detector_id": "test.detector2",
                "title": "Resolved Finding",
                "severity": "medium",
                "triage": {"status": "resolved", "tags": [], "notes": []}
            }
        ]
        
        filters = {"status": "open"}
        filtered = _apply_filters(test_findings, filters)
        
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['title'], 'Open Finding')
    
    def test_apply_filters_owner(self):
        """Test owner filtering."""
        test_findings = [
            {
                "detector_id": "test.detector1",
                "title": "Alice Finding",
                "severity": "high",
                "triage": {"status": "open", "tags": [], "notes": [], "owner": "alice@example.com"}
            },
            {
                "detector_id": "test.detector2",
                "title": "Bob Finding",
                "severity": "medium",
                "triage": {"status": "open", "tags": [], "notes": [], "owner": "bob@example.com"}
            }
        ]
        
        filters = {"owner": "alice@example.com"}
        filtered = _apply_filters(test_findings, filters)
        
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['title'], 'Alice Finding')
    
    def test_apply_filters_tag(self):
        """Test tag filtering."""
        test_findings = [
            {
                "detector_id": "test.detector1",
                "title": "Auth Finding",
                "severity": "high",
                "triage": {"status": "open", "tags": ["auth", "critical"], "notes": []}
            },
            {
                "detector_id": "test.detector2",
                "title": "Header Finding",
                "severity": "medium",
                "triage": {"status": "open", "tags": ["header"], "notes": []}
            }
        ]
        
        filters = {"tag": "auth"}
        filtered = _apply_filters(test_findings, filters)
        
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['title'], 'Auth Finding')
    
    def test_apply_filters_date(self):
        """Test date filtering."""
        test_findings = [
            {
                "detector_id": "test.detector1",
                "title": "Recent Finding",
                "severity": "high",
                "created_at": "2025-01-15T10:00:00Z",
                "triage": {"status": "open", "tags": [], "notes": []}
            },
            {
                "detector_id": "test.detector2",
                "title": "Old Finding",
                "severity": "medium",
                "created_at": "2025-01-10T10:00:00Z",
                "triage": {"status": "open", "tags": [], "notes": []}
            }
        ]
        
        filters = {"since": "2025-01-12"}
        filtered = _apply_filters(test_findings, filters)
        
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['title'], 'Recent Finding')
    
    def test_apply_filters_multiple(self):
        """Test multiple filters combined."""
        test_findings = [
            {
                "detector_id": "test.detector1",
                "title": "Matching Finding",
                "severity": "high",
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
                "title": "Non-matching Finding",
                "severity": "medium",
                "created_at": "2025-01-15T10:00:00Z",
                "triage": {
                    "status": "resolved",  # Different status
                    "tags": ["auth"],
                    "notes": [],
                    "owner": "alice@example.com"
                }
            }
        ]
        
        filters = {
            "status": "open",
            "owner": "alice@example.com",
            "tag": "auth"
        }
        filtered = _apply_filters(test_findings, filters)
        
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['title'], 'Matching Finding')


if __name__ == '__main__':
    unittest.main()
