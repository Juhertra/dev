#!/usr/bin/env python3
"""
P3 - Backfill Missing Nuclei Run Info

Backfills missing nuclei.info for old runs that don't have template information.

Usage:
    python scripts/backfill_run_info.py [--pid <id>] [--dry-run]

Features:
- Finds runs with missing nuclei.info
- Synthesizes minimal info from template_id and severity
- Creates backup before modifying
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_run_file(file_path: Path) -> Dict[str, Any]:
    """Load run from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"❌ Error loading {file_path}: {e}")
        return {}


def save_run_file(file_path: Path, run_data: Dict[str, Any], backup: bool = False) -> bool:
    """Save run to JSON file with optional backup."""
    if backup:
        backup_path = file_path.with_suffix(f'.bak.{int(time.time())}.json')
        try:
            with open(file_path, 'r', encoding='utf-8') as src:
                with open(backup_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            print(f"📦 Backup created: {backup_path}")
        except Exception as e:
            print(f"⚠️  Backup failed: {e}")
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(run_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Error saving {file_path}: {e}")
        return False


def backfill_run_file(file_path: Path, dry_run: bool = False, backup: bool = False) -> Dict[str, int]:
    """Backfill missing nuclei info in a single run file."""
    print(f"\n📁 Processing {file_path}")
    
    run_data = load_run_file(file_path)
    if not run_data:
        return {"total": 0, "backfilled": 0, "skipped": 0}
    
    stats = {
        "total": 0,
        "backfilled": 0,
        "skipped": 0
    }
    
    findings = run_data.get('findings', [])
    if not findings:
        print("ℹ️  No findings in run")
        return stats
    
    stats["total"] = len(findings)
    modified = False
    
    for i, finding in enumerate(findings):
        # Check if nuclei info is missing
        nuclei_info = finding.get('nuclei', {}).get('info')
        if not nuclei_info:
            # Try to synthesize from available data
            template_id = finding.get('template_id', finding.get('detector_id', ''))
            severity = finding.get('severity', 'info')
            
            # Create minimal nuclei info
            nuclei_info = {
                "name": template_id or "Unknown Template",
                "severity": severity,
                "description": ""
            }
            
            # Ensure nuclei object exists
            if 'nuclei' not in finding:
                finding['nuclei'] = {}
            
            finding['nuclei']['info'] = nuclei_info
            stats["backfilled"] += 1
            modified = True
            
            print(f"🔧 Backfilled nuclei info for finding {i}: {template_id}")
        else:
            stats["skipped"] += 1
    
    # Save if modified and not dry run
    if modified and not dry_run:
        if save_run_file(file_path, run_data, backup):
            print(f"✅ Saved backfilled run")
        else:
            print(f"❌ Failed to save {file_path}")
    elif modified and dry_run:
        print(f"🔍 Dry run: would backfill {stats['backfilled']} findings")
    else:
        print(f"ℹ️  No backfilling needed")
    
    return stats


def main():
    parser = argparse.ArgumentParser(description='Backfill missing nuclei run info')
    parser.add_argument('--pid', help='Specific project ID to backfill (default: all projects)')
    parser.add_argument('--dry-run', action='store_true', help='No write; prints summary only')
    
    args = parser.parse_args()
    
    print("🚀 P3 Backfill - Missing Nuclei Run Info")
    print("=" * 50)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be modified")
    
    # Find run files
    ui_projects_dir = Path("ui_projects")
    if not ui_projects_dir.exists():
        print("❌ ui_projects directory not found")
        return 1
    
    run_files = []
    if args.pid:
        # Specific project
        runs_dir = ui_projects_dir / args.pid / "runs"
        if runs_dir.exists():
            run_files = list(runs_dir.glob("*.json"))
        else:
            print(f"❌ Runs directory not found for project {args.pid}")
            return 1
    else:
        # All projects
        for project_dir in ui_projects_dir.iterdir():
            if project_dir.is_dir():
                runs_dir = project_dir / "runs"
                if runs_dir.exists():
                    run_files.extend(runs_dir.glob("*.json"))
    
    if not run_files:
        print("❌ No run files found")
        return 1
    
    print(f"📂 Found {len(run_files)} run files")
    
    # Process each file
    total_stats = {"total": 0, "backfilled": 0, "skipped": 0}
    
    for run_file in run_files:
        stats = backfill_run_file(run_file, args.dry_run, backup=True)
        for key in total_stats:
            total_stats[key] += stats[key]
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 BACKFILL SUMMARY")
    print("=" * 50)
    print(f"Total findings processed: {total_stats['total']}")
    print(f"Backfilled nuclei info: {total_stats['backfilled']}")
    print(f"Skipped (already present): {total_stats['skipped']}")
    
    if args.dry_run:
        print("\n🔍 This was a dry run - no files were modified")
    else:
        print(f"\n✅ Backfill complete! Processed {len(run_files)} files")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
