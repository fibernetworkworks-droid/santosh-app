"""F4 of docs/FINANCE_GLOBAL_PLAN.md - Tax worldwide (employee `tax`, tool `tax_worldwide`), for people, sole traders and businesses in
any country. It reads her own books (F3) and statements (the spine), never the model's memory:

  settings     her tax registration: country, scheme (vat | gst | sales_tax | none), her rates by tax code, period, home state,
               her own due-date rule, her seller details for e-invoices. Her rates are HERS: Hoola uses them and says so.
  return       a VAT / GST return worksheet for the period from her issued invoices and bills, laid out like that country's form
               (GB 9 boxes, DE UStVA, AU BAS, SG GST F5, IN GSTR-3B, others a general VAT layout), with each box traced to the
               documents, the reverse charge she self-accounts at her rate, and the lines whose tax does not match her rate.
  sales_tax    US: per state - sales, exempt, taxable, tax collected, tax due at HER state rate; the 12-month total per state
               against the nexus threshold she gives (the common figure is shown as not confirmed).
  oss          cross-border B2C sales per destination country with that country's rate she gives (the EU One Stop Shop shape).
  withholding  tax withheld on payments she makes or receives, at the rate she gives with its source, certificates tracked.
  einvoice     an invoice as UBL 2.1 / Peppol BIS Billing 3.0 XML, checked (totals add up, required fields present), and which
               e-invoicing model her country uses (clearance / Peppol / none - not confirmed). Hoola makes the file; it never sends it.
  organiser    personal return organiser: the tax year's income by kind and the costs that may matter, from her statements, the
               papers to gather, and an estimate ONLY on bands she gives.
  quarterly    sole-trader quarterly figures (income and costs by account for the quarter and the year so far), from her books.
  notice       a tax letter read: authority, reference, amount, the dates in it, what it asks; a reply skeleton with blanks; its date
               goes into her calendar (a date on her own paper).
  calendar     her return due dates from HER rule, the notice dates, her own dates; country deadlines are shown as not confirmed.

Filing is hers: Hoola prepares the figures, she (or her tax agent) files on the official portal or her software. Box layouts and
country facts are from memory until checked (status verify) and every output says so. Not tax advice."""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .. import laws as L
from .. import pack as P
from ..calc import from_minor, to_minor


class TaxError(ValueError):
    pass


FILING = ("Hoola does not file. You (or your tax agent) file this on the official portal or in your tax software; Hoola gives you "
          "the figures and the documents behind each one.")
CODES = ("std", "reduced", "super_reduced", "zero", "exempt", "export", "eu_goods", "rc_out", "rc_in", "oss", "outside")
CODE_WORDS = {"std": "standard rate", "reduced": "reduced rate", "super_reduced": "super-reduced rate", "zero": "zero rate",
              "exempt": "exempt", "export": "export (zero-rated)", "eu_goods": "goods to a business in another EU country",
              "rc_out": "services to a business abroad (the buyer accounts for the tax)",
              "rc_in": "bought from abroad - you account for the tax yourself (reverse charge)",
              "oss": "sold to a consumer in another country (One Stop Shop)", "outside": "outside the scope of the tax"}

# form layouts - from memory, status verify, until a qualified person in that country checks them
FORMS: dict[str, dict[str, Any]] = {
    "GB": {"name": "VAT Return (9 boxes, Making Tax Digital)", "status": "verify"},
    "DE": {"name": "Umsatzsteuer-Voranmeldung (UStVA)", "status": "verify"},
    "AU": {"name": "Business Activity Statement (GST)", "status": "verify"},
    "SG": {"name": "GST F5 return", "status": "verify"},
    "IN": {"name": "GSTR-3B summary (from Hoola's books; GST & Accounts keeps the portal work)", "status": "verify"},
    "*": {"name": "VAT / GST return (general layout)", "status": "verify"},
}
EINVOICE_MODEL: dict[str, tuple[str, str]] = {   # from memory - not confirmed
    "IN": ("clearance", "The government portal (IRP) gives each invoice its number first; in Hoola that is the GST & Accounts e-Invoice tab."),
    "SA": ("clearance", "ZATCA FATOORA clears or reports each invoice."),
    "DE": ("structured", "Businesses must be able to receive EN 16931 invoices (XRechnung / ZUGFeRD); sending is being phased in."),
    "SG": ("peppol", "InvoiceNow on the Peppol network."),
    "AU": ("peppol", "Peppol e-invoicing, voluntary for most businesses."),
    "AE": ("peppol", "A Peppol-style e-invoicing system is being introduced."),
    "IE": ("none", "No general mandate yet; EU rules (ViDA) are coming."),
    "GB": ("none", "No mandate; Peppol is optional."),
    "US": ("none", "No federal mandate; the voluntary DBNA network exists."),
    "CA": ("none", "No federal mandate."),
}
NOT_CONFIRMED = " (not confirmed - check this)"


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
        raise TaxError(str(e))


def _cfg(w: dict[str, Any]) -> dict[str, Any]:
    return dict((w.get("settings") or {}).get("tax") or {})


def _country(w: dict[str, Any], a: dict[str, Any]) -> str:
    cc = str(a.get("country") or _cfg(w).get("country") or (w.get("countries") or [""])[0] or "").upper()
    if not re.fullmatch(r"[A-Z]{2}", cc):
        raise TaxError("country: which country this return is for (ISO code, e.g. GB).")
    return cc


def _u(minor: int, cur: str) -> float:
    return float(from_minor(int(minor), cur))


def _pct(minor: int, rate: Any) -> int:
    return int((Decimal(int(minor)) * Decimal(str(rate)) / 100).quantize(Decimal(1), ROUND_HALF_UP))


def _whole(minor: int, cur: str) -> float:
    """A form that takes whole units only: the minor part is dropped (towards zero)."""
    k = 10 ** P.minor_unit(cur)
    return float(int(minor / k))


def _day(s: Any, what: str) -> str:
    try:
        return date.fromisoformat(str(s)[:10]).isoformat()
    except ValueError:
        raise TaxError(f"{what}: a date as YYYY-MM-DD.")


def _range(a: dict[str, Any]) -> tuple[str, str]:
    """period YYYY-MM | YYYY-Qn | YYYY, or since + upto."""
    p = str(a.get("period") or "").upper()
    if a.get("since") or a.get("upto"):
        return _day(a.get("since") or "0001-01-01", "since"), _day(a.get("upto") or date.today().isoformat(), "upto")
    m = re.fullmatch(r"(\d{4})-(\d{2})", p)
    if m:
        y, mo = int(m[1]), int(m[2])
        end = (date(y + (mo == 12), mo % 12 + 1, 1) - timedelta(days=1))
        return date(y, mo, 1).isoformat(), end.isoformat()
    m = re.fullmatch(r"(\d{4})-Q([1-4])", p)
    if m:
        y, q = int(m[1]), int(m[2])
        start = date(y, 3 * q - 2, 1)
        end = date(y + (q == 4), (3 * q) % 12 + 1, 1) - timedelta(days=1)
        return start.isoformat(), end.isoformat()
    if re.fullmatch(r"\d{4}", p):
        return f"{p}-01-01", f"{p}-12-31"
    raise TaxError("period: YYYY-MM, YYYY-Qn or YYYY (or since + upto).")


def _rate(w: dict[str, Any], cc: str, code: str, where: str = "") -> tuple[Decimal, str]:
    """The rate for a tax code: hers first (she typed it - she stands behind it), else the pack's when a person checked it; a rate
    that is only 'verify' is never used."""
    c = _cfg(w)
    mine = (c.get("state_rates") or {}).get(where) if where else (c.get("rates") or {}).get(code)
    if where and mine is None:
        mine = (c.get("oss_rates") or {}).get(where)
    if mine is not None:
        return Decimal(str(mine)), "your rate"
    try:
        v = P.value_of(cc, f"tax.vat_rates.{code}", "checked")
        return Decimal(str(v["value"])), f"country pack, checked {v['checked_on']}"
    except P.Unchecked as e:
        hint = P.peek(cc, "tax.vat_standard_rate_pct") if code == "std" else None
        raise TaxError(str(e) + (f" The pack says {hint}%{NOT_CONFIRMED}." if hint is not None else "")
                       + " Put your own rate in your tax settings (settings, rates) to go on.")


def _docs(tenant: str, ws: str, since: str, upto: str) -> list[dict[str, Any]]:
    """Issued invoices and bills (not drafts, not void) dated in the period, with lines in the book currency."""
    w = _ws(tenant, ws)
    book = str(w.get("currency") or "USD").upper()
    db, M = _db()
    out = []
    with db.session() as s:
        q = s.query(M.FinInvoice).filter(M.FinInvoice.tenant_id == tenant, M.FinInvoice.workspace_id == ws,
                                          M.FinInvoice.status.in_(("open", "paid")), M.FinInvoice.issue >= since, M.FinInvoice.issue <= upto)
        for d in q.order_by(M.FinInvoice.issue, M.FinInvoice.number).all():
            f = (lambda x, r=d.rate: int(round(x * r))) if d.currency != book else (lambda x: x)
            lines = []
            for ln in json.loads(d.lines or "[]"):
                code = ln.get("tax_code") or ("std" if ln.get("tax_pct") else "zero")
                lines.append({"code": code, "net": f(int(ln.get("net_minor") or 0)), "tax": f(int(ln.get("tax_minor") or 0)),
                              "tax_pct": float(ln.get("tax_pct") or 0), "capital": bool(ln.get("capital"))})
            out.append({"id": d.id, "kind": d.kind, "number": d.number, "party": d.party, "issue": d.issue, "currency": d.currency,
                        "supply": json.loads(d.supply or "{}"), "lines": lines})
    return out


# ---- settings ----------------------------------------------------------------------------------------------------------------

def save_settings(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    from ... import db
    from ..models import FinWorkspace, ensure
    new: dict[str, Any] = {}
    if a.get("country"):
        new["country"] = str(a["country"]).upper()[:2]
    if a.get("scheme"):
        if a["scheme"] not in ("vat", "gst", "sales_tax", "none"):
            raise TaxError("scheme: vat | gst | sales_tax | none.")
        new["scheme"] = a["scheme"]
    for k in ("rates", "state_rates", "oss_rates", "nexus"):
        if isinstance(a.get(k), dict):
            try:
                new[k] = {str(x)[:16]: float(v) for x, v in a[k].items() if float(v) >= 0}
            except (TypeError, ValueError):
                raise TaxError(f"{k}: numbers only, e.g. {{\"std\": 20}}.")
            if k == "rates" and any(x not in CODES for x in new[k]):
                raise TaxError("rates: tax codes " + ", ".join(CODES))
    if a.get("period_kind"):
        if a["period_kind"] not in ("monthly", "quarterly", "yearly"):
            raise TaxError("period_kind: monthly | quarterly | yearly.")
        new["period_kind"] = a["period_kind"]
    for k in ("home_state", "quarter_ends"):
        if a.get(k):
            new[k] = str(a[k]).upper()[:8] if k == "home_state" else [int(x) for x in a[k]][:4]
    if a.get("due_offset_days") is not None:
        new["due_offset_days"] = int(a["due_offset_days"])
    if isinstance(a.get("seller"), dict):
        new["seller"] = {k: str(v)[:160] for k, v in a["seller"].items() if k in ("name", "tax_id", "street", "city", "postcode", "country")}
    if not new:
        raise TaxError("settings: country, scheme, rates {code: %}, period_kind, home_state, due_offset_days, seller {name, tax_id ...}.")
    ensure()
    with db.session() as s:
        row = s.get(FinWorkspace, ws)
        if not row or row.tenant_id != tenant:
            raise TaxError("No such workspace.")
        st = json.loads(row.settings or "{}")
        st.setdefault("tax", {}).update(new)
        row.settings = json.dumps(st)
        s.commit()
        cfg = st["tax"]
    return {"workspace": ws, "tax": cfg, "says": "Your rates are used as you gave them; Hoola does not check them against the law."}


# ---- the VAT / GST return ----------------------------------------------------------------------------------------------------

def _agg(w: dict[str, Any], cc: str, docs: list[dict[str, Any]]) -> dict[str, Any]:
    sales: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    buys: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    cap = [0, 0]
    rc = [0, 0]
    warn, used = [], set()
    for d in docs:
        for ln in d["lines"]:
            b = sales if d["kind"] == "sales" else buys
            b[ln["code"]][0] += ln["net"]
            b[ln["code"]][1] += ln["tax"]
            if d["kind"] == "purchase" and ln["capital"]:
                cap[0] += ln["net"]
                cap[1] += ln["tax"]
            if d["kind"] == "purchase" and ln["code"] == "rc_in":
                r, src = _rate(w, cc, "std")
                used.add(f"standard {r}% ({src}) for the reverse charge")
                rc[0] += ln["net"]
                rc[1] += _pct(ln["net"], r)
            elif ln["code"] in ("std", "reduced", "super_reduced"):
                try:
                    r, src = _rate(w, cc, ln["code"])
                except TaxError:
                    continue
                if abs(Decimal(str(ln["tax_pct"])) - r) > Decimal("0.001"):
                    warn.append(f"{d['number'] or d['id']}: a line is taxed at {ln['tax_pct']}% but your {CODE_WORDS[ln['code']]} is {r}%.")
            if ln["code"] in ("zero", "exempt", "export", "eu_goods", "rc_out", "outside") and ln["tax"]:
                warn.append(f"{d['number'] or d['id']}: a {CODE_WORDS[ln['code']]} line carries tax.")
    return {"sales": sales, "buys": buys, "cap": cap, "rc": rc, "warnings": warn, "rates_used": sorted(used)}


def _sum(b: dict[str, list[int]], codes: tuple[str, ...] | None = None, i: int = 0, skip: tuple[str, ...] = ()) -> int:
    return sum(v[i] for k, v in b.items() if (codes is None or k in codes) and k not in skip)


TAXED = ("std", "reduced", "super_reduced")


def _gb(g, cur):
    S, B, rc = g["sales"], g["buys"], g["rc"]
    b1 = _sum(S, TAXED, 1) + rc[1]
    b4 = _sum(B, None, 1) + rc[1]
    b6 = _sum(S, skip=("outside",)) + rc[0]
    b7 = _sum(B, skip=("outside",))
    ex = {"1": b1, "2": 0, "3": b1, "4": b4, "5": b1 - b4, "6": b6, "7": b7, "8": _sum(S, ("eu_goods",)), "9": 0}
    lab = {"1": "VAT due on sales and other outputs", "2": "VAT due on acquisitions (Northern Ireland only)", "3": "Total VAT due",
           "4": "VAT reclaimed on purchases", "5": "Net VAT to pay (or reclaim)", "6": "Total sales excluding VAT",
           "7": "Total purchases excluding VAT", "8": "Goods supplied to the EU (Northern Ireland only)",
           "9": "Goods acquired from the EU (Northern Ireland only)"}
    boxes = [{"box": k, "label": lab[k], "amount": _u(v, cur) if k in "12345" else _whole(v, cur)} for k, v in ex.items()]
    return boxes, ex, ex["5"], "Boxes 6 to 9 are whole pounds (pence dropped)."


def _de(g, cur):
    S, B, rc = g["sales"], g["buys"], g["rc"]
    ex = {"81": _sum(S, ("std",)), "81_tax": _sum(S, ("std",), 1), "86": _sum(S, ("reduced",)), "86_tax": _sum(S, ("reduced",), 1),
          "41": _sum(S, ("eu_goods",)), "21": _sum(S, ("rc_out",)), "43": _sum(S, ("export",)), "48": _sum(S, ("exempt",)),
          "46": rc[0], "47": rc[1], "66": _sum(B, None, 1), "67": rc[1]}
    ex["83"] = ex["81_tax"] + ex["86_tax"] + ex["47"] - ex["66"] - ex["67"]
    lab = {"81": "Taxable sales at the standard rate (base)", "81_tax": "Tax on them", "86": "Taxable sales at the reduced rate (base)",
           "86_tax": "Tax on them", "41": "Supplies of goods to EU businesses", "21": "Services to EU businesses (buyer pays the tax)",
           "43": "Exports", "48": "Other exempt sales", "46": "Services bought from EU businesses (reverse charge, base)",
           "47": "Tax on them", "66": "Input tax", "67": "Input tax on the reverse charge", "83": "Tax to pay (or refund)"}
    base = {"81", "86", "41", "21", "43", "48", "46"}
    boxes = [{"box": k, "label": lab[k], "amount": _whole(v, cur) if k in base else _u(v, cur)} for k, v in ex.items()]
    return boxes, ex, ex["83"], "Bases are whole euros (cents dropped); tax amounts keep their cents."


def _au(g, cur):
    S, B, cap = g["sales"], g["buys"], g["cap"]
    allb = _sum(B, None, 0) + _sum(B, None, 1)
    ex = {"G1": _sum(S, skip=("outside",)) + _sum(S, None, 1, skip=("outside",)), "G2": _sum(S, ("export",)),
          "G3": _sum(S, ("zero",)), "G4": _sum(S, ("exempt",)), "G10": cap[0] + cap[1], "G11": allb - cap[0] - cap[1],
          "1A": _sum(S, None, 1), "1B": _sum(B, None, 1)}
    lab = {"G1": "Total sales (including GST)", "G2": "Export sales", "G3": "Other GST-free sales", "G4": "Input-taxed sales",
           "G10": "Capital purchases (including GST)", "G11": "Non-capital purchases (including GST)", "1A": "GST on sales",
           "1B": "GST on purchases"}
    boxes = [{"box": k, "label": lab[k], "amount": _whole(v, cur)} for k, v in ex.items()]
    return boxes, ex, ex["1A"] - ex["1B"], "Every label is whole dollars (cents dropped)."


def _sg(g, cur):
    S, B, rc = g["sales"], g["buys"], g["rc"]
    ex = {"1": _sum(S, TAXED) + rc[0], "2": _sum(S, ("zero", "export")), "3": _sum(S, ("exempt",)),
          "5": _sum(B, skip=("outside", "exempt")), "6": _sum(S, TAXED, 1) + rc[1], "7": _sum(B, None, 1) + rc[1], "14": rc[0]}
    ex["4"] = ex["1"] + ex["2"] + ex["3"]
    ex["8"] = ex["6"] - ex["7"]
    lab = {"1": "Standard-rated supplies", "2": "Zero-rated supplies", "3": "Exempt supplies", "4": "Total supplies",
           "5": "Total taxable purchases", "6": "Output tax due", "7": "Input tax and refunds claimed", "8": "Net GST to pay (or claim)",
           "14": "Imported services under the reverse charge"}
    order = ("1", "2", "3", "4", "5", "6", "7", "8", "14")
    boxes = [{"box": k, "label": lab[k], "amount": _u(ex[k], cur)} for k in order]
    return boxes, {k: ex[k] for k in order}, ex["8"], ""


def _general(g, cur):
    S, B, rc = g["sales"], g["buys"], g["rc"]
    ex = {"sales_taxed": _sum(S, TAXED), "output_tax": _sum(S, TAXED, 1) + rc[1], "sales_zero_exempt": _sum(S, ("zero", "exempt", "export", "eu_goods", "rc_out", "oss")),
          "purchases": _sum(B, skip=("outside",)), "input_tax": _sum(B, None, 1) + rc[1], "reverse_charge_base": rc[0]}
    ex["net"] = ex["output_tax"] - ex["input_tax"]
    lab = {"sales_taxed": "Taxable sales (base)", "output_tax": "Output tax (incl. reverse charge)", "sales_zero_exempt": "Zero-rated, exempt and other sales",
           "purchases": "Purchases (base)", "input_tax": "Input tax (incl. reverse charge)", "reverse_charge_base": "Reverse-charge purchases (base)",
           "net": "Net tax to pay (or reclaim)"}
    boxes = [{"box": k, "label": lab[k], "amount": _u(v, cur)} for k, v in ex.items()]
    return boxes, ex, ex["net"], ""


def _in(w, docs, cur):
    """GSTR-3B shape: intra-state = CGST + SGST halves, inter-state = IGST, by the other party's state against her home state."""
    home = str(_cfg(w).get("home_state") or "")
    if not home:
        raise TaxError("home_state: your GST state (settings home_state) - Hoola needs it to tell CGST + SGST from IGST.")
    out = {"3.1a_value": 0, "3.1a_igst": 0, "3.1a_cgst": 0, "3.1a_sgst": 0, "3.1b_value": 0, "3.1c_value": 0,
           "3.1d_value": 0, "3.1d_igst": 0, "3.1d_cgst": 0, "3.1d_sgst": 0, "4A3_igst": 0, "4A3_cgst": 0, "4A3_sgst": 0,
           "4A5_igst": 0, "4A5_cgst": 0, "4A5_sgst": 0}

    def split(tax, st):
        if st and st != home:
            return tax, 0, 0
        c = tax // 2
        return 0, c, tax - c

    for d in docs:
        st = str(d["supply"].get("state") or "")
        for ln in d["lines"]:
            if d["kind"] == "sales":
                if ln["code"] in TAXED:
                    i, c, s = split(ln["tax"], st)
                    out["3.1a_value"] += ln["net"]; out["3.1a_igst"] += i; out["3.1a_cgst"] += c; out["3.1a_sgst"] += s   # noqa: E702
                elif ln["code"] == "export":
                    out["3.1b_value"] += ln["net"]
                elif ln["code"] in ("zero", "exempt"):
                    out["3.1c_value"] += ln["net"]
            else:
                if ln["code"] == "rc_in":
                    r, _ = _rate(w, "IN", "std")
                    i, c, s = split(_pct(ln["net"], r), st)
                    out["3.1d_value"] += ln["net"]
                    for h, v in (("igst", i), ("cgst", c), ("sgst", s)):
                        out[f"3.1d_{h}"] += v
                        out[f"4A3_{h}"] += v
                elif ln["tax"]:
                    i, c, s = split(ln["tax"], st)
                    out["4A5_igst"] += i; out["4A5_cgst"] += c; out["4A5_sgst"] += s   # noqa: E702
    for h in ("igst", "cgst", "sgst"):
        out[f"net_{h}"] = out[f"3.1a_{h}"] + out[f"3.1d_{h}"] - out[f"4A3_{h}"] - out[f"4A5_{h}"]
    net = out["net_igst"] + out["net_cgst"] + out["net_sgst"]
    boxes = [{"box": k, "label": k.replace("_", " "), "amount": _u(v, cur)} for k, v in out.items()]
    return boxes, out, net, "Gross by head, before setting credit off against tax (GST & Accounts does the set-off and the portal work)."


def vat_return(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _ws(tenant, ws)
    cc = _country(w, a)
    cur = str(w.get("currency") or "USD").upper()
    since, upto = _range(a)
    docs = _docs(tenant, ws, since, upto)
    if cc == "US":
        raise TaxError("The US has no VAT: use sales_tax (per state).")
    if cc == "IN":
        g = _agg(w, cc, docs)
        boxes, exact, net, note = _in(w, docs, cur)
    else:
        g = _agg(w, cc, docs)
        boxes, exact, net, note = {"GB": _gb, "DE": _de, "AU": _au, "SG": _sg}.get(cc, _general)(g, cur)
    form = FORMS.get(cc, FORMS["*"])
    return {"country": cc, "form": form["name"], "layout": f"Box layout from memory{NOT_CONFIRMED} against the official form before you use it.",
            "since": since, "upto": upto, "currency": cur, "boxes": boxes, "exact": {k: _u(v, cur) for k, v in exact.items()},
            "to_pay": _u(net, cur) if net >= 0 else 0.0, "to_reclaim": _u(-net, cur) if net < 0 else 0.0,
            "documents": [{"number": d["number"], "kind": d["kind"], "issue": d["issue"], "party": d["party"]} for d in docs],
            "rates_used": g["rates_used"], "warnings": g["warnings"], "rounding": note,
            "basis": "Invoice dates (accrual). Cash accounting is not worked out here.", "says": FILING}


# ---- US sales tax, cross-border consumer sales, withholding -----------------------------------------------------------------------

def sales_tax(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _ws(tenant, ws)
    cur = str(w.get("currency") or "USD").upper()
    since, upto = _range(a)
    by: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for d in _docs(tenant, ws, since, upto):
        if d["kind"] != "sales":
            continue
        st = str(d["supply"].get("state") or "?")
        for ln in d["lines"]:
            by[st]["sales"] += ln["net"]
            by[st]["lines"] += 1
            by[st]["collected"] += ln["tax"]
            by[st]["exempt" if ln["code"] in ("exempt", "zero", "export", "outside") else "taxable"] += ln["net"]
    rows, warn, due_all = [], [], 0
    for st in sorted(by):
        r = by[st]
        rate = (_cfg(w).get("state_rates") or {}).get(st)
        row = {"state": st, "sales": _u(r["sales"], cur), "exempt": _u(r["exempt"], cur), "taxable": _u(r["taxable"], cur),
               "collected": _u(r["collected"], cur)}
        if rate is None:
            row["due"] = None
            row["says"] = f"No rate for {st} in your settings (state_rates) - Hoola does not guess a state or local rate."
        else:
            due = _pct(r["taxable"], rate)
            due_all += due
            row.update({"rate": float(rate), "due": _u(due, cur), "difference": _u(r["collected"] - due, cur)})
            if abs(r["collected"] - due) > (r["lines"] + 1) // 2:   # more than rounding each line to the cent can explain
                warn.append(f"{st}: collected {_u(r['collected'], cur)} but {rate}% of taxable sales is {_u(due, cur)}.")
        rows.append(row)
    return {"since": since, "upto": upto, "currency": cur, "states": rows, "due_total": _u(due_all, cur), "warnings": warn,
            "says": "Rates are the ones you gave per state (local rates add to the state rate). " + FILING}


def nexus(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    """The last 12 months of sales per state against her thresholds (the common one is shown, not confirmed)."""
    w = _ws(tenant, ws)
    cur = str(w.get("currency") or "USD").upper()
    upto = _day(a.get("as_of") or date.today().isoformat(), "as_of")
    since = (date.fromisoformat(upto) - timedelta(days=365)).isoformat()
    tot: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for d in _docs(tenant, ws, since, upto):
        if d["kind"] == "sales":
            st = str(d["supply"].get("state") or "?")
            tot[st][0] += sum(ln["net"] for ln in d["lines"])
            tot[st][1] += 1
    mine = _cfg(w).get("nexus") or {}
    rows = []
    for st, (amt, n) in sorted(tot.items()):
        th = mine.get(st)
        row = {"state": st, "sales_12m": _u(amt, cur), "invoices_12m": n}
        if th is None:
            row["says"] = f"Many states use about $100,000 of sales or 200 transactions a year{NOT_CONFIRMED}; put your threshold in settings nexus."
        else:
            row["threshold"] = float(th)
            row["over"] = _u(amt, cur) >= float(th)
        rows.append(row)
    return {"since": since, "upto": upto, "states": rows, "says": "Whether you must register in a state is a legal question; this shows your numbers."}


def oss(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _ws(tenant, ws)
    cc = _country(w, a)
    cur = str(w.get("currency") or "USD").upper()
    since, upto = _range(a)
    by: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for d in _docs(tenant, ws, since, upto):
        if d["kind"] != "sales":
            continue
        dest = str(d["supply"].get("country") or "?")
        for ln in d["lines"]:
            if ln["code"] == "oss":
                by[dest][0] += ln["net"]
                by[dest][1] += ln["tax"]
                by[dest][2] += 1
    rows, warn, total = [], [], 0
    for dest in sorted(by):
        net, booked = by[dest][0], by[dest][1]
        try:
            r, src = _rate(w, cc, "std", where=dest)
        except TaxError:
            rows.append({"country": dest, "net": _u(net, cur), "tax_booked": _u(booked, cur), "tax_due": None,
                         "says": f"No rate for {dest} in your settings (oss_rates)."})
            continue
        due = _pct(net, r)
        total += due
        rows.append({"country": dest, "net": _u(net, cur), "rate": float(r), "tax_due": _u(due, cur), "tax_booked": _u(booked, cur)})
        if abs(due - booked) > (by[dest][2] + 1) // 2:
            warn.append(f"{dest}: tax on the invoices is {_u(booked, cur)} but {r}% is {_u(due, cur)}.")
    return {"since": since, "upto": upto, "currency": cur, "countries": rows, "due_total": _u(total, cur), "warnings": warn,
            "threshold": f"In the EU distance sales below EUR 10,000 a year in total may stay taxed at home{NOT_CONFIRMED}.",
            "says": FILING}


def withholding(a: dict[str, Any]) -> dict[str, Any]:
    cur = str(a.get("currency") or "USD").upper()
    rows, by = [], defaultdict(lambda: [0, 0])
    for i, p in enumerate(a.get("payments") or []):
        if p.get("rate_pct") is None or not str(p.get("rate_source") or "").strip():
            raise TaxError(f"payments[{i}]: rate_pct and rate_source (the law, treaty article or your adviser) - Hoola does not guess a rate.")
        g = to_minor(Decimal(str(p.get("gross") or 0)), cur)
        wh = _pct(g, p["rate_pct"])
        payee = str(p.get("payee") or "?")[:80]
        by[payee][0] += g
        by[payee][1] += wh
        rows.append({"payee": payee, "kind": str(p.get("kind") or ""), "day": str(p.get("day") or ""), "gross": _u(g, cur),
                     "rate_pct": float(p["rate_pct"]), "withheld": _u(wh, cur), "net": _u(g - wh, cur), "rate_source": str(p["rate_source"])[:120],
                     "certificate": str(p.get("certificate") or "") or "missing"})
    return {"currency": cur, "payments": rows,
            "by_payee": {k: {"gross": _u(v[0], cur), "withheld": _u(v[1], cur)} for k, v in sorted(by.items())},
            "certificates_missing": [r["payee"] for r in rows if r["certificate"] == "missing"],
            "says": "Hoola works out the amounts on your rates; paying the tax over and the forms stay with you."}


# ---- e-invoicing ----------------------------------------------------------------------------------------------------------------

CAT = {"std": "S", "reduced": "S", "super_reduced": "S", "zero": "Z", "exempt": "E", "export": "G", "eu_goods": "K", "rc_out": "AE",
       "oss": "S", "outside": "O", "rc_in": "AE"}


def einvoice(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _ws(tenant, ws)
    cc = _country(w, a)
    db, M = _db()
    with db.session() as s:
        d = s.get(M.FinInvoice, str(a.get("doc") or ""))
        if not d or d.tenant_id != tenant or d.workspace_id != ws or d.kind != "sales":
            raise TaxError("doc: one of her sales invoices.")
        d = {"number": d.number, "issue": d.issue, "due": d.due, "currency": d.currency, "party": d.party, "status": d.status,
             "net": d.net_minor, "tax": d.tax_minor, "total": d.total_minor, "lines": json.loads(d.lines or "[]"),
             "supply": json.loads(d.supply or "{}")}
    seller = _cfg(w).get("seller") or {}
    problems = []
    if d["status"] == "draft" or not d["number"]:
        problems.append("The invoice is a draft: issue it first so it has its number.")
    for k in ("name", "tax_id", "country"):
        if not seller.get(k):
            problems.append(f"Your {k.replace('_', ' ')} is missing (settings seller).")
    if d["supply"].get("b2b") and not d["supply"].get("tax_id"):
        problems.append("The buyer is a business but its tax id is not on the invoice.")
    cur = d["currency"]
    ln_net = sum(int(x.get("net_minor") or 0) for x in d["lines"])
    ln_tax = sum(int(x.get("tax_minor") or 0) for x in d["lines"])
    if ln_net != d["net"] or ln_tax != d["tax"] or d["net"] + d["tax"] != d["total"]:
        problems.append("The lines do not add up to the invoice totals.")
    C = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
    B = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
    ET.register_namespace("", "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2")
    ET.register_namespace("cac", C)
    ET.register_namespace("cbc", B)
    root = ET.Element("{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}Invoice")

    def cb(parent, tag, text, **attr):
        e = ET.SubElement(parent, f"{{{B}}}{tag}", {k: str(v) for k, v in attr.items()})
        e.text = str(text)
        return e

    def ca(parent, tag):
        return ET.SubElement(parent, f"{{{C}}}{tag}")

    money = lambda m: f"{from_minor(int(m), cur):.{P.minor_unit(cur)}f}"   # noqa: E731
    cb(root, "CustomizationID", "urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0")
    cb(root, "ProfileID", "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0")
    cb(root, "ID", d["number"] or "DRAFT")
    cb(root, "IssueDate", d["issue"])
    cb(root, "DueDate", d["due"])
    cb(root, "InvoiceTypeCode", "380")
    cb(root, "DocumentCurrencyCode", cur)

    def party(tag, name, tax_id, country, extra=None):
        p = ca(ca(root, tag), "Party")
        addr = ca(p, "PostalAddress")
        for k, t in (("street", "StreetName"), ("city", "CityName"), ("postcode", "PostalZone")):
            if (extra or {}).get(k):
                cb(addr, t, extra[k])
        cb(ca(addr, "Country"), "IdentificationCode", country or "")
        if tax_id:
            ts = ca(p, "PartyTaxScheme")
            cb(ts, "CompanyID", tax_id)
            cb(ca(ts, "TaxScheme"), "ID", "VAT")
        cb(ca(p, "PartyLegalEntity"), "RegistrationName", name)

    party("AccountingSupplierParty", seller.get("name", ""), seller.get("tax_id", ""), seller.get("country", cc), seller)
    party("AccountingCustomerParty", d["party"], d["supply"].get("tax_id", ""), d["supply"].get("country", cc))
    groups: dict[tuple[str, float], list[int]] = defaultdict(lambda: [0, 0])
    for x in d["lines"]:
        k = (CAT.get(x.get("tax_code") or ("std" if x.get("tax_pct") else "zero"), "S"), float(x.get("tax_pct") or 0))
        groups[k][0] += int(x.get("net_minor") or 0)
        groups[k][1] += int(x.get("tax_minor") or 0)
    tt = ca(root, "TaxTotal")
    cb(tt, "TaxAmount", money(d["tax"]), currencyID=cur)
    for (cat, pct), (n, t) in sorted(groups.items()):
        st = ca(tt, "TaxSubtotal")
        cb(st, "TaxableAmount", money(n), currencyID=cur)
        cb(st, "TaxAmount", money(t), currencyID=cur)
        tc = ca(st, "TaxCategory")
        cb(tc, "ID", cat)
        cb(tc, "Percent", f"{pct:g}")
        cb(ca(tc, "TaxScheme"), "ID", "VAT")
    lm = ca(root, "LegalMonetaryTotal")
    cb(lm, "LineExtensionAmount", money(d["net"]), currencyID=cur)
    cb(lm, "TaxExclusiveAmount", money(d["net"]), currencyID=cur)
    cb(lm, "TaxInclusiveAmount", money(d["total"]), currencyID=cur)
    cb(lm, "PayableAmount", money(d["total"]), currencyID=cur)
    for i, x in enumerate(d["lines"], 1):
        il = ca(root, "InvoiceLine")
        cb(il, "ID", i)
        cb(il, "InvoicedQuantity", f"{x.get('qty') or 1:g}", unitCode="C62")
        cb(il, "LineExtensionAmount", money(x.get("net_minor") or 0), currencyID=cur)
        it = ca(il, "Item")
        cb(it, "Name", x.get("description") or "Item")
        ct = ca(it, "ClassifiedTaxCategory")
        cb(ct, "ID", CAT.get(x.get("tax_code") or ("std" if x.get("tax_pct") else "zero"), "S"))
        cb(ct, "Percent", f"{float(x.get('tax_pct') or 0):g}")
        cb(ca(ct, "TaxScheme"), "ID", "VAT")
        cb(ca(il, "Price"), "PriceAmount", f"{Decimal(str(x.get('price') or 0)):.{P.minor_unit(cur)}f}", currencyID=cur)
    xml = ET.tostring(root, encoding="unicode", xml_declaration=True)
    model, how = EINVOICE_MODEL.get(cc, ("unknown", "Hoola has no note for this country yet."))
    return {"country": cc, "format": "UBL 2.1 / Peppol BIS Billing 3.0", "xml": xml, "ok": not problems, "problems": problems,
            "model": model, "how": how + NOT_CONFIRMED,
            "says": "Hoola makes and checks the file; it does not send it. Send it through your Peppol access point, your country's "
                    "portal or your software." + (" In India use the e-Invoice tab of GST & Accounts (the official IRP route)." if cc == "IN" else "")}


# ---- personal and sole trader -------------------------------------------------------------------------------------------------

INCOME_KINDS = (("employment", ("salary", "payroll", "wages", "gehalt", "lohn", "stipend")), ("interest", ("interest",)),
                ("dividends", ("dividend",)), ("property", ("rent received", "rental income", "tenant")),
                ("self_employment", ("invoice", "client", "freelance", "fees received", "stripe payout", "paypal payout")),
                ("pension", ("pension credit", "annuity")), ("benefits", ("benefit", "allowance", "child benefit")))
COST_KINDS = (("pension_contributions", ("pension contribution", "retirement contribution", "401k", "nps", "superannuation")),
              ("donations", ("donation", "charity", "gift aid")), ("medical", ("hospital", "pharmacy", "medical", "doctor", "health insurance")),
              ("education", ("tuition", "school fee", "university")), ("childcare", ("childcare", "nursery", "creche")))
PAPERS = ["Year-end pay certificate from each employer", "Interest and dividend statements", "Pension statements",
          "Rent received and the costs of the property", "Your business income and costs (or your books)",
          "Receipts for donations, medical, education and childcare costs if your country allows them",
          "Any tax already paid or withheld (payments on account, certificates)", "Last year's return and any letter from the tax office"]


def _year(w: dict[str, Any], a: dict[str, Any]) -> tuple[str, str]:
    if a.get("since") and a.get("upto"):
        return _day(a["since"], "since"), _day(a["upto"], "upto")
    ye = str((w.get("settings") or {}).get("year_end") or "12-31")
    y = int(a.get("year") or date.today().year)
    mm, dd = int(ye[:2]), int(ye[3:])
    end = date(y, mm, dd)
    return (end.replace(year=y - 1) + timedelta(days=1)).isoformat(), end.isoformat()


def _year_start(w: dict[str, Any], day: str) -> str:
    """The first day of her tax year that contains `day`."""
    ye = str((w.get("settings") or {}).get("year_end") or "12-31")
    d = date.fromisoformat(day)
    end = date(d.year, int(ye[:2]), int(ye[3:]))
    if d > end:
        end = end.replace(year=d.year + 1)
    return (end.replace(year=end.year - 1) + timedelta(days=1)).isoformat()


def _kind(text: str, kinds) -> str:
    t = text.lower()
    return next((k for k, words in kinds if any(x in t for x in words)), "")


def bands_tax(income: int, bands: list[dict[str, Any]], allowance: int = 0) -> tuple[int, list[dict[str, Any]]]:
    """Progressive tax on her bands [{upto (None = rest), pct}] after an allowance - all integer minor units."""
    left, lo, tax, rows = max(0, income - allowance), 0, 0, []
    for b in bands:
        hi = b.get("upto")
        width = left if hi is None else max(0, min(left, int(hi) - lo))
        t = _pct(width, b["pct"])
        rows.append({"from": lo, "upto": hi, "pct": b["pct"], "taxed": width, "tax": t})
        tax += t
        left -= width
        lo = int(hi) if hi is not None else lo
        if left <= 0:
            break
    return tax, rows


def organiser(tenant: str, a: dict[str, Any]) -> dict[str, Any]:
    from .household import _rows
    w = _ws(tenant, str(a.get("workspace") or "")) if a.get("workspace") else {"settings": {}, "countries": [a.get("country") or ""]}
    since, upto = _year(w, a)
    rows = [r for r in _rows(tenant, a) if since <= r["day"] <= upto]
    cur = str(a.get("currency") or w.get("currency") or next((r["currency"] for r in rows if r.get("currency")), "") or "USD").upper()
    inc: dict[str, int] = defaultdict(int)
    cost: dict[str, int] = defaultdict(int)
    unsure = 0
    for r in rows:
        if r["amount_minor"] > 0:
            k = _kind(r["narration"], INCOME_KINDS)
            if not k:
                unsure += 1
                k = "other"
            inc[k] += r["amount_minor"]
        else:
            k = _kind(r["narration"], COST_KINDS)
            if k:
                cost[k] += -r["amount_minor"]
    for x in a.get("extra_income") or []:   # what is not in her statements (gains, foreign income)
        inc[str(x.get("kind") or "other")[:24]] += to_minor(Decimal(str(x.get("amount") or 0)), cur)
    out = {"since": since, "upto": upto, "currency": cur, "income": {k: _u(v, cur) for k, v in sorted(inc.items())},
           "costs_that_may_matter": {k: _u(v, cur) for k, v in sorted(cost.items())}, "money_in_not_sorted": unsure,
           "papers_to_gather": PAPERS, "says": "Income here is money in your statements (gross pay may be higher than what reached the "
           "bank). Whether a cost reduces your tax depends on your country's rules" + NOT_CONFIRMED + ". " + FILING}
    if a.get("bands"):
        taxable = sum(v for k, v in inc.items() if k not in ("benefits",))
        allowance = to_minor(Decimal(str(a.get("allowance") or 0)), cur)
        bands = [{"upto": None if b.get("upto") is None else to_minor(Decimal(str(b["upto"])), cur), "pct": b["pct"]} for b in a["bands"]]
        tax, rows_ = bands_tax(taxable, bands, allowance)
        out["estimate"] = {"on_income": _u(taxable, cur), "allowance": _u(allowance, cur), "tax": _u(tax, cur),
                           "bands": [{**r, "from": _u(r["from"], cur), "upto": None if r["upto"] is None else _u(r["upto"], cur),
                                      "taxed": _u(r["taxed"], cur), "tax": _u(r["tax"], cur)} for r in rows_],
                           "says": "An estimate on the bands YOU gave - not your country's law checked by Hoola."}
    else:
        out["estimate"] = None
        out["estimate_says"] = "No estimate: give your bands [{upto, pct}] and allowance, or wait until a person checks the country pack."
    return out


def quarterly(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    from . import books as BK
    w = _ws(tenant, ws)
    cur = str(w.get("currency") or "USD").upper()
    since, upto = _range(a)
    ys = _year_start(w, upto)
    names = {x["code"]: (x["name"], x["type"]) for x in BK.coa(tenant, ws)}

    def pl(f, t):
        bal = BK.balances(tenant, ws, upto=t, since=f)
        inc = {names[c][0]: -v for c, v in bal.items() if c in names and names[c][1] == "income" and v}
        exp = {names[c][0]: v for c, v in bal.items() if c in names and names[c][1] == "expense" and v}
        return inc, exp

    qi, qe = pl(since, upto)
    yi, ye = pl(ys, upto)
    f = lambda d: {k: _u(v, cur) for k, v in sorted(d.items())}   # noqa: E731
    return {"since": since, "upto": upto, "currency": cur, "quarter": {"income": f(qi), "costs": f(qe),
            "profit": _u(sum(qi.values()) - sum(qe.values()), cur)},
            "year_to_date": {"since": ys, "income": f(yi), "costs": f(ye), "profit": _u(sum(yi.values()) - sum(ye.values()), cur)},
            "says": "Quarterly figures from your books (for updates like Making Tax Digital for Income Tax" + NOT_CONFIRMED + "). " + FILING}


# ---- notices and the calendar ---------------------------------------------------------------------------------------------------

AUTHORITIES = ("HMRC", "IRS", "Income Tax Department", "CBIC", "GSTN", "Finanzamt", "ATO", "IRAS", "Revenue", "CRA", "FTA", "ZATCA")
_ASKS = (("penalty", "a penalty"), ("assessment", "an assessment"), ("enquiry", "an enquiry"), ("inquiry", "an enquiry"),
         ("audit", "an audit"), ("demand", "a demand to pay"), ("reminder", "a reminder"), ("refund", "a refund"),
         ("mismatch", "a mismatch"), ("show cause", "a show-cause notice"), ("information", "a request for information"))
_MONTHS = {m: i for i, m in enumerate(("january", "february", "march", "april", "may", "june", "july", "august", "september",
                                        "october", "november", "december"), 1)}
_DATE_RX = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b|\b(\d{1,2})[/.](\d{1,2})[/.](\d{4})\b|\b(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})\b|\b([A-Za-z]{3,9})\s+(\d{1,2}),\s*(\d{4})\b")
_AMT_RX = re.compile(r"(?:£|\$|€|₹|rs\.?|inr|usd|gbp|eur|aud|sgd)\s*([\d,]+(?:\.\d{1,2})?)|([\d,]+\.\d{2})\s*(?:gbp|usd|eur|inr|aud|sgd)", re.I)
_REF_RX = re.compile(r"\b(?:reference|ref|notice|case|din|utr)\s*(?:no\.?|number|id)?\s*[:#]?\s*([A-Z0-9][A-Z0-9/-]{4,30})", re.I)


def _dates(text: str, dmy: bool = True) -> list[str]:
    out = []
    for m in _DATE_RX.finditer(text):
        try:
            if m[1]:
                d = date.fromisoformat(m[1])
            elif m[2]:
                a, b = int(m[2]), int(m[3])
                d = date(int(m[4]), b, a) if dmy else date(int(m[4]), a, b)
            elif m[5]:
                mo = next((v for k, v in _MONTHS.items() if k.startswith(m[6].lower()[:3])), 0)
                d = date(int(m[7]), mo, int(m[5]))
            else:
                mo = next((v for k, v in _MONTHS.items() if k.startswith(m[8].lower()[:3])), 0)
                d = date(int(m[10]), mo, int(m[9]))
            out.append(d.isoformat())
        except (ValueError, TypeError):
            continue
    return out


def notice(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    text = str(a.get("text") or "")
    if len(text.strip()) < 20:
        raise TaxError("text: the words of the tax letter.")
    low = text.lower()
    auth = next((x for x in AUTHORITIES if x.lower() in low), "")
    ref = (_REF_RX.search(text) or [None, ""])[1]
    amt = _AMT_RX.search(text)
    dates = _dates(text, dmy=str(a.get("country") or "").upper() != "US")
    by = ""
    m = re.search(r"(?:by|before|within|no later than|on or before)\s+([^\n.;]{4,40})", text, re.I)
    if m:
        dd = _dates(m[1], dmy=str(a.get("country") or "").upper() != "US")
        by = dd[0] if dd else ""
    asks = [w for k, w in _ASKS if k in low]
    out = {"authority": auth or "not found", "reference": ref or "not found", "amount": (amt[1] or amt[2]) if amt else None,
           "dates_in_letter": dates, "reply_by": by or None, "what_it_is": asks or ["not clear - read it with your adviser"],
           "reply_draft": (f"To: {auth or '[tax office]'}\nReference: {ref or '[reference]'}\n\nDear Sir or Madam,\n\nThank you for your "
                           "letter dated [date]. [What you agree with / what you dispute and why]. I enclose [documents].\n\n"
                           "Yours faithfully,\n[name]\n[tax id]"),
           "says": "Read from your letter. Check every figure against the letter itself; Hoola does not send the reply. A deadline in a "
                   "tax letter matters - if you are unsure, ask a tax adviser."}
    if ws and by:
        db, M = _db()
        with db.session() as s:
            title = f"Reply to {auth or 'tax'} letter {ref}".strip()
            if not s.query(M.FinObligation).filter_by(tenant_id=tenant, workspace_id=ws, title=title, due=by).first():
                s.add(M.FinObligation(tenant_id=tenant, workspace_id=ws, kind="tax", title=title, due=by,
                                      country=str(a.get("country") or "")[:2], pack_path="her letter"))
                s.commit()
        out["calendar"] = f"Added: reply by {by} (the date in your letter)."
    return out


def _period_ends(cfg: dict[str, Any], year: int) -> list[date]:
    kind = cfg.get("period_kind") or "quarterly"
    if kind == "monthly":
        months = list(range(1, 13))
    elif kind == "yearly":
        months = [int((cfg.get("quarter_ends") or [12])[-1])]
    else:
        months = sorted(cfg.get("quarter_ends") or [3, 6, 9, 12])
    return [date(year + (m == 12), m % 12 + 1, 1) - timedelta(days=1) for m in months]


def calendar_(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _ws(tenant, ws)
    cfg = _cfg(w)
    cc = _country(w, a)
    year = int(a.get("year") or date.today().year)
    items = []
    off = cfg.get("due_offset_days")
    for end in _period_ends(cfg, year):
        row = {"what": f"{cfg.get('scheme', 'tax').upper()} return for the period ending {end}", "period_end": end.isoformat()}
        if off is None:
            row["due"] = None
            row["says"] = f"No due rule: give due_offset_days (days after the period end) - Hoola does not guess {cc}'s deadline."
        else:
            row["due"] = (end + timedelta(days=int(off))).isoformat()
            row["from"] = "your rule"
        items.append(row)
    db, M = _db()
    with db.session() as s:
        for o in s.query(M.FinObligation).filter_by(tenant_id=tenant, workspace_id=ws, kind="tax").order_by(M.FinObligation.due).all():
            if o.due.startswith(str(year)):
                items.append({"what": o.title, "due": o.due, "from": o.pack_path or "you", "status": o.status})
    for path in ("filing_deadline", "year_end"):
        v = P.peek(cc, f"tax.{path}")
        if v:
            items.append({"what": f"{cc} {path.replace('_', ' ')}: {v}{NOT_CONFIRMED}", "due": None, "from": "country pack (verify)"})
    items.sort(key=lambda x: (x.get("due") is None, x.get("due") or ""))
    return {"year": year, "country": cc, "items": items, "says": "Dates from your rule and your letters are reminders; check every "
            "deadline with the tax office or your adviser."}


def add_date(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    due = _day(a.get("due"), "due")
    title = str(a.get("title") or "").strip()[:200]
    if not title:
        raise TaxError("title: what is due.")
    _ws(tenant, ws)
    db, M = _db()
    with db.session() as s:
        o = M.FinObligation(tenant_id=tenant, workspace_id=ws, kind="tax", title=title, due=due, pack_path="you")
        s.add(o)
        s.commit()
        return {"id": o.id, "title": title, "due": due}


# ---- the tool's entry ------------------------------------------------------------------------------------------------------

ACTIONS = ("settings", "return", "sales_tax", "nexus", "oss", "withholding", "einvoice", "organiser", "quarterly", "notice", "calendar",
           "add_date", "codes", "file")


def run(tenant: str, action: str, a: dict[str, Any], actor: str = "owner") -> dict[str, Any]:
    a = dict(a)
    ws = str(a.get("workspace") or "")
    if action == "file":
        raise L.Refused("file_as_institution", FILING)
    if action == "codes":
        return {"codes": CODE_WORDS, "not_advice": L.NOT_ADVICE}
    if action == "withholding":
        out = withholding(a)
    elif action == "organiser":
        out = organiser(tenant, a)
    elif action == "notice":
        out = notice(tenant, ws, a)
    else:
        if not ws:
            raise TaxError("workspace: the finance workspace these books belong to.")
        f = {"settings": lambda: save_settings(tenant, ws, a), "return": lambda: vat_return(tenant, ws, a),
             "sales_tax": lambda: sales_tax(tenant, ws, a), "nexus": lambda: nexus(tenant, ws, a), "oss": lambda: oss(tenant, ws, a),
             "einvoice": lambda: einvoice(tenant, ws, a), "quarterly": lambda: quarterly(tenant, ws, a),
             "calendar": lambda: calendar_(tenant, ws, a), "add_date": lambda: add_date(tenant, ws, a)}
        if action not in f:
            raise TaxError("action: " + ", ".join(ACTIONS))
        out = f[action]()
    out.setdefault("not_advice", L.NOT_ADVICE)
    return out
