"""D0 THE PC CARD (docs/DESKTOP_AI_PLAN.md section 4): 40 real Windows tasks through the REAL PC operator on a PC
the owner named as a TEST PC, each scored by a CODE check of the end state (window title / page text / the
operator's summary / its status) - never by the operator saying 'ho gaya'. Every later change to the PC agent
(D1 toolset, D2 planner, D4 verify...) is measured on this card.

Safety, in code:
  - a run needs a PC name; the named PC must be online and its name must contain 'test', unless the caller passes
    confirm_not_her_pc=True (so her own PC is never driven by accident);
  - one card at a time (module flag), and a PC already busy is never taken over (operator.start replace=False);
  - a shopping task that reaches the approval card is STOPPED right there (operator.stop) - nothing is bought;
  - the card only reads the PC to check ('screen', 'page_text'); it presses nothing itself.

Results: <QUALITY_DIR>/pccard-<time>.json (the same folder as every other quality card), history via saved().
This module never edits the operator: it only calls operator.start / OPS / _pc / stop / give_answer."""
from __future__ import annotations

import asyncio
import json
import re
import statistics
import time
from typing import Any

from .pccard_tasks import GROUPS, SET_V, TASKS

POLL_S = 0.5
MAX_ANSWERS = 2          # the card answers a task's questions at most twice, then counts it as 'asked'
KINDS = ("title", "windows", "page", "answer", "status")

STATUS: dict[str, Any] = {"running": False}
_RUNNING = False
_STOP = False
_CUR: dict[str, str] = {}        # tenant / session id of the task running now (for stop)


# ---------------------------------------------------------------- the checker (pure, no PC)

def check_known(chk: dict) -> bool:
    """Every node of a check is a known kind with its field (used by the task-set test)."""
    if not isinstance(chk, dict):
        return False
    if "all" in chk or "any" in chk:
        parts = chk.get("all", chk.get("any"))
        return isinstance(parts, list) and bool(parts) and all(check_known(p) for p in parts)
    k = chk.get("kind")
    if k not in KINDS:
        return False
    if k == "status":
        return isinstance(chk.get("in"), list) and bool(chk["in"])
    try:
        re.compile(str(chk.get("re") or ""))
    except re.error:
        return False
    return bool(chk.get("re"))


def needs(chk: dict) -> set[str]:
    """Which reads a check needs: 'screen' (title / windows), 'page' (page text)."""
    if "all" in chk or "any" in chk:
        out: set[str] = set()
        for p in chk.get("all", chk.get("any")) or []:
            out |= needs(p)
        return out
    k = chk.get("kind")
    return {"screen"} if k in ("title", "windows") else {"page"} if k == "page" else set()


def check(chk: dict, state: dict) -> tuple[bool, str]:
    """state = {title, windows: [..], page, answer, status, errors: {screen|page: reason}}. -> (ok, reason)."""
    if "all" in chk:
        for p in chk["all"]:
            ok, why = check(p, state)
            if not ok:
                return False, why
        return True, "all parts passed"
    if "any" in chk:
        whys = []
        for p in chk["any"]:
            ok, why = check(p, state)
            if ok:
                return True, why
            whys.append(why)
        return False, "none passed: " + "; ".join(whys)
    k = chk.get("kind")
    errs = state.get("errors") or {}
    if k == "status":
        st = str(state.get("status") or "")
        return (st in chk["in"]), f"status {st or '-'} {'in' if st in chk['in'] else 'not in'} {chk['in']}"
    rx = re.compile(str(chk.get("re") or ""), re.I | re.S)
    if k == "title":
        if "screen" in errs:
            return False, f"screen not read: {errs['screen']}"
        hay = str(state.get("title") or "")
    elif k == "windows":
        if "screen" in errs:
            return False, f"screen not read: {errs['screen']}"
        hay = "\n".join(str(w) for w in (state.get("windows") or [])) + "\n" + str(state.get("title") or "")
    elif k == "page":
        if "page" in errs:
            return False, f"page not read: {errs['page']}"
        hay = str(state.get("page") or "")
    elif k == "answer":
        hay = str(state.get("answer") or "")
    else:
        return False, f"unknown check kind {k!r}"
    if rx.search(hay):
        return True, f"{k} matches /{chk['re']}/"
    return False, f"{k} does not match /{chk['re']}/ (saw: {hay.strip()[:120]!r})"


# ---------------------------------------------------------------- the PC (seams the tests replace)

def _op_mod():
    from ..pc import operator
    return operator


def _resolve(tenant: str, pc_name: str) -> dict | None:
    """The online PC she named: {device_id, name, kind}. None = no such PC online."""
    from ..pc.hub import HOOLA_PC_KIND, hub
    want = str(pc_name or "").strip()
    conn = next((c for c in hub.online(tenant) if c.device_id == want), None) or hub.find(tenant, want)
    if conn is None:
        return None
    info = conn.info or {}
    return {"device_id": conn.device_id, "name": str(info.get("name") or ""),
            "kind": HOOLA_PC_KIND if info.get("kind") == HOOLA_PC_KIND else ""}


def _online(tenant: str, device_id: str) -> bool:
    from ..pc.hub import hub
    return hub.is_online(tenant, device_id=device_id)


def guard(tenant: str, pc_name: str, confirm_not_her_pc: bool = False) -> dict:
    """Refuse a run that could drive her own PC by accident. Returns the resolved PC or raises ValueError."""
    if not str(pc_name or "").strip():
        raise ValueError("Name the TEST PC to run the PC card on (pc=...). The card never picks a PC by itself.")
    dev = _resolve(tenant, pc_name)
    if dev is None:
        raise ValueError(f"No online PC matches '{str(pc_name)[:60]}'. Turn the test PC on and pair it first.")
    if "test" not in (dev.get("name") or "").lower() and not confirm_not_her_pc:
        raise ValueError(f"'{dev.get('name') or dev['device_id']}' does not have 'test' in its name. The PC card "
                         "clicks, types and opens sites for ~40 tasks, so it runs only on a test PC: rename that PC "
                         "to include 'test', or pass confirm_not_her_pc=true if you are sure it is NOT her own PC.")
    return dev


# ---------------------------------------------------------------- one task

async def _read_state(op, want: set[str]) -> dict:
    O = _op_mod()
    st: dict[str, Any] = {"title": op.window, "windows": list(op.windows or []), "page": "", "errors": {}}
    if "screen" in want:
        try:
            s = await O._pc(op, "screen", {"max_width": 640, "monitor": op.monitor})
            st["title"] = str(s.get("active_window") or "")
            st["windows"] = [str(w) for w in (s.get("windows") or [])]
        except Exception as e:
            st["errors"]["screen"] = str(e)[:200] or type(e).__name__
    if "page" in want:
        try:
            r = await O._pc(op, "page_text", {"max_chars": 4000})
            st["page"] = "\n".join(str(r.get(k) or "") for k in ("title", "url", "text"))
        except Exception as e:
            st["errors"]["page"] = str(e)[:200] or type(e).__name__
    return st


async def run_task(tenant: str, conv: str, task: dict, dev: dict) -> dict:
    O = _op_mod()
    t0 = time.time()
    row: dict[str, Any] = {"id": task["id"], "group": task["group"], "ok": False, "reason": "", "seconds": 0.0,
                           "steps": 0, "status": "", "brain": "", "model": "", "asks": 0, "answered": 0,
                           "false_done": False, "stopped_at_approval": False}
    try:
        live = await O.start(tenant, conv, task["ask"], wait=0, kind=dev.get("kind") or "",
                             pc=dev["device_id"], replace=False)
    except Exception as e:
        row["reason"] = f"could not start: {str(e)[:200] or type(e).__name__}"
        row["status"] = "not_started"
        return row
    sid = str((live or {}).get("session_id") or "")
    op = O.OPS.get(sid)
    if op is None:
        row["reason"], row["status"] = "operator gave no session", "not_started"
        return row
    _CUR.update(tenant=tenant, sid=sid)
    deadline = t0 + float(task.get("max_minutes") or 4) * 60
    final, stop_after = "", False
    try:
        while True:
            if op.done_event.is_set():
                final = str(op.status or "")
                break
            if op.status == "needs_confirm":
                final, stop_after = "needs_confirm", True
                break
            ask = getattr(op, "ask", None)
            if ask is not None and not ask.get("answered"):
                if task.get("answer") and row["answered"] < MAX_ANSWERS:
                    if O.give_answer(tenant, task["answer"], op.conv):
                        row["answered"] += 1
                else:
                    final, stop_after = "asked", True
                    break
            if _STOP:
                final, stop_after = "card_stopped", True
                break
            if time.time() > deadline:
                final, stop_after = "timeout", True
                break
            await asyncio.sleep(POLL_S)
        state = await _read_state(op, needs(task["check"]))
        state["answer"] = " ".join(x for x in (str(op.summary or ""), str(op.reason or "")) if x)
        state["status"] = final
        ok, why = check(task["check"], state)
        if final == "timeout":
            ok, why = False, f"timed out after {task.get('max_minutes')} min ({why})"
        elif final == "card_stopped":
            ok, why = False, "card stopped by the owner"
        row.update(ok=ok, reason=why, status=final)
        row["stopped_at_approval"] = final == "needs_confirm"
        row["false_done"] = final == "done" and not ok
        row["page_seen"] = str(state.get("page") or "")[:300]
        row["title_seen"] = str(state.get("title") or "")[:120]
    finally:
        if stop_after or not op.done_event.is_set():
            try:
                O.stop(tenant, sid)       # an approval stop: nothing is bought, the task ends here
            except Exception:
                pass
        _CUR.clear()
        row["seconds"] = round(time.time() - t0, 1)
        row["steps"] = int(getattr(op, "step", 0) or 0)
        row["brain"] = str(getattr(op, "brain", "") or "")
        row["model"] = str(getattr(op, "brain_model", "") or "")
        row["asks"] = sum(1 for e in (getattr(op, "timeline", None) or []) if (e or {}).get("do") == "ask_user")
    return row


# ---------------------------------------------------------------- the card

def summarize(rows: list[dict]) -> dict:
    ran = [r for r in rows if not r.get("skipped")]
    ok = [r for r in ran if r.get("ok")]
    secs = [r["seconds"] for r in ran if r.get("status") != "not_started"]
    steps = [r["steps"] for r in ran if r.get("status") != "not_started"]
    groups = {}
    for g in GROUPS:
        gr = [r for r in ran if r["group"] == g]
        if gr:
            n_ok = sum(1 for r in gr if r.get("ok"))
            groups[g] = {"n": len(gr), "ok": n_ok, "pct": round(100 * n_ok / len(gr), 1)}
    return {"ran": len(ran), "ok": len(ok), "skipped": len(rows) - len(ran),
            "success_pct": round(100 * len(ok) / len(ran), 1) if ran else 0.0,
            "median_seconds": round(statistics.median(secs), 1) if secs else None,
            "median_steps": statistics.median(steps) if steps else None,
            "false_done": sum(1 for r in ran if r.get("false_done")),
            "asks": sum(r.get("asks", 0) for r in ran),
            "approval_stops": sum(1 for r in ran if r.get("stopped_at_approval")),
            "rupees": "not measured", "groups": groups}


async def run_card(tenant: str, pc_name: str, ids: list[str] | None = None, conv: str | None = None,
                   budget_minutes: float = 240, confirm_not_her_pc: bool = False,
                   skip_needs: list[str] | None = None, label: str = "", save_card: bool = True) -> dict:
    """Run the card (or the tasks in `ids`) on the named TEST PC, in order. Returns the saved card."""
    global _RUNNING, _STOP
    if _RUNNING:
        raise RuntimeError("A PC card is already running - wait for it or stop it first.")
    dev = guard(tenant, pc_name, confirm_not_her_pc)
    tasks = [t for t in TASKS if not ids or t["id"] in set(ids)]
    if ids:
        unknown = sorted(set(ids) - {t["id"] for t in TASKS})
        if unknown:
            raise ValueError(f"Unknown task ids: {', '.join(unknown)}")
    _RUNNING, _STOP = True, False
    conv = conv or "__pccard__"
    skip = set(skip_needs or [])
    t0 = time.time()
    rows: list[dict] = []
    note = ""
    STATUS.clear()
    STATUS.update(running=True, pc=dev.get("name") or dev["device_id"], of=len(tasks), done=0, task="",
                  started=int(t0), ok=0)
    try:
        for t in tasks:
            if t.get("needs") and t["needs"] in skip:
                rows.append({"id": t["id"], "group": t["group"], "skipped": True, "reason": f"PC has no {t['needs']}"})
                continue
            if _STOP:
                note = "stopped by the owner"
                break
            if (time.time() - t0) / 60 > budget_minutes:
                note = f"time budget of {budget_minutes} min used up"
                break
            if not _online(tenant, dev["device_id"]):
                note = "the test PC went offline"
                break
            STATUS["task"] = t["id"]
            row = await run_task(tenant, conv, t, dev)
            rows.append(row)
            STATUS["done"] = len(rows)
            STATUS["ok"] = sum(1 for r in rows if r.get("ok"))
    finally:
        _RUNNING = False
        STATUS.update(running=False, task="")
    card = {"kind": "pccard", "set": SET_V, "pc": dev.get("name") or "", "device_id": dev["device_id"],
            "label": label, "at": int(time.time()), "minutes": round((time.time() - t0) / 60, 1),
            "asked_for": len(tasks), "note": note, "summary": summarize(rows), "rows": rows}
    if save_card:
        card = save(card)
    STATUS["last"] = card.get("file", "")
    return card


def request_stop() -> bool:
    """Stop the running card: the current task is stopped at once, the rest are not started."""
    global _STOP
    if not _RUNNING:
        return False
    _STOP = True
    if _CUR.get("sid"):
        try:
            _op_mod().stop(_CUR["tenant"], _CUR["sid"])
        except Exception:
            pass
    return True


def running() -> bool:
    return _RUNNING


# ---------------------------------------------------------------- storage (the quality folder, like every card)

def save(card: dict) -> dict:
    from .run import _dir
    name = f"pccard-{time.strftime('%Y%m%d-%H%M%S')}.json"
    (_dir() / name).write_text(json.dumps(card, ensure_ascii=False, indent=1))
    return {**card, "file": name}


def saved() -> list[dict]:
    from .run import _dir
    out = []
    for p in sorted(_dir().glob("pccard-*.json"), reverse=True)[:30]:
        try:
            d = json.loads(p.read_text())
            out.append({"file": p.name, "at": d.get("at"), "pc": d.get("pc"), "label": d.get("label"),
                        "note": d.get("note"), "summary": d.get("summary")})
        except Exception:
            continue
    return out


def last() -> dict | None:
    from .run import _dir
    files = sorted(_dir().glob("pccard-*.json"), reverse=True)
    if not files:
        return None
    try:
        return {**json.loads(files[0].read_text()), "file": files[0].name}
    except Exception:
        return None


def lines(card: dict) -> list[str]:
    s = card.get("summary") or {}
    out = [f"PC card (set v{card.get('set')}) on {card.get('pc') or card.get('device_id')}: "
           f"{s.get('ok')}/{s.get('ran')} passed ({s.get('success_pct')}%), median {s.get('median_seconds')} s / "
           f"{s.get('median_steps')} steps, false done {s.get('false_done')}, asks {s.get('asks')}, "
           f"approval stops {s.get('approval_stops')}, rupees {s.get('rupees')}"
           + (f" - {card['note']}" if card.get("note") else "")]
    for g, v in (s.get("groups") or {}).items():
        out.append(f"  {g}: {v['ok']}/{v['n']} ({v['pct']}%)")
    return out
