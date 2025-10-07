"""
Nuclei Integration Layer (Phase 5)
Converts Nuclei results to our finding model and integrates with the existing system.
"""

import time, os, json, logging
from typing import Dict, List, Any, Optional, Tuple, Union
from nuclei_wrapper import NucleiWrapper, NucleiResult, NucleiStatus
from findings import append_findings, get_findings
from store import get_runtime, persist_from_runtime, ensure_dirs, get_project_dir
from specs import RefResolver, build_preview, op_seed

logger = logging.getLogger(__name__)

class NucleiIntegration:
    # CVE/CWE enrichment mapping (Phase 4A)
    _CVE_CWE_MAP = {
        # Common nuclei templates with known CVEs
        "http-methods": {"cve_id": None, "cwe": "CWE-200", "component": "information_disclosure", "remediation": "Disable unnecessary HTTP methods"},
        "sqli-auth": {"cve_id": None, "cwe": "CWE-89", "component": "database", "remediation": "Use parameterized queries"},
        "xss": {"cve_id": None, "cwe": "CWE-79", "component": "web_application", "remediation": "Implement proper input validation and output encoding"},
        "jwt-secrets": {"cve_id": None, "cwe": "CWE-327", "component": "authentication", "remediation": "Use strong, unpredictable secrets for JWT signing"},
        "oauth-bypass": {"cve_id": None, "cwe": "CWE-287", "component": "authentication", "remediation": "Implement proper OAuth flow validation"},
        "rce": {"cve_id": None, "cwe": "CWE-78", "component": "command_execution", "remediation": "Avoid command injection, use safe APIs"},
        "ssrf": {"cve_id": None, "cwe": "CWE-918", "component": "network", "remediation": "Validate and restrict external network access"},
        "xxe": {"cve_id": None, "cwe": "CWE-611", "component": "xml_parser", "remediation": "Disable XML external entity processing"},
        "path-traversal": {"cve_id": None, "cwe": "CWE-22", "component": "file_system", "remediation": "Validate and sanitize file paths"},
        "ldap-injection": {"cve_id": None, "cwe": "CWE-90", "component": "ldap", "remediation": "Use parameterized LDAP queries"},
        "nosql-injection": {"cve_id": None, "cwe": "CWE-943", "component": "database", "remediation": "Use parameterized NoSQL queries"},
    }
    
    def _enrich_finding_with_cve_cwe(self, finding: Dict[str, Any], template_id: str) -> Dict[str, Any]:
        """Enrich finding with CVE/CWE data based on template ID."""
        enrichment = self._CVE_CWE_MAP.get(template_id)
        if enrichment:
            # Only set cve_id if it's a valid CVE
            cve_id = enrichment.get("cve_id")
            if cve_id and isinstance(cve_id, str) and self._is_valid_cve(cve_id):
                finding["cve_id"] = cve_id
            else:
                # Don't set cve_id if it's invalid
                finding.pop("cve_id", None)
            
            finding["cwe"] = finding.get("cwe") or enrichment.get("cwe")
            finding["affected_component"] = enrichment.get("component")
            finding["suggested_remediation"] = finding.get("suggested_remediation") or enrichment.get("remediation")
            
            # Add evidence anchors if we have request/response data
            anchors = []
            if finding.get("req", {}).get("data"):
                anchors.append("request_body")
            if finding.get("res", {}).get("body"):
                anchors.append("response_body")
            if finding.get("url"):
                anchors.append("url")
            finding["evidence_anchors"] = anchors
        
        return finding
    
    def _is_valid_cve(self, cve_id: str) -> bool:
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

    def _build_endpoints_from_specs(self, pid: str) -> List[Dict[str, Any]]:
        """Build all endpoints from project specifications and endpoint dossiers."""
        endpoints: List[Dict[str, Any]] = []
        session, SPECS, QUEUE = get_runtime(pid)
        
        # First, try to get endpoints from specs
        for spec_id, spec in SPECS.items():
            base_url = spec.get('base_url') or spec.get('url', '')
            operations = spec.get('ops', [])
            
            for idx, op in enumerate(operations):
                method = op.get('method', 'GET')
                path = op.get('path', '')
                
                # Build full URL
                if base_url:
                    full_url = f"{base_url.rstrip('/')}{path}" if path.startswith('/') else f"{base_url.rstrip('/')}/{path}"
                else:
                    full_url = path
                
                endpoints.append({
                    'url': full_url,
                    'method': method,
                    'headers': {},
                    'body': None,
                    'spec_id': spec_id,
                    'op_index': idx
                })
        
        # If no specs, try to get endpoints from endpoint dossiers
        if not endpoints:
            try:
                import os
                import json
                from utils.endpoints import endpoint_key
                
                endpoints_dir = os.path.join('ui_projects', pid, 'endpoints')
                if os.path.exists(endpoints_dir):
                    for filename in os.listdir(endpoints_dir):
                        if filename.endswith('.json'):
                            try:
                                with open(os.path.join(endpoints_dir, filename), 'r') as f:
                                    dossier = json.load(f)
                                
                                # Extract endpoint info from dossier
                                key = dossier.get('key', '')
                                if key:
                                    # Parse key format: "METHOD URL"
                                    parts = key.split(' ', 1)
                                    if len(parts) == 2:
                                        method = parts[0]
                                        url = parts[1]
                                        endpoints.append({
                                            'url': url,
                                            'method': method,
                                            'headers': {},
                                            'body': None,
                                            'spec_id': 'dossier',
                                            'op_index': 0
                                        })
                                else:
                                    # Try alternative format with separate method/path fields
                                    method = dossier.get('method', '')
                                    path = dossier.get('path', '')
                                    base = dossier.get('base', '')
                                    if method and path:
                                        url = f"{base.rstrip('/')}{path}" if base else path
                                        endpoints.append({
                                            'url': url,
                                            'method': method,
                                            'headers': {},
                                            'body': None,
                                            'spec_id': 'dossier',
                                            'op_index': 0
                                        })
                            except Exception:
                                continue
            except Exception:
                pass
        
        return endpoints

    def _build_endpoints_from_queue(self, pid: str) -> List[Dict[str, Any]]:
        """Build fully-expanded endpoints from the Test Queue (shared by POST and SSE)."""
        endpoints: List[Dict[str, Any]] = []
        session, SPECS, QUEUE = get_runtime(pid)
        
        # If queue is empty, fall back to all endpoints from specs
        if not QUEUE:
            return self._build_endpoints_from_specs(pid)
        
        for i, item in enumerate(QUEUE or []):
            try:
                if item.get('spec_id') not in SPECS:
                    continue
                spec = SPECS[item['spec_id']]
                ops = spec.get('ops', [])
                if item.get('idx') is not None and isinstance(item.get('idx'), int) and 0 <= item.get('idx') < len(ops):
                    op = ops[item['idx']]
                    if op is None:
                        continue
                    try:
                        resolver = RefResolver(spec.get('raw', {}))
                        seed = op_seed(op)
                        preview = build_preview(resolver, op, seed=seed, overrides=item.get('override') or {})
                        full_url = preview.get('url')
                        if not full_url:
                            base_url = spec.get('base_url') or spec.get('url', '')
                            full_url = f"{base_url.rstrip('/')}{op.get('path', '')}" if base_url else op.get('path', '')
                        headers = preview.get('headers') or {}
                        body = None
                        if preview.get('body') is not None:
                            body = preview.get('body') if isinstance(preview.get('body'), str) else json.dumps(preview.get('body'))
                        elif preview.get('data') is not None:
                            body = preview.get('data') if isinstance(preview.get('data'), str) else json.dumps(preview.get('data'))
                        endpoints.append({
                            'url': full_url,
                            'method': (preview.get('method') or op.get('method', 'GET')),
                            'headers': headers,
                            'body': body,
                            'spec_id': item['spec_id'],
                            'op_index': item['idx']
                        })
                    except Exception:
                        # Fallback to naive concat
                        base_url = spec.get('base_url') or spec.get('url', '')
                        full_url = f"{base_url.rstrip('/')}{op.get('path', '')}" if base_url else op.get('path', '')
                        endpoints.append({
                            'url': full_url,
                            'method': op.get('method', 'GET'),
                            'headers': {},
                            'body': None,
                            'spec_id': item['spec_id'],
                            'op_index': item['idx']
                        })
                else:
                    continue
            except Exception:
                continue
        return endpoints
    """Integration layer between Nuclei and our finding system."""
    
    def __init__(self):
        self.nuclei = NucleiWrapper()
    
    def to_internal(self, nuclei_item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Nuclei result to internal finding format with proper CWE/OWASP mapping."""
        # Extract basic info
        template_id = nuclei_item.get('template-id', 'unknown')
        template_info = nuclei_item.get('info', {})
        template_name = template_info.get('name', template_id)
        severity = self._map_severity(template_info.get('severity', 'info'))
        classification = template_info.get('classification') or {}
        
        # Extract URL and path
        matched_url = nuclei_item.get('matched-at', '')
        parsed_url = self._parse_url(matched_url)
        path = parsed_url.get('path', '/')
        
        # Map to CWE/OWASP
        # Prefer classification-provided CWE/OWASP if present
        cwe = None
        try:
            cwe_val = classification.get('cwe')
            if isinstance(cwe_val, list) and cwe_val:
                cwe = f"CWE-{cwe_val[0]}" if not str(cwe_val[0]).upper().startswith('CWE-') else str(cwe_val[0]).upper()
            elif isinstance(cwe_val, (str, int)):
                cwe = f"CWE-{cwe_val}" if not str(cwe_val).upper().startswith('CWE-') else str(cwe_val).upper()
        except Exception:
            cwe = None

        if not cwe:
            cwe = self._extract_cwe(nuclei_item)

        owasp = None
        try:
            owasp_val = classification.get('owasp')
            if isinstance(owasp_val, list) and owasp_val:
                owasp = str(owasp_val[0])
            elif isinstance(owasp_val, str):
                owasp = owasp_val
        except Exception:
            owasp = None

        if not owasp:
            owasp = self._map_cwe_to_owasp(cwe) or self._map_template_to_owasp(template_id, template_info)
        
        # Clean up OWASP value to match schema pattern (A##:####)
        if owasp:
            import re
            match = re.match(r'^(A\d{2}:\d{4})', owasp)
            if match:
                owasp = match.group(1)
        
        # Determine if it's web or API specific (best-effort)
        is_web = self._is_web_vulnerability(template_info)
        is_api = self._is_api_vulnerability(template_info) or (str(owasp or '').strip().upper().startswith('API'))
        
        # Build evidence (prefer extracted-results as concrete proof)
        evidence = self._build_evidence(nuclei_item)

        # Parse raw request/response into structured objects like our detectors use
        req_obj = self._parse_raw_http_request(nuclei_item.get('request'))
        res_obj = self._parse_raw_http_response(nuclei_item.get('response'))
        if res_obj and res_obj.get('status') and not nuclei_item.get('status-code'):
            nuclei_item['status-code'] = res_obj.get('status')
        
        out = {
            "title": template_name,
            "severity": severity,
            "method": self._extract_method(nuclei_item),
            "path": path,
            "url": matched_url,
            # Set OWASP/API directly based on classification/tags
            "owasp": None if is_api else owasp,
            "owasp_api": owasp if is_api else None,
            "subcategory": template_info.get('tags', [])[0] if template_info.get('tags') else None,
            "detector_id": f"nuclei.{template_id}",
            "confidence": self._score_confidence(nuclei_item),
            "evidence": evidence,
            "status": "open",  # For triaging
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source": "nuclei",
            "description": template_info.get('description', ''),
            "remediation": template_info.get('remediation'),
            "reference": template_info.get('reference', []),
            "author": template_info.get('author', []),
            "matched_at": matched_url,
            "request": nuclei_item.get('request', ''),
            "response": nuclei_item.get('response', ''),
            "curl_command": nuclei_item.get('curl-command', ''),
            "status_code": nuclei_item.get('status-code'),
            # Structured HTTP context for UI parity with detectors
            "req": req_obj or {},
            "res": res_obj or {},
        }
        
        # Only add cwe if it's not None
        if cwe:
            out["cwe"] = cwe
        # Attach vendor block with raw, classification, matcher, path if present
        vendor_block = {
            "template_id": template_id,
            "template_name": template_name,
            "severity_raw": template_info.get('severity'),
            "confidence_raw": template_info.get('confidence'),
            "tags": template_info.get('tags', []),
            "classification": template_info.get('classification') or {},
            "matcher_name": nuclei_item.get('matcher-name'),
            "extracted_results": nuclei_item.get('extracted-results'),
            "matched_at": matched_url,
            "status_code": nuclei_item.get('status-code'),
        }
        # Promote matcher_name into subcategory if present
        if vendor_block.get("matcher_name") and not out.get("subcategory"):
            out["subcategory"] = vendor_block.get("matcher_name")
        # Carry any template path if provided by wrapper via passthrough
        if nuclei_item.get('_template_path'):
            vendor_block["template_path"] = nuclei_item.get('_template_path')
        if nuclei_item.get('_raw'):
            vendor_block["raw"] = nuclei_item.get('_raw')
        # Origin endpoint context
        if nuclei_item.get('_origin_url'):
            origin_url = nuclei_item.get('_origin_url')
            out["url"] = origin_url
            # Also recompute path from origin url for proper grouping/signature
            try:
                parsed = self._parse_url(origin_url)
                if parsed.get('path'):
                    out["path"] = parsed.get('path')
            except Exception:
                pass
        if nuclei_item.get('_origin_method'):
            out["method"] = nuclei_item.get('_origin_method')
        out["nuclei"] = vendor_block
        
        # Enrich with CVE/CWE data (Phase 4A)
        out = self._enrich_finding_with_cve_cwe(out, template_id)
        
        return out
    
    def convert_nuclei_to_finding(self, result: Union[Dict[str, Any], NucleiResult], pid: str) -> Dict[str, Any]:
        """Convert a Nuclei result (dict or NucleiResult) to our finding format."""
        if isinstance(result, NucleiResult):
            raw = getattr(result, 'raw', {}) or {}
            nuclei_item = {
                'template-id': result.template_id,
                'info': {**(result.info or {}), 'name': result.template_name, 'severity': result.severity},
                'matched-at': result.matched_at or result.url,
                'request': result.request or '',
                'response': result.response or '',
                'curl-command': result.curl_command or '',
                'status-code': result.status_code if result.status_code is not None else raw.get('status-code'),
                # Prefer extracted-results/matcher-name from raw nuclei JSON if present
                'extracted-results': raw.get('extracted-results'),
                'matcher-name': raw.get('matcher-name'),
                # pass-throughs for vendor block
                '_template_path': getattr(result, 'template_path', None),
                '_raw': getattr(result, 'raw', None),
                '_origin_url': getattr(result, 'origin_url', None),
                '_origin_method': getattr(result, 'origin_method', None),
            }
            return self.to_internal(nuclei_item)
        return self.to_internal(result)
    
    def scan_project_endpoints(self, pid: str, 
                             templates: Optional[List[str]] = None,
                             severity: Optional[List[str]] = None,
                             exclude_patterns: Optional[List[str]] = None,
                             run_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Scan all endpoints in a project's queue with Nuclei.
        
        Args:
            pid: Project ID
            templates: Specific Nuclei template IDs to use
            severity: Severity levels to include
            exclude_patterns: Patterns to exclude from scanning
            
        Returns:
            Dictionary with scan results and statistics
        """
        try:
            # Get project runtime
            print(f"Getting runtime for project {pid}")
            session, SPECS, QUEUE = get_runtime(pid)
            print(f"Session: {session}")
            print(f"SPECS keys: {list(SPECS.keys()) if SPECS else 'None'}")
            print(f"QUEUE length: {len(QUEUE) if QUEUE else 'None'}")
            
            if not QUEUE:
                return {
                    "success": False,
                    "message": "No endpoints in queue to scan",
                    "findings_count": 0
                }
            
            # Convert queue items to endpoint format
            endpoints = []
            print(f"Processing {len(QUEUE)} queue items...")
            
            for i, item in enumerate(QUEUE):
                print(f"Processing item {i}: {item}")
                try:
                    if item.get('spec_id') in SPECS:
                        spec = SPECS[item['spec_id']]
                        print(f"Found spec: {spec}")
                        
                        if spec is None:
                            print(f"Spec is None for spec_id: {item['spec_id']}")
                            continue
                        
                        ops = spec.get('ops', [])
                        print(f"Operations: {ops}")
                        
                        if item.get('idx') is not None and isinstance(item.get('idx'), int) and 0 <= item.get('idx') < len(ops):
                            op = ops[item['idx']]
                            print(f"Operation: {op}")
                            
                            if op is None:
                                print(f"Operation at index {item['idx']} is None, skipping")
                            else:
                                # Build finalized URL and request using preview (expands path params and overrides)
                                try:
                                    resolver = RefResolver(spec.get('spec'))
                                    seed = op_seed(spec.get('url', ''), op.get('method', ''), op.get('path', ''))
                                    preview = build_preview(
                                        spec=spec.get('spec'),
                                        base_url=spec.get('base_url'),
                                        op=op,
                                        resolver=resolver,
                                        override=item.get('override') or {},
                                        seed=seed,
                                        fresh=False,
                                    )
                                    full_url = preview.get('url') or ''
                                    # Prepare headers
                                    headers = {}
                                    print(f"Session: {session}")
                                    if session and session.get('bearer'):
                                        headers['Authorization'] = f"Bearer {session['bearer']}"
                                    # Merge preview headers and override (already applied inside preview)
                                    ph = preview.get('headers') or {}
                                    if ph:
                                        headers.update(ph)
                                    # Prefer JSON body if present, fallback to form/raw data
                                    body = None
                                    if preview.get('json') is not None:
                                        try:
                                            body = json.dumps(preview.get('json'))
                                        except Exception:
                                            body = str(preview.get('json'))
                                    elif preview.get('data') is not None:
                                        if isinstance(preview.get('data'), str):
                                            body = preview.get('data')
                                        elif isinstance(preview.get('data'), bytes):
                                            body = preview.get('data').decode('utf-8', errors='ignore')
                                        else:
                                            try:
                                                body = json.dumps(preview.get('data'))
                                            except Exception:
                                                body = str(preview.get('data'))
                                    endpoint = {
                                        'url': full_url,
                                        'method': preview.get('method') or op.get('method', 'GET'),
                                        'headers': headers,
                                        'body': body,
                                        'spec_id': item['spec_id'],
                                        'op_index': item['idx']
                                    }
                                    endpoints.append(endpoint)
                                    print(f"Added endpoint: {endpoint}")
                                except Exception as e:
                                    print(f"Error building preview URL: {e}")
                                    import traceback
                                    traceback.print_exc()
                                    # Fallback to naive concat
                                    base_url = spec.get('base_url') or spec.get('url', '')
                                    full_url = f"{base_url.rstrip('/')}{op.get('path', '')}" if base_url else op.get('path', '')
                                    endpoint = {
                                        'url': full_url,
                                        'method': op.get('method', 'GET'),
                                        'headers': {},
                                        'body': None,
                                        'spec_id': item['spec_id'],
                                        'op_index': item['idx']
                                    }
                                    endpoints.append(endpoint)
                        else:
                            print(f"Invalid operation index: {item.get('idx')} (type: {type(item.get('idx'))}) for {len(ops)} operations")
                    else:
                        print(f"Spec not found: {item.get('spec_id')}")
                except Exception as e:
                    print(f"Error processing item {i}: {e}")
                    import traceback
                    traceback.print_exc()
                    # Add error to response for debugging
                    if not hasattr(self, '_errors'):
                        self._errors = []
                    self._errors.append(f"Item {i}: {str(e)}")
            
            if not endpoints:
                # Get sample idx values and ops count for debugging
                sample_idx = [item.get('idx') for item in QUEUE[:3]]
                sample_ops_count = []
                for item in QUEUE[:3]:
                    if item.get('spec_id') in SPECS:
                        ops = SPECS[item['spec_id']].get('ops', [])
                        sample_ops_count.append(len(ops))
                    else:
                        sample_ops_count.append('spec-not-found')
                
                error_msg = f"No valid endpoints found to scan. Processed {len(QUEUE)} queue items, found {len(endpoints)} valid endpoints. Sample idx: {sample_idx}, Sample ops count: {sample_ops_count}"
                if hasattr(self, '_errors') and self._errors:
                    error_msg += f". Errors: {self._errors[:3]}"
                
                return {
                    "success": False,
                    "message": error_msg,
                    "findings_count": 0
                }
            
            # Run Nuclei scan
            print(f"Starting Nuclei scan of {len(endpoints)} endpoints...")
            print(f"Endpoints: {[ep['url'] for ep in endpoints[:3]]}...")  # Debug first 3 endpoints
            
            try:
                # Check if Nuclei is available
                if not self.nuclei.check_nuclei_available():
                    print("Nuclei not available, simulating scan...")
                    findings = []
                    
                    # Simulate some findings for testing
                    if endpoints:
                        findings = [{
                            'template-id': 'xss-test',
                            'info': {
                                'name': 'XSS Test Vulnerability',
                                'severity': 'high',
                                'tags': ['xss', 'injection'],
                                'description': 'Test XSS vulnerability detection'
                            },
                            'matched-at': endpoints[0]['url'] + '/test',
                            'request': 'GET /test HTTP/1.1',
                            'response': 'HTTP/1.1 200 OK',
                            'curl-command': 'curl -X GET ' + endpoints[0]['url'] + '/test',
                            'cwe_id': 'CWE-79',
                            'owasp_category': 'A03:2021-Injection'
                        }]
                    
                    print(f"Simulated scan completed. Found {len(findings)} findings.")
                else:
                    print("Running real Nuclei scan...")
                    # Run actual Nuclei scan
                    # Save runnable commands for user to reproduce
                    save_cmd_dir = None
                    if run_id:
                        try:
                            ensure_dirs(pid)
                            save_cmd_dir = os.path.join(get_project_dir(pid), "runs", f"{run_id}.cmds")
                            os.makedirs(save_cmd_dir, exist_ok=True)
                        except Exception:
                            save_cmd_dir = None
                    findings = self.nuclei.scan_multiple_endpoints(
                        endpoints=endpoints,
                        templates=templates,
                        severity=severity,
                        save_cmd_dir=save_cmd_dir
                    )
                    print(f"Real Nuclei scan completed. Found {len(findings)} findings.")
            except Exception as e:
                print(f"Nuclei scan error: {e}")
                import traceback
                traceback.print_exc()
                return {
                    "success": False,
                    "message": f"Scan failed: {str(e)}",
                    "findings_count": 0
                }
            
            # Convert findings to our format using normalize_finding
            converted_findings: List[Dict[str, Any]] = []
            for finding in findings:
                # Convert nuclei finding to raw format first
                raw_finding = self.convert_nuclei_to_finding(finding, pid)
                
                # Normalize using the new utility
                from utils.findings_normalize import normalize_finding
                normalized = normalize_finding(
                    raw_finding,
                    pid=pid,
                    run_id=run_id or f"nuclei_{int(time.time())}",
                    method=raw_finding.get("method", "GET"),
                    url=raw_finding.get("url", ""),
                    status_code=raw_finding.get("status_code")
                )
                converted_findings.append(normalized)

            # Compute severity counts and worst severity
            sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
            sev_counts: Dict[str, int] = {"critical":0, "high":0, "medium":0, "low":0, "info":0}
            for f in converted_findings:
                s = str(f.get("severity") or "info").lower()
                if s in sev_counts:
                    sev_counts[s] += 1
            worst = None
            if converted_findings:
                worst = min((str(f.get("severity") or "info").lower() for f in converted_findings), key=lambda x: sev_order.get(x, 9))

            # Persist NDJSON artifact with raw nuclei lines if run_id provided
            artifact_path = None
            if run_id:
                try:
                    ensure_dirs(pid)
                    runs_dir = os.path.join(get_project_dir(pid), "runs")
                    artifact_path = os.path.join(runs_dir, f"{run_id}.nuclei.ndjson")
                    with open(artifact_path, "w", encoding="utf-8") as af:
                        for item in findings:
                            raw: Dict[str, Any] = {}
                            if isinstance(item, NucleiResult):
                                raw = item.raw or {}
                            elif isinstance(item, dict):
                                raw = item
                            if raw:
                                af.write(json.dumps(raw, ensure_ascii=False) + "\n")
                except Exception as _e:
                    print(f"[WARN] could not write nuclei artifact: {_e}")
            
            # Attach run provenance to each finding
            if run_id:
                prov_path = artifact_path
                for f in converted_findings:
                    f["run_id"] = run_id
                    if prov_path:
                        f["artifact_path"] = prov_path
            # Add findings to project with proper storage order
            if converted_findings:
                # Store findings first
                append_findings(pid, converted_findings)
                
                # Bust cache immediately after storage
                try:
                    from store import _bust_vulns_cache
                    _bust_vulns_cache(pid)
                except Exception as e:
                    logger.warning(f"VULNS_CACHE_BUST_ERROR pid={pid} error={str(e)}")
            
            # Run custom pattern engine detection for each endpoint (Phase 4A fix)
            pattern_findings_count = 0
            try:
                from findings import analyze_and_record
                for ep in endpoints:
                    try:
                        # Build request preview from endpoint
                        req_preview = {
                            "url": ep.get("url", ""),
                            "method": ep.get("method", "GET"),
                            "headers": ep.get("headers", {}),
                            "cookies": ep.get("cookies", {}),
                            "query": ep.get("query", {}),
                            "json": ep.get("json"),
                            "data": ep.get("data"),
                        }
                        
                        # Run pattern engine detection (no response data available in non-streaming mode)
                        pattern_findings = analyze_and_record(pid, req_preview, None)
                        if pattern_findings:
                            pattern_findings_count += len(pattern_findings)
                    except Exception:
                        # Pattern engine errors are non-fatal
                        continue
            except Exception:
                # Pattern engine errors are non-fatal
                pass
            
            return {
                "success": True,
                "message": f"Scan completed. Found {len(converted_findings)} vulnerabilities.",
                "findings_count": len(converted_findings),
                "endpoints_scanned": len(endpoints),
                "templates_used": templates or "all",
                "severity_filter": severity or "all",
                "severity_counts": sev_counts,
                "worst_severity": worst,
                "artifact_path": artifact_path,
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Scan failed: {str(e)}",
                "findings_count": 0
            }
    
    def get_available_templates(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get available Nuclei templates."""
        return self.nuclei.list_templates(category)
    
    def update_templates(self) -> Tuple[bool, str]:
        """Update Nuclei templates."""
        try:
            # Force rebuild index from configured directories
            self.nuclei._index_built = False
            self.nuclei._build_index()
            ok, msg = self.nuclei.update_templates()
            return (ok, msg) if isinstance(ok, bool) else (True, "Templates refreshed")
        except Exception as e:
            return False, f"Failed to refresh templates: {e}"
    
    def check_nuclei_status(self) -> Dict[str, Any]:
        """Check Nuclei availability and status."""
        available = self.nuclei.check_nuclei_available()
        templates = self.get_available_templates()
        
        return {
            "available": available,
            "template_count": len(templates),
            "templates": templates[:10],  # Show first 10 templates
            "version": "v3.4.5"  # TODO: Extract from nuclei -version
        }

    def scan_project_endpoints_stream(self, pid: str,
                                      templates: Optional[List[str]] = None,
                                      severity: Optional[List[str]] = None,
                                      exclude_patterns: Optional[List[str]] = None,
                                      run_id: Optional[str] = None):
        """Generator that scans and yields SSE-formatted events as progress/findings arrive."""
        import json as _json
        import time
        from findings import append_findings
        from store import ensure_dirs, get_project_dir
        
        start_time = time.time()
        
        # Build endpoints from Test Queue
        endpoints: List[Dict[str, Any]] = self._build_endpoints_from_queue(pid)

        total = len(endpoints)
        sev_counts: Dict[str, int] = {k: 0 for k in ['critical','high','medium','low','info']}
        converted_buffer: List[Dict[str, Any]] = []

        # Prepare artifacts if run_id provided
        af = None
        artifact_path = None
        rr_dir = None
        if run_id:
            try:
                ensure_dirs(pid)
                runs_dir = os.path.join(get_project_dir(pid), 'runs')
                os.makedirs(runs_dir, exist_ok=True)
                artifact_path = os.path.join(runs_dir, f"{run_id}.nuclei.ndjson")
                af = open(artifact_path, 'w', encoding='utf-8')
                rr_dir = os.path.join(runs_dir, f"{run_id}.rr")
                os.makedirs(rr_dir, exist_ok=True)
            except Exception:
                af = None

        # Emit start
        yield f"event: start\ndata: {_json.dumps({'run_id': run_id, 'total_endpoints': total})}\n\n"

        # Iterate endpoints and stream results per endpoint
        for idx, ep in enumerate(endpoints, start=1):
            # Extract template info for progress event
            current_template = templates[0] if templates else "default"
            
            yield f"event: progress\ndata: {_json.dumps({'processed': idx, 'total': total, 'endpoint': {'method': ep.get('method'), 'path': ep.get('url')}, 'template_id': current_template, 'detector_source': 'nuclei'})}\n\n"
            try:
                results = self.nuclei.scan_endpoint(
                    url=ep.get('url',''),
                    method=ep.get('method','GET'),
                    headers=ep.get('headers'),
                    body=ep.get('body'),
                    templates=templates,
                    severity=severity,
                    include_rr=True,
                    markdown_export_dir=rr_dir
                )
            except Exception:
                results = []

            for r in results:
                # Write raw to artifact if available
                try:
                    raw = getattr(r, 'raw', None)
                    if af is not None and raw is not None:
                        af.write(_json.dumps(raw) + "\n")
                except Exception:
                    pass

                # Convert nuclei finding to raw format first
                raw_finding = self.convert_nuclei_to_finding(r, pid)
                
                # Normalize using the new utility
                from utils.findings_normalize import normalize_finding
                converted = normalize_finding(
                    raw_finding,
                    pid=pid,
                    run_id=run_id,
                    method=raw_finding.get("method", "GET"),
                    url=raw_finding.get("url", ""),
                    status_code=raw_finding.get("status_code")
                )
                
                # Track counts
                sev_counts[converted.get('severity','info')] = sev_counts.get(converted.get('severity','info'),0)+1
                converted_buffer.append(converted)
                
                # Store finding first, then bust cache
                try:
                    append_findings(pid, [converted])
                    # Only proceed with SSE if storage succeeded
                    storage_success = True
                except Exception as e:
                    logger.warning(f"STORAGE_FAILED pid={pid} detector_id={converted.get('detector_id')} error={str(e)}")
                    storage_success = False
                
                if storage_success:
                    try:
                        from store import _bust_vulns_cache
                        _bust_vulns_cache(pid)
                    except Exception as e:
                        logger.warning(f"VULNS_CACHE_BUST_ERROR pid={pid} error={str(e)}")
                
                # Run custom pattern engine detection (Phase 4A fix)
                try:
                    from findings import analyze_and_record
                    # Build request preview from nuclei result
                    req_preview = {
                        "url": converted.get("url", ""),
                        "method": converted.get("method", "GET"),
                        "headers": converted.get("req", {}).get("headers", {}),
                        "cookies": converted.get("req", {}).get("cookies", {}),
                        "query": converted.get("req", {}).get("query", {}),
                        "json": converted.get("req", {}).get("json"),
                        "data": converted.get("req", {}).get("data"),
                    }
                    
                    # Build response from nuclei result
                    resp_data = {
                        "status": converted.get("status"),
                        "headers": converted.get("res", {}).get("headers", {}),
                        "body": converted.get("res", {}).get("body", ""),
                        "content_type": converted.get("res", {}).get("content_type"),
                    }
                    
                    # Run pattern engine detection
                    pattern_findings = analyze_and_record(pid, req_preview, resp_data)
                    if pattern_findings:
                        # Convert pattern findings to our format and append
                        pattern_converted = []
                        for pf in pattern_findings:
                            pattern_converted.append({
                                "id": pf.get("id"),
                                "pid": pid,
                                "version": pf.get("version"),
                                "ts": pf.get("ts"),
                                "detector_id": pf.get("detector_id"),
                                "title": pf.get("title"),
                                "severity": pf.get("severity"),
                                "owasp": pf.get("owasp"),
                                "owasp_api": pf.get("owasp_api"),
                                "cwe": pf.get("cwe"),
                                "detail": pf.get("detail"),
                                "evidence": pf.get("evidence"),
                                "method": pf.get("method"),
                                "url": pf.get("url"),
                                "status": pf.get("status"),
                                "req": pf.get("req"),
                                "res": pf.get("res"),
                                "tags": pf.get("tags"),
                                "subcategory": pf.get("subcategory"),
                                "confidence": pf.get("confidence"),
                            })
                        append_findings(pid, pattern_converted)
                        # Update counts and emit finding events
                        for pf in pattern_converted:
                            sev = pf.get('severity','info')
                            sev_counts[sev] = sev_counts.get(sev,0)+1
                            
                            # Emit finding event for pattern engine findings - only after successful storage
                            from utils.endpoints import endpoint_key
                            ep_key = endpoint_key(pf.get('method', 'GET'), pf.get('url', ''), None)
                            out = {
                                'event': 'finding',
                                'stored': True,
                                'severity': sev,
                                'detector_id': pf.get('detector_id'),
                                'endpoint_key': ep_key,
                                'title': pf.get('title'),
                                'created_at': pf.get('ts'),
                                'source': 'pattern'
                            }
                            yield f"event: finding\ndata: {_json.dumps(out)}\n\n"
                            logger.info(f"SSE_EVENT kind=\"finding\" run_id={run_id} endpoint_key=\"{ep_key}\" detector_id=\"{pf.get('detector_id')}\" severity={sev} stored=true")
                except Exception as e:
                    # Pattern engine errors are non-fatal
                    pass
                # Emit finding event (compact) - only after successful storage
                if storage_success:
                    from utils.endpoints import endpoint_key
                    ep_key = endpoint_key(converted.get('method', 'GET'), converted.get('url', ''), None)
                    out = {
                        'event': 'finding',
                        'stored': True,
                        'severity': converted.get('severity'),
                        'detector_id': converted.get('detector_id', 'nuclei'),
                        'endpoint_key': ep_key,
                        'title': converted.get('title'),
                        'created_at': converted.get('created_at'),
                        'source': 'nuclei'
                    }
                    yield f"event: finding\ndata: {_json.dumps(out)}\n\n"
                    logger.info(f"SSE_EVENT kind=\"finding\" run_id={run_id} endpoint_key=\"{ep_key}\" detector_id=\"{converted.get('detector_id', 'nuclei')}\" severity={converted.get('severity')} stored=true")
                else:
                    # Emit error event for failed storage
                    yield f"event: error\ndata: {_json.dumps({'count_failed': 1, 'error': 'Storage failed for nuclei finding'})}\n\n"
                
                # Emit heartbeat every few findings
                if len(converted_buffer) % 5 == 0:
                    yield f"event: heartbeat\ndata: {_json.dumps({'timestamp': time.time()})}\n\n"

        # Close artifact file
        if af is not None:
            try: af.close()
            except Exception: pass

        # Emit done summary
        total_findings = sum(sev_counts.values())
        worst = None
        for sev in ['critical','high','medium','low','info']:
            if sev_counts.get(sev):
                worst = worst or sev
        
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)
        
        done = {
            'run_id': run_id,
            'duration_ms': duration_ms,
            'endpoints_processed': total,
            'findings': total_findings
        }
        yield f"event: done\ndata: {_json.dumps(done)}\n\n"
    
    def _parse_url(self, url: str) -> Dict[str, str]:
        """Parse URL into components."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return {
                'scheme': parsed.scheme,
                'hostname': parsed.hostname,
                'port': str(parsed.port) if parsed.port else '',
                'path': parsed.path,
                'query': parsed.query,
                'fragment': parsed.fragment
            }
        except Exception:
            return {'path': '/'}
    
    def _extract_method(self, nuclei_item: Dict[str, Any]) -> str:
        """Extract HTTP method from Nuclei result."""
        request = nuclei_item.get('request', {})
        if isinstance(request, dict):
            return request.get('method', 'GET')
        elif isinstance(request, str) and request:
            # Parse method from request string
            lines = request.split('\n')
            if lines and lines[0]:
                parts = lines[0].split()
                if len(parts) > 0:
                    return parts[0]
        return 'GET'
    
    def _extract_cwe(self, nuclei_item: Dict[str, Any]) -> Optional[str]:
        """Extract CWE ID from Nuclei result."""
        info = nuclei_item.get('info', {})
        cwe_ids = info.get('cwe-id')
        if cwe_ids:
            if isinstance(cwe_ids, list) and cwe_ids:
                return f"CWE-{cwe_ids[0]}"
            elif isinstance(cwe_ids, (str, int)):
                return f"CWE-{cwe_ids}"
        
        # Fallback to tags if no direct CWE-ID
        tags = info.get('tags', [])
        for tag in tags:
            if tag.upper().startswith('CWE-'):
                return tag.upper()
        return None
    
    def _map_cwe_to_owasp(self, cwe: Optional[str]) -> Optional[str]:
        """Map CWE ID to OWASP Top 10 category."""
        if not cwe:
            return None
        
        # CWE to OWASP mapping
        cwe_owasp_map = {
            "CWE-79": "A03:2021-Injection",  # XSS
            "CWE-89": "A03:2021-Injection",  # SQL Injection
            "CWE-78": "A03:2021-Injection",  # Command Injection
            "CWE-918": "A10:2021-Server-Side Request Forgery",  # SSRF
            "CWE-284": "A01:2021-Broken Access Control",  # Improper Access Control
            "CWE-16": "A05:2021-Security Misconfiguration",  # Configuration
            "CWE-200": "A05:2021-Security Misconfiguration",  # Information Exposure
            "CWE-521": "A07:2021-Identification and Authentication Failures",  # Weak Password
            "CWE-287": "A07:2021-Identification and Authentication Failures",  # Authentication Bypass
            "CWE-601": "A03:2021-Injection",  # Open Redirect
            "CWE-93": "A03:2021-Injection",  # CRLF Injection
            "CWE-22": "A03:2021-Injection",  # Path Traversal
            "CWE-94": "A03:2021-Injection",  # Code Injection
            "CWE-611": "A05:2021-Security Misconfiguration",  # XXE
            "CWE-352": "A01:2021-Broken Access Control",  # CSRF
            "CWE-444": "A03:2021-Injection",  # HTTP Request Smuggling
            "CWE-434": "A04:2021-Insecure Design",  # File Upload
            "CWE-917": "A03:2021-Injection",  # SSTI
            "CWE-502": "A08:2021-Software and Data Integrity Failures",  # Deserialization
            "CWE-942": "A07:2021-Identification and Authentication Failures",  # CORS
            "CWE-358": "A05:2021-Security Misconfiguration",  # Subdomain Takeover
        }
        
        return cwe_owasp_map.get(cwe)
    
    def _map_template_to_owasp(self, template_id: str, template_info: Dict[str, Any]) -> str:
        """Map template to OWASP category based on template ID and tags."""
        tags = template_info.get('tags', [])
        template_lower = template_id.lower()
        
        # Enhanced mapping based on template ID patterns
        template_patterns = {
            # Injection vulnerabilities
            'xss': "A03:2021-Injection",
            'sqli': "A03:2021-Injection", 
            'sql-injection': "A03:2021-Injection",
            'rce': "A03:2021-Injection",
            'command-injection': "A03:2021-Injection",
            'code-injection': "A03:2021-Injection",
            'ldap-injection': "A03:2021-Injection",
            'nosql-injection': "A03:2021-Injection",
            'ssti': "A03:2021-Injection",
            'template-injection': "A03:2021-Injection",
            'path-traversal': "A03:2021-Injection",
            'lfi': "A03:2021-Injection",
            'rfi': "A03:2021-Injection",
            'xxe': "A05:2021-Security Misconfiguration",
            'xml-external-entity': "A05:2021-Security Misconfiguration",
            'open-redirect': "A03:2021-Injection",
            'crlf': "A03:2021-Injection",
            'http-request-smuggling': "A03:2021-Injection",
            
            # Access Control
            'idor': "A01:2021-Broken Access Control",
            'access-control': "A01:2021-Broken Access Control",
            'privilege-escalation': "A01:2021-Broken Access Control",
            'privesc': "A01:2021-Broken Access Control",
            'horizontal-privilege': "A01:2021-Broken Access Control",
            'vertical-privilege': "A01:2021-Broken Access Control",
            'csrf': "A01:2021-Broken Access Control",
            'clickjacking': "A01:2021-Broken Access Control",
            
            # Authentication & Session Management
            'auth': "A07:2021-Identification and Authentication Failures",
            'authentication': "A07:2021-Identification and Authentication Failures",
            'session': "A07:2021-Identification and Authentication Failures",
            'jwt': "A07:2021-Identification and Authentication Failures",
            'oauth': "A07:2021-Identification and Authentication Failures",
            'saml': "A07:2021-Identification and Authentication Failures",
            'cors': "A07:2021-Identification and Authentication Failures",
            'weak-password': "A07:2021-Identification and Authentication Failures",
            'default-login': "A07:2021-Identification and Authentication Failures",
            'brute-force': "A07:2021-Identification and Authentication Failures",
            'password-reset': "A07:2021-Identification and Authentication Failures",
            
            # Security Misconfiguration
            'misconfiguration': "A05:2021-Security Misconfiguration",
            'config': "A05:2021-Security Misconfiguration",
            'exposure': "A05:2021-Security Misconfiguration",
            'disclosure': "A05:2021-Security Misconfiguration",
            'info-disclosure': "A05:2021-Security Misconfiguration",
            'directory-listing': "A05:2021-Security Misconfiguration",
            'debug': "A05:2021-Security Misconfiguration",
            'backup': "A05:2021-Security Misconfiguration",
            'subdomain-takeover': "A05:2021-Security Misconfiguration",
            'dns': "A05:2021-Security Misconfiguration",
            'ssl': "A05:2021-Security Misconfiguration",
            'tls': "A05:2021-Security Misconfiguration",
            'certificate': "A05:2021-Security Misconfiguration",
            'headers': "A05:2021-Security Misconfiguration",
            'security-headers': "A05:2021-Security Misconfiguration",
            
            # Insecure Design
            'file-upload': "A04:2021-Insecure Design",
            'upload': "A04:2021-Insecure Design",
            'business-logic': "A04:2021-Insecure Design",
            'logic': "A04:2021-Insecure Design",
            'rate-limiting': "A04:2021-Insecure Design",
            'dos': "A04:2021-Insecure Design",
            'denial-of-service': "A04:2021-Insecure Design",
            
            # Vulnerable Components
            'cve': "A06:2021-Vulnerable and Outdated Components",
            'vulnerable': "A06:2021-Vulnerable and Outdated Components",
            'outdated': "A06:2021-Vulnerable and Outdated Components",
            'version': "A06:2021-Vulnerable and Outdated Components",
            'framework': "A06:2021-Vulnerable and Outdated Components",
            'library': "A06:2021-Vulnerable and Outdated Components",
            
            # Logging & Monitoring
            'logging': "A09:2021-Security Logging and Monitoring Failures",
            'monitoring': "A09:2021-Security Logging and Monitoring Failures",
            'audit': "A09:2021-Security Logging and Monitoring Failures",
            
            # Server-Side Request Forgery
            'ssrf': "A10:2021-Server-Side Request Forgery",
            'request-forgery': "A10:2021-Server-Side Request Forgery",
            'blind-ssrf': "A10:2021-Server-Side Request Forgery",
            
            # Software and Data Integrity
            'deserialization': "A08:2021-Software and Data Integrity Failures",
            'serialization': "A08:2021-Software and Data Integrity Failures",
            'integrity': "A08:2021-Software and Data Integrity Failures",
            'supply-chain': "A08:2021-Software and Data Integrity Failures",
        }
        
        # Check template ID patterns first
        for pattern, owasp in template_patterns.items():
            if pattern in template_lower:
                return owasp
        
        # Check tags
        for tag in tags:
            tag_lower = tag.lower()
            for pattern, owasp in template_patterns.items():
                if pattern in tag_lower:
                    return owasp
        
        # API-specific patterns
        if any(api_tag in template_lower for api_tag in ['api', 'rest', 'graphql', 'soap', 'endpoint']):
            # If it's API-related but doesn't match other patterns, likely misconfiguration
            return "A05:2021-Security Misconfiguration"
        
        # Default fallback
        return "A05:2021-Security Misconfiguration"
    
    def _is_web_vulnerability(self, template_info: Dict[str, Any]) -> bool:
        """Determine if this is a web-specific vulnerability."""
        tags = template_info.get('tags', [])
        web_tags = ['xss', 'csrf', 'cors', 'file-upload', 'path-traversal', 'lfi', 'rfi']
        return any(tag.lower() in web_tags for tag in tags)
    
    def _is_api_vulnerability(self, template_info: Dict[str, Any]) -> bool:
        """Determine if this is an API-specific vulnerability."""
        tags = template_info.get('tags', [])
        api_tags = ['api', 'rest', 'graphql', 'soap', 'endpoint', 'api-key', 'jwt', 'oauth']
        return any(tag.lower() in api_tags for tag in tags)
    
    def _build_evidence(self, nuclei_item: Dict[str, Any]) -> str:
        """Build evidence string from Nuclei result."""
        evidence_parts = []
        # Prefer extracted results
        ex = nuclei_item.get('extracted-results')
        if isinstance(ex, list) and ex:
            for v in ex:
                try:
                    evidence_parts.append(str(v))
                except Exception:
                    pass
        # If nothing extracted, include match location as minimal context
        if not evidence_parts:
            matched_at = nuclei_item.get('matched-at', '')
            if matched_at:
                evidence_parts.append(f"match: {matched_at}")

        # Add request/response snippets
        request = nuclei_item.get('request', '')
        response = nuclei_item.get('response', '')
        
        if request:
            evidence_parts.append(f"Request: {request[:200]}{'...' if len(request) > 200 else ''}")
        
        if response:
            evidence_parts.append(f"Response: {response[:200]}{'...' if len(response) > 200 else ''}")
        
        return "\n".join(evidence_parts)

    def _parse_raw_http_request(self, raw: Optional[str]) -> Optional[Dict[str, Any]]:
        if not raw or not isinstance(raw, str):
            return None
        try:
            lines = raw.splitlines()
            start = lines[0] if lines else ''
            headers: Dict[str, str] = {}
            body_lines: List[str] = []
            in_headers = True
            for line in lines[1:]:
                if in_headers:
                    if not line.strip():
                        in_headers = False
                    elif ':' in line:
                        k, v = line.split(':', 1)
                        headers[k.strip()] = v.strip()
                else:
                    body_lines.append(line)
            body = "\n".join(body_lines).strip()
            json_payload = None
            data_payload: Optional[str] = None
            ct = headers.get('Content-Type', headers.get('content-type', '')).lower()
            if body:
                if 'application/json' in ct:
                    try:
                        import json as _json
                        json_payload = _json.loads(body)
                    except Exception:
                        data_payload = body
                else:
                    data_payload = body
            return {
                "headers": headers,
                "json": json_payload,
                "data": data_payload,
                "start": start,
            }
        except Exception:
            return None

    def _parse_raw_http_response(self, raw: Optional[str]) -> Optional[Dict[str, Any]]:
        if not raw or not isinstance(raw, str):
            return None
        try:
            lines = raw.splitlines()
            status_line = lines[0] if lines else ''
            headers: Dict[str, str] = {}
            body_lines: List[str] = []
            in_headers = True
            for line in lines[1:]:
                if in_headers:
                    if not line.strip():
                        in_headers = False
                    elif ':' in line:
                        k, v = line.split(':', 1)
                        headers[k.strip()] = v.strip()
                else:
                    body_lines.append(line)
            body = "\n".join(body_lines)
            status_code = None
            try:
                # e.g., HTTP/1.1 200 OK
                parts = status_line.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    status_code = int(parts[1])
            except Exception:
                pass
            return {
                "headers": headers,
                "body": body,
                "content_type": headers.get('Content-Type', headers.get('content-type')),
                "status": status_code,
                "status_line": status_line,
            }
        except Exception:
            return None
    
    def _map_severity(self, sev: str) -> str:
        """Map Nuclei severity to internal severity levels."""
        if not sev:
            return 'info'
        sev = sev.strip().lower()
        if sev in ('critical', 'crit'):
            return 'critical'
        if sev in ('high',):
            return 'high'
        if sev in ('medium', 'med'):
            return 'medium'
        if sev in ('low',):
            return 'low'
        return 'info'
    
    def _score_confidence(self, nuclei_item: Dict[str, Any]) -> int:
        """Score confidence based on Nuclei result."""
        # Use Nuclei's confidence if available
        info = nuclei_item.get('info', {})
        nuclei_confidence = info.get('confidence', 0)
        
        if isinstance(nuclei_confidence, int) and nuclei_confidence > 0:
            return min(max(nuclei_confidence, 0), 100)
        
        # Default confidence based on severity
        severity = info.get('severity', 'info').lower()
        severity_scores = {
            'critical': 95,
            'high': 85,
            'medium': 70,
            'low': 50,
            'info': 30
        }
        
        return severity_scores.get(severity, 50)

# Global instance
nuclei_integration = NucleiIntegration()
