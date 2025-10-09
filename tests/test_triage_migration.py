#!/usr/bin/env python3
"""
P5 - Triage Migration Tests

Test the idempotent migration script for backfilling triage defaults.
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

from scripts.backfill_triage_defaults import (
    add_triage_defaults,
    load_findings_file,
    migrate_project_findings,
    save_findings_file,
)


class TestTriageMigration(unittest.TestCase):
    """Test triage migration functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        # Create ui_projects directory structure
        self.ui_projects_dir = os.path.join(self.test_dir, "ui_projects")
        os.makedirs(self.ui_projects_dir, exist_ok=True)
        self.findings_file = os.path.join(self.ui_projects_dir, "test.findings.json")
        
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
    def test_load_findings_file_empty(self):
        """Test loading empty findings file."""
        # Create empty file
        open(self.findings_file, 'w').close()
        
        findings = load_findings_file(self.findings_file)
        self.assertEqual(findings, [])
    
    def test_load_findings_file_valid(self):
        """Test loading valid findings file."""
        test_findings = [
            {
                "detector_id": "test.detector",
                "title": "Test Finding",
                "severity": "medium",
                "method": "GET",
                "url": "https://example.com/test",
                "path": "/test",
                "created_at": "2025-01-15T10:00:00Z"
            }
        ]
        
        with open(self.findings_file, 'w') as f:
            json.dump(test_findings, f)
        
        findings = load_findings_file(self.findings_file)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["detector_id"], "test.detector")
    
    def test_load_findings_file_invalid_json(self):
        """Test loading invalid JSON file."""
        with open(self.findings_file, 'w') as f:
            f.write("invalid json")
        
        findings = load_findings_file(self.findings_file)
        self.assertEqual(findings, [])
    
    def test_add_triage_defaults_new_finding(self):
        """Test adding triage defaults to finding without triage."""
        finding = {
            "detector_id": "test.detector",
            "title": "Test Finding"
        }
        
        result = add_triage_defaults(finding)
        
        self.assertIn("triage", result)
        self.assertEqual(result["triage"]["status"], "open")
        self.assertEqual(result["triage"]["tags"], [])
        self.assertEqual(result["triage"]["notes"], [])
    
    def test_add_triage_defaults_existing_triage(self):
        """Test adding defaults to finding with existing triage."""
        finding = {
            "detector_id": "test.detector",
            "title": "Test Finding",
            "triage": {
                "status": "in_progress",
                "owner": "test@example.com"
            }
        }
        
        result = add_triage_defaults(finding)
        
        self.assertEqual(result["triage"]["status"], "in_progress")
        self.assertEqual(result["triage"]["owner"], "test@example.com")
        self.assertEqual(result["triage"]["tags"], [])
        self.assertEqual(result["triage"]["notes"], [])
    
    def test_add_triage_defaults_partial_triage(self):
        """Test adding defaults to finding with partial triage."""
        finding = {
            "detector_id": "test.detector",
            "title": "Test Finding",
            "triage": {
                "owner": "test@example.com"
            }
        }
        
        result = add_triage_defaults(finding)
        
        self.assertEqual(result["triage"]["status"], "open")
        self.assertEqual(result["triage"]["owner"], "test@example.com")
        self.assertEqual(result["triage"]["tags"], [])
        self.assertEqual(result["triage"]["notes"], [])
    
    def test_save_findings_file_success(self):
        """Test saving findings file successfully."""
        test_findings = [
            {
                "detector_id": "test.detector",
                "title": "Test Finding"
            }
        ]
        
        result = save_findings_file(self.findings_file, test_findings)
        self.assertTrue(result)
        
        # Verify file was created and contains correct data
        self.assertTrue(os.path.exists(self.findings_file))
        with open(self.findings_file, 'r') as f:
            saved_findings = json.load(f)
        self.assertEqual(saved_findings, test_findings)
    
    def test_save_findings_file_with_backup(self):
        """Test saving findings file with backup."""
        # Create original file
        original_findings = [{"detector_id": "original"}]
        with open(self.findings_file, 'w') as f:
            json.dump(original_findings, f)
        
        # Save new findings with backup
        new_findings = [{"detector_id": "new"}]
        result = save_findings_file(self.findings_file, new_findings, backup=True)
        
        self.assertTrue(result)
        
        # Verify backup was created
        backup_files = [f for f in os.listdir(self.ui_projects_dir) if '.bak.' in f]
        self.assertEqual(len(backup_files), 1)
        
        # Verify original content is in backup
        backup_file = os.path.join(self.ui_projects_dir, backup_files[0])
        with open(backup_file, 'r') as f:
            backup_findings = json.load(f)
        self.assertEqual(backup_findings, original_findings)
        
        # Verify new content is in main file
        with open(self.findings_file, 'r') as f:
            saved_findings = json.load(f)
        self.assertEqual(saved_findings, new_findings)
    
    @patch('scripts.backfill_triage_defaults._bust_vulns_cache')
    @patch('scripts.backfill_triage_defaults.Path')
    def test_migrate_project_findings_dry_run(self, mock_path, mock_bust_cache):
        """Test migrating project findings in dry run mode."""
        # Mock Path to return our test directory
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.glob.return_value = [Path(self.findings_file)]
        
        # Create test findings file
        test_findings = [
            {
                "detector_id": "test.detector",
                "title": "Test Finding"
            }
        ]
        
        with open(self.findings_file, 'w') as f:
            json.dump(test_findings, f)
        
        # Change to test directory and run migration
        original_cwd = os.getcwd()
        try:
            os.chdir(self.test_dir)
            stats = migrate_project_findings("test", dry_run=True, backup=False)
        finally:
            os.chdir(original_cwd)
        
        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["updated"], 1)
        self.assertEqual(stats["errors"], 0)
        
        # Verify no changes were made to file
        with open(self.findings_file, 'r') as f:
            saved_findings = json.load(f)
        self.assertEqual(saved_findings, test_findings)
        
        # Verify cache bust was not called
        mock_bust_cache.assert_not_called()
    
    @patch('scripts.backfill_triage_defaults._bust_vulns_cache')
    def test_migrate_project_findings_actual_run(self, mock_bust_cache):
        """Test migrating project findings in actual run mode."""
        # Create test findings file
        test_findings = [
            {
                "detector_id": "test.detector",
                "title": "Test Finding"
            }
        ]
        
        with open(self.findings_file, 'w') as f:
            json.dump(test_findings, f)
        
        # Change to test directory and run migration
        original_cwd = os.getcwd()
        try:
            os.chdir(self.test_dir)
            stats = migrate_project_findings("test", dry_run=False, backup=False)
        finally:
            os.chdir(original_cwd)
        
        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["updated"], 1)
        self.assertEqual(stats["errors"], 0)
        
        # Verify changes were made to file
        with open(self.findings_file, 'r') as f:
            saved_findings = json.load(f)
        
        self.assertIn("triage", saved_findings[0])
        self.assertEqual(saved_findings[0]["triage"]["status"], "open")
        self.assertEqual(saved_findings[0]["triage"]["tags"], [])
        self.assertEqual(saved_findings[0]["triage"]["notes"], [])
        
        # Verify cache bust was called
        mock_bust_cache.assert_called_once_with("test")
    
    @patch('scripts.backfill_triage_defaults._bust_vulns_cache')
    def test_migrate_project_findings_idempotent(self, mock_bust_cache):
        """Test that migration is idempotent."""
        # Create test findings file with existing triage
        test_findings = [
            {
                "detector_id": "test.detector",
                "title": "Test Finding",
                "triage": {
                    "status": "open",
                    "tags": [],
                    "notes": []
                }
            }
        ]
        
        with open(self.findings_file, 'w') as f:
            json.dump(test_findings, f)
        
        # Change to test directory and run migration
        original_cwd = os.getcwd()
        try:
            os.chdir(self.test_dir)
            stats = migrate_project_findings("test", dry_run=False, backup=False)
        finally:
            os.chdir(original_cwd)
        
        self.assertEqual(stats["processed"], 1)
        self.assertEqual(stats["updated"], 0)  # No updates needed
        self.assertEqual(stats["errors"], 0)
        
        # Verify file content is unchanged
        with open(self.findings_file, 'r') as f:
            saved_findings = json.load(f)
        self.assertEqual(saved_findings, test_findings)
    
    def test_migrate_project_findings_nonexistent_file(self):
        """Test migrating non-existent findings file."""
        stats = migrate_project_findings("nonexistent", dry_run=False, backup=False)
        
        self.assertEqual(stats["processed"], 0)
        self.assertEqual(stats["updated"], 0)
        self.assertEqual(stats["errors"], 0)


if __name__ == '__main__':
    unittest.main()
