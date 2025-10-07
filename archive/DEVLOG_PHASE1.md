Phase 1 Scaffold (No Behavior Changes)
=====================================

Scope
-----
Add scaffolding for app package, settings, logging, middleware, api package, schemas, storage facade, tools, tasks, and static placeholders. Keep all routes/URLs and runtime behavior unchanged.

New files
---------
- app/__init__.py (factory loading existing top-level app.py)
- app/settings.py (config loader)
- app/logging_conf.py (JSON logging)
- app/middleware/request_context.py (request_id + timing)
- wsgi.py (WSGI entrypoint)
- api/__init__.py (re-export existing api_bp) + stubs: projects.py, findings.py, analysis.py, patterns.py, reports.py, stats.py
- schemas/run.py, schemas/finding.py (validation only)
- storage/{__init__,projects,state,findings,runs,profiles}.py (thin wrappers)
- tools/{__init__,registry,nuclei}.py (interfaces; pass-through)
- tasks/{__init__,nuclei}.py (sync wrappers)
- static/notifications.js, static/filters.js (placeholders)

Minimal wiring
--------------
- web_routes.py: request logging now uses logger "request" with same payload fields.
- No routes, URLs, or templates changed beyond import/logging.

Proofs
------
- Route map before/after: identical (see DEBUG_RUN.md, Added: [], Removed: []).
- Pages (HEAD/GET 200) + first160 chars captured in DEBUG_RUN.md.
- Drawer HTMX probes executed; responses non-empty for clear/remove; add returned 500 when invoked without form fields (expected when posting raw), noted as probe-only.
- Grep confirms exactly one `#global-indicator` and one `#panel-body` in templates; page counts in DEBUG_RUN.md are 1 each (except sitemap reported 2 for indicator due to indicator appearing twice in composed markup; template audit shows single definition in `_layout.html`).
- Sample JSON logs: see tail of server log (logger active; request lines appear during runtime).


