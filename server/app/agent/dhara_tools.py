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
import json
import re
import secrets
import sqlite3
import time
import uuid
from datetime import datetime, timedelta
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
_MAX_DEPTH = 1           # condition/loop bodies nest exactly one level
_LOOP_MAX = 50           # iterations per loop step
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
               "router", "filter")      # v0.999.87 HOOLA ROUTE: a router with named routes + a filter gate
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
_RETRY_MAX = 10
_DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
# Turn-shaped tools that make no sense inside a background run (they need the live turn to carry
# the answer). Everything else is allowed — each tool's OWN guards still apply (actor="routine").
_TOOL_STEP_DENY = {"ask_form"}
_EXPR_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_.\[\]]{0,120})\s*\}\}")
_PATH_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z0-9_]+)*$")
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
                  settings: dict | None = None) -> tuple[dict, bool]:
    """Insert or update by name. Returns (row, created). Keeps id / created_at on update;
    a webhook token is generated once and kept unless the trigger kind changed away and back."""
    now_ = time.time()
    con = _con(tenant_id)
    try:
        old = con.execute("SELECT * FROM workflows WHERE name = ?", (name,)).fetchone()
        token_hash = None
        if trigger_kind == "webhook":
            if old is not None and old["token_hash"]:
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
            th = token_hash if trigger_kind == "webhook" else (old["token_hash"] if old["trigger_kind"] == "webhook" else None)
            con.execute("UPDATE workflows SET description=?, trigger_kind=?, trigger_spec=?, token_hash=?, steps=?, "
                        "updated_at=? WHERE id=?",
                        (description[:500], trigger_kind, json.dumps(trigger_spec), th, json.dumps(steps), now_, wid))
            if settings is not None:        # v0.999.87: None = keep the route's settings as they are
                con.execute("UPDATE workflows SET settings = ? WHERE id = ?", (json.dumps(settings), wid))
            created = False
        con.commit()
        return _wf_row(con.execute("SELECT * FROM workflows WHERE id = ?", (wid,)).fetchone()), created
    finally:
        con.close()


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
        cur = con.execute("UPDATE workflows SET enabled = ?, updated_at = ? WHERE id = ?",
                          (1 if enabled else 0, time.time(), wf_id))
        con.commit()
        return cur.rowcount > 0
    finally:
        con.close()


def workflows_with_hash(tenant_id: str, token_hash: str) -> dict[str, Any] | None:
    con = _con(tenant_id)
    try:
        r = con.execute("SELECT * FROM workflows WHERE token_hash = ?", (token_hash,)).fetchone()
        return _wf_row(r)
    finally:
        con.close()


def create_run(tenant_id: str, wf: dict, vars_: dict | None = None, missed: bool = False) -> str:
    now_ = time.time()
    rid = "rn_" + uuid.uuid4().hex[:12]
    con = _con(tenant_id)
    try:
        con.execute("INSERT INTO runs (id, workflow_id, wf_name, status, cursor, context, steps_log, tries, "
                    "started_at, missed, created_at, updated_at) VALUES (?,?,?,?,0,?,?,0,?,?,?,?)",
                    (rid, wf["id"], wf["name"], "queued", json.dumps({"vars": dict(vars_ or {}), "steps": {}, "notify": 0}),
                     "[]", now_ if not missed else None, 1 if missed else 0, now_, now_))
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


def list_runs(tenant_id: str, wf_id: str = "", limit: int = 10) -> list[dict[str, Any]]:
    con = _con(tenant_id)
    try:
        if wf_id:
            rows = con.execute("SELECT * FROM runs WHERE workflow_id = ? ORDER BY created_at DESC LIMIT ?",
                               (wf_id, int(limit))).fetchall()
        else:
            rows = con.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (int(limit),)).fetchall()
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


def update_run(tenant_id: str, run_id: str, **fields) -> None:
    if not fields:
        return
    if "context" in fields and not isinstance(fields["context"], str):
        fields["context"] = json.dumps(fields["context"])
    if "steps_log" in fields and not isinstance(fields["steps_log"], str):
        fields["steps_log"] = json.dumps(fields["steps_log"])
    fields.setdefault("updated_at", time.time())  # an explicit updated_at (tests backdate) wins
    sets = ", ".join(f"{k} = ?" for k in fields)
    con = _con(tenant_id)
    try:
        con.execute(f"UPDATE runs SET {sets} WHERE id = ?", (*fields.values(), run_id))
        con.commit()
    finally:
        con.close()


def forget_old_runs(tenant_id: str, keep_days: int = 30, keep: int = 40) -> int:
    cut = time.time() - max(1, int(keep_days)) * 86400
    con = _con(tenant_id)
    try:
        gone = con.execute("DELETE FROM runs WHERE status NOT IN ('queued','running','sleeping','waiting_approval','incomplete') "
                           "AND updated_at < ?", (cut,)).rowcount
        extra = con.execute("SELECT id FROM runs WHERE status NOT IN ('queued','running','sleeping','waiting_approval','incomplete') "
                            "ORDER BY updated_at DESC LIMIT -1 OFFSET ?", (int(keep),)).fetchall()
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
            if sub:
                out.extend(_walk_steps(sub, depth + 1))
        for rt in (s.get("routes") or []) if isinstance(s.get("routes"), list) else []:
            if isinstance(rt, dict) and rt.get("steps"):
                out.extend(_walk_steps(rt["steps"], depth + 1))
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
    if do not in _ON_ERROR:
        raise ToolError(f"Step '{sid}': on_error do must be one of: {', '.join(_ON_ERROR)}")
    out: dict[str, Any] = {"do": do}
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
            raise ToolError("Steps inside a condition/loop can go only one level deep (nesting cap 1)")
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
            if "items" not in st_:
                raise ToolError(f"Step '{sid}': a loop needs items (an expression that gives a list)")
        elif typ == "wait":
            if not st_.get("duration_s") and not st_.get("until"):
                raise ToolError(f"Step '{sid}': give wait a duration_s (<= 3600) or until 'HH:MM'")
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
        elif typ == "filter":
            if st_.get("filter") is None:
                raise ToolError(f"Step '{sid}': a filter step needs a filter ({{left, op, right}} or {{all: [...]}})")
            validate_filter(st_["filter"], sid)
        elif typ == "http":
            if not str(st_.get("url") or "").strip():
                raise ToolError(f"Step '{sid}': http needs a url")
            if str(st_.get("method") or "GET").upper() not in ("GET", "POST"):
                raise ToolError(f"Step '{sid}': http method can be only GET or POST (v1)")
        if "on_error" in st_:
            st_["on_error"] = validate_on_error(st_.get("on_error"), sid)
            if st_["on_error"] is None:
                st_.pop("on_error", None)
        # expression size cap on every string field
        for v in st_.values():
            if isinstance(v, str) and len(v) > _EXPR_CHARS:
                raise ToolError(f"Step '{sid}': expression/text too long (cap {_EXPR_CHARS} chars)")
    _ = loop_max  # loop iteration cap lives in the engine (a graph cannot exceed it anyway)
    return top


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


def _resolve_one(expr: Any, ctx: dict) -> Any:
    """A pure {{path}} returns the VALUE (so conditions compare real types); mixed text returns text."""
    if isinstance(expr, str):
        m = _EXPR_RE.fullmatch(expr.strip())
        if m:
            return _dig(ctx, m.group(1))
        def sub(mm):
            v = _dig(ctx, mm.group(1))
            return "" if v is None else (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v))
        return _EXPR_RE.sub(sub, expr)
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
    update_run(tenant_id, run_id, **fields)


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
    if output is not None:
        try:
            text = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
        except Exception:
            text = str(output)
        entry["output"] = text[:_STEP_LOG_SNIPPET]
    run["steps_log"].append(entry)


def _save_checkpoint(tenant_id: str, run: dict) -> None:
    update_run(tenant_id, run["id"], cursor=run["cursor"], context=run["context"],
               steps_log=run["steps_log"], status=run["status"], error=run.get("error") or "",
               next_wake_at=run.get("next_wake_at"), pause_reason=run.get("pause_reason"))


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


async def _exec_sublist(tenant_id: str, conv: str, sublist: list, ctx: dict, run_id: str,
                        soft_parent: bool, done_key: str = "") -> tuple[bool, str]:
    """Condition/loop/route bodies: run their steps inline (atomic with the parent step). Returns (ok, error).
    v0.999.87: a step's own on_error ignore / resume is handled here; any other on_error rides up to the
    top-level step (ctx['_sub_on_error']). With done_key (router routes) a step that already finished in an
    earlier attempt of this run is NOT run again when the router is retried."""
    done = ctx.setdefault("_done", []) if done_key else None
    for sub in _flat_steps(sublist):
        mark = f"{done_key}/{sub.get('id')}" if done_key else ""
        if done is not None and mark in done:
            continue
        ok, out, err = await _exec_one(tenant_id, conv, sub, ctx, run_id)
        if err == "__STOP__":           # a filter inside a route closes just that route
            return True, "__STOP__"
        if not ok:
            oe = sub.get("on_error") or {}
            if oe.get("do") == "ignore":
                ok = True
            elif oe.get("do") == "resume":
                ctx["steps"][str(sub.get("id"))] = {"output": resolve(oe.get("value"), ctx)}
                ok = True
            elif soft_parent or sub.get("soft"):
                _log_step({"steps_log": []}, sub.get("id", "?"), sub.get("type", "?"), "error", 0, error=err)
                continue
            else:
                if oe:
                    ctx["_sub_on_error"] = {**oe, "step": str(sub.get("id"))}
                return False, f"step '{sub.get('id')}' ({sub.get('type')}): {err}"
        if done is not None and ok:
            done.append(mark)
    return True, ""


async def _exec_one(tenant_id: str, conv: str, step: dict, ctx: dict, run_id: str) -> tuple[bool, Any, str]:
    """One step. Returns (ok, output, error). ctx mutates: ctx['steps'][id]['output'] = output."""
    from ..config import get_settings
    s = get_settings()
    sid, typ = str(step.get("id")), str(step.get("type"))
    t0 = time.time()
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
            return True, res, ""
        if typ == "condition":
            if step.get("filter") is not None:           # v0.999.87 the full filter language
                passed = eval_filter(step["filter"], ctx)
            else:
                passed = _cmp(resolve(step.get("left"), ctx), str(step.get("op")), resolve(step.get("right"), ctx))
            branch = step.get("then") if passed else step.get("else")
            if not isinstance(branch, list):
                return True, {"branch": "skipped (no steps)"}, ""
            ok, err = await _exec_sublist(tenant_id, conv, branch, ctx, run_id, bool(step.get("soft")))
            if not ok:
                return False, None, err
            ctx["steps"][sid] = {"output": {"branch": "then" if passed else "else"}}
            return True, ctx["steps"][sid]["output"], ""
        if typ == "filter":
            passed = eval_filter(step.get("filter"), ctx)
            ctx["steps"][sid] = {"output": {"passed": passed}}
            return True, {"passed": passed}, "" if passed else "__STOP__"
        if typ == "router":
            # Every route whose filter passes runs, in order (a route without a filter always runs); the
            # fallback runs only when no filtered route passed. Each route is atomic with the router step.
            taken: list[str] = []
            matched = False
            for i, rt in enumerate(step.get("routes") or []):
                label = str(rt.get("label") or f"route {i + 1}")
                has_filter = rt.get("filter") is not None
                if has_filter and not eval_filter(rt["filter"], ctx):
                    continue
                matched = matched or has_filter
                ok, err = await _exec_sublist(tenant_id, conv, rt.get("steps") or [], ctx, run_id,
                                              bool(step.get("soft")), done_key=f"{sid}#{i}")
                if not ok:
                    return False, None, f"route '{label}': {err}"
                taken.append(label)
            if not matched and isinstance(step.get("fallback"), list) and step.get("fallback"):
                ok, err = await _exec_sublist(tenant_id, conv, step["fallback"], ctx, run_id,
                                              bool(step.get("soft")), done_key=f"{sid}#fallback")
                if not ok:
                    return False, None, f"fallback route: {err}"
                taken.append("fallback")
            ctx["steps"][sid] = {"output": {"routes": taken}}
            return True, {"routes": taken}, ""
        if typ == "loop":
            items = resolve(step.get("items"), ctx)
            if not isinstance(items, list):
                return False, None, "the loop items did not give a list"
            cap = int(getattr(s, "dhara_loop_max", _LOOP_MAX))
            if len(items) > cap:
                return False, None, f"loop items {len(items)} > cap {cap}"
            results = []
            for item in items[:cap]:
                ctx["item"] = item
                ok, err = await _exec_sublist(tenant_id, conv, step.get("body") or [], ctx, run_id,
                                              bool(step.get("soft")))
                if not ok:
                    return False, None, err
                results.append(item)
            ctx["item"] = None
            ctx["steps"][sid] = {"output": {"iterations": len(results)}}
            return True, ctx["steps"][sid]["output"], ""
        if typ == "wait":
            dur = step.get("duration_s")
            if dur:
                secs = min(int(resolve(dur, ctx) or 0), 3600)
            else:
                hh, mm = str(step.get("until") or "00:00").split(":")[:2]
                now_i = datetime.now(_IST)
                target = now_i.replace(hour=int(hh) % 24, minute=int(mm) % 60, second=0, microsecond=0)
                if target <= now_i:
                    target += timedelta(days=1)
                secs = int((target - now_i).total_seconds())
            if secs > 5 and not step.get("_test_now"):
                run_ref = ctx.setdefault("_run", {})
                run_ref["next_wake_at"] = time.time() + secs
                return True, {"wait_s": secs}, "__PARK__"
            await asyncio.sleep(min(secs, 5))
            return True, {"wait_s": secs}, ""
        if typ == "notify":
            n_max = _NOTIFY_MAX
            if ctx.get("notify", 0) >= n_max:
                return True, {"skipped": "notify cap"}, ""
            ctx["notify"] = ctx.get("notify", 0) + 1
            _notify(conv, str(resolve(step.get("text") or "", ctx))[:800])
            return True, {"sent": True}, ""
        if typ == "approval":
            return True, None, "__APPROVE__"
        if typ == "set":
            ctx["vars"][str(step.get("name"))] = resolve(step.get("value"), ctx)
            return True, {"set": str(step.get("name"))}, ""
        if typ == "http":
            body = await _http_step(tenant_id, step, ctx)
            ctx["steps"][sid] = {"output": body}
            return True, body, ""
        return False, None, f"unknown step type '{typ}'"
    except ToolError as e:
        return False, None, str(e)
    except Exception as e:
        return False, None, f"{type(e).__name__}: {e}"
    finally:
        _ = t0  # timing is taken by the caller for the log row


async def _http_step(tenant_id: str, step: dict, ctx: dict) -> dict:
    import httpx
    from . import scrape_tools as st
    url = str(resolve(step.get("url") or "", ctx)).strip()
    guard = await asyncio.to_thread(st._guard_url, url)
    method = str(step.get("method") or "GET").upper()
    headers = {str(k): str(v) for k, v in (resolve(step.get("headers") or {}, ctx) or {}).items()}
    body = resolve(step.get("body"), ctx) if method == "POST" else None
    timeout = httpx.Timeout(15.0)

    def go():
        if method == "POST":
            r = httpx.post(guard, json=body, headers=headers, timeout=timeout, follow_redirects=True)
        else:
            r = httpx.get(guard, headers=headers, timeout=timeout, follow_redirects=True)
        text = r.text[:_HTTP_CHARS]
        try:
            parsed = r.json()
        except Exception:
            parsed = None
        return {"status": r.status_code, "json": parsed, "text": None if parsed is not None else text[:2000]}

    return await asyncio.to_thread(go)


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
        err = ""
        while run["cursor"] < len(steps):
            if time.time() - float(run["started_at"]) > timeout_s:
                err = f"run wall-clock cap ({timeout_s}s) passed — stopped"
                break
            step = steps[run["cursor"]]
            t0 = time.time()
            ok, out, serr = await _exec_one(tenant_id, conv, step, ctx, run_id)
            ms = int((time.time() - t0) * 1000)
            if serr == "__PARK__":
                _log_step(run, step["id"], step["type"], "sleeping", ms, output=out, version=int(step.get("v") or 1))
                run["status"] = "sleeping"
                run["pause_reason"] = "sleeping"          # v0.512: the typed pause reason (Dify's PauseReason idea)
                run["next_wake_at"] = ctx.get("_run", {}).get("next_wake_at")
                run["cursor"] += 1  # the wait IS the step doing its job; the wake resumes AFTER it
                _save_checkpoint(tenant_id, run)
                return
            if serr == "__APPROVE__":
                _log_step(run, step["id"], step["type"], "waiting_approval", ms, version=int(step.get("v") or 1))
                run["status"] = "waiting_approval"
                run["pause_reason"] = "waiting_approval"  # v0.512: typed, not implied
                _save_checkpoint(tenant_id, run)
                hrs = int(getattr(s, "dhara_approval_hours", 24))
                _notify(conv, f'DHARA "{wf["name"]}" (run {run_id}) is waiting: {str(step.get("question") or "shall I go ahead?")} '
                              f'Reply "yes" in the chat (or "stop" to cancel) within {hrs} hours.')
                return
            if serr == "__STOP__":
                # v0.999.87 a filter step that did not pass: the run ends cleanly here (not an error)
                _log_step(run, step["id"], step["type"], "filtered", ms, output=out, version=int(step.get("v") or 1))
                run["cursor"] = len(steps)
                _save_checkpoint(tenant_id, run)
                _finish(tenant_id, run_id, run, len(steps), "done", "", acc)
                _after_run(tenant_id, wf, "done", "", run_id)
                return
            _log_step(run, step["id"], step["type"], "ok" if ok else "error", ms,
                      output=(out if ok and out is not None else None), error="" if ok else serr,
                      version=int(step.get("v") or 1))
            if ok:
                ctx.pop("_retries_" + str(step["id"]), None)
                run["cursor"] += 1
            elif step.get("soft"):
                run["cursor"] += 1
            else:
                # v0.999.87 HOOLA ROUTE: the step's error directive decides (a step inside a route may carry its own)
                oe = ctx.pop("_sub_on_error", None) or step.get("on_error") or {}
                do = str(oe.get("do") or "")
                if do == "ignore":
                    run["steps_log"][-1]["status"] = "ignored"
                    run["cursor"] += 1
                elif do == "resume":
                    ctx["steps"][str(oe.get("step") or step["id"])] = {"output": resolve(oe.get("value"), ctx)}
                    run["steps_log"][-1]["status"] = "resumed"
                    run["cursor"] += 1
                elif do == "commit":
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
                        err += " (rolled back: the run is marked failed; steps that already ran, like a sent message, cannot be undone)"
                    break
            _save_checkpoint(tenant_id, run)
            if polite_s:
                await asyncio.sleep(polite_s)
        if run["cursor"] >= len(steps) and not err:
            _save_checkpoint(tenant_id, run)
            _finish(tenant_id, run_id, run, len(steps), "done", "", acc)
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
        if er and er != wf["name"]:
            target = get_workflow(tenant_id, name=er)
            if target is not None and target.get("enabled"):
                create_run(tenant_id, target, vars_={"failed_route": wf["name"], "failed_run": run_id,
                                                     "error": str(err)[:500]})
    except Exception:   # noqa: BLE001
        pass


# --------------------------------------------------------------------------- claim + tick (crawl-jobs shape)

def _claim(tenant_id: str, run_id: str, tries_max: int) -> bool:
    con = _con(tenant_id)
    try:
        cur = con.execute("UPDATE runs SET tries = tries + 1, status = 'running', updated_at = ? "
                          "WHERE id = ? AND status IN ('queued','sleeping') AND tries < ?",
                          (time.time(), run_id, int(tries_max)))
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
            nxt = next_due(wf, from_ts=now_)
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
    spec = wf.get("trigger_spec") or {}
    settings = wf.get("settings") or {}
    modern = any(k in spec for k in ("timezone", "every_minutes", "days", "monthdays", "dates", "once", "quiet",
                                      "skip_holidays", "end_date")) or bool(settings.get("timezone"))
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
    for at in spec.get("at") or []:
        if _hm(at) is None:
            raise ToolError(f"Time '{at}' is not HH:MM (24-hour)")
    for dd in spec.get("days") or []:
        if str(dd).lower()[:3] not in _DAYS:
            raise ToolError(f"Day '{dd}' is not one of mon tue wed thu fri sat sun")
    for md in spec.get("monthdays") or []:
        if not str(md).isdigit() or not 1 <= int(md) <= 31:
            raise ToolError(f"Day of month '{md}' must be 1-31")
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
                if _claim(tenant, rid, tries_max):
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

def webhook_enqueue(token: str, body: dict) -> dict:
    """POST /api/dhara/hook/{token}. Returns an honest dict; never raises (route maps ok=False)."""
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
            if hit is not None and hit.get("trigger_kind") == "webhook" and hit.get("enabled", 0):
                wf, tenant = hit, t
                break
    if wf is None:
        return {"ok": False, "status": 401, "error": "token not found / workflow is off"}
    con = _con(tenant)
    try:
        last = con.execute("SELECT created_at FROM runs WHERE workflow_id = ? ORDER BY created_at DESC LIMIT 1",
                           (wf["id"],)).fetchone()
    finally:
        con.close()
    if last is not None and time.time() - float(last["created_at"]) < _TOKEN_MIN_RATE_S:
        return {"ok": False, "status": 429, "error": "webhook throttle (10/min per workflow)"}
    if _over_daily_cap(tenant, wf):
        return {"ok": False, "status": 429, "error": "this route reached its runs-per-day limit"}
    rid = create_run(tenant, wf, vars_={"body": body})
    return {"ok": True, "status": 202, "run_id": rid, "workflow": wf["name"]}


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


async def dhara_save(ctx: Ctx, name, steps, description="", trigger="manual", trigger_spec=None, settings=None, **_):
    """Create/update one of her workflows: validated hard BEFORE anything is stored."""
    from ..config import get_settings
    s = get_settings()
    if not getattr(s, "dhara_enabled", True):
        raise ToolError("DHARA is turned off on this server (dhara_enabled=false)")
    nm = str(name or "").strip().lower().replace(" ", "_")
    if not nm or not _PATH_RE.match(nm):
        raise ToolError("Give the workflow name in lowercase_with_underscores (like daily_morning_report)")
    kind = str(trigger or "manual").lower()
    if kind not in ("manual", "schedule", "webhook"):
        raise ToolError("trigger manual | schedule | webhook (v1)")
    spec = dict(trigger_spec or {})
    st_norm = validate_settings(settings) if settings is not None else None
    if kind == "schedule":
        spec = validate_schedule(spec, st_norm)   # v0.999.87: any time zone, days, monthdays, dates, quiet, holidays
    if kind == "webhook":
        spec = {}
    norm = validate_steps(steps)
    wf, created = save_workflow(ctx.tenant_id, nm, str(description or ""), kind, spec, norm,
                                str(ctx.conversation_id or ""), settings=st_norm)
    if kind == "schedule":
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
    if not wf.get("enabled", 0):
        raise ToolError(f'"{wf["name"]}" is disabled right now — turn it on with dhara_control action=enable')
    v = dict(vars) if isinstance(vars, dict) else {}
    rid = create_run(ctx.tenant_id, wf, vars_=v)
    t = asyncio.ensure_future(execute_run(ctx.tenant_id, rid))
    _TASKS.add(t)
    t.add_done_callback(lambda _t: _TASKS.discard(_t))
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
        r["steps_log"].append({"id": str(r["cursor"]), "type": "approval", "status": "approved", "at": time.strftime("%H:%M:%S")})
        update_run(ctx.tenant_id, r["id"], status="queued", tries=0,
                   cursor=int(r["cursor"]) + 1, steps_log=r["steps_log"], pause_reason=None)
        t = asyncio.ensure_future(execute_run(ctx.tenant_id, r["id"]))
        _TASKS.add(t)
        t.add_done_callback(lambda _t: _TASKS.discard(_t))
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
        t = asyncio.ensure_future(execute_run(ctx.tenant_id, r["id"]))
        _TASKS.add(t)
        t.add_done_callback(lambda _t: _TASKS.discard(_t))
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
        if kind not in ("manual", "schedule", "webhook"):
            raise ToolError("trigger manual | schedule | webhook (v1)")
        spec = dict(dsl.get("trigger_spec") or {})
        if kind == "webhook":
            spec = {}   # a new token is minted here and shown ONCE in this reply
        st_imp = validate_settings(dsl.get("settings") or {})
        if kind == "schedule":
            spec = validate_schedule(spec, st_imp)
        if get_workflow(ctx.tenant_id, name=nm) is not None:
            return {"ok": False, "already_exists": True, "existing": nm,
                    "note": f"'{nm}' already exists — to bring it in under another name "
                            f"give new_name='{nm}_2' (or rename the old one first)"}
        norm_steps = validate_steps(dsl.get("steps"))   # THE SAME hard validator as dhara_save
        wf, _created = save_workflow(ctx.tenant_id, nm, str(dsl.get("description") or "")[:500], kind, spec,
                                     norm_steps, str(ctx.conversation_id or ""), settings=st_imp)
        set_enabled(ctx.tenant_id, wf["id"], False)      # imported lands BAND — she reads, she enables
        if kind == "schedule":
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
        "wait (duration_s / until HH:MM), notify (a chat line to her), approval (pauses until SHE says yes), set (a "
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
        "time zone and currency - never assume India."),
     "input_schema": {"type": "object", "properties": {
         "name": {"type": "string", "description": "lowercase_with_underscores, unique, e.g. daily_morning_notice_check"},
         "steps": {"type": "array", "description": "The steps: [{id, type, ...}] — see the tool guide for each type's fields"},
         "description": {"type": "string", "description": "One line: what it does"},
         "trigger": {"type": "string", "enum": ["manual", "schedule", "webhook"], "description": "Default manual"},
         "trigger_spec": {"type": "object", "description": "schedule: {timezone: 'Europe/London', days: ['mon','fri'], at: ['09:30'], quiet: {from: '21:00', to: '08:00'}, skip_holidays: 'GB'} or {every_minutes: 30} or {every_hours: 24, at: ['09:30']}; webhook: none"},
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
