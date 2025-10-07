from typing import Any, Dict, List, Optional
from flask import render_template, request, jsonify, redirect, url_for


def register_findings_routes(bp):
    """Register findings-related routes on the given blueprint."""

    @bp.get("/p/<pid>/findings")
    def findings_page(pid: str):
        """Enhanced findings page with flexible grouping system."""
        from findings import get_findings, build_groups
        from store import get_project_name

        group_by = request.args.get('group', 'rule')
        if group_by not in ['rule', 'endpoint', 'owasp', 'cwe']:
            group_by = 'rule'

        rows = get_findings(pid) or []

        def _norm(i: int, f: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "idx": i,
                "severity": (f.get("severity") or "info").lower(),
                "method": (f.get("method") or "GET").upper(),
                "path": f.get("path") or f.get("url") or "",
                "url": f.get("url") or "",
                "title": f.get("title") or f.get("detector_id") or "Finding",
                "subcategory": f.get("subcategory") or "",
                "detector_id": f.get("detector_id") or "",
                "cwe": f.get("cwe") or "",
                "confidence": int(f.get("confidence") or 0),
                "owasp": f.get("owasp") or "",
                "owasp_api": f.get("owasp_api") or "",
                "status": f.get("status", "open"),
            }

        normalized_findings = [_norm(i, f) for i, f in enumerate(rows)]
        groups_sorted = build_groups(normalized_findings, mode=group_by)
        counts = {
            "total": len(normalized_findings),
            "critical": sum(1 for f in normalized_findings if f.get("severity") == "critical"),
            "high": sum(1 for f in normalized_findings if f.get("severity") == "high"),
            "medium": sum(1 for f in normalized_findings if f.get("severity") == "medium"),
            "low": sum(1 for f in normalized_findings if f.get("severity") == "low"),
            "info": sum(1 for f in normalized_findings if f.get("severity") == "info"),
        }

        return render_template(
            "findings_clean.html",
            pid=pid,
            project_name=get_project_name(pid),
            groups_sorted=groups_sorted,
            counts=counts,
            group_by=group_by,
        )

    @bp.post("/p/<pid>/findings/clear")
    def findings_clear(pid: str):
        # Guard: do not touch templates directory; only clear stored findings
        from findings import clear_findings
        clear_findings(pid)
        return redirect(url_for("web.findings_page", pid=pid))

    @bp.post("/p/<pid>/findings/triage-group")
    def triage_group(pid: str):
        """Bulk triage all findings in a group (best-effort)."""
        try:
            data = request.get_json()
            group_key = data.get('group_key') if data else None
            status = data.get('status') if data else None
            if not group_key or not status:
                return jsonify({"success": False, "error": "Missing group_key or status"}), 400
            from findings import get_findings
            rows = get_findings(pid) or []
            updated_count = 0
            for finding in rows:
                if (finding.get('detector_id') and group_key.endswith(finding.get('detector_id'))) or \
                   (finding.get('title') and group_key.endswith((finding.get('title') or '').lower())):
                    finding['status'] = status
                    updated_count += 1
            if updated_count > 0:
                from findings import _write_findings
                _write_findings(pid, rows)
            return jsonify({"success": True, "message": f"Updated {updated_count} findings to {status}", "updated_count": updated_count})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.get("/p/<pid>/findings/export-group")
    def export_group(pid: str):
        try:
            group_key = request.args.get('key')
            if not group_key:
                return jsonify({"error": "Missing group key"}), 400
            from findings import get_findings
            rows = get_findings(pid) or []
            group_findings: List[Dict[str, Any]] = []
            for finding in rows:
                if (finding.get('detector_id') and group_key.endswith(finding.get('detector_id'))) or \
                   (finding.get('title') and group_key.endswith((finding.get('title') or '').lower())):
                    group_findings.append(finding)
            return jsonify({"group_key": group_key, "findings": group_findings, "count": len(group_findings)})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.post("/p/<pid>/findings/queue-group")
    def queue_group(pid: str):
        try:
            data = request.get_json()
            group_key = data.get('group_key') if data else None
            if not group_key:
                return jsonify({"success": False, "error": "Missing group_key"}), 400
            from findings import get_findings
            rows = get_findings(pid) or []
            endpoints = set()
            for finding in rows:
                if (finding.get('detector_id') and group_key.endswith(finding.get('detector_id'))) or \
                   (finding.get('title') and group_key.endswith((finding.get('title') or '').lower())):
                    if finding.get('url'):
                        endpoints.add(finding['url'])
            return jsonify({"success": True, "message": f"Added {len(endpoints)} endpoints to Test Queue", "added_count": len(endpoints)})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.get("/p/<pid>/findings/<int:idx>")
    def finding_detail(pid: str, idx: int):
        """Get individual finding details for the side panel (rich)."""
        try:
            from findings import get_findings, get_finding_explanation
            rows = get_findings(pid) or []
            if idx < 0 or idx >= len(rows):
                return render_template("finding_detail.html", error="Not found"), 404
            f = rows[idx]

            method = (f.get("method") or "GET").upper()
            url = f.get("url") or f.get("path") or ""
            title = f.get("title") or f.get("detector_id") or "Finding"

            toks: List[str] = []
            for k in ("match", "param"):
                v = f.get(k)
                if isinstance(v, str) and v.strip():
                    toks.append(v.strip())
            res_headers = ((f.get("res") or {}).get("headers") or {}) or {}
            det_id_for_hl = (f.get("detector_id") or f.get("detector") or "").lower()
            try:
                if det_id_for_hl == "server_tech_disclosure":
                    for hk in ("Server", "X-Powered-By"):
                        hv = res_headers.get(hk) or res_headers.get(hk.lower())
                        if isinstance(hv, str) and len(hv) >= 2:
                            toks.append(hv)
                elif det_id_for_hl == "cors_star_with_credentials":
                    for hk in ("Access-Control-Allow-Origin", "Access-Control-Allow-Credentials"):
                        hv = res_headers.get(hk) or res_headers.get(hk.lower())
                        if isinstance(hv, str) and len(hv) >= 1:
                            toks.append(hv)
            except Exception:
                pass
            seen = set(); uniq: List[str] = []
            for t in toks:
                tl = t.lower()
                if tl in seen: continue
                uniq.append(t); seen.add(tl)
            toks = uniq

            import json as _json
            req = f.get("req") or {}
            res = f.get("res") or {}
            req_headers = dict(req.get("headers") or {})
            if "Authorization" in req_headers:
                req_headers["Authorization"] = "***"
            req_headers_json = _json.dumps(req_headers, indent=2, ensure_ascii=False)
            res_headers_json = _json.dumps(res.get("headers") or {}, indent=2, ensure_ascii=False)
            if req.get("json") is not None:
                req_body_str = _json.dumps(req.get("json"), indent=2, ensure_ascii=False)
            elif req.get("data") is not None:
                try:
                    req_body_str = _json.dumps(req.get("data"), indent=2, ensure_ascii=False)
                except Exception:
                    req_body_str = str(req.get("data"))
            else:
                req_body_str = ""
            res_body_str = str(res.get("body") or "")

            from markupsafe import escape
            def _hl(s: str, needles: List[str]) -> str:
                try:
                    import re as _re
                    out = s or ""
                    for t in needles:
                        if not t: continue
                        if len(t) < 3 or t.isdigit():
                            continue
                        pat = _re.compile(_re.escape(t), _re.IGNORECASE)
                        out = pat.sub(lambda m: "<mark>" + escape(m.group(0)) + "</mark>", out)
                    return out
                except Exception:
                    return s or ""

            req_headers_json_hl = escape(_hl(req_headers_json, toks))
            res_headers_json_hl = escape(_hl(res_headers_json, toks))
            req_body_json_hl = escape(_hl(req_body_str, toks))
            res_body_hl = escape(_hl(res_body_str, toks))

            explain_html = get_finding_explanation(f)

            f_escaped: Dict[str, Any] = {}
            for k, v in f.items():
                f_escaped[k] = escape(v) if isinstance(v, str) else v

            try:
                req_for_curl = f.get("req") or {}
                curl_lines = []
                method_for_curl = (req_for_curl.get("method") or f.get("method") or "").upper()
                url_for_curl = req_for_curl.get("url") or f.get("url") or ""
                if method_for_curl and url_for_curl:
                    curl_lines.append(f"curl -X {method_for_curl} '{url_for_curl}'")
                hdrs_for_curl = req_for_curl.get("headers") or {}
                if isinstance(hdrs_for_curl, dict):
                    for hk, hv in hdrs_for_curl.items():
                        try:
                            if str(hk).lower() == "authorization":
                                hv = "***"
                            curl_lines.append(f"  -H '{hk}: {hv}'")
                        except Exception:
                            continue
                if req_for_curl.get("json") is not None:
                    curl_lines.append("  -d '" + _json.dumps(req_for_curl.get("json"), ensure_ascii=False) + "'")
                elif req_for_curl.get("data") is not None:
                    curl_lines.append("  -d '" + str(req_for_curl.get("data")) + "'")
                panel_curl = " \\\n+".join(curl_lines)
            except Exception:
                panel_curl = ""

            from store import get_project_name
            return render_template(
                "finding_detail.html",
                pid=pid,
                project_name=get_project_name(pid),
                f=f_escaped,
                req_headers_json_hl=req_headers_json_hl,
                req_body_json_hl=req_body_json_hl,
                res_headers_json_hl=res_headers_json_hl,
                res_body_hl=res_body_hl,
                explain_html=explain_html,
                panel_curl=panel_curl,
            )
        except Exception as e:
            return f"Error loading finding: {str(e)}", 500

    @bp.post("/p/<pid>/findings/view")
    def finding_view(pid: str):
        from findings import get_finding_by_index, get_finding_explanation
        try:
            try:
                idx = int(request.form.get("idx") or -1)
            except Exception:
                idx = -1
            f = get_finding_by_index(pid, idx)
            if not f:
                return redirect(url_for("web.findings_page", pid=pid))
            return findings_detail_render(pid, f)
        except Exception as e:
            return f"Error loading finding view: {str(e)}", 500

    # Helper used by finding_view to render the rich template
    def findings_detail_render(pid: str, f: Dict[str, Any]):
        # Reuse the logic by calling the GET handler with an injected list index if needed.
        # Here we keep it simple and redirect to findings_page for now.
        return redirect(url_for("web.findings_page", pid=pid))

    @bp.post("/p/<pid>/findings/triage")
    def triage_finding(pid: str):
        """Update finding status for triaging."""
        try:
            finding_id = request.form.get('finding_id')
            status = request.form.get('status')
            notes = request.form.get('notes', '')
            if not finding_id or not status:
                return {"success": False, "error": "Missing finding_id or status"}, 400
            from findings import get_findings
            rows = get_findings(pid)
            updated = False
            import time as _time
            for finding in rows:
                if finding.get('id') == finding_id or str(finding.get('created_at', '')) == finding_id:
                    finding['status'] = status
                    finding['triage_notes'] = notes
                    finding['triaged_at'] = int(_time.time())
                    finding['triaged_by'] = 'user'
                    updated = True
                    break
            if not updated:
                return {"success": False, "error": "Finding not found"}, 404
            from findings import _write_findings
            _write_findings(pid, rows)
            try:
                from cache import invalidate_cache
                invalidate_cache(f"count_findings_cached:('{pid}',)")
            except Exception:
                pass
            return {"success": True, "message": f"Finding status updated to {status}", "status": status}
        except Exception as e:
            return {"success": False, "error": str(e)}, 500

    @bp.get("/p/<pid>/findings/triage-stats")
    def triage_stats(pid: str):
        try:
            from findings import get_findings
            rows = get_findings(pid)
            stats = {
                'total': len(rows),
                'open': 0,
                'accepted_risk': 0,
                'false_positive': 0,
                'fixed': 0,
                'untriaged': 0,
            }
            for finding in rows:
                status = finding.get('status', 'open')
                if status in stats:
                    stats[status] += 1
                else:
                    stats['untriaged'] += 1
            return {"success": True, "stats": stats}
        except Exception as e:
            return {"success": False, "error": str(e)}, 500


