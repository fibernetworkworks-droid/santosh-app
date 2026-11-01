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


def for_owner(r: AppProject, coll: str, row_id: str) -> bytes:
    c, row, d = _check(r, coll, row_id, W.Who(owner=True))
    return pdf(r, c, row, d)


def number(r: AppProject, row) -> str:
    day = row.created_at.strftime("%y%m%d") if row.created_at else "000000"
    return f"{(r.number or 'A').replace(' ', '')}-{day}-{row.id[-5:].upper()}"


def _money(v: Any) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return ""
    return f"₹{f:,.0f}" if f == int(f) else f"₹{f:,.2f}"


def pdf(r: AppProject, c: dict[str, Any], row, d: dict[str, Any]) -> bytes:
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
    return f"receipt-{number(r, row)}.pdf"


__all__ = ["link", "by_link", "for_owner", "pdf", "ready", "number"]
