"""v0.510.0 DHARA — her workflows (धारा, the stream): the n8n idea, house-sized, end to end.

Owner: "DEVLOPE A N8N CLONE FOR HOOLA AI END TO END" after the full READ of github.com/n8n-io/n8n
(v2.47.0, fair-code). ZERO n8n code exists here (the Sustainable Use License forbids it and the
house forbids it anyway) — what is kept from n8n is the IDEA: a saved, validated workflow GRAPH;
triggers (manual / schedule / webhook); durable runs with a checkpoint after every step; honest
step logs. What n8n needs a visual canvas for, Hoola gets free: the AGENT builds the graph from
her words (dhara_save), tests it (dhara_run) and watches it (dhara_runs).

Storage: per-tenant SQLite beside the other lanes — data/dhara/<tenant>/dhara.db (workflows + runs).

The engine (dhara_jobs tick, the v0.491 crawl-jobs shape):
- Claim = ONE conditional UPDATE (tries+1; tries exhausted = failed honestly), stale-claim after
  dhara_stale_s, max 1 running per tenant.
- CHECKPOINT after every TOP-LEVEL step: cursor + context + step log written back, so a pm2 restart
  or a crash resumes mid-run and a finished step NEVER runs twice. A condition / loop step is one
  atomic unit (its body re-runs whole if the process died inside it — recorded in its log row).
- Two honest parks: waiting_approval (NEVER auto-resumes; her word in chat -> the agent relays it
  with dhara_control action=approve; expires after dhara_approval_hours = failed honestly) and
  sleeping (a wait step; the tick wakes it at next_wake_at).
- The safety net n8n does not have: tool steps run with Ctx(actor="routine") — the house's existing
  actor gate; services already refuse `routine` for sensitive actions, so money / messages / files
  still need HER the house way. ask_form is refused in steps (it is a same-turn card).

Steps (9): tool | code (pylab sandbox) | condition (then/else) | loop (capped) | wait | notify |
approval | set | http (SSRF-guarded). Expressions {{steps.id.output.f}} / {{vars.x}} / {{item}} /
{{now}} go through a safe dotted-path resolver — NEVER eval().

Tools (5): dhara_save / dhara_run / dhara_runs / dhara_control (enable|disable|stop|approve) /
dhara_list. Registry 536 -> 541. Webhook: POST /api/dhara/hook/{token} (token shown ONCE at save,
stored sha256-hashed, 10 req/min/token).
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .tools import Ctx, ToolError


def _masked(v: Any) -> Any:
    """ID numbers in what comes back are masked before the chat model reads it (the house rule)."""
    from ..operator.browser import mask_ids
    if isinstance(v, str):
        return mask_ids(v)
    if isinstance(v, dict):
        return {k: _masked(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_masked(x) for x in v]
    return v

_IST = ZoneInfo("Asia/Kolkata")
_MAX_STEPS = 40          # top-level steps per workflow (config clamps around this)
_MAX_DEPTH = 3           # v0.999.239 ROUTE R4: branches / loops nest up to three levels (was one)
_LOOP_MAX = 1000         # v0.999.239 iterations per loop step (was 50); the run's time limit still applies
_LOOP_HARD = 5000        # a setting can raise the loop cap only this far
_SUB_DEPTH = 3           # v0.999.239 a sub-route may start a sub-route, at most 3 deep
_WAIT_MAX_S = 30 * 86400 # v0.999.239 the longest wait: 30 days (was one hour)
_WAIT_UNITS = {"seconds": 1, "minutes": 60, "hours": 3600, "days": 86400, "weeks": 7 * 86400}
_RESPOND_WAIT_S = 25     # a webhook caller waits this long for a Respond step
_RESPOND_MAX = 100_000   # one response body cap
_CONTAINERS = ("condition", "router", "loop")
_SIGNALS = ("__PARK__", "__APPROVE__", "__END__", "__HALT__")
_RESPONSES: dict[str, dict] = {}   # run id -> the Respond step's answer (the webhook caller waits on it)
_NOTIFY_MAX = 5          # notify steps that may fire per run
_GRAPH_CHARS = 64_000    # serialized steps cap
_EXPR_CHARS = 2_000      # one expression cap
_STEP_LOG_SNIPPET = 600  # chars of a step output kept in steps_log
_HTTP_CHARS = 100_000    # http step body cap
_TOKEN_MIN_RATE_S = 6.0  # webhook: >= 6 s between runs of one workflow (10/min ceiling)
polite_s = 0.05          # sleep between two steps (tests may shrink it)
_RUNNING: set[str] = set()
_TASKS: set["asyncio.Task"] = set()

_STEP_TYPES = ("tool", "code", "condition", "loop", "wait", "notify", "approval", "set", "http",
               "router", "filter", "data", "subroute", "stop", "respond", "ai",
               "store", "var", "send")   # v0.999.254 MAKE PARITY: data stores + Make's variable tools   # v0.999.243 ROUTE R6: AI steps      # v0.999.87 HOOLA ROUTE: a router with named routes + a filter gate
_COND_OPS = ("eq", "ne", "gt", "lt", "contains", "empty")
# v0.999.87 HOOLA ROUTE filter language (the Make / n8n filter idea, own code): one condition is
# {left, op, right, ci?}; groups are {"all": [...]} (AND) / {"any": [...]} (OR), nested up to _FILTER_DEPTH.
_FILTER_OPS = ("exists", "not_exists", "empty", "not_empty", "eq", "ne", "contains", "not_contains",
               "starts_with", "ends_with", "matches", "gt", "gte", "lt", "lte", "between",
               "before", "after", "is_true", "is_false", "in", "not_in",
               "length_eq", "length_gt", "length_lt")
_FILTER_DEPTH = 4
_FILTER_ITEMS = 20
_ROUTES_MAX = 8
# v0.999.87 per-step error handling (the Make directives, own code): what a failed step does to its run.
_ON_ERROR = ("break", "resume", "ignore", "commit", "rollback", "tell")
_VAR_OPS = ("set_many", "get", "get_many", "increment", "save")     # v0.999.254 Make's Tools: variables + counter
_REPEAT_MAX = 10_000
_RETRY_MAX = 10
_DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
# Turn-shaped tools that make no sense inside a background run (they need the live turn to carry
# the answer). Everything else is allowed — each tool's OWN guards still apply (actor="routine").
_TOOL_STEP_DENY = {"ask_form"}
_EXPR_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_.\[\]]{0,120})\s*\}\}")
_PATH_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z0-9_]+)*$")
# v0.999.237 ROUTE R3: any {{ ... }} - a plain path keeps the old meaning; anything else is an expression (dhara_data)
_ANY_EXPR_RE = re.compile(r"\{\{(.{1,2000}?)\}\}", re.S)
_EventHandlerT = Any  # events module is imported lazily (house pattern)


# --------------------------------------------------------------------------- store (per-tenant sqlite)

def _db_path(tenant_id: str) -> Path:
    return Path("data") / "dhara" / tenant_id / "dhara.db"


def _con(tenant_id: str) -> sqlite3.Connection:
    _db_path(tenant_id).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(_db_path(tenant_id)), timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE IF NOT EXISTS workflows (id TEXT PRIMARY KEY, name TEXT UNIQUE, "
                "description TEXT, trigger_kind TEXT DEFAULT 'manual', trigger_spec TEXT DEFAULT '{}', "
                "token_hash TEXT, steps TEXT, enabled INTEGER DEFAULT 1, next_due_at REAL, "
                "conversation_id TEXT, created_at REAL, updated_at REAL)")
    con.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, workflow_id TEXT, wf_name TEXT, "
                "status TEXT, cursor INTEGER DEFAULT 0, context TEXT DEFAULT '{}', steps_log TEXT DEFAULT '[]', "
                "error TEXT, tries INTEGER DEFAULT 0, next_wake_at REAL, started_at REAL, missed INTEGER DEFAULT 0, "
                "created_at REAL, updated_at REAL)")
    # v0.512: ops-grade eyes on the runs — a computed summary at every honest end + a typed pause reason.
    # Idempotent ALTERs so tenants whose dhara.db predates v0.512 keep working untouched.
    for _col in ("summary TEXT", "pause_reason TEXT"):
        try:
            con.execute(f"ALTER TABLE runs ADD COLUMN {_col}")
        except sqlite3.OperationalError:
            pass  # column already exists
    # v0.999.87 HOOLA ROUTE: route-level settings (folder, time zone, errors-in-a-row stop, error route, daily cap)
    # + the count of failed runs in a row. Idempotent: an older dhara.db gains the columns on first open.
    for _col in ("settings TEXT DEFAULT '{}'", "consecutive_errors INTEGER DEFAULT 0"):
        try:
            con.execute(f"ALTER TABLE workflows ADD COLUMN {_col}")
        except sqlite3.OperationalError:
            pass
    con.execute("CREATE INDEX IF NOT EXISTS idx_runs_wf ON runs (workflow_id, created_at)")
    return con


def _wf_row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    if r is None:
        return None
    d = dict(r)
    try:
        d["trigger_spec"] = json.loads(d.get("trigger_spec") or "{}")
    except Exception:
        d["trigger_spec"] = {}
    try:
        d["steps"] = json.loads(d.get("steps") or "[]")
    except Exception:
        d["steps"] = []
    try:
        d["settings"] = json.loads(d.get("settings") or "{}") or {}
    except Exception:
        d["settings"] = {}
    d["consecutive_errors"] = int(d.get("consecutive_errors") or 0)
    return d


def _run_row(r: sqlite3.Row | None) -> dict[str, Any] | None:
    if r is None:
        return None
    d = dict(r)
    try:
        d["context"] = json.loads(d.get("context") or "{}")
    except Exception:
        d["context"] = {"vars": {}, "steps": {}}
    try:
        d["steps_log"] = json.loads(d.get("steps_log") or "[]")
    except Exception:
        d["steps_log"] = []
    try:
        d["summary"] = json.loads(d["summary"]) if d.get("summary") else None
    except Exception:
        d["summary"] = None
    return d


def save_workflow(tenant_id: str, name: str, description: str, trigger_kind: str,
                  trigger_spec: dict, steps: list, conversation_id: str = "",
                  settings: dict | None = None, note: str = "") -> tuple[dict, bool]:
    """Insert or update by name. Returns (row, created). Keeps id / created_at on update;
    a webhook token is generated once and kept unless the trigger kind changed away and back.
    v0.999.246: every save keeps a version of the route (route/workspace.keep_version)."""
    now_ = time.time()
    con = _con(tenant_id)
    try:
        old = con.execute("SELECT * FROM workflows WHERE name = ?", (name,)).fetchone()
        token_hash = None
        if trigger_kind in ("webhook", "form", "chat"):   # v0.999.240: a form / chat page has an address too
            if old is not None and old["token_hash"] and old["trigger_kind"] == trigger_kind:
                token_hash = old["token_hash"]
            else:
                token_hash = hashlib.sha256(secrets.token_urlsafe(24).encode()).hexdigest()
        if old is None:
            wid = "wl_" + uuid.uuid4().hex[:12]
            con.execute("INSERT INTO workflows (id, name, description, trigger_kind, trigger_spec, token_hash, "
                        "steps, enabled, conversation_id, created_at, updated_at) VALUES (?,?,?,?,?,?,?,1,?,?,?)",
                        (wid, name, description[:500], trigger_kind, json.dumps(trigger_spec), token_hash,
                         json.dumps(steps), conversation_id[:100], now_, now_))
            created = True
            if settings is not None:
                con.execute("UPDATE workflows SET settings = ? WHERE id = ?", (json.dumps(settings), wid))
        else:
            wid = old["id"]
            th = token_hash if trigger_kind in ("webhook", "form", "chat") else None
            con.execute("UPDATE workflows SET description=?, trigger_kind=?, trigger_spec=?, token_hash=?, steps=?, "
                        "updated_at=? WHERE id=?",
                        (description[:500], trigger_kind, json.dumps(trigger_spec), th, json.dumps(steps), now_, wid))
            if settings is not None:        # v0.999.87: None = keep the route's settings as they are
                con.execute("UPDATE workflows SET settings = ? WHERE id = ?", (json.dumps(settings), wid))
            created = False
        con.commit()
        row = _wf_row(con.execute("SELECT * FROM workflows WHERE id = ?", (wid,)).fetchone())
    finally:
        con.close()
    try:
        from ..route import workspace as WS
        WS.keep_version(tenant_id, row, note)
    except Exception:   # noqa: BLE001  (a version is a help, never a reason a save fails)
        pass
    return row, created


def get_workflow(tenant_id: str, name: str = "", wf_id: str = "") -> dict[str, Any] | None:
    con = _con(tenant_id)
    try:
        if wf_id:
            r = con.execute("SELECT * FROM workflows WHERE id = ?", (wf_id,)).fetchone()
        else:
            r = con.execute("SELECT * FROM workflows WHERE name = ?", (name,)).fetchone()
        return _wf_row(r)
    finally:
        con.close()


def list_workflows(tenant_id: str, limit: int = 25) -> list[dict[str, Any]]:
    con = _con(tenant_id)
    try:
        rows = con.execute("SELECT * FROM workflows ORDER BY updated_at DESC LIMIT ?", (int(limit),)).fetchall()
        return [_wf_row(r) for r in rows]
    finally:
        con.close()


def set_enabled(tenant_id: str, wf_id: str, enabled: bool) -> bool:
    con = _con(tenant_id)
    try:
        # v0.999.253: on / off is not an edit of the route - it no longer moves updated_at, so an editor left open
        # does not get "this route changed since you opened it" on its next save
        cur = con.execute("UPDATE workflows SET enabled = ? WHERE id = ?", (1 if enabled else 0, wf_id))
        con.commit()
        changed = cur.rowcount > 0
    finally:
        con.close()
    if changed and enabled:
        try:                       # v0.999.254: calls kept while it was off now run, oldest first, 6 s apart
            con = _con(tenant_id)
            try:
                rows = con.execute("SELECT id FROM runs WHERE workflow_id = ? AND status = 'sleeping' AND "
                                   "pause_reason = 'queue_off' ORDER BY created_at", (wf_id,)).fetchall()
                t0 = time.time()
                for i, r in enumerate(rows):
                    con.execute("UPDATE runs SET pause_reason = 'queue', next_wake_at = ? WHERE id = ?",
                                (t0 + i * _TOKEN_MIN_RATE_S, r["id"]))
                con.commit()
            finally:
                con.close()
        except Exception:   # noqa: BLE001
            pass
        try:                       # v0.999.240: an app-event route switched on looks fresh (old items do not run)
            from ..route import triggers as TR
            TR.rebaseline(tenant_id, wf_id)
        except Exception:   # noqa: BLE001
            pass
    return changed


def workflows_with_hash(tenant_id: str, token_hash: str) -> dict[str, Any] | None:
    con = _con(tenant_id)
    try:
        r = con.execute("SELECT * FROM workflows WHERE token_hash = ?", (token_hash,)).fetchone()
        return _wf_row(r)
    finally:
        con.close()


def create_run(tenant_id: str, wf: dict, vars_: dict | None = None, missed: bool = False,
               extra: dict | None = None, park: tuple | None = None) -> str:
    """extra (v0.999.253): more context written WITH the run (a test's pinned data), so the worker can never pick
    the run up before it is there."""
    now_ = time.time()
    rid = "rn_" + uuid.uuid4().hex[:12]
    ctx0 = {"vars": dict(vars_ or {}), "steps": {}, "notify": 0,
            "_start": dict(vars_ or {})}             # v0.999.248 R8: what it started with, for Run again
    if isinstance(extra, dict):
        ctx0.update(extra)
    con = _con(tenant_id)
    try:
        con.execute("INSERT INTO runs (id, workflow_id, wf_name, status, cursor, context, steps_log, tries, "
                    "started_at, missed, created_at, updated_at) VALUES (?,?,?,?,0,?,?,0,?,?,?,?)",
                    (rid, wf["id"], wf["name"], "queued", json.dumps(ctx0, ensure_ascii=False),
                     "[]", now_ if not missed else None, 1 if missed else 0, now_, now_))
        if park:                      # v0.999.254: written asleep in one go - the worker never sees it queued
            con.execute("UPDATE runs SET status = 'sleeping', pause_reason = ?, next_wake_at = ? WHERE id = ?",
                        (str(park[0]), float(park[1]), rid))
        con.commit()
    finally:
        con.close()
    return rid


def get_run(tenant_id: str, run_id: str) -> dict[str, Any] | None:
    con = _con(tenant_id)
    try:
        return _run_row(con.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone())
    finally:
        con.close()


def latest_run(tenant_id: str, wf_id: str) -> dict[str, Any] | None:
    con = _con(tenant_id)
    try:
        return _run_row(con.execute("SELECT * FROM runs WHERE workflow_id = ? ORDER BY created_at DESC LIMIT 1",
                                    (wf_id,)).fetchone())
    finally:
        con.close()


def list_runs(tenant_id: str, wf_id: str = "", limit: int = 10, status: str = "") -> list[dict[str, Any]]:
    con = _con(tenant_id)
    try:
        where, args = [], []
        if wf_id:
            where.append("workflow_id = ?"); args.append(wf_id)
        if status:            # v0.999.128: filtered in SQL, so an older run of that state is never cut by the limit
            where.append("status = ?"); args.append(status)
        rows = con.execute("SELECT * FROM runs" + (" WHERE " + " AND ".join(where) if where else "") +
                           " ORDER BY created_at DESC LIMIT ?", (*args, int(limit))).fetchall()
        out = []
        for r in rows:
            d = _run_row(r)
            d["steps_log"] = len(d["steps_log"])
            d["missed"] = bool(d.get("missed"))
            d.pop("context", None)
            out.append(d)
        return out
    finally:
        con.close()


def update_run(tenant_id: str, run_id: str, _keep_stop: bool = False, **fields) -> bool:
    """_keep_stop (v0.999.253): the engine's own writes never undo a Stop she pressed while a step was running."""
    if not fields:
        return False
    if "context" in fields and not isinstance(fields["context"], str):
        fields["context"] = json.dumps(fields["context"], ensure_ascii=False)   # v0.999.253: findable in any language
    if "steps_log" in fields and not isinstance(fields["steps_log"], str):
        fields["steps_log"] = json.dumps(fields["steps_log"], ensure_ascii=False)
    fields.setdefault("updated_at", time.time())  # an explicit updated_at (tests backdate) wins
    sets = ", ".join(f"{k} = ?" for k in fields)
    con = _con(tenant_id)
    try:
        guard = " AND status != 'stopped'" if _keep_stop else ""
        cur = con.execute(f"UPDATE runs SET {sets} WHERE id = ?{guard}", (*fields.values(), run_id))
        con.commit()
        return cur.rowcount > 0
    finally:
        con.close()


def forget_old_runs(tenant_id: str, keep_days: int = 30, keep: int = 40) -> int:
    """Finished runs past the keeping go. v0.999.248 R8: a route that says how long / how many runs it keeps
    (settings keep_runs_days / keep_runs) is kept that way; the rest share the server's default."""
    from ..route import runs as RU
    fin = "status NOT IN ('queued','running','sleeping','waiting_approval','incomplete')"
    now_ = time.time()
    cut = now_ - max(1, int(keep_days)) * 86400
    con = _con(tenant_id)
    try:
        own: dict[str, tuple[int, int]] = {}
        for r in con.execute("SELECT id, settings FROM workflows").fetchall():
            try:
                k = RU.keeping(json.loads(r["settings"] or "{}") or {}, keep_days, keep)
            except (TypeError, ValueError):
                k = None
            if k:
                own[r["id"]] = k
        gone = 0
        for wid, (d, k) in own.items():
            gone += con.execute(f"DELETE FROM runs WHERE workflow_id = ? AND {fin} AND updated_at < ?",
                                (wid, now_ - d * 86400)).rowcount
            for (rid,) in con.execute(f"SELECT id FROM runs WHERE workflow_id = ? AND {fin} "
                                      "ORDER BY updated_at DESC LIMIT -1 OFFSET ?", (wid, int(k))).fetchall():
                con.execute("DELETE FROM runs WHERE id = ?", (rid,))
                gone += 1
        mine = (" AND workflow_id NOT IN (" + ",".join("?" * len(own)) + ")") if own else ""
        gone += con.execute(f"DELETE FROM runs WHERE {fin} AND updated_at < ?" + mine, (cut, *own)).rowcount
        extra = con.execute(f"SELECT id FROM runs WHERE {fin}" + mine +
                            " ORDER BY updated_at DESC LIMIT -1 OFFSET ?", (*own, int(keep))).fetchall()
        for (rid,) in extra:
            con.execute("DELETE FROM runs WHERE id = ?", (rid,))
            gone += 1
        con.commit()
        return gone
    finally:
        con.close()


# --------------------------------------------------------------------------- validation

def _walk_steps(steps: list, depth: int = 0) -> "list[tuple[dict, int]]":
    out = []
    for s in steps or []:
        if not isinstance(s, dict):
            raise ToolError("Every step must be an object ({}), got: " + type(s).__name__)
        out.append((s, depth))
        for key in ("then", "else", "body", "fallback"):
            sub = s.get(key)
            if key == "body" and str(s.get("type") or "") != "loop":
                continue        # v0.999.239: a web request's / an answer's body is data, not steps
            if sub:
                out.extend(_walk_steps(sub, depth + 1))
        for rt in (s.get("routes") or []) if isinstance(s.get("routes"), list) else []:
            if isinstance(rt, dict) and rt.get("steps"):
                out.extend(_walk_steps(rt["steps"], depth + 1))
        oe = s.get("on_error")                       # v0.999.254: an error handler's own steps (Make's handler route)
        if isinstance(oe, dict) and isinstance(oe.get("steps"), list) and oe["steps"]:
            out.extend(_walk_steps(oe["steps"], depth + 1))
    return out


def validate_filter(f: Any, sid: str = "?", depth: int = 0) -> None:
    """v0.999.87: a filter is one condition {left, op, right} or a group {all|any: [...]}; raises on the FIRST problem."""
    if depth > _FILTER_DEPTH:
        raise ToolError(f"Step '{sid}': the filter is nested too deep (cap {_FILTER_DEPTH} levels)")
    if not isinstance(f, dict):
        raise ToolError(f"Step '{sid}': a filter must be an object like {{left, op, right}} or {{all: [...]}}")
    for grp in ("all", "any"):
        if grp in f:
            items = f[grp]
            if not isinstance(items, list) or not items:
                raise ToolError(f"Step '{sid}': '{grp}' needs a non-empty list of conditions")
            if len(items) > _FILTER_ITEMS:
                raise ToolError(f"Step '{sid}': at most {_FILTER_ITEMS} conditions in one group")
            for it in items:
                validate_filter(it, sid, depth + 1)
            return
    op = str(f.get("op") or "")
    if op not in _FILTER_OPS:
        raise ToolError(f"Step '{sid}': filter op '{op}' is unknown — choose one of: {', '.join(_FILTER_OPS)}")
    if "left" not in f:
        raise ToolError(f"Step '{sid}': a filter condition needs a left value (like {{{{steps.order.output.total}}}})")
    if op == "matches":
        try:
            re.compile(str(f.get("right") or ""))
        except re.error as e:
            raise ToolError(f"Step '{sid}': the 'matches' pattern is not a valid regular expression ({e})")
    if op == "between" and not (isinstance(f.get("right"), list) and len(f["right"]) == 2):
        raise ToolError(f"Step '{sid}': 'between' needs right = [low, high]")


def validate_on_error(oe: Any, sid: str) -> dict | None:
    """v0.999.87: {do: break|resume|ignore|commit|rollback|tell, retries?, wait_min?, value?} -> normalised."""
    if oe in (None, "", {}):
        return None
    if isinstance(oe, str):
        oe = {"do": oe}
    if not isinstance(oe, dict):
        raise ToolError(f"Step '{sid}': on_error must be like {{do: 'break', retries: 3, wait_min: 10}}")
    do = str(oe.get("do") or "").lower()
    hsteps = oe.get("steps")
    if hsteps not in (None, []) and not isinstance(hsteps, list):
        raise ToolError(f"Step '{sid}': the error handler's steps must be a list")
    if not do and hsteps:
        do = "ignore"                                # Make: a handler route with no directive at its end = ignore
    if do not in _ON_ERROR:
        raise ToolError(f"Step '{sid}': on_error do must be one of: {', '.join(_ON_ERROR)}")
    out: dict[str, Any] = {"do": do}
    if hsteps:
        bad = [str(x.get("id")) for x, _d in _walk_steps(hsteps) if str(x.get("type")) in ("wait", "approval", "respond")]
        if bad:
            raise ToolError(f"Step '{sid}': an error handler cannot wait or ask (step {bad[0]}) - it runs straight through")
        out["steps"] = hsteps
    if do == "break":
        try:
            out["retries"] = max(0, min(int(oe.get("retries", 3)), _RETRY_MAX))
            out["wait_min"] = max(1, min(int(oe.get("wait_min", 10)), 1440))
        except (TypeError, ValueError):
            raise ToolError(f"Step '{sid}': break needs whole numbers for retries (0-{_RETRY_MAX}) and wait_min (1-1440)")
    if do == "resume":
        out["value"] = oe.get("value")
    return out


def validate_steps(steps: list) -> list[dict]:
    """Hard validation. Returns the normalised steps or raises ToolError with the FIRST problem."""
    from ..config import get_settings
    s = get_settings()
    max_steps = int(getattr(s, "dhara_max_steps", _MAX_STEPS))
    loop_max = int(getattr(s, "dhara_loop_max", _LOOP_MAX))
    if not isinstance(steps, list) or not steps:
        raise ToolError("steps must be a non-empty list")
    if len(json.dumps(steps)) > _GRAPH_CHARS:
        raise ToolError(f"The workflow graph is too big ({len(json.dumps(steps))} chars; cap {_GRAPH_CHARS})")
    top = [s for s in steps]
    if len(top) > max_steps:
        raise ToolError(f"At most {max_steps} steps (got {len(top)})")
    seen: set[str] = set()
    for st_, depth in _walk_steps(top):
        if depth > _MAX_DEPTH:
            raise ToolError(f"Steps inside branches and loops can go only {_MAX_DEPTH} levels deep")
        sid = str(st_.get("id") or "").strip()
        typ = str(st_.get("type") or "").strip().lower()
        if not sid or not _PATH_RE.match(sid):
            raise ToolError(f"Every step needs a short id (lowercase_with_underscores) — got: {sid!r}")
        if sid in seen:
            raise ToolError(f"Step id '{sid}' appears twice — keep ids unique")
        seen.add(sid)
        if typ not in _STEP_TYPES:
            raise ToolError(f"Step '{sid}': unknown type '{typ}' — choose one of: {', '.join(_STEP_TYPES)}")
        if typ == "tool":
            name = str(st_.get("name") or "").strip()
            if not name:
                raise ToolError(f"Step '{sid}': a tool step needs a tool name")
            if name in _TOOL_STEP_DENY:
                raise ToolError(f"Step '{sid}': {name} is a same-turn card — it cannot run in a background run")
            if name.startswith("dhara_") and name not in ("dhara_list", "dhara_runs"):
                # v0.999.253: a route that starts / changes routes could run for ever (reading them is fine)
                raise ToolError(f"Step '{sid}': a route cannot use {name} - use a 'Run another route' step instead")
        elif typ == "code":
            if not str(st_.get("code") or "").strip():
                raise ToolError(f"Step '{sid}': give a code step python code")
        elif typ == "condition":
            if st_.get("filter") is not None:          # v0.999.87: a condition may use the full filter language
                validate_filter(st_["filter"], sid)
            elif str(st_.get("op") or "") not in _COND_OPS:
                raise ToolError(f"Step '{sid}': op must be one of: {', '.join(_COND_OPS)}")
            if not isinstance(st_.get("then"), list) and not isinstance(st_.get("else"), list):
                raise ToolError(f"Step '{sid}': give a condition a list of then or else steps")
        elif typ == "loop":
            if not isinstance(st_.get("body"), list) or not st_.get("body"):
                raise ToolError(f"Step '{sid}': give a loop a list of body steps")
            rp = st_.get("repeat")                   # v0.999.254 Make's Repeater: a loop over a counted range
            if rp is not None:
                if not isinstance(rp, dict) or rp.get("times") in (None, ""):
                    raise ToolError(f"Step '{sid}': repeat needs times (and start / step if you like)")
                for kk in ("times", "start", "step"):
                    vv = rp.get(kk)
                    if vv not in (None, "") and "{{" not in str(vv):
                        try:
                            int(vv)
                        except (TypeError, ValueError):
                            raise ToolError(f"Step '{sid}': repeat {kk} must be a whole number")
                if "{{" not in str(rp["times"]) and not 0 <= int(rp["times"]) <= _REPEAT_MAX:
                    raise ToolError(f"Step '{sid}': repeat times is 0-{_REPEAT_MAX}")
            elif "items" not in st_:
                raise ToolError(f"Step '{sid}': a loop needs items (an expression that gives a list)")
            if st_.get("as") not in (None, "") and not _PATH_RE.match(str(st_["as"])):
                raise ToolError(f"Step '{sid}': as must be a short name (lowercase_with_underscores)")
        elif typ == "wait":
            _validate_wait(st_, sid)
        elif typ == "subroute":
            if not str(st_.get("route") or "").strip():
                raise ToolError(f"Step '{sid}': a sub-route step needs the name of the route to run")
            if st_.get("vars") not in (None, "") and not isinstance(st_.get("vars"), (dict, str)):
                raise ToolError(f"Step '{sid}': vars must be an object of name: value")
        elif typ == "stop":
            if str(st_.get("as") or "error") not in ("error", "done"):
                raise ToolError(f"Step '{sid}': stop as must be error or done")
        elif typ == "respond":
            stc = st_.get("status", 200)
            if not isinstance(stc, str) or "{{" not in stc:
                try:
                    if not 100 <= int(stc) <= 599:
                        raise ValueError
                except (TypeError, ValueError):
                    raise ToolError(f"Step '{sid}': respond status must be an HTTP code 100-599")
        elif typ == "notify":
            if not str(st_.get("text") or "").strip():
                raise ToolError(f"Step '{sid}': notify needs text")
        elif typ == "approval":
            if not str(st_.get("question") or "").strip():
                raise ToolError(f"Step '{sid}': approval needs a question")
        elif typ == "set":
            if not _PATH_RE.match(str(st_.get("name") or "")):
                raise ToolError(f"Step '{sid}': give set a variable name (lowercase_with_underscores)")
        elif typ == "router":
            routes = st_.get("routes")
            if not isinstance(routes, list) or not routes:
                raise ToolError(f"Step '{sid}': a router needs routes: [{{label, filter, steps}}, ...]")
            if len(routes) > _ROUTES_MAX:
                raise ToolError(f"Step '{sid}': at most {_ROUTES_MAX} routes on one router")
            for i, rt in enumerate(routes):
                if not isinstance(rt, dict) or not isinstance(rt.get("steps"), list) or not rt.get("steps"):
                    raise ToolError(f"Step '{sid}': route {i + 1} needs a list of steps")
                if rt.get("filter") is not None:
                    validate_filter(rt["filter"], sid)
                if len(str(rt.get("label") or "")) > 80:
                    raise ToolError(f"Step '{sid}': route {i + 1} label is too long (80 chars)")
            if st_.get("fallback") is not None and not isinstance(st_.get("fallback"), list):
                raise ToolError(f"Step '{sid}': fallback must be a list of steps")
            if st_.get("ai") is not None:              # v0.999.243: the AI picks the way
                from ..route import aistep as AS
                AS.validate_choose(st_, sid)
        elif typ == "filter":
            if st_.get("filter") is None:
                raise ToolError(f"Step '{sid}': a filter step needs a filter ({{left, op, right}} or {{all: [...]}})")
            validate_filter(st_["filter"], sid)
        elif typ == "data":                              # v0.999.237 ROUTE R3
            from . import dhara_data as DD
            DD.validate(st_, sid)
        elif typ == "ai":                                # v0.999.243 ROUTE R6
            from ..route import aistep as AS
            AS.validate(st_, sid)
        elif typ == "store":                             # v0.999.254 MAKE PARITY: data stores
            from ..route import store as DS
            DS.validate(st_, sid)
        elif typ == "var":
            op_ = str(st_.get("op") or "")
            if op_ not in _VAR_OPS:
                raise ToolError(f"Step '{sid}': a variables step needs op = one of: {', '.join(_VAR_OPS)}")
            if op_ == "set_many" and not isinstance(st_.get("values"), (dict, str)):
                raise ToolError(f"Step '{sid}': set_many needs values - an object of name: value")
            if op_ in ("get", "increment", "save") and not _PATH_RE.match(str(st_.get("name") or "")):
                raise ToolError(f"Step '{sid}': give the variable a name (lowercase_with_underscores)")
            if op_ == "increment" and str(st_.get("reset") or "never") not in ("never", "run"):
                raise ToolError(f"Step '{sid}': increment reset is never (keeps counting across runs) or run")
        elif typ == "http":                              # v0.999.254: Make's HTTP app (every method, body, page)
            from ..route import http as HT
            HT.validate(st_, sid)
        elif typ == "send":                              # v0.999.278 SENDING: mail / Telegram / Slack / Discord / Mattermost
            from ..route import send as SN
            SN.validate(st_, sid)
        if "on_error" in st_:
            st_["on_error"] = validate_on_error(st_.get("on_error"), sid)
            if st_["on_error"] is None:
                st_.pop("on_error", None)
        # expression size cap on every string field
        for v in st_.values():
            if isinstance(v, str) and len(v) > _EXPR_CHARS:
                raise ToolError(f"Step '{sid}': expression/text too long (cap {_EXPR_CHARS} chars)")
        # v0.999.237: every {{ }} that is not a plain path must be a well-formed expression
        from . import dhara_data as DD

        def _exprs(v):
            if isinstance(v, str):
                for mm in _ANY_EXPR_RE.finditer(v):
                    inner = mm.group(1).strip()
                    if _PATH_RE.match(inner):
                        continue
                    why = DD.check(inner)
                    if why:
                        raise ToolError(f"Step '{sid}': {{{{ {inner[:60]} }}}} - {why}")
            elif isinstance(v, dict):
                for x in v.values():
                    _exprs(x)
            elif isinstance(v, list):
                for x in v:
                    _exprs(x)
        for k, v in st_.items():
            if k not in ("then", "else", "body", "fallback", "routes", "code"):
                _exprs(v)
    _ = loop_max  # loop iteration cap lives in the engine (a graph cannot exceed it anyway)
    return top


def _validate_wait(st_: dict, sid: str) -> None:
    """v0.999.239 ROUTE R4: a wait is some time (duration_s, or amount + unit, up to 30 days), until a moment
    (HH:MM or a date and time, in the route's time zone), or until someone calls the run's resume link."""
    if str(st_.get("for") or "") == "call":
        t = st_.get("timeout_s", 86400)
        try:
            if not 60 <= int(t) <= _WAIT_MAX_S:
                raise ValueError
        except (TypeError, ValueError):
            raise ToolError(f"Step '{sid}': a wait for a call needs timeout_s from 60 seconds to 30 days")
        if str(st_.get("on_timeout") or "continue") not in ("continue", "fail"):
            raise ToolError(f"Step '{sid}': on_timeout must be continue or fail")
        return
    if st_.get("for") not in (None, ""):
        raise ToolError(f"Step '{sid}': wait for can only be call")
    if st_.get("amount") not in (None, ""):
        if str(st_.get("unit") or "minutes") not in _WAIT_UNITS:
            raise ToolError(f"Step '{sid}': unit must be one of: {', '.join(_WAIT_UNITS)}")
        a = st_["amount"]
        if not (isinstance(a, str) and "{{" in a):
            try:
                if float(a) * _WAIT_UNITS[str(st_.get("unit") or "minutes")] > _WAIT_MAX_S or float(a) < 0:
                    raise ValueError
            except (TypeError, ValueError):
                raise ToolError(f"Step '{sid}': a wait can be up to 30 days")
        return
    d = st_.get("duration_s")
    if d not in (None, "", 0):
        if not (isinstance(d, str) and "{{" in d):
            try:
                if not 0 < int(d) <= _WAIT_MAX_S:
                    raise ValueError
            except (TypeError, ValueError):
                raise ToolError(f"Step '{sid}': duration_s must be 1 second to 30 days ({_WAIT_MAX_S})")
        return
    u = str(st_.get("until") or "").strip()
    if not u:
        raise ToolError(f"Step '{sid}': give wait a duration_s, an amount and unit, until 'HH:MM' or a date and "
                        "time, or for: call")
    if "{{" not in u and _hm(u) is None:
        try:
            datetime.fromisoformat(u.replace(" ", "T"))
        except ValueError:
            raise ToolError(f"Step '{sid}': until must be 'HH:MM' or 'YYYY-MM-DD HH:MM'")


def _wait_secs(step: dict, ctx: dict) -> int:
    """How long a wait step waits from now (0 = a moment already past: go straight on)."""
    if step.get("amount") not in (None, ""):
        try:
            a = float(resolve(step.get("amount"), ctx) or 0)
        except (TypeError, ValueError):
            raise ToolError("the wait amount is not a number with this data")
        return int(max(0, min(a * _WAIT_UNITS.get(str(step.get("unit") or "minutes"), 60), _WAIT_MAX_S)))
    dur = step.get("duration_s")
    if dur not in (None, "", 0):
        try:
            return int(max(0, min(float(resolve(dur, ctx) or 0), _WAIT_MAX_S)))
        except (TypeError, ValueError):
            raise ToolError("the wait time is not a number with this data")
    tz = _tzinfo(str(ctx.get("_tz") or ""))
    now_i = datetime.now(tz)
    u = str(resolve(step.get("until") or "", ctx) or "").strip()
    hm = _hm(u)
    if hm is not None:
        target = now_i.replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)
        if target <= now_i:
            target += timedelta(days=1)
    else:
        try:
            target = datetime.fromisoformat(u.replace(" ", "T").replace("Z", "+00:00"))
        except ValueError:
            raise ToolError(f"'{u[:40]}' is not a time (HH:MM) or a date and time")
        if target.tzinfo is None:
            target = target.replace(tzinfo=tz)
    secs = int((target - now_i).total_seconds())
    if secs > _WAIT_MAX_S:
        raise ToolError("that moment is more than 30 days away - a wait can be up to 30 days")
    return max(0, secs)


# --------------------------------------------------------------------------- expressions (safe, never eval)

def _dig(obj: Any, path: str) -> Any:
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.isdigit():
            i = int(part)
            cur = cur[i] if 0 <= i < len(cur) else None
        else:
            return None
    return cur


def _one_value(inner: str, ctx: dict, raw: str) -> Any:
    """v0.999.237: the value of one {{ }}: a plain path as before; else a safe expression; one that fails stays as written."""
    from . import dhara_data as DD
    inner = inner.strip()
    if _PATH_RE.match(inner) and not (inner in DD.KEYWORDS and inner not in ctx):
        return _dig(ctx, inner)
    try:
        return DD.evaluate(inner, ctx)
    except DD.ExprError:
        return raw


def _resolve_one(expr: Any, ctx: dict) -> Any:
    """A pure {{path}} returns the VALUE (so conditions compare real types); mixed text returns text.
    v0.999.237: {{ }} may hold an expression with maths and functions (dhara_data) - a whole-string one returns its value."""
    if isinstance(expr, str):
        whole = _ANY_EXPR_RE.fullmatch(expr.strip())
        if whole and ("}}" in whole.group(1) or "{{" in whole.group(1)):
            whole = None                     # v0.999.254: "{{a}}|{{b}}" is two values in a text, not one expression
        if whole:
            return _one_value(whole.group(1), ctx, expr)

        def sub(mm):
            v = _one_value(mm.group(1), ctx, mm.group(0))
            if v is mm.group(0):
                return v
            return "" if v is None else (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v))
        return _ANY_EXPR_RE.sub(sub, expr)
    return expr


def resolve(expr: Any, ctx: dict) -> Any:
    if isinstance(expr, str) and len(expr) > _EXPR_CHARS:
        raise ToolError(f"Expression too long (cap {_EXPR_CHARS})")
    if isinstance(expr, dict):
        return {k: resolve(v, ctx) for k, v in expr.items()}
    if isinstance(expr, list):
        return [resolve(v, ctx) for v in expr]
    return _resolve_one(expr, ctx)


def _cmp(left: Any, op: str, right: Any) -> bool:
    if op == "empty":
        return left is None or left == "" or left == [] or left == {}
    try:
        if op == "eq":
            return left == right
        if op == "ne":
            return left != right
        if op in ("gt", "lt"):
            l, r = float(left), float(right)
            return l > r if op == "gt" else l < r
    except (TypeError, ValueError):
        return False
    if op == "contains":
        try:
            return str(right).lower() in str(left).lower()
        except Exception:
            return False
    return False


def _as_dt(v: Any) -> "datetime | None":
    """A date for before/after: ISO text, a unix number, or 'now'."""
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v
    try:
        if isinstance(v, (int, float)) or (isinstance(v, str) and re.fullmatch(r"\d{9,11}(\.\d+)?", v.strip())):
            return datetime.fromtimestamp(float(v))
        t = str(v).strip()
        if t.lower() == "now":
            return datetime.now()
        d = datetime.fromisoformat(t.replace("Z", "+00:00"))
        return d.replace(tzinfo=None) if d.tzinfo else d
    except (TypeError, ValueError, OverflowError):
        return None


def _num(v: Any) -> float:
    return float(str(v).replace(",", "").strip()) if isinstance(v, str) else float(v)


def _one(left: Any, op: str, right: Any, ci: bool) -> bool:
    """One filter condition. Never raises: a value that cannot be compared is simply False (honest, not an error)."""
    def txt(x: Any) -> str:
        t = "" if x is None else (json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list)) else str(x))
        return t.lower() if ci else t
    try:
        if op == "exists":
            return left is not None
        if op == "not_exists":
            return left is None
        if op == "empty":
            return left is None or left == "" or left == [] or left == {}
        if op == "not_empty":
            return not (left is None or left == "" or left == [] or left == {})
        if op == "is_true":
            return left is True or txt(left).lower() in ("true", "yes", "1")
        if op == "is_false":
            return left is False or txt(left).lower() in ("false", "no", "0", "")
        if op in ("eq", "ne"):
            if isinstance(left, (int, float)) and not isinstance(left, bool) or isinstance(right, (int, float)) and not isinstance(right, bool):
                try:
                    same = _num(left) == _num(right)
                except (TypeError, ValueError):
                    same = txt(left) == txt(right)
            else:
                same = left == right if not ci else txt(left) == txt(right)
            return same if op == "eq" else not same
        if op in ("contains", "not_contains"):
            if isinstance(left, list):
                hit = any(txt(x) == txt(right) for x in left)
            else:
                hit = txt(right) in txt(left)
            return hit if op == "contains" else not hit
        if op == "starts_with":
            return txt(left).startswith(txt(right))
        if op == "ends_with":
            return txt(left).endswith(txt(right))
        if op == "matches":
            return re.search(str(right or ""), "" if left is None else str(left), re.I if ci else 0) is not None
        if op in ("gt", "gte", "lt", "lte"):
            l, r = _num(left), _num(right)
            return {"gt": l > r, "gte": l >= r, "lt": l < r, "lte": l <= r}[op]
        if op == "between":
            lo, hi = right
            return _num(lo) <= _num(left) <= _num(hi)
        if op in ("before", "after"):
            l, r = _as_dt(left), _as_dt(right)
            if l is None or r is None:
                return False
            return l < r if op == "before" else l > r
        if op in ("in", "not_in"):
            pool = right if isinstance(right, list) else [x.strip() for x in str(right or "").split(",")]
            hit = any(txt(left) == txt(x) for x in pool)
            return hit if op == "in" else not hit
        if op in ("length_eq", "length_gt", "length_lt"):
            n = len(left) if isinstance(left, (list, dict, str)) else 0
            r = int(_num(right))
            return {"length_eq": n == r, "length_gt": n > r, "length_lt": n < r}[op]
    except (TypeError, ValueError, re.error, ZeroDivisionError):
        return False
    return False


def eval_filter(f: Any, ctx: dict, depth: int = 0) -> bool:
    """v0.999.87: evaluate a validated filter against the run's context. Values resolve through the same safe
    {{path}} resolver as every step — never eval()."""
    if depth > _FILTER_DEPTH or not isinstance(f, dict):
        return False
    if "all" in f:
        return all(eval_filter(x, ctx, depth + 1) for x in (f.get("all") or []))
    if "any" in f:
        return any(eval_filter(x, ctx, depth + 1) for x in (f.get("any") or []))
    return _one(resolve(f.get("left"), ctx), str(f.get("op") or ""), resolve(f.get("right"), ctx), bool(f.get("ci")))


# ---------------------------------------------------------------- summaries (v0.512, the Dify WorkflowRunSummary idea)

def _summary(run: dict, steps_total: int, err: str, acc: dict | None = None) -> dict[str, Any]:
    """The one honest paragraph about a finished run: what it did, where it stopped, what it cost.
    The cost line comes from usage.run_meter (v0.476) — whatever model calls the run's steps made."""
    logs = run.get("steps_log") or []
    s: dict[str, Any] = {"steps_total": int(steps_total), "steps_ran": int(run.get("cursor") or 0),
                         "parks": sum(1 for e in logs if e.get("status") in ("sleeping", "waiting_approval")),
                         "tries": int(run.get("tries") or 0),
                         # v0.999.254 MAKE PARITY: Make's operations - every step that ran, inner steps too
                         "operations": sum(1 for e in logs if e.get("id") != "..." and e.get("status") not in
                                           ("sleeping", "waiting_approval", "retry_wait")),
                         "wall_ms": int((time.time() - float(run.get("started_at") or time.time())) * 1000)}
    if err:
        s["fail_error"] = str(err)[:200]
    cost = {"usd": round(float((acc or {}).get("usd") or 0.0), 5), "calls": int((acc or {}).get("calls") or 0),
            "tok_in": int((acc or {}).get("tok_in") or 0), "tok_out": int((acc or {}).get("tok_out") or 0)}
    if cost["calls"]:
        try:
            from .. import usage as U
            cost["inr"] = round(cost["usd"] * U.usd_inr(), 2)
        except Exception:
            pass
    s["cost"] = cost
    return s


def _finish(tenant_id: str, run_id: str, run: dict, steps_total: int, status: str, err: str, acc: dict | None = None,
            **extra) -> None:
    """One honest end: status + summary written together (the fail path never loses its log — the v0.502 lesson)."""
    from ..config import get_settings
    s = get_settings()
    fields: dict[str, Any] = {"status": status, "pause_reason": None, **extra}
    if getattr(s, "dhara_summaries_enabled", True):
        fields["summary"] = json.dumps(_summary(run, steps_total, err, acc), ensure_ascii=False)
    if not update_run(tenant_id, run_id, _keep_stop=(status != "stopped"), **fields):
        run["status"] = "stopped"           # v0.999.253: a Stop that came while the last step ran stays a stop


# --------------------------------------------------------------------------- engine

def _flat_steps(steps: list) -> list[dict]:
    return [s for s in steps if isinstance(s, dict)]


def _log_step(run: dict, step_id: str, typ: str, status: str, ms: int, output: Any = None, error: str = "",
              version: int | None = None) -> None:
    entry = {"id": step_id, "type": typ, "status": status, "ms": ms, "at": time.strftime("%H:%M:%S")}
    if version is not None:            # v0.512: the step-type version that REALLY executed (Dify's node_version idea)
        entry["v"] = int(version)
    if error:
        entry["error"] = error[:400]
    if (run.get("context") or {}).get("_confidential"):    # v0.999.254 Make: keep data confidential
        output = None
        entry["hidden"] = True
    if output is not None:
        try:
            text = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
        except Exception:
            text = str(output)
        entry["output"] = text[:_STEP_LOG_SNIPPET]
    run["steps_log"].append(entry)


def _save_checkpoint(tenant_id: str, run: dict) -> None:
    seg = (run.get("context") or {}).get("_seg")    # v0.999.239 the run's working time (waits do not count)
    if isinstance(seg, list) and len(seg) == 2:
        run["context"]["_active_s"] = float(seg[1]) + max(0.0, time.time() - float(seg[0]))
    if not update_run(tenant_id, run["id"], _keep_stop=True, cursor=run["cursor"], context=run["context"],
                      steps_log=run["steps_log"], status=run["status"], error=run.get("error") or "",
                      next_wake_at=run.get("next_wake_at"), pause_reason=run.get("pause_reason")):
        # she pressed Stop while a step ran: keep 'stopped', but keep the log of what did run
        update_run(tenant_id, run["id"], steps_log=run["steps_log"], context=run["context"])
        run["status"] = "stopped"


def _runs_tell(tenant_id: str, where: str, args: tuple, line: str) -> None:
    """wave 10: tell her about runs a bulk UPDATE is about to fail (approval waited out, tries used up) - they used to go
    'failed' in silence. `line` gets {name}."""
    try:
        con = _con(tenant_id)
        try:
            rows = con.execute("SELECT r.id, r.wf_name, w.conversation_id FROM runs r LEFT JOIN workflows w "
                               "ON w.id = r.workflow_id WHERE " + where, args).fetchall()
        finally:
            con.close()
        for rid, name, conv in rows:
            _notify(conv or "", line.format(name=name or "workflow", run=rid))
    except Exception:   # noqa: BLE001
        pass


def _notify(conv: str, text: str) -> None:
    try:
        from .. import events
        events.notify(conv, text)
    except Exception:
        pass


def _due_park(tenant_id: str, run: dict, run_id: str, note: str) -> dict:
    _notify(run.get("conversation_id", ""), note)
    _save_checkpoint(tenant_id, run)
    _RUNNING.discard(f"{tenant_id}:{run_id}")
    return run


def _pruned(ctx: dict, sid: str) -> None:
    """A top-level step finished: forget the done marks and decisions of the steps inside it."""
    pre = f"/{sid}"
    inside = lambda k: k.startswith(pre) and k[len(pre):len(pre) + 1] in (":", "#", "@", "/")
    if isinstance(ctx.get("_done"), list):
        ctx["_done"] = [m for m in ctx["_done"] if not inside(m)]
    for key in ("_dec", "_subs"):
        if isinstance(ctx.get(key), dict):
            ctx[key] = {k: v for k, v in ctx[key].items() if not inside(k)}


def _keep_going(tenant_id: str, run_id: str, ctx: dict) -> str:
    """Inside a long branch or loop: save progress every few seconds (a restart picks up from here) and notice
    a stop she asked for. Returns an error word or ''."""
    dl = ctx.get("_deadline")
    if dl and time.time() > float(dl):
        return "the run passed its time limit"
    if not run_id or run_id == "step-test" or time.time() - float(ctx.get("_saved_at") or 0) < 3:
        return ""
    ctx["_saved_at"] = time.time()
    try:
        r = get_run(tenant_id, run_id)
        if r is not None and r.get("status") == "stopped":
            return "__HALT__"
        if r is not None:
            update_run(tenant_id, run_id, context=ctx)
    except Exception:   # noqa: BLE001  (saving is a help, never a reason to fail)
        pass
    return ""


_SUBLOG_CAP = 60      # v0.999.253: steps inside branches / loops kept in the run log per top-level step


def _where(scope: str) -> str:
    """The path of branches / ways / loop rounds a step sits in, in words ('big: if yes > each: round 2')."""
    out = []
    for part in [p for p in str(scope or "").split("/") if p]:
        m = re.match(r"^([^:#@]+)(?::(then|else)|#(\d+)|@(\d+))?$", part)
        if not m:
            out.append(part)
            continue
        sid, br, way, rnd = m.groups()
        if br:
            out.append(f"{sid}: if {'yes' if br == 'then' else 'no'}")
        elif way is not None:
            out.append(f"{sid}: way {int(way) + 1}")
        elif rnd is not None:
            out.append(f"{sid}: round {int(rnd) + 1}")
        else:
            out.append(sid)
    return " > ".join(out)


def _note_inner(ctx: dict, sub: dict, scope: str, status: str, ms: int, output: Any = None, error: str = "") -> None:
    """v0.999.253 ROUTE CHECK: a step inside a branch or loop leaves a line in the run's step log too (they were
    invisible). Kept in ctx['_sublog'] until the top-level step is logged; capped, errors always kept."""
    if not isinstance(ctx, dict) or ctx.get("_no_sublog"):
        return
    lg = ctx.setdefault("_sublog", [])
    if not isinstance(lg, list):
        return
    if len(lg) >= _SUBLOG_CAP and status == "ok":
        ctx["_sublog_more"] = int(ctx.get("_sublog_more") or 0) + 1
        return
    if len(lg) >= _SUBLOG_CAP * 2:
        ctx["_sublog_more"] = int(ctx.get("_sublog_more") or 0) + 1
        return
    tmp = {"steps_log": [], "context": {"_confidential": ctx.get("_confidential")}}
    _log_step(tmp, str(sub.get("id", "?")), str(sub.get("type", "?")), status, ms, output=output, error=error,
              version=int(sub.get("v") or 1))
    entry = tmp["steps_log"][0]
    entry["in"] = _where(scope)
    lg.append(entry)


def _flush_inner(run: dict) -> None:
    """Move the inner-step lines into the run log, just before the top-level step's own line."""
    ctx = run.get("context") or {}
    lg = ctx.pop("_sublog", None)
    more = int(ctx.pop("_sublog_more", 0) or 0)
    if isinstance(lg, list) and lg:
        run["steps_log"].extend(lg)
    if more:
        run["steps_log"].append({"id": "...", "type": "note", "status": "ok", "ms": 0,
                                 "at": time.strftime("%H:%M:%S"), "in": "...",
                                 "output": f"{more} more inner steps not listed"})


async def _run_handler(tenant_id: str, conv: str, step: dict, oe: dict, ctx: dict, run_id: str, err: str,
                       scope: str = "") -> tuple[bool, str]:
    """v0.999.254 MAKE PARITY: an error handler route - the steps on a step's on_error run first, with the error in
    {{error.message}} / {{error.step}}, then its directive decides. A handler that fails itself ends the run."""
    hs = oe.get("steps") if isinstance(oe, dict) else None
    if not hs:
        return True, ""
    hscope = f"{scope}/{step.get('id')}!err"
    ctx["_done"] = [m for m in (ctx.get("_done") or []) if not str(m).startswith(hscope + "/")]
    prev = ctx.get("error")
    ctx["error"] = {"step": str(step.get("id")), "type": str(step.get("type")), "message": str(err)[:800]}
    try:
        ok, herr = await _exec_sublist(tenant_id, conv, hs, ctx, run_id, False, scope=hscope)
    finally:
        if prev is None:
            ctx.pop("error", None)
        else:
            ctx["error"] = prev
    if not ok:
        return False, f"the error handler of '{step.get('id')}' failed too: {herr}"
    return True, ""


def _rollback_stores(tenant_id: str, ctx: dict) -> int:
    """Make's Rollback: take back this run's data store writes. The rest (a sent message) cannot be undone."""
    undo = ctx.pop("_store_undo", None) or []
    if not undo:
        return 0
    try:
        from ..route import store as DS
        return DS.undo_all(tenant_id, undo)
    except Exception:   # noqa: BLE001
        return 0


async def _exec_sublist(tenant_id: str, conv: str, sublist: list, ctx: dict, run_id: str,
                        soft_parent: bool, scope: str = "") -> tuple[bool, str]:
    """Condition/loop/route bodies: run their steps inline (atomic with the parent step). Returns (ok, error).
    v0.999.87: a step's own on_error ignore / resume is handled here; any other on_error rides up to the
    top-level step (ctx['_sub_on_error']).
    v0.999.239 ROUTE R4: every finished step leaves a done mark under its scope (the path of the branches and
    loop rounds above it), so a pause anywhere inside (a wait, an approval, a sub-route still running) parks the
    whole run and the resume - or a retry - picks up at the same step; a finished step never runs twice. A
    pause comes back as (True, signal)."""
    done = ctx.setdefault("_done", [])
    for sub in _flat_steps(sublist):
        mark = f"{scope}/{sub.get('id')}"
        if mark in done:
            continue
        why = _keep_going(tenant_id, run_id, ctx)
        if why == "__HALT__":
            return True, "__HALT__"
        if why:
            return False, why
        t_in = time.time()
        ok, out, err = await _exec_one(tenant_id, conv, sub, ctx, run_id, scope=scope)
        ms_in = int((time.time() - t_in) * 1000)
        if err == "__STOP__":           # a filter inside a branch closes just that branch (or loop round)
            _note_inner(ctx, sub, scope, "filtered", ms_in)
            return True, "__STOP__"
        if err in _SIGNALS:
            if err == "__PARK__" and ctx.pop("_park_done", False):
                done.append(mark)       # the wait IS this step doing its job: the resume goes on after it
            elif err == "__APPROVE__" and sub.get("type") == "approval":
                ctx["_wait_mark"] = mark
                ctx["_wait_q"] = str(resolve(sub.get("question") or "", ctx))[:400]
            if err in ("__PARK__", "__APPROVE__"):
                _note_inner(ctx, sub, scope, "waiting_approval" if err == "__APPROVE__" else "sleeping", ms_in)
            return True, err
        if not ok:
            oe = sub.get("on_error") or {}
            if oe.get("steps"):                          # v0.999.254: the handler route runs first
                h_ok, h_err = await _run_handler(tenant_id, conv, sub, oe, ctx, run_id, err, scope)
                if not h_ok:
                    _note_inner(ctx, sub, scope, "error", ms_in, error=err)
                    return False, h_err
                oe = {**oe, "_handled": True}
            if oe.get("do") == "ignore":
                ok = True
            elif oe.get("do") == "resume":
                ctx["steps"][str(sub.get("id"))] = {"output": resolve(oe.get("value"), ctx)}
                ok = True
            elif soft_parent or sub.get("soft"):
                _note_inner(ctx, sub, scope, "error", ms_in, error=err)
                done.append(mark)
                continue
            else:
                _note_inner(ctx, sub, scope, "error", ms_in, error=err)
                if oe:
                    ctx["_sub_on_error"] = {**oe, "step": str(sub.get("id"))}
                return False, f"step '{sub.get('id')}' ({sub.get('type')}): {err}"
            _note_inner(ctx, sub, scope, "ignored" if oe.get("do") == "ignore" else "resumed", ms_in)
            done.append(mark)
            continue
        if ok:
            _note_inner(ctx, sub, scope, "ok", ms_in, output=out)
            done.append(mark)
    return True, ""


async def _exec_one(tenant_id: str, conv: str, step: dict, ctx: dict, run_id: str,
                    scope: str = "") -> tuple[bool, Any, str]:
    """One step. Returns (ok, output, error). ctx mutates: ctx['steps'][id]['output'] = output.
    scope = the path of the branches / loop rounds this step sits in ('' at the top)."""
    from ..config import get_settings
    s = get_settings()
    sid, typ = str(step.get("id")), str(step.get("type"))
    t0 = time.time()
    # v0.999.234 ROUTE R2: in a test run from the editor, a step with pinned data uses it instead of running
    # (her pinned output; never on a real run - only the editor's test puts _pins in the context)
    pins = ctx.get("_pins")
    if isinstance(pins, dict) and sid in pins and typ not in ("condition", "router", "loop", "filter", "approval", "wait",
                                                              "stop", "respond"):
        ctx.setdefault("steps", {})[sid] = {"output": pins[sid]}
        return True, pins[sid], ""
    base = f"{scope}/{sid}"
    dec = ctx.setdefault("_dec", {})
    done = ctx.setdefault("_done", [])
    try:
        if typ == "tool":
            from .tools import HANDLERS
            name = str(step.get("name") or "")
            if name not in HANDLERS:
                return False, None, f"tool '{name}' is not in the registry"
            args = resolve(step.get("args") or {}, ctx)
            if not isinstance(args, dict):
                return False, None, "tool args must be an object"
            tool_ctx = Ctx(tenant_id=tenant_id, conversation_id=conv, actor="routine")
            out = await HANDLERS[name](tool_ctx, **args)
            ctx["steps"][sid] = {"output": out}
            return True, out, ""
        if typ == "code":
            from ..pylab import service as PL
            code = str(resolve(step.get("code") or "", ctx))
            res = await asyncio.to_thread(PL.run, tenant_id, code, None, None, conv, 60)
            ctx["steps"][sid] = {"output": res}
            if isinstance(res, dict) and res.get("ok") is False:   # v0.999.128: a failed program is a failed step
                why = "the code took too long" if res.get("timed_out") else (res.get("error") or "the code did not run")
                return False, res, str(why)[:300]
            return True, res, ""
        if typ == "condition":
            if base in dec:                              # v0.999.239 a resumed branch takes the same way
                passed = bool(dec[base])
            elif step.get("filter") is not None:         # v0.999.87 the full filter language
                passed = eval_filter(step["filter"], ctx)
            else:
                passed = _cmp(resolve(step.get("left"), ctx), str(step.get("op")), resolve(step.get("right"), ctx))
            dec[base] = bool(passed)
            branch = step.get("then") if passed else step.get("else")
            if not isinstance(branch, list):
                return True, {"branch": "skipped (no steps)"}, ""
            ok, err = await _exec_sublist(tenant_id, conv, branch, ctx, run_id, bool(step.get("soft")),
                                          scope=base + (":then" if passed else ":else"))
            if not ok:
                return False, None, err
            if err in _SIGNALS:
                return True, None, err
            ctx["steps"][sid] = {"output": {"branch": "then" if passed else "else"}}
            return True, ctx["steps"][sid]["output"], ""
        if typ == "filter":
            passed = eval_filter(step.get("filter"), ctx)
            ctx["steps"][sid] = {"output": {"passed": passed}}
            return True, {"passed": passed}, "" if passed else "__STOP__"
        if typ == "router":
            # Every route whose filter passes runs, in order (a route without a filter always runs); the
            # fallback runs only when no filtered route passed. Each route is atomic with the router step.
            # v0.999.239: the ways are decided once (a resumed router takes the same ways); a finished way
            # never runs again when the router is resumed or retried.
            routes = step.get("routes") or []
            if base in dec and isinstance(dec[base], list):
                plan = dec[base]
            elif step.get("ai"):                         # v0.999.243 ROUTE R6: the AI reads a text and picks one way
                from ..route import aistep as AS
                try:
                    pick = await AS.choose(step, ctx, resolve)
                except AS.AIError as e:
                    return False, None, str(e)[:300]
                labels = [str(r.get("label") or f"Way {i + 1}") for i, r in enumerate(routes)]
                plan = [labels.index(pick)] if pick in labels else (
                    ["fallback"] if isinstance(step.get("fallback"), list) and step.get("fallback") else [])
                dec[base] = plan
            else:
                plan, matched = [], False
                for i, rt in enumerate(routes):
                    has_filter = rt.get("filter") is not None
                    if has_filter and not eval_filter(rt["filter"], ctx):
                        continue
                    matched = matched or has_filter
                    plan.append(i)
                if not matched and isinstance(step.get("fallback"), list) and step.get("fallback"):
                    plan.append("fallback")
                dec[base] = plan
            taken: list[str] = []
            for i in plan:
                fb = i == "fallback"
                if not fb and not (isinstance(i, int) and 0 <= i < len(routes)):
                    continue
                label = "fallback" if fb else str(routes[i].get("label") or f"route {i + 1}")
                rmark = f"{base}#{i}"
                if rmark not in done:
                    ok, err = await _exec_sublist(tenant_id, conv, (step.get("fallback") if fb else routes[i].get("steps")) or [],
                                                  ctx, run_id, bool(step.get("soft")), scope=rmark)
                    if not ok:
                        return False, None, (f"fallback route: {err}" if fb else f"route '{label}': {err}")
                    if err in _SIGNALS:
                        return True, None, err
                    done.append(rmark)
                taken.append(label)
            why = (ctx.get("_ai_why") or {}).pop(sid, None)
            ctx["steps"][sid] = {"output": {"routes": taken, **({"why": why} if why else {})}}
            return True, ctx["steps"][sid]["output"], ""
        if typ == "loop":
            if base in dec and isinstance(dec[base], list):
                items = dec[base]                        # v0.999.239 a resumed loop goes on with the same list
            elif isinstance(step.get("repeat"), dict):   # v0.999.254 Make's Repeater: i = start, start+step, ...
                rp = resolve(step["repeat"], ctx)
                try:
                    n_, a_, d_ = int(rp.get("times")), int(rp.get("start") if rp.get("start") not in (None, "") else 1), \
                        int(rp.get("step") if rp.get("step") not in (None, "") else 1)
                except (TypeError, ValueError):
                    return False, None, "repeat times / start / step did not give whole numbers"
                if not 0 <= n_ <= _REPEAT_MAX:
                    return False, None, f"repeat can go 0 to {_REPEAT_MAX} times (got {n_})"
                items = [a_ + d_ * k for k in range(n_)]
                dec[base] = items
            else:
                items = resolve(step.get("items"), ctx)
                if not isinstance(items, list):
                    return False, None, "the loop items did not give a list"
                cap = min(int(getattr(s, "dhara_loop_max", _LOOP_MAX)), _LOOP_HARD)
                if len(items) > cap:
                    return False, None, f"the list has {len(items)} items - a loop can go through up to {cap}"
                dec[base] = items
            coll_key = base + "~collect"                 # v0.999.254 Make's array / text aggregator over the rounds
            collected = ctx.setdefault("_dec", {}).setdefault(coll_key, []) if step.get("collect") is not None else None
            prev, name_as = ctx.get("item"), str(step.get("as") or "")
            count = 0
            for i, item in enumerate(items):
                imark = f"{base}@{i}"
                if imark in done:
                    count += 1
                    continue
                ctx["item"] = item
                if name_as:
                    ctx["vars"][name_as] = item
                ok, err = await _exec_sublist(tenant_id, conv, step.get("body") or [], ctx, run_id,
                                              bool(step.get("soft")), scope=imark)
                if not ok:
                    return False, None, err
                if err in _SIGNALS:
                    return True, None, err
                if collected is not None and err != "__STOP__":
                    try:
                        collected.append(resolve(step.get("collect"), ctx))
                    except ToolError:
                        collected.append(None)
                done.append(imark)
                count += 1
            ctx["item"] = prev                          # a loop inside a loop gives the outer item back
            outp: dict[str, Any] = {"iterations": count}
            if collected is not None:
                outp["results"] = list(collected)
                if step.get("join") is not None:          # the text aggregator: the results as one text
                    sep = str(resolve(step.get("join"), ctx)).replace("\\n", "\n")
                    outp["text"] = sep.join("" if x is None else (x if isinstance(x, str) else json.dumps(x, ensure_ascii=False))
                                            for x in collected)
                dec.pop(coll_key, None)
            ctx["steps"][sid] = {"output": outp}
            return True, ctx["steps"][sid]["output"], ""
        if typ == "wait":
            if str(step.get("for") or "") == "call":     # v0.999.239 wait until someone calls the resume link
                return _wait_call(step, ctx, sid, base, run_id)
            secs = _wait_secs(step, ctx)
            if secs > 5 and not step.get("_test_now"):
                run_ref = ctx.setdefault("_run", {})
                run_ref["next_wake_at"] = time.time() + secs
                ctx["_park_done"] = True                 # the wait IS the step doing its job
                ctx["_pause"] = "sleeping"
                return True, {"wait_s": secs}, "__PARK__"
            if secs > 0:
                await asyncio.sleep(min(secs, 5))
            return True, {"wait_s": secs}, ""
        if typ == "store":                               # v0.999.254 MAKE PARITY: data stores
            from ..route import store as DS
            try:
                out = await asyncio.to_thread(DS.run, tenant_id, step, ctx, resolve)
            except DS.StoreError as e:
                return False, None, str(e)[:300]
            ctx["steps"][sid] = {"output": out}
            return True, out, ""
        if typ == "var":                                 # v0.999.254 Make's Tools: variables and the increment function
            out = await asyncio.to_thread(_var_step, tenant_id, step, ctx)
            if isinstance(out, dict) and out.get("_error"):
                return False, None, out["_error"]
            ctx["steps"][sid] = {"output": out}
            return True, out, ""
        if typ == "ai":                                  # v0.999.243 ROUTE R6: summarise, classify, extract, agent ...
            from ..route import aistep as AS
            try:
                out = await AS.run(tenant_id, step, ctx, resolve, conv, run_id)
            except AS.AIError as e:
                return False, None, str(e)[:300]
            ctx["steps"][sid] = {"output": out}
            return True, out, ""
        if typ == "subroute":                            # v0.999.239 run another route
            return await _subroute(tenant_id, step, ctx, sid, base, run_id)
        if typ == "stop":                                # v0.999.239 end the run here, as an error or as done
            how = "done" if str(step.get("as") or "error") == "done" else "error"
            msg = str(resolve(step.get("message") or "", ctx) or "")[:500]
            ctx["_end"] = {"as": how, "message": msg, "step": sid}
            ctx["steps"][sid] = {"output": {"stopped": how, "message": msg}}
            return True, ctx["steps"][sid]["output"], "__END__"
        if typ == "respond":                             # v0.999.239 answer the webhook caller
            try:
                code = int(resolve(step.get("status", 200), ctx) or 200)
            except (TypeError, ValueError):
                return False, None, "the answer's status is not a number"
            if not 100 <= code <= 599:
                return False, None, "the answer's status must be 100-599"
            body = resolve(step.get("body"), ctx)
            try:
                size = len(json.dumps(body, ensure_ascii=False, default=str))
            except Exception:   # noqa: BLE001
                body, size = str(body), len(str(body))
            if size > _RESPOND_MAX:
                return False, None, f"the answer is too big ({size} characters; up to {_RESPOND_MAX})"
            ans = {"status": code, "body": body}
            if not ctx.get("_response"):                 # the first answer is the one the caller gets
                ctx["_response"] = ans
                if run_id and run_id != "step-test" and ctx.get("_caller_waits"):
                    _RESPONSES[run_id] = ans
                    try:
                        update_run(tenant_id, run_id, context=ctx)
                    except Exception:   # noqa: BLE001
                        pass
            ctx["steps"][sid] = {"output": {"answered": code}}
            return True, ctx["steps"][sid]["output"], ""
        if typ == "notify":
            n_max = _NOTIFY_MAX
            if ctx.get("notify", 0) >= n_max:
                return True, {"skipped": "notify cap"}, ""
            ctx["notify"] = ctx.get("notify", 0) + 1
            _notify(conv, str(resolve(step.get("text") or "", ctx))[:800])
            return True, {"sent": True}, ""
        if typ == "approval":
            return True, None, "__APPROVE__"
        if typ == "send":                                  # v0.999.278 SENDING: only once she allowed this route to send
            from ..route import send as SN
            return await SN.run(tenant_id, step, ctx, resolve, run_id)
        if typ == "data":                                  # v0.999.237 ROUTE R3: sort, dates, files, ...
            from . import dhara_data as DD
            try:
                out = await asyncio.to_thread(DD.run, tenant_id, step, ctx, resolve)
            except DD.ExprError as e:
                return False, None, str(e)[:300]
            ctx["steps"][sid] = {"output": out}
            return True, out, ""
        if typ == "set":
            ctx["vars"][str(step.get("name"))] = resolve(step.get("value"), ctx)
            return True, {"set": str(step.get("name"))}, ""
        if typ == "http":
            from ..route import http as HT
            try:
                body = await _http_step(tenant_id, step, ctx)
            except HT.HttpError as e:
                return False, None, str(e)[:300]
            fail = body.pop("_fail", None) if isinstance(body, dict) else None
            code = int((body or {}).get("status") or 0) if isinstance(body, dict) else 0
            if fail is None and code >= 400 and step.get("fail_on_error") is not False and \
                    str(step.get("fail_on_error")).lower() != "false":
                fail = f"the site answered {code}"
            ctx["steps"][sid] = {"output": body}
            if fail:             # v0.999.128: a refused / broken answer is a failed step (unless she turned that off)
                return False, body, fail
            return True, body, ""
        return False, None, f"unknown step type '{typ}'"
    except ToolError as e:
        return False, None, str(e)
    except Exception as e:
        return False, None, f"{type(e).__name__}: {e}"
    finally:
        _ = t0  # timing is taken by the caller for the log row


def _wait_call(step: dict, ctx: dict, sid: str, base: str, run_id: str) -> tuple[bool, Any, str]:
    """v0.999.239 ROUTE R4: park until someone calls the run's resume link ({{vars.resume_url}}) or the time
    runs out. The call's data becomes this step's output."""
    if run_id == "step-test":
        return True, {"would_wait": "for a call to the run's resume link"}, ""
    w = ctx.get("_call")
    if isinstance(w, dict) and w.get("mark") == base:
        if "body" in w:
            ctx.pop("_call", None)
            out = {"called": True, "body": w["body"]}
            ctx["steps"][sid] = {"output": out}
            return True, out, ""
        if time.time() >= float(w.get("until") or 0):
            ctx.pop("_call", None)
            if str(step.get("on_timeout") or "continue") == "fail":
                return False, None, "nobody called the resume link in time"
            out = {"called": False, "timed_out": True}
            ctx["steps"][sid] = {"output": out}
            return True, out, ""
    else:
        try:
            t = max(60, min(int(step.get("timeout_s") or 86400), _WAIT_MAX_S))
        except (TypeError, ValueError):
            t = 86400
        w = {"mark": base, "until": time.time() + t}
        ctx["_call"] = w
    ctx.setdefault("_run", {})["next_wake_at"] = float(w["until"])
    ctx["_pause"] = "waiting_call"
    return True, {"waiting_for_call": True}, "__PARK__"


def _resume_link(ctx: dict, run_id: str) -> None:
    """The run's resume link, made once per run: {{vars.resume_url}} (send it, then wait for a call)."""
    if ctx.get("_resume_h") or not run_id or run_id == "step-test":
        return
    from ..config import get_settings
    secret = secrets.token_urlsafe(18)
    ctx["_resume_h"] = hashlib.sha256(secret.encode()).hexdigest()
    root = str(getattr(get_settings(), "public_base_url", "") or "").rstrip("/")
    ctx.setdefault("vars", {})["resume_url"] = f"{root}/api/dhara/resume/{run_id}.{secret}"


def _has_call_wait(steps: list) -> bool:
    try:
        return any(st.get("type") == "wait" and str(st.get("for") or "") == "call" for st, _ in _walk_steps(steps))
    except ToolError:
        return False


def resume_call(token: str, body: Any) -> dict:
    """POST /api/dhara/resume/{run}.{secret}: the call a 'wait for a call' step waits for. Never raises."""
    rid, _, secret = str(token or "").partition(".")
    if not re.fullmatch(r"rn_[0-9a-f]{12}", rid) or not secret:
        return {"ok": False, "status": 404, "error": "This link is not valid"}
    root = Path("data") / "dhara"
    for p in sorted(root.glob("*/dhara.db")) if root.is_dir() else []:
        tenant = p.parent.name
        r = get_run(tenant, rid)
        if r is None:
            continue
        c = r.get("context") or {}
        if not hmac.compare_digest(str(c.get("_resume_h") or ""), hashlib.sha256(secret.encode()).hexdigest()):
            return {"ok": False, "status": 404, "error": "This link is not valid"}
        w = c.get("_call")
        if r.get("status") != "sleeping" or not isinstance(w, dict):
            return {"ok": False, "status": 409, "error": "This route is not waiting for a call now"}
        if "body" in w:
            return {"ok": False, "status": 409, "error": "This call was already received"}
        w["body"] = body
        con = _con(tenant)            # v0.999.253: only one caller wins (two calls at once both used to)
        try:
            cur = con.execute("UPDATE runs SET status = 'queued', next_wake_at = NULL, pause_reason = NULL, context = ?, "
                              "updated_at = ? WHERE id = ? AND status = 'sleeping'",
                              (json.dumps(c, ensure_ascii=False), time.time(), rid))
            con.commit()
            won = cur.rowcount > 0
        finally:
            con.close()
        if not won:
            return {"ok": False, "status": 409, "error": "This call was already received"}
        return {"ok": True, "status": 200, "run_id": rid, "tenant": tenant}
    return {"ok": False, "status": 404, "error": "This link is not valid"}


async def resume_call_and_go(token: str, body: Any) -> dict:
    out = await asyncio.to_thread(resume_call, token, body)
    if out.get("ok"):
        _start_now(out["tenant"], out["run_id"])
    out.pop("tenant", None)
    return out


def _start_now(tenant_id: str, run_id: str) -> bool:
    from ..config import get_settings
    if _claim(tenant_id, run_id, int(getattr(get_settings(), "dhara_tries", 3)) + 1):
        t = asyncio.ensure_future(execute_run(tenant_id, run_id))
        _TASKS.add(t)
        t.add_done_callback(lambda _t: _TASKS.discard(_t))
        return True
    return False


async def _subroute(tenant_id: str, step: dict, ctx: dict, sid: str, base: str, run_id: str) -> tuple[bool, Any, str]:
    """v0.999.239 ROUTE R4: run another of her routes with the data given. wait (the default) = this run goes
    on with the other route's result; if the other route pauses (a wait, an approval), this run waits too and
    looks again every 30 seconds. wait=false = start it and go straight on. Up to 3 deep, never a loop."""
    subs = ctx.setdefault("_subs", {})
    cid = subs.get(base)
    wait = step.get("wait", True) not in (False, "false", "no", 0)
    if not cid:
        name = str(resolve(step.get("route"), ctx) or "").strip().lower().replace(" ", "_")
        wf = get_workflow(tenant_id, name=name)
        if wf is None:
            return False, None, f"there is no route named '{name}'"
        chain = [str(x) for x in (ctx.get("_chain") or [])] + ([str(ctx["_route"])] if ctx.get("_route") else [])
        if wf["name"] in chain:
            return False, None, "a route cannot start itself (directly or through other routes)"
        depth = int(ctx.get("_depth") or 0) + 1
        if depth > _SUB_DEPTH:
            return False, None, f"sub-routes can go only {_SUB_DEPTH} deep"
        vars_ = resolve(step.get("vars") or {}, ctx)
        if isinstance(vars_, str):
            try:
                vars_ = json.loads(vars_)
            except ValueError:
                vars_ = None
        if not isinstance(vars_, dict):
            return False, None, "the data for the sub-route must be an object of name: value"
        cid = create_run(tenant_id, wf, vars_=vars_)
        c = get_run(tenant_id, cid)["context"]
        c.update({"_parent": run_id, "_depth": depth, "_chain": chain})
        if not wait:
            update_run(tenant_id, cid, context=c)
            out = {"run_id": cid, "route": wf["name"], "started": True}
            ctx["steps"][sid] = {"output": out}
            return True, out, ""
        subs[base] = cid
        update_run(tenant_id, cid, context=c, status="running")
        from ..config import get_settings
        await _execute_run(tenant_id, cid, get_settings(), {})
    child = get_run(tenant_id, cid)
    if child is None:
        subs.pop(base, None)
        return False, None, "the sub-route's run is gone"
    st = child.get("status")
    if st == "done":
        subs.pop(base, None)
        cc = child.get("context") or {}
        outs = [x.get("output") for x in (cc.get("steps") or {}).values() if isinstance(x, dict)]
        end = cc.get("_end") or {}
        out = {"run_id": cid, "route": child.get("wf_name"), "status": "done",
               "vars": {k: v for k, v in (cc.get("vars") or {}).items() if not str(k).startswith("_") and k != "resume_url"},
               "result": outs[-1] if outs else None}
        if end.get("message"):
            out["message"] = end["message"]
        ctx["steps"][sid] = {"output": out}
        return True, out, ""
    if st in ("failed", "stopped", "incomplete"):
        subs.pop(base, None)
        return False, None, f"the route '{child.get('wf_name')}' did not finish: {str(child.get('error') or st)[:300]}"
    ctx.setdefault("_run", {})["next_wake_at"] = time.time() + 30
    ctx["_pause"] = "waiting_subroute"
    return True, {"waiting_for": cid}, "__PARK__"


def _var_step(tenant_id: str, step: dict, ctx: dict) -> Any:
    """v0.999.254 MAKE PARITY - Make's Tools: Set multiple variables, Get variable(s), Increment function, and
    Update a custom variable (her route variable, kept between runs, read as {{env.NAME}})."""
    op = str(step.get("op"))
    vs = ctx.setdefault("vars", {})
    if op == "set_many":
        vals = step.get("values")
        if isinstance(vals, str):
            try:
                vals = json.loads(vals)
            except ValueError:
                return {"_error": "values must be an object of name: value"}
        out = {}
        for k, v in (vals or {}).items():
            if not _PATH_RE.match(str(k)):
                return {"_error": f"'{k}' is not a variable name (lowercase_with_underscores)"}
            out[str(k)] = vs[str(k)] = resolve(v, ctx)
        return out
    if op == "get":
        return vs.get(str(step.get("name")))
    if op == "get_many":
        names = step.get("names")
        names = names if isinstance(names, list) else [x.strip() for x in str(names or "").split(",") if x.strip()]
        return {str(n): vs.get(str(n)) for n in names}
    name = str(step.get("name"))
    if op == "increment":
        if str(step.get("reset") or "never") == "run":
            v = int(ctx.setdefault("_counters", {}).get(name) or 0) + 1
            ctx["_counters"][name] = v
        else:
            wf_id = str((ctx.get("run") or {}).get("route_id") or ctx.get("_route") or "")
            con = _con(tenant_id)
            try:
                con.execute("CREATE TABLE IF NOT EXISTS ds_counters (route_id TEXT, name TEXT, value INTEGER, "
                            "updated_at REAL, PRIMARY KEY (route_id, name))")
                con.execute("BEGIN IMMEDIATE")
                r = con.execute("SELECT value FROM ds_counters WHERE route_id = ? AND name = ?", (wf_id, name)).fetchone()
                v = int(r[0] if r is not None else 0) + 1
                con.execute("INSERT INTO ds_counters (route_id, name, value, updated_at) VALUES (?, ?, ?, ?) "
                            "ON CONFLICT(route_id, name) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                            (wf_id, name, v, time.time()))
                con.commit()
            finally:
                con.close()
        vs[name] = v
        return {"value": v}
    if op == "save":
        from ..route import workspace as WS
        val = resolve(step.get("value"), ctx)
        try:
            WS.set_variable(tenant_id, name.upper(), val, note="set by a route")
        except Exception as e:   # noqa: BLE001
            return {"_error": str(e)[:200]}
        ctx.setdefault("env", {})[name.upper()] = val
        return {"name": name.upper(), "value": val}
    return {"_error": "unknown variables step"}


async def _http_step(tenant_id: str, step: dict, ctx: dict) -> dict:
    """v0.999.254: the web request is route/http.py now (Make's HTTP app); this name stays the engine's one door."""
    from ..route import http as HT
    return await HT.run(tenant_id, step, ctx, resolve)


async def execute_run(tenant_id: str, run_id: str) -> None:
    """The whole run, from its checkpoint. Runs as a background task; the tick claims first.
    v0.512: the run carries its OWN cost meter (usage.run_meter, the v0.476 run-scoped shape) and
    binds feature="dhara" in the usage ledger, so its model calls are visible per run and per day."""
    from ..config import get_settings
    from .. import usage
    s = get_settings()
    key = f"{tenant_id}:{run_id}"
    _RUNNING.add(key)
    acc: dict = {}
    try:
        usage.bind(tenant=tenant_id, feature="dhara")
        with usage.run_meter(acc):
            await _execute_run(tenant_id, run_id, s, acc)
    except Exception as e:  # the lane never breaks the worker
        try:
            update_run(tenant_id, run_id, status="failed", error=f"{type(e).__name__}: {e}"[:800])
            _runs_tell(tenant_id, "r.id = ?", (run_id,),   # wave 10: a crashed run is told, never silent
                       'DHARA "{name}" stopped midway (internal error) - run {run}. Shall I run it again?')
        except Exception:
            pass
    finally:
        _RUNNING.discard(key)


async def _execute_run(tenant_id: str, run_id: str, s, acc: dict) -> None:
    key = f"{tenant_id}:{run_id}"
    _RUNNING.add(key)
    try:
        run = get_run(tenant_id, run_id)
        if run is None or run["status"] not in ("queued", "running"):
            return
        wf = get_workflow(tenant_id, wf_id=run["workflow_id"])
        if wf is None:
            _finish(tenant_id, run_id, run, 0, "failed", "workflow delete/gone", error="workflow delete/gone")
            return
        ctx = run["context"]
        ctx.setdefault("vars", {})
        ctx.setdefault("steps", {})
        run["cursor"] = int(run.get("cursor") or 0)
        run["status"] = "running"
        run["pause_reason"] = None
        run.setdefault("steps_log", [])
        if not run.get("started_at"):
            update_run(tenant_id, run_id, started_at=time.time())
        run["started_at"] = run["started_at"] or time.time()
        conv = wf.get("conversation_id") or ""
        run["conversation_id"] = conv
        steps = _flat_steps(wf["steps"])
        timeout_s = int(getattr(s, "dhara_run_timeout_s", 600))
        update_run(tenant_id, run_id, status="running")
        # v0.999.239 ROUTE R4: the time limit counts working time only (a wait of days does not use it up)
        used = float(ctx.get("_active_s") or 0)
        ctx["_seg"] = [time.time(), used]
        ctx["_deadline"] = time.time() + max(0.0, timeout_s - used)
        ctx["_tz"] = str((wf.get("settings") or {}).get("timezone") or "")
        ctx["_route"] = wf["name"]
        ctx["_confidential"] = bool((wf.get("settings") or {}).get("confidential"))
        # v0.999.254 MAKE PARITY: Make's system variables, read as {{run.id}}, {{run.route}}, {{run.started_at}} ...
        ctx["run"] = {"id": run_id, "route": wf["name"], "route_id": wf["id"], "trigger": wf.get("trigger_kind") or "",
                      "started_at": datetime.fromtimestamp(float(run["started_at"]), timezone.utc).isoformat(timespec="seconds"),
                      "attempt": int(run.get("tries") or 0) + 1, "test": bool(ctx.get("_pins") is not None or ctx.get("_test"))}
        try:                                     # v0.999.246 ROUTE R7: her variables, read as {{env.NAME}}
            from ..route import workspace as WS
            ctx["env"] = WS.env(tenant_id)
        except Exception:   # noqa: BLE001
            ctx["env"] = {}
        if _has_call_wait(wf["steps"]):
            _resume_link(ctx, run_id)
        child = bool(ctx.get("_parent"))
        err = ""
        while run["cursor"] < len(steps):
            if time.time() > float(ctx["_deadline"]):
                err = f"run wall-clock cap ({timeout_s}s of working time; waits do not count) passed — stopped"
                break
            if run["cursor"] and (get_run(tenant_id, run_id) or {}).get("status") == "stopped":
                return                                  # she stopped it between two steps
            step = steps[run["cursor"]]
            t0 = time.time()
            ok, out, serr = await _exec_one(tenant_id, conv, step, ctx, run_id)
            ms = int((time.time() - t0) * 1000)
            if serr == "__HALT__":
                return
            if serr == "__PARK__":
                done_now = bool(ctx.pop("_park_done", False))
                why = str(ctx.pop("_pause", "") or "sleeping")
                _flush_inner(run)
                _log_step(run, step["id"], step["type"], "sleeping", ms, output=out, version=int(step.get("v") or 1))
                run["status"] = "sleeping"
                run["pause_reason"] = why                 # v0.512: the typed pause reason (Dify's PauseReason idea)
                run["next_wake_at"] = ctx.get("_run", {}).get("next_wake_at")
                if done_now:            # a top-level wait IS the step doing its job; the wake resumes AFTER it
                    _pruned(ctx, step["id"])
                    run["cursor"] += 1
                _save_checkpoint(tenant_id, run)          # a pause inside a branch keeps the cursor: it resumes there
                return
            if serr == "__APPROVE__":
                _flush_inner(run)
                _log_step(run, step["id"], step["type"], "waiting_approval", ms, version=int(step.get("v") or 1))
                run["status"] = "waiting_approval"
                run["pause_reason"] = "waiting_approval"  # v0.512: typed, not implied
                _save_checkpoint(tenant_id, run)
                hrs = int(getattr(s, "dhara_approval_hours", 24))
                q = ctx.get("_wait_q") if ctx.get("_wait_mark") else str(resolve(step.get("question") or "", ctx))
                _notify(conv, f'DHARA "{wf["name"]}" (run {run_id}) is waiting: {str(q or "shall I go ahead?")} '
                              f'Reply "yes" in the chat (or "stop" to cancel) within {hrs} hours.')
                return
            if serr == "__END__":
                end = ctx.get("_end") or {}
                _flush_inner(run)
                _log_step(run, step["id"], step["type"], "stopped", ms, output=out, version=int(step.get("v") or 1))
                run["cursor"] = len(steps)
                if end.get("as") == "done":
                    _save_checkpoint(tenant_id, run)
                    _finish(tenant_id, run_id, run, len(steps), "done", "", acc)
                    if end.get("message") and not child:
                        _notify(conv, f'Route "{wf["name"]}" ended early (run {run_id}): {end["message"][:300]}')
                    _after_run(tenant_id, wf, "done", "", run_id)
                    return
                err = f"stopped by step '{end.get('step') or step['id']}': {end.get('message') or 'stop with an error'}"
                break
            if serr == "__STOP__":
                # v0.999.87 a filter step that did not pass: the run ends cleanly here (not an error)
                _flush_inner(run)
                _log_step(run, step["id"], step["type"], "filtered", ms, output=out, version=int(step.get("v") or 1))
                run["cursor"] = len(steps)
                _save_checkpoint(tenant_id, run)
                _finish(tenant_id, run_id, run, len(steps), "done", "", acc)
                _after_run(tenant_id, wf, "done", "", run_id)
                return
            _flush_inner(run)
            _log_step(run, step["id"], step["type"], "ok" if ok else "error", ms,
                      output=(out if ok and out is not None else None), error="" if ok else serr,
                      version=int(step.get("v") or 1))
            if ok:
                ctx.pop("_retries_" + str(step["id"]), None)
                _pruned(ctx, step["id"])
                run["cursor"] += 1
                if (wf.get("settings") or {}).get("auto_commit"):
                    ctx.pop("_store_undo", None)               # Make: commit after each module
            elif step.get("soft"):
                _pruned(ctx, step["id"])
                run["cursor"] += 1
            else:
                # v0.999.87 HOOLA ROUTE: the step's error directive decides (a step inside a route may carry its own)
                oe = ctx.pop("_sub_on_error", None) or step.get("on_error") or {}
                if oe.get("steps") and not oe.get("_handled"):     # v0.999.254: the handler route runs first
                    h_ok, h_err = await _run_handler(tenant_id, conv, step, oe, ctx, run_id, serr)
                    _flush_inner(run)
                    if not h_ok:
                        oe = {}
                        serr = h_err
                do = str(oe.get("do") or "")
                if do == "ignore":
                    run["steps_log"][-1]["status"] = "ignored"
                    _pruned(ctx, step["id"])
                    run["cursor"] += 1
                elif do == "resume":
                    ctx["steps"][str(oe.get("step") or step["id"])] = {"output": resolve(oe.get("value"), ctx)}
                    run["steps_log"][-1]["status"] = "resumed"
                    _pruned(ctx, step["id"])
                    run["cursor"] += 1
                elif do == "commit":
                    ctx.pop("_store_undo", None)               # v0.999.254: data store writes are kept
                    run["steps_log"][-1]["status"] = "committed"
                    run["cursor"] = len(steps)
                    _save_checkpoint(tenant_id, run)
                    _finish(tenant_id, run_id, run, len(steps), "done", "", acc,
                            error=f"ended early after an error (commit): {serr}"[:800])
                    _notify(conv, f'Route "{wf["name"]}" ended early after an error and kept what was done '
                                  f'(run {run_id}): {serr[:200]}')
                    _after_run(tenant_id, wf, "done", "", run_id)
                    return
                elif do == "break":
                    key_r = "_retries_" + str(step["id"])
                    used = int(ctx.get(key_r) or 0)
                    if used < int(oe.get("retries", 3)):
                        ctx[key_r] = used + 1
                        wait_s = int(oe.get("wait_min", 10)) * 60
                        run["steps_log"][-1]["status"] = "retry_wait"
                        run["status"] = "sleeping"
                        run["pause_reason"] = "retry"
                        run["next_wake_at"] = time.time() + wait_s
                        run["error"] = serr[:800]
                        _save_checkpoint(tenant_id, run)
                        update_run(tenant_id, run_id, tries=0)   # a retry wait is not a failed claim
                        return
                    err = f"step '{step['id']}' ({step['type']}): {serr}"
                    if not (wf.get("settings") or {}).get("keep_incomplete", True):
                        n_back = _rollback_stores(tenant_id, ctx)       # Make: no incomplete runs = a rollback
                        err += (f" (retries used; the run is not kept - {n_back} data store change"
                                f"{'s' if n_back != 1 else ''} taken back)")
                        break
                    run["status"] = "incomplete"
                    run["error"] = err
                    _save_checkpoint(tenant_id, run)
                    _finish(tenant_id, run_id, run, len(steps), "incomplete", err, acc, error=err[:800],
                            pause_reason="retries_used")
                    _notify(conv, f'Route "{wf["name"]}" could not finish after {used} retries, so the run is '
                                  f'kept in Incomplete runs (run {run_id}). Fix the cause, then retry it: {serr[:200]}')
                    _after_run(tenant_id, wf, "failed", err, run_id)
                    return
                else:
                    err = f"step '{step['id']}' ({step['type']}): {serr}"
                    if do == "rollback":
                        n_back = _rollback_stores(tenant_id, ctx)
                        err += (f" (rolled back: {n_back} data store change{'s' if n_back != 1 else ''} taken back; "
                                "steps outside Hoola, like a sent message, cannot be undone)")
                    break
            _save_checkpoint(tenant_id, run)
            if polite_s:
                await asyncio.sleep(polite_s)
        if run["cursor"] >= len(steps) and not err:
            _save_checkpoint(tenant_id, run)
            _finish(tenant_id, run_id, run, len(steps), "done", "", acc)
            if not child:                                  # a sub-route's result goes to the route that started it
                _notify(conv, f'DHARA "{wf["name"]}" is complete ({len(steps)} steps, run {run_id}).'
                        f'{" (from a missed schedule) " if run.get("missed") else ""}')
            _after_run(tenant_id, wf, "done", "", run_id)
        else:
            run["status"] = "failed"
            run["error"] = err
            _save_checkpoint(tenant_id, run)
            _finish(tenant_id, run_id, run, len(steps), "failed", err, acc, error=err[:800])
            _notify(conv, f'DHARA "{wf["name"]}" stopped: {err[:300]}')
            _after_run(tenant_id, wf, "failed", err, run_id)
    except Exception as e:  # the lane never breaks the worker
        try:
            update_run(tenant_id, run_id, status="failed", error=f"{type(e).__name__}: {e}"[:800])
        except Exception:
            pass
    finally:
        _RUNNING.discard(key)


def _after_run(tenant_id: str, wf: dict, status: str, err: str, run_id: str) -> None:
    """v0.999.87 HOOLA ROUTE, after every honest end: count failed runs in a row, switch the route OFF after
    settings.stop_after_errors of them (and say so once), and start the route's error route with the details.
    Never raises (the run's own result is already saved)."""
    try:                                   # v0.999.253: she stopped it while a step ran - not a done / failed run
        r_now = get_run(tenant_id, run_id) if run_id else None
        if r_now is not None and r_now.get("status") == "stopped":
            return
    except Exception:   # noqa: BLE001
        pass
    try:
        from ..route import runs as RU
        RU.tally(tenant_id, wf["id"], status, run_id)       # v0.999.248 R8 insights
    except Exception:   # noqa: BLE001
        pass
    try:
        st = dict(wf.get("settings") or {})
        con = _con(tenant_id)
        try:
            if status == "done":
                con.execute("UPDATE workflows SET consecutive_errors = 0 WHERE id = ?", (wf["id"],))
                con.commit()
                return
            con.execute("UPDATE workflows SET consecutive_errors = COALESCE(consecutive_errors, 0) + 1 WHERE id = ?",
                        (wf["id"],))
            row = con.execute("SELECT consecutive_errors, enabled FROM workflows WHERE id = ?", (wf["id"],)).fetchone()
            con.commit()
        finally:
            con.close()
        n = int(row["consecutive_errors"] or 0) if row else 0
        cap = int(st.get("stop_after_errors") or 0)
        if cap and n >= cap and row and row["enabled"] and wf.get("trigger_kind") != "manual":
            set_enabled(tenant_id, wf["id"], False)
            _notify(wf.get("conversation_id") or "",
                    f'Route "{wf["name"]}" was switched off after {n} failed runs in a row. Last error: {err[:200]} '
                    f'Fix the cause, then switch it on again.')
        er = str(st.get("error_route") or "").strip().lower()
        chain = 0
        try:                         # v0.999.253: error routes failing into each other stop after 3 hops
            prev = (get_run(tenant_id, run_id) or {}).get("context") or {}
            chain = int((prev.get("vars") or {}).get("_error_chain") or 0)
        except Exception:   # noqa: BLE001
            chain = 0
        if chain >= 3:
            return
        payload = {"failed_route": wf["name"], "failed_run": run_id, "error": str(err)[:500], "_error_chain": chain + 1}
        started = set()
        if er and er != wf["name"]:
            target = get_workflow(tenant_id, name=er)
            if target is not None and target.get("enabled") and not _over_daily_cap(tenant_id, target):
                create_run(tenant_id, target, vars_=payload)
                started.add(target["id"])
        from ..route import triggers as TR     # v0.999.240 routes started "when a route fails"
        for w in TR.error_watchers(tenant_id, wf):
            if w["id"] not in started and not _over_daily_cap(tenant_id, w):
                create_run(tenant_id, w, vars_=payload)
                started.add(w["id"])
    except Exception:   # noqa: BLE001
        pass


# --------------------------------------------------------------------------- claim + tick (crawl-jobs shape)

def _claim(tenant_id: str, run_id: str, tries_max: int, stale_s: int | None = None) -> bool:
    """Take a run to start it: queued / sleeping, or (v0.999.253) a 'running' run nobody has written for stale_s
    (cut by a restart or a crash; it used to stay 'running' for ever). Never one this process is running."""
    if f"{tenant_id}:{run_id}" in _RUNNING:
        return False
    con = _con(tenant_id)
    try:
        if stale_s is None:
            from ..config import get_settings
            stale_s = int(getattr(get_settings(), "dhara_stale_s", 180))
        cut = time.time() - max(30, int(stale_s))
        # v0.999.254 MAKE PARITY: 'process data in order' - one run of the route at a time, oldest first, and none
        # while one waits in Incomplete runs or on its own retry
        me = con.execute("SELECT r.workflow_id, r.created_at, w.settings FROM runs r LEFT JOIN workflows w "
                         "ON w.id = r.workflow_id WHERE r.id = ?", (run_id,)).fetchone()
        if me is not None and me["settings"]:
            try:
                in_order = bool(json.loads(me["settings"] or "{}").get("in_order"))
            except ValueError:
                in_order = False
            if in_order:
                busy = con.execute("SELECT 1 FROM runs WHERE workflow_id = ? AND id != ? AND ("
                                   "(status = 'running' AND updated_at >= ?) OR status = 'incomplete' OR "
                                   "(status = 'sleeping' AND pause_reason = 'retry') OR "
                                   "(status = 'queued' AND created_at < ?)) LIMIT 1",
                                   (me["workflow_id"], run_id, cut, me["created_at"])).fetchone()
                if busy is not None:
                    return False
        cur = con.execute("UPDATE runs SET tries = tries + 1, status = 'running', updated_at = ? "
                          "WHERE id = ? AND tries < ? AND (status IN ('queued','sleeping') OR "
                          "(status = 'running' AND updated_at < ?))",
                          (time.time(), run_id, int(tries_max), cut))
        con.commit()
        return cur.rowcount > 0
    finally:
        con.close()


def _claimants(tenant_id: str, stale_s: int) -> list[str]:
    con = _con(tenant_id)
    try:
        cut = time.time() - max(30, int(stale_s))
        rows = con.execute("SELECT id FROM runs WHERE (status = 'queued') OR "
                           "(status = 'running' AND updated_at < ?) ORDER BY created_at LIMIT 5",
                           (cut,)).fetchall()
        return [r["id"] for r in rows]
    finally:
        con.close()


def _scheduled_due(tenant_id: str) -> list[dict]:
    """Enabled scheduled workflows whose next_due_at has passed; advances next_due_at (fire-once)."""
    con = _con(tenant_id)
    out = []
    try:
        now_ = time.time()
        rows = con.execute("SELECT * FROM workflows WHERE enabled = 1 AND trigger_kind = 'schedule' "
                           "AND next_due_at IS NOT NULL AND next_due_at <= ? LIMIT 10", (now_,)).fetchall()
        for r in rows:
            wf = _wf_row(r)
            try:
                nxt = next_due(wf, from_ts=now_)
            except Exception:   # noqa: BLE001  v0.999.253: one broken schedule never stops the other routes
                con.execute("UPDATE workflows SET next_due_at = NULL WHERE id = ?", (wf["id"],))
                _notify(wf.get("conversation_id") or "", f'Route "{wf["name"]}" has a schedule Hoola cannot read, so '
                        'it will not start by itself. Open its start in the editor and set the time again.')
                continue
            missed = now_ - float(wf["next_due_at"]) > 3600
            con.execute("UPDATE workflows SET next_due_at = ? WHERE id = ?", (nxt, wf["id"]))   # None = no next time
            out.append((wf, missed))
        con.commit()
        return out
    finally:
        con.close()


_SCHED_KEYS = ("every_hours", "at", "every_minutes", "days", "monthdays", "dates", "once")


def _tzinfo(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(str(name)) if name else _IST
    except Exception:
        return _IST


def _hm(at: Any) -> tuple[int, int] | None:
    try:
        hh, mm = str(at).split(":")[:2]
        h, m = int(hh), int(mm)
        return (h, m) if 0 <= h < 24 and 0 <= m < 60 else None
    except Exception:
        return None


def _holiday_set(country: str):
    """The country's public holidays (python-holidays, MIT) or None when unknown / not installed."""
    if not country:
        return None
    try:
        import holidays as _h
        return _h.country_holidays(str(country).upper())
    except Exception:
        return None


def _in_quiet(t: datetime, quiet: dict | None) -> datetime | None:
    """If t falls inside quiet hours, the moment the quiet window ends; else None."""
    if not quiet:
        return None
    a, b = _hm(quiet.get("from")), _hm(quiet.get("to"))
    if not a or not b or a == b:
        return None
    mins, fa, tb = t.hour * 60 + t.minute, a[0] * 60 + a[1], b[0] * 60 + b[1]
    inside = (fa <= mins < tb) if fa < tb else (mins >= fa or mins < tb)
    if not inside:
        return None
    end = t.replace(hour=b[0], minute=b[1], second=0, microsecond=0)
    if end <= t:
        end += timedelta(days=1)
    return end


def next_due(wf: dict, from_ts: float | None = None) -> float | None:
    """When a scheduled workflow runs next. None = never again (a passed 'once' / no allowed day in 400 days).

    Legacy spec (v0.502, kept byte-for-byte in behaviour): {"every_hours": N, "at": ["HH:MM", ...]} in IST.
    v0.999.87 HOOLA ROUTE, for anyone anywhere: "timezone" (IANA, e.g. "Europe/London"; the route's settings
    timezone when the spec has none; IST only when neither says), "every_minutes" (>= 15), "days" ["mon".."sun"],
    "monthdays" [1..31], "dates" ["YYYY-MM-DD"], "once" "YYYY-MM-DDTHH:MM", "quiet" {"from":"21:00","to":"08:00"},
    "skip_holidays" "<country code>" (that country's public holidays), "end_date" "YYYY-MM-DD"."""
    if wf.get("trigger_kind") == "event":       # v0.999.240 an app event: the first look soon after saving
        return float(from_ts or time.time()) + 20
    spec = wf.get("trigger_spec") or {}
    settings = wf.get("settings") or {}
    if spec.get("start_date"):                   # v0.999.254 Make's advanced scheduling: not before this date
        try:
            st_d = datetime.fromisoformat(str(spec["start_date"])[:16])
            st_d = st_d.replace(tzinfo=_tzinfo(spec.get("timezone") or settings.get("timezone") or "")) \
                if st_d.tzinfo is None else st_d
            if float(from_ts or time.time()) < st_d.timestamp():
                from_ts = st_d.timestamp() - 1
        except (TypeError, ValueError):
            pass
    modern = any(k in spec for k in ("timezone", "every_minutes", "days", "monthdays", "dates", "once", "quiet",
                                      "skip_holidays", "end_date", "start_date")) or bool(settings.get("timezone"))
    if not modern:
        try:
            every_h = int(spec.get("every_hours") or 24)
        except Exception:
            every_h = 24
        every_h = max(1, min(every_h, 24 * 30))
        ats = spec.get("at") or []
        if not ats:
            return (from_ts or time.time()) + every_h * 3600
        now_i = datetime.fromtimestamp(from_ts or time.time(), _IST)
        cands: list[datetime] = []
        for at in ats:
            try:
                hh, mm = str(at).split(":")[:2]
                t = now_i.replace(hour=int(hh) % 24, minute=int(mm) % 60, second=0, microsecond=0)
                if t <= now_i:
                    t += timedelta(days=1)
                cands.append(t)
            except Exception:
                continue
        if not cands:
            return (from_ts or time.time()) + every_h * 3600
        return min(cands).timestamp()

    tz = _tzinfo(spec.get("timezone") or settings.get("timezone") or "")
    now_l = datetime.fromtimestamp(from_ts or time.time(), tz)
    quiet = spec.get("quiet") if isinstance(spec.get("quiet"), dict) else None
    hol = _holiday_set(spec.get("skip_holidays") or "")
    end_date = None
    try:
        end_date = datetime.fromisoformat(str(spec["end_date"])).date() if spec.get("end_date") else None
    except ValueError:
        end_date = None

    def allowed_day(d) -> bool:
        if end_date and d > end_date:
            return False
        if hol is not None and d in hol:
            return False
        if spec.get("days"):
            if _DAYS[d.weekday()] not in [str(x).lower()[:3] for x in spec["days"]]:
                return False
        if spec.get("monthdays"):
            if d.day not in [int(x) for x in spec["monthdays"] if str(x).isdigit()]:
                return False
        if spec.get("dates"):
            if d.isoformat() not in [str(x)[:10] for x in spec["dates"]]:
                return False
        return True

    def settle(t: datetime) -> datetime | None:
        """Push a candidate past quiet hours and onto an allowed day (bounded)."""
        for _ in range(400):
            q = _in_quiet(t, quiet)
            if q is not None:
                t = q
                continue
            if not allowed_day(t.date()):
                t = (t + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                continue
            return t
        return None

    if spec.get("once"):
        try:
            t = datetime.fromisoformat(str(spec["once"]))
            t = t.replace(tzinfo=tz) if t.tzinfo is None else t
        except ValueError:
            return None
        return t.timestamp() if t > now_l else None
    if spec.get("every_minutes"):
        mins = max(15, min(int(spec.get("every_minutes") or 60), 60 * 24 * 30))
        t = settle(now_l + timedelta(minutes=mins))
        return t.timestamp() if t else None
    ats = [x for x in (_hm(a) for a in (spec.get("at") or [])) if x] or ([(9, 0)] if (spec.get("days") or spec.get("monthdays") or spec.get("dates")) else [])
    if not ats:
        every_h = max(1, min(int(spec.get("every_hours") or 24), 24 * 30))
        t = settle(now_l + timedelta(hours=every_h))
        return t.timestamp() if t else None
    day0 = now_l.replace(hour=0, minute=0, second=0, microsecond=0)
    for k in range(0, 400):
        d = day0 + timedelta(days=k)
        if not allowed_day(d.date()):
            continue
        for h, m in sorted(ats):
            t = d.replace(hour=h, minute=m)
            if t <= now_l:
                continue
            q = _in_quiet(t, quiet)
            if q is not None:
                t = settle(q)
                if t is None:
                    return None
            if allowed_day(t.date()):
                return t.timestamp()
    return None


def validate_schedule(spec: dict, settings: dict | None = None) -> dict:
    """v0.999.87: hard-check a schedule spec; returns it normalised or raises ToolError with the first problem."""
    spec = dict(spec or {})
    if not any(spec.get(k) for k in _SCHED_KEYS):
        raise ToolError("Give a schedule one of: every_minutes (>= 15), every_hours, at ['HH:MM'], days ['mon'...], "
                        "monthdays [1..31], dates ['YYYY-MM-DD'] or once 'YYYY-MM-DDTHH:MM'")
    tzname = spec.get("timezone") or (settings or {}).get("timezone")
    if tzname:
        try:
            ZoneInfo(str(tzname))
        except Exception:
            raise ToolError(f"Unknown time zone '{tzname}' — use an IANA name like Europe/London or America/New_York")
    if spec.get("every_minutes") is not None:
        try:
            if int(spec["every_minutes"]) < 15:
                raise ToolError("every_minutes must be 15 or more (the fastest a schedule may run)")
        except (TypeError, ValueError):
            raise ToolError("every_minutes must be a whole number")
    if spec.get("every_hours") is not None:     # v0.999.253: '2h' used to break every route's schedule
        try:
            if not 1 <= int(spec["every_hours"]) <= 24 * 30:
                raise ToolError("every_hours must be 1 to 720")
        except (TypeError, ValueError):
            raise ToolError("every_hours must be a whole number of hours")
    for at in spec.get("at") or []:
        if _hm(at) is None:
            raise ToolError(f"Time '{at}' is not HH:MM (24-hour)")
    for dd in spec.get("days") or []:
        if str(dd).lower()[:3] not in _DAYS:
            raise ToolError(f"Day '{dd}' is not one of mon tue wed thu fri sat sun")
    for md in spec.get("monthdays") or []:
        if not str(md).isdigit() or not 1 <= int(md) <= 31:
            raise ToolError(f"Day of month '{md}' must be 1-31")
    if spec.get("start_date"):
        try:
            datetime.fromisoformat(str(spec["start_date"])[:16])
        except ValueError:
            raise ToolError("start_date must be YYYY-MM-DD (or YYYY-MM-DDTHH:MM)")
    for dt in list(spec.get("dates") or []) + ([spec["end_date"]] if spec.get("end_date") else []):
        try:
            datetime.fromisoformat(str(dt)[:10])
        except ValueError:
            raise ToolError(f"Date '{dt}' is not YYYY-MM-DD")
    if spec.get("once"):
        try:
            datetime.fromisoformat(str(spec["once"]))
        except ValueError:
            raise ToolError("once must be 'YYYY-MM-DDTHH:MM'")
    q = spec.get("quiet")
    if q is not None and (not isinstance(q, dict) or _hm(q.get("from")) is None or _hm(q.get("to")) is None):
        raise ToolError("quiet must be {from: 'HH:MM', to: 'HH:MM'}")
    if spec.get("skip_holidays"):
        if _holiday_set(spec["skip_holidays"]) is None:
            raise ToolError(f"No public-holiday calendar for country '{spec['skip_holidays']}' — use a 2-letter "
                            "country code like US, GB, DE, IN, BR")
        spec["skip_holidays"] = str(spec["skip_holidays"]).upper()
    return spec


def validate_settings(st: Any, tenant_id: str = "") -> dict:
    """v0.999.87 route-level settings: folder, timezone, stop_after_errors (1-20), error_route, runs_per_day."""
    if st in (None, ""):
        return {}
    if not isinstance(st, dict):
        raise ToolError("settings must be an object")
    out: dict[str, Any] = {}
    if st.get("folder"):
        out["folder"] = str(st["folder"]).strip()[:40]
    if st.get("timezone"):
        try:
            ZoneInfo(str(st["timezone"]))
        except Exception:
            raise ToolError(f"Unknown time zone '{st['timezone']}' — use an IANA name like Asia/Tokyo")
        out["timezone"] = str(st["timezone"])
    if st.get("stop_after_errors") not in (None, ""):
        try:
            out["stop_after_errors"] = max(1, min(int(st["stop_after_errors"]), 20))
        except (TypeError, ValueError):
            raise ToolError("stop_after_errors must be a number 1-20")
    if st.get("sends_per_day") not in (None, ""):    # v0.999.278 SENDING: messages a route may send a day
        try:
            out["sends_per_day"] = max(1, min(int(st["sends_per_day"]), 2000))
        except (TypeError, ValueError):
            raise ToolError("sends_per_day must be a number 1-2000")
    if st.get("runs_per_day") not in (None, ""):
        try:
            out["runs_per_day"] = max(1, min(int(st["runs_per_day"]), 10000))
        except (TypeError, ValueError):
            raise ToolError("runs_per_day must be a number 1-10000")
    if st.get("error_route"):
        er = str(st["error_route"]).strip().lower().replace(" ", "_")
        if not _PATH_RE.match(er):
            raise ToolError("error_route must be the name of another route")
        out["error_route"] = er
    if st.get("currency"):
        out["currency"] = str(st["currency"]).upper()[:3]
    if st.get("tags") not in (None, "", []):          # v0.999.246 ROUTE R7: tags to find routes by
        tags = st["tags"] if isinstance(st["tags"], list) else str(st["tags"]).split(",")
        tags = [str(x).strip().lower()[:30] for x in tags if str(x).strip()]
        if len(tags) > 10:
            raise ToolError("Up to 10 tags on a route")
        out["tags"] = list(dict.fromkeys(tags))
    for key, lo, hi, what in (("keep_runs_days", 1, 3650, "days to keep its runs"),    # v0.999.248 ROUTE R8
                              ("keep_runs", 1, 20000, "runs to keep"),
                              ("minutes_saved", 0, 1440, "minutes a run saves")):
        if st.get(key) not in (None, ""):
            try:
                v = float(st[key]) if key == "minutes_saved" else int(st[key])
            except (TypeError, ValueError):
                raise ToolError(f"{what} must be a number {lo}-{hi}")
            if not lo <= v <= hi:
                raise ToolError(f"{what} must be {lo}-{hi}")
            if v or key != "minutes_saved":
                out[key] = v
    if st.get("shared_with") not in (None, "", []):   # team members who may run it from their own Hoola
        ids = [str(x) for x in (st["shared_with"] if isinstance(st["shared_with"], list) else [st["shared_with"]])]
        if tenant_id:
            try:
                from ..employee import service as ES
                team = {m["id"] for m in ES.team(tenant_id)}
            except Exception:   # noqa: BLE001
                team = set(ids)
            bad = [i for i in ids if i not in team]
            if bad:
                raise ToolError("Share only with people in your team (AI Employees > Team)")
        out["shared_with"] = list(dict.fromkeys(ids))[:50]
    # v0.999.254 MAKE PARITY - Make's scenario settings: process data in order, keep data confidential, store
    # incomplete executions, commit after each module, webhook queue while off, IP restrictions
    for key in ("in_order", "confidential", "keep_incomplete", "auto_commit", "queue_when_off"):
        if st.get(key) not in (None, ""):
            v = st[key]
            out[key] = v if isinstance(v, bool) else str(v).strip().lower() in ("true", "yes", "1", "on")
    if st.get("queue_max") not in (None, ""):
        try:
            out["queue_max"] = max(1, min(int(st["queue_max"]), 10000))
        except (TypeError, ValueError):
            raise ToolError("queue_max must be a number 1-10000")
    if st.get("allow_ips") not in (None, "", []):
        import ipaddress
        ips = st["allow_ips"] if isinstance(st["allow_ips"], list) else re.split(r"[,\s]+", str(st["allow_ips"]))
        good = []
        for x in [str(i).strip() for i in ips if str(i).strip()][:50]:
            try:
                good.append(str(ipaddress.ip_network(x, strict=False)))
            except ValueError:
                raise ToolError(f"'{x}' is not an IP address or range (like 203.0.113.7 or 203.0.113.0/24)")
        out["allow_ips"] = good
    return out


def _runs_today(tenant_id: str, wf_id: str) -> int:
    con = _con(tenant_id)
    try:
        return int(con.execute("SELECT COUNT(*) FROM runs WHERE workflow_id = ? AND created_at >= ?",
                               (wf_id, time.time() - 86400)).fetchone()[0])
    finally:
        con.close()


def _over_daily_cap(tenant_id: str, wf: dict) -> bool:
    cap = int((wf.get("settings") or {}).get("runs_per_day") or 0)
    return bool(cap) and _runs_today(tenant_id, wf["id"]) >= cap


async def tick() -> int:
    """The worker slot (worker.dhara_jobs): enqueue due scheduled runs, wake sleepers, claim runs, forget old."""
    from ..config import get_settings
    s = get_settings()
    if not getattr(s, "dhara_enabled", True):
        return 0
    started = 0
    try:
        root = Path("data") / "dhara"
        tenants = sorted(p.parent.name for p in root.glob("*/dhara.db")) if root.is_dir() else []
    except Exception:
        tenants = []
    tries_max = int(getattr(s, "dhara_tries", 3))
    stale_s = int(getattr(s, "dhara_stale_s", 180))
    max_running = int(getattr(s, "dhara_max_running", 1))
    for tenant in tenants:
        try:
            for wf, missed in _scheduled_due(tenant):
                if _over_daily_cap(tenant, wf):      # v0.999.87 the route's own runs_per_day ceiling
                    continue
                rid = create_run(tenant, wf, missed=missed)
                started += 1
            from ..route import triggers as TR      # v0.999.240 app events: each due route looks for new items
            for wf in TR.events_due(tenant):
                t_ = asyncio.ensure_future(TR.poll(tenant, wf))
                _TASKS.add(t_)
                t_.add_done_callback(lambda _t: _TASKS.discard(_t))
            # wake sleepers whose time came (park them back to queued; the claim below starts them)
            con = _con(tenant)
            try:
                con.execute("UPDATE runs SET status = 'queued', next_wake_at = NULL, pause_reason = NULL, updated_at = ? "
                            "WHERE status = 'sleeping' AND next_wake_at IS NOT NULL AND next_wake_at <= ?",
                            (time.time(), time.time()))
                # expire approvals that waited too long
                cut = time.time() - int(getattr(s, "dhara_approval_hours", 24)) * 3600
                _runs_tell(tenant, "r.status = 'waiting_approval' AND r.updated_at < ?", (cut,),
                           'DHARA "{name}" stopped: the wait for your approval became too long (run {run}). '
                           'Run it again if you want.')
                con.execute("UPDATE runs SET status = 'failed', pause_reason = 'approval_expired', "
                            "error = 'the wait for approval ended (dhara_approval_hours passed)', updated_at = ? "
                            "WHERE status = 'waiting_approval' AND updated_at < ?", (time.time(), cut))
                con.commit()
            finally:
                con.close()
            running = len([k for k in _RUNNING if k.startswith(tenant + ":")])
            budget = max(0, max_running - running)
            for rid in _claimants(tenant, stale_s):
                if budget <= 0:
                    break
                if _claim(tenant, rid, tries_max, stale_s):
                    t = asyncio.ensure_future(execute_run(tenant, rid))
                    _TASKS.add(t)
                    t.add_done_callback(lambda _t: _TASKS.discard(_t))
                    budget -= 1
                    started += 1
            _runs_tell(tenant, "r.status = 'queued' AND r.tries >= ?", (int(tries_max),),
                       'DHARA "{name}" did not run even after several tries, so it was dropped (run {run}).')
            con = _con(tenant)
            try:
                con.execute("UPDATE runs SET status = 'failed', error = 'tries used up (dhara_tries) — run dropped', "
                            "updated_at = ? WHERE status = 'queued' AND tries >= ?", (time.time(), int(tries_max)))
                # v0.999.253: a run cut by restarts again and again ends honestly instead of 'running' for ever
                con.execute("UPDATE runs SET status = 'failed', error = 'the run was cut off (the server restarted) "
                            "too many times - run it again', updated_at = ? WHERE status = 'running' AND tries >= ? "
                            "AND updated_at < ?", (time.time(), int(tries_max), time.time() - max(30, int(stale_s))))
                con.commit()
            finally:
                con.close()
            forget_old_runs(tenant, int(getattr(s, "dhara_keep_runs_days", 30)))
        except Exception:
            continue
    return started


async def drain() -> None:
    if _TASKS:
        await asyncio.gather(*list(_TASKS), return_exceptions=True)


# --------------------------------------------------------------------------- webhook

def _ip_ok(ip: str, allow: list) -> bool:
    import ipaddress
    try:
        a = ipaddress.ip_address(str(ip or "").strip())
    except ValueError:
        return False
    for net in allow or []:
        try:
            if a in ipaddress.ip_network(str(net), strict=False):
                return True
        except ValueError:
            continue
    return False


def webhook_enqueue(token: str, body: dict, meta: dict | None = None) -> dict:
    """POST /api/dhara/hook/{token}. Returns an honest dict; never raises (route maps ok=False).
    v0.999.254 MAKE PARITY: calls that come faster than one per 6 s wait in the route's queue (Make's webhook queue,
    up to queue_max, default 667) and run in turn - none is lost; a route that is off keeps them when its setting
    queue_when_off is on; allow_ips limits who may call; the caller's headers, method and query ride along."""
    from ..config import get_settings
    s = get_settings()
    if not getattr(s, "dhara_enabled", True) or not getattr(s, "dhara_webhook_enabled", True):
        return {"ok": False, "status": 503, "error": "The DHARA webhook is off"}
    th = hashlib.sha256(str(token or "").encode()).hexdigest()
    root = Path("data") / "dhara"
    wf = None
    tenant = ""
    if root.is_dir():
        for p in sorted(root.glob("*/dhara.db")):
            t = p.parent.name
            hit = workflows_with_hash(t, th)
            if hit is not None and hit.get("trigger_kind") == "webhook" and (
                    hit.get("enabled", 0) or (hit.get("settings") or {}).get("queue_when_off")):
                wf, tenant = hit, t
                break
    if wf is None:
        return {"ok": False, "status": 401, "error": "token not found / workflow is off"}
    st = wf.get("settings") or {}
    meta = dict(meta or {})
    if st.get("allow_ips") and not _ip_ok(str(meta.get("ip") or ""), st["allow_ips"]):
        return {"ok": False, "status": 403, "error": "this address is not allowed to call the route"}
    vars0 = {"body": body}
    if meta:
        hdr = {str(k).lower(): str(v)[:2000] for k, v in (meta.get("headers") or {}).items()
               if str(k).lower() not in ("authorization", "cookie", "x-api-key", "proxy-authorization")}
        vars0["request"] = {"method": str(meta.get("method") or "POST"), "headers": hdr,
                            "query": dict(meta.get("query") or {}), "ip": str(meta.get("ip") or "")}
    off = not wf.get("enabled", 0)
    con = _con(tenant)
    try:
        last = con.execute("SELECT created_at FROM runs WHERE workflow_id = ? ORDER BY created_at DESC LIMIT 1",
                           (wf["id"],)).fetchone()
        q = con.execute("SELECT COUNT(*), MAX(next_wake_at) FROM runs WHERE workflow_id = ? AND status = 'sleeping' "
                        "AND pause_reason IN ('queue', 'queue_off')", (wf["id"],)).fetchone()
    finally:
        con.close()
    if _over_daily_cap(tenant, wf):
        return {"ok": False, "status": 429, "error": "this route reached its runs-per-day limit"}
    waiting, latest = int(q[0] or 0), float(q[1] or 0)
    soon = last is not None and time.time() - float(last["created_at"]) < _TOKEN_MIN_RATE_S
    if off or soon or waiting:
        if waiting >= int(st.get("queue_max") or 667):
            return {"ok": False, "status": 429, "error": f"the route's queue is full ({waiting} calls are waiting)"}
        if off:                                   # kept until she switches the route on
            rid = create_run(tenant, wf, vars_=vars0, park=("queue_off", time.time() + 10 * 365 * 86400))
            return {"ok": True, "status": 202, "run_id": rid, "workflow": wf["name"], "tenant": tenant, "answers": False,
                    "note": "The route is off - the call is kept and runs when it is switched on"}
        slot = max(time.time(), float(last["created_at"]) + _TOKEN_MIN_RATE_S if last is not None else 0, latest + _TOKEN_MIN_RATE_S)
        rid = create_run(tenant, wf, vars_=vars0, park=("queue", slot))
        return {"ok": True, "status": 202, "run_id": rid, "workflow": wf["name"], "tenant": tenant, "answers": False,
                "note": f"Waiting its turn in the route's queue ({waiting + 1} waiting) - it runs in about "
                        f"{max(1, int(slot - time.time()))} seconds"}
    rid = create_run(tenant, wf, vars_=vars0)
    answers = _has_respond(wf.get("steps") or [])
    if answers:                       # v0.999.239 the caller waits for the route's Respond step
        c = get_run(tenant, rid)["context"]
        c["_caller_waits"] = True
        update_run(tenant, rid, context=c)
    return {"ok": True, "status": 202, "run_id": rid, "workflow": wf["name"], "tenant": tenant, "answers": answers}


def _has_respond(steps: list) -> bool:
    try:
        return any(st.get("type") == "respond" for st, _ in _walk_steps(steps))
    except ToolError:
        return False


async def await_answer(tenant: str, rid: str, wait_s: float = _RESPOND_WAIT_S) -> dict:
    """Wait for a run's Respond step (or its end, or a pause). {answered, status, answer, run_status, run_id}."""
    t_end = time.time() + wait_s
    while True:
        ans = _RESPONSES.pop(rid, None)
        r = None
        if ans is None:
            r = await asyncio.to_thread(get_run, tenant, rid)
            if r is not None:
                ans = (r.get("context") or {}).get("_response")
        if ans is not None:
            _RESPONSES.pop(rid, None)
            return {"answered": True, "status": int(ans.get("status") or 200), "answer": ans.get("body"), "run_id": rid,
                    "run_status": (r or {}).get("status")}
        st = (r or {}).get("status")
        if st in ("done", "failed", "stopped", "incomplete", "sleeping", "waiting_approval") or time.time() >= t_end:
            return {"answered": False, "run_status": st or "queued", "run_id": rid}
        await asyncio.sleep(0.25)


async def start_and_wait(tenant: str, wf: dict, vars_: dict, wait_s: float = _RESPOND_WAIT_S) -> dict:
    """v0.999.240: a run started by a form, a chat message or an AI app: start it now and wait for its answer."""
    rid = await asyncio.to_thread(create_run, tenant, wf, vars_)
    c = (await asyncio.to_thread(get_run, tenant, rid))["context"]
    c["_caller_waits"] = True
    await asyncio.to_thread(update_run, tenant, rid, context=c)
    _start_now(tenant, rid)
    return await await_answer(tenant, rid, wait_s)


async def webhook_call(token: str, body: dict, meta: dict | None = None) -> dict:
    """v0.999.239 ROUTE R4: the webhook. A route with a Respond step starts at once and the caller gets that
    step's answer (status + body) - or, after 25 seconds, a note that it is still working."""
    out = await asyncio.to_thread(webhook_enqueue, token, body, meta)
    tenant, rid = out.pop("tenant", ""), out.get("run_id")
    if not out.get("ok") or not out.pop("answers", False):
        out.pop("answers", None)
        return out
    _start_now(tenant, rid)
    res = await await_answer(tenant, rid)
    if res.get("answered"):
        return {**out, "status": res["status"], "answer": res.get("answer"), "answered": True}
    st = res.get("run_status")
    if st == "done":
        return {**out, "status": 200, "note": "The route ran but did not send an answer"}
    if st in ("failed", "stopped", "incomplete", "sleeping", "waiting_approval"):
        return {**out, "status": 202, "note": "The route is still going (it paused before its answer)"}
    return {**out, "status": 202, "note": "The route is still working; it did not answer within 25 seconds"}


# --------------------------------------------------------------------------- tools

def _fmt_wf(wf: dict, run: dict | None = None) -> dict[str, Any]:
    out = {"workflow_id": wf["id"], "name": wf["name"], "trigger": wf["trigger_kind"],
           "enabled": bool(wf.get("enabled")), "steps": len(wf.get("steps") or []),
           "description": (wf.get("description") or "")[:200]}
    if wf["trigger_kind"] == "schedule":
        out["next_due_at"] = wf.get("next_due_at")
    if wf.get("settings"):
        out["settings"] = wf["settings"]
    if run is not None:
        out["last_run"] = {"run_id": run["id"], "status": run["status"], "cursor": run["cursor"],
                           "steps_logged": len(run.get("steps_log") or []), "error": (run.get("error") or "")[:200]}
    return out


def _owner_only(ctx: Ctx) -> None:
    if str(getattr(ctx, "actor", "") or "").startswith(("staff:", "customer:")):
        raise ToolError("Only the owner changes routes; a team member can run a route shared with them")


async def dhara_save(ctx: Ctx, name, steps, description="", trigger="manual", trigger_spec=None, settings=None, **_):
    """Create/update one of her workflows: validated hard BEFORE anything is stored."""
    from ..config import get_settings
    _owner_only(ctx)
    s = get_settings()
    if not getattr(s, "dhara_enabled", True):
        raise ToolError("DHARA is turned off on this server (dhara_enabled=false)")
    nm = str(name or "").strip().lower().replace(" ", "_")
    if not nm or not _PATH_RE.match(nm):
        raise ToolError("Give the workflow name in lowercase_with_underscores (like daily_morning_report)")
    kind = str(trigger or "manual").lower()
    from ..route import triggers as TR
    st_norm = validate_settings(settings, ctx.tenant_id) if settings is not None else None
    spec = TR.validate(kind, dict(trigger_spec or {}), st_norm)   # v0.999.240: every trigger kind, checked in one place
    norm = validate_steps(steps)
    wf, created = save_workflow(ctx.tenant_id, nm, str(description or ""), kind, spec, norm,
                                str(ctx.conversation_id or ""), settings=st_norm)
    if kind in ("schedule", "event"):
        con = _con(ctx.tenant_id)
        try:
            con.execute("UPDATE workflows SET next_due_at = ? WHERE id = ?",
                        (next_due(wf), wf["id"]))
            con.commit()
        finally:
            con.close()
        wf = get_workflow(ctx.tenant_id, wf_id=wf["id"])
    out = _fmt_wf(wf)
    out["created"] = created
    out["note"] = ("Workflow created — try it now with dhara_run"
                   if created else "Workflow updated (same name, same id)")
    if wf["trigger_kind"] == "webhook":
        out["webhook_note"] = ("The token is shown only now — keep it safe (it cannot be shown again): "
                               + webhook_token_reveal(ctx.tenant_id, wf["id"])) if created else \
                              "The webhook token is the old one (no new one was made)"
    if wf["trigger_kind"] in ("form", "chat"):
        pub = TR.public_address(ctx.tenant_id, wf) or (TR.make_address(ctx.tenant_id, wf)["url"] if created else "")
        out["address"] = pub or "Make its address on the route's page (What starts it)"
    if wf["trigger_kind"] == "tool":
        out["tool_note"] = ("It is offered to AI apps once it is on and her MCP address is made (Hoola Route > "
                            "Settings > Your routes as tools)")
    return out


def webhook_token_reveal(tenant_id: str, wf_id: str) -> str:
    """v1 honest limitation: the hash is one-way, so a NEW token is minted and stored on reveal
    (the old one dies). Called only at creation time."""
    tok = secrets.token_urlsafe(24)
    th = hashlib.sha256(tok.encode()).hexdigest()
    con = _con(tenant_id)
    try:
        con.execute("UPDATE workflows SET token_hash = ? WHERE id = ?", (th, wf_id))
        con.commit()
    finally:
        con.close()
    return tok


async def dhara_run(ctx: Ctx, name="", workflow_id="", vars=None, **_):
    """Run a workflow NOW (manual trigger). Returns the run_id; watch it with dhara_runs."""
    from ..config import get_settings
    s = get_settings()
    if not getattr(s, "dhara_enabled", True):
        raise ToolError("DHARA is turned off on this server (dhara_enabled=false)")
    wf = get_workflow(ctx.tenant_id, name=str(name or "").lower(), wf_id=str(workflow_id or ""))
    if wf is None:
        raise ToolError("No workflow with this name found — check dhara_list")
    if str(getattr(ctx, "actor", "") or "").startswith("staff:"):   # v0.999.246: a team member runs only routes shared with them
        from ..route import workspace as WS
        if not WS.team_may_run(ctx.tenant_id, ctx.actor, wf):
            raise ToolError("This route is not shared with this team member")
    if not wf.get("enabled", 0):
        raise ToolError(f'"{wf["name"]}" is disabled right now — turn it on with dhara_control action=enable')
    if _over_daily_cap(ctx.tenant_id, wf):    # v0.999.253: the route's runs-a-day limit holds here too
        raise ToolError(f'"{wf["name"]}" already ran as many times today as its settings allow (runs a day)')
    v = dict(vars) if isinstance(vars, dict) else {}
    rid = create_run(ctx.tenant_id, wf, vars_=v)
    _start_now(ctx.tenant_id, rid)             # v0.999.253: claimed first, so it can never run twice
    return {"run_id": rid, "workflow": wf["name"], "status": "queued",
            "note": "Run started — see every step's status with dhara_runs run_id=" + rid + ""}


async def dhara_runs(ctx: Ctx, run_id="", workflow_id="", limit=8, **_):
    """Recent runs (status, steps done); run_id= gives the full step-by-step log of one run."""
    if run_id:
        r = get_run(ctx.tenant_id, str(run_id))
        if r is None:
            raise ToolError("This run_id was not found")
        return _masked({"run_id": r["id"], "workflow": r["wf_name"], "status": r["status"],
                "cursor": r["cursor"], "error": r.get("error") or "",
                "pause_reason": r.get("pause_reason") or "",
                "summary": r.get("summary"),
                "steps_log": r["steps_log"][-40:],
                "note": ("Still running — check again in a little while"
                         if r["status"] in ("queued", "running") else "")})
    wf_id = str(workflow_id or "")
    if wf_id and get_workflow(ctx.tenant_id, wf_id=wf_id) is None:
        raise ToolError("This workflow_id was not found")
    rows = list_runs(ctx.tenant_id, wf_id=wf_id, limit=max(1, min(int(limit or 8), 20)))
    return _masked({"count": len(rows), "runs": [
        {"run_id": x["id"], "workflow": x["wf_name"], "status": x["status"], "steps_done": x["cursor"],
         "steps_logged": x["steps_log"], "missed": bool(x.get("missed")), "error": (x.get("error") or "")[:150],
         "pause_reason": x.get("pause_reason") or "", "summary": x.get("summary"),
         "age_s": int(time.time() - float(x["created_at"]))} for x in rows]})


async def dhara_control(ctx: Ctx, action, name="", workflow_id="", run_id="", **_):
    """enable | disable | stop | approve — the house decides on HER word; the agent relays it here."""
    _owner_only(ctx)
    act = str(action or "").lower()
    if act in ("enable", "disable"):
        wf = get_workflow(ctx.tenant_id, name=str(name or "").lower(), wf_id=str(workflow_id or ""))
        if wf is None:
            raise ToolError("Workflow not found — check the name with dhara_list")
        set_enabled(ctx.tenant_id, wf["id"], act == "enable")
        return {"workflow": wf["name"], "enabled": act == "enable",
                "note": "Trigger is on" if act == "enable" else "Trigger is off — you can still run it manually with dhara_run"}
    if act == "stop":
        r = get_run(ctx.tenant_id, str(run_id)) if run_id else None
        if r is None:
            wf = get_workflow(ctx.tenant_id, name=str(name or "").lower(), wf_id=str(workflow_id or ""))
            r = latest_run(ctx.tenant_id, wf["id"]) if wf else None
        if r is None:
            raise ToolError("Run not found — give a run_id (or the workflow name)")
        if r["status"] in ("done", "failed", "stopped"):
            return {"run_id": r["id"], "status": r["status"], "note": "This run had already stopped"}
        update_run(ctx.tenant_id, r["id"], status="stopped", error="the owner asked to stop it")
        wf = get_workflow(ctx.tenant_id, wf_id=r["workflow_id"])
        _finish(ctx.tenant_id, r["id"], r, len(wf["steps"]) if wf else 0, "stopped", "the owner asked to stop it",
                error="the owner asked to stop it")
        return {"run_id": r["id"], "status": "stopped", "note": "The run was stopped midway — the steps already done are in the log"}
    if act == "approve":
        r = get_run(ctx.tenant_id, str(run_id)) if run_id else None
        if r is None:
            raise ToolError("Give a run_id for approve (from dhara_runs)")
        if r["status"] != "waiting_approval":
            return {"run_id": r["id"], "status": r["status"], "note": "This run was not waiting for approval"}
        # her haan = the gate is passed: the cursor moves PAST the approval step, else the resumed run
        # would hit the same gate and park forever (the resume executes from the checkpoint).
        # v0.999.239: an approval inside a branch / loop is marked done instead and the run resumes inside it.
        c = r.get("context") or {}
        mark = c.pop("_wait_mark", None)
        c.pop("_wait_q", None)
        r["steps_log"].append({"id": str(mark or r["cursor"]), "type": "approval", "status": "approved",
                               "at": time.strftime("%H:%M:%S")})
        if mark:
            c.setdefault("_done", []).append(mark)
        update_run(ctx.tenant_id, r["id"], status="queued", tries=0, context=c,
                   cursor=int(r["cursor"]) + (0 if mark else 1), steps_log=r["steps_log"], pause_reason=None)
        _start_now(ctx.tenant_id, r["id"])     # v0.999.253: claimed first, so it can never run twice
        return {"run_id": r["id"], "status": "queued", "note": "Her approval is received — the run continued from the same place"}
    if act == "retry":
        # v0.512 (the Dify node-retry idea): a failed/stopped run re-queues FROM ITS CURSOR — the
        # checkpoint law makes this safe by construction: a finished step never runs twice.
        r = get_run(ctx.tenant_id, str(run_id)) if run_id else None
        if r is None:
            wf = get_workflow(ctx.tenant_id, name=str(name or "").lower(), wf_id=str(workflow_id or ""))
            r = latest_run(ctx.tenant_id, wf["id"]) if wf else None
        if r is None:
            raise ToolError("Give a run_id (or the workflow name) for retry")
        if r["status"] not in ("failed", "stopped", "incomplete"):
            return {"run_id": r["id"], "status": r["status"],
                    "note": "retry works only on a stopped (failed / stopped / incomplete) run"}
        ctx_r = r.get("context") or {}
        for k in [k for k in ctx_r if str(k).startswith("_retries_")]:
            ctx_r.pop(k, None)               # v0.999.87 a hand retry gets its automatic retries back
        if (r.get("pause_reason") or "") == "approval_expired":
            return {"run_id": r["id"], "status": r["status"], "ok": False,
                    "note": "the approval time had run out — it cannot go past the gate without approving again; "
                            "run the workflow again as a new run with dhara_run"}
        r["steps_log"].append({"id": str(r["cursor"]), "type": "retry", "status": "retry",
                               "at": time.strftime("%H:%M:%S")})
        update_run(ctx.tenant_id, r["id"], status="queued", tries=0, error="", pause_reason=None,
                   steps_log=r["steps_log"], context=ctx_r)
        _start_now(ctx.tenant_id, r["id"])     # v0.999.253: claimed first, so it can never run twice
        return {"run_id": r["id"], "status": "queued",
                "note": "Resumed from the checkpoint — the steps already done will not run again"}
    raise ToolError("action: enable | disable | stop | approve | retry")


async def dhara_list(ctx: Ctx, **_):
    """Her workflows with trigger state and the last run's haal — the mini-board."""
    from ..config import get_settings
    s = get_settings()
    if not getattr(s, "dhara_enabled", True):
        raise ToolError("DHARA is turned off on this server (dhara_enabled=false)")
    wfs = list_workflows(ctx.tenant_id, 20)
    out = []
    for wf in wfs:
        last = latest_run(ctx.tenant_id, wf["id"])
        out.append(_fmt_wf(wf, last))
    return {"count": len(out), "workflows": out,
            "note": ("Use dhara_save to make a new one" if out else "No workflow yet — make the first one with dhara_save")}


# --------------------------------------------------------------------------- DSL (v0.512, the Dify DSL idea)

_DSL_VERSION = 1


def _scrub_for_export(obj: Any) -> Any:
    """The export law: what leaves the tenant carries NO secrets — ids masked, identifiers masked;
    runtime outputs were never stored in steps (args only), and the webhook token never rides
    (it lives sha256-hashed in its own column, which the envelope never includes)."""
    return _masked(obj)


def dsl_export(tenant_id: str, wf: dict) -> dict[str, Any]:
    env = {"dhara_dsl": _DSL_VERSION, "source": "hoola-dhara",
           "name": wf["name"], "description": wf.get("description") or "",
           "trigger": wf["trigger_kind"], "trigger_spec": wf.get("trigger_spec") or {},
           "steps": _scrub_for_export(wf.get("steps") or []),
           "settings": wf.get("settings") or {},
           "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    return env


async def dhara_dsl(ctx: Ctx, action: str, name: str = "", workflow_id: str = "", dsl=None, new_name: str = "", **_):
    """export (workflow -> a portable JSON envelope, secrets-free) | import (the SAME hard validator,
    lands disabled, she enables it). Backup, migrate between tenants, share a proven recipe."""
    from ..config import get_settings
    _owner_only(ctx)
    s = get_settings()
    if not getattr(s, "dhara_enabled", True) or not getattr(s, "dhara_dsl_enabled", True):
        raise ToolError("DHARA DSL is turned off on this server (dhara_dsl_enabled=false)")
    max_kb = int(getattr(s, "dhara_dsl_max_kb", 64) or 64)
    if str(action).lower() == "export":
        wf = get_workflow(ctx.tenant_id, name=str(name or "").lower(), wf_id=str(workflow_id or ""))
        if wf is None:
            raise ToolError("No workflow with this name found — check dhara_list")
        env = dsl_export(ctx.tenant_id, wf)
        raw = json.dumps(env, ensure_ascii=False)
        if len(raw.encode()) > max_kb * 1024:
            raise ToolError(f"The export is too big ({len(raw.encode()) // 1024} KB; cap {max_kb} KB) — "
                            "keep the workflow in smaller parts")
        return {"ok": True, "dsl": env, "bytes": len(raw.encode()),
                "note": "Keep this file safe — it has the workflow's steps, NOT secrets "
                        "(a webhook token is never in an export). To bring it into another tenant: "
                        "dhara_dsl action=import dsl=<this same envelope>"}
    if str(action).lower() == "import":
        if isinstance(dsl, str):
            try:
                dsl = json.loads(dsl)
            except Exception:
                raise ToolError("dsl must be a JSON object (or its JSON string)")
        if not isinstance(dsl, dict) or dsl.get("dhara_dsl") != _DSL_VERSION:
            raise ToolError(f"This does not look like a DHARA DSL file (needs dhara_dsl={_DSL_VERSION})")
        raw = json.dumps(dsl, ensure_ascii=False)
        if len(raw.encode()) > max_kb * 1024:
            raise ToolError(f"The DSL file is too big (cap {max_kb} KB)")
        nm = str(new_name or dsl.get("name") or "").strip().lower().replace(" ", "_")
        if not nm or not _PATH_RE.match(nm):
            raise ToolError("Give the workflow name in lowercase_with_underscores")
        kind = str(dsl.get("trigger") or "manual").lower()
        st_imp = validate_settings(dsl.get("settings") or {})
        from ..route import triggers as TR
        spec = TR.validate(kind, dict(dsl.get("trigger_spec") or {}), st_imp)   # a webhook's new token is shown once below
        if get_workflow(ctx.tenant_id, name=nm) is not None:
            return {"ok": False, "already_exists": True, "existing": nm,
                    "note": f"'{nm}' already exists — to bring it in under another name "
                            f"give new_name='{nm}_2' (or rename the old one first)"}
        norm_steps = validate_steps(dsl.get("steps"))   # THE SAME hard validator as dhara_save
        wf, _created = save_workflow(ctx.tenant_id, nm, str(dsl.get("description") or "")[:500], kind, spec,
                                     norm_steps, str(ctx.conversation_id or ""), settings=st_imp)
        set_enabled(ctx.tenant_id, wf["id"], False)      # imported lands BAND — she reads, she enables
        if kind in ("schedule", "event"):
            con = _con(ctx.tenant_id)
            try:
                con.execute("UPDATE workflows SET next_due_at = ? WHERE id = ?", (next_due(wf), wf["id"]))
                con.commit()
            finally:
                con.close()
        out = _fmt_wf(get_workflow(ctx.tenant_id, wf_id=wf["id"]))
        out["ok"] = True
        out["note"] = "Imported but it is OFF — check the steps, then turn it on with dhara_control action=enable"
        if kind == "webhook":
            out["webhook_note"] = ("New webhook token (shown only once): "
                                   + webhook_token_reveal(ctx.tenant_id, wf["id"]))
        return out
    raise ToolError("action: export | import")


DHARA_TOOLS = [
    {"name": "dhara_save", "description": (
        "Create or update one of her WORKFLOWS (v0.502, the n8n idea house-sized): a named, saved graph of steps "
        "that runs on a trigger without anyone asking again. Steps (max 40): tool (ANY registered tool by name + args), "
        "code (python in the pylab sandbox), condition (left/op/right with then/else), loop (items + body, cap 50), "
        "wait (duration_s / until HH:MM; see below), notify (a chat line to her), send (really sends: via email {to, cc, subject, body, account} or telegram {chat, text} / slack {channel, text} / discord / mattermost {channel, text} with connection = her saved sign-in; it sends only after SHE taps Allow sending on the route page - never claim it sent before that), approval (pauses until SHE says yes), set (a "
        "variable), http (SSRF-guarded GET/POST). Expressions like {{steps.get_data.output.total}} / {{vars.x}} / "
        "{{item}} / {{now}}. Triggers: manual | schedule | webhook (token minted once). Validate-first: unknown step "
        "types / caps / unsafe names are refused with the exact problem. "
        "HOOLA ROUTE (v0.999.87) adds: router {routes: [{label, filter, steps}], fallback: [steps]} - every route "
        "whose filter passes runs in order, fallback only when none did; filter {filter} - the run ends cleanly when "
        "it does not pass. A filter is {left, op, right, ci} or {all: [...]} (AND) / {any: [...]} (OR), ops: exists "
        "not_exists empty not_empty eq ne contains not_contains starts_with ends_with matches gt gte lt lte between "
        "before after is_true is_false in not_in length_eq length_gt length_lt. Any step may carry on_error: "
        "{do: break, retries: 3, wait_min: 10} (retry later, then keep it in Incomplete runs) | {do: resume, value} | "
        "ignore | commit | rollback | tell. Schedules work for anyone anywhere: timezone (IANA, e.g. "
        "America/New_York), every_minutes (>=15), every_hours, at ['HH:MM'], days ['mon'..], monthdays [1..31], "
        "dates ['YYYY-MM-DD'], once 'YYYY-MM-DDTHH:MM', quiet {from, to}, skip_holidays '<country code>'. "
        "settings: {folder, timezone, stop_after_errors, error_route, runs_per_day, currency}. Use the user's own "
        "time zone and currency - never assume India. "
        "v0.999.237 adds the DATA step {type: data, op, ...}: sort {items, by, order asc|desc} | limit {items, count, keep "
        "first|last} | dedupe {items, by} | aggregate {items, field, how count|sum|avg|min|max|list|unique|join, sep} | split "
        "{items, field} | compare {a, b, key} -> added/removed/changed/same | keep_fields {items, fields, mode keep|drop} | "
        "rename {items, map {old: new}} | fields {values {name: value}} | date {action format|add|subtract|diff|parse|now, "
        "value, amount, unit, other, format, tz} | text {action html_text|html_select|xml_to_data|csv_to_rows|rows_to_csv|"
        "json_parse|json_text|base64_encode|base64_decode|url_encode|url_decode, value, selector, attr} | file {action "
        "make_xlsx|make_csv|make_pdf|read, items, name, title, value, file_id} -> {file_id, url} | crypto {action sha256|sha1|"
        "md5|hmac_sha256|uuid|random, value, secret}. EXPRESSIONS in {{ }} can do maths and call functions: "
        "{{ steps.x.output.total * 1.18 }}, {{ round(vars.a / 3, 2) }}, {{ 'big' if vars.amount > 5000 else 'small' }}, "
        "upper lower title trim len count replace split join slice contains starts_with ends_with text num int round abs "
        "floor ceil min max sum avg default json parse_json keys values first last sort unique pluck get now today "
        "date_add date_diff date_format to_date; lists by index {{ vars.rows[0].name }}. "
        "v0.999.239 adds FLOW steps: merge (data op) {a, b, mode append|by_key|by_position|keep_matches|keep_non_matches, "
        "key, key_b, join inner|left|outer}; subroute {route: '<another route name>', vars {..}, wait true|false} -> "
        "{{steps.x.output.result}} (its last step) and .vars (up to 3 deep, never itself); stop {as error|done, message} "
        "ends the run; respond {status, body} answers the app that called the webhook (it waits up to 25 s); wait {amount, "
        "unit seconds|minutes|hours|days|weeks} up to 30 days, or until 'HH:MM' / 'YYYY-MM-DD HH:MM' in the route's time "
        "zone, or {for: call, timeout_s, on_timeout continue|fail} = wait until someone calls {{vars.resume_url}} (send "
        "that link in an earlier step; the call's data is the step's output). Approvals and waits work anywhere, also "
        "inside branches and loops. Loops take up to 1,000 items (as: '<name>' keeps the item as {{vars.<name>}} for a "
        "loop inside it); branches and loops nest up to 3 levels. "
        "v0.999.243 adds AI steps {type: ai, op, ..., quality fast|best, instructions}: write {prompt} -> {text} | summarise "
        "{text, length short|medium|long|points, language} -> {summary} | classify {text, categories 'a, b', multi} -> "
        "{category, matched, reason} | extract {text, fields {name: what it is}} -> an object of those fields | sentiment "
        "{text} -> {label, score} | answer {question, files [file ids], text, knowledge true} -> {answer, found, sources} (only "
        "from those) | agent {prompt, tools ['sheet_read', ...] (only these, up to 15), max_steps 1-10, memory none|on, "
        "memory_key} -> {answer, used}. A router may carry ai {text, instructions}: the AI picks ONE way by its label. "
        "v0.999.246: her variables {{env.NAME}}; an http step may carry auth '<sign-in name>' (saved on the Route page under "
        "Sign-ins - never ask for a key in chat; it is only sent to its own site); settings also take tags [..] and "
        "shared_with [team member ids] (they may run it, never change it); every save is kept as a version. "
        "v0.999.254 MAKE PARITY: DATA STORES {type: store, op add|update|get|exists|delete|delete_all|search|count|increment, "
        "store '<name>', key, data {field: value}, overwrite, insert_missing, filter {field, op, value} (or all/any), sort, "
        "order, limit (<=3200), field, by, confirm true (delete_all)} - her own tables kept between runs (made on the Route "
        "page under Data stores; a rollback takes this run's writes back); VARIABLES {type: var, op set_many {values} | get "
        "{name} | get_many {names} | increment {name, reset never|run} -> {value} | save {name, value} (her route variable "
        "{{env.NAME}})}; a loop may be a REPEATER {repeat: {times, start, step}} (item = the number) and may collect "
        "{collect: '{{...}}', join: ', '} -> output.results / output.text (Make's array / text aggregator); on_error may "
        "carry steps: [...] that run first with {{error.message}} / {{error.step}} (Make's error handler route; no do = "
        "ignore); http {action request|download|resolve, method GET|HEAD|POST|PUT|PATCH|DELETE|OPTIONS, url, headers, "
        "query, body_type json|form|multipart|raw|none, body, form, files [{field, file_id}], content_type, timeout 1-300, "
        "redirects, share_cookies, compressed, parse, fail_on_error, pagination {type offset|page|url|cursor, items, param, "
        "size, size_param, start, next, limit}}; text actions regex_match {pattern, global, case_sensitive, multiline, "
        "singleline} | regex_replace {pattern, replace} | data_to_xml {root} | rows_to_table {column_sep, row_sep} | "
        "markdown_to_html | html_to_markdown; file actions zip {items [file ids]} | unzip {file_id}. Make's FUNCTIONS work "
        "in {{ }} under their own names (formatDate parseDate addDays setDay if ifempty switch omit pick map flatten merge "
        "distinct toCollection toArray formatNumber parseNumber trunc median substring indexOf startcase stripHTML sha256 "
        "replace with /regex/g ...) and its keywords (now timestamp uuid random newline space tab emptystring); {{run.id}} "
        "{{run.route}} {{run.started_at}}. settings also take in_order, confidential, keep_incomplete, auto_commit, "
        "queue_when_off, queue_max, allow_ips; a schedule may have start_date; an app event start now|all|since."),
     "input_schema": {"type": "object", "properties": {
         "name": {"type": "string", "description": "lowercase_with_underscores, unique, e.g. daily_morning_notice_check"},
         "steps": {"type": "array", "description": "The steps: [{id, type, ...}] — see the tool guide for each type's fields"},
         "description": {"type": "string", "description": "One line: what it does"},
         "trigger": {"type": "string", "enum": ["manual", "schedule", "webhook", "event", "form", "chat", "error", "route", "tool"],
                     "description": "Default manual. event = an app event (new email / sheet row / form answer / calendar event / "
                                    "Drive file / feed item / any app's list); form = a Hoola form page; chat = a Hoola chat page; "
                                    "error = when a route fails; route = called by another route; tool = offered to AI apps (MCP)"},
         "trigger_spec": {"type": "object", "description": "schedule: {timezone: 'Europe/London', days: ['mon','fri'], at: ['09:30'], quiet: {from: '21:00', to: '08:00'}, skip_holidays: 'GB'} or {every_minutes: 30} or {every_hours: 24, at: ['09:30']}; webhook: none; event: {app: email|sheet_row|form_answer|calendar_event|drive_file|rss|app, every_minutes (5-1440, default 15), folder/search/account (email), spreadsheet/tab (sheet_row), form (form_answer), query (calendar_event / drive_file), url (rss), tool + args + items + id (app: a tool that only reads)} -> each new item runs with {{vars.event}}; form: {title, intro, fields: [{name, label, type text|textarea|email|number|date|select|checkbox|phone, required, options}], button, thanks} -> {{vars.form.<name>}}, a respond step's answer is shown to the sender; chat: {title, greeting, placeholder} -> {{vars.message}}, {{vars.history}}, reply with a respond step; error: {routes: [names], empty = any} -> {{vars.failed_route}} {{vars.error}}; route: {inputs: [{name, description}]}; tool: {description, inputs: [{name, description, type, required}]}"},
         "settings": {"type": "object", "description": "Route settings: {folder, timezone, stop_after_errors (1-20), error_route (another route's name), runs_per_day, currency}"}},
         "required": ["name", "steps"]}},
    {"name": "dhara_run", "description": (
        "Run one of her saved workflows NOW (v0.502). Returns a run_id at once — the run goes in the background "
        "with a checkpoint after every step; dhara_runs shows the status. Optional vars land as {{vars.x}}. A disabled "
        "workflow refuses; enable it first with dhara_control."),
     "input_schema": {"type": "object", "properties": {
         "name": {"type": "string", "description": "The workflow's name (or workflow_id)"},
         "workflow_id": {"type": "string", "description": "Alternative to name"},
         "vars": {"type": "object", "description": "Variables for this run ({{vars.name}} in expressions)"}},
         "required": []}},
    {"name": "dhara_runs", "description": (
        "Her workflow runs (v0.502): recent list (status, steps done, errors, missed-schedule flag) or ONE run's "
        "full step-by-step log with run_id= (each step: id, type, ok/error, ms, output snippet). Works mid-run."),
     "input_schema": {"type": "object", "properties": {
         "run_id": {"type": "string", "description": "One run's full log"},
         "workflow_id": {"type": "string", "description": "Only this workflow's runs"},
         "limit": {"type": "integer", "description": "Default 8, cap 20"}},
         "required": []}},
    {"name": "dhara_control", "description": (
        "Turn a workflow's trigger on/off, stop a run, or relay HER yes (v0.502). action=approve run_id=... when "
        "she answered a waiting approval step in chat ('yes' / 'haan') — the run resumes from the same step. action=stop "
        "lands between steps; finished steps stay in the log. action=retry (v0.512) re-runs a failed/stopped run "
        "FROM its checkpoint — finished steps never run twice; an approval-expired run is honestly refused. "
        "Never approve without her word."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["enable", "disable", "stop", "approve", "retry"]},
         "name": {"type": "string", "description": "Workflow name (enable/disable)"},
         "workflow_id": {"type": "string"},
         "run_id": {"type": "string", "description": "For stop / approve / retry"}},
         "required": ["action"]}},
    {"name": "dhara_list", "description": (
        "Her workflows — the mini-board (v0.502): name, trigger, enabled, step count, next schedule due, last run's "
        "status and error. Use before building (what already exists) and when she asks 'how are my workflows'."),
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "dhara_dsl", "description": (
        "Export or import her WORKFLOWS as portable files (v0.512, the Dify DSL idea). action=export name=... gives a "
        "JSON envelope of the whole workflow — secrets-free by law (the webhook token never rides, values pass the "
        "house mask); keep it as a backup, share it, or move a proven workflow to another of her spaces with "
        "action=import dsl=<envelope> (new_name= to rename). Import runs the SAME hard validator as dhara_save and "
        "lands DISABLED — she reads the steps, then enables it herself. A webhook workflow gets a NEW token on import, "
        "shown once."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["export", "import"]},
         "name": {"type": "string", "description": "export: the workflow's name (or workflow_id)"},
         "workflow_id": {"type": "string"},
         "dsl": {"type": "object", "description": "import: the envelope (a dhara_dsl=1 JSON object or its JSON string)"},
         "new_name": {"type": "string", "description": "import under a different name"}},
         "required": ["action"]}},
]

DHARA_LABELS = {"dhara_save": "Creating or updating the workflow",
                "dhara_run": "Running the workflow now",
                "dhara_runs": "Checking run status",
                "dhara_control": "Controlling the workflow",
                "dhara_list": "Checking workflows",
                "dhara_dsl": "Fetching the workflow file"}

DHARA_HANDLERS = {"dhara_save": dhara_save, "dhara_run": dhara_run, "dhara_runs": dhara_runs,
                  "dhara_control": dhara_control, "dhara_list": dhara_list, "dhara_dsl": dhara_dsl}
