"""HOOLA CODER storage - the observations vault (v0.478.0).

A raw-sqlite3 store, one file, following the gyan/store.py house pattern (per-process RLock,
WAL, idempotent schema). It keeps the durable memory the coder observer compresses out of
Santosh's sessions:

  sessions    one row per conversation that was captured (chat / voice / wake)
  observations  the compressed notes (type, title, facts, narrative, concepts, files)
  summaries   one per session: request / investigated / learned / completed / next_steps / notes
  prompts     her exact asks (the privacy gate anchors to them: an empty-after-strip prompt
              means that turn was <private> and nothing from it is stored)
  tool_uses   the raw index of what ran (retention-limited, the deep-dig layer)
  work_state  cross-session to-do lists (todo / doing / done)
  dedup_candidates  near-duplicate pairs awaiting a human decision (never auto-merged)
  consumed    exactly-once markers for the spool drainer (filename is the dedupe key)

Full-text search rides FTS5 external-content tables kept in sync by triggers; when FTS5 is
unavailable (a probe decides at ensure time) search falls back to LIKE substrings - memory
never depends on an optional extension being present.

Deletion is by explicit retention only; like claude-mem, observations have no TTL
(coder_retain_days 0 = keep forever). A malformed retention value must never purge anything,
so a bad value is read as 0.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
import time
import unicodedata
from contextlib import contextmanager

log = __import__("logging").getLogger("coder.store")

_SCHEMA_VERSION = 1

_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS schema_version (v INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS sessions (
        conv TEXT PRIMARY KEY, tenant TEXT NOT NULL DEFAULT '', platform TEXT NOT NULL DEFAULT 'chat',
        started_at TEXT NOT NULL, started_epoch INTEGER NOT NULL, ended_at TEXT, ended_epoch INTEGER,
        status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','completed','failed')),
        observed INTEGER NOT NULL DEFAULT 0, discovery_tokens INTEGER NOT NULL DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT, conv TEXT NOT NULL, tenant TEXT NOT NULL DEFAULT '',
        type TEXT NOT NULL, title TEXT NOT NULL, subtitle TEXT NOT NULL DEFAULT '',
        facts TEXT NOT NULL DEFAULT '[]', narrative TEXT NOT NULL DEFAULT '',
        concepts TEXT NOT NULL DEFAULT '[]', files_read TEXT NOT NULL DEFAULT '[]',
        files_modified TEXT NOT NULL DEFAULT '[]', turn_id TEXT NOT NULL DEFAULT '', actor TEXT NOT NULL DEFAULT '',
        discovery_tokens INTEGER NOT NULL DEFAULT 0, content_hash TEXT NOT NULL,
        title_norm_key TEXT NOT NULL DEFAULT '', occurrence_count INTEGER NOT NULL DEFAULT 1,
        reinforcement_dates TEXT NOT NULL DEFAULT '[]', last_reinforced TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL, created_epoch INTEGER NOT NULL)""",
    """CREATE UNIQUE INDEX IF NOT EXISTS idx_obs_content ON observations(conv, content_hash)""",
    """CREATE INDEX IF NOT EXISTS idx_obs_conv ON observations(conv, created_epoch)""",
    """CREATE INDEX IF NOT EXISTS idx_obs_tenant ON observations(tenant, created_epoch)""",
    """CREATE INDEX IF NOT EXISTS idx_obs_type ON observations(type)""",
    """CREATE INDEX IF NOT EXISTS idx_obs_norm ON observations(tenant, title_norm_key)""",
    """CREATE TABLE IF NOT EXISTS summaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT, conv TEXT NOT NULL UNIQUE, tenant TEXT NOT NULL DEFAULT '',
        request TEXT NOT NULL DEFAULT '', investigated TEXT NOT NULL DEFAULT '', learned TEXT NOT NULL DEFAULT '',
        completed TEXT NOT NULL DEFAULT '', next_steps TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL, created_epoch INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS prompts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, conv TEXT NOT NULL, n INTEGER NOT NULL,
        text TEXT NOT NULL, private INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL)""",
    """CREATE INDEX IF NOT EXISTS idx_prompts_conv ON prompts(conv, n)""",
    """CREATE TABLE IF NOT EXISTS tool_uses (
        id INTEGER PRIMARY KEY AUTOINCREMENT, conv TEXT NOT NULL, tenant TEXT NOT NULL DEFAULT '',
        tool TEXT NOT NULL, args_brief TEXT NOT NULL DEFAULT '', ok INTEGER NOT NULL DEFAULT 1,
        ms INTEGER NOT NULL DEFAULT 0, line TEXT NOT NULL DEFAULT '', turn_id TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL, created_epoch INTEGER NOT NULL)""",
    """CREATE INDEX IF NOT EXISTS idx_tool_conv ON tool_uses(conv, created_epoch)""",
    """CREATE TABLE IF NOT EXISTS work_state (
        list TEXT PRIMARY KEY, items TEXT NOT NULL DEFAULT '[]', updated_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS dedup_candidates (
        observation_id INTEGER NOT NULL, duplicate_of_id INTEGER NOT NULL, score REAL NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','merged','distinct','dismissed')),
        created_at TEXT NOT NULL,
        UNIQUE(observation_id, duplicate_of_id))""",
    """CREATE TABLE IF NOT EXISTS skills (
        name TEXT NOT NULL, tenant TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '',
        body TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        PRIMARY KEY (name, tenant))""",
    """CREATE TABLE IF NOT EXISTS consumed (key TEXT PRIMARY KEY, at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS token_df (
        tenant TEXT NOT NULL, token TEXT NOT NULL, df INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (tenant, token))""",
]

# External-content FTS5 kept in sync by triggers; created only when the probe passes.
_FTS_SQL = [
    """CREATE VIRTUAL TABLE IF NOT EXISTS obs_fts USING fts5(
        title, subtitle, narrative, facts, concepts, content='observations', content_rowid='id')""",
    """CREATE TRIGGER IF NOT EXISTS obs_fts_ai AFTER INSERT ON observations BEGIN
        INSERT INTO obs_fts(rowid, title, subtitle, narrative, facts, concepts)
        VALUES (new.id, new.title, new.subtitle, new.narrative, new.facts, new.concepts); END""",
    """CREATE TRIGGER IF NOT EXISTS obs_fts_ad AFTER DELETE ON observations BEGIN
        INSERT INTO obs_fts(obs_fts, rowid, title, subtitle, narrative, facts, concepts)
        VALUES ('delete', old.id, old.title, old.subtitle, old.narrative, old.facts, old.concepts); END""",
    """CREATE VIRTUAL TABLE IF NOT EXISTS sum_fts USING fts5(
        request, investigated, learned, completed, next_steps, notes,
        content='summaries', content_rowid='id')""",
    """CREATE TRIGGER IF NOT EXISTS sum_fts_ai AFTER INSERT ON summaries BEGIN
        INSERT INTO sum_fts(rowid, request, investigated, learned, completed, next_steps, notes)
        VALUES (new.id, new.request, new.investigated, new.learned, new.completed, new.next_steps, new.notes); END""",
    # v0.477 HOOLA SKILLS: the file is the source of truth; this mirror exists so the FTS
    # search covers skills with the same discipline as observations.
    """CREATE VIRTUAL TABLE IF NOT EXISTS skills_fts USING fts5(
        name, description, body, content='skills', content_rowid='rowid')""",
    """CREATE TRIGGER IF NOT EXISTS skills_fts_ai AFTER INSERT ON skills BEGIN
        INSERT INTO skills_fts(rowid, name, description, body)
        VALUES (new.rowid, new.name, new.description, new.body); END""",
    """CREATE TRIGGER IF NOT EXISTS skills_fts_ad AFTER DELETE ON skills BEGIN
        INSERT INTO skills_fts(skills_fts, rowid, name, description, body)
        VALUES ('delete', old.rowid, old.name, old.description, old.body); END""",
    """CREATE TRIGGER IF NOT EXISTS skills_fts_au AFTER UPDATE ON skills BEGIN
        INSERT INTO skills_fts(skills_fts, rowid, name, description, body)
        VALUES ('delete', old.rowid, old.name, old.description, old.body);
        INSERT INTO skills_fts(rowid, name, description, body)
        VALUES (new.rowid, new.name, new.description, new.body); END""",
]

_LOCK = threading.RLock()
_LOCAL = threading.local()
_fts_ok: bool | None = None


def root() -> str:
    import os
    from ..config import get_settings
    d = getattr(get_settings(), "coder_dir", "./data/coder") or "./data/coder"
    os.makedirs(d, exist_ok=True)
    return d


def path() -> str:
    import os
    return os.path.join(root(), "coder.db")


class _suppress:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return True


@contextmanager
def db(write: bool = False):
    """One connection per thread PER RESOLVED PATH (the cache key is abspath: two tests both ask
    for './data/coder/coder.db' from different cwd and must NEVER share a handle)."""
    with _LOCK:
        p = os.path.abspath(path())
        conn = getattr(_LOCAL, "conn", None)
        cpath = getattr(_LOCAL, "conn_path", None)
        if conn is None or cpath != p:
            if conn is not None:
                with _suppress():
                    conn.close()
            conn = sqlite3.connect(p, timeout=15, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA foreign_keys=ON")
            _LOCAL.conn = conn
            _LOCAL.conn_path = p
        try:
            if write:
                conn.execute("BEGIN IMMEDIATE")
            yield conn
            if write:
                conn.execute("COMMIT")
        except Exception:
            if write:
                with _suppress():
                    conn.execute("ROLLBACK")
            raise


def ensure() -> None:
    """Idempotent: create every table, probe FTS5 once, stamp the schema version."""
    global _fts_ok
    with _LOCK:
        conn = sqlite3.connect(path(), timeout=15)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            for stmt in _SCHEMA:
                conn.execute(stmt)
            row = conn.execute("SELECT v FROM schema_version").fetchone()
            if row is None:
                conn.execute("INSERT INTO schema_version(v) VALUES (?)", (_SCHEMA_VERSION,))
            if _fts_ok is None:
                try:
                    conn.execute("CREATE VIRTUAL TABLE temp._fts_probe USING fts5(x)")
                    _fts_ok = True
                except sqlite3.Error:
                    _fts_ok = False
            if _fts_ok:
                for stmt in _FTS_SQL:
                    conn.execute(stmt)
            conn.commit()
        finally:
            conn.close()


def fts_available() -> bool:
    ensure()
    return bool(_fts_ok)


# ---------------------------------------------------------------- content hashes / dedup keys

def content_hash(conv: str, title: str, narrative: str) -> str:
    """First 16 hex of sha256 - the exact-duplicate key (same session + same words = same memory)."""
    h = hashlib.sha256("\0".join([conv, title, narrative]).encode("utf-8")).hexdigest()
    return h[:16]


_WORD_RE = re.compile(r"[^\w]+", re.UNICODE)


def norm_title(title: str) -> str:
    """NFC, lowercase, letters/digits/whitespace only - the Tier-0 merge key input."""
    t = unicodedata.normalize("NFC", title or "").lower()
    t = "".join(ch for ch in t if unicodedata.category(ch).startswith(("L", "N", "M")) or ch.isspace())
    return " ".join(t.split())


def title_norm_key(tenant: str, title: str) -> str:
    h = hashlib.sha256("\0".join([tenant, norm_title(title)]).encode("utf-8")).hexdigest()
    return h[:32]


# ---------------------------------------------------------------- sessions

def session_started(conv: str, tenant: str, platform: str) -> None:
    ensure()
    now, ep = time.strftime("%Y-%m-%dT%H:%M:%S%z"), int(time.time())
    with db(write=True) as c:
        c.execute("INSERT OR IGNORE INTO sessions(conv, tenant, platform, started_at, started_epoch) "
                  "VALUES (?,?,?,?,?)", (conv, tenant, platform, now, ep))


def session_ended(conv: str) -> None:
    ensure()
    now, ep = time.strftime("%Y-%m-%dT%H:%M:%S%z"), int(time.time())
    with db(write=True) as c:
        c.execute("UPDATE sessions SET status='completed', ended_at=?, ended_epoch=? "
                  "WHERE conv=? AND status='active'", (now, ep, conv))


def session_row(conv: str) -> dict | None:
    ensure()
    with db() as c:
        r = c.execute("SELECT * FROM sessions WHERE conv=?", (conv,)).fetchone()
        return dict(r) if r else None


# ---------------------------------------------------------------- prompts (the privacy gate anchor)

def note_prompt(conv: str, text: str) -> None:
    """Store her ask (redacted at the caller), numbered per conversation. An empty-after-strip
    prompt marks the turn private - the words never land, only the marker."""
    ensure()
    from .redact import strip_private
    kept = strip_private(text or "").strip()
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    with db(write=True) as c:
        r = c.execute("SELECT COALESCE(MAX(n), 0) + 1 FROM prompts WHERE conv=?", (conv,)).fetchone()
        c.execute("INSERT INTO prompts(conv, n, text, private, created_at) VALUES (?,?,?,?,?)",
                  (conv, int(r[0]), kept[:2000], 0 if kept else 1, now))


def latest_prompt_private(conv: str) -> bool:
    """The privacy gate: her NEWEST recorded ask was wholly <private> - nothing from that turn's
    events belongs in memory (the safe side: skip more, never leak)."""
    ensure()
    with db() as c:
        r = c.execute("SELECT private FROM prompts WHERE conv=? ORDER BY id DESC LIMIT 1",
                      (conv,)).fetchone()
        return bool(r and r["private"])


def prompt_is_private(conv: str, n: int | None) -> bool:
    if not n:
        return False
    ensure()
    with db() as c:
        r = c.execute("SELECT private FROM prompts WHERE conv=? AND n=? ORDER BY id DESC LIMIT 1",
                      (conv, n)).fetchone()
        return bool(r and r["private"])


# ---------------------------------------------------------------- observations

def store_observation(conv: str, tenant: str, obs: dict, turn_id: str = "", actor: str = "",
                      discovery_tokens: int = 0) -> int | None:
    """Insert one parsed observation. Exact-content dedupe (session + hash) re-confirms the existing
    row instead of duplicating it; the Tier-0 normalized-title merge bumps occurrence_count and
    reinforces (the world said it again). Returns the row id (canonical or new), None if dropped."""
    ensure()
    title = (obs.get("title") or "").strip()
    if not title:                      # claude-mem rule: an untitled observation is nobody's memory
        return None
    narrative = (obs.get("narrative") or "").strip()
    chash = content_hash(conv, title, narrative)
    nk = title_norm_key(tenant, title)
    now, ep = time.strftime("%Y-%m-%dT%H:%M:%S%z"), int(time.time())
    today = now[:10]
    facts = json.dumps(obs.get("facts") or [], ensure_ascii=False)
    concepts = json.dumps(obs.get("concepts") or [], ensure_ascii=False)
    fread = json.dumps(obs.get("files_read") or [], ensure_ascii=False)
    fmod = json.dumps(obs.get("files_modified") or [], ensure_ascii=False)
    with db(write=True) as c:
        # Tier-0: the same normalized title in the same tenant is THE same memory, re-confirmed.
        row = c.execute("SELECT id FROM observations WHERE tenant=? AND title_norm_key=? "
                        "ORDER BY id LIMIT 1", (tenant, nk)).fetchone()
        if row is not None:
            old = c.execute("SELECT reinforcement_dates FROM observations WHERE id=?",
                            (row["id"],)).fetchone()
            c.execute("UPDATE observations SET occurrence_count = occurrence_count + 1, "
                      "last_reinforced=?, reinforcement_dates=? WHERE id=?",
                      (today, _bump_dates(old[0] if old else "[]", today), row["id"]))
            return row["id"]
        dup = c.execute("SELECT id FROM observations WHERE conv=? AND content_hash=?", (conv, chash)).fetchone()
        if dup is not None:
            old = c.execute("SELECT reinforcement_dates FROM observations WHERE id=?", (dup["id"],)).fetchone()
            c.execute("UPDATE observations SET occurrence_count = occurrence_count + 1, last_reinforced=?, "
                      "reinforcement_dates=? WHERE id=?",
                      (today, _bump_dates(old[0] if old else "[]", today), dup["id"]))
            return dup["id"]
        cur = c.execute(
            "INSERT INTO observations(conv, tenant, type, title, subtitle, facts, narrative, concepts, "
            "files_read, files_modified, turn_id, actor, discovery_tokens, content_hash, title_norm_key, "
            "created_at, created_epoch) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (conv, tenant, obs.get("type") or "discovery", title, (obs.get("subtitle") or "")[:300],
             facts, narrative[:8000], concepts, fread, fmod, turn_id, actor, discovery_tokens, chash, nk,
             now, ep))
        _bump_df(c, tenant, norm_title(title))
        return int(cur.lastrowid)


def _bump_dates(dates_json: str, today: str) -> str:
    try:
        dates = json.loads(dates_json or "[]")
    except Exception:
        dates = []
    if today not in dates:
        dates.append(today)
    return json.dumps(dates[-10:], ensure_ascii=False)   # MAX_REINFORCEMENT_HISTORY = 10, FIFO


def _bump_df(c, tenant: str, title_norm: str) -> None:
    for tok in set(title_norm.split()):
        if len(tok) < 3:
            continue
        c.execute("INSERT INTO token_df(tenant, token, df) VALUES (?,?,1) "
                  "ON CONFLICT(tenant, token) DO UPDATE SET df = df + 1", (tenant, tok))


def reinforce(obs_id: int) -> None:
    ensure()
    today = time.strftime("%Y-%m-%d")
    with db(write=True) as c:
        r = c.execute("SELECT reinforcement_dates FROM observations WHERE id=?", (obs_id,)).fetchone()
        if r is not None:
            c.execute("UPDATE observations SET last_reinforced=?, reinforcement_dates=? WHERE id=?",
                      (today, _bump_dates(r[0], today), obs_id))


def get_observations(ids: list[int]) -> list[dict]:
    """Full rows by id, in the caller's order (the layer-3 fetch)."""
    ensure()
    if not ids:
        return []
    with db() as c:
        marks = ",".join("?" * len(ids))
        rows = c.execute(f"SELECT * FROM observations WHERE id IN ({marks})", ids).fetchall()
    by_id = {r["id"]: dict(r) for r in rows}
    return [by_id[i] for i in ids if i in by_id]


def recent_observations(tenant: str, limit: int = 50, conv: str | None = None) -> list[dict]:
    ensure()
    q = "SELECT * FROM observations WHERE tenant=?"
    args: list = [tenant]
    if conv:
        q += " AND conv=?"
        args.append(conv)
    q += " ORDER BY created_epoch DESC, id DESC LIMIT ?"
    args.append(limit)
    with db() as c:
        return [dict(r) for r in c.execute(q, args).fetchall()]


# ---------------------------------------------------------------- summaries

def store_summary(conv: str, tenant: str, s: dict) -> None:
    """Exactly one summary per conversation - the newest Stop rewrites it (UNIQUE conv)."""
    ensure()
    now, ep = time.strftime("%Y-%m-%dT%H:%M:%S%z"), int(time.time())
    with db(write=True) as c:
        c.execute("INSERT INTO summaries(conv, tenant, request, investigated, learned, completed, "
                  "next_steps, notes, created_at, created_epoch) VALUES (?,?,?,?,?,?,?,?,?,?) "
                  "ON CONFLICT(conv) DO UPDATE SET request=excluded.request, "
                  "investigated=excluded.investigated, learned=excluded.learned, "
                  "completed=excluded.completed, next_steps=excluded.next_steps, notes=excluded.notes, "
                  "created_at=excluded.created_at, created_epoch=excluded.created_epoch",
                  (conv, tenant, (s.get("request") or "")[:4000], (s.get("investigated") or "")[:8000],
                   (s.get("learned") or "")[:8000], (s.get("completed") or "")[:8000],
                   (s.get("next_steps") or "")[:8000], (s.get("notes") or "")[:4000], now, ep))


def last_summary(tenant: str, conv: str | None = None) -> dict | None:
    ensure()
    q, args = "SELECT * FROM summaries WHERE tenant=?", [tenant]
    if conv:
        q += " AND conv=?"
        args.append(conv)
    q += " ORDER BY created_epoch DESC, id DESC LIMIT 1"
    with db() as c:
        r = c.execute(q, args).fetchone()
        return dict(r) if r else None


# ---------------------------------------------------------------- tool_uses

def note_tool_use(conv: str, tenant: str, tool: str, args_brief: str, ok: bool, ms: int, line: str,
                  turn_id: str) -> None:
    ensure()
    now, ep = time.strftime("%Y-%m-%dT%H:%M:%S%z"), int(time.time())
    with db(write=True) as c:
        c.execute("INSERT INTO tool_uses(conv, tenant, tool, args_brief, ok, ms, line, turn_id, "
                  "created_at, created_epoch) VALUES (?,?,?,?,?,?,?,?,?,?)",
                  (conv, tenant, tool, args_brief[:2000], 1 if ok else 0, ms, line[:1000], turn_id, now, ep))


def tool_uses_by_ids(ids: list[int]) -> list[dict]:
    ensure()
    if not ids:
        return []
    with db() as c:
        marks = ",".join("?" * len(ids))
        rows = c.execute(f"SELECT * FROM tool_uses WHERE id IN ({marks})", ids).fetchall()
    by_id = {r["id"]: dict(r) for r in rows}
    return [by_id[i] for i in ids if i in by_id]


# ---------------------------------------------------------------- work state

def work_write(lst: str, items: list[dict]) -> None:
    ensure()
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    with db(write=True) as c:
        c.execute("INSERT INTO work_state(list, items, updated_at) VALUES (?,?,?) "
                  "ON CONFLICT(list) DO UPDATE SET items=excluded.items, updated_at=excluded.updated_at",
                  (lst[:200], json.dumps(items[:100], ensure_ascii=False), now))


def work_read(lst: str | None = None, include_closed: bool = False) -> dict:
    ensure()
    with db() as c:
        if lst:
            rows = c.execute("SELECT * FROM work_state WHERE list=?", (lst,)).fetchall()
        else:
            rows = c.execute("SELECT * FROM work_state ORDER BY updated_at").fetchall()
    out: dict[str, list] = {}
    for r in rows:
        try:
            items = json.loads(r["items"])
        except Exception:
            items = []
        if not include_closed:
            items = [i for i in items if (i.get("status") or "todo") in ("todo", "doing")]
        out[r["list"]] = items
    return out


# ---------------------------------------------------------------- skills (v0.477 mirror + search)

def skill_mirror(name: str, tenant: str, description: str, body: str) -> None:
    """The vault row behind one skill file (files are the source of truth; this is the index)."""
    ensure()
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    with db(write=True) as c:
        c.execute("INSERT INTO skills(name, tenant, description, body, created_at, updated_at) "
                  "VALUES (?,?,?,?,?,?) ON CONFLICT(name, tenant) DO UPDATE SET "
                  "description=excluded.description, body=excluded.body, updated_at=excluded.updated_at",
                  (name, tenant, description[:300], body[:8000], now, now))


def skill_unmirror(name: str, tenant: str) -> None:
    ensure()
    with db(write=True) as c:
        c.execute("DELETE FROM skills WHERE name=? AND tenant=?", (name, tenant))


def skills_search(tenant: str, query: str, limit: int = 2) -> list[dict]:
    """Top skills for the current ask - the injection shortlist. FTS5 match first; LIKE fallback
    (the obs search discipline); scoped to the caller's tenant always."""
    ensure()
    q = (query or "").strip()
    if not q:
        return []
    with db() as c:
        if _fts_ok:
            terms = " OR ".join(f'"{t.replace(chr(34), "")}"' for t in q.split() if len(t) >= 3)[:400]
            if terms:
                try:
                    rows = c.execute(
                        "SELECT s.name, s.description, s.body FROM skills_fts f "
                        "JOIN skills s ON s.rowid = f.rowid "
                        "WHERE skills_fts MATCH ? AND s.tenant=? "
                        "ORDER BY rank LIMIT ?", (terms, tenant, limit)).fetchall()
                    return [dict(r) for r in rows]
                except sqlite3.Error:
                    pass                       # a malformed match string falls through to LIKE
        like = f"%{q[:200]}%"
        rows = c.execute(
            "SELECT name, description, body FROM skills WHERE tenant=? AND "
            "(name LIKE ? OR description LIKE ? OR body LIKE ?) LIMIT ?",
            (tenant, like, like, like, limit)).fetchall()
        return [dict(r) for r in rows]


def skills_count() -> int:
    ensure()
    with db() as c:
        return int(c.execute("SELECT COUNT(*) FROM skills").fetchone()[0])


def nudge_counts() -> dict:
    """What the self-teaching fork has written so far (rows carry actor='nudge')."""
    ensure()
    with db() as c:
        obs = c.execute("SELECT COUNT(*) FROM observations WHERE actor='nudge'").fetchone()[0]
        convs = c.execute("SELECT COUNT(DISTINCT conv) FROM observations WHERE actor='nudge'").fetchone()[0]
    return {"nudge_observations": int(obs), "nudge_conversations": int(convs)}


# ---------------------------------------------------------------- dedup candidates (review-only)

def note_candidate(obs_id: int, dup_of: int, score: float) -> None:
    ensure()
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    with db(write=True) as c:
        c.execute("INSERT OR IGNORE INTO dedup_candidates(observation_id, duplicate_of_id, score, created_at) "
                  "VALUES (?,?,?,?)", (obs_id, dup_of, score, now))


def candidates(status: str = "pending") -> list[dict]:
    ensure()
    with db() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM dedup_candidates WHERE status=? ORDER BY score DESC LIMIT 200",
            (status,)).fetchall()]


# ---------------------------------------------------------------- consumed markers + retention

def mark_consumed(key: str) -> None:
    ensure()
    with db(write=True) as c:
        c.execute("INSERT OR REPLACE INTO consumed(key, at) VALUES (?,?)",
                  (key, time.strftime("%Y-%m-%dT%H:%M:%S%z")))


def is_consumed(key: str) -> bool:
    ensure()
    with db() as c:
        return c.execute("SELECT 1 FROM consumed WHERE key=?", (key,)).fetchone() is not None


def forget_old(days) -> None:
    """Explicit retention only. 0/negative/malformed = keep forever (a typo must never purge)."""
    try:
        d = int(days)
    except (TypeError, ValueError):
        return
    if d <= 0:
        return
    cut = int(time.time()) - d * 86400
    ensure()
    with db(write=True) as c:
        c.execute("DELETE FROM observations WHERE created_epoch < ?", (cut,))
        c.execute("DELETE FROM tool_uses WHERE created_epoch < ?", (cut,))


def stats() -> dict:
    ensure()
    with db() as c:
        n_obs = c.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        n_sum = c.execute("SELECT COUNT(*) FROM summaries").fetchone()[0]
        n_sessions = c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        n_tools = c.execute("SELECT COUNT(*) FROM tool_uses").fetchone()[0]
        disc = c.execute("SELECT COALESCE(SUM(discovery_tokens),0) FROM observations").fetchone()[0]
        cand = c.execute("SELECT COUNT(*) FROM dedup_candidates WHERE status='pending'").fetchone()[0]
        n_skills = c.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
    return {"observations": n_obs, "summaries": n_sum, "sessions": n_sessions, "tool_uses": n_tools,
            "discovery_tokens": disc, "pending_dedup_candidates": cand, "skills": int(n_skills),
            **nudge_counts(), "fts": bool(_fts_ok)}
