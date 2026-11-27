"""v0.999.240 NEW TRIGGERS (R5 of the Hoola Route plan; owner: "GO R5").

What can start a route, beside by hand, a schedule and a web address (webhook):

- event   an app event, looked for every few minutes: a new email, a new row in a sheet, a new form answer, a new calendar
          event, a new Drive file, a new item in an RSS feed, or any connected app's list (new payments, orders, tickets)
          through a tool that only reads. The first look only notes what is already there (nothing runs for old items);
          after that each new item starts one run with the item as {{vars.event}}.
- form    a Hoola form page at its own address: her fields; each answer starts a run with {{vars.form}}. A Respond step's
          answer is shown to the person who sent the form.
- chat    a Hoola chat page at its own address: each message starts a run with {{vars.message}} and the conversation so
          far ({{vars.history}}); the route's Respond step is the reply.
- error   when another route fails (one she names, or any): {{vars.failed_route}}, {{vars.error}}, {{vars.failed_run}}.
- route   called by another route (a Run another route step) with the inputs it says it takes.
- tool    offered as a tool to AI apps: her routes marked so are the tools of her own MCP address (one per account,
          shown once); an AI app calls one and gets the route's answer.

Everything here is data checked in code; a poll never sends anything (a tool must only read); public pages are rate
limited and never show her data except what a Respond step answers.
"""
from __future__ import annotations

import asyncio
import hashlib
import html
import json
import logging
import re
import secrets
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("santosh.routetrig")

KINDS = ("manual", "schedule", "webhook", "event", "form", "chat", "error", "route", "tool")
TOKEN_KINDS = ("webhook", "form", "chat")      # started from an address of their own
PUBLIC_KINDS = ("form", "chat")                # the address is meant to be shared, so it is kept to show again
_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

EVENTS: dict[str, dict[str, Any]] = {
    "email": {"title": "New email", "tool": "email_check"},
    "sheet_row": {"title": "New row in a sheet", "tool": "sheet_read"},
    "form_answer": {"title": "New answer to a Google form", "tool": "form_responses"},
    "calendar_event": {"title": "New calendar event", "tool": "calendar_agenda"},
    "drive_file": {"title": "New file in Drive", "tool": "drive_find"},
    "rss": {"title": "New item in a feed (RSS / Atom)", "tool": ""},
    "app": {"title": "New item in another app", "tool": ""},
}
EVERY_MIN, EVERY_MAX, EVERY_DEFAULT = 5, 1440, 15
RUNS_PER_POLL = 20
SEEN_MAX = 5000
FAILS_TO_TELL = 5
FORM_TYPES = ("text", "textarea", "email", "number", "date", "select", "checkbox", "phone")
FORM_FIELDS_MAX = 30
INPUTS_MAX = 20
INPUT_TYPES = ("string", "number", "boolean", "object", "array")
PUBLIC_PER_MIN = 30           # form answers / chat messages per route per minute
CHAT_KEEP = 40                # messages kept per chat conversation
CHAT_DAYS = 7
READ_WORDS = ("check", "read", "list", "find", "agenda", "dekho", "responses", "search", "status", "get", "fetch",
              "query", "lookup", "watch_list")
_PUB_HITS: dict[str, list[float]] = {}


class TriggerError(ValueError):
    pass


def _err(msg: str) -> None:
    from ..agent.tools import ToolError
    raise ToolError(msg)


# ---------------------------------------------------------------- validation
def _txt(v: Any, cap: int) -> str:
    return str(v or "").strip()[:cap]


def _inputs(spec_inputs: Any, what: str) -> list[dict]:
    out: list[dict] = []
    if spec_inputs in (None, ""):
        return out
    if not isinstance(spec_inputs, list):
        _err(f"{what}: inputs must be a list of {{name, description}}")
    if len(spec_inputs) > INPUTS_MAX:
        _err(f"{what}: at most {INPUTS_MAX} inputs")
    seen = set()
    for i, x in enumerate(spec_inputs):
        if isinstance(x, str):
            x = {"name": x}
        if not isinstance(x, dict) or not _NAME.match(str(x.get("name") or "")):
            _err(f"{what}: input {i + 1} needs a short name (letters, digits, _)")
        nm = str(x["name"])
        if nm in seen:
            _err(f"{what}: the input '{nm}' is there twice")
        seen.add(nm)
        typ = str(x.get("type") or "string")
        if typ not in INPUT_TYPES:
            _err(f"{what}: input type must be one of: {', '.join(INPUT_TYPES)}")
        out.append({"name": nm, "description": _txt(x.get("description"), 300), "type": typ,
                    "required": bool(x.get("required"))})
    return out


def read_only(tool: str, args: dict | None) -> bool:
    """A trigger only reads: the tool's name (or, for a tool that runs an app's action, that action) must read."""
    t = str(tool or "").lower()
    act = ""
    for k in ("action", "tool", "tool_slug", "slug", "operation"):
        if isinstance((args or {}).get(k), str):
            act = str(args[k]).lower()
            break
    words = re.split(r"[^a-z]+", (t + " " + act))
    if act and not any(w in READ_WORDS for w in re.split(r"[^a-z]+", act)):
        return False
    return any(w in READ_WORDS for w in words)


def validate(kind: str, spec: Any, settings: dict | None = None) -> dict:
    """The trigger's spec, checked and normalised. Raises ToolError with the first problem."""
    from ..agent import dhara_tools as D
    kind = str(kind or "manual").lower()
    if kind not in KINDS:
        _err("A route starts: by hand (manual), on a schedule, when data arrives (webhook), on an app event (event), "
             "from a form (form), from a chat (chat), when a route fails (error), when another route calls it (route) "
             "or as a tool for AI apps (tool)")
    sp = dict(spec or {}) if isinstance(spec, dict) else {}
    if kind == "schedule":
        return D.validate_schedule(sp, settings)
    if kind in ("manual", "webhook"):
        return {}
    if kind == "event":
        app = str(sp.get("app") or "")
        if app not in EVENTS:
            _err(f"An app event needs app = one of: {', '.join(EVENTS)}")
        try:
            every = int(sp.get("every_minutes") or EVERY_DEFAULT)
        except (TypeError, ValueError):
            _err("every_minutes must be a whole number")
        if not EVERY_MIN <= every <= EVERY_MAX:
            _err(f"An app event is looked for every {EVERY_MIN} to {EVERY_MAX} minutes")
        out: dict[str, Any] = {"app": app, "every_minutes": every}
        if app == "email":
            for k in ("folder", "search", "account"):
                if sp.get(k):
                    out[k] = _txt(sp[k], 300)
            out["unread_only"] = bool(sp.get("unread_only"))
        elif app == "sheet_row":
            if not str(sp.get("spreadsheet") or "").strip():
                _err("A new-row event needs the sheet (its name, link or id)")
            out["spreadsheet"] = _txt(sp["spreadsheet"], 300)
            if sp.get("tab"):
                out["tab"] = _txt(sp["tab"], 100)
        elif app == "form_answer":
            if not str(sp.get("form") or "").strip():
                _err("A new-answer event needs the form (its name, link or id)")
            out["form"] = _txt(sp["form"], 300)
        elif app == "calendar_event":
            if sp.get("query"):
                out["query"] = _txt(sp["query"], 200)
        elif app == "drive_file":
            for k in ("query", "folder"):
                if sp.get(k):
                    out[k] = _txt(sp[k], 300)
        elif app == "rss":
            url = str(sp.get("url") or "").strip()
            if not re.match(r"^https?://[^\s/]+", url):
                _err("A feed event needs the feed's web address (https://...)")
            out["url"] = url[:500]
        elif app == "app":
            from ..agent.tools import HANDLERS
            tool = str(sp.get("tool") or "").strip()
            if tool not in HANDLERS:
                _err(f"'{tool}' is not one of Hoola's tools")
            args = sp.get("args") or {}
            if not isinstance(args, dict):
                _err("args must be an object of name: value")
            if not read_only(tool, args):
                _err("An app event can only read: pick a tool (or an app action) that lists, gets or searches - "
                     "a trigger never sends, changes or deletes anything")
            out.update({"tool": tool, "args": args})
            for k in ("items", "id"):
                if sp.get(k):
                    if not D._PATH_RE.match(str(sp[k])):
                        _err(f"{k} must be a field path like data.items")
                    out[k] = str(sp[k])
        return out
    if kind == "form":
        fields = sp.get("fields")
        if not isinstance(fields, list) or not fields:
            _err("A form needs at least one field")
        if len(fields) > FORM_FIELDS_MAX:
            _err(f"A form can have up to {FORM_FIELDS_MAX} fields")
        norm, names = [], set()
        for i, f in enumerate(fields):
            if not isinstance(f, dict) or not _NAME.match(str(f.get("name") or "")):
                _err(f"Form field {i + 1} needs a short name (letters, digits, _), used as {{{{vars.form.name}}}}")
            nm = str(f["name"])
            if nm in names or nm.startswith("_"):
                _err(f"Form field name '{nm}' is used twice or starts with _")
            names.add(nm)
            typ = str(f.get("type") or "text")
            if typ not in FORM_TYPES:
                _err(f"Form field type must be one of: {', '.join(FORM_TYPES)}")
            d = {"name": nm, "label": _txt(f.get("label") or nm.replace("_", " ").capitalize(), 120), "type": typ,
                 "required": bool(f.get("required"))}
            if f.get("placeholder"):
                d["placeholder"] = _txt(f["placeholder"], 120)
            if typ == "select":
                opts = [str(o).strip()[:100] for o in (f.get("options") or []) if str(o).strip()]
                if not opts or len(opts) > 50:
                    _err(f"The choice field '{nm}' needs 1 to 50 options")
                d["options"] = opts
            norm.append(d)
        return {"title": _txt(sp.get("title") or "A form", 120), "intro": _txt(sp.get("intro"), 1000),
                "button": _txt(sp.get("button") or "Send", 40), "thanks": _txt(sp.get("thanks") or "Thank you - it was sent.", 500),
                "fields": norm}
    if kind == "chat":
        return {"title": _txt(sp.get("title") or "Chat", 120), "greeting": _txt(sp.get("greeting") or "Hi! How can I help?", 500),
                "placeholder": _txt(sp.get("placeholder") or "Write a message", 120)}
    if kind == "error":
        routes = sp.get("routes") or []
        if isinstance(routes, str):
            routes = [r.strip() for r in routes.split(",")]
        if not isinstance(routes, list):
            _err("routes must be a list of route names (empty = any route)")
        rs = []
        for r in routes:
            n = str(r or "").strip().lower().replace(" ", "_")
            if n and not D._PATH_RE.match(n):
                _err(f"'{r}' is not a route name")
            if n:
                rs.append(n)
        return {"routes": rs[:50]}
    if kind == "route":
        return {"inputs": _inputs(sp.get("inputs"), "Called by another route")}
    if kind == "tool":
        desc = _txt(sp.get("description"), 500)
        if not desc:
            _err("A route offered as a tool needs a description: what it does, so an AI app knows when to use it")
        return {"description": desc, "inputs": _inputs(sp.get("inputs"), "Offered as a tool")}
    return {}


# ---------------------------------------------------------------- tables
def _con(tenant: str):
    from ..agent import dhara_tools as D
    con = D._con(tenant)
    con.execute("CREATE TABLE IF NOT EXISTS route_seen (workflow_id TEXT, item TEXT, at REAL, PRIMARY KEY (workflow_id, item))")
    con.execute("CREATE TABLE IF NOT EXISTS route_poll (workflow_id TEXT PRIMARY KEY, spec_hash TEXT, baselined INTEGER DEFAULT 0, "
                "state TEXT DEFAULT '{}', last_at REAL, last_error TEXT, fails INTEGER DEFAULT 0, last_new INTEGER DEFAULT 0, "
                "told INTEGER DEFAULT 0)")
    con.execute("CREATE TABLE IF NOT EXISTS route_chat (workflow_id TEXT, session TEXT, role TEXT, text TEXT, at REAL)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_route_chat ON route_chat (workflow_id, session, at)")
    con.execute("CREATE TABLE IF NOT EXISTS route_keys (kind TEXT PRIMARY KEY, token_hash TEXT, created_at REAL)")
    return con


def _hash(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, default=str).encode()).hexdigest()


def poll_state(tenant: str, wf_id: str) -> dict:
    con = _con(tenant)
    try:
        r = con.execute("SELECT * FROM route_poll WHERE workflow_id = ?", (wf_id,)).fetchone()
        n = con.execute("SELECT COUNT(*) FROM route_seen WHERE workflow_id = ?", (wf_id,)).fetchone()[0]
    finally:
        con.close()
    if r is None:
        return {"looked": False, "seen": int(n)}
    return {"looked": bool(r["baselined"]), "last_at": r["last_at"], "error": r["last_error"] or "", "fails": int(r["fails"] or 0),
            "last_new": int(r["last_new"] or 0), "seen": int(n)}


def forget(tenant: str, wf_id: str) -> None:
    con = _con(tenant)
    try:
        for t in ("route_seen", "route_poll", "route_chat"):
            con.execute(f"DELETE FROM {t} WHERE workflow_id = ?", (wf_id,))
        con.commit()
    finally:
        con.close()


def rebaseline(tenant: str, wf_id: str) -> None:
    """Switched on again: the next look only notes what is there (no runs for what came while it was off)."""
    con = _con(tenant)
    try:
        con.execute("UPDATE route_poll SET baselined = 0 WHERE workflow_id = ?", (wf_id,))
        con.commit()
    finally:
        con.close()


# ---------------------------------------------------------------- app events (polling)
def items_of(out: Any, path: str = "") -> list:
    from ..agent import dhara_tools as D
    if path:
        v = D._dig(out, path) if isinstance(out, (dict, list)) else None
        return v if isinstance(v, list) else []
    if isinstance(out, list):
        return out
    if isinstance(out, dict):
        for k in ("items", "emails", "messages", "rows", "responses", "events", "files", "results", "data", "entries",
                  "records", "list"):
            v = out.get(k)
            if isinstance(v, list):
                return v
            if isinstance(v, dict):
                inner = items_of(v)
                if inner:
                    return inner
        for v in out.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
    return []


def id_of(x: Any, field: str = "") -> str:
    from ..agent import dhara_tools as D
    if field and isinstance(x, (dict, list)):
        v = D._dig(x, field)
        if v not in (None, ""):
            return str(v)[:300]
    if isinstance(x, dict):
        for k in ("id", "response_id", "responseId", "event_id", "message_id", "messageId", "guid", "_row", "link",
                  "url", "uid", "key"):
            if x.get(k) not in (None, ""):
                return f"{k}:{x[k]}"[:300]
    return "h:" + _hash(x)[:24]


def _rss_parse(text: str) -> list[dict]:
    import xml.etree.ElementTree as ET
    if "<!DOCTYPE" in text[:2000].upper() or "<!ENTITY" in text[:5000].upper():
        raise TriggerError("The feed uses XML features Hoola does not read (a DOCTYPE)")
    try:
        root = ET.fromstring(text.encode("utf-8", "replace"))
    except ET.ParseError as e:
        raise TriggerError(f"This is not an RSS or Atom feed ({str(e)[:80]})")
    strip = lambda t: t.split("}", 1)[-1] if "}" in t else t  # noqa: E731
    out = []
    for el in root.iter():
        tag = strip(el.tag)
        if tag not in ("item", "entry"):
            continue
        d: dict[str, Any] = {}
        for ch in el:
            k = strip(ch.tag)
            if k == "link" and ch.get("href"):
                d.setdefault("link", ch.get("href"))
            elif k in ("title", "link", "guid", "id", "pubDate", "published", "updated", "description", "summary",
                       "author", "category", "content", "encoded"):
                v = "".join(ch.itertext()).strip()
                if v:
                    d.setdefault({"pubDate": "published", "encoded": "content", "summary": "description",
                                  "id": "guid"}.get(k, k), v[:4000])
        if d:
            out.append(d)
        if len(out) >= 200:
            break
    return out


async def _rss(url: str) -> list[dict]:
    import httpx
    from ..agent import scrape_tools as st
    guard = await asyncio.to_thread(st._guard_url, url)

    def go():
        r = httpx.get(guard, timeout=httpx.Timeout(20.0), follow_redirects=True,
                      headers={"User-Agent": "Hoola Route feed reader", "Accept": "application/rss+xml, application/atom+xml, text/xml, */*"})
        if r.status_code >= 400:
            raise TriggerError(f"The feed answered {r.status_code}")
        return r.text[:3_000_000]
    return _rss_parse(await asyncio.to_thread(go))


async def _read(tenant: str, wf: dict, sp: dict, state: dict) -> tuple[list, str, bool]:
    """(items, id field, newest_first) for one look."""
    from ..agent.tools import Ctx, HANDLERS
    app = sp.get("app")
    if app == "rss":
        return await _rss(sp["url"]), "", True
    ctx = Ctx(tenant_id=tenant, conversation_id=wf.get("conversation_id") or "", actor="routine")

    async def call(name: str, **args):
        if name not in HANDLERS:
            raise TriggerError(f"The tool {name} is not on this server")
        args = {k: v for k, v in args.items() if v not in (None, "")}
        return await asyncio.wait_for(HANDLERS[name](ctx, **args), 90)
    if app == "email":
        out = await call("email_check", folder=sp.get("folder") or "inbox", unread_only=bool(sp.get("unread_only")),
                         search=sp.get("search") or "", limit=30, account=sp.get("account"))
        return items_of(out), "", True
    if app == "form_answer":
        return items_of(await call("form_responses", form=sp["form"], limit=50)), "", True
    if app == "calendar_event":
        import datetime as _dt
        d0 = _dt.date.today()
        out = await call("calendar_agenda", from_date=d0.isoformat(), to_date=(d0 + _dt.timedelta(days=60)).isoformat(),
                         query=sp.get("query"))
        return items_of(out), "", False
    if app == "drive_file":
        return items_of(await call("drive_find", query=sp.get("query") or "", folder=sp.get("folder"), modified_days=7,
                                   order="newest")), "", True
    if app == "sheet_row":
        rows, offset = [], int(state.get("offset") or 0)
        for _ in range(50 if not state.get("offset_known") else 5):
            out = await call("sheet_read", spreadsheet=sp["spreadsheet"], tab=sp.get("tab"), limit=100, offset=offset)
            page = items_of(out)
            rows.extend(page)
            offset += len(page)
            if len(page) < 100:
                break
        state["offset"], state["offset_known"] = offset, True
        return rows, "_row", False
    if app == "app":
        out = await call(sp["tool"], **(sp.get("args") or {}))
        return items_of(out, sp.get("items") or ""), sp.get("id") or "", True
    raise TriggerError("Unknown app event")


_POLLING: set[str] = set()


async def poll(tenant: str, wf: dict) -> dict:
    """One look for new items: a new item starts a run with {{vars.event}}. The first look only notes what is there."""
    from ..agent import dhara_tools as D
    key = f"{tenant}:{wf['id']}"
    if key in _POLLING:
        return {"skipped": "already looking"}
    _POLLING.add(key)
    try:
        sp = wf.get("trigger_spec") or {}
        shash = _hash(sp)
        con = _con(tenant)
        try:
            r = con.execute("SELECT * FROM route_poll WHERE workflow_id = ?", (wf["id"],)).fetchone()
            if r is None or r["spec_hash"] != shash:
                con.execute("DELETE FROM route_seen WHERE workflow_id = ?", (wf["id"],))
                con.execute("INSERT OR REPLACE INTO route_poll (workflow_id, spec_hash, baselined, state, fails, told) "
                            "VALUES (?, ?, 0, '{}', 0, 0)", (wf["id"], shash))
                con.commit()
                r = con.execute("SELECT * FROM route_poll WHERE workflow_id = ?", (wf["id"],)).fetchone()
            baselined = bool(r["baselined"])
            try:
                state = json.loads(r["state"] or "{}")
            except ValueError:
                state = {}
        finally:
            con.close()
        try:
            items, idf, newest_first = await _read(tenant, wf, sp, state)
        except Exception as e:   # noqa: BLE001  (a failed look is noted and said after a few in a row)
            from ..agent.tools import ToolError
            why = str(e) if isinstance(e, (TriggerError, ToolError)) else f"{type(e).__name__}: {str(e)[:200]}"
            if isinstance(e, asyncio.TimeoutError):
                why = "the app took too long to answer"
            con = _con(tenant)
            try:
                con.execute("UPDATE route_poll SET last_at = ?, last_error = ?, fails = COALESCE(fails, 0) + 1 WHERE workflow_id = ?",
                            (time.time(), why[:400], wf["id"]))
                row = con.execute("SELECT fails, told FROM route_poll WHERE workflow_id = ?", (wf["id"],)).fetchone()
                tell = row is not None and int(row["fails"]) >= FAILS_TO_TELL and not row["told"]
                if tell:
                    con.execute("UPDATE route_poll SET told = 1 WHERE workflow_id = ?", (wf["id"],))
                con.commit()
            finally:
                con.close()
            if tell:
                D._notify(wf.get("conversation_id") or "", f'Route "{wf["name"]}" could not look for new items '
                          f'{FAILS_TO_TELL} times in a row: {why[:200]}. It keeps trying.')
            return {"ok": False, "error": why}
        ids = [(id_of(x, idf), x) for x in items]
        con = _con(tenant)
        try:
            seen = {row[0] for row in con.execute("SELECT item FROM route_seen WHERE workflow_id = ?", (wf["id"],))}
            new = [(i, x) for i, x in ids if i not in seen]
            if newest_first:
                new.reverse()               # the oldest new item runs first
            # v0.999.253 ROUTE CHECK: only items that really start a run are marked seen (the first look notes them
            # all); the rest - more than 20 at once, or the day's run limit reached - start at the next look.
            # They used to be marked seen and lost.
            go: list = []
            if baselined:
                for i, x in new[:RUNS_PER_POLL]:
                    if D._over_daily_cap(tenant, wf):
                        break
                    go.append((i, x))
            mark = new if not baselined else go
            now_ = time.time()
            con.executemany("INSERT OR IGNORE INTO route_seen (workflow_id, item, at) VALUES (?, ?, ?)",
                            [(wf["id"], i, now_) for i, _ in mark])
            extra = con.execute("SELECT COUNT(*) FROM route_seen WHERE workflow_id = ?", (wf["id"],)).fetchone()[0] - SEEN_MAX
            if extra > 0:
                con.execute("DELETE FROM route_seen WHERE rowid IN (SELECT rowid FROM route_seen WHERE workflow_id = ? "
                            "ORDER BY at LIMIT ?)", (wf["id"], int(extra)))
            con.execute("UPDATE route_poll SET baselined = 1, state = ?, last_at = ?, last_error = '', fails = 0, told = 0, "
                        "last_new = ? WHERE workflow_id = ?",
                        (json.dumps(state), now_, len(new) if baselined else 0, wf["id"]))
            con.commit()
        finally:
            con.close()
        if not baselined:
            return {"ok": True, "first_look": True, "noted": len(ids)}
        for _i, x in go:
            D.create_run(tenant, wf, vars_={"event": x, "app": sp.get("app")})
        return {"ok": True, "new": len(new), "started": len(go), "waiting": len(new) - len(go)}
    finally:
        _POLLING.discard(key)


def events_due(tenant: str) -> list[dict]:
    """Switched-on app-event routes whose look is due; the next look is set at once (fire-once)."""
    from ..agent import dhara_tools as D
    con = D._con(tenant)
    out = []
    try:
        now_ = time.time()
        rows = con.execute("SELECT * FROM workflows WHERE enabled = 1 AND trigger_kind = 'event' AND "
                           "(next_due_at IS NULL OR next_due_at <= ?) LIMIT 10", (now_,)).fetchall()
        for r in rows:
            wf = D._wf_row(r)
            every = int((wf.get("trigger_spec") or {}).get("every_minutes") or EVERY_DEFAULT)
            con.execute("UPDATE workflows SET next_due_at = ? WHERE id = ?", (now_ + every * 60, wf["id"]))
            out.append(wf)
        con.commit()
    finally:
        con.close()
    return out


# ---------------------------------------------------------------- error trigger
def error_watchers(tenant: str, failed: dict) -> list[dict]:
    """Switched-on routes started 'when a route fails' that watch this route (or any route)."""
    from ..agent import dhara_tools as D
    if failed.get("trigger_kind") == "error":
        return []                       # a failing error route never starts error routes (no chains)
    con = D._con(tenant)
    try:
        rows = con.execute("SELECT * FROM workflows WHERE enabled = 1 AND trigger_kind = 'error'").fetchall()
    finally:
        con.close()
    out = []
    for r in rows:
        wf = D._wf_row(r)
        names = (wf.get("trigger_spec") or {}).get("routes") or []
        if wf["id"] != failed["id"] and (not names or failed["name"] in names):
            out.append(wf)
    return out


# ---------------------------------------------------------------- public addresses (form, chat)
def _find(token: str, kinds: tuple) -> tuple[str, dict | None]:
    from ..agent import dhara_tools as D
    th = hashlib.sha256(str(token or "").encode()).hexdigest()
    root = Path("data") / "dhara"
    for p in sorted(root.glob("*/dhara.db")) if root.is_dir() else []:
        t = p.parent.name
        hit = D.workflows_with_hash(t, th)
        if hit is not None and hit.get("trigger_kind") in kinds:
            return t, hit
    return "", None


def make_address(tenant: str, wf: dict) -> dict:
    """A new address for a route started from one (webhook, form, chat). A form's / chat's address is kept so the
    page can show it again (it is meant to be shared); a webhook's is shown once."""
    from ..agent import dhara_tools as D
    from ..config import get_settings
    from . import editor as E
    kind = wf.get("trigger_kind")
    if kind not in TOKEN_KINDS:
        raise TriggerError("This route is not started from an address")
    tok = D.webhook_token_reveal(tenant, wf["id"])
    path = {"webhook": f"/api/dhara/hook/{tok}", "form": f"/route-form/{tok}", "chat": f"/route-chat/{tok}"}[kind]
    if kind in PUBLIC_KINDS:
        E.set_public(tenant, wf["id"], path)
    base = (get_settings().public_base_url or "").rstrip("/")
    return {"url": (base + path) if base else path, "path": path,
            "note": ("Shown only now. The old address has stopped working." if kind == "webhook" else
                     "Share this address. Making a new one stops the old one.")}


def public_address(tenant: str, wf: dict) -> str:
    from ..agent import dhara_tools as D
    from ..config import get_settings
    from . import editor as E
    if wf.get("trigger_kind") not in PUBLIC_KINDS:
        return ""
    path = E.public_of(tenant, wf["id"])
    if not path:
        return ""
    tok = path.rsplit("/", 1)[-1]
    if hashlib.sha256(tok.encode()).hexdigest() != (wf.get("token_hash") or ""):
        return ""
    base = (get_settings().public_base_url or "").rstrip("/")
    _ = D
    return (base + path) if base else path


def _limited(wf_id: str) -> bool:
    now_ = time.time()
    hits = [t for t in _PUB_HITS.get(wf_id, []) if now_ - t < 60]
    if len(hits) >= PUBLIC_PER_MIN:
        _PUB_HITS[wf_id] = hits
        return True
    hits.append(now_)
    _PUB_HITS[wf_id] = hits
    return False


_CSS = """
:root{--ink:#1C1917;--mut:#57534E;--line:#E7E5E4;--bg:#FFFFFF;--soft:#F5F5F4;--acc:#5B45E0;--bad:#991B1B}
@media (prefers-color-scheme: dark){:root{--ink:#E6E5E1;--mut:#B2B0A9;--line:#2E2E2B;--bg:#141413;--soft:#262624;--acc:#9C88FF;--bad:#FCA5A5}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:640px;margin:0 auto;padding:40px 16px 64px}h1{font-size:28px;line-height:1.25;font-weight:600;margin:0 0 8px}
p.lead{color:var(--mut);margin:0 0 24px;white-space:pre-line}form{display:flex;flex-direction:column;gap:16px}
label{display:flex;flex-direction:column;gap:6px;font-size:14px;font-weight:500}label.chk{flex-direction:row;align-items:center;gap:10px}
input,textarea,select{font:inherit;color:inherit;background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:10px 12px;min-height:44px}
textarea{min-height:110px;resize:vertical}input[type=checkbox]{min-height:0;width:20px;height:20px}
input:focus,textarea:focus,select:focus{outline:2px solid var(--acc);outline-offset:1px}
button{font:inherit;font-weight:600;color:#fff;background:var(--ink);border:0;border-radius:999px;padding:12px 22px;min-height:44px;cursor:pointer;align-self:flex-start}
@media (prefers-color-scheme: dark){button{color:var(--bg)}}
.req{color:var(--mut);font-weight:400}.err{color:var(--bad);font-size:14px}.hp{position:absolute;left:-9999px}
.done{border:1px solid var(--line);background:var(--soft);border-radius:14px;padding:20px;white-space:pre-line}
.foot{margin-top:32px;font-size:12px;color:var(--mut)}
"""


def page_headers() -> dict[str, str]:
    return {"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; script-src 'self'; connect-src 'self'; "
            "img-src 'self' data:; form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
            "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "Cache-Control": "no-store",
            "X-Frame-Options": "DENY", "X-Robots-Tag": "noindex"}


def _shell(title: str, body: str, script: str = "") -> str:
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, '
            f'initial-scale=1"><title>{html.escape(title)}</title><style>{_CSS}</style></head><body><main>{body}'
            f'<div class="foot">Made with Hoola Route</div></main>{script}</body></html>')


def form_html(spec: dict, values: dict | None = None, errors: list[str] | None = None, done: str = "") -> str:
    e = html.escape
    title = spec.get("title") or "A form"
    if done:
        return _shell(title, f'<h1>{e(title)}</h1><div class="done" role="status">{e(done)}</div>')
    values = values or {}
    parts = [f'<h1>{e(title)}</h1>']
    if spec.get("intro"):
        parts.append(f'<p class="lead">{e(spec["intro"])}</p>')
    if errors:
        parts.append('<div class="err" role="alert">' + "<br>".join(e(x) for x in errors) + "</div>")
    parts.append('<form method="post" novalidate>')
    parts.append('<label class="hp" aria-hidden="true">Leave this empty <input name="_hp" tabindex="-1" autocomplete="off"></label>')
    for f in spec.get("fields") or []:
        nm, typ = f["name"], f.get("type") or "text"
        v = str(values.get(nm) or "")
        req = " required" if f.get("required") else ""
        star = ' <span class="req">(needed)</span>' if f.get("required") else ""
        ph = f' placeholder="{e(f["placeholder"])}"' if f.get("placeholder") else ""
        if typ == "textarea":
            ctl = f'<textarea name="{e(nm)}"{req}{ph}>{e(v)}</textarea>'
        elif typ == "select":
            ctl = (f'<select name="{e(nm)}"{req}><option value="">Choose…</option>' +
                   "".join(f'<option{" selected" if v == o else ""}>{e(o)}</option>' for o in f.get("options") or []) + "</select>")
        elif typ == "checkbox":
            parts.append(f'<label class="chk"><input type="checkbox" name="{e(nm)}" value="yes"{" checked" if v else ""}{req}>'
                         f'{e(f["label"])}{star}</label>')
            continue
        else:
            it = {"phone": "tel"}.get(typ, typ)
            ctl = f'<input type="{e(it)}" name="{e(nm)}" value="{e(v)}"{req}{ph}>'
        parts.append(f'<label>{e(f["label"])}{star}{ctl}</label>')
    parts.append(f'<button type="submit">{e(spec.get("button") or "Send")}</button></form>')
    return _shell(title, "".join(parts))


def form_check(spec: dict, data: dict) -> tuple[dict, list[str]]:
    vals: dict[str, Any] = {}
    errs: list[str] = []
    for f in spec.get("fields") or []:
        nm, typ = f["name"], f.get("type") or "text"
        raw = str(data.get(nm) or "").strip()[:5000]
        if typ == "checkbox":
            vals[nm] = bool(raw)
            if f.get("required") and not raw:
                errs.append(f"Tick “{f['label']}”.")
            continue
        if not raw:
            if f.get("required"):
                errs.append(f"Fill in “{f['label']}”.")
            vals[nm] = ""
            continue
        if typ == "email" and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", raw):
            errs.append(f"“{f['label']}” is not an email address.")
        elif typ == "number":
            try:
                n = float(raw)
                raw = int(n) if n.is_integer() else n
            except ValueError:
                errs.append(f"“{f['label']}” must be a number.")
        elif typ == "date" and not re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
            errs.append(f"“{f['label']}” must be a date.")
        elif typ == "select" and raw not in (f.get("options") or []):
            errs.append(f"Choose one of the options for “{f['label']}”.")
        elif typ == "phone" and not re.match(r"^[+()\d\s.-]{5,25}$", raw):
            errs.append(f"“{f['label']}” is not a phone number.")
        vals[nm] = raw
    return vals, errs


async def form_get(token: str) -> tuple[int, str]:
    t, wf = await asyncio.to_thread(_find, token, ("form",))
    if wf is None or not wf.get("enabled"):
        return 404, _shell("Not found", "<h1>This form is not open</h1><p class='lead'>The link may have changed or the form is off.</p>")
    return 200, form_html(wf.get("trigger_spec") or {})


async def form_post(token: str, data: dict) -> tuple[int, str]:
    from ..agent import dhara_tools as D
    t, wf = await asyncio.to_thread(_find, token, ("form",))
    if wf is None or not wf.get("enabled"):
        return 404, _shell("Not found", "<h1>This form is not open</h1>")
    spec = wf.get("trigger_spec") or {}
    if str(data.get("_hp") or ""):
        return 200, form_html(spec, done=spec.get("thanks") or "Thank you.")        # a robot: say thanks, start nothing
    vals, errs = form_check(spec, data)
    if errs:
        return 400, form_html(spec, data, errs)
    if _limited(wf["id"]) or await asyncio.to_thread(D._over_daily_cap, t, wf):
        return 429, form_html(spec, data, ["Too many answers just now - please try again in a minute."])
    res = await D.start_and_wait(t, wf, {"form": vals, "sent_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    ans = res.get("answer")
    text = spec.get("thanks") or "Thank you."
    if res.get("answered") and ans not in (None, ""):
        text = ans if isinstance(ans, str) else str((ans or {}).get("message") or (ans or {}).get("text") or text) \
            if isinstance(ans, dict) else str(ans)
    return 200, form_html(spec, done=str(text)[:3000])


def chat_html(spec: dict) -> str:
    e = html.escape
    title = spec.get("title") or "Chat"
    body = (f'<h1>{e(title)}</h1><div id="rcLog" class="rclog" aria-live="polite"><div class="rcm bot">{e(spec.get("greeting") or "")}</div></div>'
            f'<form id="rcForm" class="rcform"><label class="hp" aria-hidden="true">x<input id="rcHp" tabindex="-1"></label>'
            f'<label for="rcIn" class="sr">Message</label><textarea id="rcIn" rows="2" placeholder="{e(spec.get("placeholder") or "")}" required></textarea>'
            f'<button type="submit">Send</button></form>')
    style = ("<style>.rclog{display:flex;flex-direction:column;gap:10px;margin:16px 0}.rcm{max-width:85%;padding:10px 14px;border-radius:14px;"
             "white-space:pre-wrap;word-wrap:break-word}.rcm.bot{background:var(--soft);align-self:flex-start}.rcm.me{background:var(--ink);"
             "color:var(--bg);align-self:flex-end}.rcm.wait{color:var(--mut)}.rcform{flex-direction:row;align-items:flex-end;gap:8px}"
             ".rcform textarea{flex:1;min-height:48px}.sr{position:absolute;left:-9999px}.rcform button{align-self:auto}</style>")
    return _shell(title, style + body, '<script src="/static/console/routechat.js"></script>')


async def chat_get(token: str) -> tuple[int, str]:
    t, wf = await asyncio.to_thread(_find, token, ("chat",))
    if wf is None or not wf.get("enabled"):
        return 404, _shell("Not found", "<h1>This chat is not open</h1><p class='lead'>The link may have changed or the chat is off.</p>")
    return 200, chat_html(wf.get("trigger_spec") or {})


def _history(tenant: str, wf_id: str, session: str) -> list[dict]:
    con = _con(tenant)
    try:
        rows = con.execute("SELECT role, text FROM route_chat WHERE workflow_id = ? AND session = ? ORDER BY at DESC LIMIT 20",
                           (wf_id, session)).fetchall()
    finally:
        con.close()
    return [{"role": r["role"], "text": r["text"]} for r in reversed(rows)]


def _remember(tenant: str, wf_id: str, session: str, role: str, text: str) -> None:
    con = _con(tenant)
    try:
        con.execute("INSERT INTO route_chat (workflow_id, session, role, text, at) VALUES (?, ?, ?, ?, ?)",
                    (wf_id, session, role, text[:4000], time.time()))
        con.execute("DELETE FROM route_chat WHERE workflow_id = ? AND session = ? AND rowid NOT IN (SELECT rowid FROM "
                    "route_chat WHERE workflow_id = ? AND session = ? ORDER BY at DESC LIMIT ?)",
                    (wf_id, session, wf_id, session, CHAT_KEEP))
        con.execute("DELETE FROM route_chat WHERE at < ?", (time.time() - CHAT_DAYS * 86400,))
        con.commit()
    finally:
        con.close()


async def chat_send(token: str, session: str, text: str) -> dict:
    from ..agent import dhara_tools as D
    t, wf = await asyncio.to_thread(_find, token, ("chat",))
    if wf is None or not wf.get("enabled"):
        return {"ok": False, "status": 404, "error": "This chat is not open"}
    session = re.sub(r"[^A-Za-z0-9_-]", "", str(session or ""))[:64]
    text = str(text or "").strip()[:4000]
    if not session or not text:
        return {"ok": False, "status": 400, "error": "Write a message"}
    if _limited(wf["id"]) or await asyncio.to_thread(D._over_daily_cap, t, wf):
        return {"ok": False, "status": 429, "error": "Too many messages just now - please try again in a minute."}
    hist = await asyncio.to_thread(_history, t, wf["id"], session)
    await asyncio.to_thread(_remember, t, wf["id"], session, "user", text)
    res = await D.start_and_wait(t, wf, {"message": text, "session": session, "history": hist})
    ans = res.get("answer")
    if res.get("answered") and ans not in (None, ""):
        reply = ans if isinstance(ans, str) else str((ans or {}).get("reply") or (ans or {}).get("message") or
                                                     (ans or {}).get("text") or json.dumps(ans, ensure_ascii=False)) \
            if isinstance(ans, dict) else str(ans)
    else:
        reply = "Got it, thank you." if res.get("run_status") == "done" else "Thanks - I am on it."
    reply = reply[:4000]
    await asyncio.to_thread(_remember, t, wf["id"], session, "bot", reply)
    return {"ok": True, "status": 200, "reply": reply}


# ---------------------------------------------------------------- routes as tools for AI apps (MCP)
MCP_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")


def mcp_key(tenant: str) -> dict:
    """Her MCP address (one per account): a new key every time, shown once; the old one stops working."""
    from ..config import get_settings
    tok = "rmcp_" + secrets.token_urlsafe(24)
    con = _con(tenant)
    try:
        con.execute("INSERT OR REPLACE INTO route_keys (kind, token_hash, created_at) VALUES ('mcp', ?, ?)",
                    (hashlib.sha256(tok.encode()).hexdigest(), time.time()))
        con.commit()
    finally:
        con.close()
    base = (get_settings().public_base_url or "").rstrip("/")
    path = f"/mcp/route/{tok}"
    return {"url": (base + path) if base else path, "path": path,
            "note": "Shown only now. Add it to an AI app as an MCP server (Streamable HTTP). Making a new one stops the old one."}


def mcp_state(tenant: str) -> dict:
    con = _con(tenant)
    try:
        r = con.execute("SELECT created_at FROM route_keys WHERE kind = 'mcp'").fetchone()
    finally:
        con.close()
    return {"made": r is not None, "at": r["created_at"] if r is not None else None}


def _mcp_tenant(token: str) -> str:
    th = hashlib.sha256(str(token or "").encode()).hexdigest()
    root = Path("data") / "dhara"
    import hmac as _h
    for p in sorted(root.glob("*/dhara.db")) if root.is_dir() else []:
        t = p.parent.name
        con = _con(t)
        try:
            r = con.execute("SELECT token_hash FROM route_keys WHERE kind = 'mcp'").fetchone()
        finally:
            con.close()
        if r is not None and _h.compare_digest(str(r["token_hash"] or ""), th):
            return t
    return ""


def _tools_of(tenant: str) -> list[dict]:
    from ..agent import dhara_tools as D
    con = D._con(tenant)
    try:
        rows = con.execute("SELECT * FROM workflows WHERE enabled = 1 AND trigger_kind = 'tool' ORDER BY name").fetchall()
    finally:
        con.close()
    return [D._wf_row(r) for r in rows]


def _schema(spec: dict) -> dict:
    props, req = {}, []
    for x in spec.get("inputs") or []:
        props[x["name"]] = {"type": x.get("type") or "string", **({"description": x["description"]} if x.get("description") else {})}
        if x.get("required"):
            req.append(x["name"])
    return {"type": "object", "properties": props, **({"required": req} if req else {})}


async def mcp_handle(token: str, msg: Any) -> tuple[int, Any]:
    """JSON-RPC 2.0 over HTTP (MCP Streamable HTTP, plain JSON answers): initialize, ping, tools/list, tools/call."""
    from ..agent import dhara_tools as D
    tenant = await asyncio.to_thread(_mcp_tenant, token)
    if not tenant:
        return 401, {"jsonrpc": "2.0", "id": None, "error": {"code": -32001, "message": "This address is not valid"}}
    if isinstance(msg, list):
        outs = []
        for m in msg[:20]:
            code, o = await mcp_handle(token, m)
            if o is not None:
                outs.append(o)
        return 200, outs or None
    if not isinstance(msg, dict):
        return 400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid request"}}
    mid, method, params = msg.get("id"), str(msg.get("method") or ""), msg.get("params") or {}
    ok = lambda res: (200, {"jsonrpc": "2.0", "id": mid, "result": res})  # noqa: E731
    bad = lambda code, m: (200, {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": m}})  # noqa: E731
    if mid is None and method.startswith("notifications/"):
        return 202, None
    if method == "initialize":
        want = str(params.get("protocolVersion") or "")
        return ok({"protocolVersion": want if want in MCP_VERSIONS else MCP_VERSIONS[0],
                   "capabilities": {"tools": {"listChanged": False}},
                   "serverInfo": {"name": "hoola-route", "version": "1"},
                   "instructions": "Each tool is one of her Hoola routes. Calling one runs that route and returns its answer."})
    if method == "ping":
        return ok({})
    if method == "tools/list":
        wfs = await asyncio.to_thread(_tools_of, tenant)
        return ok({"tools": [{"name": w["name"], "description": (w.get("trigger_spec") or {}).get("description") or w.get("description") or "",
                              "inputSchema": _schema(w.get("trigger_spec") or {})} for w in wfs]})
    if method == "tools/call":
        name = str(params.get("name") or "")
        args = params.get("arguments") or {}
        wfs = {w["name"]: w for w in await asyncio.to_thread(_tools_of, tenant)}
        wf = wfs.get(name)
        if wf is None:
            return bad(-32602, f"Unknown tool: {name}")
        if not isinstance(args, dict):
            return bad(-32602, "arguments must be an object")
        miss = [x["name"] for x in (wf.get("trigger_spec") or {}).get("inputs") or [] if x.get("required") and args.get(x["name"]) in (None, "")]
        if miss:
            return ok({"content": [{"type": "text", "text": "Missing: " + ", ".join(miss)}], "isError": True})
        if await asyncio.to_thread(D._over_daily_cap, tenant, wf):
            return ok({"content": [{"type": "text", "text": "This route reached its runs-per-day limit."}], "isError": True})
        res = await D.start_and_wait(tenant, wf, {k: v for k, v in args.items() if isinstance(k, str) and _NAME.match(k)})
        st = res.get("run_status")
        if res.get("answered"):
            body = res.get("answer")
            text = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False, default=str)
            return ok({"content": [{"type": "text", "text": text[:50_000]}], "isError": int(res.get("status") or 200) >= 400})
        if st == "done":
            r = await asyncio.to_thread(D.get_run, tenant, res["run_id"])
            c = (r or {}).get("context") or {}
            outs = [x.get("output") for x in (c.get("steps") or {}).values() if isinstance(x, dict)]
            text = json.dumps({"result": outs[-1] if outs else None}, ensure_ascii=False, default=str)
            return ok({"content": [{"type": "text", "text": text[:50_000]}]})
        if st in ("failed", "stopped", "incomplete"):
            r = await asyncio.to_thread(D.get_run, tenant, res["run_id"])
            return ok({"content": [{"type": "text", "text": "The route did not finish: " + str((r or {}).get("error") or st)[:500]}],
                       "isError": True})
        return ok({"content": [{"type": "text", "text": "The route started and is still going (it waits for a step, "
                                                        "like an approval). Its owner will see the result in Hoola."}]})
    return bad(-32601, f"Unknown method: {method}")
