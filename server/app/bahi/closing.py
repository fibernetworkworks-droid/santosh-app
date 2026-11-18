"""v0.849 BAHI A10 - month-end and year-end: the checklist (every tick from what Hoola really holds), the MIS and the daily cash line, the calendar (the monthly
dates plus the yearly ones, from rules files), the accuracy sweep, and the GSTR-9 comparison.

Laws: a line is ticked only on a record - never on assumption; what Hoola does not hold (payroll, accruals) is shown as 'not tracked here', not ticked; the daily line
and the checklist are TEXT and data - nothing is sent or filed from here; the GSTR-9 comparison reads the portal's own figures and files nothing.
NOT BUILT: sending the daily line to WhatsApp / voice, the HSN-vs-rate check (needs an HSN rate table), the cash-payment limit check (Hoola does not hold cash payments to
parties), Rule 37A (needs the supplier filing track per bill). NOT VERIFIED: the GSTR-9 reads (paths from the spec) and their layout.
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select

from ..db import session
from . import connect as CN
from . import einv as EV
from . import payables as PY
from . import rules as RU
from . import wb
from .models import (AccBankLine, AccBankRecon, AccDoc, AccEvent, AccIntake, AccIrn, AccPack, AccParty, AccTds, AccTwoB, ensure_tables)


class CloseError(Exception):
    pass


def _month(m: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}", m or ""):
        raise CloseError("Month as YYYY-MM.")
    return m


def _events(s, tenant: str, what: str, g: str, month: str) -> bool:
    return s.scalars(select(AccEvent).where(AccEvent.tenant_id == tenant, AccEvent.what == what, AccEvent.ref == f"{g}:{month}")).first() is not None


def checklist(tenant: str, gstin: str, month: str, today: date | None = None) -> dict[str, Any]:
    g, month, today = (gstin or "").strip().upper(), _month(month), today or date.today()
    ensure_tables()
    rtn = month[5:] + month[:4]
    items: list[dict[str, Any]] = []
    due = {d["id"]: d for d in RU.dues_for(month, today=today)}

    def add(key, title, state, why, tab, due_id=""):
        d = due.get(due_id) if due_id else None
        items.append({"key": key, "title": title, "state": state, "why": why, "tab": tab, "due": d["date"] if d else "", "days_left": d["days_left"] if d else None})

    with session() as s:
        drafts = s.scalars(select(AccIntake).where(AccIntake.tenant_id == tenant, AccIntake.status == "draft")).all()
        add("bills", "Purchase bills in and checked", "todo" if drafts else "done",
            f"{len(drafts)} bill draft(s) waiting for you." if drafts else "No bill draft is waiting.", "bl")
        lines = s.scalars(select(AccBankLine).where(AccBankLine.tenant_id == tenant, AccBankLine.date.like(month + "%"))).all()
        open_ = [l for l in lines if l.status == "open"]
        prop = [l for l in lines if l.status == "proposed"]
        rec = s.scalars(select(AccBankRecon).where(AccBankRecon.tenant_id == tenant, AccBankRecon.month == month)).first()
        if not lines:
            add("bank", "Bank statement reconciled", "todo", "No bank statement for this month is imported.", "bk")
        elif open_ or prop or rec is None:
            add("bank", "Bank statement reconciled", "todo", f"{len(open_)} line(s) unmatched, {len(prop)} match(es) to confirm" + ("" if rec else "; the month-end statement is not stored yet") + ".", "bk")
        else:
            add("bank", "Bank statement reconciled", "done", f"{len(lines)} lines, all matched; the reconciliation is stored.", "bk")
        two = s.scalars(select(AccTwoB).where(AccTwoB.tenant_id == tenant, AccTwoB.gstin == g, AccTwoB.period == rtn)).all()
        undecided = [t for t in two if not t.action and t.itcavl and not t.rev]
        unsent = [t for t in two if t.action and not t.applied_at]
        if not two:
            add("twob", "Credit (2B) checked and decided", "todo", "This month's GSTR-2B has not been pulled.", "itc", "gstr2b")
        elif undecided:
            add("twob", "Credit (2B) checked and decided", "todo", f"{len(undecided)} invoice(s) have no accept / pending / reject decision.", "itc", "gstr2b")
        elif unsent:
            add("twob", "Credit (2B) checked and decided", "todo", f"{len(unsent)} decision(s) are made but not yet sent to the portal.", "itc", "gstr2b")
        else:
            add("twob", "Credit (2B) checked and decided", "done", f"{len(two)} invoices decided and sent.", "itc", "gstr2b")
        irn_pending = len(EV.watch(tenant, g)) if g else 0
        if irn_pending:
            add("irn", "e-invoices issued", "todo", f"{irn_pending} sale(s) to registered customers have no IRN yet.", "ei")
        gp = {}
        try:
            from ..gstp.service import GstClient, GstReturn
            c = s.scalars(select(GstClient).where(GstClient.tenant_id == tenant, GstClient.gstin == g)).first()
            if c is not None:
                for r in s.scalars(select(GstReturn).where(GstReturn.tenant_id == tenant, GstReturn.client_id == c.id, GstReturn.period == month)).all():
                    gp[r.kind] = r.status
        except Exception:   # noqa: BLE001
            pass
        for kind, key, title, saved_ev, tab, due_id in (("gstr1", "gstr1", "GSTR-1", "gstr1_saved", "g1", "gstr1"), ("gstr3b", "gstr3b", "GSTR-3B", "gstr3b_saved", "g3", "gstr3b")):
            if gp.get(kind) == "filed" or _events(s, tenant, f"{kind}_filed", g, month):
                add(key, f"{title} filed", "done", "Filed (a record exists).", tab, due_id)
            elif _events(s, tenant, saved_ev, g, month):
                add(key, f"{title} filed", "todo", "A draft is saved on the portal; filing is still to do.", tab, due_id)
            elif gp.get(kind) == "ready":
                add(key, f"{title} filed", "todo", "Prepared in Hoola; not saved or filed.", tab, due_id)
            else:
                add(key, f"{title} filed", "todo", "Not prepared yet.", tab, due_id)
        tds = s.scalars(select(AccTds).where(AccTds.tenant_id == tenant, AccTds.paid_on.like(month + "%"))).all()
        und = [t for t in tds if not t.deposited_on]
        if not tds:
            add("tds", "TDS deposited", "info", "No deduction is recorded for this month. If you paid anyone liable to TDS, record it.", "py", "tds_deposit")
        elif und:
            add("tds", "TDS deposited", "todo", f"Rs {sum(t.tds for t in und):g} on {len(und)} deduction(s) is not deposited.", "py", "tds_deposit")
        else:
            add("tds", "TDS deposited", "done", f"{len(tds)} deduction(s), all deposited.", "py", "tds_deposit")
        add("payroll", "Payroll posted", "na", "Not tracked here - payroll lives in its own part of Hoola.", "")
        add("accruals", "Accruals listed", "na", "Not tracked here.", "")
        pack = s.scalars(select(AccPack).where(AccPack.tenant_id == tenant, AccPack.month == month, AccPack.closed_at != "")).first()
        add("closed", "Month closed with the CA pack", "done" if pack else "todo", "Closed on a pack." if pack else "Build the CA pack and close the month when everything above is done.", "ca")
    counted = [i for i in items if i["state"] in ("done", "todo")]
    done = sum(1 for i in counted if i["state"] == "done")
    return {"gstin": g, "month": month, "items": items, "done": done, "total": len(counted), "ready_to_close": all(i["state"] != "todo" for i in items if i["key"] != "closed")}


# ------------------------------------------------------------------ MIS + the daily line
def mis(tenant: str, gstin: str, month: str) -> dict[str, Any]:
    g, month = (gstin or "").strip().upper(), _month(month)
    ensure_tables()
    with session() as s:
        docs = [d for d in s.scalars(select(AccDoc).where(AccDoc.tenant_id == tenant, AccDoc.period == month, AccDoc.status != "gone")).all() if d.gstin in (g, "")]
        lines = s.scalars(select(AccBankLine).where(AccBankLine.tenant_id == tenant, AccBankLine.date.like(month + "%"))).all()
    def tot(direction, f):
        return round(sum((d.taxable or 0) * (-1 if d.kind == "cn" else 1) for d in docs if d.direction == direction and f(d)), 2)
    sales, buys = tot("out", lambda d: True), tot("in", lambda d: True)
    ar, ap = PY.ageing(tenant, "out"), PY.ageing(tenant, "in")
    overdue = lambda a: round(a["totals"]["all"] - a["totals"]["not_due"], 2)   # noqa: E731
    cin, cout = round(sum(l.credit for l in lines), 2), round(sum(l.debit for l in lines), 2)
    return {"month": month, "sales_taxable": sales, "purchases_taxable": buys, "margin_on_purchases": round(sales - buys, 2),
            "margin_note": "Sales minus purchase bills only - Hoola holds no stock, so this is not a true gross profit.",
            "cash_in": cin, "cash_out": cout, "net_cash": round(cin - cout, 2), "bank_lines": len(lines),
            "receivables": ar["totals"]["all"], "receivables_overdue": overdue(ar), "payables": ap["totals"]["all"], "payables_overdue": overdue(ap)}


def daily_line(tenant: str, day: str = "", gstin: str = "") -> dict[str, Any]:
    today = date.fromisoformat(day) if day else date.today()
    tomorrow = today + timedelta(days=1)
    ensure_tables()
    with session() as s:
        ls = s.scalars(select(AccBankLine).where(AccBankLine.tenant_id == tenant, AccBankLine.date == today.isoformat())).all()
        dues = []
        for direction in ("out", "in"):
            for d in PY._open_docs(s, tenant, direction):
                p = PY._party_for(s, tenant, d)
                days = p.agreed_days if p and p.agreed_days else 30
                try:
                    if date.fromisoformat(d.doc_date) + timedelta(days=days) == tomorrow:
                        dues.append((direction, (p.name if p else d.party_name) or "a party", d.total))
                except ValueError:
                    continue
    cin, cout = round(sum(l.credit for l in ls), 2), round(sum(l.debit for l in ls), 2)
    parts = [f"Today Rs {cin:,.0f} came in and Rs {cout:,.0f} went out." if ls else "No bank movement is recorded for today."]
    coll = [x for x in dues if x[0] == "out"]
    pay = [x for x in dues if x[0] == "in"]
    if coll:
        parts.append("Due tomorrow from customers: " + ", ".join(f"{n} Rs {a:,.0f}" for _, n, a in coll[:4]) + ".")
    if pay:
        parts.append("You owe tomorrow: " + ", ".join(f"{n} Rs {a:,.0f}" for _, n, a in pay[:4]) + ".")
    return {"day": today.isoformat(), "in": cin, "out": cout, "due_tomorrow_from": [{"party": n, "amount": a} for _, n, a in coll], "you_owe_tomorrow": [{"party": n, "amount": a} for _, n, a in pay],
            "text": " ".join(parts), "note": "Text only - Hoola sends nothing. The dues use the days agreed with each party, or 30."}


# ------------------------------------------------------------------ calendar
def calendar(tenant: str, gstin: str, today: date | None = None, horizon_days: int = 120) -> dict[str, Any]:
    today = today or date.today()
    out: list[dict[str, Any]] = []
    seen: set[tuple] = set()
    for back in (2, 1, 0):                          # the monthly dates of the periods whose work is still ahead or just gone
        y, m = today.year, today.month - back
        while m < 1:
            m, y = m + 12, y - 1
        for d in RU.dues_for(f"{y:04d}-{m:02d}", today=today):
            key = (d["id"], d["date"])
            if key not in seen and -7 <= d["days_left"] <= horizon_days:
                seen.add(key)
                out.append({**d, "kind": "monthly"})
    for r in RU.rows("annual"):
        for yy in (today.year, today.year + 1):
            try:
                dt = date(yy, r["month"], r["day"])
            except ValueError:
                continue
            left = (dt - today).days
            if -7 <= left <= horizon_days and (r["id"], dt.isoformat()) not in seen:
                seen.add((r["id"], dt.isoformat()))
                out.append({"id": r["id"], "what": r["what"], "date": dt.isoformat(), "days_left": left, "if_missed": r.get("if_missed", ""), "basis": r["basis"], "source": r["source"],
                            "checked_on": r["checked_on"], "kind": "yearly", "warning_only": r["basis"] == "unverified"})
    out.sort(key=lambda x: x["date"])
    cliff = next((x for x in out if x["id"] == "itc_cliff"), None)
    extra: dict[str, Any] = {}
    if cliff:
        fy_end_year = date.fromisoformat(cliff["date"]).year
        lo, hi = f"{fy_end_year - 1}-04", f"{fy_end_year}-03"              # the financial year whose purchases can still be claimed until the cliff
        with session() as s:
            docs = [d for d in s.scalars(select(AccDoc).where(AccDoc.tenant_id == tenant, AccDoc.direction == "in", AccDoc.status != "gone", AccDoc.period >= lo, AccDoc.period <= hi)).all()]
        extra = {"itc_cliff_for": f"purchases dated {lo} to {hi}", "purchase_bills": len(docs),
                 "credit_in_those_bills": round(sum((d.igst + d.cgst + d.sgst + d.cess) or d.tax for d in docs), 2),
                 "note": "Upper bound: the credit printed on those bills. Check any not yet taken in a GSTR-3B before the date."}
    return {"today": today.isoformat(), "items": out, "itc_cliff": extra, "not_built": "Rule 37A (supplier did not file) needs the supplier filing track per bill."}


# ------------------------------------------------------------------ the accuracy sweep
def _nn(n: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (n or "").lower())


def sweep(tenant: str) -> dict[str, Any]:
    ensure_tables()
    flags: list[dict[str, Any]] = []
    with session() as s:
        docs = s.scalars(select(AccDoc).where(AccDoc.tenant_id == tenant, AccDoc.status != "gone")).all()
        by_gstin: dict[str, set[str]] = {}
        by_name: dict[str, set[str]] = {}
        for d in docs:
            if d.party_gstin and d.party_name:
                by_gstin.setdefault(d.party_gstin, set()).add(d.party_name.strip())
                by_name.setdefault(_nn(d.party_name), set()).add(d.party_gstin)
        for g, names in by_gstin.items():
            if len({_nn(n) for n in names}) > 1:
                flags.append({"kind": "party_many_names", "text": f"GSTIN {g} appears under {len(names)} names: {', '.join(sorted(names))}. Keep one in the party list.", "fix": "py"})
        for n, gs in by_name.items():
            if len(gs) > 1:
                flags.append({"kind": "name_many_gstins", "text": f"A party named '{n}' appears with {len(gs)} different GSTINs: {', '.join(sorted(gs))} - one may be a typing mistake.", "fix": "py"})
        lines = s.scalars(select(AccBankLine).where(AccBankLine.tenant_id == tenant)).all()
        for l in lines:
            amt = l.credit or l.debit
            if l.mode == "cash" and amt >= 50000 and amt % 1000 == 0:
                flags.append({"kind": "round_cash", "text": f"{l.date}: a round cash amount of Rs {amt:g} ('{l.narration[:40]}') - keep the voucher or the reason.", "fix": "bk", "ref": l.id})
        seen: dict[str, set[str]] = {}
        names = {d.id: d.party_name for d in docs}
        for l in lines:
            if l.status == "matched" and l.match_doc_id in names and l.narration:
                seen.setdefault(re.sub(r"\d{3,}", "", l.narration.lower())[:40], set()).add(names[l.match_doc_id])
        for narr, ps in seen.items():
            if len(ps) > 1 and len(narr.strip()) > 8:
                flags.append({"kind": "same_narration", "text": f"The narration '{narr.strip()}' was matched to {len(ps)} different parties ({', '.join(sorted(ps))}) - check one is not wrong.", "fix": "bk"})
        for t in s.scalars(select(AccParty).where(AccParty.tenant_id == tenant)).all():
            if t.bank_history and t.bank_history != "[]":
                flags.append({"kind": "bank_changed", "text": f"{t.name}: the bank account was changed {len(json.loads(t.bank_history))} time(s) - confirm by phone before the next payment.", "fix": "py"})
    return {"flags": flags[:200], "not_checked": ["HSN against the rate (needs an HSN rate table)", "cash payments over the legal limit (Hoola does not hold cash payments to parties)"]}


# ------------------------------------------------------------------ GSTR-9 comparison
def gstr9_compare(tenant: str, gstin: str, fy: str) -> dict[str, Any]:
    """The portal's auto-calculated annual figures beside the register's totals for the year. Reads only; files nothing."""
    from .apisetu import shape_keys
    g = (gstin or "").strip().upper()
    if not re.fullmatch(r"\d{4}-\d{2}", fy or ""):
        raise CloseError("Financial year as YYYY-YY, for example 2025-26.")
    y = int(fy[:4])
    lo, hi = f"{y}-04", f"{y + 1}-03"
    try:
        user, state, txn = CN.session_for(tenant, g)
        auto = wb.data_of(wb.gstr9_autocal(tenant, g, fy, user, state, txn))
        t8a = wb.data_of(wb.gstr9_8a(tenant, g, fy, user, state, txn))
    except (CN.ConnectError, wb.WbError) as e:
        raise CloseError(getattr(e, "message", None) or str(e)) from None
    from .gstr3b import _liab
    portal = _liab(auto)
    with session() as s:
        docs = [d for d in s.scalars(select(AccDoc).where(AccDoc.tenant_id == tenant, AccDoc.direction == "out", AccDoc.status != "gone", AccDoc.period >= lo, AccDoc.period <= hi)).all() if d.gstin in (g, "")]
        two = s.scalars(select(AccTwoB).where(AccTwoB.tenant_id == tenant, AccTwoB.gstin == g)).all()
    mine = {"igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0}
    for d in docs:
        sg = -1 if d.kind == "cn" else 1
        for h in mine:
            mine[h] += (getattr(d, h) or 0) * sg
    rows = [{"head": h, "register": round(mine[h], 2), "portal": portal.get(h, 0.0), "diff": round(mine[h] - portal.get(h, 0.0), 2)} for h in mine] if portal else []
    return {"fy": fy, "compared": bool(portal), "rows": rows, "register_sales_docs": len(docs), "your_2b_rows_held": len(two),
            "portal_fields_autocal": shape_keys(auto), "portal_fields_8a": shape_keys(t8a),
            "note": ("" if portal else "The portal's layout was not recognised, so nothing was compared - its fields are listed.") +
            " This is a comparison for your CA's GSTR-9 / 9C work; Hoola files nothing. Reads are from the spec's names and are NOT VERIFIED."}
