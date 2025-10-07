# detectors/pattern_engine.py
from __future__ import annotations
import os, re, json, glob, time
from typing import Any, Dict, List, Optional

def _cvss_to_severity(cvss: Optional[float]) -> str:
    try:
        v = float(cvss)
    except Exception:
        return "info"
    if v >= 9.0: return "critical"
    if v >= 7.0: return "high"
    if v >= 4.0: return "medium"
    if v >  0.0: return "low"
    return "info"

class PatternEngine:
    """
    KISS pattern engine with:
    - external JSON packs (rules) from a directory
    - rule validation, regex caching
    - rule enable/disable
    - CWE/CVSS/confidence/tags
    - pack metadata attached to output
    """
    def __init__(self, pattern_dir: str):
        self.pattern_dir = pattern_dir
        self.rule_sets: List[Dict[str, Any]] = []
        self._compiled: List[Dict[str, Any]] = []
        self._compiled_cache: Dict[str, re.Pattern] = {}
        self._last_reload = 0.0

    # ---------- public API ----------

    def _compile(self, rx: str) -> re.Pattern:
        """Compile regex with caching."""
        if rx not in self._compiled_cache:
            self._compiled_cache[rx] = re.compile(rx, re.IGNORECASE)
        return self._compiled_cache[rx]

    def _validate_rule(self, r: Dict[str, Any]) -> List[str]:
        """Enhanced rule validation with comprehensive checks."""
        errs = []
        
        # Required fields
        if not r.get("regex"): 
            errs.append("missing regex")
        if not r.get("title"): 
            errs.append("missing title")
        
        # Regex validation with compilation test
        regex = r.get("regex", "")
        if regex:
            try:
                self._compile(regex)
            except re.error as e:
                errs.append(f"bad regex: {e}")
        
        # Confidence validation
        conf = r.get("confidence", 50)
        if not isinstance(conf, (int, float)) or conf < 0 or conf > 100:
            errs.append("confidence must be 0-100")
        
        # CWE format validation
        cwe = r.get("cwe")
        if cwe:
            if isinstance(cwe, str):
                cwe_normalized = cwe.upper().strip()
                if not cwe_normalized.startswith("CWE-"):
                    if not cwe_normalized.isdigit():
                        errs.append("CWE must be in format CWE-XXX or just the number")
            else:
                errs.append("CWE must be a string")
        
        # CVSS validation
        cvss = r.get("cvss")
        if cvss is not None:
            try:
                cvss_val = float(cvss)
                if not 0.0 <= cvss_val <= 10.0:
                    errs.append("CVSS score must be between 0.0 and 10.0")
            except (ValueError, TypeError):
                errs.append("CVSS must be a number")
        
        # Severity validation
        severity = r.get("severity")
        if severity and severity not in ["info", "low", "medium", "high", "critical"]:
            errs.append("severity must be one of: info, low, medium, high, critical")
        
        return errs

    def reload(self) -> None:
        """Load (or reload) all JSON packs from the directory with validation."""
        self.rule_sets = []
        self._compiled = []
        self._compiled_cache.clear()  # Clear cache on reload
        
        if not os.path.isdir(self.pattern_dir):
            print(f"[patterns] directory not found: {self.pattern_dir}")
            return
            
        paths = sorted(glob.glob(os.path.join(self.pattern_dir, "*.json")))
        for p in paths:
            try:
                with open(p, "r", encoding="utf-8") as fh:
                    try:
                        data = json.load(fh)
                    except json.JSONDecodeError as e:
                        print(f"[patterns] skip {p}: cannot parse JSON: line {e.lineno} col {e.colno} — {e.msg}")
                        continue
            except Exception as e:
                print(f"[patterns] skip {p}: cannot read file: {e}")
                continue

            rules = data.get("rules") or data.get("patterns", [])
            if not isinstance(rules, list):
                print(f"[patterns] skip {p}: 'rules' must be a list")
                continue

            pack_name = data.get("name") or os.path.basename(p)
            pack_version = data.get("version")
            for r in rules:
                if r.get("enabled") is False:
                    continue  # allow toggle without deletion
                    
                errs = self._validate_rule(r)
                if errs:
                    print(f"[patterns] skip rule in {p}: {', '.join(errs)}")
                    continue
                    
                try:
                    rx = r.get("regex", "")
                    ro = self._compile(rx)
                except Exception as e:
                    print(f"[patterns] skip rule (compile) in {p}: {e}")
                    continue
                where = r.get("where") or ["response.body"]
                if isinstance(where, str):
                    where = [where]
                item = {
                    "id": str(r.get("id") or ""),
                    "title": r.get("title") or "Pattern match",
                    "where": list(where),
                    "regex": rx,
                    "re": ro,
                    "cwe": r.get("cwe"),
                    "cvss": r.get("cvss"),
                    "severity": r.get("severity"),  # optional override
                    "confidence": int(r.get("confidence") or 60),
                    "tags": r.get("tags") or [],
                    "enabled": True,
                    "pack_name": pack_name,
                    "pack_version": pack_version,
                    "pack_path": p,
                    # Gate flags
                    "context_gate": r.get("context_gate", True),
                    "content_type_gate": r.get("content_type_gate", True),
                    "minified_gate": r.get("minified_gate", True),
                    "status_gate": r.get("status_gate", True),
                    "allow_error_responses": r.get("allow_error_responses", False),
                    "allow_redirects": r.get("allow_redirects", False),
                    "allow_binary_content": r.get("allow_binary_content", False),
                    "allow_minified_content": r.get("allow_minified_content", False),
                    "allow_minified_js": r.get("allow_minified_js", False),
                }
                self._compiled.append(item)

            self.rule_sets.append(data)
        self._last_reload = time.time()
        print(f"[pattern] loaded {len(self._compiled)} rules from {len(paths)} file(s)")

    def detect(self, req: Dict[str, Any], res: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Run all compiled rules against a request/response pair.
        Returns a list of finding dicts (not persisted; caller decides).
        """
        text_fields = self._extract_text_fields(req, res)
        out: List[Dict[str, Any]] = []
        for r in self._compiled:
            for w in r["where"]:
                s = text_fields.get(w, "")
                if not s:
                    continue
                m = r["re"].search(s)
                if not m:
                    continue
                
                # Apply false-positive reducers
                if not self._should_report_match(r, m, s, req, res):
                    continue
                
                # Enhanced evidence capture
                snippet = m.group(0)
                context_start = max(0, m.start() - 100)
                context_end = min(len(s), m.end() + 100)
                context_snippet = s[context_start:context_end]
                
                # Extract request snippet for context
                req_snippet = ""
                if w.startswith("request."):
                    req_snippet = self._extract_request_snippet(req, w)
                
                # Calculate enhanced confidence based on context
                enhanced_confidence = self._calculate_enhanced_confidence(r, m, s, req, res)
                
                sev = r.get("severity") or _cvss_to_severity(r.get("cvss"))
                out.append({
                    "detector_id": f"pattern:{r['id']}" if r["id"] else "pattern",
                    "title": r["title"],
                    "severity": sev,
                    "confidence": enhanced_confidence,
                    "cwe": r.get("cwe"),
                    "cvss": r.get("cvss"),
                    "evidence": snippet[:2048],
                    "tags": r.get("tags") or [],
                    "meta": {
                        "where": w,
                        "regex": r["regex"],
                        "pack": r["pack_name"],
                        "pack_version": r.get("pack_version"),
                        "pack_path": r["pack_path"],
                        "pattern_id": r["id"],
                        "matched_fragment": snippet,
                        "context_snippet": context_snippet,
                        "request_snippet": req_snippet,
                        "match_position": m.start(),
                        "match_length": len(snippet),
                        "response_status": res.get("status"),
                        "content_type": res.get("headers", {}).get("content-type", ""),
                        "request_method": req.get("method", ""),
                        "request_url": req.get("url", ""),
                    }
                })
                break  # one hit per rule is enough
        return out

    def _extract_request_snippet(self, req: Dict[str, Any], where: str) -> str:
        """Extract relevant request snippet based on where field."""
        if where == "request.body":
            body = req.get("json") or req.get("data") or ""
            if isinstance(body, dict):
                body = str(body)
            return str(body)[:500]  # Limit request body snippet
        elif where == "request.headers":
            headers = req.get("headers", {})
            return str(headers)[:500]
        elif where == "request.url":
            return req.get("url", "")[:500]
        elif where == "request.params":
            params = req.get("query", {})
            return str(params)[:500]
        return ""

    def _should_report_match(self, rule: Dict[str, Any], match: re.Match, text: str, req: Dict[str, Any], res: Dict[str, Any]) -> bool:
        """Apply false-positive reducers to determine if match should be reported."""
        matched_text = match.group(0)
        
        # Context gates - check if reflected value is reasonable
        if rule.get("context_gate", True):  # Default to enabled
            # Skip if matched text is too long (likely not user input)
            if len(matched_text) > 1000:
                return False
            
            # Skip if matched text is purely alphanumeric and long (likely not user input)
            if len(matched_text) > 100 and matched_text.replace(" ", "").isalnum():
                return False
            
            # Skip if matched text appears to be a UUID or hash
            if len(matched_text) == 32 and matched_text.replace("-", "").isalnum():
                return False
            if len(matched_text) == 40 and matched_text.isalnum():  # SHA1
                return False
            if len(matched_text) == 64 and matched_text.isalnum():  # SHA256
                return False
        
        # Content-type gates
        content_type = res.get("headers", {}).get("content-type", "").lower()
        if rule.get("content_type_gate", True):  # Default to enabled
            # Skip binary content types unless explicitly allowed
            binary_types = ["application/octet-stream", "image/", "video/", "audio/", "application/pdf"]
            if any(ct in content_type for ct in binary_types):
                if not rule.get("allow_binary_content", False):
                    return False
            
            # Skip minified JavaScript unless explicitly allowed
            if "application/javascript" in content_type or "text/javascript" in content_type:
                if self._is_minified_content(text) and not rule.get("allow_minified_js", False):
                    return False
        
        # Minified content detection
        if rule.get("minified_gate", True):  # Default to enabled
            if self._is_minified_content(text):
                # Skip minified content unless explicitly allowed
                if not rule.get("allow_minified_content", False):
                    return False
        
        # Response status gates
        status = res.get("status")
        if status and rule.get("status_gate", True):  # Default to enabled
            # Skip error responses unless explicitly allowed
            if status >= 400 and not rule.get("allow_error_responses", False):
                return False
            
            # Skip redirects unless explicitly allowed
            if 300 <= status < 400 and not rule.get("allow_redirects", False):
                return False
        
        # Size gates - skip very large responses
        if len(text) > 1000000:  # 1MB limit
            if not rule.get("allow_large_responses", False):
                return False
        
        # Pattern-specific gates
        pattern_id = rule.get("id", "")
        
        # XSS-specific gates
        if "xss" in pattern_id.lower() or "cross-site" in rule.get("title", "").lower():
            # Skip if matched text doesn't look like user input
            if not self._looks_like_user_input(matched_text):
                return False
        
        # SQL injection gates
        if "sql" in pattern_id.lower() or "injection" in rule.get("title", "").lower():
            # Skip if matched text is too generic
            generic_sql_patterns = ["SELECT", "INSERT", "UPDATE", "DELETE", "WHERE", "FROM"]
            if matched_text.upper() in generic_sql_patterns:
                return False
        
        # Path traversal gates
        if "path" in pattern_id.lower() or "traversal" in rule.get("title", "").lower():
            # Skip if matched text doesn't contain path separators
            if "../" not in matched_text and "..\\" not in matched_text:
                return False
        
        return True

    def _is_minified_content(self, text: str) -> bool:
        """Detect if content appears to be minified."""
        if len(text) < 1000:
            return False
        
        # Check for low whitespace ratio
        whitespace_ratio = text.count(" ") / len(text)
        if whitespace_ratio < 0.01:  # Less than 1% whitespace
            return True
        
        # Check for very long lines
        lines = text.split("\n")
        if len(lines) > 10:  # Multiple lines
            avg_line_length = sum(len(line) for line in lines) / len(lines)
            if avg_line_length > 200:  # Very long lines
                return True
        
        return False

    def _looks_like_user_input(self, text: str) -> bool:
        """Determine if text looks like user input rather than system data."""
        # Skip if too long
        if len(text) > 200:
            return False
        
        # Skip if contains system-like patterns
        system_patterns = [
            r"^\d+$",  # Pure numbers
            r"^[a-f0-9]{32}$",  # MD5 hash
            r"^[a-f0-9]{40}$",  # SHA1 hash
            r"^[a-f0-9]{64}$",  # SHA256 hash
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",  # UUID
        ]
        
        for pattern in system_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return False
        
        # Skip if mostly special characters
        special_char_ratio = sum(1 for c in text if not c.isalnum() and c not in " -_") / len(text)
        if special_char_ratio > 0.5:
            return False
        
        return True

    def _calculate_enhanced_confidence(self, rule: Dict[str, Any], match: re.Match, text: str, req: Dict[str, Any], res: Dict[str, Any]) -> int:
        """Calculate enhanced confidence based on context and match quality."""
        base_confidence = rule.get("confidence", 60)
        
        # Start with base confidence
        confidence = base_confidence
        
        # Context-based adjustments
        matched_text = match.group(0)
        
        # Boost confidence for specific patterns
        if len(matched_text) < 50:  # Short, specific matches
            confidence += 10
        elif len(matched_text) > 200:  # Very long matches might be false positives
            confidence -= 15
        
        # Check if match appears to be reflected input
        if req.get("method") in ["GET", "POST", "PUT", "PATCH"]:
            # Look for parameter reflection
            url_params = req.get("query", {})
            body_data = req.get("json") or req.get("data") or {}
            
            # Check if matched text appears in request parameters
            for param_value in url_params.values():
                if isinstance(param_value, str) and matched_text in param_value:
                    confidence += 15  # Parameter reflection increases confidence
                    break
            
            # Check if matched text appears in request body
            if isinstance(body_data, dict):
                for value in body_data.values():
                    if isinstance(value, str) and matched_text in value:
                        confidence += 15
                        break
        
        # Adjust based on response status
        status = res.get("status")
        if status:
            if 200 <= status < 300:
                confidence += 5  # Successful responses are more reliable
            elif status >= 400:
                confidence -= 10  # Error responses might be false positives
        
        # Adjust based on content type
        content_type = res.get("headers", {}).get("content-type", "")
        if "application/json" in content_type:
            confidence += 5  # JSON responses are more structured
        elif "text/html" in content_type:
            confidence -= 5  # HTML might contain more noise
        
        # Check for minified content (likely false positive)
        if len(text) > 1000 and len(text.split()) < 50:  # Dense, few spaces
            confidence -= 20
        
        # Clamp confidence to valid range
        return max(0, min(100, confidence))

    def detect_text(self, text: str) -> List[Dict[str, Any]]:
        """Simple text detection method for testing patterns."""
        out = []
        if not text:
            return out
        for r in self._compiled:
            m = r["re"].search(text)
            if m:
                out.append({
                    "title": r["title"],
                    "regex": r["regex"],
                    "cwe": r.get("cwe"),
                    "cvss": r.get("cvss"),
                    "confidence": r.get("confidence", 50),
                    "evidence": m.group(0)[:200],
                    "tags": r.get("tags") or [],
                })
        return out

    def get_pattern_stats(self) -> Dict[str, Any]:
        """Comprehensive statistics for debugging/metrics."""
        enabled = sum(1 for r in self._compiled if r.get("enabled", True))
        disabled = len(self._compiled) - enabled
        
        # Count by pack
        pack_stats = {}
        for rule in self._compiled:
            pack_name = rule.get("pack_name", "unknown")
            if pack_name not in pack_stats:
                pack_stats[pack_name] = {"total": 0, "enabled": 0, "disabled": 0}
            pack_stats[pack_name]["total"] += 1
            if rule.get("enabled", True):
                pack_stats[pack_name]["enabled"] += 1
            else:
                pack_stats[pack_name]["disabled"] += 1
        
        # Count by severity
        severity_stats = {}
        for rule in self._compiled:
            sev = rule.get("severity") or _cvss_to_severity(rule.get("cvss"))
            severity_stats[sev] = severity_stats.get(sev, 0) + 1
        
        # Count by CWE
        cwe_stats = {}
        for rule in self._compiled:
            cwe = rule.get("cwe")
            if cwe:
                cwe_stats[cwe] = cwe_stats.get(cwe, 0) + 1
        
        return {
            "total_rules": len(self._compiled),
            "enabled_rules": enabled,
            "disabled_rules": disabled,
            "packs_loaded": len(self.rule_sets),
            "cache_size": len(self._compiled_cache),
            "last_reload": self._last_reload,
            "pack_breakdown": pack_stats,
            "severity_breakdown": severity_stats,
            "cwe_breakdown": cwe_stats,
        }

    def test_pattern(self, rule_id: str, test_text: str) -> bool:
        """Test a specific pattern against text."""
        for rule in self._compiled:
            if rule["id"] == rule_id:
                return bool(rule["re"].search(test_text))
        return False
    
    def test_all_patterns(self, test_text: str) -> List[Dict[str, Any]]:
        """Test all patterns against given text and return matches."""
        matches = []
        for rule in self._compiled:
            if not rule.get("enabled", True):
                continue
            m = rule["re"].search(test_text)
            if m:
                matches.append({
                    "rule_id": rule["id"],
                    "title": rule["title"],
                    "pack": rule["pack_name"],
                    "severity": rule.get("severity") or _cvss_to_severity(rule.get("cvss")),
                    "cwe": rule.get("cwe"),
                    "cvss": rule.get("cvss"),
                    "confidence": rule["confidence"],
                    "match": m.group(0),
                    "tags": rule.get("tags", [])
                })
        return matches
    
    def list_patterns(self) -> List[Dict[str, Any]]:
        """List all loaded patterns with their metadata."""
        return [
            {
                "id": rule["id"],
                "title": rule["title"],
                "enabled": rule.get("enabled", True),
                "pack": rule["pack_name"],
                "pack_version": rule.get("pack_version"),
                "severity": rule.get("severity") or _cvss_to_severity(rule.get("cvss")),
                "cwe": rule.get("cwe"),
                "cvss": rule.get("cvss"),
                "confidence": rule["confidence"],
                "tags": rule.get("tags", []),
                "where": rule["where"]
            }
            for rule in self._compiled
        ]
    
    def get_pattern_by_id(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific pattern by its ID."""
        for rule in self._compiled:
            if rule["id"] == rule_id:
                return rule
        return None
    
    def toggle_pattern(self, rule_id: str, enabled: bool) -> bool:
        """Enable/disable a specific pattern."""
        for rule in self._compiled:
            if rule["id"] == rule_id:
                rule["enabled"] = enabled
                return True
        return False

    # ---------- internals ----------

    def _compile(self, rx: str) -> Optional[re.Pattern]:
        if rx in self._compiled_cache:
            return self._compiled_cache[rx]
        try:
            obj = re.compile(rx, re.IGNORECASE)
            self._compiled_cache[rx] = obj
            return obj
        except Exception as e:
            print(f"[pattern] invalid regex: {rx!r} -> {e}")
            return None


    def _extract_text_fields(self, req: Dict[str, Any], res: Dict[str, Any]) -> Dict[str, str]:
        def _json_str(x: Any) -> str:
            try:
                return json.dumps(x, ensure_ascii=False)
            except Exception:
                return str(x)
        out = {
            "request.url": req.get("url") or "",
            "request.headers": _json_str(req.get("headers")),
            "request.cookies": _json_str(req.get("cookies")),
            "request.query": _json_str(req.get("query")),
            "request.body": _json_str(req.get("json") if req.get("json") is not None else req.get("data")),
            "response.headers": _json_str(res.get("headers")),
            "response.body": str(res.get("body") or ""),
        }
        return out

# Singleton pattern engine instance
_default_engine: Optional[PatternEngine] = None

def load_engine(pattern_dir: Optional[str] = None) -> PatternEngine:
    """Load pattern engine singleton to avoid reloading patterns multiple times."""
    global _default_engine
    if _default_engine is None:
        if pattern_dir is None:
            pattern_dir = os.path.join(os.path.dirname(__file__), "patterns")
        _default_engine = PatternEngine(pattern_dir)
        _default_engine.reload()
    return _default_engine
