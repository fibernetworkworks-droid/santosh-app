"""Wave 4 (v0.586.0) const_studio: the visualisation & presentation desk (register #119, #120).

Hoola does NOT render and does NOT design the deck: it keeps the shot-brief register, the asset
checklist and the report outline - the render is the visualiser's GPU time, the deck the
architect's/PM's approval (gates: "approve a design" class)."""
from __future__ import annotations

from sqlalchemy import select

from ..db import session
from . import models as M
from .common import CstError, _dump, _j, publish


def shot_add(tenant: str, project: str, rows: list, conv: str = "") -> dict:
    """#119: rows [shot, view, time_of_day, purpose] - the brief as fed."""
    if not rows:
        raise CstError("Shot rows are needed [shot, view, time_of_day, purpose].")
    made = []
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or not r:
                continue
            it = M.CstudioItem(tenant_id=tenant, project=project, kind="shot", name=str(r[0])[:80],
                               data=_dump({"view": str(r[1])[:120] if len(r) > 1 else "",
                                           "time": str(r[2])[:40] if len(r) > 2 else "",
                                           "purpose": str(r[3])[:160] if len(r) > 3 else "",
                                           "status": "briefed"}))
            s.add(it)
            s.flush()
            made.append(it.id)
    publish(tenant, "const_studio", {"kind": "shots", "project": project, "rows": len(made)}, conv)
    return {"ok": True, "ids": made, "rows": len(made),
            "said": f"{len(made)} shot brief(s) written - rendering is your visualiser's/GPU's job."}


def shot_asset(tenant: str, project: str, shot: str, rows: list) -> dict:
    """Asset checklist per shot: [asset, needed(yes/no), status] - ready jab SAB ready hain."""
    with session() as s:
        head = s.scalars(select(M.CstudioItem).where(M.CstudioItem.tenant_id == tenant,
                                                     M.CstudioItem.project == project,
                                                     M.CstudioItem.kind == "shot",
                                                     M.CstudioItem.name == shot)).first()
        if not head:
            raise CstError(f"Shot '{shot}' not found - run action=shot_add first.")
        for r in rows:
            if not isinstance(r, (list, tuple)) or not r:
                continue
            s.add(M.CstudioItem(tenant_id=tenant, project=project, kind="shot_asset", ref=head.id,
                                name=str(r[0])[:120],
                                data=_dump({"needed": str(r[1])[:8] if len(r) > 1 else "yes",
                                            "status": str(r[2])[:40] if len(r) > 2 else "pending"})))
    return {"ok": True, "shot": shot, "rows": len(rows),
            "said": f"{len(rows)} asset row(s) under '{shot}'."}


def report_add(tenant: str, project: str, name: str, rows: list, conv: str = "") -> dict:
    """#120: report/slide outline - rows [section, kind, status]."""
    if not name or not rows:
        raise CstError("Give the report's name and section rows [section, kind, status].")
    made = []
    with session() as s:
        head = M.CstudioItem(tenant_id=tenant, project=project, kind="report", name=name[:120],
                             data=_dump({"sections": len(rows)}))
        s.add(head)
        s.flush()
        rid = head.id
        for r in rows:
            if not isinstance(r, (list, tuple)) or not r:
                continue
            it = M.CstudioItem(tenant_id=tenant, project=project, kind="report_asset", ref=rid,
                               name=str(r[0])[:160],
                               data=_dump({"kind": str(r[1])[:40] if len(r) > 1 else "",
                                           "status": str(r[2])[:40] if len(r) > 2 else "pending"}))
            s.add(it)
            made.append(it.id)
    publish(tenant, "const_studio", {"kind": "report", "project": project, "name": name}, conv)
    return {"ok": True, "id": rid, "rows": len(made),
            "said": f"Outline '{name}' written ({len(made)} section(s)) - make the deck; the approval is yours."}


def studio_status(tenant: str, project: str, ref: str = "") -> dict:
    """Checklist status: pending vs ready per shot/report."""
    q = select(M.CstudioItem).where(M.CstudioItem.tenant_id == tenant,
                                    M.CstudioItem.project == project)
    if ref:
        q = q.where(M.CstudioItem.ref == ref)
    with session() as s:
        rows = s.scalars(q).all()
    out: dict[str, dict] = {}
    for r in rows:
        if r.kind not in ("shot_asset", "report_asset"):
            continue
        d = _j(r.data, {})
        o = out.setdefault(r.ref, {"pending": 0, "ready": 0, "items": []})
        st = str(d.get("status") or "pending").lower()
        if st in ("ready", "done", "ok", "received"):
            o["ready"] += 1
        else:
            o["pending"] += 1
        o["items"].append({"name": r.name, "status": st})
    return {"ok": True, "groups": [{"ref": k, **v} for k, v in out.items()],
            "said": ("Some rows are pending - wait for the render/report." if any(v["pending"] for v in out.values())
                     else "All ready.")}
