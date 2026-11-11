"""Wave 4 (v0.586.0) const_land: the land & feasibility desk (register #1-#6).

Same laws as every construction desk: the record says what was FED and who said it, arithmetic is
arithmetic, and the reserved acts stay with the humans - the title opinion is the title advocate's
(gates.py: "certify a clear title"), the JV/land terms are signed by the owner, the funding
structure is the CFO's. Hoola never fetches a land record: rows are pasted with their source."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select

from ..db import session
from . import models as M
from .common import CstError, _dump, _j, _num, _rs, publish, today


def _w(data: dict) -> dict:
    return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------- parcels (#1)
def parcel_add(tenant: str, project: str, survey_no: str, village: str, area: float,
               area_source: str, area_unit: str = "sqm", note: str = "", conv: str = "") -> dict:
    if not project or not survey_no:
        raise CstError("Both the project and the survey no are needed.")
    if area <= 0:
        raise CstError("The area must be more than 0 - and the name of the source is required (7/12 / mutation / agreement).")
    if not area_source:
        raise CstError("An area is not written without a source (name the 7/12 / mutation / agreement).")
    with session() as s:
        p = M.CLandParcel(tenant_id=tenant, project=project, survey_no=survey_no, village=village,
                          area=area, area_unit=area_unit, area_source=area_source, note=note)
        s.add(p)
        s.flush()
        pid = p.id
    publish(tenant, "const_land", {"kind": "parcel", "project": project, "survey_no": survey_no}, conv)
    return {"ok": True, "id": pid, "project": project, "survey_no": survey_no,
            "area": area, "area_unit": area_unit, "area_source": area_source,
            "said": f"Parcel {survey_no} ({village}) - area {area} {area_unit}, source: {area_source}."}


# ---------------------------------------------------------------- items (#1-#6)
_KINDS = ("title", "record", "criterion", "worksheet", "finance", "funding", "jv")


def item_add(tenant: str, project: str, kind: str, rows: list, by: str = "", source: str = "",
             note: str = "", conv: str = "") -> dict:
    """kind=title: [doc, status] - a status mark WITHOUT `by` refuses (the clash_mark law).
    kind=record: [doc_no, area, date] - the reconciler totals these against the parcel.
    kind=criterion: [criterion, weight, score] - weights and scores are HER marks, sum is arithmetic.
    kind=worksheet: fsi (FED w/ source) + rows [use, builtup] - permissible = fsi x plot area.
    kind=finance: [head, amount]; kind=funding: [source, amount]; kind=jv: [party, share_pct]."""
    if kind not in _KINDS:
        raise CstError(f"kind '{kind}' is not valid - one of: {', '.join(_KINDS)}.")
    if not rows or not isinstance(rows, list):
        raise CstError("rows are needed (list of lists).")
    if kind == "title":
        if not by:
            raise CstError("A title document's status comes with the NAME of the person who stated it (the clash_mark law).")
    if kind in ("worksheet", "finance", "jv") and not source:
        raise CstError(f"{kind} row needs a source (FSI zone row / deed / cost sheet) - a number without a source is not written.")
    made = []
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or not r:
                continue
            name = str(r[0])[:160]
            data: dict[str, Any] = {}
            if kind == "title":
                data = {"doc": name, "status": str(r[1])[:40] if len(r) > 1 else "", "by": by}
            elif kind == "record":
                data = {"doc_no": name, "area": _num(r[1]) if len(r) > 1 else 0.0,
                        "date": str(r[2])[:10] if len(r) > 2 else ""}
            elif kind == "criterion":
                data = {"criterion": name, "weight": _num(r[1]) if len(r) > 1 else 0.0,
                        "score": _num(r[2]) if len(r) > 2 else 0.0}
            elif kind == "worksheet":
                data = {"use": name, "builtup": _num(r[1]) if len(r) > 1 else 0.0}
            elif kind == "finance":
                data = {"head": name, "amount": _num(r[1]) if len(r) > 1 else 0.0}
            elif kind == "funding":
                data = {"source": name, "amount": _num(r[1]) if len(r) > 1 else 0.0}
            elif kind == "jv":
                data = {"party": name, "share_pct": _num(r[1]) if len(r) > 1 else 0.0}
            it = M.CLandItem(tenant_id=tenant, project=project, kind=kind, name=name,
                             data=_dump(data), by=by, source=source, note=note)
            s.add(it)
            s.flush()
            made.append(it.id)
    publish(tenant, "const_land", {"kind": kind, "project": project, "rows": len(made)}, conv)
    return {"ok": True, "ids": made, "kind": kind, "rows": len(made), "by": by, "source": source,
            "said": f"{len(made)} {kind} row(s) likhi ({project})."}


# ---------------------------------------------------------------- arithmetic
def records_recon(tenant: str, project: str, parcel: str = "") -> dict:
    """#3: total the FED record areas and reconcile against the parcel's claimed area."""
    with session() as s:
        q = select(M.CLandParcel).where(M.CLandParcel.tenant_id == tenant,
                                        M.CLandParcel.project == project)
        parcels = s.scalars(q).all()
        if parcel:
            parcels = [p for p in parcels if p.id == parcel]
        if not parcels:
            raise CstError("Parcel not found - add it with action=parcel_add first.")
        items = s.scalars(select(M.CLandItem).where(M.CLandItem.tenant_id == tenant,
                                                    M.CLandItem.project == project,
                                                    M.CLandItem.kind == "record")).all()
    out = []
    for p in parcels:
        recs = [_j(i.data, {}) for i in items if i.project == project]
        recs = [r for r in recs if r.get("area")]
        total = round(sum(float(r.get("area") or 0) for r in recs), 3)
        diff = round(total - float(p.area), 3)
        out.append({"parcel": p.id, "survey_no": p.survey_no, "claimed": p.area,
                    "claimed_source": p.area_source, "records": len(recs),
                    "records_total": total, "diff": diff,
                    "verdict": "match" if abs(diff) < 0.005 else "MISMATCH - check which entry",
                    "entries": [{"doc_no": r.get("doc_no"), "area": r.get("area"),
                                 "date": r.get("date")} for r in recs]})
    return {"ok": True, "kind": "records_recon", "parcels": out,
            "said": "The reconciliation is ARITHMETIC - the authoritative account of the land record is the revenue consultant's."}


def feasibility(tenant: str, project: str, plot_area: float, fsi: float, fsi_source: str,
                name: str = "") -> dict:
    """#4: permissible built-up = FSI x plot area (both FED, FSI needs its source); consumed vs
    balance against the FED worksheet rows."""
    if plot_area <= 0 or fsi <= 0:
        raise CstError("Both the plot area and the FSI are needed (more than 0).")
    if not fsi_source:
        raise CstError("No FSI without a source - name the zone/DC rule (DCR/DCP row or approval letter).")
    permissible = round(fsi * plot_area, 2)
    with session() as s:
        rows = s.scalars(select(M.CLandItem).where(M.CLandItem.tenant_id == tenant,
                                                   M.CLandItem.project == project,
                                                   M.CLandItem.kind == "worksheet")).all()
    used = round(sum(float((_j(r.data, {})).get("builtup") or 0) for r in rows), 2)
    res = {"plot_area": plot_area, "fsi": fsi, "fsi_source": fsi_source,
           "permissible_builtup": permissible, "programme_rows": len(rows),
           "programme_builtup": used, "balance": round(permissible - used, 2),
           "consumed_pct": round(used / permissible * 100, 1) if permissible else 0.0,
           "said": "The FSI is from the source you gave - the FINAL word on development potential is the DM's / architect's."}
    with session() as s:
        s.add(M.CLandItem(tenant_id=tenant, project=project, kind="worksheet", name=name or "feasibility",
                          data=_dump(res), source=fsi_source, by="",
                          note="feasibility arithmetic result"))
    return {"ok": True, "kind": "feasibility", **res}


def jv_entitlement(tenant: str, project: str, developable_area: float) -> dict:
    """#6: each party's share of the developable area - shares AS FED from the deed (with source);
    the agreement itself is signed by the owner (gates)."""
    if developable_area <= 0:
        raise CstError("The developable area must be more than 0.")
    with session() as s:
        rows = s.scalars(select(M.CLandItem).where(M.CLandItem.tenant_id == tenant,
                                                   M.CLandItem.project == project,
                                                   M.CLandItem.kind == "jv")).all()
    if not rows:
        raise CstError("No JV share rows found - add the deed's shares with action=item_add, kind=jv (with a source).")
    shares = []
    tot = 0.0
    for r in rows:
        d = _j(r.data, {})
        pct = float(d.get("share_pct") or 0)
        tot += pct
        shares.append({"party": d.get("party"), "share_pct": pct,
                       "area": round(developable_area * pct / 100, 2)})
    res = {"developable_area": developable_area, "share_total_pct": round(tot, 2),
           "shares": shares,
           "said": ("The share total is not 100% - check it." if abs(tot - 100) > 0.01
                    else "Shares add up to 100%. This is arithmetic - only the advocate reads the deed's terms.")}
    res["verdict_ok"] = abs(tot - 100) <= 0.01
    return {"ok": True, "kind": "jv_entitlement", **res}


def finance_sum(tenant: str, project: str, interest_rate_pct: float, rate_source: str,
                years: float = 0.0) -> dict:
    """#5: totals of the FED cost heads and funding rows, equity:debt, simple interest outgo on the
    FED rate (with its source). NO advice: the funding structure is the CFO's (gates)."""
    if not rate_source:
        raise CstError("Give the source of the interest rate (sanction letter / term sheet).")
    with session() as s:
        fin = s.scalars(select(M.CLandItem).where(M.CLandItem.tenant_id == tenant,
                                                  M.CLandItem.project == project,
                                                  M.CLandItem.kind == "finance")).all()
        fund = s.scalars(select(M.CLandItem).where(M.CLandItem.tenant_id == tenant,
                                                   M.CLandItem.project == project,
                                                   M.CLandItem.kind == "funding")).all()
    cost = round(sum(float(_j(r.data, {}).get("amount") or 0) for r in fin), 2)
    equity = round(sum(float(_j(r.data, {}).get("amount") or 0) for r in fund
                       if (_j(r.data, {}).get("kind") or _j(r.data, {}).get("source", "")).lower()
                       in ("equity", "own", "self")), 2)
    debt = round(sum(float(_j(r.data, {}).get("amount") or 0) for r in fund
                     if (_j(r.data, {}).get("kind") or _j(r.data, {}).get("source", "")).lower()
                     not in ("equity", "own", "self")), 2)
    interest = round(debt * interest_rate_pct / 100 * years, 2) if years else 0.0
    return {"ok": True, "kind": "finance_sum", "cost_total": cost, "funding_total": round(equity + debt, 2),
            "equity": equity, "debt": debt,
            "equity_debt_ratio": (f"{equity / debt:.2f} : 1" if debt > 0 else "debt 0"),
            "interest_rate_pct": interest_rate_pct, "rate_source": rate_source, "years": years,
            "interest_outgo_simple": interest,
            "cost_rows": len(fin), "funding_rows": len(fund),
            "said": f"Summary: cost {_rs(cost)}, funding {_rs(equity + debt)} (equity {_rs(equity)} / debt {_rs(debt)}). The CFO decides the structure - Hoola only adds it up."}


def dekho(tenant: str, what: str, project: str = "", kind: str = "", parcel: str = "") -> dict:
    with session() as s:
        if what == "parcels":
            q = select(M.CLandParcel).where(M.CLandParcel.tenant_id == tenant)
            if project:
                q = q.where(M.CLandParcel.project == project)
            rows = s.scalars(q).all()
            return {"parcels": [{"id": r.id, "project": r.project, "survey_no": r.survey_no,
                                 "village": r.village, "area": r.area, "unit": r.area_unit,
                                 "source": r.area_source} for r in rows]}
        if what == "items":
            q = select(M.CLandItem).where(M.CLandItem.tenant_id == tenant)
            if project:
                q = q.where(M.CLandItem.project == project)
            if kind:
                q = q.where(M.CLandItem.kind == kind)
            rows = s.scalars(q).all()
            return {"items": [{"id": r.id, "project": r.project, "kind": r.kind, "name": r.name,
                               "data": _j(r.data, {}), "by": r.by, "source": r.source} for r in rows]}
    raise CstError("what is not valid - parcels | items.")
