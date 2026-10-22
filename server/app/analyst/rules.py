"""Finance rules and benchmarks Hoola checks against (researched 22 Oct 2026; sources in CLAUDE.md v0.95). Pure functions.

Benchmarks are the common Indian bank / analyst yardsticks, not law: current ratio 1.33 (Tandon II), DSCR 1.25 minimum
(1.5+ comfortable), TOL / TNW up to 3, working capital limit for MSMEs up to Rs 5 crore = 20% of projected turnover
(Nayak: need 25%, owner brings 5%). Law: Income-tax Act 2025 Sec 37(2)(g) (old 43B(h)) - a payment to a micro / small
supplier later than 15 days (45 with a written agreement) is not deductible until paid; MSMED Act Sec 16 interest =
3x the RBI bank rate, compounded monthly (bank rate 5.75% from 7 Oct 2026 -> 17.25%). Advance tax 15 / 45 / 75 / 100%
by 15 Jun / 15 Sep / 15 Dec / 15 Mar when the year's tax is Rs 10,000 or more.
"""
from __future__ import annotations

import math
import re
from datetime import date

BANK_RATE = 5.75                 # % (RBI bank rate = MSF, from 7 Oct 2026; repo 5.50%)
MSME_INTEREST = 3 * BANK_RATE    # % a year, compounded monthly (MSMED Act Sec 16)
MSME_DAYS_NO_AGREEMENT = 15
MSME_DAYS_MAX = 45

BENCH = {
    "current_ratio": (1.33, "min", "Current ratio (current assets / current liabilities)"),
    "quick_ratio": (1.0, "min", "Quick ratio (without stock)"),
    "dscr": (1.25, "min", "DSCR (cash for debt / interest + instalments)"),
    "tol_tnw": (3.0, "max", "TOL / TNW (outside liabilities / own funds)"),
    "debt_equity": (2.0, "max", "Debt / equity"),
    "gross_margin": (None, "info", "Gross margin %"),
    "net_margin": (None, "info", "Net margin %"),
    "debtor_days": (60, "max", "Receivable days"),
    "creditor_days": (None, "info", "Payable days"),
    "stock_days": (None, "info", "Stock days"),
    "interest_cover": (2.0, "min", "Interest cover (EBIT / interest)"),
}

# Tally's standard groups -> where they sit in the statements
GROUPS = {
    "sales accounts": "revenue", "sales": "revenue", "direct incomes": "other_income_direct", "indirect incomes": "other_income",
    "income (direct)": "other_income_direct", "income (indirect)": "other_income",
    "purchase accounts": "purchases", "purchases": "purchases", "direct expenses": "direct_exp", "expenses (direct)": "direct_exp",
    "indirect expenses": "indirect_exp", "expenses (indirect)": "indirect_exp", "opening stock": "opening_stock",
    "closing stock": "closing_stock", "stock-in-hand": "closing_stock", "stock in hand": "closing_stock",
    "sundry debtors": "debtors", "cash-in-hand": "cash", "cash in hand": "cash", "bank accounts": "bank",
    "deposits (asset)": "other_ca", "loans & advances (asset)": "other_ca", "loans and advances (asset)": "other_ca",
    "current assets": "other_ca", "fixed assets": "fixed_assets", "investments": "investments", "misc. expenses (asset)": "other_ca",
    "sundry creditors": "creditors", "duties & taxes": "duties", "duties and taxes": "duties", "provisions": "provisions",
    "current liabilities": "other_cl", "bank od a/c": "bank_od", "bank od accounts": "bank_od", "bank occ a/c": "bank_od",
    "secured loans": "secured_loans", "unsecured loans": "unsecured_loans", "loans (liability)": "secured_loans",
    "capital account": "capital", "reserves & surplus": "reserves", "reserves and surplus": "reserves",
    "suspense a/c": "suspense", "branch / divisions": "other_cl", "profit & loss a/c": "reserves",
}
# ledger words when there is no group column
LEDGER_WORDS = [
    (("sales", "sale a/c", "revenue", "turnover", "service income", "fees received"), "revenue"),
    (("purchase",), "purchases"), (("opening stock",), "opening_stock"), (("closing stock", "stock in hand"), "closing_stock"),
    (("freight inward", "carriage inward", "wages", "factory", "power & fuel", "job work"), "direct_exp"),
    (("depreciation",), "depreciation"), (("interest on loan", "interest on od", "interest on cc", "bank interest paid", "finance cost"), "interest"),
    (("salary", "salaries", "rent", "electricity", "telephone", "internet", "office", "printing", "travel", "conveyance",
      "repairs", "advertis", "marketing", "professional", "audit fee", "bank charges", "insurance", "staff welfare", "commission paid",
      "legal", "software", "postage", "courier", "misc", "general expenses", "fuel"), "indirect_exp"),
    (("interest received", "discount received", "commission received", "other income", "rent received"), "other_income"),
    (("debtor", "receivable"), "debtors"), (("creditor", "payable"), "creditors"), (("cash",), "cash"),
    (("bank", "hdfc", "icici", "sbi", "axis", "kotak", "current a/c", "savings a/c"), "bank"),
    (("gst", "cgst", "sgst", "igst", "tds payable", "tds", "pt payable", "pf payable", "esi payable"), "duties"),
    (("od", "cc a/c", "overdraft", "cash credit"), "bank_od"), (("term loan", "vehicle loan", "car loan", "machinery loan"), "secured_loans"),
    (("loan from", "unsecured"), "unsecured_loans"), (("capital",), "capital"), (("reserve", "surplus", "profit & loss"), "reserves"),
    (("machinery", "furniture", "computer", "vehicle", "building", "land", "plant"), "fixed_assets"),
    (("advance", "deposit", "prepaid"), "other_ca"), (("provision", "outstanding", "expenses payable"), "provisions"),
]


def classify(name: str, group: str = "") -> str:
    g = re.sub(r"\s+", " ", str(group or "").strip().lower())
    if g in GROUPS:
        return GROUPS[g]
    n = " " + re.sub(r"\s+", " ", str(name or "").strip().lower()) + " "
    if n.strip() in GROUPS:
        return GROUPS[n.strip()]
    if "depreciation" in n:
        return "depreciation"
    for words, cat in LEDGER_WORDS:
        if any((" " + w) in n or n.strip().startswith(w) for w in words):
            return cat
    return "unknown"


# bank narration -> spend / income category (her own rules are learned on top)
BANK_WORDS = [
    (("salary", "sal ", "payroll", "wages"), "salary"), (("rent",), "rent"), (("gst", "cbic", "gstn", "cpin"), "gst"),
    (("tds", "itns", "oltas", "income tax", "advance tax", "tin-nsdl", "incometax"), "income_tax"),
    (("epfo", "epf", "provident", "esic"), "pf_esi"), (("emi", "loan", "ln ", "nach", "ach d", "ecs"), "loan_emi"),
    (("electricity", "msedcl", "bescom", "tata power", "adani elec", "torrent power", "power"), "utilities"),
    (("airtel", "jio", "vodafone", "bsnl", "broadband", "act fibernet"), "utilities"),
    (("petrol", "diesel", "fuel", "hpcl", "iocl", "bpcl", "indian oil"), "fuel"),
    (("amazon", "flipkart", "swiggy", "zomato"), "misc"), (("atm", "cash wdl", "cash withdrawal", "self"), "cash_withdrawal"),
    (("interest", "int.pd", "int pd", "int.cr"), "interest"), (("charges", "chrg", "fee", "commission"), "bank_charges"),
    (("insurance", "lic", "premium"), "insurance"), (("refund", "reversal"), "refund"),
]


def bank_category(narration: str, credit: bool) -> str:
    n = " " + re.sub(r"\s+", " ", str(narration or "").lower()) + " "
    for words, cat in BANK_WORDS:
        if any(w in n for w in words):
            if cat == "interest":
                return "interest_income" if credit else "interest_paid"
            return cat
    return "sales_receipt" if credit else "supplier_payment"


# ---------------------------------------------------------------- statements from mapped balances
def statements(b: dict[str, float]) -> dict:
    """b: category -> amount (positive). Returns P&L, balance sheet and ratios."""
    g = lambda k: float(b.get(k, 0.0) or 0.0)  # noqa: E731
    revenue = g("revenue")
    cogs = g("opening_stock") + g("purchases") + g("direct_exp") - g("closing_stock")
    gross = revenue + g("other_income_direct") - cogs
    opex = g("indirect_exp")
    ebitda = gross - opex
    ebit = ebitda - g("depreciation")
    interest = g("interest")
    pbt = ebit - interest + g("other_income")
    ca = g("debtors") + g("cash") + g("bank") + g("closing_stock") + g("other_ca")
    cl = g("creditors") + g("duties") + g("provisions") + g("other_cl") + g("bank_od")
    tnw = g("capital") + g("reserves") + (pbt if g("reserves") == 0 else 0.0)
    debt = g("secured_loans") + g("unsecured_loans") + g("bank_od")
    tol = cl + g("secured_loans") + g("unsecured_loans")
    pl = {"revenue": round(revenue), "cogs": round(cogs), "gross_profit": round(gross), "opex": round(opex), "ebitda": round(ebitda),
          "depreciation": round(g("depreciation")), "interest": round(interest), "other_income": round(g("other_income")),
          "profit_before_tax": round(pbt)}
    bs = {"current_assets": round(ca), "current_liabilities": round(cl), "debtors": round(g("debtors")), "stock": round(g("closing_stock")),
          "cash_bank": round(g("cash") + g("bank")), "creditors": round(g("creditors")), "fixed_assets": round(g("fixed_assets")),
          "loans": round(debt), "own_funds": round(tnw)}
    return {"pl": pl, "bs": bs, "raw": {k: round(v) for k, v in b.items()}}


def ratios(st: dict, days: int = 365, debt_service: float = 0.0) -> dict:
    pl, bs = st["pl"], st["bs"]
    rev = pl["revenue"] or 0
    cogs = pl["cogs"] or 0
    purchases = st["raw"].get("purchases", 0)
    out: dict[str, float | None] = {}
    div = lambda a, b: (round(a / b, 2) if b else None)  # noqa: E731
    out["gross_margin"] = div(pl["gross_profit"] * 100, rev)
    out["net_margin"] = div(pl["profit_before_tax"] * 100, rev)
    out["current_ratio"] = div(bs["current_assets"], bs["current_liabilities"])
    out["quick_ratio"] = div(bs["current_assets"] - bs["stock"], bs["current_liabilities"])
    tol = bs["current_liabilities"] + max(0, bs["loans"] - st["raw"].get("bank_od", 0))
    out["tol_tnw"] = div(tol, bs["own_funds"]) if bs["own_funds"] > 0 else None
    out["debt_equity"] = div(bs["loans"], bs["own_funds"]) if bs["own_funds"] > 0 else None
    out["debtor_days"] = div(bs["debtors"] * days, rev)
    out["creditor_days"] = div(bs["creditors"] * days, purchases or cogs)
    out["stock_days"] = div(bs["stock"] * days, cogs)
    out["interest_cover"] = div(pl["ebitda"] - pl["depreciation"], pl["interest"])
    cash_for_debt = pl["profit_before_tax"] + pl["depreciation"] + pl["interest"]
    out["dscr"] = div(cash_for_debt, pl["interest"] + debt_service) if (pl["interest"] + debt_service) else None
    return out


def judge(r: dict) -> list[dict]:
    """Each ratio with its benchmark and a plain verdict."""
    rows = []
    for k, v in r.items():
        bench, how, label = BENCH.get(k, (None, "info", k))
        verdict = "info"
        if v is not None and bench is not None:
            verdict = "good" if (v >= bench if how == "min" else v <= bench) else "weak"
        rows.append({"key": k, "label": label, "value": v, "benchmark": bench, "rule": how, "verdict": verdict})
    return rows


# ---------------------------------------------------------------- money tools
def emi(principal: float, annual_rate: float, months: int) -> float:
    r = annual_rate / 12 / 100
    if months <= 0:
        return 0.0
    if r == 0:
        return round(principal / months, 2)
    return round(principal * r * (1 + r) ** months / ((1 + r) ** months - 1), 2)


def nayak_limit(projected_turnover: float) -> dict:
    """MSME working capital up to Rs 5 crore: need 25% of turnover, owner margin 5%, bank finance 20%."""
    need = projected_turnover * 0.25
    return {"need": round(need), "owner_margin": round(projected_turnover * 0.05), "bank_limit": round(min(projected_turnover * 0.20, 5e7)),
            "applies": projected_turnover * 0.20 <= 5e7}


def break_even(fixed_costs: float, contribution_margin_pct: float) -> float | None:
    if contribution_margin_pct <= 0:
        return None
    return round(fixed_costs / (contribution_margin_pct / 100))


def msme_interest(amount: float, days: int, rate: float = MSME_INTEREST) -> float:
    """Compound interest with monthly rests at 3x bank rate."""
    if days <= 0:
        return 0.0
    months, rem = divmod(days, 30)
    bal = amount * (1 + rate / 100 / 12) ** months
    bal *= 1 + rate / 100 * rem / 365
    return round(bal - amount, 0)


def msme_limit(agreed_days: int | None) -> int:
    if agreed_days and agreed_days > 0:
        return min(int(agreed_days), MSME_DAYS_MAX)
    return MSME_DAYS_NO_AGREEMENT


# ---------------------------------------------------------------- advance tax
def tax_estimate(profit: float, entity: str = "individual") -> dict:
    p = max(0.0, float(profit))
    if entity == "company":                       # new regime (old 115BAA): 22% + 10% surcharge + 4% cess
        t = p * 0.22 * 1.10 * 1.04
    elif entity in ("firm", "llp"):               # 30% + 12% surcharge above Rs 1 crore + 4% cess
        t = p * 0.30 * (1.12 if p > 1e7 else 1.0) * 1.04
    else:                                         # individual / proprietor: new regime slabs (no standard deduction on business)
        from ..payroll.rules import annual_tax
        t = annual_tax(p, "new")["total"]          # business income: no salary standard deduction
    return {"profit": round(p), "tax": round(t)}


def advance_tax_plan(year_tax: float, fy_start: int, paid: float = 0.0, on: date | None = None) -> dict:
    """15 / 45 / 75 / 100% by 15 Jun / 15 Sep / 15 Dec / 15 Mar. Under Rs 10,000 a year: none needed."""
    sched = [(date(fy_start, 6, 15), 0.15), (date(fy_start, 9, 15), 0.45), (date(fy_start, 12, 15), 0.75), (date(fy_start + 1, 3, 15), 1.0)]
    if year_tax < 10000:
        return {"needed": False, "installments": [], "note": "Saal ka tax Rs 10,000 se kam: advance tax nahi."}
    rows = []
    for d, pct in sched:
        due = round(year_tax * pct)
        rows.append({"due": d.isoformat(), "cumulative_pct": int(pct * 100), "cumulative": due,
                     "short": max(0, due - round(paid)) if on and on > d else None})
    nxt = next((r for r in rows if on is None or date.fromisoformat(r["due"]) >= on), None)
    pay_now = max(0, nxt["cumulative"] - round(paid)) if nxt else 0
    return {"needed": True, "installments": rows, "next": nxt, "pay_by_next": pay_now,
            "note": "Kam bharne par 1% mahina byaaj (purane 234B / 234C jaisa)."}


def fy_start_of(d: date) -> int:
    return d.year if d.month >= 4 else d.year - 1


def runway_months(cash: float, monthly_net_out: float) -> float | None:
    if monthly_net_out <= 0:
        return None
    return round(cash / monthly_net_out, 1)


def aging_bucket(days: int) -> str:
    return "0-30" if days <= 30 else "31-60" if days <= 60 else "61-90" if days <= 90 else "90+"


def months_between(a: date, b: date) -> int:
    return max(1, (b.year - a.year) * 12 + b.month - a.month + 1)


def pct_change(new: float, old: float) -> float | None:
    if not old:
        return None
    return round((new - old) * 100 / abs(old), 1)


def clean_amount(v) -> float:
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    neg = s.startswith("(") and s.endswith(")")
    s2 = re.sub(r"[^\d.\-]", "", s.replace(",", ""))
    try:
        x = float(s2) if s2 not in ("", "-", ".") else 0.0
    except ValueError:
        x = 0.0
    return -abs(x) if neg else x


def isfinite(x) -> bool:
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False
