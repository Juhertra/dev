from typing import Any, Dict
from flask import render_template, request, render_template_string, current_app
from utils.rendering import render_first
from utils.preview import build_endpoint_preview
from store import get_runtime
from utils.endpoints import endpoint_key
import logging
import time
import os
import json

# Local imports inside route functions to avoid circular deps

logger = logging.getLogger(__name__)

def _build_cached_sitemap(pid: str):
    """Simple sitemap builder (no caching for now)."""
    from sitemap_builder import build_site_map
    
    # Log cache operation (MISS since we're always executing)
    cache_logger = logging.getLogger('cache')
    cache_logger.info(f"CACHE MISS key=sitemap:{pid}")
    
    return build_site_map(pid)

def register_sitemap_routes(bp):
    """Register sitemap-related routes on the given blueprint."""

    @bp.route("/p/<pid>/sitemap")
    def site_map_page(pid: str):
        """Site Map page - hierarchical view of all endpoints."""
        start_time = time.time()
        request_id = getattr(request, 'request_id', 'unknown')
        
        try:
            from store import get_project_name
            from findings import count_findings_cached
            
            # Use cached sitemap builder
            sitemap_roots = _build_cached_sitemap(pid)
            
            # Record metrics (Phase 3) - simplified for browser validation
            pass
            
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(f"request_id={request_id} duration_ms={duration_ms} path=/p/{pid}/sitemap method=GET status=200")
            
            return render_template(
                "sitemap.html",
                pid=pid,
                project_name=get_project_name(pid),
                counts=count_findings_cached(pid),
                sitemap={"roots": sitemap_roots},
                active_nav="sitemap",
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"request_id={request_id} duration_ms={duration_ms} path=/p/{pid}/sitemap method=GET status=500 error=\"{str(e)}\"")
            return f"Error loading site map: {str(e)}", 500

    @bp.post("/p/<pid>/sitemap/endpoint-preview")
    def sitemap_endpoint_preview(pid: str):
        """Preview endpoint details (rich preview in a drawer)."""
        start_time = time.time()
        request_id = getattr(request, 'request_id', 'unknown')
        
        try:
            url = request.form.get("url") or ""
            method = (request.form.get("method") or "GET").upper()
            
            # Parse URL to get base and path
            if url.startswith(("http://", "https://")):
                from urllib.parse import urlparse
                parsed = urlparse(url)
                base_url = f"{parsed.scheme}://{parsed.netloc}"
                path = parsed.path or "/"
            else:
                base_url = ""
                path = url
            
            # Build absolute cURL (always absolute URL)
            absolute_curl = f"curl -X {method} '{url}'"
            
            # Build endpoint metadata
            ep = {
                "method": method,
                "base_url": base_url,
                "path": path,
                "requires_auth": False,  # TODO: Extract from spec if available
                "has_params": False,    # TODO: Extract from spec if available
                "has_body": method in ["POST", "PUT", "PATCH"],
                "curl": absolute_curl
            }
            
            # Build preview data from actual test runs
            preview = {
                "curl": absolute_curl,
                "headers": {},
                "body": None,
                "params": [],
                "example_response": None
            }
            
            # Build coverage data from dossier using canonical endpoint key
            from store import get_endpoint_runs_by_key
            key = endpoint_key(method, url, None)
            runs = get_endpoint_runs_by_key(pid, key, limit=5)
            
            # Try to get real test data from the most recent run
            if runs:
                latest_run = runs[0]
                artifact_path = latest_run.get("artifact")
                if artifact_path and os.path.exists(artifact_path):
                    try:
                        # Read the first line of the artifact file to get test data
                        with open(artifact_path, 'r') as f:
                            first_line = f.readline().strip()
                            if first_line:
                                test_data = json.loads(first_line)
                                
                                # Extract request data
                                req_data = test_data.get("request", "")
                                if req_data:
                                    # Parse HTTP request
                                    lines = req_data.split('\r\n')
                                    if len(lines) > 0:
                                        # First line is method/path
                                        first_line_parts = lines[0].split(' ')
                                        if len(first_line_parts) >= 2:
                                            preview["method"] = first_line_parts[0]
                                            preview["path"] = first_line_parts[1]
                                    
                                    # Extract headers
                                    headers = {}
                                    body_start = -1
                                    for i, line in enumerate(lines[1:], 1):
                                        if line.strip() == "":
                                            body_start = i + 1
                                            break
                                        if ':' in line:
                                            key, value = line.split(':', 1)
                                            headers[key.strip()] = value.strip()
                                    preview["headers"] = headers
                                    
                                    # Extract body if present
                                    if body_start > 0 and body_start < len(lines):
                                        body_lines = lines[body_start:]
                                        if body_lines:
                                            preview["body"] = '\r\n'.join(body_lines)
                                
                                # Extract response data
                                res_data = test_data.get("response", "")
                                if res_data:
                                    preview["example_response"] = res_data
                                    
                                # Update cURL with real data
                                if "curl-command" in test_data:
                                    preview["curl"] = test_data["curl-command"]
                                    absolute_curl = test_data["curl-command"]
                    except Exception as e:
                        logger.warning(f"Failed to parse artifact {artifact_path}: {e}")
                        pass
            
            # Calculate coverage from dossier data (Phase 4A enhancement)
            coverage = {
                "queued": "no",  # TODO: Check queue status
                "last_when": runs[0].get("finished_at") if runs else "—",
                "findings": runs[0].get("findings", 0) if runs else 0,
                "worst": runs[0].get("worst") if runs else None
            }
            
            # Log dossier read for debugging (Phase 4A)
            try:
                current_app.logger.info(f"DOSSIER_READ key=\"{key}\" count={len(runs)}")
            except Exception:
                pass
            
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(f"request_id={request_id} duration_ms={duration_ms} path=/p/{pid}/sitemap/endpoint-preview method=POST status=200")
            
            return render_template("drawer_endpoint_preview.html", 
                                 pid=pid, ep=ep, preview=preview, coverage=coverage)
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"request_id={request_id} duration_ms={duration_ms} path=/p/{pid}/sitemap/endpoint-preview method=POST status=500 error=\"{str(e)}\"")
            return f"Error loading endpoint preview: {e}", 500

    @bp.post("/p/<pid>/sitemap/endpoint-runs")
    def sitemap_runs_for_endpoint(pid: str):
        """Get runs for a specific endpoint from sitemap."""
        start_time = time.time()
        request_id = getattr(request, 'request_id', 'unknown')
        
        try:
            from store import get_endpoint_runs_by_key, _endpoint_dossier_path_by_key

            url = request.form.get("url") or ""
            method = (request.form.get("method") or "GET").upper()
            
            # Parse URL to get path
            if url.startswith(("http://", "https://")):
                from urllib.parse import urlparse
                parsed = urlparse(url)
                path = parsed.path or "/"
            else:
                path = url
            
            # Use canonical endpoint key for dossier lookup
            key = endpoint_key(method, url, None)
            fpath = _endpoint_dossier_path_by_key(pid, key)
            runs = get_endpoint_runs_by_key(pid, key, limit=15)
            
            # Normalize runs data for the template (newest first) with test details
            normalized_runs = []
            for run in runs:
                normalized_run = {
                    "run_id": run.get("run_id", ""),
                    "started_at": run.get("started_at", ""),
                    "finished_at": run.get("finished_at", ""),
                    "findings": run.get("findings", 0),
                    "worst": run.get("worst", ""),
                    "templates": run.get("templates", ""),
                    "templates_count": run.get("templates_count", ""),
                    "artifact": run.get("artifact", ""),
                    "test_details": None
                }
                
                # Try to load test details from artifact
                artifact_path = run.get("artifact")
                if artifact_path and os.path.exists(artifact_path):
                    try:
                        with open(artifact_path, 'r') as f:
                            lines = f.readlines()
                            if lines:
                                # Parse first test result for summary
                                first_test = json.loads(lines[0].strip())
                                normalized_run["test_details"] = {
                                    "template_name": first_test.get("info", {}).get("name", ""),
                                    "severity": first_test.get("info", {}).get("severity", ""),
                                    "matcher_name": first_test.get("matcher-name", ""),
                                    "matched_at": first_test.get("matched-at", ""),
                                    "curl_command": first_test.get("curl-command", ""),
                                    "total_tests": len(lines)
                                }
                    except Exception as e:
                        logger.warning(f"Failed to parse test details from {artifact_path}: {e}")
                        pass
                
                normalized_runs.append(normalized_run)
            
            # Log dossier read for debugging
            try:
                current_app.logger.info(f"DOSSIER_READ key=\"{key}\" file=\"{fpath}\" count={len(runs)}")
            except Exception:
                pass
            
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(f"request_id={request_id} duration_ms={duration_ms} path=/p/{pid}/sitemap/endpoint-runs method=POST status=200")
            
            return render_template("drawer_endpoint_runs.html", 
                                 pid=pid, method=method, path=path, url=url, runs=normalized_runs)
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"request_id={request_id} duration_ms={duration_ms} path=/p/{pid}/sitemap/endpoint-runs method=POST status=500 error=\"{str(e)}\"")
            return f"Error loading endpoint runs: {e}", 500

    @bp.route("/p/<pid>/sitemap/preview", methods=["POST"])
    def sitemap_preview_endpoint(pid: str):
        """Legacy alias that builds a rich preview from spec (kept for compatibility)."""
        try:
            from store import get_runtime
            from specs import RefResolver, op_seed, build_preview
            method = request.form.get("method")
            path = request.form.get("path")
            spec_id = request.form.get("spec_id")
            if not all([method, path, spec_id]):
                return "Missing required parameters", 400
            session, SPECS, QUEUE = get_runtime(pid)
            spec = SPECS.get(spec_id)
            if spec:
                for idx, op in enumerate(spec.get("ops", [])):
                    if op.get("method") == method and op.get("path") == path:
                        resolver = RefResolver(spec["spec"])
                        seed = op_seed(spec["url"], op["method"], op["path"])
                        pre = build_preview(
                            spec["spec"], spec["base_url"], op, resolver, override=None, seed=seed, fresh=False
                        )
                        pre_headers = dict(pre.get("headers") or {})
                        if session.get("bearer") and "Authorization" not in pre_headers:
                            pre_headers["Authorization"] = f"Bearer {session['bearer']}"
                        pre = dict(pre)
                        pre["headers"] = pre_headers
                        display_headers = dict(pre.get("headers") or {})
                        if session.get("bearer") and "Authorization" not in display_headers:
                            display_headers["Authorization"] = f"Bearer {session['bearer']}"
                        from core import _json_safe as __safe
                        pre_safe: Dict[str, Any] = dict(pre)
                        pre_safe["query"] = __safe(pre.get("query"))
                        pre_safe["headers"] = __safe(pre.get("headers"))
                        pre_safe["cookies"] = __safe(pre.get("cookies"))
                        pre_safe["json"] = __safe(pre.get("json"))
                        pre_safe["data"] = __safe(pre.get("data"))
                        return render_template(
                            "op_preview.html",
                            pre=pre_safe,
                            headers=__safe(display_headers),
                            files_map={},
                        )
            return "Operation not found", 404
        except Exception as e:
            return f"Error previewing endpoint: {str(e)}", 500


    @bp.get("/p/<pid>/runs")
    def runs_index_page(pid: str):
        """Simple runs list page; returns 200 with recent runs and logs RUNS_INDEX."""
        try:
            from store import list_runs, get_project_name
            from findings import count_findings_cached
            runs = list_runs(pid, limit=50)
            try:
                current_app.logger.info(f"RUNS_INDEX pid=\"{pid}\" count={len(runs or [])}")
            except Exception:
                pass
            return render_template("runs.html", pid=pid, runs=runs, project_name=get_project_name(pid), counts=count_findings_cached(pid))
        except Exception as e:
            return f"Error loading runs: {e}", 500

