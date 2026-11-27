"""v0.999.234 STEPS YOU CAN TEST (R2 of the Hoola Route plan; owner: "GO R2").

What a step sees and what it gives back, kept beside the route in route_meta (dhara.db):

- data   the newest data of the route: the latest run's full context (every step's whole output - the run log keeps only
         600 characters) with single-step tests made since laid over it. The editor shows it as "What comes in" and
         "What goes out" and lets her drag a field into a step's box.
- pins   test data she pinned: a step's output (used instead of running that step in a TEST run, never a real one) and
         `trigger` = the data a test run starts with (what a webhook would send). Capped.
- test   one step run on that data. Steps that decide (if / else, switch, filter, repeat) report the way they would
         take; a wait and an approval say what they would do; every other step really runs, like Test route.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from . import editor as E

PIN_MAX_BYTES = 200_000
PINS_MAX = 40
DATA_MAX_BYTES = 1_500_000
VIEW_MAX_BYTES = 120_000
NO_PIN = ("condition", "router", "loop", "filter", "approval", "wait", "stop", "respond")


def _cols(con) -> None:
    for col in ("pins TEXT DEFAULT '{}'", "data TEXT DEFAULT '{}'"):
        try:
            con.execute(f"ALTER TABLE route_meta ADD COLUMN {col}")
        except Exception:   # noqa: BLE001  (already there)
            pass


def _read(tenant: str, wf_id: str) -> tuple[dict, dict]:
    con = E._con(tenant)
    try:
        _cols(con)
        r = con.execute("SELECT pins, data FROM route_meta WHERE workflow_id = ?", (wf_id,)).fetchone()
    finally:
        con.close()
    out = []
    for k in ("pins", "data"):
        try:
            out.append(json.loads((r[k] if r is not None else "") or "{}") or {})
        except Exception:   # noqa: BLE001
            out.append({})
    return out[0], out[1]


def _write(tenant: str, wf_id: str, **fields) -> None:
    con = E._con(tenant)
    try:
        _cols(con)
        con.execute("INSERT OR IGNORE INTO route_meta (workflow_id, layout, chat, updated_at) VALUES (?, '{}', '', ?)",
                    (wf_id, time.time()))
        for k, v in fields.items():
            con.execute(f"UPDATE route_meta SET {k} = ?, updated_at = ? WHERE workflow_id = ?", (json.dumps(v), time.time(), wf_id))
        con.commit()
    finally:
        con.close()


def pins(tenant: str, wf_id: str) -> dict:
    return _read(tenant, wf_id)[0]


def _size(v: Any) -> int:
    try:
        return len(json.dumps(v, ensure_ascii=False))
    except Exception:   # noqa: BLE001
        return len(str(v))


def set_pin(tenant: str, wf: dict, sid: str, value: Any) -> dict:
    ids = {s["id"]: s for s in _all(wf.get("steps") or [])}
    if sid != "trigger":
        if sid not in ids:
            raise ValueError("No such step in this route")
        if ids[sid].get("type") in NO_PIN:
            raise ValueError("This step decides or waits - it has no data to pin")
    elif not isinstance(value, dict):
        raise ValueError("The data a test starts with must be an object { }")
    if _size(value) > PIN_MAX_BYTES:
        raise ValueError(f"Pinned data can be up to {PIN_MAX_BYTES // 1000} KB")
    p = pins(tenant, wf["id"])
    p[sid] = value
    p = {k: v for k, v in p.items() if k == "trigger" or k in ids}          # pins of deleted steps go
    if len(p) > PINS_MAX:
        raise ValueError(f"At most {PINS_MAX} pins on one route")
    _write(tenant, wf["id"], pins=p)
    return p


def drop_pin(tenant: str, wf_id: str, sid: str) -> dict:
    p = pins(tenant, wf_id)
    p.pop(sid, None)
    _write(tenant, wf_id, pins=p)
    return p


def _all(steps: list, out: list | None = None) -> list:
    out = [] if out is None else out
    for s in steps or []:
        if not isinstance(s, dict):
            continue
        out.append(s)
        for k in ("then", "else", "body", "fallback"):
            if k != "body" or s.get("type") == "loop":      # a web request's body is data, not steps
                _all(s.get(k) or [], out)
        for rt in s.get("routes") or []:
            if isinstance(rt, dict):
                _all(rt.get("steps") or [], out)
    return out


def _view(v: Any) -> Any:
    """A value for the page: masked, and a very large value cut to a short note (the page shows it as such)."""
    from ..agent import dhara_tools as D
    if _size(v) > VIEW_MAX_BYTES:
        txt = json.dumps(v, ensure_ascii=False)[:VIEW_MAX_BYTES]
        return {"_too_big": True, "first_part": D._masked(txt)}
    return D._masked(v)


def data(tenant: str, wf: dict) -> dict:
    """The newest data of the route: the latest run's whole context, single-step tests made since laid over it."""
    from ..agent import dhara_tools as D
    p, d = _read(tenant, wf["id"])
    last = D.latest_run(tenant, wf["id"])
    vars_, steps, src, at = {}, {}, "", 0.0
    if last is not None:
        ctx = last.get("context") or {}
        vars_ = {k: v for k, v in (ctx.get("vars") or {}).items()}
        steps = {k: {"output": (x or {}).get("output"), "from": "run", "at": last.get("updated_at")}
                 for k, x in (ctx.get("steps") or {}).items() if isinstance(x, dict)}
        src, at = last["id"], float(last.get("updated_at") or 0)
    for k, x in (d.get("steps") or {}).items():
        if float(x.get("at") or 0) > at:
            steps[k] = x
    if float(d.get("vars_at") or 0) > at and isinstance(d.get("vars"), dict):
        vars_ = d["vars"]
    live = {s["id"] for s in _all(wf.get("steps") or [])}
    return {"vars": _view(vars_), "steps": {k: {**x, "output": _view(x.get("output"))} for k, x in steps.items() if k in live},
            "pins": {k: _view(v) for k, v in p.items()}, "run_id": src,
            "status": (last or {}).get("status"), "log": {l.get("id"): {k: l.get(k) for k in ("status", "ms", "error")}
                                                          for l in ((last or {}).get("steps_log") or [])}}


def _keep(tenant: str, wf_id: str, sid: str, output: Any) -> None:
    _, d = _read(tenant, wf_id)
    st = d.get("steps") or {}
    st[sid] = {"output": output, "from": "step test", "at": time.time()}
    while st and _size(st) > DATA_MAX_BYTES:                       # oldest tests go first
        st.pop(min(st, key=lambda k: float(st[k].get("at") or 0)))
    d["steps"] = st
    _write(tenant, wf_id, data=d)


def context_for(tenant: str, wf: dict, use_pins: bool = True) -> dict:
    """The data a single-step test (or a test run) works on: the newest data + her pins."""
    from ..agent import dhara_tools as D
    p, d = _read(tenant, wf["id"])
    last = D.latest_run(tenant, wf["id"])
    ctx: dict[str, Any] = {"vars": {}, "steps": {}, "notify": 0}
    at = 0.0
    if last is not None:
        c = last.get("context") or {}
        ctx["vars"] = dict(c.get("vars") or {})
        ctx["steps"] = {k: v for k, v in (c.get("steps") or {}).items() if isinstance(v, dict)}
        at = float(last.get("updated_at") or 0)
    for k, x in (d.get("steps") or {}).items():
        if float(x.get("at") or 0) > at:
            ctx["steps"][k] = {"output": x.get("output")}
    if use_pins:
        if isinstance(p.get("trigger"), dict):
            ctx["vars"] = dict(p["trigger"])
        for k, v in p.items():
            if k != "trigger":
                ctx["steps"][k] = {"output": v}
        ctx["_pins"] = {k: v for k, v in p.items() if k != "trigger"}
    return ctx


async def test_step(tenant: str, wf: dict, sid: str, use_pins: bool = True) -> dict:
    from ..agent import dhara_tools as D
    from ..agent.tools import ToolError
    step = next((s for s in _all(wf.get("steps") or []) if s.get("id") == sid), None)
    if step is None:
        raise ValueError("No such step in this route - save the route first")
    ctx = context_for(tenant, wf, use_pins)
    ctx.pop("_pins", None)                       # the step under test really runs, even when it has a pin
    loop = next((s for s in _all(wf.get("steps") or []) if s.get("type") == "loop"
                 and any(b.get("id") == sid for b in _all(s.get("body") or []))), None)
    if loop is not None:                         # inside "repeat for each": the first item stands in for {{item}}
        items = D.resolve(loop.get("items"), ctx)
        if isinstance(items, list) and items:
            ctx["item"] = items[0]
    typ = step.get("type")
    t0 = time.time()
    ok, out, err = True, None, ""
    try:
        if typ in ("condition", "filter"):
            if step.get("filter") is not None:
                passed = D.eval_filter(step["filter"], ctx)
            else:
                passed = D._cmp(D.resolve(step.get("left"), ctx), str(step.get("op")), D.resolve(step.get("right"), ctx))
            out = {"passed": bool(passed), "way": ("If yes" if passed else "If no") if typ == "condition" else
                   ("goes on" if passed else "stops here")}
        elif typ == "router" and step.get("ai"):     # v0.999.243: the AI picks the way (a real model call)
            from . import aistep as AS
            pick = await AS.choose(step, ctx, D.resolve)
            out = {"way": pick or ("Anything else" if isinstance(step.get("fallback"), list) else "none - it goes straight on"),
                   "why": (ctx.get("_ai_why") or {}).get(sid, "")}
        elif typ == "router":
            way = None
            for j, rt in enumerate(step.get("routes") or []):
                if rt.get("filter") is None or D.eval_filter(rt["filter"], ctx):
                    way = rt.get("label") or f"Way {j + 1}"
                    break
            out = {"way": way or ("Anything else" if isinstance(step.get("fallback"), list) else "none - it goes straight on")}
        elif typ == "loop":
            items = D.resolve(step.get("items"), ctx)
            if not isinstance(items, list):
                ok, err = False, "The list to go through is not a list with this data"
            else:
                out = {"count": len(items), "items": items[:50]}
        elif typ == "wait":
            if str(step.get("for") or "") == "call":
                out = {"would_wait": "until someone calls the run's resume link ({{vars.resume_url}})",
                       "up_to_hours": round(int(step.get("timeout_s") or 86400) / 3600, 1)}
            elif step.get("amount") not in (None, ""):
                out = {"would_wait": f"{D.resolve(step.get('amount'), ctx)} {step.get('unit') or 'minutes'}"}
            elif step.get("duration_s"):
                out = {"would_wait": f"{D.resolve(step['duration_s'], ctx)} seconds"}
            else:
                out = {"would_wait": f"until {D.resolve(step.get('until'), ctx)}"}
        elif typ == "stop":
            out = {"would_end": "as an error" if str(step.get("as") or "error") == "error" else "as done",
                   "message": str(D.resolve(step.get("message") or "", ctx))}
        elif typ == "respond":
            out = {"would_answer": {"status": D.resolve(step.get("status", 200), ctx), "body": D.resolve(step.get("body"), ctx)},
                   "note": "Only a call to the webhook gets this answer"}
        elif typ == "approval":
            out = {"would_ask": str(D.resolve(step.get("question") or "", ctx))}
        else:
            ok, out, err = await asyncio.wait_for(D._exec_one(tenant, wf.get("conversation_id") or "", step, ctx, "step-test"), 150)
            if ok and typ == "set":              # show the value it set, not only its name
                out = {"set": str(step.get("name")), "value": ctx["vars"].get(str(step.get("name")))}
    except asyncio.TimeoutError:
        ok, err = False, "The step took longer than 150 seconds"
    except ToolError as e:
        ok, err = False, str(e)
    except Exception as e:   # noqa: BLE001
        ok, err = False, f"{type(e).__name__}: {str(e)[:300]}"
    ms = int((time.time() - t0) * 1000)
    if ok and typ not in NO_PIN:
        _keep(tenant, wf["id"], sid, out)
    return {"ok": bool(ok), "output": _view(out), "error": str(err or "")[:600], "ms": ms, "real": typ not in NO_PIN}


def preview(tenant: str, wf: dict, text: str, sid: str = "") -> dict:
    """v0.999.237 ROUTE R3: what a box would become with the route's newest data - for the editor, as she types."""
    from ..agent import dhara_data as DD
    from ..agent import dhara_tools as D
    text = str(text or "")[:4000]
    ctx = context_for(tenant, wf, True)
    ctx.pop("_pins", None)
    if sid:
        loop = next((s for s in _all(wf.get("steps") or []) if s.get("type") == "loop"
                     and any(b.get("id") == sid for b in _all(s.get("body") or []))), None)
        if loop is not None:
            items = D.resolve(loop.get("items"), ctx)
            if isinstance(items, list) and items:
                ctx["item"] = items[0]
    errors = []
    for mm in D._ANY_EXPR_RE.finditer(text):
        inner = mm.group(1).strip()
        if D._PATH_RE.match(inner):
            continue
        why = DD.check(inner)
        if not why:
            try:
                DD.evaluate(inner, ctx)
            except DD.ExprError as e:
                why = str(e)
        if why:
            errors.append({"expr": inner[:80], "error": why})
    try:
        value = D.resolve(text, ctx)
    except Exception as e:   # noqa: BLE001
        value, errors = None, errors + [{"expr": "", "error": str(e)[:160]}]
    return {"value": _view(value), "errors": errors, "has_data": bool(ctx.get("steps") or ctx.get("vars"))}
