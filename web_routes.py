from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import requests
import urllib3

logger = logging.getLogger(__name__)
import os
import time
import uuid

from flask import (
    Blueprint,
    current_app,
    g,
    jsonify,
    redirect,
    render_template,
    render_template_string,
    request,
    url_for,
)

from core import _files_preview_map, _json_safe, compose_display_url, parse_json_field
from findings import (
    analyze_and_record,
    count_findings_cached,
    get_finding_by_index,
    get_finding_explanation,
    get_findings,
)
from specs import (
    RefResolver,
    build_preview,
    iter_operations,
    load_spec_from_text_or_convert,
    load_spec_text,
    op_seed,
    pick_server,
    spec_meta,
)
from store import (
    append_send_log,
    create_project,
    delete_project,
    ensure_runtime,
    get_current_project_id,
    get_project_name,
    get_runtime,
    list_projects,
    load_run,
    make_run_id,
    persist_from_runtime,
    rename_project,
    save_run,
    set_current_project_id,
)
from utils.endpoints import endpoint_key

# from detectors.enhanced_pattern_engine import EnhancedPatternEngine  # Unused import
# from detectors.pattern_manager import PatternManager  # Unused import

try:
    # Prefer modular blueprint if available
    from routes import web_bp as bp  # type: ignore
except Exception:
    bp = Blueprint("web", __name__)

# Make feature_flag available to all templates
def feature_flag(name: str) -> bool:
    key = f"FEATURE_{name.upper()}"
    # env overrides flask config; default False
    if key in os.environ:
        v = os.environ.get(key, "false").lower()
        return v in ("1", "true", "yes", "on")
    return bool(current_app.config.get(key, False))

bp.add_app_template_global(feature_flag, name="feature_flag")

# Add regex_search filter for CVE validation
import re


def regex_search(text: str, pattern: str) -> bool:
    """Check if text matches regex pattern."""
    if not text or not isinstance(text, str):
        return False
    try:
        return bool(re.search(pattern, text))
    except Exception:
        return False

bp.add_app_template_filter(regex_search, name="regex_search")

# Background template reindex status (simple in-process store)
_TPL_REINDEX_STATUS: Dict[str, Dict[str, Any]] = {}

# ---------- Drawer helpers: safe getters (non-intrusive aliases) ----------
def _rt(pid: str) -> Dict[str, Any]:
    """Return a dict-shaped runtime view regardless of underlying store structure."""
    try:
        # Our store returns (session, SPECS, QUEUE)
        session, SPECS, QUEUE = get_runtime(pid)
        try:
            rows = get_findings(pid) or []
        except Exception:
            rows = []
        return {"SESSION": session, "SPECS": SPECS, "QUEUE": QUEUE, "findings": rows}
    except Exception:
        return {}

def _find_finding_by_idx(rt: Dict[str, Any], idx: int) -> Optional[Dict[str, Any]]:
    try:
        i = int(idx)
    except Exception:
        return None
    rows = rt.get("findings") or []
    if isinstance(rows, list) and 0 <= i < len(rows):
        item = dict(rows[i]) if isinstance(rows[i], dict) else rows[i]
        if isinstance(item, dict):
            item["idx"] = i
        return item
    if isinstance(rows, dict) and str(i) in rows:
        item = dict(rows[str(i)])
        item["idx"] = i
        return item
    return None
bp.add_app_template_global(count_findings_cached, name="count_findings")

@bp.before_app_request
def _start_req_timer():
    g._req_start = time.time()
    g._req_id = str(uuid.uuid4())

@bp.after_app_request
def _log_req(resp):
    try:
        dur_ms = int((time.time() - getattr(g, "_req_start", time.time())) * 1000)
        payload = {
            "request_id": getattr(g, "_req_id", "-"),
            "method": request.method,
            "path": request.path,
            "status": resp.status_code,
            "duration_ms": dur_ms,
            "hx": bool(request.headers.get("HX-Request")),
        }
        # Use structured logger; keep payload fields identical for compatibility
        logging.getLogger("request").info("request", extra=payload)
    except Exception as e:
        logging.getLogger("request").warning("log_error", extra={"log_error": str(e)})
    return resp


# ---------- small local helpers used by templates ----------

def _with_session_bearer(headers: Optional[Dict[str, str]], session: Dict[str, Any]) -> Dict[str, str]:
    """Return a copy of headers, adding Authorization: Bearer <token> from session if not already present."""
    h = dict(headers or {})
    b = (session.get("bearer") or "").strip()
    if b and "Authorization" not in h:
        h["Authorization"] = f"Bearer {b}"
    return h

def _specs_model(SPECS: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    from core import safe_id
    return {
        "specs": {
            sid: {
                "title": s["title"],
                "version": s["version"],
                "url": s["url"],
                "base_url": s["base_url"],
                "ops": s["ops"],
                "safe_id": s.get("safe_id", safe_id(sid)),
                "error": s.get("_error"),
            } for sid, s in SPECS.items()
        }
    }

# Import the new sitemap builder
from nuclei_integration import nuclei_integration

# ---------- Shared CSS + JS blocks ----------

BASE_STYLE = """
  :root{
    --bg:#0b1020; --bg2:#0f172a; --fg:#e5e7eb; --muted:#9ca3af;
    --accent:#22d3ee; --accent-2:#a78bfa; --ok:#10b981; --err:#ef4444;
    --chip:#0ea5e9; --chip-get:#38bdf8; --chip-post:#34d399; --chip-put:#fbbf24; --chip-del:#f87171;
    --card:rgba(255,255,255,.08); --card-b:rgba(255,255,255,.2);
    --ring:0 0 0 2px rgba(34,211,238,.35), 0 10px 20px rgba(0,0,0,.25) inset;
    --radius:16px;
  }
  :root.light{
    --bg:#f8fafc; --bg2:#ffffff; --fg:#0b1020; --muted:#475569;
    --accent:#0ea5e9; --accent-2:#6d28d9;
    --card:rgba(15,23,42,.04); --card-b:rgba(15,23,42,.12);
    --ring:0 0 0 2px rgba(14,165,233,.25), 0 6px 16px rgba(2,6,23,.08);
  }
  *{box-sizing:border-box}
  body{
    margin:0; color:var(--fg);
    font:14px/1.45 ui-sans-serif,system-ui,-apple-system,Segoe UI,Inter,Roboto,sans-serif;
    background: radial-gradient(1200px 600px at 10% -10%, #172554 10%, transparent 60%),
                linear-gradient(180deg,var(--bg),var(--bg2));
    min-height:100dvh; padding-bottom:64px;
  }
  .wrap{max-width:1200px;margin:32px auto;padding:0 16px}

  /* Topbar */
  .topbar{position:sticky;top:0;z-index:30;backdrop-filter:blur(10px);
          background:linear-gradient(180deg,rgba(255,255,255,.06),rgba(255,255,255,0));
          border-bottom:1px solid var(--card-b)}
  .topbar-inner{max-width:1200px;margin:auto;display:flex;align-items:center;gap:12px;padding:14px 16px}
  .title,h1,h2{margin:0;font-weight:800;letter-spacing:.2px}
  .title{font-size:20px;background:linear-gradient(90deg,var(--accent),var(--accent-2));-webkit-background-clip:text;background-clip:text;color:transparent}

  /* Buttons & links */
  .btn,button,.link{cursor:pointer;border:1px solid var(--card-b);background:var(--card);color:var(--fg);
    padding:9px 12px;border-radius:12px;font-weight:600;transition:transform .15s ease, background .15s ease}
  .btn:hover,button:hover,.link:hover{transform:translateY(-1px);background:rgba(255,255,255,.14)}
  .btn.primary{background:linear-gradient(90deg,rgba(34,211,238,.20),rgba(167,139,250,.20));border-color:rgba(255,255,255,.30)}
  .btn.ghost{background:transparent}
  .btn-danger{background:rgba(239,68,68,.18);border-color:rgba(239,68,68,.35)}
  .link{text-decoration:none;display:inline-flex;gap:8px;align-items:center}

  /* Cards & inputs */
  .card{background:var(--card);border:1px solid var(--card-b);border-radius:var(--radius);padding:16px;box-shadow:var(--ring)}
  input[type=text],textarea,select{width:100%;padding:10px 12px;border-radius:12px;border:1px solid var(--card-b);background:var(--bg2);color:var(--fg)}
  .muted{color:var(--muted)}

  /* Layout helpers */
  .grid{display:grid;grid-template-columns:minmax(360px,1fr) 380px;gap:16px;align-items:start}
  @media (max-width:980px){ .grid{grid-template-columns:1fr} }
  .row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
  .toolbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:8px 0 12px}

  /* Tables */
  table{width:100%;border-collapse:collapse}
  th,td{padding:10px;border-bottom:1px solid var(--card-b);text-align:left}

  /* Details/spec blocks */
  details.spec{border:1px solid var(--card-b);border-radius:14px;background:linear-gradient(180deg, var(--card), transparent 120%);margin-top:16px}
  details.spec summary{list-style:none;cursor:pointer;display:flex;gap:10px;align-items:flex-start;padding:12px 16px}
  details.spec summary::-webkit-details-marker{display:none}
  .chev{transition:transform .15s ease}
  details[open] .chev{transform:rotate(90deg)}
  .spec-body{padding:12px 16px}

  /* Misc */
  .chip{font-weight:800;letter-spacing:.3px;font-size:12px;padding:4px 8px;border-radius:999px;color:#0b1020}
  .GET{background:var(--chip-get)} .POST{background:var(--chip-post)} .PUT{background:var(--chip-put)} .DELETE{background:var(--chip-del)}
  .drawer{margin-top:8px;padding:12px;border:1px solid var(--card-b);border-radius:12px;background:linear-gradient(180deg,rgba(255,255,255,.06),rgba(255,255,255,.02))}
  pre{background:#0b1020;color:#e5e7eb;padding:10px;border-radius:10px;overflow:auto;border:1px solid rgba(255,255,255,.18)}
  .ok{color:var(--ok)} .err{color:var(--err)}
  .hint{color:var(--muted)}
  .id{color:var(--muted);font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,"Liberation Mono","Courier New",monospace}
  .actions{display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap}
  .pill{padding:6px 10px;border-radius:999px;background:var(--card);border:1px solid var(--card-b)}

  /* — NEW: method filter chips — */
  .filters{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:8px 0 0}
  .tag{border:1px solid var(--card-b);background:var(--card);padding:6px 10px;border-radius:999px;cursor:pointer;font-weight:700}
  .tag.active{outline:2px solid rgba(34,211,238,.45)}
  .sep{opacity:.5}

  /* HTMX indicator */
  .htmx-indicator{ 
    position:fixed; left:18px; bottom:18px; z-index:50;
    display:none; align-items:center; gap:10px;
    padding:10px 12px; border-radius:12px;
    background:var(--card); border:1px solid var(--card-b);
    box-shadow:var(--ring); color:var(--fg); font-weight:700;
  }
  .htmx-request .htmx-indicator{ display:flex }
  .spinner{ width:14px; height:14px; border-radius:50%;
    border:2px solid currentColor; border-right-color:transparent;
    animation:spin .8s linear infinite; }
  @keyframes spin{to{transform:rotate(360deg)}}
"""

BASE_SCRIPT = """
  // Theme helpers live in static/main.js; avoid redefining to prevent duplicate variables
  // setTheme/getTheme should already be globally available; if not, safely no-op
  const setTheme = window.setTheme || function(){};
  const getTheme = window.getTheme || function(){ return 'dark'; };

// --- unified flash helpers
function flash(btn, text, cls) {
  if (!btn) return;
  const orig = btn.getAttribute('data-label') || btn.textContent;
  btn.setAttribute('data-label', orig);
  btn.disabled = true;
  if (cls) btn.classList.add(cls);
  btn.textContent = text;
  setTimeout(() => {
    btn.textContent = btn.getAttribute('data-label') || orig;
    btn.disabled = false;
    if (cls) btn.classList.remove(cls);
  }, 1100);
}
function flashSuccess(btn, text) { flash(btn, text || '✓ Done', 'ok'); }
function flashError(btn, text)   { flash(btn, text || '✗ Error', 'err'); }


function confirmClearSends() {
  // Use themed confirmation modal instead of browser confirm
  openClearSendsConfirmation();
  return false; // Prevent form submission
}

function openClearSendsConfirmation() {
  const modal = document.getElementById('clear-sends-modal');
  if (!modal) {
    createClearSendsModal();
    return;
  }
  modal.classList.add('open');
}

function createClearSendsModal() {
  const modal = document.createElement('div');
  modal.id = 'clear-sends-modal';
  modal.className = 'modal';
  modal.setAttribute('aria-hidden', 'true');
  modal.innerHTML = `
    <div class="modal-content" style="width: min(400px, 90vw)">
      <div class="modal-head">
        <h3 style="margin:0">Clear Sends Data</h3>
      </div>
      <div class="clear-sends-content">
        <div class="card">
          <p style="margin:0 0 16px;color:var(--fg)">
            Are you sure you want to clear all sends data?
          </p>
          <p class="muted" style="margin:0 0 16px;font-size:12px">
            This action cannot be undone.
          </p>
          <div class="row" style="gap:8px;justify-content:flex-end">
            <button class="btn ghost" onclick="closeClearSendsConfirmation()">Cancel</button>
            <button class="btn" onclick="confirmClearSendsAction()" style="background:var(--err);color:white">Clear All</button>
          </div>
        </div>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
  modal.classList.add('open');
}

function closeClearSendsConfirmation() {
  const modal = document.getElementById('clear-sends-modal');
  if (!modal) return;
  modal.classList.remove('open');
}

function confirmClearSendsAction() {
  // Close the modal first
  closeClearSendsConfirmation();
  
  // Show loading notification
  showNotification('Clearing all sends data...', 'info');
  
  // Submit via fetch to handle the response
  fetch(document.querySelector('form[action*="sends_clear"]').action, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    }
  })
  .then(response => {
    console.log('Clear sends response:', response.status, response.statusText);
    if (response.ok) {
      showNotification('All sends data cleared successfully', 'success');
      // Reload the page to show empty state
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    } else {
      showNotification('Error clearing sends data: ' + response.status, 'error');
    }
  })
  .catch(error => {
    console.error('Error clearing sends data:', error);
    showNotification('Error clearing sends data: ' + error.message, 'error');
  });
}

// copy helper using same flash pattern
  function copyWithFeedback(text, btn){
  navigator.clipboard.writeText(text).then(
    () => showNotification('Copied to clipboard', 'success'),
    () => showNotification('Copy failed', 'error')
  );
}

// ---- Existing helpers
  function expandAll(){ document.querySelectorAll('details.spec').forEach(d=>d.open=true) }
  function collapseAll(){ document.querySelectorAll('details.spec').forEach(d=>d.open=false) }
  function toggleDetails(btn, postUrl, specId, safeId, index){
    const id = `det-${safeId}-${index}`, el = document.getElementById(id);
    if(!el) return;
    if(el.innerHTML.trim()){ el.innerHTML=''; btn.textContent='Preview'; return; }
    btn.textContent='Close';
    htmx.ajax('POST', postUrl, {target:'#'+id, swap:'innerHTML', values:{pid:'{{pid}}', spec_id:specId, index:index}});
  }
  function checkAllInTable(safeId, check){ document.querySelectorAll(`#tbl-${safeId} input[name=sel]`).forEach(cb=>cb.checked=!!check) }
  function qDetails(btn, targetId, postUrl, qid){
    const el=document.getElementById(targetId);
    if(!el) return; if(el.innerHTML.trim()){ el.innerHTML=''; btn.textContent='Preview'; return; }
    btn.textContent='Close'; htmx.ajax('POST', postUrl, {target:'#'+targetId, swap:'innerHTML', values:{qid}});
  }
  // Method filters live in static/main.js to avoid duplicate globals

// Theme + initial sync
document.addEventListener('DOMContentLoaded', ()=>{
  setTheme(getTheme());
  syncFilterChips();
  setTimeout(applyFilters,0);
});

// Re-apply whenever #specs is HTMX-swapped
document.addEventListener('htmx:afterSwap', (e)=>{
  if (e.target && (e.target.id === 'specs' || (e.target.closest && e.target.closest('#specs')))) {
    syncFilterChips();
    setTimeout(applyFilters,0);
  }
});

// Global HTMX error → toast-style flash on the triggering element
document.body.addEventListener('htmx:responseError', function(ev){
  const elt = ev.detail.elt;
  if (elt && elt.tagName === 'BUTTON') showNotification('Request failed', 'error');
});
"""

# ---------- Projects Dashboard ----------

def render_projects_dashboard():
    projs = list_projects()
    current = get_current_project_id()
    T = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Projects — OpenAPI UI</title>
<link rel="stylesheet" href="{{ url_for('static', filename='tokens.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='main.css') }}">
<script src="{{ url_for('static', filename='main.js') }}"></script>
</head>
<body>

  <div class="topbar">
    <div class="topbar-inner">
      <div class="title">Projects</div>
      <span style="flex:1"></span>
      <button id="theme" class="btn" onclick="setTheme(getTheme()==='light'?'dark':'light')">🌙</button>
    </div>
  </div>

  <div class="wrap">

    <div class="card">
      <div class="hint" style="margin-bottom:8px">Create, rename, switch, or delete projects.</div>
      <form method="post" action="{{ url_for('web.project_create') }}">
        <div class="row">
          <div style="flex:1 1 360px"><input type="text" name="name" placeholder="New project name"></div>
          <button class="btn primary" type="submit">Create project</button>
        </div>
      </form>
    </div>

    <div class="card" style="margin-top:16px">
      {% if not projs %}
        <div class="hint">No projects yet.</div>
      {% else %}
        <table>
          <thead>
            <tr>
              <th style="width:42%">Name</th>
              <th>ID</th>
              <th style="text-align:center">Current</th>
              <th style="text-align:center">Actions</th>
            </tr>
          </thead>
          <tbody>
          {% for p in projs %}
            <tr>
              <!-- Name + inline rename -->
              <td>
                <form method="post" action="{{ url_for('web.project_rename') }}"
                      style="display:flex;gap:8px;align-items:center">
                  <input type="hidden" name="id" value="{{ p.id }}">
                  <input type="text" name="name" value="{{ p.name }}" style="max-width:260px">
                  <button class="btn ghost" type="submit">Rename</button>
                </form>
              </td>

              <!-- ID -->
              <td class="id">{{ p.id }}</td>

              <!-- Current -->
              <td style="text-align:center;white-space:nowrap">
                {% if p.id == current %}
                  <span class="pill">Yes</span>
                {% else %}
                  <form method="post" action="{{ url_for('web.project_set_current') }}" style="display:inline">
                    <input type="hidden" name="id" value="{{ p.id }}">
                    <button class="btn ghost" type="submit">Set current</button>
                  </form>
                {% endif %}
              </td>

              <!-- Actions -->
              <td style="text-align:center;white-space:nowrap">
                <a class="btn ghost" href="{{ url_for('web.project_open', pid=p.id) }}">Open</a>
                <form method="post" action="{{ url_for('web.project_delete') }}" style="display:inline">
                  <input type="hidden" name="id" value="{{ p.id }}">
                  <button class="btn primary" type="submit">Delete</button>
                </form>
              </td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      {% endif %}
    </div>
  </div>
  
</body>
</html>
"""
    return render_template_string(T, projs=projs, current=current)

@bp.route("/", methods=["GET"])
def projects_home():
    return render_projects_dashboard()

@bp.route("/project/create", methods=["POST"])
def project_create():
    name = (request.form.get("name") or "").strip() or "New Project"
    pid = create_project(name)
    return redirect(url_for("web.project_open", pid=pid))

@bp.route("/project/rename", methods=["POST"])
def project_rename():
    pid = request.form.get("id") or ""
    name = (request.form.get("name") or "").strip()
    if pid and name:
        rename_project(pid, name)
    return redirect(url_for("web.projects_home"))

@bp.route("/project/delete", methods=["POST"])
def project_delete():
    pid = request.form.get("id") or ""
    if pid:
        delete_project(pid)
    return redirect(url_for("web.projects_home"))

@bp.route("/project/set_current", methods=["POST"])
def project_set_current():
    pid = request.form.get("id") or ""
    set_current_project_id(pid if pid else None)
    return redirect(url_for("web.projects_home"))

@bp.route("/p/<pid>/api/retire", methods=["POST"])
def retire_api_endpoints(pid: str):
    """Mark endpoints from a specific API as retired."""
    try:
        api_url = request.form.get("api_url", "")
        if not api_url:
            return "Missing API URL", 400
        
        # Get all endpoints that would be from this API
        from store import get_runtime
        session, SPECS, QUEUE = get_runtime(pid)
        
        # Find endpoints that match this API's base URL
        retired_endpoints = []
        for spec_id, spec in SPECS.items():
            if spec.get("url") == api_url:
                base_url = spec.get("base_url", "")
                for op in spec.get("ops", []):
                    method = op.get("method", "")
                    path = op.get("path", "")
                    from utils.endpoints import endpoint_key
                    canonical_key = endpoint_key(method, base_url, path)
                    retired_endpoints.append(canonical_key)
        
        if retired_endpoints:
            from utils.dossier_management import mark_endpoints_retired
            reason = f"API specification removed: {api_url}"
            results = mark_endpoints_retired(pid, retired_endpoints, reason)
            
            success_count = sum(1 for result in results.values() if result)
            if success_count > 0:
                flash(f"Marked {success_count} endpoints as retired", "success")
            else:
                flash("No endpoints found to retire", "info")
        else:
            flash("No endpoints found for this API", "info")
            
    except Exception as e:
        logger.error(f"Failed to retire API endpoints: {e}")
        flash(f"Error retiring endpoints: {str(e)}", "error")
    
    return redirect(url_for("web.project_open", pid=pid))

# ---------- Main Browser ----------

@bp.route("/p/<pid>", methods=["GET"])
def project_open(pid: str):
    ensure_runtime(pid)
    session, SPECS, QUEUE = get_runtime(pid)
    return render_browser(pid, session, SPECS, QUEUE, results=None)

def render_browser(pid: str, SESSION: Dict[str, Any], SPECS: Dict[str, Dict[str, Any]], QUEUE: List[Dict[str, Any]], results: Optional[List[Dict[str, Any]]]):
    def specs_fragment():
        model = _specs_model(SPECS)
        return render_template("specs_fragment.html", pid=pid, **model)

    spec_html = specs_fragment()
    return render_template("browser.html", pid=pid, project_name=get_project_name(pid), proxy=SESSION.get("proxy"), verify=SESSION.get("verify", True), bearer=SESSION.get("bearer"), spec_html=spec_html, results=results)

# ---------- Spec actions ----------

@bp.post("/p/<pid>/add")
def add_specs(pid: str):
    session, SPECS, QUEUE = get_runtime(pid)
    urls_raw = (request.form.get("spec_urls") or "").strip()
    raw_text = (request.form.get("raw_text") or "").strip()
    proxy = (request.form.get("proxy") or "").strip() or None
    verify = request.form.get("verify") == "1"
    bearer = (request.form.get("bearer") or "").strip() or None
    headers_json = (request.form.get("headers_json") or "").strip()
    input_type = (request.form.get("input_type") or "auto").strip().lower()
    session["proxy"] = proxy
    session["verify"] = verify
    session["bearer"] = bearer
    if urls_raw or raw_text:
        proxies = {"http": proxy, "https": proxy} if proxy else None
        headers = {"User-Agent": "openapi-ui/1.0"}
        if bearer: headers["Authorization"] = f"Bearer {bearer}"
        # Merge custom headers if provided as JSON
        if headers_json:
            try:
                extra = json.loads(headers_json)
                if isinstance(extra, dict):
                    for k, v in extra.items():
                        try:
                            if isinstance(k, str):
                                headers[k] = str(v)
                        except Exception:
                            continue
            except Exception:
                pass
        if verify is False:
            try: urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            except Exception: pass
        from flask import make_response
        triggered_msgs: List[Dict[str, str]] = []
        # Handle raw pasted text first, if provided
        if raw_text:
            try:
                spec = load_spec_from_text_or_convert(raw_text, input_type=input_type)
                base = pick_server(spec)
                resolver = RefResolver(spec)
                ops = iter_operations(spec, resolver)
                title, version = spec_meta(spec)
                spec_id = f"pasted://{title}|{version}"
                from core import safe_id
                SPECS[spec_id] = {"url": "(pasted)", "title": title, "version": version, "base_url": base, "ops": ops, "spec": spec, "safe_id": safe_id(spec_id)}
            except Exception as e:
                triggered_msgs.append({"type": "error", "message": f"Failed to import pasted spec — {str(e)}"})

        for line in urls_raw.splitlines():
            u = line.strip()
            if not u: continue
            try:
                text = load_spec_text(u, proxies=proxies, verify=verify, headers=headers)
                spec = load_spec_from_text_or_convert(text, input_type=input_type)
                base = pick_server(spec)
                resolver = RefResolver(spec)
                ops = iter_operations(spec, resolver)
                title, version = spec_meta(spec)
                spec_id = f"{u}|{title}|{version}"
                from core import safe_id
                SPECS[spec_id] = {"url": u, "title": title, "version": version, "base_url": base, "ops": ops, "spec": spec, "safe_id": safe_id(spec_id)}
            except Exception as e:
                triggered_msgs.append({"type": "error", "message": f"Failed to load spec: {u} — {str(e)}"})
    persist_from_runtime(pid, session, SPECS, QUEUE)
    model = _specs_model(SPECS)
    html = render_template("specs_fragment.html", pid=pid, **model)
    # If this was an HTMX request, attach HX-Trigger with notifications
    resp = make_response(html)
    if request.headers.get("HX-Request") and triggered_msgs:
        import json as _json
        # Use a custom event name the client listens for
        resp.headers["HX-Trigger"] = _json.dumps({"notify": triggered_msgs})
    return resp

@bp.post("/p/<pid>/remove")
def remove_spec(pid: str):
    session, SPECS, QUEUE = get_runtime(pid)
    sid = request.form.get("spec_id")
    if sid:
        SPECS.pop(sid, None)
        for i in reversed(range(len(QUEUE))):
            if QUEUE[i]["spec_id"] == sid: QUEUE.pop(i)
    persist_from_runtime(pid, session, SPECS, QUEUE)
    model = _specs_model(SPECS)
    return render_template("specs_fragment.html", pid=pid, **model)

@bp.post("/p/<pid>/clear")
def clear_specs(pid: str):
    session, SPECS, QUEUE = get_runtime(pid)
    SPECS.clear(); QUEUE.clear()
    persist_from_runtime(pid, session, SPECS, QUEUE)
    return "<div class='muted'>No specs loaded yet.</div>"

# ---------- Operation details / edit ----------

## moved to routes/explorer.py: op_details
def op_details(pid: str):
    session, SPECS, QUEUE = get_runtime(pid)
    spec_id = request.form.get("spec_id")
    idx_raw = request.form.get("index")
    try:
        idx = int(idx_raw or 0)
    except:
        idx = 0
    s = SPECS.get(spec_id)
    if not s:
        return "<div class='drawer'>Not found</div>"
    ops = s["ops"]
    if idx < 0 or idx >= len(ops):
        return "<div class='drawer'>Invalid index</div>"

    resolver = RefResolver(s["spec"])
    seed = op_seed(s["url"], ops[idx]["method"], ops[idx]["path"])
    pre = build_preview(s["spec"], s["base_url"], ops[idx], resolver, seed=seed, fresh=False)

    # Merge session bearer for DISPLAY ONLY (so preview & cURL show it)
    display_headers = dict(pre.get("headers") or {})
    if session.get("bearer") and "Authorization" not in display_headers:
        display_headers["Authorization"] = f"Bearer {session['bearer']}"

    display_url = compose_display_url(pre.get("url", ""), pre.get("query") or {})
    pre_safe = dict(pre)
    pre_safe["query"] = _json_safe(pre.get("query"))
    pre_safe["headers"] = _json_safe(pre.get("headers"))
    pre_safe["cookies"] = _json_safe(pre.get("cookies"))
    pre_safe["json"] = _json_safe(pre.get("json"))
    pre_safe["data"] = _json_safe(pre.get("data"))
    return render_template(
        "op_details.html",
        pre=pre_safe,
        display_url=display_url,
        headers=_json_safe(display_headers),
        files_map=_files_preview_map(pre.get("files")),
    )

## moved to routes/explorer.py: op_edit
def op_edit(pid: str):
    session, SPECS, QUEUE = get_runtime(pid)
    spec_id = request.form.get("spec_id"); idx_raw = request.form.get("index")
    try: idx = int(idx_raw or 0)
    except: idx = 0
    s = SPECS.get(spec_id)
    if not s: return "<div class='drawer'>Not found</div>"
    ops = s["ops"]
    if idx < 0 or idx >= len(ops): return "<div class='drawer'>Invalid index</div>"
    resolver = RefResolver(s["spec"])
    seed = op_seed(s["url"], ops[idx]["method"], ops[idx]["path"])
    pre = build_preview(s["spec"], s["base_url"], ops[idx], resolver, seed=seed, fresh=False)
    # Prepare safe object for template
    pre_safe = dict(pre)
    pre_safe["query"] = _json_safe(pre.get("query"))
    pre_safe["headers"] = _json_safe(pre.get("headers"))
    pre_safe["cookies"] = _json_safe(pre.get("cookies"))
    pre_safe["json"] = _json_safe(pre.get("json"))
    pre_safe["data"] = _json_safe(pre.get("data"))
    return render_template(
        "op_edit.html",
        pid=pid, sid=s["safe_id"], idx=idx, spec_id=spec_id,
        pre=pre_safe,
    )
    

# ---------- Override preview/send ----------

def _make_override_from_form(form) -> Dict[str, Any]:
    ov: Dict[str, Any] = {}
    path_params = parse_json_field(form.get("path_params_json"), {})
    query = parse_json_field(form.get("query_json"), {})
    headers = parse_json_field(form.get("headers_json"), {})
    cookies = parse_json_field(form.get("cookies_json"), {})
    if isinstance(path_params, dict) and path_params: ov["path_params"] = path_params
    if isinstance(query, dict) and query: ov["query"] = query
    if isinstance(headers, dict) and headers: ov["headers"] = headers
    if isinstance(cookies, dict) and cookies: ov["cookies"] = cookies

    body_kind = (form.get("body_kind") or "default").strip()
    ct = (form.get("content_type") or "").strip()
    jb = form.get("json_body") or ""
    fj = form.get("form_json") or ""
    raw_ct = form.get("raw_ct") or ""
    raw_data = form.get("raw_data") or ""

    if body_kind == "default":
        if jb.strip():
            body_kind = "json"
        elif fj.strip():
            body_kind = "form"
        elif raw_data.strip():
            body_kind = "raw"

    ov["body_kind"] = body_kind
    if ct: ov["content_type"] = ct

    if body_kind == "json":
        try:
            ov["json"] = json.loads(jb) if jb.strip() else {}
        except Exception as e:
            ov["json"] = {"__invalid_json__": str(e), "__raw__": jb}
    elif body_kind == "form":
        parsed = parse_json_field(fj, {})
        ov["form"] = parsed if isinstance(parsed, dict) else {}
    elif body_kind == "raw":
        ov["raw"] = {"content_type": raw_ct, "data": raw_data}

    return ov

## moved to routes/explorer.py: op_preview_override
def op_preview_override(pid: str):
    session, SPECS, QUEUE = get_runtime(pid)
    spec_id = request.form.get("spec_id"); idx = int(request.form.get("index") or 0)
    s = SPECS.get(spec_id)
    if not s: return "<div class='drawer'>Not found</div>"
    resolver = RefResolver(s["spec"])
    op = s["ops"][idx]
    ov = _make_override_from_form(request.form)
    seed = op_seed(s["url"], op["method"], op["path"])
    fresh = request.form.get("fresh") == "1"
    pre = build_preview(s["spec"], s["base_url"], op, resolver, override=ov, seed=seed, fresh=fresh)
    # merge Bearer from session into preview headers for display/curl
    pre_headers = dict(pre.get("headers") or {})
    if session.get("bearer") and "Authorization" not in pre_headers:
        pre_headers["Authorization"] = f"Bearer {session['bearer']}"
    pre = dict(pre)
    pre["headers"] = pre_headers

    display_headers = dict(pre.get("headers") or {})
    if session.get("bearer") and "Authorization" not in display_headers:
        display_headers["Authorization"] = f"Bearer {session['bearer']}"

    pre_safe = dict(pre)
    pre_safe["query"] = _json_safe(pre.get("query"))
    pre_safe["headers"] = _json_safe(pre.get("headers"))
    pre_safe["cookies"] = _json_safe(pre.get("cookies"))
    pre_safe["json"] = _json_safe(pre.get("json"))
    pre_safe["data"] = _json_safe(pre.get("data"))
    return render_template(
        "op_preview.html",
        pre=pre_safe,
        headers=_json_safe(display_headers),
        files_map=_files_preview_map(pre.get("files")),
    )

## moved to routes/explorer.py: queue_add_override
def queue_add_override(pid: str):
    session, SPECS, QUEUE = get_runtime(pid)
    spec_id = request.form.get("spec_id"); idx = int(request.form.get("index") or 0)
    ov = _make_override_from_form(request.form)

    # merge session bearer into the override's headers so it persists in queue
    ov_headers = _with_session_bearer(ov.get("headers"), session)
    if ov_headers:
        ov["headers"] = ov_headers

    if spec_id in SPECS and 0 <= idx < len(SPECS[spec_id]["ops"]):
        QUEUE.append({"spec_id": spec_id, "idx": idx, "ops": SPECS[spec_id]["ops"], "override": ov})
        persist_from_runtime(pid, session, SPECS, QUEUE)
        return "<div class='drawer' style='border-color:#a7f3d0;color:#065f46;background:#ecfdf5'>Added 1 to queue.</div>"
    return "<div class='drawer'>Invalid selection</div>"

## moved to routes/explorer.py: send_now_override
def send_now_override(pid: str):
    session, SPECS, QUEUE = get_runtime(pid)
    spec_id = request.form.get("spec_id"); idx = int(request.form.get("index") or 0)
    s = SPECS.get(spec_id)
    if not s: return "<div class='drawer'>Not found</div>"
    resolver = RefResolver(s["spec"])
    op = s["ops"][idx]
    ov = _make_override_from_form(request.form)
    seed = op_seed(s["url"], op["method"], op["path"])
    pre = build_preview(s["spec"], s["base_url"], op, resolver, override=ov, seed=seed, fresh=False)
    proxies = {"http": session.get("proxy"), "https": session.get("proxy")} if session.get("proxy") else None
    if session.get("verify") is False:
        try:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except Exception:
            pass
    headers = dict(pre["headers"] or {})
    if session.get("bearer") and "Authorization" not in headers:
        headers["Authorization"] = f"Bearer {session['bearer']}"
    try:
        t0 = time.time()
        resp = requests.request(
            pre["method"], pre["url"], headers=headers, params=pre["query"] or None, cookies=pre["cookies"] or None,
            json=pre["json"] if pre["json"] is not None else None, data=pre["data"] if pre["data"] is not None else None,
            files=pre["files"] if pre["files"] is not None else None, timeout=60, proxies=proxies, verify=session.get("verify", True),
        )
        elapsed = int((time.time()-t0)*1000)
        out = {"ok": True, "status": resp.status_code, "reason": resp.reason, "url": pre["url"], "ms": elapsed}
    except Exception as e:
        out = {"ok": False, "status": "ERROR", "reason": str(e), "url": pre["url"]}
    RES = """
<div class="drawer">
  <div><strong>{{ 'OK' if out.ok else 'ERROR' }}</strong> {{ out.status }} {{ out.reason }}</div>
  <div class="muted">{{ out.url }}</div>
</div>
"""
    # Log send
    try:
        size = (resp.headers.get('Content-Length') if 'resp' in locals() and hasattr(resp,'headers') else None)
        entry = {
            "ts": int(time.time()*1000),
            "method": pre["method"],
            "url": pre["url"],
            "status": out["status"],
            "ok": out["ok"],
            "detail": out.get("reason"),
            "ms": out.get("ms"),
            "size": int(size) if (isinstance(size, str) and size.isdigit()) else None,
        }
        append_send_log(pid, entry)
        # Run detectors
        try:
            analyze_and_record(pid, pre, resp=resp if out["ok"] else None, error=None if out["ok"] else out.get("reason"))
        except Exception:
            pass
    except Exception:
        pass
    return render_template_string(RES, out=out)

# ---------- Queue ----------

@bp.post("/p/<pid>/queue_add")
def queue_add(pid: str):
    session, SPECS, QUEUE = get_runtime(pid)
    spec_id = request.form.get("spec_id")
    sels = request.form.getlist("sel")
    added = 0
    s = SPECS.get(spec_id)
    if s:
        # Build set of existing endpoint keys to prevent duplicates
        existing_keys = set()
        for ex in (QUEUE or []):
            try:
                sx = SPECS.get(ex.get("spec_id"))
                opx = (sx.get("ops") or [])[ex.get("idx", -1)] if sx else None
                if sx and opx:
                    kx = endpoint_key(opx.get("method") or "GET", sx.get("base_url") or sx.get("url") or "", opx.get("path") or "/")
                    existing_keys.add(kx)
            except Exception:
                continue
        for v in sels:
            try:
                idx = int(v)
                if 0 <= idx < len(s["ops"]):
                    op = s["ops"][idx]
                    k = endpoint_key(op.get("method") or "GET", s.get("base_url") or s.get("url") or "", op.get("path") or "/")
                    if k in existing_keys:
                        continue
                    # ensure Authorization header is persisted with the queued item
                    ov: Dict[str, Any] = {}
                    hdr = _with_session_bearer(None, session)
                    if hdr.get("Authorization"):
                        ov["headers"] = {"Authorization": hdr["Authorization"]}
                    QUEUE.append({"spec_id": spec_id, "idx": idx, "ops": s["ops"], "override": ov or None, "key": k})
                    existing_keys.add(k)
                    added += 1
            except:
                pass
    persist_from_runtime(pid, session, SPECS, QUEUE)
    TOAST = """<div class="drawer" style="border-color:#a7f3d0;color:#065f46;background:#ecfdf5">Added {{ count }} to queue. <a class="link" href='{{ url_for('web.queue_page', pid=pid) }}'>Open Queue</a></div>"""
    return render_template_string(TOAST, count=added, pid=pid)

@bp.route("/p/<pid>/queue_add_single", methods=["POST"])
def queue_add_single(pid: str):
    """Add a single endpoint to the queue from Site Map."""
    session, SPECS, QUEUE = get_runtime(pid)
    spec_id = request.form.get("spec_id")
    method = request.form.get("method")
    path = request.form.get("path")
    url = request.form.get("url")
    
    if not all([spec_id, method, path]):
        return "Missing required parameters", 400
    
    # Find the operation index in the spec
    spec = SPECS.get(spec_id)
    if not spec:
        return "Spec not found", 404
    
    # Find the operation by method and path (ignore query when matching op)
    ops = spec.get("ops", [])
    idx = None
    for i, op in enumerate(ops):
        if op.get("method") == method:
            op_path = op.get("path") or "/"
            req_path = path or "/"
            if url and not path:
                from urllib.parse import urlsplit
                u = urlsplit(url)
                req_path = u.path or "/"
            # Compare without query strings
            if op_path == req_path:
                idx = i
                break
    
    if idx is None:
        return "Operation not found in spec", 404
    
    # Compute endpoint key and de-dupe against existing queue
    op = ops[idx]
    # Build canonical key using full URL (include query) when provided
    if url:
        k = endpoint_key(method or "GET", url, None)
    else:
        k = endpoint_key(op.get("method") or "GET", spec.get("base_url") or spec.get("url") or "", op.get("path") or "/")
    for ex in (QUEUE or []):
        try:
            sx = SPECS.get(ex.get("spec_id"))
            opx = (sx.get("ops") or [])[ex.get("idx", -1)] if sx else None
            if sx and opx:
                kx = endpoint_key(opx.get("method") or "GET", sx.get("base_url") or sx.get("url") or "", opx.get("path") or "/")
                if kx == k:
                    return render_template_string("""
<div class=\"drawer\" style=\"border-color:#a7f3d0;color:#065f46;background:#ecfdf5\">Already in Test Queue</div>
""")
        except Exception:
            continue

    # Add to queue with session headers
    ov: Dict[str, Any] = {}
    hdr = _with_session_bearer(None, session)
    if hdr.get("Authorization"):
        ov["headers"] = {"Authorization": hdr["Authorization"]}

    QUEUE.append({"spec_id": spec_id, "idx": idx, "ops": ops, "override": ov or None, "key": k})
    persist_from_runtime(pid, session, SPECS, QUEUE)
    
    # Return a concise toast message that auto-dismisses
    TOAST = """<div class="drawer" style="border-color:#a7f3d0;color:#065f46;background:#ecfdf5;animation:slideIn 0.3s ease-out">✓ Added to Test Queue</div>
    <script>
      setTimeout(() => {
        const toast = document.querySelector('.drawer');
        if (toast) {
          toast.style.animation = 'slideOut 0.3s ease-in forwards';
          setTimeout(() => toast.remove(), 300);
        }
      }, 3000);
    </script>"""
    return render_template_string(TOAST)

## moved to routes/queue.py: queue_page

## moved to routes/queue.py: queue_item_details

# Back-compat alias with hyphenated path
## moved to routes/queue.py: queue_item_details_alias

@bp.post("/p/<pid>/queue/update_settings")
def queue_update_settings(pid: str):
    session, SPECS, QUEUE = get_runtime(pid)
    session["proxy"] = (request.form.get("proxy") or "").strip() or None
    session["verify"] = request.form.get("verify") == "1"
    session["bearer"] = (request.form.get("bearer") or "").strip() or None
    persist_from_runtime(pid, session, SPECS, QUEUE)

    # If it's an HTMX request, return an inline toast instead of redirecting
    if request.headers.get("HX-Request"):
        return render_template_string("""
<div class="drawer" style="border-color:#a7f3d0;color:#065f46;background:#ecfdf5">
  Settings saved ✓
</div>
""")

    # Fallback for non-HTMX posts
    return redirect(url_for("web.queue_page", pid=pid))

@bp.post("/p/<pid>/queue/remove")
def queue_remove(pid: str):
    session, SPECS, QUEUE = get_runtime(pid)
    try: idx = int(request.form.get("qid"))
    except: return redirect(url_for("web.queue_page", pid=pid))
    if 0 <= idx < len(QUEUE): QUEUE.pop(idx)
    persist_from_runtime(pid, session, SPECS, QUEUE)
    return redirect(url_for("web.queue_page", pid=pid))

@bp.post("/p/<pid>/queue/remove_selected")
def queue_remove_selected(pid: str):
    session, SPECS, QUEUE = get_runtime(pid)
    sel = request.form.getlist("sel")
    removed_any = False
    if sel:
        picks = []
        for v in sel:
            try:
                picks.append(int(v))
            except:
                pass
        for i in sorted(set(picks), reverse=True):
            if 0 <= i < len(QUEUE):
                QUEUE.pop(i)
                removed_any = True
        if removed_any:
            persist_from_runtime(pid, session, SPECS, QUEUE)
        return redirect(url_for("web.queue_page", pid=pid))

    all_ids = [int(v) for v in request.form.getlist("all_ids")]
    raw = (request.form.get("ids") or "").strip()
    to_remove = set()
    if raw:
        for chunk in raw.split(","):
            chunk = chunk.strip()
            if not chunk: continue
            try:
                qid = int(chunk)
                if qid in all_ids: to_remove.add(qid)
            except: pass
    if to_remove:
        for i in sorted(to_remove, reverse=True):
            if 0 <= i < len(QUEUE): QUEUE.pop(i)
        persist_from_runtime(pid, session, SPECS, QUEUE)
    return redirect(url_for("web.queue_page", pid=pid))

@bp.post("/p/<pid>/queue/send_selected")
def queue_send_selected(pid: str):
    session, SPECS, QUEUE = get_runtime(pid)
    sels = request.form.getlist("sel")
    picks = set()
    for v in sels:
        try:
            qid = int(v)
            picks.add(qid)
        except: pass
    proxies = {"http": session.get("proxy"), "https": session.get("proxy")} if session.get("proxy") else None
    if session.get("verify") is False:
        try:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except Exception:
            pass
    results = []
    for qid in sorted(picks):
        if not (0 <= qid < len(QUEUE)): continue
        it = QUEUE[qid]
        s = SPECS.get(it["spec_id"])
        if not s: 
            results.append({"ok": False, "status": "N/A", "method": "?", "url": "spec removed", "detail": "Spec not found"})
            continue
        resolver = RefResolver(s["spec"])
        op = s["ops"][it["idx"]]
        seed = op_seed(s["url"], op["method"], op["path"])
        pre = build_preview(s["spec"], s["base_url"], op, resolver, override=it.get("override"), seed=seed, fresh=False)
        headers = dict(pre["headers"] or {})
        if session.get("bearer") and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {session['bearer']}"
        try:
            t0 = time.time()
            resp = requests.request(
                pre["method"], pre["url"], headers=headers, params=pre["query"] or None, cookies=pre["cookies"] or None,
                json=pre["json"] if pre["json"] is not None else None, data=pre["data"] if pre["data"] is not None else None,
                files=pre["files"] if pre["files"] is not None else None, timeout=60, proxies=proxies, verify=session.get("verify", True),
            )
            elapsed = int((time.time()-t0)*1000)
            results.append({"ok": True, "status": resp.status_code, "method": pre["method"], "url": pre["url"], "detail": resp.reason})
            try:
                entry = {
                    "ts": int(time.time()*1000),
                    "method": pre["method"],
                    "url": pre["url"],
                    "status": resp.status_code,
                    "ok": True,
                    "detail": resp.reason,
                    "ms": elapsed,
                    "size": int(resp.headers.get('Content-Length')) if (resp.headers.get('Content-Length') and str(resp.headers.get('Content-Length')).isdigit()) else None,
                }
                append_send_log(pid, entry)
                try:
                    analyze_and_record(pid, pre, resp=resp)
                    # Additional reflection handled within analyze_and_record
                except Exception:
                    pass
            except Exception:
                pass
        except Exception as e:
            results.append({"ok": False, "status": "ERROR", "method": pre["method"], "url": pre["url"], "detail": str(e)})
            try:
                append_send_log(pid, {"ts": int(time.time()*1000), "method": pre["method"], "url": pre["url"], "status": "ERROR", "ok": False, "detail": str(e), "ms": None, "size": None})
                try:
                    analyze_and_record(pid, pre, resp=None, error=str(e))
                except Exception:
                    pass
            except Exception:
                pass
    return render_browser(pid, session, SPECS, QUEUE, results=results)

@bp.post("/p/<pid>/queue/clear")
def queue_clear(pid: str):
    session, SPECS, QUEUE = get_runtime(pid)
    QUEUE.clear()
    persist_from_runtime(pid, session, SPECS, QUEUE)
    return redirect(url_for("web.queue_page", pid=pid))

@bp.post("/p/<pid>/queue/send_all")
def queue_send_all(pid: str):
    session, SPECS, QUEUE = get_runtime(pid)
    proxies = {"http": session.get("proxy"), "https": session.get("proxy")} if session.get("proxy") else None
    if session.get("verify") is False:
        try:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except Exception:
            pass
    results = []
    for it in list(QUEUE):
        s = SPECS.get(it["spec_id"])
        if not s:
            results.append({"ok": False, "status": "N/A", "method": "?", "url": "spec removed", "detail": "Spec not found"})
            continue
        resolver = RefResolver(s["spec"])
        op = s["ops"][it["idx"]]
        seed = op_seed(s["url"], op["method"], op["path"])
        pre = build_preview(s["spec"], s["base_url"], op, resolver, override=it.get("override"), seed=seed, fresh=False)
        headers = dict(pre["headers"] or {})
        if session.get("bearer") and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {session['bearer']}"
        try:
            t0 = time.time()
            resp = requests.request(
                pre["method"], pre["url"], headers=headers, params=pre["query"] or None, cookies=pre["cookies"] or None,
                json=pre["json"] if pre["json"] is not None else None, data=pre["data"] if pre["data"] is not None else None,
                files=pre["files"] if pre["files"] is not None else None, timeout=60, proxies=proxies, verify=session.get("verify", True),
            )
            elapsed = int((time.time()-t0)*1000)
            results.append({"ok": True, "status": resp.status_code, "method": pre["method"], "url": pre["url"], "detail": resp.reason})
            try:
                entry = {
                    "ts": int(time.time()*1000),
                    "method": pre["method"],
                    "url": pre["url"],
                    "status": resp.status_code,
                    "ok": True,
                    "detail": resp.reason,
                    "ms": elapsed,
                    "size": int(resp.headers.get('Content-Length')) if (resp.headers.get('Content-Length') and str(resp.headers.get('Content-Length')).isdigit()) else None,
                }
                append_send_log(pid, entry)
                try:
                    analyze_and_record(pid, pre, resp=resp)
                    try:
                        body_text = ""
                        try:
                            body_text = resp.text or ""
                        except Exception:
                            body_text = ""
                        res_obj = {
                            "content_type": (resp.headers.get('Content-Type') if hasattr(resp, 'headers') else None),
                            "headers": dict(resp.headers or {}),
                        }
                        # Additional reflection handled within analyze_and_record
                    except Exception:
                        pass
                except Exception:
                    pass
            except Exception:
                pass
        except Exception as e:
            results.append({"ok": False, "status": "ERROR", "method": pre["method"], "url": pre["url"], "detail": str(e)})
            try:
                append_send_log(pid, {"ts": int(time.time()*1000), "method": pre["method"], "url": pre["url"], "status": "ERROR", "ok": False, "detail": str(e), "ms": None, "size": None})
                try:
                    analyze_and_record(pid, pre, resp=None, error=str(e))
                except Exception:
                    pass
            except Exception:
                pass
    persist_from_runtime(pid, session, SPECS, QUEUE)
    return render_browser(pid, session, SPECS, QUEUE, results=results)

# ---------- Sends history ----------

## moved to routes/history.py: sends_page

## moved to routes/history.py: sends_clear


# ---------- Route Aliases (Phase 4 - Backward Compatibility) ----------

## moved to routes/history.py: history_page

## moved to routes/history.py: history_clear


# ---------- Findings ----------

## moved to routes/findings.py: findings_page

## moved to routes/findings.py: findings_clear

## moved to routes/findings.py: triage_group

## moved to routes/findings.py: export_group

## moved to routes/findings.py: queue_group

## moved to routes/findings.py: finding_detail


## moved to routes/findings.py: finding_view
def old_finding_view(pid: str):
    """Single finding view with explanation (category + evidence-driven subcases) and highlighted evidence."""
    try:
        idx = int(request.form.get("idx") or -1)
    except Exception:
        idx = -1
    f = get_finding_by_index(pid, idx)
    if not f:
        return redirect(url_for("web.findings_page", pid=pid))

    # Build tokens to highlight across headers/body (detector-aware)
    toks: List[str] = []
    for k in ("match", "param"):
        v = f.get(k)
        if isinstance(v, str) and v.strip():
            toks.append(v.strip())
    res_headers = ((f.get("res") or {}).get("headers") or {}) or {}
    det_id_for_hl = (f.get("detector_id") or f.get("detector") or "").lower()
    try:
        if det_id_for_hl == "server_tech_disclosure":
            for hk in ("Server", "X-Powered-By"):
                hv = res_headers.get(hk) or res_headers.get(hk.lower())
                if isinstance(hv, str) and len(hv) >= 2:
                    toks.append(hv)
        elif det_id_for_hl == "cors_star_with_credentials":
            for hk in ("Access-Control-Allow-Origin", "Access-Control-Allow-Credentials"):
                hv = res_headers.get(hk) or res_headers.get(hk.lower())
                if isinstance(hv, str) and len(hv) >= 1:
                    toks.append(hv)
        # For rate_limit_headers_missing and sec_headers_missing, do not add header values
    except Exception:
        pass
    # dedupe case-insensitively
    seen = set(); uniq = []
    for t in toks:
        tl = t.lower()
        if tl in seen: continue
        uniq.append(t); seen.add(tl)
    toks = uniq

    # Simple highlighter
    def _hl(s: str, needles: List[str]) -> str:
        try:
            import re as _re

            from markupsafe import escape
            out = s or ""
            for t in needles:
                if not t:
                    continue
                if len(t) < 3 or t.isdigit():  # avoid excessive noise
                    continue
                pat = _re.compile(_re.escape(t), _re.IGNORECASE)
                out = pat.sub(lambda m: "<mark>" + escape(m.group(0)) + "</mark>", out)
            return out
        except Exception:
            return s or ""

    # Compose Request/Response display blobs
    import json as _json
    req = f.get("req") or {}
    res = f.get("res") or {}
    req_headers = dict(req.get("headers") or {})
    if "Authorization" in req_headers:
        req_headers["Authorization"] = "***"
    req_headers_json = _json.dumps(req_headers, indent=2, ensure_ascii=False)
    res_headers_json = _json.dumps(res.get("headers") or {}, indent=2, ensure_ascii=False)
    if req.get("json") is not None:
        req_body_str = _json.dumps(req.get("json"), indent=2, ensure_ascii=False)
    elif req.get("data") is not None:
        try:
            req_body_str = _json.dumps(req.get("data"), indent=2, ensure_ascii=False)
        except Exception:
            req_body_str = str(req.get("data"))
    else:
        req_body_str = ""
    res_body_str = str(res.get("body") or "")

    # Highlight and escape content to prevent XSS
    from markupsafe import escape
    req_headers_json_hl = escape(_hl(req_headers_json, toks))
    res_headers_json_hl = escape(_hl(res_headers_json, toks))
    req_body_json_hl = escape(_hl(req_body_str, toks))
    res_body_hl = escape(_hl(res_body_str, toks))

    explain_html = get_finding_explanation(f)

    # Escape all finding data to prevent XSS
    from markupsafe import escape
    f_escaped = {}
    for k, v in f.items():
        if isinstance(v, str):
            f_escaped[k] = escape(v)
        else:
            f_escaped[k] = v

    # Provide panel header Copy curl payload for consistency across pages
    try:
        req_for_curl = f.get("req") or {}
        curl_lines = []
        method_for_curl = (req_for_curl.get("method") or f.get("method") or "").upper()
        url_for_curl = req_for_curl.get("url") or f.get("url") or ""
        curl_lines.append(f"curl -X {method_for_curl} '{url_for_curl}'")
        hdrs_for_curl = req_for_curl.get("headers") or {}
        if isinstance(hdrs_for_curl, dict):
            for hk, hv in hdrs_for_curl.items():
                try:
                    if str(hk).lower() == "authorization":
                        hv = "***"
                    curl_lines.append(f"  -H '{hk}: {hv}'")
                except Exception:
                    continue
        if req_for_curl.get("json") is not None:
            import json as _json
            curl_lines.append("  -d '" + _json.dumps(req_for_curl.get("json"), ensure_ascii=False) + "'")
        elif req_for_curl.get("data") is not None:
            curl_lines.append("  -d '" + str(req_for_curl.get("data")) + "'")
        panel_curl = " \\\n+".join(curl_lines)
    except Exception:
        panel_curl = ""

    # Friendly detector label for view
    det_id = (f.get("detector_id") or f.get("detector") or "").lower()
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
    }.get(det_id, (f.get("detector_id") or f.get("detector") or "").replace('_',' '))

    T = """
<div class="card">
  <div class="row" style="justify-content:space-between">
    <div><span class="pill">{{ f.severity or '' }}</span> {{ f.title|e }}</div>
    <div class="muted">{{ f.ts or '' }}</div>
  </div>
  <div class="row" style="margin-top:8px;align-items:center;gap:10px;flex-wrap:nowrap">
    <span class="chip {{ f.method }}">{{ f.method|e }}</span>
    <span class="muted">{{ f.status or '' }}</span>
    <div class="muted" style="flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ f.url|e }}</div>
  </div>
  <div class="row" style="margin-top:6px;align-items:center;gap:8px;flex-wrap:wrap">
    {% if det_friendly %}<span class="pill">{{ det_friendly|e }}</span>{% endif %}
    {% if f.owasp_api %}<span class="pill">{{ f.owasp_api|e }}</span>{% endif %}
    {% if f.owasp %}<span class="pill">{{ f.owasp|e }}</span>{% endif %}
    {% if f.cwe %}<span class="pill">{{ f.cwe|e }}</span>{% endif %}
  </div>

  <div class="drawer">
    <strong>Details</strong>
    <div style="margin-top:6px">{{ explain_html|safe }}</div>
  </div>

  {% if f.evidence %}
  <div class="drawer" style="margin-top:12px">
    <strong>Evidence</strong>
    <pre>{{ f.evidence|e }}</pre>
  </div>
  {% endif %}

  <details class="coll" open>
    <summary><span class="chev">▶</span> Request</summary>
    <div class="drawer">
      <script id="panel-curl" type="application/json">{{ panel_curl }}</script>
      <div class="panel-section"><h4>Headers</h4><pre>{{ req_headers_json_hl|safe }}</pre></div>
      {% if req_body_json_hl %}
        <div class="panel-section"><h4>Body</h4><pre>{{ req_body_json_hl|safe }}</pre></div>
      {% endif %}
    </div>
  </details>

  <details class="coll" open>
    <summary><span class="chev">▶</span> Response</summary>
    <div class="drawer">
      <div class="panel-section"><h4>Headers</h4><pre>{{ res_headers_json_hl }}</pre></div>
      <div class="panel-section"><h4>Body</h4><pre>{{ res_body_hl }}</pre></div>
    </div>
  </details>
</div>
"""
    return render_template(
        "finding_detail.html",
        pid=pid,
        project_name=get_project_name(pid),
        f=f_escaped,
        req_headers_json_hl=req_headers_json_hl,
        req_body_json_hl=req_body_json_hl,
        res_headers_json_hl=res_headers_json_hl,
        res_body_hl=res_body_hl,
        explain_html=explain_html,
        panel_curl=panel_curl,
    )

## moved to routes/patterns.py: patterns routes

# ===========================
# Reporting Routes
# ===========================

## moved to routes/reports.py: reports_page

## moved to routes/reports.py: export_report

## moved to routes/reports.py: report_summary

# ====== SITE MAP ROUTES ======

## moved to routes/sitemap.py: site_map_page

## moved to routes/sitemap.py: sitemap_preview_endpoint (legacy)

@bp.route("/p/<pid>/sitemap/test-folder", methods=["POST"])
def sitemap_test_folder(pid: str):
    """Add all endpoints in a folder to the test queue."""
    try:
        folder_id = request.form.get("folder_id")
        if not folder_id:
            return "Missing folder_id", 400

        session, SPECS, QUEUE = get_runtime(pid)

        # Parse folder_id to get base and path prefix
        # Format: "base_safe_id::path_prefix"
        parts = folder_id.split("::", 1)
        if len(parts) != 2:
            return "Invalid folder_id format", 400
        
        base_safe_id, path_prefix = parts
        # Find all endpoints that match this folder path
        endpoints_to_add = []

        for spec_id, spec in SPECS.items():
            ops = spec.get("ops", [])
            for op in ops:
                path = op.get("path", "")
                # Check if this endpoint belongs to the folder
                # path_prefix is like "/pet" - check if path starts with it
                if path.startswith(path_prefix):
                    # Find the operation index
                    idx = ops.index(op)

                    # Add to queue with session headers
                    ov: Dict[str, Any] = {}
                    hdr = _with_session_bearer(None, session)
                    if hdr.get("Authorization"):
                        ov["headers"] = {"Authorization": hdr["Authorization"]}

                    QUEUE.append({
                        "spec_id": spec_id,
                        "idx": idx,
                        "ops": ops,
                        "override": ov or None
                    })
                    endpoints_to_add.append(f"{op.get('method')} {path}")

        persist_from_runtime(pid, session, SPECS, QUEUE)

        # Return a concise toast message that auto-dismisses
        TOAST = """<div class="drawer" style="border-color:#a7f3d0;color:#065f46;background:#ecfdf5;animation:slideIn 0.3s ease-out">✓ Added {{ count }} endpoints to Test Queue</div>
        <script>
          setTimeout(() => {
            const toast = document.querySelector('.drawer');
            if (toast) {
              toast.style.animation = 'slideOut 0.3s ease-in forwards';
              setTimeout(() => toast.remove(), 300);
            }
          }, 3000);
        </script>"""
        return render_template_string(TOAST, count=len(endpoints_to_add))
    except Exception as e:
        return f"Error adding folder to queue: {str(e)}", 500


# ---------- Phase 5: Nuclei Active Testing ----------

## moved to routes/nuclei.py: nuclei_status
def nuclei_status(pid: str):
    """Get Nuclei scanner status and available templates."""
    try:
        status = nuclei_integration.check_nuclei_status()
        return {
            "success": True,
            "status": status
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }, 500

## moved to routes/nuclei.py: nuclei_update_templates
def nuclei_update_templates(pid: str):
    """Update Nuclei templates."""
    try:
        success, message = nuclei_integration.update_templates()
        return {
            "success": success,
            "message": message
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }, 500

## moved to routes/nuclei.py: nuclei_templates
def nuclei_templates(pid: str):
    """Get available Nuclei templates with enhanced support for ASVS and filtering."""
    try:
        category = request.args.get('category')
        source = request.args.get('source')
        all_flag = request.args.get('all') == '1'
        
        # Use the enhanced nuclei wrapper
        templates = nuclei_integration.nuclei.list_templates(
            category=category, 
            source=source, 
            all_templates=all_flag
        )
        
        return {
            "success": True,
            "templates": templates
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }, 500

## moved to routes/nuclei.py: nuclei_scan
def nuclei_scan(pid: str):
    """Run Nuclei scan on project endpoints."""
    try:
        # Get scan parameters
        templates = request.form.getlist('templates') or None
        severity = request.form.getlist('severity') or None
        exclude_patterns = request.form.getlist('exclude_patterns') or None
        
        # Run scan
        result = nuclei_integration.scan_project_endpoints(
            pid=pid,
            templates=templates,
            severity=severity,
            exclude_patterns=exclude_patterns
        )
        
        # Enhanced run tracking with full provenance
        if result["success"]:
            run_id = make_run_id()
            started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            finished_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            
            # Build comprehensive run document
            run_doc = {
                "run_id": run_id,
                "started_at": started_at,
                "finished_at": finished_at,
                "initiator": {"user": "admin", "source": "ui"},
                "provenance": {
                    "nuclei_version": "unknown",  # Could get from nuclei_integration
                    "template_dirs": nuclei_integration.nuclei.extra_template_dirs + [nuclei_integration.nuclei.template_dir],
                    "severity": severity or [],
                    "templates_requested": templates or [],
                    "templates_resolved": len(templates) if templates else 0,
                    "exclude_patterns": exclude_patterns or []
                },
                "targets": [],  # Will be populated from endpoints
                "stats": {
                    "endpoints": result.get("endpoints_scanned", 0),
                    "findings": result["findings_count"],
                    "by_severity": {}  # Will be calculated
                },
                "results": []  # Will be populated with detailed results
            }
            
            try:
                # Save run document
                save_run(pid, run_doc)
                # Update endpoint dossiers for each queued endpoint using canonical key
                from store import _endpoint_dossier_path_by_key, get_runtime
                from store import update_endpoint_dossier_by_key as write_dossier
                from utils.endpoints import endpoint_key as make_key
                session, SPECS, QUEUE = get_runtime(pid)
                # Build a normalized per-endpoint summary
                summary = {
                    "run_id": run_id,
                    "started_at": started_at,
                    "finished_at": finished_at,
                    "findings": result.get("findings_count", 0),
                    "worst": result.get("worst_severity") or "info",
                    "artifact": result.get("artifact_path"),
                }
                for it in list(QUEUE or []):
                    s = SPECS.get(it.get("spec_id"))
                    if not s:
                        continue
                    try:
                        op = (s.get("ops") or [])[it.get("idx", -1)]
                    except Exception:
                        op = None
                    if not op:
                        continue
                    base = s.get("base_url") or s.get("url") or ""
                    method = (op.get("method") or "GET").upper()
                    path = op.get("path") or "/"
                    # Prefer queue item's canonical key if present (includes query)
                    key = it.get("key")
                    if not key:
                        # Try to construct from a full preview URL (captures query)
                        try:
                            from specs import RefResolver, build_preview, op_seed
                            resolver = RefResolver(s.get("spec"))
                            seed = op_seed(s.get("url"), op.get("method"), op.get("path"))
                            pre = build_preview(s.get("spec"), s.get("base_url"), op, resolver, override=it.get("override"), seed=seed, fresh=False)
                            full_url = pre.get("url") or (base + path)
                            key = make_key(method, full_url, None)
                        except Exception:
                            key = make_key(method, base, path)
                    write_dossier(pid, key, summary)
                    try:
                        fpath = _endpoint_dossier_path_by_key(pid, key)
                        logging.getLogger("dossier").info(f"DOSSIER_WRITE key=\"{key}\" run=\"{run_id}\" findings={summary.get('findings',0)} worst=\"{summary.get('worst')}\" file=\"{fpath}\"")
                    except Exception:
                        pass
            except Exception as e:
                logging.error(f"Failed to save run: {e}")
        
        return {
            "success": result["success"],
            "message": result["message"],
            "findings_count": result["findings_count"],
            "endpoints_scanned": result.get("endpoints_scanned", 0),
            "templates_used": result.get("templates_used", "all"),
            "severity_filter": result.get("severity_filter", "all")
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }, 500

## moved to routes/nuclei.py: active_testing_page
def active_testing_page(pid: str):
    return "Moved to routes/nuclei.py", 404

## moved to routes/nuclei.py: queue_summary
def queue_summary(pid: str):
    return {"success": False, "error": "Moved to routes/nuclei.py"}, 404


# ---------- Phase 5: Triaging Workflow ----------

## moved to routes/findings.py: triage_finding
def triage_finding(pid: str):
    pass

## moved to routes/findings.py: triage_stats
def triage_stats(pid: str):
    pass


# ---------- Template Management ----------

## moved to routes/nuclei.py: nuclei_profiles
def nuclei_profiles(pid: str):
    """Get list of saved template profiles."""
    from flask import jsonify

    from store import get_profiles
    
    try:
        profiles = get_profiles(pid)
        return jsonify({"success": True, "profiles": profiles})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

## moved to routes/nuclei.py: nuclei_profiles_save
def nuclei_profiles_save(pid: str):
    """Save a template profile."""
    from flask import jsonify, request

    from store import save_profile
    
    try:
        data = request.get_json()
        name = data.get("name")
        templates = data.get("templates", [])
        
        if not name:
            return jsonify({"success": False, "error": "Profile name required"}), 400
        
        save_profile(pid, name, templates)
        return jsonify({"success": True})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

## moved to routes/nuclei.py: nuclei_profile_load
def nuclei_profile_load(pid: str, name: str):
    """Load a specific template profile."""
    from flask import jsonify

    from store import load_profile
    
    try:
        templates = load_profile(pid, name)
        return jsonify({"success": True, "templates": templates})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

## moved to routes/nuclei.py: nuclei_profile_delete
def nuclei_profile_delete(pid: str, name: str):
    """Delete a template profile."""
    from flask import jsonify

    from store import delete_profile
    
    try:
        delete_profile(pid, name)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

## moved to routes/sitemap.py: sitemap_runs_for_endpoint

## moved to routes/sitemap.py: sitemap_endpoint_preview

@bp.post("/p/<pid>/runs/detail-for-endpoint")
def run_detail_for_endpoint(pid: str):
    """Get detailed run information for a specific endpoint."""
    try:
        run_id = request.form.get("run_id")
        method = request.form.get("method", "GET")
        url = request.form.get("url", "")
        
        if not run_id:
            return "Missing run_id", 400
            
        # Try to load run from dossier first
        from store import get_endpoint_runs_by_key
        from utils.endpoints import endpoint_key
        
        key = endpoint_key(method, url, None)
        runs = get_endpoint_runs_by_key(pid, key, limit=50)
        
        # Find the specific run
        target_run = None
        for run in runs:
            if run.get("run_id") == run_id:
                target_run = run
                break
        
        if not target_run:
            return "Run not found", 404
            
        # Load detailed test data from artifact
        artifact_path = target_run.get("artifact")
        test_results = []
        
        if artifact_path and os.path.exists(artifact_path):
            try:
                with open(artifact_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            test_data = json.loads(line)
                            test_results.append(test_data)
            except Exception as e:
                logger.warning(f"Failed to parse artifact {artifact_path}: {e}")
        
        # Create a mock run object for the template
        mock_run = {
            "run_id": run_id,
            "started_at": target_run.get("started_at", ""),
            "finished_at": target_run.get("finished_at", ""),
            "findings": target_run.get("findings", 0),
            "worst": target_run.get("worst", "info")
        }
        
        # Create a mock result object with nuclei findings
        mock_result = {
            "nuclei": test_results,
            "endpoint": {
                "method": method,
                "url": url
            }
        }
        
        return render_template("run_detail_endpoint.html", run=mock_run, r=mock_result)
    except Exception as e:
        return f"Error loading run detail: {e}", 500

@bp.post("/p/<pid>/runs/detail-latest")
def run_detail_latest(pid: str):
    """Open run detail for the first endpoint in a run (helper for Active Testing)."""
    try:
        run_id = request.form["run_id"]
        run = load_run(pid, run_id)
        slim = None
        for r in run.get("results", []) or []:
            if r.get("endpoint"):
                slim = r
                break
        return render_template("run_detail_endpoint.html", run=run, r=slim)
    except Exception as e:
        return f"Error loading run detail: {e}", 500

@bp.get("/p/<pid>/runs")
def runs_page(pid: str):
    """Enhanced runs list page with endpoint info, filtering, and sorting."""
    try:
        import logging

        from flask import request

        from findings import count_findings_cached
        from store import get_project_name, list_runs
        
        # Get runs with enhanced endpoint information
        runs = list_runs(pid, limit=100)  # Get more runs for filtering
        
        # Enhance runs with endpoint information
        enhanced_runs = []
        for run in runs:
            enhanced_run = dict(run)
            
            # Try to extract endpoint info from run metadata
            if 'endpoints' in run and run['endpoints']:
                # For runs with endpoint info, use the first endpoint
                endpoint_info = run['endpoints'][0] if isinstance(run['endpoints'], list) else run['endpoints']
                enhanced_run['endpoint_method'] = endpoint_info.get('method', '')
                enhanced_run['endpoint_path'] = endpoint_info.get('path', '')
                enhanced_run['endpoint_key'] = f"{enhanced_run['endpoint_method']} {enhanced_run['endpoint_path']}"
            elif 'endpoint_method' in run and 'endpoint_path' in run:
                # Direct endpoint info
                enhanced_run['endpoint_method'] = run['endpoint_method']
                enhanced_run['endpoint_path'] = run['endpoint_path'] 
                enhanced_run['endpoint_key'] = f"{enhanced_run['endpoint_method']} {enhanced_run['endpoint_path']}"
            else:
                # No endpoint info available
                enhanced_run['endpoint_method'] = ''
                enhanced_run['endpoint_path'] = ''
                enhanced_run['endpoint_key'] = ''
            
            enhanced_runs.append(enhanced_run)
        
        # Handle sorting
        sort_param = request.args.get('sort', 'when_desc')
        if sort_param == 'when_desc':
            enhanced_runs.sort(key=lambda x: str(x.get('finished_at') or x.get('started_at') or ''), reverse=True)
        elif sort_param == 'when':
            enhanced_runs.sort(key=lambda x: str(x.get('finished_at') or x.get('started_at') or ''), reverse=False)
        elif sort_param == 'findings_desc':
            enhanced_runs.sort(key=lambda x: x.get('stats', {}).get('findings', x.get('findings', 0)) or 0, reverse=True)
        elif sort_param == 'findings':
            enhanced_runs.sort(key=lambda x: x.get('stats', {}).get('findings', x.get('findings', 0)) or 0, reverse=False)
        elif sort_param == 'endpoint':
            enhanced_runs.sort(key=lambda x: f"{x.get('endpoint_method', '')} {x.get('endpoint_path', '')}")
        elif sort_param == 'worst':
            enhanced_runs.sort(key=lambda x: str(x.get('stats', {}).get('worst', x.get('worst', 'info'))))
        elif sort_param == 'run_id':
            enhanced_runs.sort(key=lambda x: str(x.get('run_id', '')))
        
        try:
            logging.getLogger("runs").info(
                "RUNS_INDEX pid=\"%s\" count=%s enhanced=%s",
                pid,
                len(runs or []),
                len(enhanced_runs),
            )
        except Exception:
            pass
            
        return render_template("runs.html", pid=pid, runs=enhanced_runs, 
                             project_name=get_project_name(pid), counts=count_findings_cached(pid))
    except Exception as e:
        return f"Error loading runs: {e}", 500

@bp.get("/p/<pid>/runs/export")
def run_export(pid: str):
    """Download run artifact (NDJSON) if available."""
    try:
        from flask import send_file
        run_id = request.args.get("run_id")
        if not run_id:
            return {"error": "run_id required"}, 400
        run = load_run(pid, run_id)
        art = (run or {}).get("artifact")
        if not art or not os.path.exists(art):
            return {"error": "artifact not found"}, 404
        return send_file(art, mimetype="application/x-ndjson", as_attachment=True, download_name=f"{run_id}.ndjson")
    except Exception as e:
        return {"error": str(e)}, 500

## removed: legacy minimal drawer alias for findings detail

@bp.get("/p/<pid>/templates/status")
def template_status(pid: str):
    """Get current template status and available sources."""
    try:
        # Get current template counts (from cached index for speed)
        all_templates = nuclei_integration.nuclei.list_templates(all_templates=True)
        nuclei_count = len([t for t in all_templates if t.get("source") == "nuclei"])
        # Consider ASVS present if any path includes '/asvs/' or is tagged asvs
        asvs_count = len([
            t for t in all_templates
            if (
                t.get("source") == "asvs"
                or "/asvs/" in str(t.get("path", "")).lower()
                or ("asvs" in str(t.get("path", "")).lower())
            )
        ])
        
        # Check for available template sources
        sources = {
            "nuclei": {
                "name": "Nuclei Templates",
                "description": "Built-in Nuclei security templates",
                "count": nuclei_count,
                "available": True,
                "path": nuclei_integration.nuclei.template_dir
            },
            "asvs": {
                "name": "OWASP ASVS Templates", 
                "description": "OWASP Application Security Verification Standard templates",
                "count": asvs_count,
                "available": asvs_count > 0,
                "path": None
            }
        }
        
        # Check if ASVS is available
        if asvs_count == 0:
            sources["asvs"]["status"] = "not_installed"
            sources["asvs"]["install_url"] = "https://github.com/OWASP/owasp-asvs-security-evaluation-templates-with-nuclei"
        else:
            sources["asvs"]["status"] = "installed"
        
        return {
            "success": True,
            "sources": sources,
            "total_templates": len(all_templates)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

@bp.post("/p/<pid>/templates/reindex")
def templates_reindex(pid: str):
    """Kick off a background reindex of templates without blocking the UI."""
    try:
        import threading
        import time as _t

        from nuclei_integration import nuclei_integration
        if _TPL_REINDEX_STATUS.get(pid, {}).get("running"):
            return {"success": True, "message": "Reindex already running"}

        _TPL_REINDEX_STATUS[pid] = {"running": True, "started_at": _t.time()}

        def worker():
            try:
                nuclei_integration.nuclei._index_built = False
                nuclei_integration.nuclei._build_index()
                items = nuclei_integration.nuclei.list_templates(all_templates=True)
                _TPL_REINDEX_STATUS[pid] = {
                    "running": False,
                    "finished": True,
                    "finished_at": _t.time(),
                    "count": len(items)
                }
            except Exception as ex:
                _TPL_REINDEX_STATUS[pid] = {
                    "running": False,
                    "finished": True,
                    "error": str(ex)
                }

        threading.Thread(target=worker, daemon=True).start()
        return {"success": True, "message": "Reindex started"}
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

@bp.get("/p/<pid>/templates/reindex-status")
def templates_reindex_status(pid: str):
    """Query background reindex state."""
    try:
        st = _TPL_REINDEX_STATUS.get(pid) or {"running": False}
        return {"success": True, **st}
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

@bp.post("/p/<pid>/templates/update")
def update_templates(pid: str):
    """Update templates from available sources."""
    try:
        source = request.form.get("source", "all")
        action = request.form.get("action", "update")
        
        results = {
            "nuclei": {"updated": False, "count": 0, "error": None},
            "asvs": {"updated": False, "count": 0, "error": None}
        }
        
        if source in ["all", "nuclei"]:
            try:
                # Use cached index first; only rebuild if requested
                if action == "reindex":
                    nuclei_integration.nuclei._index_built = False
                    nuclei_templates = nuclei_integration.nuclei.list_templates(source="nuclei", all_templates=True)
                    results["nuclei"]["updated"] = True
                    results["nuclei"]["count"] = len(nuclei_templates)
            except Exception as e:
                results["nuclei"]["error"] = str(e)
        
        if source in ["all", "asvs"]:
            if action == "install":
                # This would trigger ASVS installation
                results["asvs"]["message"] = "ASVS installation requires manual setup. See documentation."
            else:
                # Check if ASVS is already available
                # Reuse broader detection (tag or path contains asvs)
                asvs_templates = [
                    t for t in nuclei_integration.nuclei.list_templates(all_templates=True)
                    if (
                        t.get("source") == "asvs"
                        or "/asvs/" in str(t.get("path", "")).lower()
                        or ("asvs" in str(t.get("path", "")).lower())
                    )
                ]
                if asvs_templates:
                    results["asvs"]["updated"] = True
                    results["asvs"]["count"] = len(asvs_templates)
                else:
                    results["asvs"]["error"] = "ASVS templates not found. Please install manually."
        
        return {
            "success": True,
            "results": results,
            "message": "Template update completed"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

@bp.post("/p/<pid>/templates/register-source")
def register_template_source(pid: str):
    """Register a new template source directory."""
    try:
        source_path = request.form.get("path", "").strip()
        source_name = request.form.get("name", "custom")
        
        if not source_path or not os.path.isdir(source_path):
            return {"success": False, "error": "Invalid directory path"}, 400
        
        # Register the new source
        nuclei_integration.nuclei.register_template_dir(source_path, source=source_name)
        
        # Get updated counts
        all_templates = nuclei_integration.nuclei.list_templates(all_templates=True)
        source_count = len([t for t in all_templates if t.get("source") == source_name])
        
        return {
            "success": True,
            "message": f"Registered {source_name} source with {source_count} templates",
            "source": {
                "name": source_name,
                "path": source_path,
                "count": source_count
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

def install_asvs_templates():
    """Install ASVS templates automatically."""
    import shutil
    import tempfile
    import urllib.request
    import zipfile
    
    try:
        # Create ASVS directory within configured nuclei templates dir
        from config import set as cfg_set
        nuclei_template_dir = nuclei_integration.nuclei.template_dir
        asvs_dir = os.path.join(nuclei_template_dir, "asvs")
        
        # Create directory if it doesn't exist
        os.makedirs(asvs_dir, exist_ok=True)
        
        # Download ASVS repository as zip file
        temp_dir = tempfile.mkdtemp(prefix="asvs_")
        zip_url = "https://github.com/OWASP/www-project-asvs-security-evaluation-templates-with-nuclei/archive/main.zip"
        zip_path = os.path.join(temp_dir, "asvs.zip")
        
        try:
            # Download the zip file
            print(f"Downloading ASVS templates from {zip_url}...")
            urllib.request.urlretrieve(zip_url, zip_path)
            
            # Extract the zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Find the extracted directory
            extracted_dir = None
            for item in os.listdir(temp_dir):
                if item.startswith("www-project-asvs-security-evaluation-templates-with-nuclei"):
                    extracted_dir = os.path.join(temp_dir, item)
                    break
            
            if not extracted_dir:
                return {
                    "updated": False,
                    "count": 0,
                    "error": "Could not find extracted ASVS directory",
                    "message": None
                }
            
            # Copy templates to ASVS directory
            source_templates = os.path.join(extracted_dir, "templates")
            if os.path.exists(source_templates):
                # Clear existing ASVS templates
                if os.path.exists(asvs_dir):
                    shutil.rmtree(asvs_dir)
                os.makedirs(asvs_dir, exist_ok=True)
                
                # Copy new templates
                for item in os.listdir(source_templates):
                    src = os.path.join(source_templates, item)
                    dst = os.path.join(asvs_dir, item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                
                # Register the ASVS directory
                nuclei_integration.nuclei.register_template_dir(asvs_dir, source="asvs")
                # Persist templates directory in config for stability across runs
                try:
                    cfg_set("nuclei_templates_dir", nuclei_template_dir)
                except Exception:
                    pass
                
                # Force reindex
                nuclei_integration.nuclei._index_built = False
                nuclei_integration.nuclei._build_index()
                asvs_templates = nuclei_integration.nuclei.list_templates(source="asvs", all_templates=True)
                
                return {
                    "updated": True,
                    "count": len(asvs_templates),
                    "error": None,
                    "message": f"Successfully installed {len(asvs_templates)} ASVS templates"
                }
            else:
                return {
                    "updated": False,
                    "count": 0,
                    "error": "No templates found in ASVS repository",
                    "message": None
                }
                
        finally:
            # Clean up temporary directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                
    except Exception as e:
        return {
            "updated": False,
            "count": 0,
            "error": f"Installation failed: {str(e)}",
            "message": None
        }

@bp.post("/p/<pid>/templates/install-asvs")
def install_asvs(pid: str):
    """Install ASVS templates."""
    try:
        result = install_asvs_templates()
        return {
            "success": result["updated"],
            "message": result.get("message", "ASVS installation completed"),
            "count": result["count"],
            "error": result.get("error")
        }
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

@bp.get("/p/<pid>/templates/manager")
def template_manager(pid: str):
    """Template management page."""
    try:
        from config import get as cfg_get
        templates_dir = cfg_get("nuclei_templates_dir")
    except Exception:
        templates_dir = None
    return render_template("template_manager_page.html", pid=pid, templates_dir=templates_dir)

@bp.post("/p/<pid>/templates/set-dir")
def set_templates_dir(pid: str):
    """Persist the nuclei templates directory and rebuild index."""
    try:
        from config import set as cfg_set
        from nuclei_integration import nuclei_integration
        path = request.form.get("path", "").strip()
        if not path:
            return {"success": False, "error": "Missing path"}, 400
        import os
        if not os.path.isdir(path):
            return {"success": False, "error": "Directory not found"}, 400
        cfg_set("nuclei_templates_dir", path)
        # Force wrapper to use the new path
        nuclei_integration.nuclei.template_dir = path
        nuclei_integration.nuclei._index_built = False
        nuclei_integration.nuclei._build_index()
        return {"success": True, "message": "Templates directory updated"}
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

def register_nuclei_routes(bp):
    """Register nuclei-related routes on the given blueprint."""

    @bp.get("/p/<pid>/nuclei/status")
    def nuclei_status(pid: str):
        from nuclei_integration import nuclei_integration
        try:
            status = nuclei_integration.check_nuclei_status()
            return {"success": True, "status": status}
        except Exception as e:
            return {"success": False, "error": str(e)}, 500

    @bp.post("/p/<pid>/nuclei/update-templates")
    def nuclei_update_templates(pid: str):
        from nuclei_integration import nuclei_integration
        try:
            success, message = nuclei_integration.update_templates()
            return {"success": success, "message": message}
        except Exception as e:
            return {"success": False, "error": str(e)}, 500

    @bp.get("/p/<pid>/nuclei/templates")
    def nuclei_templates(pid: str):
        from nuclei_integration import nuclei_integration
        try:
            category = request.args.get('category')
            source = request.args.get('source')
            all_flag = request.args.get('all') == '1'
            templates = nuclei_integration.nuclei.list_templates(
                category=category, source=source, all_templates=all_flag
            )
            return {"success": True, "templates": templates}
        except Exception as e:
            return {"success": False, "error": str(e)}, 500

    @bp.post("/p/<pid>/nuclei/scan")
    def nuclei_scan(pid: str):
        import logging
        import time as _t

        from nuclei_integration import nuclei_integration
        from store import (
            _endpoint_dossier_path_by_key,
            get_runtime,
            save_run,
            update_endpoint_dossier_by_key,
        )
        from utils.endpoints import endpoint_key
        try:
            templates = request.form.getlist('templates') or None
            severity = request.form.getlist('severity') or None
            exclude_patterns = request.form.getlist('exclude_patterns') or None
            # Allow client-provided run_id to keep SSE and POST in sync
            run_id = request.form.get('run_id') or f"{_t.strftime('%Y-%m-%dT%H-%M-%SZ', _t.gmtime())}-{pid[:4].upper()}"
            result = nuclei_integration.scan_project_endpoints(
                pid=pid, templates=templates, severity=severity, exclude_patterns=exclude_patterns, run_id=run_id
            )
            if result.get("success"):
                started_at = _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime())
                finished_at = _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime())
                run_doc = {
                    "run_id": run_id,
                    "started_at": started_at,
                    "finished_at": finished_at,
                    "results": [],
                    "stats": {
                        "findings": result.get("findings_count", 0),
                        "by_severity": result.get("severity_counts") or {},
                        "worst": result.get("worst_severity")
                    },
                    "artifact": result.get("artifact_path"),
                }
                try:
                    save_run(pid, run_doc)
                    # After saving run, write endpoint dossiers using queue item keys (preserve query)
                    try:
                        session, SPECS, QUEUE = get_runtime(pid)
                        summary = {
                            "run_id": run_id,
                            "started_at": started_at,
                            "finished_at": finished_at,
                            "findings": run_doc["stats"].get("findings", 0),
                            "worst": run_doc["stats"].get("worst") or "info",
                            "artifact": run_doc.get("artifact"),
                        }
                        for it in list(QUEUE or []):
                            key = it.get("key")
                            if not key:
                                # Fallback to canonical without query if key missing
                                s = SPECS.get(it.get("spec_id"))
                                if not s:
                                    continue
                                try:
                                    op = (s.get("ops") or [])[it.get("idx", -1)]
                                except Exception:
                                    op = None
                                if not op:
                                    continue
                                base = s.get("base_url") or s.get("url") or ""
                                method = (op.get("method") or "GET").upper()
                                path = op.get("path") or "/"
                                key = endpoint_key(method, base, path)
                            update_endpoint_dossier_by_key(pid, key, summary)
                            try:
                                fpath = _endpoint_dossier_path_by_key(pid, key)
                                msg = f"DOSSIER_WRITE key=\"{key}\" run=\"{run_id}\" findings={summary.get('findings',0)} worst=\"{summary.get('worst')}\" file=\"{fpath}\""
                                logging.getLogger("dossier").info(msg)
                                try:
                                    current_app.logger.info(msg)
                                except Exception:
                                    pass
                            except Exception:
                                pass
                    except Exception:
                        pass
                except Exception:
                    pass
            return {
                "success": result.get("success", False),
                "message": result.get("message"),
                "findings_count": result.get("findings_count", 0),
                "endpoints_scanned": result.get("endpoints_scanned", 0),
                "severity_counts": result.get("severity_counts"),
                "worst_severity": result.get("worst_severity"),
                "artifact_path": result.get("artifact_path"),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}, 500

    @bp.get("/p/<pid>/nuclei/stream")
    def nuclei_stream(pid: str):
        """Deterministic SSE: start, heartbeats, then done within ~10s."""
        import time as _t

        from flask import Response

        from nuclei_integration import nuclei_integration
        try:
            run_id = request.args.get('run_id') or f"{_t.strftime('%Y-%m-%dT%H-%M-%SZ', _t.gmtime())}-{pid[:4].upper()}"
            templates = request.args.getlist('templates') or None
            severity = request.args.getlist('severity') or None

            def generate():
                # Emit start immediately
                yield f"event: start\ndata: {{\"run_id\": \"{run_id}\"}}\n\n"
                # Two deterministic heartbeats ~2s total
                yield ": ping\n\n"
                _t.sleep(1)
                yield ": ping\n\n"
                # Stream scan output
                for chunk in nuclei_integration.scan_project_endpoints_stream(
                    pid=pid, templates=templates, severity=severity, exclude_patterns=None, run_id=run_id
                ):
                    if not chunk.endswith("\n\n"):
                        chunk = chunk.rstrip("\n") + "\n\n"
                    yield chunk
                # Always emit done
                yield f"event: done\ndata: {{\"run_id\": \"{run_id}\"}}\n\n"

            resp = Response(generate(), mimetype='text/event-stream')
            resp.headers['Cache-Control'] = 'no-cache, no-transform'
            resp.headers['Connection'] = 'keep-alive'
            resp.headers['X-Accel-Buffering'] = 'no'
            return resp
        except Exception as e:
            return {"success": False, "error": str(e)}, 500

    @bp.get("/p/<pid>/active-testing")
    def active_testing_page(pid: str):
        """Active Testing page with comprehensive scan configuration."""
        try:
            from findings import count_findings_cached
            from store import get_project_name
            return render_template(
                "active_testing.html",
                pid=pid,
                project_name=get_project_name(pid),
                counts=count_findings_cached(pid),
                active_nav="active_testing",
            )
        except Exception as e:
            return f"Error loading active testing page: {str(e)}", 500

    @bp.get("/p/<pid>/queue/summary")
    def queue_summary(pid: str):
        """Get summary of endpoints in queue for active testing."""
        print(f"DEBUG: queue_summary called for pid={pid}")
        try:
            from store import get_runtime
            session, SPECS, QUEUE = get_runtime(pid)
            
            # If queue is empty, get all endpoints from specs
            if not QUEUE:
                methods = set()
                endpoint_count = 0
                
                # First try specs
                for spec_id, spec in SPECS.items():
                    operations = spec.get('ops', [])
                    endpoint_count += len(operations)
                    for op in operations:
                        methods.add(op.get('method', 'GET'))
                
                # If no specs, try endpoint dossiers
                if endpoint_count == 0:
                    try:
                        import json
                        import os
                        endpoints_dir = os.path.join('ui_projects', pid, 'endpoints')
                        print(f"DEBUG: Checking endpoints dir: {endpoints_dir}")
                        print(f"DEBUG: Dir exists: {os.path.exists(endpoints_dir)}")
                        if os.path.exists(endpoints_dir):
                            files = os.listdir(endpoints_dir)
                            print(f"DEBUG: Found {len(files)} files")
                            for filename in files:
                                if filename.endswith('.json'):
                                    try:
                                        with open(os.path.join(endpoints_dir, filename), 'r') as f:
                                            dossier = json.load(f)
                                        key = dossier.get('key', '')
                                        if key:
                                            # Parse key format: "METHOD URL"
                                            parts = key.split(' ', 1)
                                            if len(parts) == 2:
                                                method = parts[0]
                                                url = parts[1]
                                                endpoint_count += 1
                                                methods.add(method)
                                                print(f"DEBUG: Added endpoint {method} {url}")
                                        else:
                                            # Try alternative format with separate method/path fields
                                            method = dossier.get('method', '')
                                            path = dossier.get('path', '')
                                            base = dossier.get('base', '')
                                            if method and path:
                                                endpoint_count += 1
                                                methods.add(method)
                                                print(f"DEBUG: Added endpoint {method} {path}")
                                    except Exception as e:
                                        print(f"DEBUG: Error with {filename}: {e}")
                                        continue
                    except Exception as e:
                        print(f"DEBUG: Error reading endpoints dir: {e}")
                        pass
                
                return {
                    "success": True,
                    "endpoint_count": endpoint_count,
                    "methods": sorted(list(methods)),
                    "specs_count": len(SPECS),
                }
            
            # Original queue logic
            methods = set()
            for item in QUEUE:
                if item.get("spec_id") in SPECS:
                    spec = SPECS[item["spec_id"]]
                    ops = spec.get("ops", [])
                    if item.get("idx") < len(ops):
                        methods.add(ops[item["idx"]].get("method", "GET"))
            return {
                "success": True,
                "endpoint_count": len(QUEUE),
                "methods": sorted(list(methods)),
                "specs_count": len(SPECS),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}, 500

    @bp.get("/p/<pid>/nuclei/profiles")
    def nuclei_profiles(pid: str):
        from store import get_profiles
        try:
            profiles = get_profiles(pid)
            return jsonify({"success": True, "profiles": profiles})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.post("/p/<pid>/nuclei/profiles")
    def nuclei_profiles_save(pid: str):
        from store import save_profile
        try:
            data = request.get_json()
            name = data.get("name")
            templates = data.get("templates", [])
            if not name:
                return jsonify({"success": False, "error": "Profile name required"}), 400
            save_profile(pid, name, templates)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.get("/p/<pid>/nuclei/profiles/<name>")
    def nuclei_profile_load(pid: str, name: str):
        from store import load_profile
        try:
            templates = load_profile(pid, name)
            return jsonify({"success": True, "templates": templates})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.delete("/p/<pid>/nuclei/profiles/<name>")
    def nuclei_profile_delete(pid: str, name: str):
        from store import delete_profile
        try:
            delete_profile(pid, name)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.post("/p/<pid>/templates/register-source")
    def register_template_source(pid: str):
        """Register a new template source directory."""
        try:
            source_path = request.form.get("path", "").strip()
            source_name = request.form.get("name", "custom")
            
            if not source_path or not os.path.isdir(source_path):
                return {"success": False, "error": "Invalid directory path"}, 400
            
            # Register the new source
            nuclei_integration.nuclei.register_template_dir(source_path, source=source_name)
            
            # Persist base nuclei templates dir
            try:
                from config import set as cfg_set
                if source_path:
                    cfg_set("nuclei_templates_dir", source_path)
            except Exception:
                pass
            
            # Get updated counts
            all_templates = nuclei_integration.nuclei.list_templates(all_templates=True)
            source_count = len([t for t in all_templates if t.get("source") == source_name])
            
            return {
                "success": True,
                "message": f"Registered {source_name} source with {source_count} templates",
                "source": {
                    "name": source_name,
                    "path": source_path,
                    "count": source_count
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}, 500

    def install_asvs_templates():
        """Install ASVS templates automatically."""
        import shutil
        import tempfile
        import urllib.request
        import zipfile
        
        try:
            # Create ASVS directory within configured nuclei templates dir
            from config import set as cfg_set
            nuclei_template_dir = nuclei_integration.nuclei.template_dir
            asvs_dir = os.path.join(nuclei_template_dir, "asvs")
            
            # Create directory if it doesn't exist
            os.makedirs(asvs_dir, exist_ok=True)
            
            # Download ASVS repository as zip file
            temp_dir = tempfile.mkdtemp(prefix="asvs_")
            zip_url = "https://github.com/OWASP/www-project-asvs-security-evaluation-templates-with-nuclei/archive/main.zip"
            zip_path = os.path.join(temp_dir, "asvs.zip")
            
            try:
                # Download the zip file
                print(f"Downloading ASVS templates from {zip_url}...")
                urllib.request.urlretrieve(zip_url, zip_path)
                
                # Extract the zip file
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Find the extracted directory
                extracted_dir = None
                for item in os.listdir(temp_dir):
                    if item.startswith("www-project-asvs-security-evaluation-templates-with-nuclei"):
                        extracted_dir = os.path.join(temp_dir, item)
                        break
                
                if not extracted_dir:
                    return {
                        "updated": False,
                        "count": 0,
                        "error": "Could not find extracted ASVS directory",
                        "message": None
                    }
                
                # Copy templates to ASVS directory
                source_templates = os.path.join(extracted_dir, "templates")
                if os.path.exists(source_templates):
                    # Clear existing ASVS templates
                    if os.path.exists(asvs_dir):
                        shutil.rmtree(asvs_dir)
                    os.makedirs(asvs_dir, exist_ok=True)
                    
                    # Copy new templates
                    for item in os.listdir(source_templates):
                        src = os.path.join(source_templates, item)
                        dst = os.path.join(asvs_dir, item)
                        if os.path.isdir(src):
                            shutil.copytree(src, dst)
                        else:
                            shutil.copy2(src, dst)
                    
                    # Register the ASVS directory
                    nuclei_integration.nuclei.register_template_dir(asvs_dir, source="asvs")
                    # Persist templates directory in config for stability across runs
                    try:
                        cfg_set("nuclei_templates_dir", nuclei_template_dir)
                    except Exception:
                        pass
                    
                    # Force reindex
                    nuclei_integration.nuclei._index_built = False
                    nuclei_integration.nuclei._build_index()
                    asvs_templates = nuclei_integration.nuclei.list_templates(source="asvs", all_templates=True)
                    
                    return {
                        "updated": True,
                        "count": len(asvs_templates),
                        "error": None,
                        "message": f"Successfully installed {len(asvs_templates)} ASVS templates"
                    }
                else:
                    return {
                        "updated": False,
                        "count": 0,
                        "error": "No templates found in ASVS repository",
                        "message": None
                    }
                    
            finally:
                # Clean up temporary directory
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    
        except Exception as e:
            return {
                "updated": False,
                "count": 0,
                "error": f"Installation failed: {str(e)}",
                "message": None
            }

    @bp.post("/p/<pid>/templates/install-asvs")
    def install_asvs(pid: str):
        """Install ASVS templates."""
        try:
            result = install_asvs_templates()
            return {
                "success": result["updated"],
                "message": result.get("message"),
                "error": result.get("error"),
                "count": result.get("count", 0),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}, 500