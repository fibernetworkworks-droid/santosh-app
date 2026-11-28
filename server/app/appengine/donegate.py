"""v0.999.322 THE DONE CHECK + FILE FINGERPRINTS (from the bolt.diy read) for Web Studio React apps.

1. THE DONE CHECK. Before Hoola changes an App Engine app it records a PLAN (action=plan: goal, steps, numbered
   success checks, whether the preview must be seen working). Every change, build, rule test and browser check of that
   task is written down as it happens. Hoola may only call the task finished (action=done) when the record shows, AFTER
   its last change: a good build, TypeScript clean, the rules holding (when a rule changed), the browser check passing
   (when the plan asks for the preview or the app saves data), no errors the preview reported on that version, and
   every planned check answered by its id. Otherwise action=done is refused with what is missing, and every answer
   of the tool carries the ONE next thing to do. The record is code; the model never decides it passed.

2. FILE FINGERPRINTS. A read (action=view) hands out the file's fingerprint and the tool remembers it for this chat.
   An edit or a full rewrite of an existing file must match it: a file that changed in between (her click-edit, a
   GitHub pull, another turn) refuses the edit, and Hoola must read it again.

Kept per app in `<app folder>/_work.json`, per conversation. Switches: app_engine_done_gate, app_engine_read_first.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any

TASK_TTL = 24 * 3600
MAX_SEEN = 400
_IO = threading.Lock()


class GateError(Exception):
    pass


# ------------------------------------------------------------------ storage

def _file(r):
    from . import service as S
    return S.pdir(r.tenant_id, r.id) / "_work.json"


def _load(r) -> dict[str, Any]:
    try:
        d = json.loads(_file(r).read_text())
        return d if isinstance(d, dict) else {"convs": {}}
    except (OSError, ValueError):
        return {"convs": {}}


def _store(r, d: dict[str, Any]) -> None:
    f = _file(r)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(d))
    tmp.replace(f)


def _key(conv: str) -> str:
    return str(conv or "-")[:80]


def _conv(d: dict[str, Any], conv: str) -> dict[str, Any]:
    c = d.setdefault("convs", {}).setdefault(_key(conv), {})
    c.setdefault("seen", {})
    return c


def _open(c: dict[str, Any]) -> dict[str, Any] | None:
    t = c.get("task")
    if not t or t.get("end"):
        return None
    if time.time() - float(t.get("t0") or 0) > TASK_TTL:
        return None
    return t


# ------------------------------------------------------------------ fingerprints

def seen(r, conv: str, rel: str) -> str | None:
    return (_conv(_load(r), conv)["seen"] or {}).get(rel)


def mark_seen(r, conv: str, rel: str, rev: str, old: str = "") -> None:
    with _IO:
        d = _load(r)
        s = _conv(d, conv)["seen"]
        if old:
            s.pop(old, None)
        if rev:
            s[rel] = rev
        else:
            s.pop(rel, None)
        if len(s) > MAX_SEEN:
            for k in list(s)[: len(s) - MAX_SEEN]:
                s.pop(k, None)
        _store(r, d)


# ------------------------------------------------------------------ the plan

def _clean_plan(p: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(p, dict):
        raise GateError("plan needs {goal, steps, criteria, preview}.")
    goal = " ".join(str(p.get("goal") or "").split())
    if not goal:
        raise GateError("plan needs goal: what she asked for, in one or two sentences.")
    steps = [" ".join(str(s).split())[:250] for s in (p.get("steps") or []) if str(s).strip()]
    if not 1 <= len(steps) <= 6:
        raise GateError("plan needs 1 to 6 steps.")
    crit, ids = [], set()
    for c in p.get("criteria") or []:
        if not isinstance(c, dict):
            continue
        cid = " ".join(str(c.get("id") or "").split())[:40]
        desc = " ".join(str(c.get("description") or "").split())[:400]
        if not cid or not desc:
            raise GateError("Every check needs an id and a description (what she will see working).")
        if cid in ids:
            raise GateError(f"Check id '{cid}' is used twice; ids must be unique.")
        ids.add(cid)
        crit.append({"id": cid, "description": desc})
    if not 1 <= len(crit) <= 8:
        raise GateError("plan needs 1 to 8 checks (criteria), each something that can be seen working.")
    return {"goal": goal[:500], "steps": steps, "criteria": crit, "preview": bool(p.get("preview", True))}


def record_plan(r, conv: str, plan: dict[str, Any]) -> dict[str, Any]:
    from ..db import now
    clean = _clean_plan(plan)
    with _IO:
        d = _load(r)
        c = _conv(d, conv)
        t = _open(c)
        if t is None:
            prev = c.get("task")
            if prev and prev.get("end"):
                c["last"] = prev
            t = {"n": int((prev or {}).get("n") or 0) + 1, "t0": time.time(), "at": now().isoformat(), "seq": 0, "events": [],
                 "base": int(r.version or 0)}
            c["task"] = t
        t["seq"] = int(t.get("seq") or 0) + 1
        t["plan"] = clean
        t["plan_seq"] = t["seq"]
        _store(r, d)
    return {"plan": clean, "say": "Plan recorded with checks " + ", ".join(x["id"] for x in clean["criteria"])
            + ". Now make the change; when it is built and checked, finish with action=done."}


def has_plan(r, conv: str) -> bool:
    t = _open(_conv(_load(r), conv))
    return bool(t and t.get("plan"))


def note(r, conv: str, kind: str, **data: Any) -> None:
    """One thing that happened in the open task (edit / build / browser / rules); ignored when no task is open."""
    with _IO:
        d = _load(r)
        t = _open(_conv(d, conv))
        if t is None:
            return
        t["seq"] = int(t.get("seq") or 0) + 1
        ev = {"seq": t["seq"], "kind": kind, "at": time.time(), **{k: v for k, v in data.items() if v is not None}}
        t["events"] = (t.get("events") or [])[-200:] + [ev]
        _store(r, d)


# ------------------------------------------------------------------ where the task stands

def _saves_data(r) -> bool:
    try:
        from . import cloud as CL
        return bool(CL.schema(r).get("lists"))
    except Exception:                                    # noqa: BLE001
        return False


def _open_errors(r, since_version: int) -> list[dict[str, Any]]:
    try:
        from . import pick as PK
        return [x for x in PK._read_errors(r) if x.get("state") == "open" and int(x.get("version") or 0) >= since_version]
    except Exception:                                    # noqa: BLE001
        return []


def progress_of(r, t: dict[str, Any] | None) -> dict[str, Any]:
    if not t:
        return {"status": "none"}
    if t.get("end"):
        e = t["end"]
        return {"status": e.get("outcome"), "plan": t.get("plan"), "end": e, "n": t.get("n")}
    plan = t.get("plan")
    ev = t.get("events") or []
    edits = [e for e in ev if e["kind"] == "edit"]
    last_edit = max((e["seq"] for e in edits), default=-1)
    builds = [e for e in ev if e["kind"] == "build" and e["seq"] > last_edit]
    build = builds[-1] if builds else None
    good = build if build and build.get("ok") else None
    rule_change = max((e["seq"] for e in edits if e.get("rules")), default=-1)
    rules_after = [e for e in ev if e["kind"] == "rules" and e["seq"] > rule_change]
    rules = rules_after[-1] if rules_after else None
    need_browser = bool(plan and plan.get("preview")) or _saves_data(r)
    browsers = [e for e in ev if e["kind"] == "browser" and good and e["seq"] > good["seq"]]
    browser = browsers[-1] if browsers else None
    errs = _open_errors(r, int((good or {}).get("version") or 10 ** 9)) if good else []
    st = {"status": "working", "plan": plan, "n": t.get("n"), "edited": bool(edits), "files": sorted({e.get("file") for e in edits if e.get("file")})[:30],
          "built": bool(good), "build_failed": bool(build and not build.get("ok")), "types_ok": bool(good and good.get("types_ok")),
          "version": (good or {}).get("version"), "rules_needed": rule_change >= 0, "rules_ok": bool(rules and rules.get("ok")),
          "browser_needed": need_browser, "browser": (None if not browser else ("ok" if browser.get("ok") else
                                                     ("not_run" if not browser.get("ran") else "failed"))),
          "browser_why": (browser or {}).get("why") or "", "preview_errors": len(errs)}
    st["next"] = _next(st, build, errs)
    st["ready"] = st["next"].startswith("Finish with action=done")
    return st


def _next(st: dict[str, Any], build: dict | None, errs: list) -> str:
    if not st.get("plan"):
        return "Record your plan first: action=plan {goal, steps, criteria: [{id, description}], preview}."
    if not st["edited"]:
        return "Make the change the plan describes (view a file before you edit it)."
    if st["build_failed"]:
        return "The last build failed: fix the problems it named (file and line), then action=build again."
    if not st["built"]:
        return "Build now: action=build, and read its answer."
    if not st["types_ok"]:
        return "TypeScript found problems in the build: fix them (file and line in the build answer), then action=build."
    if st["rules_needed"] and not st["rules_ok"]:
        return "A rule changed: run action=tests and make every rule test pass."
    if st["browser_needed"] and st["browser"] == "failed":
        return "The browser check found problems: fix them, then action=build again."
    if st["browser_needed"] and st["browser"] is None:
        return "Build again (action=build) so the browser check runs on the new version."
    if errs:
        return (f"The preview reported {len(errs)} error(s) on this version (action=logs lists them with file and line): "
                "fix them, then action=build.")
    ids = ", ".join(c["id"] for c in st["plan"]["criteria"])
    return f"Finish with action=done {{outcome: complete, summary, criteria: [{ids}]}}."


def progress(r, conv: str) -> dict[str, Any]:
    c = _conv(_load(r), conv)
    return progress_of(r, _open(c) or c.get("task"))


def next_line(r, conv: str) -> str:
    st = progress(r, conv)
    if st["status"] != "working":
        return ""
    return "NEXT: " + st["next"]


# ------------------------------------------------------------------ finishing

def complete(r, conv: str, outcome: str, summary: str, criteria: list[Any]) -> dict[str, Any]:
    from ..db import now
    outcome = str(outcome or "complete").lower()
    summary = " ".join(str(summary or "").split())[:1000]
    if outcome not in ("complete", "blocked"):
        raise GateError("outcome is complete or blocked.")
    if not summary:
        raise GateError("done needs a summary: what changed, in plain words.")
    with _IO:
        d = _load(r)
        c = _conv(d, conv)
        t = _open(c)
        if t is None:
            raise GateError("There is no open task on this app in this chat: record a plan (action=plan) before you change it.")
        st = progress_of(r, t)
        if outcome == "blocked":
            t["end"] = {"outcome": "blocked", "summary": summary, "at": now().isoformat()}
            _store(r, d)
            return {"accepted": True, "outcome": "blocked", "say": "Recorded as blocked. Tell her plainly what is "
                    "blocking and which checks are not met. Do not say it is finished."}
        if not st["edited"]:
            t["end"] = {"outcome": "complete", "summary": summary, "at": now().isoformat(), "evidence": ["no change was made"],
                        "criteria": [], "files": []}
            _store(r, d)
            return {"accepted": True, "outcome": "complete", "evidence": ["no change was made"],
                    "say": "Recorded: no change was made to the app. Tell her that plainly."}
        problems = []
        if not st["ready"]:
            problems.append(st["next"])
        plan_ids = [x["id"] for x in (st.get("plan") or {}).get("criteria") or []]
        got = [str(x.get("id") if isinstance(x, dict) else x).strip() for x in (criteria or [])]
        for cid in plan_ids:
            if got.count(cid) != 1:
                problems.append(f"Report check {cid} exactly once.")
        for cid in got:
            if cid not in plan_ids:
                problems.append(f"Check '{cid}' is not in the recorded plan.")
        if problems:
            return {"accepted": False, "problems": problems, "planned": plan_ids,
                    "say": "Not finished yet - " + " ".join(dict.fromkeys(problems)) + " Do not tell her it is done."}
    # v0.999.324 a second look at the code by another model (outside the lock: it is a model call)
    rv = _review(r, t, st)
    with _IO:
        d = _load(r)
        c = _conv(d, conv)
        t = _open(c)
        if t is None:
            raise GateError("The task was closed meanwhile; record a new plan.")
        if rv.get("ran") and rv.get("version") == st["version"]:
            t["review"] = rv
        blocking = [f for f in rv.get("findings") or [] if f["severity"] in ("high", "medium")] if rv.get("ran") else []
        seen_v = list(t.get("review_blocked") or [])          # the built versions whose review still had problems
        if blocking and st["version"] not in seen_v:
            seen_v.append(st["version"])
            t["review_blocked"] = seen_v
        if blocking and len(seen_v) <= REVIEW_ROUNDS:            # 2 fix rounds; a third still-open review lets it finish, named
            _store(r, d)
            from . import review as RV
            return {"accepted": False, "review": blocking, "planned": plan_ids,
                    "say": f"Not finished yet - a second model reviewed the change and found {len(blocking)} problem(s): "
                           + RV.say(blocking) + ". Fix them (or, if one is wrong, change nothing for it), build again, then "
                           "action=done. Do not tell her it is done."}
        evidence = [f"built version {st['version']}", "TypeScript clean"]
        if st["rules_needed"]:
            evidence.append("rule tests passed")
        if st["browser_needed"]:
            evidence.append("browser check passed at phone and desktop size" if st["browser"] == "ok"
                            else "browser check could not run on this server" + (f" ({st['browser_why']})" if st["browser_why"] else ""))
        evidence.append("no preview errors on this version")
        if rv.get("ran") is False:
            evidence.append("the code review could not run (" + str(rv.get("why") or "unknown") + ")")
        elif rv.get("ran"):
            from . import review as RV
            evidence.append(("a second model reviewed the change: still open - " + RV.say(blocking) + " (tell her)") if blocking
                            else "a second model reviewed the change and found nothing blocking")
        t["end"] = {"outcome": "complete", "summary": summary, "at": now().isoformat(), "version": st["version"],
                    "evidence": evidence, "criteria": plan_ids, "files": st["files"]}
        _store(r, d)
    return {"accepted": True, "outcome": "complete", "version": st["version"], "evidence": evidence,
            "say": "Checks accepted: " + "; ".join(evidence) + ". Now tell her what changed in plain words. "
                   "Going live is her tap in the Studio."}


REVIEW_ROUNDS = 2


def _review(r, t: dict[str, Any], st: dict[str, Any]) -> dict[str, Any]:
    """The review of this version's change: done once per built version (a repeat done reuses it)."""
    from ..config import get_settings
    if not getattr(get_settings(), "app_engine_auto_review", True):
        return {"ran": None}
    old = t.get("review") or {}
    if old.get("version") == st["version"] and old.get("ran"):
        return old
    from . import review as RV
    try:
        res = RV.run(r, t.get("plan") or {}, int(t.get("base") or 0))
    except Exception as e:                               # noqa: BLE001 - a review that cannot run never blocks
        res = {"ran": False, "findings": [], "why": str(e)[:160]}
    res["version"] = st["version"]
    return res


def latest(r) -> dict[str, Any]:
    """The Studio's card: the task touched last on this app, in any chat."""
    d = _load(r)
    best = None
    for c in (d.get("convs") or {}).values():
        t = c.get("task")
        if t and (best is None or float(t.get("t0") or 0) > float(best.get("t0") or 0)):
            best = t
    if best is None:
        return {"status": "none"}
    if not best.get("end") and time.time() - float(best.get("t0") or 0) > TASK_TTL:
        return {"status": "none"}
    st = progress_of(r, best)
    st["at"] = best.get("at")
    return st


# ------------------------------------------------------------------ v0.999.324 the blueprint of a NEW app
BLUEPRINT = ".hoola/plan/blueprint.md"


def _items(x: Any, keys: tuple[str, ...], n: int) -> list[dict[str, str]]:
    out = []
    for it in (x or [])[:n]:
        if isinstance(it, str) and it.strip():
            out.append({keys[0]: " ".join(it.split())[:200]})
        elif isinstance(it, dict):
            row = {k: " ".join(str(it.get(k) or "").split())[:300] for k in keys}
            if row[keys[0]]:
                out.append(row)
    return out


def has_blueprint(r) -> bool:
    from . import service as S
    return (S.src_dir(r) / BLUEPRINT).is_file()


def needs_blueprint(r) -> bool:
    """A NEW app (never built) gets its blueprint before its first line of code."""
    return not int(r.version or 0) and not has_blueprint(r)


def write_blueprint(r, bp: dict[str, Any]) -> dict[str, Any]:
    from . import service as S
    what = " ".join(str((bp or {}).get("what") or "").split())[:800]
    if not what:
        raise GateError("blueprint needs what: the app in her words, in one to three sentences.")
    screens = _items(bp.get("screens"), ("name", "purpose"), 20)
    if not screens:
        raise GateError("blueprint needs screens: [{name, purpose}] - every screen the first version has.")
    users = _items(bp.get("users"), ("who", "can"), 10)
    data = _items(bp.get("data"), ("list", "fields"), 20)
    out_of = _items(bp.get("out_of_scope"), ("thing",), 12)
    qs = _items(bp.get("questions"), ("q", "a"), 5)
    if len(bp.get("questions") or []) > 5:
        raise GateError("Ask her at most 5 questions; keep the five that change the app most.")
    md = ["# Blueprint", "", what, ""]
    if users:
        md += ["## Who uses it", ""] + [f"- **{u['who']}**" + (f": {u['can']}" if u.get("can") else "") for u in users] + [""]
    md += ["## Screens", ""] + [f"- **{x['name']}**" + (f": {x['purpose']}" if x.get("purpose") else "") for x in screens] + [""]
    if data:
        md += ["## Data it keeps", ""] + [f"- **{x['list']}**" + (f": {x['fields']}" if x.get("fields") else "") for x in data] + [""]
    if out_of:
        md += ["## Not in the first version", ""] + [f"- {x['thing']}" for x in out_of] + [""]
    if qs:
        md += ["## What she was asked", ""] + [f"- {x['q']}" + (f" - **{x['a']}**" if x.get("a") else " - (not answered: Hoola's choice)") for x in qs] + [""]
    res = S.write(r.tenant_id, r.id, BLUEPRINT, "\n".join(md))
    return {"blueprint": BLUEPRINT, "screens": len(screens), "revision": res.get("revision"),
            "say": f"Blueprint written ({len(screens)} screen(s)). Now record your plan (action=plan) and build the first version from it."}


def blueprint_text(r) -> str:
    from . import service as S
    f = S.src_dir(r) / BLUEPRINT
    try:
        return f.read_text("utf-8")[:6000] if f.is_file() else ""
    except OSError:
        return ""

