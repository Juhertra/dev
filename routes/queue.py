from typing import Any, Dict, List
from flask import render_template, request, render_template_string, redirect, url_for
from utils.rendering import render_first


def register_queue_routes(bp):
    """Register queue-related routes on the given blueprint."""

    @bp.get("/p/<pid>/queue")
    def queue_page(pid: str):
        from store import get_runtime, get_project_name
        from specs import RefResolver, op_seed, build_preview
        from core import compose_display_url, _json_safe

        session, SPECS, QUEUE = get_runtime(pid)

        def build_item(s, it, qid):
            resolver = RefResolver(s["spec"])
            op = s["ops"][it["idx"]]
            seed = op_seed(s["url"], op["method"], op["path"])
            pre = build_preview(
                s["spec"], s["base_url"], op, resolver,
                override=it.get("override"), seed=seed, fresh=False,
            )
            return {
                "qid": qid,
                "method": pre["method"],
                "url": compose_display_url(pre["url"], pre.get("query") or {}),
                "operationId": op.get("operationId") or "",
                "has_override": bool(it.get("override")),
                "preview": pre,
            }

        groups: Dict[str, Dict[str, Any]] = {}
        for i, it in enumerate(QUEUE):
            s = SPECS.get(it["spec_id"])
            if not s:
                continue
            g = groups.setdefault(
                it["spec_id"],
                {
                    "safe_id": s["safe_id"],
                    "spec_title": f"{s['title']} v{s['version']}",
                    "spec_url": s["url"],
                    "items": [],
                },
            )
            g["items"].append(build_item(s, it, i))

        groups_list = sorted(groups.items(), key=lambda kv: kv[1]["spec_title"].lower())

        return render_first(["queue.html"], pid=pid, project_name=get_project_name(pid), groups_list=groups_list, proxy=session.get("proxy"), verify=session.get("verify", True), bearer=session.get("bearer"))

    @bp.post("/p/<pid>/queue/item_details")
    def queue_item_details(pid: str):
        from store import get_runtime
        from specs import RefResolver, op_seed, build_preview
        from core import _json_safe, _files_preview_map

        session, SPECS, QUEUE = get_runtime(pid)
        try:
            qid = int(request.form.get("qid") or "-1")
        except Exception:
            return "<div class='drawer'>Invalid ID</div>"
        if qid < 0 or qid >= len(QUEUE):
            return "<div class='drawer'>Invalid ID</div>"
        it = QUEUE[qid]
        s = SPECS.get(it["spec_id"])
        if not s:
            return "<div class='drawer'>Spec removed</div>"
        resolver = RefResolver(s["spec"])
        op = s["ops"][it["idx"]]
        seed = op_seed(s["url"], op["method"], op["path"])
        pre = build_preview(s["spec"], s["base_url"], op, resolver, override=it.get("override"), seed=seed, fresh=False)

        display_headers = dict(pre.get("headers") or {})
        if session.get("bearer") and "Authorization" not in display_headers:
            display_headers["Authorization"] = f"Bearer {session['bearer']}"

        pre_safe: Dict[str, Any] = dict(pre)
        pre_safe["query"] = _json_safe(pre.get("query"))
        pre_safe["headers"] = _json_safe(pre.get("headers"))
        pre_safe["cookies"] = _json_safe(pre.get("cookies"))
        pre_safe["json"] = _json_safe(pre.get("json"))
        pre_safe["data"] = _json_safe(pre.get("data"))
        return render_first(["queue_item_details.html"], pre=pre_safe, headers=_json_safe(display_headers), files_map=_files_preview_map(pre.get("files")))

    @bp.post("/p/<pid>/queue/item-details")
    def queue_item_details_alias(pid: str):
        return queue_item_details(pid)


