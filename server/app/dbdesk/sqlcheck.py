"""A check of one SQL query in code (no parser library, no database): the patterns that stop an index from being used or make a
query slower than it needs to be, and the index the WHERE / JOIN / ORDER BY ask for - equality columns first, then a range or the
sort. Suggestions only: the SQLite lab or her own EXPLAIN proves them. A query is DATA."""
from __future__ import annotations

import re
from typing import Any

MAX = 100_000
KW = {"select", "from", "where", "and", "or", "not", "in", "is", "null", "like", "ilike", "between", "join", "left", "right", "inner", "outer",
      "on", "group", "by", "order", "having", "limit", "offset", "as", "asc", "desc", "case", "when", "then", "else", "end", "exists", "distinct",
      "true", "false", "interval", "now", "current_date", "current_timestamp", "lower", "upper", "date", "coalesce", "cast"}


def _clean(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return re.sub(r"\s+", " ", sql).strip().rstrip(";")


def _no_str(sql: str) -> str:
    return re.sub(r"'(?:[^']|'')*'", "'?'", sql)


def aliases(sql: str) -> dict[str, str]:
    """alias -> table from FROM / JOIN."""
    out: dict[str, str] = {}
    for m in re.finditer(r"\b(?:FROM|JOIN)\s+([\w.\"`]+)(?:\s+(?:AS\s+)?([A-Za-z_]\w*))?", sql, re.I):
        t = m[1].strip('"`').split(".")[-1]
        a = m[2] if m[2] and m[2].lower() not in KW else t
        out[a] = t
        out[t] = t
    return out


def _clause(sql: str, name: str, ends: tuple[str, ...]) -> str:
    m = re.search(r"\b" + name + r"\b(.*?)(?=\b(?:" + "|".join(ends) + r")\b|$)", sql, re.I | re.S)
    return m[1] if m else ""


def _colref(x: str, al: dict[str, str], default: str) -> tuple[str, str] | None:
    x = x.strip().strip('"`')
    if "." in x:
        a, c = x.split(".", 1)
        return (al.get(a, a), c.strip('"`'))
    if x.lower() in KW or not re.match(r"[A-Za-z_]\w*$", x):
        return None
    return (default, x)


def check(sql: str) -> dict[str, Any]:
    raw = str(sql or "")[:MAX]
    q = _clean(raw)
    if not re.match(r"(WITH|SELECT|UPDATE|DELETE|INSERT)\b", q, re.I):
        return {"ok": False, "error": "Paste one SELECT, UPDATE, DELETE or INSERT ... SELECT query."}
    s = _no_str(q)
    al = aliases(s)
    tabs = list(dict.fromkeys(al.values()))
    first = tabs[0] if tabs else ""
    issues: list[dict[str, Any]] = []

    def add(sev, say, fix, code=""):
        issues.append({"sev": sev, "say": say, "fix": fix, "code": code})

    where = _clause(s, "WHERE", ("GROUP BY", "ORDER BY", "HAVING", "LIMIT", "OFFSET", "UNION", "RETURNING", "FOR UPDATE"))
    order = _clause(s, "ORDER BY", ("LIMIT", "OFFSET", "FOR UPDATE", "UNION"))
    if re.search(r"SELECT\s+(DISTINCT\s+)?\*", s, re.I) or re.search(r"SELECT\s+\w+\.\*", s, re.I):
        add("warn", "SELECT * reads every column", "Name the columns you use: less data moves, and a covering index becomes possible.")
    for m in re.finditer(r"([\w.]+)\s+(?:I?LIKE)\s+'\?'", s, re.I):
        lit = re.search(re.escape(m[0]).replace(r"'\?'", r"('(?:[^']|'')*')"), q, re.I)
        if lit and lit[1].startswith("'%"):
            add("bad", f"{m[1]} LIKE '%...' starts with a wildcard", "A B-tree index cannot help a leading %. Use a trigram index (pg_trgm) or full-text search.", lit[0])
    for m in re.finditer(r"\b(lower|upper|date|trim|coalesce|cast|substring|extract|to_char|year|month|date_trunc)\s*\(\s*([\w.]+)[^)]*\)\s*(=|<|>|<=|>=|IN|LIKE|BETWEEN)", where, re.I):
        add("bad", f"{m[1]}({m[2]}) in the WHERE hides the column from its index",
            f"Compare the bare column (e.g. a range on the date), or create an expression index on {m[1]}({m[2]}).", m[0])
    if re.search(r"[\w.]+\s*[-+*/]\s*\d+\s*(=|<|>|<=|>=)", where):
        add("warn", "Arithmetic on a column in the WHERE", "Move the arithmetic to the other side so the column stands alone.")
    if re.search(r"\bNOT\s+IN\s*\(\s*SELECT", s, re.I):
        add("bad", "NOT IN (SELECT ...) returns nothing if the subquery has a NULL", "Use NOT EXISTS (...): it handles NULL correctly and plans as an anti-join.")
    if re.search(r"\bOR\b", where, re.I) and len(set(re.findall(r"([\w.]+)\s*=", where))) > 1:
        add("info", "OR across different columns", "Each side may need its own index; a UNION ALL of two indexed queries is often faster.")
    off = re.search(r"\bOFFSET\s+(\d+)", s, re.I) or re.search(r"\bLIMIT\s+(\d+)\s*,", s, re.I)
    if off and int(off[1]) >= 1000:
        add("warn", f"OFFSET {off[1]} reads and throws away {int(off[1]):,} rows", "Page by the last key seen (WHERE id > :last ORDER BY id LIMIT n) instead.")
    if order and not re.search(r"\bLIMIT\b|\bFETCH\s+FIRST\b|\bTOP\b", s, re.I) and re.match(r"SELECT", s, re.I):
        add("info", "ORDER BY without LIMIT sorts every matching row", "Fine for reports; for a page of results add LIMIT.")
    if re.match(r"(UPDATE|DELETE)\b", s, re.I) and not where.strip():
        add("bad", "UPDATE / DELETE without WHERE changes every row", "Add the WHERE - or, if every row really is meant, TRUNCATE / a batch job.")
    if re.search(r"\bIN\s*\(\s*(?:'\?'|\d+)(?:\s*,\s*(?:'\?'|\d+)){999,}", s):
        add("warn", "An IN list of 1,000+ values", "Join to a temporary table or an array parameter (= ANY($1)).")
    if len(re.findall(r"\bJOIN\b", s, re.I)) >= 8:
        add("info", "8 or more joins", "Above join_collapse_limit (8) PostgreSQL stops reordering joins: write them in a good order, or raise the limit.")
    if re.search(r"SELECT\s+COUNT\s*\(\s*\*\s*\)\s+FROM\s+\w+\s*$", s, re.I):
        add("info", "COUNT(*) of a whole table reads all of it", "For a rough number, the planner's estimate (pg_class.reltuples / information_schema) is instant.")
    # the index the query asks for, per table: equality columns, then one range column or the ORDER BY columns
    want: dict[str, dict[str, list[str]]] = {}

    def put(ref, kind):
        if ref:
            t, c = ref
            w = want.setdefault(t, {"eq": [], "range": [], "order": [], "join": []})
            if c not in w[kind] and c not in w["eq"]:
                w[kind].append(c)

    for m in re.finditer(r"([\w.\"`]+)\s*(=|<>|!=|<=|>=|<|>|\bIN\b|\bBETWEEN\b|\bIS\b)\s*([\w.\"`']+|\(|\?)", where, re.I):
        left, op, right = m[1], m[2].upper(), m[3]
        if left.lower() in KW or re.match(r"\d", left):
            continue
        if op in ("<>", "!=", "IS"):
            continue
        rightcol = _colref(right, al, first) if re.match(r"[A-Za-z_]", right) and right.lower() not in KW and "'" not in right else None
        if rightcol and rightcol[0] in tabs and op == "=":
            put(_colref(left, al, first), "join")
            put(rightcol, "join")
            continue
        put(_colref(left, al, first), "eq" if op in ("=", "IN") else "range")
    for m in re.finditer(r"\bON\s+(.+?)(?=\bJOIN\b|\bWHERE\b|\bGROUP\b|\bORDER\b|\bLIMIT\b|\bLEFT\b|\bINNER\b|$)", s, re.I):
        for a, b in re.findall(r"([\w.\"`]+)\s*=\s*([\w.\"`]+)", m[1]):
            put(_colref(a, al, first), "join")
            put(_colref(b, al, first), "join")
    for part in order.split(","):
        r = _colref(part.strip().split()[0] if part.strip() else "", al, first)
        put(r, "order")
    suggest = []
    for t, w in want.items():
        if t not in tabs:
            continue
        cols = list(w["eq"])
        if w["range"]:
            cols.append(w["range"][0])
        elif w["order"] and (len(tabs) == 1 or w["eq"]):
            cols += [c for c in w["order"] if c not in cols]
        join_only = [c for c in w["join"] if c not in cols]
        if cols == ["id"] and not w["eq"]:
            cols = []
        if cols:
            suggest.append({"table": t, "cols": cols[:4], "why": ("equality on " + ", ".join(w["eq"]) if w["eq"] else "") +
                            (("; " if w["eq"] else "") + "range on " + w["range"][0] if w["range"] else "") +
                            (("; " if w["eq"] else "") + "then the ORDER BY" if (not w["range"] and w["order"] and cols[len(w["eq"]):]) else ""),
                            "sql": f"CREATE INDEX ON {t} ({', '.join(cols[:4])});"})
        for c in join_only:
            if not (t in tabs and c in ("id",)):
                suggest.append({"table": t, "cols": [c], "why": "join column", "sql": f"CREATE INDEX ON {t} ({c});"})
    order_ = {"bad": 0, "warn": 1, "info": 2}
    issues.sort(key=lambda x: order_[x["sev"]])
    counts = {k: sum(1 for i in issues if i["sev"] == k) for k in order_}
    return {"ok": True, "sql": q, "tables": tabs, "issues": issues, "counts": counts, "suggest": suggest[:8],
            "verdict": (f"{counts['bad']} serious, {counts['warn']} to check, {counts['info']} note(s)." if issues else "No problems found by these checks.") +
                       (f" {len(suggest)} index suggestion(s) - prove them in the lab or with your own EXPLAIN." if suggest else "")}
