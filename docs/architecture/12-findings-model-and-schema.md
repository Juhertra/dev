---
title: "SecFlow — Findings Model & Schema Normalization"
author: "Hernan Trajtemberg, Lead Security Engineer"
codename: "SecFlow"
version: "1.0"
date: "2025-10-06"
---

# 12 — Findings Model & Schema Normalization

## 🧭 Overview

The **Findings Schema** is the canonical data contract for SecFlow —  
it defines how vulnerabilities, anomalies, and tool outputs are normalized, enriched, and persisted.

Every discovery, scan, or enrichment step in the workflow produces **Findings**, which are standardized across tools (Nuclei, Ferox, ZAP, Caido, custom detectors).

The schema ensures:
- Cross-tool consistency  
- Automated CVE/CWE/OWASP correlation  
- Risk scoring alignment (CVSS/NIST)  
- Deterministic enrichment for analytics and triage  

---

## 🧱 Data Flow Summary

```
[ Tool Output ]
        ↓
[ Findings Engine ]
        ↓
[ Normalization Layer ]
        ↓
[ Enrichment Layer (CVE/CWE/OWASP) ]
        ↓
[ Persistent Store + Cache + Analytics ]
```

---

## ⚙️ Findings Core Model

```
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime

class Finding(BaseModel):
    id: UUID
    project_id: UUID
    run_id: Optional[UUID]
    detector_id: str = Field(description="canonical tool or plugin id, e.g. scan.nuclei")
    title: str
    severity: str  # enum: info, low, medium, high, critical
    resource: str  # canonical URL or identifier
    evidence: Dict[str, object] = {}
    cwe: Optional[int]
    owasp: Optional[str]
    cve_ids: List[str] = []
    cvss: Optional[float]
    mitre_attack: List[str] = []
    poc_links: List[str] = []
    created_at: datetime
    provenance: Dict[str, object] = {}
```

## 🧩 Normalization Process

Each wrapper or plugin output goes through the Findings Normalizer, which performs:

1. Schema validation
2. Severity normalization
3. Field mapping
4. Evidence compression
5. Deduplication

### Example Normalized Finding

```
{
  "id": "7a3d9f8e-1f83-4a55-9a6c-5ea9e1a3b8d2",
  "project_id": "b0b8b6e0-7c6a-43e8-8b2f-8a0d0e8b0f3c",
  "run_id": "2a2b3c4d-5e6f-7081-92a3-b4c5d6e7f809",
  "detector_id": "scan.nuclei",
  "title": "X-Frame-Options header missing",
  "severity": "low",
  "resource": "https://app.acme.com/",
  "evidence": { "request_id": "r-01HXXQ5AKP0NWS", "template": "misconfig/headers/xfo-missing.yaml" },
  "cwe": 693,
  "owasp": "A05",
  "cve_ids": [],
  "cvss": 3.7,
  "mitre_attack": ["T1190"],
  "poc_links": [],
  "created_at": "2025-10-07T08:22:31Z",
  "provenance": { "tool_version": "nuclei 3.1.0", "host": "runner-12" }
}
```

```
def normalize(raw: dict, source: str) -> Finding:
    severity_map = {"info": "info", "low": "low", "medium": "medium", "high": "high", "critical": "critical"}
    return Finding(
        id=str(uuid4()),
        project_id=raw.get("project_id"),
        detector_id=source,
        title=raw.get("info", {}).get("name") or raw.get("title", "Unnamed Finding"),
        severity=severity_map.get(raw.get("severity", "info")),
        path=raw.get("matched-at") or raw.get("url"),
        evidence=raw,
        created_at=datetime.utcnow(),
        provenance={"tool": source, "version": raw.get("version", "unknown")}
    )
```

## 🧩 Normalization Rules by Source

| Tool | Input Format | Mapping |
|------|--------------|---------|
| **Nuclei** | JSON lines | `info.name` → `title`, `info.severity` → `severity`, `matched-at` → `path` |
| **Feroxbuster** | Text | `URL` → `path`, `status` → `evidence.status` |
| **ZAP/Burp** | XML/JSON | `PluginId` → `cwe`, `RiskDesc` → `severity` |
| **Caido** | SQLite | `Vulnerability.name` → `title`, `score` → `cvss_score` |
| **Custom Detectors** | Python dict | Arbitrary fields normalized via schema mapping |

Normalization is performed by `findings-engine` using source-specific adapters.

## 🧠 Severity Mapping

| Raw Severity | Normalized | CVSS Equivalent |
|--------------|------------|-----------------|
| informational | info | 0.0–3.9 |
| low | low | 4.0–6.9 |
| medium | medium | 6.0–7.4 |
| high | high | 7.5–8.9 |
| critical | critical | 9.0–10.0 |

## 🧠 Deduplication Strategy

Findings are hashed on a deterministic fingerprint:

```
hash_input = f"{finding.path}:{finding.title}:{finding.detector_id}"
finding_hash = hashlib.sha256(hash_input.encode()).hexdigest()
```

If the hash already exists in the same project and run scope, the finding is merged rather than duplicated.

## 🧩 Enrichment Metadata Structure

```
finding.enrichment = {
    "cwe": {"id": 89, "name": "SQL Injection"},
    "owasp": {"category": "A03", "name": "Injection"},
    "CVSS": {"score": 9.1, "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H"},
    "mitre": {"technique": "T1505", "tactic": "Persistence"},
    "poc": {"source": "exploitdb", "link": "https://www.exploit-db.com/exploits/52341"}
}
```

This metadata is populated during the Enrichment Phase (CVE/CWE/CVSS sync).

## 🧩 CVE / CWE / OWASP Mapping

### CVE → CWE
- NVD API provides `cve.affects.vendor.vendor_data` → `cwe.id`
- Mapping stored in local SQLite cache.

### CWE → OWASP
| CWE | OWASP Category |
|-----|----------------|
| CWE-79 | A03: Injection |
| CWE-89 | A03: Injection |
| CWE-287 | A07: Identification and Authentication Failures |
| CWE-601 | A10: Server-Side Request Forgery (SSRF) |

### Example Mapping Resolver
```
def resolve_owasp(cwe_id):
    mapping = {"79": "A03", "89": "A03", "287": "A07", "601": "A10"}
    return mapping.get(str(cwe_id))
```

## 🧩 Confidence & Risk Scoring

Confidence combines tool reliability, correlation consistency, and enrichment coverage.

### Formula
```
confidence = (tool_weight * 0.5) + (enrichment_score * 0.3) + (cross_source_count * 0.2)
```

### Risk Score Calculation
```
risk_score = CVSS * confidence
```

This allows probabilistic triage prioritization.

## 🧠 Evidence Normalization

Evidence is stored in compact, structured form for indexing:

```
{
  "request": {
    "method": "POST",
    "url": "https://target.com/login",
    "headers": {"Content-Type": "application/json"},
    "body": "{\"username\":\"admin\"}"
  },
  "response": {
    "status": 500,
    "headers": {"Server": "Apache"},
    "body_snippet": "SQL syntax error"
  }
}
```

Large payloads are truncated or compressed to avoid storage overhead.

## 🧩 Finding Status Lifecycle

| Status | Meaning | Managed By |
|--------|---------|------------|
| open | Newly discovered issue | Scanner |
| triaged | Analyst reviewed | Analyst |
| resolved | Fixed or confirmed | Analyst |
| false_positive | Invalid finding | Analyst |
| archived | Expired or obsolete | System (GC) |

Each status change triggers an audit log event and optional webhook notification.

## 🧱 Storage Layer Integration

Findings are persisted via the `StoragePort` interface:

```
class FindingsRepository(Protocol):
    def save(self, finding: Finding) -> None:
        """Save a finding to storage."""
        pass
    
    def list(self, project_id: str) -> List[Finding]:
        """List findings for a project."""
        pass
    
    def get(self, id: str) -> Finding:
        """Get a finding by ID."""
        pass
```

### Supported backends:
- SQLite (default local mode)
- PostgreSQL (production multi-project)
- JSON (testing or demo mode)

## 🧩 Findings Export Schema

SecFlow exports findings in structured formats for interoperability:

| Format | Command |
|--------|---------|
| JSON | `SecFlow export findings --format json` |
| CSV | `SecFlow export findings --format csv` |
| HTML | `SecFlow report findings --template summary.html` |
| SARIF | `SecFlow export findings --format sarif` |

### Example JSON export:
```
{
  "project": "acme-api",
  "findings": [
    {
      "id": "a2b4f3c8-d9e2-4f1a-5b6c-7d8e9f0a1b2c",
      "title": "SQL Injection",
      "severity": "critical",
      "cwe": 89,
      "cvss_score": 9.1,
      "path": "/login",
      "created_at": "2025-10-06T10:15:00Z"
    }
  ]
}
```

## 🧠 Indexing & Analytics

Each finding is indexed in the analytics database:

- **Primary Index:** `project_id` + `severity` + `cwe`
- **Full-Text Search:** `title`, `path`, `evidence.body_snippet`
- **Aggregations:** count by severity, top affected endpoints, common CWE classes.

The metrics system (see [06-plugin-system.md](06-plugin-system.md) & [17-observability-logging-and-metrics.md](17-observability-logging-and-metrics.md)) uses these indexes to generate dashboards.

## 🔮 Future Enhancements

- Graph-based finding correlation (attack paths).
- AI-driven risk clustering ("find similar vulnerabilities").
- Contextual auto-triage (OWASP/NIST mapping feedback loops).
- Delta reports between runs (`run_id` diff).
- Live sync to vulnerability management platforms (DefectDojo, VulnDB).

---

**Next:** [CVE/CWE/POC Enrichment Layer](13-cve-cwe-poc-enrichment-layer.md)
```
```
```
```
```
```
```
```
```
```
```
```
```
```
```
```
```
```
```
```
```
```