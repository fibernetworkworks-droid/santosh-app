"""v0.989 B2 SEPARATE DATA (owner: "GO B1 B2" on docs/research/lovable/03_backend_vs_hoola.md).

A website's data lives in its App Sahayak project (`app:<id>` rows + members). Before this, the Studio preview and every
draft of a linked website read and wrote THOSE rows: testing a sign-up in the preview made a real member, and a draft -
which told her "It has its own data" - wrote into the live site (`drafts.create` copied the site's `link`).

Now a TWIN project holds the data of the preview and of each draft:
- the preview twin follows the website's structure (lists, fields, rules, logic) and keeps its own rows and members; the
  preview pages call `/api/site-app/<site>~p`, the live site calls `/api/site-app/<site>`;
- a draft gets its own twin when it starts (a fork: it does not follow the website after that); Accept carries only the
  NEW lists / fields it added into the website (additive, like every schema change), never its rows;
- a twin never reaches the outside world: no payment gateway, no outgoing actions, no her-own-database write-through,
  no scheduled jobs, no owner notes (Lovable's drafts run on LIVE secrets - Hoola stays stricter);
- the website's staff / admin accounts are copied in (new ids, same email + password) so she can sign in to test.
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
from typing import Any

from ..db import new_id, now, session

log = logging.getLogger("santosh.site.twin")

PREVIEW = "~p"                    # the preview pages' dataset marker on /api/site-app/<site>~p
STRIP = ("pay", "owndb", "connect", "khata_remind", "quota_told", "twins")   # never copied into a twin
MINE = ("twin_of", "twin_kind", "synced")                                     # a twin's own keys, kept across a sync


def _j(s: Any, d: Any) -> Any:
    try:
        return json.loads(s) if s else d
    except (TypeError, ValueError):
        return d


def split(site_id: str) -> tuple[str, str]:
    """'<site>~p' -> ('<site>', 'p'); a plain id -> (id, '')."""
    s = str(site_id or "")
    if s.endswith(PREVIEW):
        return s[: -len(PREVIEW)], "p"
    return s, ""


def of(p) -> str:
    """The project a twin copies ('' = not a twin)."""
    if p is None:
        return ""
    return str((_j(getattr(p, "backend", None), {}) or {}).get("twin_of") or "")


def is_twin(p) -> bool:
    return bool(of(p))


def _digest(p) -> str:
    be = {k: v for k, v in (_j(p.backend, {}) or {}).items() if k not in STRIP}
    return hashlib.sha256((json.dumps(be, sort_keys=True, default=str) + "|" + (p.plan or "")).encode()).hexdigest()[:24]


def _twin_backend(main, kind: str, mine: dict[str, Any] | None = None) -> str:
    be = {k: v for k, v in copy.deepcopy(_j(main.backend, {}) or {}).items() if k not in STRIP}
    be.update(mine or {})
    be.update({"twin_of": main.id, "twin_kind": kind, "synced": _digest(main)})
    return json.dumps(be, ensure_ascii=False)


def _copy_staff(main_id: str, twin_id: str) -> int:
    """Her staff / admin accounts in the twin (new ids, same email + password hash), so she can sign in to test."""
    from ..appmaker import backend as BE
    from . import webapp as W
    W.ensure_tables()
    n = 0
    with session() as s:
        rows = s.query(W.SiteAppMember).filter(W.SiteAppMember.site_id == BE.bid(main_id),
                                               W.SiteAppMember.role.in_(("staff", "admin"))).limit(50).all()
        for m in rows:
            s.add(W.SiteAppMember(id=new_id("mem"), site_id=BE.bid(twin_id), email=m.email, name=m.name, pw=m.pw,
                                  role=m.role, gen=0, phone=m.phone, consent=m.consent, totp=m.totp, ext=None))
            n += 1
    return n


def make(main, kind: str, staff: bool = True):
    """A new twin of `main` (kind 'preview' | 'draft' | 'check'): same plan + structure, no rows, her staff accounts
    copied (not for a rule check, which brings its own people)."""
    from ..appmaker.models import AppProject
    with session() as s:
        t = AppProject(id=new_id("app"), tenant_id=main.tenant_id, number="", name=main.name, brief=main.brief,
                       field=main.field, goal=main.goal, style=main.style, styles=main.styles, language=main.language,
                       facts=main.facts, answers=main.answers, plan=main.plan, looks="[]", look=main.look,
                       status="twin", stage="twin", conv="", android=None, backend=_twin_backend(main, kind))
        s.add(t)
        s.flush()
        s.expunge(t)
    if staff:
        _copy_staff(main.id, t.id)
    return t


def _load(pid: str):
    from ..appmaker.models import AppProject
    if not pid:
        return None
    with session() as s:
        p = s.get(AppProject, pid)
        if p is not None:
            s.expunge(p)
        return p


def preview_of(main):
    """The preview twin of a website's project, made on first use and brought up to the website's structure whenever it
    changed (lists, fields, rules, logic - never rows). A draft's own twin is its preview."""
    if main is None or is_twin(main):
        return main
    from ..appmaker import backend as BE
    main = _load(main.id) or main                 # the row as it is NOW (a caller's copy can be older than its twin)
    tid = str(((_j(main.backend, {}) or {}).get("twins") or {}).get("preview") or "")
    t = _load(tid)
    if t is None or of(t) != main.id:
        t = make(main, "preview")
        won: dict[str, str] = {}

        def keep(be):                             # under the app's lock: the first twin made wins, a racing one goes
            tw = be.setdefault("twins", {})
            old = _load(str(tw.get("preview") or ""))
            if old is not None and of(old) == main.id:
                won["id"] = old.id
            else:
                tw["preview"] = won["id"] = t.id
        BE.patch_backend(main, fn=keep)
        if won.get("id") != t.id:
            drop(t.id)
            t = _load(won["id"])
        return t
    if (_j(t.backend, {}) or {}).get("synced") != _digest(main):
        mine = {k: v for k, v in (_j(t.backend, {}) or {}).items() if k in MINE}
        from ..appmaker.models import AppProject
        with session() as s:
            row = s.get(AppProject, t.id)
            row.plan = main.plan
            row.backend = _twin_backend(main, mine.get("twin_kind") or "preview", mine)
            row.updated_at = now()
        t = _load(t.id)
    return t


def drop(pid: str) -> None:
    """A twin goes away with its rows, members and sessions (only ever a twin)."""
    from ..appmaker import backend as BE
    from ..appmaker.models import AppProject
    from . import webapp as W
    t = _load(pid)
    if t is None or not is_twin(t):
        return
    W.ensure_tables()
    with session() as s:
        s.query(W.SiteAppRow).filter(W.SiteAppRow.site_id == BE.bid(pid)).delete(synchronize_session=False)
        s.query(W.SiteAppMember).filter(W.SiteAppMember.site_id == BE.bid(pid)).delete(synchronize_session=False)
        row = s.get(AppProject, pid)
        if row is not None:
            s.delete(row)


def carry(twin_id: str, main_id: str) -> list[str]:
    """Accept: the lists and fields the draft ADDED go into the website (additive, never its rows). Returns what moved."""
    from ..appmaker import backend as BE
    t, m = _load(twin_id), _load(main_id)
    if t is None or m is None or of(t) != m.id:
        return []
    old = {c["key"]: c for c in ((BE.ensure(m).get("schema") or {}).get("collections") or [])}
    new = (BE.ensure(t).get("schema") or {}).get("collections") or []
    ops: dict[str, Any] = {"add_list": [], "add": []}
    for c in new:
        if c["key"] not in old:
            ops["add_list"].append({"key": c["key"], "label": c.get("label"), "rules": c.get("rules") or {},
                                    "fields": [{k: v for k, v in f.items()} for f in c.get("fields") or []]})
            continue
        have = {f["key"] for f in old[c["key"]].get("fields") or []}
        for f in c.get("fields") or []:
            if f["key"] not in have:
                ops["add"].append({"coll": c["key"], **{k: v for k, v in f.items()}})
    if not (ops["add_list"] or ops["add"]):
        return []
    try:
        BE.change_schema(m, ops, "draft accepted: the lists / fields it added")
    except Exception as e:                      # noqa: BLE001 - Accept never fails on the data side; it says what did not move
        log.info("draft carry failed: %s", e)
        return [f"not moved: {e}"]
    return [f"list {x['key']}" for x in ops["add_list"]] + [f"field {x['coll']}.{x['key']}" for x in ops["add"]]
