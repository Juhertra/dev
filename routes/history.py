from typing import Any, Dict, List, Optional
from flask import render_template_string, request, redirect, url_for


def register_history_routes(bp):
    """Register sends/history routes on the given blueprint."""

    @bp.get("/p/<pid>/sends")
    def sends_page(pid: str):
        from store import get_runtime, get_project_name
        from store import get_sends
        rows = list(reversed(get_sends(pid)))

        # Filters
        m = (request.args.get("method") or "").strip().upper()
        url_sub = (request.args.get("url") or "").strip()
        status_kind = (request.args.get("status_kind") or "any").lower()

        def _as_int(x: Optional[str]) -> Optional[int]:
            try:
                return int(x) if x not in (None, "") else None
            except Exception:
                return None

        s_from = _as_int(request.args.get("status_from"))
        s_to = _as_int(request.args.get("status_to"))
        ms_min = _as_int(request.args.get("ms_min"))
        ms_max = _as_int(request.args.get("ms_max"))
        sz_min = _as_int(request.args.get("size_min"))
        sz_max = _as_int(request.args.get("size_max"))

        def _keep(r: Dict[str, Any]) -> bool:
            if m and (str(r.get("method") or "").upper() != m):
                return False
            if url_sub and (url_sub.lower() not in str(r.get("url") or "").lower()):
                return False
            if status_kind == "ok" and not r.get("ok"):
                return False
            if status_kind == "error" and r.get("ok"):
                return False
            st = r.get("status")
            try:
                st_i = int(st)
            except Exception:
                st_i = None
            if s_from is not None and (st_i is None or st_i < s_from):
                return False
            if s_to is not None and (st_i is None or st_i > s_to):
                return False
            ms = r.get("ms")
            if ms_min is not None and (ms is None or int(ms) < ms_min):
                return False
            if ms_max is not None and (ms is None or int(ms) > ms_max):
                return False
            sz = r.get("size")
            if sz_min is not None and (sz is None or int(sz) < sz_min):
                return False
            if sz_max is not None and (sz is None or int(sz) > sz_max):
                return False
            return True

        rows = [r for r in rows if _keep(r)]

        # Human-readable timestamps
        import datetime
        for r in rows:
            if 'ts' in r and isinstance(r['ts'], (int, float)):
                try:
                    dt = datetime.datetime.fromtimestamp(r['ts'] / 1000 if r['ts'] > 1e10 else r['ts'])
                    r['ts'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    pass

        T = """
{% extends "_layout.html" %}
{% set active_nav = 'history' %}

{% block page_title %}History{% endblock %}

{% block breadcrumbs %}
  {{ super() }}
  <span class="sep">›</span>
  <span>History</span>
{% endblock %}

{% block content %}
    <div class="card">
      <form method="get" class="row" style="gap:10px;align-items:flex-end;flex-wrap:wrap">
        <div>
          <div class="muted">Method</div>
          <select name="method">
            <option value="">Any</option>
            {% for mm in ['GET','POST','PUT','DELETE','PATCH'] %}
              <option value="{{ mm }}" {% if request.args.get('method','').upper()==mm %}selected{% endif %}>{{ mm }}</option>
            {% endfor %}
          </select>
        </div>
        <div>
          <div class="muted">URL contains</div>
          <input type="text" name="url" value="{{ request.args.get('url','') }}">
        </div>
        <div>
          <div class="muted">Kind</div>
          <select name="status_kind">
            {% set sk=request.args.get('status_kind','any') %}
            <option value="any" {% if sk=='any' %}selected{% endif %}>Any</option>
            <option value="ok" {% if sk=='ok' %}selected{% endif %}>OK only</option>
            <option value="error" {% if sk=='error' %}selected{% endif %}>ERROR only</option>
          </select>
        </div>
        <div>
          <div class="muted">Status from/to</div>
          <div class="row"><input style="width:120px" type="text" name="status_from" value="{{ request.args.get('status_from','') }}"><input style="width:120px" type="text" name="status_to" value="{{ request.args.get('status_to','') }}"></div>
        </div>
        <div>
          <div class="muted">ms min/max</div>
          <div class="row"><input style="width:120px" type="text" name="ms_min" value="{{ request.args.get('ms_min','') }}"><input style="width:120px" type="text" name="ms_max" value="{{ request.args.get('ms_max','') }}"></div>
        </div>
        <div>
          <div class="muted">size min/max</div>
          <div class="row"><input style="width:120px" type="text" name="size_min" value="{{ request.args.get('size_min','') }}"><input style="width:120px" type="text" name="size_max" value="{{ request.args.get('size_max','') }}"></div>
        </div>
        <div class="row" style="gap:8px">
          <button class="btn primary" type="submit">Apply</button>
          <a class="btn ghost" href="{{ url_for('web.sends_page', pid=pid) }}">Reset</a>
        </div>
      </form>
      <div class="row" style="gap:8px;margin-top:8px;align-items:center">
        <form method="post" action="{{ url_for('web.sends_clear', pid=pid) }}" style="display:inline;margin:0">
          <button class="btn ghost" type="submit">Clear</button>
        </form>
      </div>
      <div class="row" style="justify-content:space-between;margin-top:8px"><div class="muted">Total: {{ rows|length }}</div></div>
      <table>
        <thead><tr><th>#</th><th>Time</th><th>Status</th><th>ms</th><th>Size</th><th>Method</th><th>URL</th><th>Detail</th></tr></thead>
        <tbody>
        {% for r in rows %}
          <tr>
            <td>{{ loop.index }}</td>
            <td class="muted">{{ r.ts }}</td>
            <td class="{{ 'ok' if r.ok else 'err' }}">{{ r.status }}</td>
            <td>{{ r.ms or '' }}</td>
            <td>{{ r.size or '' }}</td>
            <td><span class="chip {{ r.method }}">{{ r.method }}</span></td>
            <td style="word-break:break-word">{{ r.url }}</td>
            <td class="muted">{{ r.detail or '' }}</td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
{% endblock %}
"""
        from flask import make_response
        from store import get_project_name
        response = make_response(render_template_string(T, pid=pid, project_name=get_project_name(pid), rows=rows))
        # Disable caching for this page
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    @bp.post("/p/<pid>/sends/clear")
    def sends_clear(pid: str):
        from store import clear_sends
        clear_sends(pid)
        import time as _t
        return redirect(url_for("web.sends_page", pid=pid, _t=int(_t.time())))

    # Aliases
    @bp.get("/p/<pid>/history")
    def history_page(pid: str):
        return sends_page(pid)

    @bp.post("/p/<pid>/history/clear")
    def history_clear(pid: str):
        return sends_clear(pid)


