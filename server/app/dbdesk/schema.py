"""Read CREATE TABLE / CREATE INDEX statements (PostgreSQL, MySQL, SQLite dialects) into tables, columns, keys and indexes, and
review them: tables without a primary key, foreign keys with no index on their column, indexes another index already covers,
timestamps without a time zone, money in floating point, very wide keys. A schema is DATA."""
from __future__ import annotations

import re
from typing import Any

MAX = 600_000


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    return re.sub(r"--[^\n]*", "", sql)


def split(sql: str) -> list[str]:
    """Statements split on ; outside quotes and parentheses."""
    out, buf, q, depth = [], [], "", 0
    for ch in sql:
        if q:
            buf.append(ch)
            if ch == q:
                q = ""
            continue
        if ch in "'\"`":
            q = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == ";" and depth == 0:
            s = "".join(buf).strip()
            if s:
                out.append(s)
            buf = []
            continue
        buf.append(ch)
    s = "".join(buf).strip()
    if s:
        out.append(s)
    return out


def _parts(body: str) -> list[str]:
    out, buf, depth, q = [], [], 0, ""
    for ch in body:
        if q:
            buf.append(ch)
            if ch == q:
                q = ""
            continue
        if ch in "'\"`":
            q = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            out.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    if "".join(buf).strip():
        out.append("".join(buf).strip())
    return out


_ID = r'[`"\[]?([A-Za-z_][\w$]*)[`"\]]?'


def _name(x: str) -> str:
    x = x.strip().strip('`"[]')
    return x.split(".")[-1].strip('`"[]')


def _cols(lst: str) -> list[str]:
    return [_name(re.split(r"\s+", c.strip())[0]) for c in _parts(lst) if c.strip()]


def parse(sql: str) -> dict[str, Any]:
    sql = _strip_comments(str(sql or "")[:MAX])
    tables: dict[str, dict[str, Any]] = {}
    indexes: list[dict[str, Any]] = []
    for st in split(sql):
        m = re.match(r"CREATE\s+(?:TEMP(?:ORARY)?\s+|UNLOGGED\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([\w.`\"\[\]$]+)\s*\((.*)\)\s*[^)]*$", st, re.S | re.I)
        if m:
            t = {"name": _name(m[1]), "columns": [], "pk": [], "fks": [], "uniques": [], "line": sql[:sql.find(st)].count("\n") + 1}
            for part in _parts(m[2]):
                p = part.strip()
                u = p.upper()
                if re.match(r"(CONSTRAINT\s+\S+\s+)?PRIMARY\s+KEY", u):
                    t["pk"] = _cols(re.search(r"\((.*?)\)", p)[1])
                    continue
                if re.match(r"(CONSTRAINT\s+\S+\s+)?FOREIGN\s+KEY", u):
                    fm = re.search(r"FOREIGN\s+KEY\s*\((.*?)\)\s*REFERENCES\s+([\w.`\"\[\]$]+)\s*(?:\((.*?)\))?", p, re.I)
                    if fm:
                        t["fks"].append({"cols": _cols(fm[1]), "ref": _name(fm[2]), "ref_cols": _cols(fm[3]) if fm[3] else []})
                    continue
                if re.match(r"(CONSTRAINT\s+\S+\s+)?UNIQUE", u):
                    um = re.search(r"\((.*?)\)", p)
                    if um:
                        t["uniques"].append(_cols(um[1]))
                    continue
                if re.match(r"(CONSTRAINT|CHECK|KEY|INDEX|FULLTEXT|SPATIAL|EXCLUDE)\b", u):
                    km = re.match(r"(?:KEY|INDEX)\s+(\S+)?\s*\((.*?)\)", p, re.I)
                    if km:
                        indexes.append({"name": _name(km[1] or ""), "table": t["name"], "cols": _cols(km[2]), "unique": False, "line": t["line"]})
                    continue
                cm = re.match(_ID + r"\s+(.+)$", p, re.S)
                if not cm:
                    continue
                cname, rest = cm[1], cm[2]
                typ = re.match(r"([A-Za-z ]+?(?:\([^)]*\))?)(?=\s+(?:NOT|NULL|DEFAULT|PRIMARY|REFERENCES|UNIQUE|CHECK|GENERATED|AUTO_INCREMENT|COLLATE|CONSTRAINT|COMMENT)\b|\s*$)", rest.strip(), re.I)
                col = {"name": cname, "type": (typ[1] if typ else rest.split()[0]).strip().lower(), "null": "NOT NULL" not in rest.upper() and "PRIMARY KEY" not in rest.upper()}
                t["columns"].append(col)
                if re.search(r"\bPRIMARY\s+KEY\b", rest, re.I):
                    t["pk"] = [cname]
                rm = re.search(r"REFERENCES\s+([\w.`\"\[\]$]+)\s*(?:\((.*?)\))?", rest, re.I)
                if rm:
                    t["fks"].append({"cols": [cname], "ref": _name(rm[1]), "ref_cols": _cols(rm[2]) if rm[2] else []})
                if re.search(r"\bUNIQUE\b", rest, re.I):
                    t["uniques"].append([cname])
            tables[t["name"].lower()] = t
            continue
        m = re.match(r"CREATE\s+(UNIQUE\s+)?INDEX\s+(?:CONCURRENTLY\s+)?(?:IF\s+NOT\s+EXISTS\s+)?([\w.`\"\[\]$]*)\s*ON\s+(?:ONLY\s+)?([\w.`\"\[\]$]+)"
                     r"\s*(?:USING\s+(\w+)\s*)?\((.*?)\)\s*(?:INCLUDE\s*\((.*?)\))?\s*(?:WHERE\s+(.*))?$", st, re.S | re.I)
        if m:
            indexes.append({"name": _name(m[2]), "table": _name(m[3]), "cols": _cols(m[5]), "unique": bool(m[1]), "method": (m[4] or "").lower(),
                            "include": _cols(m[6]) if m[6] else [], "partial": bool(m[7]), "line": sql[:sql.find(st)].count("\n") + 1})
    return {"tables": list(tables.values()), "indexes": indexes}


def _covered(cols: list[str], t: dict[str, Any], idx: list[dict[str, Any]]) -> str:
    """Name of an index / key whose leading columns are exactly `cols` (in order), or ''."""
    low = [c.lower() for c in cols]
    if [c.lower() for c in t["pk"][:len(low)]] == low:
        return "the primary key"
    for u in t["uniques"]:
        if [c.lower() for c in u[:len(low)]] == low:
            return "a unique key"
    for i in idx:
        if i["table"].lower() == t["name"].lower() and not i.get("partial") and [c.lower() for c in i["cols"][:len(low)]] == low:
            return i["name"] or "an index"
    return ""


def review(sql: str, engine: str = "postgres") -> dict[str, Any]:
    d = parse(sql)
    tables, idx = d["tables"], d["indexes"]
    if not tables and not idx:
        return {"ok": False, "error": "No CREATE TABLE or CREATE INDEX found. Paste the schema (pg_dump --schema-only, SHOW CREATE TABLE, .schema)."}
    issues: list[dict[str, Any]] = []
    for t in tables:
        if not t["pk"]:
            issues.append({"sev": "bad", "table": t["name"], "say": f"{t['name']} has no primary key",
                           "fix": "Every table needs a primary key: replication, updates by row and many tools depend on it." +
                                  (" MySQL InnoDB otherwise makes a hidden one you cannot use." if engine == "mysql" else "")})
        for fk in t["fks"]:
            if engine != "mysql" and not _covered(fk["cols"], t, idx):
                issues.append({"sev": "warn", "table": t["name"], "say": f"{t['name']}.{', '.join(fk['cols'])} references {fk['ref']} but has no index",
                               "fix": f"CREATE INDEX ON {t['name']} ({', '.join(fk['cols'])}); - joins on it and deletes in {fk['ref']} otherwise scan {t['name']}.",
                               "sql": f"CREATE INDEX {t['name']}_{'_'.join(fk['cols'])}_idx ON {t['name']} ({', '.join(fk['cols'])});"})
        for c in t["columns"]:
            ty = c["type"]
            if engine == "postgres" and re.match(r"timestamp(\(\d\))?$|timestamp without time zone", ty):
                issues.append({"sev": "info", "table": t["name"], "say": f"{t['name']}.{c['name']} is a timestamp without a time zone",
                               "fix": "Use timestamptz so the same moment reads the same from every time zone."})
            if re.match(r"(float|double|real)", ty) and re.search(r"price|amount|total|cost|balance|money|fee|tax", c["name"], re.I):
                issues.append({"sev": "warn", "table": t["name"], "say": f"{t['name']}.{c['name']} keeps money in floating point ({ty})",
                               "fix": "Use numeric / decimal (or whole minor units in a bigint): floating point cannot hold 0.10 exactly."})
            if engine == "postgres" and re.match(r"(varchar|character varying)\(\d+\)", ty) and int(re.search(r"\d+", ty)[0]) > 10000:
                issues.append({"sev": "info", "table": t["name"], "say": f"{t['name']}.{c['name']} is {ty}", "fix": "In PostgreSQL text is the same speed; a check constraint states the limit more clearly."})
        if engine == "postgres" and any(c["type"] in ("serial", "bigserial") for c in t["columns"]):
            issues.append({"sev": "info", "table": t["name"], "say": f"{t['name']} uses serial",
                           "fix": "Identity columns (GENERATED ALWAYS AS IDENTITY) are the SQL-standard way since PostgreSQL 10."})
    # redundant indexes: one index's columns are a leading prefix of another's on the same table (same method, both non-unique / non-partial)
    for a in idx:
        for b in idx:
            if a is b or a["table"].lower() != b["table"].lower() or a.get("partial") or b.get("partial") or a["unique"]:
                continue
            if (a.get("method") or "btree") != (b.get("method") or "btree"):
                continue
            la, lb = [c.lower() for c in a["cols"]], [c.lower() for c in b["cols"]]
            if len(la) < len(lb) and lb[:len(la)] == la:
                issues.append({"sev": "warn", "table": a["table"], "say": f"Index {a['name'] or '(unnamed)'} ({', '.join(a['cols'])}) is covered by "
                                                                       f"{b['name'] or '(unnamed)'} ({', '.join(b['cols'])})",
                               "fix": "The longer index answers the same lookups: dropping the shorter one saves writes and space (check it is not used by a constraint first).",
                               "sql": f"DROP INDEX {a['name']};" if a["name"] else ""})
            if la == lb and id(a) < id(b):
                issues.append({"sev": "warn", "table": a["table"], "say": f"Indexes {a['name']} and {b['name']} are the same ({', '.join(a['cols'])})",
                               "fix": "Keep one.", "sql": f"DROP INDEX {b['name']};" if b["name"] else ""})
    order = {"bad": 0, "warn": 1, "info": 2}
    issues.sort(key=lambda x: order[x["sev"]])
    counts = {k: sum(1 for i in issues if i["sev"] == k) for k in order}
    return {"ok": True, "tables": tables, "indexes": idx, "issues": issues, "counts": counts,
            "verdict": f"{len(tables)} table(s), {len(idx)} index(es): " + (f"{counts['bad']} serious, {counts['warn']} to check, {counts['info']} note(s)."
                                                                            if issues else "nothing found by these checks.")}
