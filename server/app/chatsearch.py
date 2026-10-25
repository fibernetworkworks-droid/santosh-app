"""v0.178 Console search power (CONSOLE_V2 phase 4): SQLite FTS5 over her chat messages.

The old search (v0.162) was a LIKE scan over `messages.display` per query. This module keeps the same
result shape but backs it with an FTS5 index: prefix matching, Hinglish / Devanagari via the unicode61
tokenizer, bm25 ranking and real snippet() windows with <<match>> marks for the console to highlight.

Index design (kept deliberately simple):
- `messages_fts` is a standalone FTS5 table whose rowid IS `messages.id` (Message rows are append-only:
  Edit / Dobara create NEW rows as branch versions, nothing updates in place).
- `search_meta` keeps the watermark (the highest indexed message id); every search first indexes whatever
  is newer, in batches, so a fresh server or a fresh database self-heals on the first query.
- Everything that can change at runtime is NOT baked into the index: tenant, soft-deleted chats, hidden
  branch versions (`hid:`) and taken-back messages are filtered at QUERY time by joining the live tables,
  exactly like the old LIKE search. The index only ever accelerates text matching, so branch switches,
  deletes and take-backs can never leave stale results behind.
- If the host SQLite has no FTS5 (rare), `available()` is False and `chats.search` falls back to the old
  LIKE path unchanged.
"""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy import text as sqltext

from .db import Message, now, session

_FTS_NEVER = False                  # cached NO only (no FTS5 on this SQLite); YES is re-verified per DB, tests included
_BATCH = 2000                       # messages indexed per pass (first call backfills in these chunks)
_MAX_PER_CALL = 20000               # hard cap per search call so one cold query can never stall the server


def available() -> bool:
    """True when the FTS5 virtual table exists on this SQLite. The CREATE IF NOT EXISTS runs every time (cheap,
    idempotent DDL) because each database needs its own tables — fresh test DBs and new servers included. Only a
    hard NO (SQLite without FTS5) is cached, so the LIKE fallback never pays the exception cost again."""
    global _FTS_NEVER
    if _FTS_NEVER:
        return False
    try:
        with session() as s:
            s.execute(sqltext(
                "CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5("
                "text, conv UNINDEXED, role UNINDEXED, tokenize='unicode61')"))
            s.execute(sqltext("CREATE TABLE IF NOT EXISTS search_meta (key TEXT PRIMARY KEY, value TEXT)"))
            s.commit()
        return True
    except Exception:                # pragma: no cover - only on sqlite builds without FTS5
        _FTS_NEVER = True
        return False


def _watermark(s) -> int:
    row = s.execute(sqltext("SELECT value FROM search_meta WHERE key='indexed_id'")).first()
    return int(row[0]) if row and str(row[0]).isdigit() else 0


def ensure_index() -> bool:
    """Index every eligible message newer than the watermark. Cheap when nothing is new (one SELECT max(id))."""
    if not available():
        return False
    with session() as s:
        if _watermark(s) >= (s.execute(sqltext("SELECT COALESCE(MAX(id), 0) FROM messages")).scalar() or 0):
            return True
    done = 0
    while done < _MAX_PER_CALL:
        with session() as s:
            lo = _watermark(s)
            rows = s.execute(sqltext(
                "SELECT id, display, conversation_id, role FROM messages "
                "WHERE id > :lo AND role IN ('user', 'assistant') AND display IS NOT NULL "
                "ORDER BY id LIMIT :b"), {"lo": lo, "b": _BATCH}).all()
            if not rows:
                return True
            top = rows[-1][0]
            for mid, display, conv, role in rows:
                s.execute(sqltext(
                    "INSERT OR IGNORE INTO messages_fts(rowid, text, conv, role) VALUES (:i, :t, :c, :r)"),
                    {"i": mid, "t": display, "c": conv, "r": role})
            s.execute(sqltext("INSERT OR REPLACE INTO search_meta (key, value) VALUES ('indexed_id', :w)"),
                      {"w": str(top)})
            s.commit()
            done += len(rows)
            if len(rows) < _BATCH:
                return True
    return True


def match_query(q: str) -> str:
    """Her words -> an FTS5 MATCH string: every word becomes a quoted prefix token (AND), "quotes" stay a phrase."""
    toks = _tokens(q)
    if not toks:
        return ""
    q = (q or "").strip()
    if len(q) > 1 and q[0] == q[-1] == '"':                      # "exact phrase"
        inner = q[1:-1].strip()
        return f'"{inner}"' if inner else ""
    return " ".join(f'"{t}"*' for t in toks)


def _tokens(q: str) -> list[str]:
    """The words of her query (lowercase, Devanagari included) — also what snippets highlight."""
    return re.findall(r"[\w\u0900-\u097F]+", (q or "").lower())[:8]     # letters/digits/_ + Devanagari, max 8 words


def _marks(text: str, toks: list[str], width: int = 80) -> str:
    """Snippet built in PYTHON, not by FTS5: unicode61 splits Devanagari words at the matras (its letter table has
    no combining marks), so snippet() drew highlights mid-word (<<किराय>>ा). Python sees whole codepoints, so the
    window lands on the real word and the marks wrap it cleanly."""
    t = re.sub(r"\s+", " ", text or "").strip()
    use = sorted({tok for tok in toks if len(tok) > 1}, key=len, reverse=True)
    if not use:
        return t[:2 * width]
    low = t.lower()
    pos = -1
    for tok in use:
        pos = low.find(tok)
        if pos >= 0:
            break
    if pos < 0:
        return t[:2 * width]
    a, b = max(0, pos - width), min(len(t), pos + width)
    win = t[a:b]
    # one pass, never nested; each mark covers the WHOLE word that contains the token (a prefix like "warr"
    # lights up "warranty" whole — never <<warr>>anty), word = letters/digits/Devanagari, punctuation stays out
    pat = re.compile("|".join(f"[\\w\\u0900-\\u097F]*{re.escape(tok)}[\\w\\u0900-\\u097F]*"
                              for tok in use), re.IGNORECASE)
    win = pat.sub(lambda m: f"<<{m.group(0)}>>", win)
    return ("…" if a else "") + win + ("…" if b < len(t) else "")


_LIVE = "(c.deleted IS NULL OR c.deleted = 0)"
_NOT_HIDDEN = "(m.branch IS NULL OR m.branch NOT LIKE 'hid:%')"


def _fts_rows(s, mq: str, tenant: str, conv: str | None, wide: int) -> list[Any]:
    sql = ("SELECT m.id, m.role, m.display, c.id AS conv_id, m.created_at AS at "
           "FROM messages_fts f JOIN messages m ON m.id = f.rowid JOIN conversations c ON c.id = f.conv "
           f"WHERE messages_fts MATCH :mq AND c.tenant_id = :tenant AND {_LIVE} AND {_NOT_HIDDEN} "
           "AND m.role IN ('user', 'assistant') ")
    args: dict[str, Any] = {"mq": mq, "tenant": tenant}
    if conv:
        sql += "AND f.conv = :conv "
        args["conv"] = conv
    sql += "ORDER BY m.id DESC LIMIT :lim"
    args["lim"] = wide
    return s.execute(sqltext(sql), args).all()


def _event_ok(e) -> bool:
    p = e.payload if isinstance(e.payload, dict) else {}
    return not (p.get("taken_back") or p.get("replaced_by"))


def _as_utc(d):
    """Raw-SQL rows hand datetimes back as strings; chats._utc wants a datetime."""
    if isinstance(d, str):
        from datetime import datetime
        try:
            d = datetime.fromisoformat(d)
        except ValueError:
            return None
    from .chats import _utc
    return _utc(d)


def _hits(s, rows, toks: list[str]) -> list[dict[str, Any]]:
    """Live-table result rows -> the search response shape. Taken-back messages drop; a message whose event
    cannot be mapped still shows (event_id 0, same as the LIKE fallback) — the chat just opens, no jump."""
    from .chats import _event_of, _title                      # lazy: avoid an import cycle
    from .db import Event
    out: list[dict[str, Any]] = []
    for mid, role, display, conv_id, at in rows:
        m = s.get(Message, mid)
        if m is None:
            continue
        eid = _event_of(s, m) or 0
        if eid:
            ev = s.get(Event, eid)
            if ev is not None and not _event_ok(ev):
                continue
        out.append({"conversation_id": conv_id, "title": _title(s, conv_id) or "", "role": role,
                    "snippet": _marks(display, toks), "message_id": mid, "event_id": eid,
                    "at": (_as_utc(at) or now()).isoformat()})
    return out


def search(tenant: str, q: str, limit: int = 30) -> list[dict[str, Any]]:
    """The console search: title hits first, then message hits ranked newest-first (same shape as v0.162)."""
    q = (q or "").strip()
    if len(q) < 2 or not ensure_index():
        return []
    mq = match_query(q)
    if not mq:
        return []
    with session() as s:
        like = f"%{q[:80]}%"
        live = "(deleted IS NULL OR deleted = 0)"
        titles = s.execute(sqltext(
            f"SELECT id, title, COALESCE(last_at, created_at) AS at FROM conversations "
            f"WHERE tenant_id=:t AND {live} AND title LIKE :like COLLATE NOCASE ORDER BY id DESC LIMIT 10"),
            {"t": tenant, "like": like}).all()
        rows = _fts_rows(s, mq, tenant, None, limit * 3)
        out: list[dict[str, Any]] = [{"conversation_id": tid, "title": t, "snippet": t, "event_id": 0, "role": "title",
                                      "at": (_as_utc(at) or now()).isoformat()} for tid, t, at in titles]
        out += _hits(s, rows[:limit * 2], _tokens(q))
    return out[:limit]


def find_in_chat(tenant: str, conv: str, q: str, limit: int = 300) -> dict[str, Any]:
    """v0.178 in-chat find (console Ctrl+F): every live match of THIS chat, oldest first, with a total count."""
    q = (q or "").strip()
    if len(q) < 1:
        return {"total": 0, "matches": []}
    if not ensure_index():
        return {"total": 0, "matches": []}
    mq = match_query(q)
    if not mq:
        return {"total": 0, "matches": []}
    with session() as s:
        wide = max(limit, 60) * 2
        rows = list(reversed(_fts_rows(s, mq, tenant, conv, wide)))   # document order: oldest first
        total = s.execute(sqltext(
            "SELECT COUNT(*) FROM messages_fts f JOIN messages m ON m.id = f.rowid JOIN conversations c ON c.id = f.conv "
            f"WHERE messages_fts MATCH :mq AND {_LIVE} AND {_NOT_HIDDEN} AND m.role IN ('user', 'assistant') "
            "AND f.conv = :conv"), {"mq": mq, "conv": conv}).scalar() or 0
        hits = _hits(s, rows[:limit], _tokens(q))
    return {"total": total, "matches": hits, "query": q[:200]}
