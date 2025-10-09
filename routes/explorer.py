import json as _json
import time as _time
from typing import Any, Dict

import requests
from flask import render_template, render_template_string, request

from utils.runtime import safe_int


def register_explorer_routes(bp):
    """Register API Explorer (operations) routes on the given blueprint."""

    @bp.post("/p/<pid>/op_details")
    def op_details(pid: str):
        from core import _files_preview_map, _json_safe, compose_display_url
        from specs import RefResolver, build_preview, op_seed
        from store import get_runtime

        session, SPECS, QUEUE = get_runtime(pid)
        spec_id = request.form.get("spec_id")
        idx_raw = request.form.get("index")
        idx = safe_int(idx_raw, 0)
        s = SPECS.get(spec_id)
        if not s:
            return "<div class='drawer'>Not found</div>"
        ops = s["ops"]
        if idx < 0 or idx >= len(ops):
            return "<div class='drawer'>Invalid index</div>"

        resolver = RefResolver(s["spec"])
        seed = op_seed(s["url"], ops[idx]["method"], ops[idx]["path"])
        pre = build_preview(s["spec"], s["base_url"], ops[idx], resolver, seed=seed, fresh=False)

        display_headers = dict(pre.get("headers") or {})
        if session.get("bearer") and "Authorization" not in display_headers:
            display_headers["Authorization"] = f"Bearer {session['bearer']}"

        display_url = compose_display_url(pre.get("url", ""), pre.get("query") or {})
        pre_safe: Dict[str, Any] = dict(pre)
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

    @bp.post("/p/<pid>/op_edit")
    def op_edit(pid: str):
        from core import _json_safe
        from specs import RefResolver, build_preview, op_seed
        from store import get_runtime

        session, SPECS, QUEUE = get_runtime(pid)
        spec_id = request.form.get("spec_id"); idx_raw = request.form.get("index")
        idx = safe_int(idx_raw, 0)
        s = SPECS.get(spec_id)
        if not s:
            return "<div class='drawer'>Not found</div>"
        ops = s["ops"]
        if idx < 0 or idx >= len(ops):
            return "<div class='drawer'>Invalid index</div>"
        resolver = RefResolver(s["spec"])
        seed = op_seed(s["url"], ops[idx]["method"], ops[idx]["path"])
        pre = build_preview(s["spec"], s["base_url"], ops[idx], resolver, seed=seed, fresh=False)
        pre_safe: Dict[str, Any] = dict(pre)
        pre_safe["query"] = _json_safe(pre.get("query"))
        pre_safe["headers"] = _json_safe(pre.get("headers"))
        pre_safe["cookies"] = _json_safe(pre.get("cookies"))
        pre_safe["json"] = _json_safe(pre.get("json"))
        pre_safe["data"] = _json_safe(pre.get("data"))
        return render_template("op_edit.html", pid=pid, sid=s["safe_id"], idx=idx, spec_id=spec_id, pre=pre_safe)

    @bp.post("/p/<pid>/op_preview_override")
    def op_preview_override(pid: str):
        from core import _json_safe
        from specs import RefResolver, build_preview, op_seed
        from store import get_runtime

        def _make_override_from_form(form) -> Dict[str, Any]:
            from core import parse_json_field
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
                if jb.strip(): body_kind = "json"
                elif fj.strip(): body_kind = "form"
                elif raw_data.strip(): body_kind = "raw"
            ov["body_kind"] = body_kind
            if ct: ov["content_type"] = ct
            if body_kind == "json":
                try: ov["json"] = _json.loads(jb) if jb.strip() else {}
                except Exception as e: ov["json"] = {"__invalid_json__": str(e), "__raw__": jb}
            elif body_kind == "form":
                from core import parse_json_field as _pf
                parsed = _pf(fj, {})
                ov["form"] = parsed if isinstance(parsed, dict) else {}
            elif body_kind == "raw":
                ov["raw"] = {"content_type": raw_ct, "data": raw_data}
            return ov

        session, SPECS, QUEUE = get_runtime(pid)
        spec_id = request.form.get("spec_id"); idx = int(request.form.get("index") or 0)
        s = SPECS.get(spec_id)
        if not s:
            return "<div class='drawer'>Not found</div>"
        resolver = RefResolver(s["spec"])
        op = s["ops"][idx]
        ov = _make_override_from_form(request.form)
        seed = op_seed(s["url"], op["method"], op["path"])
        fresh = request.form.get("fresh") == "1"
        pre = build_preview(s["spec"], s["base_url"], op, resolver, override=ov, seed=seed, fresh=fresh)
        pre_headers = dict(pre.get("headers") or {})
        if session.get("bearer") and "Authorization" not in pre_headers:
            pre_headers["Authorization"] = f"Bearer {session['bearer']}"
        pre = dict(pre); pre["headers"] = pre_headers
        display_headers = dict(pre.get("headers") or {})
        if session.get("bearer") and "Authorization" not in display_headers:
            display_headers["Authorization"] = f"Bearer {session['bearer']}"
        pre_safe: Dict[str, Any] = dict(pre)
        pre_safe["query"] = _json_safe(pre.get("query"))
        pre_safe["headers"] = _json_safe(pre.get("headers"))
        pre_safe["cookies"] = _json_safe(pre.get("cookies"))
        pre_safe["json"] = _json_safe(pre.get("json"))
        pre_safe["data"] = _json_safe(pre.get("data"))
        return render_template("op_preview.html", pre=pre_safe, headers=_json_safe(display_headers), files_map={})

    @bp.post("/p/<pid>/queue_add_override")
    def queue_add_override(pid: str):
        from store import get_runtime, persist_from_runtime

        def _make_override_from_form(form) -> Dict[str, Any]:
            from core import parse_json_field
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
                if jb.strip(): body_kind = "json"
                elif fj.strip(): body_kind = "form"
                elif raw_data.strip(): body_kind = "raw"
            ov["body_kind"] = body_kind
            if ct: ov["content_type"] = ct
            if body_kind == "json":
                try: ov["json"] = _json.loads(jb) if jb.strip() else {}
                except Exception as e: ov["json"] = {"__invalid_json__": str(e), "__raw__": jb}
            elif body_kind == "form":
                from core import parse_json_field as _pf
                parsed = _pf(fj, {})
                ov["form"] = parsed if isinstance(parsed, dict) else {}
            elif body_kind == "raw":
                ov["raw"] = {"content_type": raw_ct, "data": raw_data}
            return ov

        session, SPECS, QUEUE = get_runtime(pid)
        spec_id = request.form.get("spec_id"); idx = int(request.form.get("index") or 0)
        ov = _make_override_from_form(request.form)
        hdr = dict(ov.get("headers") or {})
        if session.get("bearer") and "Authorization" not in hdr:
            hdr["Authorization"] = f"Bearer {session['bearer']}"
        if hdr: ov["headers"] = hdr
        if spec_id in SPECS and 0 <= idx < len(SPECS[spec_id]["ops"]):
            QUEUE.append({"spec_id": spec_id, "idx": idx, "ops": SPECS[spec_id]["ops"], "override": ov})
            persist_from_runtime(pid, session, SPECS, QUEUE)
            return "<div class='drawer' style='border-color:#a7f3d0;color:#065f46;background:#ecfdf5'>Added 1 to queue.</div>"
        return "<div class='drawer'>Invalid selection</div>"

    @bp.post("/p/<pid>/send_now_override")
    def send_now_override(pid: str):
        from specs import RefResolver, build_preview, op_seed
        from store import get_runtime
        session, SPECS, QUEUE = get_runtime(pid)
        spec_id = request.form.get("spec_id"); idx = int(request.form.get("index") or 0)
        s = SPECS.get(spec_id)
        if not s:
            return "<div class='drawer'>Not found</div>"
        resolver = RefResolver(s["spec"])
        op = s["ops"][idx]
        # Reuse override builder
        def _make_override_from_form(form) -> Dict[str, Any]:
            from core import parse_json_field
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
                if jb.strip(): body_kind = "json"
                elif fj.strip(): body_kind = "form"
                elif raw_data.strip(): body_kind = "raw"
            ov["body_kind"] = body_kind
            if ct: ov["content_type"] = ct
            if body_kind == "json":
                try: ov["json"] = _json.loads(jb) if jb.strip() else {}
                except Exception as e: ov["json"] = {"__invalid_json__": str(e), "__raw__": jb}
            elif body_kind == "form":
                from core import parse_json_field as _pf
                parsed = _pf(fj, {})
                ov["form"] = parsed if isinstance(parsed, dict) else {}
            elif body_kind == "raw":
                ov["raw"] = {"content_type": raw_ct, "data": raw_data}
            return ov

        ov = _make_override_from_form(request.form)
        seed = op_seed(s["url"], op["method"], op["path"])
        pre = build_preview(s["spec"], s["base_url"], op, resolver, override=ov, seed=seed, fresh=False)
        proxies = {"http": session.get("proxy"), "https": session.get("proxy")} if session.get("proxy") else None
        if session.get("verify") is False:
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            except Exception:
                pass
        headers = dict(pre["headers"] or {})
        if session.get("bearer") and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {session['bearer']}"
        try:
            t0 = _time.time()
            resp = requests.request(
                pre["method"], pre["url"], headers=headers, params=pre.get("query") or None, cookies=pre.get("cookies") or None,
                json=pre.get("json") if pre.get("json") is not None else None, data=pre.get("data") if pre.get("data") is not None else None,
                files=pre.get("files") if pre.get("files") is not None else None, timeout=60, proxies=proxies, verify=session.get("verify", True),
            )
            elapsed = int((_time.time()-t0)*1000)
            out = {"ok": True, "status": resp.status_code, "reason": resp.reason, "url": pre["url"], "ms": elapsed}
        except Exception as e:
            out = {"ok": False, "status": "ERROR", "reason": str(e), "url": pre.get("url")}
        RES = """
<div class="drawer">
  <div><strong>{{ 'OK' if out.ok else 'ERROR' }}</strong> {{ out.status }} {{ out.reason }}</div>
  <div class="muted">{{ out.url }}</div>
</div>
"""
        return render_template_string(RES, out=out)


