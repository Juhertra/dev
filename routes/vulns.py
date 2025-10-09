import json
import logging
import os
import time
from collections import defaultdict
from typing import Any, Dict, List

from flask import jsonify, render_template, request

logger = logging.getLogger(__name__)

def register_vulns_routes(bp):
    """Register vulnerabilities-related routes on the given blueprint."""

    @bp.route("/p/<pid>/vulns")
    def vulns_page(pid: str):
        """Vulnerabilities hub page - aggregated view of findings across runs."""
        start_time = time.time()
        request_id = getattr(request, 'request_id', 'unknown')
        
        try:
            from store import get_project_name
            from utils.schema_validation import validate_json
            
            # Check if we have a cached summary
            summary_file = os.path.join("ui_projects", pid, "indexes", "vulns_summary.json")
            vulns_data = []
            cache_stale = False
            
            if os.path.exists(summary_file):
                try:
                    # Check if cache is stale (older than 5 minutes)
                    cache_age = time.time() - os.path.getmtime(summary_file)
                    if cache_age > 300:  # 5 minutes
                        cache_stale = True
                        logger.info(f"VULNS_SUMMARY_CACHE_STALE pid={pid} age_seconds={int(cache_age)}")
                    else:
                        with open(summary_file, 'r') as f:
                            vulns_data = json.load(f)
                        logger.info(f"VULNS_SUMMARY_CACHE_HIT pid={pid} count={len(vulns_data)}")
                except Exception as e:
                    logger.warning(f"VULNS_SUMMARY_CACHE_ERROR pid={pid} error={str(e)}")
                    vulns_data = []
            
            # If no cache, empty, or stale, compute from runs
            if not vulns_data or cache_stale:
                start_compute = time.time()
                vulns_data = _compute_vulns_summary(pid)
                compute_duration_ms = int((time.time() - start_compute) * 1000)
                
                # Validate before writing
                if validate_json(vulns_data, "vulns_summary.schema.json", "vulns_summary"):
                    # Write cache
                    os.makedirs(os.path.dirname(summary_file), exist_ok=True)
                    with open(summary_file, 'w') as f:
                        json.dump(vulns_data, f, indent=2)
                    logger.info(f"VULNS_INDEX_REBUILT pid={pid} groups={len(vulns_data)} ms={compute_duration_ms}")
                else:
                    logger.warning(f"VULNS_SUMMARY_VALIDATION_FAIL pid={pid}")
            
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(f"request_id={request_id} duration_ms={duration_ms} path=/p/{pid}/vulns method=GET status=200")
            
            return render_template(
                "vulns.html",
                pid=pid,
                project_name=get_project_name(pid),
                vulns=vulns_data
            )
            
        except Exception as e:
            logger.error(f"request_id={request_id} error={str(e)} path=/p/{pid}/vulns method=GET status=500")
            return f"Error loading vulnerabilities page: {str(e)}", 500

    @bp.route("/p/<pid>/vulns/preview", methods=["POST"])
    def vulns_preview(pid: str):
        """Open preview drawer for a vulnerability."""
        try:
            endpoint_key = request.form.get('endpoint_key')
            if not endpoint_key:
                return "Missing endpoint_key", 400
            
            # This would normally open the preview drawer
            # For now, return a simple response
            return f"<div class='alert alert-info'>Preview for endpoint: {endpoint_key}</div>"
            
        except Exception as e:
            logger.error(f"VULNS_PREVIEW_ERROR pid={pid} error={str(e)}")
            return f"Error opening preview: {str(e)}", 500

    @bp.route("/p/<pid>/vulns/runs", methods=["POST"])
    def vulns_runs(pid: str):
        """Open runs drawer for a vulnerability."""
        try:
            endpoint_key = request.form.get('endpoint_key')
            if not endpoint_key:
                return "Missing endpoint_key", 400
            
            # This would normally open the runs drawer
            # For now, return a simple response
            return f"<div class='alert alert-info'>Runs for endpoint: {endpoint_key}</div>"
            
        except Exception as e:
            logger.error(f"VULNS_RUNS_ERROR pid={pid} error={str(e)}")
            return f"Error opening runs: {str(e)}", 500

    @bp.route("/p/<pid>/vulns/summary.json")
    def vulns_summary_json(pid: str):
        """Live vulnerabilities summary as JSON (no disk cache)."""
        try:
            # Always compute fresh from findings
            vulns_data = _compute_vulns_summary(pid)
            
            logger.info(f"VULNS_SUMMARY_JSON pid={pid} count={len(vulns_data)}")
            return jsonify(vulns_data)
            
        except Exception as e:
            logger.error(f"VULNS_SUMMARY_JSON_ERROR pid={pid} error={str(e)}")
            return jsonify({"error": str(e)}), 500

    @bp.route("/p/<pid>/vulns/bulk", methods=["POST"])
    def vulns_bulk_actions(pid: str):
        """Apply bulk triage actions to multiple vulnerabilities."""
        try:
            
            # Get request data
            data = request.get_json() or {}
            indices = data.get('indices', [])
            actions = data.get('actions', [])
            
            if not indices:
                return jsonify({"error": "No indices provided"}), 400
            
            if not actions:
                return jsonify({"error": "No actions provided"}), 400
            
            # Validate indices are integers
            try:
                indices = [int(idx) for idx in indices]
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid indices format"}), 400
            
            # Apply bulk actions
            result = _apply_bulk_actions(pid, indices, actions)
            
            if result['success']:
                logger.info(f"BULK_APPLY_OK pid={pid} count={result['count']} actions={len(actions)}")
                return jsonify({
                    "success": True,
                    "count": result['count'],
                    "message": f"Applied {len(actions)} action(s) to {result['count']} vulnerability(ies)"
                })
            else:
                return jsonify({"error": result['error']}), 400
                
        except Exception as e:
            logger.error(f"VULNS_BULK_ERROR pid={pid} error={str(e)}")
            return jsonify({"error": str(e)}), 500

def _apply_bulk_actions(pid: str, indices: List[int], actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Apply bulk triage actions to findings with batching and error handling."""
    try:
        from datetime import datetime, timezone

        from findings import get_findings
        from store import _bust_vulns_cache
        
        # Load findings
        findings = get_findings(pid)
        
        if not findings:
            return {"success": False, "error": "No findings found for project"}
        
        # Validate indices
        max_index = len(findings) - 1
        invalid_indices = [idx for idx in indices if idx < 0 or idx > max_index]
        if invalid_indices:
            return {"success": False, "error": f"Invalid indices: {invalid_indices}"}
        
        # Batch processing for large selections
        BATCH_SIZE = 250
        total_updated = 0
        
        for batch_start in range(0, len(indices), BATCH_SIZE):
            batch_indices = indices[batch_start:batch_start + BATCH_SIZE]
            
            # Apply each action to the batch
            for action in actions:
                action_type = action.get('action')
                value = action.get('value')
                
                if not action_type:
                    continue
                
                # Apply action to each finding in batch
                for idx in batch_indices:
                    finding = findings[idx]
                    
                    # Initialize triage if not exists
                    if 'triage' not in finding:
                        finding['triage'] = {"status": "open", "tags": [], "notes": []}
                    
                    # Apply specific action
                    if action_type == 'set_status':
                        if value in ['open', 'in_progress', 'risk_accepted', 'false_positive', 'resolved']:
                            finding['triage']['status'] = value
                    
                    elif action_type == 'set_owner':
                        if isinstance(value, str) and value.strip():
                            finding['triage']['owner'] = value.strip()
                    
                    elif action_type == 'add_tag':
                        if isinstance(value, str) and value.strip():
                            if 'tags' not in finding['triage']:
                                finding['triage']['tags'] = []
                            tag = value.strip()
                            if tag not in finding['triage']['tags']:
                                finding['triage']['tags'].append(tag)
                    
                    elif action_type == 'remove_tag':
                        if isinstance(value, str) and value.strip():
                            if 'tags' in finding['triage']:
                                tag = value.strip()
                                if tag in finding['triage']['tags']:
                                    finding['triage']['tags'].remove(tag)
                    
                    elif action_type == 'suppress':
                        if isinstance(value, dict):
                            suppress_data = {
                                "reason": value.get('reason', ''),
                                "scope": value.get('scope', 'this')
                            }
                            if value.get('until'):
                                suppress_data['until'] = value['until']
                            finding['triage']['suppress'] = suppress_data
                    
                    # Update timestamp
                    finding['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            total_updated += len(batch_indices)
        
        # Save findings file
        findings_file = f"ui_projects/{pid}.findings.json"
        with open(findings_file, 'w') as f:
            json.dump(findings, f, indent=2)
        
        # Bust caches
        try:
            _bust_vulns_cache(pid)
        except Exception as e:
            logger.warning(f"Cache bust failed for {pid}: {e}")
        
        logger.info(f"BULK_APPLY_COMPLETE pid={pid} updated={total_updated} actions={len(actions)}")
        
        return {
            "success": True,
            "count": total_updated
        }
        
    except Exception as e:
        logger.error(f"BULK_APPLY_ERROR pid={pid} error={str(e)}")
        return {"success": False, "error": str(e)}

def _compute_vulns_summary(pid: str) -> List[Dict[str, Any]]:
    """Compute vulnerabilities summary from runs data."""
    try:
        from findings import get_findings
        from utils.endpoints import endpoint_key
        
        # Get all findings for the project
        findings = get_findings(pid)
        
        # Group by endpoint_key + detector_id
        groups = defaultdict(lambda: {
            'endpoint_key': '',
            'detector_id': '',
            'template_id': '',
            'title': '',
            'occurrences': 0,
            'latest_run_id': '',
            'latest_at': '',
            'worst_severity': 'info',
            'severity_rank': 0,
            'cve_id': None,
            'cwe': None,
            'owasp': None,
            'owasp_api': None,
            'source': 'detector',
            'counts_by_status': {  # P5 triage status counts
                'open': 0,
                'in_progress': 0,
                'risk_accepted': 0,
                'false_positive': 0,
                'resolved': 0
            },
            'has_suppressed': False  # P5 suppression flag
        })
        
        severity_ranks = {'critical': 5, 'high': 4, 'medium': 3, 'low': 2, 'info': 1}
        
        for finding in findings:
            # TODO(P3-cleanup): remove after migration complete
            # Tolerant reader shims for legacy fields
            if 'created_at' not in finding and 'ts' in finding:
                finding['created_at'] = finding['ts']
            if 'path' not in finding and 'url' in finding:
                from urllib.parse import urlparse
                parsed = urlparse(finding['url'])
                finding['path'] = parsed.path or '/'
            
            # Check if finding is suppressed (P5)
            triage = finding.get('triage', {})
            suppress = triage.get('suppress', {})
            is_suppressed = False
            
            if suppress:
                # Check if suppression is still active
                until = suppress.get('until')
                if until:
                    from datetime import datetime, timezone
                    try:
                        suppress_until = datetime.fromisoformat(until.replace('Z', '+00:00'))
                        is_suppressed = suppress_until > datetime.now(timezone.utc)
                    except ValueError:
                        # Invalid timestamp, treat as not suppressed
                        is_suppressed = False
                else:
                    # No until date means permanent suppression
                    is_suppressed = True
            
            # Create grouping key
            finding_endpoint_key = endpoint_key(
                finding.get('method', 'GET'),
                finding.get('url', ''),
                finding.get('path', '')
            )
            detector_id = finding.get('detector_id', 'unknown')
            group_key = f"{finding_endpoint_key}|{detector_id}"
            
            group = groups[group_key]
            group['endpoint_key'] = finding_endpoint_key
            group['detector_id'] = detector_id
            group['template_id'] = finding.get('nuclei', {}).get('template_id', '')
            group['title'] = finding.get('title', 'Unknown')
            
            # Only count non-suppressed findings in occurrences
            if not is_suppressed:
                group['occurrences'] += 1
            
            # Track suppression status
            if is_suppressed:
                group['has_suppressed'] = True
            
            # Track triage status counts (P5)
            status = triage.get('status', 'open')
            if status in group['counts_by_status']:
                group['counts_by_status'][status] += 1
            
            # Update latest run info
            run_id = finding.get('run_id', '')
            if run_id and (not group['latest_run_id'] or run_id > group['latest_run_id']):
                group['latest_run_id'] = run_id
                group['latest_at'] = finding.get('created_at', '')
            
            # Update worst severity
            severity = finding.get('severity', 'info')
            if severity_ranks.get(severity, 0) > severity_ranks.get(group['worst_severity'], 0):
                group['worst_severity'] = severity
                group['severity_rank'] = severity_ranks.get(severity, 0)
            
            # Set classification fields (use first occurrence values)
            if not group['cve_id']:
                cve_id = finding.get('cve_id')
                # Only set if it's a real CVE, not placeholder
                if cve_id and cve_id != 'CVE-0000-0000':
                    group['cve_id'] = cve_id
            if not group['cwe']:
                group['cwe'] = finding.get('cwe')
            if not group['owasp']:
                group['owasp'] = finding.get('owasp')
            if not group['owasp_api']:
                group['owasp_api'] = finding.get('owasp_api')
            if not group['source'] or group['source'] == 'detector':
                group['source'] = finding.get('source', 'detector')
        
        # Convert to list and sort by severity rank (desc) then occurrences (desc)
        vulns_list = list(groups.values())
        vulns_list.sort(key=lambda x: (-x['severity_rank'], -x['occurrences']))
        
        logger.info(f"VULNS_SUMMARY_COMPUTED pid={pid} groups={len(vulns_list)}")
        return vulns_list
        
    except Exception as e:
        logger.error(f"VULNS_SUMMARY_COMPUTE_ERROR pid={pid} error={str(e)}")
        return []
