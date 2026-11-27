"""v0.999.280 db_desk: the Database Engine Developer's tool - query plans read (PostgreSQL, MySQL, SQLite), queries and schemas
checked, index ideas proved in a throwaway SQLite lab on generated rows, benchmark runs read and compared. Nothing touches her
database."""
from __future__ import annotations

import asyncio

from .tools import Ctx, ToolError

DBENG_TOOLS = [
    {"name": "db_desk", "description": (
        "Database engine work for her (Database Engine Developer desk). action=plan (text = EXPLAIN output: PostgreSQL EXPLAIN "
        "(ANALYZE, BUFFERS) text or FORMAT JSON, MySQL EXPLAIN ANALYZE / FORMAT=TREE / the classic table, SQLite EXPLAIN QUERY PLAN) "
        "-> the steps with planned vs real rows and time, and findings: full scans that throw rows away (with the index to try), "
        "estimates far off (ANALYZE), sorts / hashes that spilled to disk (work_mem), nested loops repeating a scan, lossy bitmaps, "
        "heap fetches. action=query (text = one SQL query) -> patterns that stop an index being used (function on a column, leading "
        "%, NOT IN with NULLs, big OFFSET, SELECT *) and the index the WHERE / JOIN / ORDER BY ask for. action=schema (text = CREATE "
        "TABLE / CREATE INDEX statements) -> missing primary keys, foreign keys without an index, redundant indexes, timestamps "
        "without time zone, money in floats. action=lab (text = a SELECT, indexes = CREATE INDEX statements, schema optional - else "
        "her latest schema) -> runs it in a throwaway SQLite database on generated rows before and after the index: the plan, the "
        "time, whether the index was used and the same rows came back. SQLite, not her server: say so. action=bench (text = pgbench / "
        "sysbench / YCSB / HammerDB output or latencies; baseline = id of an earlier run) -> the numbers and the change. "
        "action=list / show (id) / mark (id, status open | fixed | ignored). You never connect to her database or change it."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["plan", "query", "schema", "lab", "bench", "list", "show", "mark"]},
         "text": {"type": "string"}, "title": {"type": "string"}, "schema": {"type": "string"}, "indexes": {"type": "string"},
         "rows": {"type": "integer"}, "baseline": {"type": "string"}, "id": {"type": "string"},
         "status": {"type": "string", "enum": ["open", "fixed", "ignored"]}},
         "required": ["action"]}},
]
DBENG_LABELS = {"db_desk": "Reading query plans / checking the database"}


def _short(d: dict) -> dict:
    r = d.get("result") or {}
    out = {k: d[k] for k in ("id", "number", "kind", "title", "status", "note") if k in d}
    k = d.get("kind")
    if k == "plan":
        out.update(verdict=r.get("verdict"), engine=r.get("engine"), total_ms=r.get("total_ms"), analyzed=r.get("analyzed"),
                   findings=[{x: f.get(x) for x in ("sev", "say", "fix")} for f in (r.get("findings") or [])[:12]])
    elif k in ("query", "schema"):
        out.update(verdict=r.get("verdict"), issues=[{x: i.get(x) for x in ("sev", "say", "fix", "table")} for i in (r.get("issues") or [])[:20]],
                   suggest=r.get("suggest"))
    elif k == "lab":
        out.update(verdict=r.get("verdict"), indexes=r.get("indexes"), rows=r.get("rows"), before=r.get("before"), after=r.get("after"),
                   used=r.get("used"), same_result=r.get("same_result"), note_lab=r.get("note"))
    elif k == "bench":
        out.update({x: r.get(x) for x in ("tool", "tps", "qps", "lat_avg", "lat_p95", "lat_p99", "lat_max", "errors", "clients")}, compare=r.get("compare"))
    return out


async def db_desk(ctx: Ctx, action="list", **kw):
    from ..dbdesk import service as S
    t = ctx.tenant_id
    g = lambda k: str(kw.get(k) or "")   # noqa: E731
    try:
        if action in ("plan", "query", "schema", "lab", "bench"):
            d = await asyncio.to_thread(S.add, t, action, kw.get("text"), g("title"), schema=kw.get("schema"), indexes=kw.get("indexes"),
                                        rows=kw.get("rows"), baseline=g("baseline"))
            return {**_short(d), "note": "Say only what this shows. The desk page has the full report."}
        if action == "list":
            return {"items": await asyncio.to_thread(S.items, t, "", 30)}
        if action == "show":
            return _short(await asyncio.to_thread(S.get, t, g("id")))
        if action == "mark":
            return _short(await asyncio.to_thread(S.mark, t, g("id"), g("status") or "fixed"))
    except S.DbError as e:
        raise ToolError(str(e))
    raise ToolError("Unknown db_desk action.")


DBENG_HANDLERS = {"db_desk": db_desk}
