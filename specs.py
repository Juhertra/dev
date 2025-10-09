from __future__ import annotations

import base64
import hashlib
import json
import os
import random
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import requests
import yaml

from core import Json

PREFERRED_CT = ["application/json", "application/x-www-form-urlencoded", "multipart/form-data"]

def load_spec_text(url: str, proxies=None, verify: bool=True, headers=None) -> str:
    import re
    if re.match(r"^https?://", url):
        r = requests.get(url, timeout=30, proxies=proxies, verify=verify, headers=headers)
        r.raise_for_status()
        return r.text
    with open(url, "r", encoding="utf-8") as f:
        return f.read()

def parse_spec(text: str) -> Json:
    # Try strict JSON first regardless of leading characters (handles BOM/whitespace)
    try:
        return json.loads(text)
    except Exception:
        # Fallback to YAML (handles OpenAPI in YAML format)
        return yaml.safe_load(text)

# -------- Extended import support (OpenAPI, Postman, HAR, Auto) --------

def _ensure_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]

def sniff_spec_kind_from_obj(obj: Any) -> str:
    try:
        if not isinstance(obj, dict):
            return "unknown"
        # OpenAPI 3 or Swagger 2
        if isinstance(obj.get("openapi"), str) or isinstance(obj.get("swagger"), str):
            return "openapi"
        # HAR format
        if isinstance(obj.get("log"), dict) and isinstance((obj.get("log") or {}).get("entries"), list):
            return "har"
        # Postman collection v2.x
        if ("item" in obj) and (isinstance(obj.get("info"), dict) or isinstance(obj.get("item"), list)):
            return "postman"
        # Swagger UI config (commonly has url or urls at top-level)
        if ("urls" in obj and isinstance(obj.get("urls"), list)) or ("url" in obj and isinstance(obj.get("url"), str)):
            return "swagger_ui_config"
        return "unknown"
    except Exception:
        return "unknown"

def sniff_spec_kind(text: str) -> str:
    try:
        obj = json.loads(text)
    except Exception:
        try:
            obj = yaml.safe_load(text)
        except Exception:
            return "unknown"
    return sniff_spec_kind_from_obj(obj)

def _add_server(doc: Dict[str, Any], base_url: str):
    if not base_url:
        return
    servers = doc.setdefault("servers", [])
    if all((s.get("url") != base_url) for s in servers if isinstance(s, dict)):
        servers.append({"url": base_url})

def _compose_url_from_postman(url_obj: Any) -> str:
    # url can be string or object
    try:
        if isinstance(url_obj, str):
            return url_obj
        if isinstance(url_obj, dict):
            raw = url_obj.get("raw")
            if isinstance(raw, str) and raw:
                return raw
            proto = url_obj.get("protocol") or "https"
            host = url_obj.get("host")
            if isinstance(host, list):
                host = ".".join([str(h) for h in host])
            path = url_obj.get("path")
            if isinstance(path, list):
                path = "/" + "/".join([str(p) for p in path])
            elif isinstance(path, str):
                if not path.startswith("/"):
                    path = "/" + path
            else:
                path = "/"
            return f"{proto}://{host}{path}"
    except Exception:
        pass
    return ""

def _iter_postman_items(items: List[Any]):
    for it in items or []:
        if isinstance(it, dict) and "item" in it:
            # folder
            for sub in _iter_postman_items(it.get("item") or []):
                yield sub
        else:
            yield it

def build_openapi_from_postman(pm: Dict[str, Any]) -> Json:
    doc: Dict[str, Any] = {"openapi": "3.0.0", "info": {"title": (pm.get("info") or {}).get("name") or "Imported Postman", "version": "converted"}, "paths": {}, "servers": []}
    items = pm.get("item") or []
    for it in _iter_postman_items(items):
        if not isinstance(it, dict):
            continue
        req = it.get("request") or {}
        method = (req.get("method") or "GET").lower()
        url = _compose_url_from_postman(req.get("url"))
        if not url:
            continue
        try:
            from urllib.parse import urlparse
            pu = urlparse(url)
            base_url = f"{pu.scheme}://{pu.netloc}"
            path = pu.path or "/"
            _add_server(doc, base_url)
            path_item = doc["paths"].setdefault(path, {})
            if method not in path_item:
                op = {"summary": it.get("name") or "", "responses": {"200": {"description": "OK"}}}
                # body detection
                body = req.get("body") or {}
                if isinstance(body, dict) and body.get("raw"):
                    op["requestBody"] = {"content": {"application/json": {"schema": {"type": "object"}}}}
                path_item[method] = op
        except Exception:
            continue
    return doc

def build_openapi_from_har(har: Dict[str, Any]) -> Json:
    doc: Dict[str, Any] = {"openapi": "3.0.0", "info": {"title": "Imported HAR", "version": "converted"}, "paths": {}, "servers": []}
    log = har.get("log") or {}
    entries = log.get("entries") or []
    for ent in entries:
        try:
            req = ent.get("request") or {}
            method = (req.get("method") or "GET").lower()
            url = req.get("url") or ""
            if not url:
                continue
            from urllib.parse import urlparse
            pu = urlparse(url)
            base_url = f"{pu.scheme}://{pu.netloc}"
            path = pu.path or "/"
            _add_server(doc, base_url)
            path_item = doc["paths"].setdefault(path, {})
            if method not in path_item:
                op = {"summary": (req.get("headers") or {}).get("Referer", ""), "responses": {"200": {"description": "OK"}}}
                # If request has postData with mimeType, mark body
                post = req.get("postData") or {}
                if isinstance(post, dict) and (post.get("text") or post.get("params")):
                    ct = (post.get("mimeType") or "application/json").split(";")[0]
                    op["requestBody"] = {"content": {ct: {"schema": {"type": "object"}}}}
                path_item[method] = op
        except Exception:
            continue
    return doc

def load_spec_from_text_or_convert(text: str, input_type: str = "auto") -> Json:
    kind = (input_type or "auto").lower()
    if kind == "openapi" or kind == "swagger":
        return parse_spec(text)
    if kind == "postman":
        obj = parse_spec(text)
        return build_openapi_from_postman(obj)
    if kind == "har":
        obj = parse_spec(text)
        return build_openapi_from_har(obj)
    # auto/raw: sniff and convert as needed
    detected = sniff_spec_kind(text)
    if detected == "openapi":
        return parse_spec(text)
    if detected == "postman":
        return build_openapi_from_postman(parse_spec(text))
    if detected == "har":
        return build_openapi_from_har(parse_spec(text))
    if detected == "swagger_ui_config":
        raise ValueError("URL returns Swagger UI config; load the 'url' from the config instead.")
    # Last resort: try parse as OpenAPI; let exceptions bubble
    return parse_spec(text)

def is_openapi3(spec: Json) -> bool:
    return bool(spec.get("openapi", "").startswith("3"))

def pick_server(spec: Json) -> str:
    if is_openapi3(spec):
        servers = spec.get("servers", []) or []
        if servers:
            return (servers[0].get("url") or "").rstrip("/")
        return ""
    schemes = spec.get("schemes", ["http"]) or ["http"]
    scheme = schemes[0]
    host = spec.get("host", "")
    base_path = spec.get("basePath", "")
    return f"{scheme}://{host}{base_path}".rstrip("/")

class RefResolver:
    def __init__(self, spec: Json):
        self.spec = spec
    def resolve(self, node: Json) -> Json:
        if not isinstance(node, dict) or "$ref" not in node:
            return node
        ref = node["$ref"]
        if not ref.startswith("#/"):
            return node
        target = self._resolve_pointer(ref[2:].split("/"))
        merged = dict(target); merged.update({k:v for k,v in node.items() if k!="$ref"})
        return merged
    def _resolve_pointer(self, parts: List[str]) -> Json:
        cur: Any = self.spec
        for p in parts:
            p = p.replace("~1", "/").replace("~0", "~")
            if isinstance(cur, dict):
                cur = cur.get(p)
            else:
                raise KeyError
            if cur is None:
                raise KeyError
        return cur

def collect_parameters(path_params: List[Json], op_params: List[Json]) -> List[Json]:
    merged: Dict[Tuple[str,str], Json] = {}
    for p in path_params + op_params:
        if not isinstance(p, dict):
            continue
        name = p.get("name"); pin = p.get("in")
        if not name or not pin:
            continue
        merged[(name, pin)] = p
    return list(merged.values())

def iter_operations(spec: Json, resolver: RefResolver) -> List[Dict[str, Any]]:
    ops: List[Dict[str,Any]] = []
    paths = spec.get("paths", {}) or {}
    for raw_path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        path_level_params = [resolver.resolve(p) for p in path_item.get("parameters", [])]
        for method in ["get","put","post","delete","options","head","patch","trace"]:
            op_obj = path_item.get(method)
            if not isinstance(op_obj, dict):
                continue
            op_obj = resolver.resolve(op_obj)
            op_params = [resolver.resolve(p) for p in op_obj.get("parameters", [])]
            params = collect_parameters(path_level_params, op_params)
            request_body = None
            if is_openapi3(spec):
                request_body = op_obj.get("requestBody")
            else:
                body_params = [p for p in params if p.get("in") == "body"]
                request_body = body_params[0] if body_params else None
                params = [p for p in params if p.get("in") != "body"]
            ops.append({
                "operationId": op_obj.get("operationId"),
                "summary": op_obj.get("summary"),
                "path": raw_path,
                "method": method.upper(),
                "hasBody": bool(request_body),
                "parameters": params,
                "requestBody": request_body,
            })
    return ops

def spec_meta(spec: Json) -> Tuple[str,str]:
    info = spec.get("info", {}) or {}
    title = info.get("title") or ("OpenAPI" if is_openapi3(spec) else "Swagger")
    return (title, info.get("version") or "")

# ---------- example generation ----------

def _rand_str(n: int = 8) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(random.choice(alphabet) for _ in range(n))

def _rand_int(minimum: Optional[int] = None, maximum: Optional[int] = None) -> int:
    if minimum is None and maximum is None: return random.randint(1, 1000)
    if minimum is None: return random.randint(max(0, int(maximum) - 100), int(maximum))
    if maximum is None: return random.randint(int(minimum), int(minimum) + 100)
    a, b = int(minimum), int(maximum)
    if a > b: a, b = b, a
    return random.randint(a, b)

def _rand_float(minimum: Optional[float] = None, maximum: Optional[float] = None) -> float:
    if minimum is None and maximum is None: return round(random.uniform(1, 1000), 3)
    if minimum is None:
        m = float(maximum); return round(random.uniform(max(0.0, m - 100.0), m), 3)
    if maximum is None:
        m = float(minimum); return round(random.uniform(m, m + 100.0), 3)
    a, b = float(minimum), float(maximum)
    if a > b: a, b = b, a
    return round(random.uniform(a, b), 3)

def gen_example(resolver: RefResolver, schema: Optional[Json]) -> Any:
    if not schema: return None
    schema = resolver.resolve(schema)
    if not isinstance(schema, dict): return None
    if "example" in schema: return schema["example"]
    if "examples" in schema:
        ex = schema["examples"]
        if isinstance(ex, list) and ex: return ex[0]
        if isinstance(ex, dict) and ex:
            val = next(iter(ex.values()))
            if isinstance(val, dict) and "value" in val: return val["value"]
            return val
    if "enum" in schema and isinstance(schema["enum"], list) and schema["enum"]: return schema["enum"][0]
    if "default" in schema: return schema["default"]
    t = schema.get("type")
    if "oneOf" in schema and isinstance(schema["oneOf"], list) and schema["oneOf"]: return gen_example(resolver, schema["oneOf"][0])
    if "anyOf" in schema and isinstance(schema["anyOf"], list) and schema["anyOf"]: return gen_example(resolver, schema["anyOf"][0])
    if "allOf" in schema and isinstance(schema["allOf"], list):
        merged = {"type":"object","properties":{}, "required":[]}
        for s in schema["allOf"]:
            s = resolver.resolve(s)
            if isinstance(s, dict) and s.get("type") == "object":
                merged["properties"].update(s.get("properties", {}))
                merged["required"] = list(set(merged["required"]) | set(s.get("required", [])))
        return gen_example(resolver, merged)
    if t == "object" or ("properties" in schema):
        props = schema.get("properties", {}) or {}
        req = set(schema.get("required", []) or [])
        obj: Dict[str, Any] = {}
        opt_count = 0
        for name, sub in props.items():
            val = gen_example(resolver, sub)
            if val is None:
                st = sub.get("type") if isinstance(sub, dict) else None
                if st == "array": val = [_rand_str()]
                elif st == "integer": val = _rand_int(sub.get("minimum"), sub.get("maximum"))
                elif st == "number": val = _rand_float(sub.get("minimum"), sub.get("maximum"))
                elif st == "boolean": val = bool(random.getrandbits(1))
                elif st == "object": val = {}
                else: val = _rand_str()
            if name in req or opt_count < 3:
                obj[name] = val
                if name not in req: opt_count += 1
        return obj
    if t == "array":
        item = gen_example(resolver, schema.get("items", {}))
        if item is None: item = _rand_str()
        return [item]
    if t == "integer": return _rand_int(schema.get("minimum"), schema.get("maximum"))
    if t == "number": return _rand_float(schema.get("minimum"), schema.get("maximum"))
    if t == "boolean": return bool(random.getrandbits(1))
    fmt = schema.get("format")
    if fmt == "date-time": return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    if fmt == "date": return date.today().isoformat()
    if fmt == "uuid": return str(uuid.uuid4())
    if fmt == "byte": return base64.b64encode(os.urandom(12)).decode()
    if fmt == "binary": return os.urandom(12)
    min_len = schema.get("minLength"); max_len = schema.get("maxLength")
    n = 8
    if isinstance(min_len, int): n = max(n, min_len)
    if isinstance(max_len, int): n = min(n, max_len) if max_len >= 1 else 1
    return _rand_str(max(1, n))

def choose_content_type(spec: Json, op: Json) -> Tuple[str, str]:
    if is_openapi3(spec):
        rb = op.get("requestBody") or {}
        rb = rb.get("content", {}) if isinstance(rb, dict) else {}
        for ct in PREFERRED_CT:
            if ct in rb: return ct, "application/json"
        if rb:
            ct = next(iter(rb.keys()))
            return ct, "application/json"
        return "", "application/json"
    consumes = op.get("consumes") or spec.get("consumes") or []
    produces = op.get("produces") or spec.get("produces") or ["application/json"]
    req_ct = ""
    for ct in PREFERRED_CT:
        if ct in consumes: req_ct = ct; break
    if not req_ct and consumes: req_ct = consumes[0]
    accept = produces[0] if produces else "application/json"
    return req_ct, accept

def op_seed(spec_url: str, method: str, path: str) -> int:
    h = hashlib.sha256(f"{spec_url}|{method}|{path}".encode()).digest()
    return int.from_bytes(h[:8], "big", signed=False)

def _with_seed(seed: Optional[int], fn):
    if seed is None:
        return fn()
    state = random.getstate()
    try:
        random.seed(seed)
        return fn()
    finally:
        random.setstate(state)

def build_preview(spec: Json, base_url: str, op: Json, resolver: RefResolver,
                  override: Optional[Dict[str, Any]]=None,
                  seed: Optional[int]=None, fresh: bool=False) -> Dict[str, Any]:
    def _build_defaults():
        path_template = op["path"]
        headers: Dict[str, str] = {}
        query: Dict[str, str] = {}
        cookies: Dict[str, str] = {}
        ct_req, accept = choose_content_type(spec, op)
        if accept: headers["Accept"] = accept

        path_params_default: Dict[str, str] = {}
        for p in op.get("parameters", []):
            p = resolver.resolve(p)
            where = p.get("in"); name = p.get("name")
            schema = p.get("schema") or p
            val = gen_example(resolver, schema)
            if val is None: val = "string"
            if where == "path":
                path_params_default[name] = str(val)
            elif where == "query":
                if isinstance(val, list): query[name] = ",".join(str(v) for v in val)
                elif isinstance(val, dict): query[name] = json.dumps(val)
                else: query[name] = str(val)
            elif where == "header":
                headers[name] = str(val)
            elif where == "cookie":
                cookies[name] = str(val)

        body = None; files = None; data = None
        if is_openapi3(spec):
            rb = op.get("requestBody")
            if isinstance(rb, dict):
                rb = resolver.resolve(rb)
                content = rb.get("content", {})
                if content:
                    ct = None
                    for pref in PREFERRED_CT:
                        if pref in content: ct = pref; break
                    if not ct: ct = next(iter(content.keys()))
                    schema = content.get(ct, {}).get("schema")
                    example = gen_example(resolver, schema)
                    if ct == "application/json":
                        body = example; headers["Content-Type"] = ct
                    elif ct == "application/x-www-form-urlencoded":
                        if isinstance(example, dict):
                            data = {k: (json.dumps(v) if isinstance(v, (dict,list)) else v) for k,v in example.items()}
                        else:
                            data = {"value": example}
                        headers["Content-Type"] = ct
                    elif ct == "multipart/form-data":
                        files = {}
                        if isinstance(example, dict):
                            for k, v in example.items():
                                if isinstance(v, (bytes, bytearray)):
                                    files[k] = (f"{k}.bin", v)
                                else:
                                    if data is None: data = {}
                                    data[k] = v if isinstance(v, (str,int,float)) else json.dumps(v)
                    else:
                        if ct == "application/octet-stream":
                            body = None; files = None
                            data = example if isinstance(example, (bytes, bytearray)) else os.urandom(12)
                            headers["Content-Type"] = ct
                        else:
                            body = example
                        headers["Content-Type"] = ct
        else:
            if op.get("requestBody"):
                schema = op["requestBody"].get("schema")
                example = gen_example(resolver, schema)
                if ct_req in ("", "application/json"):
                    body = example; headers["Content-Type"] = "application/json"
                elif ct_req == "application/x-www-form-urlencoded":
                    data = {k: (json.dumps(v) if isinstance(v, (dict,list)) else v) for k,v in (example or {}).items()} if isinstance(example, dict) else {"value": example}
                    headers["Content-Type"] = ct_req
                else:
                    body = example; headers["Content-Type"] = ct_req

        return {
            "method": op["method"],
            "base_url": base_url.rstrip("/") if base_url else "",
            "path_template": path_template,
            "path_params_default": path_params_default,
            "headers": headers, "query": query, "cookies": cookies,
            "json": body, "data": data, "files": files
        }

    def _finalize_url(pre: Dict[str, Any], merged_path_params: Dict[str, str]) -> str:
        tpl = pre["path_template"]
        for k, v in merged_path_params.items():
            tpl = tpl.replace("{"+k+"}", requests.utils.quote(str(v), safe=""))
        return (pre["base_url"] + tpl) if pre["base_url"] else tpl

    def _apply_override(prev: Dict[str, Any], ov: Dict[str, Any]) -> Dict[str, Any]:
        out = {k: (v.copy() if isinstance(v, dict) else v) for k,v in prev.items()}

        ov_path = ov.get("path_params") or {}
        merged_path = dict(out.get("path_params_default") or {})
        merged_path.update({k: str(v) for k, v in ov_path.items()})
        url = _finalize_url(out, merged_path)

        for key in ["query","headers","cookies"]:
            if key in ov and isinstance(ov[key], dict):
                merged = dict(out.get(key) or {})
                for k2, v2 in ov[key].items():
                    if v2 == "":
                        merged.pop(k2, None)
                    else:
                        merged[k2] = v2 if not isinstance(v2, (dict,list)) else json.dumps(v2)
                out[key] = merged

        ct_override = ov.get("content_type")
        body_kind = ov.get("body_kind")

        if body_kind in (None, "", "default"):
            pass
        elif body_kind == "none":
            out["json"], out["data"], out["files"] = None, None, None
            out["headers"].pop("Content-Type", None)
        elif body_kind == "json":
            out["json"], out["data"], out["files"] = ov.get("json"), None, None
            out["headers"]["Content-Type"] = ct_override or "application/json"
        elif body_kind == "form":
            form = ov.get("form") or {}
            out["json"], out["data"], out["files"] = None, form, None
            out["headers"]["Content-Type"] = ct_override or "application/x-www-form-urlencoded"
        elif body_kind == "raw":
            raw = ov.get("raw") or {}
            out["json"], out["files"] = None, None
            out["data"] = raw.get("data") or ""
            out["headers"]["Content-Type"] = ct_override or raw.get("content_type") or out["headers"].get("Content-Type","application/octet-stream")

        if ct_override and body_kind != "none":
            out["headers"]["Content-Type"] = ct_override

        out["url"] = url
        return out

    if not fresh:
        return _with_seed(seed, lambda: _apply_override(_build_defaults(), override or {}))
    return _apply_override(_build_defaults(), override or {})
