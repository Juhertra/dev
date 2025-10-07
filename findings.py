from __future__ import annotations
import os, re, json, hashlib, logging, time
from typing import Any, Dict, List, Optional, Callable, Iterable, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime

logger = logging.getLogger(__name__)

from core import read_json, write_json, _json_safe
from store import STORE_DIR

# Try to import cache decorator with fallback
try:
    from cache import cached, invalidate_cache
except ImportError:
    # Fallback decorator if cache is not available
    def cached(ttl_seconds=60):
        def decorator(func):
            return func
        return decorator
    def invalidate_cache(pattern=None):
        pass

# ============================================================
# Storage config
# ============================================================

FILENAME_SUFFIX = ".findings.json"
MAX_FINDINGS = 2000           # keep a rolling window
FINDINGS_VERSION = "0.3"      # bump when schema changes

def _findings_path(pid: str) -> str:
    return os.path.join(STORE_DIR, f"{pid}{FILENAME_SUFFIX}")

def _read_findings(pid: str) -> List[Dict[str, Any]]:
    return read_json(_findings_path(pid), [])

def _write_findings(pid: str, rows: List[Dict[str, Any]]):
    write_json(_findings_path(pid), rows)

def get_findings(pid: str) -> List[Dict[str, Any]]:
    return _read_findings(pid)

def count_findings(pid: str) -> int:
    return len(_read_findings(pid))

# Stage 4: Light caching for count_findings
# Import cached decorator locally to avoid circular imports

@cached(ttl_seconds=60)
def count_findings_cached(pid: str) -> int:
    """Cached version of count_findings for better performance."""
    return len(_read_findings(pid))

def clear_findings(pid: str):
    _write_findings(pid, [])
    # Invalidate cache for this project
    invalidate_cache(f"count_findings_cached:('{pid}',)")

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

def append_findings(pid: str, items: List[Dict[str, Any]]):
    if not items: return
    
    # Validate only the new items against schema before adding to existing data
    try:
        from utils.schema_validation import validate_json
        if not validate_json(items, "findings.schema.json", f"findings_append_{pid}"):
            # Log specific detector_id for debugging
            detector_ids = [item.get("detector_id", "unknown") for item in items]
            logger.warning(f"SCHEMA_VALIDATION_FAIL pid={pid} err=\"schema validation failed\" detector_id={detector_ids[0] if detector_ids else 'unknown'}")
            return
        else:
            logger.info(f"SCHEMA_VALIDATION_OK pid={pid} count={len(items)}")
    except Exception as e:
        logger.warning(f"SCHEMA_VALIDATION_FAIL pid={pid} err=\"{str(e)}\" detector_id=unknown")
        return
    
    # Only add to storage if validation passed
    rows = _read_findings(pid)
    rows.extend(items)
    if len(rows) > MAX_FINDINGS:
        rows = rows[-MAX_FINDINGS:]
    
    _write_findings(pid, rows)
    # Invalidate cache for this project
    invalidate_cache(f"count_findings_cached:('{pid}',)")
    
    # Bust vulns summary cache (Phase 4A)
    try:
        from store import _bust_vulns_cache
        _bust_vulns_cache(pid)
    except Exception as e:
        logger.warning(f"VULNS_CACHE_BUST_ERROR pid={pid} error={str(e)}")

# ============================================================
# Finding model
# ============================================================

@dataclass
class Finding:
    # identity
    id: str
    pid: str
    version: str
    ts: str

    # classification
    title: str
    severity: str                         # "info" | "low" | "medium" | "high" | "critical"
    detector_id: str
    owasp: Optional[str] = None           # e.g., "A05:2021-Security Misconfiguration"
    owasp_api: Optional[str] = None       # e.g., "API1:2023-BOLA"
    cwe: Optional[str] = None             # e.g., "CWE-284"

    # enrichment fields (Phase 4A)
    cve_id: Optional[str] = None          # e.g., "CVE-2023-1234"
    affected_component: Optional[str] = None  # e.g., "database", "authentication"
    evidence_anchors: List[str] = field(default_factory=list)  # e.g., ["line:45", "param:user_id"]
    suggested_remediation: Optional[str] = None  # e.g., "Use parameterized queries"

    # evidence + context
    detail: Optional[str] = None
    evidence: Optional[str] = None
    match: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    subcategory: Optional[str] = None
    confidence: int = 50  # Pattern engine confidence (0-100)

    # HTTP snapshot
    method: Optional[str] = None
    url: Optional[str] = None
    status: Optional[int] = None
    req: Dict[str, Any] = field(default_factory=dict)
    res: Dict[str, Any] = field(default_factory=dict)

    def asdict(self) -> Dict[str, Any]:
        return asdict(self)

def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def _mk_id(pid: str, detector_id: str, url: Optional[str], extra: Optional[str] = None) -> str:
    h = hashlib.sha256()
    h.update((pid or "-").encode())
    h.update((detector_id or "-").encode())
    h.update((url or "-").encode())
    if extra:
        h.update(extra.encode())
    return h.hexdigest()[:16]

def _snippet(text: str, limit: int = 240) -> str:
    s = (text or "").replace("\r", " ").replace("\n", " ")
    return s[:limit] + ("…" if len(s) > limit else "")

# ============================================================
# Detector registry
# ============================================================

DetectorFn = Callable[[Dict[str, Any], Dict[str, Any], Dict[str, Any]], Iterable[Finding]]
_DETECTORS: List[Tuple[str, DetectorFn, Dict[str, Any]]] = []

def register_detector(detector_id: str, **meta):
    def _wrap(fn: DetectorFn):
        _DETECTORS.append((detector_id, fn, meta))
        return fn
    return _wrap

# ============================================================
# Helpers for detectors
# ============================================================

_SQL_ERROR_PATTERNS = [
    r"SQL syntax", r"You have an error in your SQL", r"ORA-\d+",
    r"Unclosed quotation mark after the character string", r"PG::SyntaxError",
    r"psql:\s*error", r"mysql_fetch_", r"SQLSTATE\[",
]

_STACKTRACE_MARKERS = [
    "Traceback (most recent call last)", "NullPointerException", "Stack trace:",
    "at org.", "at com.", "at sun.", "at java.", "System.ArgumentException",
    "Microsoft.SqlServer", "HttpUnhandledException"
]

_PII_PATTERNS = {
    "email": re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE),
    "credit_card": re.compile(r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5]\d{14}|3[47]\d{13}|6(?:011|5\d{2})\d{12})\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}

def _lower_headers(hdrs: Optional[Dict[str, Any]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k, v in (hdrs or {}).items():
        try:
            out[str(k).lower()] = str(v)
        except Exception:
            pass
    return out

def _iter_request_string_tokens(pre: Dict[str, Any]) -> Iterable[Tuple[str, Optional[str], str]]:
    # source, key, token
    for source, obj in (("query", pre.get("query")),
                        ("json", pre.get("json")),
                        ("form", pre.get("data") if isinstance(pre.get("data"), dict) else None),
                        ("cookies", pre.get("cookies")),
                        ("headers", pre.get("headers"))):
        if not obj:
            continue
        if isinstance(obj, dict):
            for k, v in obj.items():
                for tok in _iter_string_tokens(v):
                    yield source, k, tok
        else:
            for tok in _iter_string_tokens(obj):
                yield source, None, tok

def _iter_string_tokens(value: Any, max_len: int = 150):
    try:
        if isinstance(value, str):
            v = value.strip()
            if v and len(v) <= max_len:
                yield v
        elif isinstance(value, dict):
            for _, v in value.items():
                yield from _iter_string_tokens(v, max_len)
        elif isinstance(value, list):
            for v in value:
                yield from _iter_string_tokens(v, max_len)
    except Exception:
        return

def _ok_token(t: str) -> bool:
    t = t.strip()
    if len(t) < 4: return False
    if t.isdigit(): return False
    low = t.lower()
    if low in {"true", "false", "null", "none"}: return False
    return any(c.isalpha() for c in t)

def _classify_html_context(html: str, token: str) -> Tuple[str, str]:
    # context, severity
    try:
        if re.search(r"<script[^>]*>[\s\S]*?" + re.escape(token) + r"[\s\S]*?</script>", html, re.I):
            return "script", "high"
        if re.search(r"on\w+\s*=\s*(['\"]).*?" + re.escape(token) + r".*?\1", html, re.I):
            return "event_attr", "high"
        if re.search(r"\b(href|src)\s*=\s*(['\"]).*?" + re.escape(token) + r".*?\2", html, re.I):
            return "url_attr", "medium"
        if re.search(r"<[^>]+?=\s*(['\"]).*?" + re.escape(token) + r".*?\1", html, re.I):
            return "attr", "medium"
        if re.search(r">[^<]*?" + re.escape(token) + r"[^<]*?<", html):
            return "text", "low"
    except Exception:
        pass
    return "unknown", "low"

# ============================================================
# Passive detectors (OWASP / OWASP API aligned)
# ============================================================

@register_detector(
    "sql_error",
    owasp="A03:2021-Injection",
    cwe="CWE-89"
)
def det_sql_error(pre, res, ctx):
    body = res.get("body") or ""
    for pat in _SQL_ERROR_PATTERNS:
        if re.search(pat, body, re.I):
            yield Finding(
                id=_mk_id(ctx["pid"], "sql_error", pre.get("url"), pat),
                pid=ctx["pid"], version=FINDINGS_VERSION, ts=_now_iso(),
                detector_id="sql_error", title="SQL error pattern in response",
                severity="high", owasp="A03:2021-Injection", cwe="CWE-89",
                detail=f"Matched pattern: {pat}",
                evidence=_snippet(body),
                subcategory="SQL error leaked",
                match=pat, method=pre.get("method"), url=pre.get("url"),
                status=res.get("status"), req=ctx["req_obj"], res=ctx["res_obj"],
                tags=["error", "db", "injection"],
                confidence=85  # High confidence for SQL error patterns
            )

@register_detector(
    "stacktrace",
    owasp="A05:2021-Security Misconfiguration",
    cwe="CWE-209"
)
def det_stacktrace(pre, res, ctx):
    body = res.get("body") or ""
    for m in _STACKTRACE_MARKERS:
        if m in body:
            yield Finding(
                id=_mk_id(ctx["pid"], "stacktrace", pre.get("url"), m),
                pid=ctx["pid"], version=FINDINGS_VERSION, ts=_now_iso(),
                detector_id="stacktrace", title="Stack trace leaked in response",
                severity="medium", owasp="A05:2021-Security Misconfiguration", cwe="CWE-209",
                detail=f"Found marker: {m}",
                evidence=_snippet(body),
                subcategory="Debug stack trace leaked",
                match=m, method=pre.get("method"), url=pre.get("url"),
                status=res.get("status"), req=ctx["req_obj"], res=ctx["res_obj"],
                tags=["error", "debug"]
            )

@register_detector(
    "cors_star_with_credentials",
    owasp="A05:2021-Security Misconfiguration",
    cwe="CWE-346"
)
def det_cors_misconfig(pre, res, ctx):
    hdrs = _lower_headers(res.get("headers"))
    acao = (hdrs.get("access-control-allow-origin") or "").strip()
    acac = (hdrs.get("access-control-allow-credentials") or "").strip().lower()
    if acao == "*" and acac == "true":
        yield Finding(
            id=_mk_id(ctx["pid"], "cors_star_with_credentials", pre.get("url")),
            pid=ctx["pid"], version=FINDINGS_VERSION, ts=_now_iso(),
            detector_id="cors_star_with_credentials",
            title="CORS misconfiguration: '*' with credentials",
            severity="high", owasp="A05:2021-Security Misconfiguration", cwe="CWE-346",
            detail="ACAO is '*' while ACAC is true",
            evidence=f"ACAO={acao}, ACAC={acac}",
            subcategory="CORS: * + credentials",
            method=pre.get("method"), url=pre.get("url"),
            status=res.get("status"), req=ctx["req_obj"], res=ctx["res_obj"],
            tags=["cors", "misconfig"]
        )

@register_detector(
    "sec_headers_missing",
    owasp="A05:2021-Security Misconfiguration",
    cwe="CWE-693"
)
def det_security_headers(pre, res, ctx):
    # Disabled - pattern engine provides more specific header findings
    return
    hdrs_full = res.get("headers") or {}
    missing_full = _which_missing_headers(hdrs_full)
    # Map to short labels for concise detail
    missing = []
    for name in missing_full:
        if name.startswith("Content-Security-Policy"):
            missing.append("CSP")
        elif name.startswith("Strict-Transport-Security"):
            missing.append("HSTS")
        else:
            missing.append(name)
    if missing:
        core = {"CSP", "X-Frame-Options", "X-Content-Type-Options", "Referrer-Policy"}
        sev = "medium" if any(x in core for x in missing) else "low"
        yield Finding(
            id=_mk_id(ctx["pid"], "sec_headers_missing", pre.get("url"), ",".join(missing)),
            pid=ctx["pid"], version=FINDINGS_VERSION, ts=_now_iso(),
            detector_id="sec_headers_missing",
            title="Missing recommended security headers",
            severity=sev, owasp="A05:2021-Security Misconfiguration",
            detail="Missing: " + ", ".join(missing),
            evidence="", subcategory="Security headers missing",
            method=pre.get("method"), url=pre.get("url"),
            status=res.get("status"), req=ctx["req_obj"], res=ctx["res_obj"],
            tags=["headers", "hardening"],
            confidence=80  # High confidence for missing headers
        )

@register_detector(
    "server_tech_disclosure",
    owasp="A05:2021-Security Misconfiguration",
    cwe="CWE-200"
)
def det_server_tech_disclosure(pre, res, ctx):
    hdrs = _lower_headers(res.get("headers"))
    leaks = []
    if "server" in hdrs and hdrs["server"].strip():
        leaks.append(f"Server: {hdrs['server']}")
    if "x-powered-by" in hdrs and hdrs["x-powered-by"].strip():
        leaks.append(f"X-Powered-By: {hdrs['x-powered-by']}")
    if leaks:
        yield Finding(
            id=_mk_id(ctx["pid"], "server_tech_disclosure", pre.get("url"), ";".join(leaks)),
            pid=ctx["pid"], version=FINDINGS_VERSION, ts=_now_iso(),
            detector_id="server_tech_disclosure",
            title="Server technology disclosed in headers",
            severity="low", owasp="A05:2021-Security Misconfiguration", cwe="CWE-200",
            detail="; ".join(leaks),
            evidence="",
            subcategory="Server header disclosed",
            method=pre.get("method"), url=pre.get("url"),
            status=res.get("status"), req=ctx["req_obj"], res=ctx["res_obj"],
            tags=["info-leak", "headers"]
        )

@register_detector(
    "dir_listing",
    owasp="A01:2021-Broken Access Control",
    cwe="CWE-548"
)
def det_dir_listing(pre, res, ctx):
    body = res.get("body") or ""
    if "<title>Index of /" in body or "<h1>Index of /" in body:
        yield Finding(
            id=_mk_id(ctx["pid"], "dir_listing", pre.get("url")),
            pid=ctx["pid"], version=FINDINGS_VERSION, ts=_now_iso(),
            detector_id="dir_listing", title="Directory listing exposed",
            severity="low", owasp="A05:2021-Security Misconfiguration", cwe="CWE-548",
            detail="Index of / detected",
            evidence=_snippet(body), subcategory="Directory listing enabled",
            method=pre.get("method"), url=pre.get("url"),
            status=res.get("status"), req=ctx["req_obj"], res=ctx["res_obj"],
            tags=["listing"]
        )

@register_detector(
    "reflected_input",
    owasp="A03:2021-Injection",
    cwe="CWE-79"
)
def det_reflection(pre, res, ctx):
    body = res.get("body") or ""
    ctype = (res.get("content_type") or "").lower()
    # collect candidate tokens from request
    seen = set()
    for source, name, tok in _iter_request_string_tokens(pre):
        if not _ok_token(tok): continue
        key = (source, name, tok.lower())
        if key in seen: continue
        seen.add(key)

        if tok.lower() not in body.lower():
            continue

        if "application/json" in ctype:
            yield Finding(
                id=_mk_id(ctx["pid"], "reflected_input", pre.get("url"), tok),
                pid=ctx["pid"], version=FINDINGS_VERSION, ts=_now_iso(),
                detector_id="reflected_input",
                title="Input reflected in JSON response",
                severity="low", owasp="A03:2021-Injection", cwe="CWE-200",
                detail=f"{source} parameter '{name}' value echoed (JSON)",
                evidence=_snippet(tok), subcategory="Reflection (JSON)", match=tok,
                method=pre.get("method"), url=pre.get("url"),
                status=res.get("status"), req=ctx["req_obj"], res=ctx["res_obj"],
                tags=["reflection", "json"],
                confidence=75  # High confidence for JSON reflection
            )
        else:
            ctx_name, sev = _classify_html_context(body, tok)
            yield Finding(
                id=_mk_id(ctx["pid"], "reflected_input", pre.get("url"), tok + ":" + ctx_name),
                pid=ctx["pid"], version=FINDINGS_VERSION, ts=_now_iso(),
                detector_id="reflected_input",
                title="Reflected input in response",
                severity=sev, owasp="A03:2021-Injection", cwe="CWE-79",
                detail=f"{source} parameter '{name}' value reflected ({ctx_name})",
                evidence=_snippet(tok), subcategory=f"Reflection ({ctx_name})", match=tok,
                method=pre.get("method"), url=pre.get("url"),
                status=res.get("status"), req=ctx["req_obj"], res=ctx["res_obj"],
                tags=["reflection", ctx_name],
                confidence=80  # High confidence for HTML reflection
            )

@register_detector(
    "pii_disclosure",
    owasp="A02:2021-Cryptographic Failures",
    cwe="CWE-359"
)
def det_pii(pre, res, ctx):
    body = (res.get("body") or "")[:8000]
    hits = []
    for name, rx in _PII_PATTERNS.items():
        if rx.search(body):
            hits.append(name)
    if hits:
        yield Finding(
            id=_mk_id(ctx["pid"], "pii_disclosure", pre.get("url"), ",".join(sorted(set(hits)))),
            pid=ctx["pid"], version=FINDINGS_VERSION, ts=_now_iso(),
            detector_id="pii_disclosure",
            title="Potential PII disclosed in response",
            severity="medium", owasp="A02:2021-Cryptographic Failures", cwe="CWE-359",
            detail="Detected patterns: " + ", ".join(sorted(set(hits))),
            evidence=_snippet(body),
            subcategory="PII patterns observed",
            method=pre.get("method"), url=pre.get("url"),
            status=res.get("status"), req=ctx["req_obj"], res=ctx["res_obj"],
            tags=["pii", "data-exposure"]
        )

@register_detector(
    "api_auth_bola_heuristic",
    owasp_api="API1:2023-Broken Object Level Authorization",
    cwe="CWE-639"
)
def det_api_bola_heuristic(pre, res, ctx):
    """
    Heuristic: 2xx response to 'object-like' paths (/users/{id}, /accounts/123, /admin) without any Authorization.
    Not proof; we record as medium/info depending on path.
    """
    url = pre.get("url") or ""
    method = (pre.get("method") or "").upper()
    status = res.get("status") or 0
    hdrs = _lower_headers(pre.get("headers"))
    has_auth = "authorization" in hdrs or "cookie" in hdrs  # crude
    path = url.split("?", 1)[0]

    looks_object = re.search(r"/(users?|accounts?|orders?|items?|profiles?)/(\d+|[0-9a-fA-F-]{8,})\b", path)
    adminish = re.search(r"/(admin|root|superuser)\b", path)

    if method in {"GET","PUT","PATCH","DELETE"} and status and 200 <= status < 300 and not has_auth and (looks_object or adminish):
        sev = "medium" if adminish else "low"
        yield Finding(
            id=_mk_id(ctx["pid"], "api_auth_bola_heuristic", url, method),
            pid=ctx["pid"], version=FINDINGS_VERSION, ts=_now_iso(),
            detector_id="api_auth_bola_heuristic",
            title="Possibly unprotected object endpoint (heuristic)",
            severity=sev, owasp_api="API1:2023-BOLA", cwe="CWE-639",
            detail="2xx on object-like or admin path without Authorization header",
            evidence=path, subcategory="Possibly unprotected object endpoint",
            method=method, url=url, status=status,
            req=ctx["req_obj"], res=ctx["res_obj"],
            tags=["auth", "bola", "heuristic"],
            confidence=60  # Medium confidence for BOLA heuristic
        )

@register_detector(
    "api_rate_limit_headers_missing",
    owasp_api="API9:2023-Imprecise Rate Limiting",
    cwe="CWE-770"
)
def det_rate_limit_headers(pre, res, ctx):
    # Purely informational: warn when common RL headers are absent.
    hdrs = _lower_headers(res.get("headers"))
    keys = [k for k in hdrs.keys() if k.startswith("x-ratelimit") or k in {"retry-after"}]
    if not keys:
        yield Finding(
            id=_mk_id(ctx["pid"], "api_rate_limit_headers_missing", pre.get("url")),
            pid=ctx["pid"], version=FINDINGS_VERSION, ts=_now_iso(),
            detector_id="api_rate_limit_headers_missing",
            title="No rate limiting headers observed",
            severity="info", owasp_api="API9:2023-Imprecise Rate Limiting",
            detail="Common rate limit headers (X-RateLimit-*, Retry-After) not present",
            evidence="", subcategory="Rate limiting headers missing",
            method=pre.get("method"), url=pre.get("url"),
            status=res.get("status"), req=ctx["req_obj"], res=ctx["res_obj"],
            tags=["rate-limit", "observability"],
            confidence=70  # Medium confidence for missing rate limit headers
        )

# ============================================================
# Analyzer entrypoints
# ============================================================

def _build_req_obj(pre: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "method": pre.get("method"),
        "url": pre.get("url"),
        "headers": _json_safe(pre.get("headers") or {}),
        "query": _json_safe(pre.get("query") or {}),
        "cookies": _json_safe(pre.get("cookies") or {}),
        "json": _json_safe(pre.get("json")),
        "data": _json_safe(pre.get("data")),
    }

def _build_res_obj(resp) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}
    status = None
    reason = None
    body_text = ""
    
    # Handle both response objects and dictionaries
    if isinstance(resp, dict):
        headers = resp.get("headers", {})
        status = resp.get("status")
        reason = resp.get("reason")
        body_text = resp.get("body", "")
    else:
        try:
            headers = dict(resp.headers or {})
            status = getattr(resp, "status_code", None)
            reason = getattr(resp, "reason", None)
            body_text = ""
            try:
                body_text = resp.text or ""
            except Exception:
                body_text = ""
        except Exception:
            pass
    
    return {
        "status": status, "reason": reason, "headers": headers,
        "body": body_text[:8000] if isinstance(body_text, str) else "",
        "content_type": headers.get("Content-Type") if isinstance(headers, dict) else None,
    }

def _dedupe(items: List[Any]) -> List[Any]:
    seen = set()
    out: List[Any] = []
    for f in items:
        # Handle both Finding objects and dictionaries
        if isinstance(f, dict):
            detector_id = f.get('detector_id', '')
            url = f.get('url', '')
            title = f.get('title', '')
        else:
            detector_id = f.detector_id
            url = f.url
            title = f.title
        
        # Use detector_id + url + title as the deduplication key
        # This allows different detectors to find different issues on the same URL
        key = (detector_id, url, title)
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out

def analyze_and_record(
    pid: str,
    pre: Dict[str, Any],
    resp: Optional[Any] = None,
    error: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Runs all passive detectors on (request preview + response).
    Records findings to disk for the given project id.
    """
    ts = _now_iso()
    req_obj = _build_req_obj(pre)
    res_obj = _build_res_obj(resp) if resp is not None else {"status": None, "reason": None, "headers": {}, "body": "", "content_type": None}

    ctx = {"pid": pid, "req_obj": req_obj, "res_obj": res_obj}

    findings: List[Dict[str, Any]] = []
    # Error channel
    if error:
        exception_finding = Finding(
            id=_mk_id(pid, "exception", pre.get("url"), error[:80]),
            pid=pid, version=FINDINGS_VERSION, ts=ts,
            detector_id="exception", title="Request error",
            severity="medium", owasp=None, detail=error, evidence=_snippet(error),
            method=pre.get("method"), url=pre.get("url"),
            status=res_obj.get("status"), req=req_obj, res=res_obj, tags=["exception"]
        )
        # Convert Finding object to dict and normalize
        finding_dict = exception_finding.asdict()
        from utils.findings_normalize import normalize_finding
        normalized = normalize_finding(
            finding_dict,
            pid=pid,
            run_id=f"exception_{int(time.time())}",
            method=pre.get("method", "GET"),
            url=pre.get("url", ""),
            status_code=res_obj.get("status")
        )
        findings.append(normalized)

    # Passive detectors
    for det_id, fn, meta in _DETECTORS:
        try:
            for f in fn(pre, res_obj, ctx) or []:
                # inherit OWASP/API/CWE metadata defaults from decorator if finder didn't set them
                if not f.owasp and meta.get("owasp"): f.owasp = meta["owasp"]
                if not f.owasp_api and meta.get("owasp_api"): f.owasp_api = meta["owasp_api"]
                if not f.cwe and meta.get("cwe"): f.cwe = meta["cwe"]
                
                # Convert Finding object to dict and normalize
                finding_dict = f.asdict()
                from utils.findings_normalize import normalize_finding
                normalized = normalize_finding(
                    finding_dict,
                    pid=pid,
                    run_id=f"legacy_{int(time.time())}",
                    method=pre.get("method", "GET"),
                    url=pre.get("url", ""),
                    status_code=res_obj.get("status")
                )
                findings.append(normalized)
        except Exception:
            # detector errors are non-fatal
            continue

    # Pattern engine enrichment (new) - use enhanced pattern engine
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        pattern_dir = os.path.join(base_dir, "detectors", "patterns")
        if os.path.isdir(pattern_dir):
            from detectors.pattern_engine import PatternEngine
            engine = PatternEngine(pattern_dir)
            engine.reload()  # Ensure patterns are loaded
            
            # Prepare request/response data for pattern engine
            req_blob = {
                "url": pre.get("url"),
                "headers": pre.get("headers") or {},
                "cookies": pre.get("cookies") or {},
                "query": pre.get("query") or {},
                "json": pre.get("json"),
                "data": pre.get("data"),
            }
            
            res_blob = {
                "status": res_obj.get("status"),
                "headers": res_obj.get("headers") or {},
                "body": res_obj.get("body") or "",
            }
            
            logger.info(f"PATTERN_ENGINE_INPUT req_headers={req_blob['headers']} res_headers={res_blob['headers']}")
            
            # Run pattern detection
            pattern_findings = engine.detect(req_blob, res_blob)
            logger.info(f"DETECTORS_RUN key=\"{pre.get('url', '')}\" findings={len(pattern_findings)}")
            
            # Convert pattern findings using normalize_finding
            for pf in pattern_findings:
                # Use normalize_finding to ensure schema compliance
                from utils.findings_normalize import normalize_finding
                normalized = normalize_finding(
                    pf,
                    pid=pid,
                    run_id=f"pattern_{int(time.time())}",  # Generate run_id for pattern findings
                    method=pre.get("method", "GET"),
                    url=pre.get("url", ""),
                    status_code=res_obj.get("status")
                )
                findings.append(normalized)
    except Exception as e:
        # Pattern engine errors are non-fatal, but log them for debugging
        logger.warning(f"PATTERN_ENGINE_ERROR pid={pid} error={str(e)}")
        pass

    findings = _dedupe(findings)
    if findings:
        # All findings are already normalized dicts
        append_findings(pid, findings)
        return findings

# ============================================================
# Optional: reflection-only helper (kept for compatibility)
# ============================================================

def analyze_reflection_owasp_only(pid: str, pre: Dict[str, Any], res_obj: Dict[str, Any], body_text: str) -> List[Dict[str, Any]]:
    # Build a minimal ctx and run only the reflection detector
    ctx = {"pid": pid, "req_obj": _build_req_obj(pre), "res_obj": {"status": res_obj.get("status"), "reason": res_obj.get("reason"),
            "headers": res_obj.get("headers") or {}, "body": body_text[:8000], "content_type": res_obj.get("content_type")}}
    items = []
    try:
        for f in det_reflection(pre, ctx["res_obj"], ctx):  # direct call
            items.append(f)
    except Exception:
        pass
    if items:
        append_findings(pid, [f.asdict() for f in _dedupe(items)])
    return [f.asdict() for f in items]

# ============================================================
# Future: active fuzzing scaffold (no hardcoded payloads)
# ============================================================

class PayloadSource:
    """
    Pluggable payload provider (SecLists, custom dirs, etc.).
    Not used by passive detectors. For future active tests.
    """
    def __init__(self, roots: List[str]):
        self.roots = roots

    def iter_lines(self, relpath: str) -> Iterable[str]:
        for root in self.roots:
            p = os.path.join(root, relpath)
            if os.path.isfile(p):
                with open(p, "r", errors="ignore") as fh:
                    for line in fh:
                        yield line.rstrip("\n")

# Example future use:
# src = PayloadSource([os.environ.get("SECLISTS_DIR", "/opt/seclists")])
# for payload in src.iter_lines("Fuzzing/SQLi/Generic-SQLi.txt"): ...

# ===========================
# OWASP category explanations
# ===========================

OWASP_WEB_DETAILS = {
    "A01:2021-Broken Access Control": {
        "what": "Access controls are missing or ineffective (IDOR, forced browsing, privilege escalation).",
        "why": "Business rules aren’t consistently enforced at the resource level.",
        "risk": "Unauthorized data access/modification; lateral movement across roles/tenants.",
        "validate": "Attempt actions as a different/unauthenticated user; verify object and function authorization is enforced.",
        "remediate": [
            "Deny-by-default: authorize every request server-side.",
            "Enforce ownership checks on object/resource access.",
            "Centralize authorization and test negative cases.",
        ],
    },
    "A02:2021-Cryptographic Failures": {
        "what": "Weak or missing cryptography for data at rest/in transit.",
        "why": "Improper TLS/cipher choices, missing encryption, or key mishandling expose data.",
        "risk": "Sensitive data disclosure, MITM attacks, compliance failures.",
        "validate": "Inspect TLS config, key usage, and data at rest encryption; verify secrets handling & rotation.",
        "remediate": [
            "Use TLS 1.2+ with strong ciphers; HSTS on web.",
            "Encrypt sensitive data at rest; manage keys securely.",
            "Avoid custom crypto; follow platform best practices.",
        ],
    },
    "A03:2021-Injection": {
        "what": "Untrusted data is interpreted as commands (SQL/NoSQL/LDAP/OS/template).",
        "why": "Concatenated queries or unsafe sinks allow attacker-controlled execution.",
        "risk": "Data exfiltration, corruption, RCE depending on sink.",
        "validate": "Fuzz parameters with meta-characters; look for errors, blind behaviors, or data leakage.",
        "remediate": [
            "Use parameterized queries/ORM binding.",
            "Apply context-aware encoding; avoid dynamic eval.",
            "Enforce input validation and least privilege.",
        ],
    },
    "A04:2021-Insecure Design": {
        "what": "Design flaws (not implementation bugs) that ignore threats and misuse cases.",
        "why": "Missing threat modeling, security requirements, and defense-in-depth.",
        "risk": "Systemic weaknesses exploitable despite correct code.",
        "validate": "Review architecture vs. abuse cases; run design reviews and misuse case tests.",
        "remediate": [
            "Adopt threat modeling and STRIDE-style reviews.",
            "Define explicit security requirements and SLAs.",
            "Layer controls; prefer secure-by-default patterns.",
        ],
    },
    "A05:2021-Security Misconfiguration": {
        "what": "Insecure defaults, verbose errors, unnecessary features/services enabled.",
        "why": "Drift, missing hardening, missing headers, or forgotten debug toggles.",
        "risk": "Information leakage and expanded attack surface.",
        "validate": "Scan configs, headers, error paths; check for default creds, open consoles, directory listing.",
        "remediate": [
            "Baseline hardening and CIS-style benchmarks.",
            "Remove unused features; lock admin consoles.",
            "Add security headers; turn off verbose errors.",
        ],
    },
    "A06:2021-Vulnerable and Outdated Components": {
        "what": "Using components with known vulnerabilities or unsupported versions.",
        "why": "Old libraries/containers bring exploitable CVEs.",
        "risk": "RCE, data exposure, or auth bypass via known bugs.",
        "validate": "SBOM and dependency scan; track CVEs, check image digests.",
        "remediate": [
            "Pin versions by digest; patch regularly.",
            "Automate dependency & image updates.",
            "Remove unused packages; verify signatures/provenance.",
        ],
    },
    "A07:2021-Identification and Authentication Failures": {
        "what": "Weak login/session/token management (bruteforce, weak JWTs, session fixation).",
        "why": "Missing MFA, poor password/lockout policies, long-lived tokens.",
        "risk": "Account takeover, credential stuffing success.",
        "validate": "Check MFA, session rotation, lockout, and token claims (`aud`, `iss`, TTL).",
        "remediate": [
            "Enforce MFA and progressive delays/lockouts.",
            "Short token TTLs; rotate/validate claims.",
            "Secure session cookies: HttpOnly, Secure, SameSite.",
        ],
    },
    "A08:2021-Software and Data Integrity Failures": {
        "what": "Unsigned or unverified updates, insecure CI/CD, or deserialization flaws.",
        "why": "Trusting untrusted code/data paths without integrity checks.",
        "risk": "Supply-chain compromise, RCE, persistent tampering.",
        "validate": "Verify signatures, build provenance, deserialization paths.",
        "remediate": [
            "Sign artifacts; verify in deployment.",
            "Harden CI/CD with least privilege & build provenance.",
            "Avoid unsafe deserialization; whitelist types.",
        ],
    },
    "A09:2021-Security Logging and Monitoring Failures": {
        "what": "Insufficient audit logs/alerts to detect or investigate attacks.",
        "why": "Missing context/retention; noisy or uncorrelated events.",
        "risk": "Delayed detection and poor incident response.",
        "validate": "Check coverage, retention, and alerting for auth, admin, data access.",
        "remediate": [
            "Log security-relevant events with context.",
            "Centralize & alert on anomalies; protect logs.",
            "Rehearse IR playbooks; verify time sync.",
        ],
    },
    "A10:2021-Server-Side Request Forgery": {
        "what": "Server makes attacker-controlled HTTP requests to internal/external targets.",
        "why": "URL fetchers trust user input; no egress or metadata service protections.",
        "risk": "Access to internal networks/IMDS, data exfiltration.",
        "validate": "Probe egress with internal/IMDS URLs; look for SSRF indicators and timeouts.",
        "remediate": [
            "Allowlist destinations; deny raw URLs from users.",
            "Block IMDS and internal address ranges at egress.",
            "Normalize & validate URLs; use SSRF-safe libraries.",
        ],
    },
}

OWASP_API_DETAILS = {
    "API1:2023-Broken Object Level Authorization": {
        "what": "Missing per-object checks (BOLA/IDOR).",
        "why": "Handlers trust user-provided IDs without verifying ownership.",
        "risk": "Cross-tenant data access/modification.",
        "validate": "Swap IDs between users; verify 403/404 and filtered results.",
        "remediate": [
            "Enforce ownership checks on every data fetch/update.",
            "Use opaque identifiers; centralize object ACLs.",
        ],
    },
    "API2:2023-Broken Authentication": {
        "what": "Weak auth (predictable sessions, weak tokens/secrets, long TTLs).",
        "why": "Improper credential, token, or session handling.",
        "risk": "Account takeover, replay and impersonation.",
        "validate": "Review login flows, token algorithms/claims/rotation, and session cookie flags.",
        "remediate": [
            "MFA, short TTLs, rotation; prefer asymmetric JWTs.",
            "Validate `aud`,`iss`,`exp`; revoke on logout.",
        ],
    },
    "API3:2023-Broken Object Property Level Authorization": {
        "what": "Field-level reads/writes allowed without fine-grained authorization (BOPLA).",
        "why": "Server accepts/returns properties regardless of caller's rights.",
        "risk": "Sensitive fields leaked or modified.",
        "validate": "Try overposting/overreading disallowed fields.",
        "remediate": [
            "Schema-based allowlists; per-field authorization.",
            "Drop unknown fields; ignore forbidden writes.",
        ],
    },
    "API4:2023-Unrestricted Resource Consumption": {
        "what": "No effective limits on requests, payloads, CPU, memory, or concurrency.",
        "why": "Lack of quotas, timeouts, and pagination.",
        "risk": "DoS or cost spikes.",
        "validate": "Burst tests and large payloads; look for 429, backoff, and server-side ceilings.",
        "remediate": [
            "Rate limits per user/IP/tenant; backpressure and queues.",
            "Pagination, size/time limits; circuit breakers.",
        ],
    },
    "API5:2023-Broken Function Level Authorization": {
        "what": "Sensitive functions reachable without proper role checks (BFLA).",
        "why": "UI-driven auth assumptions; missing server-side role validation.",
        "risk": "Privilege escalation or unauthorized admin actions.",
        "validate": "Call privileged endpoints without the expected role; verify denial.",
        "remediate": [
            "Enforce server-side RBAC/ABAC for each function.",
            "Hide is not protect: do not rely on client UI.",
        ],
    },
    "API6:2023-Unrestricted Access to Sensitive Business Flows": {
        "what": "Critical workflows are open to automation/abuse (e.g., checkout, password reset flows).",
        "why": "No friction or anomaly checks on sensitive sequences.",
        "risk": "Fraud, inventory abuse, mass automation.",
        "validate": "Automate flows; verify CAPTCHAs, anomaly detection, or step-up auth.",
        "remediate": [
            "Add friction (rate limits, CAPTCHAs, velocity checks).",
            "Step-up auth for risky flows.",
        ],
    },
    "API7:2023-Server Side Request Forgery": {
        "what": "API fetches attacker-controlled URLs (SSRF).",
        "why": "No URL allowlisting or egress controls.",
        "risk": "Internal network/IMDS access and data exfiltration.",
        "validate": "Supply internal/IMDS URLs; check egress/response.",
        "remediate": [
            "Allowlist hosts; block link-local & IMDS.",
            "Normalize & validate URLs; isolate fetchers.",
        ],
    },
    "API8:2023-Security Misconfiguration": {
        "what": "Insecure defaults, verbose errors, missing headers/config drift.",
        "why": "Lack of hardening and config management.",
        "risk": "Info disclosure and broader attack surface.",
        "validate": "Check headers, errors, consoles, directory listing, default creds.",
        "remediate": [
            "Baseline hardening and secrets management.",
            "Disable debug; add security headers.",
        ],
    },
    "API9:2023-Imprecise Rate Limiting": {
        "what": "Inconsistent/missing throttling across endpoints or identities.",
        "why": "Perimeter-only or uneven quotas; lack of 429/Retry-After.",
        "risk": "Credential stuffing, scraping, resource exhaustion.",
        "validate": "Burst per-user/IP/tenant; confirm 429 and consistent headers.",
        "remediate": [
            "Apply identity-aware quotas and backoff.",
            "Expose clear 429 semantics and `Retry-After`.",
        ],
    },
    "API10:2023-Unsafe Consumption of APIs": {
        "what": "Trusting unverified upstream schemas, data, or IDs.",
        "why": "Weak input validation and insufficient trust boundaries.",
        "risk": "Data confusion, SSRF via integrations, injection via third-party data.",
        "validate": "Fuzz upstream integrations and schema mismatches.",
        "remediate": [
            "Validate/transform upstream data; pin schemas & versions.",
            "Use timeouts, retries, and allowlists for egress.",
        ],
    },
}

# Detector → category hints (used if a detector didn't tag OWASP fields)
DETECTOR_TO_CATEGORY = {
    # Web
    "idor": "A01:2021-Broken Access Control",
    "access_control": "A01:2021-Broken Access Control",
    "crypto": "A02:2021-Cryptographic Failures",
    "tls": "A02:2021-Cryptographic Failures",
    "injection": "A03:2021-Injection",
    "sql": "A03:2021-Injection",
    "xss": "A03:2021-Injection",
    "insecure_design": "A04:2021-Insecure Design",
    "misconfig": "A05:2021-Security Misconfiguration",
    "sec_headers_missing": "A05:2021-Security Misconfiguration",
    "server_tech_disclosure": "A05:2021-Security Misconfiguration",
    "vuln_components": "A06:2021-Vulnerable and Outdated Components",
    "auth_fail": "A07:2021-Identification and Authentication Failures",
    "jwt_weak": "A07:2021-Identification and Authentication Failures",
    "integrity": "A08:2021-Software and Data Integrity Failures",
    "logging": "A09:2021-Security Logging and Monitoring Failures",
    "monitoring": "A09:2021-Security Logging and Monitoring Failures",
    "ssrf": "A10:2021-Server-Side Request Forgery",
    # Nuclei detectors
    "nuclei::": "A05:2021-Security Misconfiguration",  # Default for Nuclei findings
    # API
    "api_auth_bola": "API1:2023-Broken Object Level Authorization",
    "bola": "API1:2023-Broken Object Level Authorization",
    "api_broken_auth": "API2:2023-Broken Authentication",
    "api_bopla": "API3:2023-Broken Object Property Level Authorization",
    "resource_consumption": "API4:2023-Unrestricted Resource Consumption",
    "bfla": "API5:2023-Broken Function Level Authorization",
    "sensitive_flows": "API6:2023-Unrestricted Access to Sensitive Business Flows",
    "api_ssrf": "API7:2023-Server Side Request Forgery",
    "cors": "API8:2023-Security Misconfiguration",
    "api_misconfig": "API8:2023-Security Misconfiguration",
    "rate_limit_missing": "API9:2023-Imprecise Rate Limiting",
    "unsafe_consumption": "API10:2023-Unsafe Consumption of APIs",
}

# CWE fallback mapping for detectors (used to backfill older persisted items)
DETECTOR_TO_CWE = {
    "sec_headers_missing": "CWE-693",
    "server_tech_disclosure": "CWE-200",
    "cors_star_with_credentials": "CWE-346",
    "sql_error": "CWE-89",
    "reflected_input": "CWE-79",
    "dir_listing": "CWE-548",
    "stacktrace": "CWE-209",
    "pii_disclosure": "CWE-359",
    "api_auth_bola_heuristic": "CWE-639",
    "api_rate_limit_headers_missing": "CWE-770",
    "exception": None,
}

# ------------------------------
# Subcategory mini explanations
# ------------------------------

_SUBCASE_EXPL = {
    # Misconfiguration
    "cors:*+credentials": {
        "label": "CORS: wildcard origin + credentials",
        "why": "Any site can read authenticated responses via the victim’s browser.",
        "validate": "Check `Access-Control-Allow-Origin` and `Access-Control-Allow-Credentials` on an authenticated call.",
        "remediate": [
            "Use a strict allowlist of origins.",
            "Do not combine `Allow-Credentials: true` with wildcard/broad origins.",
        ],
    },
    "cors:reflected-origin": {
        "label": "CORS: origin reflection without validation",
        "why": "Server reflects arbitrary `Origin`, enabling cross-site reads.",
        "validate": "Send random `Origin`; verify ACAO echoes it without allowlist enforcement.",
        "remediate": ["Validate and restrict origins; avoid dynamic echo."],
    },
    "headers:security-missing": {
        "label": "Security headers missing",
        "why": "Missing CSP, XFO, XCTO, RP, HSTS, etc., weaken client-side defenses.",
        "validate": "Inspect response headers for the baseline set.",
        "remediate": ["Set CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, HSTS."],
    },
    "stacktrace:leak": {
        "label": "Debug stack trace leaked",
        "why": "Reveals internal code paths and libraries.",
        "validate": "Trigger error and confirm stack trace is suppressed.",
        "remediate": ["Disable debug; return generic errors; capture details server-side only."],
    },
    "dirlisting:enabled": {
        "label": "Directory listing enabled",
        "why": "Exposes files/structure and aids recon.",
        "validate": "Browse to the path; verify index listing disabled.",
        "remediate": ["Disable auto-index; restrict access; serve explicit index files."],
    },
    # Injection / reflection
    "sql:error-leak": {
        "label": "SQL error leaked",
        "why": "Suggests unsafe query construction or unhandled DB exceptions.",
        "validate": "Fuzz inputs; verify generic error handling post-fix.",
        "remediate": ["Parametrized queries; generic errors; limit DB privileges."],
    },
    "xss:reflected-html": {
        "label": "Reflected input in HTML context",
        "why": "May enable XSS if not encoded per context.",
        "validate": "Inject harmless payload (e.g., `<x onxxx=1>`) and review sink.",
        "remediate": ["Contextual output encoding; avoid dangerous sinks; CSP."],
    },
    "reflection:json": {
        "label": "Reflected input in JSON response",
        "why": "Echoed values in JSON can aid data leakage or serve as an injection primitive downstream.",
        "validate": "Supply a unique marker in parameters and verify it appears verbatim in JSON fields.",
        "remediate": ["Validate inputs; avoid blindly echoing untrusted data; enforce output schemas."],
    },
    "reflection:script": {
        "label": "Reflected input in <script> context",
        "why": "High-risk XSS vector if values reach inline scripts without encoding.",
        "validate": "Inject benign JS identifiers and confirm they appear inside script blocks.",
        "remediate": ["Avoid inline scripts; use templates with proper encoding; apply strict CSP."],
    },
    "reflection:event_attr": {
        "label": "Reflected input in event handler attribute",
        "why": "High-risk XSS vector in on* attributes if not encoded.",
        "validate": "Place a harmless token in input and confirm presence in on* attribute value.",
        "remediate": ["Sanitize/encode attribute contexts; avoid concatenation into event handlers."],
    },
    "reflection:url_attr": {
        "label": "Reflected input in URL attribute",
        "why": "May enable open redirects or script URL injection depending on usage.",
        "validate": "Check href/src attributes containing user-controlled values.",
        "remediate": ["Validate URLs against allowlists; encode attribute values; disallow javascript: URLs."],
    },
    "reflection:text": {
        "label": "Reflected input in HTML text",
        "why": "Lower-risk reflection; still useful for phishing or information leaks.",
        "validate": "Ensure plain text is encoded; verify no HTML interpretation.",
        "remediate": ["HTML-encode untrusted text; avoid mixing markup and data."],
    },
    # Auth / JWT
    "jwt:none": {
        "label": "JWT `alg:none` or unsigned",
        "why": "Tokens can be forged without secret/key.",
        "validate": "Decode header; confirm `alg`.",
        "remediate": ["Use RS256/ES256; reject `none`; enforce signature verification."],
    },
    "server:header-disclosure": {
        "label": "Server/X-Powered-By header disclosed",
        "why": "Reveals technology stack and versions to attackers.",
        "validate": "Inspect response headers for `Server`/`X-Powered-By` values.",
        "remediate": ["Remove/obfuscate identifying headers; standardize via reverse proxy."],
    },
    "jwt:weak-hs": {
        "label": "JWT HS* with weak/shared secret",
        "why": "Brute force or reuse across services possible.",
        "validate": "Assess secret entropy, rotation, and isolation.",
        "remediate": ["Prefer asymmetric signing; rotate secrets; scope keys per service."],
    },
    "pii:observed": {
        "label": "Potential PII observed in response",
        "why": "Exposure of emails/SSNs/credit cards can violate privacy and compliance.",
        "validate": "Search responses for PII regex matches; confirm accidental leakage.",
        "remediate": ["Mask redaction; minimize data; apply access controls and encryption."],
    },
    "jwt:missing-claims": {
        "label": "JWT missing critical claims",
        "why": "Replay or audience confusion risks.",
        "validate": "Check `aud`,`iss`,`exp`,`iat`.",
        "remediate": ["Validate claims; set short TTLs; rotate keys."],
    },
    # Rate limiting
    "rate:missing-429": {
        "label": "No 429 or throttling headers",
        "why": "Brute force and resource exhaustion become trivial.",
        "validate": "Burst traffic and look for 429/`Retry-After`/`X-RateLimit-*`.",
        "remediate": ["Apply quotas per user/IP/tenant; send 429 with retry hints."],
    },
    "rate:inconsistent": {
        "label": "Inconsistent rate limiting",
        "why": "Allows bypass via method/route variations.",
        "validate": "Vary paths/methods; confirm consistent throttling.",
        "remediate": ["Centralize rate limiting; normalize routes/identities."],
    },
    # BOLA / BFLA / BOPLA
    "bola:predictable-id": {
        "label": "Predictable or enumerable object IDs",
        "why": "Attackers can access other users’ objects.",
        "validate": "Swap IDs; expect 403/404 if unauthorized.",
        "remediate": ["Opaque IDs; enforce ownership checks server-side."],
    },
    "bfla:admin-function-exposed": {
        "label": "Privileged function lacks role checks",
        "why": "Enables privilege escalation through hidden endpoints.",
        "validate": "Invoke function without role; verify denial.",
        "remediate": ["Server-side RBAC/ABAC; defense beyond UI hiding."],
    },
    "bopla:overposting": {
        "label": "Overposting/overreading fields",
        "why": "Sensitive fields can be written/read without permission.",
        "validate": "Send extra fields; inspect unexpected reads.",
        "remediate": ["Whitelist schema; per-field authorization; drop unknown fields."],
    },
    # SSRF
    "ssrf:imds": {
        "label": "SSRF to metadata service",
        "why": "Can expose cloud credentials and instance data.",
        "validate": "Probe IMDS IPs; confirm blocked at egress.",
        "remediate": ["Block IMDS routes; allowlist hosts; sanitize URLs."],
    },
    "ssrf:internal-ip": {
        "label": "SSRF to internal IP space",
        "why": "Pivot into internal networks.",
        "validate": "Test RFC1918/IPv6 link-local; verify denies.",
        "remediate": ["Deny private ranges at egress; normalize/validate URLs."],
    },
    # Logging/monitoring
    "logging:insufficient": {
        "label": "Insufficient audit logging",
        "why": "Detection and investigations are impeded.",
        "validate": "Check coverage/retention for auth/admin/data access.",
        "remediate": ["Centralize logs; alert on anomalies; protect logs at rest."],
    },
    # Components
    "deps:outdated": {
        "label": "Outdated/vulnerable components",
        "why": "Known CVEs are exploitable.",
        "validate": "Scan SBOM/deps; check CVE feeds.",
        "remediate": ["Pin and update; remove unused; verify signatures/provenance."],
    },
    "bola:heuristic": {
        "label": "Possibly unprotected object endpoint (heuristic)",
        "why": "Object-like endpoints responding without authorization checks may allow IDOR/BOLA.",
        "validate": "Call with another user's ID without auth; expect 403/404 if protected.",
        "remediate": ["Enforce per-object authorization; use opaque IDs; centralize checks."],
    },
    "exception:error": {
        "label": "Request error during call",
        "why": "Network or server errors may indicate instability or misconfiguration.",
        "validate": "Reproduce errors; inspect logs for root cause.",
        "remediate": ["Harden error handling; add retries/backoff; fix server-side exceptions."],
    },
}

# Security header baseline used by missing-headers logic
_SEC_HEADER_BASELINE = [
    "Content-Security-Policy",
    "X-Frame-Options",
    "X-Content-Type-Options",
    "Referrer-Policy",
    "Strict-Transport-Security",
    # optional:
    "Permissions-Policy",
    "Cross-Origin-Opener-Policy",
    "Cross-Origin-Embedder-Policy",
    "Cross-Origin-Resource-Policy",
]

# ===========================
# Evidence & mini-case utils
# ===========================

def _which_missing_headers(res_headers: dict) -> list:
    """Compare response headers with our baseline and list which are missing/misconfigured."""
    missing = []
    if not isinstance(res_headers, dict):
        return _SEC_HEADER_BASELINE[:]  # unknown → assume missing
    low = {str(k).lower(): str(v) for k, v in res_headers.items()}
    for name in _SEC_HEADER_BASELINE:
        if name.lower() not in low:
            missing.append(name)
    # light quality checks
    if "content-security-policy" in low and "default-src" not in (low.get("content-security-policy") or ""):
        missing.append("Content-Security-Policy (no default-src)")
    if "strict-transport-security" in low and "max-age" not in (low.get("strict-transport-security") or ""):
        missing.append("Strict-Transport-Security (no max-age)")
    return missing

def _hdr(headers: dict, name: str) -> str:
    return (headers or {}).get(name) or (headers or {}).get(name.lower()) or ""

def _cors_status(headers: dict) -> dict:
    acao = (_hdr(headers, "Access-Control-Allow-Origin") or "").strip()
    acac = (_hdr(headers, "Access-Control-Allow-Credentials") or "").strip().lower()
    return {
        "acao": acao,
        "acac": acac,
        "wildcard_with_creds": (acao in ("*", "") or acao.lower() == "null") and acac == "true",
        "reflected": bool(acao and acao not in ("*", "null") and ("http://" in acao or "https://" in acao)),
    }

def _rate_limit_status(headers: dict) -> dict:
    xrl = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
    return {
        "has_429_hints": any(k.startswith("x-ratelimit") for k in xrl.keys()) or "retry-after" in xrl,
        "retry_after": xrl.get("retry-after"),
        "x_rate": {k: v for k, v in (headers or {}).items() if str(k).lower().startswith("x-ratelimit")},
    }

def _jwt_quick_parse(auth_header: str) -> dict:
    """Very lightweight JWT header/claims parse (no verification). Accepts 'Authorization: Bearer <token>'."""
    import base64, json
    out = {"alg": None, "claims": {}}
    if not auth_header or " " not in auth_header:
        return out
    try:
        token = auth_header.split(" ", 1)[1].strip()
        parts = token.split(".")
        if len(parts) >= 2:
            hdr = json.loads(base64.urlsafe_b64decode(parts[0] + "==").decode("utf-8", "ignore") or "{}")
            out["alg"] = hdr.get("alg")
        if len(parts) >= 3:
            claims = json.loads(base64.urlsafe_b64decode(parts[1] + "==").decode("utf-8", "ignore") or "{}")
            out["claims"] = claims
    except Exception:
        pass
    return out

def _guess_ssrf_target(pre: dict, req: dict) -> str:
    """Heuristic: look for typical URL params in query/body."""
    keys = ("url", "target", "image", "link", "fetch", "callback")
    for src in (pre.get("query") or {}, pre.get("json") or {}, pre.get("data") or {}):
        if isinstance(src, dict):
            for k in keys:
                v = src.get(k)
                if isinstance(v, str) and (v.startswith("http://") or v.startswith("https://")):
                    return v
    return ""

def _mini_block(key: str) -> str:
    meta = _SUBCASE_EXPL.get(key)
    if not meta:
        return ""
    return _render_mini(meta["label"], meta["why"], None, meta.get("remediate"))

def _render_mini(label: str, why: str, extra: str = None, remediate: list = None) -> str:
    from markupsafe import escape
    bits = [f"<li><strong>{escape(label)}:</strong> {escape(why)}"]
    if extra:
        bits.append(f" <span class='muted'>{extra}</span>")
    if remediate:
        bits.append("<ul>")
        for r in remediate:
            bits.append(f"<li>{escape(r)}</li>")
        bits.append("</ul>")
    bits.append("</li>")
    return "".join(bits)

def _build_subcase_appendix(f: dict) -> str:
    """Build a compact appendix with mini subcategory snippets derived from real evidence."""
    from markupsafe import escape
    pre = f.get("req") or {}
    res = f.get("res") or {}
    headers = res.get("headers") or {}
    body = res.get("body") or ""
    auth = (pre.get("headers") or {}).get("Authorization") or ""

    bullets = []

    # Primary: infer subcategory key from explicit subcategory, detector id, or OWASP mapping
    def _subcat_key_for_finding(fnd: dict) -> Optional[str]:
        s = _normalize_subcategory(fnd.get("subcategory"))
        det = (fnd.get("detector_id") or fnd.get("detector") or "").lower()
        oapi = (fnd.get("owasp_api") or "").strip()
        ctype = str(((fnd.get("res") or {}).get("content_type") or "")).lower()
        title_low = str(fnd.get("title") or "").lower()
        # 1) explicit subcategory text
        if s:
            if "cors" in s and "*" in s and "credential" in s: return "cors:*+credentials"
            if "header" in s and "missing" in s: return "headers:security-missing"
            if "server" in s and "header" in s and ("disclosed" in s or "disclosure" in s): return "server:header-disclosure"
            if "directory" in s and "listing" in s: return "dirlisting:enabled"
            if "sql" in s and "error" in s: return "sql:error-leak"
            if s.startswith("reflection (json)"): return "reflection:json"
            if "reflection (script)" in s: return "reflection:script"
            if "reflection (event_attr)" in s: return "reflection:event_attr"
            if "reflection (url_attr)" in s: return "reflection:url_attr"
            if s.startswith("reflection ") or "reflection (text)" in s: return "reflection:text"
            if "pii" in s: return "pii:observed"
            if "unprotected" in s and "endpoint" in s: return "bola:heuristic"
            if "rate" in s and "limit" in s: return "rate:missing-429"
            if "request error" in s: return "exception:error"
        # 2) detector id fallbacks
        if det:
            if "reflected_input" in det:
                # Prefer JSON-specific when signaled by title, ctype, or subcategory text
                if "json" in s or "json" in title_low or "application/json" in ctype:
                    return "reflection:json"
                return "reflection:text"
            if det.startswith("pattern:xss.") or det == "xss_reflect":
                return "xss:reflected-html"
            if "api_auth_bola" in det or det == "bola" or "bola" in det:
                return "bola:heuristic"
            if det == "sec_headers_missing":
                return "headers:security-missing"
            if det == "api_rate_limit_headers_missing":
                return "rate:missing-429"
            if det == "server_tech_disclosure":
                return "server:header-disclosure"
            if det == "dir_listing":
                return "dirlisting:enabled"
            if det == "sql_error":
                return "sql:error-leak"
            if det == "pii_disclosure":
                return "pii:observed"
            if det == "exception":
                return "exception:error"
        # 3) OWASP category hint (e.g., API1:2023 → BOLA)
        if oapi.startswith("API1:2023"):
            return "bola:heuristic"
        return None

    primary_key = _subcat_key_for_finding(f)
    if primary_key == "headers:security-missing":
        # Enrich with actual missing list
        missing = _which_missing_headers(headers)
        label = _SUBCASE_EXPL[primary_key]["label"]
        why = _SUBCASE_EXPL[primary_key]["why"]
        remed = _SUBCASE_EXPL[primary_key]["remediate"]
        bullets.append(_render_mini(label, why, f"Missing: {escape(', '.join(missing))}.", remed))
    elif primary_key:
        bullets.append(_mini_block(primary_key))

    # If a primary subcategory was identified, suppress unrelated generic hints
    allow_generic = primary_key is None

    # CORS
    if allow_generic:
        c = _cors_status(headers)
        if c.get("wildcard_with_creds"):
            bullets.append(_mini_block("cors:*+credentials"))
        elif c.get("reflected"):
            bullets.append(_mini_block("cors:reflected-origin"))

    # Missing headers
    if allow_generic:
        missing = _which_missing_headers(headers)
        if missing:
            label = _SUBCASE_EXPL["headers:security-missing"]["label"]
            why = _SUBCASE_EXPL["headers:security-missing"]["why"]
            remed = _SUBCASE_EXPL["headers:security-missing"]["remediate"]
            bullets.append(_render_mini(label, why, f"Missing: {escape(', '.join(missing))}.", remed))

    # SQL error leakage
    if allow_generic and isinstance(body, str) and any(sig in body.lower() for sig in ("sql syntax", "syntax error", "psql:", "postgres", "sqlite", "mysql", "odbc", "ora-")):
        bullets.append(_mini_block("sql:error-leak"))

    # XSS reflection hints
    if _normalize_subcategory(f.get("subcategory")).startswith("reflection") and any(ch in (f.get("evidence") or "") for ch in "<>\"'"):
        bullets.append(_mini_block("xss:reflected-html"))

    # JWT quick hints
    if allow_generic and auth.startswith("Bearer "):
        j = _jwt_quick_parse(auth)
        alg = (j.get("alg") or "").upper()
        claims = j.get("claims") or {}
        if alg == "NONE":
            bullets.append(_mini_block("jwt:none"))
        elif alg.startswith("HS"):
            bullets.append(_mini_block("jwt:weak-hs"))
        missing_claims = [x for x in ("aud", "iss", "exp", "iat") if x not in claims]
        if missing_claims:
            label = _SUBCASE_EXPL["jwt:missing-claims"]["label"]
            why = _SUBCASE_EXPL["jwt:missing-claims"]["why"]
            remed = _SUBCASE_EXPL["jwt:missing-claims"]["remediate"]
            bullets.append(_render_mini(label, why, f"Missing claims: {escape(', '.join(missing_claims))}.", remed))

    # Rate limit hints
    if allow_generic:
        rl = _rate_limit_status(headers)
        if not rl["has_429_hints"]:
            bullets.append(_mini_block("rate:missing-429"))
        elif rl["x_rate"] and rl["retry_after"] is None:
            bullets.append(_mini_block("rate:inconsistent"))

    # SSRF hints
    if allow_generic:
        target = _guess_ssrf_target(pre, pre)
        if target.startswith("http://169.254.169.254") or target.startswith("http://169.254.170.2"):
            bullets.append(_mini_block("ssrf:imds"))
        elif any(target.startswith(p) for p in ("http://10.", "http://172.16.", "http://192.168.", "http://[fd", "http://[fe80")):
            bullets.append(_mini_block("ssrf:internal-ip"))

    # BOLA/BFLA/BOPLA hints – rely on subcategory text if present
    if allow_generic:
        sub = _normalize_subcategory(f.get("subcategory"))
        if "predictable id" in sub or "enumerable" in sub:
            bullets.append(_mini_block("bola:predictable-id"))
        if "admin function" in sub or "role check" in sub:
            bullets.append(_mini_block("bfla:admin-function-exposed"))
        if "overpost" in sub or "property level" in sub or "field-level" in sub:
            bullets.append(_mini_block("bopla:overposting"))

    # Directory listing / stack trace
    if allow_generic:
        if "directory index" in sub or "dir listing" in sub:
            bullets.append(_mini_block("dirlisting:enabled"))
        if "stack trace" in sub or (isinstance(body, str) and "traceback" in body.lower()):
            bullets.append(_mini_block("stacktrace:leak"))

    if not bullets:
        return ""
    return (
        "<div class='drawer' style='margin-top:8px'>"
        "<div class='muted'>Subcategory specifics</div>"
        "<ul>" + "".join(bullets) + "</ul>"
        "</div>"
    )

# ==================================
# Explanation builder (exported API)
# ==================================

def get_finding_explanation(f: dict) -> str:
    """
    Build Details with:
      1) detector-specific explanation (if known),
      2) else OWASP API/Web category text,
      3) then append evidence-driven mini subcategory snippets.
    Returns HTML (safe to use with |safe in templates).
    """
    def _assemble_expl(what, why, risk, validate, remediate) -> str:
        from markupsafe import escape
        out = []
        if what: out.append(f"<p><strong>What:</strong> {escape(what)}</p>")
        if why: out.append(f"<p><strong>Why it matters:</strong> {escape(why)}</p>")
        if risk: out.append(f"<p><strong>Risk:</strong> {escape(risk)}</p>")
        if validate: out.append(f"<p><strong>How to validate quickly:</strong> {escape(validate)}</p>")
        if remediate:
            out.append("<p><strong>Remediation:</strong></p><ul>")
            for r in remediate:
                out.append(f"<li>{escape(r)}</li>")
            out.append("</ul>")
        return "\n".join(out) or "<p class='muted'>No additional details.</p>"

    # 0) Nuclei vendor details take precedence if available
    if (f.get("source") == "nuclei") or str(f.get("detector_id") or "").lower().startswith("nuclei::"):
        from markupsafe import escape
        info = f.get("nuclei") or {}
        # Prefer the template description if present (used as Why)
        desc = f.get("description") or ""
        refs = f.get("reference") or []
        cls = info.get("classification") or {}
        remediation = f.get("remediation")
        # Build a textual risk (not severity) using OWASP fallback if available, else generic
        risk_text = None
        try:
            # Try to pull from our OWASP blocks as a fallback
            cat_lbl = f.get("owasp") or f.get("owasp_api")
            if cat_lbl:
                cat = OWASP_API_DETAILS.get(cat_lbl) or OWASP_WEB_DETAILS.get(cat_lbl)
                if cat and cat.get("risk"):
                    risk_text = cat.get("risk")
        except Exception:
            pass
        if not risk_text:
            risk_text = "Potential information leakage or misconfiguration impact depending on context."
        parts = []
        # Template meta row: id + link
        t_id = info.get("template_id") or ""
        t_path = info.get("template_path") or ""
        if t_id:
            link = f" (<a href='file://{escape(t_path)}' target='_blank' rel='noopener'>view file</a>)" if t_path else ""
            parts.append(f"<p><strong>Template:</strong> {escape(t_id)}{link}</p>")
        # Header chips: avoid duplicates (OWASP may already show above; only render once here)
        chips = []
        if not f.get("owasp") and f.get("owasp_api"):
            chips.append(f"<span class='pill'>{escape(str(f['owasp_api']))}</span>")
        if f.get("cwe"):
            chips.append(f"<span class='pill'>{escape(str(f['cwe']))}</span>")
        if info.get("matcher_name"):
            chips.append(f"<span class='pill'>{escape(str(info['matcher_name']))}</span>")
        if chips:
            parts.append("<div style='display:flex;gap:6px;flex-wrap:wrap;margin:6px 0'>" + "".join(chips) + "</div>")
        # What/Why/Risk/Remediation block (consistent with detectors)
        what_text = f.get("title") or info.get("template_name") or "Nuclei finding"
        validate_text = None  # Nuclei templates generally lack a short "validate" text
        parts.append(_assemble_expl(what_text, desc, risk_text, validate_text,
                                    remediation if isinstance(remediation, list) else ([remediation] if remediation else None)))
        # Classification bullets
        bullets = []
        if cls:
            if cls.get("cwe"):
                bullets.append(f"<li><strong>CWE:</strong> {escape(str(cls.get('cwe')))}</li>")
            if cls.get("owasp"):
                bullets.append(f"<li><strong>OWASP:</strong> {escape(str(cls.get('owasp')))}</li>")
            if cls.get("cve"):
                bullets.append(f"<li><strong>CVE:</strong> {escape(str(cls.get('cve')))}</li>")
            if cls.get("cvss-score") or cls.get("cvss"):
                bullets.append(f"<li><strong>CVSS:</strong> {escape(str(cls.get('cvss-score') or cls.get('cvss')))}</li>")
        if bullets:
            parts.append("<ul>" + "".join(bullets) + "</ul>")
        # References (collapsed)
        if refs:
            try:
                links = []
                for r in (refs if isinstance(refs, list) else [refs]):
                    u = str(r)
                    links.append(f"<li><a href='{escape(u)}' target='_blank' rel='noopener'>{escape(u)}</a></li>")
                parts.append("<details><summary>Sources</summary><ul>" + "".join(links) + "</ul></details>")
            except Exception:
                pass
        # Evidence - show matched URL and status code + extracted results
        matched_at = (info.get("matched_at") or f.get("matched_at") or f.get("url") or "")
        if matched_at:
            try:
                endpoint_host = (f.get("url") or "").split("//",1)[1].split("/",1)[0] if "//" in (f.get("url") or "") else ""
            except Exception:
                endpoint_host = ""
            if not (endpoint_host and str(matched_at).startswith(endpoint_host)):
                parts.append(f"<p><strong>Matched at:</strong> {escape(str(matched_at))}</p>")
        sc = info.get("status_code") or f.get("status_code") or ((f.get("res") or {}).get("status"))
        if sc is not None:
            parts.append(f"<p><strong>Status code:</strong> {escape(str(sc))}</p>")
        # Extracted results (short)
        er = info.get("extracted_results")
        try:
            if isinstance(er, list) and er:
                items = "".join([f"<li>{escape(str(x))}</li>" for x in er[:5]])
                parts.append("<p><strong>Extracted:</strong></p><ul>" + items + ("<li>…</li>" if len(er) > 5 else "") + "</ul>")
        except Exception:
            pass
        # Request/Response toggle note (UI already renders if present)
        return "\n".join(parts) or "<p class='muted'>No additional details.</p>"

    # 1) detector-specific? (you already have some detectors named like 'sec_headers_missing', 'api_auth_bola_heuristic', etc.)
    # If your file includes a _DETECTOR_EXPLANATIONS dict, you can hook it here; otherwise we fall back to categories.
    # (Keeping this flexible so you can extend later without changing the function.)
    # --- fallthrough to category text ---

    det = (f.get("detector_id") or f.get("detector") or "").lower()

    # 2) category fallback (prefer API)
    api_lbl = f.get("owasp_api")
    web_lbl = f.get("owasp")
    # if neither exists, try to infer from detector name
    if not api_lbl and not web_lbl and det:
        for needle, cat in DETECTOR_TO_CATEGORY.items():
            if needle in det:
                if cat.startswith("API"):
                    api_lbl = cat
                else:
                    web_lbl = cat
                break

    def _find_category_details(cat_label: str) -> dict:
        if not cat_label:
            return {}
        if cat_label in OWASP_API_DETAILS:
            return OWASP_API_DETAILS[cat_label]
        if cat_label in OWASP_WEB_DETAILS:
            return OWASP_WEB_DETAILS[cat_label]
        # try by code prefix
        pref = cat_label.split(":")[0]
        for d in (OWASP_API_DETAILS, OWASP_WEB_DETAILS):
            for k, v in d.items():
                if k.startswith(pref):
                    return v
        return {}

    cat = _find_category_details(api_lbl) or _find_category_details(web_lbl)
    base_html = _assemble_expl(
        cat.get("what"), cat.get("why"), cat.get("risk"),
        cat.get("validate"), cat.get("remediate"),
    )
    sub_html = _build_subcase_appendix(f)
    return base_html + sub_html

# ==================================================
# UI helpers (exported): grouping & finding by index
# ==================================================

def _normalize_subcategory(subcategory) -> str:
    """Normalize subcategory to lowercase string, handling both string and list inputs."""
    if not subcategory:
        return ""
    if isinstance(subcategory, list):
        return " ".join(subcategory).lower().strip()
    return str(subcategory).lower().strip()

def group_findings_for_ui(pid: str) -> Dict[str, Any]:
    """
    Build UI groupings by OWASP category (API & Web).
    Returns:
      {
        'web': { cat_label: { 'title': str, 'items': [ {idx, method, path, title, severity, subcategory}, ... ] }, ... },
        'api': { ... },
        'counts': {'total': N, 'web': X, 'api': Y},
      }
    """
    rows = list(get_findings(pid))
    out_web: Dict[str, Dict[str, Any]] = {}
    out_api: Dict[str, Dict[str, Any]] = {}
    out_subcats: Dict[str, Dict[str, Any]] = {}
    out_detectors: Dict[str, Dict[str, Any]] = {}

    def _path_from_url(u: str) -> str:
        try:
            if "://" in (u or ""):
                return "/" + u.split("://", 1)[1].split("/", 1)[1]
            return u or ""
        except Exception:
            return u or ""

    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    # Fallback subcategory labels per detector if none was set at detection time
    detector_default_subcat = {
        "sec_headers_missing": "Security headers missing",
        "server_tech_disclosure": "Server header disclosed",
        "cors_star_with_credentials": "CORS: * + credentials",
        "sql_error": "SQL error leaked",
        "reflected_input": "Reflection",
        "dir_listing": "Directory listing enabled",
        "stacktrace": "Debug stack trace leaked",
        "pii_disclosure": "PII patterns observed",
        "api_auth_bola_heuristic": "Possibly unprotected object endpoint",
        "api_rate_limit_headers_missing": "Rate limiting headers missing",
        "exception": "Request error",
    }
    for i, f in enumerate(rows):
        path = _path_from_url(f.get("url") or "")
        # Infer missing OWASP category from detector if needed
        if not f.get("owasp") and not f.get("owasp_api"):
            det = (f.get("detector_id") or f.get("detector") or "").lower()
            for needle, cat in DETECTOR_TO_CATEGORY.items():
                if needle in det:
                    if cat.startswith("API"):
                        f["owasp_api"] = f.get("owasp_api") or cat
                    else:
                        f["owasp"] = f.get("owasp") or cat
                    break
        # Backfill CWE using detector mapping (with special case for JSON reflection)
        if not f.get("cwe"):
            det = (f.get("detector_id") or f.get("detector") or "").lower()
            guess = DETECTOR_TO_CWE.get(det)
            sub = _normalize_subcategory(f.get("subcategory"))
            if det == "reflected_input" and ("json" in sub):
                guess = "CWE-200"
            if guess:
                f["cwe"] = guess
        # Compute display subcategory with fallbacks
        det_for_sub = (f.get("detector_id") or f.get("detector") or "").lower()
        sub_fallback = detector_default_subcat.get(det_for_sub)
        # Special-case: infer JSON reflection when missing
        if (not f.get("subcategory")) and det_for_sub == "reflected_input":
            ct = str(((f.get("res") or {}).get("content_type") or "")).lower()
            title_low = str(f.get("title") or "").lower()
            if "json" in title_low or "application/json" in ct:
                sub_fallback = "Reflection (JSON)"
        sub_display = _normalize_subcategory(f.get("subcategory")) or sub_fallback
        # If still missing, show OWASP/API or CWE code as a last resort
        if not sub_display:
            sub_display = f.get("owasp") or f.get("owasp_api") or f.get("cwe") or ""

        # Escape string fields to prevent XSS
        from markupsafe import escape
        row_small = {
            "idx": i, 
            "method": f.get("method"), 
            "path": escape(str(path or "")),
            "title": escape(str(f.get("title") or "")),
            "severity": f.get("severity"),
            "subcategory": escape(str(sub_display or "")),
            "url": escape(str(f.get("url") or "")),
            "confidence": f.get("confidence", 50),
            "status": f.get("status", "new"),
            "sev_rank": sev_order.get(str(f.get("severity") or "").lower(), 9),
            "owasp": f.get("owasp"),
            "owasp_api": f.get("owasp_api"),
            "cwe": f.get("cwe"),
            "detector_id": f.get("detector_id") or f.get("detector"),
        }
        if f.get("owasp"):
            grp = out_web.setdefault(f["owasp"], {"title": f["owasp"], "items": []})
            grp["items"].append(row_small)
        if f.get("owasp_api"):
            grp = out_api.setdefault(f["owasp_api"], {"title": f["owasp_api"], "items": []})
            grp["items"].append(row_small)

        # Group by subcategory (fallback if missing)
        sub = sub_display or "(unspecified)"
        sc = out_subcats.setdefault(sub, {"title": sub, "items": []})
        sc["items"].append(row_small)

        # Group by detector + title (beautified label)
        det_lbl_raw = (f.get("detector_id") or f.get("detector") or "detector").lower()
        det_friendly = {
            "api_auth_bola_heuristic": "BOLA heuristic",
            "api_rate_limit_headers_missing": "Rate limiting headers missing",
            "reflected_input": "Reflected input",
            "sec_headers_missing": "Security headers missing",
            "server_tech_disclosure": "Server technology disclosure",
            "cors_star_with_credentials": "CORS: * + credentials",
            "sql_error": "SQL error pattern",
            "dir_listing": "Directory listing enabled",
            "stacktrace": "Debug stack trace leaked",
            "pii_disclosure": "PII patterns observed",
            "exception": "Request error",
        }.get(det_lbl_raw) or det_lbl_raw.replace('_',' ')
        key = f"{det_friendly} — {f.get('title') or ''}"
        dg = out_detectors.setdefault(key, {"title": key, "items": []})
        dg["items"].append(row_small)

    # Create "other" category for non-OWASP findings
    out_other: Dict[str, Dict[str, Any]] = {}
    for i, f in enumerate(rows):
        if not f.get("owasp") and not f.get("owasp_api"):
            path = _path_from_url(f.get("url") or "")
            det_for_sub = (f.get("detector_id") or f.get("detector") or "").lower()
            sub_fallback = detector_default_subcat.get(det_for_sub)
            if (not f.get("subcategory")) and det_for_sub == "reflected_input":
                ct = str(((f.get("res") or {}).get("content_type") or "")).lower()
                title_low = str(f.get("title") or "").lower()
                if "json" in title_low or "application/json" in ct:
                    sub_fallback = "Reflection (JSON)"
            sub_display = _normalize_subcategory(f.get("subcategory")) or sub_fallback or "Other"
            
            from markupsafe import escape
            row_small = {
                "idx": i, 
                "method": f.get("method"), 
                "path": escape(str(path or "")),
                "title": escape(str(f.get("title") or "")),
                "severity": f.get("severity"),
                "subcategory": escape(str(sub_display or "")),
                "url": escape(str(f.get("url") or "")),
                "confidence": f.get("confidence", 50),
                "status": f.get("status", "new"),
                "sev_rank": sev_order.get(str(f.get("severity") or "").lower(), 9),
                "owasp": f.get("owasp"),
                "owasp_api": f.get("owasp_api"),
                "cwe": f.get("cwe"),
                "detector_id": f.get("detector_id") or f.get("detector"),
            }
            
            grp = out_other.setdefault(sub_display, {"title": sub_display, "items": []})
            grp["items"].append(row_small)

    out_web = dict(sorted(out_web.items(), key=lambda kv: kv[0]))
    out_api = dict(sorted(out_api.items(), key=lambda kv: kv[0]))
    out_other = dict(sorted(out_other.items(), key=lambda kv: kv[0].lower()))
    
    return {
        "web": out_web,
        "api": out_api,
        "other": out_other,
        "subcats": dict(sorted(out_subcats.items(), key=lambda kv: kv[0].lower())),
        "detectors": dict(sorted(out_detectors.items(), key=lambda kv: kv[0].lower())),
        "counts": {
            "total": len(rows),
            "web": len([f for f in rows if f.get("owasp")]),
            "api": len([f for f in rows if f.get("owasp_api")]),
            "other": len([f for f in rows if not f.get("owasp") and not f.get("owasp_api")]),
        },
    }

def get_finding_by_index(pid: str, idx: int) -> Optional[Dict[str, Any]]:
    rows = list(get_findings(pid))
    if 0 <= idx < len(rows):
        f = rows[idx]
        # Backfill classification for older entries
        if not f.get("cwe"):
            det = (f.get("detector_id") or f.get("detector") or "").lower()
            sub = _normalize_subcategory(f.get("subcategory"))
            guess = DETECTOR_TO_CWE.get(det)
            if det == "reflected_input" and ("json" in sub):
                guess = "CWE-200"
            if guess:
                f["cwe"] = guess
        if not f.get("owasp") and not f.get("owasp_api"):
            det = (f.get("detector_id") or f.get("detector") or "").lower()
            for needle, cat in DETECTOR_TO_CATEGORY.items():
                if needle in det:
                    if cat.startswith("API"):
                        f["owasp_api"] = f.get("owasp_api") or cat
                    else:
                        f["owasp"] = f.get("owasp") or cat
                    break
        return f
    return None

# ============================================================
# Enhanced Grouping System
# ============================================================

def normalize_path(p: str) -> str:
    """Keep {param} segments intact, lower-case, collapse slashes."""
    if not p:
        return '/'
    p = '/' + '/'.join([s for s in p.strip().split('/') if s])
    return p.lower()

def signature(item):
    """Unique-ish per endpoint occurrence."""
    return f"{item['method']} {normalize_path(item.get('path') or item.get('url') or '')}"

def group_key_rule(item):
    """Group by detector/template ID with fallback to OWASP/CWE/title."""
    rid = item.get('detector_id') or item.get('template_id') or ''
    if not rid:
        # Fall back to OWASP/API + CWE + subcategory + normalized title
        rid = "|".join(filter(None, [
            item.get('owasp') or item.get('owasp_api') or 'Other',
            item.get('cwe') or '',
            item.get('subcategory') or '',
            (item.get('title') or '').strip().lower(),
        ]))
    return f"rule::{rid}"

def group_key_endpoint(item):
    """Group by endpoint signature."""
    return f"endpoint::{signature(item)}"

def group_key_owasp(item):
    """Group by OWASP category."""
    return f"owasp::{item.get('owasp') or item.get('owasp_api') or 'Other'}"

def group_key_cwe(item):
    """Group by CWE category."""
    return f"cwe::{item.get('cwe') or 'Unspecified'}"

def build_groups(findings, mode='rule'):
    """Build grouped findings with statistics."""
    key_fn = {
        'rule': group_key_rule,
        'endpoint': group_key_endpoint,
        'owasp': group_key_owasp,
        'cwe': group_key_cwe,
    }[mode]

    groups = {}
    for f in findings:
        k = key_fn(f)
        # Set title based on grouping mode
        if mode == 'endpoint':
            # For endpoint grouping, show the endpoint signature
            title = signature(f)
        elif mode == 'rule':
            # For rule grouping, show the vulnerability title
            title = f.get('title') or (f.get('detector_id') or f.get('template_id') or 'Issue')
        elif mode == 'owasp':
            # For OWASP grouping, show the OWASP category
            title = f.get('owasp') or f.get('owasp_api') or 'Other'
        elif mode == 'cwe':
            # For CWE grouping, show the CWE category
            title = f.get('cwe') or 'Unspecified'
        else:
            # Fallback to vulnerability title
            title = f.get('title') or (f.get('detector_id') or f.get('template_id') or 'Issue')
        
        g = groups.setdefault(k, {
            'key': k, 'items_list': [], 'worst_sev': 'info', 'endpoints': set(),
            'source': ('nuclei' if str(f.get('detector_id','')).startswith('nuclei::') else 'detector'),
            'owasp': f.get('owasp') or f.get('owasp_api'),
            'cwe': f.get('cwe'),
            'title': title,
            'conf_min': 101, 'conf_max': -1,
        })
        g['items_list'].append(f)
        # Only add to endpoints set if not grouping by endpoint
        if mode != 'endpoint':
            g['endpoints'].add(signature(f))
        
        # Severity ladder
        order = {'critical':4,'high':3,'medium':2,'low':1,'info':0}
        if order.get(f.get('severity','info'),0) > order.get(g['worst_sev'],0):
            g['worst_sev'] = f['severity']
        
        # Confidence range
        c = int(f.get('confidence') or 0)
        g['conf_min'] = min(g['conf_min'], c)
        g['conf_max'] = max(g['conf_max'], c)

    # Finalize sets & counts
    for g in groups.values():
        if mode == 'endpoint':
            # When grouping by endpoint, each group represents one endpoint
            g['endpoint_count'] = 1
            g['occurrence_count'] = len(g['items_list'])
        else:
            # When grouping by other criteria, count unique endpoints
            g['endpoint_count'] = len(g['endpoints'])
            g['occurrence_count'] = len(g['items_list'])
        del g['endpoints']
        if g['conf_min'] == 101: g['conf_min'] = 0
        if g['conf_max'] == -1: g['conf_max'] = 0
    
    # Sort by worst severity desc, then count desc
    severity_order = {'critical':4,'high':3,'medium':2,'low':1,'info':0}
    groups_sorted = sorted(groups.values(), 
                          key=lambda g: (severity_order.get(g['worst_sev'], 0), g['occurrence_count']), 
                          reverse=True)
    
    return groups_sorted
