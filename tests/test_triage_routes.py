#!/usr/bin/env python3
"""
P5 - Triage Routes Tests

Test the triage API routes for updating findings triage state.
"""

import json
import os
import shutil

# Add project root to path
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask

from routes.triage import register_triage_routes


class TestTriageRoutes(unittest.TestCase):
    """Test triage API routes."""
    
    def setUp(self):
        """Set up test environment."""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Register triage routes
        register_triage_routes(self.app)
        
        # Create test directory and findings file
        self.test_dir = tempfile.mkdtemp()
        self.pid = "test_project"
        self.findings_file = f"ui_projects/{self.pid}.findings.json"
        
        # Ensure ui_projects directory exists
        os.makedirs("ui_projects", exist_ok=True)
        
        # Create test findings
        self.test_findings = [
            {
                "detector_id": "test.detector",
                "title": "Test Finding",
                "severity": "medium",
                "method": "GET",
                "url": "https://example.com/test",
                "path": "/test",
                "created_at": "2025-01-15T10:00:00Z",
                "triage": {
                    "status": "open",
                    "tags": [],
                    "notes": []
                }
            }
        ]
        
        with open(self.findings_file, 'w') as f:
            json.dump(self.test_findings, f)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
        if os.path.exists(self.findings_file):
            os.remove(self.findings_file)
        if os.path.exists("ui_projects"):
            shutil.rmtree("ui_projects")
    
    @patch('routes.triage._bust_vulns_cache')
    def test_update_finding_triage_status(self, mock_bust_cache):
        """Test updating finding triage status."""
        response = self.client.post(f'/p/{self.pid}/findings/0/triage', 
                                   json={'status': 'in_progress'})
        
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['triage']['status'], 'in_progress')
        
        # Verify file was updated
        with open(self.findings_file, 'r') as f:
            findings = json.load(f)
        self.assertEqual(findings[0]['triage']['status'], 'in_progress')
        
        # Verify cache was busted
        mock_bust_cache.assert_called_once_with(self.pid)
    
    @patch('routes.triage._bust_vulns_cache')
    def test_update_finding_triage_owner(self, mock_bust_cache):
        """Test updating finding triage owner."""
        response = self.client.post(f'/p/{self.pid}/findings/0/triage', 
                                   json={'owner': 'alice@example.com'})
        
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['triage']['owner'], 'alice@example.com')
        
        # Verify file was updated
        with open(self.findings_file, 'r') as f:
            findings = json.load(f)
        self.assertEqual(findings[0]['triage']['owner'], 'alice@example.com')
    
    @patch('routes.triage._bust_vulns_cache')
    def test_update_finding_triage_tags(self, mock_bust_cache):
        """Test updating finding triage tags."""
        response = self.client.post(f'/p/{self.pid}/findings/0/triage', 
                                   json={'tags': ['auth', 'critical']})
        
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['triage']['tags'], ['auth', 'critical'])
        
        # Verify file was updated
        with open(self.findings_file, 'r') as f:
            findings = json.load(f)
        self.assertEqual(findings[0]['triage']['tags'], ['auth', 'critical'])
    
    @patch('routes.triage._bust_vulns_cache')
    def test_update_finding_triage_suppress(self, mock_bust_cache):
        """Test suppressing a finding."""
        suppress_data = {
            'suppress': {
                'reason': 'False positive',
                'scope': 'this',
                'until': '2025-12-31T23:59:59Z'
            }
        }
        
        response = self.client.post(f'/p/{self.pid}/findings/0/triage', 
                                   json=suppress_data)
        
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['triage']['suppress']['reason'], 'False positive')
        
        # Verify file was updated
        with open(self.findings_file, 'r') as f:
            findings = json.load(f)
        self.assertEqual(findings[0]['triage']['suppress']['reason'], 'False positive')
    
    @patch('routes.triage._bust_vulns_cache')
    def test_add_finding_note(self, mock_bust_cache):
        """Test adding a note to a finding."""
        note_data = {
            'text': 'This is a test note',
            'by': 'test@example.com'
        }
        
        response = self.client.post(f'/p/{self.pid}/findings/0/note', 
                                   json=note_data)
        
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['note']['text'], 'This is a test note')
        self.assertEqual(data['note']['by'], 'test@example.com')
        self.assertEqual(data['total_notes'], 1)
        
        # Verify file was updated
        with open(self.findings_file, 'r') as f:
            findings = json.load(f)
        self.assertEqual(len(findings[0]['triage']['notes']), 1)
        self.assertEqual(findings[0]['triage']['notes'][0]['text'], 'This is a test note')
    
    @patch('routes.triage._bust_vulns_cache')
    def test_add_finding_tag(self, mock_bust_cache):
        """Test adding a tag to a finding."""
        tag_data = {
            'tag': 'auth',
            'action': 'add'
        }
        
        response = self.client.post(f'/p/{self.pid}/findings/0/tag', 
                                   json=tag_data)
        
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'add')
        self.assertEqual(data['tag'], 'auth')
        self.assertIn('auth', data['tags'])
        
        # Verify file was updated
        with open(self.findings_file, 'r') as f:
            findings = json.load(f)
        self.assertIn('auth', findings[0]['triage']['tags'])
    
    @patch('routes.triage._bust_vulns_cache')
    def test_remove_finding_tag(self, mock_bust_cache):
        """Test removing a tag from a finding."""
        # First add a tag
        self.client.post(f'/p/{self.pid}/findings/0/tag', 
                        json={'tag': 'auth', 'action': 'add'})
        
        # Then remove it
        tag_data = {
            'tag': 'auth',
            'action': 'remove'
        }
        
        response = self.client.post(f'/p/{self.pid}/findings/0/tag', 
                                   json=tag_data)
        
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'remove')
        self.assertEqual(data['tag'], 'auth')
        self.assertNotIn('auth', data['tags'])
    
    @patch('routes.triage._bust_vulns_cache')
    def test_suppress_finding(self, mock_bust_cache):
        """Test suppressing a finding."""
        suppress_data = {
            'reason': 'False positive',
            'scope': 'this'
        }
        
        response = self.client.post(f'/p/{self.pid}/findings/0/suppress', 
                                   json=suppress_data)
        
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['suppress']['reason'], 'False positive')
        self.assertEqual(data['suppress']['scope'], 'this')
        
        # Verify file was updated
        with open(self.findings_file, 'r') as f:
            findings = json.load(f)
        self.assertEqual(findings[0]['triage']['suppress']['reason'], 'False positive')
    
    def test_update_finding_triage_invalid_index(self):
        """Test updating triage for invalid finding index."""
        response = self.client.post(f'/p/{self.pid}/findings/999/triage', 
                                   json={'status': 'in_progress'})
        
        self.assertEqual(response.status_code, 400)
        
        data = response.get_json()
        self.assertIn('error', data)
        self.assertIn('Invalid finding index', data['error'])
    
    def test_add_finding_note_empty_text(self):
        """Test adding note with empty text."""
        note_data = {
            'text': '',
            'by': 'test@example.com'
        }
        
        response = self.client.post(f'/p/{self.pid}/findings/0/note', 
                                   json=note_data)
        
        self.assertEqual(response.status_code, 400)
        
        data = response.get_json()
        self.assertIn('error', data)
        self.assertIn('Note text is required', data['error'])
    
    def test_suppress_finding_empty_reason(self):
        """Test suppressing finding with empty reason."""
        suppress_data = {
            'reason': '',
            'scope': 'this'
        }
        
        response = self.client.post(f'/p/{self.pid}/findings/0/suppress', 
                                   json=suppress_data)
        
        self.assertEqual(response.status_code, 400)
        
        data = response.get_json()
        self.assertIn('error', data)
        self.assertIn('Suppression reason is required', data['error'])
    
    def test_add_finding_tag_invalid_action(self):
        """Test adding tag with invalid action."""
        tag_data = {
            'tag': 'auth',
            'action': 'invalid'
        }
        
        response = self.client.post(f'/p/{self.pid}/findings/0/tag', 
                                   json=tag_data)
        
        self.assertEqual(response.status_code, 400)
        
        data = response.get_json()
        self.assertIn('error', data)
        self.assertIn('Invalid action', data['error'])


if __name__ == '__main__':
    unittest.main()
