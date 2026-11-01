"""v0.355 GST BILL (App Sahayak Phase 19, owner: "START PHASE 19"): a GST tax invoice for a GST-registered business.

She sets her GSTIN once per app (checked: format + the GSTIN check digit; her state comes from its first two digits), a
default rate (0 / 0.25 / 3 / 5 / 12 / 18 / 28 %) and optional HSN / SAC + rate per product. Then the receipt of a finished row
(v0.354 RASEED) becomes a TAX INVOICE with the Rule 46 particulars: supplier name, address and GSTIN; a consecutive invoice
number unique for the financial year (INV/2026-27/0001), given ONCE per row and never reused; date; recipient name and
address (+ GSTIN for a business buyer); place of supply with its state; HSN / SAC, quantity, taxable value, rate and the tax -
CGST + SGST inside her state, IGST outside it - and the total in figures.

Prices are taken as GST-INCLUSIVE (the shelf / MRP price the customer already paid), so the invoice total is always exactly
the server-priced order total - no customer is ever charged more by an invoice. (GST-exclusive pricing would change what the
app charges; not done here.) Credit notes for a row cancelled after its invoice, e-invoicing (IRN, turnover above the
notified limit) and GST returns are NOT done; she files with her CA."""
from __future__ import annotations

import json
import re
import threading
from datetime import timedelta
from typing import Any

from ..db import now, session
from ..site import webapp as W
from .models import AppProject
from . import locks as LK                     # v0.388 one cross-process lock per app

STATES = {"01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh", "05": "Uttarakhand",
          "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim",
          "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur", "15": "Mizoram", "16": "Tripura", "17": "Meghalaya",
          "18": "Assam", "19": "West Bengal", "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh",
          "24": "Gujarat", "26": "Dadra and Nagar Haveli and Daman and Diu", "27": "Maharashtra", "29": "Karnataka", "30": "Goa",
          "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry", "35": "Andaman and Nicobar Islands",
          "36": "Telangana", "37": "Andhra Pradesh", "38": "Ladakh", "97": "Other Territory"}
ALIASES = {"orissa": "21", "pondicherry": "34", "bombay": "27", "mumbai": "27", "pune": "27", "nagpur": "27", "akola": "27",
           "bangalore": "29", "bengaluru": "29", "chennai": "33", "kolkata": "19", "hyderabad": "36", "new delhi": "07",
           "gurgaon": "06", "gurugram": "06", "noida": "09", "ahmedabad": "24", "jaipur": "08", "lucknow": "09", "patna": "10"}
RATES = (0, 0.25, 3, 5, 12, 18, 28)
GSTIN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
HSN = re.compile(r"^[0-9]{4,8}$")
_CH = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_LOCK = threading.Lock()
STATS = {"invoices": 0, "numbers": 0}


class GstError(W.AppError):
    pass


def check_digit(first14: str) -> str:
    total = 0
    for i, c in enumerate(first14):
        p = _CH.index(c) * (2 if i % 2 else 1)
        total += p // 36 + p % 36
    return _CH[(36 - total % 36) % 36]


def valid_gstin(g: str) -> bool:
    g = (g or "").strip().upper()
    return bool(GSTIN.match(g)) and g[:2] in STATES and check_digit(g[:14]) == g[14]


def _be(r: AppProject) -> dict[str, Any]:
    from . import backend as BE
    return BE.ensure(r)


def settings(r: AppProject) -> dict[str, Any]:
    return dict(_be(r).get("gst") or {})


def on(r: AppProject) -> bool:
    return bool(settings(r).get("gstin"))


def view(r: AppProject) -> dict[str, Any]:
    g = settings(r)
    from . import backend as BE
    prods = [{"id": k, "name": p.get("name"), "price": p.get("price"), **(g.get("items", {}).get(k) or {})}
             for k, p in list(BE._base_products(r).items())[:200]]
    return {"on": bool(g.get("gstin")), "gstin": g.get("gstin", ""), "legal_name": g.get("legal_name", ""),
            "state": STATES.get(str(g.get("gstin", ""))[:2], ""), "rate": g.get("rate", 18), "hsn": g.get("hsn", ""),
            "inclusive": True, "products": prods, "rates": list(RATES), "issued": g.get("issued", 0),
            "note": "Prices are GST-inclusive: an invoice never changes what the customer pays. Returns / credit notes / e-invoicing stay with your CA."}


def set_settings(r: AppProject, body: dict[str, Any]) -> dict[str, Any]:
    """Her GST details. gstin "" switches tax invoices off (plain receipts again); issued numbers are kept."""
    body = body if isinstance(body, dict) else {}
    from . import backend as BE
    with LK.app(r.id), session() as s:
        row = s.get(AppProject, r.id)
        be = BE._j(row.backend, {})
        g = dict(be.get("gst") or {})
        if "gstin" in body:
            v = str(body.get("gstin") or "").strip().upper().replace(" ", "")
            if v and not valid_gstin(v):
                raise GstError("GSTIN sahi nahi lag raha (15 akshar, aakhri check digit milna chahiye). Certificate se dobara dekhiye.")
            g["gstin"] = v
        if "legal_name" in body:
            g["legal_name"] = re.sub(r"[\x00-\x1f]+", " ", str(body.get("legal_name") or "")).strip()[:120]
        if "rate" in body:
            g["rate"] = _rate(body.get("rate"))
        if "hsn" in body:
            g["hsn"] = _hsn(body.get("hsn"))
        if isinstance(body.get("items"), dict):            # {product id: {hsn, rate}}
            items = dict(g.get("items") or {})
            prods = BE._base_products(r)
            for k, v in list(body["items"].items())[:500]:
                if str(k) not in prods or not isinstance(v, dict):
                    continue
                cur = dict(items.get(str(k)) or {})
                if "hsn" in v:
                    cur["hsn"] = _hsn(v.get("hsn"))
                if "rate" in v:
                    cur["rate"] = _rate(v.get("rate")) if v.get("rate") not in (None, "") else None
                items[str(k)] = {x: y for x, y in cur.items() if y not in (None, "")}
            g["items"] = items
        be["gst"] = g
        row.backend = json.dumps(be, ensure_ascii=False)
        r.backend = row.backend
    return view(r)


def _rate(v: Any) -> float:
    try:
        f = float(str(v).replace("%", "").strip())
    except (TypeError, ValueError):
        raise GstError("GST rate: " + ", ".join(f"{x:g}" for x in RATES) + " mein se.")
    if f not in RATES:
        raise GstError("GST rate: " + ", ".join(f"{x:g}" for x in RATES) + " mein se.")
    return int(f) if f == int(f) else f


def _hsn(v: Any) -> str:
    s = re.sub(r"\s+", "", str(v or ""))
    if s and not HSN.match(s):
        raise GstError("HSN / SAC code 4 se 8 ank ka hota hai.")
    return s


def fy(dt=None) -> str:
    """The Indian financial year (April - March, IST) as 2026-27."""
    d = (dt or now()) + timedelta(hours=5, minutes=30)
    y = d.year if d.month >= 4 else d.year - 1
    return f"{y}-{str(y + 1)[2:]}"


def number_for(r: AppProject, row_id: str) -> tuple[str, str]:
    """The row's invoice number + date: given ONCE (consecutive per financial year), the same forever after."""
    from . import backend as BE
    with LK.app(r.id), session() as s:
        row = s.get(W.SiteAppRow, row_id)
        d = BE._j(row.data, {})
        if d.get("_inv_no"):
            return d["_inv_no"], d.get("_inv_date", "")
        app = s.get(AppProject, r.id)
        be = BE._j(app.backend, {})
        g = dict(be.get("gst") or {})
        year = fy()
        seq = dict(g.get("seq") or {})
        n = int(seq.get(year) or 0) + 1
        seq[year] = n
        g["seq"], g["issued"] = seq, int(g.get("issued") or 0) + 1
        be["gst"] = g
        no = f"INV/{year}/{n:04d}"
        day = (now() + timedelta(hours=5, minutes=30)).strftime("%d %b %Y")
        d.update({"_inv_no": no, "_inv_date": day})
        row.data, app.backend = json.dumps(d, ensure_ascii=False), json.dumps(be, ensure_ascii=False)
    STATS["numbers"] += 1
    return no, day


LINE = re.compile(r"^\s*(\d+)\s*x\s*(.+?)(?:\s*@\s*Rs\s*([\d.]+))?\s*$")


def _state_of(text: str) -> str:
    t = " " + re.sub(r"[^a-z ]+", " ", (text or "").lower()) + " "
    for code, name in STATES.items():
        if f" {name.lower()} " in t:
            return code
    for k, code in ALIASES.items():
        if f" {k} " in t:
            return code
    return ""


def compute(r: AppProject, c: dict[str, Any], d: dict[str, Any]) -> dict[str, Any]:
    """The tax lines of a row (GST-inclusive prices): [{name, hsn, qty, rate, taxable, cgst, sgst, igst, amount}] + totals."""
    from . import backend as BE
    g = settings(r)
    home = str(g.get("gstin", ""))[:2]
    buyer = ""
    for f in c["fields"]:
        v = str(d.get(f["key"]) or "").strip().upper().replace(" ", "")
        if ("gst" in f["key"].lower() or "gst" in str(f.get("label", "")).lower()) and valid_gstin(v):
            buyer = v
    text = " ".join(str(d.get(f["key"]) or "") for f in c["fields"]          # her customer's own words (never the item names)
                    if (f.get("type") in ("text", "long_text", "location") or f["key"] in ("address", "city", "state"))
                    and f["key"] not in ("items", "utr", "status", "paid", "name") and not f.get("admin_only"))
    pos = buyer[:2] if buyer else (_state_of(text) or home)
    inter = pos != home
    by_name = {str(p.get("name") or "").strip().lower(): k for k, p in BE._products(r).items()}
    prods = BE._products(r)
    lines, raw = [], [ln for ln in str(d.get("items") or "").splitlines() if ln.strip()]
    for ln in raw[:80]:
        m = LINE.match(ln)
        if not m:
            continue
        q, name, price = int(m.group(1)), m.group(2).strip(), m.group(3)
        pid = by_name.get(name.lower(), "")
        if price is None:
            price = (prods.get(pid) or {}).get("price") or 0
        lines.append({"pid": pid, "name": name, "qty": q, "gross": round(float(price) * q, 2)})
    if not lines and d.get("total") not in (None, ""):            # a booking / request with a price: one line
        lines.append({"pid": "", "name": c["label"], "qty": 1, "gross": round(float(d.get("total") or 0), 2)})
    total = float(d.get("total") or 0) if d.get("total") not in (None, "") else sum(x["gross"] for x in lines)
    fee = float(d.get("_delivery") or 0)                         # v0.360 DELIVERY: its own line; the goods share the rest
    if fee and lines and lines[-1]["pid"] == "" and lines[-1]["name"] == c["label"]:
        lines[-1]["gross"] = round(lines[-1]["gross"] - fee, 2)
    total = round(total - fee, 2)
    gsum = sum(x["gross"] for x in lines)
    if lines and gsum > 0 and abs(gsum - total) > 0.01:         # the server total is the truth (v0.358 a coupon: spread over
        f = total / gsum                                        # every line, so each line's tax is right); rounding -> last line
        for x in lines:
            x["gross"] = round(x["gross"] * f, 2)
        lines[-1]["gross"] = round(lines[-1]["gross"] + (total - sum(x["gross"] for x in lines)), 2)
    if fee > 0:
        lines.append({"pid": "_delivery", "name": "Delivery charges", "qty": 1, "gross": round(fee, 2)})
    out, t = [], {"taxable": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0, "amount": 0.0}
    for x in lines:
        base_pid = x["pid"].split("::")[0]               # v0.362 a size keeps its product's HSN / rate
        it = {"hsn": "9968"} if x["pid"] == "_delivery" else ((g.get("items") or {}).get(x["pid"]) or (g.get("items") or {}).get(base_pid, {})
                                                                if x["pid"] else {})
        rate = float(it.get("rate") if it.get("rate") is not None else g.get("rate", 18))
        taxable = round(x["gross"] / (1 + rate / 100), 2)
        tax = round(x["gross"] - taxable, 2)
        cg = 0.0 if inter else round(tax / 2, 2)
        sg = 0.0 if inter else round(tax - cg, 2)
        ig = tax if inter else 0.0
        row = {"name": x["name"], "hsn": it.get("hsn") or g.get("hsn", ""), "qty": x["qty"], "rate": rate,
               "taxable": taxable, "cgst": cg, "sgst": sg, "igst": ig, "amount": x["gross"]}
        out.append(row)
        for k in t:
            t[k] = round(t[k] + row[k], 2)
    return {"lines": out, "totals": t, "inter": inter, "pos": pos, "pos_name": STATES.get(pos, ""), "buyer_gstin": buyer,
            "gstin": g.get("gstin", ""), "legal_name": g.get("legal_name", ""), "home_name": STATES.get(home, "")}


def words(n: float) -> str:
    """Rupees in words, Indian system (lakh / crore), for the invoice total."""
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen",
            "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def two(x):
        return ones[x] if x < 20 else tens[x // 10] + ("" if x % 10 == 0 else " " + ones[x % 10])

    def three(x):
        return (ones[x // 100] + " Hundred" + (" " + two(x % 100) if x % 100 else "")) if x >= 100 else two(x)

    rs, paise = int(n), round((n - int(n)) * 100)
    if rs == 0:
        out = "Zero"
    else:
        parts, crore, rs2 = [], rs // 10000000, rs % 10000000
        if crore:
            parts.append(three(crore) + " Crore") if crore < 1000 else parts.append(str(crore) + " Crore")
        lakh, rs2 = rs2 // 100000, rs2 % 100000
        if lakh:
            parts.append(two(lakh) + " Lakh")
        th, rs2 = rs2 // 1000, rs2 % 1000
        if th:
            parts.append(two(th) + " Thousand")
        if rs2:
            parts.append(three(rs2))
        out = " ".join(parts)
    return "Rupees " + out + (f" and {two(paise)} Paise" if paise else "") + " Only"



# ---------------------------------------------------------------- v0.356 WAPSI (App Sahayak Phase 20): GST credit notes
# A row that already carries a tax invoice and is then cancelled (or that she marks as returned) gets a CREDIT NOTE for
# the full value (Section 34): its own consecutive series per financial year (CN/2026-27/0001), given once, referring to
# the original invoice number + date, same place of supply and tax split as the invoice, and the reason. Money never moves
# here - a refund (if any) is hers to make; the credit note only records it. Partial credit notes are not made.
STATS.update({"credit_notes": 0})


def credit_for(r: AppProject, row_id: str, reason: str = "") -> tuple[str, str] | None:
    """The row's credit note number + date (given ONCE). None when the row has no invoice (nothing to credit)."""
    from . import backend as BE
    reason = re.sub(r"[\x00-\x1f]+", " ", str(reason or "")).strip()[:200] or "Order cancelled"
    with LK.app(r.id), session() as s:
        row = s.get(W.SiteAppRow, row_id)
        if row is None:
            return None
        d = BE._j(row.data, {})
        if not d.get("_inv_no"):
            return None
        if d.get("_cn_no"):
            return d["_cn_no"], d.get("_cn_date", "")
        app = s.get(AppProject, r.id)
        be = BE._j(app.backend, {})
        g = dict(be.get("gst") or {})
        year = fy()
        seq = dict(g.get("cn_seq") or {})
        n = int(seq.get(year) or 0) + 1
        seq[year] = n
        g["cn_seq"], g["credited"] = seq, int(g.get("credited") or 0) + 1
        be["gst"] = g
        no = f"CN/{year}/{n:04d}"
        day = (now() + timedelta(hours=5, minutes=30)).strftime("%d %b %Y")
        d.update({"_cn_no": no, "_cn_date": day, "_cn_reason": reason})
        row.data, app.backend = json.dumps(d, ensure_ascii=False), json.dumps(be, ensure_ascii=False)
    STATS["credit_notes"] += 1
    return no, day


def credit(r: AppProject, coll: str, row_id: str, reason: str = "") -> dict[str, Any]:
    """Her own credit note for an invoiced row (a return / a wrong bill): full value, with her reason."""
    from . import backend as BE
    with session() as s:
        row = s.get(W.SiteAppRow, row_id)
        if row is None or row.site_id != BE.bid(r) or row.coll != coll:
            raise GstError("Yeh entry nahi mili.", 404)
    got = credit_for(r, row_id, reason or "Goods returned / bill corrected")
    if got is None:
        raise GstError("Is entry ka tax invoice abhi bana hi nahi; credit note sirf invoice ke baad banta hai.", 409)
    return {"credit_note": got[0], "date": got[1], "row": row_id}
