#!/usr/bin/env python3
"""
Dossier Management Utilities

Functions to manage endpoint dossier data, including:
- Fixing run attribution issues
- Managing retired endpoint status
- Cleaning up shared runs
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from utils.endpoints import endpoint_key, endpoint_safe_key

logger = logging.getLogger(__name__)


def get_project_endpoints_dir(pid: str) -> str:
    """Get the endpoints directory for a project."""
    return os.path.join("/Users/hernan.trajtemberg/Documents/Test/dev/ui_projects", pid, "endpoints")


def load_endpoint_dossier(pid: str, endpoint_key: str) -> Optional[Dict[str, Any]]:
    """Load an endpoint dossier file."""
    safe_key = endpoint_safe_key(endpoint_key)
    dossier_path = os.path.join(get_project_endpoints_dir(pid), f"{safe_key}.json")
    
    if not os.path.exists(dossier_path):
        return None
    
    try:
        with open(dossier_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load dossier {dossier_path}: {e}")
        return None


def save_endpoint_dossier(pid: str, endpoint_key: str, dossier_data: Dict[str, Any]) -> bool:
    """Save an endpoint dossier file."""
    safe_key = endpoint_safe_key(endpoint_key)
    endpoints_dir = get_project_endpoints_dir(pid)
    dossier_path = os.path.join(endpoints_dir, f"{safe_key}.json")
    
    try:
        os.makedirs(endpoints_dir, exist_ok=True)
        with open(dossier_path, 'w', encoding='utf-8') as f:
            json.dump(dossier_data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save dossier {dossier_path}: {e}")
        return False


def remove_run_from_dossier(pid: str, endpoint_key: str, run_id: str) -> bool:
    """Remove a specific run from an endpoint dossier."""
    dossier_data = load_endpoint_dossier(pid, endpoint_key)
    if not dossier_data:
        return False
    
    original_count = len(dossier_data.get("runs", []))
    dossier_data["runs"] = [
        run for run in dossier_data.get("runs", [])
        if run.get("run_id") != run_id
    ]
    
    removed_count = original_count - len(dossier_data["runs"])
    if removed_count > 0:
        logger.info(f"Removed {removed_count} run(s) with ID {run_id} from {endpoint_key}")
        return save_endpoint_dossier(pid, endpoint_key, dossier_data)
    
    return False


def get_artifact_endpoint_info(artifact_path: str) -> Optional[Dict[str, str]]:
    """Extract endpoint information from a Nuclei artifact file."""
    if not os.path.exists(artifact_path) or os.path.getsize(artifact_path) == 0:
        return None
    
    try:
        with open(artifact_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line:
                data = json.loads(first_line)
                
                # Extract URL from various possible fields
                url = data.get("host", "")
                if not url:
                    url = data.get("matched-at", "")
                if not url:
                    # Try to extract from request field
                    request = data.get("request", "")
                    if request:
                        lines = request.split('\n')
                        if len(lines) > 0:
                            parts = lines[0].split()
                            if len(parts) >= 2:
                                url = parts[1]
                
                # Extract method
                method = "GET"
                request_field = data.get("request", "")
                if request_field:
                    parts = request_field.split()
                    if len(parts) > 0:
                        method = parts[0].upper()
                
                if url and method:
                    return {
                        "method": method,
                        "url": url,
                        "matched_at": data.get("matched-at", "")
                    }
    except Exception as e:
        logger.error(f"Failed to parse artifact {artifact_path}: {e}")
    
    return None


def fix_run_attribution(pid: str, shared_run_id: str, correct_endpoint_key: str, 
                       incorrect_endpoint_keys: List[str]) -> Dict[str, bool]:
    """
    Fix run attribution by moving a run to the correct endpoint and removing it from incorrect ones.
    
    Args:
        pid: Project ID
        shared_run_id: The run ID that's incorrectly attributed to multiple endpoints
        correct_endpoint_key: The endpoint this run should belong to
        incorrect_endpoint_keys: List of endpoints this run should be removed from
    
    Returns:
        Dict mapping endpoint_key to success status
    """
    results = {}
    
    # Remove the run from incorrect endpoints
    for incorrect_key in incorrect_endpoint_keys:
        success = remove_run_from_dossier(pid, incorrect_key, shared_run_id)
        results[incorrect_key] = success
        logger.info(f"Removed run {shared_run_id} from {incorrect_key}: {'Success' if success else 'Failed'}")
    
    # Verify the correct endpoint still has the run
    correct_dossier = load_endpoint_dossier(pid, correct_endpoint_key)
    if correct_dossier:
        has_run = any(run.get("run_id") == shared_run_id for run in correct_dossier.get("runs", []))
        results[correct_endpoint_key] = has_run
        logger.info(f"Correct endpoint {correct_endpoint_key} has run {shared_run_id}: {'Yes' if has_run else 'No'}")
    
    return results


def fix_pet_endpoint_run_attribution(pid: str) -> Dict[str, bool]:
    """
    Specific fix for the pet endpoint run attribution issue.
    
    Based on our analysis:
    - run_1759590564242 has 0 findings (empty artifact)
    - It appears in both PUT and POST pet endpoints
    - run_PETSTORE_VALIDATED_1 has 5 findings and only appears in POST
    
    We'll remove run_1759590564242 from PUT since it seems to be a POST-specific run.
    """
    put_key = "PUT https://petstore3.swagger.io/api/v3/pet"
    post_key = "POST https://petstore3.swagger.io/api/v3/pet"
    shared_run_id = "run_1759590564242"
    
    logger.info("Fixing pet endpoint run attribution...")
    
    # Based on the data, this run seems to be POST-specific since POST has more comprehensive data
    results = fix_run_attribution(
        pid=pid,
        shared_run_id=shared_run_id,
        correct_endpoint_key=post_key,
        incorrect_endpoint_keys=[put_key]
    )
    
    return results


def mark_endpoints_retired(pid: str, endpoint_keys: List[str], reason: str = "API specification removed") -> Dict[str, bool]:
    """
    Mark endpoints as retired by adding retirement metadata to their dossier files.
    
    Args:
        pid: Project ID
        endpoint_keys: List of endpoint keys to mark as retired
        reason: Reason for retirement
    
    Returns:
        Dict mapping endpoint_key to success status
    """
    results = {}
    
    for endpoint_key in endpoint_keys:
        dossier_data = load_endpoint_dossier(pid, endpoint_key)
        if dossier_data:
            dossier_data["retired"] = {
                "status": "retired",
                "retired_at": __import__('time').strftime("%Y-%m-%dT%H:%M:%SZ", __import__('time').gmtime()),
                "reason": reason
            }
            
            success = save_endpoint_dossier(pid, endpoint_key, dossier_data)
            results[endpoint_key] = success
            logger.info(f"Marked {endpoint_key} as retired: {'Success' if success else 'Failed'}")
        else:
            results[endpoint_key] = False
            logger.warning(f"Cannot mark {endpoint_key} as retired - dossier not found")
    
    return results


def get_endpoint_status(pid: str, endpoint_key: str) -> str:
    """Get the current status of an endpoint (active, retired, etc.)."""
    dossier_data = load_endpoint_dossier(pid, endpoint_key)
    if not dossier_data:
        return "unknown"
    
    retired_info = dossier_data.get("retired")
    if retired_info:
        return retired_info.get("status", "retired")
    
    return "active"


if __name__ == "__main__":
    # Test the pet endpoint fix
    pid = "ec4c0976-fd94-463c-8ada-0705fe12b944"
    
    print("Fixing pet endpoint run attribution...")
    results = fix_pet_endpoint_run_attribution(pid)
    print("Results:", results)
    
    # Verify the fix
    print("\nVerifying fix...")
    put_key = "PUT https://petstore3.swagger.io/api/v3/pet"
    post_key = "POST https://petstore3.swagger.io/api/v3/pet"
    
    put_dossier = load_endpoint_dossier(pid, put_key)
    post_dossier = load_endpoint_dossier(pid, post_key)
    
    print(f"PUT endpoint runs: {len(put_dossier.get('runs', [])) if put_dossier else 0}")
    print(f"POST endpoint runs: {len(post_dossier.get('runs', [])) if post_dossier else 0}")
