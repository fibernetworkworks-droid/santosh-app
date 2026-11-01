"""v0.373 GSTR-1 FILE (App Sahayak Phase 37, owner: "START PHASE 37"): the month's GSTR-1 as a JSON file in the shape the GST
portal's offline tool imports, made from the SAME numbers as her invoices (gst.compute) - so her CA imports it, checks it
in the offline tool and files it. Hoola never files anything and never talks to the GST portal.

Sections: b2b (invoices to a buyer GSTIN, item rows per rate), b2cl (inter-state invoices to unregistered buyers above
Rs 1,00,000), b2cs (all other consumer sales, netted with their credit notes, per supply type / place of supply / rate), cdnr
(credit notes against b2b invoices), cdnur (credit notes against b2cl invoices), hsn (net by HSN + rate) and doc_issue (the
invoice and credit-note number ranges). Dates dd-mm-yyyy, the period MMYYYY, amounts rounded to 2 decimals.
Not covered: exports, nil-rated / exempt tables, advances, amendments, e-commerce operator tables, the 2025 split of the HSN
table into B2B / B2C - the offline tool shows anything to complete."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select

from ..db import session
from ..site import webapp as W
from .models import AppProject

B2CL_LIMIT = 100000.0
STATS = {"files": 0}


def _dmy(day: str) -> str:
    try:
        return datetime.strptime(day, "%d %b %Y").strftime("%d-%m-%Y")
    except (TypeError, ValueError):
        return ""


def _items(lines: list[dict[str, Any]], inter: bool) -> list[dict[str, Any]]:
    by: dict[float, dict[str, float]] = {}
    for ln in lines:
        b = by.setdefault(float(ln["rate"]), {"txval": 0.0, "iamt": 0.0, "camt": 0.0, "samt": 0.0})
        b["txval"] += ln["taxable"]
        b["iamt"] += ln["igst"]
        b["camt"] += ln["cgst"]
        b["samt"] += ln["sgst"]
    return [{"num": i + 1, "itm_det": {"rt": rt, "txval": round(v["txval"], 2), "iamt": round(v["iamt"], 2) if inter else 0,
                                       "camt": 0 if inter else round(v["camt"], 2), "samt": 0 if inter else round(v["samt"], 2), "csamt": 0}}
            for i, (rt, v) in enumerate(sorted(by.items()))]


def _range(nos: list[str]) -> list[dict[str, Any]]:
    if not nos:
        return []
    nos = sorted(nos)
    return [{"num": 1, "from": nos[0], "to": nos[-1], "totnum": len(nos), "cancel": 0, "net_issue": len(nos)}]


def build(r: AppProject, month: str) -> dict[str, Any]:
    from . import backend as BE
    from . import gst as G
    from . import hisaab as HS
    month = month or HS.default_month()
    if not HS.MONTH.match(month):
        raise HS.HisaabError("Mahina YYYY-MM (jaise 2026-10).")
    g = G.settings(r)
    if not g.get("gstin"):
        raise HS.HisaabError("GSTR-1 ke liye pehle GSTIN daaliye (GST invoices).", 409)
    sch = BE.schema(r)
    colls = {c["key"]: c for c in sch["collections"]}
    with session() as s:
        rows = s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == BE.bid(r))).all()
        for x in rows:
            s.expunge(x)
    b2b: dict[str, list] = {}
    b2cl: dict[str, list] = {}
    b2cs: dict[tuple[str, str, float], dict[str, float]] = {}
    cdnr: dict[str, list] = {}
    cdnur: list = []
    hsn: dict[tuple[str, float], dict[str, float]] = {}
    inv_nos, cn_nos = [], []

    def add_b2cs(lines, inter, pos, sign):
        for ln in lines:
            k = ("INTER" if inter else "INTRA", pos, float(ln["rate"]))
            b = b2cs.setdefault(k, {"txval": 0.0, "iamt": 0.0, "camt": 0.0, "samt": 0.0})
            b["txval"] += sign * ln["taxable"]
            b["iamt"] += sign * ln["igst"]
            b["camt"] += sign * ln["cgst"]
            b["samt"] += sign * ln["sgst"]

    def add_hsn(lines, sign):
        for ln in lines:
            h = hsn.setdefault((ln["hsn"] or "-", float(ln["rate"])), {"qty": 0, "txval": 0.0, "iamt": 0.0, "camt": 0.0, "samt": 0.0})
            h["qty"] += sign * ln["qty"]
            h["txval"] += sign * ln["taxable"]
            h["iamt"] += sign * ln["igst"]
            h["camt"] += sign * ln["cgst"]
            h["samt"] += sign * ln["sgst"]

    for x in rows:
        c = colls.get(x.coll)
        if c is None:
            continue
        d = BE._j(x.data, {})
        for kind, no_key, day_key in (("inv", "_inv_no", "_inv_date"), ("cn", "_cn_no", "_cn_date")):
            if not d.get(no_key) or HS._month_of_day(d.get(day_key, "")) != month:
                continue
            gx = G.compute(r, c, d)
            val = round(gx["totals"]["amount"], 2)
            buyer, inter, pos = gx["buyer_gstin"], gx["inter"], gx["pos"]
            big = (not buyer) and inter and val > B2CL_LIMIT
            if kind == "inv":
                inv_nos.append(d[no_key])
                row = {"inum": d[no_key], "idt": _dmy(d.get(day_key, "")), "val": val, "pos": pos, "itms": _items(gx["lines"], inter)}
                if buyer:
                    b2b.setdefault(buyer, []).append({**row, "rchrg": "N", "inv_typ": "R"})
                elif big:
                    b2cl.setdefault(pos, []).append(row)
                else:
                    add_b2cs(gx["lines"], inter, pos, 1)
                add_hsn(gx["lines"], 1)
            else:
                cn_nos.append(d[no_key])
                note = {"ntty": "C", "nt_num": d[no_key], "nt_dt": _dmy(d.get(day_key, "")), "val": val, "pos": pos,
                        "itms": _items(gx["lines"], inter)}
                if buyer:
                    cdnr.setdefault(buyer, []).append({**note, "rchrg": "N", "inv_typ": "R"})
                elif big:
                    cdnur.append({**note, "typ": "B2CL"})
                else:
                    add_b2cs(gx["lines"], inter, pos, -1)        # a consumer credit note nets the B2CS figure
                add_hsn(gx["lines"], -1)
    out: dict[str, Any] = {"gstin": g["gstin"], "fp": month[5:7] + month[:4]}
    if b2b:
        out["b2b"] = [{"ctin": k, "inv": v} for k, v in sorted(b2b.items())]
    if b2cl:
        out["b2cl"] = [{"pos": k, "inv": v} for k, v in sorted(b2cl.items())]
    rows_cs = [{"sply_ty": k[0], "pos": k[1], "typ": "OE", "rt": k[2], "txval": round(v["txval"], 2),
                "iamt": round(v["iamt"], 2), "camt": round(v["camt"], 2), "samt": round(v["samt"], 2), "csamt": 0}
               for k, v in sorted(b2cs.items()) if abs(v["txval"]) >= 0.005]
    if rows_cs:
        out["b2cs"] = rows_cs
    if cdnr:
        out["cdnr"] = [{"ctin": k, "nt": v} for k, v in sorted(cdnr.items())]
    if cdnur:
        out["cdnur"] = cdnur
    hrows = [{"num": i + 1, "hsn_sc": k[0], "desc": "", "uqc": "NOS", "qty": v["qty"], "rt": k[1], "txval": round(v["txval"], 2),
              "iamt": round(v["iamt"], 2), "camt": round(v["camt"], 2), "samt": round(v["samt"], 2), "csamt": 0}
             for i, (k, v) in enumerate(sorted(hsn.items())) if abs(v["txval"]) >= 0.005]
    if hrows:
        out["hsn"] = {"data": hrows}
    docs = []
    if inv_nos:
        docs.append({"doc_num": 1, "docs": _range(inv_nos)})          # 1 = invoices for outward supply
    if cn_nos:
        docs.append({"doc_num": 5, "docs": _range(cn_nos)})           # 5 = credit notes
    if docs:
        out["doc_issue"] = {"doc_det": docs}
    STATS["files"] += 1
    return out


def file_bytes(r: AppProject, month: str) -> tuple[bytes, str]:
    from . import hisaab as HS
    data = build(r, month)
    m = month or HS.default_month()
    return json.dumps(data, ensure_ascii=False, indent=1).encode(), f"GSTR1-{data['gstin']}-{m}.json"
