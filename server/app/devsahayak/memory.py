"""HOOLA CODE MEMORY (owner: "https://github.com/thedotmack/claude-mem.git --- check this repo and devlope same for hoola
code"). claude-mem's design (Apache-2.0, read at 6b779c0; ideas only, no upstream code) for Hoola Code's working-copy
engine, kept PER REPO:

- CAPTURE: the engine already holds the whole round (her words, every tool step, the change, the coder's own report),
  so ONE cheap model call when a round ends (`dev_memory_model`, Haiku) is the observer: it turns the round into a few
  typed observations (bugfix / feature / refactor / change / discovery / decision / security_alert / security_note,
  with concepts how-it-works / why-it-exists / what-changed / problem-solution / gotcha / pattern / trade-off) and one
  round summary (request / investigated / learned / completed / next steps). claude-mem's "chill" mode (only what would
  be painful to rediscover) is `dev_memory_mode=chill`.
- PRIVACY: her `<private>...</private>` text never reaches the observer or a row, every string is passed through the
  house secret redaction (coder.redact) before AND after the model, and a 'sensitive' observation is not stored at all
  (stricter than claude-mem, which keeps it labelled).
- STORAGE: SQLite + FTS5 at data/devsahayak/memory.db, scoped (tenant, repo); the same title in the same repo is the
  same memory, re-confirmed (hits + 1) instead of duplicated.
- THE NEXT SESSION STARTS WHERE THE LAST ONE LEFT OFF: a new session's first message carries a compact INDEX of the
  repo's memory (`primer`), fitted to `dev_memory_primer_chars` by measuring and dropping the cheapest loss first
  (full narratives, then the last summary block, then older summaries, then the oldest index lines) - claude-mem's
  context budget, so it never overflows and never cuts an item in half.
- PROGRESSIVE DISCLOSURE: one `memory` tool with claude-mem's three steps - search (an index with ids) -> timeline
  (what happened around one) -> get (full details for chosen ids only) - plus save (a note on purpose).
- HER PAGE: Settings > a repo > What Hoola remembers: every row, delete one, forget the repo."""
from __future__ import annotations

import contextlib
import json
import logging
import re
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("santosh.devsahayak.memory")

TYPES = {
    "bugfix": "something was broken, now fixed", "feature": "a new capability added",
    "refactor": "code restructured, behaviour unchanged", "change": "docs / config / other modification",
    "discovery": "learned how the existing system works", "decision": "a design choice and its reason",
    "security_alert": "a security problem that needs attention", "security_note": "security-relevant, not urgent",
}
CONCEPTS = ("how-it-works", "why-it-exists", "what-changed", "problem-solution", "gotcha", "pattern", "trade-off")
_LOCK = threading.Lock()
STATS = {"captured": 0, "observations": 0, "skipped": 0, "primers": 0}


def _set(name: str, default: Any) -> Any:
    try:
        from ..config import get_settings
        v = getattr(get_settings(), name, default)
        return default if v is None else v
    except Exception:
        return default


def on() -> bool:
    return bool(_set("dev_memory", True))


def path() -> Path:
    return Path("data") / "devsahayak" / "memory.db"


# ---------------------------------------------------------------- storage
SCHEMA = [
    """CREATE TABLE IF NOT EXISTS obs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, tenant TEXT NOT NULL DEFAULT '', repo TEXT NOT NULL,
        task TEXT NOT NULL DEFAULT '', type TEXT NOT NULL, title TEXT NOT NULL, subtitle TEXT NOT NULL DEFAULT '',
        facts TEXT NOT NULL DEFAULT '[]', narrative TEXT NOT NULL DEFAULT '', concepts TEXT NOT NULL DEFAULT '[]',
        files_read TEXT NOT NULL DEFAULT '[]', files_modified TEXT NOT NULL DEFAULT '[]', title_key TEXT NOT NULL,
        hits INTEGER NOT NULL DEFAULT 1, source TEXT NOT NULL DEFAULT 'round', created_epoch INTEGER NOT NULL,
        seen_epoch INTEGER NOT NULL)""",
    "CREATE UNIQUE INDEX IF NOT EXISTS obs_key ON obs(tenant, repo, title_key)",
    "CREATE INDEX IF NOT EXISTS obs_repo ON obs(tenant, repo, seen_epoch)",
    """CREATE TABLE IF NOT EXISTS summaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT, tenant TEXT NOT NULL DEFAULT '', repo TEXT NOT NULL,
        task TEXT NOT NULL DEFAULT '', request TEXT NOT NULL DEFAULT '', investigated TEXT NOT NULL DEFAULT '',
        learned TEXT NOT NULL DEFAULT '', completed TEXT NOT NULL DEFAULT '', next_steps TEXT NOT NULL DEFAULT '',
        files_edited TEXT NOT NULL DEFAULT '[]', created_epoch INTEGER NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS sum_repo ON summaries(tenant, repo, created_epoch)",
]
FTS = [
    "CREATE VIRTUAL TABLE IF NOT EXISTS obs_fts USING fts5(title, subtitle, narrative, facts, concepts, "
    "content='obs', content_rowid='id')",
    "CREATE TRIGGER IF NOT EXISTS obs_ai AFTER INSERT ON obs BEGIN INSERT INTO obs_fts(rowid, title, subtitle, narrative, "
    "facts, concepts) VALUES (new.id, new.title, new.subtitle, new.narrative, new.facts, new.concepts); END",
    "CREATE TRIGGER IF NOT EXISTS obs_ad AFTER DELETE ON obs BEGIN INSERT INTO obs_fts(obs_fts, rowid, title, subtitle, "
    "narrative, facts, concepts) VALUES ('delete', old.id, old.title, old.subtitle, old.narrative, old.facts, old.concepts); END",
    "CREATE TRIGGER IF NOT EXISTS obs_au AFTER UPDATE ON obs BEGIN INSERT INTO obs_fts(obs_fts, rowid, title, subtitle, "
    "narrative, facts, concepts) VALUES ('delete', old.id, old.title, old.subtitle, old.narrative, old.facts, old.concepts); "
    "INSERT INTO obs_fts(rowid, title, subtitle, narrative, facts, concepts) VALUES (new.id, new.title, new.subtitle, "
    "new.narrative, new.facts, new.concepts); END",
]
_READY: dict[str, bool] = {}


@contextlib.contextmanager
def db():
    p = path()
    p.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(p), timeout=10)
    c.row_factory = sqlite3.Row
    try:
        key = str(p.resolve())
        if key not in _READY:
            with _LOCK:
                c.execute("PRAGMA journal_mode=WAL")
                for q in SCHEMA:
                    c.execute(q)
                fts = True
                try:
                    for q in FTS:
                        c.execute(q)
                except sqlite3.OperationalError:          # an sqlite without FTS5: LIKE search instead
                    fts = False
                c.commit()
                _READY[key] = fts
        yield c
        c.commit()
    finally:
        c.close()


def _fts() -> bool:
    with db():
        pass
    return _READY.get(str(path().resolve()), False)


def _clean(text: Any, cap: int = 4000) -> str:
    """Her private blocks out, secrets masked, at every boundary."""
    from ..coder import redact as RD
    s = RD.redact_secrets(RD.strip_private(str(text or "")))
    return s.strip()[:cap]


def _key(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(title or "").lower()).strip()[:200]


def _j(v: Any) -> list:
    if isinstance(v, list):
        return v
    try:
        x = json.loads(v or "[]")
        return x if isinstance(x, list) else []
    except (TypeError, ValueError):
        return []


def store(tenant: str, repo: str, task: str, o: dict[str, Any], source: str = "round") -> int | None:
    """One observation; the same title in the same repo re-confirms the old row (hits + 1, newest wording kept)."""
    typ = str(o.get("type") or "").strip().lower()
    if typ == "sensitive" or typ not in TYPES:
        return None
    title = _clean(o.get("title"), 160)
    if not title:
        return None
    rec = {"subtitle": _clean(o.get("subtitle"), 240), "narrative": _clean(o.get("narrative"), 1600),
           "facts": json.dumps([_clean(x, 300) for x in _j(o.get("facts"))[:8] if _clean(x, 300)]),
           "concepts": json.dumps([c for c in _j(o.get("concepts")) if c in CONCEPTS][:4]),
           "files_read": json.dumps([str(x)[:200] for x in _j(o.get("files_read"))[:15]]),
           "files_modified": json.dumps([str(x)[:200] for x in _j(o.get("files_modified"))[:15]])}
    now, k = int(time.time()), _key(title)
    with db() as c:
        row = c.execute("SELECT id FROM obs WHERE tenant=? AND repo=? AND title_key=?", (tenant, repo, k)).fetchone()
        if row is not None:
            c.execute("UPDATE obs SET hits=hits+1, seen_epoch=?, type=?, subtitle=?, narrative=?, facts=?, concepts=?, "
                      "files_read=?, files_modified=?, task=? WHERE id=?",
                      (now, typ, rec["subtitle"], rec["narrative"] or "", rec["facts"], rec["concepts"], rec["files_read"],
                       rec["files_modified"], task, row["id"]))
            return int(row["id"])
        cur = c.execute("INSERT INTO obs(tenant, repo, task, type, title, subtitle, facts, narrative, concepts, files_read, "
                        "files_modified, title_key, source, created_epoch, seen_epoch) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (tenant, repo, task, typ, title, rec["subtitle"], rec["facts"], rec["narrative"], rec["concepts"],
                         rec["files_read"], rec["files_modified"], k, source, now, now))
        STATS["observations"] += 1
        return int(cur.lastrowid)


def store_summary(tenant: str, repo: str, task: str, s: dict[str, Any], files: list[str]) -> int | None:
    vals = {k: _clean(s.get(k), 900) for k in ("request", "investigated", "learned", "completed", "next_steps")}
    if not any(vals.values()):
        return None
    with db() as c:
        cur = c.execute("INSERT INTO summaries(tenant, repo, task, request, investigated, learned, completed, next_steps, "
                        "files_edited, created_epoch) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (tenant, repo, task, vals["request"], vals["investigated"], vals["learned"], vals["completed"],
                         vals["next_steps"], json.dumps([str(f)[:200] for f in files[:30]]), int(time.time())))
        return int(cur.lastrowid)


def _row(r: sqlite3.Row, full: bool = False) -> dict[str, Any]:
    d = {"id": r["id"], "type": r["type"], "title": r["title"], "subtitle": r["subtitle"], "hits": r["hits"],
         "at": r["seen_epoch"], "files": _j(r["files_modified"])[:6] or _j(r["files_read"])[:4]}
    if full:
        d.update({"narrative": r["narrative"], "facts": _j(r["facts"]), "concepts": _j(r["concepts"]),
                  "files_read": _j(r["files_read"]), "files_modified": _j(r["files_modified"]), "task": r["task"],
                  "created": r["created_epoch"], "source": r["source"]})
    return d


# ---------------------------------------------------------------- the three steps
def search(tenant: str, repo: str, query: str = "", typ: str = "", limit: int = 15) -> list[dict[str, Any]]:
    """Step 1: a compact index (ids, type, title, files) - never the full text."""
    limit = max(1, min(int(limit or 15), 50))
    q = re.sub(r"[^\w\s./-]+", " ", str(query or "")).strip()
    args: list[Any] = [tenant, repo]
    where = "o.tenant=? AND o.repo=?"
    if typ in TYPES:
        where += " AND o.type=?"
        args.append(typ)
    with db() as c:
        if q and _fts():
            terms = " OR ".join(f'"{w}"' for w in q.split()[:12])
            rows = c.execute(f"SELECT o.* FROM obs_fts f JOIN obs o ON o.id=f.rowid WHERE obs_fts MATCH ? AND {where} "
                             "ORDER BY bm25(obs_fts), o.seen_epoch DESC LIMIT ?", [terms] + args + [limit]).fetchall()
        elif q:
            like = [f"%{w}%" for w in q.split()[:6]]
            cond = " OR ".join("(o.title LIKE ? OR o.narrative LIKE ? OR o.facts LIKE ?)" for _ in like)
            flat = [x for w in like for x in (w, w, w)]
            rows = c.execute(f"SELECT o.* FROM obs o WHERE {where} AND ({cond}) ORDER BY o.seen_epoch DESC LIMIT ?",
                             args + flat + [limit]).fetchall()
        else:
            rows = c.execute(f"SELECT o.* FROM obs o WHERE {where} ORDER BY o.seen_epoch DESC LIMIT ?", args + [limit]).fetchall()
    return [_row(r) for r in rows]


def timeline(tenant: str, repo: str, anchor: int, before: int = 4, after: int = 4) -> list[dict[str, Any]]:
    """Step 2: what was happening around one observation (by time, same repo)."""
    with db() as c:
        a = c.execute("SELECT * FROM obs WHERE id=? AND tenant=? AND repo=?", (int(anchor), tenant, repo)).fetchone()
        if a is None:
            return []
        pre = c.execute("SELECT * FROM obs WHERE tenant=? AND repo=? AND created_epoch<=? AND id<>? ORDER BY created_epoch DESC, "
                        "id DESC LIMIT ?", (tenant, repo, a["created_epoch"], a["id"], max(0, min(before, 10)))).fetchall()
        post = c.execute("SELECT * FROM obs WHERE tenant=? AND repo=? AND created_epoch>=? AND id<>? ORDER BY created_epoch, id "
                         "LIMIT ?", (tenant, repo, a["created_epoch"], a["id"], max(0, min(after, 10)))).fetchall()
    return [_row(r) for r in reversed(pre)] + [{**_row(a), "anchor": True}] + [_row(r) for r in post]


def get(tenant: str, repo: str, ids: list[Any]) -> list[dict[str, Any]]:
    """Step 3: the full details, only for the ids chosen."""
    want = [int(str(i).strip().lstrip("#")) for i in (ids or []) if str(i).strip().lstrip("#").isdigit()][:20]
    if not want:
        return []
    with db() as c:
        rows = c.execute(f"SELECT * FROM obs WHERE tenant=? AND repo=? AND id IN ({','.join('?' * len(want))})",
                         [tenant, repo] + want).fetchall()
    return [_row(r, full=True) for r in rows]


def summaries(tenant: str, repo: str, limit: int = 6) -> list[dict[str, Any]]:
    with db() as c:
        rows = c.execute("SELECT * FROM summaries WHERE tenant=? AND repo=? ORDER BY created_epoch DESC, id DESC LIMIT ?",
                         (tenant, repo, max(1, min(limit, 50)))).fetchall()
    return [{k: (r[k] if k != "files_edited" else _j(r[k])) for k in r.keys()} for r in rows]


def forget(tenant: str, oid: int) -> bool:
    with db() as c:
        return c.execute("DELETE FROM obs WHERE id=? AND tenant=?", (int(oid), tenant)).rowcount > 0


def forget_summary(tenant: str, sid: int) -> bool:
    with db() as c:
        return c.execute("DELETE FROM summaries WHERE id=? AND tenant=?", (int(sid), tenant)).rowcount > 0


def forget_repo(tenant: str, repo: str) -> dict[str, int]:
    with db() as c:
        a = c.execute("DELETE FROM obs WHERE tenant=? AND repo=?", (tenant, repo)).rowcount
        b = c.execute("DELETE FROM summaries WHERE tenant=? AND repo=?", (tenant, repo)).rowcount
    return {"observations": a, "summaries": b}


def counts(tenant: str, repo: str) -> dict[str, int]:
    with db() as c:
        a = c.execute("SELECT COUNT(*) FROM obs WHERE tenant=? AND repo=?", (tenant, repo)).fetchone()[0]
        b = c.execute("SELECT COUNT(*) FROM summaries WHERE tenant=? AND repo=?", (tenant, repo)).fetchone()[0]
    return {"observations": int(a), "summaries": int(b)}


# ---------------------------------------------------------------- the primer a new session starts with
def _ago(ep: int) -> str:
    d = max(0, int(time.time()) - int(ep or 0))
    return "today" if d < 86400 else f"{d // 86400} day{'s' if d >= 172800 else ''} ago"


def primer(tenant: str, repo: str, budget: int = 0) -> str:
    """The repo's memory as an INDEX for a new session, fitted to the budget by measuring: drop the full narratives,
    then the last-session block, then older summary lines, then the oldest index lines - whole items only."""
    if not on() or not repo:
        return ""
    budget = int(budget or _set("dev_memory_primer_chars", 6000) or 6000)
    obs = search(tenant, repo, limit=40)
    sums = summaries(tenant, repo, limit=6)
    if not obs and not sums:
        return ""
    full = get(tenant, repo, [o["id"] for o in obs if o["type"] in ("decision", "security_alert", "bugfix")][:3])
    head = (f"<repo_memory repo=\"{repo}\">\nWhat earlier Hoola Code sessions on this repo recorded (newest first). It is an "
            "INDEX: before you rely on an item, open it with the memory tool (action=get, ids=[...]); search older ones with "
            "action=search. The code in the working copy is the truth when they disagree - say so and move on.")
    foot = "</repo_memory>"
    n_obs, show_full, show_last, n_sums = len(obs), bool(full), bool(sums), max(0, len(sums) - 1)

    def render() -> str:
        parts = [head]
        if show_last and sums:
            s = sums[0]
            parts.append(f"Last session ({_ago(s['created_epoch'])}): asked: {s['request'][:300]}\n  completed: "
                         f"{s['completed'][:400]}\n  learned: {s['learned'][:400]}\n  next: {s['next_steps'][:300]}")
        if n_sums:
            parts.append("Earlier sessions:\n" + "\n".join(f"- {_ago(s['created_epoch'])}: {s['request'][:120]} -> "
                                                            f"{s['completed'][:160]}" for s in sums[1:1 + n_sums]))
        if n_obs:
            parts.append("Index (#id [type] title - files):\n" + "\n".join(
                f"#{o['id']} [{o['type']}] {o['title']}" + (f" - {o['subtitle'][:90]}" if o["subtitle"] else "")
                + (f" ({', '.join(o['files'][:3])})" if o["files"] else "") + (f" x{o['hits']}" if o["hits"] > 1 else "")
                for o in obs[:n_obs]))
        if show_full and full:
            parts.append("Worth knowing in full:\n" + "\n".join(f"#{f['id']} {f['title']}: {f['narrative'][:500]}" for f in full))
        return "\n\n".join(parts + [foot])
    text = render()
    while len(text) > budget:
        if show_full:
            show_full = False
        elif show_last and (n_sums or n_obs > 3):
            show_last = False
        elif n_sums:
            n_sums -= 1
        elif n_obs > 1:
            n_obs -= max(1, n_obs // 8)
        else:
            break
        text = render()
    STATS["primers"] += 1
    return text


# ---------------------------------------------------------------- the tool the coder uses
TOOL = {
    "name": "memory",
    "description": ("This repo's memory from earlier Hoola Code sessions (the <repo_memory> index in your first message). "
                    "Three steps, cheapest first: action=search (query, optional type) -> a short index with ids; "
                    "action=timeline (id) -> what happened around it; action=get (ids) -> full details of only those. "
                    "action=save (title, text, type) records something a future session must know (a decision and why, a "
                    "gotcha). Never save a key, a password or her private text."),
    "input_schema": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["search", "timeline", "get", "save"]},
        "query": {"type": "string"}, "type": {"type": "string", "enum": sorted(TYPES)},
        "id": {"type": "integer"}, "ids": {"type": "array", "items": {"type": "integer"}},
        "title": {"type": "string"}, "text": {"type": "string"}, "files": {"type": "array", "items": {"type": "string"}}},
        "required": ["action"]},
}


def _line(o: dict[str, Any]) -> str:
    return (f"#{o['id']} [{o['type']}] {o['title']}" + (f" - {o['subtitle']}" if o.get("subtitle") else "")
            + (f" ({', '.join(o.get('files') or [])})" if o.get("files") else "") + f" · {_ago(o.get('at', 0))}"
            + (" <- this one" if o.get("anchor") else ""))


def tool(tenant: str, repo: str, task: str, inp: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Runs one memory call. Returns (text for the coder, page event)."""
    act = str((inp or {}).get("action") or "")
    try:
        if act == "search":
            rows = search(tenant, repo, str(inp.get("query") or ""), str(inp.get("type") or ""), 15)
            out = "\n".join(_line(o) for o in rows) or "Nothing in this repo's memory matches."
            return out + ("\n(Open the ones that matter with action=get ids=[...].)" if rows else ""), \
                {"k": "memory", "action": "search", "q": str(inp.get("query") or "")[:80], "n": len(rows)}
        if act == "timeline":
            rows = timeline(tenant, repo, int(inp.get("id") or 0))
            return ("\n".join(_line(o) for o in rows) or "No such memory in this repo."), \
                {"k": "memory", "action": "timeline", "n": len(rows)}
        if act == "get":
            rows = get(tenant, repo, inp.get("ids") or ([inp["id"]] if inp.get("id") else []))
            if not rows:
                return "No such memory in this repo.", {"k": "memory", "action": "get", "n": 0}
            txt = "\n\n".join(f"#{r['id']} [{r['type']}] {r['title']}\n{r['subtitle']}\n{r['narrative']}"
                              + ("\nFacts: " + "; ".join(r["facts"]) if r["facts"] else "")
                              + ("\nFiles: " + ", ".join(r["files_modified"] or r["files_read"]) if (r["files_modified"] or r["files_read"]) else "")
                              for r in rows)
            return txt, {"k": "memory", "action": "get", "n": len(rows)}
        if act == "save":
            oid = store(tenant, repo, task, {"type": inp.get("type") or "decision", "title": inp.get("title"),
                                             "narrative": inp.get("text"), "files_modified": inp.get("files") or []},
                        source="saved")
            if oid is None:
                return "Not saved: give a title and a type from the list (never a key or her private text).", \
                    {"k": "memory", "action": "save", "n": 0}
            return f"Saved as #{oid}.", {"k": "memory", "action": "save", "n": 1, "title": _clean(inp.get("title"), 120)}
    except Exception as e:                                # memory never breaks a round
        log.warning("memory tool failed: %s", e)
        return f"The memory could not be read right now ({e.__class__.__name__}).", {}
    return "Unknown action: use search, timeline, get or save.", {}


# ---------------------------------------------------------------- capture: the observer at the end of a round
OBSERVER = """You are the memory observer for Hoola Code, a coding assistant working in the owner's repository. You are
given the record of ONE finished round of work. Write what a FUTURE session on this repo must know, so it does not have
to rediscover it. You do not do the work and you have no tools; record only what the record shows.

Record durable technical signal: what was built / fixed / changed and how, how the existing system works (where things
live, how parts talk), decisions and their reasons, gotchas and traps, commands that are the right way to test or build,
security findings. Write titles as short facts ("Cart total no longer divides by item count - empty carts crashed"),
not as actions of yours. Facts are short, checkable sentences with file paths and names.
{focus}
Skip: anything obvious from reading the code or git log, the step-by-step story, failed attempts that taught nothing,
chit-chat, and everything private. NEVER write a key, token, password, personal data or anything inside <private>.
If the round produced nothing worth remembering, return no observations.

Types: {types}. Concepts (0-3 each): {concepts}.
Answer with ONE JSON object and nothing else:
{{"observations": [{{"type": "...", "title": "...", "subtitle": "one line", "facts": ["..."], "narrative": "2-5 sentences",
"concepts": ["..."], "files_read": ["path"], "files_modified": ["path"]}}],
"summary": {{"request": "what she asked", "investigated": "...", "learned": "...", "completed": "...",
"next_steps": "what is left / what she might ask next"}}}}
At most {max_obs} observations."""
FOCUS = {"code": "Record every meaningful finding of the round.",
         "chill": "SELECTIVE: only what would be painful to rediscover - a shipped feature or fix, a decision and its "
                  "reason, a non-obvious gotcha, a big restructure. Skip incremental steps and anything plain from the code."}


def _record(t: Any, follow_up: str, ctx: dict[str, Any], out: dict[str, Any], says: list[str]) -> str:
    loop = ((ctx or {}).get("found") or {}).get("loop") or {}
    files = [f.get("path", "") for f in (out or {}).get("files") or []]
    parts = [f"Repo: {getattr(t, 'repo', '')}", "Her request: " + _clean(follow_up or getattr(t, "text", ""), 3000)]
    if follow_up:
        parts.append("(The session began with: " + _clean(getattr(t, "text", ""), 800) + ")")
    parts.append("Steps taken:\n" + "\n".join(_clean(x, 200) for x in (loop.get("trail") or [])[-60:]))
    if says:
        parts.append("What the coder said while working:\n" + "\n".join(_clean(x, 600) for x in says[-12:]))
    for k in ("explain", "cause", "test_plan", "risk"):
        if (out or {}).get(k):
            parts.append(f"Coder's final {k}: " + _clean(out[k], 1500))
    parts.append("Files changed: " + (", ".join(files[:40]) or "none"))
    if loop.get("reality"):
        parts.append(f"Independent reality check: {loop['reality']}")
    return "\n\n".join(parts)[:40000]


def _parse(text: str) -> dict[str, Any]:
    s = str(text or "")
    a, b = s.find("{"), s.rfind("}")
    if a < 0 or b <= a:
        return {}
    try:
        v = json.loads(s[a:b + 1])
        return v if isinstance(v, dict) else {}
    except ValueError:
        return {}


def capture(t: Any, follow_up: str, ctx: dict[str, Any], out: dict[str, Any], messages: list[dict] | None = None) -> dict[str, Any]:
    """The observer for one finished round. Never raises; nothing is stored for an all-private request."""
    res = {"observations": 0, "summary": False}
    if not on():
        return res
    tenant, repo, task = str(getattr(t, "tenant_id", "") or ""), str(getattr(t, "repo", "") or ""), str(getattr(t, "id", ""))
    ask = str(follow_up or getattr(t, "text", "") or "")
    if not repo or (ask.strip() and not _clean(ask)):      # her whole ask was <private>: nothing of it is kept
        STATS["skipped"] += 1
        return res
    says = []
    for m in (messages or [])[-40:]:
        if m.get("role") == "assistant" and isinstance(m.get("content"), list):
            says += [str(b.get("text") or "") for b in m["content"] if b.get("type") == "text" and str(b.get("text") or "").strip()]
    mode = str(_set("dev_memory_mode", "code") or "code")
    system = OBSERVER.format(focus=FOCUS.get(mode, FOCUS["code"]), types=", ".join(f"{k} ({v})" for k, v in TYPES.items()),
                             concepts=", ".join(CONCEPTS), max_obs=6 if mode == "code" else 3)
    from . import brain as B
    old = (getattr(B.PICK, "model", ""), getattr(B.PICK, "effort", ""))
    B.PICK.model, B.PICK.effort = str(_set("dev_memory_model", "claude-haiku-5-5") or ""), "low"
    try:
        blocks, _ = B.call(system, [{"role": "user", "content": "<round>\n" + _record(t, follow_up, ctx, out, says)
                                     + "\n</round>"}], [], max_tokens=3000, think=False)
    except Exception as e:
        log.warning("memory capture failed: %s", e)
        return res
    finally:
        B.PICK.model, B.PICK.effort = old
    data = _parse(" ".join(str(b.get("text") or "") for b in blocks if b.get("type") == "text"))
    for o in (data.get("observations") or [])[:6 if mode == "code" else 3]:
        if isinstance(o, dict) and store(tenant, repo, task, o) is not None:
            res["observations"] += 1
    if isinstance(data.get("summary"), dict):
        res["summary"] = store_summary(tenant, repo, task, data["summary"],
                                       [f.get("path", "") for f in (out or {}).get("files") or []]) is not None
    STATS["captured"] += 1
    return res
