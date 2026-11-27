"""Read a query plan - PostgreSQL EXPLAIN (text or JSON, with or without ANALYZE / BUFFERS), MySQL EXPLAIN ANALYZE / FORMAT=TREE
or the classic table, SQLite EXPLAIN QUERY PLAN - into a tree of steps with estimated vs actual rows and the time each step really
took, then the findings a database engineer looks for first: a full scan that throws most rows away, an estimate that is far off,
a sort or hash that spilled to disk, a nested loop that repeats a scan, a lossy bitmap, heap fetches. A plan is DATA."""
from __future__ import annotations

import json
import re
from typing import Any

MAX = 1_000_000


def _f(x: Any) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _node(op: str, **kw: Any) -> dict[str, Any]:
    n = {"op": op.strip(), "rel": "", "alias": "", "index": "", "est_rows": None, "rows": None, "loops": 1, "total_ms": None,
         "cost": None, "detail": [], "children": []}
    n.update({k: v for k, v in kw.items() if v is not None})
    return n


# ---------------------------------------------------------------- PostgreSQL text
_PG_NODE = re.compile(r"^(?P<ind>\s*)(?:->\s+)?(?P<head>[A-Z][^(]*?)\s+\(cost=(?P<c1>[\d.]+)\.\.(?P<c2>[\d.]+) rows=(?P<er>\d+) width=\d+\)"
                      r"(?:\s+\((?:actual time=(?P<t1>[\d.]+)\.\.(?P<t2>[\d.]+) rows=(?P<ar>[\d.]+) loops=(?P<lp>\d+)|(?P<never>never executed))\))?")
_PG_NODE_NOCOST = re.compile(r"^(?P<ind>\s*)(?:->\s+)?(?P<head>[A-Z][^(]*?)\s+\((?:actual time=(?P<t1>[\d.]+)\.\.(?P<t2>[\d.]+) "
                             r"rows=(?P<ar>[\d.]+) loops=(?P<lp>\d+)|(?P<never>never executed))\)")


def _pg_head(head: str) -> dict[str, str]:
    head = head.strip()
    m = re.match(r"(?P<op>.+?) using (?P<idx>\S+) on (?P<rel>\S+)(?: (?P<alias>\S+))?$", head)
    if m:
        return {"op": m["op"], "index": m["idx"], "rel": m["rel"], "alias": m["alias"] or ""}
    m = re.match(r"(?P<op>.+?) on (?P<rel>\S+)(?: (?P<alias>\S+))?$", head)
    if m:
        return {"op": m["op"], "rel": m["rel"], "alias": m["alias"] or ""}
    return {"op": head}


def _pg_text(text: str) -> dict[str, Any]:
    root: dict[str, Any] | None = None
    stack: list[tuple[int, dict[str, Any]]] = []
    extra: dict[str, Any] = {}
    for raw in text.splitlines():
        line = raw.rstrip()
        if re.match(r"^\s*(QUERY PLAN|-{5,}|\(\d+ rows?\))\s*$", line):
            continue
        m = _PG_NODE.match(line) or _PG_NODE_NOCOST.match(line)
        if m:
            ind = len(m["ind"]) + (2 if "->" in line[:len(m["ind"]) + 3] else 0)
            h = _pg_head(m["head"])
            gd = m.groupdict()
            n = _node(h["op"], rel=h.get("rel", ""), alias=h.get("alias", ""), index=h.get("index", ""),
                      est_rows=int(gd["er"]) if gd.get("er") else None, cost=_f(gd.get("c2")),
                      rows=None if gd.get("never") or not gd.get("ar") else float(gd["ar"]),
                      loops=int(gd["lp"]) if gd.get("lp") else (0 if gd.get("never") else 1),
                      total_ms=(_f(gd["t2"]) * int(gd["lp"])) if gd.get("t2") else None, never=bool(gd.get("never")))
            while stack and stack[-1][0] >= ind:
                stack.pop()
            if stack:
                stack[-1][1]["children"].append(n)
            elif root is None:
                root = n
            else:
                root["children"].append(n)
            stack.append((ind, n))
            continue
        s = line.strip()
        mt = re.match(r"(Planning|Execution) [Tt]ime: ([\d.]+) ms", s)
        if mt:
            extra["planning_ms" if mt[1] == "Planning" else "execution_ms"] = float(mt[2])
            continue
        mj = re.match(r"JIT:", s)
        if mj:
            extra["jit"] = True
            continue
        mjt = re.match(r"Timing: .*Total ([\d.]+) ms", s)
        if mjt:
            extra["jit_ms"] = float(mjt[1])
            continue
        if s and stack:
            stack[-1][1]["detail"].append(s)
    if root is None:
        return {}
    return {"root": root, **extra}


# ---------------------------------------------------------------- PostgreSQL JSON
def _pg_json_node(p: dict[str, Any]) -> dict[str, Any]:
    loops = int(p.get("Actual Loops", 1) or 0)
    t = _f(p.get("Actual Total Time"))
    det = []
    for k in ("Filter", "Index Cond", "Join Filter", "Hash Cond", "Merge Cond", "Recheck Cond", "Sort Key", "Group Key"):
        if p.get(k):
            det.append(f"{k}: {', '.join(p[k]) if isinstance(p[k], list) else p[k]}")
    if p.get("Rows Removed by Filter") is not None:
        det.append(f"Rows Removed by Filter: {p['Rows Removed by Filter']}")
    if p.get("Sort Method"):
        det.append(f"Sort Method: {p['Sort Method']}  {p.get('Sort Space Type', '')}: {p.get('Sort Space Used', '')}kB")
    if p.get("Hash Batches"):
        det.append(f"Buckets: {p.get('Hash Buckets')}  Batches: {p['Hash Batches']}")
    if p.get("Heap Fetches") is not None:
        det.append(f"Heap Fetches: {p['Heap Fetches']}")
    if p.get("Exact Heap Blocks") is not None or p.get("Lossy Heap Blocks"):
        det.append(f"Heap Blocks: exact={p.get('Exact Heap Blocks', 0)} lossy={p.get('Lossy Heap Blocks', 0)}")
    n = _node(p.get("Node Type", "?"), rel=p.get("Relation Name", ""), alias=p.get("Alias", ""), index=p.get("Index Name", ""),
              est_rows=p.get("Plan Rows"), cost=_f(p.get("Total Cost")), rows=_f(p.get("Actual Rows")), loops=loops,
              total_ms=(t * loops) if t is not None else None, detail=det)
    n["children"] = [_pg_json_node(c) for c in p.get("Plans") or []]
    return n


def _pg_json(text: str) -> dict[str, Any]:
    try:
        d = json.loads(text)
    except ValueError:
        return {}
    if isinstance(d, list) and d:
        d = d[0]
    if isinstance(d, dict) and "QUERY PLAN" in d:
        d = d["QUERY PLAN"][0] if isinstance(d["QUERY PLAN"], list) else d["QUERY PLAN"]
    if not isinstance(d, dict) or "Plan" not in d:
        return {}
    out = {"root": _pg_json_node(d["Plan"])}
    if d.get("Planning Time") is not None:
        out["planning_ms"] = float(d["Planning Time"])
    if d.get("Execution Time") is not None:
        out["execution_ms"] = float(d["Execution Time"])
    return out


# ---------------------------------------------------------------- MySQL tree (EXPLAIN ANALYZE / FORMAT=TREE)
_MY = re.compile(r"^(?P<ind>\s*)-> (?P<head>.+?)(?:\s+\(cost=(?P<cost>[\d.e+]+)(?:\.\.(?P<c2>[\d.e+]+))? rows=(?P<er>[\d.e+]+)\))?"
                 r"(?:\s+\(actual time=(?P<t1>[\d.]+)\.\.(?P<t2>[\d.]+) rows=(?P<ar>[\d.e+]+) loops=(?P<lp>\d+)\))?\s*$")


def _my_head(head: str) -> dict[str, str]:
    m = re.match(r"(?P<op>Table scan|Index scan|Index range scan|Covering index scan|Index lookup|Single-row index lookup|"
                 r"Covering index lookup|Full-text index search|Index range scan \(Multi-Range Read\)) on (?P<rel>\S+)(?: using (?P<idx>\S+))?(?P<rest>.*)$", head)
    if m:
        return {"op": m["op"], "rel": m["rel"], "index": m["idx"] or "", "cond": m["rest"].strip()}
    return {"op": head}


def _mysql_tree(text: str) -> dict[str, Any]:
    root = None
    stack: list[tuple[int, dict[str, Any]]] = []
    for raw in text.splitlines():
        line = raw.replace("\\n", "\n").rstrip()
        for sub in line.split("\n"):
            m = _MY.match(sub)
            if not m:
                continue
            h = _my_head(m["head"])
            lp = int(m["lp"]) if m["lp"] else 1
            n = _node(h["op"], rel=h.get("rel", ""), index=h.get("index", ""), est_rows=int(float(m["er"])) if m["er"] else None,
                      cost=_f(m["c2"] or m["cost"]), rows=_f(m["ar"]), loops=lp, total_ms=(_f(m["t2"]) * lp) if m["t2"] else None,
                      detail=[h["cond"]] if h.get("cond") else ([m["head"]] if h["op"] != m["head"] else []))
            ind = len(m["ind"])
            while stack and stack[-1][0] >= ind:
                stack.pop()
            if stack:
                stack[-1][1]["children"].append(n)
            elif root is None:
                root = n
            else:
                root["children"].append(n)
            stack.append((ind, n))
    return {"root": root} if root else {}


# ---------------------------------------------------------------- MySQL classic table
def _mysql_table(text: str) -> dict[str, Any]:
    rows = [ln for ln in text.splitlines() if ln.strip().startswith("|")]
    if len(rows) < 2:
        return {}
    head = [c.strip().lower() for c in rows[0].strip().strip("|").split("|")]
    if "type" not in head or "table" not in head:
        return {}
    root = _node("Query")
    for ln in rows[1:]:
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) != len(head):
            continue
        d = dict(zip(head, cells))
        typ = d.get("type", "")
        op = {"ALL": "Table scan", "index": "Index scan", "range": "Index range scan", "ref": "Index lookup", "eq_ref": "Single-row index lookup",
              "const": "Constant row", "system": "Constant row", "fulltext": "Full-text index search", "index_merge": "Index merge"}.get(typ, typ or "?")
        det = []
        if d.get("possible_keys") and d["possible_keys"] != "NULL":
            det.append("possible_keys: " + d["possible_keys"])
        if d.get("extra"):
            det.append("Extra: " + d["extra"])
        if d.get("filtered"):
            det.append("filtered: " + d["filtered"] + "%")
        root["children"].append(_node(op, rel=d.get("table", ""), index="" if d.get("key") in (None, "", "NULL") else d["key"],
                                      est_rows=int(_f(d.get("rows")) or 0) if _f(d.get("rows")) is not None else None, detail=det,
                                      mysql_type=typ))
    return {"root": root} if root["children"] else {}


# ---------------------------------------------------------------- SQLite EXPLAIN QUERY PLAN
def _sqlite(text: str) -> dict[str, Any]:
    lines = [ln for ln in text.splitlines() if re.search(r"\b(SCAN|SEARCH|USE TEMP B-TREE|CO-ROUTINE|MATERIALIZE|COMPOUND|SCALAR SUBQUERY|"
                                                         r"CORRELATED|LIST SUBQUERY|MULTI-INDEX OR|BLOOM FILTER)\b", ln)]
    if not lines:
        return {}
    root = _node("Query")
    stack: list[tuple[int, dict[str, Any]]] = []
    for ln in lines:
        m = re.match(r"^([\s|`-]*)(.*)$", ln)
        ind, body = len(m[1]), m[2].strip()
        rel = re.match(r"(?:SCAN|SEARCH) (\S+)", body)
        idx = re.search(r"USING (?:COVERING |INTEGER PRIMARY KEY|PRIMARY KEY)?\s*(?:INDEX )?(\S+)?", body)
        op = "Table scan" if body.startswith("SCAN") and "USING" not in body else "Index search" if body.startswith("SEARCH") else \
            "Covering index scan" if body.startswith("SCAN") else body.split(" (")[0]
        n = _node(op, rel=rel[1] if rel else "", index=(idx[1] or "") if idx and "INDEX" in body else "", detail=[body])
        while stack and stack[-1][0] >= ind:
            stack.pop()
        (stack[-1][1] if stack else root)["children"].append(n)
        stack.append((ind, n))
    return {"root": root}


# ---------------------------------------------------------------- parse + findings
def detect(text: str) -> str:
    t = text.strip()
    if t.startswith("[") or t.startswith("{"):
        return "postgres-json"
    if re.search(r"^\s*-> .+\(cost=[\d.e+]+(?:\.\.[\d.e+]+)? rows=", t, re.M) and not re.search(r"width=\d+\)", t):
        return "mysql-tree"
    if re.search(r"^\s*\|\s*id\s*\|\s*select_type", t, re.M | re.I):
        return "mysql-table"
    if re.search(r"\(cost=[\d.]+\.\.[\d.]+ rows=\d+ width=\d+\)", t) or re.search(r"\(actual time=[\d.]+\.\.[\d.]+ rows=", t):
        return "postgres"
    if re.search(r"\b(SCAN|SEARCH) \w+", t):
        return "sqlite"
    return ""


def _walk(n: dict[str, Any], depth: int = 0, out: list | None = None, parent: dict | None = None) -> list:
    out = [] if out is None else out
    n["depth"] = depth
    n["_parent_op"] = parent["op"] if parent else ""
    n["_parent"] = parent
    out.append(n)
    for c in n["children"]:
        _walk(c, depth + 1, out, n)
    return out


def _walk_only(n: dict[str, Any]) -> list:
    out = [n]
    for c in n["children"]:
        out += _walk_only(c)
    return out


def _self_times(n: dict[str, Any]) -> None:
    for c in n["children"]:
        _self_times(c)
    if n.get("total_ms") is not None:
        kids = sum(c["total_ms"] or 0 for c in n["children"] if c.get("total_ms") is not None)
        n["self_ms"] = round(max(0.0, n["total_ms"] - kids), 3)


def _cols(cond: str) -> list[str]:
    cond = re.sub(r"'[^']*'", "", cond)
    cols = re.findall(r"\(?\b(?:[a-z_][\w]*\.)?([a-z_][\w]*)\b\s*(?:=|<=|>=|<|>|<>|!=|~~|LIKE|IN|IS|BETWEEN|::)", cond, re.I)
    bad = {"and", "or", "not", "null", "true", "false", "text", "integer", "bigint", "numeric", "date", "timestamp", "any", "array"}
    seen = []
    for c in cols:
        if c.lower() not in bad and c not in seen:
            seen.append(c)
    return seen[:4]


def _det(n: dict[str, Any], key: str) -> str:
    for d in n["detail"]:
        if d.lower().startswith(key.lower()):
            return d.split(":", 1)[1].strip() if ":" in d else d
    return ""


def findings(root: dict[str, Any], big: int = 10000) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    nodes = _walk(root)
    for x in reversed(nodes):
        r_, e_ = x.get("rows"), x.get("est_rows")
        x["_est"] = bool(r_ is not None and e_ is not None and r_ * (x.get("loops") or 1) >= 100 and not 0.1 < (r_ + 1) / (e_ + 1) < 10)
    total = root.get("total_ms") or max([n.get("total_ms") or 0 for n in nodes] or [0])
    for n in nodes:
        op, rel = n["op"], n["rel"]
        where = f"{op}{' on ' + rel if rel else ''}"
        rows, est, loops = n.get("rows"), n.get("est_rows"), n.get("loops") or 1
        removed = _det(n, "Rows Removed by Filter")
        removed_n = _f(removed.split()[0]) if removed else None
        filt = _det(n, "Filter") or (n["detail"][0] if n["detail"] and op in ("Table scan",) else "")
        is_full = op in ("Seq Scan", "Parallel Seq Scan", "Table scan") or n.get("mysql_type") == "ALL"
        if is_full:
            scanned = (rows or 0) * loops + (removed_n or 0) * loops if rows is not None else est or 0
            kept = (rows or 0) * loops if rows is not None else None
            if removed_n is not None and removed_n * loops >= big and removed_n > 9 * (rows or 0):
                cols = _cols(filt)
                out.append({"sev": "bad", "kind": "scan", "where": where, "rel": rel, "cols": cols,
                            "say": f"{where} reads {int(scanned):,} rows to keep {int(kept or 0):,}" + (f" - filtered on {', '.join(cols)}" if cols else ""),
                            "fix": (f"An index on {rel} ({', '.join(cols)}) lets the database go straight to the rows." if cols and rel else
                                    "An index on the filtered column(s) lets the database go straight to the rows.")})
            elif (n["_parent_op"].startswith("Filter:") and rows is not None and rows * loops >= big
                  and (n["_parent"].get("rows") or 0) <= rows / 10):
                cols = _cols(n["_parent_op"])
                out.append({"sev": "bad", "kind": "scan", "where": where, "rel": rel, "cols": cols,
                            "say": f"{where} reads {int(rows * loops):,} rows; the filter above it keeps {int(n['_parent']['rows'] or 0):,}" +
                                   (f" - filtered on {', '.join(cols)}" if cols else ""),
                            "fix": (f"An index on {rel} ({', '.join(cols)}) lets the database go straight to the rows." if cols and rel else
                                    "An index on the filtered column(s) lets the database go straight to the rows.")})
            elif op == "Table scan" and rows is None and est is None and n["detail"] and n["detail"][0].startswith("SCAN"):
                out.append({"sev": "warn", "kind": "scan", "where": where, "rel": rel, "cols": [],
                            "say": f"{where}: SQLite reads the whole table",
                            "fix": "If the query filters or joins on this table, an index on those columns lets SQLite SEARCH instead of SCAN."})
            elif (est or 0) >= big and n.get("mysql_type") == "ALL":
                pk = re.search(r"possible_keys: (\S+)", " ".join(n["detail"]))
                out.append({"sev": "warn", "kind": "scan", "where": where, "rel": rel, "cols": [],
                            "say": f"{where}: a full scan of about {int(est):,} rows" + (f" although {pk[1]} could be used" if pk else ""),
                            "fix": "Check the WHERE / JOIN columns of this table have an index the optimiser can use (same type, no function around the column)."})
        if rows is not None and est is not None and rows * loops >= 100:
            r = (rows + 1) / (est + 1)
            below = any(x.get("_est") for x in _walk_only(n) if x is not n)
            if (r >= 10 or r <= 0.1) and not below:
                out.append({"sev": "warn", "kind": "estimate", "where": where, "rel": rel,
                            "say": f"{where}: planned {est:,} rows, really {int(rows):,}" + (f" per loop x{loops}" if loops > 1 else "") + f" ({r:.0f}x off)" if r >= 1 else
                                   f"{where}: planned {est:,} rows, really {int(rows):,} ({1 / r:.0f}x fewer)",
                            "fix": f"Refresh the statistics (ANALYZE {rel or 'the table'}); for correlated columns, extended statistics (CREATE STATISTICS). "
                                   "A wrong estimate makes the planner pick the wrong join or scan."})
        sm = _det(n, "Sort Method")
        if sm and ("external" in sm.lower() or "disk" in sm.lower()):
            out.append({"sev": "bad", "kind": "spill", "where": where, "rel": rel, "say": f"{where} spilled to disk ({sm})",
                        "fix": "Raise work_mem for this query (SET LOCAL work_mem), or add an index that already returns the rows in this order."})
        hb = re.search(r"Batches: (\d+)", " ".join(n["detail"]))
        if hb and int(hb[1]) > 1:
            out.append({"sev": "warn", "kind": "spill", "where": where, "rel": rel, "say": f"{where}: the hash table was split into {hb[1]} batches (spilled to disk)",
                        "fix": "Raise work_mem / hash_mem_multiplier, or reduce the rows before the join."})
        if "Using filesort" in " ".join(n["detail"]) or "Using temporary" in " ".join(n["detail"]) or op == "USE TEMP B-TREE FOR ORDER BY":
            out.append({"sev": "warn", "kind": "sort", "where": where, "rel": rel, "say": f"{where}: sorted in a temporary structure ({', '.join(x for x in ('filesort', 'temporary table') if x.split()[0] in ' '.join(n['detail']).lower()) or 'temp B-tree'})",
                        "fix": "An index whose columns match the ORDER BY / GROUP BY (after the equality columns) avoids the sort."})
        if loops >= 1000 and (n["_parent_op"] in ("Nested Loop", "Nested loop inner join", "Nested loop left join") or n["_parent_op"].startswith("Nested")) and is_full:
            out.append({"sev": "bad", "kind": "loop", "where": where, "rel": rel, "say": f"{where} runs {loops:,} times inside a nested loop",
                        "fix": f"Index the join column on {rel or 'this table'}, or let the planner use a hash join (check the estimate above)."})
        lossy = re.search(r"lossy=(\d+)", " ".join(n["detail"]))
        if lossy and int(lossy[1]) > 0:
            out.append({"sev": "warn", "kind": "bitmap", "where": where, "rel": rel, "say": f"{where}: {lossy[1]} lossy heap blocks - every row in them was rechecked",
                        "fix": "Raise work_mem so the bitmap stays exact."})
        hf = re.search(r"Heap Fetches: (\d+)", " ".join(n["detail"]))
        if hf and op.startswith("Index Only Scan") and rows and int(hf[1]) > 0.5 * rows * loops:
            out.append({"sev": "warn", "kind": "vacuum", "where": where, "rel": rel, "say": f"{where}: {int(hf[1]):,} heap fetches - the visibility map is out of date",
                        "fix": f"VACUUM {rel or 'the table'} so the index-only scan does not visit the table."})
    if total:
        slow = max((n for n in nodes if n.get("self_ms") is not None), key=lambda n: n["self_ms"], default=None)
        if slow and slow["self_ms"] >= 0.3 * total and slow["self_ms"] >= 1:
            out.append({"sev": "info", "kind": "time", "where": f"{slow['op']}{' on ' + slow['rel'] if slow['rel'] else ''}", "rel": slow["rel"],
                        "say": f"Most of the time ({slow['self_ms']:.1f} of {total:.1f} ms) is spent in {slow['op']}{' on ' + slow['rel'] if slow['rel'] else ''}",
                        "fix": "Start there."})
    order = {"bad": 0, "warn": 1, "info": 2}
    seen, uniq = set(), []
    for f in sorted(out, key=lambda f: order[f["sev"]]):
        k = (f["kind"], f["where"])
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    return uniq


def _strip(n: dict[str, Any]) -> dict[str, Any]:
    return {**{k: v for k, v in n.items() if k not in ("children", "_parent_op", "_parent", "_est")}, "children": [_strip(c) for c in n["children"]]}


def read(text: str, big: int = 10000) -> dict[str, Any]:
    text = str(text or "")[:MAX]
    kind = detect(text)
    p = {"postgres": _pg_text, "postgres-json": _pg_json, "mysql-tree": _mysql_tree, "mysql-table": _mysql_table, "sqlite": _sqlite}.get(kind, lambda _t: {})(text)
    if not p or not p.get("root"):
        return {"ok": False, "error": "This does not look like a query plan. Paste the output of EXPLAIN (ANALYZE, BUFFERS) for PostgreSQL, "
                                      "EXPLAIN ANALYZE or EXPLAIN FORMAT=TREE for MySQL, or EXPLAIN QUERY PLAN for SQLite."}
    root = p["root"]
    _self_times(root)
    fs = findings(root, big)
    nodes = _walk(root)
    analyzed = any(n.get("rows") is not None for n in nodes)
    engine = {"postgres": "PostgreSQL", "postgres-json": "PostgreSQL", "mysql-tree": "MySQL", "mysql-table": "MySQL", "sqlite": "SQLite"}[kind]
    total = p.get("execution_ms") or root.get("total_ms")
    bad = sum(1 for f in fs if f["sev"] == "bad")
    verdict = (f"{len(nodes)} step(s){', ' + format(total, '.1f') + ' ms' if total else ''}. " +
               (f"{bad} serious finding(s): start with the first." if bad else "No serious problem found." if fs == [] or all(f["sev"] == "info" for f in fs) else
                f"{len(fs)} thing(s) to check.") + ("" if analyzed else " This plan has estimates only - run it with ANALYZE for the real rows and times."))
    return {"ok": True, "engine": engine, "format": kind, "analyzed": analyzed, "steps": len(nodes), "total_ms": total,
            "planning_ms": p.get("planning_ms"), "jit_ms": p.get("jit_ms"), "root": _strip(root), "findings": fs, "verdict": verdict,
            "tables": sorted({n["rel"] for n in nodes if n["rel"]})}
