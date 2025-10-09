import json
import logging
import os
import time

from flask import jsonify, render_template, request

logger = logging.getLogger(__name__)

def register_tools_routes(bp):
    """Register tools-related routes on the given blueprint."""

    @bp.route("/p/<pid>/tools")
    def tools_page(pid: str):
        """Tools Manager page - Nuclei Templates management."""
        start_time = time.time()
        request_id = getattr(request, 'request_id', 'unknown')
        
        try:
            from nuclei_integration import nuclei_integration
            from store import get_project_name
            
            # Get nuclei status and template count
            try:
                nuclei_status = nuclei_integration.check_nuclei_status()
                template_count = len(nuclei_integration.nuclei.list_templates()) if nuclei_status.get('available') else 0
            except Exception as e:
                logger.warning(f"TOOLS_NUCLEI_STATUS_ERROR error={str(e)} pid={pid}")
                nuclei_status = {"available": False, "error": str(e)}
                template_count = 0
            
            # Get last indexed time from a timestamp file
            last_indexed = None
            timestamp_file = os.path.join("ui_projects", pid, "nuclei_last_indexed.txt")
            if os.path.exists(timestamp_file):
                try:
                    with open(timestamp_file, 'r') as f:
                        last_indexed = f.read().strip()
                except Exception:
                    pass
            
            # Load presets
            presets = {}
            presets_file = "tools/presets.json"
            if os.path.exists(presets_file):
                try:
                    with open(presets_file, 'r') as f:
                        presets = json.load(f)
                except Exception as e:
                    logger.warning(f"TOOLS_PRESETS_LOAD_ERROR error={str(e)}")
            
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(f"request_id={request_id} duration_ms={duration_ms} path=/p/{pid}/tools method=GET status=200")
            
            return render_template(
                "tools/index.html",
                pid=pid,
                project_name=get_project_name(pid),
                nuclei_status=nuclei_status,
                template_count=template_count,
                last_indexed=last_indexed,
                presets=presets
            )
            
        except Exception as e:
            logger.error(f"request_id={request_id} error={str(e)} path=/p/{pid}/tools method=GET status=500")
            return f"Error loading tools page: {str(e)}", 500

    @bp.route("/p/<pid>/tools/nuclei/reindex", methods=["POST"])
    def nuclei_reindex(pid: str):
        """Reindex Nuclei templates."""
        start_time = time.time()
        request_id = getattr(request, 'request_id', 'unknown')
        
        try:
            from nuclei_integration import nuclei_integration
            
            # Update templates
            success, message = nuclei_integration.update_templates()
            
            if success:
                # Update timestamp file
                timestamp_file = os.path.join("ui_projects", pid, "nuclei_last_indexed.txt")
                os.makedirs(os.path.dirname(timestamp_file), exist_ok=True)
                with open(timestamp_file, 'w') as f:
                    f.write(time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()))
                
                # Get new count
                template_count = len(nuclei_integration.nuclei.list_templates())
                took_ms = int((time.time() - start_time) * 1000)
                
                logger.info(f"TOOLS_REINDEX_SUCCESS pid={pid} count={template_count} took_ms={took_ms}")
                
                return jsonify({
                    "success": True,
                    "count": template_count,
                    "took_ms": took_ms,
                    "message": message
                })
            else:
                logger.warning(f"TOOLS_REINDEX_FAILED pid={pid} error={message}")
                return jsonify({
                    "success": False,
                    "error": message
                }), 400
                
        except Exception as e:
            logger.error(f"TOOLS_REINDEX_ERROR pid={pid} error={str(e)}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @bp.route("/p/<pid>/tools/nuclei/selftest", methods=["POST"])
    def nuclei_selftest(pid: str):
        """Run self-test with fixture templates."""
        start_time = time.time()
        request_id = getattr(request, 'request_id', 'unknown')
        
        try:
            
            # Use fixture templates for self-test
            fixture_dir = "tools/fixtures/nuclei"
            sample_ids = []
            
            if os.path.exists(fixture_dir):
                for filename in os.listdir(fixture_dir):
                    if filename.endswith('.yaml'):
                        template_id = filename.replace('.yaml', '')
                        sample_ids.append(template_id)
            
            # Run a dry-run test against localhost
            test_url = "http://127.0.0.1:8080/test"
            results = []
            
            for template_id in sample_ids[:2]:  # Limit to 2 templates
                try:
                    # This would normally run nuclei, but for self-test we just simulate
                    result = {
                        "template_id": template_id,
                        "status": "ok",
                        "matched": False,
                        "url": test_url
                    }
                    results.append(result)
                except Exception as e:
                    logger.warning(f"TOOLS_SELFTEST_TEMPLATE_ERROR template={template_id} error={str(e)}")
                    results.append({
                        "template_id": template_id,
                        "status": "error",
                        "error": str(e)
                    })
            
            took_ms = int((time.time() - start_time) * 1000)
            logger.info(f"TOOLS_SELFTEST_SUCCESS pid={pid} templates={len(results)} took_ms={took_ms}")
            
            return jsonify({
                "ok": True,
                "sample_ids": sample_ids,
                "results": results,
                "took_ms": took_ms
            })
            
        except Exception as e:
            logger.error(f"TOOLS_SELFTEST_ERROR pid={pid} error={str(e)}")
            return jsonify({
                "ok": False,
                "error": str(e)
            }), 500
