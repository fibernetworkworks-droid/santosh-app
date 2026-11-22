"""F2 of docs/FINANCE_GLOBAL_PLAN.md - Household Money (employee `household`, tool `household_money`), for people and sole traders
in any country.

Parts: categorise her transactions, budget and cash flow, bills and subscriptions found from her own statements (with the next due
date and price rises), a 3-month forecast, savings goals, net worth, the forgotten money finder, retirement readiness, benefits and
credits check, life modes (student, renter, expat, gig, family), bereavement admin, will and nominee check.

Everything is arithmetic on HER numbers (the F0 spine, or rows she gives) plus country rules at their D3 level: an official
service's name or link is shown with 'not confirmed - check this' until it is read; no state pension, benefit amount or tax rate
is ever used in a sum unless a person confirmed it. Hoola never pays a bill: paying stays with Hoola Wallet and her tap.
"""
from __future__ import annotations

import calendar
import re
import statistics
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from .. import laws as L
from .. import pack as P
from .safety import NOT_CONFIRMED, SafetyError, _cc, shown

# ---- categories (words in narrations, worldwide; her own rules win) ---------------------------------------------------------

CATEGORIES: list[tuple[str, tuple[str, ...]]] = [
    ("income", ("salary", "payroll", "wages", "gehalt", "lohn", "stipend", "pension credit", "dividend", "interest paid", "refund",
                "uber payout", "deliveroo payout", "upwork", "fiverr", "client payment", "invoice paid")),
    ("rent_mortgage", ("rent", "mortgage", "miete", "landlord", "letting", "housing loan", "home loan", "hdb", "strata")),
    ("utilities", ("british gas", "octopus energy", "edf", "eon", "e.on", "thames water", "water", "electric", "power", "gas bill",
                   "con edison", "pg&e", "duke energy", "vattenfall", "stadtwerke", "agl", "origin energy", "sp services", "bescom",
                   "tata power", "adani electricity", "council tax", "broadband", "internet", "bt group", "virgin media", "comcast",
                   "xfinity", "verizon", "at&t", "t-mobile", "vodafone", "telekom", "o2", "airtel", "jio", "singtel", "starhub",
                   "telstra", "optus", "mobile bill")),
    ("insurance", ("insurance", "assurance", "versicherung", "allianz", "aviva", "geico", "state farm", "lic ", "hdfc life",
                   "aia", "prudential", "nrma")),
    ("subscriptions", ("netflix", "spotify", "disney", "amazon prime", "prime video", "apple.com/bill", "icloud", "youtube premium",
                       "google one", "hotstar", "hulu", "audible", "microsoft 365", "adobe", "dropbox", "chatgpt", "openai",
                       "patreon", "gym", "fitness", "peloton", "membership")),
    ("groceries", ("tesco", "sainsbury", "asda", "morrisons", "aldi", "lidl", "waitrose", "walmart", "kroger", "costco", "safeway",
                   "whole foods", "trader joe", "rewe", "edeka", "kaufland", "netto", "woolworths", "coles", "fairprice", "ntuc",
                   "cold storage", "bigbasket", "dmart", "reliance fresh", "blinkit", "zepto", "instamart", "carrefour", "spar",
                   "supermarket", "grocery", "kirana")),
    ("eating_out", ("restaurant", "cafe", "coffee", "starbucks", "mcdonald", "kfc", "burger", "pizza", "domino", "subway",
                    "pret", "greggs", "nando", "swiggy", "zomato", "uber eats", "doordash", "grubhub", "deliveroo", "just eat",
                    "lieferando", "foodpanda", "grabfood")),
    ("transport", ("uber", "lyft", "ola", "grab", "bolt", "tfl", "transport for london", "metro", "mrt", "bus", "rail", "train",
                   "deutsche bahn", "trainline", "amtrak", "fuel", "petrol", "shell", "bp ", "esso", "chevron", "exxon", "aral",
                   "parking", "toll", "fastag", "opal", "myki")),
    ("shopping", ("amazon", "ebay", "argos", "target", "best buy", "ikea", "zalando", "otto", "flipkart", "myntra", "ajio",
                  "shopee", "lazada", "kmart", "primark", "h&m", "zara", "uniqlo", "decathlon")),
    ("health", ("pharmacy", "chemist", "boots", "cvs", "walgreens", "apotheke", "apollo", "dentist", "doctor", "clinic",
                "hospital", "medical", "optician")),
    ("education", ("school", "tuition", "college", "university", "course", "udemy", "coursera", "student loan")),
    ("cash", ("atm", "cash withdrawal", "geldautomat")),
    ("transfers", ("transfer to", "transfer from", "to savings", "standing order to", "neft", "imps", "faster payment to self")),
    ("fees", ("fee", "charge", "overdraft", "interest charged", "late payment")),
]
OUT_ORDER = [c for c, _ in CATEGORIES if c != "income"] + ["other"]
_NOISE = re.compile(r"\b(card payment to|card purchase|pos|direct debit|dd|so|standing order|payment to|paid to|purchase|visa|"
                    r"mastercard|debit card|contactless|ach debit|ach|upi|on \d{1,2} \w{3}|ref[:#]?\s*\S+)\b", re.I)


def _key(narration: str) -> str:
    """The payee, without card words, dates, references and numbers - so the same payee groups across months."""
    s = _NOISE.sub(" ", str(narration or "").lower())
    s = re.sub(r"[\d#*/\\\-_.:,]+", " ", s)
    s = re.sub(r"\b(ltd|limited|gmbh|inc|llc|plc|pty|pte|co|the|uk|us|de|sg|au|in)\b", " ", s)
    w = [x for x in s.split() if len(x) > 1]
    return " ".join(w[:3])


def category(narration: str, amount_minor: int, rules: dict[str, str] | None = None) -> str:
    n = f" {str(narration or '').lower()} "
    for word, cat in (rules or {}).items():
        if word and word.lower() in n:
            return cat
    for cat, words in CATEGORIES:
        if cat == "income" and amount_minor < 0:
            continue
        if any(w in n for w in words):
            return cat
    return "income" if amount_minor > 0 else "other"


# ---- the transactions -----------------------------------------------------------------------------------------------------

def _rows(tenant: str, a: dict[str, Any]) -> list[dict[str, Any]]:
    """Her transactions as [{day, amount_minor, narration, currency}]: rows she gives, else her workspace's imported statements."""
    if a.get("rows"):
        out = []
        for r in list(a["rows"])[:20000]:
            m = r.get("amount_minor")
            if m is None:
                from ..calc import to_minor
                m = to_minor(Decimal(str(r.get("amount") or 0)), str(r.get("currency") or a.get("currency") or "USD"))
            out.append({"day": str(r.get("day") or r.get("date") or "")[:10], "amount_minor": int(m),
                        "narration": str(r.get("narration") or ""), "currency": str(r.get("currency") or a.get("currency") or "")})
        return [r for r in out if re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["day"])]
    if a.get("workspace"):
        from .. import spine as SP
        return [{"day": t["day"], "amount_minor": t["amount_minor"], "narration": t["narration"], "currency": t["currency"]}
                for t in SP.txns(tenant, str(a["workspace"]), limit=20000)]
    raise SafetyError("Give her transactions: workspace (imported statements) or rows [{day, amount, narration}].")


def _cur(rows: list[dict[str, Any]], a: dict[str, Any]) -> str:
    return str(a.get("currency") or next((r["currency"] for r in rows if r.get("currency")), "") or "USD").upper()


def _units(minor: int, cur: str) -> float:
    return round(minor / (10 ** P.minor_unit(cur)), P.minor_unit(cur))


def categorise(rows: list[dict[str, Any]], rules: dict[str, str] | None = None) -> list[dict[str, Any]]:
    return [{**r, "category": category(r["narration"], r["amount_minor"], rules)} for r in rows]


def budget(rows: list[dict[str, Any]], cur: str, limits: dict[str, float] | None = None, rules: dict[str, str] | None = None) -> dict[str, Any]:
    cat = categorise(rows, rules)
    months: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in cat:
        months[r["day"][:7]][r["category"] if r["amount_minor"] < 0 or r["category"] == "income" else "income"] += r["amount_minor"]
    table = []
    for m in sorted(months):
        c = months[m]
        inn = sum(v for k, v in c.items() if v > 0)
        out = -sum(v for v in c.values() if v < 0)
        table.append({"month": m, "in": _units(inn, cur), "out": _units(out, cur), "net": _units(inn - out, cur),
                      "by_category": {k: _units(-v, cur) for k, v in sorted(c.items()) if v < 0}})
    over = []
    if limits and table:
        last = table[-1]
        for k, lim in limits.items():
            spent = last["by_category"].get(k, 0.0)
            if spent > float(lim):
                over.append({"category": k, "limit": float(lim), "spent": spent, "month": last["month"]})
    return {"currency": cur, "months": table, "over_budget": over, "uncategorised": sum(1 for r in cat if r["category"] == "other")}


def _add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


PERIODS = (("weekly", 7, 2), ("fortnightly", 14, 3), ("monthly", 30.4, 4), ("quarterly", 91.3, 10), ("yearly", 365.25, 20))


def recurring(rows: list[dict[str, Any]], cur: str, rules: dict[str, str] | None = None) -> dict[str, Any]:
    """Bills, subscriptions and regular income found in her own history: the same payee, a similar amount, a steady gap."""
    groups: dict[tuple[str, bool], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        k = _key(r["narration"])
        if k:
            groups[(k, r["amount_minor"] > 0)].append(r)
    found = []
    for (k, income), g in groups.items():
        g = sorted(g, key=lambda x: x["day"])
        if len(g) < 2:
            continue
        days = [date.fromisoformat(x["day"]) for x in g]
        gaps = [(b - a).days for a, b in zip(days, days[1:])]
        if not gaps or min(gaps) <= 0:
            continue
        med = statistics.median(gaps)
        per = next(((n, ln, tol) for n, ln, tol in PERIODS if abs(med - ln) <= tol), None)
        if per is None or any(abs(x - per[1]) > per[2] * 1.5 for x in gaps):
            continue
        need = 2 if per[0] in ("quarterly", "yearly") else 3
        if len(g) < need:
            continue
        amts = [abs(x["amount_minor"]) for x in g]
        typical = statistics.median(amts)
        if any(abs(x - typical) > max(0.25 * typical, 1) for x in amts[:-1]):
            continue   # amounts jump about: not a regular payment (the last one may have risen; checked below)
        if len(g) == 2 and abs(amts[0] - amts[1]) > 0.05 * max(amts):
            continue   # seen only twice: call it regular only when it is (nearly) the same amount
        last = days[-1]
        nxt = _add_months(last, {"monthly": 1, "quarterly": 3, "yearly": 12}[per[0]]) if per[0] in ("monthly", "quarterly", "yearly") \
            else last + timedelta(days=int(per[1]))
        cat = category(g[-1]["narration"], g[-1]["amount_minor"], rules)
        rise = None
        if len(amts) >= 2 and amts[-1] > amts[-2] * 1.03:
            rise = {"from": _units(amts[-2], cur), "to": _units(amts[-1], cur), "pct": round((amts[-1] / amts[-2] - 1) * 100, 1)}
        kind = "income" if income else ("subscription" if cat == "subscriptions" else "bill")
        found.append({"payee": k, "kind": kind, "category": cat, "every": per[0], "amount": _units(amts[-1], cur),
                      "typical": _units(int(typical), cur), "times_seen": len(g), "last": last.isoformat(), "next_due": nxt.isoformat(),
                      "price_rise": rise, "sample": g[-1]["narration"][:80]})
    found.sort(key=lambda x: (x["kind"], x["next_due"]))
    monthly = {"monthly": 1, "weekly": 52 / 12, "fortnightly": 26 / 12, "quarterly": 1 / 3, "yearly": 1 / 12}
    out_month = sum(f["amount"] * monthly[f["every"]] for f in found if f["kind"] != "income")
    return {"currency": cur, "found": found, "bills": [f for f in found if f["kind"] == "bill"],
            "subscriptions": [f for f in found if f["kind"] == "subscription"], "income": [f for f in found if f["kind"] == "income"],
            "regular_out_per_month": round(out_month, 2),
            "pay": "Hoola does not pay bills from here. To pay one, use Hoola Wallet: it gets the payment ready and waits for your tap."}


def forecast(rows: list[dict[str, Any]], cur: str, months_ahead: int = 3, start_balance: float | None = None,
             rules: dict[str, str] | None = None) -> dict[str, Any]:
    """Next months: regular income and bills where they fall, plus her usual other spending (median of her last 3 full months)."""
    if not rows:
        raise SafetyError("No transactions to forecast from.")
    rec = recurring(rows, cur, rules)
    keys = {(f["payee"], f["kind"] == "income") for f in rec["found"]}
    last_day = max(date.fromisoformat(r["day"]) for r in rows)
    full = sorted({r["day"][:7] for r in rows})
    if date(last_day.year, last_day.month, calendar.monthrange(last_day.year, last_day.month)[1]) != last_day:
        full = [m for m in full if m != last_day.strftime("%Y-%m")]
    full = full[-3:]
    other_in, other_out = defaultdict(int), defaultdict(int)
    for r in rows:
        if r["day"][:7] in full and (_key(r["narration"]), r["amount_minor"] > 0) not in keys:
            (other_in if r["amount_minor"] > 0 else other_out)[r["day"][:7]] += abs(r["amount_minor"])
    med_in = statistics.median([other_in.get(m, 0) for m in full]) if full else 0
    med_out = statistics.median([other_out.get(m, 0) for m in full]) if full else 0
    out, bal = [], start_balance
    first = _add_months(date(last_day.year, last_day.month, 1), 1)
    for i in range(max(1, min(int(months_ahead or 3), 12))):
        m0 = _add_months(first, i)
        m1 = _add_months(m0, 1)
        reg_in = reg_out = 0.0
        for f in rec["found"]:
            d = date.fromisoformat(f["next_due"])
            step = {"weekly": 7, "fortnightly": 14}.get(f["every"])
            while d < m1:
                if d >= m0:
                    if f["kind"] == "income":
                        reg_in += f["typical"]
                    else:
                        reg_out += f["amount"]
                d = d + timedelta(days=step) if step else _add_months(d, {"monthly": 1, "quarterly": 3, "yearly": 12}[f["every"]])
        inn = reg_in + _units(int(med_in), cur)
        o = reg_out + _units(int(med_out), cur)
        row = {"month": m0.strftime("%Y-%m"), "in": round(inn, 2), "out": round(o, 2), "net": round(inn - o, 2),
               "regular_out": round(reg_out, 2), "usual_other_out": _units(int(med_out), cur)}
        if bal is not None:
            bal = round(bal + inn - o, 2)
            row["end_balance"] = bal
        out.append(row)
    low = [r for r in out if r.get("end_balance") is not None and r["end_balance"] < 0]
    return {"currency": cur, "based_on_months": full, "months": out,
            "warning": f"Your balance may go below zero in {low[0]['month']}." if low else "",
            "says": "A forecast from your own history, not a promise: one-off costs and changes in pay are not in it."}


# ---- goals, net worth, retirement (her numbers and her assumptions only) ----------------------------------------------------

def goal(a: dict[str, Any]) -> dict[str, Any]:
    target, saved = float(a.get("target") or 0), float(a.get("saved") or 0)
    by = date.fromisoformat(str(a.get("by") or "")[:10]) if a.get("by") else None
    today = date.fromisoformat(str(a.get("today") or date.today().isoformat())[:10])
    if target <= 0 or not by or by <= today:
        raise SafetyError("goal: target (amount), by (a future date YYYY-MM-DD), saved (so far).")
    months = max(1, (by.year - today.year) * 12 + by.month - today.month)
    r = float(a.get("return_pct") or 0) / 100 / 12
    need = target - saved * (1 + r) ** months
    if need <= 0:
        per = 0.0
    elif r:
        per = need * r / ((1 + r) ** months - 1)
    else:
        per = need / months
    return {"target": target, "saved": saved, "by": by.isoformat(), "months": months, "per_month": round(per, 2),
            "assumed_return_pct": float(a.get("return_pct") or 0),
            "says": ("Already enough at that growth." if per == 0 else
                     f"Put aside {per:,.2f} a month for {months} months.") +
                    (" The growth rate is your assumption, not a promise." if r else "")}


def net_worth(a: dict[str, Any]) -> dict[str, Any]:
    base = str(a.get("currency") or "USD").upper()
    rates = {str(x.get("currency", "")).upper(): x for x in a.get("fx") or []}
    tot_a = tot_l = 0.0
    rows, missing = [], []
    for it in a.get("items") or []:
        cur = str(it.get("currency") or base).upper()
        amt = float(it.get("amount") or 0)
        if cur != base:
            fx = rates.get(cur)
            if not fx or not fx.get("rate") or not fx.get("date") or not fx.get("source"):
                missing.append(cur)
                continue
            amt = amt * float(fx["rate"])
        liab = str(it.get("kind") or "asset") == "liability"
        tot_l += amt if liab else 0
        tot_a += 0 if liab else amt
        rows.append({"name": it.get("name", ""), "kind": "liability" if liab else "asset", "in_" + base.lower(): round(amt, 2)})
    return {"currency": base, "assets": round(tot_a, 2), "liabilities": round(tot_l, 2), "net_worth": round(tot_a - tot_l, 2),
            "items": rows, "left_out": sorted(set(missing)),
            "says": ("Left out, no dated exchange rate given: " + ", ".join(sorted(set(missing))) + "." if missing else "")}


def retirement(a: dict[str, Any], cc: str) -> dict[str, Any]:
    pot, monthly = float(a.get("pot") or 0), float(a.get("monthly") or 0)
    years = int(a.get("years") or 0)
    if years <= 0:
        raise SafetyError("retirement: years (until you stop work), pot (saved now), monthly (you add), want_monthly (income you want).")
    want = float(a.get("want_monthly") or 0)
    rates = [float(a["real_return_pct"])] if a.get("real_return_pct") not in (None, "") else [2.0, 4.0, 6.0]
    scen = []
    for rp in rates:
        r = rp / 100 / 12
        n = years * 12
        fv = pot * (1 + r) ** n + (monthly * (((1 + r) ** n - 1) / r) if r else monthly * n)
        draw = fv * 0.04 / 12   # the 4% rule of thumb, shown as such
        scen.append({"real_return_pct": rp, "pot_at_retirement": round(fv, 2), "monthly_at_4pct": round(draw, 2),
                     "gap_monthly": round(max(0.0, want - draw), 2) if want else None})
    state = shown(cc, "pension.state") if P.load(cc) else None
    return {"country": cc, "scenarios": scen, "state_pension": state,
            "says": "Today's money (after inflation). Returns are assumptions, not forecasts; the 4% rule is a rough guide. "
                    + ("Your state pension is not added in: Hoola only adds it once its amount is confirmed. " if state else "")
                    + L.NOT_ADVICE}


# ---- country help: forgotten money, benefits, life modes, bereavement, wills -------------------------------------------------

def forgotten(a: dict[str, Any], cc: str, rows: list[dict[str, Any]] | None) -> dict[str, Any]:
    out = {"country": cc, "where_to_look": [], "quiet_accounts": []}
    if P.load(cc):
        for path in ("unclaimed.finder", "unclaimed.pensions", "unclaimed.insurance"):
            v = shown(cc, path)
            if v:
                out["where_to_look"].append(v)
    if not out["where_to_look"]:
        out["where_to_look"] = ["Ask each bank, pension and insurer you ever used whether they hold money for you (use your old addresses)."]
    if a.get("workspace"):
        from .. import spine as SP
        today = date.fromisoformat(str(a.get("today") or date.today().isoformat())[:10])
        for acc in SP.accounts(a["_tenant"], str(a["workspace"])):
            last = acc.get("last_day") or ""
            if last and (today - date.fromisoformat(last)).days > 365:
                out["quiet_accounts"].append({"account": acc["name"], "last_activity": last})
    return out


def benefits(cc: str) -> dict[str, Any]:
    if P.load(cc) is None:
        return {"country": cc, "checkers": [], "says": f"Hoola has no benefits guide for {cc} yet - ask your government's official site."}
    checkers = [x for x in (shown(cc, "benefits.checker"), shown(cc, "benefits.tax_credits")) if x]
    return {"country": cc, "checkers": checkers,
            "says": "Hoola points you to the official checker; it does not decide whether you qualify or how much you get."}


LIFE = {
    "student": ["Make a monthly budget around term dates and when the loan or grant arrives",
                "Check for a student bank account with a free overdraft and its end date",
                "Keep proof of fees and course dates (needed for tax, visas and discounts)"],
    "renter": ["Keep the tenancy agreement, the deposit receipt and photos of the home on the day you move in",
               "Find out how your deposit is protected", "Set rent and bills to leave the day after pay arrives"],
    "expat": ["Keep one account open in your home country and know which country taxes you",
              "Note exchange rates and fees each time you send money home", "Tell banks and pensions your new address"],
    "gig": ["Put a share of every payout aside for tax in a separate pot", "Keep a record of expenses as they happen",
            "Smooth your income: pay yourself the same each month from a buffer"],
    "family": ["Write down who pays what and when", "Name a backup person for each account", "Plan for school and childcare costs by month"],
}


def life_mode(mode: str, cc: str) -> dict[str, Any]:
    mode = str(mode or "").lower()
    if mode not in LIFE:
        raise SafetyError("mode: " + " | ".join(LIFE))
    steps = list(LIFE[mode])
    if P.load(cc):
        extra = {"renter": "housing.deposit_protection", "student": "benefits.student", "gig": "benefits.self_employed_tax"}.get(mode)
        v = shown(cc, extra) if extra else None
        if v:
            steps.append(v)
    return {"country": cc, "mode": mode, "steps": steps}


def bereavement(a: dict[str, Any], cc: str) -> dict[str, Any]:
    tell = shown(cc, "bereavement.tell_once") if P.load(cc) else None
    steps = ["Get several certified copies of the death certificate", "Find the will (and who the executor is)",
             "List every bank, card, loan, pension, insurer, utility and subscription from the statements",
             "Tell each one in writing and stop direct debits that are no longer needed",
             "Do not pay debts that were only in the person's name before asking the estate's adviser"]
    if tell:
        steps.insert(1, f"One official service may tell many offices at once: {tell}")
    rec = None
    if a.get("workspace") or a.get("rows"):
        rows = _rows(a["_tenant"], a)
        rec = recurring(rows, _cur(rows, a))["found"]
    letter = ("To: [organisation]\nRe: [name of the person who died], account / reference [last 4 digits]\n\n"
              "I am writing to tell you that [name] died on [date]. I am the [executor / next of kin]. Please freeze the account, "
              "stop all payments, and tell me what you need to close it. A copy of the death certificate is attached.\n\n[your name]\n")
    return {"country": cc, "steps": steps, "who_to_tell": [f["payee"] for f in rec or [] if f["kind"] != "income"],
            "letter": letter, "she_sends": True}


def will_check(a: dict[str, Any], cc: str) -> dict[str, Any]:
    accs = list(a.get("accounts") or [])
    if a.get("workspace") and not accs:
        from .. import spine as SP
        accs = [{"name": x["name"], "nominee": None} for x in SP.accounts(a["_tenant"], str(a["workspace"]))]
    missing = [x.get("name", "") for x in accs if not x.get("nominee")]
    out = {"country": cc, "accounts": len(accs), "no_nominee_recorded": missing,
           "steps": ["Add a nominee or beneficiary on each account that allows one", "Keep a list of accounts where your family can find it",
                     "Review after a marriage, a divorce or a child"]}
    reg = shown(cc, "estate.will_registry") if P.load(cc) else None
    if reg:
        out["steps"].append(f"Registering a will: {reg}")
    out["says"] = "Hoola does not write a will; a lawyer or notary in your country does. " + L.NOT_ADVICE
    return out


# ---- the tool's entry ------------------------------------------------------------------------------------------------------

ACTIONS = ("budget", "bills", "forecast", "goal", "net_worth", "forgotten", "retirement", "benefits", "life_mode", "bereavement",
           "will_check", "categorise", "save_rules")


def _saved_rules(tenant: str, ws: str) -> dict[str, str]:
    from ..profile import ProfileError, get
    try:
        return dict((get(tenant, ws).get("settings") or {}).get("category_rules") or {})
    except ProfileError:
        return {}


def save_rules(tenant: str, ws: str, rules: dict[str, str]) -> dict[str, Any]:
    """Her own words -> category, kept on the workspace (they win over Hoola's list)."""
    import json
    from ... import db
    from ..models import FinWorkspace, ensure
    bad = [c for c in rules.values() if c not in OUT_ORDER + ["income"]]
    if bad:
        raise SafetyError("category: " + ", ".join(OUT_ORDER + ["income"]))
    ensure()
    with db.session() as s:
        w = s.get(FinWorkspace, ws)
        if not w or w.tenant_id != tenant:
            raise SafetyError("No such workspace.")
        st = json.loads(w.settings or "{}")
        st.setdefault("category_rules", {}).update({str(k).lower()[:60]: v for k, v in rules.items()})
        w.settings = json.dumps(st)
        s.commit()
        return {"workspace": ws, "rules": st["category_rules"]}
NEEDS_COUNTRY = ("forgotten", "retirement", "benefits", "life_mode", "bereavement", "will_check")


def run(tenant: str, action: str, a: dict[str, Any]) -> dict[str, Any]:
    a = dict(a)
    a["_tenant"] = tenant
    rules = {str(k): str(v) for k, v in (a.get("rules") or {}).items()}
    if action == "save_rules":
        if not a.get("workspace"):
            raise SafetyError("save_rules needs a workspace.")
        return save_rules(tenant, str(a["workspace"]), rules)
    if a.get("workspace"):
        rules = {**_saved_rules(tenant, str(a["workspace"])), **rules}
    if action in ("budget", "bills", "forecast", "categorise"):
        rows = _rows(tenant, a)
        cur = _cur(rows, a)
        if action == "budget":
            out = budget(rows, cur, a.get("limits"), rules)
        elif action == "bills":
            out = recurring(rows, cur, rules)
        elif action == "forecast":
            out = forecast(rows, cur, int(a.get("months_ahead") or 3), a.get("start_balance"), rules)
        else:
            out = {"currency": cur, "rows": [{"day": r["day"], "narration": r["narration"][:80], "amount": _units(r["amount_minor"], cur),
                                              "category": r["category"]} for r in categorise(rows, rules)[-500:]]}
    elif action == "goal":
        out = goal(a)
    elif action == "net_worth":
        out = net_worth(a)
    elif action in NEEDS_COUNTRY:
        cc = _cc(a)
        if action == "forgotten":
            out = forgotten(a, cc, None)
        elif action == "retirement":
            out = retirement(a, cc)
        elif action == "benefits":
            out = benefits(cc)
        elif action == "life_mode":
            out = life_mode(a.get("mode"), cc)
        elif action == "bereavement":
            out = bereavement(a, cc)
        else:
            out = will_check(a, cc)
    else:
        raise SafetyError("action: " + ", ".join(ACTIONS))
    out.setdefault("not_advice", L.NOT_ADVICE)
    return out


__all__ = ["run", "ACTIONS", "category", "recurring", "forecast", "budget", "NOT_CONFIRMED"]
