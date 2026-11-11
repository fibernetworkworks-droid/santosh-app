"""Wave 4 (v0.586.0) const_fm: the facility/property FM rows (#102, #103, #105, #106, #107, #108).

These seats belong to the EXISTING property/society employees (plan §12) - the tools below ride
their hire (roles.py duty `fm_work`), no new hire key. Same laws: due-dates and gaps are arithmetic
on FED rows, the compliance certificate is the agency's, and the structural-audit certificate is
the registered structural engineer's (gates.py)."""
from __future__ import annotations

from sqlalchemy import select

from ..db import session
from . import models as M
from .common import CstError, _dump, _j, _num, publish, today


def wo_add(tenant: str, project: str, location: str, issue: str, priority: str = "normal",
           conv: str = "") -> dict:
    """#102: one work order (open)."""
    if not location or not issue:
        raise CstError("Give both the location and the issue.")
    with session() as s:
        it = M.CfmItem(tenant_id=tenant, project=project, kind="wo", name=issue[:160],
                       data=_dump({"location": location[:160], "priority": priority[:12]}))
        s.add(it)
        s.flush()
        wid = it.id
    publish(tenant, "const_fm", {"kind": "wo", "project": project, "wo": wid}, conv)
    return {"ok": True, "id": wid, "status": "open",
            "said": f"Work order {wid} opened ({location}, {priority})."}


def wo_update(tenant: str, wo: str, status: str, by: str) -> dict:
    """Status change WITHOUT the doer's name refuses (the clash_mark law)."""
    if not by:
        raise CstError("The WO status needs the NAME of the person doing it.")
    if status not in ("open", "in_progress", "done", "cancelled"):
        raise CstError("status open | in_progress | done | cancelled.")
    with session() as s:
        it = s.get(M.CfmItem, wo)
        if not it or it.tenant_id != tenant:
            raise CstError("Work order not found.")
        it.status = status
        d = _j(it.data, {})
        d["last_by"] = by
        it.data = _dump(d)
    return {"ok": True, "id": wo, "status": status, "by": by, "said": f"WO {wo} -> {status} ({by})."}


def ppm_add(tenant: str, project: str, rows: list, conv: str = "") -> dict:
    """#103: rows [asset, task, freq_days, last_done] - next due = last + freq (arithmetic)."""
    if not rows:
        raise CstError("PPM rows are needed [asset, task, freq_days, last_done].")
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 3:
                continue
            freq = _num(r[2])
            if freq <= 0:
                raise CstError(f"Row '{r[0]}': freq_days 0 se bada do.")
            s.add(M.CfmItem(tenant_id=tenant, project=project, kind="ppm", name=str(r[0])[:120],
                            data=_dump({"task": str(r[1])[:160], "freq_days": freq,
                                        "last_done": str(r[3])[:10] if len(r) > 3 else ""})))
            made += 1
    publish(tenant, "const_fm", {"kind": "ppm", "project": project, "rows": made}, conv)
    return {"ok": True, "rows": made, "said": f"{made} PPM task(s) - next due = last + frequency."}


def ppm_due(tenant: str, project: str = "") -> dict:
    """Next-due arithmetic from the datetime module - no scheduler runs, the list is the act."""
    from datetime import timedelta
    q = select(M.CfmItem).where(M.CfmItem.tenant_id == tenant, M.CfmItem.kind == "ppm")
    if project:
        q = q.where(M.CfmItem.project == project)
    with session() as s:
        rows = s.scalars(q).all()
    t0 = today(tenant)
    out = []
    for r in rows:
        d = _j(r.data, {})
        last = str(d.get("last_done") or "")
        if not last:
            out.append({"asset": r.name, "task": d.get("task"), "verdict": "NO LAST DATE FED"})
            continue
        nxt = None
        from datetime import date as _d, timedelta as _td
        try:
            last_d = _d.fromisoformat(last)
            nxt = last_d + _td(days=int(float(d.get("freq_days") or 0)))
        except ValueError:
            out.append({"asset": r.name, "task": d.get("task"), "verdict": "BAD LAST DATE"})
            continue
        out.append({"asset": r.name, "task": d.get("task"), "last_done": last,
                    "next_due": nxt.isoformat(),
                    "verdict": ("OVERDUE" if nxt < t0 else
                                ("due soon" if (nxt - t0).days <= 7 else "ok"))})
    n_over = sum(1 for o in out if o.get("verdict") == "OVERDUE")
    return {"ok": True, "rows": out, "overdue": n_over,
            "said": f"{n_over} PPM overdue - the FM decides which goes to the vendor."}


def comp_add(tenant: str, project: str, rows: list, conv: str = "") -> dict:
    """#105: compliance calendar rows [system(lift|fire|stp|wtp|other), cert_no, agency, last, due]."""
    if not rows:
        raise CstError("Compliance rows are needed [system, cert_no, agency, last, due].")
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 5:
                continue
            s.add(M.CfmItem(tenant_id=tenant, project=project, kind="comp", name=str(r[0])[:40],
                            data=_dump({"cert_no": str(r[1])[:80], "agency": str(r[2])[:120],
                                        "last": str(r[3])[:10], "due": str(r[4])[:10]})))
            made += 1
    publish(tenant, "const_fm", {"kind": "compliance", "project": project, "rows": made}, conv)
    return {"ok": True, "rows": made,
            "said": f"{made} compliance row(s) - the agency gives the certificate, Hoola keeps the calendar."}


def comp_due(tenant: str, project: str = "") -> dict:
    q = select(M.CfmItem).where(M.CfmItem.tenant_id == tenant, M.CfmItem.kind == "comp")
    if project:
        q = q.where(M.CfmItem.project == project)
    with session() as s:
        rows = s.scalars(q).all()
    t0 = today(tenant)
    out = []
    for r in rows:
        d = _j(r.data, {})
        due = str(d.get("due") or "")
        if not due:
            out.append({"system": r.name, "verdict": "NO DUE FED"})
            continue
        out.append({"system": r.name, "cert_no": d.get("cert_no"), "agency": d.get("agency"),
                    "due": due, "verdict": "OVERDUE" if due < t0.isoformat() else "in date"})
    n_over = sum(1 for o in out if o.get("verdict") == "OVERDUE")
    return {"ok": True, "rows": out, "overdue": n_over,
            "said": (f"{n_over} renewal(s) overdue - getting the inspection booked is your/the FM's job."
                     if n_over else "All renewals are in date.")}


def roster_add(tenant: str, project: str, rows: list) -> dict:
    """#106: rows [post, weekday, shift, person] - person khaali = khali post."""
    if not rows:
        raise CstError("Roster rows are needed [post, weekday, shift, person].")
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 3:
                continue
            s.add(M.CfmItem(tenant_id=tenant, project=project, kind="roster", name=str(r[0])[:60],
                            data=_dump({"weekday": str(r[1])[:12], "shift": str(r[2])[:24],
                                        "person": str(r[3])[:80] if len(r) > 3 else ""})))
            made += 1
    return {"ok": True, "rows": made, "said": f"{made} roster row(s) likhi."}


def roster_gap(tenant: str, project: str) -> dict:
    """Unfilled posts = arithmetic on the fed rows."""
    with session() as s:
        rows = s.scalars(select(M.CfmItem).where(M.CfmItem.tenant_id == tenant,
                                                 M.CfmItem.project == project,
                                                 M.CfmItem.kind == "roster")).all()
    gaps = [{"post": r.name, **_j(r.data, {})} for r in rows if not (_j(r.data, {}).get("person"))]
    return {"ok": True, "posts": len(rows), "gaps": gaps,
            "said": f"{len(gaps)} vacant post(s) - arranging cover is yours."}


def audit_add(tenant: str, project: str, rows: list) -> dict:
    """#107: rows [building, audit_type, last_done, cycle_yrs(FED with source on the note),
    agency] - the cycle is HER municipal rule, fed; Hoola only adds."""
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 4:
                continue
            cyc = _num(r[3])
            if cyc <= 0:
                raise CstError(f"Row '{r[0]}': give cycle_yrs from your municipal circular (not 0).")
            s.add(M.CfmItem(tenant_id=tenant, project=project, kind="audit", name=str(r[0])[:120],
                            data=_dump({"audit_type": str(r[1])[:60], "last": str(r[2])[:10],
                                        "cycle_yrs": cyc,
                                        "agency": str(r[4])[:120] if len(r) > 4 else ""})))
            made += 1
    return {"ok": True, "rows": made,
            "said": "The audit cycle is fed from YOUR circular - the certificate is the registered engineer's / agency's (tier C)."}


def audit_due(tenant: str, project: str = "") -> dict:
    from datetime import timedelta
    q = select(M.CfmItem).where(M.CfmItem.tenant_id == tenant, M.CfmItem.kind == "audit")
    if project:
        q = q.where(M.CfmItem.project == project)
    with session() as s:
        rows = s.scalars(q).all()
    out = []
    for r in rows:
        d = _j(r.data, {})
        last = str(d.get("last") or "")
        if not last:
            out.append({"building": r.name, "verdict": "NO LAST AUDIT FED"})
            continue
        from datetime import date as _d
        y, m, dd = (int(x) for x in last.split("-"))
        nxt = _d(y, m, dd) + timedelta(days=int(365.25 * float(d.get("cycle_yrs") or 0)))
        t0 = today(tenant)
        out.append({"building": r.name, "audit_type": d.get("audit_type"), "last": last,
                    "next_due": nxt.isoformat(),
                    "verdict": "OVERDUE" if nxt < t0 else "in date"})
    n_over = sum(1 for o in out if o.get("verdict") == "OVERDUE")
    return {"ok": True, "rows": out, "overdue": n_over,
            "said": (f"{n_over} audit(s) overdue - book the structural engineer (the certificate is theirs)."
                     if n_over else "Audits in date.")}


def asset_add(tenant: str, project: str, rows: list) -> dict:
    """#108: rows [asset, space, dept, warranty_till]."""
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 2:
                continue
            s.add(M.CfmItem(tenant_id=tenant, project=project, kind="asset", name=str(r[0])[:120],
                            data=_dump({"space": str(r[1])[:80], "dept": str(r[2])[:80] if len(r) > 2 else "",
                                        "warranty_till": str(r[3])[:10] if len(r) > 3 else ""})))
            made += 1
    return {"ok": True, "rows": made, "said": f"{made} asset/space row(s) likhi."}


def dekho(tenant: str, what: str, project: str = "") -> dict:
    q_kind = {"wo": "wo", "ppm": "ppm", "comp": "comp", "roster": "roster", "audit": "audit",
              "asset": "asset"}.get(what, "")
    if not q_kind:
        raise CstError("what: wo | ppm | comp | roster | audit | asset.")
    q = select(M.CfmItem).where(M.CfmItem.tenant_id == tenant, M.CfmItem.kind == q_kind)
    if project:
        q = q.where(M.CfmItem.project == project)
    with session() as s:
        rows = s.scalars(q).all()
    return {what: [{"id": r.id, "project": r.project, "name": r.name, "status": r.status,
                    "data": _j(r.data, {})} for r in rows]}
