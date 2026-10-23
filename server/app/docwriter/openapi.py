"""API reference straight from her OpenAPI file (Swagger 2.0 / OpenAPI 3.0 / 3.1 / 3.2), by code: no model, so nothing is
invented. Each operation is one doc part (`op:GET /orders/{id}`) with a hash, so a changed endpoint makes its section stale."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

METHODS = ("get", "post", "put", "patch", "delete", "head", "options", "query")


class OpenApiError(ValueError):
    pass


def load(data: bytes | str) -> dict[str, Any]:
    text = data.decode("utf-8", "replace") if isinstance(data, bytes) else data
    if len(text) > 3_000_000:
        raise OpenApiError("OpenAPI file 3 MB se badi hai")
    doc: Any = None
    try:
        doc = json.loads(text)
    except ValueError:
        try:
            import yaml
            doc = yaml.safe_load(text)
        except Exception as e:
            raise OpenApiError(f"OpenAPI file padh nahi paya: {e.__class__.__name__}")
    if not isinstance(doc, dict) or not (doc.get("openapi") or doc.get("swagger")) or not isinstance(doc.get("paths"), dict):
        raise OpenApiError("Yeh OpenAPI / Swagger file nahi lagti (openapi / swagger + paths chahiye)")
    return doc


def _ref(doc: dict, node: Any, depth: int = 0) -> Any:
    if isinstance(node, dict) and "$ref" in node and isinstance(node["$ref"], str) and node["$ref"].startswith("#/") and depth < 8:
        cur: Any = doc
        for p in node["$ref"][2:].split("/"):
            p = p.replace("~1", "/").replace("~0", "~")
            cur = cur.get(p) if isinstance(cur, dict) else None
            if cur is None:
                return node
        return _ref(doc, cur, depth + 1)
    return node


def _schema_line(doc: dict, sch: Any, depth: int = 0) -> str:
    sch = _ref(doc, sch)
    if not isinstance(sch, dict) or depth > 2:
        return "object"
    t = sch.get("type")
    if isinstance(t, list):
        t = "|".join(str(x) for x in t)
    if t == "array":
        return f"array of {_schema_line(doc, sch.get('items'), depth + 1)}"
    if sch.get("enum"):
        return f"{t or 'value'} ({', '.join(str(x) for x in sch['enum'][:8])})"
    if sch.get("format"):
        return f"{t or 'string'} ({sch['format']})"
    for k in ("oneOf", "anyOf", "allOf"):
        if sch.get(k):
            return f" {k} ".join(_schema_line(doc, s, depth + 1) for s in sch[k][:4])
    return str(t or "object")


def _fields(doc: dict, sch: Any) -> list[dict[str, str]]:
    sch = _ref(doc, sch)
    if not isinstance(sch, dict):
        return []
    if sch.get("allOf"):
        out = []
        for s in sch["allOf"]:
            out += _fields(doc, s)
        return out[:40]
    req = set(sch.get("required") or [])
    return [{"name": n, "type": _schema_line(doc, p), "required": "yes" if n in req else "",
             "about": _one(( _ref(doc, p) or {}).get("description") if isinstance(_ref(doc, p), dict) else "")}
            for n, p in list((sch.get("properties") or {}).items())[:40]]


def _one(s: Any, n: int = 160) -> str:
    return " ".join(str(s or "").split())[:n]


def operations(doc: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    v2 = bool(doc.get("swagger"))
    gsec = doc.get("security")
    for path, item in doc["paths"].items():
        item = _ref(doc, item)
        if not isinstance(item, dict):
            continue
        shared = item.get("parameters") or []
        for m in METHODS:
            op = item.get(m)
            if not isinstance(op, dict):
                continue
            params = []
            body = None
            for p in list(shared) + list(op.get("parameters") or []):
                p = _ref(doc, p)
                if not isinstance(p, dict):
                    continue
                if v2 and p.get("in") == "body":
                    body = {"type": "application/json", "fields": _fields(doc, p.get("schema")), "schema": _schema_line(doc, p.get("schema"))}
                    continue
                params.append({"name": str(p.get("name") or ""), "in": str(p.get("in") or ""), "required": bool(p.get("required")),
                               "type": _schema_line(doc, p.get("schema") or p), "about": _one(p.get("description"))})
            rb = _ref(doc, op.get("requestBody"))
            if isinstance(rb, dict) and isinstance(rb.get("content"), dict) and rb["content"]:
                ct, cv = next(iter(rb["content"].items()))
                sch = (cv or {}).get("schema")
                body = {"type": ct, "fields": _fields(doc, sch), "schema": _schema_line(doc, sch), "required": bool(rb.get("required"))}
            resps = []
            for code, r in (op.get("responses") or {}).items():
                r = _ref(doc, r)
                if isinstance(r, dict):
                    sch = None
                    if isinstance(r.get("content"), dict) and r["content"]:
                        sch = (next(iter(r["content"].values())) or {}).get("schema")
                    elif r.get("schema"):
                        sch = r["schema"]
                    resps.append({"code": str(code), "about": _one(r.get("description")), "schema": _schema_line(doc, sch) if sch else ""})
            sec = op.get("security", gsec)
            auth = sorted({k for s in (sec or []) if isinstance(s, dict) for k in s})
            key = f"op:{m.upper()} {path}"
            raw = json.dumps({"p": path, "m": m, "op": op, "shared": shared}, sort_keys=True, default=str)
            out.append({"id": key, "method": m.upper(), "path": path, "summary": _one(op.get("summary"), 120),
                        "about": _one(op.get("description"), 600), "tags": [str(t) for t in (op.get("tags") or [])][:3],
                        "params": params[:30], "body": body, "responses": resps[:12], "auth": auth,
                        "deprecated": bool(op.get("deprecated")), "hash": hashlib.sha256(raw.encode()).hexdigest()[:16]})
    return out


def info(doc: dict[str, Any]) -> dict[str, Any]:
    i = doc.get("info") or {}
    servers = [str(s.get("url")) for s in (doc.get("servers") or []) if isinstance(s, dict) and s.get("url")][:3]
    if doc.get("host"):
        servers = [f"{(doc.get('schemes') or ['https'])[0]}://{doc['host']}{doc.get('basePath') or ''}"]
    schemes = {}
    for n, s in (((doc.get("components") or {}).get("securitySchemes")) or doc.get("securityDefinitions") or {}).items():
        if isinstance(s, dict):
            schemes[n] = " ".join(x for x in (str(s.get("type") or ""), str(s.get("scheme") or ""), str(s.get("in") or ""),
                                                str(s.get("name") or "")) if x)
    return {"title": _one(i.get("title"), 120), "version": _one(i.get("version"), 40), "about": _one(i.get("description"), 800),
            "spec": str(doc.get("openapi") or doc.get("swagger")), "servers": servers, "auth": schemes}


def _cell(s: Any) -> str:
    return str(s or "").replace("|", "\\|").replace("\n", " ")


def op_markdown(op: dict[str, Any], auth_names: dict[str, str] | None = None) -> str:
    """One endpoint as reference Markdown (code-made, so it never says more than the file)."""
    lines = [f"`{op['method']} {op['path']}`", ""]
    if op.get("deprecated"):
        lines += ["> **Deprecated.** Is endpoint ki jagah naya endpoint use kijiye.", ""]
    if op.get("summary"):
        lines.append(op["summary"] + ("" if op["summary"].endswith(".") else "."))
    if op.get("about") and op["about"] != op.get("summary"):
        lines += ["", op["about"]]
    if op.get("auth"):
        lines += ["", "**Auth:** " + ", ".join(f"{a} ({(auth_names or {}).get(a, '')})".replace(" ()", "") for a in op["auth"])]
    if op.get("params"):
        lines += ["", "**Parameters**", "", "| Name | In | Type | Required | Description |", "|---|---|---|---|---|"]
        for p in op["params"]:
            lines.append(f"| `{_cell(p['name'])}` | {_cell(p['in'])} | {_cell(p['type'])} | {'yes' if p['required'] else ''} | {_cell(p['about'])} |")
    if op.get("body"):
        b = op["body"]
        lines += ["", f"**Request body** ({b['type']}{', required' if b.get('required') else ''})"]
        if b.get("fields"):
            lines += ["", "| Field | Type | Required | Description |", "|---|---|---|---|"]
            for f in b["fields"]:
                lines.append(f"| `{_cell(f['name'])}` | {_cell(f['type'])} | {f['required']} | {_cell(f['about'])} |")
        else:
            lines.append(f"Body: {b.get('schema')}")
    if op.get("responses"):
        lines += ["", "**Responses**", "", "| Code | Meaning | Body |", "|---|---|---|"]
        for r in op["responses"]:
            lines.append(f"| {_cell(r['code'])} | {_cell(r['about'])} | {_cell(r['schema'])} |")
    return "\n".join(lines)


def title_of(op: dict[str, Any]) -> str:
    return op.get("summary") or f"{op['method']} {op['path']}"


def find_files(paths: list[str]) -> list[str]:
    rx = re.compile(r"(^|/)(openapi|swagger|api)[\w.-]*\.(json|ya?ml)$", re.I)
    return [p for p in paths if rx.search(p) and "node_modules/" not in p][:5]
