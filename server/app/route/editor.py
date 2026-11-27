"""v0.999.232 THE ROUTE EDITOR (R1 of the Hoola Route plan; owner: design canvas -> "GO BUILD").

What the editor page needs beside the engine (agent/dhara_tools.py), kept small and in the same per-tenant dhara.db:

- route_meta   one row per route: the canvas layout (positions she dragged nodes to, her sticky notes) and the id of
               the route's own Ask Hoola chat. Layout never changes what a route DOES, so it saves without checks.
- save_graph   the steps she edited on the canvas, saved through the engine's own hard validation. A value the page
               only ever saw masked (an ID number) is put back from the stored route, so an edit never overwrites it.
               A save made while someone else changed the route (Hoola in the chat, another tab) is refused with 409.
- new_route    a route made from the page starts OFF with one placeholder step; nothing runs until she switches it on.
- catalog      the steps she can add: the step kinds, and Hoola's tools found by her words (with their argument fields).
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

_ID = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
NOTE_COLORS = ("yellow", "blue", "green", "pink", "grey")
_POS_MAX = 400
_NOTES_MAX = 30
_NOTE_CHARS = 2000
_DECO = ("app",)                # keys the page's graph carries only for drawing


def _con(tenant: str):
    from ..agent import dhara_tools as D
    con = D._con(tenant)
    con.execute("CREATE TABLE IF NOT EXISTS route_meta (workflow_id TEXT PRIMARY KEY, layout TEXT DEFAULT '{}', "
                "chat TEXT DEFAULT '', updated_at REAL)")
    try:                                  # v0.999.240 the form / chat page's address, kept to show again
        con.execute("ALTER TABLE route_meta ADD COLUMN pub TEXT DEFAULT ''")
    except Exception:   # noqa: BLE001  (already there)
        pass
    return con


def meta(tenant: str, wf_id: str) -> dict[str, Any]:
    con = _con(tenant)
    try:
        r = con.execute("SELECT layout, chat FROM route_meta WHERE workflow_id = ?", (wf_id,)).fetchone()
    finally:
        con.close()
    lay: dict[str, Any] = {}
    if r is not None:
        try:
            lay = json.loads(r["layout"] or "{}") or {}
        except Exception:   # noqa: BLE001
            lay = {}
    return {"pos": lay.get("pos") or {}, "notes": lay.get("notes") or [], "chat": (r["chat"] if r is not None else "") or ""}


def _upsert(tenant: str, wf_id: str, **fields) -> None:
    con = _con(tenant)
    try:
        con.execute("INSERT OR IGNORE INTO route_meta (workflow_id, layout, chat, updated_at) VALUES (?, '{}', '', ?)",
                    (wf_id, time.time()))
        for k, v in fields.items():
            con.execute(f"UPDATE route_meta SET {k} = ?, updated_at = ? WHERE workflow_id = ?", (v, time.time(), wf_id))
        con.commit()
    finally:
        con.close()


def chat_of(tenant: str, wf_id: str) -> str:
    return meta(tenant, wf_id)["chat"]


def set_chat(tenant: str, wf_id: str, conv: str) -> None:
    _upsert(tenant, wf_id, chat=str(conv or "")[:64])


def set_public(tenant: str, wf_id: str, path: str) -> None:
    _upsert(tenant, wf_id, pub=str(path or "")[:200])


def public_of(tenant: str, wf_id: str) -> str:
    con = _con(tenant)
    try:
        r = con.execute("SELECT pub FROM route_meta WHERE workflow_id = ?", (wf_id,)).fetchone()
        return (r["pub"] if r is not None else "") or ""
    finally:
        con.close()


def route_of_chat(tenant: str, conv: str) -> str:
    con = _con(tenant)
    try:
        r = con.execute("SELECT workflow_id FROM route_meta WHERE chat = ? AND chat != ''", (conv,)).fetchone()
        return r["workflow_id"] if r is not None else ""
    finally:
        con.close()


def forget(tenant: str, wf_id: str) -> None:
    con = _con(tenant)
    try:
        con.execute("DELETE FROM route_meta WHERE workflow_id = ?", (wf_id,))
        con.commit()
    finally:
        con.close()
    try:
        from . import triggers as TR
        TR.forget(tenant, wf_id)
    except Exception:   # noqa: BLE001
        pass


def _num(v: Any) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("A position must be a number")
    if x != x or abs(x) > 100000:
        raise ValueError("A position is out of range")
    return round(x, 1)


def clean_layout(body: dict) -> dict[str, Any]:
    """Positions {step_id: [x, y]} and notes [{id, x, y, w, text, color}], checked and capped."""
    pos_in = (body or {}).get("pos") or {}
    notes_in = (body or {}).get("notes") or []
    if not isinstance(pos_in, dict) or not isinstance(notes_in, list):
        raise ValueError("pos must be an object and notes a list")
    if len(pos_in) > _POS_MAX:
        raise ValueError(f"At most {_POS_MAX} positions")
    if len(notes_in) > _NOTES_MAX:
        raise ValueError(f"At most {_NOTES_MAX} notes on one route")
    pos = {}
    for k, v in pos_in.items():
        if not _ID.match(str(k)) or not isinstance(v, (list, tuple)) or len(v) != 2:
            raise ValueError("Each position is step_id: [x, y]")
        pos[str(k)] = [_num(v[0]), _num(v[1])]
    notes = []
    for n in notes_in:
        if not isinstance(n, dict) or not _ID.match(str(n.get("id") or "")):
            raise ValueError("Each note needs an id")
        text = str(n.get("text") or "")
        if len(text) > _NOTE_CHARS:
            raise ValueError(f"A note can hold {_NOTE_CHARS} characters")
        w = max(160.0, min(_num(n.get("w") or 220), 600.0))
        notes.append({"id": str(n["id"])[:40], "x": _num(n.get("x")), "y": _num(n.get("y")), "w": w, "text": text,
                      "color": n.get("color") if n.get("color") in NOTE_COLORS else "yellow"})
    return {"pos": pos, "notes": notes}


def save_layout(tenant: str, wf_id: str, body: dict) -> dict[str, Any]:
    lay = clean_layout(body)
    _upsert(tenant, wf_id, layout=json.dumps(lay))
    return lay


# ---------------------------------------------------------------- the graph
def strip_deco(v: Any) -> Any:
    if isinstance(v, dict):
        return {k: strip_deco(x) for k, x in v.items() if k not in _DECO}
    if isinstance(v, list):
        return [strip_deco(x) for x in v]
    return v


def _index(steps: list, out: dict | None = None) -> dict[str, dict]:
    out = {} if out is None else out
    for s in steps or []:
        if not isinstance(s, dict):
            continue
        if s.get("id"):
            out[str(s["id"])] = s
        for k in ("then", "else", "body", "fallback"):
            if k != "body" or s.get("type") == "loop":      # a web request's body is data, not steps
                _index(s.get(k) or [], out)
        for rt in s.get("routes") or []:
            if isinstance(rt, dict):
                _index(rt.get("steps") or [], out)
    return out


def _restore(new: Any, old: Any) -> Any:
    """Where the page sent back exactly the masked text of a stored value, keep the stored value."""
    from ..agent import dhara_tools as D
    if isinstance(new, str) and isinstance(old, str):
        return old if new != old and new == D._masked(old) else new
    if isinstance(new, dict) and isinstance(old, dict):
        return {k: (_restore(v, old[k]) if k in old else v) for k, v in new.items()}
    if isinstance(new, list) and isinstance(old, list) and len(new) == len(old):
        return [_restore(a, b) for a, b in zip(new, old)]
    return new


def unmask(new_steps: list, old_steps: list) -> list:
    old = _index(old_steps)

    def walk(lst):
        res = []
        for s in lst or []:
            if not isinstance(s, dict):
                res.append(s)
                continue
            o = old.get(str(s.get("id") or ""))
            d = dict(s)
            if o is not None:
                for k, v in s.items():
                    if k in ("then", "else", "fallback", "routes") or (k == "body" and s.get("type") == "loop"):
                        continue
                    if k in o:
                        d[k] = _restore(v, o[k])
            for k in ("then", "else", "body", "fallback"):
                if isinstance(s.get(k), list) and (k != "body" or s.get("type") == "loop"):
                    d[k] = walk(s[k])
            if isinstance(s.get("routes"), list):
                d["routes"] = [{**rt, "steps": walk(rt.get("steps"))} if isinstance(rt, dict) else rt for rt in s["routes"]]
            res.append(d)
        return res
    return walk(new_steps)


def save_graph(tenant: str, wf: dict, body: dict) -> dict:
    """Her canvas edits, through the engine's own validation. Raises ToolError (400) or ValueError('conflict')."""
    from ..agent import dhara_tools as D
    from ..agent.tools import ToolError
    base = (body or {}).get("base")
    if base not in (None, "") and abs(float(base) - float(wf.get("updated_at") or 0)) > 1e-3:
        raise ValueError("conflict")
    steps = body.get("steps")
    if not isinstance(steps, list):
        raise ToolError("steps must be a list")
    steps = unmask(strip_deco(steps), wf.get("steps") or [])
    kind = str(body.get("trigger") or wf.get("trigger_kind") or "manual").lower()
    spec = body.get("trigger_spec") if body.get("trigger_spec") is not None else (wf.get("trigger_spec") or {})
    from . import triggers as TR                # v0.999.240 ROUTE R5: every trigger kind, checked by the engine's rules
    spec = TR.validate(kind, dict(spec or {}) if isinstance(spec, dict) else {}, wf.get("settings") or {})
    desc = str(body["description"]) if body.get("description") is not None else str(wf.get("description") or "")
    norm = D.validate_steps(steps)
    new, _ = D.save_workflow(tenant, wf["name"], desc[:500], kind, spec, norm, settings=None)
    con = D._con(tenant)
    try:
        con.execute("UPDATE workflows SET next_due_at = ? WHERE id = ?",
                    (D.next_due(new) if kind in ("schedule", "event") else None, new["id"]))
        con.commit()
    finally:
        con.close()
    return D.get_workflow(tenant, wf_id=new["id"])


def slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", str(title or "").lower()).strip("_")
    s = re.sub(r"_+", "_", s)[:60].strip("_")
    if not s or not s[0].isalpha():
        s = "route_" + s if s else "new_route"
    return s


PLACEHOLDER = [{"id": "tell_me", "type": "notify", "label": "Tell me it ran", "text": "This route ran."}]


def new_route(tenant: str, title: str, folder: str = "") -> dict:
    from ..agent import dhara_tools as D
    base = slug(title)
    name, n = base, 2
    while D.get_workflow(tenant, name=name) is not None:
        name = f"{base[:56]}_{n}"
        n += 1
    st = D.validate_settings({"folder": folder}) if folder else None
    wf, _ = D.save_workflow(tenant, name, "", "manual", {}, json.loads(json.dumps(PLACEHOLDER)), settings=st)
    D.set_enabled(tenant, wf["id"], False)      # nothing runs until she switches it on
    return D.get_workflow(tenant, wf_id=wf["id"])


# ---------------------------------------------------------------- the catalog
KINDS: list[dict[str, Any]] = [
    # v0.999.243 ROUTE R6: the AI steps (engine type "ai", told apart by op)
    {"key": "ai_agent", "type": "ai", "group": "AI", "title": "AI agent", "sub": "Does a task with the Hoola tools you give it",
     "make": {"op": "agent", "prompt": "", "tools": [], "max_steps": 5, "memory": "none"}},
    {"key": "ai_write", "type": "ai", "group": "AI", "title": "Ask AI", "sub": "Write, rewrite, translate, answer - from a prompt",
     "make": {"op": "write", "prompt": ""}},
    {"key": "ai_summarise", "type": "ai", "group": "AI", "title": "Summarise", "sub": "Short, a paragraph or points, in any language",
     "make": {"op": "summarise", "text": "", "length": "short"}},
    {"key": "ai_classify", "type": "ai", "group": "AI", "title": "Sort into categories", "sub": "Put a message into one of your categories",
     "make": {"op": "classify", "text": "", "categories": "question, complaint, order, other"}},
    {"key": "ai_extract", "type": "ai", "group": "AI", "title": "Pull out fields", "sub": "Names, amounts, dates from any text",
     "make": {"op": "extract", "text": "", "fields": {"name": "The person's name", "amount": "The total"}}},
    {"key": "ai_sentiment", "type": "ai", "group": "AI", "title": "How it feels", "sub": "Positive, neutral, negative, with a score",
     "make": {"op": "sentiment", "text": ""}},
    {"key": "ai_answer", "type": "ai", "group": "AI", "title": "Answer from my files", "sub": "Only from the files, text or Knowledge you give",
     "make": {"op": "answer", "question": "", "knowledge": True}},
    {"key": "ai_switch", "type": "router", "group": "AI", "title": "AI picks the way", "sub": "A switch where the AI reads a text and picks a way",
     "make": {"ai": {"text": ""}, "routes": [{"label": "Sales", "steps": []}, {"label": "Support", "steps": []}], "fallback": []}},
    {"type": "approval", "group": "Human in the loop", "title": "Ask me first", "sub": "Waits for your tap before going on",
     "make": {"question": "Go ahead?"}},
    {"type": "notify", "group": "Human in the loop", "title": "Tell me", "sub": "A message to you in Hoola",
     "make": {"text": "Done."}},
    {"type": "condition", "group": "Flow", "title": "If / else", "sub": "Two ways, by a test",
     "make": {"filter": {"left": "", "op": "exists"}, "then": [], "else": []}},
    {"type": "router", "group": "Flow", "title": "Switch", "sub": "Up to 8 named ways, each with its own test",
     "make": {"routes": [{"label": "Way 1", "filter": {"left": "", "op": "exists"}, "steps": []}]}},
    {"type": "filter", "group": "Flow", "title": "Filter", "sub": "Stop here unless it passes",
     "make": {"filter": {"left": "", "op": "exists"}}},
    {"type": "loop", "group": "Flow", "title": "Repeat for each", "sub": "Run steps for every item of a list",
     "make": {"items": "", "body": []}},
    {"type": "wait", "group": "Flow", "title": "Wait", "sub": "Minutes, hours or days (up to 30), or until a date and time",
     "make": {"amount": 10, "unit": "minutes"}},
    # v0.999.239 ROUTE R4: the flow steps
    {"key": "wait_call", "type": "wait", "group": "Flow", "title": "Wait for a reply", "sub": "Until someone calls the run's link (a form, an email button)",
     "make": {"for": "call", "timeout_s": 86400, "on_timeout": "continue"}},
    {"type": "subroute", "group": "Flow", "title": "Run another route", "sub": "Use one of your routes as a step, with its result",
     "make": {"route": "", "vars": {}}},
    {"type": "stop", "group": "Flow", "title": "Stop the run", "sub": "End here, as an error or as done",
     "make": {"as": "error", "message": ""}},
    {"type": "respond", "group": "Core", "title": "Answer the caller", "sub": "What an app that called the webhook gets back",
     "make": {"status": 200, "body": {"ok": True}}},
    {"type": "set", "group": "Data", "title": "Set a value", "sub": "Keep a value for later steps",
     "make": {"name": "value", "value": ""}},
    # v0.999.237 ROUTE R3: the data steps (one engine type "data", told apart by op)
    {"key": "fields", "type": "data", "group": "Data", "title": "Set several fields", "sub": "Make an object of values at once",
     "make": {"op": "fields", "values": {"name": "", "total": ""}}},
    {"key": "sort", "type": "data", "group": "Data", "title": "Sort", "sub": "Put a list in order by a field",
     "make": {"op": "sort", "items": "", "by": "", "order": "asc"}},
    {"key": "limit", "type": "data", "group": "Data", "title": "Limit", "sub": "Keep the first or last few of a list",
     "make": {"op": "limit", "items": "", "count": 10, "keep": "first"}},
    {"key": "dedupe", "type": "data", "group": "Data", "title": "Remove duplicates", "sub": "Keep one of each, by a field or whole",
     "make": {"op": "dedupe", "items": "", "by": ""}},
    {"key": "aggregate", "type": "data", "group": "Data", "title": "Summarise", "sub": "Count, sum, average, min, max, join a list",
     "make": {"op": "aggregate", "items": "", "field": "", "how": "sum"}},
    {"key": "split", "type": "data", "group": "Data", "title": "Split out a list", "sub": "Turn a list inside each item into one list",
     "make": {"op": "split", "items": "", "field": ""}},
    {"key": "compare", "type": "data", "group": "Data", "title": "Compare two lists", "sub": "What was added, removed, changed",
     "make": {"op": "compare", "a": "", "b": "", "key": "id"}},
    {"key": "merge", "type": "data", "group": "Data", "title": "Merge two lists", "sub": "Join by a field, one after the other, side by side",
     "make": {"op": "merge", "mode": "by_key", "a": "", "b": "", "key": "id", "join": "inner"}},
    {"key": "keep_fields", "type": "data", "group": "Data", "title": "Keep or drop fields", "sub": "Only the fields you name",
     "make": {"op": "keep_fields", "items": "", "fields": "", "mode": "keep"}},
    {"key": "rename", "type": "data", "group": "Data", "title": "Rename fields", "sub": "Give fields new names",
     "make": {"op": "rename", "items": "", "map": {"old_name": "new_name"}}},
    {"key": "date", "type": "data", "group": "Data", "title": "Date and time", "sub": "Format, add days, time between, time zones",
     "make": {"op": "date", "action": "format", "value": "", "format": "%d %b %Y"}},
    {"key": "text", "type": "data", "group": "Data", "title": "Text and formats", "sub": "HTML, XML, CSV, JSON, Base64, web addresses",
     "make": {"op": "text", "action": "html_text", "value": ""}},
    {"key": "file", "type": "data", "group": "Data", "title": "Make or read a file", "sub": "CSV, Excel, PDF - to send on or read",
     "make": {"op": "file", "action": "make_xlsx", "items": "", "name": "report"}},
    {"key": "crypto", "type": "data", "group": "Data", "title": "Hash and IDs", "sub": "SHA-256, HMAC, a random id",
     "make": {"op": "crypto", "action": "sha256", "value": ""}},
    {"type": "code", "group": "Data", "title": "Code", "sub": "Python in a locked sandbox",
     "make": {"code": "result = {'ok': True}\nprint(result)"}},
    {"type": "http", "group": "Core", "title": "Web request", "sub": "Call any address: GET, POST, PUT, PATCH, DELETE ...",
     "make": {"action": "request", "method": "GET", "url": "https://"}},
    # v0.999.254 MAKE PARITY: the rest of Make's built-in apps
    {"key": "http_download", "type": "http", "group": "Core", "title": "Download a file", "sub": "Keep a file from a web address for the next steps",
     "make": {"action": "download", "method": "GET", "url": "https://"}},
    {"key": "http_resolve", "type": "http", "group": "Core", "title": "Resolve a web address", "sub": "Follow its redirects to where it ends",
     "make": {"action": "resolve", "url": "https://"}},
    {"key": "store_add", "type": "store", "group": "Data store", "title": "Add or replace a record", "sub": "Keep a record in one of your data stores",
     "make": {"op": "add", "store": "", "key": "", "data": {}}},
    {"key": "store_update", "type": "store", "group": "Data store", "title": "Update a record", "sub": "Change some fields of a record",
     "make": {"op": "update", "store": "", "key": "", "data": {}}},
    {"key": "store_get", "type": "store", "group": "Data store", "title": "Get a record", "sub": "Read one record by its key",
     "make": {"op": "get", "store": "", "key": ""}},
    {"key": "store_exists", "type": "store", "group": "Data store", "title": "Is the record there?", "sub": "Yes or no, by its key",
     "make": {"op": "exists", "store": "", "key": ""}},
    {"key": "store_search", "type": "store", "group": "Data store", "title": "Search records", "sub": "Records whose fields pass a test, sorted",
     "make": {"op": "search", "store": "", "filter": {"field": "", "op": "exists"}, "limit": 100}},
    {"key": "store_count", "type": "store", "group": "Data store", "title": "Count records", "sub": "How many records (that pass a test)",
     "make": {"op": "count", "store": ""}},
    {"key": "store_delete", "type": "store", "group": "Data store", "title": "Delete a record", "sub": "Remove one record by its key",
     "make": {"op": "delete", "store": "", "key": ""}},
    {"key": "store_delete_all", "type": "store", "group": "Data store", "title": "Delete all records", "sub": "Empty a data store (asks you to confirm)",
     "make": {"op": "delete_all", "store": "", "confirm": True}},
    {"key": "store_increment", "type": "store", "group": "Data store", "title": "Add to a number", "sub": "A counter in a record (stock, visits)",
     "make": {"op": "increment", "store": "", "key": "", "field": "count", "by": 1}},
    {"key": "var_set_many", "type": "var", "group": "Variables", "title": "Set several values", "sub": "Keep values for later steps, all at once",
     "make": {"op": "set_many", "values": {"name": ""}}},
    {"key": "var_get", "type": "var", "group": "Variables", "title": "Get a value", "sub": "Read a value set earlier in the run",
     "make": {"op": "get", "name": ""}},
    {"key": "var_increment", "type": "var", "group": "Variables", "title": "Counter", "sub": "1, 2, 3 ... every time it runs (or every run)",
     "make": {"op": "increment", "name": "counter", "reset": "never"}},
    {"key": "var_save", "type": "var", "group": "Variables", "title": "Save a variable", "sub": "A value every route reads next time ({{env.NAME}})",
     "make": {"op": "save", "name": "last_run", "value": "{{run.started_at}}"}},
    {"key": "repeat", "type": "loop", "group": "Flow", "title": "Repeater", "sub": "Run steps a number of times (1, 2, 3 ...)",
     "make": {"repeat": {"times": 3, "start": 1, "step": 1}, "body": []}},
    {"key": "aggregate_loop", "type": "loop", "group": "Flow", "title": "Repeat and collect", "sub": "Go through a list and gather a value from each round",
     "make": {"items": "", "body": [], "collect": "{{item}}"}},
    {"key": "regex_match", "type": "data", "group": "Text parser", "title": "Match a pattern", "sub": "Find text by a pattern (regular expression)",
     "make": {"op": "text", "action": "regex_match", "value": "", "pattern": "", "global": True}},
    {"key": "regex_replace", "type": "data", "group": "Text parser", "title": "Replace by a pattern", "sub": "Change every match of a pattern",
     "make": {"op": "text", "action": "regex_replace", "value": "", "pattern": "", "replace": ""}},
    {"key": "markdown", "type": "data", "group": "Text parser", "title": "Markdown to HTML", "sub": "Turn Markdown text into a web page part",
     "make": {"op": "text", "action": "markdown_to_html", "value": ""}},
    {"key": "make_xml", "type": "data", "group": "Data", "title": "Make XML", "sub": "Turn data into XML text",
     "make": {"op": "text", "action": "data_to_xml", "value": "", "root": "data"}},
    {"key": "table_text", "type": "data", "group": "Data", "title": "Rows as a text table", "sub": "Columns and rows with your separators",
     "make": {"op": "text", "action": "rows_to_table", "value": "", "column_sep": " | "}},
    {"key": "zip", "type": "data", "group": "Data", "title": "Make a ZIP", "sub": "Put files from earlier steps into one ZIP",
     "make": {"op": "file", "action": "zip", "items": "", "name": "files"}},
    {"key": "unzip", "type": "data", "group": "Data", "title": "Open a ZIP", "sub": "Take the files out of a ZIP",
     "make": {"op": "file", "action": "unzip", "file_id": ""}},
]
for _k in KINDS:
    _k.setdefault("key", _k["type"])
POPULAR = ("email_draft", "email_check", "sheet_append", "sheet_read", "calendar_add_event", "drive_upload",
           "form_responses", "gdoc_write", "scrape_page", "web_fetch", "create_reminder", "composio_apps")
_HIDE_PREFIX = ("dhara_", "tool_search", "ask_form", "skill_")


def _fields(schema: dict) -> list[dict[str, Any]]:
    props = (schema or {}).get("properties") or {}
    req = set((schema or {}).get("required") or [])
    out = []
    for k, p in list(props.items())[:24]:
        if not isinstance(p, dict):
            continue
        t = p.get("type")
        if isinstance(t, list):
            t = next((x for x in t if x != "null"), "string")
        out.append({"name": k, "type": t or "string", "enum": [str(e) for e in (p.get("enum") or [])][:30],
                    "help": str(p.get("description") or "")[:160], "required": k in req})
    return out


def _first(s: str, n: int = 140) -> str:
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    m = re.split(r"(?<=[.!?])\s", s, maxsplit=1)[0]
    s = m if len(m) >= 20 else s
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def _tool_row(t: dict, labels: dict) -> dict[str, Any]:
    from .api import app_of
    return {"name": t["name"], "label": labels.get(t["name"]) or t["name"].replace("_", " ").capitalize(),
            "desc": _first(t.get("description") or ""), "app": app_of({"type": "tool", "name": t["name"]}),
            "fields": _fields(t.get("input_schema") or {})}


def tools(q: str = "", limit: int = 30) -> list[dict[str, Any]]:
    from ..agent import tools as T
    from ..agent import dhara_tools as D
    labels = getattr(T, "TOOL_LABELS", {}) or {}
    pool = [t for t in T.TOOLS if not t["name"].startswith(_HIDE_PREFIX) and t["name"] not in D._TOOL_STEP_DENY]
    words = [w for w in re.findall(r"[a-z0-9]+", str(q or "").lower()) if len(w) > 1]
    if not words:
        by = {t["name"]: t for t in pool}
        return [_tool_row(by[n], labels) for n in POPULAR if n in by][:limit]
    scored = []
    for t in pool:
        name = t["name"].lower()
        lab = str(labels.get(t["name"]) or "").lower()
        desc = str(t.get("description") or "").lower()[:600]
        sc = 0.0
        for w in words:
            sc += 4 if w in name else 0
            sc += 2 if w in lab else 0
            sc += 1 if re.search(r"\b" + re.escape(w), desc) else 0
        if sc:
            scored.append((sc, len(name), t))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [_tool_row(t, labels) for _, _, t in scored[:limit]]


def tool_one(name: str) -> dict[str, Any] | None:
    from ..agent import tools as T
    for t in T.TOOLS:
        if t["name"] == name:
            return _tool_row(t, getattr(T, "TOOL_LABELS", {}) or {})
    return None
