"""F3 of docs/FINANCE_GLOBAL_PLAN.md - Books & Accounts for any country (employee `books`, tool `books_accounts`).

Double-entry books on the F0 spine, in integer minor units of the workspace's currency:

  chart of accounts   one per workspace, a plain worldwide starter she can add to
  journal             every posting balances or is refused; a locked month refuses new postings; a source posts once
  invoices / bills    numbered once and never reused; her own tax rate (a country's rate is shown, never used, until checked)
  receipts            a receipt's text read into a DRAFT bill she confirms
  cash application    bank lines matched to open invoices and bills, each match with its reason; nothing is posted until she confirms
  bank lines          a bank line with no document posted to the account she picks (Hoola proposes one from its words)
  reconciliation      bank vs books: matched, bank only, books only, the difference explained
  ageing              receivables / payables in 0-30 / 31-60 / 61-90 / 90+ days past due
  fixed assets        straight-line or reducing balance, a month's depreciation posted once
  inventory cost      FIFO or weighted average on her stock movements
  multi-currency      every foreign document carries a dated rate and its source; realised FX on payment, revaluation at month end
  close               a checklist worked out from the books; the month locks only on her confirm of that exact checklist
  reports + exports   trial balance, profit and loss, balance sheet; journal CSV, Xero / QuickBooks import CSV, Tally XML

Hoola never sends an invoice, pays a bill or files anything. In India the same work runs through GST & Accounts (bahi) as today.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from .. import laws as L
from .. import pack as P
from ..calc import from_minor, to_minor
from .safety import SafetyError

COA = [
    ("1000", "Bank", "asset", "bank"), ("1100", "Accounts receivable", "asset", "ar"), ("1200", "Inventory", "asset", "inventory"),
    ("1300", "Prepayments", "asset", ""), ("1400", "Tax paid on purchases", "asset", "tax_in"),
    ("1500", "Fixed assets at cost", "asset", "fixed"), ("1510", "Accumulated depreciation", "asset", "accum_dep"),
    ("2000", "Accounts payable", "liability", "ap"), ("2100", "Tax due on sales", "liability", "tax_out"),
    ("2200", "Accrued expenses", "liability", ""), ("2300", "Loans", "liability", ""),
    ("3000", "Owner's capital", "equity", "capital"), ("3100", "Retained earnings", "equity", "retained"),
    ("4000", "Sales", "income", "sales"), ("4900", "Other income", "income", ""),
    ("5000", "Cost of sales", "expense", "cogs"), ("6000", "General expenses", "expense", ""), ("6100", "Rent", "expense", ""),
    ("6200", "Utilities", "expense", ""), ("6300", "Wages", "expense", ""), ("6400", "Depreciation", "expense", "dep"),
    ("6500", "Bank charges", "expense", ""), ("6600", "Software and subscriptions", "expense", ""), ("6700", "Travel", "expense", ""),
    ("7000", "Exchange gains and losses", "expense", "fx"), ("9999", "Suspense", "asset", "suspense"),
]
# a bank line's words -> the account Hoola proposes (she confirms or picks another)
PROPOSE = {"rent_mortgage": "6100", "utilities": "6200", "subscriptions": "6600", "transport": "6700", "fees": "6500",
           "insurance": "6000", "groceries": "6000", "eating_out": "6700", "shopping": "6000", "health": "6000", "education": "6000",
           "cash": "9999", "transfers": "9999", "other": "9999", "income": "4900"}


class BooksError(SafetyError):
    pass


# ---- plumbing --------------------------------------------------------------------------------------------------------------

def _db():
    from ... import db
    from .. import models as M
    M.ensure()
    return db, M


def _ws(tenant: str, ws: str) -> dict[str, Any]:
    from ..profile import ProfileError, get
    try:
        return get(tenant, ws)
    except ProfileError as e:
        raise BooksError(str(e))


def _book_cur(w: dict[str, Any]) -> str:
    return str(w.get("currency") or "USD").upper()


def _m(x: Any, cur: str) -> int:
    return to_minor(Decimal(str(x or 0)), cur)


def _u(minor: int, cur: str) -> float:
    return float(from_minor(int(minor), cur))


def _day(s: Any, what: str) -> str:
    try:
        return date.fromisoformat(str(s)[:10]).isoformat()
    except ValueError:
        raise BooksError(f"{what}: a date as YYYY-MM-DD.")


def ensure_coa(tenant: str, ws: str) -> None:
    db, M = _db()
    with db.session() as s:
        have = {c for (c,) in s.query(M.FinCoa.code).filter(M.FinCoa.tenant_id == tenant, M.FinCoa.workspace_id == ws).all()}
        for code, name, typ, sub in COA:
            if code not in have:
                s.add(M.FinCoa(tenant_id=tenant, workspace_id=ws, code=code, name=name, type=typ, sub=sub))
        s.commit()


def coa(tenant: str, ws: str) -> list[dict[str, Any]]:
    _ws(tenant, ws)
    ensure_coa(tenant, ws)
    db, M = _db()
    with db.session() as s:
        return [{"code": c.code, "name": c.name, "type": c.type, "sub": c.sub}
                for c in s.query(M.FinCoa).filter(M.FinCoa.tenant_id == tenant, M.FinCoa.workspace_id == ws).order_by(M.FinCoa.code)]


def add_account(tenant: str, ws: str, code: str, name: str, typ: str) -> dict[str, Any]:
    if typ not in ("asset", "liability", "equity", "income", "expense") or not re.fullmatch(r"\d{3,8}", str(code)) or not name:
        raise BooksError("account: code (3-8 digits), name, type asset | liability | equity | income | expense.")
    ensure_coa(tenant, ws)
    db, M = _db()
    with db.session() as s:
        if s.query(M.FinCoa).filter(M.FinCoa.tenant_id == tenant, M.FinCoa.workspace_id == ws, M.FinCoa.code == code).first():
            raise BooksError(f"Account {code} already exists.")
        s.add(M.FinCoa(tenant_id=tenant, workspace_id=ws, code=str(code), name=str(name)[:120], type=typ))
        s.commit()
    return {"code": code, "name": name, "type": typ}


def _code_of(s, M, tenant: str, ws: str, sub: str) -> str:
    c = s.query(M.FinCoa).filter(M.FinCoa.tenant_id == tenant, M.FinCoa.workspace_id == ws, M.FinCoa.sub == sub).first()
    if not c:
        raise BooksError(f"The chart of accounts has no {sub} account.")
    return c.code


def locked(tenant: str, ws: str, period: str) -> bool:
    db, M = _db()
    with db.session() as s:
        return s.query(M.FinPeriod).filter(M.FinPeriod.tenant_id == tenant, M.FinPeriod.workspace_id == ws,
                                           M.FinPeriod.period == period).first() is not None


def post(tenant: str, ws: str, day: str, lines: list[dict[str, Any]], memo: str = "", source: str = "manual", source_ref: str = "",
         actor: str = "owner", session=None) -> str:
    """One journal. Lines [{code, debit_minor | credit_minor, party?, txn_id?}] in book minor units. Refused unless it balances, every
    account exists, the month is open, and (with a source_ref) it was not posted before."""
    day = _day(day, "day")
    period = day[:7]
    if locked(tenant, ws, period):
        raise BooksError(f"{period} is closed and locked; post it in an open month.")
    dr = sum(int(l.get("debit_minor") or 0) for l in lines)
    cr = sum(int(l.get("credit_minor") or 0) for l in lines)
    if not lines or dr != cr or dr == 0 or any(int(l.get("debit_minor") or 0) < 0 or int(l.get("credit_minor") or 0) < 0 for l in lines):
        raise BooksError(f"The entry does not balance (debits {dr}, credits {cr}).")
    db, M = _db()
    if session is None:
        with db.session() as s:
            jid = _post(s, M, tenant, ws, day, period, lines, memo, source, source_ref, actor)
            s.commit()
            return jid
    return _post(session, M, tenant, ws, day, period, lines, memo, source, source_ref, actor)


def _post(s, M, tenant, ws, day, period, lines, memo, source, source_ref, actor) -> str:
    codes = {c for (c,) in s.query(M.FinCoa.code).filter(M.FinCoa.tenant_id == tenant, M.FinCoa.workspace_id == ws).all()}
    bad = sorted({str(l.get("code")) for l in lines} - codes)
    if bad:
        raise BooksError("No such account: " + ", ".join(bad))
    if source_ref and s.query(M.FinJournal).filter(M.FinJournal.tenant_id == tenant, M.FinJournal.workspace_id == ws,
                                                   M.FinJournal.source_ref == source_ref).first():
        raise BooksError(f"Already posted ({source_ref}).")
    j = M.FinJournal(tenant_id=tenant, workspace_id=ws, day=day, period=period, memo=str(memo)[:240], source=source,
                     source_ref=source_ref, posted_by=actor)
    s.add(j)
    s.flush()
    for l in lines:
        s.add(M.FinLine(tenant_id=tenant, workspace_id=ws, journal_id=j.id, code=str(l["code"]), debit_minor=int(l.get("debit_minor") or 0),
                        credit_minor=int(l.get("credit_minor") or 0), party=str(l.get("party") or "")[:120],
                        txn_id=str(l.get("txn_id") or ""), dim=str(l.get("dim") or "")[:80]))
    return j.id


def journal_entry(tenant: str, ws: str, a: dict[str, Any], actor: str) -> dict[str, Any]:
    w = _ws(tenant, ws)
    ensure_coa(tenant, ws)
    cur = _book_cur(w)
    lines = [{"code": str(l.get("code")), "debit_minor": _m(l.get("debit"), cur), "credit_minor": _m(l.get("credit"), cur),
              "party": l.get("party", ""), "dim": _cc(tenant, ws, l.get("cost_centre"))} for l in a.get("lines") or []]
    jid = post(tenant, ws, a.get("day") or date.today().isoformat(), lines, a.get("memo", ""), "manual", "", actor)
    return {"journal": jid, "lines": len(lines)}


def _cc(tenant: str, ws: str, v: Any) -> str:
    """A cost centre: free text, or one of the business's list when it has one (v0.999.159)."""
    v = str(v or "").strip()[:80]
    if not v:
        return ""
    from . import books_ent as E
    known = E.controls(tenant, ws).get("cost_centres") or []
    if known and v not in known:
        raise BooksError(f"cost_centre: one of {', '.join(known)}.")
    return v


def _ic(tenant: str, ws: str, v: Any) -> str:
    """The other company of the same group this document is with (v0.999.159): one of her own businesses, never this one."""
    v = str(v or "").strip()
    if not v:
        return ""
    if v == ws:
        raise BooksError("intercompany: another of your businesses, not this one.")
    _ws(tenant, v)
    return v


# ---- invoices and bills -------------------------------------------------------------------------------------------------------

def _next_number(s, M, tenant: str, ws: str, kind: str, issue: str) -> str:
    pre = ("INV" if kind == "sales" else "BILL") + f"-{issue[:4]}-"
    n = s.query(M.FinInvoice).filter(M.FinInvoice.tenant_id == tenant, M.FinInvoice.workspace_id == ws, M.FinInvoice.kind == kind,
                                     M.FinInvoice.number.like(pre + "%")).count()
    return f"{pre}{n + 1:04d}"


def _fx(cur: str, book: str, a: dict[str, Any]) -> tuple[float, str, str]:
    if cur == book:
        return 1.0, "", ""
    rate, rd, src = a.get("rate"), str(a.get("rate_date") or ""), str(a.get("rate_source") or "")
    if not rate or not rd or not src:
        raise BooksError(f"A {cur} document in {book} books needs rate, rate_date and rate_source (where the rate came from).")
    return float(rate), _day(rd, "rate_date"), src[:120]


def _hint(w: dict[str, Any]) -> str:
    cc = (w.get("countries") or [""])[0]
    if not cc or P.load(cc) is None:
        return ""
    v = P.peek(cc, "tax.vat_standard_rate_pct") or P.peek(cc, "tax.sales_tax_note")
    return f"For {cc} Hoola has {v} (not confirmed - check this); the rate used is the one you entered." if v else ""


def _supply(x: Any) -> dict[str, Any]:
    """Where the supply was made, for the tax returns (F4): the other party's country / state, whether it is a business, its tax id
    (kept masked: last 4 only)."""
    if not isinstance(x, dict):
        return {}
    out: dict[str, Any] = {}
    if x.get("country"):
        out["country"] = str(x["country"]).upper()[:2]
    if x.get("state"):
        out["state"] = str(x["state"]).upper()[:8]
    if "b2b" in x:
        out["b2b"] = bool(x["b2b"])
    tid = re.sub(r"\s", "", str(x.get("buyer_tax_id") or x.get("tax_id") or ""))
    if tid:
        out["tax_id"] = ("*" * max(0, len(tid) - 4) + tid[-4:])[:40]
        out["b2b"] = out.get("b2b", True)
    return out


def create_doc(tenant: str, ws: str, kind: str, a: dict[str, Any], actor: str, source: str = "manual") -> dict[str, Any]:
    """An invoice (sales) or a bill (purchase). Lines [{description, qty, price, tax_pct}] in the document's currency.
    issue=true posts it to the books; otherwise it stays a draft."""
    w = _ws(tenant, ws)
    ensure_coa(tenant, ws)
    book = _book_cur(w)
    cur = str(a.get("currency") or book).upper()
    issue = _day(a.get("issue") or date.today().isoformat(), "issue")
    due = _day(a.get("due") or issue, "due")
    if not str(a.get("party") or "").strip():
        raise BooksError("party: who the invoice is to (or the bill is from).")
    net = tax = 0
    lines = []
    for l in a.get("lines") or []:
        q = Decimal(str(l.get("qty") or 1))
        amt = _m(q * Decimal(str(l.get("price") or 0)), cur)
        t = _m(Decimal(amt) * Decimal(str(l.get("tax_pct") or 0)) / 100 / (10 ** P.minor_unit(cur)), cur)
        net, tax = net + amt, tax + t
        row = {"description": str(l.get("description") or "")[:160], "qty": float(q), "price": float(l.get("price") or 0),
               "tax_pct": float(l.get("tax_pct") or 0), "net_minor": amt, "tax_minor": t}
        if l.get("tax_code"):   # F4: how the line is treated for VAT / GST (std, reduced, zero, exempt, export, rc_in ...)
            row["tax_code"] = str(l["tax_code"])[:16]
        if l.get("capital"):
            row["capital"] = True
        lines.append(row)
    if not lines or net <= 0:
        raise BooksError("lines: [{description, qty, price, tax_pct}] with a positive amount.")
    rate, rd, src = _fx(cur, book, a)
    db, M = _db()
    with db.session() as s:
        d = M.FinInvoice(tenant_id=tenant, workspace_id=ws, kind=kind, party=str(a["party"])[:120], issue=issue, due=due, currency=cur,
                         net_minor=net, tax_minor=tax, total_minor=net + tax, rate=rate, carried_rate=rate, rate_date=rd, rate_source=src,
                         code=str(a.get("code") or ("4000" if kind == "sales" else "6000")), lines=json.dumps(lines),
                         supply=json.dumps(_supply(a.get("supply"))),
                         cost_centre=_cc(tenant, ws, a.get("cost_centre")), ic_ws=_ic(tenant, ws, a.get("intercompany")),
                         status="draft", source=source)
        s.add(d)
        s.commit()
        did = d.id
    out = {"id": did, "kind": kind, "status": "draft", "currency": cur, "net": _u(net, cur), "tax": _u(tax, cur), "total": _u(net + tax, cur),
           "tax_note": _hint(w)}
    if a.get("issue_now"):
        out.update(issue_doc(tenant, ws, did, actor))
    return out


def issue_doc(tenant: str, ws: str, doc_id: str, actor: str) -> dict[str, Any]:
    """Draft -> open: the number is given (once) and it is posted. Hoola does not send it."""
    db, M = _db()
    with db.session() as s:
        d = s.get(M.FinInvoice, doc_id)
        if not d or d.tenant_id != tenant or d.workspace_id != ws:
            raise BooksError("No such document.")
        if d.status != "draft":
            raise BooksError(f"It is already {d.status}.")
        book = _book_cur(_ws(tenant, ws))
        f = lambda x: int(round(x * d.rate)) if d.currency != book else x   # noqa: E731
        net, tax = f(d.net_minor), f(d.tax_minor)
        if d.kind == "sales":
            lines = [{"code": _code_of(s, M, tenant, ws, "ar"), "debit_minor": net + tax, "party": d.party},
                     {"code": d.code, "credit_minor": net, "dim": d.cost_centre or ""}]
            if tax:
                lines.append({"code": _code_of(s, M, tenant, ws, "tax_out"), "credit_minor": tax})
        else:
            lines = [{"code": d.code, "debit_minor": net, "dim": d.cost_centre or ""}, {"code": _code_of(s, M, tenant, ws, "ap"), "credit_minor": net + tax, "party": d.party}]
            if tax:
                lines.append({"code": _code_of(s, M, tenant, ws, "tax_in"), "debit_minor": tax})
        d.number = d.number or _next_number(s, M, tenant, ws, d.kind, d.issue)
        post(tenant, ws, d.issue, lines, f"{'Invoice' if d.kind == 'sales' else 'Bill'} {d.number} {d.party}", d.kind if d.kind == "sales" else "bill",
             f"doc:{d.id}", actor, session=s)
        d.status = "open"
        s.commit()
        return {"id": d.id, "number": d.number, "status": "open",
                "says": "Posted to the books. Hoola does not send invoices or pay bills; you send or pay it yourself."}


def docs(tenant: str, ws: str, kind: str = "", status: str = "") -> list[dict[str, Any]]:
    db, M = _db()
    with db.session() as s:
        q = s.query(M.FinInvoice).filter(M.FinInvoice.tenant_id == tenant, M.FinInvoice.workspace_id == ws)
        if kind:
            q = q.filter(M.FinInvoice.kind == kind)
        if status:
            q = q.filter(M.FinInvoice.status == status)
        return [{"id": d.id, "kind": d.kind, "number": d.number, "party": d.party, "issue": d.issue, "due": d.due, "currency": d.currency,
                 "total": _u(d.total_minor, d.currency), "open": _u(d.total_minor - d.paid_minor, d.currency), "status": d.status,
                 "source": d.source, "cost_centre": d.cost_centre or "", "intercompany": d.ic_ws or ""} for d in q.order_by(M.FinInvoice.issue).all()]


_TOTAL = re.compile(r"(?:grand\s+)?total(?:\s+(?:due|amount|to pay))?\W{0,6}[^\d\n]{0,6}(\d[\d,]*(?:[.,]\d{2})?)", re.I)
_TAX = re.compile(r"\b(?:vat|gst|tax|mwst|ust)\b[^\n]{0,24}?(\d[\d.,]*[.,]\d{2})(?!\s*%)", re.I)
_DATE = re.compile(r"(\d{4}-\d{2}-\d{2}|\d{1,2}[/.]\d{1,2}[/.]\d{2,4})")


def _num(s: str) -> Decimal:
    s = s.strip()
    if re.search(r",\d{2}$", s) and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif re.search(r",\d{2}$", s):
        s = s.replace(",", ".")
    return Decimal(s.replace(",", ""))


def read_receipt(tenant: str, ws: str, text: str, actor: str) -> dict[str, Any]:
    """A receipt's text -> a DRAFT bill with what was read and what was not. She checks and issues it."""
    if not str(text or "").strip():
        raise BooksError("text: the receipt's words (from a photo or a PDF).")
    lines = [l.strip() for l in str(text).splitlines() if l.strip()]
    totals = [_num(m.group(1)) for m in _TOTAL.finditer(text)]
    taxes = [_num(m.group(1)) for m in _TAX.finditer(text)]
    dm = _DATE.search(text)
    day = ""
    if dm:
        raw = dm.group(1)
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%d/%m/%y", "%d.%m.%y"):
            try:
                from datetime import datetime
                day = datetime.strptime(raw, fmt).date().isoformat()
                break
            except ValueError:
                continue
    missing = [n for n, v in (("total", totals), ("date", day), ("seller", lines[:1])) if not v]
    if "total" in missing:
        raise BooksError("Hoola could not find a total on this receipt; type the amount instead.")
    total = max(totals)
    tax = taxes[-1] if taxes and taxes[-1] < total else Decimal(0)
    w = _ws(tenant, ws)
    cur = str(_book_cur(w))
    pct = float((tax / (total - tax) * 100).quantize(Decimal("0.01"))) if tax else 0.0
    out = create_doc(tenant, ws, "purchase", {"party": lines[0][:120], "issue": day or date.today().isoformat(), "currency": cur,
                                              "lines": [{"description": "From a receipt", "qty": 1, "price": str(total - tax), "tax_pct": pct}]},
                     actor, source="receipt")
    out.update(read={"seller": lines[0][:120], "date": day, "total": float(total), "tax": float(tax)},
               not_found=[m for m in missing if m != "total"], says="A draft bill: check it, then issue it to post it.")
    return out


# ---- bank lines: cash application and posting ------------------------------------------------------------------------------

def _bank_lines(tenant: str, ws: str, account: str = "", since: str = "", until: str = "") -> list[dict[str, Any]]:
    """Every bank line of the business (v0.999.159: read here with no cap - the spine's list API stops at 5,000 rows, so
    matching, reconciliation and the close check silently missed older lines on a big business)."""
    db, M = _db()
    with db.session() as s:
        q = s.query(M.FinTxn.id, M.FinTxn.day, M.FinTxn.amount_minor, M.FinTxn.narration).filter(
            M.FinTxn.tenant_id == tenant, M.FinTxn.workspace_id == ws)
        if account:
            q = q.filter(M.FinTxn.account_id == account)
        if since:
            q = q.filter(M.FinTxn.day >= since)
        if until:
            q = q.filter(M.FinTxn.day <= until)
        return [{"id": i, "day": d, "amount_minor": a, "narration": n or ""} for i, d, a, n in q.order_by(M.FinTxn.day.desc(), M.FinTxn.id).all()]


def _bank_line(tenant: str, ws: str, txn_id: str) -> dict[str, Any] | None:
    db, M = _db()
    with db.session() as s:
        t = s.get(M.FinTxn, txn_id)
        if t is None or t.tenant_id != tenant or t.workspace_id != ws:
            return None
        return {"id": t.id, "day": t.day, "amount_minor": t.amount_minor, "narration": t.narration or ""}


def _linked(s, M, tenant: str, ws: str) -> set[str]:
    return {t for (t,) in s.query(M.FinLine.txn_id).filter(M.FinLine.tenant_id == tenant, M.FinLine.workspace_id == ws,
                                                            M.FinLine.txn_id != "").all()}


def propose_matches(tenant: str, ws: str, account: str = "", limit: int = 500) -> dict[str, Any]:
    """Each unposted bank line against open documents. Confidence by rule, with the reason; a line that fits more than one
    document equally is listed as unsure and never auto-applied.
    v0.999.159: indexed (document number, amount) so 200,000 bank lines against 50,000 open documents stay seconds, not hours;
    `limit` lines come back with the full count."""
    w = _ws(tenant, ws)
    book = _book_cur(w)
    db, M = _db()
    with db.session() as s:
        done = _linked(s, M, tenant, ws)
        open_docs = s.query(M.FinInvoice).filter(M.FinInvoice.tenant_id == tenant, M.FinInvoice.workspace_id == ws,
                                                 M.FinInvoice.status == "open").all()
        od = [{"id": d.id, "kind": d.kind, "number": d.number, "party": d.party.lower(), "currency": d.currency,
               "left": d.total_minor - d.paid_minor, "book_left": int(round((d.total_minor - d.paid_minor) * d.carried_rate))
               if d.currency != book else d.total_minor - d.paid_minor} for d in open_docs]
    by_num = {d["number"].lower(): d for d in od if d["number"]}
    by_amt: dict[tuple[str, int], list] = defaultdict(list)
    foreign: dict[str, list] = defaultdict(list)
    for d in od:
        by_amt[(d["kind"], d["book_left"])].append(d)
        if d["currency"] != book:
            foreign[d["kind"]].append(d)
    num_re = re.compile(r"(?:inv|bill)-\d{4}-\d{4,}", re.I)
    words = lambda d: [x for x in d["party"].split() if len(x) > 3]   # noqa: E731
    from .household import category
    out, total = [], 0
    for t in _bank_lines(tenant, ws, account):
        if t["id"] in done:
            continue
        total += 1
        if len(out) >= limit:
            continue
        amt, nar = t["amount_minor"], t["narration"].lower()
        want = "sales" if amt > 0 else "purchase"
        cands, seen = [], set()
        for m in num_re.findall(nar):
            d = by_num.get(m.lower())
            if d and d["kind"] == want and d["id"] not in seen:
                cands.append((0.97, d, f"invoice number {d['number']} is in the bank line"))
                seen.add(d["id"])
        for d in by_amt.get((want, abs(amt)), []):
            if d["id"] in seen:
                continue
            seen.add(d["id"])
            if d["party"] and any(x in nar for x in words(d)):
                cands.append((0.9, d, f"same amount and the name {d['party']}"))
            else:
                cands.append((0.6, d, "same amount only"))
        for d in foreign.get(want, []):
            if d["id"] not in seen and d["party"] and any(x in nar for x in words(d)) \
                    and abs(abs(amt) - d["book_left"]) <= 0.1 * d["book_left"]:
                seen.add(d["id"])
                cands.append((0.8, d, f"the name {d['party']}; the amount differs by the exchange rate"))
        cands.sort(key=lambda c: -c[0])
        if cands and (len(cands) == 1 or cands[0][0] > cands[1][0]):
            c, d, why = cands[0]
            out.append({"txn": t["id"], "day": t["day"], "amount": _u(amt, book), "narration": t["narration"][:80], "doc": d["id"],
                        "number": d["number"], "confidence": c, "why": why, "sure": c >= 0.9})
        elif cands:
            out.append({"txn": t["id"], "day": t["day"], "amount": _u(amt, book), "narration": t["narration"][:80], "doc": None,
                        "confidence": cands[0][0], "why": f"fits {len(cands)} documents equally - choose one", "sure": False,
                        "choices": [c[1]["number"] for c in cands if c[0] == cands[0][0]]})
        else:
            cat = category(t["narration"], amt)
            out.append({"txn": t["id"], "day": t["day"], "amount": _u(amt, book), "narration": t["narration"][:80], "doc": None,
                        "propose_account": PROPOSE.get(cat, "9999"), "why": f"no document; looks like {cat.replace('_', ' ')}", "sure": False})
    return {"currency": book, "lines": out, "total": total, "more": max(0, total - len(out)),
            "says": "Nothing is posted until you confirm. Unsure lines need your choice."}


def apply_match(tenant: str, ws: str, txn_id: str, doc_id: str, actor: str) -> dict[str, Any]:
    """Her confirm: the bank line pays (part of) the document; any exchange difference goes to the FX account."""
    w = _ws(tenant, ws)
    book = _book_cur(w)
    t = _bank_line(tenant, ws, txn_id)
    if not t:
        raise BooksError("No such bank line.")
    db, M = _db()
    with db.session() as s:
        if txn_id in _linked(s, M, tenant, ws):
            raise BooksError("That bank line is already in the books.")
        d = s.get(M.FinInvoice, doc_id)
        if not d or d.tenant_id != tenant or d.workspace_id != ws or d.status != "open":
            raise BooksError("No such open document.")
        if (d.kind == "sales") != (t["amount_minor"] > 0):
            raise BooksError("Money in pays an invoice; money out pays a bill.")
        bank, ctrl = _code_of(s, M, tenant, ws, "bank"), _code_of(s, M, tenant, ws, "ar" if d.kind == "sales" else "ap")
        paid_book = abs(t["amount_minor"])
        left = d.total_minor - d.paid_minor
        if d.currency == book:
            if paid_book > left:
                raise BooksError(f"The payment is more than the {_u(left, book)} still open.")
            settled_doc, carried = paid_book, paid_book
            fx = 0
        else:   # a foreign document is settled in full by one bank line
            settled_doc, carried = left, int(round(left * d.carried_rate))
            fx = paid_book - carried                                  # + = more book money than carried
        fxc = _code_of(s, M, tenant, ws, "fx")
        if d.kind == "sales":
            lines = [{"code": bank, "debit_minor": paid_book, "txn_id": txn_id}, {"code": ctrl, "credit_minor": carried, "party": d.party}]
            if fx > 0:
                lines.append({"code": fxc, "credit_minor": fx})
            elif fx < 0:
                lines.append({"code": fxc, "debit_minor": -fx})
        else:
            lines = [{"code": ctrl, "debit_minor": carried, "party": d.party}, {"code": bank, "credit_minor": paid_book, "txn_id": txn_id}]
            if fx > 0:
                lines.append({"code": fxc, "debit_minor": fx})
            elif fx < 0:
                lines.append({"code": fxc, "credit_minor": -fx})
        post(tenant, ws, t["day"], lines, f"Payment {d.number} {d.party}", "payment", f"txn:{txn_id}", actor, session=s)
        d.paid_minor += settled_doc
        if d.paid_minor >= d.total_minor:
            d.status = "paid"
        s.commit()
        gain = (fx if d.kind == "sales" else -fx)
        return {"doc": d.number, "status": d.status, "open": _u(d.total_minor - d.paid_minor, d.currency),
                "fx_gain": _u(gain, book) if fx else 0.0}


def post_bank_line(tenant: str, ws: str, txn_id: str, code: str, actor: str, cost_centre: str = "") -> dict[str, Any]:
    """A bank line with no document, posted to the account she picked."""
    t = _bank_line(tenant, ws, txn_id)
    if not t:
        raise BooksError("No such bank line.")
    ensure_coa(tenant, ws)
    db, M = _db()
    with db.session() as s:
        bank = _code_of(s, M, tenant, ws, "bank")
        a = abs(t["amount_minor"])
        dim = _cc(tenant, ws, cost_centre)
        lines = ([{"code": bank, "debit_minor": a, "txn_id": txn_id}, {"code": str(code), "credit_minor": a, "dim": dim}] if t["amount_minor"] > 0 else
                 [{"code": str(code), "debit_minor": a, "dim": dim}, {"code": bank, "credit_minor": a, "txn_id": txn_id}])
        jid = post(tenant, ws, t["day"], lines, t["narration"][:200], "bank", f"txn:{txn_id}", actor, session=s)
        s.commit()
        return {"journal": jid, "account": code}


def reconcile(tenant: str, ws: str, period: str, statement_balance: Any = None) -> dict[str, Any]:
    """Bank (the imported statement) vs books (the bank account) for one month."""
    w = _ws(tenant, ws)
    book = _book_cur(w)
    db, M = _db()
    with db.session() as s:
        bank = _code_of(s, M, tenant, ws, "bank")
        linked = _linked(s, M, tenant, ws)
        rows = s.query(M.FinLine, M.FinJournal).join(M.FinJournal, M.FinJournal.id == M.FinLine.journal_id) \
            .filter(M.FinLine.tenant_id == tenant, M.FinLine.workspace_id == ws, M.FinLine.code == bank).all()
        book_only = [{"journal": j.id, "day": j.day, "memo": j.memo, "amount": _u(l.debit_minor - l.credit_minor, book)}
                     for l, j in rows if not l.txn_id and j.period == period]
        book_bal = sum(l.debit_minor - l.credit_minor for l, j in rows if j.day[:7] <= period)
    lines = _bank_lines(tenant, ws, since=f"{period}-01", until=f"{period}-31")
    bank_only = [{"txn": t["id"], "day": t["day"], "amount": _u(t["amount_minor"], book), "narration": t["narration"][:80]}
                 for t in lines if t["id"] not in linked]
    matched = len(lines) - len(bank_only)
    stmt = _m(statement_balance, book) if statement_balance not in (None, "") else \
        sum(t["amount_minor"] for t in _bank_lines(tenant, ws, until=f"{period}-31"))
    diff = stmt - book_bal
    explained = sum(_m(x["amount"], book) for x in bank_only) - sum(_m(x["amount"], book) for x in book_only)
    return {"period": period, "currency": book, "bank_lines": len(lines), "matched": matched, "bank_only": bank_only, "book_only": book_only,
            "statement_balance": _u(stmt, book), "book_balance": _u(book_bal, book), "difference": _u(diff, book),
            "unexplained": _u(diff - explained, book), "reconciled": not bank_only and not book_only and diff == 0}


# ---- ageing, assets, inventory, currency -------------------------------------------------------------------------------------

BUCKETS = (("not_due", None, 0), ("1_30", 1, 30), ("31_60", 31, 60), ("61_90", 61, 90), ("over_90", 91, None))


def ageing(tenant: str, ws: str, kind: str, as_of: str) -> dict[str, Any]:
    as_of = _day(as_of, "as_of")
    ref = date.fromisoformat(as_of)
    w = _ws(tenant, ws)
    book = _book_cur(w)
    db, M = _db()
    tot: dict[str, int] = defaultdict(int)
    by_party: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    with db.session() as s:
        for d in s.query(M.FinInvoice).filter(M.FinInvoice.tenant_id == tenant, M.FinInvoice.workspace_id == ws,
                                              M.FinInvoice.kind == kind, M.FinInvoice.status == "open", M.FinInvoice.issue <= as_of):
            left = d.total_minor - d.paid_minor
            left = int(round(left * d.carried_rate)) if d.currency != book else left
            late = (ref - date.fromisoformat(d.due)).days
            b = next(n for n, lo, hi in BUCKETS if (lo is None and late <= hi) or (lo is not None and late >= lo and (hi is None or late <= hi)))
            tot[b] += left
            by_party[d.party][b] += left
    return {"kind": kind, "as_of": as_of, "currency": book, "buckets": {n: _u(tot[n], book) for n, _, _ in BUCKETS},
            "total": _u(sum(tot.values()), book),
            "by_party": {p: {n: _u(v[n], book) for n, _, _ in BUCKETS} for p, v in sorted(by_party.items())}}


def _months_between(a: str, b: str) -> int:
    return (int(b[:4]) - int(a[:4])) * 12 + int(b[5:7]) - int(a[5:7])


def asset_add(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _ws(tenant, ws)
    cur = _book_cur(w)
    start = str(a.get("start") or "")[:7]
    if not re.fullmatch(r"\d{4}-\d{2}", start) or not a.get("name") or not a.get("cost"):
        raise BooksError("asset: name, cost, start (YYYY-MM), life_months or method reducing + rate_pct, salvage.")
    method = str(a.get("method") or "straight")
    if method not in ("straight", "reducing") or (method == "reducing" and not a.get("rate_pct")):
        raise BooksError("method: straight | reducing (with rate_pct a year).")
    db, M = _db()
    with db.session() as s:
        x = M.FinAsset(tenant_id=tenant, workspace_id=ws, name=str(a["name"])[:160], cost_minor=_m(a["cost"], cur),
                       salvage_minor=_m(a.get("salvage") or 0, cur), start=start, life_months=int(a.get("life_months") or 36),
                       method=method, rate_pct=float(a.get("rate_pct") or 0))
        s.add(x)
        s.commit()
        return {"id": x.id, "name": x.name}


def dep_for(x, period: str) -> int:
    """One month's depreciation in minor units (0 before the start or once fully depreciated)."""
    n = _months_between(x.start, period)
    if n < 0:
        return 0
    base = x.cost_minor - x.salvage_minor
    if x.method == "straight":
        if n >= x.life_months:
            return 0
        per = base // x.life_months
        return base - per * (x.life_months - 1) if n == x.life_months - 1 else per   # the last month takes the rounding
    bv = x.cost_minor
    for _ in range(n):
        bv -= int(round(bv * x.rate_pct / 100 / 12))
    return max(0, min(int(round(bv * x.rate_pct / 100 / 12)), bv - x.salvage_minor))


def post_depreciation(tenant: str, ws: str, period: str, actor: str) -> dict[str, Any]:
    if not re.fullmatch(r"\d{4}-\d{2}", str(period)):
        raise BooksError("period: YYYY-MM.")
    ensure_coa(tenant, ws)
    db, M = _db()
    done, total = [], 0
    with db.session() as s:
        dep, acc = _code_of(s, M, tenant, ws, "dep"), _code_of(s, M, tenant, ws, "accum_dep")
        for x in s.query(M.FinAsset).filter(M.FinAsset.tenant_id == tenant, M.FinAsset.workspace_id == ws).all():
            amt = dep_for(x, period)
            ref = f"dep:{x.id}:{period}"
            if amt <= 0 or s.query(M.FinJournal).filter(M.FinJournal.tenant_id == tenant, M.FinJournal.workspace_id == ws,
                                                        M.FinJournal.source_ref == ref).first():
                continue
            last = f"{period}-28"
            post(tenant, ws, last, [{"code": dep, "debit_minor": amt}, {"code": acc, "credit_minor": amt}], f"Depreciation {x.name} {period}",
                 "depreciation", ref, actor, session=s)
            done.append(x.name)
            total += amt
        s.commit()
    cur = _book_cur(_ws(tenant, ws))
    return {"period": period, "assets": done, "amount": _u(total, cur)}


def inventory_cost(a: dict[str, Any]) -> dict[str, Any]:
    """Her stock movements [{day, qty (+ in / - out), unit_cost (for ins)}] -> cost of what went out, what is left. FIFO or average."""
    method = str(a.get("method") or "fifo")
    if method not in ("fifo", "average"):
        raise BooksError("method: fifo | average.")
    layers: list[list[Decimal]] = []
    qty_avg, cost_avg = Decimal(0), Decimal(0)
    cogs = Decimal(0)
    for mv in sorted(a.get("movements") or [], key=lambda x: str(x.get("day"))):
        q = Decimal(str(mv.get("qty") or 0))
        if q > 0:
            c = Decimal(str(mv.get("unit_cost") or 0))
            layers.append([q, c])
            qty_avg, cost_avg = qty_avg + q, cost_avg + q * c
        elif q < 0:
            out = -q
            if method == "average":
                if out > qty_avg:
                    raise BooksError(f"More goes out ({out}) than is in stock ({qty_avg}) on {mv.get('day')}.")
                unit = cost_avg / qty_avg
                cogs += out * unit
                qty_avg, cost_avg = qty_avg - out, cost_avg - out * unit
            else:
                if out > sum(l[0] for l in layers):
                    raise BooksError(f"More goes out ({out}) than is in stock on {mv.get('day')}.")
                while out > 0:
                    take = min(out, layers[0][0])
                    cogs += take * layers[0][1]
                    layers[0][0] -= take
                    out -= take
                    if layers[0][0] == 0:
                        layers.pop(0)
                qty_avg = sum(l[0] for l in layers)
                cost_avg = sum(l[0] * l[1] for l in layers)
    return {"method": method, "cost_of_goods_out": float(cogs.quantize(Decimal("0.01"))), "qty_left": float(qty_avg),
            "value_left": float(cost_avg.quantize(Decimal("0.01")))}


def revalue(tenant: str, ws: str, period: str, rates: list[dict[str, Any]], actor: str) -> dict[str, Any]:
    """Month end: open foreign documents to the closing rate she gives (each with its date and source)."""
    w = _ws(tenant, ws)
    book = _book_cur(w)
    r = {str(x.get("currency", "")).upper(): x for x in rates or []}
    db, M = _db()
    moves, total = [], 0
    with db.session() as s:
        ar, ap, fxc = _code_of(s, M, tenant, ws, "ar"), _code_of(s, M, tenant, ws, "ap"), _code_of(s, M, tenant, ws, "fx")
        for d in s.query(M.FinInvoice).filter(M.FinInvoice.tenant_id == tenant, M.FinInvoice.workspace_id == ws,
                                              M.FinInvoice.status == "open", M.FinInvoice.currency != book).all():
            x = r.get(d.currency)
            if not x or not x.get("rate") or not x.get("date") or not x.get("source"):
                raise BooksError(f"A closing {d.currency} rate with its date and source is needed.")
            left = d.total_minor - d.paid_minor
            diff = int(round(left * float(x["rate"]))) - int(round(left * d.carried_rate))
            if diff == 0:
                continue
            gain = diff if d.kind == "sales" else -diff
            ctrl = ar if d.kind == "sales" else ap
            lines = ([{"code": ctrl, "debit_minor": diff}, {"code": fxc, "credit_minor": diff}] if diff > 0 else
                     [{"code": fxc, "debit_minor": -diff}, {"code": ctrl, "credit_minor": -diff}])
            if d.kind == "purchase":
                lines = ([{"code": fxc, "debit_minor": diff}, {"code": ctrl, "credit_minor": diff}] if diff > 0 else
                         [{"code": ctrl, "debit_minor": -diff}, {"code": fxc, "credit_minor": -diff}])
            post(tenant, ws, f"{period}-28", lines, f"Revaluation {d.number} at {x['rate']} ({x['source']})", "reval",
                 f"reval:{d.id}:{period}", actor, session=s)
            d.carried_rate = float(x["rate"])
            moves.append({"doc": d.number, "gain": _u(gain, book)})
            total += gain
        s.commit()
    return {"period": period, "revalued": moves, "gain": _u(total, book)}


# ---- reports, close, exports ----------------------------------------------------------------------------------------------

def balances(tenant: str, ws: str, upto: str = "", since: str = "") -> dict[str, int]:
    db, M = _db()
    with db.session() as s:
        q = s.query(M.FinLine, M.FinJournal).join(M.FinJournal, M.FinJournal.id == M.FinLine.journal_id) \
            .filter(M.FinLine.tenant_id == tenant, M.FinLine.workspace_id == ws)
        out: dict[str, int] = defaultdict(int)
        for l, j in q.all():
            if (upto and j.day > upto) or (since and j.day < since):
                continue
            out[l.code] += l.debit_minor - l.credit_minor
        return dict(out)


def reports(tenant: str, ws: str, since: str, upto: str) -> dict[str, Any]:
    w = _ws(tenant, ws)
    book = _book_cur(w)
    chart = {c["code"]: c for c in coa(tenant, ws)}
    all_ = balances(tenant, ws, upto=upto)
    per = balances(tenant, ws, upto=upto, since=since)
    tb = [{"code": c, "name": chart[c]["name"], "debit": _u(max(v, 0), book), "credit": _u(max(-v, 0), book)} for c, v in sorted(all_.items()) if v]
    inc = -sum(v for c, v in per.items() if chart[c]["type"] == "income")
    exp = sum(v for c, v in per.items() if chart[c]["type"] == "expense")
    earn = -sum(v for c, v in all_.items() if chart[c]["type"] in ("income", "expense"))
    side = lambda t: sum(v for c, v in all_.items() if chart[c]["type"] == t)   # noqa: E731
    assets, liab, eq = side("asset"), -side("liability"), -side("equity") + earn
    return {"currency": book, "trial_balance": tb, "balanced": sum(all_.values()) == 0,
            "profit_and_loss": {"from": since, "to": upto, "income": _u(inc, book), "expenses": _u(exp, book), "profit": _u(inc - exp, book)},
            "balance_sheet": {"as_of": upto, "assets": _u(assets, book), "liabilities": _u(liab, book), "equity": _u(eq, book),
                              "checks": assets == liab + eq}}


def close_checklist(tenant: str, ws: str, period: str) -> dict[str, Any]:
    if not re.fullmatch(r"\d{4}-\d{2}", str(period)):
        raise BooksError("period: YYYY-MM.")
    _ws(tenant, ws)
    ensure_coa(tenant, ws)
    db, M = _db()
    w = _ws(tenant, ws)
    book = _book_cur(w)
    with db.session() as s:
        linked = _linked(s, M, tenant, ws)
        drafts = s.query(M.FinInvoice).filter(M.FinInvoice.tenant_id == tenant, M.FinInvoice.workspace_id == ws,
                                              M.FinInvoice.status == "draft", M.FinInvoice.issue <= f"{period}-31").count()
        assets = s.query(M.FinAsset).filter(M.FinAsset.tenant_id == tenant, M.FinAsset.workspace_id == ws).all()
        dep_missing = [x.name for x in assets if dep_for(x, period) > 0 and not s.query(M.FinJournal).filter(
            M.FinJournal.tenant_id == tenant, M.FinJournal.workspace_id == ws, M.FinJournal.source_ref == f"dep:{x.id}:{period}").first()]
        foreign = s.query(M.FinInvoice).filter(M.FinInvoice.tenant_id == tenant, M.FinInvoice.workspace_id == ws,
                                               M.FinInvoice.status == "open", M.FinInvoice.currency != book).all()
        reval_missing = [d.number for d in foreign if not s.query(M.FinJournal).filter(
            M.FinJournal.tenant_id == tenant, M.FinJournal.workspace_id == ws, M.FinJournal.source_ref == f"reval:{d.id}:{period}").first()
            and d.issue[:7] <= period]
        sus = _code_of(s, M, tenant, ws, "suspense")
    unposted = [t for t in _bank_lines(tenant, ws, since=f"{period}-01", until=f"{period}-31") if t["id"] not in linked]
    bal = balances(tenant, ws, upto=f"{period}-31")
    items = [
        {"item": "Every bank line of the month is in the books", "ok": not unposted, "count": len(unposted)},
        {"item": "No draft invoices or bills dated in or before the month", "ok": drafts == 0, "count": drafts},
        {"item": "Depreciation posted for the month", "ok": not dep_missing, "count": len(dep_missing), "which": dep_missing},
        {"item": "Open foreign-currency documents revalued", "ok": not reval_missing, "count": len(reval_missing), "which": reval_missing},
        {"item": "Suspense account is empty", "ok": bal.get(sus, 0) == 0, "amount": _u(bal.get(sus, 0), book)},
        {"item": "The trial balance balances", "ok": sum(bal.values()) == 0},
    ]
    h = hashlib.sha256(json.dumps({"p": period, "items": items}, sort_keys=True, default=str).encode()).hexdigest()
    return {"period": period, "items": items, "ready": all(i["ok"] for i in items), "hash": h, "locked": locked(tenant, ws, period)}


def lock(tenant: str, ws: str, period: str, hash: str, actor: str, exceptions: str = "") -> dict[str, Any]:
    """Her confirm of the checklist she saw (its hash). Items not ready need her reason in writing."""
    ck = close_checklist(tenant, ws, period)
    if ck["locked"]:
        raise BooksError(f"{period} is already locked.")
    if hash != ck["hash"]:
        raise BooksError("The books changed since the checklist was shown; look at it again.")
    if not ck["ready"] and len(str(exceptions or "").strip()) < 10:
        raise BooksError("Some items are not done. Fix them, or write why you are closing anyway (exceptions).")
    from ..profile import approval_for
    db, M = _db()
    with db.session() as s:
        s.add(M.FinPeriod(tenant_id=tenant, workspace_id=ws, period=period, locked_by=actor, exceptions=str(exceptions or "")[:2000], hash=hash))
        s.commit()
    from .. import evidence as EV
    EV.record(tenant, ws, actor, "close", f"locked {period}", {"hash": hash, "exceptions": exceptions})
    return {"period": period, "locked": True, "approval": approval_for(_ws(tenant, ws), "close")}


def export(tenant: str, ws: str, fmt: str, since: str, upto: str) -> dict[str, Any]:
    w = _ws(tenant, ws)
    book = _book_cur(w)
    chart = {c["code"]: c["name"] for c in coa(tenant, ws)}
    db, M = _db()
    with db.session() as s:
        js = s.query(M.FinJournal).filter(M.FinJournal.tenant_id == tenant, M.FinJournal.workspace_id == ws,
                                          M.FinJournal.day >= since, M.FinJournal.day <= upto).order_by(M.FinJournal.day).all()
        lines = defaultdict(list)
        for l in s.query(M.FinLine).filter(M.FinLine.journal_id.in_([j.id for j in js])).all():
            lines[l.journal_id].append(l)
    buf = io.StringIO()
    wr = csv.writer(buf)
    if fmt == "csv":
        wr.writerow(["Date", "Journal", "Account code", "Account", "Debit", "Credit", "Memo"])
        for j in js:
            for l in lines[j.id]:
                wr.writerow([j.day, j.id, l.code, chart.get(l.code, ""), _u(l.debit_minor, book) or "", _u(l.credit_minor, book) or "", j.memo])
    elif fmt == "xero":
        wr.writerow(["*Narration", "*Date", "Description", "*AccountCode", "*TaxRate", "*Amount"])
        for j in js:
            for l in lines[j.id]:
                wr.writerow([j.memo or j.id, j.day, chart.get(l.code, ""), l.code, "Tax Exempt", _u(l.debit_minor - l.credit_minor, book)])
    elif fmt == "quickbooks":
        wr.writerow(["Journal No", "Journal Date", "Account", "Debits", "Credits", "Description", "Name"])
        for n, j in enumerate(js, 1):
            for l in lines[j.id]:
                wr.writerow([n, j.day, chart.get(l.code, l.code), _u(l.debit_minor, book) or "", _u(l.credit_minor, book) or "", j.memo, l.party])
    elif fmt == "tally":
        from ...bahi import book as BK
        vs = [{"type": "Journal", "date": j.day, "number": j.id[-8:], "party": "", "narration": j.memo,
               "rows": [(chart.get(l.code, l.code), _u(l.debit_minor or l.credit_minor, book), bool(l.debit_minor)) for l in lines[j.id]]}
              for j in js]
        return {"format": fmt, "text": BK.to_xml(vs), "journals": len(js),
                "says": "Tally import XML. Your Tally ledger names must match the account names."}
    else:
        raise BooksError("format: csv | xero | quickbooks | tally.")
    return {"format": fmt, "text": buf.getvalue(), "journals": len(js),
            "says": "An import file in the column layout that system's manual import uses; check it in a test company first."}


# ---- the tool's entry ------------------------------------------------------------------------------------------------------

ACTIONS = ("chart", "add_account", "journal", "invoice", "bill", "issue", "documents", "receipt", "matches", "apply_match", "post_bank",
           "reconcile", "ageing", "asset", "depreciation", "inventory", "revalue", "reports", "close_check", "close_lock", "export")


def run(tenant: str, action: str, a: dict[str, Any], actor: str = "owner") -> dict[str, Any]:
    """The one door (tool, routes, desk). v0.999.159: with the business's controls on, a posting goes to a second person
    (books_ent) instead of the books; only books_ent.approve runs it, through _exec."""
    a = {k: v for k, v in (a or {}).items() if not str(k).startswith("_")}     # nothing from outside may claim an approval
    ws = str(a.get("workspace") or "")
    if ws and action != "inventory":
        from . import books_ent as E
        held = E.hold(tenant, ws, action, a, actor)
        if held is not None:
            return held
    return _exec(tenant, action, a, actor)


def _exec(tenant: str, action: str, a: dict[str, Any], actor: str = "owner") -> dict[str, Any]:
    if action == "inventory":
        return inventory_cost(a)
    ws = str(a.get("workspace") or "")
    if not ws:
        raise BooksError("workspace: the finance workspace these books belong to.")
    p = str(a.get("period") or "")
    f = {"chart": lambda: {"accounts": coa(tenant, ws)},
         "add_account": lambda: add_account(tenant, ws, str(a.get("code") or ""), str(a.get("name") or ""), str(a.get("type") or "")),
         "journal": lambda: journal_entry(tenant, ws, a, actor),
         "invoice": lambda: create_doc(tenant, ws, "sales", a, actor),
         "bill": lambda: create_doc(tenant, ws, "purchase", a, actor),
         "issue": lambda: issue_doc(tenant, ws, str(a.get("doc") or ""), actor),
         "documents": lambda: {"documents": docs(tenant, ws, str(a.get("kind") or ""), str(a.get("status") or ""))},
         "receipt": lambda: read_receipt(tenant, ws, str(a.get("text") or ""), actor),
         "matches": lambda: propose_matches(tenant, ws, str(a.get("account") or ""), int(a.get("limit") or 500)),
         "apply_match": lambda: apply_match(tenant, ws, str(a.get("txn") or ""), str(a.get("doc") or ""), actor),
         "post_bank": lambda: post_bank_line(tenant, ws, str(a.get("txn") or ""), str(a.get("code") or ""), actor, str(a.get("cost_centre") or "")),
         "reconcile": lambda: reconcile(tenant, ws, p, a.get("statement_balance")),
         "ageing": lambda: ageing(tenant, ws, "purchase" if a.get("kind") == "payables" else "sales", str(a.get("as_of") or date.today())),
         "asset": lambda: asset_add(tenant, ws, a),
         "depreciation": lambda: post_depreciation(tenant, ws, p, actor),
         "revalue": lambda: revalue(tenant, ws, p, a.get("rates") or [], actor),
         "reports": lambda: reports(tenant, ws, str(a.get("since") or "0000-01-01"), str(a.get("upto") or date.today())),
         "close_check": lambda: close_checklist(tenant, ws, p),
         "close_lock": lambda: lock(tenant, ws, p, str(a.get("hash") or ""), actor, str(a.get("exceptions") or "")),
         "export": lambda: export(tenant, ws, str(a.get("format") or "csv"), str(a.get("since") or "0000-01-01"), str(a.get("upto") or date.today()))}
    if action not in f:
        raise BooksError("action: " + ", ".join(ACTIONS))
    out = f[action]()
    out.setdefault("not_advice", L.NOT_ADVICE)
    return out
