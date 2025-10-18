#!/usr/bin/env python3
import json, sys, pathlib, re, datetime as dt

ROOT = pathlib.Path(__file__).resolve().parents[1]
J = ROOT / "control" / "journal" / "agents"
CONF_BASELINE = ROOT / "control" / "config" / "journals_baseline.json"

EVENTS = {"sod","mid","eod","note","handoff","decision"}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Link tokens we accept inside links[]; we allow URLs and common identifiers
LINK_TOKEN = re.compile(
    r"^(PR#\d+|Issue#\d+|FEAT-\d+|SHA:[0-9a-fA-F]{7,40}|commit:[0-9a-fA-F]{7,40}|https?://\S+|[\w\-/\.]+)$"
)

MAX_ITEMS = 12
MAX_ITEM_CHARS = 200

# Security deny-list patterns for secrets and PII
SECRET_PATTERNS = [
    # API Keys and Tokens
    re.compile(r'(?i)(api[_-]?key|token|secret|password|passwd|pwd)\s*[:=]\s*["\']?[a-zA-Z0-9+/=]{20,}["\']?', re.IGNORECASE),
    # GitHub tokens
    re.compile(r'gh[ops]_[a-zA-Z0-9]{36}', re.IGNORECASE),
    # AWS credentials
    re.compile(r'AKIA[0-9A-Z]{16}', re.IGNORECASE),
    re.compile(r'aws[_-]?access[_-]?key[_-]?id', re.IGNORECASE),
    re.compile(r'aws[_-]?secret[_-]?access[_-]?key', re.IGNORECASE),
    # Database credentials
    re.compile(r'(?i)(database[_-]?url|db[_-]?url|connection[_-]?string)\s*[:=]\s*["\']?[^"\']*["\']?', re.IGNORECASE),
    # JWT tokens
    re.compile(r'eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*', re.IGNORECASE),
    # Private keys
    re.compile(r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----', re.IGNORECASE),
    # SSH keys
    re.compile(r'-----BEGIN\s+(?:RSA\s+|DSA\s+|EC\s+)?PRIVATE\s+KEY-----', re.IGNORECASE),
]

PII_PATTERNS = [
    # Email addresses
    re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    # Phone numbers (US format)
    re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
    # SSN (US format) - more specific pattern to avoid false positives with GitHub IDs
    re.compile(r'\b(?!000|666|9\d{2})\d{3}-?(?!00)\d{2}-?(?!0000)\d{4}\b(?![0-9])'),
    # Credit card numbers
    re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
    # IP addresses
    re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
]

def parse_iso(ts: str) -> dt.datetime:
    # Expect "YYYY-MM-DDTHH:MM:SSZ"
    return dt.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)

def load_baseline() -> dt.datetime:
    if CONF_BASELINE.exists():
        data = json.loads(CONF_BASELINE.read_text())
        ts = data.get("baseline_ts", "1970-01-01T00:00:00Z")
    else:
        ts = "1970-01-01T00:00:00Z"
    return parse_iso(ts)

BASELINE_TS = load_baseline()

def err(p, i, msg):
    print(f"::error file={p},line={i}::{msg}")

def warn(p, i, msg):
    print(f"::warning file={p},line={i}::{msg}")

def validate_security(p, i, rec):
    """Validate journal entry for secrets and PII."""
    ok = True
    text_content = json.dumps(rec, separators=(',', ':'))
    
    # Check for secrets
    for pattern in SECRET_PATTERNS:
        if pattern.search(text_content):
            err(p, i, f"Potential secret detected: {pattern.pattern[:50]}...")
            ok = False
    
    # Check for PII with context awareness
    for pattern in PII_PATTERNS:
        matches = pattern.findall(text_content)
        for match in matches:
            # Skip common false positives
            if is_false_positive(match, text_content):
                continue
            err(p, i, f"Potential PII detected: {pattern.pattern[:50]}...")
            ok = False
    
    # Check specific fields for sensitive content
    sensitive_fields = ['items', 'title', 'links']
    for field in sensitive_fields:
        if field in rec:
            field_content = str(rec[field])
            for pattern in SECRET_PATTERNS + PII_PATTERNS:
                matches = pattern.findall(field_content)
                for match in matches:
                    if pattern in PII_PATTERNS and is_false_positive(match, field_content):
                        continue
                    err(p, i, f"Potential sensitive content in {field}: {pattern.pattern[:50]}...")
                    ok = False
    
    return ok

def is_false_positive(match, context):
    """Check if a PII match is likely a false positive."""
    # Common false positive patterns
    false_positives = [
        # GitHub workflow IDs
        r'ID:\s*\d{9}',
        r'workflow.*ID.*\d{9}',
        # Version numbers
        r'v?\d+\.\d+\.\d+',
        # Line numbers
        r'lines?\s+\d+-\d+',
        # Common technical IDs
        r'PR#\d+',
        r'Issue#\d+',
        r'FEAT-\d+',
    ]
    
    for fp_pattern in false_positives:
        if re.search(fp_pattern, context, re.IGNORECASE):
            return True
    
    return False

def validate_shape(p, i, rec, role):
    ok = True
    # required shape checks apply to ALL records (legacy and new)
    if rec.get("role") != role:
        err(p, i, "role mismatch with directory name")
        ok = False
    if rec.get("event") not in EVENTS:
        err(p, i, f"bad event '{rec.get('event')}'")
        ok = False
    if not DATE.match(rec.get("period","")):
        err(p, i, "bad 'period' format (YYYY-MM-DD)")
        ok = False
    if "items" in rec and not isinstance(rec["items"], list):
        err(p, i, "'items' must be a list if present")
        ok = False
    if "links" in rec and not isinstance(rec["links"], list):
        err(p, i, "'links' must be a list if present")
        ok = False
    if "ts" not in rec:
        err(p, i, "missing 'ts'")
        ok = False
    return ok

def validate_strict(p, i, rec):
    """Strict rules apply only to records with ts >= BASELINE_TS."""
    ok = True
    # items limits
    items = rec.get("items", [])
    if len(items) > MAX_ITEMS:
        err(p, i, f"too many items ({len(items)} > {MAX_ITEMS})")
        ok = False
    for it in items:
        if len(str(it)) > MAX_ITEM_CHARS:
            err(p, i, f"item too long (> {MAX_ITEM_CHARS} chars)")
            ok = False
    # links patterns
    links = rec.get("links", [])
    for ln in links:
        if not LINK_TOKEN.match(str(ln)):
            err(p, i, f"link token invalid: {ln}")
            ok = False
    # handoff-specific: must @tag and have actionable link(s)
    if rec.get("event") == "handoff":
        if not any(isinstance(x, str) and x.startswith("@") for x in items):
            err(p, i, "handoff requires @tag in items[]")
            ok = False
        if not links:
            err(p, i, "handoff requires at least one actionable link")
            ok = False
    return ok

def main():
    ok_all = True
    for p in J.rglob("*.ndjson"):
        role = p.parent.parent.name
        lines = p.read_text().splitlines()
        for idx, line in enumerate(lines, 1):
            try:
                rec = json.loads(line)
            except Exception as e:
                err(p, idx, f"not JSON: {e}")
                ok_all = False
                continue
            if not validate_shape(p, idx, rec, role):
                ok_all = False
                continue
            
            # Security validation applies to ALL records
            if not validate_security(p, idx, rec):
                ok_all = False
                continue
            
            # Strict checks only for records at/after baseline
            try:
                ts = parse_iso(rec["ts"])
            except Exception as e:
                err(p, idx, f"bad ts: {rec.get('ts')}")
                ok_all = False
                continue
            if ts >= BASELINE_TS:
                if not validate_strict(p, idx, rec):
                    ok_all = False
            else:
                # Legacy record: encourage cleanup without failing CI
                if rec.get("event") == "handoff":
                    warn(p, idx, "legacy handoff missing strict rules (pre-baseline)")
    sys.exit(0 if ok_all else 1)

if __name__ == "__main__":
    main()