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
        raise CstError("Contract ka naam aur doosri party bataiye.")
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
                   + (f", notice window {int(_num(notice_days))} din (contract ke hisaab se)." if _num(notice_days) else
                      ". Notice window contract mein se padh ke batao - obligations ki alert usi se chalegi.")}


def oblig_add(tenant: str, contract_id: str, obligation: str, due_on: str, owner_side: bool = True,
              note: str = "") -> dict:
    """One obligation of one side with its due date - the chase rides this."""
    d = _date(due_on)
    if not str(obligation or "").strip() or d is None:
        raise CstError("Obligation aur due date dono chahiye.")
    with _LOCK, session() as s:
        c = s.get(CContract, contract_id)
        if not c or c.tenant_id != tenant:
            raise CstError("Contract nahi mila.")
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
            raise CstError("Obligation nahi mili.")
        x.status = "done"
        x.done_on = d.isoformat() if d else x.done_on
        what = x.obligation
    return {"say": f"'{what[:80]}' done mark. Record aapke word par."}


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
    say = (f"Contract chase: {len(late)} late, {len(soon)} agle {days} dinon mein."
           + (f" Late: {'; '.join(r['obligation'][:40] for r in late[:3])}" if late else "")
           + " Notice bhejna aapke aur advocate ke through.")
    return {"late": late, "soon": soon, "say": say}


def variation_draft(tenant: str, contract_id: str, desc: str, basis: str, qty=None, rate=None,
                    ref: str = "", conv: str = "") -> dict:
    """#45 variation paper DRAFT: what changed, the rate basis (SOR item / quoted / daywork), the
    money. Approval is the client's act - the paper starts as DRAFT and stays honest."""
    if not str(desc or "").strip():
        raise CstError("Kya badla, yeh bataiye.")
    if not str(basis or "").strip():
        raise CstError("Rate basis bataiye (SOR item / quoted rate / daywork) - bina basis ke variation "
                       "adhoora hai.")
    q, r = _num(qty), _num(rate)
    if q <= 0 or r <= 0:
        raise CstError("Qty aur rate dono chahiye (> 0).")
    with _LOCK, session() as s:
        c = s.get(CContract, contract_id)
        if not c or c.tenant_id != tenant:
            raise CstError("Contract nahi mila.")
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
                   "Approve client karega (main kabhi nahi) - approval aaye to unka naam ke saath record hota hai."}


def variation_mark(tenant: str, variation_id: str, status: str, approved_by: str = "") -> dict:
    """Record the paper's walk: draft -> submitted -> approved/rejected. 'approved' needs the
    CLIENT's name as SHE reports it - Hoola's own word approves nothing."""
    if status not in ("draft", "submitted", "approved", "rejected"):
        raise CstError("status: draft | submitted | approved | rejected")
    who = str(approved_by or "").strip()
    if status == "approved" and not who:
        raise CstError("Kaun approve hua? Client ke Naam ke saath record hota hai (main approval ka "
                       "faalsa nahi karta - sirf record rakhta hoon).")
    with _LOCK, session() as s:
        x = s.get(CContrVariation, variation_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Variation nahi mili.")
        x.status = status
        if status == "approved":
            x.approved_by = who[:120]
        desc, amt = x.desc, x.amount
    return {"say": f"Variation '{desc[:60]}' ({_rs(amt)}): status -> {status}"
                   + (f", approved by {who} (aapke bataye se record)." if status == "approved" else "") + "."}


def claim_paper(tenant: str, contract_id: str, cause: str, event_on: str, noticed_on: str = "",
                notice_days=None, matrix=None, conv: str = "") -> dict:
    """#46 the working paper: her entitlement matrix rows + the notice-compliance arithmetic.
    The conclusion (entitled ya nahi) counsel ka hai - yeh paper wahi rok deta hai jahan kaayda
    shuru hota hai."""
    if not str(cause or "").strip():
        raise CstError("Claim ki wajah bataiye (delay, extra work, escalation...).")
    ev = _date(event_on)
    if ev is None:
        raise CstError("Event ki tareekh bataiye (jab hua).")
    nd = int(_num(notice_days))
    if nd <= 0:
        with session() as s:
            c = s.get(CContract, contract_id)
            if not c or c.tenant_id != tenant:
                raise CstError("Contract nahi mila.")
            nd = c.notice_days
    no = _date(noticed_on)
    rows = [r for r in (matrix or []) if isinstance(r, dict) and str(r.get("clause", "")).strip()]
    if not rows:
        raise CstError("Entitlement matrix bhejo [{event, clause, effect, evidence}] - clause ke bina "
                       "row nahi rehti (yahi paper ko working paper banata hai).")
    compliance = None
    if no is not None:
        taken = (no - ev).days
        compliance = {"event_on": ev.isoformat(), "noticed_on": no.isoformat(), "days_taken": taken,
                      "window_days": nd, "in_time": taken <= nd if nd > 0 else None,
                      "note": ("notice window ke andar" if taken <= nd else f"notice {taken - nd} din LATE")
                      if nd > 0 else "contract mein notice window nahi likha - advocate dekhenge"}
    with _LOCK, session() as s:
        c = s.get(CContract, contract_id)
        if not c or c.tenant_id != tenant:
            raise CstError("Contract nahi mila.")
        x = CContrClaim(tenant_id=tenant, contract_id=contract_id[:40], cause=cause.strip()[:400],
                        event_on=ev.isoformat(), noticed_on=no.isoformat() if no else "", notice_days=nd,
                        matrix=_dump(rows), status="draft")
        s.add(x)
        s.flush()
        kid, cname = x.id, c.name
    from .common import publish
    publish(tenant, "const_contracts", {"kind": "claim_paper", "contract": cname}, conv)
    say = (f"Claims working paper ({cname}): {cause[:70]}, {len(rows)} matrix rows (sab clause ke saath). ")
    say += (f"Notice compliance: {compliance['note']}. " if compliance
            else "Notice kab diya - yeh batao, compliance ka hisaab banega. ")
    say += "Entitlement ka nishkarsh advocate/counsel dega - yeh paper wahi karta hai jo kaayda kehta hai."
    return {"claim_id": kid, "notice_compliance": compliance, "matrix_rows": len(rows), "say": say}


def day(tenant: str) -> dict:
    """The contracts morning: open contracts, variations in play, claims in draft."""
    with session() as s:
        cs = s.scalars(select(CContract).where(CContract.tenant_id == tenant, CContract.status == "open")).all()
        vs = s.scalars(select(CContrVariation).where(CContrVariation.tenant_id == tenant,
                                                     CContrVariation.status.in_(("draft", "submitted")))).all()
        ks = s.scalars(select(CContrClaim).where(CContrClaim.tenant_id == tenant, CContrClaim.status == "draft")).all()
    say = (f"Contracts: {len(cs)} open, {len(vs)} variation chal rahi, {len(ks)} claim working-paper draft.")
    return {"open_contracts": len(cs), "variations_open": len(vs), "claims_draft": len(ks), "say": say}
