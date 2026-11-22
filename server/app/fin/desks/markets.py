"""F10 of docs/FINANCE_GLOBAL_PLAN.md - Markets & Post-Trade (employee 10; tool `markets_desk`), for brokers, asset managers, custodians
and the investor-relations side of a listed company, any country.

  recon        positions (and cash) in HER books against a custodian's or broker's file, by account and instrument: missing at the
               custodian, missing in her books, quantity breaks, cash breaks, each with the difference. Files as rows or CSV text.
  confirm      her trades against the counterparties' confirmations: matched, unconfirmed, confirmations with no trade, and the field
               breaks (quantity, price beyond her tolerance, dates, side, account).
  fails        settlements past their intended date: age, value, and the penalty at the daily rate SHE gives.
  corp_action  a corporate action applied to the positions held at the record date: splits, consolidations, cash and stock dividends,
               rights - entitlements per account, fractions and the cash in lieu at her price.
  reclaim      dividend withholding: what was withheld against the treaty rate SHE gives, what can be reclaimed, and the date the claim
               must be in by (from the years she gives); expired claims named.
  margin       a margin call worked out: collateral after HER haircuts against the requirement, the shortfall, and the notice text.
  best_ex      executions against their benchmark price: slippage in basis points, the worst ones, the total cost.
  comps        a comparables table: EV / EBITDA, EV / revenue, P / E per peer, median and mean, and the value range they imply for a target.
  ssi          settlement instructions checked: missing parts, BIC and IBAN shape, two different instructions for the same account.
  calendar     an investor-relations / disclosure calendar from the period ends and HER rules (days after a period end).

No order is ever placed, changed, cancelled, allocated or affirmed: nothing here sends anything anywhere. Not investment advice."""
from __future__ import annotations

import csv
import io
import re
import statistics
from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .. import laws as L


class MarketsError(ValueError):
    pass


NEVER = "Hoola never places, changes, cancels, allocates or affirms an order or a trade: you (or your operations team) do."
ZERO = Decimal(0)


def _n(v: Any, what: str, lo: float | None = None) -> Decimal:
    try:
        x = Decimal(str(v).replace(",", "").strip())
    except Exception:
        raise MarketsError(f"{what}: a number.")
    if not x.is_finite():
        raise MarketsError(f"{what}: a number.")
    if lo is not None and x < Decimal(str(lo)):
        raise MarketsError(f"{what}: not below {lo}.")
    return x


def _d(s: Any, what: str) -> date:
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        raise MarketsError(f"{what}: a date as YYYY-MM-DD.")


def money(x: Decimal) -> float:
    return float(x.quantize(Decimal("0.01"), ROUND_HALF_UP))


def q6(x: Decimal) -> float:
    return float(x.quantize(Decimal("0.000001"), ROUND_HALF_UP))


def _rows(a: dict[str, Any], key: str) -> list[dict[str, Any]]:
    v = a.get(key)
    if v is None and a.get(key + "_csv"):
        v = list(csv.DictReader(io.StringIO(str(a[key + "_csv"]).strip())))
    if not isinstance(v, list):
        raise MarketsError(f"{key}: rows [{{...}}] or {key}_csv: CSV text with a header line.")
    return [{str(k).strip().lower(): (x.strip() if isinstance(x, str) else x) for k, x in r.items()} for r in v]


def _key(r: dict[str, Any]) -> tuple[str, str]:
    return (str(r.get("account") or "").upper(), str(r.get("symbol") or r.get("isin") or "").upper())


# ---- reconciliation ----------------------------------------------------------------------------------------------------------

def recon(a: dict[str, Any]) -> dict[str, Any]:
    ours, theirs = _rows(a, "internal"), _rows(a, "custodian")
    tol = _n(a.get("tolerance") or 0, "tolerance", 0)
    sum_o: dict[tuple, Decimal] = defaultdict(lambda: ZERO)
    sum_t: dict[tuple, Decimal] = defaultdict(lambda: ZERO)
    for i, r in enumerate(ours):
        sum_o[_key(r)] += _n(r.get("qty"), f"internal[{i}].qty")
    for i, r in enumerate(theirs):
        sum_t[_key(r)] += _n(r.get("qty"), f"custodian[{i}].qty")
    breaks, matched = [], 0
    for k in sorted(set(sum_o) | set(sum_t)):
        o, t = sum_o.get(k), sum_t.get(k)
        row = {"account": k[0], "symbol": k[1]}
        if t is None:
            if o != 0:
                breaks.append({**row, "break": "missing at the custodian", "ours": q6(o), "theirs": None, "difference": q6(o)})
            else:
                matched += 1
        elif o is None:
            if t != 0:
                breaks.append({**row, "break": "missing in our books", "ours": None, "theirs": q6(t), "difference": q6(-t)})
            else:
                matched += 1
        elif abs(o - t) > tol:
            breaks.append({**row, "break": "quantity", "ours": q6(o), "theirs": q6(t), "difference": q6(o - t)})
        else:
            matched += 1
    cash = []
    if a.get("internal_cash") is not None or a.get("custodian_cash") is not None:
        co: dict[tuple, Decimal] = defaultdict(lambda: ZERO)
        ct: dict[tuple, Decimal] = defaultdict(lambda: ZERO)
        for side, src in ((co, a.get("internal_cash") or []), (ct, a.get("custodian_cash") or [])):
            for i, r in enumerate(src):
                side[(str(r.get("account") or "").upper(), str(r.get("currency") or "").upper())] += _n(r.get("amount"), "cash.amount")
        for k in sorted(set(co) | set(ct)):
            o, t = co.get(k, ZERO), ct.get(k, ZERO)
            if abs(o - t) > Decimal("0.005"):
                cash.append({"account": k[0], "currency": k[1], "ours": money(o), "theirs": money(t), "difference": money(o - t)})
    return {"matched": matched, "breaks": breaks, "cash_breaks": cash, "balanced": not breaks and not cash,
            "by_kind": {k: sum(1 for b in breaks if b["break"] == k) for k in ("missing at the custodian", "missing in our books", "quantity")},
            "says": "Each break needs an owner and a reason; Hoola does not adjust either side."}


# ---- confirmations -----------------------------------------------------------------------------------------------------------

def confirm(a: dict[str, Any]) -> dict[str, Any]:
    trades, confs = _rows(a, "trades"), _rows(a, "confirms")
    ptol = _n(a.get("price_tolerance") or 0, "price_tolerance", 0)
    by_id = {str(c.get("id") or c.get("trade_id") or ""): c for c in confs}
    used, matched, breaks, unconfirmed = set(), [], [], []
    for i, t in enumerate(trades):
        tid = str(t.get("id") or "")
        c = by_id.get(tid)
        if c is None:
            unconfirmed.append(tid)
            continue
        used.add(tid)
        diffs = []
        for f in ("side", "symbol", "account", "trade_date", "settle_date"):
            if t.get(f) not in (None, "") and str(t.get(f)).upper() != str(c.get(f) or "").upper():
                diffs.append({"field": f, "ours": t.get(f), "theirs": c.get(f)})
        if _n(t.get("qty"), f"trades[{i}].qty") != _n(c.get("qty"), f"confirm {tid}.qty"):
            diffs.append({"field": "qty", "ours": q6(_n(t.get("qty"), "qty")), "theirs": q6(_n(c.get("qty"), "qty"))})
        tp, cp = _n(t.get("price"), f"trades[{i}].price"), _n(c.get("price"), f"confirm {tid}.price")
        if abs(tp - cp) > ptol:
            diffs.append({"field": "price", "ours": q6(tp), "theirs": q6(cp)})
        (breaks.append({"id": tid, "differences": diffs}) if diffs else matched.append(tid))
    orphan = [k for k in by_id if k not in used]
    return {"matched": matched, "breaks": breaks, "unconfirmed": unconfirmed, "confirms_with_no_trade": orphan,
            "affirmed": False, "never": NEVER}


def fails(a: dict[str, Any]) -> dict[str, Any]:
    today = _d(a.get("today") or date.today().isoformat(), "today")
    bp = _n(a["penalty_bp_per_day"], "penalty_bp_per_day", 0) if a.get("penalty_bp_per_day") is not None else None
    out = []
    for i, s in enumerate(_rows(a, "settlements")):
        if str(s.get("settled") or "").lower() in ("true", "yes", "1"):
            continue
        due = _d(s.get("intended"), f"settlements[{i}].intended")
        if due >= today:
            continue
        age = (today - due).days
        v = _n(s.get("value") or 0, f"settlements[{i}].value", 0)
        out.append({"id": s.get("id"), "symbol": s.get("symbol"), "counterparty": s.get("counterparty"), "days_late": age,
                    "value": money(v), "penalty": money(v * bp / 10000 * age) if bp is not None else None})
    out.sort(key=lambda x: -x["days_late"])
    buckets = {"1-2 days": 0, "3-5 days": 0, "6-10 days": 0, "over 10 days": 0}
    for f in out:
        d = f["days_late"]
        buckets["1-2 days" if d <= 2 else "3-5 days" if d <= 5 else "6-10 days" if d <= 10 else "over 10 days"] += 1
    return {"fails": out, "by_age": buckets, "value": money(sum((Decimal(str(f["value"])) for f in out), ZERO)),
            "penalty": money(sum((Decimal(str(f["penalty"])) for f in out), ZERO)) if bp is not None else
            "set penalty_bp_per_day (your market's rate) to estimate penalties"}


# ---- corporate actions -------------------------------------------------------------------------------------------------------

def _ratio(s: Any) -> tuple[Decimal, Decimal]:
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*[:/for ]+\s*(\d+(?:\.\d+)?)\s*", str(s or ""))
    if not m:
        raise MarketsError("ratio: like 2:1 (new for old).")
    new, old = Decimal(m.group(1)), Decimal(m.group(2))
    if new <= 0 or old <= 0:
        raise MarketsError("ratio: both sides above 0.")
    return new, old


def corp_action(a: dict[str, Any]) -> dict[str, Any]:
    ev = a.get("event") or {}
    kind = str(ev.get("type") or "").lower()
    sym = str(ev.get("symbol") or "").upper()
    rec = _d(ev.get("record_date"), "event.record_date")
    price = _n(ev["cash_in_lieu_price"], "event.cash_in_lieu_price", 0) if ev.get("cash_in_lieu_price") is not None else None
    held: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for i, p in enumerate(_rows(a, "positions")):
        if str(p.get("symbol") or "").upper() != sym:
            continue
        if p.get("date") and _d(p["date"], f"positions[{i}].date") > rec:
            continue
        held[str(p.get("account") or "")] += _n(p.get("qty"), f"positions[{i}].qty")
    out = []
    for acc, q in sorted(held.items()):
        row = {"account": acc, "held": q6(q)}
        if kind in ("split", "reverse_split", "consolidation", "stock_dividend", "bonus", "rights"):
            new, old = _ratio(ev.get("ratio"))
            if kind == "stock_dividend" or kind == "bonus" or kind == "rights":
                ent = q * new / old
                whole = ent.to_integral_value(rounding="ROUND_FLOOR")
                row.update({"entitled": q6(ent), "new_shares": float(whole), "fraction": q6(ent - whole)})
                if kind == "rights":
                    sub = _n(ev.get("subscription_price"), "event.subscription_price", 0)
                    row["cost_to_take_up"] = money(whole * sub)
            else:
                after = q * new / old
                whole = after.to_integral_value(rounding="ROUND_FLOOR")
                row.update({"after": float(whole), "fraction": q6(after - whole)})
            if row["fraction"] and price is not None:
                row["cash_in_lieu"] = money(Decimal(str(row["fraction"])) * price)
        elif kind == "cash_dividend":
            rate = _n(ev.get("rate"), "event.rate", 0)
            gross = q * rate
            wh = _n(ev.get("withholding_pct") or 0, "event.withholding_pct", 0)
            row.update({"gross": money(gross), "withheld": money(gross * wh / 100), "net": money(gross - gross * wh / 100)})
        else:
            raise MarketsError("event.type: split | reverse_split | consolidation | cash_dividend | stock_dividend | bonus | rights.")
        out.append(row)
    return {"event": {"type": kind, "symbol": sym, "record_date": rec.isoformat()}, "entitlements": out,
            "total_held": q6(sum(held.values(), ZERO)), "says": "Check the terms against the issuer's own notice before booking."}


def reclaim(a: dict[str, Any]) -> dict[str, Any]:
    treaty = {str(k).upper(): _n(v, f"treaty.{k}", 0) for k, v in (a.get("treaty") or {}).items()}
    years = {str(k).upper(): int(_n(v, f"claim_years.{k}", 0)) for k, v in (a.get("claim_years") or {}).items()}
    today = _d(a.get("today") or date.today().isoformat(), "today")
    out, missing = [], set()
    for i, d in enumerate(_rows(a, "dividends")):
        c = str(d.get("country") or "").upper()
        gross = _n(d.get("gross"), f"dividends[{i}].gross", 0)
        wh = _n(d.get("withheld"), f"dividends[{i}].withheld", 0)
        if c not in treaty:
            missing.add(c)
            continue
        back = wh - gross * treaty[c] / 100
        if back <= 0:
            continue
        paid = _d(d.get("date"), f"dividends[{i}].date")
        by = None
        if c in years:
            y = paid.year + years[c]
            try:
                by = date(y, paid.month, paid.day)
            except ValueError:
                by = date(y, 2, 28)
        out.append({"date": paid.isoformat(), "symbol": d.get("symbol"), "country": c, "gross": money(gross), "withheld": money(wh),
                    "treaty_rate_pct": float(treaty[c]), "reclaimable": money(back), "claim_by": by.isoformat() if by else None,
                    "expired": bool(by and by < today)})
    live = [x for x in out if not x["expired"]]
    return {"claims": out, "reclaimable": money(sum((Decimal(str(x["reclaimable"])) for x in live), ZERO)),
            "expired": money(sum((Decimal(str(x["reclaimable"])) for x in out if x["expired"]), ZERO)),
            "no_treaty_rate_given_for": sorted(missing), "says": "The treaty rate and the claim period are yours: check them with the tax office."}


def margin(a: dict[str, Any]) -> dict[str, Any]:
    hc = {str(k).upper(): _n(v, f"haircuts.{k}", 0) for k, v in (a.get("haircuts") or {}).items()}
    req = _n(a.get("requirement"), "requirement", 0)
    coll, rows = ZERO, []
    for i, c in enumerate(a.get("collateral") or []):
        v = _n(c.get("value"), f"collateral[{i}].value", 0)
        k = str(c.get("symbol") or "").upper()
        cl = str(c.get("class") or "").upper()
        h = hc.get(k, hc.get(cl))
        if h is None:
            raise MarketsError(f"haircuts: none given for {k or cl} (yours).")
        after = v * (1 - h / 100)
        coll += after
        rows.append({"item": k or cl, "value": money(v), "haircut_pct": float(h), "counts_for": money(after)})
    short = req - coll
    out = {"requirement": money(req), "collateral_after_haircuts": money(coll), "collateral": rows,
           "shortfall": money(short) if short > 0 else 0.0, "excess": money(-short) if short < 0 else 0.0}
    if short > 0:
        out["notice"] = (f"Margin call: the requirement is {money(req):,.2f} and your collateral counts for {money(coll):,.2f} after "
                         f"haircuts. Please provide {money(short):,.2f}" + (f" by {a['due']}" if a.get("due") else "") + ".")
    return out


def best_ex(a: dict[str, Any]) -> dict[str, Any]:
    out = []
    for i, e in enumerate(_rows(a, "executions")):
        side = str(e.get("side") or "").lower()
        px, bm = _n(e.get("price"), f"executions[{i}].price", 0), _n(e.get("benchmark"), f"executions[{i}].benchmark", 0)
        qty = _n(e.get("qty"), f"executions[{i}].qty", 0)
        if bm <= 0 or side not in ("buy", "sell"):
            raise MarketsError(f"executions[{i}]: side buy|sell and a benchmark above 0.")
        cost = (px - bm) * qty if side == "buy" else (bm - px) * qty
        out.append({"id": e.get("id"), "side": side, "slippage_bp": float(((cost / (bm * qty)) * 10000).quantize(Decimal("0.01"))) if qty else 0.0,
                    "cost": money(cost)})
    out.sort(key=lambda x: -x["slippage_bp"])
    return {"executions": out, "worst": out[:5], "total_cost": money(sum((Decimal(str(x["cost"])) for x in out), ZERO)),
            "average_bp": round(statistics.mean([x["slippage_bp"] for x in out]), 2) if out else 0.0}


def comps(a: dict[str, Any]) -> dict[str, Any]:
    peers = []
    mult = defaultdict(list)
    for i, p in enumerate(a.get("peers") or []):
        row = {"name": p.get("name") or f"#{i}"}
        ev = _n(p["ev"], "ev") if p.get("ev") is not None else None
        for m, num, den in (("ev_ebitda", ev, p.get("ebitda")), ("ev_revenue", ev, p.get("revenue")), ("pe", p.get("price"), p.get("eps"))):
            if num is not None and den not in (None, "", 0, "0"):
                d = _n(den, f"peers[{i}].{m}")
                if d > 0:
                    v = Decimal(str(num)) / d
                    row[m] = float(v.quantize(Decimal("0.01")))
                    mult[m].append(v)
        peers.append(row)
    stats = {m: {"median": float(Decimal(statistics.median(v)).quantize(Decimal("0.01"))),
                 "mean": float((sum(v, ZERO) / len(v)).quantize(Decimal("0.01"))), "low": float(min(v).quantize(Decimal("0.01"))),
                 "high": float(max(v).quantize(Decimal("0.01"))), "peers": len(v)} for m, v in mult.items()}
    implied = {}
    t = a.get("target") or {}
    for m, base in (("ev_ebitda", t.get("ebitda")), ("ev_revenue", t.get("revenue")), ("pe", t.get("eps"))):
        if base is not None and m in stats:
            b = _n(base, f"target.{m}")
            implied[m] = {k: money(Decimal(str(stats[m][k])) * b) for k in ("low", "median", "high")}
    return {"peers": peers, "multiples": stats, "implied_for_target": implied,
            "says": "Multiples describe the peers you chose; they are not a valuation opinion."}


def _iban_ok(s: str) -> bool:
    s = re.sub(r"\s", "", s).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", s):
        return False
    n = "".join(str(int(c, 36)) for c in s[4:] + s[:4])
    return int(n) % 97 == 1


def ssi(a: dict[str, Any]) -> dict[str, Any]:
    seen: dict[tuple, dict] = {}
    out = []
    for i, r in enumerate(_rows(a, "instructions")):
        prob = []
        for f in ("counterparty", "currency", "bic", "account"):
            if not str(r.get(f) or "").strip():
                prob.append(f"{f} missing")
        bic = str(r.get("bic") or "").upper()
        if bic and not re.fullmatch(r"[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?", bic):
            prob.append("BIC is not 8 or 11 characters of the right shape")
        if r.get("iban") and not _iban_ok(str(r["iban"])):
            prob.append("IBAN check digits do not match")
        key = (str(r.get("counterparty") or "").upper(), str(r.get("currency") or "").upper())
        if key in seen and (seen[key].get("account"), seen[key].get("bic")) != (r.get("account"), r.get("bic")):
            prob.append(f"a different instruction for {key[0]} {key[1]} is already on file: confirm by a call-back on a known number")
        seen.setdefault(key, r)
        out.append({"row": i, "counterparty": r.get("counterparty"), "currency": r.get("currency"), "problems": prob, "ok": not prob})
    return {"instructions": out, "problems": sum(len(x["problems"]) for x in out)}


def calendar(a: dict[str, Any]) -> dict[str, Any]:
    rules = a.get("rules") or []
    if not rules:
        raise MarketsError("rules: [{name, days_after, period quarter|half|year}] - from your exchange's rulebook.")
    ends = [_d(x, "period_ends") for x in a.get("period_ends") or []]
    if not ends:
        raise MarketsError("period_ends: the dates your periods end.")
    out = []
    for e in ends:
        for r in rules:
            out.append({"period_end": e.isoformat(), "what": r.get("name"),
                        "due": (e + timedelta(days=int(_n(r.get("days_after"), "rules.days_after", 0)))).isoformat()})
    out.sort(key=lambda x: x["due"])
    return {"calendar": out, "from": "your rules"}


ACTIONS = ("recon", "confirm", "fails", "corp_action", "reclaim", "margin", "best_ex", "comps", "ssi", "calendar")
_ORDERISH = re.compile(r"order|execute|place|buy|sell|cancel|allocat|affirm|instruct|submit|send|transfer|pay|release|book_trade|route")


def run(tenant: str, action: str, a: dict[str, Any], actor: str = "owner") -> dict[str, Any]:
    a = dict(a)
    if _ORDERISH.search(str(action).lower()):
        raise L.Refused("place_order", NEVER)
    if action not in ACTIONS:
        raise MarketsError("action: " + ", ".join(ACTIONS))
    out = globals()[action](a)
    out.setdefault("not_advice", L.NOT_ADVICE)
    return out
