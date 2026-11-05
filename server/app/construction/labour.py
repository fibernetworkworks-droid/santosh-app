"""#85 Labour Compliance Desk + #87 Wage & Payment Auditor + #90 BOCW Cess & TDS (v0.512.0, Wave 1).
All tier A: muster rolls, licence / registration renewals on a calendar, her wage rates with their
source, the wage audit (days x rate with the trail), and the DETERMINED cess / TDS arithmetic read from
the state pack (the pack refuses a stale pack instead of answering). Payment itself is always her tap -
Hoola records the wage_paid row AFTER she has paid, never moves money."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select

from ..db import session
from . import gates
from .common import (CstError, _LOCK, _date, _num, _rs, today)
from .models import CLabourLicence, CLabourMuster, CLabourWage
from .statepacks import PackError, tax_rows

KINDS = ("contract_labour", "bocw", "epf", "esic", "other")


def muster(tenant: str, site: str, day: str = "", contractor: str = "", trade: str = "", present=None,
           absent=None, ot_hours=None, wage_basis: str = "", note: str = "", conv: str = "") -> dict:
    if not str(site or "").strip():
        raise CstError("Site bataiye.")
    d = _date(day, today(tenant))
    p = int(present or 0)
    a = int(absent or 0)
    if p <= 0 and a <= 0:
        raise CstError("Hazari bataiye (kitne aaye, kitne gayab).")
    with _LOCK, session() as s:
        s.add(CLabourMuster(tenant_id=tenant, site=site[:160], day=d.isoformat(), contractor=contractor[:160],
                            trade=trade[:40], present=p, absent=a, ot_hours=_num(ot_hours),
                            wage_basis=(wage_basis or "day")[:20], note=note[:300]))
    say = f"Muster {d.strftime('%d %b')}: {site} - {trade or 'mazdoor'} aaye {p}, gayab {a}" + \
          (f", OT {float(ot_hours or 0):g} ghante" if ot_hours else "") + \
          (f" ({contractor})" if contractor else "") + "."
    from .common import publish
    publish(tenant, "const_labour", {"kind": "muster", "site": site, "day": d.isoformat(), "present": p}, conv)
    return {"day": d.isoformat(), "say": say}


def licence(tenant: str, kind: str, number: str = "", authority: str = "", holder: str = "", site: str = "",
            valid_from: str = "", valid_to: str = "", status: str = "", note: str = "") -> dict:
    k = (kind or "").strip().lower().replace(" ", "_")
    if k not in KINDS:
        raise CstError("kind: contract_labour | bocw | epf | esic | other")
    vt = _date(valid_to)
    if not vt:
        raise CstError("valid_to (expiry) bataiye - wahin calendar chalta hai.")
    with _LOCK, session() as s:
        s.add(CLabourLicence(tenant_id=tenant, kind=k, number=str(number)[:80], authority=authority[:160],
                             holder=holder[:160], site=site[:160], valid_from=(_date(valid_from) or "").isoformat() if valid_from else "",
                             valid_to=vt.isoformat(), status=(status or ("valid" if vt >= today(tenant) else "expired"))[:12],
                             note=note[:300]))
    return {"say": f"{k} licence ({number or 'number? '}) juda: {authority or '-'} se, valid till {vt.strftime('%d %b %Y')}."}


def wage_rate(tenant: str, trade: str, rate, basis: str = "day", site: str = "", wef: str = "",
              source: str = "", note: str = "") -> dict:
    """Her wage rate, with WHERE the number came from (her agreement / her word / a notified rate she typed).
    Hoola never supplies the minimum wage from memory - below check_wages explains why."""
    r = _num(rate)
    if not str(trade or "").strip() or r <= 0:
        raise CstError("Trade aur rate bataiye.")
    if (basis or "day") not in ("day", "hour", "piece"):
        raise CstError("basis: day | hour | piece")
    with _LOCK, session() as s:
        s.add(CLabourWage(tenant_id=tenant, trade=trade.strip().lower()[:60], site=site[:160], rate=r, basis=basis,
                          wef=(_date(wef) or today(tenant)).isoformat(), source=source[:200] or "uski baat (source likha nahi)",
                          note=note[:200]))
    return {"say": f"Wage rate: {trade} {_rs(r)}/{basis}" + (f" ({source})" if source else "") + "."}


def wage_audit(tenant: str, site: str, day: str = "", trade: str = "", workers=None, ot_hours=None, advances=None,
               deductions=None) -> dict:
    """#87 the working paper: workers x rate x (days implied 1) + OT - advances - deductions, with the trail.
    The PAYMENT stays her tap; Hoola records it in the muster's wage_paid only after she says it is paid."""
    w = int(workers or 0)
    if w <= 0:
        raise CstError("Kitne workers? Bataiye.")
    d = _date(day, today(tenant))
    with session() as s:
        rows = s.scalars(select(CLabourWage).where(CLabourWage.tenant_id == tenant,
                                                   CLabourWage.trade == (trade or "mazdoor").strip().lower())).all()
        if not rows:
            raise CstError(f"'{trade or 'mazdoor'}' ka wage rate set nahi - pehle wage_rate se rate aur uska SOURCE bataiye.")
        wr = rows[-1]
        base = round(wr.rate * w, 2)
        ot = round((wr.rate / 8) * 1.5 * _num(ot_hours), 2) if ot_hours else 0.0     # OT at 1.5x hourly, stated openly
        gross = round(base + ot, 2)
        adv = round(_num(advances), 2)
        ded = round(_num(deductions), 2)
        net = round(gross - adv - ded, 2)
        trail = {"rate_row_id": wr.id, "rate": wr.rate, "basis": wr.basis, "source": wr.source, "workers": w,
                 "ot_hours": _num(ot_hours), "ot_rule": "1.5 x (rate/8) per hour", "advances": adv, "deductions": ded}
    say = (f"Wage audit {d.strftime('%d %b')} ({site}): {w} x {_rs(wr.rate)}/{wr.basis} = {_rs(base)}"
           + (f" + OT {_rs(ot)}" if ot else "") + f" = {_rs(gross)}"
           + (f" - advance {_rs(adv)}" if adv else "") + (f" - katuayi {_rs(ded)}" if ded else "")
           + f" -> DENE HAI {_rs(net)}. Payment aapke tap se (paisa Hoola nahi bhejta). Rate ka source: {wr.source}.")
    return {"gross": gross, "net": net, "trail": trail, "say": say}


def wage_paid(tenant: str, site: str, day: str = "", trade: str = "", amount=None, workers=None, note: str = "") -> dict:
    """Record that the payment HAPPENED (after her transfer / cash) - the audit trail's closing line."""
    amt = _num(amount)
    if amt <= 0:
        raise CstError("Kitna diya? Rakam bataiye.")
    d = _date(day, today(tenant))
    with _LOCK, session() as s:
        s.add(CLabourMuster(tenant_id=tenant, site=site[:160], day=d.isoformat(), contractor="",
                            trade=(trade or "mazdoor")[:40], present=int(workers or 0), absent=0,
                            wage_paid=amt, wage_basis="day", note=("PAID. " + note)[:300]))
    return {"say": f"Record: {site} {d.strftime('%d %b')} - {_rs(amt)} wages diye gaye ({trade or 'mazdoor'}, {workers or '-'} workers). {note[:120]}"}


def cess_tds(tenant: str, base, state: str = "maharashtra", individual: bool = False, pan_ok: bool = True) -> dict:
    """#90 DETERMINED arithmetic only, from the state pack (which refuses when stale): BOCW cess on the
    construction cost, and Sec 393(1) (old 194C) TDS on a contract payment. Legal entitlement is NOT decided."""
    b = _num(base)
    if b <= 0:
        raise CstError("Base rakam (construction cost / contract payment) bataiye.")
    try:
        t = tax_rows(state)
    except PackError as ex:
        raise CstError(str(ex)) from None
    cess_v = float(t["bocw_cess"]["value"])
    cess = round(b * cess_v / 100, 2)
    ir = t["it_tds_194c"]["value"]
    rate = (ir["individual"] if individual else ir["other"]) if pan_ok else ir["no_pan"]
    tds = round(b * rate / 100, 2)
    say = (f"Hisaab (determined arithmetic, pack {t['bocw_cess']['checked_on']} ko checked): BOCW cess {cess_v:g}% = {_rs(cess)}"
           f"; TDS (Sec 393(1)) {rate:g}% = {_rs(tds)}. Base {_rs(b)}." 
           + " Cess jama aur return compliance CA / compliance officer dekhein - Hoola sirf hisaab banata hai.")
    return {"cess": cess, "tds": tds, "rows": t, "say": say}


def day(tenant: str) -> dict:
    """The compliance morning: licences expiring in 30 days, open wage audits (unpaid muster rows)."""
    t0 = today(tenant)
    from datetime import timedelta
    soon = t0 + timedelta(days=30)
    with session() as s:
        lic = [{"kind": r.kind, "number": r.number, "authority": r.authority, "holder": r.holder, "valid_to": r.valid_to,
                "status": r.status}
               for r in s.scalars(select(CLabourLicence).where(CLabourLicence.tenant_id == tenant)).all()
               if r.valid_to and r.valid_to <= soon.isoformat()]
        open_muster = [{"day": r.day, "site": r.site, "trade": r.trade, "present": r.present, "wage_paid": r.wage_paid}
                       for r in s.scalars(select(CLabourMuster).where(CLabourMuster.tenant_id == tenant,
                                                                      CLabourMuster.wage_paid == 0.0)).all()[-8:]]
    say = ""
    if lic:
        say += "Licence / registration: " + "; ".join(f"{x['kind']} {x['number']} ({x['holder'] or '-'}) valid till {x['valid_to']}" for x in lic[:4]) + "."
    if open_muster:
        say += f" {len(open_muster)} muster rows wages-abhi-unpaid (auditor se close karwaiye)."
    return {"licences": lic, "open_muster": open_muster, "say": say or "Labour desk: kuch expiry nahi, sab clear."}


def licences(tenant: str) -> list[dict]:
    with session() as s:
        return [{"kind": r.kind, "number": r.number, "authority": r.authority, "holder": r.holder, "site": r.site,
                 "valid_from": r.valid_from, "valid_to": r.valid_to, "status": r.status}
                for r in s.scalars(select(CLabourLicence).where(CLabourLicence.tenant_id == tenant)).all()]
