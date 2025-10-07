# Phase 4A Implementation Plan

**Goal:** Improve day-to-day usability and accuracy without touching authentication. Keep all existing routes stable. Make small, surgical PRs with proofs in `DEBUG_RUN.md`.

## Guardrails Confirmed

✅ **No route renames** - Only additive endpoints  
✅ **No breaking storage changes** - Only add fields to existing JSON  
✅ **Reuse canonical endpoint helpers** - `utils/endpoints.py:endpoint_key()`, `endpoint_safe_key()`  
✅ **Use existing file-backed storage** - Add indexes where helpful  
✅ **Each PR adds proof block** to `DEBUG_RUN.md` and updates `ARCHITECTURE_MAP.md` & `FILE_INDEX.md` if new files appear

## Canonical Key System Confirmed

**Single Source of Truth Functions** (`utils/endpoints.py`):
- `endpoint_key(method, base_or_url, path=None)` → `"GET https://api.example.com/users"`
- `endpoint_safe_key(key)` → `"GET_https_api_example_com_users"` (for filenames)

**Current Usage Pattern**:
- Dossier files: `ui_projects/<pid>/endpoints/{safe_key}.json`
- Route handlers: `routes/sitemap.py::sitemap_endpoint_preview()` uses `endpoint_key()`
- Storage: `store.py::update_endpoint_dossier_by_key()` uses `endpoint_safe_key()`

---

## PR-0 — Pre-flight plan & pointers ✅

**Status**: Complete - This document serves as the plan

---

## PR-1 — Detectors enrichment & Findings UX

### Files to Touch

**Core Storage & Logic**:
- `findings.py` - Add enrichment fields to `_write_findings()` and `append_findings()`
- `store.py` - Extend dossier update logic for enriched findings
- `routes/nuclei.py::nuclei_scan()` - Post-scan normalization with CVE/CWE matcher

**Templates & UI**:
- `templates/finding_detail.html` - Add CVE/CWE chips and "View CVE" links
- `static/js/main.js` - Add external link handlers

**Schema Extensions** (non-breaking):
- `forChatGPT/DATA_SCHEMA/findings.schema.json` - Add optional enrichment fields

### Implementation Details

**Enrichment Fields** (add to existing findings):
```json
{
  "cve_id": "CVE-2023-1234",           // Optional CVE identifier
  "cwe": "CWE-89",                     // Existing field, ensure populated
  "affected_component": "database",     // New: component affected
  "evidence_anchors": ["line:45", "param:user_id"], // New: evidence locations
  "suggested_remediation": "Use parameterized queries" // New: remediation hint
}
```

**CVE/CWE Matcher** (`routes/nuclei.py`):
- Simple map: `nuclei_template_id → {cve_id, cwe, remediation}`
- Post-scan normalization in `nuclei_scan()` function

**UI Enhancements**:
- CVE chips with external links to `https://cve.mitre.org/cgi-bin/cvename.cgi?name={cve_id}`
- "View Run" button linking to `/p/<pid>/runs?highlight=<run_id>`

---

## PR-2 — Nuclei Templates Manager

### Files to Touch

**New Routes**:
- `routes/tools.py` - New file for tools management
- `templates/tools/index.html` - New template for tools page

**Integration Points**:
- `routes/nuclei.py` - Existing nuclei adapter integration
- `routes/__init__.py` - Register new tools blueprint

### Implementation Details

**Tools Page** (`/p/<pid>/tools`):
- Nuclei Templates card with count, last indexed time
- "Reindex" button → calls `nuclei_integration.update_templates()`
- "Self-test" button → dry run with JSON response
- Quick-select presets: "top-50-web", "auth", "info", "high-impact"

**Template Presets**:
```json
{
  "top-50-web": ["http-methods", "sqli-auth", "xss", "..."],
  "auth": ["jwt-secrets", "oauth-bypass", "..."],
  "info": ["http-methods", "tech-detect", "..."],
  "high-impact": ["rce", "ssrf", "xxe", "..."]
}
```

---

## PR-3 — Vulnerabilities hub page

### Files to Touch

**New Routes**:
- `routes/vulns.py` - New file for vulnerabilities aggregation
- `templates/vulns.html` - New template for vulns page

**Integration Points**:
- `routes/sitemap.py` - Add link from Site Map header
- `routes/__init__.py` - Register vulns blueprint

### Implementation Details

**Vulnerabilities Page** (`/p/<pid>/vulns`):
- Aggregate findings across runs by endpoint + vuln signature
- Columns: Endpoint (METHOD + path), Title/ID, Total occurrences, Latest run, Worst severity, Actions
- Reuse dossier + runs data to compute worst/last
- Link from Site Map header to `/vulns`

**Data Aggregation**:
- Group by: `endpoint_key` + `detector_id` (nuclei template)
- Compute: total occurrences, latest run, worst severity across all runs

---

## PR-4 — Site Map drawers final polish

### Files to Touch

**Templates**:
- `templates/drawer_endpoint_preview.html` - Polish preview drawer
- `templates/drawer_endpoint_runs.html` - Polish runs drawer

**Routes**:
- `routes/sitemap.py::sitemap_endpoint_preview()` - Enhance preview logic
- `routes/sitemap.py::sitemap_runs_for_endpoint()` - Enhance runs logic

**Frontend**:
- `static/js/main.js` - Add relative time helpers, copy actions

### Implementation Details

**Preview Drawer**:
- Sections order: cURL → Headers → Params → Body (render only if present)
- Coverage: read from dossier via canonical key (queued?, last run id/time, worst severity)
- Buttons: Copy URL, Copy cURL, Add to Queue, Run Now, View Runs

**Runs Drawer**:
- Table: When (relative), Run ID, Templates (#), Findings, Worst, Actions
- Empty state: "No runs yet" + Add to Queue / Run Now inline actions
- Relative times: "Xm ago" with ISO tooltip

---

## PR-5 — SSE Live Runner resiliency & signals

### Files to Touch

**Backend**:
- `routes/nuclei.py::nuclei_stream()` - Enhance SSE stream with heartbeats

**Frontend**:
- `static/js/main.js` - Enhance SSE listener for heartbeats
- `templates/active_testing.html` - Update Live Results panel

### Implementation Details

**SSE Stream Enhancement**:
- Deterministic flow: `start` → periodic `: ping` heartbeats (every 1-2s) → streaming progress → `done`
- Headers: `text/event-stream`, `no-cache`, `keep-alive`, `X-Accel-Buffering: no`
- Backpressure/timeout handling (no thread leak)

**Heartbeat Format**:
```
event: ping
data: {"timestamp": "2024-01-15T10:45:30Z", "status": "active"}
```

---

## PR-6 — Storage & Performance hardening

### Files to Touch

**Storage Layer**:
- `store.py` - Add index file creation and management
- `cache.py` - Add new cache keys and invalidation logic

**Routes**:
- `routes/sitemap.py` - Use indexes for faster reads
- `routes/vulns.py` - Use indexes for aggregation

### Implementation Details

**Light Indexes**:
- `ui_projects/<pid>/indexes/endpoints.json` - Map safe_key → last_run_id/worst
- `ui_projects/<pid>/indexes/runs_recent.json` - Latest N run_ids + metadata

**Cache Keys**:
- `sitemap:{pid}`, `templates:index:{pid}`, `runs:index:{pid}`, `dossier:{pid}:{key}`
- Bust: when queue changes, run saved, dossier updated, templates reindexed

---

## PR-7 — Tools Manager & Workboard

### Files to Touch

**Tools Manager** (extends PR-2):
- `routes/tools.py` - Add "Active Tools" selector
- `templates/tools/index.html` - Add multi-select tools UI

**New Workboard**:
- `routes/workboard.py` - New file for workboard functionality
- `templates/workboard/index.html` - New template for workboard
- `static/js/workboard.js` - New JS for drag-and-drop (if needed)

**Storage**:
- `ui_projects/<pid>/tools_active.json` - Active tools selection
- `ui_projects/<pid>/workboard.json` - Workboard state

### Implementation Details

**Tools Manager**:
- Multi-select: Nuclei, Detectors-Pack A/B, Placeholder "Custom Tool"
- Persists to `tools_active.json`

**Workboard MVP**:
- Columns: New, Confirmed, In Progress, Fixed, Ignored
- Cards: findings with endpoint + title + severity + latest run id
- Actions: move card (POST update state in `workboard.json`)

---

## PR-8 — Consistency pass (UI kit-level)

### Files to Touch

**Templates**:
- `templates/drawer_endpoint_preview.html` - Consistent header layout
- `templates/drawer_endpoint_runs.html` - Consistent header layout
- `templates/finding_detail.html` - Consistent header layout

**Frontend**:
- `static/js/main.js` - Toast notifications for all "Copy" actions
- `static/main.css` - Consistent drawer header styles

### Implementation Details

**Consistency Requirements**:
- Drawer headers and action bars visually consistent (chips, spacing, buttons)
- Toast notifications for all "Copy" actions
- Exactly one `#global-indicator` and one `#panel-body` per page
- Keyboard affordances: Enter triggers primary action, ESC closes drawer

---

## PR-9 — Proof & Smoke

### Files to Touch

**Testing**:
- `tools/smoke.py` - Extend smoke test for Phase 4A features
- `DEBUG_RUN.md` - Add "Phase 4A — Final Proof (Petstore)" section

### Implementation Details

**Extended Smoke Test**:
- Petstore import, queue 2 endpoints, run scan with run_id, read SSE first bytes
- Preview & Runs drawers probes (200 + non-empty)
- Vulns page returns rows
- Tools Manager shows template count and active tool selection round-trip
- Workboard move persists

**Final Proof Block**:
- Before/After drawer excerpts, SSE lines, scan JSON head, dossier file paths
- Vulns page clip, tools/workboard JSON heads

---

## File Map Summary

### Existing Files (Confirmed Present)
- `routes/sitemap.py` - Site map and drawer routes ✅
- `routes/nuclei.py` - Nuclei integration and SSE ✅
- `routes/findings.py` - Findings management ✅
- `routes/queue.py` - Queue management ✅
- `templates/drawer_endpoint_preview.html` - Preview drawer ✅
- `templates/drawer_endpoint_runs.html` - Runs drawer ✅
- `templates/finding_detail.html` - Finding detail ✅
- `store.py` - Storage layer ✅
- `findings.py` - Findings logic ✅
- `utils/endpoints.py` - Canonical key helpers ✅
- `static/js/main.js` - Frontend utilities ✅

### New Files to Create
- `routes/tools.py` - Tools management
- `routes/vulns.py` - Vulnerabilities hub
- `routes/workboard.py` - Workboard functionality
- `templates/tools/index.html` - Tools page
- `templates/vulns.html` - Vulnerabilities page
- `templates/workboard/index.html` - Workboard page
- `static/js/workboard.js` - Workboard interactions (if needed)

### Storage Extensions
- `ui_projects/<pid>/indexes/endpoints.json` - Endpoint index
- `ui_projects/<pid>/indexes/runs_recent.json` - Runs index
- `ui_projects/<pid>/tools_active.json` - Active tools
- `ui_projects/<pid>/workboard.json` - Workboard state

---

## Architecture Map Updates Required

**Sections to Update**:
1. **Route Table Snapshot** - Add new routes from PR-2, PR-3, PR-7
2. **Filesystem Layout** - Add new index files and workboard storage
3. **Frontend JS Utilities** - Add new utility functions for tools/workboard
4. **How to Extend** - Add examples for new detector enrichment patterns

**FILE_INDEX.md Updates**:
- Add new routes and templates to appropriate feature sections
- Update file pointers for enhanced functionality

---

## Implementation Order

1. **PR-0** ✅ (This plan)
2. **PR-1** - Detectors enrichment & Findings UX
3. **PR-2** - Nuclei Templates Manager
4. **PR-3** - Vulnerabilities hub page
5. **PR-4** - Site Map drawers final polish
6. **PR-5** - SSE Live Runner resiliency
7. **PR-6** - Storage & Performance hardening
8. **PR-7** - Tools Manager & Workboard
9. **PR-8** - Consistency pass
10. **PR-9** - Proof & Smoke

Each PR will be implemented sequentially with proof blocks added to `DEBUG_RUN.md` and architecture documentation updated as needed.
