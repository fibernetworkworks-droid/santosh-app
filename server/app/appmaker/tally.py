"""v0.374 TALLY EXPORT (App Sahayak Phase 38, owner: "START PHASE 38"): the month's tax invoices and credit notes as a Tally
XML file she (or her CA) imports in Tally (Gateway of Tally > Import > Vouchers), made from the same numbers as the invoices
(gst.compute). Each invoice = a Sales voucher, each credit note = a Credit Note voucher, accounting-invoice style: the party
ledger debited / credited with the total, the sales ledger with the taxable value, and the output tax ledgers with CGST + SGST
or IGST. Ledger names default to the usual ones and are hers to change (gst settings `tally`), because Tally imports into
ledgers that already exist in her company. Hoola never connects to her Tally; Tally validates the file on import."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from xml.sax.saxutils import escape

from sqlalchemy import select

from ..db import session
from ..site import webapp as W
from .models import AppProject
from . import locks as LK                     # v0.388 one cross-process lock per app

DEFAULTS = {"party": "Cash", "sales": "Sales", "cgst": "Output CGST", "sgst": "Output SGST", "igst": "Output IGST",
            "round": "Round Off"}
STATS = {"files": 0}


def names(r: AppProject) -> dict[str, str]:
    from . import gst as G
    return {**DEFAULTS, **{k: v for k, v in (G.settings(r).get("tally") or {}).items() if k in DEFAULTS and v}}


def set_names(r: AppProject, body: dict[str, Any]) -> dict[str, str]:
    """Her Tally ledger names (must match ledgers in her Tally company)."""
    import json as _json
    from . import backend as BE
    from . import gst as G
    clean = {}
    for k, v in (body or {}).items():
        if k in DEFAULTS:
            v = re.sub(r"[\x00-\x1f<>&\"]+", " ", str(v or "")).strip()[:60]
            if v:
                clean[k] = v
    with LK.app(r.id), session() as s:
        row = s.get(AppProject, r.id)
        be = BE._j(row.backend, {})
        g = dict(be.get("gst") or {})
        g["tally"] = {**(g.get("tally") or {}), **clean}
        be["gst"] = g
        row.backend = _json.dumps(be, ensure_ascii=False)
        r.backend = row.backend
    return names(r)


def _ymd(day: str) -> str:
    try:
        return datetime.strptime(day, "%d %b %Y").strftime("%Y%m%d")
    except (TypeError, ValueError):
        return ""


def _entry(ledger: str, amount: float, debit: bool) -> str:
    # Tally: a debit is ISDEEMEDPOSITIVE Yes with a NEGATIVE amount; a credit is No with a positive amount
    a = -abs(amount) if debit else abs(amount)
    return (f"<ALLLEDGERENTRIES.LIST><LEDGERNAME>{escape(ledger)}</LEDGERNAME><ISDEEMEDPOSITIVE>{'Yes' if debit else 'No'}"
            f"</ISDEEMEDPOSITIVE><AMOUNT>{a:.2f}</AMOUNT></ALLLEDGERENTRIES.LIST>")


def voucher(kind: str, no: str, day: str, party_name: str, x: dict[str, Any], ln: dict[str, str], note: str) -> str:
    """One voucher. Sales: party Dr total / sales Cr taxable / taxes Cr. Credit Note: the mirror image."""
    t = x["totals"]
    sale = kind == "Sales"
    rows = [_entry(ln["party"], t["amount"], sale), _entry(ln["sales"], t["taxable"], not sale)]
    for k in ("cgst", "sgst", "igst"):
        if t[k]:
            rows.append(_entry(ln[k], t[k], not sale))
    diff = round(t["amount"] - t["taxable"] - t["cgst"] - t["sgst"] - t["igst"], 2)      # paise left by rounding
    if diff:
        rows.append(_entry(ln["round"], diff, not sale))
    return (f'<TALLYMESSAGE xmlns:UDF="TallyUDF"><VOUCHER VCHTYPE="{kind}" ACTION="Create" OBJVIEW="Accounting Voucher View">'
            f"<DATE>{_ymd(day)}</DATE><VOUCHERTYPENAME>{kind}</VOUCHERTYPENAME><VOUCHERNUMBER>{escape(no)}</VOUCHERNUMBER>"
            f"<PARTYLEDGERNAME>{escape(ln['party'])}</PARTYLEDGERNAME><BASICBUYERNAME>{escape(party_name[:80])}</BASICBUYERNAME>"
            + (f"<PARTYGSTIN>{escape(x['buyer_gstin'])}</PARTYGSTIN>" if x.get("buyer_gstin") else "")
            + f"<PLACEOFSUPPLY>{escape(x.get('pos_name') or '')}</PLACEOFSUPPLY><NARRATION>{escape(note[:200])}</NARRATION>"
            f"<PERSISTEDVIEW>Accounting Voucher View</PERSISTEDVIEW>{''.join(rows)}</VOUCHER></TALLYMESSAGE>")


def build(r: AppProject, month: str) -> tuple[str, int]:
    from . import backend as BE
    from . import gst as G
    from . import hisaab as HS
    month = month or HS.default_month()
    if not HS.MONTH.match(month):
        raise HS.HisaabError("Mahina YYYY-MM (jaise 2026-10).")
    ln = names(r)
    sch = BE.schema(r)
    colls = {c["key"]: c for c in sch["collections"]}
    with session() as s:
        rows = s.scalars(select(W.SiteAppRow).where(W.SiteAppRow.site_id == BE.bid(r))).all()
        for x in rows:
            s.expunge(x)
    out, n = [], 0
    for row in sorted(rows, key=lambda y: y.created_at or datetime.min):
        c = colls.get(row.coll)
        if c is None:
            continue
        d = BE._j(row.data, {})
        who = str(d.get("name") or d.get("customer") or "Customer")
        for kind, no_key, day_key in (("Sales", "_inv_no", "_inv_date"), ("Credit Note", "_cn_no", "_cn_date")):
            if d.get(no_key) and HS._month_of_day(d.get(day_key, "")) == month:
                x = G.compute(r, c, d)
                note = (f"{c['label']} {row.id[-6:].upper()} from the {r.name or 'app'} app" if kind == "Sales"
                        else f"Against {d.get('_inv_no', '')}: {d.get('_cn_reason') or 'Order cancelled'}")
                out.append(voucher(kind, d[no_key], d.get(day_key, ""), who, x, ln, note))
                n += 1
    xml = ('<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDESC>'
           '<REPORTNAME>Vouchers</REPORTNAME></REQUESTDESC><REQUESTDATA>' + "".join(out) + "</REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>")
    STATS["files"] += 1
    return xml, n


def file_bytes(r: AppProject, month: str) -> tuple[bytes, str, int]:
    from . import hisaab as HS
    xml, n = build(r, month)
    return xml.encode("utf-8"), f"tally-{(r.number or 'app').replace(' ', '')}-{month or HS.default_month()}.xml", n
