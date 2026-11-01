"""v0.354 RASEED (App Sahayak Phase 18, owner: "START PHASE 18"): a receipt PDF for a finished order / booking / request.

Made by the SERVER from the server's own row (items + the server-priced total, the payment state she verified) and her
business facts - never from anything the phone says. Who may have it: the customer who made the row, staff, her. When: the
row is finished (Done / Delivered / Completed ...) or its UPI payment is Verified; a cancelled row never. It says plainly it is
a receipt, not a GST tax invoice. The installed app asks for a short-lived signed link (15 minutes, bound to this app, list and
row) and opens it in the phone's browser, so the app needs no storage permission and no file sharing; the link carries only
the row id. Devanagari names come out right (ReportLab with the shaped Noto run fonts, as in Lekhak documents)."""
from __future__ import annotations

import hashlib
import hmac
import io
import time
from typing import Any

from ..site import webapp as W
from . import backend as BE
from .models import AppProject

LINK_TTL = 15 * 60
STATS = {"receipts": 0, "links": 0, "refused": 0}
SKIP = ("items", "total", "status", "paid", "utr", "pay")


def _sig(r: AppProject, coll: str, row_id: str, exp: int) -> str:
    return hmac.new(W._secret(), f"receipt|{r.id}|{coll}|{row_id}|{exp}".encode(), hashlib.sha256).hexdigest()[:40]


def _load(r: AppProject, coll: str, row_id: str) -> tuple[dict[str, Any], Any, dict[str, Any]]:
    sch = BE.schema(r)
    c = W.coll(sch, coll)
    from ..db import session
    with session() as s:
        row = s.get(W.SiteAppRow, row_id)
        if row is None or row.site_id != BE.bid(r) or row.coll != coll:
            raise W.AppError("Yeh entry nahi mili.", 404)
        s.expunge(row)
    return c, row, BE._j(row.data, {})


def ready(d: dict[str, Any]) -> bool:
    return BE.receipt_ready(d)


def _check(r: AppProject, coll: str, row_id: str, w: W.Who):
    c, row, d = _load(r, coll, row_id)
    if not (w.staff or (w.id and row.owner == w.id)):
        STATS["refused"] += 1
        raise W.AppError("Yeh entry nahi mili.", 404)
    if not ready(d):
        STATS["refused"] += 1
        raise W.AppError("Raseed kaam poora hone (ya UPI verify hone) ke baad milegi.", 409)
    return c, row, d


def link(r: AppProject, coll: str, row_id: str, w: W.Who) -> dict[str, Any]:
    """The installed app's short-lived address of the receipt (opened in the phone's browser)."""
    if w.m is None and not w.owner:
        raise W.AppError("Pehle login kijiye.", 401)
    _check(r, coll, row_id, w)
    from ..config import get_settings
    exp = int(time.time()) + LINK_TTL
    key = BE._j(r.android, {}).get("app_key") or ""
    base = (get_settings().public_base_url or "").rstrip("/")
    STATS["links"] += 1
    return {"url": f"{base}/api/app-api/{key}/receipt/{coll}/{row_id}?e={exp}&s={_sig(r, coll, row_id, exp)}", "expires": exp}


def by_link(r: AppProject, coll: str, row_id: str, e: str, s: str) -> bytes:
    try:
        exp = int(e)
    except (TypeError, ValueError):
        exp = 0
    if exp < time.time() or not hmac.compare_digest(str(s or ""), _sig(r, coll, row_id, exp)):
        STATS["refused"] += 1
        raise W.AppError("Yeh raseed ka link purana ho gaya; app se dobara kholiye.", 403)
    c, row, d = _load(r, coll, row_id)
    if not ready(d):
        raise W.AppError("Raseed abhi nahi.", 409)
    return pdf(r, c, row, d)


def for_owner(r: AppProject, coll: str, row_id: str, doc: str = "") -> bytes:
    """Her copy; doc="invoice" = the original tax invoice of a row that now has a credit note (v0.356)."""
    c, row, d = _check(r, coll, row_id, W.Who(owner=True))
    return pdf(r, c, row, d, doc)


def number(r: AppProject, row) -> str:
    day = row.created_at.strftime("%y%m%d") if row.created_at else "000000"
    return f"{(r.number or 'A').replace(' ', '')}-{day}-{row.id[-5:].upper()}"


def _money(v: Any) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return ""
    return f"₹{f:,.0f}" if f == int(f) else f"₹{f:,.2f}"


def pdf(r: AppProject, c: dict[str, Any], row, d: dict[str, Any], doc: str = "") -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A5
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    from ..docstudio import pdfgen as PG
    from . import service as AS
    PG.ensure_fonts()
    T = PG._t
    font = "FreeSans" if "FreeSans" in PG._FONT_STATE["pool"] else "Helvetica"
    bold = font + "-Bold" if font != "Helvetica" else "Helvetica-Bold"
    st = {"h": ParagraphStyle("h", fontName=bold, fontSize=15, leading=19),
          "p": ParagraphStyle("p", fontName=font, fontSize=9, leading=12.5, textColor=colors.HexColor("#333333")),
          "b": ParagraphStyle("b", fontName=bold, fontSize=10, leading=13),
          "s": ParagraphStyle("s", fontName=font, fontSize=7.5, leading=10, textColor=colors.HexColor("#666666"))}
    facts = AS._j(r.facts, {}) if getattr(r, "facts", None) else {}
    name = str(facts.get("name") or r.name or "Receipt")
    from . import gst as G
    if d.get("_cn_no") and doc != "invoice":      # v0.356 WAPSI: a cancelled invoiced row's document is its credit note
        return _tax_invoice(r, c, row, d, facts, name, st, T, credit=True)
    if G.on(r) or (doc == "invoice" and d.get("_inv_no")):   # v0.355 GST BILL: a registered business gets a tax invoice
        return _tax_invoice(r, c, row, d, facts, name, st, T)
    out: list[Any] = [Paragraph(T(name), st["h"])]
    contact = " · ".join(str(facts[k]) for k in ("address", "phone", "email") if facts.get(k))
    if contact:
        out.append(Paragraph(T(contact), st["s"]))
    out += [Spacer(1, 4 * mm), Paragraph(T("Receipt"), st["b"]),
            Paragraph(T(f"No. {number(r, row)} · {row.created_at.strftime('%d %b %Y, %I:%M %p') if row.created_at else ''}"), st["p"]),
            Paragraph(T(f"{c['label']} · Status: {d.get('status') or '-'}"), st["p"]), Spacer(1, 3 * mm)]
    # who and what (her own fields, as sent; files / photos / admin-only fields left out)
    rows = []
    for f in c["fields"]:
        k = f["key"]
        if k in SKIP or f.get("type") in ("photo", "file") or f.get("admin_only") or f.get("hidden") or not str(d.get(k) or "").strip():
            continue
        rows.append([Paragraph(T(f["label"]), st["s"]), Paragraph(T(str(d[k])[:300]), st["p"])])
    if rows:
        t = Table(rows, colWidths=[32 * mm, None])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
        out += [t, Spacer(1, 3 * mm)]
    items = [ln.strip() for ln in str(d.get("items") or "").splitlines() if ln.strip()]
    if items:
        lines = [[Paragraph(T("Item"), st["b"])]] + [[Paragraph(T(x[:200]), st["p"])] for x in items[:80]]
        t = Table(lines, colWidths=[None])
        t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#999999")),
                               ("LINEBELOW", (0, -1), (-1, -1), 0.6, colors.HexColor("#999999"))]))
        out.append(t)
    if d.get("discount"):                          # v0.358 COUPON
        out += [Spacer(1, 2 * mm), Paragraph(T(f"Subtotal: {_money(d.get('subtotal'))}"), st["p"]),
                Paragraph(T(f"Coupon {d.get('coupon')}: -{_money(d.get('discount'))}"), st["p"])]
    if d.get("total") not in (None, ""):
        out += [Spacer(1, 2 * mm), Paragraph(T(f"Total: {_money(d.get('total'))}"), st["h"])]
    paid = str(d.get("paid") or "")
    pay = str(d.get("pay") or "")
    line = ("Paid by UPI - verified by " + name + (f" (UPI ref {d['utr']})" if d.get("utr") else "")) if paid == "Verified" else \
        ("Payment: customer says paid, not yet verified by the business" if paid == "Customer says paid" else
         (f"Payment: {pay}" if pay else ""))
    if line:
        out.append(Paragraph(T(line), st["p"]))
    if d.get("_to_name"):
        out.append(Paragraph(T(f"Handled by {d['_to_name']}"), st["p"]))
    out += [Spacer(1, 6 * mm), Paragraph(T("This is a receipt, not a GST tax invoice. Made by the " + name + " app."), st["s"])]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A5, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
                            title=f"Receipt {number(r, row)}", author=name, subject="Receipt")
    doc.build(out)
    STATS["receipts"] += 1
    return buf.getvalue()


def filename(r: AppProject, row) -> str:
    d = BE._j(row.data, {}) if row is not None else {}
    if d.get("_cn_no"):
        return f"credit-note-{d['_cn_no'].replace('/', '-')}.pdf"
    inv = d.get("_inv_no") or ""
    return f"invoice-{inv.replace('/', '-')}.pdf" if inv else f"receipt-{number(r, row)}.pdf"


__all__ = ["link", "by_link", "for_owner", "pdf", "ready", "number"]


def _tax_invoice(r: AppProject, c: dict[str, Any], row, d: dict[str, Any], facts: dict[str, Any], name: str, st, T,
                 credit: bool = False) -> bytes:
    """v0.355 the Rule 46 tax invoice (GST-inclusive prices; the total is the server's order total).
    v0.356 credit=True: the CREDIT NOTE for the same lines, referring to the original invoice."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    from . import gst as G
    no, day = G.number_for(r, row.id)
    inv_no, inv_day = no, day
    if credit:
        no, day = d["_cn_no"], d.get("_cn_date", "")
    x = G.compute(r, c, d)
    P = lambda t, k="p": Paragraph(T(t), st[k])
    seller = x["legal_name"] or name
    out: list[Any] = [P("CREDIT NOTE" if credit else "TAX INVOICE", "h"), P(seller, "b")]
    if x["legal_name"] and x["legal_name"] != name:
        out.append(P(f"Trade name: {name}"))
    contact = " · ".join(str(facts[k]) for k in ("address", "phone", "email") if facts.get(k))
    if contact:
        out.append(P(contact, "s"))
    out += [P(f"GSTIN: {x['gstin']} · State: {x['home_name']} ({x['gstin'][:2]})"), Spacer(1, 3 * mm)]
    buyer_name = next((str(d.get(k)) for k in ("name", "customer", "student", "company") if d.get(k)), "")
    buyer_addr = next((str(d.get(k)) for k in ("address", "site_address", "city") if d.get(k)), "")
    head = [[P(f"{'Credit note' if credit else 'Invoice'} No. {no}", "b"), P(f"Date: {day}", "b")],
            [P("Bill to: " + (buyer_name or "Customer") + (f", {buyer_addr}" if buyer_addr else "")[:300]),
             P(f"Place of supply: {x['pos_name']} ({x['pos']})")]]
    if x["buyer_gstin"]:
        head.append([P(f"Buyer GSTIN: {x['buyer_gstin']}"), P("")])
    if credit:
        head.append([P(f"Against tax invoice {inv_no} dated {inv_day}", "b"), P("Reason: " + str(d.get("_cn_reason") or "Order cancelled"))])
    t = Table(head, colWidths=[110 * mm, None])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    out += [t, Spacer(1, 3 * mm)]
    m = lambda v: f"{v:,.2f}"
    tax_cols = ["IGST"] if x["inter"] else ["CGST", "SGST"]
    rows = [[P(h, "b") for h in ["#", "Item", "HSN/SAC", "Qty", "Taxable", "Rate"] + tax_cols + ["Amount"]]]
    for i, ln in enumerate(x["lines"], 1):
        tax = [m(ln["igst"])] if x["inter"] else [m(ln["cgst"]), m(ln["sgst"])]
        rows.append([P(str(i)), P(ln["name"][:120]), P(ln["hsn"] or "-"), P(str(ln["qty"])), P(m(ln["taxable"])),
                     P(f"{ln['rate']:g}%")] + [P(v) for v in tax] + [P(m(ln["amount"]))])
    tt = x["totals"]
    rows.append([P(""), P("Total", "b"), P(""), P(""), P(m(tt["taxable"]), "b"), P("")]
                + ([P(m(tt["igst"]), "b")] if x["inter"] else [P(m(tt["cgst"]), "b"), P(m(tt["sgst"]), "b")]) + [P(m(tt["amount"]), "b")])
    widths = [8 * mm, None, 18 * mm, 10 * mm, 22 * mm, 13 * mm] + ([20 * mm] if x["inter"] else [18 * mm, 18 * mm]) + [22 * mm]
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#999999")),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    if d.get("discount"):                          # v0.358 the coupon is already spread over the lines above
        out.append(P(f"Includes coupon {d.get('coupon')} discount of ₹{m(float(d['discount']))} on ₹{m(float(d.get('subtotal') or 0))}.", "s"))
    label = "Credit note value" if credit else "Invoice total"
    out += [t, Spacer(1, 3 * mm), P(f"{label}: ₹{m(tt['amount'])} (GST included)", "b"), P(G.words(tt["amount"]), "s")]
    paid = str(d.get("paid") or "")
    if credit:
        out.append(P("The tax on this credit note reduces the supplier's output tax for the original invoice. "
                     "Any refund is made by the business separately."))
    elif paid == "Verified":
        out.append(P("Paid by UPI" + (f" (ref {d['utr']})" if d.get("utr") else "") + "."))
    out += [P("Tax payable on reverse charge: No."), Spacer(1, 10 * mm), P(f"For {seller}", "b"), P("Authorised signatory", "s"),
            Spacer(1, 4 * mm), P(f"Computer-generated {'credit note' if credit else 'invoice'} made by the " + name + " app.", "s")]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                            title=f"{'Credit note' if credit else 'Tax invoice'} {no}", author=seller,
                            subject="Credit note" if credit else "Tax invoice")
    doc.build(out)
    STATS["receipts"] += 1
    G.STATS["invoices"] += 1
    return buf.getvalue()
