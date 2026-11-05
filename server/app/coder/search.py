"""HOOLA CODER search - the three-layer discipline (v0.473.0).

claude-mem's token economics, ported: layer 1 `search` returns an INDEX (ids + titles, tens of
tokens per row), layer 2 `timeline` returns the chronological neighbourhood of an anchor, layer 3
`get_observations` returns full rows for chosen ids only. Never fetch details before filtering.

Keyword leg: FTS5 with bm25 rank when available (quoted tokens ANDed), escalating to any-term
widening (>= 3 tokens, rarest first) and finally a LIKE substring fallback when FTS5 is missing.
No vector store in v1 - that is the documented upgrade path, not a silent absence.
"""
from __future__ import annotations

import json
import re

from . import store

_MAX_TEXT_BYTES = 32 * 1024


def _fts_match(query: str) -> str:
    """Quoted tokens ANDed; punctuation-only tokens dropped (the claude-mem buildFTSMatchQuery rule)."""
    toks = [t for t in re.findall(r"\w+", query or "") if not re.fullmatch(r"[\W_]+", t)]
    return " AND ".join(f'"{t}"' for t in toks)


def _fts_any(query: str) -> str:
    toks = [t for t in re.findall(r"\w+", query or "")]
    if len(toks) < 3:
        return ""
    return " OR ".join(f'"{t}"' for t in toks[:40])


def _like(query: str) -> str:
    toks = [t for t in re.findall(r"\w{3,}", query or "")][:6]
    return " AND ".join(toks)


def search(tenant: str, query: str, limit: int = 20, obs_type: str | None = None,
           date_start: str | None = None, date_end: str | None = None) -> dict:
    """Layer 1: the index. {observations: [{id, conv, type, title, subtitle, created_at}], total}."""
    store.ensure()
    limit = max(1, min(int(limit or 20), 100))
    rows: list[dict] = []
    if store.fts_available() and _fts_match(query):
        q = _fts_match(query)
        sql = ("SELECT o.id, o.conv, o.type, o.title, o.subtitle, o.created_at, o.created_epoch "
               "FROM obs_fts JOIN observations o ON o.id = obs_fts.rowid WHERE obs_fts MATCH ? "
               "AND o.tenant=? AND o.superseded_by=0")
        args: list = [q, tenant]
        rows = _run(sql, args, obs_type, date_start, date_end, limit)
        if not rows:
            q2 = _fts_any(query)
            if q2:
                sql2 = sql.replace("MATCH ? AND", "MATCH ? AND")  # same shape, OR-ed terms
                rows = _run(sql2, [q2, tenant], obs_type, date_start, date_end, limit)
    if not rows:
        like = _like(query)
        if like:
            cond = " AND ".join(["(o.title LIKE ? OR o.narrative LIKE ? OR o.subtitle LIKE ?)"] *
                                len(like.split(" AND ")))
            args: list = []
            for tok in like.split(" AND "):
                args += [f"%{tok}%", f"%{tok}%", f"%{tok}%"]
            sql = f"SELECT o.id, o.conv, o.type, o.title, o.subtitle, o.created_at, o.created_epoch " \
                  f"FROM observations o WHERE o.tenant=? AND o.superseded_by=0 AND {cond}"
            rows = _run(sql, [tenant] + args, obs_type, date_start, date_end, limit)
    return {"query": query, "total": len(rows), "observations": rows[:limit]}


def _run(sql: str, args: list, obs_type: str | None, date_start: str | None, date_end: str | None,
         limit: int) -> list[dict]:
    if obs_type:
        sql += " AND o.type=?"
        args.append(obs_type)
    if date_start:
        sql += " AND o.created_at >= ?"
        args.append(date_start)
    if date_end:
        sql += " AND o.created_at <= ?"
        args.append(date_end + "z" if len(date_end) == 10 else date_end)
    sql += " ORDER BY o.created_epoch DESC, o.id DESC LIMIT ?"
    args.append(limit)
    with store.db() as c:
        try:
            return [dict(r) for r in c.execute(sql, args).fetchall()]
        except Exception:
            return []


def timeline(tenant: str, anchor: str | None, depth_before: int = 5, depth_after: int = 5) -> dict:
    """Layer 2: the neighbourhood. anchor = observation id | ISO date prefix; None = newest edge."""
    store.ensure()
    depth_before = max(0, min(int(depth_before or 5), 50))
    depth_after = max(0, min(int(depth_after or 5), 50))
    with store.db() as c:
        if anchor and anchor.isdigit():
            row = c.execute("SELECT id, conv, created_epoch FROM observations "
                            "WHERE id=? AND tenant=? AND superseded_by=0",
                            (int(anchor), tenant)).fetchone()
            if row is None:
                return {"anchor": anchor, "rows": []}
            ep, conv = row["created_epoch"], row["conv"]
            before = c.execute(
                "SELECT * FROM observations WHERE conv=? AND superseded_by=0 AND "
                "(created_epoch < ? OR (created_epoch = ? AND id < ?)) "
                "ORDER BY created_epoch DESC, id DESC LIMIT ?",
                (conv, ep, ep, row["id"], depth_before)).fetchall()
            after = c.execute(
                "SELECT * FROM observations WHERE conv=? AND superseded_by=0 AND "
                "(created_epoch > ? OR (created_epoch = ? AND id > ?)) "
                "ORDER BY created_epoch ASC, id ASC LIMIT ?",
                (conv, ep, ep, row["id"], depth_after)).fetchall()
            mid = [dict(c.execute("SELECT * FROM observations WHERE id=? AND superseded_by=0",
                                  (row["id"],)).fetchone() or {'id': row['id']})]
        elif anchor:
            rows = c.execute(
                "SELECT * FROM observations WHERE tenant=? AND superseded_by=0 AND created_at LIKE ? "
                "ORDER BY created_epoch ASC, id ASC LIMIT 200", (tenant, anchor + "%")).fetchall()
            return {"anchor": anchor, "rows": [dict(r) for r in rows][:depth_before + depth_after + 1]}
        else:
            newest = c.execute("SELECT created_epoch FROM observations WHERE tenant=? "
                               "AND superseded_by=0 ORDER BY created_epoch DESC LIMIT 1",
                               (tenant,)).fetchone()
            ep = newest[0] if newest else 0
            before = c.execute("SELECT * FROM observations WHERE tenant=? AND superseded_by=0 "
                               "AND created_epoch <= ? ORDER BY created_epoch DESC, id DESC LIMIT ?",
                               (tenant, ep, depth_before + 1)).fetchall()
            after, mid = [], []
            if before:
                mid = [dict(before[0])]
                before = before[1:]
            return {"anchor": anchor, "rows": [dict(r) for r in reversed(before)] + mid + after}
    out = [dict(r) for r in reversed(before)] + mid + [dict(r) for r in after]
    return {"anchor": anchor, "rows": out}


def get_observations(ids: list[int]) -> list[dict]:
    """Layer 3: full rows, caller's order, JSON fields decoded."""
    rows = store.get_observations([int(i) for i in ids or [] if str(i).isdigit()])
    for r in rows:
        for k in ("facts", "concepts", "files_read", "files_modified", "reinforcement_dates"):
            try:
                r[k] = json.loads(r.get(k) or "[]")
            except Exception:
                r[k] = []
    return rows


# ---------------------------------------------------------------- renderers (text, for the model)

def render_index(result: dict) -> str:
    lines = ["# search results", "| ID | date | type | title |", "|---|---|---|---|"]
    for r in result["observations"]:
        lines.append(f"| {r['id']} | {str(r['created_at'])[:16]} | {r['type']} | {r['title'][:90]} |")
    lines.append("Fetch details with get_observations([IDs]). Full raw tool I/O via "
                 "/api/coder/tool-uses with the observation's turn.")
    text = "\n".join(lines)
    return text[:_MAX_TEXT_BYTES]


def render_timeline(t: dict) -> str:
    lines = [f"# timeline around {t.get('anchor') or 'newest'}"]
    day = ""
    for r in t["rows"]:
        d = str(r["created_at"])[:10]
        if d != day:
            day = d
            lines.append(f"### {d}")
        lines.append(f"{r['id']} {str(r['created_at'])[11:16]} {r['type']}: {r['title'][:100]}")
    return "\n".join(lines)[:_MAX_TEXT_BYTES]
