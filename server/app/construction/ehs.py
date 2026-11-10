"""Wave 4 (v0.586.0) const_ehs: the safety, environment & welfare desk (register #83, #84, #86).

Readings and limits are FED with their sources (Hoola seats no sensors, no monitors); expiry and
exceedance are arithmetic; "declare the site safe / resume work" stays with the EHS head (gates.py)
and the welfare verdict with the labour welfare officer."""
from __future__ import annotations

from sqlalchemy import select

from ..db import session
from . import models as M
from .common import CstError, _dump, _j, _num, publish, today


def training_add(tenant: str, project: str, rows: list, conv: str = "") -> dict:
    """#83: rows [name, trade, training, date, valid_till] - as per the register/log she pastes."""
    if not rows:
        raise CstError("Training rows chahiye [name, trade, training, date, valid_till].")
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 5:
                continue
            s.add(M.CEhsItem(tenant_id=tenant, project=project, kind="training",
                             name=str(r[0])[:120],
                             data=_dump({"trade": str(r[1])[:80], "training": str(r[2])[:120],
                                         "date": str(r[3])[:10], "valid_till": str(r[4])[:10]})))
            made += 1
    publish(tenant, "const_ehs", {"kind": "training", "project": project, "rows": made}, conv)
    return {"ok": True, "rows": made,
            "said": f"{made} training row(s) likhi - validity register ki hai, certificate copy aapki file mein."}


def training_due(tenant: str, project: str = "") -> dict:
    """Expiry arithmetic: expired, due-in-30-days, valid."""
    q = select(M.CEhsItem).where(M.CEhsItem.tenant_id == tenant, M.CEhsItem.kind == "training")
    if project:
        q = q.where(M.CEhsItem.project == project)
    with session() as s:
        rows = s.scalars(q).all()
    t0 = today(tenant)
    from datetime import timedelta
    soon = t0 + timedelta(days=30)
    expired, due, valid = [], [], 0
    for r in rows:
        d = _j(r.data, {})
        vt = str(d.get("valid_till") or "")
        if not vt:
            continue
        if vt < t0.isoformat():
            expired.append({"name": r.name, **d})
        elif vt <= soon.isoformat():
            due.append({"name": r.name, **d})
        else:
            valid += 1
    return {"ok": True, "expired": expired, "due_30d": due, "valid": valid,
            "said": ("Refresher training EHS head hi schedule karega - yeh sirf expiry ka hisaab hai.")}


def env_add(tenant: str, project: str, kind: str, rows: list, source: str = "", conv: str = "") -> dict:
    """#84: kind=env_read [parameter, value, unit] (HER monitoring report ka number) ya
    kind=env_limit [parameter, limit, unit] - LIMIT ke saath source zaroori."""
    if kind not in ("env_read", "env_limit"):
        raise CstError("kind env_read | env_limit.")
    if kind == "env_limit" and not source:
        raise CstError("Limit ke saath source zaroori hai (CPCB/SPCB norm ka naam).")
    if not rows:
        raise CstError("rows chahiye.")
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 2:
                continue
            data = ({"parameter": str(r[0])[:80], "value": _num(r[1]), "unit": str(r[2])[:16] if len(r) > 2 else ""}
                    if kind == "env_read" else
                    {"parameter": str(r[0])[:80], "limit": _num(r[1]), "unit": str(r[2])[:16] if len(r) > 2 else ""})
            s.add(M.CEhsItem(tenant_id=tenant, project=project, kind=kind, name=str(r[0])[:80],
                             data=_dump(data), source=source))
            made += 1
    publish(tenant, "const_ehs", {"kind": kind, "project": project, "rows": made}, conv)
    return {"ok": True, "rows": made, "source": source,
            "said": f"{made} {kind} row(s) - readings aapki monitoring report se."}


def env_check(tenant: str, project: str) -> dict:
    """Exceedance = arithmetic on HER readings vs HER limits (with sources)."""
    with session() as s:
        reads = s.scalars(select(M.CEhsItem).where(M.CEhsItem.tenant_id == tenant,
                                                   M.CEhsItem.project == project,
                                                   M.CEhsItem.kind == "env_read")).all()
        limits = s.scalars(select(M.CEhsItem).where(M.CEhsItem.tenant_id == tenant,
                                                    M.CEhsItem.project == project,
                                                    M.CEhsItem.kind == "env_limit")).all()
    if not limits:
        raise CstError("Pehle limits jodo (kind=env_limit, source ke saath) - bina limit exceedance nahi.")
    lm = {}
    for l in limits:
        d = _j(l.data, {})
        lm[d.get("parameter", "").lower()] = d
    out = []
    for r in reads:
        d = _j(r.data, {})
        lim = lm.get(str(d.get("parameter") or "").lower())
        if not lim:
            out.append({"parameter": d.get("parameter"), "value": d.get("value"), "verdict": "NO LIMIT FED"})
            continue
        exceed = float(d.get("value") or 0) > float(lim.get("limit") or 0)
        out.append({"parameter": d.get("parameter"), "value": d.get("value"), "unit": d.get("unit"),
                    "limit": lim.get("limit"), "limit_source": lim.get("source") or "",
                    "verdict": "EXCEEDS" if exceed else "within"})
    n_ex = sum(1 for o in out if o.get("verdict") == "EXCEEDS")
    return {"ok": True, "rows": out, "exceeds": n_ex,
            "said": (f"{n_ex} row(s) limit cross karti hain - report SPCB/EHS head ko bhejne ka decision aapka."
                     if n_ex else "Sab readings fed limits ke andar.")}


def camp_add(tenant: str, project: str, rows: list) -> dict:
    """#86: rows [block, capacity, occupancy]."""
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 3:
                continue
            cap, occ = _num(r[1]), _num(r[2])
            s.add(M.CEhsItem(tenant_id=tenant, project=project, kind="camp", name=str(r[0])[:80],
                             data=_dump({"capacity": cap, "occupancy": occ,
                                         "util_pct": round(occ / cap * 100, 1) if cap else None})))
            made += 1
    return {"ok": True, "rows": made, "said": f"{made} camp block(s) likhi."}


def camp_check(tenant: str, project: str, rows: list, by: str = "") -> dict:
    """#86: facilities checklist [item, status] - a status WITHOUT `by` refuses (the clash_mark law);
    the welfare verdict stays the labour welfare officer's."""
    if not by:
        raise CstError("Checklist ki status ke saath US KA NAAM jo check kar raha hai (welfare officer).")
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 2:
                continue
            s.add(M.CEhsItem(tenant_id=tenant, project=project, kind="camp_check", name=str(r[0])[:120],
                             data=_dump({"status": str(r[1])[:40], "by": by})))
            made += 1
    return {"ok": True, "rows": made, "by": by,
            "said": f"{made} check row(s), checker: {by}. Welfare ka verdict officer ka hai."}
