"""F5 of docs/FINANCE_GLOBAL_PLAN.md - Cash & Treasury (employee `cash`, tool `cash_treasury`), for a sole trader up to a firm, in
any country. It reads her own statements (the spine), her open invoices and bills (F3) and her payroll runs (F5), never a guess:

  settings   min_cash (the least she wants in the bank), lag_days (how late her customers usually pay), weeks_buffer, exclude (statement
             words to leave out of the repeating items, e.g. a one-off), covenants [{name, kind min_cash | max_ratio | min_ratio,
             numerator, denominator, limit}].
  forecast   13 weeks from a date: opening cash, then per week money in (her open invoices on their due date + her lag; overdue ones in
             week 1, named) and money out (her open bills on their due date, the payroll from her last run on her pay day, the items that
             repeat in her statements on their usual day, her own one-off items), closing cash, the lowest week, the weeks under her
             minimum; and the 30 / 60 / 90-day view. Each line says where it came from.
  backtest   the repeating-items model checked on months she already lived: for each held-out month it is built only from the months
             before, then compared with what really happened (error per month and on average).
  idle       the SME treasurer: how much cash was not needed in any of the 13 weeks after her buffer - the part she could put aside.
             Hoola names no product and moves nothing.
  fees       bank charges in her statements by kind and month, the yearly figure.
  fx         money owed to or by her and held in other currencies, its value at the rates SHE gives, and what a move of X% would do.
  covenants  her loan covenants checked on her figures (and the lowest forecast week for a cash covenant): headroom or breach.

Bank asset-liability work waits for F9. Not advice; nothing is paid or moved."""
from __future__ import annotations

import json
import re
import statistics
from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .. import laws as L
from ..calc import from_minor, to_minor


class CashError(ValueError):
    pass


MOVES_NOTHING = "Hoola moves no money and names no product: these are your figures."


def _ws(tenant: str, ws: str) -> dict[str, Any]:
    from ..profile import ProfileError, get
    try:
        return get(tenant, ws)
    except ProfileError as e:
        raise CashError(str(e))


def _cfg(w: dict[str, Any]) -> dict[str, Any]:
    return dict((w.get("settings") or {}).get("cash") or {})


def _cur(w: dict[str, Any]) -> str:
    return str(w.get("currency") or "USD").upper()


def _u(minor: int, cur: str) -> float:
    return float(from_minor(int(minor), cur))


def _day(s: Any, what: str) -> date:
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        raise CashError(f"{what}: a date as YYYY-MM-DD.")


def _num(v: Any, what: str) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        raise CashError(f"{what}: a number.")


def save_settings(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    from ... import db
    from ..models import FinWorkspace, ensure
    w = _ws(tenant, ws)
    cur = _cur(w)
    new: dict[str, Any] = {}
    if a.get("min_cash") is not None:
        new["min_cash_minor"] = to_minor(_num(a["min_cash"], "min_cash"), cur)
    for k in ("lag_days", "weeks_buffer"):
        if a.get(k) is not None:
            new[k] = max(0, int(_num(a[k], k)))
    if a.get("exclude") is not None:
        new["exclude"] = [str(x).lower()[:40] for x in a["exclude"]][:30]
    if a.get("covenants") is not None:
        cv = []
        for i, c in enumerate(a["covenants"]):
            if c.get("kind") not in ("min_cash", "max_ratio", "min_ratio"):
                raise CashError(f"covenants[{i}].kind: min_cash | max_ratio | min_ratio.")
            if c["kind"] != "min_cash" and not (c.get("numerator") and c.get("denominator")):
                raise CashError(f"covenants[{i}]: a ratio needs numerator and denominator (the names of your figures).")
            cv.append({"name": str(c.get("name") or c["kind"])[:80], "kind": c["kind"], "limit": _num(c.get("limit"), f"covenants[{i}].limit"),
                       "numerator": str(c.get("numerator") or "")[:40], "denominator": str(c.get("denominator") or "")[:40]})
        new["covenants"] = cv[:12]
    if not new:
        raise CashError("settings: min_cash, lag_days, weeks_buffer, exclude, covenants.")
    ensure()
    with db.session() as s:
        row = s.get(FinWorkspace, ws)
        if not row or row.tenant_id != tenant:
            raise CashError("No such workspace.")
        st = json.loads(row.settings or "{}")
        st.setdefault("cash", {}).update(new)
        row.settings = json.dumps(st)
        s.commit()
        cfg = dict(st["cash"])
    if "min_cash_minor" in cfg:
        cfg["min_cash"] = _u(cfg.pop("min_cash_minor"), cur)
    return {"workspace": ws, "cash": cfg}


# ---- the repeating items ----------------------------------------------------------------------------------------------------

_DIGITS = re.compile(r"[\d/#:.-]+")


def _key(narration: str) -> str:
    """A narration without its changing parts (dates, numbers, references), so this month's rent matches last month's."""
    t = _DIGITS.sub(" ", str(narration or "").lower())
    return " ".join(t.split()[:4])


def _month(d: str) -> str:
    return d[:7]


def _add_months(ym: str, n: int) -> str:
    y, m = int(ym[:4]), int(ym[5:7]) - 1 + n
    return f"{y + m // 12}-{m % 12 + 1:02d}"


def recurring(rows: list[dict[str, Any]], months: list[str], exclude: list[str] = ()) -> list[dict[str, Any]]:
    """Items that appear in at least 2 of the given months: the median amount and the median day of the month.
    Signs kept: money in is positive, out negative."""
    seen: dict[tuple[str, int], dict[str, list]] = defaultdict(lambda: {"months": set(), "amounts": [], "days": []})
    want = set(months)
    for r in rows:
        if _month(r["day"]) not in want:
            continue
        k = _key(r["narration"])
        if not k or any(x in k for x in exclude):
            continue
        g = seen[(k, 1 if r["amount_minor"] > 0 else -1)]
        g["months"].add(_month(r["day"]))
        g["amounts"].append(r["amount_minor"])
        g["days"].append(int(r["day"][8:10]))
    out = []
    for (k, _), g in seen.items():
        if len(g["months"]) >= 2:
            per = int((Decimal(sum(g["amounts"])) / len(g["months"])).quantize(Decimal(1), ROUND_HALF_UP))        # a month total, even if paid in two parts
            amts = sorted(g["amounts"])
            n_per_month = len(g["amounts"]) / len(g["months"])
            out.append({"item": k, "monthly_minor": per, "median_minor": int(statistics.median(amts)),
                        "day": int(statistics.median(g["days"])), "times_a_month": round(n_per_month, 2), "months_seen": len(g["months"])})
    return sorted(out, key=lambda x: x["monthly_minor"])


def _rows(tenant: str, ws: str, since: str = "", upto: str = "", cur: str = "") -> list[dict[str, Any]]:
    from .. import spine as SP
    rows = SP.txns(tenant, ws, since=since, until=upto, limit=5000)
    return [r for r in rows if not cur or r["currency"] == cur]


def predict_month(rows: list[dict[str, Any]], month: str, window: int = 3, exclude: list[str] = ()) -> dict[str, int]:
    """Net flow for a month from the `window` months before it only: the repeating items (monthly total) plus the average of what
    did not repeat in those months."""
    before = [_add_months(month, -i) for i in range(window, 0, -1)]
    rec = recurring(rows, before, exclude)
    rec_keys = {(r["item"], 1 if r["monthly_minor"] > 0 else -1) for r in rec}
    rest = 0
    for r in rows:
        if _month(r["day"]) in before:
            k = (_key(r["narration"]), 1 if r["amount_minor"] > 0 else -1)
            if k not in rec_keys:
                rest += r["amount_minor"]
    other = int((Decimal(rest) / window).quantize(Decimal(1), ROUND_HALF_UP))
    return {"repeating": sum(r["monthly_minor"] for r in rec), "other": other,
            "net": sum(r["monthly_minor"] for r in rec) + other}


def backtest(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _ws(tenant, ws)
    cur = _cur(w)
    rows = a.get("_rows") or _rows(tenant, ws, cur=cur)
    if not rows:
        raise CashError("No statement rows: import your bank statements first.")
    window, hold = int(a.get("window") or 3), int(a.get("hold_out") or 3)
    months = sorted({_month(r["day"]) for r in rows})
    if len(months) < window + hold:
        raise CashError(f"Needs at least {window + hold} months of statements ({window} to learn from, {hold} to check); "
                        f"you have {len(months)}.")
    exclude = _cfg(w).get("exclude") or []
    out, errs, abs_err = [], [], 0
    for m in months[-hold:]:
        p = predict_month(rows, m, window, exclude)
        actual = sum(r["amount_minor"] for r in rows if _month(r["day"]) == m)
        outflow = -sum(r["amount_minor"] for r in rows if _month(r["day"]) == m and r["amount_minor"] < 0)
        e = p["net"] - actual
        pct = round(abs(e) * 100 / outflow, 1) if outflow else None
        abs_err += abs(e)
        if pct is not None:
            errs.append(pct)
        out.append({"month": m, "predicted": _u(p["net"], cur), "actual": _u(actual, cur), "error": _u(e, cur),
                    "error_pct_of_spending": pct, "learned_from": [_add_months(m, -i) for i in range(window, 0, -1)]})
    mean = round(sum(errs) / len(errs), 1) if errs else None
    return {"months": out, "mean_abs_error": _u(abs_err // len(out), cur), "mean_error_pct_of_spending": mean,
            "says": "Each held-out month was predicted only from the months before it, then compared with your statements."}


# ---- the 13-week forecast -----------------------------------------------------------------------------------------------------

def _opening(tenant: str, ws: str, cur: str, a: dict[str, Any]) -> tuple[int, str, list[dict[str, Any]]]:
    if a.get("opening") is not None:
        return to_minor(_num(a["opening"], "opening"), cur), "the opening figure you gave", []
    from .. import spine as SP
    tot, other = 0, []
    for acc in SP.accounts(tenant, ws):
        if acc["currency"] == cur:
            tot += acc["net_minor"]
        else:
            other.append({"account": acc["name"], "currency": acc["currency"], "balance": acc["net"]})
    return tot, "your statements (all accounts in " + cur + ")", other


def forecast(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _ws(tenant, ws)
    cur = _cur(w)
    c = _cfg(w)
    start = _day(a.get("start") or date.today().isoformat(), "start")
    start = start - timedelta(days=start.weekday())                    # weeks run Monday to Sunday
    weeks = max(1, min(26, int(a.get("weeks") or 13)))
    end = start + timedelta(days=7 * weeks - 1)
    lag = int(a.get("lag_days", c.get("lag_days", 0)) or 0)
    opening, opening_src, other_cur = _opening(tenant, ws, cur, a)
    items: list[dict[str, Any]] = []

    def put(day: date, minor: int, what: str, src: str) -> None:
        if day <= end:
            items.append({"day": max(day, start), "minor": minor, "what": what, "source": src, "late": day < start})

    from .books import _db
    db, M = _db()
    with db.session() as s:
        q = s.query(M.FinInvoice).filter(M.FinInvoice.tenant_id == tenant, M.FinInvoice.workspace_id == ws,
                                          M.FinInvoice.status == "open")
        for d in q.all():
            left = int(round((d.total_minor - d.paid_minor) * (d.carried_rate if d.currency != cur else 1)))
            if left <= 0 or not d.due:
                continue
            due = date.fromisoformat(d.due)
            if d.kind == "sales":
                put(due + timedelta(days=lag), left, f"invoice {d.number} {d.party}", "your open invoice" + (f" + {lag} days" if lag else ""))
            else:
                put(due, -left, f"bill {d.number} {d.party}", "your open bill")
    runs = ((w.get("settings") or {}).get("payroll") or {}).get("runs") or {}
    pay_day = ((w.get("settings") or {}).get("payroll") or {}).get("pay_day") or 28
    if runs:
        last = runs[sorted(runs)[-1]]
        if last["currency"] == cur and len(last["period"]) == 7:
            outflow = to_minor(last["totals"]["net"], cur) + sum(to_minor(v, cur) for v in last["to_authorities"].values())
            m = start.replace(day=1)
            while m <= end:
                d = m.replace(day=min(pay_day, 28))
                if d >= start:
                    put(d, -outflow, "payroll (net pay + to authorities)", f"your payroll for {last['period']}")
                m = (m + timedelta(days=32)).replace(day=1)
    hist = a.get("_rows") or _rows(tenant, ws, since=(start - timedelta(days=100)).isoformat(), upto=(start - timedelta(days=1)).isoformat(),
                                    cur=cur)
    excl = (c.get("exclude") or []) + (["salary", "payroll", "wages"] if runs else [])
    months = sorted({_month(r["day"]) for r in hist})[-3:]
    rep = recurring(hist, months, excl) if len(months) >= 2 else []
    for r in rep:
        m = start.replace(day=1)
        while m <= end:
            last_dom = ((m + timedelta(days=32)).replace(day=1) - timedelta(days=1)).day
            d = m.replace(day=min(r["day"], last_dom))
            if d >= start:
                put(d, r["monthly_minor"], r["item"], f"repeats in your statements ({r['months_seen']} of the last {len(months)} months)")
            m = (m + timedelta(days=32)).replace(day=1)
    for i, x in enumerate(a.get("items") or []):
        put(_day(x.get("date"), f"items[{i}].date"), to_minor(_num(x.get("amount"), f"items[{i}].amount"), cur),
            str(x.get("label") or "your item")[:80], "your own item")
    rows, bal, low = [], opening, None
    for i in range(weeks):
        a0 = start + timedelta(days=7 * i)
        a1 = a0 + timedelta(days=6)
        wk = [x for x in items if a0 <= x["day"] <= a1]
        inn = sum(x["minor"] for x in wk if x["minor"] > 0)
        out = sum(x["minor"] for x in wk if x["minor"] < 0)
        bal += inn + out
        row = {"week": i + 1, "from": a0.isoformat(), "to": a1.isoformat(), "in": _u(inn, cur), "out": _u(-out, cur),
               "closing": _u(bal, cur), "_closing": bal,
               "lines": [{"day": x["day"].isoformat(), "amount": _u(x["minor"], cur), "what": x["what"], "source": x["source"],
                          **({"overdue": True} if x["late"] else {})} for x in sorted(wk, key=lambda x: x["day"])]}
        rows.append(row)
        if low is None or bal < low[1]:
            low = (i + 1, bal)
    mn = c.get("min_cash_minor")
    under = [r["week"] for r in rows if mn is not None and r["_closing"] < mn]
    horizon = {}
    for d in (30, 60, 90):
        cut = start + timedelta(days=d - 1)
        horizon[f"{d}_days"] = _u(opening + sum(x["minor"] for x in items if x["day"] <= cut), cur)
    for r in rows:
        r.pop("_closing")
    return {"currency": cur, "start": start.isoformat(), "opening": _u(opening, cur), "opening_from": opening_src, "weeks": rows,
            "lowest": {"week": low[0], "closing": _u(low[1], cur)}, "under_minimum_weeks": under,
            "minimum": _u(mn, cur) if mn is not None else None, "view_30_60_90": horizon,
            "overdue_invoices": [x["what"] for x in items if x["late"] and x["minor"] > 0],
            "other_currency_accounts": other_cur, "repeating_items_used": len(rep),
            "says": "Built from your open invoices and bills, your last payroll and what repeats in your statements. " + MOVES_NOTHING,
            "_low_minor": low[1], "_rows_minor": [opening]}


def idle(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _ws(tenant, ws)
    cur = _cur(w)
    c = _cfg(w)
    f = forecast(tenant, ws, a)
    outs = [to_minor(x["out"], cur) for x in f["weeks"]]
    avg_out = sum(outs) // max(1, len(outs))
    wb = int(a.get("weeks_buffer", c.get("weeks_buffer", 4)) or 0)
    buffer = max(c.get("min_cash_minor") or 0, avg_out * wb)
    spare = f["_low_minor"] - buffer
    return {"currency": cur, "lowest_week": f["lowest"], "average_weekly_out": _u(avg_out, cur),
            "buffer": _u(buffer, cur), "buffer_rule": f"the larger of your minimum and {wb} weeks of average spending",
            "idle": _u(max(0, spare), cur),
            "says": (f"About {_u(spare, cur)} {cur} was not needed in any of the {len(f['weeks'])} weeks after your buffer - you could put it "
                     "aside for that long. " if spare > 0 else "No spare cash after your buffer in this forecast. ") + MOVES_NOTHING}


# ---- fees, fx, covenants ----------------------------------------------------------------------------------------------------

FEE_KINDS = (("overdraft or interest charged", r"overdraft|interest charged|debit interest|od int"),
             ("account fee", r"monthly fee|account fee|maintenance|service charge|min(imum)? bal"),
             ("card or payment fee", r"card fee|merchant|pos charge|processing fee|swift|wire fee|transfer fee|imps|neft chg|rtgs chg"),
             ("cash or ATM fee", r"atm|cash handling|cash deposit fee"),
             ("message or other bank charge", r"sms|alert|chq book|cheque book|stop payment|bank charge|commission|\bfee\b|\bcharges?\b"))


def fees(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _ws(tenant, ws)
    cur = _cur(w)
    rows = a.get("_rows") or _rows(tenant, ws, since=str(a.get("since") or ""), upto=str(a.get("upto") or ""), cur=cur)
    kinds: dict[str, int] = defaultdict(int)
    months: dict[str, int] = defaultdict(int)
    lines = []
    for r in rows:
        if r["amount_minor"] >= 0:
            continue
        n = str(r["narration"]).lower()
        kind = next((k for k, rx in FEE_KINDS if re.search(rx, n)), "")
        if kind:
            kinds[kind] -= r["amount_minor"]
            months[_month(r["day"])] -= r["amount_minor"]
            lines.append({"day": r["day"], "narration": r["narration"], "amount": _u(-r["amount_minor"], cur), "kind": kind})
    total = sum(kinds.values())
    n_months = max(1, len({_month(r["day"]) for r in rows}))
    return {"currency": cur, "total": _u(total, cur), "by_kind": {k: _u(v, cur) for k, v in kinds.items()},
            "by_month": {k: _u(v, cur) for k, v in sorted(months.items())},
            "a_year_at_this_rate": _u(total * 12 // n_months, cur), "months_read": n_months, "lines": lines[:200],
            "says": "Found by the words on your statement; check the lines - a word can catch something that is not a fee."}


def fx(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _ws(tenant, ws)
    cur = _cur(w)
    rates = {str(k).upper(): _num(v, f"rates.{k}") for k, v in (a.get("rates") or {}).items()}
    shock = _num(a.get("move_pct", 10), "move_pct")
    pos: dict[str, dict[str, int]] = defaultdict(lambda: {"owed_to_you": 0, "you_owe": 0, "held": 0})
    from .books import _db
    db, M = _db()
    with db.session() as s:
        for d in s.query(M.FinInvoice).filter(M.FinInvoice.tenant_id == tenant, M.FinInvoice.workspace_id == ws,
                                               M.FinInvoice.status == "open", M.FinInvoice.currency != cur).all():
            pos[d.currency]["owed_to_you" if d.kind == "sales" else "you_owe"] += d.total_minor - d.paid_minor
    from .. import spine as SP
    for acc in SP.accounts(tenant, ws):
        if acc["currency"] != cur:
            pos[acc["currency"]]["held"] += acc["net_minor"]
    out, total_move, missing = [], Decimal(0), []
    for c, p in sorted(pos.items()):
        net = p["owed_to_you"] + p["held"] - p["you_owe"]
        row = {"currency": c, "owed_to_you": _u(p["owed_to_you"], c), "you_owe": _u(p["you_owe"], c), "held": _u(p["held"], c),
               "net": _u(net, c)}
        if c in rates:
            val = Decimal(str(from_minor(net, c))) * Decimal(str(rates[c]))
            mv = (val * Decimal(str(shock)) / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
            row.update({"rate": rates[c], f"value_in_{cur}": float(val.quantize(Decimal("0.01"), ROUND_HALF_UP)),
                        f"if_{c}_falls_{shock:g}pct": float(-mv), f"if_{c}_rises_{shock:g}pct": float(mv)})
            total_move += mv
        else:
            missing.append(c)
        out.append(row)
    return {"book_currency": cur, "positions": out, "total_if_all_fall": float(-total_move), "rates_missing": missing,
            "says": "Valued at the rates you gave (book currency per one unit). " + ("Give a rate for: " + ", ".join(missing) + ". "
                                                                                     if missing else "") + MOVES_NOTHING}


def covenants(tenant: str, ws: str, a: dict[str, Any]) -> dict[str, Any]:
    w = _ws(tenant, ws)
    cur = _cur(w)
    cv = a.get("covenants") or _cfg(w).get("covenants") or []
    if not cv:
        raise CashError("covenants: put your loan covenants in settings (name, kind min_cash | max_ratio | min_ratio, numerator, "
                        "denominator, limit) - from your loan agreement.")
    figs = {str(k): _num(v, f"figures.{k}") for k, v in (a.get("figures") or {}).items()}
    low = None
    out = []
    for c in cv:
        if c["kind"] == "min_cash":
            if "cash" in figs:
                actual, src = figs["cash"], "your figure"
            else:
                if low is None:
                    f = forecast(tenant, ws, a)
                    low = _u(f["_low_minor"], cur)
                actual, src = low, "the lowest week of your 13-week forecast"
            ok, head = actual >= c["limit"], actual - c["limit"]
            out.append({"name": c["name"], "test": f"cash at least {c['limit']}", "actual": actual, "from": src, "ok": ok,
                        "headroom": round(head, 2)})
            continue
        n, d = figs.get(c["numerator"]), figs.get(c["denominator"])
        if n is None or d is None or d == 0:
            out.append({"name": c["name"], "ok": None, "says": f"Needs your figures {c['numerator']} and {c['denominator']} (not zero)."})
            continue
        ratio = float((Decimal(str(n)) / Decimal(str(d))).quantize(Decimal("0.01"), ROUND_HALF_UP))
        ok = ratio <= c["limit"] if c["kind"] == "max_ratio" else ratio >= c["limit"]
        out.append({"name": c["name"], "test": f"{c['numerator']} / {c['denominator']} {'at most' if c['kind'] == 'max_ratio' else 'at least'} "
                    f"{c['limit']}", "actual": ratio, "ok": ok, "headroom": round((c["limit"] - ratio) if c["kind"] == "max_ratio"
                                                                              else (ratio - c["limit"]), 2)})
    return {"covenants": out, "breached": [x["name"] for x in out if x.get("ok") is False],
            "says": "Checked on your figures and your loan's limits as you gave them; your lender's own calculation decides."}


ACTIONS = ("settings", "forecast", "backtest", "idle", "fees", "fx", "covenants")


def run(tenant: str, action: str, a: dict[str, Any], actor: str = "owner") -> dict[str, Any]:
    a = dict(a)
    a.pop("_rows", None)                    # only the card hands rows in directly
    ws = str(a.get("workspace") or "")
    if not ws:
        raise CashError("workspace: the finance workspace these figures belong to.")
    f = {"settings": save_settings, "forecast": forecast, "backtest": backtest, "idle": idle, "fees": fees, "fx": fx,
         "covenants": covenants}
    if action not in f:
        raise CashError("action: " + ", ".join(ACTIONS))
    out = f[action](tenant, ws, a)
    for k in [k for k in out if k.startswith("_")]:
        out.pop(k)
    out.setdefault("not_advice", L.NOT_ADVICE)
    return out
