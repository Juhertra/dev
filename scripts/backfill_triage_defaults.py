#!/usr/bin/env python3
"""
P5 - Backfill Triage Defaults Migration Script

Idempotent migration to add default triage fields to existing findings.
Safe to run multiple times - only adds missing triage fields.
"""

import json
import os
import sys
import argparse
import time
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from store import _bust_vulns_cache


def load_findings_file(file_path: str) -> List[Dict[str, Any]]:
    """Load findings from JSON file."""
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return []
    
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"❌ Error loading {file_path}: {e}")
        return []


def save_findings_file(file_path: str, findings: List[Dict[str, Any]], backup: bool = False) -> bool:
    """Save findings to JSON file with optional backup."""
    if backup:
        backup_path = f"{file_path}.bak.{int(time.time())}"
        try:
            if os.path.exists(file_path):
                os.rename(file_path, backup_path)
                print(f"📦 Backup created: {backup_path}")
        except OSError as e:
            print(f"❌ Error creating backup: {e}")
            return False
    
    try:
        with open(file_path, 'w') as f:
            json.dump(findings, f, indent=2)
        return True
    except IOError as e:
        print(f"❌ Error saving {file_path}: {e}")
        return False


def add_triage_defaults(finding: Dict[str, Any]) -> Dict[str, Any]:
    """Add default triage fields to a finding if missing."""
    if 'triage' not in finding:
        finding['triage'] = {
            "status": "open",
            "tags": [],
            "notes": []
        }
        return finding
    
    # Ensure required fields exist with defaults
    triage = finding['triage']
    if 'status' not in triage:
        triage['status'] = 'open'
    if 'tags' not in triage:
        triage['tags'] = []
    if 'notes' not in triage:
        triage['notes'] = []
    
    return finding


def migrate_project_findings(pid: str, dry_run: bool = False, backup: bool = False) -> Dict[str, int]:
    """Migrate findings for a specific project."""
    file_path = f"ui_projects/{pid}.findings.json"
    
    if not os.path.exists(file_path):
        print(f"⚠️  Findings file not found: {file_path}")
        return {"processed": 0, "updated": 0, "errors": 0}
    
    print(f"📁 Processing {file_path}...")
    
    # Load findings
    findings = load_findings_file(file_path)
    if not findings:
        print(f"ℹ️  No findings to process in {file_path}")
        return {"processed": len(findings), "updated": 0, "errors": 0}
    
    # Process findings
    updated_count = 0
    error_count = 0
    
    for i, finding in enumerate(findings):
        try:
            original_triage = finding.get('triage')
            updated_finding = add_triage_defaults(finding.copy())
            
            # Check if triage was added/modified
            if original_triage != updated_finding.get('triage'):
                findings[i] = updated_finding
                updated_count += 1
                
        except Exception as e:
            print(f"❌ Error processing finding {i}: {e}")
            error_count += 1
    
    # Save if not dry run
    if not dry_run and updated_count > 0:
        if save_findings_file(file_path, findings, backup):
            print(f"✅ Updated {updated_count} findings in {file_path}")
            
            # Bust cache
            try:
                _bust_vulns_cache(pid)
                print(f"🔄 Cache busted for {pid}")
            except Exception as e:
                print(f"⚠️  Cache bust failed for {pid}: {e}")
        else:
            print(f"❌ Failed to save {file_path}")
            error_count += updated_count
            updated_count = 0
    elif dry_run:
        print(f"🔍 Dry run: Would update {updated_count} findings in {file_path}")
    
    return {
        "processed": len(findings),
        "updated": updated_count,
        "errors": error_count
    }


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description="Backfill triage defaults for findings")
    parser.add_argument("--pid", help="Specific project ID to migrate (default: all projects)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without making changes")
    parser.add_argument("--backup", action="store_true", help="Create backup files before modifying")
    
    args = parser.parse_args()
    
    print("🚀 P5 Triage Defaults Migration")
    print("=" * 40)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    if args.backup:
        print("📦 Backup mode enabled")
    
    # Find projects to migrate
    if args.pid:
        project_ids = [args.pid]
    else:
        # Find all project findings files
        ui_projects_dir = Path("ui_projects")
        if not ui_projects_dir.exists():
            print("❌ ui_projects directory not found")
            return 1
        
        project_ids = []
        for file_path in ui_projects_dir.glob("*.findings.json"):
            pid = file_path.stem.replace(".findings", "")
            project_ids.append(pid)
    
    if not project_ids:
        print("ℹ️  No projects found to migrate")
        return 0
    
    print(f"📋 Found {len(project_ids)} project(s) to process")
    
    # Process each project
    total_stats = {"processed": 0, "updated": 0, "errors": 0}
    
    for pid in project_ids:
        print(f"\n📁 Processing project: {pid}")
        stats = migrate_project_findings(pid, args.dry_run, args.backup)
        
        total_stats["processed"] += stats["processed"]
        total_stats["updated"] += stats["updated"]
        total_stats["errors"] += stats["errors"]
    
    # Summary
    print(f"\n📊 Migration Summary")
    print("=" * 40)
    print(f"Projects processed: {len(project_ids)}")
    print(f"Total findings: {total_stats['processed']}")
    print(f"Findings updated: {total_stats['updated']}")
    print(f"Errors: {total_stats['errors']}")
    
    if total_stats["errors"] > 0:
        print(f"\n⚠️  {total_stats['errors']} errors occurred during migration")
        return 1
    
    if args.dry_run:
        print(f"\n🔍 Dry run completed successfully")
    else:
        print(f"\n✅ Migration completed successfully")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
