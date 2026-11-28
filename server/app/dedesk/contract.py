"""A table's schema checked against its contract - the shape downstream readers rely on. Reads CREATE TABLE statements (any
common SQL dialect), JSON Schema, Avro records, dbt / YAML column lists ('- name: x / data_type: y'), and plain lines
('order_id bigint not null'). Every change is sorted into breaking (a column gone, a type narrowed or changed, a column made
required) and safe (a nullable column added, a type widened), with likely renames named. Given one schema only, it is described
and checked on its own."""
from __future__ import annotations

import json
import re
from typing import Any

from .common import DeInputError, finder, finish


class ContractError(DeInputError):
    pass


_INT = {"tinyint": 8, "byte": 8, "smallint": 16, "short": 16, "int2": 16, "int": 32, "integer": 32, "int4": 32, "mediumint": 24,
        "bigint": 64, "long": 64, "int8": 64, "int64": 64, "int32": 32, "int16": 16, "serial": 32, "bigserial": 64, "hugeint": 128}
_FLT = {"real": 32, "float4": 32, "float": 64, "float8": 64, "double": 64, "double precision": 64, "float64": 64, "float32": 32}
_STR = ("varchar", "char", "character varying", "character", "text", "string", "nvarchar", "nchar", "varchar2", "nvarchar2", "clob", "uuid", "enum")
_FAM = [("bool", ("bool", "boolean", "bit")), ("timestamp", ("timestamp", "datetime", "timestamptz", "timestamp_ntz", "timestamp_ltz", "timestamp_tz", "datetime2")),
        ("date", ("date",)), ("time", ("time",)), ("json", ("json", "jsonb", "variant", "object", "struct", "map", "record", "super")),
        ("array", ("array", "list")), ("bytes", ("bytea", "blob", "binary", "varbinary", "bytes", "raw"))]


def norm(t: str) -> dict[str, Any]:
    raw = str(t or "").strip().lower()
    t = re.sub(r"\s+", " ", raw)
    base = re.sub(r"\(.*", "", t).strip()
    args = [int(x) for x in re.findall(r"\d+", t[len(base):])] if "(" in t else []
    if base.startswith("unsigned "):
        base = base[9:]
    base = base.replace(" unsigned", "")
    if base in _INT:
        return {"fam": "int", "bits": _INT[base], "raw": raw}
    if base in _FLT:
        return {"fam": "float", "bits": _FLT[base] if not (base == "float" and args and args[0] <= 24) else 32, "raw": raw}
    if base in ("decimal", "numeric", "number", "money", "bignumeric"):
        p = args[0] if args else 38
        s = args[1] if len(args) > 1 else 0
        if base == "number" and not args:
            p, s = 38, 0
        return {"fam": "decimal", "p": p, "s": s, "raw": raw}
    if base in _STR or base.startswith(("varchar", "char", "string")):
        return {"fam": "string", "len": args[0] if args else None, "raw": raw}
    if base.startswith("timestamp") or base.startswith("datetime"):
        return {"fam": "timestamp", "tz": "tz" in base or "with time zone" in t, "raw": raw}
    for fam, names in _FAM:
        if base in names or base.split(" ")[0] in names or base.startswith(tuple(n + "<" for n in names)):
            return {"fam": fam, "raw": raw}
    return {"fam": base or "unknown", "raw": raw}


def _sql(text: str) -> dict[str, Any] | None:
    m = re.search(r"create\s+(?:or\s+replace\s+)?(?:temporary\s+|temp\s+|external\s+)?table\s+(?:if\s+not\s+exists\s+)?([`\"\[\]\w.]+)\s*\((.*)\)", text, re.I | re.S)
    if not m:
        return None
    body = m.group(2)
    parts, depth, cur = [], 0, ""
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    cols, pk = [], []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        low = p.lower()
        if low.startswith(("primary key", "constraint", "unique", "foreign key", "key ", "index ", "check")):
            mm = re.search(r"primary\s+key\s*\(([^)]*)\)", p, re.I)
            if mm:
                pk += [x.strip(' `"[]') for x in mm.group(1).split(",")]
            continue
        mm = re.match(r"([`\"\[][^`\"\]]+[`\"\]]|[\w]+)\s+(.+)$", p, re.S)
        if not mm:
            continue
        name = mm.group(1).strip(' `"[]')
        body2 = mm.group(2).strip()
        typ = re.split(r"\s+(?:not\s+null|null|default|primary|references|generated|comment|collate|auto_increment|identity|unique|check|constraint|encode|sortkey|distkey)\b", body2, maxsplit=1, flags=re.I)[0].strip()
        rest = body2[len(typ):].lower()
        nn = "not null" in rest or "primary key" in rest
        if "primary key" in rest:
            pk.append(name)
        cols.append({"name": name, "type": typ, "nullable": not nn, "default": "default" in rest or "identity" in rest or "auto_increment" in rest or typ.lower().endswith("serial")})
    return {"name": m.group(1).strip('`"[]'), "columns": cols, "pk": pk, "format": "SQL CREATE TABLE"}


def _json(text: str) -> dict[str, Any] | None:
    try:
        d = json.loads(text)
    except ValueError:
        return None
    if isinstance(d, dict) and d.get("type") == "record" and isinstance(d.get("fields"), list):
        cols = []
        for f in d["fields"]:
            t = f.get("type")
            nullable = False
            if isinstance(t, list):
                nullable = "null" in t
                t = next((x for x in t if x != "null"), "string")
            if isinstance(t, dict):
                lt = t.get("logicalType")
                t = {"timestamp-millis": "timestamp", "timestamp-micros": "timestamp", "date": "date", "decimal": f"decimal({t.get('precision', 38)},{t.get('scale', 0)})"}.get(lt, t.get("type", "record"))
            t = {"float": "real", "int": "integer", "long": "bigint"}.get(t, t) if isinstance(t, str) else t   # Avro float is 32-bit
            cols.append({"name": f["name"], "type": str(t), "nullable": nullable, "default": "default" in f})
        return {"name": d.get("name", ""), "columns": cols, "pk": [], "format": "Avro"}
    if isinstance(d, dict) and isinstance(d.get("properties"), dict):
        req = set(d.get("required") or [])
        cols = []
        for k, v in d["properties"].items():
            t = v.get("type", "string")
            nullable = k not in req
            if isinstance(t, list):
                nullable = nullable or "null" in t
                t = next((x for x in t if x != "null"), "string")
            fmt = v.get("format")
            t = {"date-time": "timestamp", "date": "date"}.get(fmt, {"integer": "bigint", "number": "double", "boolean": "boolean", "object": "json", "array": "array"}.get(t, t))
            if t == "string" and v.get("maxLength"):
                t = f"varchar({v['maxLength']})"
            cols.append({"name": k, "type": t, "nullable": nullable, "default": "default" in v})
        return {"name": d.get("title", ""), "columns": cols, "pk": [], "format": "JSON Schema"}
    if isinstance(d, list) and d and isinstance(d[0], dict) and "name" in d[0]:
        cols = [{"name": c["name"], "type": str(c.get("type") or c.get("data_type") or "string"), "nullable": str(c.get("mode", "NULLABLE")).upper() != "REQUIRED" and c.get("nullable", True) is not False,
                 "default": False} for c in d]
        return {"name": "", "columns": cols, "pk": [], "format": "JSON column list"}
    if isinstance(d, dict) and d and all(isinstance(v, str) for v in d.values()):
        return {"name": "", "columns": [{"name": k, "type": v, "nullable": True, "default": False} for k, v in d.items()], "pk": [], "format": "JSON name -> type"}
    return None


def _yaml(text: str) -> dict[str, Any] | None:
    if "- name:" not in text:
        return None
    cols: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    for line in text.splitlines():
        m = re.match(r"\s*-\s*name:\s*['\"]?([\w.]+)", line)
        if m:
            cur = {"name": m.group(1), "type": "", "nullable": True, "default": False}
            cols.append(cur)
            continue
        m = re.match(r"\s*(data_type|type):\s*['\"]?([^'\"#]+)", line)
        if m and cur is not None and not cur["type"]:
            cur["type"] = m.group(2).strip()
        if cur is not None and re.match(r"\s*-\s*not_null\b", line):
            cur["nullable"] = False
    cols = [c for c in cols if c["type"] or len(cols) > 0]
    if not cols:
        return None
    if all(not c["type"] for c in cols):
        raise ContractError("The YAML lists columns but no data_type - add data_type to each column.")
    for c in cols:
        c["type"] = c["type"] or "unknown"
    return {"name": "", "columns": cols, "pk": [], "format": "YAML columns"}


def _lines(text: str) -> dict[str, Any] | None:
    cols = []
    for raw in text.splitlines():
        line = raw.split("--")[0].split("#")[0].strip().rstrip(",")
        if not line:
            continue
        if re.match(r"(?i)^(name|column|column_name)\s*[,|\t]\s*(type|data_type)", line):
            continue
        line = re.sub(r"\s*[|,\t:]\s*", " ", line, count=1)
        m = re.match(r"([`\"]?[\w.]+[`\"]?)\s+(.+)$", line)
        if not m:
            raise ContractError(f"Could not read the column line '{raw.strip()[:60]}'. Use 'name type [not null]'.")
        rest = m.group(2).strip()
        low = rest.lower()
        typ = re.sub(r"(?i)\s*[,|]?\s*\b(not null|null|nullable|required|yes|no|true|false|primary key|default.*)\s*$", "", rest).strip(" ,|")
        nn = "not null" in low or "required" in low or re.search(r"[,| ]\s*(no|false)\s*$", low) is not None or "primary key" in low
        cols.append({"name": m.group(1).strip('`"'), "type": typ or "unknown", "nullable": not nn, "default": "default" in low})
    return {"name": "", "columns": cols, "pk": [], "format": "column lines"} if cols else None


def read(text: str, what: str = "The schema") -> dict[str, Any]:
    t = str(text or "").strip()
    if not t:
        raise ContractError(f"{what}: paste a CREATE TABLE, a JSON Schema / Avro record, a YAML column list or lines 'name type'.")
    s = (_json(t) if t[:1] in "{[" else None) or _sql(t) or _yaml(t) or _lines(t)
    if not s or not s["columns"]:
        raise ContractError(f"{what}: no columns found.")
    seen = set()
    for c in s["columns"]:
        k = c["name"].lower()
        if k in seen:
            raise ContractError(f"{what}: the column {c['name']} appears twice.")
        seen.add(k)
        c["norm"] = norm(c["type"])
    return s


def _change(a: dict[str, Any], b: dict[str, Any]) -> tuple[str, str] | None:
    """(severity, words) for a type change a -> b, or None if the same."""
    if a["raw"] == b["raw"]:
        return None
    fa, fb = a["fam"], b["fam"]
    if fa == fb:
        if fa in ("int", "float"):
            if b["bits"] > a["bits"]:
                return "safe", "widened"
            if b["bits"] < a["bits"]:
                return "breaking", "narrowed - larger values will overflow"
            return None
        if fa == "decimal":
            ia, ib = a["p"] - a["s"], b["p"] - b["s"]
            if ib >= ia and b["s"] >= a["s"]:
                return ("safe", "widened") if (ib, b["s"]) != (ia, a["s"]) else None
            return "breaking", "fewer digits - values may be cut or rounded"
        if fa == "string":
            la, lb = a.get("len"), b.get("len")
            if la == lb:
                return None
            if lb is None or (la is not None and lb > la):
                return "safe", "longer"
            return "breaking", "shorter - longer values will be cut or refused"
        if fa == "timestamp" and a.get("tz") != b.get("tz"):
            return "breaking", "time zone handling changed - the same instant reads differently"
        return None
    if (fa, fb) in (("int", "decimal"), ("int", "float")):
        return ("safe", "widened to " + fb) if fb == "decimal" or a.get("bits", 64) <= 32 else ("warn", "bigint to float loses precision above 2^53")
    if (fa, fb) == ("date", "timestamp"):
        return "warn", "date became timestamp - readers comparing dates may break"
    if fb == "string":
        return "warn", f"{fa} became text - readers doing maths or date logic break"
    return "breaking", f"{fa} became {fb}"


def compare(old_text: str, new_text: str = "") -> dict[str, Any]:
    old = read(old_text, "The contract")
    issues, add = finder()
    if not str(new_text or "").strip():
        cols = old["columns"]
        res: dict[str, Any] = {"mode": "one", "format": old["format"], "name": old["name"], "columns": [{k: c[k] for k in ("name", "type", "nullable")} | {"family": c["norm"]["fam"]} for c in cols],
                               "pk": old["pk"], "changes": []}
        unk = [c["name"] for c in cols if c["norm"]["fam"] not in ("int", "float", "decimal", "string", "bool", "date", "time", "timestamp", "json", "array", "bytes")]
        if unk:
            add("info", "Types", f"Types not recognised for: {', '.join(unk[:6])}.", "They are compared as written.")
        if old["format"] == "SQL CREATE TABLE" and not old["pk"]:
            add("warn", "Key", "No primary key - duplicates cannot be refused and merges / upserts have nothing to match on.", "Declare the key (or a unique constraint), even if the warehouse does not enforce it.")
        fl = [c["name"] for c in cols if c["norm"]["fam"] == "float" and re.search(r"amount|price|total|cost|balance|tax|fee|revenue", c["name"], re.I)]
        if fl:
            add("warn", "Money", f"Money stored as floating point: {', '.join(fl[:5])} - sums drift by fractions of a cent.", "Use decimal(18,2) (or integer minor units).")
        ts = [c["name"] for c in cols if c["norm"]["fam"] == "timestamp" and not c["norm"].get("tz")]
        if ts and any(c["norm"].get("tz") for c in cols if c["norm"]["fam"] == "timestamp"):
            add("warn", "Time zones", f"Timestamps mix with and without time zone ({', '.join(ts[:4])} have none).", "Store UTC with a time zone everywhere.")
        res["verdict"] = f"{len(cols)} columns ({old['format']}) - paste the new schema to compare"
        res["note"] = "Read from the text; the warehouse may name some types differently."
        return finish(res, issues)
    new = read(new_text, "The new schema")
    oc = {c["name"].lower(): c for c in old["columns"]}
    nc = {c["name"].lower(): c for c in new["columns"]}
    changes: list[dict[str, Any]] = []
    gone = [oc[k] for k in oc if k not in nc]
    came = [nc[k] for k in nc if k not in oc]
    renames = []
    for g in list(gone):
        twin = next((c for c in came if c["norm"]["fam"] == g["norm"]["fam"] and (g["name"].lower().replace("_", "") in c["name"].lower().replace("_", "")
                     or c["name"].lower().replace("_", "") in g["name"].lower().replace("_", "") or len(gone) == 1 == len(came))), None)
        if twin:
            renames.append((g, twin))
    for c in gone:
        tw = next((t for g, t in renames if g is c), None)
        changes.append({"column": c["name"], "kind": "removed", "sev": "breaking", "old": c["type"], "new": "", "say": "removed" + (f" - renamed to {tw['name']}?" if tw else "")})
        add("bad", "Removed", f"{c['name']} is gone" + (f" (renamed to {tw['name']}?)" if tw else "") + " - every reader selecting it breaks.",
            "Keep the old column (or a view with the old name) until readers move; announce and deprecate first.", c["name"])
    for c in came:
        if not c["nullable"] and not c["default"]:
            changes.append({"column": c["name"], "kind": "added", "sev": "breaking", "old": "", "new": c["type"], "say": "added as required with no default"})
            add("bad", "Added", f"{c['name']} is new and required with no default - existing writers fail and old rows cannot be filled.",
                "Add it nullable (or with a default), backfill, then make it required.", c["name"])
        else:
            changes.append({"column": c["name"], "kind": "added", "sev": "safe", "old": "", "new": c["type"], "say": "added"})
    for k in oc:
        if k not in nc:
            continue
        a, b = oc[k], nc[k]
        ch = _change(a["norm"], b["norm"])
        if ch:
            sev, words = ch
            changes.append({"column": b["name"], "kind": "type", "sev": "breaking" if sev == "breaking" else sev, "old": a["type"], "new": b["type"], "say": words})
            if sev == "breaking":
                add("bad", "Type", f"{b['name']}: {a['type']} -> {b['type']} - {words}.", "Add a new column with the new type, move readers, then drop the old one.", b["name"])
            elif sev == "warn":
                add("warn", "Type", f"{b['name']}: {a['type']} -> {b['type']} - {words}.", "", b["name"])
        if a["nullable"] and not b["nullable"]:
            changes.append({"column": b["name"], "kind": "nullability", "sev": "breaking", "old": "nullable", "new": "required", "say": "now required"})
            add("bad", "Required", f"{b['name']} is now required - rows with no value are refused and writers that leave it out fail.",
                "Backfill old rows and update every writer before turning it on.", b["name"])
        elif not a["nullable"] and b["nullable"]:
            changes.append({"column": b["name"], "kind": "nullability", "sev": "warn", "old": "required", "new": "nullable", "say": "may now be empty"})
            add("warn", "Nullable", f"{b['name']} may now be empty - readers that assumed a value (joins, sums, keys) can break quietly.", "Tell readers; check joins on it.", b["name"])
    if old["pk"] and new["pk"] and [x.lower() for x in old["pk"]] != [x.lower() for x in new["pk"]]:
        changes.append({"column": ", ".join(new["pk"]), "kind": "key", "sev": "breaking", "old": ", ".join(old["pk"]), "new": ", ".join(new["pk"]), "say": "primary key changed"})
        add("bad", "Key", f"The primary key changed from ({', '.join(old['pk'])}) to ({', '.join(new['pk'])}) - merges and upserts match different rows.", "Treat it as a new table.")
    ordr = [c["name"].lower() for c in old["columns"] if c["name"].lower() in nc]
    ordn = [c["name"].lower() for c in new["columns"] if c["name"].lower() in oc]
    if ordr != ordn:
        add("info", "Order", "Columns changed order - only readers using SELECT * or positions (CSV, INSERT without column names) notice.", "")
    nb = sum(1 for c in changes if c["sev"] == "breaking")
    res = {"mode": "two", "format": old["format"], "format_new": new["format"], "name": new["name"] or old["name"], "changes": changes,
           "breaking": nb, "safe": sum(1 for c in changes if c["sev"] == "safe"), "old_cols": len(oc), "new_cols": len(nc),
           "columns": [{k: c[k] for k in ("name", "type", "nullable")} | {"family": c["norm"]["fam"]} for c in new["columns"]], "renames": [[g["name"], t["name"]] for g, t in renames]}
    res["verdict"] = (f"{nb} breaking change(s)" if nb else "No breaking changes") + f" - {len(changes)} change(s), {len(oc)} -> {len(nc)} columns"
    res["note"] = "Types are compared by family and size as written; check how your warehouse names them. A rename is a guess from the names and types."
    return finish(res, issues)
