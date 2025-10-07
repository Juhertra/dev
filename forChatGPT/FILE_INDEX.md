# 📁 Feature → Files Index

**Quick navigation for developers who need to find implementation by feature**

## 🔍 Core Features

### Project Management
- **Project Creation**: `store.py:create_project()` → `PROJECTS_INDEX` file  
- **Project Switching**: `store.py:set_current_project_id()` → URL redirects
- **Project Storage**: `ui_projects/<pid>.json` runtime state

### Site Map & Navigation  
- **Site Map Page**: `routes/sitemap.py:site_map_page()` → `templates/sitemap.html`
- **Site Map Builder**: `sitemap_builder.py:build_site_map()` → cached endpoint tree
- **Endpoint Filtering**: `static/main.js:applySitemapFilters()` → DOM manipulation

### Drawer System
- **Preview Drawer**: `routes/sitemap.py:sitemap_endpoint_preview()` → `templates/drawer_endpoint_preview.html`
- **Runs Drawer**: `routes/sitemap.py:sitemap_runs_for_endpoint()` → `templates/drawer_endpoint_runs.html`
- **Finding Detail**: `routes/findings.py:finding_detail()` → `templates/finding_detail.html`
- **Drawer Manager**: `static/main.js:openPanelWith()` → HTMX integration

### Test Queue & Execution
- **Queue Display**: `routes/queue.py:queue_page()` → `templates/queue.html`
- **Item Details**: `routes/queue.py:queue_item_details()` → `templates/queue_item_details.html` 
- **Active Scanning**: `routes/nuclei.py:nuclei_scan()` → `templates/active_testing.html`
- **SSE Streams**: `routes/nuclei.py:nuclei_stream()` → EventSource API

### Findings Management
- **Findings List**: `routes/findings.py:findings_page()` → `templates/findings_clean.html`
- **Triage System**: `routes/findings.py:triage_finding()` → status updates
- **Export Functions**: `routes/findings.py:export_group()` → JSON dump API
- **Group Management**: `routes/findings.py:triage_group()` → bulk operations
- **Enrichment System**: `findings.py:Finding` dataclass → CVE/CWE enrichment (Phase 4A)
- **CVE/CWE Matcher**: `nuclei_integration.py:_enrich_finding_with_cve_cwe()` → template mapping
- **Enriched UI**: `templates/finding_detail.html` → CVE chips + enrichment section

### Findings Contract & Normalization (P4)
- **Normalization**: `utils/findings_normalize.py:normalize_finding()` → single source of truth
- **Schema Validation**: `utils/schema_validation.py:validate_json()` → JSON schema compliance
- **Contract Tests**: `tests/test_findings_normalize.py` → 18 unit tests
- **Append Tests**: `tests/test_append_and_cache.py` → 5 contract tests
- **SSE Tests**: `tests/test_sse_stream.py` → 5 SSE contract tests
- **Pre-commit Guards**: `scripts/pre-commit-guards.sh` → regression prevention
- **CI Integration**: `.github/workflows/findings-contract.yml` → automated enforcement

### Dashboard (Phase 4A)
- **Dashboard Page**: `routes/dashboard.py:dashboard_page()` → `templates/dashboard.html`
- **Dashboard Data**: `routes/dashboard.py:_compute_dashboard_tiles()` → tiles aggregation
- **Trends Chart**: `routes/dashboard.py:_compute_findings_trends()` → 14-day sparkline
- **Recent Runs**: `routes/dashboard.py:_get_recent_runs()` → last 5 runs table
- **Top Endpoints**: `routes/dashboard.py:_get_top_endpoints_by_findings()` → findings ranking

### Tools Management (Phase 4A)
- **Tools Manager**: `routes/tools.py:tools_page()` → `templates/tools/index.html`
- **Nuclei Integration**: `routes/tools.py:nuclei_reindex()` → template count and timing
- **Self-test**: `routes/tools.py:nuclei_selftest()` → fixture template validation
- **Presets**: `tools/presets.json` → template category arrays
- **Fixtures**: `tools/fixtures/nuclei/` → test templates for self-test

### Vulnerabilities Hub (Phase 4A + P7 Bulk Triage)
- **Vulns Page**: `routes/vulns.py:vulns_page()` → `templates/vulns.html`
- **Aggregation**: `routes/vulns.py:_compute_vulns_summary()` → endpoint + detector grouping
- **Cache System**: `ui_projects/<pid>/indexes/vulns_summary.json` → validated aggregation cache
- **HTMX Actions**: `routes/vulns.py:vulns_preview()` → preview drawer integration
- **Cache Busting**: `store.py:_bust_vulns_cache()` → automatic invalidation
- **Bulk Triage**: `routes/vulns.py:vulns_bulk_actions()` → `POST /p/<pid>/vulns/bulk`
- **Bulk Helper**: `routes/vulns.py:_apply_bulk_actions()` → batch processing with caching
- **UI Partials**: `templates/_partials/vulns_table.html` + `vulns_bulkbar.html` → HTMX integration
- **Selection Model**: `static/js/vulns-bulk.js` → minimal JS with HTMX event handling
- **Bulk Styles**: `static/css/vulns-bulk.css` → responsive sticky bulk bar
- **Bulk Tests**: `tests/test_bulk_triage.py` → comprehensive bulk operation tests

### Metrics & Analytics Dashboard (P6)
- **Metrics Page**: `routes/metrics.py:project_metrics()` → `templates/metrics.html`
- **Analytics Core**: `analytics_core/analytics.py:get_metrics()` → comprehensive metrics computation
- **Filtered Metrics**: `analytics_core/analytics.py:get_filtered_metrics()` → status/owner/date/tag filtering
- **Cache Management**: `analytics_core/analytics.py:rebuild_metrics_cache()` → metrics cache rebuild
- **Export Functionality**: `routes/metrics.py:export_metrics()` → CSV/JSON/PDF export
- **Chart Integration**: `templates/metrics.html` → Chart.js visualizations (trend, severity, tags, owners)
- **HTMX Filtering**: `templates/metrics.html` → real-time filter updates
- **Export Scripts**: `scripts/export_findings_report.py` → CLI export tool

### Schema Validation (Phase 4A)
- **Validation Helper**: `utils/schema_validation.py:validate_json()` → JSON schema validation
- **Findings Validation**: `findings.py:append_findings()` → schema check before write
- **Runs Validation**: `store.py:append_run()` → schema check before write
- **Dossier Validation**: `store.py:update_endpoint_dossier_by_key()` → schema check before write
- **Cache Validation**: `routes/vulns.py:vulns_page()` → schema check before cache write

### Site Map Drawers Enhancement (Phase 4A)
- **Enhanced Preview Drawer**: `templates/drawer_endpoint_preview.html` → absolute cURL first, live coverage, 5-button action bar
- **Enhanced Runs Drawer**: `templates/drawer_endpoint_runs.html` → relative timestamps, clear headers, improved empty state
- **Group Headers**: `templates/sitemap_fragment.html` → labeled chips with danger styling for vulnerabilities
- **Coverage Enhancement**: `routes/sitemap.py:sitemap_endpoint_preview()` → live coverage calculation from dossier data

### SSE Live Runner Enhancement (Phase 4A)
- **Enhanced SSE Stream**: `routes/nuclei.py:nuclei_stream()` → proper headers, single-executor guard, periodic heartbeats
- **Queue De-dupe Logging**: `routes/nuclei.py:nuclei_stream()` → canonical key normalization and debug logging
- **Robust Cleanup**: `routes/nuclei.py:nuclei_stream()` → active runs cleanup on completion/error

## 🗄️ Data Storage

### Project Data (`ui_projects/<pid>/`)
- **Runtime State**: `<pid>.json` → `store.py:load_project_state()`
- **Endpoint Dossiers**: `endpoints/*.json` → `store.py:update_endpoint_dossier_by_key()`
- **Finding Store**: `findings.json` → `findings.py:_read_findings()`
- **Run History**: `runs.json` → `store.py:append_run()`
- **Queue State**: `queue.json` → legacy format
- **Vulns Summary**: `indexes/vulns_summary.json` → `routes/vulns.py:_compute_vulns_summary()`
- **Metrics Summary**: `indexes/metrics_summary.json` → `analytics_core/analytics.py:rebuild_metrics_cache()`

### Global State
- **Project Index**: `projects.json` → `store.py:list_projects()`
- **App Config**: `app_config.json` → `config.py:load_config()`

## 🔐 Security & Authentication

### Authentication (Planned Extensions)
- **Session Management**: `app/auth.py` → Flask.session integration
- **Role Guards**: `app/middleware/auth_middleware.py` → decorators
- **API Security**: `api_endpoints.py:require_api_key()` → header validation

### Security Tools
- **Nuclei Wrapper**: `nuclei_wrapper.py:NucleiWrapper` → subprocess management
- **Integration**: `nuclei_integration.py:NucleiIntegration` → finding conversion
- **Pattern Engine**: `detectors/pattern_engine.py` → built-in detectors

## 📊 Monitoring & Observability

### Logging System
- **Structured Logging**: `app/logging_conf.py:JsonRequestFormatter` → JSON output
- **Specialized Loggers**: `app/specialized_loggers.py` → domain categories
- **Request Context**: `app/middleware/request_context.py` → timing/IDs

### Metrics & Analytics (P6)
- **Analytics Core**: `analytics_core/analytics.py:get_metrics()` → comprehensive findings metrics
- **Metrics Dashboard**: `templates/metrics.html` → interactive charts and KPIs
- **Export System**: `scripts/export_findings_report.py` → CSV/JSON/PDF reports
- **Cache Integration**: `store.py:_bust_vulns_cache()` → automatic metrics rebuild
- **Performance**: `metrics.py:record_http_request()` → Prometheus format
- **Cache Stats**: `cache.py:get_cache_stats()` → hit/miss tracking
- **API Endpoints**: `api_endpoints.py:metrics_endpoint()` → `/api/v1/metrics`

### Caching Layer
- **In-Memory Cache**: `cache.py:@cached()` → TTL decorator
- **Sitemap Cache**: `sitemap_builder.py:@cached(ttl_seconds=300)` → 5min refresh
- **Finding Count**: `findings.py:@cached(ttl_seconds=60)` → rapid updates

## 🧩 Extensibility Hooks

### New Routes (Blueprint Pattern)
- **Module Setup**: `routes/custom_feature.py:register_custom_feature_routes()` → blueprint registration
- **Registration**: `routes/__init__.py` → import and register
- **App Factory**: `app.py:create_app()` → blueprints aggregation

### New Storage (Facade Pattern)
- **Storage Wrapper**: `storage/custom_storage.py` → delegate to `store.py`
- **Validation Layer**: `schemas/custom_schema.py` → Pydantic models
- **Migration Helpers**: `storage/migrations.py` → forward/backward compatibility

### Tool Plugins
- **Base Interface**: `plugins/base_tool.py:BaseSecurityTool` → common interface
- **Registry**: `plugins/registry.py:discover_tools()` → auto-detection
- **Integration**: `core/detectors.py:register_external_tool()` → tool mounting

## 🎨 Frontend Components

### Core JavaScript (`static/`)
- **Main Utilities**: `static/main.js` → drawer management, HTMX integration
- **Filter System**: `static/filters.js` → method filtering
- **Notifications**: `static/notifications.js` → toast messages
- **Styling**: `static/main.css` → core styles, `static/tokens.css` → design tokens

### Template Structure (`templates/`)
- **Base Layout**: `templates/_layout.html` → page shell + navigation
- **Macros**: `templates/_macros.html` → reusable components
- **Page Templates**: `templates/*.html` → feature-specific layouts
- **Drawer Templates**: `templates/drawer_*.html` → HTMX content fragments
- **Metrics Dashboard**: `templates/metrics.html` → analytics dashboard with Chart.js

## 🚀 Development Tools

### CLI Tools (`tools/`)
- **Sanity Checks**: `tools/proof_sanity.py` → port conflicts, setup validation
- **Pattern Validation**: `tools/validate_patterns.py` → detector syntax
- **Development**: `tools/phase1_verify.py` → testing helpers
- **Export Reports**: `scripts/export_findings_report.py` → findings report generation
- **Metrics Verification**: `scripts/verify_metrics.sh` → metrics validation

### Configuration
- **Environment**: `ENABLE_METRICS`, `LOG_LEVEL`, `API_KEYS` → runtime behavior  
- **App Config**: `config.py:get()` → persistent settings
- **Feature Flags**: `web_routes.py:feature_flag()` → conditional feature rendering

## 📚 Documentation Files

### Architecture & Design
- **Architecture Map**: `ARCHITECTURE_MAP.md` → comprehensive system overview
- **File Index**: `FILE_INDEX.md` → this file, feature → files mapping
- **Sequence Diagrams**: `SEQUENCE_DIAGRAMS.md` → interaction flows
- **UX States**: `UX_STATES.md` → user interface state management
- **Async Tasks**: `ASYNC_TASKS_DESIGN.md` → background processing design
- **Storage Migration**: `STORAGE_MIGRATION_PLAN.md` → data migration strategy
- **Auth Roles**: `AUTH_ROLES_MATRIX.md` → authentication and authorization
- **Error Contract**: `ERROR_CONTRACT.md` → error handling standards
- **Observability**: `OBSERVABILITY.md` → logging and monitoring
- **Runbook**: `RUNBOOK.md` → operational procedures
- **SSE Contract**: `SSE_CONTRACT.md` → Server-Sent Events specification
- **Metrics Runbook**: `RUNBOOK_METRICS.md` → metrics operations and troubleshooting

### P4 Regression Guardrails Documentation
- **P4 Overview**: `P4_REGRESSION_GUARDRAILS.md` → comprehensive P4 documentation
- **Test Suite**: `tests/test_findings_normalize.py` → normalization unit tests
- **Contract Tests**: `tests/test_append_and_cache.py` → schema compliance tests
- **SSE Tests**: `tests/test_sse_stream.py` → streaming contract tests
- **Pre-commit Guards**: `scripts/pre-commit-guards.sh` → regression prevention
- **CI Workflow**: `.github/workflows/findings-contract.yml` → automated enforcement
- **Migration Runbook**: `RUNBOOK_MIGRATION.md` → P3 migration procedures
- **Updated README**: `README.md` → findings contract and testing guidelines

### P5 Triage & Workflow System
- **Triage Migration**: `scripts/backfill_triage_defaults.py` → backfill triage data
- **Triage Routes**: `routes/triage.py` → status/owner/tags/notes/suppress APIs
- **Vulns Summary**: `routes/vulns.py:_compute_vulns_summary()` → triage-aware aggregation
- **Triage UI**: `templates/vulns.html` → triage panel, filters, status indicators
- **Triage Tests**: `tests/test_triage_*.py` → comprehensive triage testing
- **Schema Extension**: `findings.schema.json` → triage object definition

### P6 Metrics & Analytics (Phase 6)
- **Analytics Core**: `analytics_core/analytics.py` → metrics computation and caching
- **Metrics Routes**: `routes/metrics.py` → dashboard and export endpoints
- **Metrics UI**: `templates/metrics.html` → responsive dashboard with charts
- **Export Scripts**: `scripts/export_findings_report.py` → CSV/JSON/PDF export
- **Cache Integration**: `store.py:_bust_vulns_cache()` → metrics cache rebuild
- **Metrics Tests**: `tests/test_metrics.py` → analytics unit tests
- **Export Tests**: `tests/test_export.py` → export functionality tests
- **UI Tests**: `tests/test_ui_metrics.py` → dashboard UI tests
- **Verification**: `scripts/verify_metrics.sh` → metrics validation script
- **Metrics Runbook**: `RUNBOOK_METRICS.md` → metrics operations guide

---

**Legend**: 
- `FunctionName()` = main function implementing feature
- `filename:line_number` = specific code location  
- `database/file` = persistence layer
- `TemplateName.html` = UI template
- `NEW` = implementation needed for extension
