"""The F3 card: Books & Accounts on 20 business months in 6 countries (FINANCE_GLOBAL_PLAN phase F3).

Each business is made from a seed with a known answer: invoices and bills (one in a foreign currency), a bank statement in that
country's wording read through the real CSV reader, and planted cases - a payment naming its invoice number, one naming the customer
with the same amount, a foreign payment at a different rate, two open invoices of the same amount paid by a line naming neither, bank
lines with no document, an overdue invoice in every ageing bucket, a fixed asset, a draft and a line left for later. Then, in code:

  matches         every sure match is the right document; the two-way line is unsure and never applied; the foreign match is found
  accounts        lines with no document get the account the answer expects
  exchange        the realised gain / loss equals the one worked out by hand
  reconciliation  bank only = the lines left; once posted, bank and books agree to the cent
  ageing          every bucket equals the answer
  close           the checklist names exactly what is missing; once fixed it is ready, the month locks, a later posting is refused
  reports         the trial balance balances and the balance sheet adds up

    python -m app.fin.card_f3        builds a scratch database, prints the card; exit 1 if any business fails
"""
from __future__ import annotations

import random
import sys
from typing import Any

from . import profile as PR
from . import spine as SP
from .desks import books as B

COUNTRIES = {"GB": ("GBP", "FPS {m}"), "US": ("USD", "ACH CREDIT {m}"), "IN": ("INR", "NEFT CR {m}"),
             "DE": ("EUR", "GUTSCHRIFT {m}"), "AU": ("AUD", "OSKO {m}"), "SG": ("SGD", "PAYNOW {m}")}
FOREIGN = {"GBP": ("EUR", 0.86, 0.88), "USD": ("EUR", 1.08, 1.10), "INR": ("USD", 84.0, 84.5), "EUR": ("USD", 0.92, 0.95),
           "AUD": ("USD", 1.52, 1.49), "SGD": ("USD", 1.34, 1.36)}
PERIOD = "2026-10"
AS_OF = "2026-12-31"


def _r(i: int) -> random.Random:
    return random.Random(5000 + i)


def run_one(i: int) -> dict[str, Any]:
    rnd = _r(i)
    cc = list(COUNTRIES)[i % 6]
    cur, credit = COUNTRIES[cc]
    t = f"card3-{i}"
    pv = PR.preview({"size": "business", "countries": [cc], "wants": [], "people": []})
    ws = PR.apply(t, {**pv["answers"], "currency": cur}, PR.preview({**pv["answers"], "currency": cur})["hash"])["id"]
    k = {"GBP": 1, "USD": 1, "INR": 80, "EUR": 1, "AUD": 1.5, "SGD": 1.3}[cur]
    run = lambda a, **x: B.run(t, a, {"workspace": ws, **x}, "card")   # noqa: E731
    bad: list[str] = []

    def inv(party, issue, due, amt, **x):
        return run("invoice", party=party, issue=issue, due=due, lines=[{"description": "Work", "qty": 1, "price": amt}], issue_now=True, **x)

    a1 = round(rnd.choice([400, 650, 900]) * k, 2)
    i1 = inv("Alpha Traders", "2026-10-02", "2026-10-30", a1)
    a2 = round(rnd.choice([300, 520, 780]) * k, 2)
    i2 = inv("Brightway Ltd", "2026-10-03", "2026-10-31", a2)
    fcur, r_book, r_pay = FOREIGN[cur]
    fa = 1000.0
    i3 = inv("Overseas Client", "2026-10-04", "2026-11-03", fa, currency=fcur, rate=r_book, rate_date="2026-10-04", rate_source="central bank")
    twin = round(250 * k, 2)
    i4 = inv("Twin One", "2026-10-05", "2026-11-04", twin)
    i5 = inv("Twin Two", "2026-10-05", "2026-11-04", twin)
    rent = round(rnd.choice([700, 1100]) * k, 2)
    b1 = run("bill", party="Landmark Property", issue="2026-10-01", due="2026-10-05", code="6100",
             lines=[{"description": "Rent", "qty": 1, "price": rent}], issue_now=True)
    # overdue invoices for ageing, one per bucket as of AS_OF
    age = {"not_due": ("2026-12-01", "2027-01-15"), "1_30": ("2026-11-01", "2026-12-10"), "31_60": ("2026-10-01", "2026-11-15"),
           "61_90": ("2026-09-15", "2026-10-15"), "over_90": ("2026-08-01", "2026-09-01")}
    want_age: dict[str, float] = {}
    for n, (b, (iss, due)) in enumerate(age.items()):
        amt = round((100 + 10 * n) * k, 2)
        if iss[:7] <= PERIOD or True:
            inv(f"Late Customer {n}", iss, due, amt)
        want_age[b] = amt
    draft = run("invoice", party="Not Sent Yet", issue="2026-10-20", due="2026-11-20", lines=[{"description": "x", "qty": 1, "price": 10}])
    paid_foreign = round(fa * r_pay, 2)
    lines = [("2026-10-12", a1, credit.format(m=f"ALPHA TRADERS REF {i1['number']}")),
             ("2026-10-14", a2, credit.format(m="BRIGHTWAY LTD")),
             ("2026-10-16", paid_foreign, credit.format(m="OVERSEAS CLIENT")),
             ("2026-10-18", twin, credit.format(m="CUSTOMER PAYMENT")),
             ("2026-10-03", -rent, "DD LANDMARK PROPERTY"),
             ("2026-10-09", -round(45 * k, 2), "DD BRITISH GAS UTILITIES"),
             ("2026-10-11", -round(12 * k, 2), "CARD SPOTIFY"),
             ("2026-10-21", -round(5 * k, 2), "MONTHLY ACCOUNT FEE"),
             ("2026-10-26", -round(30 * k, 2), "TRANSFER TO SAVINGS POT")]
    want_acct = {"DD BRITISH GAS UTILITIES": "6200", "CARD SPOTIFY": "6600", "MONTHLY ACCOUNT FEE": "6500"}
    csv = "Date,Narration,Debit,Credit\n" + "".join(f"{d},{n},{'' if a > 0 else f'{-a:.2f}'},{f'{a:.2f}' if a > 0 else ''}\n" for d, a, n in lines)
    SP.import_statement(t, ws, csv, "Business current", cur)
    run("asset", name="Laptop", cost=round(1440 * k, 2), start=PERIOD, life_months=36)

    m = run("matches")["lines"]
    by_n = {x["narration"]: x for x in m}
    get = lambda part: next(x for n, x in by_n.items() if part in n)   # noqa: E731
    exp = {"ALPHA TRADERS": i1["id"], "BRIGHTWAY": i2["id"], "LANDMARK": b1["id"]}
    for part, doc in exp.items():
        x = get(part)
        if not x.get("sure") or x.get("doc") != doc:
            bad.append(f"{part}: {x.get('why')}")
    tw = get("CUSTOMER PAYMENT")
    if tw.get("sure") or tw.get("doc") or sorted(tw.get("choices") or []) != sorted([i4["number"], i5["number"]]):
        bad.append(f"twin line: {tw.get('why')}")
    fx = get("OVERSEAS")
    if fx.get("doc") != i3["id"] or fx.get("sure"):
        bad.append(f"foreign line: {fx.get('why')}")
    for n, code in want_acct.items():
        if get(n).get("propose_account") != code:
            bad.append(f"{n}: proposed {get(n).get('propose_account')} not {code}")
    for x in m:
        if x.get("sure"):
            run("apply_match", txn=x["txn"], doc=x["doc"])
    gain = run("apply_match", txn=fx["txn"], doc=i3["id"])["fx_gain"]
    want_gain = round(paid_foreign - round(fa * r_book, 2), 2)
    if abs(gain - want_gain) > 0.004:
        bad.append(f"fx gain {gain} not {want_gain}")
    for n in want_acct:
        run("post_bank", txn=get(n)["txn"], code=want_acct[n])
    rc = run("reconcile", period=PERIOD)
    left = {get("CUSTOMER PAYMENT")["txn"], get("TRANSFER TO SAVINGS")["txn"]}
    if {x["txn"] for x in rc["bank_only"]} != left or rc["unexplained"] != 0:
        bad.append(f"reconcile before: bank only {len(rc['bank_only'])}, unexplained {rc['unexplained']}")
    ck = run("close_check", period=PERIOD)
    want_open = {"Every bank line of the month is in the books", "No draft invoices or bills dated in or before the month",
                 "Depreciation posted for the month", "Open foreign-currency documents revalued"}
    got_open = {x["item"] for x in ck["items"] if not x["ok"]}
    if got_open != want_open - {"Open foreign-currency documents revalued"}:   # the only foreign document is paid
        bad.append(f"checklist open {sorted(got_open)}")
    run("apply_match", txn=get("CUSTOMER PAYMENT")["txn"], doc=i4["id"])     # her choice
    run("post_bank", txn=get("TRANSFER TO SAVINGS")["txn"], code="1300")
    run("issue", doc=draft["id"])
    dep = run("depreciation", period=PERIOD)["amount"]
    if abs(dep - round(1440 * k / 36, 2)) > 0.004:
        bad.append(f"depreciation {dep}")
    rc = run("reconcile", period=PERIOD)
    if not rc["reconciled"]:
        bad.append(f"reconcile after: {rc['difference']}")
    ck = run("close_check", period=PERIOD)
    if not ck["ready"]:
        bad.append("checklist not ready after fixes: " + ", ".join(x["item"] for x in ck["items"] if not x["ok"]))
    else:
        run("close_lock", period=PERIOD, hash=ck["hash"])
        try:
            run("journal", day="2026-10-30", lines=[{"code": "6000", "debit": 1}, {"code": "1000", "credit": 1}])
            bad.append("posted into a locked month")
        except B.BooksError:
            pass
    ag = run("ageing", as_of=AS_OF)["by_party"]
    for n, b in enumerate(age):
        row = ag.get(f"Late Customer {n}") or {}
        if abs(row.get(b, 0) - want_age[b]) > 0.004:
            bad.append(f"ageing {b}: {row}")
    rep = run("reports", since="2026-10-01", upto="2026-12-31")
    if not rep["balanced"] or not rep["balance_sheet"]["checks"]:
        bad.append("reports do not add up")
    return {"business": i, "country": cc, "currency": cur, "ok": not bad, "problems": bad}


def run(n: int = 20) -> dict[str, Any]:
    rows = []
    for i in range(n):
        try:
            rows.append(run_one(i))
        except Exception as e:   # a crash is a failed business, not a stopped card
            rows.append({"business": i, "country": list(COUNTRIES)[i % 6], "ok": False, "problems": [f"{type(e).__name__}: {e}"]})
    return {"businesses": n, "countries": sorted({r["country"] for r in rows}), "passed": sum(r["ok"] for r in rows),
            "ok": all(r["ok"] for r in rows), "rows": rows}


def _scratch_db() -> None:
    import os
    import tempfile
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(prefix="card3_"), "card.db")
    from ..config import get_settings
    get_settings.cache_clear()
    from .. import db
    db.init_db()


if __name__ == "__main__":
    _scratch_db()
    r = run()
    for x in r["rows"]:
        if not x["ok"]:
            print("FAIL", x["business"], x["country"], "; ".join(x["problems"]))
    print(f"F3 card: {r['passed']}/{r['businesses']} business months in {len(r['countries'])} countries")
    sys.exit(0 if r["ok"] else 1)
