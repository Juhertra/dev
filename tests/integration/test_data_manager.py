"""
Test Data and Fixtures for SecFlow Integration Tests

This module provides test data, fixtures, and utilities for integration testing.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, List


class TestDataManager:
    """Manages test data for integration tests."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def create_workflow_yaml(self, workflow_type: str = "linear") -> str:
        """Create a workflow YAML file."""
        if workflow_type == "linear":
            workflow = {
                "name": "sample_linear_workflow",
                "version": "1.0",
                "project_id": "test_project",
                "steps": [
                    {
                        "id": "nuclei_scan",
                        "plugin": "nuclei",
                        "config": {
                            "target": "http://test-target.com",
                            "templates": "res://templates/nuclei:latest",
                            "rate_limit": 150,
                            "threads": 25
                        }
                    }
                ]
            }
        elif workflow_type == "error_handling":
            workflow = {
                "name": "error_handling_workflow",
                "version": "1.0",
                "project_id": "test_project",
                "steps": [
                    {
                        "id": "failing_step",
                        "plugin": "failing_plugin",
                        "config": {
                            "should_fail": True,
                            "error_type": "timeout"
                        }
                    }
                ]
            }
        elif workflow_type == "security":
            workflow = {
                "name": "security_test_workflow",
                "version": "1.0",
                "project_id": "test_project",
                "steps": [
                    {
                        "id": "malicious_plugin_test",
                        "plugin": "malicious_plugin",
                        "config": {
                            "target": "http://test-target.com",
                            "unauthorized_access": True
                        }
                    }
                ]
            }
        else:
            raise ValueError(f"Unknown workflow type: {workflow_type}")
        
        yaml_file = self.data_dir / f"{workflow_type}_workflow.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(workflow, f, default_flow_style=False)
        
        return str(yaml_file)
    
    def create_plugin_manifest(self, plugin_name: str = "test_plugin") -> str:
        """Create a plugin manifest JSON file."""
        manifest = {
            "name": plugin_name,
            "version": "1.0.0",
            "binary": plugin_name,
            "capabilities": ["scan"],
            "config_schema": f"schemas/{plugin_name}-config.json",
            "defaults": {
                "timeout": 30,
                "retries": 3
            },
            "signature": f"{plugin_name}_signature_hash"
        }
        
        manifest_file = self.data_dir / f"{plugin_name}_manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return str(manifest_file)
    
    def create_test_findings(self, count: int = 5) -> List[Dict[str, Any]]:
        """Create test findings data."""
        findings = []
        severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        
        for i in range(count):
            finding = {
                "detector_id": f"TEST_DETECTOR_{i:03d}",
                "timestamp": "2025-10-14T12:00:00Z",
                "severity": severities[i % len(severities)],
                "title": f"Test Finding {i}",
                "description": f"This is test finding number {i}",
                "target": f"http://test-target-{i}.com",
                "metadata": {
                    "plugin": "test_plugin",
                    "workflow_id": "test_workflow",
                    "test_id": i
                }
            }
            findings.append(finding)
        
        return findings
    
    def create_nuclei_output(self) -> str:
        """Create mock Nuclei tool output."""
        nuclei_output = [
            {
                "template": "sql-injection",
                "info": {
                    "name": "SQL Injection",
                    "severity": "high",
                    "description": "SQL injection vulnerability detected"
                },
                "matched_at": "http://test-target.com/login",
                "timestamp": "2025-10-14T12:00:00Z"
            },
            {
                "template": "xss",
                "info": {
                    "name": "Cross-Site Scripting",
                    "severity": "medium",
                    "description": "XSS vulnerability detected"
                },
                "matched_at": "http://test-target.com/search",
                "timestamp": "2025-10-14T12:01:00Z"
            }
        ]
        
        output_file = self.data_dir / "nuclei_output.json"
        with open(output_file, 'w') as f:
            json.dump(nuclei_output, f, indent=2)
        
        return str(output_file)
    
    def create_config_schema(self, plugin_name: str = "test_plugin") -> str:
        """Create a plugin configuration schema."""
        schema = {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Target URL or IP address"
                },
                "templates": {
                    "type": "string",
                    "description": "Nuclei templates to use",
                    "default": "res://templates/nuclei:latest"
                },
                "rate_limit": {
                    "type": "integer",
                    "description": "Rate limit for requests",
                    "default": 150,
                    "minimum": 1,
                    "maximum": 1000
                },
                "threads": {
                    "type": "integer",
                    "description": "Number of threads",
                    "default": 25,
                    "minimum": 1,
                    "maximum": 100
                }
            },
            "required": ["target"]
        }
        
        schema_file = self.data_dir / f"{plugin_name}_config_schema.json"
        with open(schema_file, 'w') as f:
            json.dump(schema, f, indent=2)
        
        return str(schema_file)


# Test fixtures for pytest
def create_test_data_dir(tmp_path):
    """Create a temporary test data directory."""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    return data_dir


def create_sample_workflow_files(tmp_path):
    """Create sample workflow files for testing."""
    data_manager = TestDataManager(tmp_path / "test_data")
    
    files = {
        "linear_workflow": data_manager.create_workflow_yaml("linear"),
        "error_workflow": data_manager.create_workflow_yaml("error_handling"),
        "security_workflow": data_manager.create_workflow_yaml("security"),
        "nuclei_manifest": data_manager.create_plugin_manifest("nuclei"),
        "test_manifest": data_manager.create_plugin_manifest("test_plugin"),
        "nuclei_output": data_manager.create_nuclei_output(),
        "config_schema": data_manager.create_config_schema("nuclei")
    }
    
    return files


# Mock data for testing
MOCK_NUCLEI_OUTPUT = [
    {
        "template": "sql-injection",
        "info": {
            "name": "SQL Injection",
            "severity": "high",
            "description": "SQL injection vulnerability detected in login form"
        },
        "matched_at": "http://test-target.com/login",
        "timestamp": "2025-10-14T12:00:00Z"
    },
    {
        "template": "xss",
        "info": {
            "name": "Cross-Site Scripting",
            "severity": "medium", 
            "description": "XSS vulnerability detected in search form"
        },
        "matched_at": "http://test-target.com/search",
        "timestamp": "2025-10-14T12:01:00Z"
    },
    {
        "template": "directory-listing",
        "info": {
            "name": "Directory Listing",
            "severity": "low",
            "description": "Directory listing enabled"
        },
        "matched_at": "http://test-target.com/admin/",
        "timestamp": "2025-10-14T12:02:00Z"
    }
]

MOCK_WORKFLOW_CONFIG = {
    "name": "integration_test_workflow",
    "version": "1.0",
    "project_id": "integration_test_project",
    "steps": [
        {
            "id": "nuclei_scan",
            "plugin": "nuclei",
            "config": {
                "target": "http://test-target.com",
                "templates": "res://templates/nuclei:latest",
                "rate_limit": 150,
                "threads": 25
            }
        }
    ]
}

MOCK_PLUGIN_MANIFEST = {
    "name": "nuclei",
    "version": "1.0.0",
    "binary": "nuclei",
    "capabilities": ["scan"],
    "config_schema": "schemas/nuclei-config.json",
    "defaults": {
        "rate_limit": 150,
        "templates": "res://templates/nuclei:latest",
        "threads": 25,
        "timeout": 30
    },
    "signature": "nuclei_signature_hash_12345"
}

MOCK_FINDINGS = [
    {
        "detector_id": "NUCLEI_SQL_INJECTION_001",
        "timestamp": "2025-10-14T12:00:00Z",
        "severity": "HIGH",
        "title": "SQL Injection Vulnerability",
        "description": "SQL injection vulnerability detected in login form",
        "target": "http://test-target.com/login",
        "metadata": {
            "plugin": "nuclei",
            "template": "sql-injection",
            "workflow_id": "integration_test_workflow"
        }
    },
    {
        "detector_id": "NUCLEI_XSS_001",
        "timestamp": "2025-10-14T12:01:00Z",
        "severity": "MEDIUM",
        "title": "Cross-Site Scripting",
        "description": "XSS vulnerability detected in search form",
        "target": "http://test-target.com/search",
        "metadata": {
            "plugin": "nuclei",
            "template": "xss",
            "workflow_id": "integration_test_workflow"
        }
    },
    {
        "detector_id": "NUCLEI_DIRECTORY_LISTING_001",
        "timestamp": "2025-10-14T12:02:00Z",
        "severity": "LOW",
        "title": "Directory Listing Enabled",
        "description": "Directory listing is enabled on admin endpoint",
        "target": "http://test-target.com/admin/",
        "metadata": {
            "plugin": "nuclei",
            "template": "directory-listing",
            "workflow_id": "integration_test_workflow"
        }
    }
]
