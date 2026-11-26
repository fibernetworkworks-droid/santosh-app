"""CREDIT & LENDING DESK - the Credit & Lending employee's own section, like Payroll, Tax and Cash & Treasury (owner: "NOW LETS WORK ON
NEXT EMPLOYEE CREDIT AND LENDING").

- The Credit chat = a Conversation with kind 'credit', kept out of every Hoola chat list (callconv.not_call); facts she tells it still
  reach her one memory. A turn in it (or a voice call started from it) gets the desk's state as a block and the credit tool
  (`credit_lending`, family lending) in view.
- The desk's pages run the F6 engine (fin/desks/credit.py) on the business she picked (a finance workspace, the same businesses as Books
  & Accounts). Her team works here too: owner / accountant / approver change things, auditor and viewer read.
- Both sides of a loan:
    borrow   her own loans and offers: the APR by her country's method, offers side by side, invoice finance, the readiness pack from
             her own statements and books.
    lend     applications (figures each with their source, the borrower's statement rows, her policy rules, a credit memo, a key-facts
             draft, the conditions checklist) and the loan book (what was due against what was paid, days past due, collections contacts
             checked against her contact rules, early-warning signals, the ECL working paper).
- What the desk adds to the engine, kept in the workspace settings under `credit_desk`: loans, applications, offers, her memo policy
  limits, her underwriting rules and her APR method. Contact rules and the contact log stay where the engine keeps them.
- Hoola works the figures out. It gives no score, approves or declines nothing, pays out nothing and never sends a collections contact:
  the decision is the named person's.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select

from .db import Conversation, Message, session

log = logging.getLogger("santosh.creditchat")

KIND = "credit"
KEY = "credit_lending"         # the Hub employee
TOOL = "credit_lending"        # its tool
FAMILIES = ["lending"]
_OF: dict[str, bool] = {}
_BLOCK: dict[str, tuple[float, str]] = {}
BLOCK_TTL = 60.0
FOOT = ("Hoola works out the loan figures. It gives no score, approves or declines nothing, pays out nothing and sends no collections "
        "contact - the decision is the named person's. Not credit advice.")
WRITE = {"owner", "accountant", "approver"}
ROLE_SAY = {"owner": "Owner", "accountant": "Accountant", "approver": "Approver", "auditor": "Auditor", "viewer": "Viewer"}
SIDES = ("lent", "borrowed")
MAX_LOANS, MAX_APPS, MAX_OFFERS, MAX_ROWS = 300, 100, 12, 2000
FIG_SUGGEST = ["revenue", "ebitda", "net_profit", "interest", "debt_service", "total_debt", "net_worth", "current_assets",
               "current_liabilities", "income_monthly", "obligations_monthly"]


class CreditDeskError(ValueError):
    pass


def is_credit(conv: str) -> bool:
    if not conv:
        return False
    if conv in _OF:
        return _OF[conv]
    hit = False
    try:
        with session() as s:
            c = s.get(Conversation, conv)
            if c is not None:
                if (c.kind or "") == KIND:
                    hit = True
                elif (c.kind or "") == "call" and c.origin_conv:
                    o = s.get(Conversation, c.origin_conv)
                    hit = bool(o is not None and (o.kind or "") == KIND)
    except Exception:   # noqa: BLE001
        log.exception("credit chat kind read failed")
        return False
    _OF[conv] = hit
    return hit


def _hire():
    from .employee import hire
    return hire


def businesses(tenant: str) -> list[dict[str, Any]]:
    from .bookschat import businesses as B
    return B(tenant)


def workspace(tenant: str, want: str = "") -> dict[str, Any] | None:
    bs = businesses(tenant)
    if not want:
        try:
            want = str(_hire().settings(tenant, KEY).get("workspace") or "")
        except Exception:   # noqa: BLE001
            want = ""
    for b in bs:
        if b["id"] == want:
            return b
    return bs[0] if bs else None


def pick(tenant: str, ws: str) -> dict[str, Any]:
    if not any(b["id"] == ws for b in businesses(tenant)):
        raise CreditDeskError("No such business.")
    try:
        _hire().save_settings(tenant, KEY, workspace=ws)
    except Exception:   # noqa: BLE001
        pass
    forget(tenant)
    return {"workspace": ws}


# ---------------------------------------------------------------- desk state (kept in the workspace settings)
def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def _today() -> date:
    return date.today()


def _wsrow(owner: str, ws: str) -> dict[str, Any]:
    from .fin import profile as PR
    return PR.get(owner, ws)


def _state(owner: str, ws: str) -> dict[str, Any]:
    st = dict((_wsrow(owner, ws).get("settings") or {}).get("credit_desk") or {})
    for k, v in (("loans", []), ("apps", []), ("offers", []), ("policy", {}), ("uw_rules", []), ("apr", {})):
        st.setdefault(k, v)
    return st


def _engine_cfg(owner: str, ws: str) -> dict[str, Any]:
    return dict((_wsrow(owner, ws).get("settings") or {}).get("credit") or {})


def _put(owner: str, ws: str, st: dict[str, Any]) -> None:
    from . import db
    from .fin.models import FinWorkspace, ensure
    ensure()
    with db.session() as s:
        row = s.get(FinWorkspace, ws)
        if not row or row.tenant_id != owner:
            raise CreditDeskError("No such business.")
        cur = json.loads(row.settings or "{}")
        cur["credit_desk"] = st
        row.settings = json.dumps(cur)
        s.commit()


def _num(v: Any, what: str, lo: float | None = None) -> float:
    try:
        x = float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        raise CreditDeskError(f"{what}: a number.")
    if lo is not None and x < lo:
        raise CreditDeskError(f"{what}: not below {lo:g}.")
    return x


def _day(v: Any, what: str) -> str:
    try:
        return date.fromisoformat(str(v)[:10]).isoformat()
    except ValueError:
        raise CreditDeskError(f"{what}: a date as YYYY-MM-DD.")


def _text(v: Any, n: int = 80) -> str:
    return str(v or "").strip()[:n]


def _next_n(rows: list[dict[str, Any]]) -> int:
    return 1 + max([int(x.get("n") or 0) for x in rows] or [0])


def _find(rows: list[dict[str, Any]], n: Any, what: str) -> dict[str, Any]:
    for x in rows:
        if int(x.get("n") or 0) == int(_num(n, "n")):
            return x
    raise CreditDeskError(f"No such {what}.")


def _engine(owner: str, me: str, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from .fin import core
    from .fin.desks import credit as C
    return core.run_tool(owner, me, TOOL, action, dict(a), lambda: C.run(owner, action, a, me))


def _err(fn):
    """Run an engine call; its CreditError becomes the desk's error."""
    from .fin.desks import credit as C
    try:
        return fn()
    except C.CreditError as e:
        raise CreditDeskError(str(e))


# ---------------------------------------------------------------- the APR method (her country's, or the one she chose)
def method_args(owner: str, ws: str) -> dict[str, Any]:
    from .fin.desks import credit as C
    st = _state(owner, ws)
    if (st["apr"] or {}).get("method"):
        return {"method": st["apr"]["method"]}
    for cc in _wsrow(owner, ws).get("countries") or []:
        if str(cc).upper() in C.COUNTRY_METHOD:
            return {"country": str(cc).upper()}
    return {}


def method_view(owner: str, ws: str) -> dict[str, Any]:
    from .fin.desks import credit as C
    a = method_args(owner, ws)
    if a.get("method"):
        m, why = a["method"], "the method you chose in Settings"
    elif a.get("country"):
        m, why = C.COUNTRY_METHOD[a["country"]], f"{a['country']}'s usual method from memory - check this against your regulator's rule"
    else:
        m, why = "", "no method yet: your country is not on Hoola's list - choose one in Settings"
    return {"method": m, "method_is": C.METHODS.get(m, ""), "from": why, "checked": bool(a.get("method")),
            "methods": C.METHODS, "countries": dict(C.COUNTRY_METHOD)}


def _needs_method(owner: str, ws: str) -> dict[str, Any]:
    a = method_args(owner, ws)
    if not a:
        raise CreditDeskError("Choose an APR method in Settings - your country is not on Hoola's list of usual methods.")
    return a


# ---------------------------------------------------------------- borrow side
def apr_calc(owner: str, ws: str, me: str, a: dict[str, Any]) -> dict[str, Any]:
    keep = {k: a[k] for k in ("amount", "rate", "term", "payment", "frequency", "fee_pct", "fees_upfront", "balloon", "fees_deducted")
            if k in a and a[k] not in (None, "")}
    return _err(lambda: _engine(owner, me, "apr", {**keep, **_needs_method(owner, ws)}))


def _offer_row(a: dict[str, Any]) -> dict[str, Any]:
    name = _text(a.get("name"), 60)
    if not name:
        raise CreditDeskError("name: who is offering it.")
    row: dict[str, Any] = {"name": name, "amount": _num(a.get("amount"), "amount", 0.01), "term": int(_num(a.get("term"), "term", 1))}
    for k in ("rate", "fee_pct", "fees_upfront", "payment"):
        if a.get(k) not in (None, ""):
            row[k] = _num(a[k], k, 0)
    if "rate" not in row and "payment" not in row:
        raise CreditDeskError("rate (annual %) or the payment the lender quoted.")
    fr = str(a.get("frequency") or "monthly")
    from .fin.desks import credit as C
    if fr not in C.PPY:
        raise CreditDeskError("frequency: " + " | ".join(C.PPY))
    row["frequency"] = fr
    return row


def add_offer(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    if len(st["offers"]) >= MAX_OFFERS:
        raise CreditDeskError(f"Up to {MAX_OFFERS} offers side by side - remove one first.")
    row = {"n": _next_n(st["offers"]), **_offer_row(a), "by": me, "on": _now()}
    _err(lambda: _engine(owner, me, "apr", {**{k: row[k] for k in row if k not in ("n", "by", "on", "name")}, **_needs_method(owner, ws)}))
    st["offers"].append(row)
    _put(owner, ws, st)
    return {"offer": row}


def remove_offer(owner: str, ws: str, n: Any) -> dict[str, Any]:
    st = _state(owner, ws)
    row = _find(st["offers"], n, "offer")
    st["offers"].remove(row)
    _put(owner, ws, st)
    return {"offers": st["offers"]}


def compare(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    if not st["offers"]:
        return {"offers": [], "says": "Add the offers you have to see them side by side."}
    if not method_args(owner, ws):
        return {"offers": [], "error": "Choose an APR method in Settings first."}
    offers = [{k: v for k, v in o.items() if k not in ("n", "by", "on")} for o in st["offers"]]
    r = _err(lambda: _engine(owner, me, "shop", {"offers": offers, **method_args(owner, ws)}))
    by = {o["name"]: o for o in st["offers"]}
    for row in r["offers"]:
        o = by.get(row["name"]) or {}
        row["n"], row["amount"], row["term"], row["frequency"] = o.get("n"), o.get("amount"), o.get("term"), o.get("frequency")
        row["rate"] = o.get("rate")
    return r


def invoice_fin(owner: str, ws: str, me: str, a: dict[str, Any]) -> dict[str, Any]:
    keep = {k: a[k] for k in ("invoice", "advance_pct", "fee", "fee_pct", "days", "discount_rate_pct") if a.get(k) not in (None, "")}
    return _err(lambda: _engine(owner, me, "invoice_finance", keep))


def readiness(owner: str, ws: str, me: str, a: dict[str, Any]) -> dict[str, Any]:
    keep = {k: a[k] for k in ("since", "upto", "opening") if a.get(k) not in (None, "")}
    try:
        return _err(lambda: _engine(owner, me, "readiness", {"workspace": ws, **keep}))
    except CreditDeskError as e:
        if "No statement rows" in str(e):
            raise CreditDeskError("No bank statements for this business yet - import one in Books & Accounts > Bank, or drop one in the "
                                  "chat. Then Hoola can show what a lender will see.")
        raise


# ---------------------------------------------------------------- the loan book
def _loan_row(a: dict[str, Any], old: dict[str, Any] | None = None) -> dict[str, Any]:
    o = dict(old or {})
    name = _text(a.get("name", o.get("name")), 80)
    if not name:
        raise CreditDeskError("name: the borrower (or, for your own loan, the lender).")
    side = str(a.get("side") or o.get("side") or "lent")
    if side not in SIDES:
        raise CreditDeskError("side: lent (you lent it) | borrowed (you owe it).")
    row = {**o, "name": name, "side": side, "amount": _num(a.get("amount", o.get("amount")), "amount", 0.01),
           "term": int(_num(a.get("term", o.get("term")), "term (number of monthly payments)", 1)),
           "start": _day(a.get("start", o.get("start")), "start (first payment due)")}
    rate = a.get("rate", o.get("rate"))
    pay = a.get("payment", o.get("payment"))
    row["rate"] = _num(rate, "rate", 0) if rate not in (None, "") else 0.0
    row["payment"] = _num(pay, "payment", 0.01) if pay not in (None, "") else None
    if not row["rate"] and not row["payment"]:
        raise CreditDeskError("rate (annual %) or the monthly payment.")
    if row["term"] > 600:
        raise CreditDeskError("term: up to 600 monthly payments.")
    tz = _text(a.get("tz", o.get("tz")), 60)
    if tz:
        from zoneinfo import ZoneInfo
        try:
            ZoneInfo(tz)
        except Exception:   # noqa: BLE001
            raise CreditDeskError("tz: a time zone like Europe/London or Asia/Kolkata.")
    row["tz"] = tz
    for k in ("pd", "lgd", "pd_lifetime"):
        v = a.get(k, o.get(k))
        if v in (None, ""):
            row.pop(k, None)
            continue
        x = _num(v, k, 0)
        if x > 1:
            raise CreditDeskError(f"{k}: between 0 and 1 (for example 0.02).")
        row[k] = x
    row.setdefault("paid", [])
    return row


def add_loan(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    if len(st["loans"]) >= MAX_LOANS:
        raise CreditDeskError(f"Up to {MAX_LOANS} loans on this desk.")
    row = {"n": _next_n(st["loans"]), **_loan_row(a), "by": me, "on": _now()}
    _servicing(row, _today())
    st["loans"].append(row)
    _put(owner, ws, st)
    return {"loan": loan_view(row, _today())}


def edit_loan(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    old = _find(st["loans"], a.get("n"), "loan")
    row = _loan_row(a, old)
    _servicing(row, _today())
    old.clear()
    old.update({**row, "changed_by": me, "changed_on": _now()})
    _put(owner, ws, st)
    return {"loan": loan_view(old, _today())}


def remove_loan(owner: str, ws: str, n: Any) -> dict[str, Any]:
    st = _state(owner, ws)
    row = _find(st["loans"], n, "loan")
    st["loans"].remove(row)
    _put(owner, ws, st)
    return {"loans": len(st["loans"])}


def add_payment(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    """A payment that HAS happened (she saw it in the bank), recorded against the schedule. Nothing is paid here."""
    st = _state(owner, ws)
    loan = _find(st["loans"], a.get("n"), "loan")
    d = _day(a.get("date") or _today().isoformat(), "date")
    if d > _today().isoformat():
        raise CreditDeskError("date: a payment that has happened - not a future one.")
    amt = _num(a.get("amount"), "amount", 0.01)
    loan["paid"] = sorted(loan.get("paid", []) + [{"date": d, "amount": amt, "by": me, "on": _now()}], key=lambda x: x["date"])[-1000:]
    _put(owner, ws, st)
    return {"loan": loan_view(loan, _today())}


def remove_payment(owner: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    st = _state(owner, ws)
    loan = _find(st["loans"], a.get("n"), "loan")
    k = int(_num(a.get("i"), "i", 0))
    if k >= len(loan.get("paid", [])):
        raise CreditDeskError("No such payment.")
    loan["paid"].pop(k)
    _put(owner, ws, st)
    return {"loan": loan_view(loan, _today())}


def _servicing(loan: dict[str, Any], today: date) -> dict[str, Any]:
    from .fin.desks import credit as C
    a = {"amount": loan["amount"], "term": loan["term"], "start": loan["start"], "today": today.isoformat(),
         "paid": [{"date": p["date"], "amount": p["amount"]} for p in loan.get("paid", [])]}
    if loan.get("payment"):
        a["payment"] = loan["payment"]
    else:
        a["rate"] = loan.get("rate") or 0
    try:
        return C.servicing(a)
    except C.CreditError as e:
        raise CreditDeskError(str(e))


def _balance(loan: dict[str, Any], pay: float, paid: float) -> float:
    """The principal still owed after the payments that were made (each counted against a whole instalment, in order)."""
    n = int(loan["term"])
    k = min(n, int(Decimal(str(paid)) // Decimal(str(pay)))) if pay else 0
    i = (loan.get("rate") or 0) / 1200
    amt = float(loan["amount"])
    if i == 0:
        return round(max(0.0, amt - pay * k), 2)
    g = (1 + i) ** k
    return round(max(0.0, amt * g - pay * (g - 1) / i), 2)


def _month_ends(today: date, n: int) -> list[date]:
    out, d = [], today.replace(day=1)
    for _ in range(n):
        d = d - timedelta(days=1)
        out.append(d)
        d = d.replace(day=1)
    return list(reversed(out))


def loan_view(loan: dict[str, Any], today: date) -> dict[str, Any]:
    sv = _servicing(loan, today)
    hist = []
    for d in _month_ends(today, 3):
        if d.isoformat() >= loan["start"]:
            hist.append(_servicing(loan, d)["days_past_due"])
    hist.append(sv["days_past_due"])
    dpd = sv["days_past_due"]
    bucket = "current" if dpd == 0 else "1-30" if dpd <= 30 else "31-60" if dpd <= 60 else "61-90" if dpd <= 90 else "90+"
    out = {k: loan.get(k) for k in ("n", "name", "side", "amount", "rate", "term", "start", "tz", "pd", "lgd", "pd_lifetime", "by", "on")}
    out.update(sv)
    out["paid"] = loan.get("paid", [])
    out["outstanding"] = _balance(loan, sv["payment"], sv["paid_so_far"])
    out["dpd_history"] = hist
    out["bucket"] = bucket
    out["rising"] = len(hist) >= 2 and hist[-1] > hist[-2]
    return out


def book(owner: str, ws: str) -> dict[str, Any]:
    st = _state(owner, ws)
    t = _today()
    views = [loan_view(x, t) for x in st["loans"]]
    lent = [v for v in views if v["side"] == "lent"]
    mine = [v for v in views if v["side"] == "borrowed"]
    buckets = {b: {"count": 0, "outstanding": 0.0} for b in ("current", "1-30", "31-60", "61-90", "90+")}
    for v in lent:
        buckets[v["bucket"]]["count"] += 1
        buckets[v["bucket"]]["outstanding"] = round(buckets[v["bucket"]]["outstanding"] + v["outstanding"], 2)
    arrears = [v for v in lent if v["arrears"] > 0]
    soon = (t + timedelta(days=7)).isoformat()
    return {"loans": views,
            "lent": {"count": len(lent), "outstanding": round(sum(v["outstanding"] for v in lent), 2),
                     "in_arrears": len(arrears), "arrears": round(sum(v["arrears"] for v in arrears), 2),
                     "worst_dpd": max([v["days_past_due"] for v in lent] or [0]), "buckets": buckets},
            "borrowed": {"count": len(mine), "outstanding": round(sum(v["outstanding"] for v in mine), 2),
                         "monthly": round(sum(v["payment"] for v in mine if v["instalments_left"] > 0), 2),
                         "due_soon": [{"n": v["n"], "name": v["name"], "next_due": v["next_due"], "payment": v["payment"]}
                                      for v in mine if v["next_due"] and v["next_due"] <= soon],
                         "missed": [{"n": v["n"], "name": v["name"], "arrears": v["arrears"], "days_past_due": v["days_past_due"]}
                                    for v in mine if v["arrears"] > 0]}}


def loan_book_csv(b: dict[str, Any], cur: str) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Loan book", _today().isoformat(), cur])
    w.writerow(["#", "Name", "Side", "Amount", "Rate %", "Term", "First due", "Payment", "Due so far", "Paid so far", "Arrears",
                "Days past due", "Next due", "Principal still owed", "Instalments left"])
    for v in b["loans"]:
        w.writerow([v["n"], v["name"], v["side"], v["amount"], v["rate"], v["term"], v["start"], v["payment"], v["due_so_far"],
                    v["paid_so_far"], v["arrears"], v["days_past_due"], v["next_due"] or "", v["outstanding"], v["instalments_left"]])
    w.writerow([])
    w.writerow([FOOT])
    return buf.getvalue().encode("utf-8")


# ---------------------------------------------------------------- risk: early warning + ECL
def risk(owner: str, ws: str, me: str) -> dict[str, Any]:
    b = book(owner, ws)
    lent = [v for v in b["loans"] if v["side"] == "lent"]
    ews = []
    for v in lent:
        r = _err(lambda v=v: _engine(owner, me, "ews", {"dpd_history": v["dpd_history"]}))
        if v["arrears"] > 0 and not any(s["signal"] == "days past due rising" for s in r["signals"]):
            r["signals"].append({"signal": "in arrears", "detail": f"{v['arrears']:,.2f} owed, {v['days_past_due']} days past due"})
        if r["signals"]:
            ews.append({"n": v["n"], "name": v["name"], "signals": r["signals"]})
    ready = [v for v in lent if v.get("pd") is not None and v.get("lgd") is not None]
    out: dict[str, Any] = {"ews": ews, "needs_pd_lgd": [{"n": v["n"], "name": v["name"]} for v in lent if v not in ready], "ecl": None}
    if ready:
        ex = [{"id": f"{v['n']} {v['name']}", "ead": v["outstanding"] + v["arrears"], "pd": v["pd"], "lgd": v["lgd"],
               "dpd": v["days_past_due"], **({"pd_lifetime": v["pd_lifetime"]} if v.get("pd_lifetime") is not None else {})} for v in ready]
        out["ecl"] = _err(lambda: _engine(owner, me, "ecl", {"exposures": ex}))
    out["says"] = "Signals to look at, not a classification. The provision is the risk committee's figure; this is a working paper."
    return out


# ---------------------------------------------------------------- applications (lend side)
def _parse_rows(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for k, ln in enumerate(csv.reader(io.StringIO(str(text or "")))):
        if not ln or not "".join(ln).strip():
            continue
        if len(ln) < 3:
            raise CreditDeskError(f"Line {k + 1}: date, narration, amount.")
        d, amt = ln[0].strip(), ln[-1].strip()
        if k == 0 and not d[:4].isdigit():
            continue        # a header line
        rows.append({"date": _day(d, f"line {k + 1} date"), "narration": ",".join(ln[1:-1]).strip()[:200],
                     "amount": _num(amt, f"line {k + 1} amount")})
        if len(rows) > MAX_ROWS:
            raise CreditDeskError(f"Up to {MAX_ROWS} statement rows.")
    return rows


def add_app(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    if len([x for x in st["apps"] if x.get("status") != "closed"]) >= MAX_APPS:
        raise CreditDeskError(f"Up to {MAX_APPS} open applications.")
    who = _text(a.get("borrower"), 80)
    if not who:
        raise CreditDeskError("borrower: who is asking.")
    row = {"n": _next_n(st["apps"]), "borrower": who, "amount": _num(a.get("amount"), "amount", 0.01), "purpose": _text(a.get("purpose"), 160),
           "rate": _num(a["rate"], "rate", 0) if a.get("rate") not in (None, "") else None,
           "term": int(_num(a["term"], "term", 1)) if a.get("term") not in (None, "") else None,
           "fee_pct": _num(a["fee_pct"], "fee_pct", 0) if a.get("fee_pct") not in (None, "") else 0.0,
           "figures": {}, "applicant": {}, "rows": [], "conditions": [], "status": "open", "by": me, "on": _now()}
    st["apps"].append(row)
    _put(owner, ws, st)
    return {"app": row}


def edit_app(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    row = _find(st["apps"], a.get("n"), "application")
    for k in ("borrower", "purpose"):
        if k in a:
            row[k] = _text(a[k], 160) or row[k]
    if a.get("amount") not in (None, ""):
        row["amount"] = _num(a["amount"], "amount", 0.01)
    for k in ("rate", "fee_pct"):
        if k in a:
            row[k] = _num(a[k], k, 0) if a[k] not in (None, "") else (0.0 if k == "fee_pct" else None)
    if "term" in a:
        row["term"] = int(_num(a["term"], "term", 1)) if a["term"] not in (None, "") else None
    if "rows_csv" in a:
        row["rows"] = _parse_rows(a["rows_csv"])
    row["changed_by"], row["changed_on"] = me, _now()
    _put(owner, ws, st)
    return {"app": app_view(owner, ws, row, me)}


def set_app_figure(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    row = _find(st["apps"], a.get("n"), "application")
    name = _text(a.get("name"), 40).lower().replace(" ", "_")
    if not name:
        raise CreditDeskError("name: the figure (revenue, ebitda, net_worth ...).")
    if a.get("value") in (None, ""):
        row["figures"].pop(name, None)
    else:
        src = _text(a.get("source"), 120)
        if not src:
            raise CreditDeskError("source: where the figure comes from (the borrower's document and page). A figure with no source is not used.")
        row["figures"][name] = {"value": _num(a["value"], "value"), "source": src, "by": me}
    _put(owner, ws, st)
    return {"app": app_view(owner, ws, row, me)}


def set_app_field(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    """An applicant detail her underwriting rules test (age, months_trading, bureau_score ... from the application form)."""
    from .riskdesk import credit as RC
    st = _state(owner, ws)
    row = _find(st["apps"], a.get("n"), "application")
    f = _text(a.get("field"), 40).lower().replace(" ", "_")
    if not f:
        raise CreditDeskError("field: what the detail is.")
    if f in RC.PROTECTED or any(p in f for p in RC.PROTECTED):
        raise CreditDeskError(f"'{f}' is a ground for discrimination (or a proxy for one) - it is not kept or tested.")
    if a.get("value") in (None, ""):
        row["applicant"].pop(f, None)
    else:
        v = str(a["value"]).strip()[:60]
        try:
            row["applicant"][f] = float(v)
        except ValueError:
            row["applicant"][f] = v
    _put(owner, ws, st)
    return {"app": app_view(owner, ws, row, me)}


def set_condition(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    row = _find(st["apps"], a.get("n"), "application")
    name = _text(a.get("name"), 120)
    if not name:
        raise CreditDeskError("name: the document or condition.")
    status = str(a.get("status") or "missing")
    if status not in ("received", "missing", "waived"):
        raise CreditDeskError("status: received | missing | waived.")
    if a.get("remove"):
        row["conditions"] = [c for c in row["conditions"] if c["name"] != name]
    else:
        item = {"name": name, "status": status}
        if status == "waived":
            wb = _text(a.get("waived_by"), 80)
            if not wb:
                raise CreditDeskError("waived_by: who waived it (their name).")
            item["waived_by"] = wb
        if a.get("due"):
            item["due"] = _day(a["due"], "due")
        item["by"], item["on"] = me, _now()
        row["conditions"] = [c for c in row["conditions"] if c["name"] != name] + [item]
    _put(owner, ws, st)
    return {"app": app_view(owner, ws, row, me)}


def close_app(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    """She records what the named decider decided - Hoola does not decide it."""
    st = _state(owner, ws)
    row = _find(st["apps"], a.get("n"), "application")
    who = _text(a.get("decided_by"), 80)
    what = _text(a.get("outcome"), 160)
    if not who or not what:
        raise CreditDeskError("decided_by (the credit officer or committee) and outcome (what they decided, in their words).")
    row.update({"status": "closed", "decided_by": who, "outcome": what, "closed_by": me, "closed_on": _now()})
    _put(owner, ws, st)
    return {"app": app_view(owner, ws, row, me)}


def reopen_app(owner: str, ws: str, n: Any) -> dict[str, Any]:
    st = _state(owner, ws)
    row = _find(st["apps"], n, "application")
    row["status"] = "open"
    for k in ("decided_by", "outcome", "closed_by", "closed_on"):
        row.pop(k, None)
    _put(owner, ws, st)
    return {"app": row}


def remove_app(owner: str, ws: str, n: Any) -> dict[str, Any]:
    st = _state(owner, ws)
    row = _find(st["apps"], n, "application")
    st["apps"].remove(row)
    _put(owner, ws, st)
    return {"apps": len(st["apps"])}


def _monthly_pay(app: dict[str, Any]) -> float | None:
    from .fin.desks import credit as C
    if app.get("rate") is None or not app.get("term"):
        return None
    return C.level_payment(float(app["amount"]), float(app["rate"]), int(app["term"]), 12)


def app_view(owner: str, ws: str, app: dict[str, Any], me: str, deep: bool = False) -> dict[str, Any]:
    """One application with what the engine makes of it. deep = the memo, the rule hits, the KFS and the statement analysis."""
    out = {k: v for k, v in app.items() if k != "rows"}
    out["rows_count"] = len(app.get("rows") or [])
    out["requested_emi"] = _monthly_pay(app)
    if app.get("conditions"):
        try:
            out["checklist"] = _engine(owner, me, "conditions", {"items": app["conditions"]})
        except Exception as e:   # noqa: BLE001
            out["checklist"] = {"error": str(e)}
    else:
        out["checklist"] = None
    if not deep:
        return out
    st = _state(owner, ws)
    figs = {k: {"value": v["value"], "source": v["source"]} for k, v in (app.get("figures") or {}).items()}
    if app.get("rows"):
        try:
            out["analysis"] = _engine(owner, me, "analyse", {"rows": app["rows"]})
        except Exception as e:   # noqa: BLE001
            out["analysis"] = {"error": str(e)}
    if figs or app.get("rows"):
        a = {"figures": figs, "borrower": app["borrower"], "amount": f"{app['amount']:,.2f}", "purpose": app.get("purpose") or "",
             "policy": st["policy"]}
        if app.get("rows"):
            a["rows"] = app["rows"]
        try:
            out["memo"] = _engine(owner, me, "memo", a)
        except Exception as e:   # noqa: BLE001
            out["memo"] = {"error": str(e)}
    else:
        out["memo"] = None
    if st["uw_rules"]:
        appl = {k: v["value"] for k, v in figs.items()}
        appl.update(app.get("applicant") or {})
        memo_figs = (out.get("memo") or {}).get("figures") or {}
        for k in ("income_monthly", "obligations_monthly"):
            if k not in appl and k in memo_figs:
                appl[k] = memo_figs[k]["value"]
        if out["requested_emi"]:
            appl["requested_emi"] = out["requested_emi"]
        appl["amount"] = app["amount"]
        try:
            out["rules"] = _engine(owner, me, "rules", {"applicant": appl, "rules": st["uw_rules"]})
        except Exception as e:   # noqa: BLE001
            out["rules"] = {"error": str(e)}
    else:
        out["rules"] = None
    if app.get("rate") is not None and app.get("term") and method_args(owner, ws):
        w = _wsrow(owner, ws)
        a = {"lender": w.get("name") or "", "borrower": app["borrower"], "product": app.get("purpose") or "loan", "amount": app["amount"],
             "rate": app["rate"], "term": app["term"], "fee_pct": app.get("fee_pct") or 0, **method_args(owner, ws)}
        try:
            out["kfs"] = _engine(owner, me, "kfs", a)
        except Exception as e:   # noqa: BLE001
            out["kfs"] = {"error": str(e)}
    else:
        out["kfs"] = None
    return out


def app_one(owner: str, ws: str, me: str, n: Any) -> dict[str, Any]:
    st = _state(owner, ws)
    return app_view(owner, ws, _find(st["apps"], n, "application"), me, deep=True)


def memo_pdf(app: dict[str, Any], business: str) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    y = H - 18 * mm

    def line(txt: str, size: float = 10, bold: bool = False):
        nonlocal y
        for part in [txt[i:i + 105] for i in range(0, max(1, len(txt)), 105)] or [""]:
            if y < 18 * mm:
                c.showPage()
                y = H - 18 * mm
            c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
            c.drawString(16 * mm, y, part)
            y -= size * 1.55

    line(business, 13, True)
    for ln in ((app.get("memo") or {}).get("memo_markdown") or "").splitlines():
        if ln.startswith("# "):
            line(ln[2:], 14, True)
        elif ln.startswith("## "):
            y -= 4
            line(ln[3:], 11, True)
        else:
            line(ln.replace("**", ""), 10)
    hits = (app.get("rules") or {}).get("rule_hits") or []
    if hits:
        y -= 4
        line("Your rules that are not met", 11, True)
        for h in hits:
            line(f"- {h['code']}: needs {h['required']}, is {h['actual']} ({h['severity']})", 10)
    y -= 6
    line(FOOT, 8)
    c.save()
    return buf.getvalue()


# ---------------------------------------------------------------- collections + settings
def contacts(owner: str, ws: str) -> dict[str, Any]:
    from .fin.desks import credit as C
    cfg = _engine_cfg(owner, ws)
    log_ = list(reversed(cfg.get("contacts") or []))[:200]
    mine = cfg.get("contact_rules") or {}
    return {"log": log_, "rules": mine, "effective": C._effective(mine), "floor": C.FLOOR}   # noqa: SLF001


def collect(owner: str, ws: str, me: str, a: dict[str, Any]) -> dict[str, Any]:
    keep = {k: a[k] for k in ("borrower", "tz", "when", "channel", "to", "message", "legal_stage") if a.get(k) not in (None, "")}
    if keep.get("borrower") and not keep.get("tz"):
        st = _state(owner, ws)
        hit = next((x for x in st["loans"] if x["name"].lower() == str(keep["borrower"]).lower() and x.get("tz")), None)
        if hit:
            keep["tz"] = hit["tz"]
    return _err(lambda: _engine(owner, me, "collect", {"workspace": ws, **keep}))


def save_contact_rules(owner: str, ws: str, me: str, a: dict[str, Any]) -> dict[str, Any]:
    r = {k: a[k] for k in ("from_hour", "to_hour", "per_day", "per_week", "no_days", "channels", "source") if a.get(k) not in (None, "", [])}
    if isinstance(r.get("no_days"), str):
        r["no_days"] = [x.strip() for x in r["no_days"].split(",") if x.strip()]
    return _err(lambda: _engine(owner, me, "contact_rules", {"workspace": ws, "contact_rules": r}))


def set_method(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    from .fin.desks import credit as C
    st = _state(owner, ws)
    m = str(a.get("method") or "")
    if m and m not in C.METHODS:
        raise CreditDeskError("method: " + " | ".join(C.METHODS))
    st["apr"] = {"method": m, "by": me, "on": _now(), "source": _text(a.get("source"), 160)} if m else {}
    _put(owner, ws, st)
    return method_view(owner, ws)


def set_policy(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    from .fin.desks import credit as C
    st = _state(owner, ws)
    k = str(a.get("ratio") or "")
    if k not in C._RATIOS:   # noqa: SLF001
        raise CreditDeskError("ratio: " + " | ".join(C._RATIOS))   # noqa: SLF001
    if a.get("limit") in (None, ""):
        st["policy"].pop(k, None)
    else:
        st["policy"][k] = _num(a["limit"], "limit")
    _put(owner, ws, st)
    return {"policy": st["policy"]}


def set_rule(owner: str, ws: str, a: dict[str, Any], me: str) -> dict[str, Any]:
    from .riskdesk import credit as RC
    st = _state(owner, ws)
    code = _text(a.get("code"), 40)
    if not code:
        raise CreditDeskError("code: the rule's name in your policy (MIN_AGE, MAX_FOIR ...).")
    if a.get("remove"):
        st["uw_rules"] = [r for r in st["uw_rules"] if r["code"] != code]
    else:
        f = _text(a.get("field"), 40).lower().replace(" ", "_")
        if not f:
            raise CreditDeskError("field: what the rule tests (age, foir_pct, months_trading ...).")
        if f in RC.PROTECTED or any(p in f for p in RC.PROTECTED):
            raise CreditDeskError(f"A rule cannot be built on '{f}': it is a ground for discrimination (or a proxy for one).")
        op = str(a.get("op") or "")
        if op not in RC._OPS:   # noqa: SLF001
            raise CreditDeskError("op: " + " ".join(RC._OPS))   # noqa: SLF001
        sev = str(a.get("severity") or "refer")
        if sev not in ("refer", "info", "stop"):
            raise CreditDeskError("severity: refer | stop | info.")
        v = str(a.get("value") or "").strip()[:40]
        if not v:
            raise CreditDeskError("value: what the rule requires.")
        try:
            val: Any = float(v)
        except ValueError:
            val = v
        st["uw_rules"] = [r for r in st["uw_rules"] if r["code"] != code] + [{"code": code, "field": f, "op": op, "value": val,
                                                                              "severity": sev, "by": me}]
        st["uw_rules"] = st["uw_rules"][-200:]
    _put(owner, ws, st)
    return {"rules": st["uw_rules"]}


# ---------------------------------------------------------------- today
def _say_day(d: str | None) -> str:
    try:
        x = date.fromisoformat(str(d)[:10])
        return f"{x.day} {x:%b %Y}"
    except ValueError:
        return str(d or "")


def today_view(owner: str, ws: str, me: str) -> dict[str, Any]:
    st = _state(owner, ws)
    cur = str(_wsrow(owner, ws).get("currency") or "").upper()

    def mo(x: float) -> str:
        return f"{cur} {x:,.2f}".strip()
    b = book(owner, ws)
    t = _today().isoformat()
    week0 = (_today() - timedelta(days=_today().weekday())).isoformat()
    cons = contacts(owner, ws)
    apps = [app_view(owner, ws, x, me) for x in st["apps"]]
    open_apps = [x for x in apps if x["status"] != "closed"]
    out: dict[str, Any] = {"book": b, "apps": apps, "offers": st["offers"], "policy": st["policy"], "uw_rules": st["uw_rules"],
                           "method": method_view(owner, ws), "contacts": cons,
                           "contacts_this_week": len([c for c in cons["log"] if c["when"][:10] >= week0])}
    needs = []
    for v in sorted([v for v in b["loans"] if v["side"] == "lent" and v["arrears"] > 0], key=lambda v: -v["days_past_due"])[:6]:
        needs.append({"say": f"{v['name']} is {v['days_past_due']} days past due ({mo(v['arrears'])} behind)", "go": f"loans/{v['n']}",
                      "bad": v["days_past_due"] > 30})
    for x in b["borrowed"]["missed"]:
        needs.append({"say": f"Your loan from {x['name']}: {mo(x['arrears'])} unpaid, {x['days_past_due']} days late", "go": f"loans/{x['n']}",
                      "bad": True})
    for x in b["borrowed"]["due_soon"]:
        needs.append({"say": f"Your payment of {mo(x['payment'])} to {x['name']} is due on {_say_day(x['next_due'])}", "go": f"loans/{x['n']}"})
    for a in open_apps:
        ck = a.get("checklist") or {}
        late = [i["name"] for i in ck.get("items") or [] if i.get("late")]
        if late:
            needs.append({"say": f"{a['borrower']}: {len(late)} condition(s) past their date ({', '.join(late[:3])})", "go": f"apps/{a['n']}",
                          "bad": False})
    rising = [v for v in b["loans"] if v["side"] == "lent" and v["rising"]]
    if rising:
        needs.append({"say": f"Days past due rising on {len(rising)} loan(s): " + ", ".join(v["name"] for v in rising[:3]), "go": "risk"})
    if b["lent"]["count"]:
        nop = [v for v in b["loans"] if v["side"] == "lent" and (v.get("pd") is None or v.get("lgd") is None)]
        if nop:
            needs.append({"say": f"{len(nop)} loan(s) need your PD and LGD for the ECL working paper", "go": "risk"})
        if not cons["rules"]:
            needs.append({"say": "Save your collections contact rules (Hoola's floor applies until you do)", "go": "settings"})
    if not out["method"]["method"]:
        needs.append({"say": "Choose an APR method - your country is not on Hoola's list", "go": "settings"})
    out["needs"] = needs
    return out


def summary(tenant: str, want: str = "") -> dict[str, Any]:
    from .fin.desks import books_ent as E
    h = _hire()
    st = h.status(tenant, KEY)
    trust = ""
    if st not in ("hired", "paused"):
        try:
            shared = E.shared_with(tenant)
        except Exception:   # noqa: BLE001
            shared = []
        if not shared:
            return {"hired": False, "status": st, "say": "Credit & Lending is not hired. Hire it from AI Employees."}
    else:
        with session() as s:
            trust = h._view(h._row(s, tenant, KEY)).get("trust") or ""    # noqa: SLF001
    out: dict[str, Any] = {"hired": True, "status": st if st in ("hired", "paused") else "member",
                           "trust": {"seekh": "Learning", "saathi": "Partner", "bharosa": "Trusted"}.get(trust, "Learning"),
                           "businesses": businesses(tenant), "workspace": workspace(tenant, want), "roles": ROLE_SAY, "foot": FOOT,
                           "figures_suggested": FIG_SUGGEST}
    w = out["workspace"]
    if w:
        try:
            acc = E.access(tenant, w["id"])
            out["role"] = acc["role"]
            out["can_write"] = acc["role"] in WRITE
            out["desk"] = today_view(acc["owner"], w["id"], f"{acc['name']} <{tenant}>")
        except Exception as e:   # noqa: BLE001
            log.exception("credit desk read failed")
            out["desk_error"] = str(e)[:200]
    return out


READS = {"apr", "compare", "invoice_finance", "readiness", "app", "risk", "contacts", "book"}


def do(caller: str, part: str, a: dict[str, Any]) -> dict[str, Any]:
    """Every desk action: her role on this business first, then the engine / the desk state on the OWNER's books."""
    from .fin.desks import books_ent as E
    a = {k: v for k, v in (a or {}).items() if not str(k).startswith("_")}
    ws = str(a.get("workspace") or "")
    acc = E.access(caller, ws)
    role, owner = acc["role"], acc["owner"]
    me = f"{acc['name']} <{caller}>"
    if part not in READS and role not in WRITE:
        raise CreditDeskError(f"Your role ({ROLE_SAY.get(role, role)}) can read this desk but not change it.")
    f = {
        "apr": lambda: apr_calc(owner, ws, me, a), "compare": lambda: compare(owner, ws, me),
        "invoice_finance": lambda: invoice_fin(owner, ws, me, a), "readiness": lambda: readiness(owner, ws, me, a),
        "app": lambda: app_one(owner, ws, me, a.get("n")), "risk": lambda: risk(owner, ws, me), "contacts": lambda: contacts(owner, ws),
        "book": lambda: book(owner, ws),
        "add_offer": lambda: add_offer(owner, ws, a, me), "remove_offer": lambda: remove_offer(owner, ws, a.get("n")),
        "add_loan": lambda: add_loan(owner, ws, a, me), "edit_loan": lambda: edit_loan(owner, ws, a, me),
        "remove_loan": lambda: remove_loan(owner, ws, a.get("n")), "payment": lambda: add_payment(owner, ws, a, me),
        "remove_payment": lambda: remove_payment(owner, ws, a),
        "add_app": lambda: add_app(owner, ws, a, me), "edit_app": lambda: edit_app(owner, ws, a, me),
        "app_figure": lambda: set_app_figure(owner, ws, a, me), "app_field": lambda: set_app_field(owner, ws, a, me),
        "condition": lambda: set_condition(owner, ws, a, me), "close_app": lambda: close_app(owner, ws, a, me),
        "reopen_app": lambda: reopen_app(owner, ws, a.get("n")), "remove_app": lambda: remove_app(owner, ws, a.get("n")),
        "collect": lambda: collect(owner, ws, me, a), "contact_rules": lambda: save_contact_rules(owner, ws, me, a),
        "method": lambda: set_method(owner, ws, a, me), "policy": lambda: set_policy(owner, ws, a, me),
        "rule": lambda: set_rule(owner, ws, a, me),
    }.get(part)
    if f is None:
        raise CreditDeskError("Not a Credit & Lending desk action.")
    from .fin.desks import credit as C
    try:
        out = f()
    except C.CreditError as e:
        raise CreditDeskError(str(e))
    if part not in READS:
        forget(owner)
        forget(caller)
    return out


def owns(tenant: str, conv: str) -> bool:
    with session() as s:
        c = s.get(Conversation, conv)
        return bool(c is not None and c.tenant_id == tenant and (c.kind or "") == KIND and not c.deleted)


# ---------------------------------------------------------------- the chat
def _q(tenant: str):
    return select(Conversation).where(Conversation.tenant_id == tenant, Conversation.kind == KIND,
                                      or_(Conversation.deleted.is_(None), Conversation.deleted.is_(False)))


def greeting(tenant: str) -> str:
    d = summary(tenant)
    if not d.get("hired"):
        return "I work out loans, both the ones you take and the ones you give. Hire me from AI Employees to start."
    if not d.get("workspace"):
        return "Hello. Set up your business in Books & Accounts first (name, country, currency), then I can work on your loans."
    k = d.get("desk") or {}
    b = k.get("book") or {}
    lent, mine = b.get("lent") or {}, b.get("borrowed") or {}
    bits = []
    if lent.get("count"):
        bits.append(f"{lent['count']} loan(s) you lent, {lent.get('in_arrears', 0)} in arrears")
    if mine.get("count"):
        bits.append(f"{mine['count']} loan(s) you owe")
    open_apps = [x for x in k.get("apps") or [] if x.get("status") != "closed"]
    if open_apps:
        bits.append(f"{len(open_apps)} open application(s)")
    line = "Hello. " + ("On this desk: " + "; ".join(bits) + ". " if bits else "")
    if k.get("needs"):
        line += f"{len(k['needs'])} thing(s) need you. "
    return line + ("Ask me the real cost of a loan, compare offers, or drop a borrower's statement here. I give no score and approve "
                   "nothing - that is the named person's decision.")


def current(tenant: str) -> dict[str, Any]:
    with session() as s:
        c = s.scalars(_q(tenant).order_by(func.coalesce(Conversation.last_at, Conversation.created_at).desc()).limit(1)).first()
        if c is not None:
            _OF[c.id] = True
            return {"id": c.id, "new": False}
    return new_chat(tenant)


def new_chat(tenant: str) -> dict[str, Any]:
    with session() as s:
        for c in s.scalars(_q(tenant).order_by(Conversation.created_at.desc()).limit(3)).all():
            n = s.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id, Message.role == "user"))
            if not n:
                return {"id": c.id, "new": False}
        c = Conversation(tenant_id=tenant, kind=KIND, title="Credit chat")
        s.add(c)
        s.flush()
        cid = c.id
    _OF[cid] = True
    hi = greeting(tenant)
    with session() as s:
        s.add(Message(conversation_id=cid, role="assistant", content=hi, display=hi, in_history=False, delivered_to_agent=True))
    return {"id": cid, "new": True}


RULES = ("You are her Credit & Lending employee, talking in the desk's own chat (or a voice call started from it). Use the " + TOOL +
         " tool with workspace set to the business below: apr (a loan's APR by her country's method - pass country or method), shop (offers "
         "side by side), invoice_finance, readiness (her own statements and books for a lender), analyse (a borrower's statement rows), "
         "memo (a credit memo - every figure needs its source), rules (her own policy rules), kfs (a key-facts draft), conditions, "
         "servicing (a schedule against what was paid), collect (check a collections contact against her contact rules - it is only logged "
         "as planned, never sent), ews, ecl, methods. Every figure you say comes from the tool - never estimate one. The APR method of a "
         "country is from memory unless she chose one: say 'check this'. You give no credit score and never approve, decline or pay out a "
         "loan: the decision belongs to the named credit officer or committee. Never write a rule on religion, caste, gender, race, marital "
         "status, disability, area or surname. Never send a collections message or contact anyone other than the borrower. Never ask for or "
         "keep a password, a PIN or a full card number. Plain English, short. Not credit advice. ")


def block(tenant: str) -> str:
    hit = _BLOCK.get(tenant)
    if hit and time.time() - hit[0] < BLOCK_TTL:
        return hit[1]
    try:
        d = summary(tenant)
        if not d.get("hired"):
            txt = f"\n\n<credit_desk>{RULES}Credit & Lending is not hired yet: tell her to hire it from AI Employees.</credit_desk>"
        elif not d.get("workspace"):
            txt = f"\n\n<credit_desk>{RULES}\nNo business set up yet: ask her to set it up in Books & Accounts.</credit_desk>"
        else:
            w, k = d["workspace"], d.get("desk") or {}
            b = k.get("book") or {}
            lent, mine = b.get("lent") or {}, b.get("borrowed") or {}
            m = k.get("method") or {}
            loans = "; ".join(f"#{v['n']} {v['name']} ({v['side']}) owed {v['outstanding']:,.2f}, arrears {v['arrears']:,.2f}, "
                              f"{v['days_past_due']} days past due, next due {v['next_due'] or '-'}" for v in (b.get("loans") or [])[:12]) or "none"
            apps = "; ".join(f"#{x['n']} {x['borrower']} {x['amount']:,.2f} ({x['status']})" for x in (k.get("apps") or [])[:10]) or "none"
            txt = (f"\n\n<credit_desk>{RULES}\nBusiness: {w['name']} (workspace {w['id']}), {', '.join(w['countries'])}, currency {w['currency']}."
                   f"\nAPR method: {m.get('method') or 'none'} ({m.get('from')})."
                   f"\nLent: {lent.get('count', 0)} loans, {lent.get('outstanding', 0):,.2f} owed to her, {lent.get('in_arrears', 0)} in arrears "
                   f"({lent.get('arrears', 0):,.2f}). Borrowed: {mine.get('count', 0)} loans, {mine.get('outstanding', 0):,.2f} she owes, "
                   f"{mine.get('monthly', 0):,.2f} a month."
                   f"\nLoans: {loans}.\nApplications: {apps}."
                   f"\nOffers she is comparing: {', '.join(o['name'] for o in k.get('offers') or []) or 'none'}."
                   + (f"\nShe is the {d.get('role')} on this business (someone else owns it): explain from these figures and send her "
                      "to the desk for changes." if d.get("role") not in (None, "owner") else "")
                   + "</credit_desk>")
    except Exception:   # noqa: BLE001
        log.exception("credit block failed")
        txt = f"\n\n<credit_desk>{RULES}The desk could not be read just now.</credit_desk>"
    _BLOCK[tenant] = (time.time(), txt)
    return txt


def forget(tenant: str) -> None:
    _BLOCK.pop(tenant, None)


# ---------------------------------------------------------------- routes
router = APIRouter()


def mount(app, current_tenant, require_key) -> None:
    dep = [Depends(require_key)]

    @router.get("/api/credit/chat", dependencies=dep)
    def credit_chat(tenant: str = Depends(current_tenant)):
        return current(tenant)

    @router.post("/api/credit/chat/new", dependencies=dep)
    def credit_chat_new(tenant: str = Depends(current_tenant)):
        forget(tenant)
        return new_chat(tenant)

    @router.get("/api/credit/chat/{conv}/ok", dependencies=dep)
    def credit_chat_ok(conv: str, tenant: str = Depends(current_tenant)):
        if not owns(tenant, conv):
            raise HTTPException(404, "Not your Credit chat")
        return {"ok": True}

    @router.get("/api/credit/desk", dependencies=dep)
    def credit_desk(workspace: str = "", tenant: str = Depends(current_tenant)):
        forget(tenant)
        return summary(tenant, workspace)

    @router.post("/api/credit/do/{part}", dependencies=dep)
    def credit_do(part: str, body: dict | None = None, tenant: str = Depends(current_tenant)):
        from .fin import laws as L
        from .fin.desks.safety import SafetyError
        try:
            return do(tenant, part, body or {})
        except L.Refused as e:
            raise HTTPException(403, str(e))
        except (SafetyError, ValueError) as e:
            raise HTTPException(400, str(e))

    @router.get("/api/credit/download", dependencies=dep)
    def credit_download(workspace: str, what: str, n: int = 0, tenant: str = Depends(current_tenant)):
        from fastapi.responses import Response
        from .fin.desks import books_ent as E
        try:
            acc = E.access(tenant, workspace)
        except ValueError as e:
            raise HTTPException(404, str(e))
        me = f"{acc['name']} <{tenant}>"
        biz = next((b for b in businesses(tenant) if b["id"] == workspace), {"name": "Business", "currency": ""})
        try:
            if what == "book":
                return Response(loan_book_csv(book(acc["owner"], workspace), biz.get("currency") or ""), media_type="text/csv",
                                headers={"Content-Disposition": f'attachment; filename="loan-book-{_today().isoformat()}.csv"'})
            a = app_one(acc["owner"], workspace, me, n)
        except CreditDeskError as e:
            raise HTTPException(400, str(e))
        slug = "".join(ch if ch.isalnum() else "-" for ch in a["borrower"].lower())[:40].strip("-") or "application"
        if what == "memo":
            if not a.get("memo") or a["memo"].get("error"):
                raise HTTPException(400, (a.get("memo") or {}).get("error") or "Add figures with their sources (or statement rows) first.")
            return Response(memo_pdf(a, biz["name"]), media_type="application/pdf",
                            headers={"Content-Disposition": f'attachment; filename="credit-memo-{slug}.pdf"'})
        if what == "memo_md":
            if not a.get("memo") or a["memo"].get("error"):
                raise HTTPException(400, "Add figures with their sources (or statement rows) first.")
            return Response(a["memo"]["memo_markdown"].encode("utf-8"), media_type="text/markdown",
                            headers={"Content-Disposition": f'attachment; filename="credit-memo-{slug}.md"'})
        if what == "kfs":
            if not a.get("kfs") or a["kfs"].get("error"):
                raise HTTPException(400, (a.get("kfs") or {}).get("error") or "Give the proposed rate and term first.")
            return Response(a["kfs"]["kfs_markdown"].encode("utf-8"), media_type="text/markdown",
                            headers={"Content-Disposition": f'attachment; filename="key-facts-{slug}.md"'})
        raise HTTPException(400, "what: book | memo | memo_md | kfs")

    @router.put("/api/credit/workspace", dependencies=dep)
    def credit_workspace(body: dict, tenant: str = Depends(current_tenant)):
        try:
            return pick(tenant, str((body or {}).get("workspace") or ""))
        except CreditDeskError as e:
            raise HTTPException(400, str(e))

    app.include_router(router)
