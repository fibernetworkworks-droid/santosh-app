"""The proof lab: her schema built in a throwaway in-memory SQLite database on the server, filled with generated rows (no data of
hers), and her query run before and after an index - the plan SQLite chooses, the time (best of three) and the row count, so a
suggestion is shown to change the work, not just claimed. It is SQLite's planner, not her server's: it proves an index is usable
and how much work it saves, not her production timings - the page says so. A query and a schema are DATA; only SELECT runs."""
from __future__ import annotations

import hashlib
import random
import re
import sqlite3
import time
from typing import Any

from . import schema as SC

MAX_ROWS = 200_000
MAX_TOTAL = 600_000
DEADLINE_S = 12.0


class LabError(ValueError):
    pass


def _lite_type(t: str) -> str:
    t = t.lower()
    if re.search(r"int|serial", t):
        return "INTEGER"
    if re.search(r"numeric|decimal|float|double|real|money", t):
        return "REAL"
    if re.search(r"bool", t):
        return "INTEGER"
    return "TEXT"


def _kind(col: dict[str, Any], t: dict[str, Any], fks: dict[str, str]) -> str:
    n, ty = col["name"].lower(), col["type"].lower()
    if col["name"] in t["pk"] and len(t["pk"]) == 1:
        return "pk"
    if col["name"] in fks:
        return "fk"
    if re.search(r"time|date", ty) or re.search(r"_at$|_on$|date|time", n):
        return "time"
    if re.search(r"bool", ty) or n.startswith(("is_", "has_")):
        return "bool"
    if re.search(r"status|state|kind|type|category|level|country|currency|role|plan|tier|channel", n):
        return "cat"
    if re.search(r"email", n):
        return "email"
    if _lite_type(ty) == "INTEGER":
        return "int"
    if _lite_type(ty) == "REAL":
        return "num"
    return "text"


CAT = ["paid", "pending", "shipped", "cancelled", "refunded"]


def build(schema_sql: str, rows: dict[str, int] | int = 50_000, seed: int = 7, only: str = "") -> tuple[sqlite3.Connection, dict[str, Any]]:
    d = SC.parse(schema_sql)
    if not d["tables"]:
        raise LabError("The lab needs CREATE TABLE statements for the tables the query reads.")
    if only:
        names = {t["name"].lower() for t in d["tables"] if re.search(r"\b" + re.escape(t["name"]) + r"\b", only, re.I)}
        if not names:
            raise LabError("None of the query's tables is in the schema you gave.")
        grow = True
        while grow:
            grow = False
            for t in d["tables"]:
                if t["name"].lower() in names:
                    for fk in t["fks"]:
                        if fk["ref"].lower() not in names:
                            names.add(fk["ref"].lower())
                            grow = True
        d["tables"] = [t for t in d["tables"] if t["name"].lower() in names]
    parents = {fk["ref"].lower() for t in d["tables"] for fk in t["fks"] if fk["ref"].lower() != t["name"].lower()}
    con = sqlite3.connect(":memory:", check_same_thread=False)
    con.execute("PRAGMA journal_mode=OFF")
    con.execute("PRAGMA synchronous=OFF")
    rnd = random.Random(seed)
    made: dict[str, int] = {}
    total = 0
    order = []
    left = list(d["tables"])
    while left:          # parents before children, so foreign keys draw from a known size
        progress = False
        for t in list(left):
            if all(fk["ref"].lower() in {x["name"].lower() for x in order} or fk["ref"].lower() == t["name"].lower() or
                   fk["ref"].lower() not in {x["name"].lower() for x in d["tables"]} for fk in t["fks"]):
                order.append(t)
                left.remove(t)
                progress = True
        if not progress:
            order += left
            break
    for t in order:
        n = rows.get(t["name"], rows.get("*", 50_000)) if isinstance(rows, dict) else (rows // 20 if t["name"].lower() in parents else rows)
        n = max(1, min(int(n), MAX_ROWS))
        if total + n > MAX_TOTAL:
            n = max(1, MAX_TOTAL - total)
        fks = {fk["cols"][0]: fk["ref"] for fk in t["fks"] if fk["cols"]}
        cols = t["columns"]
        if not cols:
            continue
        defs = []
        for c in cols:
            ty = _lite_type(c["type"])
            pk = " PRIMARY KEY" if c["name"] in t["pk"] and len(t["pk"]) == 1 and ty == "INTEGER" else ""
            defs.append(f'"{c["name"]}" {ty}{pk}')
        if len(t["pk"]) > 1:
            defs.append("PRIMARY KEY (" + ", ".join(f'"{c}"' for c in t["pk"]) + ")")
        con.execute(f'CREATE TABLE "{t["name"]}" ({", ".join(defs)})')
        kinds = [_kind(c, t, fks) for c in cols]
        base = 1_767_225_600   # 2026-01-01 UTC
        data = []
        for i in range(1, n + 1):
            row = []
            for c, k in zip(cols, kinds):
                if k == "pk":
                    row.append(i)
                elif k == "fk":
                    row.append(rnd.randint(1, max(1, made.get(fks[c["name"]], n))))
                elif k == "time":
                    row.append(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(base - rnd.randint(0, 365 * 86400))))
                elif k == "bool":
                    row.append(rnd.random() < 0.3)
                elif k == "cat":
                    row.append(CAT[min(4, int(rnd.expovariate(1.2)))])
                elif k == "email":
                    row.append(f"user{i}@example.com")
                elif k == "int":
                    row.append(rnd.randint(1, 1000))
                elif k == "num":
                    row.append(round(rnd.uniform(1, 5000), 2))
                else:
                    row.append(f"{c['name']}-{rnd.randint(1, max(10, n // 4))}")
            data.append(row)
        con.executemany(f'INSERT INTO "{t["name"]}" VALUES ({", ".join("?" * len(cols))})', data)
        made[t["name"]] = n
        total += n
    existing = []
    for ix in d["indexes"]:
        if ix["table"] in made and ix["cols"] and not ix.get("partial"):
            try:
                con.execute(f'CREATE {"UNIQUE " if ix["unique"] else ""}INDEX "{ix["name"] or "ix_" + "_".join(ix["cols"])}" ON "{ix["table"]}" '
                            f'({", ".join(chr(34) + c + chr(34) for c in ix["cols"])})')
                existing.append(ix["name"])
            except sqlite3.Error:
                pass
    con.execute("ANALYZE")
    con.commit()
    return con, {"rows": made, "indexes": existing}


_DENY = {sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH, sqlite3.SQLITE_PRAGMA, sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
         sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_ALTER_TABLE, sqlite3.SQLITE_CREATE_TRIGGER}


def _guard(con: sqlite3.Connection, allow_index: bool = False) -> None:
    def auth(action, *_a):
        if action in _DENY:
            return sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_CREATE_INDEX and not allow_index:
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    con.set_authorizer(auth)


def to_sqlite(sql: str) -> str:
    q = re.sub(r"--[^\n]*", " ", str(sql or ""))
    q = re.sub(r"/\*.*?\*/", " ", q, flags=re.S).strip().rstrip(";")
    if ";" in q:
        raise LabError("One query only.")
    if not re.match(r"(WITH|SELECT)\b", q, re.I):
        raise LabError("The lab runs SELECT queries only.")
    q = re.sub(r"::\s*[a-z_ ]+(\[\])?(\(\d+(,\s*\d+)?\))?", "", q, flags=re.I)
    q = re.sub(r"\bILIKE\b", "LIKE", q, flags=re.I)
    q = re.sub(r"\bNOW\(\)", "CURRENT_TIMESTAMP", q, flags=re.I)
    q = re.sub(r"\bTRUE\b", "1", q, flags=re.I)
    q = re.sub(r"\bFALSE\b", "0", q, flags=re.I)
    q = re.sub(r"`", '"', q)
    q = re.sub(r"\bFETCH\s+FIRST\s+(\d+)\s+ROWS?\s+ONLY", r"LIMIT \1", q, flags=re.I)
    return q


def _run(con: sqlite3.Connection, q: str) -> dict[str, Any]:
    t_end = time.monotonic() + DEADLINE_S
    con.set_progress_handler(lambda: 1 if time.monotonic() > t_end else 0, 20_000)
    try:
        plan = [r[3] for r in con.execute("EXPLAIN QUERY PLAN " + q).fetchall()]
        best, n, h = None, 0, ""
        for _ in range(3):
            t0 = time.perf_counter()
            rows = con.execute(q).fetchall()
            dt = (time.perf_counter() - t0) * 1000
            best = dt if best is None else min(best, dt)
            n = len(rows)
            h = hashlib.sha1(repr(sorted(map(repr, rows))).encode()).hexdigest()[:12]
            if dt > 4000:
                break
        return {"plan": plan, "ms": round(best or 0, 4), "rows": n, "hash": h, "full_scans": [p for p in plan if p.startswith("SCAN") and "USING" not in p]}
    except sqlite3.OperationalError as e:
        if "interrupted" in str(e):
            raise LabError(f"The query ran for more than {DEADLINE_S:.0f} seconds in the lab - fewer rows, or a narrower query.")
        if "not authorized" in str(e):
            raise LabError("That is not allowed in the lab: it only reads the generated tables.")
        raise LabError(f"SQLite could not run it: {e}. The lab speaks SQLite - date functions and some types differ from your database.")
    finally:
        con.set_progress_handler(None, 0)


def index_sql(text: str) -> list[str]:
    out = []
    for st in SC.split(str(text or "")):
        m = re.match(r"CREATE\s+(UNIQUE\s+)?INDEX\s+(?:CONCURRENTLY\s+)?(?:IF\s+NOT\s+EXISTS\s+)?(\w*)\s*ON\s+([\w.\"`]+)\s*(?:USING\s+\w+\s*)?\((.*?)\)\s*$", st, re.I | re.S)
        if not m:
            raise LabError("Only CREATE INDEX statements can be tried in the lab: " + st[:80])
        cols = [re.split(r"\s+", c.strip())[0].strip('"`') for c in SC._parts(m[4])]
        if not all(re.match(r"[A-Za-z_]\w*$", c) for c in cols):
            raise LabError("The lab tries plain column indexes (no expressions): " + st[:80])
        t = m[3].strip('"`').split(".")[-1]
        name = m[2] or f"lab_{t}_{'_'.join(cols)}"
        out.append(f'CREATE {"UNIQUE " if m[1] else ""}INDEX "{name}" ON "{t}" ({", ".join(chr(34) + c + chr(34) for c in cols)})')
    return out[:6]


def _ms(v: float) -> str:
    return f"{v:.3f} ms" if v < 1 else f"{v:.2f} ms" if v < 10 else f"{v:.1f} ms"


def prove(schema_sql: str, query: str, indexes: str, rows: int = 50_000) -> dict[str, Any]:
    q = to_sqlite(query)
    ix = index_sql(indexes) if str(indexes or "").strip() else []
    t0 = time.perf_counter()
    con, info = build(schema_sql, rows, only=q)
    try:
        _guard(con)
        before = _run(con, q)
        after = None
        if ix:
            con.set_authorizer(None)
            for s in ix:
                try:
                    con.execute(s)
                except sqlite3.Error as e:
                    raise LabError(f"The index could not be made: {e}.")
            con.execute("ANALYZE")
            _guard(con)
            after = _run(con, q)
    finally:
        con.close()
    out: dict[str, Any] = {"ok": True, "sqlite": sqlite3.sqlite_version, "query": q, "indexes": ix, "rows": info["rows"], "existing": info["indexes"],
                           "before": before, "after": after, "build_s": round(time.perf_counter() - t0, 2),
                           "note": "SQLite's planner on generated rows: it shows whether the index is used and how the work changes, "
                                   "not your server's timings. Check with EXPLAIN (ANALYZE) on your own database."}
    if after:
        same = before["hash"] == after["hash"]
        speed = before["ms"] / after["ms"] if after["ms"] > 0 else None
        used = [p for p in after["plan"] if any(n.split('"')[1] in p for n in ix)]
        out["same_result"] = same
        out["speedup"] = round(min(speed, 9999), 1) if speed else None
        out["used"] = bool(used)
        sp = (f" ({speed:,.0f}x faster)" if speed >= 10 else f" ({speed:.1f}x)") if speed and used else ""
        out["verdict"] = ((f"With the index SQLite {'used it' if used else 'did not use it'}: {_ms(before['ms'])} → {_ms(after['ms'])}" + sp + (". Same rows returned." if same else ". The result changed - check the query.")))
    else:
        out["verdict"] = f"{before['rows']:,} row(s) in {_ms(before['ms'])}" + (f"; full scan of {', '.join(p[5:].split()[0] for p in before['full_scans'])}" if before["full_scans"] else "") + "."
    return out
