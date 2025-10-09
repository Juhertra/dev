"""
Tool manifest schema and validation for wrapper configuration.

This module defines the standardized manifest format for tool wrappers,
including schema validation, version checking, and configuration management.
"""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
import json
import yaml
import jsonschema
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ToolManifest:
    """Standardized tool manifest container."""
    name: str
    version: str
    binary: str
    capabilities: List[str]
    outputs: Dict[str, str]
    defaults: Dict[str, Any]
    config_schema: Optional[str] = None
    resource_requirements: Optional[Dict[str, Any]] = None
    security: Optional[Dict[str, Any]] = None
    selftest: Optional[Dict[str, Any]] = None
    min_version: Optional[str] = None


# JSON Schema for tool manifest validation
TOOL_MANIFEST_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["name", "version", "binary", "capabilities", "outputs", "defaults"],
    "properties": {
        "name": {
            "type": "string",
            "pattern": "^[a-z0-9-]+$",
            "description": "Tool name (lowercase, alphanumeric, hyphens only)"
        },
        "version": {
            "type": "string",
            "pattern": "^\\d+\\.\\d+\\.\\d+$",
            "description": "Tool version (semantic versioning)"
        },
        "binary": {
            "type": "string",
            "description": "Tool binary name or path"
        },
        "capabilities": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["scan", "crawl", "discovery", "fuzzing", "analysis"]
            },
            "description": "Tool capabilities"
        },
        "outputs": {
            "type": "object",
            "properties": {
                "dataset": {
                    "type": "string",
                    "enum": ["findings", "endpoints", "resources", "mixed"]
                }
            },
            "required": ["dataset"],
            "description": "Output data types"
        },
        "defaults": {
            "type": "object",
            "description": "Default configuration values"
        },
        "config_schema": {
            "type": "string",
            "description": "Path to configuration schema file"
        },
        "resource_requirements": {
            "type": "object",
            "properties": {
                "cpu_cores": {"type": "integer", "minimum": 1},
                "memory_mb": {"type": "integer", "minimum": 128},
                "timeout_seconds": {"type": "integer", "minimum": 30}
            },
            "description": "Resource requirements"
        },
        "security": {
            "type": "object",
            "properties": {
                "sandbox": {"type": "boolean"},
                "network_access": {"type": "boolean"},
                "file_system_access": {
                    "type": "string",
                    "enum": ["read_only", "read_write", "none"]
                }
            },
            "description": "Security constraints"
        },
        "selftest": {
            "type": "object",
            "properties": {
                "args": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "expect": {"type": "string"}
            },
            "description": "Self-test configuration"
        },
        "min_version": {
            "type": "string",
            "pattern": "^\\d+\\.\\d+\\.\\d+$",
            "description": "Minimum supported version"
        }
    }
}


class ManifestValidator:
    """Tool manifest validation and management."""
    
    def __init__(self):
        self.schema = TOOL_MANIFEST_SCHEMA
    
    def validate_manifest(self, manifest_data: Dict[str, Any]) -> bool:
        """
        Validate tool manifest against schema.
        
        Args:
            manifest_data: Manifest dictionary to validate
            
        Returns:
            bool: True if valid, False otherwise
            
        Raises:
            jsonschema.ValidationError: If manifest is invalid
        """
        try:
            jsonschema.validate(manifest_data, self.schema)
            return True
        except jsonschema.ValidationError as e:
            logger.error(f"Manifest validation failed: {e.message}")
            raise
    
    def load_manifest(self, manifest_path: Union[str, Path]) -> ToolManifest:
        """
        Load and validate tool manifest from file.
        
        Args:
            manifest_path: Path to manifest file (JSON or YAML)
            
        Returns:
            ToolManifest: Validated manifest object
        """
        path = Path(manifest_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Manifest file not found: {manifest_path}")
        
        # Load file based on extension
        with open(path, 'r') as f:
            if path.suffix.lower() in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        
        # Validate manifest
        self.validate_manifest(data)
        
        # Convert to ToolManifest object
        return ToolManifest(
            name=data["name"],
            version=data["version"],
            binary=data["binary"],
            capabilities=data["capabilities"],
            outputs=data["outputs"],
            defaults=data["defaults"],
            config_schema=data.get("config_schema"),
            resource_requirements=data.get("resource_requirements"),
            security=data.get("security"),
            selftest=data.get("selftest"),
            min_version=data.get("min_version")
        )
    
    def save_manifest(self, manifest: ToolManifest, output_path: Union[str, Path]) -> None:
        """
        Save tool manifest to file.
        
        Args:
            manifest: ToolManifest object to save
            output_path: Output file path
        """
        path = Path(output_path)
        
        # Convert to dictionary
        data = {
            "name": manifest.name,
            "version": manifest.version,
            "binary": manifest.binary,
            "capabilities": manifest.capabilities,
            "outputs": manifest.outputs,
            "defaults": manifest.defaults
        }
        
        # Add optional fields
        if manifest.config_schema:
            data["config_schema"] = manifest.config_schema
        if manifest.resource_requirements:
            data["resource_requirements"] = manifest.resource_requirements
        if manifest.security:
            data["security"] = manifest.security
        if manifest.selftest:
            data["selftest"] = manifest.selftest
        if manifest.min_version:
            data["min_version"] = manifest.min_version
        
        # Validate before saving
        self.validate_manifest(data)
        
        # Save based on extension
        with open(path, 'w') as f:
            if path.suffix.lower() in ['.yaml', '.yml']:
                yaml.dump(data, f, default_flow_style=False, indent=2)
            else:
                json.dump(data, f, indent=2)


# Example manifest templates for reference
NUCLEI_MANIFEST_TEMPLATE = {
    "name": "nuclei",
    "version": "3.2.1",
    "binary": "nuclei",
    "capabilities": ["scan"],
    "outputs": {"dataset": "findings"},
    "defaults": {
        "threads": 25,
        "rate_limit": 150,
        "templates": "res://templates/nuclei:latest"
    },
    "config_schema": "schemas/nuclei-config.json",
    "resource_requirements": {
        "cpu_cores": 2,
        "memory_mb": 512,
        "timeout_seconds": 300
    },
    "security": {
        "sandbox": True,
        "network_access": True,
        "file_system_access": "read_only"
    },
    "selftest": {
        "args": ["-version"],
        "expect": "Nuclei"
    },
    "min_version": "2.9.0"
}

FEROXBUSTER_MANIFEST_TEMPLATE = {
    "name": "feroxbuster",
    "version": "2.10.0",
    "binary": "feroxbuster",
    "capabilities": ["discovery"],
    "outputs": {"dataset": "endpoints"},
    "defaults": {
        "threads": 50,
        "wordlist": "res://wordlists/common.txt",
        "extensions": "php,html,js"
    },
    "resource_requirements": {
        "cpu_cores": 1,
        "memory_mb": 256,
        "timeout_seconds": 600
    },
    "security": {
        "sandbox": True,
        "network_access": True,
        "file_system_access": "read_only"
    },
    "min_version": "2.8.0"
}

KATANA_MANIFEST_TEMPLATE = {
    "name": "katana",
    "version": "1.0.0",
    "binary": "katana",
    "capabilities": ["crawl"],
    "outputs": {"dataset": "endpoints"},
    "defaults": {
        "depth": 3,
        "threads": 10,
        "js_crawl": True
    },
    "resource_requirements": {
        "cpu_cores": 1,
        "memory_mb": 512,
        "timeout_seconds": 900
    },
    "security": {
        "sandbox": True,
        "network_access": True,
        "file_system_access": "read_only"
    },
    "min_version": "0.0.0"
}


def create_manifest_templates(output_dir: Union[str, Path]) -> None:
    """
    Create example manifest templates for all supported tools.
    
    Args:
        output_dir: Directory to save manifest templates
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    validator = ManifestValidator()
    
    templates = {
        "nuclei.json": NUCLEI_MANIFEST_TEMPLATE,
        "feroxbuster.json": FEROXBUSTER_MANIFEST_TEMPLATE,
        "katana.json": KATANA_MANIFEST_TEMPLATE
    }
    
    for filename, template in templates.items():
        manifest = ToolManifest(**template)
        validator.save_manifest(manifest, output_path / filename)
        logger.info(f"Created manifest template: {filename}")


if __name__ == "__main__":
    # Example usage
    validator = ManifestValidator()
    
    # Validate example manifest
    try:
        validator.validate_manifest(NUCLEI_MANIFEST_TEMPLATE)
        print("✅ Nuclei manifest template is valid")
    except jsonschema.ValidationError as e:
        print(f"❌ Nuclei manifest validation failed: {e.message}")
    
    # Create manifest templates
    create_manifest_templates("manifests")
    print("✅ Manifest templates created")
