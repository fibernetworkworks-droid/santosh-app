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

_STEP_TYPES = ("tool", "code", "condition", "loop", "wait", "notify", "approval", "set", "http")
_COND_OPS = ("eq", "ne", "gt", "lt", "contains", "empty")
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
                  trigger_spec: dict, steps: list, conversation_id: str = "") -> tuple[dict, bool]:
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
        else:
            wid = old["id"]
            th = token_hash if trigger_kind == "webhook" else (old["token_hash"] if old["trigger_kind"] == "webhook" else None)
            con.execute("UPDATE workflows SET description=?, trigger_kind=?, trigger_spec=?, token_hash=?, steps=?, "
                        "updated_at=? WHERE id=?",
                        (description[:500], trigger_kind, json.dumps(trigger_spec), th, json.dumps(steps), now_, wid))
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
        gone = con.execute("DELETE FROM runs WHERE status NOT IN ('queued','running','sleeping','waiting_approval') "
                           "AND updated_at < ?", (cut,)).rowcount
        extra = con.execute("SELECT id FROM runs WHERE status NOT IN ('queued','running','sleeping','waiting_approval') "
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
            raise ToolError("Har step ek object hona chahiye ({}), mila: " + type(s).__name__)
        out.append((s, depth))
        for key in ("then", "else", "body"):
            sub = s.get(key)
            if sub:
                out.extend(_walk_steps(sub, depth + 1))
    return out


def validate_steps(steps: list) -> list[dict]:
    """Hard validation. Returns the normalised steps or raises ToolError with the FIRST problem."""
    from ..config import get_settings
    s = get_settings()
    max_steps = int(getattr(s, "dhara_max_steps", _MAX_STEPS))
    loop_max = int(getattr(s, "dhara_loop_max", _LOOP_MAX))
    if not isinstance(steps, list) or not steps:
        raise ToolError("steps ek non-empty list honi chahiye")
    if len(json.dumps(steps)) > _GRAPH_CHARS:
        raise ToolError(f"Workflow graph bohot bada hai ({len(json.dumps(steps))} chars; cap {_GRAPH_CHARS})")
    top = [s for s in steps]
    if len(top) > max_steps:
        raise ToolError(f"Zyada se zyada {max_steps} steps (mila {len(top)})")
    seen: set[str] = set()
    for st_, depth in _walk_steps(top):
        if depth > _MAX_DEPTH:
            raise ToolError("Condition/loop ke andar ek hi level tak steps chal sakte hain (nesting cap 1)")
        sid = str(st_.get("id") or "").strip()
        typ = str(st_.get("type") or "").strip().lower()
        if not sid or not _PATH_RE.match(sid):
            raise ToolError(f"Har step ko ek chhota id chahiye (lowercase_with_underscores) — mila: {sid!r}")
        if sid in seen:
            raise ToolError(f"Step id '{sid}' do baar hai — ids unique rakhein")
        seen.add(sid)
        if typ not in _STEP_TYPES:
            raise ToolError(f"Step '{sid}': anjaan type '{typ}' — inme se chunein: {', '.join(_STEP_TYPES)}")
        if typ == "tool":
            name = str(st_.get("name") or "").strip()
            if not name:
                raise ToolError(f"Step '{sid}': tool step ko tool ka naam chahiye")
            if name in _TOOL_STEP_DENY:
                raise ToolError(f"Step '{sid}': {name} ek same-turn card hai — background run mein nahi chalta")
        elif typ == "code":
            if not str(st_.get("code") or "").strip():
                raise ToolError(f"Step '{sid}': code step mein python code do")
        elif typ == "condition":
            if str(st_.get("op") or "") not in _COND_OPS:
                raise ToolError(f"Step '{sid}': op inme se hona chahiye: {', '.join(_COND_OPS)}")
            if not isinstance(st_.get("then"), list) and not isinstance(st_.get("else"), list):
                raise ToolError(f"Step '{sid}': condition mein then ya else steps ki list do")
        elif typ == "loop":
            if not isinstance(st_.get("body"), list) or not st_.get("body"):
                raise ToolError(f"Step '{sid}': loop mein body steps ki list do")
            if "items" not in st_:
                raise ToolError(f"Step '{sid}': loop ko items chahiye (expression jo list de)")
        elif typ == "wait":
            if not st_.get("duration_s") and not st_.get("until"):
                raise ToolError(f"Step '{sid}': wait ko duration_s (<= 3600) ya until 'HH:MM' do")
        elif typ == "notify":
            if not str(st_.get("text") or "").strip():
                raise ToolError(f"Step '{sid}': notify ko text chahiye")
        elif typ == "approval":
            if not str(st_.get("question") or "").strip():
                raise ToolError(f"Step '{sid}': approval ko question chahiye")
        elif typ == "set":
            if not _PATH_RE.match(str(st_.get("name") or "")):
                raise ToolError(f"Step '{sid}': set ko variable ka naam do (lowercase_with_underscores)")
        elif typ == "http":
            if not str(st_.get("url") or "").strip():
                raise ToolError(f"Step '{sid}': http ko url chahiye")
            if str(st_.get("method") or "GET").upper() not in ("GET", "POST"):
                raise ToolError(f"Step '{sid}': http method sirf GET ya POST (v1)")
        # expression size cap on every string field
        for v in st_.values():
            if isinstance(v, str) and len(v) > _EXPR_CHARS:
                raise ToolError(f"Step '{sid}': expression/text bohot lamba (cap {_EXPR_CHARS} chars)")
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
        raise ToolError(f"Expression bohot lamba (cap {_EXPR_CHARS})")
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
                        soft_parent: bool) -> tuple[bool, str]:
    """Condition/loop bodies: run their steps inline (atomic with the parent step). Returns (ok, error)."""
    for sub in _flat_steps(sublist):
        ok, out, err = await _exec_one(tenant_id, conv, sub, ctx, run_id)
        if not ok:
            if soft_parent or sub.get("soft"):
                _log_step({"steps_log": []}, sub.get("id", "?"), sub.get("type", "?"), "error", 0, error=err)
                continue
            return False, err
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
                return False, None, f"tool '{name}' registry mein nahi hai"
            args = resolve(step.get("args") or {}, ctx)
            if not isinstance(args, dict):
                return False, None, "tool args ek object hone chahiye"
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
            left = resolve(step.get("left"), ctx)
            right = resolve(step.get("right"), ctx)
            op = str(step.get("op"))
            branch = step.get("then") if _cmp(left, op, right) else step.get("else")
            if not isinstance(branch, list):
                return True, {"branch": "skipped (no steps)"}, ""
            ok, err = await _exec_sublist(tenant_id, conv, branch, ctx, run_id, bool(step.get("soft")))
            if not ok:
                return False, None, err
            ctx["steps"][sid] = {"output": {"branch": "then" if _cmp(left, op, right) else "else"}}
            return True, ctx["steps"][sid]["output"], ""
        if typ == "loop":
            items = resolve(step.get("items"), ctx)
            if not isinstance(items, list):
                return False, None, "loop items ne list nahi di"
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
        return False, None, f"anjaan step type '{typ}'"
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
                err = f"run wall-clock cap ({timeout_s}s) paar — ruk gaya"
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
                _notify(conv, f'DHARA "{wf["name"]}" (run {run_id}) ruki hai: {str(step.get("question") or "aage badhun?")} '
                              f'Chat mein "haan" likhiye (ya rokna ho to "rok do"); {hrs} ghante ke andar.')
                return
            _log_step(run, step["id"], step["type"], "ok" if ok else "error", ms,
                      output=(out if ok and out is not None else None), error="" if ok else serr,
                      version=int(step.get("v") or 1))
            if ok:
                run["cursor"] += 1
            elif step.get("soft"):
                run["cursor"] += 1
            else:
                err = f"step '{step['id']}' ({step['type']}): {serr}"
                break
            _save_checkpoint(tenant_id, run)
            if polite_s:
                await asyncio.sleep(polite_s)
        if run["cursor"] >= len(steps) and not err:
            _save_checkpoint(tenant_id, run)
            _finish(tenant_id, run_id, run, len(steps), "done", "", acc)
            _notify(conv, f'DHARA "{wf["name"]}" poora ho gaya ({len(steps)} steps, run {run_id}).'
                    f'{" (missed schedule se) " if run.get("missed") else ""}')
        else:
            run["status"] = "failed"
            run["error"] = err
            _save_checkpoint(tenant_id, run)
            _finish(tenant_id, run_id, run, len(steps), "failed", err, acc, error=err[:800])
            _notify(conv, f'DHARA "{wf["name"]}" ruk gaya: {err[:300]}')
    except Exception as e:  # the lane never breaks the worker
        try:
            update_run(tenant_id, run_id, status="failed", error=f"{type(e).__name__}: {e}"[:800])
        except Exception:
            pass
    finally:
        _RUNNING.discard(key)


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
            con.execute("UPDATE workflows SET next_due_at = ? WHERE id = ?", (nxt, wf["id"]))
            out.append((wf, missed))
        con.commit()
        return out
    finally:
        con.close()


def next_due(wf: dict, from_ts: float | None = None) -> float | None:
    """trigger_spec: {"every_hours": N, "at": ["HH:MM", ...]} in IST. None = not schedulable."""
    spec = wf.get("trigger_spec") or {}
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
                con.execute("UPDATE runs SET status = 'failed', pause_reason = 'approval_expired', "
                            "error = 'approval ka intezaar khatam (dhara_approval_hours paar)', updated_at = ? "
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
            con = _con(tenant)
            try:
                con.execute("UPDATE runs SET status = 'failed', error = 'tries poore (dhara_tries) — run chhoda gaya', "
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
        return {"ok": False, "status": 503, "error": "DHARA webhook band hai"}
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
        return {"ok": False, "status": 401, "error": "token nahi mila / workflow band hai"}
    con = _con(tenant)
    try:
        last = con.execute("SELECT created_at FROM runs WHERE workflow_id = ? ORDER BY created_at DESC LIMIT 1",
                           (wf["id"],)).fetchone()
    finally:
        con.close()
    if last is not None and time.time() - float(last["created_at"]) < _TOKEN_MIN_RATE_S:
        return {"ok": False, "status": 429, "error": "webhook throttle (10/min per workflow)"}
    rid = create_run(tenant, wf, vars_={"body": body})
    return {"ok": True, "status": 202, "run_id": rid, "workflow": wf["name"]}


# --------------------------------------------------------------------------- tools

def _fmt_wf(wf: dict, run: dict | None = None) -> dict[str, Any]:
    out = {"workflow_id": wf["id"], "name": wf["name"], "trigger": wf["trigger_kind"],
           "enabled": bool(wf.get("enabled")), "steps": len(wf.get("steps") or []),
           "description": (wf.get("description") or "")[:200]}
    if wf["trigger_kind"] == "schedule":
        out["next_due_at"] = wf.get("next_due_at")
    if run is not None:
        out["last_run"] = {"run_id": run["id"], "status": run["status"], "cursor": run["cursor"],
                           "steps_logged": len(run.get("steps_log") or []), "error": (run.get("error") or "")[:200]}
    return out


async def dhara_save(ctx: Ctx, name, steps, description="", trigger="manual", trigger_spec=None, **_):
    """Create/update one of her workflows: validated hard BEFORE anything is stored."""
    from ..config import get_settings
    s = get_settings()
    if not getattr(s, "dhara_enabled", True):
        raise ToolError("DHARA is server par band hai (dhara_enabled=false)")
    nm = str(name or "").strip().lower().replace(" ", "_")
    if not nm or not _PATH_RE.match(nm):
        raise ToolError("Workflow ka naam lowercase_with_underscores dein (jaise roz_subah_report)")
    kind = str(trigger or "manual").lower()
    if kind not in ("manual", "schedule", "webhook"):
        raise ToolError("trigger manual | schedule | webhook (v1)")
    spec = dict(trigger_spec or {})
    if kind == "schedule":
        if not (spec.get("every_hours") or spec.get("at")):
            raise ToolError("schedule trigger ko every_hours (1-720) ya at ['HH:MM', ...] (IST) dein")
    if kind == "webhook":
        spec = {}
    norm = validate_steps(steps)
    wf, created = save_workflow(ctx.tenant_id, nm, str(description or ""), kind, spec, norm,
                                str(ctx.conversation_id or ""))
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
    out["note"] = ("Workflow ban gaya — dhara_run se abhi chala kar dekhein"
                   if created else "Workflow update ho gaya (wahi naam, wahi id)")
    if wf["trigger_kind"] == "webhook":
        out["webhook_note"] = ("Token sirf ab dikhaya jayega — isko sambhal kar rakhein (dobara nahi milega): "
                               + webhook_token_reveal(ctx.tenant_id, wf["id"])) if created else \
                              "Webhook token wahi purana hai (naya nahi bana)"
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
        raise ToolError("DHARA is server par band hai (dhara_enabled=false)")
    wf = get_workflow(ctx.tenant_id, name=str(name or "").lower(), wf_id=str(workflow_id or ""))
    if wf is None:
        raise ToolError("Yeh naam ka workflow nahi mila — dhara_list se dekhein")
    if not wf.get("enabled", 0):
        raise ToolError(f'"{wf["name"]}" abhi disabled hai — dhara_control action=enable se chalu karein')
    v = dict(vars) if isinstance(vars, dict) else {}
    rid = create_run(ctx.tenant_id, wf, vars_=v)
    t = asyncio.ensure_future(execute_run(ctx.tenant_id, rid))
    _TASKS.add(t)
    t.add_done_callback(lambda _t: _TASKS.discard(_t))
    return {"run_id": rid, "workflow": wf["name"], "status": "queued",
            "note": "Run shuru — dhara_runs run_id=" + rid + " se har step ka haal dekhein"}


async def dhara_runs(ctx: Ctx, run_id="", workflow_id="", limit=8, **_):
    """Recent runs (status, steps done); run_id= gives the full step-by-step log of one run."""
    if run_id:
        r = get_run(ctx.tenant_id, str(run_id))
        if r is None:
            raise ToolError("Yeh run_id nahi mila")
        return _masked({"run_id": r["id"], "workflow": r["wf_name"], "status": r["status"],
                "cursor": r["cursor"], "error": r.get("error") or "",
                "pause_reason": r.get("pause_reason") or "",
                "summary": r.get("summary"),
                "steps_log": r["steps_log"][-40:],
                "note": ("Abhi chal raha hai — thodi der baad phir dekhein"
                         if r["status"] in ("queued", "running") else "")})
    wf_id = str(workflow_id or "")
    if wf_id and get_workflow(ctx.tenant_id, wf_id=wf_id) is None:
        raise ToolError("Yeh workflow_id nahi mila")
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
            raise ToolError("Workflow nahi mila — dhara_list se naam dekhein")
        set_enabled(ctx.tenant_id, wf["id"], act == "enable")
        return {"workflow": wf["name"], "enabled": act == "enable",
                "note": "Trigger chalu ho gaya" if act == "enable" else "Trigger band — dhara_run se phir bhi manually chala sakte hain"}
    if act == "stop":
        r = get_run(ctx.tenant_id, str(run_id)) if run_id else None
        if r is None:
            wf = get_workflow(ctx.tenant_id, name=str(name or "").lower(), wf_id=str(workflow_id or ""))
            r = latest_run(ctx.tenant_id, wf["id"]) if wf else None
        if r is None:
            raise ToolError("Run nahi mila — run_id (ya workflow ka naam) dein")
        if r["status"] in ("done", "failed", "stopped"):
            return {"run_id": r["id"], "status": r["status"], "note": "Yeh run pehle hi ruk chuka tha"}
        update_run(ctx.tenant_id, r["id"], status="stopped", error="uski Malika ne rokna kaha")
        wf = get_workflow(ctx.tenant_id, wf_id=r["workflow_id"])
        _finish(ctx.tenant_id, r["id"], r, len(wf["steps"]) if wf else 0, "stopped", "uski Malika ne rokna kaha",
                error="uski Malika ne rokna kaha")
        return {"run_id": r["id"], "status": "stopped", "note": "Run ke beech mein ruk gaya — jo steps ho chuke hain woh log mein hain"}
    if act == "approve":
        r = get_run(ctx.tenant_id, str(run_id)) if run_id else None
        if r is None:
            raise ToolError("approve ke liye run_id dein (dhara_runs se)")
        if r["status"] != "waiting_approval":
            return {"run_id": r["id"], "status": r["status"], "note": "Yeh run approval ka intezaar nahi kar raha tha"}
        # her haan = the gate is passed: the cursor moves PAST the approval step, else the resumed run
        # would hit the same gate and park forever (the resume executes from the checkpoint).
        r["steps_log"].append({"id": str(r["cursor"]), "type": "approval", "status": "approved", "at": time.strftime("%H:%M:%S")})
        update_run(ctx.tenant_id, r["id"], status="queued", tries=0,
                   cursor=int(r["cursor"]) + 1, steps_log=r["steps_log"], pause_reason=None)
        t = asyncio.ensure_future(execute_run(ctx.tenant_id, r["id"]))
        _TASKS.add(t)
        t.add_done_callback(lambda _t: _TASKS.discard(_t))
        return {"run_id": r["id"], "status": "queued", "note": "Uski haan mil gayi — run wahin se aage badha"}
    if act == "retry":
        # v0.512 (the Dify node-retry idea): a failed/stopped run re-queues FROM ITS CURSOR — the
        # checkpoint law makes this safe by construction: a finished step never runs twice.
        r = get_run(ctx.tenant_id, str(run_id)) if run_id else None
        if r is None:
            wf = get_workflow(ctx.tenant_id, name=str(name or "").lower(), wf_id=str(workflow_id or ""))
            r = latest_run(ctx.tenant_id, wf["id"]) if wf else None
        if r is None:
            raise ToolError("retry ke liye run_id (ya workflow ka naam) dein")
        if r["status"] not in ("failed", "stopped"):
            return {"run_id": r["id"], "status": r["status"],
                    "note": "retry sirf ruke hue (failed / stopped) run par chalta hai"}
        if (r.get("pause_reason") or "") == "approval_expired":
            return {"run_id": r["id"], "status": r["status"], "ok": False,
                    "note": "approval ka time nikal gaya tha — gate ke aage dobara approve kiye bina nahi badhte; "
                            "workflow ko dhara_run se nayi run mein chalayein"}
        r["steps_log"].append({"id": str(r["cursor"]), "type": "retry", "status": "retry",
                               "at": time.strftime("%H:%M:%S")})
        update_run(ctx.tenant_id, r["id"], status="queued", tries=0, error="", pause_reason=None,
                   steps_log=r["steps_log"])
        t = asyncio.ensure_future(execute_run(ctx.tenant_id, r["id"]))
        _TASKS.add(t)
        t.add_done_callback(lambda _t: _TASKS.discard(_t))
        return {"run_id": r["id"], "status": "queued",
                "note": "Wahin se chalu (checkpoint) — jo steps ho chuke hain woh dobara nahi chalenge"}
    raise ToolError("action: enable | disable | stop | approve | retry")


async def dhara_list(ctx: Ctx, **_):
    """Her workflows with trigger state and the last run's haal — the mini-board."""
    from ..config import get_settings
    s = get_settings()
    if not getattr(s, "dhara_enabled", True):
        raise ToolError("DHARA is server par band hai (dhara_enabled=false)")
    wfs = list_workflows(ctx.tenant_id, 20)
    out = []
    for wf in wfs:
        last = latest_run(ctx.tenant_id, wf["id"])
        out.append(_fmt_wf(wf, last))
    return {"count": len(out), "workflows": out,
            "note": ("Naya banane ke liye dhara_save use karein" if out else "Abhi koi workflow nahi — pehla dhara_save se banao")}


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
           "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    return env


async def dhara_dsl(ctx: Ctx, action: str, name: str = "", workflow_id: str = "", dsl=None, new_name: str = "", **_):
    """export (workflow -> a portable JSON envelope, secrets-free) | import (the SAME hard validator,
    lands disabled, she enables it). Backup, migrate between tenants, share a proven recipe."""
    from ..config import get_settings
    s = get_settings()
    if not getattr(s, "dhara_enabled", True) or not getattr(s, "dhara_dsl_enabled", True):
        raise ToolError("DHARA DSL is server par band hai (dhara_dsl_enabled=false)")
    max_kb = int(getattr(s, "dhara_dsl_max_kb", 64) or 64)
    if str(action).lower() == "export":
        wf = get_workflow(ctx.tenant_id, name=str(name or "").lower(), wf_id=str(workflow_id or ""))
        if wf is None:
            raise ToolError("Yeh naam ka workflow nahi mila — dhara_list se dekhein")
        env = dsl_export(ctx.tenant_id, wf)
        raw = json.dumps(env, ensure_ascii=False)
        if len(raw.encode()) > max_kb * 1024:
            raise ToolError(f"Export bohot bada hai ({len(raw.encode()) // 1024} KB; cap {max_kb} KB) — "
                            "workflow chhote hisso mein rakhein")
        return {"ok": True, "dsl": env, "bytes": len(raw.encode()),
                "note": "Yeh file sambhal kar rakhein — isme uske workflow ke steps hain, RAAZ nahi "
                        "(webhook ka token kabhi export mein nahi jaata). Dusre tenant mein lene ke liye: "
                        "dhara_dsl action=import dsl=<yehi envelope>"}
    if str(action).lower() == "import":
        if isinstance(dsl, str):
            try:
                dsl = json.loads(dsl)
            except Exception:
                raise ToolError("dsl ek JSON object (ya uska JSON string) hona chahiye")
        if not isinstance(dsl, dict) or dsl.get("dhara_dsl") != _DSL_VERSION:
            raise ToolError(f"Yeh DHARA DSL file nahi lagti (dhara_dsl={_DSL_VERSION} chahiye)")
        raw = json.dumps(dsl, ensure_ascii=False)
        if len(raw.encode()) > max_kb * 1024:
            raise ToolError(f"DSL file bohot badi hai (cap {max_kb} KB)")
        nm = str(new_name or dsl.get("name") or "").strip().lower().replace(" ", "_")
        if not nm or not _PATH_RE.match(nm):
            raise ToolError("Workflow ka naam lowercase_with_underscores dein")
        kind = str(dsl.get("trigger") or "manual").lower()
        if kind not in ("manual", "schedule", "webhook"):
            raise ToolError("trigger manual | schedule | webhook (v1)")
        spec = dict(dsl.get("trigger_spec") or {})
        if kind == "webhook":
            spec = {}   # a new token is minted here and shown ONCE in this reply
        if kind == "schedule" and not (spec.get("every_hours") or spec.get("at")):
            raise ToolError("schedule trigger ko every_hours ya at ['HH:MM', ...] chahiye")
        if get_workflow(ctx.tenant_id, name=nm) is not None:
            return {"ok": False, "already_exists": True, "existing": nm,
                    "note": f"'{nm}' naam ka workflow pehle se hai — doosre naam se laane ke liye "
                            f"new_name='{nm}_2' dein (ya pehle uska naam badlein)"}
        norm_steps = validate_steps(dsl.get("steps"))   # THE SAME hard validator as dhara_save
        wf, _created = save_workflow(ctx.tenant_id, nm, str(dsl.get("description") or "")[:500], kind, spec,
                                     norm_steps, str(ctx.conversation_id or ""))
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
        out["note"] = "Import ho gaya lekin BAND hai — steps dekh kar dhara_control action=enable se chalu karein"
        if kind == "webhook":
            out["webhook_note"] = ("Naya webhook token (sirf ek baar dikhega): "
                                   + webhook_token_reveal(ctx.tenant_id, wf["id"]))
        return out
    raise ToolError("action: export | import")


DHARA_TOOLS = [
    {"name": "dhara_save", "description": (
        "Create or update one of her WORKFLOWS (v0.502, the n8n idea house-sized): a named, saved graph of steps "
        "that runs on a trigger without anyone asking again. Steps (max 40): tool (ANY registered tool by name + args), "
        "code (python in the pylab sandbox), condition (left/op/right with then/else), loop (items + body, cap 50), "
        "wait (duration_s / until HH:MM), notify (a chat line to her), approval (pauses until SHE says haan), set (a "
        "variable), http (SSRF-guarded GET/POST). Expressions like {{steps.get_data.output.total}} / {{vars.x}} / "
        "{{item}} / {{now}}. Triggers: manual | schedule (every_hours + at ['HH:MM'] IST) | webhook (token minted "
        "once). Validate-first: unknown step types / caps / unsafe names are refused with the exact problem."),
     "input_schema": {"type": "object", "properties": {
         "name": {"type": "string", "description": "lowercase_with_underscores, unique, e.g. roz_subah_notice_check"},
         "steps": {"type": "array", "description": "The steps: [{id, type, ...}] — see the tool guide for each type's fields"},
         "description": {"type": "string", "description": "One line: yeh kya karti hai"},
         "trigger": {"type": "string", "enum": ["manual", "schedule", "webhook"], "description": "Default manual"},
         "trigger_spec": {"type": "object", "description": "schedule: {every_hours: 24, at: ['09:30']}; webhook: none"},
         "required": ["name", "steps"]}}},
    {"name": "dhara_run", "description": (
        "Run one of her saved workflows NOW (v0.502). Returns a run_id at once — the run goes in the background "
        "with a checkpoint after every step; dhara_runs shows the haal. Optional vars land as {{vars.x}}. A disabled "
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
        "Turn a workflow's trigger on/off, stop a run, or relay HER haan (v0.502). action=approve run_id=... when "
        "she answered a waiting approval step in chat ('haan') — the run resumes from the same step. action=stop "
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
        "status and error. Use before building (kya pehle se hai) and when she asks 'mere workflows kaise hain'."),
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

DHARA_LABELS = {"dhara_save": "Workflow bana/updat kar raha hoon",
                "dhara_run": "Workflow abhi chala raha hoon",
                "dhara_runs": "Runs ka haal dekh raha hoon",
                "dhara_control": "Workflow control kar raha hoon",
                "dhara_list": "Workflows ki tafteesh kar raha hoon",
                "dhara_dsl": "Workflow file le raha hoon"}

DHARA_HANDLERS = {"dhara_save": dhara_save, "dhara_run": dhara_run, "dhara_runs": dhara_runs,
                  "dhara_control": dhara_control, "dhara_list": dhara_list, "dhara_dsl": dhara_dsl}
