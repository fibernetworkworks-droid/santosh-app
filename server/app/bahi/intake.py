"""v0.844 BAHI A6 - bills in, checked: a purchase bill (photo, PDF or pasted text) is read into fields, every field is cross-checked, and the result is
a DRAFT with a confidence and the reasons - it enters the register only on her tap.

Reading is local first (the PDF's own text, else the OCR already on the server). No model call is made here: a bill the reader cannot understand is
shown with what is missing and she types it. Checks: the supplier GSTIN's check digit and status (API Setu / WhiteBooks), the bill is addressed to HER
GSTIN, taxable + tax = total, CGST = SGST, intra- vs inter-state tax, the rate is a slab in force on the date, a duplicate of a bill already held,
a date that makes sense. NOT WIRED yet: the WhatsApp number, the mailbox bucket and PC folders hand a file to `intake_file` - that hand-off is not built.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from typing import Any

from sqlalchemy import select

from ..db import session
from . import register as REG
from . import rules as RU
from .models import AccDoc, AccIntake, ensure_tables

GSTIN_RX = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b")
NUM = r"(?:₹|Rs\.?|INR)?\s*([\d,]+(?:\.\d{1,2})?)(?![\d.,]*\s*%)(?!\d)"


class IntakeError(Exception):
    pass


def _n(v: str) -> float:
    try:
        return round(float(str(v).replace(",", "")), 2)
    except ValueError:
        return 0.0


def _date(text: str) -> str:
    m = re.search(r"(?i)(?:invoice|bill|inv\.?)?\s*date\s*[:\-]?\s*(\d{1,2})[/\-. ](\d{1,2}|[A-Za-z]{3})[/\-. ](\d{2,4})", text)
    if not m:
        return ""
    d, mo, y = m.groups()
    y = ("20" + y) if len(y) == 2 else y
    for fmt, s in (("%d-%m-%Y", f"{d}-{mo}-{y}"), ("%d-%b-%Y", f"{d}-{mo}-{y}")):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def _amt(text: str, *labels: str) -> float:
    for lab in labels:
        m = re.search(rf"(?i){lab}[^\d\n]{{0,40}}?(?:\d+(?:\.\d+)?\s*%)?[^\d\n]{{0,12}}?{NUM}", text)
        if m and _n(m.group(1)):
            return _n(m.group(1))
    return 0.0


def extract(text: str, mine: str) -> dict[str, Any]:
    """Fields out of the bill's text. Nothing is guessed: a field not found is left empty."""
    gs = []
    for g in GSTIN_RX.findall(text.upper()):
        if g not in gs:
            gs.append(g)
    supplier = next((g for g in gs if g != mine), "")
    buyer = mine if mine in gs else next((g for g in gs if g != supplier), "")
    inv = re.search(r"(?i)(?:invoice|bill|inv)\.?\s*(?:no\.?|number|#)\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9/\-]{2,19})", text)
    hsn = []
    for h in re.findall(r"(?i)(?:hsn|sac)[^0-9\n]{0,15}(\d{4,8})", text):
        if h not in hsn:
            hsn.append(h)
    name = ""
    if supplier:
        head = text[: text.upper().find(supplier)] if text.upper().find(supplier) > 0 else text[:200]
        lines = [ln.strip() for ln in head.splitlines() if len(ln.strip()) > 3 and not re.search(r"(?i)tax invoice|gstin|invoice|original|date", ln)]
        name = lines[-1][:80] if lines else ""
    return {"supplier_gstin": supplier, "buyer_gstin": buyer, "party_name": name, "number": inv.group(1) if inv else "", "date": _date(text),
            "taxable": _amt(text, r"taxable\s*(?:value|amount)", r"assessable\s*value", r"sub\s*total"),
            "cgst": _amt(text, r"cgst"), "sgst": _amt(text, r"sgst", r"utgst"), "igst": _amt(text, r"igst"), "cess": _amt(text, r"cess"),
            "total": _amt(text, r"grand\s*total", r"total\s*invoice\s*value", r"invoice\s*(?:total|value)", r"net\s*(?:amount\s*)?payable", r"total\s*amount"),
            "hsn": hsn[:6]}


def check(tenant: str, mine: str, f: dict[str, Any], ocr_conf: float = 100.0, skip_status: bool = False) -> list[dict[str, str]]:
    from ..appmaker.gst import valid_gstin
    out: list[dict[str, str]] = []
    add = lambda lvl, text: out.append({"level": lvl, "text": text})   # noqa: E731
    sup = f.get("supplier_gstin", "")
    if not sup:
        add("error", "No supplier GSTIN found on the bill - without it the credit cannot be matched in your 2B.")
    elif not valid_gstin(sup):
        add("error", f"Supplier GSTIN {sup} fails the check digit - a misread digit or a wrong number.")
    if f.get("buyer_gstin") and f["buyer_gstin"] != mine:
        add("error", f"The bill is addressed to GSTIN {f['buyer_gstin']}, not yours ({mine}) - you cannot take credit on it.")
    elif not f.get("buyer_gstin"):
        add("warn", "Your GSTIN is not printed on this bill - credit is only allowed on a bill that carries it.")
    for key, label in (("number", "invoice number"), ("date", "invoice date"), ("taxable", "taxable value"), ("total", "invoice total")):
        if not f.get(key):
            add("error", f"The {label} could not be read - type it.")
    tax = round(f.get("cgst", 0) + f.get("sgst", 0) + f.get("igst", 0) + f.get("cess", 0), 2)
    if f.get("taxable") and f.get("total"):
        diff = round(f["taxable"] + tax - f["total"], 2)
        if abs(diff) > 1.5:
            add("error", f"Taxable Rs {f['taxable']:g} + tax Rs {tax:g} = Rs {f['taxable'] + tax:g}, but the bill's total is Rs {f['total']:g} (difference Rs {diff:g}) - one number is misread.")
    if f.get("cgst") or f.get("sgst"):
        if abs(f.get("cgst", 0) - f.get("sgst", 0)) > 1:
            add("error", f"CGST Rs {f.get('cgst', 0):g} and SGST Rs {f.get('sgst', 0):g} should be equal - one is misread.")
    if sup and mine and len(sup) == 15:
        same = sup[:2] == mine[:2]
        if same and f.get("igst"):
            add("error", "Supplier and you are in the same state, so the tax should be CGST + SGST, but the bill shows IGST.")
        if not same and (f.get("cgst") or f.get("sgst")):
            add("error", "Supplier is in another state, so the tax should be IGST, but the bill shows CGST / SGST.")
    if f.get("taxable") and tax and f.get("date"):
        rate = round((f.get("cgst", 0) + f.get("sgst", 0) + f.get("igst", 0)) / f["taxable"] * 100, 2)
        slabs = RU.slabs_on(f["date"]) or []
        if slabs and not any(abs(rate - s) <= 0.2 for s in slabs):
            add("warn", f"The tax is {rate:g}% of the taxable value, which is not a GST slab in force on {f['date']} ({', '.join(f'{x:g}' for x in sorted(slabs))}) - check the amounts.")
    if f.get("date"):
        try:
            d = date.fromisoformat(f["date"])
            if d > date.today():
                add("error", f"The bill is dated {f['date']}, in the future.")
            elif (date.today() - d).days > 365:
                add("warn", "The bill is more than a year old - credit may be time-barred (30 Nov after the financial year).")
        except ValueError:
            add("error", "The invoice date is not a real date.")
    if not f.get("hsn"):
        add("warn", "No HSN / SAC code read - fine for a purchase entry, needed if you resell the item on an e-invoice.")
    if ocr_conf < 60:
        add("warn", f"The photo was hard to read (OCR {ocr_conf:g}%) - check every number against the bill.")
    ensure_tables()
    with session() as s:
        if sup and f.get("number"):
            nn = _norm(f["number"])
            for d in s.scalars(select(AccDoc).where(AccDoc.tenant_id == tenant, AccDoc.direction == "in", AccDoc.party_gstin == sup, AccDoc.status != "gone")).all():
                if _norm(d.number) == nn:
                    add("error", f"This bill is already in your register ({d.number}, {d.doc_date}, from {REG.SOURCES.get(d.source, d.source)}) - entering it again would double the credit.")
                    break
            else:
                for d in s.scalars(select(AccDoc).where(AccDoc.tenant_id == tenant, AccDoc.direction == "in", AccDoc.party_gstin == sup,
                                                        AccDoc.doc_date == f.get("date", ""), AccDoc.status != "gone")).all():
                    if f.get("total") and abs((d.total or 0) - f["total"]) < 1:
                        add("warn", f"A bill from this supplier on the same date for the same amount is already held ({d.number}) - possibly the same bill under another number.")
                        break
    if sup and not skip_status:
        try:
            from . import connect as CN
            st = CN.supplier_check(tenant, sup, filing=False)
            if st["status"] in ("cancelled", "suspended"):
                add("error", f"The supplier's GSTIN is {st['status']} ({st['source']}) - credit on this bill is not allowed.")
            elif st["status"] == "unknown":
                add("warn", "The supplier's GSTIN status could not be checked right now.")
        except Exception:   # noqa: BLE001
            add("warn", "The supplier's GSTIN status could not be checked right now.")
    return out


def _norm(n: str) -> str:
    s = re.sub(r"[^A-Z0-9]", "", str(n or "").upper())
    return re.sub(r"(?<![0-9])0+(?=\d)", "", s)


def _confidence(f: dict[str, Any], checks: list[dict[str, str]], ocr_conf: float) -> float:
    c = 1.0 - 0.2 * sum(1 for x in checks if x["level"] == "error") - 0.05 * sum(1 for x in checks if x["level"] == "warn")
    if ocr_conf < 90:
        c -= (90 - ocr_conf) / 400
    return round(max(0.0, min(1.0, c)), 2)


def read_text_of(tenant: str, file_id: str) -> tuple[str, float, str]:
    """(text, ocr confidence, reader) of a stored file - the PDF's own text first, OCR for pictures and scanned PDFs."""
    from ..gstp.service import GstError, _load_file
    try:
        name, data = _load_file(tenant, file_id)
    except GstError as e:
        raise IntakeError(str(e)) from None
    low = name.lower()
    if low.endswith((".png", ".jpg", ".jpeg", ".webp", ".heic", ".bmp", ".tif", ".tiff")):
        from .. import ocr
        r = ocr.read(data, language="en")
        if r is None:
            raise IntakeError("This server cannot read pictures yet (OCR is not installed). Paste the bill's text instead, or send a PDF.")
        return r["text"], float(r["conf"]), "ocr"
    from .. import docread
    r = docread.read_text(name, "", data)
    text = (r.get("text") or "")
    if len(text.strip()) < 40 and low.endswith(".pdf"):
        from .. import ocr
        o = ocr.read_pdf(data, language="en")
        if o and o.get("text"):
            return o["text"], float(o.get("conf", 0)), "ocr"
    if len(text.strip()) < 20:
        raise IntakeError("Nothing readable was found in that file. Try a clearer photo, a PDF, or paste the text.")
    return text, 100.0, str(r.get("reader") or "text")


def intake_text(tenant: str, gstin: str, text: str, channel: str = "upload", file_id: str = "", ocr_conf: float = 100.0,
                skip_status: bool = False) -> dict[str, Any]:
    from ..appmaker.gst import valid_gstin
    mine = (gstin or "").strip().upper()
    if not valid_gstin(mine):
        raise IntakeError("Tell Hoola which of your GSTINs the bill is for (shape or check digit is wrong).")
    text = (text or "").strip()
    if len(text) < 20:
        raise IntakeError("There is no bill text to read.")
    h = hashlib.sha256(re.sub(r"\s+", " ", text).encode()).hexdigest()[:32]
    ensure_tables()
    with session() as s:
        prev = s.scalars(select(AccIntake).where(AccIntake.tenant_id == tenant, AccIntake.text_hash == h, AccIntake.status != "rejected")).first()
        if prev is not None:
            return _view(prev) | {"already": True}
    f = extract(text, mine)
    checks = check(tenant, mine, f, ocr_conf, skip_status)
    conf = _confidence(f, checks, ocr_conf)
    with session() as s:
        row = AccIntake(tenant_id=tenant, gstin=mine, channel=channel[:16], file_id=file_id[:60], text_hash=h, fields=json.dumps(f), checks=json.dumps(checks),
                        confidence=conf, ocr_conf=ocr_conf)
        s.add(row)
        REG._event(s, tenant, "bill_read", f"{mine}:{f.get('number', '')}", after={"confidence": conf, "channel": channel}, actor="hoola")
        s.commit()
        return _view(row)


def intake_file(tenant: str, gstin: str, file_id: str, channel: str = "upload") -> dict[str, Any]:
    text, conf, _ = read_text_of(tenant, file_id)
    return intake_text(tenant, gstin, text, channel=channel, file_id=file_id, ocr_conf=conf)


def _view(r: AccIntake) -> dict[str, Any]:
    checks = json.loads(r.checks or "[]")
    errs = [c for c in checks if c["level"] == "error"]
    return {"id": r.id, "gstin": r.gstin, "channel": r.channel, "fields": json.loads(r.fields or "{}"), "checks": checks, "confidence": r.confidence,
            "status": r.status, "doc_id": r.doc_id, "state": "ready" if not errs else "needs_you", "created_at": r.created_at.isoformat() if r.created_at else ""}


def listing(tenant: str, status: str = "draft") -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        q = select(AccIntake).where(AccIntake.tenant_id == tenant).order_by(AccIntake.created_at.desc()).limit(100)
        if status:
            q = q.where(AccIntake.status == status)
        return [_view(r) for r in s.scalars(q).all()]


FIELD_KEYS = {"supplier_gstin": str, "party_name": str, "number": str, "date": str, "taxable": float, "cgst": float, "sgst": float, "igst": float, "cess": float, "total": float}


def confirm(tenant: str, intake_id: str, overrides: dict[str, Any] | None, accept_errors: bool = False, skip_status: bool = False) -> dict[str, Any]:
    """Her tap: the draft (with any correction she types) becomes a purchase in the register. Errors must be fixed - or accepted by her, in writing."""
    ensure_tables()
    with session() as s:
        r = s.get(AccIntake, intake_id)
        if r is None or r.tenant_id != tenant:
            raise IntakeError("That bill was not found.")
        if r.status != "draft":
            raise IntakeError(f"That bill is already {r.status}.")
        f = json.loads(r.fields or "{}")
        for k, cast in FIELD_KEYS.items():
            if k in (overrides or {}) and str(overrides[k]).strip() != "":
                f[k] = (str(overrides[k]).strip().upper() if k == "supplier_gstin" else _n(overrides[k]) if cast is float else str(overrides[k]).strip())
        mine, ocr_conf = r.gstin, r.ocr_conf
    f["buyer_gstin"] = f.get("buyer_gstin") or ""
    checks = check(tenant, mine, f, ocr_conf, skip_status)
    # the check that finds THIS draft as a duplicate of itself must not exist: it is not in the register yet
    errs = [c for c in checks if c["level"] == "error"]
    if errs and not accept_errors:
        raise IntakeError("Fix first: " + " | ".join(c["text"] for c in errs))
    tax = round(f.get("cgst", 0) + f.get("sgst", 0) + f.get("igst", 0), 2)
    period = (f.get("date") or date.today().isoformat())[:7]
    with session() as s:
        r = s.get(AccIntake, intake_id)
        reason = "Read from a bill you sent (" + r.channel + "), " + ("every check passed." if not errs else f"{len(errs)} check(s) accepted by you: " + "; ".join(c["text"][:80] for c in errs))
        d = AccDoc(tenant_id=tenant, gstin=mine, period=period, direction="in", kind="bill", number=f.get("number", "")[:60], doc_date=f.get("date", ""),
                   party_name=f.get("party_name", "")[:160], party_gstin=f.get("supplier_gstin", ""), pos=mine[:2], taxable=f.get("taxable", 0),
                   cgst=f.get("cgst", 0), sgst=f.get("sgst", 0), igst=f.get("igst", 0), cess=f.get("cess", 0), tax=tax, total=f.get("total", 0),
                   source="intake", source_ref=r.id, status="confirmed", confidence=r.confidence, reason=reason[:1000],
                   problems=json.dumps([c["text"] for c in checks]))
        s.add(d)
        s.flush()
        r.status, r.doc_id, r.fields = "confirmed", d.id, json.dumps(f)
        REG._event(s, tenant, "bill_added", f"intake:{r.id}", after={"number": d.number, "total": d.total, "accepted_errors": len(errs)}, actor="owner")
        s.commit()
        return _view(r)


def reject(tenant: str, intake_id: str) -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        r = s.get(AccIntake, intake_id)
        if r is None or r.tenant_id != tenant:
            raise IntakeError("That bill was not found.")
        if r.status == "draft":
            r.status = "rejected"
            REG._event(s, tenant, "bill_rejected", f"intake:{r.id}", actor="owner")
            s.commit()
        return _view(r)
