"""
In-Memory Storage Adapter

Implements StoragePort interface using in-memory data structures.
Suitable for testing and development environments.
"""

import json
import pathlib
import tempfile
import shutil
from typing import Dict, Any, List
from datetime import datetime
import uuid

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from packages.runtime_core.storage.storage_port import StoragePort, StorageValidationError, SchemaVersionError


class InMemoryStorageAdapter:
    """In-memory implementation of StoragePort interface."""
    
    def __init__(self):
        self._findings: Dict[str, List[Dict[str, Any]]] = {}
        self._schema_version = "1.0.0"
    
    def atomic_write(self, path: pathlib.Path, data: Dict[str, Any]) -> None:
        """Atomically write data using temp file + rename pattern."""
        # Validate schema version
        if "finding_schema_version" not in data:
            raise SchemaVersionError("Data must include finding_schema_version field")
        
        # Create temp file
        temp_path = path.with_suffix(path.suffix + '.tmp')
        
        try:
            # Write to temp file
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            # Atomic rename
            shutil.move(str(temp_path), str(path))
            
        except Exception as e:
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise StorageValidationError(f"Failed to write data: {e}")
    
    def validate_store_layout(self, path: pathlib.Path) -> bool:
        """Validate storage structure and schema versioning."""
        try:
            if not path.exists():
                return False
            
            with open(path, 'r') as f:
                data = json.load(f)
            
            # Check required fields
            required_fields = ["finding_schema_version", "findings"]
            for field in required_fields:
                if field not in data:
                    return False
            
            # Validate schema version format
            version = data["finding_schema_version"]
            if not isinstance(version, str) or not version.count('.') == 2:
                return False
            
            # Validate findings array
            if not isinstance(data["findings"], list):
                return False
            
            return True
            
        except (json.JSONDecodeError, KeyError, TypeError):
            return False
    
    def get_schema_version(self) -> str:
        """Get current schema version."""
        return self._schema_version
    
    def save_finding(self, finding: Dict[str, Any]) -> None:
        """Save a finding to storage with schema validation."""
        # Validate finding has required fields
        required_fields = ["id", "project_id", "detector_id", "title", "severity", "created_at"]
        for field in required_fields:
            if field not in finding:
                raise StorageValidationError(f"Missing required field: {field}")
        
        # Add schema version if not present
        if "finding_schema_version" not in finding:
            finding["finding_schema_version"] = self._schema_version
        
        # Add to in-memory storage
        project_id = finding["project_id"]
        if project_id not in self._findings:
            self._findings[project_id] = []
        
        self._findings[project_id].append(finding)
    
    def list_findings(self, project_id: str) -> List[Dict[str, Any]]:
        """List all findings for a project."""
        return self._findings.get(project_id, [])
    
    def delete_project(self, project_id: str) -> None:
        """Delete a project and all its findings."""
        if project_id in self._findings:
            del self._findings[project_id]


# Registry for storage adapters
STORAGE_REGISTRY: Dict[str, StoragePort] = {
    "memory": InMemoryStorageAdapter()
}
