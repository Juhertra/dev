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

### Tools Management (Phase 4A)
- **Tools Manager**: `routes/tools.py:tools_page()` → `templates/tools/index.html`
- **Nuclei Integration**: `routes/tools.py:nuclei_reindex()` → template count and timing
- **Self-test**: `routes/tools.py:nuclei_selftest()` → fixture template validation
- **Presets**: `tools/presets.json` → template category arrays
- **Fixtures**: `tools/fixtures/nuclei/` → test templates for self-test

### Vulnerabilities Hub (Phase 4A)
- **Vulns Page**: `routes/vulns.py:vulns_page()` → `templates/vulns.html`
- **Aggregation**: `routes/vulns.py:_compute_vulns_summary()` → endpoint + detector grouping
- **Cache System**: `ui_projects/<pid>/indexes/vulns_summary.json` → validated aggregation cache
- **HTMX Actions**: `routes/vulns.py:vulns_preview()` → preview drawer integration
- **Cache Busting**: `store.py:_bust_vulns_cache()` → automatic invalidation

### Schema Validation (Phase 4A)
- **Validation Helper**: `utils/schema_validation.py:validate_json()` → JSON schema validation
- **Findings Validation**: `findings.py:append_findings()` → schema check before write
- **Runs Validation**: `store.py:append_run()` → schema check before write
- **Dossier Validation**: `store.py:update_endpoint_dossier_by_key()` → schema check before write
- **Cache Validation**: `routes/vulns.py:vulns_page()` → schema check before cache write

## 🗄️ Data Storage

### Project Data (`ui_projects/<pid>/`)
- **Runtime State**: `<pid>.json` → `store.py:load_project_state()`
- **Endpoint Dossiers**: `endpoints/*.json` → `store.py:update_endpoint_dossier_by_key()`
- **Finding Store**: `findings.json` → `findings.py:_read_findings()`
- **Run History**: `runs.json` → `store.py:append_run()`
- **Queue State**: `queue.json` → legacy format

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

### Metrics (Optional)
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

## 🚀 Development Tools

### CLI Tools (`tools/`)
- **Sanity Checks**: `tools/proof_sanity.py` → port conflicts, setup validation
- **Pattern Validation**: `tools/validate_patterns.py` → detector syntax
- **Development**: `tools/phase1_verify.py` → testing helpers

### Configuration
- **Environment**: `ENABLE_METRICS`, `LOG_LEVEL`, `API_KEYS` → runtime behavior  
- **App Config**: `config.py:get()` → persistent settings
- **Feature Flags**: `web_routes.py:feature_flag()` → conditional feature rendering

---

**Legend**: 
- `FunctionName()` = main function implementing feature
- `filename:line_number` = specific code location  
- `database/file` = persistence layer
- `TemplateName.html` = UI template
- `NEW` = implementation needed for extension
