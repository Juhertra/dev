#!/usr/bin/env python3
"""
One-time migration script to clean up CVE placeholder values.

This script removes invalid CVE IDs (like "CVE-0000-0000") from existing findings
and replaces them with None/null values.

Usage:
    python scripts/migrate_cve_placeholders.py [project_id]

If no project_id is provided, it will migrate all projects.
"""

import os
import sys
import json
import re
import logging
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from store import list_projects, STORE_DIR

def _is_valid_cve(cve_id: str) -> bool:
    """Check if CVE ID matches the valid pattern and is not a placeholder."""
    if not cve_id or not isinstance(cve_id, str):
        return False
    # Check format and exclude placeholder
    if not re.match(r'^CVE-\d{4}-\d+$', cve_id):
        return False
    # Exclude common placeholder values
    if cve_id in ['CVE-0000-0000', 'CVE-0000-0001', 'CVE-0000-0002']:
        return False
    return True

def migrate_project_cve_placeholders(pid: str) -> Dict[str, int]:
    """Migrate CVE placeholders for a single project."""
    findings_file = os.path.join(STORE_DIR, f"{pid}.findings.json")
    
    if not os.path.exists(findings_file):
        return {"cleaned": 0, "kept": 0, "error": "findings file not found"}
    
    try:
        # Read findings
        with open(findings_file, 'r', encoding='utf-8') as f:
            findings = json.load(f)
        
        cleaned = 0
        kept = 0
        
        # Process each finding
        for finding in findings:
            cve_id = finding.get("cve_id")
            if cve_id and isinstance(cve_id, str):
                if _is_valid_cve(cve_id):
                    kept += 1
                else:
                    # Remove invalid CVE
                    finding["cve_id"] = None
                    cleaned += 1
        
        # Write back if changes were made
        if cleaned > 0:
            with open(findings_file, 'w', encoding='utf-8') as f:
                json.dump(findings, f, indent=2, ensure_ascii=False)
            
            # Remove vulnerabilities cache to force regeneration
            vulns_cache_file = os.path.join("ui_projects", pid, "indexes", "vulns_summary.json")
            if os.path.exists(vulns_cache_file):
                os.remove(vulns_cache_file)
        
        return {"cleaned": cleaned, "kept": kept}
        
    except Exception as e:
        return {"cleaned": 0, "kept": 0, "error": str(e)}

def main():
    """Main migration function."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Get project ID from command line or migrate all
    if len(sys.argv) > 1:
        project_ids = [sys.argv[1]]
    else:
        try:
            projects = list_projects()
            project_ids = [p["id"] for p in projects]
        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            return 1
    
    total_cleaned = 0
    total_kept = 0
    
    logger.info(f"Starting CVE migration for {len(project_ids)} project(s)")
    
    for pid in project_ids:
        logger.info(f"Migrating project: {pid}")
        result = migrate_project_cve_placeholders(pid)
        
        if "error" in result:
            logger.error(f"Project {pid}: {result['error']}")
            continue
        
        cleaned = result["cleaned"]
        kept = result["kept"]
        
        total_cleaned += cleaned
        total_kept += kept
        
        logger.info(f"CVE_MIGRATE cleaned={cleaned} kept={kept} pid={pid}")
    
    logger.info(f"Migration complete: {total_cleaned} CVE placeholders cleaned, {total_kept} valid CVEs kept")
    return 0

if __name__ == "__main__":
    sys.exit(main())
