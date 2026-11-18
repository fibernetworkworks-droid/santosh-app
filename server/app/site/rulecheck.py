"""v0.990 B3 PROVE THE RULES (owner: "GO B3" on docs/research/lovable/03_backend_vs_hoola.md, gap 4).

A website's data rules (who may add, see, change and remove entries in each list, which fields only staff see or set) were
enforced on every call but never TESTED: path C (React apps on Hoola Cloud) played its rules before publish
(`appengine/saboot.rule_tests`), path B - the live path for Studio websites - had nothing.

Now, for a website linked to its App Sahayak project:
- the rules are PLAYED through the real engine (`appmaker.backend` create / rows / update / delete, the same code every
  visitor's call goes through, logic hooks included) on a throwaway copy of the website's structure (a twin, kind "check",
  no rows of hers, no staff of hers, never reaching outside services) by four people: a visitor, two members and an admin;
  each answer must be what the rule says (an "own" list hides one member's entries from another, an "admin" list refuses
  a member, a staff-only field is never set by a member, a private field is never shown to a member);
- they run after every list / rule change (`after_change`, in the background) and, when the rules changed since the last
  run, before going live; a FAIL blocks going live (`blocker`) - not a dialog she can skip (Lovable's is skippable);
- the result is kept per website (`<site dir>/rule_tests.json`) with a fingerprint of the rules it played, so a change of
  rules makes it stale and it runs again.

No model call, Rs 0. Said plainly: it tests the RULES (who may do what), not whether the lists are the right ones for her
business, and a list whose sample entry the data checks refuse is reported as "data refused" with the check named."""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from ..db import now, session

log = logging.getLogger("santosh.site.rulecheck")

_RUN = threading.Lock()
WHO = {"anon": "a visitor", "a": "its owner (a member)", "b": "another member", "c": "the admin"}
SKIP_TYPES = ("photo", "location", "scan", "file", "signature", "photos", "video", "audio", "ref")


def _site_file(r) -> Path:
    from . import build as B
    return B.site_dir(r.tenant_id, r.id) / "rule_tests.json"


def _main(r):
    """The website's own data project (never a twin)."""
    from . import applink as AL
    from . import twin as TW
    p = AL.project(r)
    if p is not None and TW.is_twin(p):
        p = TW._load(TW.of(p))
    return p


def _schema(p) -> dict[str, Any]:
    from ..appmaker import backend as BE
    return BE.schema(p)


def _lists(sch: dict[str, Any]) -> list[dict[str, Any]]:
    return [c for c in sch.get("collections") or [] if not str(c.get("key", "")).startswith("_")]


def fingerprint(sch: dict[str, Any]) -> str:
    """What the result depends on: each list's rules, its field flags and its gate - not its labels or rows."""
    view = [{"k": c["key"], "r": c.get("rules"), "g": c.get("gate"),
             "f": [[f["key"], f.get("type"), bool(f.get("admin_only")), bool(f.get("private")), bool(f.get("required"))]
                   for f in c.get("fields") or []]} for c in _lists(sch)]
    return hashlib.sha256(json.dumps(view, sort_keys=True).encode()).hexdigest()[:20]


def _sample(f: dict[str, Any]) -> Any:
    t = f.get("type")
    return {"number": 7, "phone": "9876500000", "email": "rule-check@example.com", "date": date.today().isoformat(),
            "yes_no": True, "url": "https://example.com/check", "choice": (f.get("options") or [""])[-1]}.get(t, "Rule check")


def _member(site: str, name: str, role: str):
    from . import webapp as W
    with session() as s:
        m = W.SiteAppMember(site_id=site, email=f"rule-{name}-{uuid.uuid4().hex[:6]}@example.com", name=f"Check {name}",
                            pw="!", role=role, gen=0)
        s.add(m)
        s.flush()
        s.expunge(m)
    return W.Who(member=m)


def _seed(site: str, coll: str, owner: str, data: dict[str, Any]) -> str:
    from . import webapp as W
    with session() as s:
        row = W.SiteAppRow(site_id=site, coll=coll, owner=owner, data=json.dumps(data, ensure_ascii=False))
        s.add(row)
        s.flush()
        return row.id


def _wipe_rows(site: str, coll: str) -> None:
    from . import webapp as W
    with session() as s:
        s.query(W.SiteAppRow).filter(W.SiteAppRow.site_id == site, W.SiteAppRow.coll == coll).delete(synchronize_session=False)


def _try(fn, *a) -> tuple[str, Any, str]:
    """('allowed' | 'denied', result, note). A refusal of the DATA (not of the person) still means the rule let them in."""
    from . import webapp as W
    try:
        return "allowed", fn(*a), ""
    except W.AppError as e:
        if e.code in (401, 403):
            return "denied", None, ""
        return "allowed", None, f"data refused ({e.code}): {str(e)[:120]}"


def play(main) -> dict[str, Any]:
    """Play every list's rules against the real engine on a throwaway copy. Never touches her rows or members."""
    from ..appmaker import backend as BE
    from . import twin as TW
    from . import webapp as W
    sch = _schema(main)
    lists = _lists(sch)
    checks: list[dict[str, Any]] = []

    def chk(lst: str, name: str, want: str, got: str, note: str = "") -> None:
        checks.append({"list": lst, "check": name, "want": want, "got": got, "ok": want == got, "note": note})

    with _RUN:
        t = TW.make(main, "check", staff=False)
        try:
            site = BE.bid(t)
            for c in _lists(_schema(t)):
                k, rl = c["key"], c.get("rules") or {}
                who = {"anon": W.Who(), "a": _member(site, "a", "member"), "b": _member(site, "b", "member"),
                       "c": _member(site, "c", "admin")}          # fresh people per list (the per-person write limit)
                fields = [f for f in c.get("fields") or [] if f.get("type") not in SKIP_TYPES and not f.get("hidden")]
                data = {f["key"]: _sample(f) for f in fields}
                # add
                want_c = {"public": {"anon": "allowed", "a": "allowed", "c": "allowed"},
                          "member": {"anon": "denied", "a": "allowed", "c": "allowed"},
                          "admin": {"anon": "denied", "a": "denied", "c": "allowed"}}.get(rl.get("create"))
                for wk, want in (want_c or {}).items():
                    got, _res, note = _try(BE.create, t, k, dict(data), who[wk], f"10.9.{len(checks) % 250}.1")
                    chk(k, f"add as {WHO[wk]}", want, got, note)
                # a staff-only field is never set by a member (its value stays the default)
                if rl.get("create") in ("public", "member"):
                    for f in fields:
                        if not f.get("admin_only") or f.get("default") == data[f["key"]]:
                            continue
                        st, res, _note = _try(BE.create, t, k, dict(data), who["a"], "10.9.251.1")
                        if st == "allowed" and res:
                            with session() as s:
                                row = s.get(W.SiteAppRow, res["id"])
                                got_v = json.loads(row.data or "{}").get(f["key"]) if row is not None else None
                            chk(k, f"staff-only field '{f['key']}' set by a member", "not set",
                                "set" if got_v == _value_of(f, data) else "not set")
                # see one entry made by member a
                _wipe_rows(site, k)
                _seed(site, k, who["a"].id, data)
                want_r = {"public": {"anon": "1", "a": "1", "b": "1", "c": "1"},
                          "members": {"anon": "denied", "a": "1", "b": "1", "c": "1"},
                          "own": {"anon": "denied", "a": "1", "b": "0", "c": "1"},
                          "admin": {"anon": "denied", "a": "denied", "b": "denied", "c": "1"},
                          "gated": {"anon": "denied", "a": "0", "b": "0", "c": "1"}}.get(rl.get("read"))
                for wk, want in (want_r or {}).items():
                    st, rows, note = _try(BE.rows, t, k, who[wk])
                    got = st if st == "denied" else str(len(rows)) if rows is not None else "error"
                    chk(k, f"see as {WHO[wk]}", want, got, note)
                    for f in fields:                     # a private field never reaches a member; the admin sees it
                        if f.get("private") and st == "allowed" and rows:
                            chk(k, f"private field '{f['key']}' as {WHO[wk]}", "shown" if wk == "c" else "hidden",
                                "shown" if f["key"] in rows[0] else "hidden")
                # change / remove a's entry
                for opname, fn, rule in (("change", lambda rid, w: BE.update(t, k, rid, dict(data), w), rl.get("update")),
                                         ("remove", lambda rid, w: BE.delete(t, k, rid, w), rl.get("delete"))):
                    want_w = {"own": {"anon": "denied", "a": "allowed", "b": "denied", "c": "allowed"},
                              "admin": {"anon": "denied", "a": "denied", "b": "denied", "c": "allowed"}}.get(rule)
                    for wk, want in (want_w or {}).items():
                        rid = _seed(site, k, who["a"].id, data)
                        got, _res, note = _try(fn, rid, who[wk])
                        chk(k, f"{opname} as {WHO[wk]}", want, got, note)
        finally:
            TW.drop(t.id)
    failed = [c for c in checks if not c["ok"]]
    return {"ran": True, "ok": not failed, "count": len(checks), "failed": failed[:20], "checks": checks[:400],
            "lists": len(lists), "at": now().isoformat(), "fp": fingerprint(sch),
            "refused": [c for c in checks if c["note"]][:10]}


def _value_of(f: dict[str, Any], data: dict[str, Any]) -> Any:
    from . import webapp as W
    try:
        return W._value(f, data.get(f["key"]))
    except Exception:                         # noqa: BLE001
        return data.get(f["key"])


def run(r) -> dict[str, Any]:
    """Play the rules of a website now and keep the result. A website with no data lists has nothing to test."""
    main = _main(r)
    if main is None or not _lists(_schema(main)):
        out = {"ran": False, "ok": True, "count": 0, "lists": 0, "failed": [], "checks": [], "at": now().isoformat(),
               "fp": "", "say": "This website keeps no data lists, so there are no data rules to test."}
    else:
        out = play(main)
    out["say"] = out.get("say") or say(out)
    f = _site_file(r)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(out, ensure_ascii=False))
    return out


def last(r) -> dict[str, Any] | None:
    try:
        return json.loads(_site_file(r).read_text())
    except (OSError, ValueError):
        return None


def current(r) -> dict[str, Any]:
    """The kept result when it still matches the rules; otherwise a fresh run (fast: in-process, no model)."""
    main = _main(r)
    fp = fingerprint(_schema(main)) if main is not None else ""
    got = last(r)
    if got is not None and got.get("fp") == fp:
        return got
    return run(r)


def say(t: dict[str, Any]) -> str:
    if not t.get("lists"):
        return "This website keeps no data lists, so there are no data rules to test."
    if t["ok"]:
        return (f"Rule tests passed: {t['count']} checks over {t['lists']} list(s) behaved exactly as the rules say "
                f"(a visitor, two members and an admin tried every list).")
    f = t["failed"][0]
    return (f"Rule tests FAILED ({len(t['failed'])} of {t['count']}): in '{f['list']}', {f['check']} should have been "
            f"'{f['want']}' but was '{f['got']}'.")


def blocker(r) -> str:
    """'' when going live may go ahead; else the reason. A website with data must have passing rule tests for the
    rules it has NOW (run here when they changed since the last run)."""
    try:
        t = current(r)
    except Exception as e:                    # noqa: BLE001 - a test that could not run is not a pass
        log.exception("rule tests could not run")
        return f"the data rule tests could not run ({str(e)[:120]}); try Go live again, or ask Hoola to look"
    if t.get("ok"):
        return ""
    return say(t) + " Fix the list's rules, then tap Go live again."


def after_change(project) -> None:
    """A list / rule of a website's data changed: test its rules again in the background (her answer is not held up)."""
    from ..config import get_settings
    from . import twin as TW
    if project is None or TW.is_twin(project) or not get_settings().site_rule_tests_bg:
        return
    pid = project.id

    def work() -> None:
        try:
            from .models import Site
            with session() as s:
                rows = s.query(Site).filter(Site.app.like(f'%"{pid}"%')).limit(5).all()
                for x in rows:
                    s.expunge(x)
            from . import applink as AL
            for x in rows:
                if AL.linked_id(x) == pid and not getattr(x, "draft_of", ""):
                    run(x)
        except Exception:                     # noqa: BLE001
            log.exception("rule tests after a change")
    threading.Thread(target=work, daemon=True, name="rule-tests").start()
