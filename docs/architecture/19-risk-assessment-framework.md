---
title: "SecFlow — Risk Assessment, Scoring & Prioritization Framework"
author: "Hernan Trajtemberg, Lead Security Engineer"
codename: "SecFlow"
version: "1.0"
date: "2025-10-06"
---

# 19 — Risk Assessment, Scoring & Prioritization Framework

## 🧭 Overview

The **Risk Assessment Framework** in SecFlow provides a consistent and transparent way to evaluate and prioritize vulnerabilities across multiple projects and tools.  
It merges four complementary standards:

1. **NIST 5×5 Matrix** — contextual risk evaluation (Impact × Likelihood).  
2. **CVSS v3.1** — standardized vulnerability severity scoring.  
3. **CWE / OWASP Mapping** — weakness classification.  
4. **MITRE ATT&CK Correlation** — adversarial behavior context.

This layered model supports both **quantitative** (numeric scores) and **qualitative** (High/Critical/etc.) analysis for triage and reporting.

---

## 🧱 Architecture Overview

```text
+-------------------------------------------------------------+
|                SecFlow Risk Engine                          |
| - CVSS Normalizer (from findings or enrichment)            |
| - NIST 5×5 Contextual Matrix                               |
| - MITRE ATT&CK Mapper                                      |
| - Risk Aggregator & Scorer                                 |
| - Project Risk Dashboard                                   |
+-------------------------------------------------------------+
```yaml

---

## ⚙️ Core Objectives

| Goal | Description |
|------|-------------|
| **Standardization** | Consistent risk scoring across tools and projects. |
| **Transparency** | Traceable logic behind every score. |
| **Extensibility** | Pluggable scoring policies (per organization). |
| **Automation** | Auto-scoring during enrichment and triage. |
| **Context-Awareness** | Includes exploitability, exposure, and asset criticality. |

---

## 🧱 Scoring Pipeline

```text
Finding
   ↓
CVSS Vector Parsing
   ↓
CWE / OWASP Classification
   ↓
Exploit & Exposure Context
   ↓
NIST Risk Matrix Evaluation
   ↓
Final Risk Score (0–100) + Risk Tier
```text

---

## 🧠 CVSS Normalization

SecFlow ingests CVSS vectors either from NVD (via enrichment) or tool metadata.

### Example:
```text
CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H
```text

Converted into internal representation:
```json
{
  "base_score": 9.8,
  "impact_subscore": 5.9,
  "exploitability_subscore": 3.9,
  "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H"
}
```json

If missing, heuristic fallback is applied based on CWE ID or OWASP category (see [13-cve-cwe-poc-enrichment-layer.md](13-cve-cwe-poc-enrichment-layer.md)).

## 🧩 CWE / OWASP Mapping

| CWE ID | OWASP Category | Default Impact | Default Likelihood |
|--------|----------------|----------------|-------------------|
| 79 | A03: Injection | High | High |
| 89 | A03: Injection | Very High | High |
| 200 | A01: Broken Access Control | High | Medium |
| 601 | A10: SSRF | Medium | Medium |
| 787 | A05: Buffer Overflow | Critical | Medium |
| 352 | A08: CSRF | Medium | High |

Mappings are maintained in `/resources/mappings/cwe_owasp.json`.

## 🧠 MITRE ATT&CK Mapping

Findings enriched with ATT&CK technique IDs (TIDs) during correlation (see [13-cve-cwe-poc-enrichment-layer.md](13-cve-cwe-poc-enrichment-layer.md)) are leveraged to infer attack chain context.

| MITRE Technique ID | Tactic | Effect |
|-------------------|--------|--------|
| T1059.007 | Execution | Cross-Site Scripting |
| T1505.003 | Persistence | SQL Injection |
| T1071.001 | Command & Control | Web Protocols |
| T1190 | Initial Access | Exploit Public-Facing App |

This mapping helps classify whether the finding affects initial compromise, lateral movement, or data exfiltration.

## ⚙️ NIST 5×5 Risk Matrix

### Definition
| Impact ↓ / Likelihood → | Very Low | Low | Medium | High | Very High |
|------------------------|----------|-----|--------|------|-----------|
| **Very High** | Medium | High | High | Critical | Critical |
| **High** | Low | Medium | High | High | Critical |
| **Medium** | Low | Low | Medium | High | High |
| **Low** | Low | Low | Low | Medium | High |
| **Very Low** | Low | Low | Low | Low | Medium |

### Mapping to Severity
| Result | Score Range | Label |
|--------|-------------|-------|
| Critical | 90–100 | 🔥 |
| High | 70–89 | ⚠️ |
| Medium | 40–69 | ⚖️ |
| Low | 20–39 | 🧩 |
| Informational | 0–19 | ℹ️ |

## 🧩 Likelihood Factors

Likelihood is dynamically computed using multiple context sources:

| Factor | Description | Weight |
|--------|-------------|--------|
| Exploit Availability | Known PoC, KEV presence | +0.3 |
| Network Exposure | Publicly reachable target | +0.25 |
| Authentication Required | Lowers likelihood if true | -0.15 |
| Complexity | Tool-derived complexity | ±0.1 |
| Detection Confidence | Based on finding engine | ±0.2 |

### Pseudo-code:
```python
def likelihood_score(finding):
    score = 0.3 if finding.poc_available else 0
    if finding.exposure == "internet": score += 0.25
    if finding.auth_required: score -= 0.15
    if finding.complexity == "low": score += 0.1
    return min(max(score, 0), 1)
```python

## 🧠 Impact Factors

Impact combines technical and business context:

| Factor | Example | Weight |
|--------|---------|--------|
| Confidentiality | Data exposure | +0.3 |
| Integrity | Tampering possible | +0.3 |
| Availability | Service crash, DoS | +0.2 |
| Privilege Escalation | Root/system access | +0.2 |
| Asset Criticality | System importance | +0.4 |

Final impact = weighted sum normalized to 1.0.

## ⚙️ Combined Risk Formula

Final quantitative risk score (0–100):

```python
risk_score = ((CVSS_base / 10) * 0.6 + impact_factor * 0.25 + likelihood_factor * 0.15) * 100
```python

Rounded to nearest integer.

### Example
| Metric | Value |
|--------|-------|
| CVSS Base | 9.8 |
| Impact Factor | 0.8 |
| Likelihood Factor | 0.7 |
| Final Score | `((0.98*0.6)+(0.8*0.25)+(0.7*0.15))*100 = 89.7` → **High** |

## 🧠 Contextual Adjustments

Certain contexts modify final risk score:

| Context | Adjustment |
|---------|------------|
| Active exploit in wild (CISA KEV) | +10 |
| Proof-of-concept verified | +5 |
| Patched version available | -5 |
| Internal-only system | -10 |
| Compensating controls present | -15 |

Scores are capped at 100 and floored at 0.

## 🧩 Aggregated Risk Dashboard

Each project's analytics tab visualizes:

| Metric | Description |
|--------|-------------|
| Average CVSS per project | |
| Top 10 findings by risk score | |
| Risk evolution over time | |
| Distribution by OWASP category | |
| ATT&CK tactics heatmap | |

### Example chart:
```text
Risk Trend (Score over Time)
│        ████████ High
│   ████ Medium
│  ██
└────────────────────────────
   Jan  Feb  Mar  Apr  May
```text

## ⚙️ Risk Normalization Across Tools

Different tools report different severity models (e.g., "Critical", "High", "Medium").
SecFlow converts all to internal numeric ranges:

| Tool | Critical | High | Medium | Low |
|------|----------|------|--------|-----|
| Nuclei | 90–100 | 70–89 | 40–69 | 20–39 |
| ZAP | 85–100 | 65–84 | 35–64 | 15–34 |
| Burp | 90–100 | 75–89 | 45–74 | 25–44 |

All are harmonized via the risk formula to produce consistent prioritization.

## 🧠 Risk Aggregation & Reporting

Project-level risk is computed as weighted mean:

```python
def project_risk(findings):
    weights = [f.cvss_score * f.impact_weight for f in findings]
    return sum(weights) / len(weights)
```python

Analytics engine stores snapshots in `/analytics/risk_snapshots/`.

## 🧩 Risk API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/risk/score/{finding_id}` | GET | Returns risk vector and classification |
| `/api/v1/risk/project/{id}` | GET | Aggregated project risk summary |
| `/api/v1/risk/export` | POST | Export risk data to JSON/CSV |
| `/api/v1/risk/heatmap` | GET | Generates OWASP × ATT&CK matrix |

### Example Response:
```json
{
  "finding_id": "abcd-123",
  "score": 89.7,
  "severity": "High",
  "CVSS": 9.8,
  "impact_factor": 0.8,
  "likelihood_factor": 0.7,
  "nist_matrix": "High/High → Critical",
  "owasp": "A03: Injection",
  "mitre_tid": "T1505.003"
}
```json

## 🔒 Auditability & Traceability

Every risk computation is versioned and auditable:
- Stored with enrichment metadata hash.
- Recomputed automatically if CVSS source data updates.

### Log entry example:
```json
{
  "event": "risk_recalc",
  "finding_id": "abcd-123",
  "old_score": 78,
  "new_score": 89.7,
  "reason": "CISA KEV inclusion"
}
```

## 🔮 Future Enhancements

- Integration with EPSS (Exploit Prediction Scoring System).
- ML-based contextual risk forecasting.
- Auto-adjustment based on exploit telemetry feeds.
- Risk-driven workflow prioritization for automated scanning.
- AI-assistant suggestions for mitigations.

---

**Next:** [Migration & Implementation Phases](20-migration-and-implementation-phases.md)
