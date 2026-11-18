"""v0.846 BAHI A7 - bank and UPI reconciliation, stored.

A statement she imports (CSV, Excel, MT940, or a PDF whose password she types once and Hoola never keeps) becomes stored lines. Each line is read for its
mode and reference (UPI RRN, NEFT/IMPS UTR, cheque number, payer, UPI id) and matched against the register: invoice number in the narration, a payer
Hoola learned from an earlier confirmation, or amount + a sensible date window when only ONE document fits. Every match is a PROPOSAL with a reason and a
confidence; nothing is linked until she confirms. Hoola never touches the bank: it reads statements she gives it.
NOT BUILT: fetching a gateway's settlements itself (she hands them over), a cheque register (uncleared cheques are shown as bank-only / books-only), a bank API.
NOT VERIFIED on real statements: the PDF layout reader and the narration styles are written from common formats, not from her bank.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select

from ..db import session
from . import register as REG
from .models import AccBankLearn, AccBankLine, AccBankRecon, AccDoc, ensure_tables

WINDOW_AFTER = 45          # a payment may come up to this many days after the document date
WINDOW_BEFORE = 7          # or a few days before (advance)


class BankError(Exception):
    pass


# ------------------------------------------------------------------ narration
def read_narration(n: str) -> dict[str, str]:
    """mode / reference / payer / UPI id out of the common bank narration styles. Anything it cannot read is left empty."""
    t = re.sub(r"\s+", " ", n or "").strip()
    up = t.upper()
    out = {"mode": "other", "ref": "", "payer": "", "vpa": ""}
    vpa = re.search(r"[A-Za-z0-9._]{2,}@[A-Za-z]{2,}", t)
    if vpa:
        out["vpa"] = vpa.group(0).lower()
    if up.startswith("UPI") or "/UPI/" in up or " UPI" in up:
        out["mode"] = "upi"
        rrn = re.search(r"\b(\d{12})\b", t)
        if rrn:
            out["ref"] = rrn.group(1)
        parts = [p.strip() for p in re.split(r"[/]", t) if p.strip()] if "/" in t else [p.strip() for p in t.split("-") if p.strip()]
        names = [p for p in parts[1:] if not re.fullmatch(r"\d{6,}", p) and "@" not in p and not re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", p.upper()) and len(p) > 2
                 and p.upper() not in ("UPI", "CR", "DR", "PAYMENT", "PAID", "TRANSFER")]
        out["payer"] = names[0][:80] if names else ""
    elif up.startswith(("NEFT", "RTGS", "IMPS")):
        out["mode"] = up[:4].lower() if not up.startswith("IMPS") else "imps"
        m = re.search(r"(?:NEFT|RTGS|IMPS)[\s/\-]*(?:CR|DR)?[\s/\-]*([A-Z0-9]{8,22})", up)
        if m:
            out["ref"] = m.group(1)
        name = re.split(r"[\-/]", t)
        out["payer"] = next((p.strip()[:80] for p in name[2:] if re.search(r"[A-Za-z]{3}", p) and not re.fullmatch(r"[A-Z0-9]{8,22}", p.strip())), "")
    elif re.search(r"\b(CHQ|CHEQUE|CLG|CLEARING)\b", up):
        out["mode"] = "cheque"
        m = re.search(r"(?:CHQ|CHEQUE|NO)[\s.#:\-]*(\d{5,8})", up)
        if m:
            out["ref"] = m.group(1)
    elif re.search(r"\b(POS|ECOM|CARD|ATM)\b", up):
        out["mode"] = "card" if "ATM" not in up else "cash"
    elif re.search(r"\bCASH\b|\bCDM\b", up):
        out["mode"] = "cash"
    return out


# ------------------------------------------------------------------ import
def _hash(account: str, row: dict[str, Any], nth: int) -> str:
    return hashlib.sha256(f"{account}|{row['date']}|{row['narration']}|{row['debit']}|{row['credit']}|{row.get('balance', 0)}|{nth}".encode()).hexdigest()[:32]


def parse_mt940(text: str) -> list[dict[str, Any]]:
    rows, cur = [], None
    for ln in text.splitlines():
        ln = ln.rstrip()
        m = re.match(r":61:(\d{6})(?:\d{4})?(R?[DC])([\d,]+)N\w{3}(.*)", ln)
        if m:
            d, dc, amt, rest = m.groups()
            try:
                day = datetime.strptime(d, "%y%m%d").date().isoformat()
            except ValueError:
                cur = None
                continue
            a = float(amt.replace(",", "."))
            cur = {"date": day, "narration": rest.strip(), "debit": a if dc.endswith("D") else 0.0, "credit": a if dc.endswith("C") else 0.0, "balance": 0.0}
            rows.append(cur)
        elif ln.startswith(":86:") and cur is not None:
            cur["narration"] = (cur["narration"] + " " + ln[4:]).strip()
        elif cur is not None and ln and not ln.startswith(":"):
            cur["narration"] = (cur["narration"] + " " + ln).strip()
        elif ln.startswith(":"):
            cur = cur if ln.startswith(":86:") else None
    return rows


def parse_pdf(data: bytes, password: str = "") -> list[dict[str, Any]]:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise BankError("PDF reading is not installed on this server.") from e
    rd = PdfReader(io.BytesIO(data))
    if rd.is_encrypted:
        if not password:
            raise BankError("This PDF is password-protected. Type its password (Hoola uses it once and keeps nothing).")
        if not rd.decrypt(password):
            raise BankError("That password did not open the PDF.")
    text = "\n".join((p.extract_text() or "") for p in rd.pages[:60])
    rows, prev = [], None
    pat = re.compile(r"^\s*(\d{2}[/\-]\d{2}[/\-]\d{2,4}|\d{2}\s[A-Za-z]{3}\s\d{4})\s+(.+?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*(Cr|Dr|CR|DR)?\s*$")
    from ..finguard.statement import _day
    for ln in text.splitlines():
        m = pat.match(ln)
        if not m:
            continue
        d, narr, amt, bal = m.group(1), m.group(2), float(m.group(3).replace(",", "")), float(m.group(4).replace(",", ""))
        day = _day(d)
        if not day:
            continue
        credit = prev is not None and bal > prev
        if prev is None:
            credit = bool(re.search(r"(?i)\bcr\b|credit|received|deposit|by ", narr))
        rows.append({"date": day, "narration": narr, "debit": 0.0 if credit else amt, "credit": amt if credit else 0.0, "balance": bal})
        prev = bal
    return rows


def parse_any(name: str, data: bytes, password: str = "") -> list[dict[str, Any]]:
    from ..finguard import statement as ST
    low = (name or "").lower()
    if low.endswith(".pdf") or data[:4] == b"%PDF":
        rows = parse_pdf(data, password)
    elif low.endswith((".xlsx", ".xlsm")):
        try:
            import openpyxl
        except ImportError as e:
            raise BankError("Excel reading is not installed on this server - export the statement as CSV.") from e
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        buf = io.StringIO()
        w = csv.writer(buf)
        for r in wb.worksheets[0].iter_rows(values_only=True):
            w.writerow(["" if c is None else (c.strftime("%d-%m-%Y") if hasattr(c, "strftime") else c) for c in r])
        rows = ST.parse_csv(buf.getvalue())
    else:
        text = data.decode("utf-8-sig", errors="replace")
        if ":61:" in text:
            rows = parse_mt940(text)
        else:
            try:
                rows = ST.parse_csv(text)
            except ValueError as e:
                raise BankError(str(e)) from None
    if not rows:
        raise BankError("No transactions could be read from that statement.")
    return rows


def import_rows(tenant: str, account: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    ensure_tables()
    seen: dict[tuple, int] = {}
    added = dup = 0
    with session() as s:
        have = {h for (h,) in s.execute(select(AccBankLine.line_hash).where(AccBankLine.tenant_id == tenant)).all()}
        for r in rows:
            row = {"date": r["date"], "narration": re.sub(r"\s+", " ", str(r.get("narration") or "")).strip()[:200], "debit": round(abs(float(r.get("debit") or 0)), 2),
                   "credit": round(abs(float(r.get("credit") or 0)), 2), "balance": round(float(r.get("balance") or 0), 2)}
            key = (row["date"], row["narration"], row["debit"], row["credit"], row["balance"])
            nth = seen[key] = seen.get(key, 0) + 1
            h = _hash(account, row, nth)
            if h in have:
                dup += 1
                continue
            info = read_narration(row["narration"])
            s.add(AccBankLine(tenant_id=tenant, account=account[:40], line_hash=h, mode=info["mode"], ref=info["ref"], payer=info["payer"], vpa=info["vpa"], **row))
            have.add(h)
            added += 1
        REG._event(s, tenant, "bank_imported", account or "bank", after={"added": added, "already_there": dup}, actor="owner")
        s.commit()
    return {"read": len(rows), "added": added, "already_there": dup,
            "from": min((r["date"] for r in rows), default=""), "to": max((r["date"] for r in rows), default="")}


def import_text(tenant: str, account: str, name: str, data: bytes, password: str = "") -> dict[str, Any]:
    return import_rows(tenant, account or "bank", parse_any(name, data, password))


def import_file(tenant: str, account: str, file_id: str, password: str = "") -> dict[str, Any]:
    from ..gstp.service import GstError, _load_file
    try:
        name, data = _load_file(tenant, file_id)
    except GstError as e:
        raise BankError(str(e)) from None
    return import_text(tenant, account, name, data, password)


# ------------------------------------------------------------------ matching
def _norm(n: str) -> str:
    s = re.sub(r"[^A-Z0-9]", "", str(n or "").upper())
    return re.sub(r"(?<![0-9])0+(?=\d)", "", s)


def _tokens(name: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{3,}", (name or "").lower()) if w not in ("pvt", "ltd", "private", "limited", "and", "the", "traders", "enterprises", "co")}


def _days(a: str, b: str) -> int:
    try:
        return (date.fromisoformat(a) - date.fromisoformat(b)).days
    except ValueError:
        return 9999


def match(tenant: str, month: str = "") -> dict[str, Any]:
    """Propose matches for open lines. Credits go to sales documents, debits to purchases. Nothing is linked yet."""
    ensure_tables()
    with session() as s:
        q = select(AccBankLine).where(AccBankLine.tenant_id == tenant, AccBankLine.status.in_(("open", "proposed")))
        if month:
            q = q.where(AccBankLine.date.like(month + "%"))
        lines = s.scalars(q.order_by(AccBankLine.date)).all()
        docs = s.scalars(select(AccDoc).where(AccDoc.tenant_id == tenant, AccDoc.status != "gone", AccDoc.total > 0)).all()
        taken = {l.match_doc_id for l in s.scalars(select(AccBankLine).where(AccBankLine.tenant_id == tenant, AccBankLine.status == "matched")).all()}
        learn = {r.key: r for r in s.scalars(select(AccBankLearn).where(AccBankLearn.tenant_id == tenant, AccBankLearn.kind == "vpa")).all()}
        used: set[str] = set(taken)
        n = 0
        for l in lines:
            credit = l.credit > 0
            amt = l.credit if credit else l.debit
            pool = [d for d in docs if d.id not in used and d.direction == ("out" if credit else "in") and d.kind in ("inv", "bill", "dn")]
            cand = [d for d in pool if abs((d.total or 0) - amt) <= 1.0 and -WINDOW_BEFORE <= _days(l.date, d.doc_date) <= WINDOW_AFTER]
            kind, reason, conf, pick = "", "", 0.0, None
            nar = _norm(l.narration)
            for d in cand:                                                 # 1: the invoice number is in the narration
                if d.number and len(_norm(d.number)) >= 3 and _norm(d.number) in nar:
                    kind, pick, conf, reason = "invoice_no", d, 0.97, f"The narration carries invoice {d.number} and the amount (Rs {amt:g}) is the same."
                    break
            if pick is None and l.vpa in learn:                            # 2: a payer you confirmed before
                who = learn[l.vpa]
                hit = [d for d in cand if (who.party_gstin and d.party_gstin == who.party_gstin) or (who.party_name and _tokens(who.party_name) & _tokens(d.party_name))]
                if len(hit) == 1:
                    kind, pick, conf, reason = "known_payer", hit[0], 0.92, f"{l.vpa} is {who.party_name} (confirmed earlier), and invoice {hit[0].number} is for Rs {amt:g}."
            if pick is None and l.payer:                                   # 3: payer name matches the party and the amount fits
                hit = [d for d in cand if _tokens(l.payer) & _tokens(d.party_name)]
                if len(hit) == 1:
                    kind, pick, conf, reason = "name_amount", hit[0], 0.85, f"Payer '{l.payer}' resembles {hit[0].party_name}; invoice {hit[0].number} is the same amount (Rs {amt:g}) within the date window."
            if pick is None and len(cand) == 1:                            # 4: only one document fits
                d = cand[0]
                kind, pick, conf, reason = "amount_date", d, 0.7, f"Only one {'sale' if credit else 'purchase'} fits: invoice {d.number} for Rs {amt:g}, {abs(_days(l.date, d.doc_date))} days from the payment."
            if pick is not None:
                l.status, l.match_doc_id, l.match_kind, l.match_reason, l.match_conf = "proposed", pick.id, kind, reason, conf
                used.add(pick.id)
                n += 1
            else:
                if l.status == "proposed":
                    l.status, l.match_doc_id, l.match_kind, l.match_reason, l.match_conf = "open", "", "", "", 0.0
                if not l.category:
                    l.category = _category(s, tenant, l)
        s.commit()
    return {"proposed": n, "open": sum(1 for _ in lines) - n}


def _category(s, tenant: str, l: AccBankLine) -> str:
    from ..finguard.statement import category
    words = {r.key: r.category for r in s.scalars(select(AccBankLearn).where(AccBankLearn.tenant_id == tenant, AccBankLearn.kind == "word")).all()}
    return category(l.narration, l.credit > 0, words)


def _view(l: AccBankLine, docs: dict[str, AccDoc] | None = None) -> dict[str, Any]:
    d = (docs or {}).get(l.match_doc_id)
    return {"id": l.id, "account": l.account, "date": l.date, "narration": l.narration, "debit": l.debit, "credit": l.credit, "mode": l.mode, "ref": l.ref,
            "payer": l.payer, "vpa": l.vpa, "status": l.status, "category": l.category, "match": ({"doc_id": l.match_doc_id, "kind": l.match_kind, "reason": l.match_reason,
            "confidence": l.match_conf, "doc": f"{d.number} · {d.party_name} · Rs {d.total:g}" if d else ""} if l.match_doc_id else None),
            "settlement": json.loads(l.settlement) if l.settlement else None}


def lines(tenant: str, status: str = "", month: str = "", limit: int = 300) -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        q = select(AccBankLine).where(AccBankLine.tenant_id == tenant).order_by(AccBankLine.date.desc()).limit(limit)
        if status:
            q = q.where(AccBankLine.status == status)
        if month:
            q = q.where(AccBankLine.date.like(month + "%"))
        ls = s.scalars(q).all()
        docs = {d.id: d for d in s.scalars(select(AccDoc).where(AccDoc.id.in_([x.match_doc_id for x in ls if x.match_doc_id]))).all()} if ls else {}
        return [_view(l, docs) for l in ls]


def confirm(tenant: str, ids: list[str], min_conf: float = 0.0) -> dict[str, Any]:
    """Her tap: proposed matches become matched; a UPI payer is remembered so the next payment from them is recognised."""
    ensure_tables()
    n = 0
    with session() as s:
        for lid in ids:
            l = s.get(AccBankLine, lid)
            if l is None or l.tenant_id != tenant or l.status != "proposed" or l.match_conf < min_conf:
                continue
            if any(o.id != l.id and o.status == "matched" and o.match_doc_id == l.match_doc_id for o in
                   s.scalars(select(AccBankLine).where(AccBankLine.tenant_id == tenant, AccBankLine.match_doc_id == l.match_doc_id)).all()):
                continue                                            # one document is paid by one line here; split payments are for her to handle
            l.status = "matched"
            d = s.get(AccDoc, l.match_doc_id)
            if l.vpa and d is not None and (d.party_name or d.party_gstin) and not s.scalars(select(AccBankLearn).where(
                    AccBankLearn.tenant_id == tenant, AccBankLearn.kind == "vpa", AccBankLearn.key == l.vpa)).first():
                s.add(AccBankLearn(tenant_id=tenant, kind="vpa", key=l.vpa, party_name=d.party_name, party_gstin=d.party_gstin))
            n += 1
        REG._event(s, tenant, "bank_matched", "bank", after={"lines": n}, actor="owner")
        s.commit()
    return {"matched": n}


def unmatch(tenant: str, line_id: str) -> dict[str, Any]:
    with session() as s:
        l = s.get(AccBankLine, line_id)
        if l is None or l.tenant_id != tenant:
            raise BankError("That line was not found.")
        l.status, l.match_doc_id, l.match_kind, l.match_reason, l.match_conf = "open", "", "", "", 0.0
        s.commit()
    return {"id": line_id, "status": "open"}


def categorise(tenant: str, line_id: str, category: str, remember: bool = True) -> dict[str, Any]:
    category = re.sub(r"[^a-z_ ]", "", (category or "").lower()).strip()[:40]
    if not category:
        raise BankError("Give a category.")
    with session() as s:
        l = s.get(AccBankLine, line_id)
        if l is None or l.tenant_id != tenant:
            raise BankError("That line was not found.")
        l.category = category
        if remember:
            word = (re.sub(r"\d{3,}", " ", l.narration).split() or [""])[:2]
            key = " ".join(word).lower()[:60]
            if len(key) >= 4 and not s.scalars(select(AccBankLearn).where(AccBankLearn.tenant_id == tenant, AccBankLearn.kind == "word", AccBankLearn.key == key)).first():
                s.add(AccBankLearn(tenant_id=tenant, kind="word", key=key, category=category))
        s.commit()
    return {"id": line_id, "category": category}


# ------------------------------------------------------------------ gateway settlements she hands over
def attach_settlements(tenant: str, settlements: list[dict[str, Any]]) -> dict[str, Any]:
    """A gateway settlement (Razorpay / Cashfree report) explains ONE bank credit: gross collected - fees - GST on fees = what the bank got."""
    ensure_tables()
    n = 0
    with session() as s:
        for st in settlements:
            try:
                net = round(float(st.get("amount")), 2)
                fees, tax = round(float(st.get("fees") or 0), 2), round(float(st.get("tax") or 0), 2)
            except (TypeError, ValueError):
                continue
            utr = str(st.get("utr") or "").strip()
            cand = [l for l in s.scalars(select(AccBankLine).where(AccBankLine.tenant_id == tenant, AccBankLine.credit > 0, AccBankLine.settlement == "")).all()
                    if abs(l.credit - net) <= 0.5 and ((utr and utr in l.narration.upper()) or not utr)]
            if utr:
                cand = [l for l in cand if utr.upper() in l.narration.upper()] or cand
            if len(cand) != 1:
                continue
            l = cand[0]
            l.settlement = json.dumps({"gross": round(net + fees + tax, 2), "fees": fees, "gst_on_fees": tax, "net": net, "utr": utr, "id": str(st.get("id") or "")})
            l.status = "matched" if l.status == "open" else l.status
            l.match_kind = l.match_kind or "settlement"
            l.match_reason = l.match_reason or f"A gateway settlement of Rs {net:g} (gross Rs {net + fees + tax:g} less fees Rs {fees:g} and GST Rs {tax:g})."
            n += 1
        s.commit()
    return {"attached": n}


# ------------------------------------------------------------------ the stored reconciliation statement
def reconcile(tenant: str, month: str, account: str = "") -> dict[str, Any]:
    if not re.fullmatch(r"\d{4}-\d{2}", month or ""):
        raise BankError("Month as YYYY-MM.")
    ensure_tables()
    with session() as s:
        q = select(AccBankLine).where(AccBankLine.tenant_id == tenant, AccBankLine.date.like(month + "%")).order_by(AccBankLine.date, AccBankLine.created_at)
        if account:
            q = q.where(AccBankLine.account == account)
        ls = s.scalars(q).all()
        if not ls:
            raise BankError("No bank lines for that month - import the statement first.")
        docs = {d.id: d for d in s.scalars(select(AccDoc).where(AccDoc.tenant_id == tenant, AccDoc.status != "gone")).all()}
        matched = [l for l in ls if l.status == "matched"]
        proposed = [l for l in ls if l.status == "proposed"]
        bank_only = [l for l in ls if l.status == "open"]
        paid_docs = {l.match_doc_id for l in s.scalars(select(AccBankLine).where(AccBankLine.tenant_id == tenant, AccBankLine.status == "matched")).all()}
        books_only = [d for d in docs.values() if d.period == month and d.direction in ("out", "in") and d.kind in ("inv", "bill", "dn") and d.id not in paid_docs and (d.total or 0) > 0]
        bal_first = next((l.balance for l in ls if l.balance), 0.0)
        bal_last = next((l.balance for l in reversed(ls) if l.balance), 0.0)
        opening = round(bal_first - l_net(ls[0]) if bal_first else 0.0, 2)
        flows = {"credits": round(sum(l.credit for l in ls), 2), "debits": round(sum(l.debit for l in ls), 2)}
        body = {
            "month": month, "account": account or "all", "lines": len(ls),
            "opening_balance": opening if bal_first else None, "closing_balance": bal_last if bal_last else None, **flows,
            "balance_check": ("ok" if not bal_first or abs(opening + flows["credits"] - flows["debits"] - bal_last) <= 1 else "the lines do not add up to the closing balance - a line may be missing from the import"),
            "matched": {"count": len(matched), "amount": round(sum(l.credit + l.debit for l in matched), 2)},
            "proposed_not_confirmed": len(proposed),
            "bank_only": [{"date": l.date, "narration": l.narration[:80], "amount": l.credit or -l.debit, "category": l.category or "", "mode": l.mode} for l in bank_only][:200],
            "books_only": [{"number": d.number, "party": d.party_name, "date": d.doc_date, "amount": d.total, "side": "receivable (sale not yet in the bank)" if d.direction == "out" else "payable (purchase not yet paid)"}
                           for d in books_only][:200],
            "uncleared_cheques": [{"date": l.date, "ref": l.ref, "narration": l.narration[:60], "amount": l.credit or -l.debit} for l in bank_only if l.mode == "cheque"],
            "note": "Books-only rows are money not seen in this bank account yet - normal for a recent invoice, a question for an old one. Uncleared cheques need your cheque register, which Hoola does not keep: cheque lines are listed as bank-only."}
        row = s.scalars(select(AccBankRecon).where(AccBankRecon.tenant_id == tenant, AccBankRecon.account == (account or "all"), AccBankRecon.month == month)).first()
        if row is None:
            row = AccBankRecon(tenant_id=tenant, account=account or "all", month=month)
            s.add(row)
        row.body = json.dumps(body, default=str)
        REG._event(s, tenant, "bank_reconciled", f"{account or 'all'}:{month}", after={"matched": len(matched), "bank_only": len(bank_only), "books_only": len(books_only)}, actor="owner")
        s.commit()
        return body


def l_net(l: AccBankLine) -> float:
    return round(l.credit - l.debit, 2)


def stored(tenant: str, month: str, account: str = "") -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        row = s.scalars(select(AccBankRecon).where(AccBankRecon.tenant_id == tenant, AccBankRecon.account == (account or "all"), AccBankRecon.month == month)).first()
        if row is None:
            raise BankError("No stored reconciliation for that month yet.")
        return json.loads(row.body) | {"stored_at": row.created_at.isoformat() if row.created_at else ""}
