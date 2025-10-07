#!/usr/bin/env python3
"""
P3 - Cache Rebuild Helper

Rebuilds vulns caches for all projects or a specific project.

Usage:
    python scripts/rebuild_vulns_caches.py [--pid <id>]

Features:
- Deletes existing vulns_summary.json files
- Invokes the existing compute route/function to rebuild
- Prints groups count per project
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def delete_cache_file(cache_path: Path) -> bool:
    """Delete a cache file if it exists."""
    try:
        if cache_path.exists():
            cache_path.unlink()
            print(f"🗑️  Deleted cache: {cache_path}")
            return True
        else:
            print(f"ℹ️  No cache to delete: {cache_path}")
            return False
    except Exception as e:
        print(f"❌ Error deleting {cache_path}: {e}")
        return False


def rebuild_cache_for_project(pid: str) -> bool:
    """Rebuild cache for a specific project."""
    try:
        # Import here to avoid circular imports
        from store import _bust_vulns_cache
        from routes.vulns import _compute_vulns_summary
        
        print(f"🔄 Rebuilding cache for project {pid}")
        
        # Bust the cache first
        _bust_vulns_cache(pid)
        
        # Force rebuild by calling the compute function
        summary = _compute_vulns_summary(pid)
        
        if summary and len(summary) > 0:
            groups_count = len(summary)
            print(f"✅ Cache rebuilt for {pid}: {groups_count} groups")
            
            # Write the cache file
            cache_path = Path("ui_projects") / pid / "indexes" / "vulns_summary.json"
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            import json
            with open(cache_path, 'w') as f:
                json.dump(summary, f, indent=2)
            
            print(f"📝 Cache written to {cache_path}")
            return True
        else:
            print(f"⚠️  Cache rebuild failed for {pid}: no groups found")
            return False
            
    except Exception as e:
        print(f"❌ Error rebuilding cache for {pid}: {e}")
        return False


def get_project_ids() -> List[str]:
    """Get all project IDs from ui_projects directory."""
    ui_projects_dir = Path("ui_projects")
    if not ui_projects_dir.exists():
        return []
    
    project_ids = []
    for item in ui_projects_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            project_ids.append(item.name)
    
    return sorted(project_ids)


def main():
    parser = argparse.ArgumentParser(description='Rebuild vulns caches')
    parser.add_argument('--pid', help='Specific project ID to rebuild (default: all projects)')
    
    args = parser.parse_args()
    
    print("🚀 P3 Cache Rebuild Helper")
    print("=" * 40)
    
    # Determine which projects to process
    if args.pid:
        project_ids = [args.pid]
    else:
        project_ids = get_project_ids()
    
    if not project_ids:
        print("❌ No projects found")
        return 1
    
    print(f"📂 Found {len(project_ids)} projects")
    
    # Process each project
    success_count = 0
    
    for pid in project_ids:
        print(f"\n📁 Processing project: {pid}")
        
        # Delete existing cache
        cache_path = Path("ui_projects") / pid / "indexes" / "vulns_summary.json"
        delete_cache_file(cache_path)
        
        # Rebuild cache
        if rebuild_cache_for_project(pid):
            success_count += 1
    
    # Print summary
    print("\n" + "=" * 40)
    print("📊 CACHE REBUILD SUMMARY")
    print("=" * 40)
    print(f"Projects processed: {len(project_ids)}")
    print(f"Successful rebuilds: {success_count}")
    print(f"Failed rebuilds: {len(project_ids) - success_count}")
    
    if success_count == len(project_ids):
        print("\n✅ All caches rebuilt successfully!")
        return 0
    else:
        print(f"\n⚠️  {len(project_ids) - success_count} caches failed to rebuild")
        return 1


if __name__ == "__main__":
    sys.exit(main())
