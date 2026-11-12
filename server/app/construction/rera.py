"""#35 RERA Compliance Manager + #93 Escrow / RERA Account Reconciler (v0.531.0, Wave 2 C9).

The registration data pack, the quarterly update DRAFTS, the form data packs (Form 3/4/5 or any
numbered form the portal names) and the 70% escrow reconciliation. THE LAW OF THIS DESK, said on
every output:

- the completion percentage is the PROMOTER's own number - Hoola records it, never computes it
  (tier C: "certify RERA percentage completion");
- a withdrawal from the escrow account saves ONLY with the certificate reference of the engineer /
  architect / CA (tier C: "certify RERA escrow withdrawal") - no certificate, no row;
- every form pack names its professional (`prepared_for`) and the signature line stays empty;
- the determined rules come from the state pack (rera_escrow_pct 70%, the CA audit window) - a stale
  pack refuses to reconcile, a missing pack says so. MahaRERA is the state authority for this pack.
"""
from __future__ import annotations

from sqlalchemy import select

from ..db import session
from .common import (CstError, _LOCK, _date, _dump, _j, _num, _rs, today, add_months)
from .models import CreraEscrow, CreraForm, CreraProject, CreraUpdate


def project_reg(tenant: str, name: str, maha_rera: str = "", promoter: str = "", start_on: str = "",
                complete_on: str = "", sanctioned_on: str = "", escrow_acct: str = "", conv: str = "") -> dict:
    """The project data pack: her facts, exactly as registered - Hoola keeps them, never amends."""
    if not str(name or "").strip():
        raise CstError("Give the project's name.")
    with _LOCK, session() as s:
        x = CreraProject(tenant_id=tenant, name=name.strip()[:160], maha_rera=maha_rera.strip()[:60],
                         promoter=promoter.strip()[:160], start_on=(_date(start_on) or "").isoformat() if start_on else "",
                         complete_on=(_date(complete_on) or "").isoformat() if complete_on else "",
                         sanctioned_on=(_date(sanctioned_on) or "").isoformat() if sanctioned_on else "",
                         escrow_acct=escrow_acct.strip()[:80])
        s.add(x)
        s.flush()
        pid = x.id
    from .common import publish
    publish(tenant, "const_rera", {"kind": "project_reg", "name": name}, conv)
    return {"rera_project_id": pid,
            "say": f"RERA project pack: {name}" + (f" (MahaRERA {maha_rera})" if maha_rera else "")
                   + ". Registration, quarterly updates and forms - the declarations are the promoter's, assembling the data is mine."}


def update_draft(tenant: str, project_id: str, quarter: str, pct_complete=None, units_booked=None,
                 units_delivered=None, complaints=None, note: str = "", conv: str = "") -> dict:
    """Quarterly update DRAFT: quarter, the % as the PROMOTER says it, units, complaints."""
    if not str(quarter or "").strip():
        raise CstError("Give the quarter (for example '2026-Q4').")
    with _LOCK, session() as s:
        p = s.get(CreraProject, project_id)
        if not p or p.tenant_id != tenant:
            raise CstError("RERA project not found.")
        x = CreraUpdate(tenant_id=tenant, project_id=project_id[:40], quarter=quarter.strip()[:20],
                        pct_complete=_num(pct_complete), units_booked=int(_num(units_booked)),
                        units_delivered=int(_num(units_delivered)), complaints=int(_num(complaints)),
                        prepared_on=today(tenant).isoformat(), status="draft", note=note[:300])
        s.add(x)
        s.flush()
        uid = x.id
        pname = p.name
    from .common import publish
    publish(tenant, "const_rera", {"kind": "update_draft", "project": pname, "quarter": quarter}, conv)
    return {"update_id": uid,
            "say": f"Quarterly update DRAFT: {pname} - {quarter}, completion {pct_complete or 0:g}% (the number you gave; "
                   "I never derive it myself - certifying it is the promoter's declaration), "
                   f"booked {int(_num(units_booked))}, delivered {int(_num(units_delivered))}. The promoter does the filing on the portal."}


def form_pack(tenant: str, project_id: str, form_no: str, purpose: str, period: str = "", data=None,
              prepared_for: str = "", note: str = "") -> dict:
    """Form data pack: rows [{item, value, source}] assembled; `prepared_for` (the named CA /
    architect / engineer) is REQUIRED - bina naam ke professional ke form pack adhoora hai."""
    if not str(form_no or "").strip():
        raise CstError("Give the form number (for example 'Form 3' - whatever the portal says).")
    who = str(prepared_for or "").strip()
    if not who:
        raise CstError("Which professional is it for? (the CA's / architect's / engineer's name) - every form pack "
                       "goes in the name of its professional, and the sign line stays empty.")
    rows = []
    for r in (data or []):
        if isinstance(r, dict) and str(r.get("item", "")).strip():
            if not str(r.get("source", "")).strip():
                raise CstError(f"'{str(r.get('item'))[:40]}' needs a source - every value in a form pack carries its own "
                               "source (measurement, site diary, sanctioned plan...).")
            rows.append({"item": str(r.get("item"))[:160], "value": str(r.get("value", ""))[:200],
                         "source": str(r.get("source"))[:160]})
    if not rows:
        raise CstError("Send the form's data [{item, value, source}] - a value without a source is dropped.")
    with _LOCK, session() as s:
        p = s.get(CreraProject, project_id)
        if not p or p.tenant_id != tenant:
            raise CstError("RERA project not found.")
        x = CreraForm(tenant_id=tenant, project_id=project_id[:40], form_no=form_no.strip()[:30],
                      purpose=purpose.strip()[:200], period=period.strip()[:40], data=_dump(rows),
                      prepared_for=who[:120], status="draft", note=note[:300])
        s.add(x)
        s.flush()
        fid, pname = x.id, p.name
    return {"form_id": fid, "rows": len(rows),
            "say": f"Form pack {form_no} DRAFT ({pname}): {len(rows)} rows, prepared for {who}. "
                   "The declaration is the professional's - the signature space is empty, they fill it in."}


def escrow_in(tenant: str, project_id: str, amount, day: str = "", ref: str = "", note: str = "") -> dict:
    """A receipt into the project accounts - the 70% reserve watch starts here."""
    amt = _num(amount)
    if amt <= 0:
        raise CstError("Give the receipt amount.")
    d = _date(day, today(tenant))
    with _LOCK, session() as s:
        p = s.get(CreraProject, project_id)
        if not p or p.tenant_id != tenant:
            raise CstError("RERA project not found.")
        x = CreraEscrow(tenant_id=tenant, project_id=project_id[:40], kind="receipt", amount=amt,
                        day=d.isoformat(), ref=ref[:120], note=note[:200])
        s.add(x)
        s.flush()
        eid, pname = x.id, p.name
    return {"entry_id": eid, "say": f"Receipt {_rs(amt)} ({pname}) recorded in the project accounts. "
                                    "See the 70% designated account position with reconcile."}


def escrow_withdraw(tenant: str, project_id: str, amount, day: str = "", certificate_ref: str = "",
                    ref: str = "", note: str = "") -> dict:
    """A withdrawal out of the designated account: NO certificate reference, NO row - the law of
    this desk (the certificate is the engineer's / architect's / CA's, tier C)."""
    amt = _num(amount)
    if amt <= 0:
        raise CstError("Give the withdrawal amount.")
    cert = str(certificate_ref or "").strip()
    if not cert:
        raise CstError("A withdrawal needs the engineer's / architect's / CA's certificate reference - "
                       "without a certificate, money out of the designated account is not recorded. Wait for the certificate.")
    d = _date(day, today(tenant))
    with _LOCK, session() as s:
        p = s.get(CreraProject, project_id)
        if not p or p.tenant_id != tenant:
            raise CstError("RERA project not found.")
        x = CreraEscrow(tenant_id=tenant, project_id=project_id[:40], kind="withdrawal", amount=amt,
                        day=d.isoformat(), certificate_ref=cert[:120], ref=ref[:120], note=note[:200])
        s.add(x)
        s.flush()
        eid, pname = x.id, p.name
    return {"entry_id": eid, "say": f"Withdrawal {_rs(amt)} ({pname}) certificate {cert} recorded. "
                                    "The certificate belongs to the professional - I only keep the accounts."}


def reconcile(tenant: str, project_id: str) -> dict:
    """#93 the reconciliation: receipts vs withdrawals vs the 70% reserve (state-pack row, cited;
    stale pack refuses). Plus the CA-audit due date (RERA s.4(2)(l)(D): within six months of each
    financial year's end)."""
    from . import statepacks as SP
    with session() as s:
        p = s.get(CreraProject, project_id)
        if not p or p.tenant_id != tenant:
            raise CstError("RERA project not found.")
        rows = s.scalars(select(CreraEscrow).where(CreraEscrow.tenant_id == tenant,
                                                   CreraEscrow.project_id == project_id)).all()
        updates = s.scalars(select(CreraUpdate).where(CreraUpdate.tenant_id == tenant,
                                                      CreraUpdate.project_id == project_id)).all()
    receipts = round(sum(r.amount for r in rows if r.kind == "receipt"), 2)
    withdrawn = round(sum(r.amount for r in rows if r.kind == "withdrawal"), 2)
    no_cert = [r for r in rows if r.kind == "withdrawal" and not r.certificate_ref]
    try:
        pack = SP.load("maharashtra")
        if SP.stale(pack):
            raise CstError("The Maharashtra rule pack is out of date (refresh_by " + str(pack.get("refresh_by"))
                           + ") - refresh the pack first, then reconcile.")
        pct = float(SP.value(pack, "rera_escrow_pct", 70.0))
        audit_m = int(float(SP.value(pack, "rera_ca_audit_months", 6)))
        src = SP.row(pack, "rera_escrow_pct") or {}
    except CstError:
        raise
    except Exception as ex:  # pack file unreadable - say it, never guess the %
        raise CstError(f"Could not open the rule pack: {ex}") from None
    reserve = round(receipts * pct / 100.0, 2)
    short = round(reserve - withdrawn, 2)
    d0 = today(tenant)
    fy_end = f"{d0.year if d0.month <= 3 else d0.year + 1}-03-31"
    audit_due = add_months(_date(fy_end), audit_m)
    upd = sorted(updates, key=lambda r: r.quarter)[-1] if updates else None
    say = (f"Escrow reconcile ({p.name}): receipts {_rs(receipts)}, withdrawals {_rs(withdrawn)}, "
           f"70% reserve {_rs(reserve)} (RERA s.4(2)(l)(D), pack {src.get('checked_on', '?')}). "
           + (f"Reserve has {_rs(short)} left. " if short > 0 else
              (f"Withdrawn {_rs(-short)} above the reserve - check the certificate rows. " if short < 0 else "Reserve is fine. "))
           + f"CA audit due {audit_due.isoformat()} (FY end + {audit_m} months)."
           + (" The QUARTERLY UPDATE is also pending." if upd is None or upd.status == "draft" else ""))
    return {"receipts": receipts, "withdrawn": withdrawn, "reserve_pct": pct, "reserve": reserve,
            "headroom": short, "audit_due": audit_due.isoformat(),
            "withdrawals_without_certificate": len(no_cert),
            "source": {"clause": src.get("clause"), "source": src.get("source"),
                       "checked_on": src.get("checked_on")}, "say": say}


def day(tenant: str) -> dict:
    """The RERA morning: projects, draft updates pending, withdrawals without certificates."""
    with session() as s:
        projects = s.scalars(select(CreraProject).where(CreraProject.tenant_id == tenant)).all()
        drafts = s.scalars(select(CreraUpdate).where(CreraUpdate.tenant_id == tenant, CreraUpdate.status == "draft")).all()
        rows = s.scalars(select(CreraEscrow).where(CreraEscrow.tenant_id == tenant, CreraEscrow.kind == "withdrawal")).all()
    no_cert = [r for r in rows if not r.certificate_ref]
    say = (f"RERA desk: {len(projects)} project, {len(drafts)} quarterly update DRAFT pending"
           + (f", {len(no_cert)} withdrawals without a certificate" if no_cert else "") + ".")
    return {"projects": len(projects), "draft_updates": len(drafts), "uncertified_withdrawals": len(no_cert), "say": say}
