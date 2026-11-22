"""The F4 card: tax returns for 6 countries computed from fixed books, checked against answers worked out by hand (FINANCE_GLOBAL_PLAN
phase F4).

For each country a business is made from a seed: sales at the standard and reduced rate, zero-rated, exempt, exports, supplies to
businesses abroad, purchases with tax, a capital purchase, a service bought from abroad under the reverse charge, a line taxed at the
wrong rate, a draft and an invoice outside the period (both must be left out). Her own rates go into her tax settings. Then the card
works out every box itself - line by line, plain Decimal arithmetic, the form's rounding - and compares to the cent:

  GB  VAT return 9 boxes          DE  UStVA            AU  BAS (whole dollars)       SG  GST F5
  IN  GSTR-3B by head (CGST + SGST inside the state, IGST across)                     US  sales tax per state at her rates

Also: the wrong-rate line is the one warning; a rate she never gave is refused, never guessed; the e-invoice file of a sales invoice
adds up and a missing seller tax id is named; cross-border consumer sales per country (DE) and withholding match by hand.

    python -m app.fin.card_f4        builds a scratch database, prints the card; exit 1 if any country fails
"""
from __future__ import annotations

import random
import sys
import xml.etree.ElementTree as ET
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from . import profile as PR
from .desks import books as B
from .desks import tax as T

D = Decimal
SETUP = {
    "GB": ("GBP", {"std": 20, "reduced": 5}, {}),
    "DE": ("EUR", {"std": 19, "reduced": 7}, {"oss_rates": {"FR": 20, "IT": 22}}),
    "AU": ("AUD", {"std": 10}, {}),
    "SG": ("SGD", {"std": 9}, {}),
    "IN": ("INR", {"std": 18, "reduced": 5}, {"home_state": "MH"}),
    "US": ("USD", {}, {"state_rates": {"CA": 7.25, "NY": 8.875, "TX": 6.25}}),
}
PERIOD, SINCE, UPTO = "2026-Q3", "2026-07-01", "2026-09-30"


def _q(x: Decimal) -> int:
    return int(x.quantize(D(1), ROUND_HALF_UP))


def _minor(units: Any) -> int:
    return _q(D(str(units)) * 100)


def _whole(minor: int) -> int:
    return int(minor / 100) * 100


class Book:
    """The card's own copy of what went in, to work the answer out by hand."""
    def __init__(self):
        self.lines: list[dict[str, Any]] = []

    def add(self, kind, code, price, qty, pct, state="", capital=False, country=""):
        net = _q(D(str(qty)) * D(str(price)) * 100)
        tax = _q(D(net) * D(str(pct)) / 100)
        self.lines.append({"kind": kind, "code": code, "net": net, "tax": tax, "pct": pct, "state": state, "capital": capital,
                           "country": country})

    def s(self, kind, codes=None, key="net", **f):
        return sum(x[key] for x in self.lines if x["kind"] == kind and (codes is None or x["code"] in codes)
                   and all(x.get(k) == v for k, v in f.items()))


def run_one(i: int, cc: str) -> dict[str, Any]:
    rnd = random.Random(7000 + i)
    cur, rates, extra = SETUP[cc]
    t = f"card4-{i}-{cc}"
    pv = PR.preview({"size": "business", "countries": [cc], "wants": [], "people": []})
    ans = {**pv["answers"], "currency": cur}
    ws = PR.apply(t, ans, PR.preview(ans)["hash"])["id"]
    run = lambda a, **x: T.run(t, a, {"workspace": ws, **x})          # noqa: E731
    books = lambda a, **x: B.run(t, a, {"workspace": ws, **x}, "card")   # noqa: E731
    bad: list[str] = []
    std = rates.get("std", 0)
    red = rates.get("reduced", 0)

    # a rate she never gave is refused, never guessed
    if cc != "US":
        books("bill", party="Abroad Ltd", issue="2026-07-02", due="2026-07-02", code="6600",
              lines=[{"description": "svc", "qty": 1, "price": 10, "tax_code": "rc_in"}], issue_now=True)
        try:
            run("return", period=PERIOD)
            bad.append("a reverse charge without her rate was not refused")
        except T.TaxError as e:
            if "settings" not in str(e):
                bad.append(f"refusal did not say how to go on: {e}")
    run("settings", country=cc, scheme="sales_tax" if cc == "US" else ("gst" if cc in ("AU", "SG", "IN") else "vat"), rates=rates,
        seller={"name": f"Card Co {cc}", "country": cc}, period_kind="quarterly", due_offset_days=37, **extra)
    bk = Book()
    if cc != "US":
        bk.add("purchase", "rc_in", 10, 1, 0)   # the bill made above, now with her rate

    def inv(kind, code, price, qty=1, pct=0, state="", capital=False, country="", issue="2026-08-10", b2b=None, now=True):
        supply = {}
        if state:
            supply["state"] = state
        if country:
            supply["country"] = country
        if b2b is not None:
            supply["b2b"] = b2b
        line = {"description": code, "qty": qty, "price": price, "tax_pct": pct, "tax_code": code, "capital": capital}
        d = books("invoice" if kind == "sales" else "bill", party=f"{code} party", issue=issue, due=issue, supply=supply,
                  lines=[line], issue_now=now, code="4000" if kind == "sales" else ("1500" if capital else "6000"))
        if now and SINCE <= issue <= UPTO:
            bk.add(kind, code, price, qty, pct, state, capital, country)
        return d

    p = lambda lo, hi: round(rnd.uniform(lo, hi), 2)   # noqa: E731
    if cc == "US":
        for st in ("CA", "NY", "TX"):
            r = extra["state_rates"][st]
            for _ in range(3):
                inv("sales", "std", p(20, 900), rnd.randint(1, 3), r, state=st)
            inv("sales", "exempt", p(50, 300), 1, 0, state=st)
        inv("sales", "std", 100, 1, 7.0, state="CA")              # undercharged
        inv("sales", "std", 400, 1, 7.25, state="CA", issue="2026-06-20")   # outside the period
        inv("sales", "std", 80, 1, 7.25, state="CA", now=False)              # a draft
        r = run("sales_tax", period=PERIOD)
        for row in r["states"]:
            st = row["state"]
            taxable = bk.s("sales", ("std",), state=st)
            due = _q(D(taxable) * D(str(extra["state_rates"][st])) / 100)
            col = bk.s("sales", None, "tax", state=st)
            if _minor(row["taxable"]) != taxable or _minor(row["due"]) != due or _minor(row["collected"]) != col \
                    or _minor(row["exempt"]) != bk.s("sales", ("exempt",), state=st):
                bad.append(f"{st}: {row} vs taxable {taxable} due {due} collected {col}")
        if [w[:3] for w in r["warnings"]] != ["CA:"]:
            bad.append(f"warnings {r['warnings']}")
        nx = run("nexus", as_of=UPTO)
        if not all("says" in x for x in nx["states"]):
            bad.append("nexus without a threshold should say the common figure is not confirmed")
    else:
        for _ in range(rnd.randint(3, 5)):
            inv("sales", "std", p(10, 800), rnd.randint(1, 4), std, state="MH" if cc == "IN" else "")
        if cc == "IN":
            for _ in range(2):
                inv("sales", "std", p(100, 900), 1, std, state="KA")
        if red:
            inv("sales", "reduced", p(20, 300), 2, red, state="MH" if cc == "IN" else "")
        inv("sales", "zero", p(30, 200), 1, 0)
        inv("sales", "exempt", p(30, 200), 1, 0)
        inv("sales", "export", p(100, 900), 1, 0, country="US")
        if cc in ("GB", "DE"):
            inv("sales", "eu_goods" if cc == "DE" else "rc_out", p(100, 500), 1, 0, country="FR", b2b=True)
        if cc == "DE":
            inv("sales", "rc_out", p(100, 500), 1, 0, country="NL", b2b=True)
            for dest in ("FR", "IT"):
                inv("sales", "oss", p(50, 400), 1, extra["oss_rates"][dest], country=dest)
        for _ in range(3):
            inv("purchase", "std", p(10, 400), 1, std, state="MH" if cc == "IN" else "")
        if cc == "IN":
            inv("purchase", "std", p(100, 400), 1, std, state="GJ")
        inv("purchase", "std", p(500, 2000), 1, std, capital=True, state="MH" if cc == "IN" else "")
        inv("purchase", "rc_in", p(100, 600), 1, 0, state="MH" if cc == "IN" else "")
        inv("sales", "std", p(50, 300), 1, std + 1.5, state="MH" if cc == "IN" else "")   # the wrong-rate line
        inv("sales", "std", 999, 1, std, issue="2026-10-02")                              # next quarter
        inv("sales", "std", 50, 1, std, now=False)                                         # a draft
        r = run("return", period=PERIOD)
        ex = {k: _minor(v) for k, v in r["exact"].items()}
        S = lambda codes=None, key="net", **f: bk.s("sales", codes, key, **f)      # noqa: E731
        Pu = lambda codes=None, key="net", **f: bk.s("purchase", codes, key, **f)  # noqa: E731
        rc_net = Pu(("rc_in",))
        rc_tax = sum(_q(D(x["net"]) * D(str(std)) / 100) for x in bk.lines if x["code"] == "rc_in")
        T3 = ("std", "reduced")
        if cc == "GB":
            want = {"1": S(T3, "tax") + rc_tax, "2": 0, "4": Pu(None, "tax") + rc_tax, "6": S() + rc_net, "7": Pu(), "8": 0, "9": 0}
            want["3"] = want["1"]
            want["5"] = want["3"] - want["4"]
            box = {b["box"]: b["amount"] for b in r["boxes"]}
            if any(_minor(box[k]) != _whole(want[k]) for k in "6789"):
                bad.append("boxes 6-9 are not whole pounds")
        elif cc == "DE":
            want = {"81": S(("std",)), "81_tax": S(("std",), "tax"), "86": S(("reduced",)), "86_tax": S(("reduced",), "tax"),
                    "41": S(("eu_goods",)), "21": S(("rc_out",)), "43": S(("export",)), "48": S(("exempt",)), "46": rc_net, "47": rc_tax,
                    "66": Pu(None, "tax"), "67": rc_tax}
            want["83"] = want["81_tax"] + want["86_tax"] + want["47"] - want["66"] - want["67"]
            o = run("oss", period=PERIOD)
            for row in o["countries"]:
                exp = _q(D(S(("oss",), country=row["country"])) * D(str(extra["oss_rates"][row["country"]])) / 100)
                if _minor(row["tax_due"]) != exp:
                    bad.append(f"oss {row}")
        elif cc == "AU":
            cap = bk.s("purchase", None, capital=True) + bk.s("purchase", None, "tax", capital=True)
            want = {"G1": S() + S(None, "tax"), "G2": S(("export",)), "G3": S(("zero",)), "G4": S(("exempt",)), "G10": cap,
                    "G11": Pu() + Pu(None, "tax") - cap, "1A": S(None, "tax"), "1B": Pu(None, "tax")}
            box = {b["box"]: b["amount"] for b in r["boxes"]}
            if any(_minor(box[k]) != _whole(want[k]) for k in want):
                bad.append("BAS labels are not whole dollars")
        elif cc == "SG":
            want = {"1": S(T3) + rc_net, "2": S(("zero", "export")), "3": S(("exempt",)), "5": Pu(), "6": S(T3, "tax") + rc_tax,
                    "7": Pu(None, "tax") + rc_tax, "14": rc_net}
            want["4"] = want["1"] + want["2"] + want["3"]
            want["8"] = want["6"] - want["7"]
        else:   # IN
            want: dict[str, int] = {k: 0 for k in ex}

            def split(tax, st):
                if st and st != "MH":
                    return tax, 0, 0
                return 0, tax // 2, tax - tax // 2
            for x in bk.lines:
                if x["kind"] == "sales":
                    if x["code"] in T3:
                        i_, c_, s_ = split(x["tax"], x["state"])
                        want["3.1a_value"] += x["net"]; want["3.1a_igst"] += i_; want["3.1a_cgst"] += c_; want["3.1a_sgst"] += s_  # noqa: E702
                    elif x["code"] == "export":
                        want["3.1b_value"] += x["net"]
                    else:
                        want["3.1c_value"] += x["net"]
                elif x["code"] == "rc_in":
                    i_, c_, s_ = split(_q(D(x["net"]) * D(str(std)) / 100), x["state"])
                    want["3.1d_value"] += x["net"]
                    for h, v in (("igst", i_), ("cgst", c_), ("sgst", s_)):
                        want[f"3.1d_{h}"] += v
                        want[f"4A3_{h}"] += v
                else:
                    i_, c_, s_ = split(x["tax"], x["state"])
                    want["4A5_igst"] += i_; want["4A5_cgst"] += c_; want["4A5_sgst"] += s_   # noqa: E702
            for h in ("igst", "cgst", "sgst"):
                want[f"net_{h}"] = want[f"3.1a_{h}"] + want[f"3.1d_{h}"] - want[f"4A3_{h}"] - want[f"4A5_{h}"]
        for k, v in want.items():
            if ex.get(k) != v:
                bad.append(f"box {k}: {ex.get(k)} not {v}")
        if len(r["warnings"]) != 1 or "taxed at" not in r["warnings"][0]:
            bad.append(f"warnings {r['warnings']}")
        if len(r["documents"]) != len(bk.lines):
            bad.append(f"documents {len(r['documents'])} not {len(bk.lines)} (a draft or an invoice outside the period got in)")
    # the e-invoice of the first sales invoice: adds up, names the missing seller tax id
    first = next(d for d in B.docs(t, ws, "sales", "open"))
    e = run("einvoice", doc=first["id"], country=cc)
    root = ET.fromstring(e["xml"].split("?>", 1)[1])
    ns = {"cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
          "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"}
    pay = root.find("cac:LegalMonetaryTotal/cbc:PayableAmount", ns)
    if pay is None or _minor(pay.text) != _minor(first["total"]):
        bad.append("e-invoice payable does not match the invoice")
    if not any("tax id" in x for x in e["problems"]):
        bad.append("e-invoice did not name the missing seller tax id")
    # withholding by hand
    gross = p(1000, 5000)
    w = run("withholding", currency=cur, payments=[{"payee": "Consultant", "gross": gross, "rate_pct": 10, "rate_source": "her adviser"}])
    if _minor(w["payments"][0]["withheld"]) != _q(D(str(gross)) * 10):
        bad.append("withholding")
    cal = run("calendar", year=2026)
    if not any(x.get("due") == "2026-11-06" for x in cal["items"]):
        bad.append("calendar: the Q3 due date from her rule is missing")
    return {"country": cc, "currency": cur, "ok": not bad, "problems": bad}


def run(n: int = 6) -> dict[str, Any]:
    rows = []
    for i in range(n):
        cc = list(SETUP)[i % 6]
        try:
            rows.append(run_one(i, cc))
        except Exception as e:   # a crash is a failed country, not a stopped card
            rows.append({"country": cc, "ok": False, "problems": [f"{type(e).__name__}: {e}"]})
    return {"returns": n, "countries": sorted({r["country"] for r in rows}), "passed": sum(r["ok"] for r in rows),
            "ok": all(r["ok"] for r in rows), "rows": rows}


def _scratch_db() -> None:
    import os
    import tempfile
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(prefix="card4_"), "card.db")
    os.environ["HOOLA_FIN_REVIEW_DIR"] = tempfile.mkdtemp(prefix="card4_review_")
    from ..config import get_settings
    get_settings.cache_clear()
    from .. import db
    db.init_db()


if __name__ == "__main__":
    _scratch_db()
    r = run(int(sys.argv[1]) if len(sys.argv) > 1 else 12)
    for x in r["rows"]:
        if not x["ok"]:
            print("FAIL", x["country"], "; ".join(x["problems"]))
    print(f"F4 card: {r['passed']}/{r['returns']} returns in {len(r['countries'])} countries")
    sys.exit(0 if r["ok"] else 1)
