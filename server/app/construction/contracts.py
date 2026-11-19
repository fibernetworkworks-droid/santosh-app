"""#44 Contracts Administrator + #45 Variation & Change-order Assistant + #46 Claims Assistant +
#51 Insurance & Bonds Coordinator (v0.531.0, Wave 2 C10).

The register, the obligations with their notice windows, the variation papers and the claims
working papers. The edges, said on every output:

- variation approval is the CLIENT's act (tier C: "approve a change order") - `approved_by` records
  THEIR name when she reports it; Hoola never marks a change approved on its own word;
- a claim's entitlement is counsel's conclusion (tier C: "decide delay entitlement") - the working
  paper carries HER entitlement matrix (event -> clause -> effect -> evidence) and the
  notice-compliance ARITHMETIC (was the notice in the contract's window), nothing more;
- notices are drafted, never issued (tier C: "issue a notice").
"""
from __future__ import annotations

from sqlalchemy import select

from ..db import session
from .common import (CstError, _LOCK, _date, _dump, _j, _num, _rs, today)
from .models import CContract, CContrClaim, CContrOblig, CContrVariation


def contract_new(tenant: str, name: str, party: str, role: str = "contractor", value=None,
                 signed_on: str = "", start_on: str = "", end_on: str = "", notice_days=None,
                 ref: str = "", conv: str = "") -> dict:
    """One contract into the register: the paper's facts, the notice window AS THE CONTRACT SAYS."""
    if not str(name or "").strip() or not str(party or "").strip():
        raise CstError("Give the contract name and the other party.")
    if role not in ("employer", "contractor", "sub-contractor"):
        raise CstError("role: employer | contractor | sub-contractor")
    with _LOCK, session() as s:
        x = CContract(tenant_id=tenant, name=name.strip()[:200], party=party.strip()[:160], role=role,
                      value=_num(value), signed_on=(_date(signed_on) or "").isoformat() if signed_on else "",
                      start_on=(_date(start_on) or "").isoformat() if start_on else "",
                      end_on=(_date(end_on) or "").isoformat() if end_on else "",
                      notice_days=int(_num(notice_days)), ref=ref[:120])
        s.add(x)
        s.flush()
        cid = x.id
    from .common import publish
    publish(tenant, "const_contracts", {"kind": "contract_new", "name": name}, conv)
    return {"contract_id": cid,
            "say": f"Contract register: {name} - {party} ({role}, {_rs(value)})"
                   + (f", notice window {int(_num(notice_days))} days (per the contract)." if _num(notice_days) else
                      ". Read the notice window from the contract and tell me - obligation alerts run on it.")}


def oblig_add(tenant: str, contract_id: str, obligation: str, due_on: str, owner_side: bool = True,
              note: str = "") -> dict:
    """One obligation of one side with its due date - the chase rides this."""
    d = _date(due_on)
    if not str(obligation or "").strip() or d is None:
        raise CstError("Both the obligation and the due date are needed.")
    with _LOCK, session() as s:
        c = s.get(CContract, contract_id)
        if not c or c.tenant_id != tenant:
            raise CstError("Contract not found.")
        x = CContrOblig(tenant_id=tenant, contract_id=contract_id[:40], obligation=obligation.strip()[:400],
                        due_on=d.isoformat(), owner_side=bool(owner_side), note=note[:200])
        s.add(x)
        s.flush()
        oid, cname = x.id, c.name
    return {"oblig_id": oid, "say": f"Obligation ({cname}, {'hamara' if owner_side else 'unka'}): "
                                    f"'{obligation[:80]}' due {d.strftime('%d %b')}."}


def oblig_done(tenant: str, oblig_id: str, on: str = "") -> dict:
    d = _date(on, today(tenant))
    with _LOCK, session() as s:
        x = s.get(CContrOblig, oblig_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Obligation not found.")
        x.status = "done"
        x.done_on = d.isoformat() if d else x.done_on
        what = x.obligation
    return {"say": f"'{what[:80]}' marked done. Recorded on your word."}


def oblig_due(tenant: str, days: int = 7) -> dict:
    """The chase: open obligations due in the window (and the already-late), both sides, honest."""
    d0 = today(tenant)
    with session() as s:
        rows = s.scalars(select(CContrOblig).where(CContrOblig.tenant_id == tenant, CContrOblig.status == "open")).all()
        cs = {c.id: c for c in s.scalars(select(CContract).where(CContract.tenant_id == tenant)).all()}
    late, soon = [], []
    for r in rows:
        dd = _date(r.due_on)
        if dd is None:
            continue
        row = {"obligation": r.obligation[:120], "due_on": r.due_on,
               "side": "hamara" if r.owner_side else "unka",
               "contract": (cs.get(r.contract_id).name if cs.get(r.contract_id) else "?")}
        delta = (dd - d0).days
        if delta < 0:
            row["late_by"] = -delta
            late.append(row)
        elif delta <= max(0, int(days)):
            row["in_days"] = delta
            soon.append(row)
    late.sort(key=lambda x: -x["late_by"])
    soon.sort(key=lambda x: x["in_days"])
    say = (f"Contract chase: {len(late)} late, {len(soon)} due in the next {days} days."
           + (f" Late: {'; '.join(r['obligation'][:40] for r in late[:3])}" if late else "")
           + " Notices are sent through you and your advocate.")
    return {"late": late, "soon": soon, "say": say}


def variation_draft(tenant: str, contract_id: str, desc: str, basis: str, qty=None, rate=None,
                    ref: str = "", conv: str = "") -> dict:
    """#45 variation paper DRAFT: what changed, the rate basis (SOR item / quoted / daywork), the
    money. Approval is the client's act - the paper starts as DRAFT and stays honest."""
    if not str(desc or "").strip():
        raise CstError("Tell me what changed.")
    if not str(basis or "").strip():
        raise CstError("Give the rate basis (SOR item / quoted rate / daywork) - without a basis the variation "
                       "is incomplete.")
    q, r = _num(qty), _num(rate)
    if q <= 0 or r <= 0:
        raise CstError("Both qty and rate are needed (> 0).")
    with _LOCK, session() as s:
        c = s.get(CContract, contract_id)
        if not c or c.tenant_id != tenant:
            raise CstError("Contract not found.")
        x = CContrVariation(tenant_id=tenant, contract_id=contract_id[:40], desc=desc.strip()[:500],
                            basis=basis.strip()[:200], qty=q, rate=r, amount=round(q * r, 2),
                            raised_on=today(tenant).isoformat(), status="draft", ref=ref[:120])
        s.add(x)
        s.flush()
        vid, cname = x.id, c.name
    from .common import publish
    publish(tenant, "const_contracts", {"kind": "variation_draft", "contract": cname, "amount": round(q * r, 2)}, conv)
    return {"variation_id": vid, "amount": round(q * r, 2),
            "say": f"Variation DRAFT ({cname}): {desc[:80]} - {q:g} x {_rs(r)} = {_rs(q * r)}, basis: {basis[:60]}. "
                   "The client approves it (never me) - when the approval comes it is recorded with their name."}


def variation_mark(tenant: str, variation_id: str, status: str, approved_by: str = "") -> dict:
    """Record the paper's walk: draft -> submitted -> approved/rejected. 'approved' needs the
    CLIENT's name as SHE reports it - Hoola's own word approves nothing."""
    if status not in ("draft", "submitted", "approved", "rejected"):
        raise CstError("status: draft | submitted | approved | rejected")
    who = str(approved_by or "").strip()
    if status == "approved" and not who:
        raise CstError("Who approved it? It is recorded with the client's name (I do not decide the "
                       "approval - I only keep the record).")
    with _LOCK, session() as s:
        x = s.get(CContrVariation, variation_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Variation not found.")
        x.status = status
        if status == "approved":
            x.approved_by = who[:120]
        desc, amt = x.desc, x.amount
    return {"say": f"Variation '{desc[:60]}' ({_rs(amt)}): status -> {status}"
                   + (f", approved by {who} (recorded as you told me)." if status == "approved" else "") + "."}


def claim_paper(tenant: str, contract_id: str, cause: str, event_on: str, noticed_on: str = "",
                notice_days=None, matrix=None, conv: str = "") -> dict:
    """#46 the working paper: her entitlement matrix rows + the notice-compliance arithmetic.
    The conclusion (entitled ya nahi) counsel ka hai - yeh paper wahi rok deta hai jahan kaayda
    shuru hota hai."""
    if not str(cause or "").strip():
        raise CstError("Give the reason for the claim (delay, extra work, escalation...).")
    ev = _date(event_on)
    if ev is None:
        raise CstError("Give the date of the event (when it happened).")
    nd = int(_num(notice_days))
    if nd <= 0:
        with session() as s:
            c = s.get(CContract, contract_id)
            if not c or c.tenant_id != tenant:
                raise CstError("Contract not found.")
            nd = c.notice_days
    no = _date(noticed_on)
    rows = [r for r in (matrix or []) if isinstance(r, dict) and str(r.get("clause", "")).strip()]
    if not rows:
        raise CstError("Send the entitlement matrix [{event, clause, effect, evidence}] - a row without a clause "
                       "is dropped (that is what makes the paper a working paper).")
    compliance = None
    if no is not None:
        taken = (no - ev).days
        compliance = {"event_on": ev.isoformat(), "noticed_on": no.isoformat(), "days_taken": taken,
                      "window_days": nd, "in_time": taken <= nd if nd > 0 else None,
                      "note": ("within the notice window" if taken <= nd else f"notice {taken - nd} days LATE")
                      if nd > 0 else "no notice window is written in the contract - the advocate will look at it"}
    with _LOCK, session() as s:
        c = s.get(CContract, contract_id)
        if not c or c.tenant_id != tenant:
            raise CstError("Contract not found.")
        x = CContrClaim(tenant_id=tenant, contract_id=contract_id[:40], cause=cause.strip()[:400],
                        event_on=ev.isoformat(), noticed_on=no.isoformat() if no else "", notice_days=nd,
                        matrix=_dump(rows), status="draft")
        s.add(x)
        s.flush()
        kid, cname = x.id, c.name
    from .common import publish
    publish(tenant, "const_contracts", {"kind": "claim_paper", "contract": cname}, conv)
    say = (f"Claims working paper ({cname}): {cause[:70]}, {len(rows)} matrix rows (all with a clause). ")
    say += (f"Notice compliance: {compliance['note']}. " if compliance
            else "Tell me when the notice was given and the compliance arithmetic will be made. ")
    say += "The conclusion on entitlement is the advocate's/counsel's - this paper does only what the rule says."
    return {"claim_id": kid, "notice_compliance": compliance, "matrix_rows": len(rows), "say": say}


def day(tenant: str) -> dict:
    """The contracts morning: open contracts, variations in play, claims in draft."""
    with session() as s:
        cs = s.scalars(select(CContract).where(CContract.tenant_id == tenant, CContract.status == "open")).all()
        vs = s.scalars(select(CContrVariation).where(CContrVariation.tenant_id == tenant,
                                                     CContrVariation.status.in_(("draft", "submitted")))).all()
        ks = s.scalars(select(CContrClaim).where(CContrClaim.tenant_id == tenant, CContrClaim.status == "draft")).all()
    say = (f"Contracts: {len(cs)} open, {len(vs)} variations in progress, {len(ks)} claim working-paper draft.")
    return {"open_contracts": len(cs), "variations_open": len(vs), "claims_draft": len(ks), "say": say}


# ---------------------------------------------------------------- Wave 4: #48 LD calculator, #50 arbitration bundle
def ld_calc(tenant: str, project: str, contract_ref: str, delay_days: int, ld_pct_per_week: float,
            contract_value: float, cap_pct: float, sources: str = "") -> dict:
    """#48: LD = value x pct/week x weeks, capped at cap_pct - ALL four numbers FED from HER
    contract (sources required). The DEDUCTION decision stays gated (tier C: 'issue an LD
    deduction')."""
    from . import models as WM
    if delay_days <= 0 or contract_value <= 0:
        raise CstError("Delay days (more than 0) and the contract value are needed.")
    if not sources:
        raise CstError("Give the source of the LD rate + cap (contract clause no) - no LD without a clause.")
    weeks = round(delay_days / 7, 2)
    raw = contract_value * ld_pct_per_week / 100 * weeks
    cap = contract_value * cap_pct / 100
    applied = min(raw, cap)
    with session() as s:
        s.add(WM.Cw4ExtItem(tenant_id=tenant, project=project, kind="ld", ref=contract_ref[:120],
                            data=_dump({"delay_days": delay_days, "weeks": weeks,
                                        "ld_pct_per_week": ld_pct_per_week, "raw": round(raw, 2),
                                        "cap_pct": cap_pct, "cap": round(cap, 2),
                                        "applied": round(applied, 2)}), source=sources))
    return {"ok": True, "ref": contract_ref, "delay_days": delay_days, "weeks": weeks,
            "ld_pct_per_week": ld_pct_per_week, "ld_raw": round(raw, 2),
            "cap_pct": cap_pct, "cap_amount": round(cap, 2), "ld_applied": round(applied, 2),
            "capped": raw > cap, "sources": sources,
            "said": ("Arithmetic complete - DEDUCTING LD is entirely in your/your advocate's hands (Hoola cannot "
                     "deduct it, tier C). Clause: " + sources[:60])}


def arb_bundle_add(tenant: str, project: str, claim: str, rows: list, by: str = "",
                   conv: str = "") -> dict:
    """#50: arbitration bundle index - rows [date, event/evidence, exhibit]. The bundle is FOR the
    counsel; the argument is the counsel's."""
    from . import models as WM
    from .common import publish as pub
    if not claim:
        raise CstError("Give the claim's name/ref.")
    if not rows:
        raise CstError("Evidence rows are needed [date, event/evidence, exhibit].")
    if not by:
        raise CstError("Each evidence entry needs the NAME of the person keeping it.")
    made = 0
    with session() as s:
        for r in rows:
            if not isinstance(r, (list, tuple)) or len(r) < 2:
                continue
            s.add(WM.Cw4ExtItem(tenant_id=tenant, project=project, kind="arb", ref=claim[:120],
                                name="evidence",
                                data=_dump({"date": str(r[0])[:10], "evidence": str(r[1])[:200],
                                            "exhibit": str(r[2])[:40] if len(r) > 2 else ""}),
                                by=by))
            made += 1
    pub(tenant, "const_contracts", {"kind": "arb_bundle", "project": project, "claim": claim}, conv)
    return {"ok": True, "claim": claim, "rows": made, "by": by,
            "said": f"Bundle index '{claim}': {made} evidence row(s) - the case goes only to counsel."}


def arb_bundle(tenant: str, project: str, claim: str) -> dict:
    from . import models as WM
    with session() as s:
        rows = s.scalars(select(WM.Cw4ExtItem).where(WM.Cw4ExtItem.tenant_id == tenant,
                                                     WM.Cw4ExtItem.project == project,
                                                     WM.Cw4ExtItem.kind == "arb",
                                                     WM.Cw4ExtItem.ref == claim)).all()
    return {"claim": claim, "rows": [{"date": _j(r.data, {}).get("date"),
                                      "evidence": _j(r.data, {}).get("evidence"),
                                      "exhibit": _j(r.data, {}).get("exhibit"), "by": r.by}
                                     for r in rows]}
