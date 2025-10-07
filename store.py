from __future__ import annotations
import os, uuid, threading, time, json, logging
from typing import Any, Dict, List, Optional, Tuple
from core import read_json, write_json, safe_id, Json
from specs import load_spec_text, parse_spec, pick_server, RefResolver, iter_operations, spec_meta

ROOT = os.path.dirname(__file__)
STORE_DIR = os.path.join(ROOT, "ui_projects")
os.makedirs(STORE_DIR, exist_ok=True)
PROJECTS_INDEX = os.path.join(STORE_DIR, "projects.json")

logger = logging.getLogger(__name__)

LOCK = threading.Lock()
RUNTIMES: Dict[str, Dict[str, Any]] = {}

def list_projects() -> List[Dict[str, Any]]:
    idx = read_json(PROJECTS_INDEX, {"projects": [], "current": None})
    return idx.get("projects") or []

def get_current_project_id() -> Optional[str]:
    idx = read_json(PROJECTS_INDEX, {"projects": [], "current": None})
    return idx.get("current")

def set_current_project_id(pid: Optional[str]):
    idx = read_json(PROJECTS_INDEX, {"projects": [], "current": None})
    idx["current"] = pid
    write_json(PROJECTS_INDEX, idx)

def project_state_path(pid: str) -> str:
    return os.path.join(STORE_DIR, f"{pid}.json")

def load_project_state(pid: str) -> Dict[str, Any]:
    return read_json(project_state_path(pid), {"session":{"proxy":None,"verify":True,"bearer":None},"specs":[],"queue":[],"sends":[]})

def save_project_state(pid: str, state: Dict[str, Any]):
    write_json(project_state_path(pid), state)

def create_project(name: str) -> str:
    pid = str(uuid.uuid4())
    proj = {"id": pid, "name": name}
    idx = read_json(PROJECTS_INDEX, {"projects": [], "current": None})
    idx["projects"].append(proj)
    idx["current"] = pid
    write_json(PROJECTS_INDEX, idx)
    save_project_state(pid, {"session":{"proxy":None,"verify":True,"bearer":None},"specs":[],"queue":[],"sends":[]})
    return pid

def rename_project(pid: str, name: str):
    idx = read_json(PROJECTS_INDEX, {"projects": [], "current": None})
    for p in idx["projects"]:
        if p["id"] == pid:
            p["name"] = name
    write_json(PROJECTS_INDEX, idx)

def delete_project(pid: str):
    idx = read_json(PROJECTS_INDEX, {"projects": [], "current": None})
    idx["projects"] = [p for p in idx["projects"] if p["id"] != pid]
    if idx.get("current") == pid:
        idx["current"] = None
    write_json(PROJECTS_INDEX, idx)
    try:
        os.remove(project_state_path(pid))
    except Exception:
        pass
    RUNTIMES.pop(pid, None)

def build_runtime_from_state(state: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    session = dict(state.get("session") or {"proxy":None,"verify":True,"bearer":None})
    SPECS: Dict[str, Dict[str, Any]] = {}
    QUEUE: List[Dict[str, Any]] = []
    proxies = {"http": session.get("proxy"), "https": session.get("proxy")} if session.get("proxy") else None
    headers = {"User-Agent": "openapi-ui/1.0"}
    if session.get("bearer"):
        headers["Authorization"] = f"Bearer {session['bearer']}"
    for item in (state.get("specs") or []):
        u = item.get("url")
        if not u:
            continue
        try:
            text = load_spec_text(u, proxies=proxies, verify=session.get("verify", True), headers=headers)
            spec = parse_spec(text)
            base = pick_server(spec)
            resolver = RefResolver(spec)
            ops = iter_operations(spec, resolver)
            title, version = spec_meta(spec)
            spec_id = f"{u}|{title}|{version}"
            SPECS[spec_id] = {
                "url": u, "title": title, "version": version, "base_url": base,
                "ops": ops, "spec": spec, "safe_id": safe_id(spec_id)
            }
        except Exception as e:
            pass
    
    for q in (state.get("queue") or []):
        su = q.get("spec_url"); method = q.get("method"); path = q.get("path")
        sid = next((k for k,v in SPECS.items() if v["url"] == su), None)
        if not sid:
            continue
        idx = next((i for i, op in enumerate(SPECS[sid]["ops"]) if op["method"] == method and op["path"] == path), None)
        if idx is None:
            continue
        QUEUE.append({"spec_id": sid, "idx": idx, "ops": SPECS[sid]["ops"], "override": q.get("override")})
    return session, SPECS, QUEUE

def persist_from_runtime(pid: str, session: Dict[str, Any], SPECS: Dict[str, Dict[str, Any]], QUEUE: List[Dict[str, Any]]):
    existing = load_project_state(pid)
    state = {
        "session": session,
        "specs": [{"url": v["url"]} for v in SPECS.values()],
        "queue": [{
            "spec_url": SPECS[q["spec_id"]]["url"] if q["spec_id"] in SPECS else None,
            "method":   SPECS[q["spec_id"]]["ops"][q["idx"]]["method"] if q["spec_id"] in SPECS else None,
            "path":     SPECS[q["spec_id"]]["ops"][q["idx"]]["path"]   if q["spec_id"] in SPECS else None,
            "override": q.get("override")
        } for q in QUEUE if q.get("spec_id") in SPECS],
        "sends": existing.get("sends") or []
    }
    save_project_state(pid, state)
    
    # Phase 4: Invalidate cache when specs change
    try:
        from cache import invalidate_cache
        invalidate_cache(f"build_site_map:('{pid}',)")
    except ImportError:
        pass  # Cache module not available

def append_send_log(pid: str, entry: Dict[str, Any], max_entries: int = 500):
    """Append one send log entry and persist. Keeps history capped."""
    state = load_project_state(pid)
    sends = state.get("sends") or []
    sends.append(entry)
    if len(sends) > max_entries:
        sends = sends[-max_entries:]
    state["sends"] = sends
    save_project_state(pid, state)

def get_sends(pid: str) -> List[Dict[str, Any]]:
    return (load_project_state(pid).get("sends") or [])

def clear_sends(pid: str):
    state = load_project_state(pid)
    state["sends"] = []
    save_project_state(pid, state)

def ensure_runtime(pid: str):
    with LOCK:
        if pid not in RUNTIMES:
            state = load_project_state(pid)
            session, specs, queue = build_runtime_from_state(state)
            RUNTIMES[pid] = {"session": session, "specs": specs, "queue": queue}

def get_runtime(pid: str):
    ensure_runtime(pid)
    d = RUNTIMES[pid]
    return d["session"], d["specs"], d["queue"]

def get_project_name(pid: str) -> str:
    for p in list_projects():
        if p["id"] == pid:
            return p["name"]
    return "Project"

# ---------- Template Profile Storage ----------

def _profiles_path(pid: str) -> str:
    """Get the path to the profiles file for a project."""
    return os.path.join(STORE_DIR, pid, "profiles.json")

def get_profiles(pid: str) -> List[Dict[str, Any]]:
    """Get list of saved template profiles for a project."""
    p = _profiles_path(pid)
    if not os.path.exists(p):
        return []
    
    try:
        data = read_json(p, {})
        return [{"name": k, "count": len(v)} for k, v in data.items()]
    except Exception:
        return []

def save_profile(pid: str, name: str, templates: List[str]) -> None:
    """Save a template profile for a project."""
    p = _profiles_path(pid)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(p), exist_ok=True)
    
    # Load existing profiles
    data = {}
    if os.path.exists(p):
        try:
            data = read_json(p, {})
        except Exception:
            data = {}
    
    # Update with new profile (dedupe and keep order)
    data[name] = list(dict.fromkeys(templates))
    
    # Save back
    write_json(p, data)

def load_profile(pid: str, name: str) -> List[str]:
    """Load a specific template profile for a project."""
    p = _profiles_path(pid)
    if not os.path.exists(p):
        return []
    
    try:
        data = read_json(p, {})
        return data.get(name, [])
    except Exception:
        return []

def delete_profile(pid: str, name: str) -> None:
    """Delete a template profile for a project."""
    p = _profiles_path(pid)
    if not os.path.exists(p):
        return
    
    try:
        data = read_json(p, {})
        if name in data:
            del data[name]
            write_json(p, data)
    except Exception:
        pass

def get_project_dir(pid: str) -> str:
    """Get the project directory path."""
    return os.path.join(STORE_DIR, pid)

def _runs_path(pid: str) -> str:
    """Get the path to the runs.json file for a project."""
    project_dir = get_project_dir(pid)
    os.makedirs(project_dir, exist_ok=True)
    return os.path.join(project_dir, "runs.json")

def append_run(pid: str, run: Dict[str, Any]):
    """Append a scan run to the project's run history."""
    path = _runs_path(pid)
    runs = []
    if os.path.exists(path):
        try:
            runs = read_json(path, [])
        except Exception:
            runs = []
    runs.append(run)
    
    # Validate against schema before writing (Phase 4A)
    try:
        from utils.schema_validation import validate_json
        if not validate_json(runs, "runs.schema.json", f"runs_append_{pid}"):
            logger.warning(f"RUNS_SCHEMA_VALIDATION_FAIL pid={pid}")
            return
    except Exception as e:
        logger.warning(f"RUNS_SCHEMA_VALIDATION_ERROR pid={pid} error={str(e)}")
    
    write_json(path, runs)
    
    # Bust vulns summary cache (Phase 4A)
    _bust_vulns_cache(pid)

def list_runs(pid: str, limit: int | None = None) -> List[Dict[str, Any]]:
    """Get the list of scan runs for a project.

    Prefer reading individual run documents under runs/ directory and sort by
    finished_at/start time if available. Fall back to runs.json if present.
    """
    runs_dir = os.path.join(get_project_dir(pid), "runs")
    items: List[Dict[str, Any]] = []
    try:
        if os.path.isdir(runs_dir):
            for name in os.listdir(runs_dir):
                if not name.endswith(".json"):
                    continue
                fp = os.path.join(runs_dir, name)
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        doc = json.load(f)
                        if isinstance(doc, dict):
                            items.append(doc)
                except Exception:
                    continue
            # Sort newest first by finished_at then started_at then filename
            def _key(d: Dict[str, Any]):
                return (
                    str(d.get("finished_at") or ""),
                    str(d.get("started_at") or ""),
                    str(d.get("run_id") or ""),
                )
            items.sort(key=_key, reverse=True)
            if isinstance(limit, int):
                return items[:limit]
            return items
    except Exception:
        items = []
    # Fallback: legacy runs.json
    path = _runs_path(pid)
    if not os.path.exists(path):
        return items
    try:
        data = read_json(path, [])
        if not isinstance(data, list):
            return items
        if isinstance(limit, int):
            return data[:limit]
        return data
    except Exception:
        return items

def make_run_id() -> str:
    """Generate a unique run ID."""
    return time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime()) + "-%04X" % int(time.time()*1000 % 0xFFFF)

def endpoint_id(base: str, method: str, path: str) -> str:
    """Generate a unique endpoint ID."""
    import hashlib
    key = f"{base}|{method}|{path}"
    return hashlib.sha1(key.encode()).hexdigest()[:16]

def save_run(pid: str, run_doc: Dict[str, Any]):
    """Save a complete run document."""
    ensure_dirs(pid)
    with open(os.path.join(get_project_dir(pid), "runs", f"{run_doc['run_id']}.json"), "w") as f:
        json.dump(run_doc, f, indent=2)

def load_run(pid: str, run_id: str) -> Dict[str, Any]:
    """Load a specific run document."""
    with open(os.path.join(get_project_dir(pid), "runs", f"{run_id}.json")) as f:
        return json.load(f)

def update_endpoint_dossier(pid: str, base: str, method: str, path: str, run_summary: Dict[str, Any]):
    """Update endpoint dossier with run summary."""
    ensure_dirs(pid)
    eid = endpoint_id(base, method, path)
    dossier_path = os.path.join(get_project_dir(pid), "endpoints", f"{eid}.json")
    
    if os.path.exists(dossier_path):
        with open(dossier_path) as f: 
            doc = json.load(f)
    else:
        doc = {
            "endpoint_id": eid, 
            "base": base, 
            "method": method, 
            "path": path,
            "first_seen": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "runs": [], 
            "totals": {"findings": 0, "by_severity": {}}
        }

    doc["last_seen"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    doc["runs"].insert(0, run_summary)  # newest first

    # Roll up totals
    sevmap = doc["totals"].setdefault("by_severity", {})
    doc["totals"]["findings"] += run_summary.get("findings", 0)
    for k, v in run_summary.get("by_severity", {}).items():
        sevmap[k] = sevmap.get(k, 0) + v
    doc["last_run"] = {
        "run_id": run_summary["run_id"], 
        "at": run_summary.get("finished_at"),
        "summary": {
            "findings": run_summary.get("findings", 0),
            "worst": run_summary.get("worst", "info")
        }
    }
    with open(dossier_path, "w") as f:
        json.dump(doc, f, indent=2)

def get_endpoint_runs(pid: str, base: str, method: str, path: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get runs for a specific endpoint."""
    eid = endpoint_id(base, method, path)
    dossier_path = os.path.join(get_project_dir(pid), "endpoints", f"{eid}.json")
    if not os.path.exists(dossier_path): 
        return []
    with open(dossier_path) as f: 
        doc = json.load(f)
    return doc.get("runs", [])[:limit]

# === By-key helpers (canonical key: base|METHOD|/path) ===
from utils.endpoints import endpoint_key
import hashlib

def _pj(pid, *parts):
    return os.path.join(STORE_DIR, pid, *parts)

def _endpoint_dossier_path_by_key(pid: str, key: str) -> str:
    # Use safe canonical filename (not hash) so proof paths match expectations
    from utils.endpoints import endpoint_safe_key as _esk  # local import to avoid cycles
    return _pj(pid, "endpoints", f"{_esk(key)}.json")

def update_endpoint_dossier_by_key(pid: str, key: str, run_summary: Dict[str, Any]):
    ensure_dirs(pid)
    path = _endpoint_dossier_path_by_key(pid, key)
    if os.path.exists(path):
        with open(path) as f:
            doc = json.load(f)
    else:
        try:
            base, method, path_only = key.split("|", 2)
        except Exception:
            base, method, path_only = "", "GET", "/"
        doc = {
            "endpoint_id": key,
            "base": base,
            "method": method,
            "path": path_only,
            "first_seen": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "runs": [],
            "totals": {"findings": 0, "by_severity": {}},
        }
    doc["last_seen"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    doc["runs"].insert(0, run_summary)
    doc["totals"]["findings"] += run_summary.get("findings", 0)
    sevmap = doc["totals"].setdefault("by_severity", {})
    for k, v in (run_summary.get("by_severity", {}) or {}).items():
        sevmap[k] = sevmap.get(k, 0) + int(v or 0)
    doc["last_run"] = {
        "run_id": run_summary.get("run_id"),
        "at": run_summary.get("finished_at"),
        "summary": {"findings": run_summary.get("findings", 0), "worst": run_summary.get("worst")},
    }
    with open(path, "w") as f:
        json.dump(doc, f, indent=2)

def get_endpoint_runs_by_key(pid: str, key: str, limit: int = 15) -> List[Dict[str, Any]]:
    path = _endpoint_dossier_path_by_key(pid, key)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        doc = json.load(f)
    return (doc.get("runs") or [])[:limit]

# --- Canonical key helpers (preserve existing API; add by-key variants) ---
def update_endpoint_dossier_by_key(pid: str, key: str, run_summary: Dict[str, Any]):
    try:
        # key format: "METHOD base/path"
        sp = key.split(" ", 1)
        if len(sp) != 2:
            return update_endpoint_dossier(pid, "", "GET", "/", run_summary)
        method = sp[0]
        rest = sp[1]
        # Split base and path by first slash after scheme://host
        # We assume rest already normalized like https://host/path
        import re
        m = re.match(r"^(https?://[^/]+)(/.*)?$", rest)
        if m:
            base = m.group(1)
            path = m.group(2) or "/"
        else:
            base, path = rest, "/"
        return update_endpoint_dossier(pid, base, method, path, run_summary)
    except Exception:
        return update_endpoint_dossier(pid, "", "GET", "/", run_summary)

def get_endpoint_runs_by_key(pid: str, key: str, limit: int = 10) -> List[Dict[str, Any]]:
    try:
        sp = key.split(" ", 1)
        if len(sp) != 2:
            return []
        method = sp[0]
        rest = sp[1]
        import re
        m = re.match(r"^(https?://[^/]+)(/.*)?$", rest)
        if m:
            base = m.group(1)
            path = m.group(2) or "/"
        else:
            base, path = rest, "/"
        return get_endpoint_runs(pid, base, method, path, limit=limit)
    except Exception:
        return []

def ensure_dirs(pid: str):
    """Ensure project directories exist."""
    os.makedirs(os.path.join(get_project_dir(pid), "runs"), exist_ok=True)
    os.makedirs(os.path.join(get_project_dir(pid), "endpoints"), exist_ok=True)

# === By-key dossier helpers (canonical key) ===
import re as _re
from utils.endpoints import endpoint_key as _endpoint_key

def _safe_filename(s: str) -> str:
    return _re.sub(r"[^A-Za-z0-9._-]+", "_", s)

def _endpoint_dossier_path_by_key(pid: str, key: str) -> str:
    ensure_dirs(pid)
    # Use safe canonical filename (not hash) so proof paths match expectations
    from utils.endpoints import endpoint_safe_key as _esk
    return os.path.join(get_project_dir(pid), "endpoints", f"{_esk(key)}.json")

def update_endpoint_dossier_by_key(pid: str, key: str, run_summary: Dict[str, Any]) -> None:
    path = _endpoint_dossier_path_by_key(pid, key)
    data: Dict[str, Any] = {"key": key, "runs": []}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f) or data
        except Exception:
            pass
    # Normalize entry shape to what UI expects
    entry: Dict[str, Any] = dict(run_summary or {})
    sev_counts: Dict[str, int] = entry.get("severity_counts") or entry.get("by_severity") or {}
    if "findings" not in entry:
        try:
            entry["findings"] = int(sum(int(v or 0) for v in sev_counts.values()))
        except Exception:
            entry["findings"] = entry.get("findings_count", 0) or 0
    if not entry.get("worst"):
        order = ["critical","high","medium","low","info"]
        worst = None
        for s in order:
            if int(sev_counts.get(s, 0) or 0) > 0:
                worst = s
                break
        entry["worst"] = worst or "info"
    if not entry.get("finished_at"):
        entry["finished_at"] = entry.get("started_at")

    existing = {r.get("run_id"): r for r in (data.get("runs") or [])}
    existing[entry.get("run_id")] = entry
    data["runs"] = sorted(existing.values(), key=lambda r: r.get("started_at", ""), reverse=True)
    
    # Validate against schema before writing (Phase 4A)
    try:
        from utils.schema_validation import validate_json
        if not validate_json(data, "dossier.schema.json", f"dossier_update_{pid}_{key}"):
            logger.warning(f"DOSSIER_SCHEMA_VALIDATION_FAIL pid={pid} key={key}")
            return
    except Exception as e:
        logger.warning(f"DOSSIER_SCHEMA_VALIDATION_ERROR pid={pid} key={key} error={str(e)}")
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    # Log dossier write (Phase 4A)
    worst_sev = entry.get("worst", "info")
    findings_count = entry.get("findings", 0)
    logger.info(f"DOSSIER_WRITE key=\"{key}\" worst=\"{worst_sev}\" findings={findings_count}")
    
    # Bust vulns summary cache (Phase 4A)
    _bust_vulns_cache(pid)

def get_endpoint_runs_by_key(pid: str, key: str, limit: int | None = None) -> List[Dict[str, Any]]:
    path = _endpoint_dossier_path_by_key(pid, key)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f) or {}
            runs = d.get("runs", [])
            if isinstance(limit, int):
                return runs[:limit]
            return runs
    except Exception:
        return []

def _bust_vulns_cache(pid: str) -> None:
    """Bust the vulnerabilities summary cache for a project (Phase 4A)."""
    try:
        summary_file = os.path.join("ui_projects", pid, "indexes", "vulns_summary.json")
        if os.path.exists(summary_file):
            os.remove(summary_file)
            logger.info(f"VULNS_CACHE_BUST pid={pid}")
        else:
            logger.info(f"VULNS_CACHE_BUST pid={pid} (no cache file)")
        
        # Also rebuild metrics cache (P6)
        try:
            from analytics_core.analytics import rebuild_metrics_cache
            rebuild_metrics_cache(pid)
        except ImportError:
            logger.debug(f"METRICS_REBUILD_SKIP pid={pid} (analytics not available)")
        except Exception as e:
            logger.warning(f"METRICS_REBUILD_ERROR pid={pid} error={str(e)}")
            
    except Exception as e:
        logger.warning(f"VULNS_CACHE_BUST_ERROR pid={pid} error={str(e)}")
