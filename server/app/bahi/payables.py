"""v0.847 BAHI A8 - payables, receivables, TDS.

One party master; ageing from the register (a document is settled once a bank line she confirmed is matched to it); the MSME 15 / 45-day alarm and
the 180-day Rule 37 watch; collection reminders DRAFTED for her to send (a party she stopped is skipped); the TDS worksheet from the rules file
(rate, limits, no-PAN rate, the 7th), a register of what she deducted and deposited, the quarter's Form 140 data and a 26AS match.
Hoola never pays, never deducts for her, never files a TDS return (there is no public deductor API) and never uploads bank details anywhere.
NOT VERIFIED: the section 393 item numbers (each row shows the old section); how the interest on delayed MSME payments is computed (shown as a warning only).
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import quote

from sqlalchemy import select

from ..accounts import decrypt, encrypt
from ..db import session
from . import register as REG
from . import rules as RU
from .models import AccBankLine, AccDoc, AccParty, AccTds, ensure_tables


class PayError(Exception):
    pass


def _today() -> date:
    return date.today()


# ------------------------------------------------------------------ party master
def _mask(acct: str) -> str:
    a = re.sub(r"\D", "", acct or "")
    return ("x" * max(0, len(a) - 4) + a[-4:]) if a else ""


def party_view(p: AccParty) -> dict[str, Any]:
    return {"id": p.id, "name": p.name, "gstin": p.gstin, "pan": p.pan, "pan_ok": p.pan_ok, "constitution": p.constitution, "udyam": p.udyam,
            "msme_class": p.msme_class, "agreed_days": p.agreed_days, "no_reminders": p.no_reminders, "bank": p.bank_mask,
            "bank_changes": len(json.loads(p.bank_history or "[]"))}                    # never the account number


def party_save(tenant: str, f: dict[str, Any], party_id: str = "") -> dict[str, Any]:
    from ..appmaker.gst import valid_gstin
    ensure_tables()
    name = str(f.get("name") or "").strip()[:160]
    gstin = str(f.get("gstin") or "").strip().upper()
    pan = str(f.get("pan") or "").strip().upper() or (gstin[2:12] if len(gstin) == 15 else "")
    if gstin and not valid_gstin(gstin):
        raise PayError("That GSTIN fails the check digit.")
    if pan and not re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", pan):
        raise PayError("A PAN is 5 letters, 4 digits, 1 letter.")
    if f.get("msme_class") not in (None, "", "micro", "small", "medium"):
        raise PayError("MSME class: micro, small or medium.")
    with session() as s:
        p = s.get(AccParty, party_id) if party_id else None
        if p is not None and p.tenant_id != tenant:
            raise PayError("That party was not found.")
        if p is None and gstin:
            p = s.scalars(select(AccParty).where(AccParty.tenant_id == tenant, AccParty.gstin == gstin)).first()
        if p is None and name:                                       # the same name is the same party - never a duplicate
            p = next((x for x in s.scalars(select(AccParty).where(AccParty.tenant_id == tenant)).all() if x.name.strip().lower() == name.lower()), None)
        if p is None:
            if not name:
                raise PayError("Give the party a name.")
            p = AccParty(tenant_id=tenant)
            s.add(p)
        if name:
            p.name = name
        for k in ("gstin", "pan"):
            v = gstin if k == "gstin" else pan
            if v:
                setattr(p, k, v)
        for k in ("udyam", "msme_class", "constitution"):
            if f.get(k) is not None:
                setattr(p, k, str(f[k]).strip()[:30])
        for k in ("pan_ok", "no_reminders"):
            if f.get(k) is not None:
                setattr(p, k, bool(f[k]))
        if f.get("agreed_days") not in (None, ""):
            p.agreed_days = max(0, min(int(f["agreed_days"]), 365))
        if f.get("bank_account"):
            new = json.dumps({"acct": re.sub(r"\D", "", str(f["bank_account"])), "ifsc": str(f.get("bank_ifsc") or "").strip().upper()})
            if p.bank_enc and decrypt(p.bank_enc) != new:
                hist = json.loads(p.bank_history or "[]")
                hist.append({"on": _today().isoformat(), "was": p.bank_mask, "now": _mask(str(f["bank_account"]))})
                p.bank_history = json.dumps(hist[-20:])
                REG._event(s, tenant, "party_bank_changed", p.name or p.id, after={"was": p.bank_mask, "now": _mask(str(f["bank_account"]))}, actor="owner")
            p.bank_enc, p.bank_mask = encrypt(new) or "", _mask(str(f["bank_account"]))
        s.flush()
        s.commit()
        return party_view(p) | ({"warning": "The bank details of this party changed - check by phone with a number you already hold before paying."} if p.bank_history != "[]" and f.get("bank_account") else {})


def parties(tenant: str) -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        return [party_view(p) for p in s.scalars(select(AccParty).where(AccParty.tenant_id == tenant).order_by(AccParty.name)).all()]


def _party_for(s, tenant: str, d: AccDoc) -> AccParty | None:
    if d.party_gstin:
        p = s.scalars(select(AccParty).where(AccParty.tenant_id == tenant, AccParty.gstin == d.party_gstin)).first()
        if p:
            return p
    if d.party_name:
        for p in s.scalars(select(AccParty).where(AccParty.tenant_id == tenant)).all():
            if p.name.strip().lower() == d.party_name.strip().lower():
                return p
    return None


# ------------------------------------------------------------------ ageing + watches
def _open_docs(s, tenant: str, direction: str) -> list[AccDoc]:
    paid = {l.match_doc_id for l in s.scalars(select(AccBankLine).where(AccBankLine.tenant_id == tenant, AccBankLine.status == "matched")).all() if l.match_doc_id}
    return [d for d in s.scalars(select(AccDoc).where(AccDoc.tenant_id == tenant, AccDoc.direction == direction, AccDoc.status != "gone", AccDoc.total > 0)).all()
            if d.kind in ("inv", "bill", "dn") and d.id not in paid and d.doc_date]


def _days(a: str, today: date) -> int:
    try:
        return (today - date.fromisoformat(a)).days
    except ValueError:
        return 0


def ageing(tenant: str, direction: str = "out", today: date | None = None) -> dict[str, Any]:
    """Who owes you (out = sales) or whom you owe (in = purchases): what is still unsettled by a matched bank line, by days past due."""
    today = today or _today()
    ensure_tables()
    buckets = ("not_due", "1-30", "31-60", "61-90", "90+")
    with session() as s:
        by: dict[str, dict[str, Any]] = {}
        for d in _open_docs(s, tenant, direction):
            p = _party_for(s, tenant, d)
            due_days = (p.agreed_days if p and p.agreed_days else 30)
            late = _days(d.doc_date, today) - due_days
            b = "not_due" if late <= 0 else "1-30" if late <= 30 else "31-60" if late <= 60 else "61-90" if late <= 90 else "90+"
            key = (p.name if p else d.party_name) or d.party_gstin or "Unnamed"
            row = by.setdefault(key, {"party": key, "party_id": p.id if p else "", "total": 0.0, **{x: 0.0 for x in buckets}, "docs": []})
            row["total"] = round(row["total"] + d.total, 2)
            row[b] = round(row[b] + d.total, 2)
            row["docs"].append({"doc_id": d.id, "number": d.number, "date": d.doc_date, "amount": d.total, "days_overdue": max(0, late)})
    rows = sorted(by.values(), key=lambda r: -r["total"])
    return {"direction": direction, "label": "Receivable (owed to you)" if direction == "out" else "Payable (you owe)", "parties": rows,
            "totals": {b: round(sum(r[b] for r in rows), 2) for b in buckets} | {"all": round(sum(r["total"] for r in rows), 2)},
            "note": "A document counts as settled only when a bank line you confirmed is matched to it (Bank tab). Part-payments are not tracked."}


def msme_watch(tenant: str, today: date | None = None) -> dict[str, Any]:
    """Purchases from micro / small suppliers: due by the agreed days (never more than 45), or 15 days when nothing is agreed in writing."""
    today = today or _today()
    ensure_tables()
    fy_end = date(today.year + (1 if today.month > 3 else 0), 3, 31)
    out = []
    with session() as s:
        for d in _open_docs(s, tenant, "in"):
            p = _party_for(s, tenant, d)
            if not p or p.msme_class not in ("micro", "small"):
                continue
            limit = min(p.agreed_days, 45) if p.agreed_days else 15
            try:
                due = date.fromisoformat(d.doc_date) + timedelta(days=limit)
            except ValueError:
                continue
            left = (due - today).days
            out.append({"doc_id": d.id, "party": p.name, "msme_class": p.msme_class, "number": d.number, "date": d.doc_date, "amount": d.total, "limit_days": limit,
                        "due_on": due.isoformat(), "days_left": left, "state": "overdue" if left < 0 else "due_soon" if left <= 7 else "ok",
                        "fy_end_risk": due <= fy_end, "agreed_in_writing": bool(p.agreed_days)})
    out.sort(key=lambda r: r["days_left"])
    return {"rows": out, "fy_end": fy_end.isoformat(),
            "note": "Payment to a micro / small supplier beyond the 15 days (45 with a written agreement) is deductible only in the year you actually pay "
                    "(old s.43B(h); s.37(2)(g) of the Income-tax Act 2025 per the plan - confirm the reference with your CA): pay before "
                    f"{fy_end.strftime('%d %b %Y')} to keep this year's deduction. Interest on delay (3x the bank rate, monthly rests) is the supplier's right and is not computed here.",
            "party_setup_missing": "Mark a supplier micro / small (and give its Udyam number) in the party master for it to appear here."}


def rule37_watch(tenant: str, today: date | None = None) -> dict[str, Any]:
    days = int(next((r["value"] for r in RU.rows("limits") if r["id"] == "rule37_days"), 180))
    today = today or _today()
    ensure_tables()
    rows = []
    with session() as s:
        for d in _open_docs(s, tenant, "in"):
            age = _days(d.doc_date, today)
            if age >= days - 30 and (d.igst + d.cgst + d.sgst + d.cess + d.tax) > 0:
                rows.append({"doc_id": d.id, "party": d.party_name or d.party_gstin, "number": d.number, "date": d.doc_date, "amount": d.total,
                             "credit_at_stake": round((d.igst + d.cgst + d.sgst + d.cess) or d.tax, 2), "age_days": age, "days_left": days - age,
                             "state": "reverse_credit" if age > days else "pay_soon"})
    rows.sort(key=lambda r: r["days_left"])
    return {"limit_days": days, "rows": rows, "note": "A supplier not paid within 180 days of the invoice date means the credit taken on it is reversed in GSTR-3B with interest "
            "(and may be taken again when you pay). Paid ones are those matched to a bank line you confirmed."}


def reminders(tenant: str, today: date | None = None) -> list[dict[str, Any]]:
    """Collection reminders DRAFTED for overdue sales - Hoola sends nothing; a party marked 'no reminders' is skipped."""
    today = today or _today()
    ag = ageing(tenant, "out", today)
    out = []
    for r in ag["parties"]:
        with session() as s:
            p = s.get(AccParty, r["party_id"]) if r["party_id"] else None
            if p is not None and p.no_reminders:
                continue
        late = [d for d in r["docs"] if d["days_overdue"] > 0]
        if not late:
            continue
        amt = round(sum(d["amount"] for d in late), 2)
        lines = ", ".join(f"{d['number']} (Rs {d['amount']:g}, {d['days_overdue']} days late)" for d in late[:6])
        msg = f"Hello {r['party']}, a gentle reminder: {lines} {'is' if len(late) == 1 else 'are'} still unpaid - Rs {amt:g} in all. Please let us know when the payment will be made. Thank you."
        out.append({"party": r["party"], "overdue": amt, "invoices": len(late), "text": msg, "wa_link": "https://wa.me/?text=" + quote(msg),
                    "note": "No payment link is attached - create one from your payment gateway if you want to."})
    return out


# ------------------------------------------------------------------ TDS
def _rule_for(nature: str) -> dict[str, Any]:
    for r in RU.rows("tds"):
        if r["nature"] == nature or r["id"] == nature:
            return r
    raise PayError("Nature of payment: " + ", ".join(r["nature"] for r in RU.rows("tds")) + ".")


def guess_nature(text: str) -> str:
    t = f" {str(text or '').lower()} "
    for r in RU.rows("tds"):
        if any(w in t for w in r.get("words", [])):
            return r["nature"]
    return ""


def due_on(paid_on: str) -> str:
    d = date.fromisoformat(paid_on)
    if d.month == 3:
        return date(d.year, 4, 30).isoformat()
    y, m = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return date(y, m, int(RU.load("tds")["general"]["due_day"])).isoformat()


def worksheet(tenant: str, party_id: str, nature: str, amount: float, paid_on: str, gst_separate: bool = False, gst_amount: float = 0.0) -> dict[str, Any]:
    """TDS on one payment: applicable or not (single / yearly limit from what she already recorded), the rate (no-PAN rate if the PAN is bad),
    the amount, the due date. It computes - it never deducts; the deduction and the deposit are hers."""
    ensure_tables()
    if amount <= 0:
        raise PayError("The payment amount must be above zero.")
    try:
        date.fromisoformat(paid_on)
    except ValueError:
        raise PayError("Payment date as YYYY-MM-DD.") from None
    rule = _rule_for(nature)
    if not RU.usable(rule):
        raise PayError("This TDS row is unverified - it is shown for information and is not used to compute.")
    gen = RU.load("tds")["general"]
    with session() as s:
        p = s.get(AccParty, party_id)
        if p is None or p.tenant_id != tenant:
            raise PayError("Pick the party from the party master (add it first).")
        fy_start = date.fromisoformat(paid_on)
        fy_start = date(fy_start.year if fy_start.month >= 4 else fy_start.year - 1, 4, 1)
        prior = sum(r.base for r in s.scalars(select(AccTds).where(AccTds.tenant_id == tenant, AccTds.party_id == p.id, AccTds.rule_id == rule["id"],
                                                                 AccTds.paid_on >= fy_start.isoformat(), AccTds.paid_on <= paid_on)).all())
        pan, pan_ok, constitution, name = p.pan, p.pan_ok, p.constitution, p.name
    base = round(amount - (gst_amount if gst_separate else 0.0), 2)
    notes: list[str] = []
    if gst_separate:
        notes.append(f"GST of Rs {gst_amount:g} is shown separately on the bill, so TDS is on Rs {base:g} (before GST).")
    over_single = bool(rule["single_limit"]) and base > rule["single_limit"]
    over_year = (prior + base) > rule["yearly_limit"]
    applies = over_single or over_year or not (rule["single_limit"] or rule["yearly_limit"])
    rate = rule["rate"]
    if rule["id"] == "194C" and constitution in ("individual", "huf"):
        rate = rule["rate_individual_huf"]
    if applies and (not pan or not pan_ok):
        rate = max(gen["no_pan_min_rate"], rate * 2)
        notes.append("No valid PAN: TDS is at the higher rate (20%, or double the normal rate if more).")
    tds = round(base * rate / 100, 0) if applies else 0.0
    if applies and (prior + (0 if over_single else 0)) and prior <= rule["yearly_limit"] < prior + base and not over_single:
        notes.append(f"This payment takes the year's total to Rs {prior + base:g}, past the Rs {rule['yearly_limit']:g} limit. TDS is worked on THIS payment; whether earlier payments also need TDS is a question for your CA.")
    if not applies:
        notes.append(f"Below the limits (single Rs {rule['single_limit']:g}, yearly Rs {rule['yearly_limit']:g}; recorded so far this year Rs {prior:g}) - no TDS needed on this payment.")
    return {"party": name, "section": rule["id"].split("_")[0], "rule_id": rule["id"], "what": rule["what"], "applies": applies, "base": base, "rate": rate if applies else 0.0,
            "tds": tds, "net_to_pay": round(amount - tds, 2), "due_on": due_on(paid_on), "year_so_far": round(prior, 2), "notes": notes,
            "verify": "Rate and limits are the old-Act section as carried into section 393 of the Income-tax Act 2025. The item number in the new table was not read on the Act's text - confirm with your CA before you deposit.",
            "source": rule["source"]}


def record(tenant: str, party_id: str, nature: str, amount: float, paid_on: str, gst_separate: bool = False, gst_amount: float = 0.0, confirm: bool = False) -> dict[str, Any]:
    """Her tap: note that she DEDUCTED this TDS (the register behind the challan). Hoola moves no money."""
    if confirm is not True:
        raise PayError("Recording a deduction needs your confirmation - it goes into the TDS register and the quarter's return data.")
    w = worksheet(tenant, party_id, nature, amount, paid_on, gst_separate, gst_amount)
    if not w["applies"]:
        raise PayError("No TDS applies to this payment, so nothing is recorded.")
    with session() as s:
        p = s.get(AccParty, party_id)
        row = AccTds(tenant_id=tenant, party_id=party_id, party_name=p.name, pan=p.pan, rule_id=w["rule_id"], section=w["section"], paid_on=paid_on,
                     base=w["base"], rate=w["rate"], tds=w["tds"], due_on=w["due_on"], note="; ".join(w["notes"])[:500])
        s.add(row)
        REG._event(s, tenant, "tds_recorded", f"{p.name}:{w['section']}", after={"tds": w["tds"], "base": w["base"]}, actor="owner")
        s.commit()
        return _tds_view(row)


def deposit(tenant: str, tds_ids: list[str], challan: str, deposited_on: str) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9\-/ ]{5,40}", challan or ""):
        raise PayError("Type the challan serial / CIN as printed on your payment receipt.")
    try:
        date.fromisoformat(deposited_on)
    except ValueError:
        raise PayError("Deposit date as YYYY-MM-DD.") from None
    n = 0
    with session() as s:
        for i in tds_ids:
            r = s.get(AccTds, i)
            if r is not None and r.tenant_id == tenant and not r.deposited_on:
                r.deposited_on, r.challan = deposited_on, challan
                n += 1
        REG._event(s, tenant, "tds_deposited", challan, after={"rows": n}, actor="owner")
        s.commit()
    return {"deposited": n}


def _late_months(a: str, b: str) -> int:
    x, y = date.fromisoformat(a), date.fromisoformat(b)
    m = (y.year - x.year) * 12 + (y.month - x.month)
    return max(0, m + (1 if y.day > x.day else 0)) if y > x else 0


def _tds_view(r: AccTds, today: date | None = None) -> dict[str, Any]:
    today = today or _today()
    late_dep = r.deposited_on and r.deposited_on > r.due_on
    pending = not r.deposited_on
    gen = RU.load("tds")["general"]
    return {"id": r.id, "party": r.party_name, "pan": r.pan, "section": r.section, "paid_on": r.paid_on, "base": r.base, "rate": r.rate, "tds": r.tds, "due_on": r.due_on,
            "deposited_on": r.deposited_on, "challan": r.challan,
            "state": "deposited_late" if late_dep else "deposited" if r.deposited_on else "overdue" if r.due_on < today.isoformat() else "to_deposit",
            "interest_estimate": round(r.tds * gen["late_deposit_interest_pct_month"] / 100 * _late_months(r.due_on, r.deposited_on if r.deposited_on else today.isoformat()), 0) if (late_dep or (pending and r.due_on < today.isoformat())) else 0.0}


def register(tenant: str, fy_start_year: int | None = None) -> dict[str, Any]:
    ensure_tables()
    today = _today()
    y = fy_start_year or (today.year if today.month >= 4 else today.year - 1)
    with session() as s:
        rows = s.scalars(select(AccTds).where(AccTds.tenant_id == tenant, AccTds.paid_on >= f"{y}-04-01", AccTds.paid_on <= f"{y + 1}-03-31").order_by(AccTds.paid_on)).all()
        vs = [_tds_view(r, today) for r in rows]
    return {"fy": f"{y}-{str(y + 1)[2:]}", "rows": vs, "to_deposit": round(sum(v["tds"] for v in vs if v["state"] in ("to_deposit", "overdue")), 2),
            "overdue": [v for v in vs if v["state"] == "overdue"]}


QUARTER_DUE = {1: "07-31", 2: "10-31", 3: "01-31", 4: "05-31"}


def quarter(tenant: str, fy_start_year: int, q: int) -> dict[str, Any]:
    """The quarter's deductions laid out for the quarterly statement (Form 140, old 26Q). Hoola files nothing: your CA or your TDS software uploads it."""
    if q not in (1, 2, 3, 4):
        raise PayError("Quarter 1 to 4.")
    months = {1: (4, 6), 2: (7, 9), 3: (10, 12), 4: (1, 3)}[q]
    y0 = fy_start_year if q < 4 else fy_start_year + 1
    a, b = f"{y0}-{months[0]:02d}-01", f"{y0}-{months[1]:02d}-31"
    ensure_tables()
    with session() as s:
        rows = s.scalars(select(AccTds).where(AccTds.tenant_id == tenant, AccTds.paid_on >= a, AccTds.paid_on <= b).order_by(AccTds.paid_on)).all()
        vs = [_tds_view(r) for r in rows]
    due = f"{fy_start_year + (1 if q == 4 else 0) + (1 if q == 3 else 0)}-{QUARTER_DUE[q]}"
    return {"fy": f"{fy_start_year}-{str(fy_start_year + 1)[2:]}", "quarter": q, "statement": "Form 140 (non-salary TDS; old Form 26Q)", "due_on": due,
            "rows": [{"deductee_pan": v["pan"] or "PANNOTAVBL", "name": v["party"], "section": v["section"], "paid_on": v["paid_on"], "amount": v["base"], "rate": v["rate"],
                      "tds": v["tds"], "deposited_on": v["deposited_on"], "challan": v["challan"]} for v in vs],
            "total_tds": round(sum(v["tds"] for v in vs), 2), "undeposited": [v["id"] for v in vs if not v["deposited_on"]],
            "note": "Hoola prepares these rows only. The statement is prepared and uploaded by your CA or TDS software (there is no public deductor API); the deductor's TAN is not held here."}


def match_26as(tenant: str, fy_start_year: int, portal_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Her deductions (the tax OTHERS deducted from her is a different table) against the portal's 26AS / AIS rows she pastes."""
    from ..finops.tax import tds_reconcile
    reg = register(tenant, fy_start_year)
    books = [{"party": r["party"], "section": r["section"], "tds": r["tds"]} for r in reg["rows"]]
    return tds_reconcile(books, portal_rows or [])
