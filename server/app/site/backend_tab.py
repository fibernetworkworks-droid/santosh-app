"""v0.991 B5 BACKEND TAB (owner: "GO B5" on docs/research/lovable/03_backend_vs_hoola.md, gap 6).

The owner could not run her website's backend from the Web Studio: the Cloud pane was a read-only table + a member list,
while backups, outside services, secrets, limits and the change log lived only under `/api/apps/*` with no screen.

This module is the Studio's one door to that backend (a website linked to its App Sahayak project). It adds only what was
missing - an overview in one call, adding an entry as the owner, and the change log - and the Studio uses the existing
`/api/apps/{ref}/*` routes for backups, restore, secrets, outside actions and limits (the same rules as before: a
restore and an outside action are her tap; a secret is typed once, sealed at once and returned by no route).
"""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("santosh.site.backend_tab")


class NotLinked(Exception):
    pass


def _linked(tenant: str, ref: str):
    from . import service as S
    r, schema, who = S._owner_app(tenant, ref)
    p = S._linked(r)
    if p is None:
        raise NotLinked("This website's data is not on the app backend yet; open the Cloud tab once to move it.")
    return r, schema, who, p


def _safe(fn, default):
    try:
        return fn()
    except Exception as e:                    # noqa: BLE001 - one part that fails never hides the rest of the overview
        log.info("backend overview part failed: %s", e)
        return {"error": str(e)[:200]} if isinstance(default, dict) else default


def overview(tenant: str, ref: str) -> dict[str, Any]:
    """Everything the Backend area shows at once: the app it runs on, usage + limits, backups, secrets (names only),
    outside actions, the last rule tests (never re-run here)."""
    from ..appmaker import backup as BK
    from ..appmaker import connect as CN
    from ..appmaker import meter as MT
    from . import rulecheck as RC
    r, schema, _who, p = _linked(tenant, ref)
    con = _safe(lambda: CN.status(p), {})
    if isinstance(con, dict):
        con = {"secrets": con.get("secrets") or [], "error": con.get("error"),
               "actions": [{k: a.get(k) for k in ("key", "label", "coll", "trigger", "approved", "leaves", "staff")}
                           for a in con.get("actions") or []],
               "runs": (con.get("runs") or [])[:10]}
    return {"site": r.id, "app": {"id": p.id, "number": p.number, "name": p.name},
            "lists": [{"key": c["key"], "label": c.get("label") or c["key"], "rules": c.get("rules") or {}}
                      for c in schema.get("collections") or [] if not str(c.get("key", "")).startswith("_")],
            "usage": _safe(lambda: MT.usage(p), {}),
            "backups": _safe(lambda: BK.snapshots(p)[:20], []),
            "connect": con,
            "rule_tests": RC.last(r)}


def add_row(tenant: str, ref: str, key: str, data: dict[str, Any]) -> dict[str, Any]:
    """Her own entry, typed in the Studio: the same checks as every other write (fields, rules, logic), journaled as hers."""
    from ..appmaker import backend as BE
    from ..appmaker import backup as BK
    from . import webapp as W
    r, schema, who, p = _linked(tenant, ref)
    W.coll(schema, key)                       # an unknown list is a plain 404
    with BK.acting(who):
        return BE.create(p, key, data if isinstance(data, dict) else {}, who, "")


def change_log(tenant: str, ref: str, coll: str = "", limit: int = 200) -> dict[str, Any]:
    """Who changed what and when (the journal every write passes through)."""
    from ..appmaker import backend as BE
    from . import security as SEC
    _r, _schema, _who, p = _linked(tenant, ref)
    rows = SEC.audit(BE.bid(p), max(1, min(int(limit or 200), 500)), str(coll or ""))
    words = {"Aap (owner)": "You (owner)", "Hoola (niyam)": "Hoola (a rule)"}
    for x in rows:
        x["by"] = words.get(x.get("by"), x.get("by"))
    return {"log": rows}


# ---------------------------------------------------------------- v0.995 B6 files (private by default) and emails
def _used_by(p) -> dict[str, list[dict[str, str]]]:
    """Which entries hold each file: one read of the website's rows, matched in memory."""
    from ..appmaker import backend as BE
    from sqlalchemy import select
    from ..db import session
    from . import webapp as W
    sch = BE.schema(p)
    kinds = {c["key"]: [f["key"] for f in c.get("fields") or [] if f.get("type") in BE.EXTRA_TYPES]
             for c in sch.get("collections") or []}
    out: dict[str, list[dict[str, str]]] = {}
    with session() as s:
        for x in s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == BE.bid(p))).all():
            keys = kinds.get(x.coll) or []
            if not keys:
                continue
            d = BE._j(x.data, {})
            for k in keys:
                for v in (d.get(k) if isinstance(d.get(k), list) else [d.get(k)]):
                    if isinstance(v, str) and v:
                        out.setdefault(v, []).append({"list": x.coll, "row": x.id})
    return out


def files(tenant: str, ref: str) -> dict[str, Any]:
    """Every file her visitors and staff sent: private unless it sits in a list anyone may read (then it is public)."""
    import json as _json
    from ..appmaker import backend as BE
    from ..db import session
    from . import webapp as W
    _r, _schema, _who, p = _linked(tenant, ref)
    d = BE._files(p)
    used = _used_by(p)
    metas = sorted(d.glob("f_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)[:500]
    owners: dict[str, str] = {}
    ids = set()
    rows = []
    for f in metas:
        try:
            m = _json.loads(f.read_text())
        except (ValueError, OSError):
            continue
        ids.add(m.get("owner") or "")
        rows.append((f.stem, m))
    with session() as s:
        for mem in s.query(W.SiteAppMember).filter(W.SiteAppMember.id.in_([i for i in ids if i])).all():
            owners[mem.id] = mem.name or mem.email
    out, total = [], 0
    for fid, m in rows:
        size = int(m.get("size") or 0)
        total += size
        kind = m.get("kind") or "photo"
        out.append({"id": fid, "kind": kind, "size": size, "at": m.get("at", ""), "public": bool(m.get("public")),
                    "by": owners.get(m.get("owner") or "", "a visitor" if not m.get("owner") else "a removed member"),
                    "used_in": used.get(fid, [])[:5]})
    return {"app": {"id": p.id}, "files": out, "count": len(out), "bytes": total,
            "say": ("Files are private: only the person who sent one, your staff and you can open it. A file becomes "
                    "public only when it sits in a list anyone may read.")}


def delete_file(tenant: str, ref: str, fid: str) -> dict[str, Any]:
    """Her tap: a file no entry uses any more is removed for good (one an entry still holds is refused)."""
    from ..appmaker import backend as BE
    from . import webapp as W
    _r, _schema, _who, p = _linked(tenant, ref)
    if BE._file_meta(p, fid) is None:
        raise W.AppError("not found", 404)
    if _used_by(p).get(fid):
        raise W.AppError("An entry still holds this file; delete or change that entry first.", 409)
    d = BE._files(p)
    for f in d.glob(fid + ".*"):
        f.unlink(missing_ok=True)
    log.info("site file %s removed by the owner", fid)
    return {"ok": True}


def mail(tenant: str, ref: str) -> dict[str, Any]:
    from . import sitemail as SM
    _r, schema, _who, p = _linked(tenant, ref)
    return {**SM.settings(p), **SM.log_view(p, 100),
            "lists": [{"key": c["key"], "label": c.get("label") or c["key"]}
                      for c in schema.get("collections") or [] if not str(c.get("key", "")).startswith("_")]}


def mail_save(tenant: str, ref: str, body: dict[str, Any]) -> dict[str, Any]:
    from . import sitemail as SM
    _r, _schema, _who, p = _linked(tenant, ref)
    SM.save_settings(p, body)
    return mail(tenant, ref)
