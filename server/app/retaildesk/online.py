"""#38 RTO risk, #78 settlement reconcile, #32 claim check, #86 landed cost, #90 shop scam signals, #79 GST split. Heuristics are labelled; the seller / shopper / CA decides."""
from __future__ import annotations

import re
from typing import Any

from ..finguard import scam as SC


def _f(v: Any) -> float:
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def rto_risk(orders: list[dict]) -> dict[str, Any]:
    if not orders:
        raise ValueError("Give orders rows: id, address, pincode, phone, cod (true/false), amount, prior_rto.")
    out = []
    for o in orders[:5000]:
        pts, why = 0, []
        addr = str(o.get("address") or "")
        if not re.fullmatch(r"\d{6}", str(o.get("pincode") or "").strip()):
            pts += 3
            why.append("pincode does not have 6 numerals")
        if len(addr.strip()) < 25:
            pts += 2
            why.append("address is too short")
        if not re.search(r"\d", addr):
            pts += 2
            why.append("no house / plot number in the address")
        if not re.fullmatch(r"[6-9]\d{9}", re.sub(r"\D", "", str(o.get("phone") or ""))[-10:] or "x"):
            pts += 3
            why.append("phone number does not have 10 numerals")
        if o.get("cod") in (True, "true", "yes", "1", 1):
            pts += 2
            why.append("COD order")
            if _f(o.get("amount")) >= 3000:
                pts += 1
                why.append("large COD amount")
        if _f(o.get("prior_rto")) > 0:
            pts += 3
            why.append("this customer had an RTO before")
        out.append({"id": o.get("id"), "points": pts, "level": "high" if pts >= 7 else ("medium" if pts >= 4 else "low"), "why": why,
                    "suggest": {"high": "Confirm with the customer before dispatch (call / WhatsApp)", "medium": "Check the address and phone once"}.get(
                        "high" if pts >= 7 else ("medium" if pts >= 4 else ""), "")})
    return {"orders": out, "high": sum(r["level"] == "high" for r in out), "kind": "heuristic score, not a verdict on the customer",
            "note": "This count is on plain signals like address / phone / COD. Stopping a customer or cancelling an order is your decision.",
            "decider": "The confirm call, dispatch or cancel is the owner's / ops manager's tap."}


def reconcile(sales: list[dict], settlements: list[dict], tolerance: Any = 1.0) -> dict[str, Any]:
    if not sales or not settlements:
        raise ValueError("Give sales and settlements rows: [{ref, amount}] / [{ref, amount, fee}].")
    tol = _f(tolerance)
    st = {str(s.get("ref")): s for s in settlements}
    seen, rows = set(), []
    for s in sales:
        ref = str(s.get("ref"))
        a = _f(s.get("amount"))
        got = st.get(ref)
        if not got:
            rows.append({"ref": ref, "sale": a, "status": "not_settled"})
            continue
        seen.add(ref)
        net = _f(got.get("amount"))
        fee = _f(got.get("fee"))
        diff = round(a - fee - net, 2)
        rows.append({"ref": ref, "sale": a, "fee": fee, "received": net, "difference": diff, "status": "match" if abs(diff) <= tol else "difference"})
    extra = [{"ref": r, "received": _f(st[r].get("amount")), "status": "not_in_sales"} for r in st if r not in seen]
    bad = [r for r in rows if r["status"] != "match"] + extra
    return {"rows": rows + extra, "matched": sum(r["status"] == "match" for r in rows), "to_check": len(bad),
            "fees_total": round(sum(_f(s.get("fee")) for s in settlements), 2),
            "not_checked": "GST on the fee, the reason for a chargeback, the COD remittance timeline.",
            "decider": "Disputes with the gateway / courier and corrections to the books are done by your accountant."}


_CLAIMS = [(r"\b100\s*%\s*(genuine|original|authentic|pure|natural|safe)\b", "absolute claim"), (r"\b(cure[sd]?|treats?|heals?|diabetes|cancer|covid)\b", "health claim"),
           (r"\b(no\.?\s*1|best in (india|world)|number one)\b", "superlative claim"), (r"\b(guarantee[d]?|risk[- ]free|money back for sure)\b", "guarantee claim"),
           (r"\b(only|last|hurry)\s+\d+\s*(left|pieces?|units?)\b", "scarcity claim - must be true"), (r"\b(organic|fssai|iso|bis|isi|ayush)\b", "certification claim - needs proof")]


def claims(text: str, spec: dict | None = None) -> dict[str, Any]:
    t = str(text or "")
    if not t.strip():
        raise ValueError("Give text (product title / description).")
    flags = []
    for pat, kind in _CLAIMS:
        for m in re.finditer(pat, t, re.I):
            flags.append({"words": m.group(0), "kind": kind, "ask": "Do you have proof / a spec for this? If not, remove it or soften it."})
    missing = [k for k in ("brand", "weight_or_size", "mrp", "hsn", "country_of_origin", "manufacturer") if not (spec or {}).get(k)]
    return {"flags": flags, "missing_listing_facts": missing,
            "note": "This works from a word list; which claim is true is known to you / the merchandiser. Packaged goods need details such as weights and measures, MRP and the manufacturer's address (verify).",
            "decider": "Whether to publish the listing and keep the claims is the merchandiser's / owner's decision."}


def landed(offers: list[dict]) -> dict[str, Any]:
    if not offers:
        raise ValueError("Give offers rows: seller, price, shipping, cod_fee, coupon_off, return_days.")
    rows = []
    for o in offers[:200]:
        total = _f(o.get("price")) + _f(o.get("shipping")) + _f(o.get("cod_fee")) - _f(o.get("coupon_off"))
        rows.append({"seller": o.get("seller"), "landed_total": round(total, 2), "return_days": o.get("return_days"), "price": _f(o.get("price"))})
    rows.sort(key=lambda r: r["landed_total"])
    note = "The cheapest landed total is different from the sticker price." if rows and rows[0]["price"] != min(r["price"] for r in rows) else ""
    return {"ranked": rows, "cheapest": rows[0]["seller"], "note": note, "not_checked": "Whether the seller is genuine, whether the coupon is genuine, the product's quality.",
            "decider": "Buying is on your tap; nothing was bought here."}


def shop_scam(url: str = "", price: Any = None, market_price: Any = None, text: str = "") -> dict[str, Any]:
    if not (url or text):
        raise ValueError("Give url or text.")
    sig = []
    res: dict[str, Any] = {}
    if url:
        res["link"] = SC.analyse_url(url)
    p, m = _f(price), _f(market_price)
    if p and m and p < 0.5 * m:
        sig.append(f"Price {p:g} is less than half the market's {m:g}: too-good-to-be-true.")
    for pat, why in ((r"\b(pay|send)\b.*\b(advance|upi|gift card)\b", "asks for money first"), (r"\b(only|just)\b.*\b(whatsapp|telegram)\b", "orders only on chat"),
                     (r"\b(cash on delivery not available|no returns?)\b", "no COD / returns"), (r"\b(last chance|offer ends|hurry)\b", "pushes you to hurry")):
        if re.search(pat, text or "", re.I):
            sig.append(why)
    return {"signals": sig, **res, "kind": "signals, not proof", "next": "Start with a small order / COD; never give a card or OTP; for a complaint use the platform or the consumer helpline.",
            "decider": "To buy or not is your decision."}


def gst_split(lines: list[dict], seller_state: str = "", buyer_state: str = "", price_includes_gst: bool = True) -> dict[str, Any]:
    if not lines:
        raise ValueError("Give lines rows: name, qty, price, gst_pct (and hsn).")
    intra = bool(seller_state and buyer_state and seller_state.strip().lower() == buyer_state.strip().lower())
    rows, tt, tx = [], 0.0, 0.0
    for l in lines[:500]:
        gross = _f(l.get("qty")) * _f(l.get("price"))
        r = _f(l.get("gst_pct"))
        taxable = gross * 100 / (100 + r) if price_includes_gst else gross
        tax = gross - taxable if price_includes_gst else taxable * r / 100
        row = {"name": l.get("name"), "hsn": l.get("hsn"), "taxable": round(taxable, 2), "gst_pct": r}
        if intra:
            row.update(cgst=round(tax / 2, 2), sgst=round(tax / 2, 2))
        else:
            row.update(igst=round(tax, 2))
        row["line_total"] = round(taxable + tax, 2)
        rows.append(row)
        tt += taxable
        tx += tax
    return {"lines": rows, "taxable_total": round(tt, 2), "tax_total": round(tx, 2), "grand_total": round(tt + tx, 2),
            "supply": "intra-state (CGST+SGST)" if intra else "inter-state (IGST)" if (seller_state and buyer_state) else "state not given: IGST assumed",
            "missing_hsn": [l.get("name") for l in lines if not l.get("hsn")],
            "not_checked": "Whether the rate is right (you give it), composition scheme, e-invoice threshold, rounding rules.",
            "decider": "Issuing the invoice and filing GST is done by you / your CA."}
