"""F11 of docs/FINANCE_GLOBAL_PLAN.md - Community & Inclusive Finance (employee 17; tool `community_finance`), any country.

  cashbook     a micro-business cash book from entries or from spoken / typed lines ("sold tea 250", "paid rent 2000"): money in, money
               out, the balance day by day; lines it could not read are listed, never guessed.
  group        a savings group's books (VSLA, SHG, susu, caja de ahorro, any): savings, loans out, repayments (interest first), fines,
               the social fund and expenses meeting by meeting; the cash the group COUNTED against the book; who owes what; the share-out
               at the end of the cycle in proportion to each member's savings, to the last cent. A meeting cannot lend money the box does
               not hold.
  rosca        a rotating group (chit, tanda, paluwagan, esusu, hui): the payout order; for an auction chit the bid, the organiser's fee
               at HER rate, the dividend each member gets and the true cost of taking the pot early; the safety signs.
  mfi          a borrower's coach: the true cost of a microloan (fees and installments -> the yearly rate), her repayments against her
               income, more lenders than is safe.
  field        an MFI field officer's collection sheet: collected, arrears, portfolio at risk over 30 days.
  farmer       a crop plan (costs, yield, price -> margin and the break-even price) and a crop-insurance claim worked out from the
               threshold and actual yields in HER scheme's terms.
  remit        sending money home: each provider's fee and rate against the mid-market rate -> what arrives and the true cost.
  mobile_money a transfer's fee from HER provider's tariff, and the signs of a mobile-money scam in a message.
  zakat        zakat on her wealth: cash, gold and silver by weight and purity, trade stock, receivables, shares, less debts due;
               the nisab on gold or silver at HER prices; 2.5% when a lunar year has passed. School differences (jewellery, shares,
               debts) are her choice and named; the ruling for her case stays with her scholar.
  islamic      Islamic business structures worked out: murabaha, ijara, diminishing musharaka, mudaraba - schedules and splits. Whether a
               structure is compliant is for her Shariah board, never Hoola.
  styles       the group traditions Hoola knows by country.

Hoola never collects, lends or sends money. Not financial or religious advice."""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .. import laws as L


class CommunityError(ValueError):
    pass


ZERO = Decimal(0)
NOT_CONFIRMED = " (from memory - not confirmed, check this)"
NEVER = "Hoola never collects, lends or sends money: you (or your group's treasurer) do."
BOARD = "Whether this is Shariah compliant is decided by your Shariah board or scholar, not by Hoola."

STYLES = {
    "KE": "VSLA / chama (shares bought each meeting, a share-out at the end of the cycle)",
    "UG": "VSLA (shares bought each meeting, a share-out at the end of the cycle)",
    "TZ": "VICOBA / VSLA", "NG": "esusu / ajo (rotating) and cooperative savings", "GH": "susu (daily collector or rotating)",
    "IN": "SHG - self-help group (monthly savings, internal loans, bank linkage); chit funds (auction, registered)",
    "BD": "samity / SHG", "PK": "committee / BC (rotating)", "MX": "tanda (rotating) and caja de ahorro (savings)",
    "PH": "paluwagan (rotating)", "ET": "iqub (rotating) and idir (burial fund)", "SN": "tontine", "HT": "sol (rotating)",
    "CN": "hui (rotating)", "KR": "gye (rotating)", "EG": "gam'eya (rotating)",
}


def _n(v: Any, what: str, lo: float | None = None) -> Decimal:
    try:
        x = Decimal(str(v).replace(",", "").strip())
    except Exception:
        raise CommunityError(f"{what}: a number.")
    if not x.is_finite():
        raise CommunityError(f"{what}: a number.")
    if lo is not None and x < Decimal(str(lo)):
        raise CommunityError(f"{what}: not below {lo}.")
    return x


def money(x: Decimal) -> float:
    return float(Decimal(x).quantize(Decimal("0.01"), ROUND_HALF_UP))


def _cents(x: Decimal) -> int:
    return int((Decimal(x) * 100).quantize(Decimal(1), ROUND_HALF_UP))


def _irr(flows: list[Decimal]) -> float | None:
    """The rate per period that makes the flows worth nothing today (bisection; None when there is no sign change)."""
    f = [float(x) for x in flows]
    if not (any(x > 0 for x in f) and any(x < 0 for x in f)):
        return None

    def npv(r):
        return sum(x / (1 + r) ** k for k, x in enumerate(f))
    lo, hi = -0.99, 10.0
    if npv(lo) * npv(hi) > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


# ---- cash book ---------------------------------------------------------------------------------------------------------------

_IN = re.compile(r"\b(sold|sale|sales|received|got|earned|income|collected|deposit|customer paid|bikri|mila|aaya|kamai)\b", re.I)
_OUT = re.compile(r"\b(bought|paid|spent|rent|fee|fees|bill|salary|wages|transport|purchase|stock|kharcha|diya|gaya)\b", re.I)
_AMT = re.compile(r"(\d[\d,]*(?:\.\d{1,2})?)")


def cashbook(a: dict[str, Any]) -> dict[str, Any]:
    rows, unread = [], []
    for i, e in enumerate(a.get("entries") or []):
        kind = str(e.get("kind") or "").lower()
        if kind not in ("in", "out"):
            raise CommunityError(f"entries[{i}].kind: in | out.")
        rows.append({"date": str(e.get("date") or ""), "kind": kind, "amount": _n(e.get("amount"), f"entries[{i}].amount", 0),
                     "note": str(e.get("note") or "")})
    day = str(a.get("date") or "")
    for line in str(a.get("text") or "").splitlines():
        t = line.strip()
        if not t:
            continue
        m = re.match(r"(\d{4}-\d{2}-\d{2})\s*[:,-]?\s*(.*)", t)
        if m:
            day, t = m.group(1), m.group(2)
            if not t:
                continue
        nums = _AMT.findall(t)
        i, o = bool(_IN.search(t)), bool(_OUT.search(t))
        if len(nums) != 1 or i == o:
            unread.append(line.strip())
            continue
        rows.append({"date": day, "kind": "in" if i else "out", "amount": _n(nums[0], "amount"), "note": t})
    opening = _n(a.get("opening") or 0, "opening")
    bal, days = opening, {}
    for r in sorted(rows, key=lambda r: r["date"]):
        bal += r["amount"] if r["kind"] == "in" else -r["amount"]
        d = days.setdefault(r["date"] or "-", {"in": ZERO, "out": ZERO})
        d[r["kind"]] += r["amount"]
        d["balance"] = bal
    tin = sum((r["amount"] for r in rows if r["kind"] == "in"), ZERO)
    tout = sum((r["amount"] for r in rows if r["kind"] == "out"), ZERO)
    return {"entries": [{**r, "amount": money(r["amount"])} for r in rows], "money_in": money(tin), "money_out": money(tout),
            "opening": money(opening), "closing": money(opening + tin - tout),
            "by_day": [{"date": k, "in": money(v["in"]), "out": money(v["out"]), "balance": money(v["balance"])} for k, v in sorted(days.items())],
            "could_not_read": unread, "says": "Lines it could not read are listed, not guessed: say them again with one amount."}


# ---- savings group -----------------------------------------------------------------------------------------------------------

def group(a: dict[str, Any]) -> dict[str, Any]:
    members = [str(m) for m in a.get("members") or []]
    if not members:
        raise CommunityError("members: the names of the group's members.")
    share = _n(a["share_value"], "share_value", 0) if a.get("share_value") is not None else None
    cash = _n(a.get("opening_cash") or 0, "opening_cash", 0)
    social = _n(a.get("opening_social") or 0, "opening_social", 0)
    saved = {m: ZERO for m in members}
    owed_p = defaultdict(lambda: ZERO)      # principal outstanding per member
    owed_i = defaultdict(lambda: ZERO)      # interest due per member
    tot = defaultdict(lambda: ZERO)
    mismatches, log = [], []
    for k, mt in enumerate(a.get("meetings") or []):
        when = str(mt.get("date") or f"meeting {k + 1}")

        def who(m, part):
            if m not in saved:
                raise CommunityError(f"{when}: {part} for {m}, who is not a member.")
            return m
        for m, v in (mt.get("savings") or {}).items():
            amt = _n(v, f"{when}.savings.{m}", 0) * (share if share is not None else 1)
            saved[who(m, "savings")] += amt
            cash += amt
            tot["savings"] += amt
        for m, v in (mt.get("fines") or {}).items():
            amt = _n(v, f"{when}.fines.{m}", 0)
            who(m, "a fine")
            cash += amt
            tot["fines"] += amt
        for m, v in (mt.get("social_fund") or {}).items():
            who(m, "social fund")
            social += _n(v, f"{when}.social_fund.{m}", 0)
        for p in mt.get("social_payouts") or []:
            amt = _n(p.get("amount"), f"{when}.social_payouts.amount", 0)
            if amt > social:
                raise CommunityError(f"{when}: the social fund holds {money(social)}, it cannot pay {money(amt)}.")
            social -= amt
        for r in mt.get("repayments") or []:
            m = who(str(r.get("member")), "a repayment")
            amt = _n(r.get("amount"), f"{when}.repayments.amount", 0)
            if amt > owed_p[m] + owed_i[m] + Decimal("0.001"):
                raise CommunityError(f"{when}: {m} repays {money(amt)} but owes {money(owed_p[m] + owed_i[m])}.")
            to_i = min(amt, owed_i[m])
            owed_i[m] -= to_i
            owed_p[m] -= amt - to_i
            tot["interest"] += to_i
            tot["principal_back"] += amt - to_i
            cash += amt
        for e in mt.get("expenses") or []:
            amt = _n(e.get("amount"), f"{when}.expenses.amount", 0)
            cash -= amt
            tot["expenses"] += amt
        for ln in mt.get("loans") or []:
            m = who(str(ln.get("member")), "a loan")
            amt = _n(ln.get("amount"), f"{when}.loans.amount", 0)
            if amt > cash:
                raise CommunityError(f"{when}: the box holds {money(cash)}, it cannot lend {money(amt)} to {m}.")
            rate = _n(ln.get("rate_pct"), f"{when}.loans.rate_pct (the group's own rate per month)", 0)
            months = _n(ln.get("months") or 1, f"{when}.loans.months", 0)
            owed_p[m] += amt
            owed_i[m] += amt * rate / 100 * months
            cash -= amt
            tot["lent"] += amt
        if cash < 0:
            raise CommunityError(f"{when}: the box would go below zero ({money(cash)}).")
        if mt.get("counted") is not None:
            c = _n(mt["counted"], f"{when}.counted")
            if abs(c - cash) >= Decimal("0.005"):
                mismatches.append({"meeting": when, "book": money(cash), "counted": money(c), "difference": money(c - cash)})
        log.append({"meeting": when, "cash": money(cash), "social_fund": money(social)})
    opening = _n(a.get("opening_cash") or 0, "opening_cash", 0)
    outstanding = sum(owed_p.values(), ZERO)
    left = cash + outstanding - (opening + tot["savings"] + tot["interest"] + tot["fines"] - tot["expenses"])
    out = {"cash_box": money(cash), "social_fund": money(social), "loans_outstanding": money(outstanding),
           "interest_due": money(sum(owed_i.values(), ZERO)), "savings": {m: money(v) for m, v in saved.items()},
           "totals": {k: money(v) for k, v in tot.items()}, "meetings": log, "count_mismatches": mismatches,
           "balanced": abs(left) < Decimal("0.005"),
           "owes": {m: money(owed_p[m] + owed_i[m]) for m in members if owed_p[m] + owed_i[m] > 0}}
    if a.get("share_out"):
        if out["owes"]:
            out["share_out"] = {"possible": False, "says": "Loans are still out: the share-out waits until they are repaid.",
                                "owes": out["owes"]}
        else:
            total_saved = sum(saved.values(), ZERO)
            pot = _cents(cash)
            if total_saved <= 0:
                raise CommunityError("share_out: nobody has saved.")
            exact = {m: Decimal(pot) * saved[m] / total_saved for m in members}
            base = {m: int(exact[m]) for m in members}
            rest = pot - sum(base.values())
            for m in sorted(members, key=lambda m: (-(exact[m] - base[m]), members.index(m)))[:rest]:
                base[m] += 1
            out["share_out"] = {"possible": True, "pot": money(cash), "per_member": {m: base[m] / 100 for m in members},
                                "profit": money(cash - total_saved),
                                "return_on_savings_pct": money((cash - total_saved) / total_saved * 100)}
    country = str(a.get("country") or "").upper()
    if country:
        out["style"] = STYLES.get(country, "a savings group") + NOT_CONFIRMED
    return out


def rosca(a: dict[str, Any]) -> dict[str, Any]:
    members = [str(m) for m in a.get("members") or []]
    if len(members) < 2:
        raise CommunityError("members: the members, in the order they take the pot.")
    c = _n(a.get("contribution"), "contribution", 0)
    n = len(members)
    pot = c * n
    bids = a.get("bids")
    flags = []
    for k, msg in (("written_record", "nothing is written down"), ("organiser_known", "the organiser is not known to the members"),
                   ("registered", "an auction chit that is not registered where the law asks for it")):
        if a.get(k) is False:
            flags.append(msg)
    if a.get("promised_return_pct"):
        flags.append("a promised return on top of the pot: a rotating group pays out only what members put in")
    if bids is None:
        sched = [{"round": k + 1, "takes_the_pot": m, "pot": money(pot)} for k, m in enumerate(members)]
        early = _irr([pot - c] + [-c] * (n - 1))
        return {"schedule": sched, "each_pays": money(pot), "each_receives": money(pot), "flags": flags,
                "first_taker_pays_per_round_pct": round(-early * 100, 3) if early is not None else 0.0,
                "says": "In a plain rotating group no one gains or loses money; the first takes an interest-free loan, the last saves."}
    fee_pct = _n(a.get("organiser_fee_pct"), "organiser_fee_pct (the organiser's fee, per the agreement)", 0)
    if len(bids) != n:
        raise CommunityError("bids: one winning bid (discount) per round, as many as members.")
    paid = {m: ZERO for m in members}
    got = {m: ZERO for m in members}
    flows = {m: [] for m in members}
    rounds = []
    for k, (m, b) in enumerate(zip(members, bids)):
        bid = _n(b, f"bids[{k}]", 0)
        fee = pot * fee_pct / 100
        if bid < fee:
            raise CommunityError(f"bids[{k}]: below the organiser's fee.")
        div = (bid - fee) / n
        for x in members:
            paid[x] += c - div
            flows[x].append(-(c - div))
        got[m] += pot - bid
        flows[m][-1] += pot - bid
        rounds.append({"round": k + 1, "takes_the_pot": m, "bid": money(bid), "organiser_fee": money(fee), "dividend_each": money(div),
                       "taker_receives": money(pot - bid), "each_pays_net": money(c - div)})
    per = {}
    for m in members:
        r = _irr(flows[m])
        first = flows[m][0] > 0
        per[m] = {"paid": money(paid[m]), "received": money(got[m]), "gain": money(got[m] - paid[m]),
                  "role": "borrows (took the pot early)" if first else "saves",
                  "rate_per_round_pct": round(r * 100, 3) if r is not None else None}
    return {"rounds": rounds, "members": per, "organiser_fees": money(pot * fee_pct / 100 * n), "flags": flags,
            "says": "For a member who borrows, the rate per round is the cost of taking the pot early; for one who saves, it is what the "
                    "bids earned. No single rate is shown when the money goes in and out more than once. " + NEVER}


# ---- microfinance, farming, remittance ---------------------------------------------------------------------------------------

PERIODS = {"weekly": 52, "fortnightly": 26, "monthly": 12}


def mfi(a: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if a.get("amount") is not None:
        amt = _n(a["amount"], "amount", 0)
        inst = _n(a.get("installment"), "installment", 0)
        k = int(_n(a.get("installments"), "installments", 1))
        freq = str(a.get("frequency") or "weekly").lower()
        if freq not in PERIODS:
            raise CommunityError("frequency: weekly | fortnightly | monthly.")
        fees = _n(a.get("upfront_fees") or 0, "upfront_fees", 0)
        r = _irr([amt - fees] + [-inst] * k)
        if r is None:
            raise CommunityError("the installments do not repay more than you receive.")
        p = PERIODS[freq]
        out["loan"] = {"you_receive": money(amt - fees), "you_repay": money(inst * k), "cost": money(inst * k - amt + fees),
                       "rate_per_period_pct": round(r * 100, 4), "yearly_rate_pct": round(r * p * 100, 2),
                       "effective_yearly_pct": round(((1 + r) ** p - 1) * 100, 2)}
    loans = a.get("loans") or []
    if loans:
        monthly = ZERO
        for i, ln in enumerate(loans):
            f = str(ln.get("frequency") or "monthly").lower()
            monthly += _n(ln.get("installment"), f"loans[{i}].installment", 0) * PERIODS.get(f, 12) / 12
        inc = _n(a["income_monthly"], "income_monthly", 0) if a.get("income_monthly") is not None else None
        lim = _n(a.get("max_share_pct") or 50, "max_share_pct", 0)
        out["repayments"] = {"lenders": len({str(ln.get("lender")) for ln in loans}), "per_month": money(monthly),
                             "share_of_income_pct": money(monthly / inc * 100) if inc else None,
                             "over_your_limit": bool(inc and monthly / inc * 100 > lim), "limit_pct": float(lim)}
        if len({str(ln.get("lender")) for ln in loans}) > 2:
            out["repayments"]["flag"] = "more than two lenders: many regulators treat this as a sign of over-borrowing" + NOT_CONFIRMED
    if not out:
        raise CommunityError("amount + installment + installments (a loan's true cost) or loans + income_monthly.")
    return out


def field(a: dict[str, Any]) -> dict[str, Any]:
    due = col = ZERO
    arrears = []
    for i, m in enumerate(a.get("collections") or []):
        d, p = _n(m.get("due"), f"collections[{i}].due", 0), _n(m.get("paid") or 0, f"collections[{i}].paid", 0)
        due, col = due + d, col + p
        if p < d:
            arrears.append({"member": m.get("member"), "short": money(d - p)})
    port = risk = ZERO
    for i, ln in enumerate(a.get("portfolio") or []):
        o = _n(ln.get("outstanding"), f"portfolio[{i}].outstanding", 0)
        port += o
        if int(_n(ln.get("days_late") or 0, "days_late", 0)) > 30:
            risk += o
    return {"due": money(due), "collected": money(col), "collection_rate_pct": money(col / due * 100) if due else None,
            "arrears": arrears, "par30_pct": money(risk / port * 100) if port else None, "portfolio": money(port)}


def farmer(a: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if a.get("area") is not None and a.get("yield_per_unit") is not None:
        area = _n(a["area"], "area", 0)
        cost = sum((_n(c.get("amount"), "costs.amount", 0) for c in a.get("costs") or []), ZERO)
        y = _n(a["yield_per_unit"], "yield_per_unit", 0) * area
        price = _n(a.get("price"), "price (yours, per unit of yield)", 0)
        out["plan"] = {"cost": money(cost), "harvest": float(y), "income": money(y * price), "margin": money(y * price - cost),
                       "break_even_price": money(cost / y) if y else None, "cost_per_area": money(cost / area) if area else None}
    if a.get("threshold_yield") is not None:
        th = _n(a["threshold_yield"], "threshold_yield", 0)
        act = _n(a.get("actual_yield"), "actual_yield", 0)
        si = _n(a.get("sum_insured"), "sum_insured (for the insured area, from the policy)", 0)
        short = max(th - act, ZERO)
        out["claim"] = {"shortfall_pct": money(short / th * 100) if th else 0.0, "claim": money(short / th * si) if th else 0.0,
                        "formula": "(threshold yield - actual yield) / threshold yield x sum insured - check your scheme's terms" + NOT_CONFIRMED,
                        "keep": ["the sowing proof", "the policy or enrolment receipt", "the crop-cutting result or loss intimation",
                                 "photos with dates", "the bank account the claim is paid to"]}
    if not out:
        raise CommunityError("area + yield_per_unit + price + costs (a crop plan) or threshold_yield + actual_yield + sum_insured (a claim).")
    return out


def remit(a: dict[str, Any]) -> dict[str, Any]:
    send = _n(a.get("send"), "send", 0)
    mid = _n(a.get("mid_rate"), "mid_rate (the mid-market rate today)", 0)
    out = []
    for i, p in enumerate(a.get("providers") or []):
        fee = _n(p.get("fee") or 0, f"providers[{i}].fee", 0) + send * _n(p.get("fee_pct") or 0, "fee_pct", 0) / 100
        rate = _n(p.get("rate"), f"providers[{i}].rate", 0)
        arrives = (send - fee) * rate if p.get("fee_from_amount", True) else send * rate
        ideal = send * mid
        out.append({"provider": p.get("name") or f"#{i}", "fee": money(fee), "rate": float(rate), "arrives": money(arrives),
                    "true_cost_pct": money((ideal - arrives) / ideal * 100) if ideal else None})
    if not out:
        raise CommunityError("providers: [{name, fee, fee_pct, rate}] as each one quotes today.")
    out.sort(key=lambda x: -x["arrives"])
    return {"providers": out, "most_arrives_with": out[0]["provider"],
            "says": "The true cost is the fee plus what the exchange rate takes compared with the mid-market rate."}


_MM_SCAM = [(r"\b(sent|sent you).{0,20}by mistake\b", "a 'sent by mistake, please send it back' request"),
            (r"\b(pin|otp|code)\b", "asks for a PIN or a code: no provider ever does"),
            (r"\b(won|winner|prize|lottery|promotion)\b", "a prize you must pay to receive"),
            (r"\b(agent|customer care).{0,30}(call|dial)\b", "an 'agent' asking you to call or dial a code"),
            (r"\b(reverse|reversal)\b", "a reversal request: ask your provider, never the sender")]


def mobile_money(a: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if a.get("amount") is not None:
        amt = _n(a["amount"], "amount", 0)
        fee = None
        for t in a.get("tariff") or []:
            if _n(t.get("min"), "tariff.min", 0) <= amt <= _n(t.get("max"), "tariff.max", 0):
                fee = _n(t.get("fee"), "tariff.fee", 0)
                break
        if fee is None:
            raise CommunityError("tariff: your provider's bands [{min, max, fee}] covering this amount.")
        out["fee"] = {"amount": money(amt), "fee": money(fee), "fee_pct": money(fee / amt * 100) if amt else 0.0}
    if a.get("message"):
        out["scam_signs"] = [why for rx, why in _MM_SCAM if re.search(rx, str(a["message"]), re.I)]
    if not out:
        raise CommunityError("amount + tariff, or message.")
    return out


# ---- zakat and Islamic structures --------------------------------------------------------------------------------------------

NISAB_GRAMS = {"gold": Decimal(85), "silver": Decimal(595)}
JEWELLERY_ZAKATABLE = {"hanafi": True, "shafii": False, "maliki": False, "hanbali": False}


def zakat(a: dict[str, Any]) -> dict[str, Any]:
    basis = str(a.get("nisab_basis") or "").lower()
    if basis not in NISAB_GRAMS:
        raise CommunityError("nisab_basis: gold | silver (yours, from your scholar).")
    gp = _n(a.get("gold_price_per_gram"), "gold_price_per_gram (24 carat, today, yours)", 0)
    sp = _n(a.get("silver_price_per_gram"), "silver_price_per_gram (today, yours)", 0) if basis == "silver" or a.get("silver_grams") else ZERO
    school = str(a.get("school") or "").lower()
    jw = a.get("jewellery_zakatable")
    if jw is None:
        jw = JEWELLERY_ZAKATABLE.get(school)
    lines = []

    def add(what, v):
        if v:
            lines.append({"what": what, "value": v})

    add("cash", _n(a.get("cash") or 0, "cash", 0))
    add("bank", _n(a.get("bank") or 0, "bank", 0))
    for i, g in enumerate(a.get("gold") or []):
        grams = _n(g.get("grams"), f"gold[{i}].grams", 0)
        k = _n(g.get("karat") or 24, f"gold[{i}].karat", 0)
        is_j = bool(g.get("jewellery"))
        if is_j and jw is None:
            raise CommunityError("gold jewellery: say your school (hanafi | shafii | maliki | hanbali) or jewellery_zakatable true | false.")
        if is_j and not jw:
            continue
        add(f"gold {grams} g {k}k" + (" (jewellery)" if is_j else ""), grams * k / 24 * gp)
    if a.get("silver_grams"):
        add("silver", _n(a["silver_grams"], "silver_grams", 0) * sp)
    add("trade stock (at sale value)", _n(a.get("business_stock") or 0, "business_stock", 0))
    add("money owed to you that you expect back", _n(a.get("receivables") or 0, "receivables", 0))
    add("shares held to trade (market value)", _n(a.get("shares_trading") or 0, "shares_trading", 0))
    if a.get("shares_longterm"):
        v = _n(a["shares_longterm"], "shares_longterm", 0)
        pct = _n(a.get("shares_longterm_pct") or 100, "shares_longterm_pct (the part your scholar counts)", 0)
        add(f"long-term shares ({float(pct)}% counted)", v * pct / 100)
    gross = sum((x["value"] for x in lines), ZERO)
    debts = _n(a.get("debts_due") or 0, "debts_due (payable now)", 0)
    net = gross - debts
    nisab = NISAB_GRAMS[basis] * (gp if basis == "gold" else sp)
    year = a.get("lunar_year_passed")
    due = net >= nisab and nisab > 0 and year is not False
    out = {"assets": [{"what": x["what"], "value": money(x["value"])} for x in lines], "gross": money(gross), "debts_due": money(debts),
           "net": money(net), "nisab": money(nisab), "nisab_from": f"{int(NISAB_GRAMS[basis])} g of {basis}" + NOT_CONFIRMED,
           "above_nisab": bool(net >= nisab), "zakat": money(net * Decimal("0.025")) if due else 0.0,
           "jewellery": ("counted" if jw else "not counted") + (f" ({school} view, as you chose)" if school else ""),
           "says": "This is the arithmetic of the usual method; the ruling for your case stays with your scholar."}
    if year is None:
        out["note"] = "lunar_year_passed: say whether a lunar year has passed since your wealth first reached the nisab."
    return out


def islamic(a: dict[str, Any]) -> dict[str, Any]:
    kind = str(a.get("structure") or "").lower()
    if kind == "murabaha":
        cost = _n(a.get("cost"), "cost", 0)
        mk = _n(a.get("markup_pct"), "markup_pct (agreed, fixed)", 0)
        k = int(_n(a.get("installments") or 1, "installments", 1))
        price = cost * (1 + mk / 100)
        inst = price / k
        out = {"sale_price": money(price), "profit": money(price - cost), "installment": money(inst),
               "late_payment": "no extra charge as income: any late-payment amount agreed goes to charity (as the contract says)",
               "order": "the seller owns the goods before selling them on"}
    elif kind == "ijara":
        cost = _n(a.get("cost"), "cost", 0)
        rent = _n(a.get("rent"), "rent (per period)", 0)
        k = int(_n(a.get("periods"), "periods", 1))
        out = {"total_rent": money(rent * k), "over_cost": money(rent * k - cost),
               "order": "the lessor owns the asset and bears the owner's risks; rent starts when the asset is delivered"}
    elif kind == "diminishing_musharaka":
        price = _n(a.get("price"), "price", 0)
        mine = _n(a.get("own_contribution"), "own_contribution", 0)
        rent_pct = _n(a.get("rent_pct_per_period"), "rent_pct_per_period (on the financier's share)", 0)
        buy = _n(a.get("buyback_per_period"), "buyback_per_period", 0)
        theirs = price - mine
        rows, k = [], 0
        while theirs > Decimal("0.004") and k < 1200:
            k += 1
            rent = theirs * rent_pct / 100
            b = min(buy, theirs)
            theirs -= b
            rows.append({"period": k, "rent": money(rent), "buyback": money(b), "financier_share_left": money(theirs),
                         "your_share_pct": money((price - theirs) / price * 100)})
        out = {"schedule": rows, "periods": k, "total_rent": money(sum((Decimal(str(r["rent"])) for r in rows), ZERO)),
               "order": "rent is paid only on the part the financier still owns"}
    elif kind == "mudaraba":
        profit = _n(a.get("profit"), "profit (or a loss as a negative number)")
        ratio = _n(a.get("manager_share_pct"), "manager_share_pct (the agreed share of profit)", 0)
        if profit >= 0:
            out = {"manager": money(profit * ratio / 100), "capital_provider": money(profit * (100 - ratio) / 100)}
        else:
            out = {"manager": 0.0, "capital_provider": money(profit),
                   "says": "a loss falls on the capital provider; the manager loses the work, unless the loss came from the manager's "
                           "negligence or breach"}
    else:
        raise CommunityError("structure: murabaha | ijara | diminishing_musharaka | mudaraba.")
    out.update({"structure": kind, "board": BOARD})
    return out


ACTIONS = ("cashbook", "group", "rosca", "mfi", "field", "farmer", "remit", "mobile_money", "zakat", "islamic", "styles")
_MONEYISH = re.compile(r"(collect_money|disburse|lend_now|send|transfer|pay|withdraw|deposit_now|issue_fatwa|certify|rule_on)")


def run(tenant: str, action: str, a: dict[str, Any], actor: str = "owner") -> dict[str, Any]:
    a = dict(a)
    if _MONEYISH.search(str(action).lower()):
        raise L.Refused("move_money", NEVER + " " + BOARD)
    if action == "styles":
        out = {"styles": STYLES, "from": "Hoola's list" + NOT_CONFIRMED}
    elif action in ACTIONS:
        out = globals()[action](a)
    else:
        raise CommunityError("action: " + ", ".join(ACTIONS))
    out.setdefault("not_advice", L.NOT_ADVICE)
    return out
