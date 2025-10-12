"""
StoragePort Contract Tests

Tests the StoragePort interface implementation to ensure
atomic I/O, schema versioning, and validation work correctly.
"""

import pytest
import json
import pathlib
import tempfile
import uuid
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from packages.storage.adapters.memory import InMemoryStorageAdapter, STORAGE_REGISTRY
from packages.runtime_core.storage.storage_port import StorageValidationError, SchemaVersionError


class TestStoragePortContract:
    """Test StoragePort interface contract compliance."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.storage = InMemoryStorageAdapter()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_atomic_write_success(self):
        """Test successful atomic write operation."""
        test_data = {
            "finding_schema_version": "1.0.0",
            "findings": [
                {
                    "id": "test-finding-1",
                    "title": "Test Finding",
                    "severity": "medium"
                }
            ]
        }
        
        test_path = pathlib.Path(self.temp_dir) / "test.json"
        self.storage.atomic_write(test_path, test_data)
        
        # Verify file exists and contains correct data
        assert test_path.exists()
        with open(test_path, 'r') as f:
            loaded_data = json.load(f)
        assert loaded_data == test_data
    
    def test_atomic_write_missing_schema_version(self):
        """Test atomic write fails without schema version."""
        test_data = {"findings": []}
        test_path = pathlib.Path(self.temp_dir) / "test.json"
        
        with pytest.raises(SchemaVersionError):
            self.storage.atomic_write(test_path, test_data)
    
    def test_validate_store_layout_valid(self):
        """Test storage layout validation with valid data."""
        test_data = {
            "finding_schema_version": "1.0.0",
            "findings": [
                {
                    "id": "test-finding-1",
                    "title": "Test Finding",
                    "severity": "medium"
                }
            ]
        }
        
        test_path = pathlib.Path(self.temp_dir) / "valid.json"
        with open(test_path, 'w') as f:
            json.dump(test_data, f)
        
        assert self.storage.validate_store_layout(test_path) is True
    
    def test_validate_store_layout_invalid(self):
        """Test storage layout validation with invalid data."""
        test_data = {"invalid": "data"}
        
        test_path = pathlib.Path(self.temp_dir) / "invalid.json"
        with open(test_path, 'w') as f:
            json.dump(test_data, f)
        
        assert self.storage.validate_store_layout(test_path) is False
    
    def test_get_schema_version(self):
        """Test schema version retrieval."""
        version = self.storage.get_schema_version()
        assert isinstance(version, str)
        assert version.count('.') == 2  # Semantic version format
    
    def test_save_finding_success(self):
        """Test successful finding save operation."""
        finding = {
            "id": str(uuid.uuid4()),
            "project_id": "test-project",
            "detector_id": "test.detector",
            "title": "Test Finding",
            "severity": "medium",
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        self.storage.save_finding(finding)
        
        # Verify finding was saved
        findings = self.storage.list_findings("test-project")
        assert len(findings) == 1
        assert findings[0]["id"] == finding["id"]
    
    def test_save_finding_missing_required_field(self):
        """Test finding save fails with missing required fields."""
        finding = {
            "id": str(uuid.uuid4()),
            "title": "Test Finding",
            # Missing required fields
        }
        
        with pytest.raises(StorageValidationError):
            self.storage.save_finding(finding)
    
    def test_list_findings_empty_project(self):
        """Test listing findings for non-existent project."""
        findings = self.storage.list_findings("non-existent-project")
        assert findings == []
    
    def test_delete_project(self):
        """Test project deletion."""
        finding = {
            "id": str(uuid.uuid4()),
            "project_id": "test-project",
            "detector_id": "test.detector",
            "title": "Test Finding",
            "severity": "medium",
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        self.storage.save_finding(finding)
        assert len(self.storage.list_findings("test-project")) == 1
        
        self.storage.delete_project("test-project")
        assert len(self.storage.list_findings("test-project")) == 0
    
    def test_storage_registry(self):
        """Test storage adapter registry."""
        assert "memory" in STORAGE_REGISTRY
        assert isinstance(STORAGE_REGISTRY["memory"], InMemoryStorageAdapter)
