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
