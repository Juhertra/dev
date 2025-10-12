"""
StoragePort Interface

Defines the contract for storage operations in SecFlow.
Implements hexagonal architecture principles with atomic I/O and schema versioning.
"""

from typing import Protocol, List, Optional, Dict, Any
from abc import abstractmethod
import json
import pathlib
from datetime import datetime


class StoragePort(Protocol):
    """Storage interface contract for SecFlow persistence operations."""
    
    @abstractmethod
    def atomic_write(self, path: pathlib.Path, data: Dict[str, Any]) -> None:
        """
        Atomically write data to storage using temp file + rename pattern.
        
        Args:
            path: Target file path
            data: Data to write (must include schema version)
        """
        pass
    
    @abstractmethod
    def validate_store_layout(self, path: pathlib.Path) -> bool:
        """
        Validate storage structure and schema versioning.
        
        Args:
            path: Storage file path to validate
            
        Returns:
            True if valid, False otherwise
        """
        pass
    
    @abstractmethod
    def get_schema_version(self) -> str:
        """
        Get current schema version for this storage implementation.
        
        Returns:
            Semantic version string (e.g., "1.0.0")
        """
        pass
    
    @abstractmethod
    def save_finding(self, finding: Dict[str, Any]) -> None:
        """
        Save a finding to storage with schema validation.
        
        Args:
            finding: Finding data with finding_schema_version field
        """
        pass
    
    @abstractmethod
    def list_findings(self, project_id: str) -> List[Dict[str, Any]]:
        """
        List all findings for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of finding dictionaries
        """
        pass
    
    @abstractmethod
    def delete_project(self, project_id: str) -> None:
        """
        Delete a project and all its findings.
        
        Args:
            project_id: Project identifier
        """
        pass


class StorageValidationError(Exception):
    """Raised when storage validation fails."""
    pass


class SchemaVersionError(Exception):
    """Raised when schema version is invalid or incompatible."""
    pass
