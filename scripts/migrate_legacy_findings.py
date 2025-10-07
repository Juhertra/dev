#!/usr/bin/env python3
"""
P3 - Historical Migration Script for Legacy Findings

Migrates all existing findings to the new schema/contract used by P1+/P2.
This script is idempotent - re-running it should change 0 records.

Usage:
    python scripts/migrate_legacy_findings.py [--pid <id>] [--dry-run] [--backup] [--limit N]

Features:
- Normalizes all findings through utils.findings_normalize.normalize_finding()
- Handles legacy aliases (ts→created_at, colon IDs, numeric CWE, etc.)
- De-duplicates within each file
- Creates backups before modifying
- Busts vulns cache after migration
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.findings_normalize import normalize_finding


def load_findings_file(file_path: Path) -> List[Dict[str, Any]]:
    """Load findings from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"❌ Error loading {file_path}: {e}")
        return []


def save_findings_file(file_path: Path, findings: List[Dict[str, Any]], backup: bool = False) -> bool:
    """Save findings to JSON file with optional backup."""
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
            json.dump(findings, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Error saving {file_path}: {e}")
        return False


def extract_key_info(finding: Dict[str, Any]) -> Tuple[str, str, str, str]:
    """Extract key info for deduplication."""
    detector_id = finding.get('detector_id', 'unknown')
    method = finding.get('method', 'GET')
    url = finding.get('url', '')
    evidence = finding.get('evidence', '')
    return detector_id, method, url, evidence


def deduplicate_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicates within findings list, keeping newest by created_at."""
    seen = {}
    deduplicated = []
    
    for finding in findings:
        key = extract_key_info(finding)
        created_at = finding.get('created_at', finding.get('ts', ''))
        
        if key not in seen:
            seen[key] = finding
            deduplicated.append(finding)
        else:
            # Keep the newer one
            existing_created_at = seen[key].get('created_at', seen[key].get('ts', ''))
            if created_at > existing_created_at:
                # Replace the existing one
                deduplicated = [f for f in deduplicated if extract_key_info(f) != key]
                seen[key] = finding
                deduplicated.append(finding)
    
    return deduplicated


def migrate_findings_file(file_path: Path, dry_run: bool = False, backup: bool = False, limit: Optional[int] = None) -> Dict[str, int]:
    """Migrate a single findings file."""
    print(f"\n📁 Processing {file_path}")
    
    findings = load_findings_file(file_path)
    if not findings:
        return {"total": 0, "migrated": 0, "dropped": 0, "duplicates": 0}
    
    # Extract project ID from filename
    pid = file_path.stem.replace('.findings', '')
    
    # Apply limit if specified
    if limit:
        findings = findings[:limit]
        print(f"🔢 Limited to first {limit} findings")
    
    stats = {
        "total": len(findings),
        "migrated": 0,
        "dropped": 0,
        "duplicates": 0
    }
    
    migrated_findings = []
    dropped_reasons = {}
    
    for i, finding in enumerate(findings):
        try:
            # Extract required fields for normalization
            method = finding.get('method', 'GET')
            url = finding.get('url', '')
            status_code = finding.get('status', finding.get('status_code'))
            
            # Skip if missing critical fields
            if not url:
                reason = "missing_url"
                dropped_reasons[reason] = dropped_reasons.get(reason, 0) + 1
                stats["dropped"] += 1
                continue
            
            # Normalize the finding
            normalized = normalize_finding(
                finding,
                pid=pid,
                run_id=finding.get('run_id', f'migration_{int(time.time())}'),
                method=method,
                url=url,
                status_code=status_code
            )
            
            migrated_findings.append(normalized)
            stats["migrated"] += 1
            
        except Exception as e:
            reason = f"normalization_error: {str(e)[:50]}"
            dropped_reasons[reason] = dropped_reasons.get(reason, 0) + 1
            stats["dropped"] += 1
            print(f"⚠️  Dropped finding {i}: {e}")
    
    # Deduplicate
    original_count = len(migrated_findings)
    migrated_findings = deduplicate_findings(migrated_findings)
    stats["duplicates"] = original_count - len(migrated_findings)
    
    # Print stats
    print(f"📊 Stats: {stats['total']} total, {stats['migrated']} migrated, {stats['dropped']} dropped, {stats['duplicates']} duplicates")
    
    if dropped_reasons:
        print("🚫 Drop reasons:")
        for reason, count in dropped_reasons.items():
            print(f"   {reason}: {count}")
    
    # Save if not dry run
    if not dry_run and migrated_findings:
        if save_findings_file(file_path, migrated_findings, backup):
            print(f"✅ Saved {len(migrated_findings)} findings")
            
            # Bust vulns cache
            try:
                from store import _bust_vulns_cache
                _bust_vulns_cache(pid)
                print(f"🔄 Cache busted for {pid}")
            except Exception as e:
                print(f"⚠️  Cache bust failed: {e}")
        else:
            print(f"❌ Failed to save {file_path}")
    elif dry_run:
        print(f"🔍 Dry run: would save {len(migrated_findings)} findings")
    
    return stats


def main():
    parser = argparse.ArgumentParser(description='Migrate legacy findings to new schema')
    parser.add_argument('--pid', help='Specific project ID to migrate (default: all projects)')
    parser.add_argument('--dry-run', action='store_true', help='No write; prints summary only')
    parser.add_argument('--backup', action='store_true', help='Create backup before modifying')
    parser.add_argument('--limit', type=int, help='Migrate first N items per file for testing')
    
    args = parser.parse_args()
    
    print("🚀 P3 Historical Migration - Legacy Findings Normalization")
    print("=" * 60)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be modified")
    
    # Find findings files
    ui_projects_dir = Path("ui_projects")
    if not ui_projects_dir.exists():
        print("❌ ui_projects directory not found")
        return 1
    
    findings_files = []
    if args.pid:
        # Specific project
        findings_file = ui_projects_dir / f"{args.pid}.findings.json"
        if findings_file.exists():
            findings_files = [findings_file]
        else:
            print(f"❌ Findings file not found for project {args.pid}")
            return 1
    else:
        # All projects
        findings_files = list(ui_projects_dir.glob("*.findings.json"))
    
    if not findings_files:
        print("❌ No findings files found")
        return 1
    
    print(f"📂 Found {len(findings_files)} findings files")
    
    # Process each file
    total_stats = {"total": 0, "migrated": 0, "dropped": 0, "duplicates": 0}
    
    for findings_file in findings_files:
        stats = migrate_findings_file(findings_file, args.dry_run, args.backup, args.limit)
        for key in total_stats:
            total_stats[key] += stats[key]
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 MIGRATION SUMMARY")
    print("=" * 60)
    print(f"Total findings processed: {total_stats['total']}")
    print(f"Successfully migrated: {total_stats['migrated']}")
    print(f"Dropped (invalid): {total_stats['dropped']}")
    print(f"Duplicates removed: {total_stats['duplicates']}")
    
    if args.dry_run:
        print("\n🔍 This was a dry run - no files were modified")
    else:
        print(f"\n✅ Migration complete! Processed {len(findings_files)} files")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
