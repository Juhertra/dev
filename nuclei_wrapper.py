"""
Nuclei Wrapper for Active Testing (Phase 5)
Integrates Nuclei scanner with the Security Toolkit for active vulnerability testing.
"""

import glob
import json
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    yaml = None

class NucleiSeverity(Enum):
    """Nuclei severity levels mapped to our system."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class NucleiStatus(Enum):
    """Finding status for triaging."""
    OPEN = "open"
    ACCEPTED_RISK = "accepted_risk"
    FALSE_POSITIVE = "false_positive"
    FIXED = "fixed"

@dataclass
class NucleiResult:
    """Normalized Nuclei result with raw metadata preserved."""
    template_id: str
    template_name: str
    severity: str
    confidence: int
    method: str
    url: str
    path: str
    status_code: Optional[int]
    matched_at: str
    info: Dict[str, Any]
    request: Optional[str] = None
    response: Optional[str] = None
    curl_command: Optional[str] = None
    cwe_id: Optional[str] = None
    owasp_category: Optional[str] = None
    template_path: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None
    # Originating endpoint context
    origin_url: Optional[str] = None
    origin_method: Optional[str] = None
    status: str = "open"  # For triaging

class NucleiWrapper:
    """Wrapper for Nuclei scanner integration."""
    
    def __init__(self, nuclei_path: str = "nuclei", extra_template_dirs: Optional[List[str]] = None):
        from config import get as cfg_get
        self.nuclei_path = nuclei_path
        # Prefer persisted config for templates directory
        cfg_dir = cfg_get("nuclei_templates_dir")
        self.template_dir = None
        if cfg_dir and os.path.isdir(cfg_dir):
            self.template_dir = cfg_dir
        else:
            # Try to find the actual nuclei templates directory
            possible_dirs = [
                os.path.expanduser("~/.local/share/nuclei/templates"),
                os.path.expanduser("~/nuclei-templates"),
                "/usr/local/share/nuclei/templates",
                "/opt/nuclei/templates"
            ]
            for dir_path in possible_dirs:
                if os.path.exists(dir_path):
                    self.template_dir = dir_path
                    break
            if not self.template_dir:
                # Fallback to default
                self.template_dir = os.path.expanduser("~/.local/share/nuclei/templates")
            
        # Merge persisted extra sources (e.g., ASVS) so they survive restarts
        persisted_extras = cfg_get("nuclei_extra_sources") or []
        self.extra_template_dirs = [d for d in (extra_template_dirs or []) if d and os.path.isdir(d)]
        for d in persisted_extras:
            if d and os.path.isdir(d) and d not in self.extra_template_dirs:
                self.extra_template_dirs.append(d)
        self.output_dir = tempfile.mkdtemp(prefix="nuclei_output_")
        self._tpl_index: Dict[str, Dict[str, Any]] = {}
        self._index_built = False

    def register_template_dir(self, path: str, source: str = "asvs"):
        """Register an additional template directory (e.g., ASVS templates)."""
        if path and os.path.isdir(path):
            self.extra_template_dirs.append(path)
            try:
                from config import append_to_list
                append_to_list("nuclei_extra_sources", path)
            except Exception:
                pass
            self._index_built = False  # Force reindex
        
    def check_nuclei_available(self) -> bool:
        """Check if Nuclei is available and working."""
        try:
            result = subprocess.run(
                [self.nuclei_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            # Nuclei outputs version info to stderr, not stdout
            # Check both return code and that we got some output
            return result.returncode == 0 and bool(result.stdout.strip() or result.stderr.strip())
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def update_templates(self) -> Tuple[bool, str]:
        """Update Nuclei templates."""
        try:
            result = subprocess.run(
                [self.nuclei_path, "-update-templates"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes
            )
            return result.returncode == 0, result.stderr if result.returncode != 0 else "Templates updated successfully"
        except subprocess.TimeoutExpired:
            return False, "Template update timed out"
        except Exception as e:
            return False, f"Template update failed: {str(e)}"
    
    def list_templates(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available Nuclei templates."""
        try:
            # Always get all templates first, then filter by category
            cmd = [self.nuclei_path, "-tl"]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return []
            
            templates = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    # Extract template ID from the file path
                    template_path = line.strip()
                    template_id = template_path.split('/')[-1].replace('.yaml', '')
                    
                    # Extract category from path structure
                    path_parts = template_path.split('/')
                    template_category = 'unknown'
                    if len(path_parts) >= 2:
                        template_category = path_parts[1]  # e.g., 'cves', 'misconfiguration', etc.
                        # Normalize category names for better filtering
                        if template_category == 'cves':
                            template_category = 'cve'
                        elif template_category == 'exposed-panels':
                            template_category = 'exposure'
                        elif template_category == 'default-logins':
                            template_category = 'default-logins'
                        elif template_category == 'vulnerabilities':
                            template_category = 'vulnerabilities'
                        elif template_category == 'technologies':
                            template_category = 'technologies'
                    
                    # Better name formatting
                    name = template_id.replace('-', ' ').replace('_', ' ').title()
                    # Handle CVE names specially
                    if template_id.startswith('cve-'):
                        name = template_id.upper()
                    
                    templates.append({
                        'id': template_id,
                        'name': name,
                        'category': template_category,
                        'path': template_path,
                        'severity': 'info',  # Default severity
                        'tags': [template_category] if template_category != 'unknown' else [],
                        'description': f'Nuclei template for {name.lower()}'
                    })
            
            # Filter by category if specified
            if category:
                templates = [t for t in templates if t['category'] == category]
            
            return templates
        except Exception as e:
            print(f"Error listing templates: {e}")
            return []
    
    def scan_endpoint(self, 
                     url: str, 
                     method: str = "GET",
                     headers: Optional[Dict[str, str]] = None,
                     body: Optional[str] = None,
                     templates: Optional[List[str]] = None,
                     severity: Optional[List[str]] = None,
                     timeout: int = 30,
                     save_cmd_dir: Optional[str] = None,
                     include_rr: bool = True,
                     markdown_export_dir: Optional[str] = None) -> List[NucleiResult]:
        """
        Scan a single endpoint with Nuclei.
        
        Args:
            url: Target URL
            method: HTTP method
            headers: Custom headers
            body: Request body (for POST/PUT)
            templates: Specific template IDs to use
            severity: Severity levels to include
            timeout: Scan timeout in seconds
            save_cmd_dir: If provided, write a runnable command + input file copy here
        
        Returns:
            List of normalized NucleiResult objects
        """
        try:
            # Create temporary input file for Nuclei
            input_file = os.path.join(self.output_dir, f"input_{int(time.time())}.txt")
            with open(input_file, 'w') as f:
                f.write(f"{url}\n")
            
            # Build Nuclei command
            cmd = [
                self.nuclei_path,
                "-l", input_file,
                "-j",  # JSONL output format
                "-silent",
                "-timeout", str(timeout),
                "-retries", "1",
                "-irr",  # Include request/response in JSON
                "-fr"    # Follow redirects
            ]
            
            # Add custom headers
            if headers:
                for key, value in headers.items():
                    cmd.extend(["-H", f"{key}: {value}"])
            
            # Add request body for POST/PUT (using variables)
            if body and method.upper() in ["POST", "PUT", "PATCH"]:
                cmd.extend(["-V", f"body={body}"])
            
            # Add template filters (each template needs its own -t flag)
            if templates:
                for template in templates:
                    # Convert template ID to full path
                    template_path = self._get_template_path(template)
                    if template_path:
                        cmd.extend(["-t", template_path])
            
            # Add severity filters (nuclei expects a single comma-separated argument)
            if severity:
                levels = ",".join([s.lower() for s in severity if s])
                cmd.extend(["-severity", levels])

            # Include RR markdown export if requested
            if include_rr:
                cmd.append("-include-rr")
                if markdown_export_dir:
                    try:
                        os.makedirs(markdown_export_dir, exist_ok=True)
                    except Exception:
                        pass
                    cmd.extend(["-markdown-export", markdown_export_dir])
            
            # Log the exact command being executed
            cmd_str = " ".join(cmd)
            print("[NUCLEI CMD]", cmd_str)
            
            # Write scan plan for debugging/UX
            plan_path = os.path.join(self.output_dir, f"plan_{int(time.time())}.json")
            with open(plan_path, "w") as pf:
                json.dump({
                    "target_url": url,
                    "method": method,
                    "headers": headers or {},
                    "templates_requested": templates or [],
                    "severity": severity or [],
                    "cmd": cmd,
                }, pf, indent=2)
            
            # Optionally persist a copy of the command + input file to rerun easily
            if save_cmd_dir:
                try:
                    os.makedirs(save_cmd_dir, exist_ok=True)
                    import hashlib
                    import shutil
                    key = hashlib.sha1(f"{url}|{method}|{','.join(templates or [])}|{','.join(severity or [])}".encode()).hexdigest()[:10]
                    saved_input = os.path.join(save_cmd_dir, f"input_{key}.txt")
                    shutil.copyfile(input_file, saved_input)
                    cmd_saved = cmd_str.replace(input_file, saved_input)
                    with open(os.path.join(save_cmd_dir, f"cmd_{key}.sh"), "w") as f:
                        f.write(cmd_saved + "\n")
                except Exception:
                    pass
            
            # Run Nuclei scan
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 10
            )
            
            # Parse results
            findings = []
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            data = json.loads(line)
                            finding = self._normalize_result(data, url, method)
                            if finding:
                                findings.append(finding)
                        except json.JSONDecodeError:
                            continue
            
            # Cleanup temp input
            try:
                os.remove(input_file)
            except Exception:
                pass
            
            return findings
            
        except subprocess.TimeoutExpired:
            return []
        except Exception as e:
            print(f"Error scanning endpoint {url}: {e}")
            return []

    def scan_multiple_endpoints(self, 
                              endpoints: List[Dict[str, Any]],
                              templates: Optional[List[str]] = None,
                              severity: Optional[List[str]] = None,
                              max_concurrent: int = 5,
                              save_cmd_dir: Optional[str] = None) -> List[NucleiResult]:
        """
        Scan multiple endpoints concurrently.
        
        Args:
            endpoints: List of endpoint dictionaries with 'url', 'method', 'headers', 'body'
            templates: Specific template IDs to use
            severity: Severity levels to include
            max_concurrent: Maximum concurrent scans
            save_cmd_dir: Directory to persist runnable nuclei commands
        
        Returns:
            List of all findings from all endpoints
        """
        all_findings = []
        
        # For now, scan sequentially to avoid overwhelming the target
        # TODO: Implement proper concurrent scanning with rate limiting
        for endpoint in endpoints:
            findings = self.scan_endpoint(
                url=endpoint.get('url', ''),
                method=endpoint.get('method', 'GET'),
                headers=endpoint.get('headers'),
                body=endpoint.get('body'),
                templates=templates,
                severity=severity,
                save_cmd_dir=save_cmd_dir
            )
            all_findings.extend(findings)
            
            # Small delay between scans
            time.sleep(0.5)
        
        return all_findings
    
    def _build_index(self):
        """Index templates from default + extra dirs with lightweight caching."""
        if self._index_built:
            return
        self._tpl_index.clear()
        # Optional on-disk cache for faster cold starts
        cache_file = os.path.join(self.template_dir or "", ".templates-index.json") if self.template_dir else None
        if cache_file and os.path.isfile(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    if isinstance(data, dict) and data.get("items") and data.get("root") == (self.template_dir or ""):
                        self._tpl_index = data["items"]
                        self._index_built = True
                        return
            except Exception:
                pass

        def add_template(path: str, source: str):
            tid = Path(path).stem  # file name without .yaml
            meta = {
                "id": tid,
                "path": path,
                # If the path clearly belongs to an ASVS directory, mark source accordingly
                "source": ("asvs" if "asvs" in path.lower() else source),
                "category": self._infer_category_from_path(path),
                "severity": "info",
                "name": tid.replace("-", " ").replace("_", " ").title(),
                "tags": []
            }
            # Try to read minimal metadata for nicer display (best-effort)
            if yaml:
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        doc = next(yaml.safe_load_all(f))  # first doc
                        info = (doc or {}).get("info", {})
                        meta["name"] = info.get("name") or meta["name"]
                        meta["severity"] = (info.get("severity") or "info").lower()
                        tags = info.get("tags") or []
                        if isinstance(tags, str):
                            tags = [t.strip() for t in tags.split(",")]
                        meta["tags"] = tags
                except Exception:
                    pass
            self._tpl_index[tid] = meta

        # 1) Default nuclei list (portable)
        try:
            res = subprocess.run([self.nuclei_path, "-tl"], capture_output=True, text=True, timeout=30)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    p = line.strip()
                    if p.endswith(".yaml"):
                        # Convert relative path to absolute
                        if not os.path.isabs(p):
                            p = os.path.join(self.template_dir, p)
                        if os.path.isfile(p):
                            # If templates repo contains an embedded 'asvs' folder, tag it as asvs
                            src = "asvs" if "asvs" in p.lower() else "nuclei"
                            add_template(p, source=src)
        except Exception:
            pass

        # 2) Extra dirs (ASVS etc.)
        for root in self.extra_template_dirs:
            for path in glob.glob(os.path.join(root, "**/*.yaml"), recursive=True):
                add_template(path, source="asvs")

        self._index_built = True
        # Save cache for next startup
        try:
            if cache_file:
                with open(cache_file, "w", encoding="utf-8") as fh:
                    json.dump({"root": self.template_dir or "", "items": self._tpl_index}, fh)
        except Exception:
            pass

    def _infer_category_from_path(self, path: str) -> str:
        """Infer category from template path."""
        p = path.lower()
        if "/cves/" in p: return "cve"
        if "/misconfiguration/" in p: return "misconfiguration"
        if "/exposed-panels/" in p or "/expos" in p: return "exposure"
        if "/vulnerabilities/" in p: return "vulnerability"
        if "/technologies/" in p or "/tech" in p: return "technologies"
        if "asvs" in p: return "asvs"
        return "web"

    def list_templates(self, category: Optional[str] = None, source: Optional[str] = None, all_templates: bool = False) -> List[Dict[str, Any]]:
        """Return templates from default + ASVS dirs with minimal metadata."""
        if not self._index_built:
            self._build_index()
        items = list(self._tpl_index.values())
        if category:
            items = [t for t in items if t.get("category") == category]
        if source:
            items = [t for t in items if t.get("source") == source]
        return items

    def _get_template_path(self, template_id: str) -> Optional[str]:
        """Convert template ID to full file path using cached index."""
        if not self._index_built:
            self._build_index()
        meta = self._tpl_index.get(template_id)
        return meta["path"] if meta else None

    def _normalize_result(self, data: Dict[str, Any], url: str, method: str) -> Optional[NucleiResult]:
        """Normalize Nuclei JSON result to our format."""
        try:
            # Extract basic info
            template_id = data.get('template-id', 'unknown')
            template_name = data.get('info', {}).get('name', template_id)
            severity = data.get('info', {}).get('severity', 'info').lower()
            confidence = data.get('info', {}).get('confidence', 0)
            
            # Extract URL and path
            matched_url = data.get('matched-at', url)
            parsed_url = self._parse_url(matched_url) or {}
            
            # Extract request/response if available
            request = data.get('request', '')
            response = data.get('response', '')
            curl_command = data.get('curl-command', '')
            
            # Map to CWE/OWASP if available
            cwe_id = self._extract_cwe(data)
            owasp_category = self._extract_owasp(data)
            
            return NucleiResult(
                template_id=template_id,
                template_name=template_name,
                severity=severity,
                confidence=confidence,
                method=method,
                url=matched_url,
                path=parsed_url.get('path', '/'),
                status_code=data.get('status-code'),
                matched_at=matched_url,
                info=data.get('info', {}),
                request=request,
                response=response,
                curl_command=curl_command,
                cwe_id=cwe_id,
                owasp_category=owasp_category,
                template_path=self._get_template_path(template_id),
                raw=data,
                origin_url=url,
                origin_method=method,
                status="open"
            )
        except Exception as e:
            print(f"Error normalizing Nuclei result: {e}")
            return None
    
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
    
    def _extract_cwe(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract CWE ID from Nuclei result."""
        # Check various fields for CWE information
        info = data.get('info', {})
        
        # Check classification field
        classification = info.get('classification', {})
        if 'cwe' in classification:
            cwe = classification['cwe']
            if isinstance(cwe, list) and cwe:
                return f"CWE-{cwe[0]}"
            elif isinstance(cwe, str):
                return f"CWE-{cwe}"
        
        # Check tags
        tags = info.get('tags', [])
        for tag in tags:
            if tag.startswith('cwe-'):
                return tag.upper().replace('CWE-', 'CWE-')
        
        return None
    
    def _extract_owasp(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract OWASP category from Nuclei result."""
        info = data.get('info', {})
        
        # Check classification field
        classification = info.get('classification', {})
        if 'owasp' in classification:
            owasp = classification['owasp']
            if isinstance(owasp, list) and owasp:
                return owasp[0]
            elif isinstance(owasp, str):
                return owasp
        
        # Check tags
        tags = info.get('tags', [])
        for tag in tags:
            if tag.startswith('owasp-'):
                return tag.upper()
        
        return None
    
    def cleanup(self):
        """Cleanup temporary files."""
        try:
            import shutil
            shutil.rmtree(self.output_dir, ignore_errors=True)
        except Exception:
            pass

# Global instance
nuclei_wrapper = NucleiWrapper()
