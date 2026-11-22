"""v0.999.115 ULTIMATE PC PLAN P5 - learn once, replay (docs/HOOLA_ULTIMATE_PC_PLAN.md).

A PC job that went well becomes a ROUTINE: its page steps (open a site, click / type / choose / hover / drag an element
named by WHAT it is - role + name, never a screen position), with the things she typed from her own words turned into
blanks ({Invoice no}, {Email}). Replaying a routine runs those steps with NO AI at all (near Rs 0, seconds), through the
same operator path as any job: her safety rules, the independent checker, approvals, the step record. When a step no
longer fits the page (the site changed), the AI takes over FROM THAT STEP with the work so far (the self-heal), instead
of the whole job failing.

    from_job(tenant, job, name)     a routine from a finished job's step record (pc/trace.py)
    play(op)                        operator._run calls it when op.replay is set; -> (all_done, steps_done, note)
    /api/pc/routines*               list / from-job / get / delete / run (values for the blanks)

Ideas from Skyvern's workflows, playwright-mcp's codegen and Stagehand's cached actions; the code is Hoola's own."""
from __future__ import annotations

import json
import os
import re
import secrets
import time
from pathlib import Path
from typing import Any

from . import trace as _trace

KEEP = ("open_url", "page_click", "page_type", "page_select", "page_fill_form", "page_hover", "page_drag", "wait_for",
        "key", "switch_tab")
_TARGET = re.compile(r"^(\S+) '(.*)'$", re.S)
_FAIL = re.compile(r"^(ERROR|REFUSED|NOT clicked|NOT RUN|NOT typed|She said no|cancelled)", re.I)
MAX_ROUTINES = 200


def _dir(tenant: str) -> Path:
    base = Path(os.environ.get("PC_ROUTINES_DIR", "data/pc_routines"))
    return base / re.sub(r"[^A-Za-z0-9_.-]", "_", str(tenant or "default"))[:64]


def _target(s: Any) -> list[str] | None:
    m = _TARGET.match(str(s or ""))
    return [m.group(1), m.group(2)] if m else None


def _blank_name(name: str, used: set) -> str:
    base = re.sub(r"[{}]", "", str(name or "value")).strip()[:40] or "value"
    k, i = base, 2
    while k.lower() in used:
        k, i = f"{base} {i}", i + 1
    used.add(k.lower())
    return k


def from_job(tenant: str, job: str, name: str = "") -> dict[str, Any]:
    """A routine from the step record of a finished, successful job."""
    rec = _trace.read(tenant, job)
    if rec is None:
        raise ValueError("no step record for that job")
    if str(rec.get("status")) != "done":
        raise ValueError(f"only a job that finished well becomes a routine (this one: {rec.get('status')})")
    task = str(rec.get("task") or "")
    low = task.lower()
    steps, blanks, used, skipped = [], [], set(), 0

    def maybe_blank(text: str, label: str) -> dict:
        t = str(text or "")
        if t and len(t) >= 2 and t.lower() in low:
            b = _blank_name(label, used)
            blanks.append({"name": b, "default": t})
            return {"blank": b}
        return {"text": t}
    for s in rec.get("steps_list") or []:
        tool, a, tg = str(s.get("tool") or ""), dict(s.get("args") or {}), s.get("targets") or {}
        if tool not in KEEP:
            if tool in ("click", "type", "double_click", "drag", "scroll"):
                skipped += 1               # a pixel step: the replay hands that part to the AI
            continue
        st: dict[str, Any] = {"tool": tool}
        if tool == "open_url":
            st["url"] = str(a.get("url") or "")
            if not st["url"]:
                continue
        elif tool in ("wait_for",):
            st["text"] = str(a.get("text") or "")
        elif tool == "key":
            st["keys"] = str(a.get("keys") or "")
        elif tool == "switch_tab":
            st["tab"] = str(a.get("tab") or "")
        elif tool == "page_fill_form":
            ents = []
            for i, e in enumerate(a.get("entries") or []):
                t = _target((tg.get("entries") or [None] * 99)[i] if i < len(tg.get("entries") or []) else None)
                if not t:
                    break
                ents.append({"target": t, **maybe_blank(e.get("text"), t[1])})
            else:
                st["entries"] = ents
            if "entries" not in st:
                skipped += 1
                continue
        else:
            t = _target(tg.get("ref"))
            if not t:
                skipped += 1
                continue
            st["target"] = t
            if tool == "page_type":
                st.update(maybe_blank(a.get("text"), t[1]))
            elif tool == "page_select":
                st.update({"value": str(a.get("value") or "")})
            elif tool == "page_drag":
                to = _target(tg.get("to_ref"))
                if not to:
                    skipped += 1
                    continue
                st["to"] = to
        steps.append(st)
    if not steps:
        raise ValueError("that job has no page steps Hoola can replay (it worked by pointing at the screen)")
    rid = "rt_" + secrets.token_hex(5)
    r = {"id": rid, "name": (name or task[:60]).strip()[:80], "task": task[:600], "from_job": job,
         "kind": rec.get("kind") or "", "steps": steps, "blanks": blanks, "pixel_steps_left_to_ai": skipped,
         "created": int(time.time()), "runs": 0, "healed": 0}
    d = _dir(tenant)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{rid}.json").write_text(json.dumps(r, indent=1))
    old = sorted(d.glob("rt_*.json"), key=lambda p: p.stat().st_mtime)
    for p in old[:-MAX_ROUTINES]:
        p.unlink(missing_ok=True)
    return r


def last_done_job(tenant: str, conv: str, kind: str) -> str:
    """The newest job of this chat on this kind of PC that finished well (what 'save that as a routine' means)."""
    for m in _trace.jobs(tenant, 50):
        if m.get("status") == "done" and (not conv or m.get("conv") == conv) and (m.get("kind") or "") in (kind, kind or "her_pc"):
            return str(m.get("job") or "")
    return ""


def listing(tenant: str) -> list[dict]:
    out = []
    for p in sorted(_dir(tenant).glob("rt_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            r = json.loads(p.read_text())
        except Exception:   # noqa: BLE001
            continue
        out.append({k: r.get(k) for k in ("id", "name", "kind", "blanks", "runs", "healed", "created")} |
                   {"steps": len(r.get("steps") or [])})
    return out


def get(tenant: str, rid: str) -> dict | None:
    if not re.fullmatch(r"rt_[0-9a-f]{10}", str(rid or "")):
        return None
    p = _dir(tenant) / f"{rid}.json"
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def find(tenant: str, name: str) -> dict | None:
    """A routine by its id or (part of) its name."""
    r = get(tenant, name)
    if r:
        return r
    want = str(name or "").strip().lower()
    for it in listing(tenant):
        if want and want in str(it.get("name") or "").lower():
            return get(tenant, it["id"])
    return None


def delete(tenant: str, rid: str) -> bool:
    if get(tenant, rid) is None:
        return False
    (_dir(tenant) / f"{rid}.json").unlink(missing_ok=True)
    return True


def _bump(tenant: str, rid: str, healed: bool) -> None:
    r = get(tenant, rid)
    if r:
        r["runs"] = int(r.get("runs") or 0) + 1
        r["healed"] = int(r.get("healed") or 0) + (1 if healed else 0)
        r["last_run"] = int(time.time())
        (_dir(tenant) / f"{rid}.json").write_text(json.dumps(r, indent=1))


def task_text(r: dict, values: dict) -> str:
    vals = ", ".join(f"{k} = {v}" for k, v in (values or {}).items())
    return f"Replay my routine '{r.get('name')}'" + (f" with {vals}" if vals else "") + f". (Originally: {r.get('task', '')[:300]})"


# ---------------------------------------------------------------- the replay (inside operator._run, no AI)
def _value(step: dict, values: dict, blanks: list) -> str:
    if "blank" in step:
        b = step["blank"]
        for k, v in (values or {}).items():
            if str(k).strip().lower() == b.lower():
                return str(v)
        return next((x["default"] for x in blanks if x["name"] == b), "")
    return str(step.get("text") or "")


def _find_ref(els: list, target: list) -> int | None:
    role, name = target[0], target[1]
    exact = [e for e in els if e.get("role") == role and (e.get("name") or "") == name]
    if exact:
        return int(exact[0]["ref"])
    low = name.lower().strip()
    loose = [e for e in els if e.get("role") == role and low and low in str(e.get("name") or "").lower()]
    return int(loose[0]["ref"]) if len(loose) == 1 else None


async def play(op) -> tuple[bool, int, str]:
    """Run the routine's steps on the job's PC. -> (all done, steps done, a note for the AI if it must take over)."""
    from . import operator as O
    from . import hands
    r = op.replay or {}
    steps, values, blanks = r.get("steps") or [], r.get("values") or {}, r.get("blanks") or []
    done = []
    for i, st in enumerate(steps):
        if op.status != "running":
            return False, i, "stopped"
        tool = st["tool"]
        a: dict[str, Any] = {}
        try:
            if tool == "open_url":
                a = {"url": st["url"]}
            elif tool == "wait_for":
                a = {"text": st.get("text", ""), "seconds": 15}
            elif tool == "key":
                a = {"keys": st.get("keys", "")}
            elif tool == "switch_tab":
                a = {"tab": st.get("tab", "")}
            else:
                pe = await O._pc(op, "page_elements", {"max_items": 200}, timeout=40)
                els = pe.get("elements") or []
                hands.remember_elements(op, els)
                op.pw_refs = {int(e.get("ref") or 0) for e in els if str(e.get("type") or "").lower() == "password"}
                if tool == "page_fill_form":
                    ents = []
                    for e in st.get("entries") or []:
                        ref = _find_ref(els, e["target"])
                        if ref is None:
                            raise LookupError(f"'{e['target'][1]}' ({e['target'][0]}) is not on the page any more")
                        ents.append({"ref": ref, "text": _value(e, values, blanks)})
                    a = {"entries": ents}
                else:
                    ref = _find_ref(els, st["target"])
                    if ref is None:
                        raise LookupError(f"'{st['target'][1]}' ({st['target'][0]}) is not on the page any more")
                    a = {"ref": ref}
                    if tool == "page_type":
                        a["text"] = _value(st, values, blanks)
                    elif tool == "page_select":
                        a["value"] = st.get("value", "")
                    elif tool == "page_drag":
                        to = _find_ref(els, st["to"])
                        if to is None:
                            raise LookupError(f"'{st['to'][1]}' is not on the page any more")
                        a["to_ref"] = to
            held = await hands.gate(op, tool, a)          # her rules, the independent check, approvals: as in any job
            if held:
                return False, i, f"Step {i + 1} ({tool}) was held: {held}"
            op.step += 1
            op.action = O._say(tool, a)
            op.timeline.append({"step": op.step, "action": op.action, "do": tool, "url": op.window,
                                "t": int(time.time()), "replay": True})
            del op.timeline[:-60]
            _trace.step(op, tool, a)
            O._event(op)
            out = await O._do(op, tool, a)
            if _FAIL.search(str(out or "").strip()):
                raise RuntimeError(str(out)[:200])
            if "page change: NOTHING visible changed" in str(out) and tool in ("page_click",):
                raise RuntimeError("the click changed nothing on the page")
            done.append(f"{tool} {st.get('target', [''])[-1] if st.get('target') else st.get('url', '')}".strip())
        except Exception as e:   # noqa: BLE001
            note = (f"ROUTINE '{r.get('name')}' replayed {i} of {len(steps)} steps without AI, then step {i + 1} "
                    f"({tool}) did not fit the page: {str(e)[:160]}. Steps done: {'; '.join(done) or 'none'}. Continue "
                    "the job from here (never redo the steps done); the routine's remaining steps were: "
                    + "; ".join(f"{s['tool']} {s.get('target', [''])[-1] if s.get('target') else s.get('url', '')}"
                                for s in steps[i:]))
            if r.get("id"):
                _bump(op.tenant, r["id"], healed=True)
            return False, i, note
    if r.get("id"):
        _bump(op.tenant, r["id"], healed=False)
    return True, len(steps), f"Replayed routine '{r.get('name')}': {len(steps)} steps, no AI needed."


# ---------------------------------------------------------------- routes
def mount(app, current_tenant, require_key) -> None:
    from fastapi import APIRouter, Depends, HTTPException

    r = APIRouter(prefix="/api/pc/routines", dependencies=[Depends(require_key)])

    @r.get("")
    def rt_list(tenant: str = Depends(current_tenant)):
        return {"routines": listing(tenant)}

    @r.post("/from-job/{job}")
    def rt_from_job(job: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
        try:
            return from_job(tenant, job, str((body or {}).get("name") or ""))
        except ValueError as e:
            raise HTTPException(409, str(e))

    @r.get("/{rid}")
    def rt_get(rid: str, tenant: str = Depends(current_tenant)):
        got = get(tenant, rid)
        if got is None:
            raise HTTPException(404, "Not found.")
        return got

    @r.delete("/{rid}")
    def rt_delete(rid: str, tenant: str = Depends(current_tenant)):
        return {"deleted": delete(tenant, rid)}

    @r.post("/{rid}/run")
    async def rt_run(rid: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
        from . import operator as O
        from .hub import HOOLA_PC_KIND
        got = get(tenant, rid)
        if got is None:
            raise HTTPException(404, "Not found.")
        b = body or {}
        values = dict(b.get("values") or {})
        kind = HOOLA_PC_KIND if (b.get("on") or got.get("kind")) == HOOLA_PC_KIND else ""
        try:
            return await O.start(tenant, str(b.get("conversation_id") or ""), task_text(got, values), kind=kind,
                                 pc=str(b.get("pc") or ""), wait=0, replay={**got, "values": values})
        except Exception as e:   # noqa: BLE001
            raise HTTPException(409, str(e)[:300])

    app.include_router(r)
