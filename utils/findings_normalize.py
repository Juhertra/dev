"""
Findings normalization utility for Phase 4A
Ensures all findings conform to findings.schema.json before storage
"""
import re
import time
from typing import Any, Dict, Optional
from urllib.parse import urlparse


def normalize_finding(raw: Dict[str, Any], *, pid: str, run_id: str, method: str, url: str, status_code: Optional[int] = None) -> Dict[str, Any]:
    """
    Normalize a raw finding to conform to findings.schema.json.
    
    Args:
        raw: Raw finding data from detector
        pid: Project ID
        run_id: Run ID
        method: HTTP method
        url: Full URL
        status_code: HTTP status code
    
    Returns:
        Normalized finding dict conforming to schema
        
    Examples:
        >>> # Test nuclei with OWASP text cleanup
        >>> raw = {"detector_id": "nuclei:http-missing-security-headers", "severity": "INFO", "owasp": "A05:2021-Security Misconfiguration"}
        >>> norm = normalize_finding(raw, pid="test", run_id="run1", method="GET", url="https://example.com/api/users")
        >>> norm["detector_id"]
        'nuclei.http-missing-security-headers'
        >>> norm["owasp"]
        'A05:2021'
        
        >>> # Test numeric CWE formatting
        >>> raw = {"detector_id": "pattern:test", "cwe": "79"}
        >>> norm = normalize_finding(raw, pid="test", run_id="run1", method="GET", url="https://example.com/api/users")
        >>> norm["cwe"]
        'CWE-79'
        
        >>> # Test URL path extraction
        >>> raw = {"detector_id": "pattern:test"}
        >>> norm = normalize_finding(raw, pid="test", run_id="run1", method="GET", url="https://example.com/api/users/123")
        >>> norm["path"]
        '/api/users/123'
    """
    
    # Normalize detector_id
    detector_id = raw.get("detector_id", "unknown")
    if detector_id.startswith("pattern:"):
        detector_id = detector_id.replace(":", "_")
    elif detector_id.startswith("nuclei:"):
        detector_id = detector_id.replace(":", ".")
    elif not detector_id.startswith("nuclei."):
        detector_id = f"nuclei.{detector_id}"
    
    # Validate detector_id pattern
    if not re.match(r'^[A-Za-z0-9][A-Za-z0-9._-]*$', detector_id):
        detector_id = "unknown"
    
    # Normalize severity
    severity = raw.get("severity", "info")
    if isinstance(severity, str):
        severity = severity.lower()
    if severity not in ["critical", "high", "medium", "low", "info"]:
        severity = "info"
    
    # Normalize created_at to ISO UTC format
    created_at = raw.get("created_at") or raw.get("ts")
    if isinstance(created_at, int):
        created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(created_at))
    elif isinstance(created_at, str):
        # Ensure it ends with Z for UTC
        if not created_at.endswith('Z'):
            created_at = created_at + 'Z' if 'T' in created_at else time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    else:
        created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    # Extract path from URL
    path = "/"
    if url:
        try:
            parsed = urlparse(url)
            path = parsed.path or "/"
        except Exception:
            path = "/"
    
    # Normalize status field
    status = raw.get("status", "open")
    if isinstance(status, int):
        status = "open"  # Convert int status to default string
    elif not isinstance(status, str):
        status = "open"
    
    # Normalize confidence to int
    confidence = raw.get("confidence", 50)
    if isinstance(confidence, str):
        try:
            confidence = int(confidence)
        except ValueError:
            confidence = 50
    elif not isinstance(confidence, int):
        confidence = 50
    
    # Ensure confidence is in valid range
    confidence = max(0, min(100, confidence))
    
    # Normalize OWASP (keep only A##:#### format)
    owasp = raw.get("owasp")
    if owasp and isinstance(owasp, str):
        match = re.match(r'^(A\d{2}:\d{4})', owasp)
        owasp = match.group(1) if match else None
    else:
        owasp = None
    
    # Normalize CWE
    cwe = raw.get("cwe")
    if cwe:
        if isinstance(cwe, (int, str)) and str(cwe).isdigit():
            cwe = f"CWE-{cwe}"
        elif isinstance(cwe, str) and not cwe.startswith("CWE-"):
            cwe = f"CWE-{cwe}"
        elif not re.match(r'^CWE-\d+$', str(cwe)):
            cwe = None
    else:
        cwe = None
    
    # Normalize CVE (reject placeholders)
    cve_id = raw.get("cve_id")
    if cve_id and isinstance(cve_id, str):
        if not re.match(r'^CVE-\d{4}-\d+$', cve_id) or cve_id in ['CVE-0000-0000', 'CVE-0000-0001', 'CVE-0000-0002']:
            cve_id = None
    else:
        cve_id = None
    
    # Ensure req/res objects exist
    req = raw.get("req", {})
    if not isinstance(req, dict):
        req = {}
    
    # Ensure req has required fields
    req.setdefault("headers", {})
    req.setdefault("body", "")
    req.setdefault("method", method)
    req.setdefault("url", url)
    
    res = raw.get("res", {})
    if not isinstance(res, dict):
        res = {}
    
    # Ensure res has required fields
    res.setdefault("headers", {})
    res.setdefault("body", "")
    res.setdefault("status_code", status_code or 0)
    
    # Build normalized finding
    normalized = {
        "detector_id": detector_id,
        "severity": severity,
        "method": method,
        "url": url,
        "path": path,
        "title": raw.get("title", "Security Finding"),
        "confidence": confidence,
        "status": status,
        "req": req,
        "res": res,
        "created_at": created_at,
        "pid": pid,
        "run_id": run_id,
    }
    
    # Add optional fields if they exist and are valid
    if owasp:
        normalized["owasp"] = owasp
    
    if cwe:
        normalized["cwe"] = cwe
    
    if cve_id:
        normalized["cve_id"] = cve_id
    
    # Handle subcategory validation - map to valid enum values
    subcategory = raw.get("subcategory")
    if subcategory:
        valid_subcategories = ['sqli', 'xss', 'rce', 'ssrf', 'xxe', 'idor', 'authentication', 'authorization', 'misconfig', 'info-disclosure']
        if subcategory not in valid_subcategories:
            # Map common subcategories to valid values
            subcategory_lower = subcategory.lower()
            if any(keyword in subcategory_lower for keyword in ['rate', 'limit', 'header', 'security', 'cors']):
                normalized["subcategory"] = "misconfig"
            elif any(keyword in subcategory_lower for keyword in ['jwt', 'auth', 'login']):
                normalized["subcategory"] = "authentication"
            elif any(keyword in subcategory_lower for keyword in ['sql', 'injection']):
                normalized["subcategory"] = "sqli"
            elif any(keyword in subcategory_lower for keyword in ['xss', 'script']):
                normalized["subcategory"] = "xss"
            elif any(keyword in subcategory_lower for keyword in ['server', 'tech', 'disclosure', 'info']):
                normalized["subcategory"] = "info-disclosure"
            else:
                normalized["subcategory"] = "misconfig"  # Default fallback
        else:
            normalized["subcategory"] = subcategory
    
    # Add other optional fields from raw finding
    optional_fields = [
        "owasp_api", "evidence", "source", "description", 
        "remediation", "reference", "author", "matched_at", "request", 
        "response", "curl_command", "status_code", "meta", "tags", "cvss",
        "affected_component", "evidence_anchors", "suggested_remediation",
        "match", "param", "triage_info"
    ]
    
    for field in optional_fields:
        if field in raw and raw[field] is not None:
            normalized[field] = raw[field]
    
    return normalized


if __name__ == "__main__":
    import doctest
    doctest.testmod()
