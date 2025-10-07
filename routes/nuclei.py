from typing import Any, Dict
from flask import jsonify, request, render_template, current_app
import logging

logger = logging.getLogger(__name__)


def register_nuclei_routes(bp):
    """Register nuclei-related routes on the given blueprint."""

    @bp.get("/p/<pid>/nuclei/status")
    def nuclei_status(pid: str):
        from nuclei_integration import nuclei_integration
        try:
            status = nuclei_integration.check_nuclei_status()
            return {"success": True, "status": status}
        except Exception as e:
            return {"success": False, "error": str(e)}, 500

    @bp.post("/p/<pid>/nuclei/update-templates")
    def nuclei_update_templates(pid: str):
        from nuclei_integration import nuclei_integration
        try:
            success, message = nuclei_integration.update_templates()
            return {"success": success, "message": message}
        except Exception as e:
            return {"success": False, "error": str(e)}, 500

    @bp.get("/p/<pid>/nuclei/templates")
    def nuclei_templates(pid: str):
        from nuclei_integration import nuclei_integration
        try:
            category = request.args.get('category')
            source = request.args.get('source')
            all_flag = request.args.get('all') == '1'
            templates = nuclei_integration.nuclei.list_templates(
                category=category, source=source, all_templates=all_flag
            )
            return {"success": True, "templates": templates}
        except Exception as e:
            return {"success": False, "error": str(e)}, 500

    RUN_EXEC: Dict[str, Dict[str, Any]] = {}

    @bp.post("/p/<pid>/nuclei/scan")
    def nuclei_scan(pid: str):
        from nuclei_integration import nuclei_integration
        from store import save_run, get_runtime, update_endpoint_dossier_by_key
        from utils.endpoints import endpoint_key
        import time as _t, threading
        import os
        try:
            templates = request.form.getlist('templates') or None
            severity = request.form.getlist('severity') or None
            exclude_patterns = request.form.getlist('exclude_patterns') or None
            # Security quick pass: sanitize inputs
            try:
                import re as _re
                if severity:
                    allowed = {"critical","high","medium","low","info"}
                    severity = [s for s in severity if (s or "").lower() in allowed]
                if templates:
                    templates = [t for t in templates if _re.match(r"^[A-Za-z0-9._/\\-]+$", t or "")] or None
                if exclude_patterns:
                    exclude_patterns = [p for p in exclude_patterns if isinstance(p, str) and len(p) < 256] or None
            except Exception:
                pass
            run_id = request.form.get('run_id') or f"{_t.strftime('%Y-%m-%dT%H-%M-%SZ', _t.gmtime())}-{pid[:4].upper()}"

            # Single-executor guard
            state = RUN_EXEC.setdefault(run_id, {"lock": threading.Lock(), "started": False})
            with state["lock"]:
                if state["started"]:
                    logging.getLogger("exec").info("[EXEC] skipped(existing)", extra={"run_id": run_id})
                    return {"success": True, "already_running": True, "run_id": run_id}
                state["started"] = True
                logging.getLogger("exec").info("[EXEC] started", extra={"run_id": run_id})
            result = nuclei_integration.scan_project_endpoints(
                pid=pid, templates=templates, severity=severity, exclude_patterns=exclude_patterns, run_id=run_id
            )
            if result.get("success"):
                run_doc = {
                    "run_id": run_id,
                    "started_at": _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime()),
                    "finished_at": _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime()),
                    "results": [],
                    "stats": {
                        "findings": result.get("findings_count", 0),
                        "by_severity": result.get("severity_counts") or {},
                        "worst": result.get("worst_severity")
                    },
                    "artifact": result.get("artifact_path"),
                }
                try:
                    save_run(pid, run_doc)
                    # Build per-endpoint results for side panel from NDJSON artifact if present
                    try:
                        import json as _json
                        from urllib.parse import urlsplit as _us
                        from nuclei_integration import nuclei_integration as _ni
                        results: list[dict] = []
                        per_ep: dict[tuple[str,str,str], dict] = {}
                        art = run_doc.get("artifact")
                        if art and os.path.exists(art):
                            with open(art, "r", encoding="utf-8", errors="ignore") as af:
                                for line in af:
                                    line = (line or "").strip()
                                    if not line:
                                        continue
                                    try:
                                        raw = _json.loads(line)
                                    except Exception:
                                        continue
                                    conv = _ni.convert_nuclei_to_finding(raw, pid)
                                    url = conv.get("url") or conv.get("matched_at") or ""
                                    method = (conv.get("method") or "GET").upper()
                                    try:
                                        u = _us(url)
                                        base = f"{u.scheme}://{u.netloc}" if u.scheme and u.netloc else ""
                                        path = u.path or "/"
                                    except Exception:
                                        base = ""; path = "/"
                                    key = (base, method, path)
                                    ep = per_ep.setdefault(key, {"endpoint": {"base": base, "method": method, "path": path}, "nuclei": [], "detector": []})
                                    # Map to template shape expected by run_detail template
                                    templ = {
                                        "template_id": (conv.get("nuclei") or {}).get("template_id"),
                                        "info": {
                                            "name": conv.get("title") or (conv.get("nuclei") or {}).get("template_name") or "Unknown Template",
                                            "severity": conv.get("severity"),
                                            "description": conv.get("description") or "",
                                            "tags": conv.get("subcategory") or [],
                                            "classification": {
                                                "cwe_id": [conv.get("cwe")] if conv.get("cwe") else [],
                                                "owasp": [conv.get("owasp") or conv.get("owasp_api")] if (conv.get("owasp") or conv.get("owasp_api")) else []
                                            }
                                        },
                                        "severity": conv.get("severity"),
                                        "owasp": conv.get("owasp") or conv.get("owasp_api"),
                                        "cwe": conv.get("cwe"),
                                        "curl_command": conv.get("curl_command"),
                                        "request": conv.get("request"),
                                        "response": conv.get("response"),
                                        "matched_at": conv.get("matched_at") or conv.get("url"),
                                    }
                                    ep["nuclei"].append(templ)
                        if per_ep:
                            results = list(per_ep.values())
                            run_doc["results"] = results
                            # Persist updated run doc including results
                            save_run(pid, run_doc)
                    except Exception:
                        pass
                    # Update endpoint dossiers using canonical queue keys (preserving query)
                    try:
                        from store import get_runtime, _endpoint_dossier_path_by_key
                        session, SPECS, QUEUE = get_runtime(pid)
                        from specs import RefResolver, build_preview, op_seed
                        summary = {
                            "run_id": run_id,
                            "started_at": run_doc["started_at"],
                            "finished_at": run_doc["finished_at"],
                            "findings": run_doc["stats"].get("findings", 0),
                            "severity_counts": run_doc["stats"].get("by_severity", {}),
                            "worst": run_doc["stats"].get("worst") or "info",
                            "artifact": run_doc.get("artifact"),
                        }
                        for it in list(QUEUE or []):
                            s = SPECS.get(it.get("spec_id"))
                            if not s:
                                continue
                            try:
                                op = s.get("ops", [])[it.get("idx", -1)]
                            except Exception:
                                op = None
                            if not op:
                                continue
                            base = s.get("base_url") or s.get("url") or ""
                            method = (op.get("method") or "GET").upper()
                            path = op.get("path") or "/"
                            key = it.get("key")
                            if not key:
                                try:
                                    resolver = RefResolver(s.get("spec"))
                                    seed = op_seed(s.get("url"), op.get("method"), op.get("path"))
                                    pre = build_preview(s.get("spec"), s.get("base_url"), op, resolver, override=it.get("override"), seed=seed, fresh=False)
                                    full_url = pre.get("url") or (base + path)
                                    key = endpoint_key(method, full_url, None)
                                except Exception:
                                    key = endpoint_key(method, base, path)
                            update_endpoint_dossier_by_key(pid, key, summary)
                            try:
                                fpath = _endpoint_dossier_path_by_key(pid, key)
                                msg = f"DOSSIER_WRITE key=\"{key}\" run=\"{run_id}\" findings={summary.get('findings',0)} worst=\"{summary.get('worst')}\" file=\"{fpath}\""
                                logging.getLogger("dossier").info(msg)
                                try:
                                    current_app.logger.info(msg)
                                except Exception:
                                    pass
                            except Exception:
                                pass
                    except Exception:
                        pass
                except Exception:
                    pass
            # Echo a plan object for UI
            plan = {
                "run_id": run_id,
                "severity": severity or [],
                "templates_sample": (templates or [])[:3],
                "endpoints": result.get("endpoints_scanned", 0),
                "artifact_path": result.get("artifact_path"),
            }
            return {
                "success": result.get("success", False),
                "message": result.get("message"),
                "findings_count": result.get("findings_count", 0),
                "endpoints_scanned": result.get("endpoints_scanned", 0),
                "severity_counts": result.get("severity_counts"),
                "worst_severity": result.get("worst_severity"),
                "artifact_path": result.get("artifact_path"),
                "plan": plan,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}, 500

    @bp.get("/p/<pid>/nuclei/stream")
    def nuclei_stream(pid: str):
        """Server-Sent Events stream for live Nuclei scanning (Phase 4A enhanced)."""
        from flask import Response
        from nuclei_integration import nuclei_integration
        import time as _t
        import threading
        
        try:
            run_id = request.args.get('run_id') or f"{_t.strftime('%Y-%m-%dT%H-%M-%SZ', _t.gmtime())}-{pid[:4].upper()}"
            templates = request.args.getlist('templates') or None
            severity = request.args.getlist('severity') or None
            
            # Single-executor guard by run_id (Phase 4A)
            if not hasattr(nuclei_stream, '_active_runs'):
                nuclei_stream._active_runs = set()
            
            if run_id in nuclei_stream._active_runs:
                logger.info(f"[EXEC] ALREADY_RUNNING run_id={run_id} pid={pid}")
                return {"already_running": True, "run_id": run_id}, 409
            
            nuclei_stream._active_runs.add(run_id)
            logger.info(f"[EXEC] START run_id={run_id} pid={pid}")
            
            # Security quick pass: sanitize inputs
            try:
                import re as _re
                if severity:
                    allowed = {"critical","high","medium","low","info"}
                    severity = [s for s in severity if (s or "").lower() in allowed]
                if templates:
                    templates = [t for t in templates if _re.match(r"^[A-Za-z0-9._/\\-]+$", t or "")] or None
            except Exception:
                pass

            def generate():
                try:
                    # Get queue count for start event
                    from store import get_runtime
                    session, SPECS, QUEUE = get_runtime(pid)
                    total = len(QUEUE) if QUEUE else 0
                    
                    # Log queue de-dupe snapshot (Phase 4A)
                    if QUEUE:
                        from utils.endpoints import endpoint_key
                        keys = []
                        for item in QUEUE:
                            if item.get('spec_id') in SPECS:
                                spec = SPECS[item['spec_id']]
                                ops = spec.get('ops', [])
                                if item.get('idx') is not None and 0 <= item.get('idx') < len(ops):
                                    op = ops[item['idx']]
                                    if op:
                                        base_url = spec.get('base_url') or spec.get('url', '')
                                        path = op.get('path', '')
                                        full_url = f"{base_url.rstrip('/')}{path}" if base_url else path
                                        key = endpoint_key(op.get('method', 'GET'), full_url, None)
                                        keys.append(key)
                        logger.info(f"[EXEC] QUEUE_DEDUPE run_id={run_id} keys={keys}")
                    
                    # Emit start event with counts
                    yield f"event: start\ndata: {{\"run_id\": \"{run_id}\", \"endpoints\": {total}}}\n\n"
                    
                    # Periodic heartbeats every ~15s (Phase 4A enhanced)
                    heartbeat_count = 0
                    last_heartbeat = _t.time()
                    heartbeat_interval = 15  # seconds
                    
                    for chunk in nuclei_integration.scan_project_endpoints_stream(
                        pid=pid, templates=templates, severity=severity, exclude_patterns=None, run_id=run_id
                    ):
                        if not chunk.endswith("\n\n"):
                            chunk = chunk.rstrip("\n") + "\n\n"
                        yield chunk
                        
                        # Send heartbeat every ~15s
                        current_time = _t.time()
                        if current_time - last_heartbeat >= heartbeat_interval:
                            heartbeat_count += 1
                            yield f"event: heartbeat\ndata: {{\"timestamp\": {int(current_time)}, \"count\": {heartbeat_count}}}\n\n"
                            last_heartbeat = current_time
                            logger.info(f"[EXEC] HEARTBEAT run_id={run_id} count={heartbeat_count}")
                    
                    # Always emit done within bounded window
                    yield f"event: done\ndata: {{\"run_id\": \"{run_id}\"}}\n\n"
                    
                finally:
                    # Clean up active run
                    nuclei_stream._active_runs.discard(run_id)
                    logger.info(f"[EXEC] DONE run_id={run_id} pid={pid}")

            # Proper SSE headers (Phase 4A)
            resp = Response(generate(), mimetype='text/event-stream')
            resp.headers['Content-Type'] = 'text/event-stream'
            resp.headers['Cache-Control'] = 'no-store'
            resp.headers['Connection'] = 'keep-alive'
            resp.headers['X-Accel-Buffering'] = 'no'
            return resp
            
        except Exception as e:
            # Clean up on error
            if 'run_id' in locals():
                nuclei_stream._active_runs.discard(run_id)
            logger.error(f"[EXEC] ERROR run_id={run_id if 'run_id' in locals() else 'unknown'} pid={pid} error={str(e)}")
            return {"success": False, "error": str(e)}, 500

    @bp.get("/p/<pid>/active-testing")
    def active_testing_page(pid: str):
        """Active Testing page with comprehensive scan configuration."""
        try:
            from findings import count_findings_cached
            from store import get_project_name
            return render_template(
                "active_testing.html",
                pid=pid,
                project_name=get_project_name(pid),
                counts=count_findings_cached(pid),
                active_nav="active_testing",
            )
        except Exception as e:
            return f"Error loading active testing page: {str(e)}", 500

    @bp.get("/p/<pid>/queue/summary")
    def queue_summary(pid: str):
        """Get summary of endpoints in queue for active testing."""
        try:
            from store import get_runtime
            session, SPECS, QUEUE = get_runtime(pid)
            
            # If queue is empty, get all endpoints from specs
            if not QUEUE:
                methods = set()
                endpoint_count = 0
                
                # First try specs
                for spec_id, spec in SPECS.items():
                    operations = spec.get('ops', [])
                    endpoint_count += len(operations)
                    for op in operations:
                        methods.add(op.get('method', 'GET'))
                
                # If no specs, try endpoint dossiers
                if endpoint_count == 0:
                    try:
                        import os
                        import json
                        endpoints_dir = os.path.join('ui_projects', pid, 'endpoints')
                        if os.path.exists(endpoints_dir):
                            for filename in os.listdir(endpoints_dir):
                                if filename.endswith('.json'):
                                    try:
                                        with open(os.path.join(endpoints_dir, filename), 'r') as f:
                                            dossier = json.load(f)
                                        key = dossier.get('key', '')
                                        if key:
                                            # Parse key format: "METHOD URL"
                                            parts = key.split(' ', 1)
                                            if len(parts) == 2:
                                                method = parts[0]
                                                url = parts[1]
                                                endpoint_count += 1
                                                methods.add(method)
                                        else:
                                            # Try alternative format with separate method/path fields
                                            method = dossier.get('method', '')
                                            path = dossier.get('path', '')
                                            base = dossier.get('base', '')
                                            if method and path:
                                                endpoint_count += 1
                                                methods.add(method)
                                    except Exception:
                                        continue
                    except Exception:
                        pass
                
                return {
                    "success": True,
                    "endpoint_count": endpoint_count,
                    "methods": sorted(list(methods)),
                    "specs_count": len(SPECS),
                }
            
            # Original queue logic
            methods = set()
            for item in QUEUE:
                if item.get("spec_id") in SPECS:
                    spec = SPECS[item["spec_id"]]
                    ops = spec.get("ops", [])
                    if item.get("idx") < len(ops):
                        methods.add(ops[item["idx"]].get("method", "GET"))
            return {
                "success": True,
                "endpoint_count": len(QUEUE),
                "methods": sorted(list(methods)),
                "specs_count": len(SPECS),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}, 500

    @bp.get("/p/<pid>/nuclei/profiles")
    def nuclei_profiles(pid: str):
        from store import get_profiles
        try:
            profiles = get_profiles(pid)
            return jsonify({"success": True, "profiles": profiles})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.post("/p/<pid>/nuclei/profiles")
    def nuclei_profiles_save(pid: str):
        from store import save_profile
        try:
            data = request.get_json()
            name = data.get("name")
            templates = data.get("templates", [])
            if not name:
                return jsonify({"success": False, "error": "Profile name required"}), 400
            save_profile(pid, name, templates)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.get("/p/<pid>/nuclei/profiles/<name>")
    def nuclei_profile_load(pid: str, name: str):
        from store import load_profile
        try:
            templates = load_profile(pid, name)
            return jsonify({"success": True, "templates": templates})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.delete("/p/<pid>/nuclei/profiles/<name>")
    def nuclei_profile_delete(pid: str, name: str):
        from store import delete_profile
        try:
            delete_profile(pid, name)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500


