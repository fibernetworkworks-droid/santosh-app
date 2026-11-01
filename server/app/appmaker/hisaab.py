"""v0.361 HISAAB (App Sahayak Phase 25, owner: "START PHASE 25"): her month's accounts + GST summary for her CA.

One ZIP of CSV files (Excel opens them) for a month, made from the SAME server numbers the invoices use: the sales register
(every order), the invoice register (Rule 46 numbers, taxable, CGST / SGST / IGST, place of supply), the credit-note register,
an HSN summary and a rate-wise summary (the shape GSTR-1 asks for), and the khata movements. Plus a one-line summary for the
chat. Nothing is filed anywhere - she / her CA files. Months are Indian time (IST); an invoice / credit note counts in the month
of ITS date, an order in the month it was placed."""
from __future__ import annotations

import csv
import io
import re
import zipfile
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select

from ..db import session
from ..site import webapp as W
from .models import AppProject

MONTH = re.compile(r"^(20\d\d)-(0[1-9]|1[0-2])$")
STATS = {"reports": 0}


class HisaabError(W.AppError):
    pass


def _ist(dt):
    return (dt + timedelta(hours=5, minutes=30)) if dt else None


def _month_of_day(s: str) -> str:
    try:
        return datetime.strptime(s, "%d %b %Y").strftime("%Y-%m")
    except (TypeError, ValueError):
        return ""


def default_month() -> str:
    from ..db import now
    t = _ist(now())
    first = t.replace(day=1)
    return (first - timedelta(days=1)).strftime("%Y-%m") if t.day <= 5 else t.strftime("%Y-%m")   # early in a month = last month


def build(r: AppProject, month: str = "") -> dict[str, Any]:
    """All the month's tables as lists of rows + the summary."""
    from . import backend as BE
    from . import gst as G
    month = month or default_month()
    if not MONTH.match(month):
        raise HisaabError("Mahina YYYY-MM (jaise 2026-10).")
    sch = BE.schema(r)
    order = sch.get("order") or ""
    colls = {c["key"]: c for c in sch["collections"]}
    site = BE.bid(r)
    with session() as s:
        rows = s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == site)).all()
        for x in rows:
            s.expunge(x)
    sales, inv, cns, khata = [], [], [], []
    hsn: dict[tuple[str, float], dict[str, float]] = {}
    rate: dict[float, dict[str, float]] = {}
    tot = {"orders": 0, "sales": 0.0, "cancelled": 0, "gst": 0.0, "taxable": 0.0, "credit": 0.0, "credit_gst": 0.0,
           "udhaar_given": 0.0, "udhaar_paid": 0.0, "discount": 0.0, "delivery": 0.0}
    for x in sorted(rows, key=lambda y: y.created_at or datetime.min):
        d = BE._j(x.data, {})
        made = _ist(x.created_at)
        if x.coll == "_khata":
            if made and made.strftime("%Y-%m") == month:
                khata.append([made.strftime("%Y-%m-%d"), d.get("name", ""), d.get("kind", ""), d.get("amount", 0), d.get("mode", ""), d.get("note", "")])
                tot["udhaar_given" if d.get("kind") == "credit" else "udhaar_paid"] += float(d.get("amount") or 0)
            continue
        c = colls.get(x.coll)
        if c is None:
            continue
        if x.coll == order and made and made.strftime("%Y-%m") == month:
            st = str(d.get("status") or "")
            cancelled = st.strip().lower() == "cancelled"
            sales.append([made.strftime("%Y-%m-%d %H:%M"), x.id[-6:].upper(), d.get("name") or d.get("customer") or "", d.get("phone", ""),
                          st, d.get("subtotal") or "", d.get("coupon", ""), d.get("discount") or "", d.get("delivery") or "",
                          d.get("total", ""), d.get("paid", ""), d.get("_inv_no", "")])
            if cancelled:
                tot["cancelled"] += 1
            else:
                tot["orders"] += 1
                tot["sales"] += float(d.get("total") or 0)
                tot["discount"] += float(d.get("discount") or 0)
                tot["delivery"] += float(d.get("delivery") or 0)
        for kind, no_key, day_key in (("inv", "_inv_no", "_inv_date"), ("cn", "_cn_no", "_cn_date")):
            if not d.get(no_key) or _month_of_day(d.get(day_key, "")) != month:
                continue
            g = G.compute(r, c, d)
            t = g["totals"]
            name = d.get("name") or d.get("customer") or ""
            if kind == "inv":
                inv.append([d[no_key], d.get(day_key, ""), name, g["buyer_gstin"], f"{g['pos']}-{g['pos_name']}", t["taxable"], t["cgst"], t["sgst"],
                            t["igst"], t["amount"]])
                tot["gst"] += t["cgst"] + t["sgst"] + t["igst"]
                tot["taxable"] += t["taxable"]
                sign = 1
            else:
                cns.append([d[no_key], d.get(day_key, ""), d.get("_inv_no", ""), d.get("_inv_date", ""), name, d.get("_cn_reason", ""),
                            t["taxable"], t["cgst"], t["sgst"], t["igst"], t["amount"]])
                tot["credit"] += t["amount"]
                tot["credit_gst"] += t["cgst"] + t["sgst"] + t["igst"]
                sign = -1
            for ln in g["lines"]:
                k = (ln["hsn"] or "-", float(ln["rate"]))
                h = hsn.setdefault(k, {"qty": 0, "taxable": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0, "amount": 0.0})
                rr = rate.setdefault(float(ln["rate"]), {"taxable": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0, "amount": 0.0})
                h["qty"] += sign * ln["qty"]
                for f in ("taxable", "cgst", "sgst", "igst", "amount"):
                    h[f] = round(h[f] + sign * ln[f], 2)
                    rr[f] = round(rr[f] + sign * ln[f], 2)
    tot = {k: round(v, 2) if isinstance(v, float) else v for k, v in tot.items()}
    say = (f"{month}: {tot['orders']} orders, sales Rs {tot['sales']:,.0f}"
           + (f", GST Rs {tot['gst']:,.2f} on {len(inv)} invoices" if inv else "")
           + (f", credit notes Rs {tot['credit']:,.0f}" if cns else "")
           + (f", udhaar diya Rs {tot['udhaar_given']:,.0f} / mila Rs {tot['udhaar_paid']:,.0f}" if khata else "") + ".")
    STATS["reports"] += 1
    return {"month": month, "summary": tot, "say": say, "counts": {"sales": len(sales), "invoices": len(inv), "credit_notes": len(cns),
                                                                   "khata": len(khata)},
            "sales": sales, "invoices": inv, "credit_notes": cns, "khata": khata,
            "hsn": [[k[0], f"{k[1]:g}", v["qty"], v["taxable"], v["cgst"], v["sgst"], v["igst"], v["amount"]] for k, v in sorted(hsn.items())],
            "rates": [[f"{k:g}", v["taxable"], v["cgst"], v["sgst"], v["igst"], v["amount"]] for k, v in sorted(rate.items())]}


HEADS = {
    "sales": ["Placed (IST)", "Order", "Customer", "Phone", "Status", "Items value", "Coupon", "Discount", "Delivery", "Total", "Payment", "Invoice"],
    "invoices": ["Invoice no", "Date", "Customer", "Buyer GSTIN", "Place of supply", "Taxable", "CGST", "SGST", "IGST", "Invoice value"],
    "credit_notes": ["Credit note no", "Date", "Against invoice", "Invoice date", "Customer", "Reason", "Taxable", "CGST", "SGST", "IGST", "Value"],
    "hsn": ["HSN/SAC", "Rate %", "Qty", "Taxable", "CGST", "SGST", "IGST", "Value"],
    "rates": ["Rate %", "Taxable", "CGST", "SGST", "IGST", "Value"],
    "khata": ["Date", "Customer", "Entry", "Amount", "Mode", "Note"],
}


def _safe(v: Any) -> Any:
    """A cell starting with = + - @ would run as a formula in Excel (her customers type these fields): quote it."""
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + v
    return v


def zip_bytes(r: AppProject, month: str = "") -> tuple[bytes, str, dict[str, Any]]:
    rep = build(r, month)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for key, head in HEADS.items():
            s = io.StringIO()
            w = csv.writer(s)
            w.writerow(head)
            for row in rep[key]:
                w.writerow([_safe(v) for v in row])
            z.writestr(f"{rep['month']}-{key.replace('_', '-')}.csv", "﻿" + s.getvalue())   # BOM: Excel reads Hindi names right
        z.writestr("README.txt", f"{r.name or 'App'} - accounts for {rep['month']} (Indian time).\n{rep['say']}\n"
                                 "Made from the app's own server numbers. GST-inclusive prices. Nothing has been filed - "
                                 "give these files to your CA for GSTR-1 / GSTR-3B.\n")
    name = f"hisaab-{(r.number or 'app').replace(' ', '')}-{rep['month']}.zip"
    return buf.getvalue(), name, rep
