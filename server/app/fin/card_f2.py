"""The F2 card: Household Money on 40 households with statements in 6 countries (FINANCE_GLOBAL_PLAN phase F2).

Each household is made from a seed with a known answer: six months of a statement in that country's own wording (card payments,
direct debits, UPI, EFTPOS, NETS, Lastschrift), read through the real statement readers (CSV; OFX for the United States), then:

  categories     at least 90% of lines in the right category
  regular items  every bill, subscription and salary found (recall >= 95% over the card, precision >= 90%), next due within 3 days
  price rises    a subscription that went up is flagged
  forecast       next month's money out within 15% of the known expected amount, regular income within 5%

    python -m app.fin.card_f2        prints the card; exit 1 if it fails
"""
from __future__ import annotations

import calendar
import random
import sys
from datetime import date, timedelta
from typing import Any

from . import spine as SP
from .desks import household as H

COUNTRIES = {
    "GB": ("GBP", "CARD PAYMENT TO {m} {n} ON {d}", "DIRECT DEBIT {m} {n}", "SALARY {m}"),
    "US": ("USD", "POS DEBIT {m} #{n}", "ACH DEBIT {m} {n}", "PAYROLL {m}"),
    "IN": ("INR", "UPI/{m}/{n}/PAYMENT", "NACH DR {m} {n}", "SALARY CREDIT {m}"),
    "DE": ("EUR", "KARTENZAHLUNG {m} {n}", "LASTSCHRIFT {m} {n}", "GEHALT {m}"),
    "AU": ("AUD", "EFTPOS {m} {n}", "DIRECT DEBIT {m} {n}", "SALARY {m}"),
    "SG": ("SGD", "NETS {m} {n}", "GIRO {m} {n}", "SALARY {m}"),
}
RENT = {"GB": "RENT OAKWOOD LETTINGS", "US": "RENT PARKVIEW APTS", "IN": "HOUSE RENT SHARMA", "DE": "MIETE HAUSVERWALTUNG",
        "AU": "RENT HARBOUR REALTY", "SG": "RENT HDB FLAT"}
UTIL = {"GB": ["BRITISH GAS", "THAMES WATER", "VIRGIN MEDIA"], "US": ["CON EDISON", "VERIZON", "COMCAST"],
        "IN": ["TATA POWER", "AIRTEL", "JIO"], "DE": ["STADTWERKE", "TELEKOM", "VODAFONE"],
        "AU": ["AGL", "TELSTRA", "ORIGIN ENERGY"], "SG": ["SP SERVICES", "SINGTEL", "STARHUB"]}
SUBS = ["NETFLIX", "SPOTIFY", "DISNEY PLUS", "YOUTUBE PREMIUM", "ICLOUD", "AUDIBLE", "MICROSOFT 365"]
SHOPS = {"GB": [("TESCO", "groceries"), ("SAINSBURYS", "groceries"), ("ALDI", "groceries"), ("PRET A MANGER", "eating_out"),
                ("NANDOS", "eating_out"), ("TFL TRAVEL", "transport"), ("SHELL", "transport"), ("ARGOS", "shopping"), ("BOOTS", "health")],
         "US": [("WALMART", "groceries"), ("KROGER", "groceries"), ("TRADER JOES", "groceries"), ("STARBUCKS", "eating_out"),
                ("DOORDASH", "eating_out"), ("CHEVRON", "transport"), ("LYFT", "transport"), ("TARGET", "shopping"), ("CVS", "health")],
         "IN": [("BIGBASKET", "groceries"), ("DMART", "groceries"), ("BLINKIT", "groceries"), ("SWIGGY", "eating_out"),
                ("ZOMATO", "eating_out"), ("OLA", "transport"), ("FASTAG", "transport"), ("FLIPKART", "shopping"), ("APOLLO PHARMACY", "health")],
         "DE": [("REWE MARKT", "groceries"), ("EDEKA", "groceries"), ("LIDL", "groceries"), ("LIEFERANDO", "eating_out"),
                ("CAFE CENTRAL", "eating_out"), ("DEUTSCHE BAHN", "transport"), ("ARAL", "transport"), ("ZALANDO", "shopping"), ("APOTHEKE", "health")],
         "AU": [("WOOLWORTHS", "groceries"), ("COLES", "groceries"), ("ALDI", "groceries"), ("UBER EATS", "eating_out"),
                ("CAFE BONDI", "eating_out"), ("OPAL TRAVEL", "transport"), ("SHELL", "transport"), ("KMART", "shopping"), ("CHEMIST WAREHOUSE", "health")],
         "SG": [("NTUC FAIRPRICE", "groceries"), ("COLD STORAGE", "groceries"), ("GRABFOOD", "eating_out"), ("FOODPANDA", "eating_out"),
                ("TOAST BOX CAFE", "eating_out"), ("MRT TRANSIT", "transport"), ("GRAB", "transport"), ("SHOPEE", "shopping"), ("GUARDIAN PHARMACY", "health")]}
STRANGERS = ["J SMITH", "MARKET STALL", "K PATEL", "HANDYMAN"]
SCALE = {"GBP": 1, "USD": 1.3, "INR": 80, "EUR": 1.15, "AUD": 2, "SGD": 1.7}
MONTHS = [(2026, m) for m in range(5, 11)]   # May to October 2026, six full months
NEXT = (2026, 11)


def _d(y: int, m: int, day: int) -> date:
    return date(y, m, min(day, calendar.monthrange(y, m)[1]))


def make(i: int) -> dict[str, Any]:
    rnd = random.Random(1000 + i)
    cc = list(COUNTRIES)[i % 6]
    cur, card, dd, sal = COUNTRIES[cc]
    k = SCALE[cur]
    lines: list[tuple[date, float, str, str]] = []          # day, amount (+ in), narration, true category
    regular: list[dict[str, Any]] = []                      # the known answer
    gig = i % 5 == 4
    if gig:
        for y, m in MONTHS:
            for wk in range(4):
                lines.append((_d(y, m, 3 + wk * 7), round(rnd.uniform(150, 420) * k, 2), "UBER PAYOUT", "income"))
        salary = 0.0
    else:
        salary = round(rnd.choice([2400, 3100, 3800, 4500]) * k, 2)
        pay_day = rnd.choice([25, 26, 27, 28])
        for y, m in MONTHS:
            lines.append((_d(y, m, pay_day), salary, sal.format(m="ACME"), "income"))
        regular.append({"name": "ACME", "kind": "income", "next": _d(*NEXT, pay_day), "amount": salary})
    rent = round(rnd.choice([700, 900, 1200, 1500]) * k, 2)
    for y, m in MONTHS:
        lines.append((_d(y, m, 1), -rent, RENT[cc], "rent_mortgage"))
    regular.append({"name": RENT[cc].split()[-1], "kind": "bill", "next": _d(*NEXT, 1), "amount": rent})
    for u in rnd.sample(UTIL[cc], 2):
        base, day = rnd.uniform(30, 120) * k, rnd.randint(5, 20)
        for y, m in MONTHS:
            lines.append((_d(y, m, day), -round(base * rnd.uniform(0.95, 1.05), 2), dd.format(m=u, n=rnd.randint(1000, 9999)), "utilities"))
        regular.append({"name": u, "kind": "bill", "next": _d(*NEXT, day), "amount": base})
    rise_to = None
    for j, s in enumerate(rnd.sample(SUBS, rnd.randint(1, 3))):
        price, day = round(rnd.choice([4.99, 9.99, 11.99, 15.99]) * k, 2), rnd.randint(2, 27)
        rises = j == 0 and i % 4 == 0
        for n, (y, m) in enumerate(MONTHS):
            amt = round(price * 1.1, 2) if rises and n == len(MONTHS) - 1 else price
            lines.append((_d(y, m, day), -amt, card.format(m=s, n=rnd.randint(100, 999), d=f"{day:02d}"), "subscriptions"))
        regular.append({"name": s, "kind": "subscription", "next": _d(*NEXT, day), "amount": round(price * 1.1, 2) if rises else price})
        if rises:
            rise_to = s
    if i % 3 == 0:   # a quarterly water bill seen twice
        amt = round(rnd.uniform(60, 90) * k, 2)
        lines += [(date(2026, 6, 15), -amt, dd.format(m="WATER BOARD", n=4411), "utilities"),
                  (date(2026, 9, 15), -amt, dd.format(m="WATER BOARD", n=4411), "utilities")]
        regular.append({"name": "WATER BOARD", "kind": "bill", "next": date(2026, 12, 15), "amount": amt})
    var_mean = 0.0
    for y, m in MONTHS:
        days = calendar.monthrange(y, m)[1]
        for name, cat in SHOPS[cc]:
            times, lo, hi = {"groceries": (3, 8, 70), "eating_out": (2, 4, 30), "transport": (2, 3, 40), "shopping": (1, 10, 90),
                             "health": (1, 3, 25)}[cat]
            for _ in range(times):
                amt = round(rnd.uniform(lo, hi) * k, 2)
                lines.append((date(y, m, rnd.randint(1, days)), -amt, card.format(m=name, n=rnd.randint(1000, 9999), d="01"), cat))
        for _ in range(2):
            lines.append((date(y, m, rnd.randint(1, days)), -round(rnd.uniform(10, 40) * k, 2), f"PAYMENT TO {rnd.choice(STRANGERS)}", "other"))
    for name, cat in SHOPS[cc]:
        times, lo, hi = {"groceries": (3, 8, 70), "eating_out": (2, 4, 30), "transport": (2, 3, 40), "shopping": (1, 10, 90),
                         "health": (1, 3, 25)}[cat]
        var_mean += times * (lo + hi) / 2 * k
    var_mean += 2 * 25 * k
    nxt_out = sum(r["amount"] for r in regular if r["kind"] != "income" and (r["next"].year, r["next"].month) == NEXT) + var_mean
    lines.sort()
    return {"i": i, "country": cc, "currency": cur, "lines": lines, "regular": regular, "rise": rise_to, "gig": gig,
            "expect": {"out": nxt_out, "regular_in": salary}}


def statement(h: dict[str, Any]) -> list[dict[str, Any]]:
    """Write the statement the way her bank would, then read it back through the real readers."""
    if h["country"] == "US":
        body = "".join(f"<STMTTRN><TRNTYPE>{'CREDIT' if a > 0 else 'DEBIT'}<DTPOSTED>{d:%Y%m%d}<TRNAMT>{a:.2f}<FITID>F{n}<NAME>{t}</STMTTRN>\n"
                       for n, (d, a, t, _) in enumerate(h["lines"]))
        rows = SP.parse_ofx(f"OFXHEADER:100\n<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><CURDEF>USD<BANKTRANLIST>\n{body}</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>")
    else:
        csv = "Date,Narration,Debit,Credit\n" + "".join(
            f"{d.isoformat()},{t},{'' if a > 0 else f'{-a:.2f}'},{f'{a:.2f}' if a > 0 else ''}\n" for d, a, t, _ in h["lines"])
        rows = SP.parse_csv(csv)
    from .calc import to_minor
    return [{"day": r["day"], "amount_minor": to_minor(r["amount"], h["currency"]), "narration": r["narration"], "currency": h["currency"]}
            for r in rows]


def check(h: dict[str, Any]) -> dict[str, Any]:
    rows = statement(h)
    bad: list[str] = []
    if len(rows) != len(h["lines"]):
        bad.append(f"read {len(rows)} of {len(h['lines'])} lines")
    cats = H.categorise(rows)
    right = sum(1 for r, (_, _, _, truth) in zip(cats, h["lines"]) if r["category"] == truth)
    acc = right / max(1, len(rows))
    if acc < 0.9:
        bad.append(f"categories {acc:.0%}")
    rec = H.recurring(rows, h["currency"])
    hit = 0
    for t in h["regular"]:
        f = next((x for x in rec["found"] if t["name"].lower() in x["sample"].lower() and x["kind"] == t["kind"]), None)
        if f is None:
            bad.append(f"missed {t['kind']} {t['name']}")
            continue
        if abs((date.fromisoformat(f["next_due"]) - t["next"]).days) > 3:
            bad.append(f"{t['name']} next due {f['next_due']} not {t['next']}")
            continue
        hit += 1
    names = [t["name"].lower() for t in h["regular"]]
    false = [x["sample"] for x in rec["found"] if not any(n in x["sample"].lower() for n in names)]
    if h["rise"]:
        f = next((x for x in rec["subscriptions"] if h["rise"].lower() in x["sample"].lower()), None)
        if not f or not f["price_rise"]:
            bad.append(f"price rise of {h['rise']} not flagged")
    fc = H.forecast(rows, h["currency"], 1)["months"][0]
    if abs(fc["out"] - h["expect"]["out"]) > 0.15 * h["expect"]["out"]:
        bad.append(f"forecast out {fc['out']:.0f} vs {h['expect']['out']:.0f}")
    if not h["gig"]:
        reg_in = sum(x["typical"] for x in rec["income"])
        if abs(reg_in - h["expect"]["regular_in"]) > 0.05 * h["expect"]["regular_in"]:
            bad.append(f"regular income {reg_in:.0f} vs {h['expect']['regular_in']:.0f}")
    return {"household": h["i"], "country": h["country"], "ok": not bad and not false, "categories": round(acc, 3),
            "found": hit, "expected": len(h["regular"]), "false": false, "problems": bad}


def run(n: int = 40) -> dict[str, Any]:
    rows = [check(make(i)) for i in range(n)]
    found, expected = sum(r["found"] for r in rows), sum(r["expected"] for r in rows)
    false = sum(len(r["false"]) for r in rows)
    recall, precision = found / max(1, expected), found / max(1, found + false)
    return {"households": n, "countries": sorted({r["country"] for r in rows}), "passed": sum(r["ok"] for r in rows),
            "recall": round(recall, 3), "precision": round(precision, 3),
            "ok": recall >= 0.95 and precision >= 0.9 and all(r["ok"] for r in rows), "rows": rows}


if __name__ == "__main__":
    r = run()
    for x in r["rows"]:
        if not x["ok"]:
            print("FAIL", x["household"], x["country"], "; ".join(x["problems"] + [f"false: {f}" for f in x["false"]]))
    print(f"F2 card: {r['passed']}/{r['households']} households in {len(r['countries'])} countries, regular items recall "
          f"{r['recall']:.0%}, precision {r['precision']:.0%}")
    sys.exit(0 if r["ok"] else 1)
