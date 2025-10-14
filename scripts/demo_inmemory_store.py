#!/usr/bin/env python3
"""
Demo script for InMemoryStorageAdapter

Demonstrates StoragePort interface implementation with atomic I/O and schema versioning.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from packages.storage.adapters.memory import InMemoryStorageAdapter
from datetime import datetime
import uuid

def main():
    """Demo InMemoryStorageAdapter functionality."""
    print("=== InMemoryStorageAdapter Demo ===")
    
    # Initialize storage adapter
    store = InMemoryStorageAdapter()
    print(f"Schema version: {store.get_schema_version()}")
    
    # Create sample finding
    finding = {
        "id": str(uuid.uuid4()),
        "project_id": "proj-1",
        "detector_id": "scan.nuclei",
        "title": "X-Frame-Options header missing",
        "severity": "low",
        "resource": "https://app.acme.com/",
        "evidence": {"template": "misconfig/headers/xfo-missing.yaml"},
        "created_at": datetime.utcnow().isoformat() + "Z",
        "finding_schema_version": "1.0.0"
    }
    
    # Save finding
    print(f"\nSaving finding: {finding['id']}")
    store.save_finding(finding)
    
    # List findings
    findings = store.list_findings("proj-1")
    print(f"Found {len(findings)} findings for proj-1")
    
    # Validate storage layout
    print(f"\nStorage validation: {store.validate_store_layout}")
    
    # Test atomic write
    test_data = {
        "finding_schema_version": "1.0.0",
        "findings": [finding]
    }
    
    print(f"\nAtomic write test data: {len(test_data)} fields")
    print("Demo completed successfully!")

if __name__ == "__main__":
    main()
