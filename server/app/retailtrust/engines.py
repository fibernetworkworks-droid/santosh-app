"""#55 fraud rule hits, return abuse, #58 dark-pattern audit, #57 grievance clock, #67 review authenticity, #52 seller KYC checks, #100 label check,
#59 delivery-promise audit, #102 override rates, price fairness."""
from __future__ import annotations

import datetime as dt
import re
from collections import Counter, defaultdict
from typing import Any


def _f(v: Any) -> float:
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _dt(v: Any) -> dt.datetime:
    s = str(v or "").strip().replace("Z", "")
    for f in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return dt.datetime.strptime(s[:19], f)
        except ValueError:
            pass
    raise ValueError(f"Could not understand the time: '{v}' (2026-11-05 or 2026-11-05T10:00:00).")


def fraud_flags(orders: list[dict], max_per_customer: Any = 5, window_hours: Any = 24, shared_address_accounts: Any = 3, high_value: Any = None) -> dict[str, Any]:
    if not orders:
        raise ValueError("Give the orders rows: id, customer, ts, amount, address, device, cod.")
    w = dt.timedelta(hours=_f(window_hours))
    by, addr, dev = defaultdict(list), defaultdict(set), defaultdict(set)
    for o in orders[:50000]:
        by[str(o.get("customer"))].append(_dt(o.get("ts")))
        if o.get("address"):
            addr[re.sub(r"\W+", " ", str(o["address"]).lower()).strip()].add(str(o.get("customer")))
        if o.get("device"):
            dev[str(o["device"])].add(str(o.get("customer")))
    hits = []
    for c, ts in by.items():
        ts.sort()
        i, best = 0, 0
        for j in range(len(ts)):
            while ts[j] - ts[i] > w:
                i += 1
            best = max(best, j - i + 1)
        if best > _f(max_per_customer):
            hits.append({"rule": "order_velocity", "customer": c, "count": best, "window_hours": _f(window_hours)})
    for a, cs in addr.items():
        if len(cs) >= int(_f(shared_address_accounts)):
            hits.append({"rule": "shared_address", "address": a[:60], "accounts": sorted(cs)})
    for d, cs in dev.items():
        if len(cs) >= int(_f(shared_address_accounts)):
            hits.append({"rule": "shared_device", "device": d, "accounts": sorted(cs)})
    if high_value is not None:
        for o in orders:
            if _f(o.get("amount")) >= _f(high_value) and o.get("cod") in (True, "true", "yes", 1, "1"):
                hits.append({"rule": "high_value_cod", "order": o.get("id"), "amount": _f(o.get("amount"))})
    return {"rule_hits": hits, "kind": "rule hit, not a verdict", "not_checked": "The customer's real history, the payment-gateway risk score, identity.",
            "decider": "Holding / releasing an order or acting on an account is the risk investigator's decision; nothing was held here."}


def return_abuse(customers: list[dict], min_orders: Any = 5, max_return_rate_pct: Any = 40) -> dict[str, Any]:
    if not customers:
        raise ValueError("Give the customers rows: id, orders, returns, refund_value.")
    out = []
    for c in customers[:20000]:
        n, r = _f(c.get("orders")), _f(c.get("returns"))
        if n >= _f(min_orders) and r / n * 100 > _f(max_return_rate_pct):
            out.append({"customer": c.get("id"), "orders": n, "returns": r, "return_rate_pct": round(100 * r / n, 1), "refund_value": _f(c.get("refund_value"))})
    return {"above_threshold": sorted(out, key=lambda x: -x["return_rate_pct"]), "min_orders": _f(min_orders),
            "kind": "pattern flag - many genuine customers (because of size / quality) also land here",
            "decider": "Changing the policy or restricting anyone is the returns manager's decision, with a route to appeal."}


_DARK = [(r"\b(only|just|hurry)\b.{0,12}\b(\d+)\s*(left|minutes?|mins?|hours?)\b", "urgency / scarcity - must be true"),
         (r"\b(\d+\s*(people|persons|users)\s*(are\s*)?(viewing|watching|bought))\b", "social-proof counter - only from real data"),
         (r"\b(pre[- ]?(ticked|selected|checked))\b", "pre-ticked add-on"), (r"\b(no thanks,? i (don'?t|do not) want|i prefer to pay more)\b", "confirm-shaming"),
         (r"\b(convenience|handling|platform|processing) fee\b.{0,20}\b(at|on) (the )?(last|final|payment)\b", "drip pricing (fee late)"),
         (r"\b(cancel|unsubscribe)\b.{0,30}\b(call|email|visit)\b", "cancel harder than sign-up"), (r"\b(limited time|offer ends|sale ends)\b", "timer - only if it is real")]


def dark_patterns(flow_text: str, checks: dict | None = None) -> dict[str, Any]:
    t = str(flow_text or "")
    if not t.strip() and not checks:
        raise ValueError("Give flow_text (screens / copy) or checks {key: true/false}.")
    hits = [{"pattern": why, "words": m.group(0)} for pat, why in _DARK for m in re.finditer(pat, t, re.I)]
    asks = {"price_shown_up_front": "Is the total price shown up front?", "addons_off_by_default": "Are add-ons off by default?", "cancel_as_easy_as_signup": "Is cancelling as easy as signing up?",
            "timer_is_real": "Is the timer / 'only N left' from real data?", "reasons_for_ranking_shown": "Is the sponsored / ranking tag shown?"}
    fails = [q for k, q in asks.items() if checks and checks.get(k) is False]
    return {"text_hits": hits, "checklist_failed": fails, "kind": "word list + checklist, not a legal opinion",
            "note": "Judging a dark pattern depends on the law (CCPA guidelines, verify) and the context.", "decider": "Product and legal/compliance decide."}


def grievance_clock(complaints: list[dict], today: Any = None, ack_hours: Any = 48, resolve_days: Any = 30) -> dict[str, Any]:
    if not complaints:
        raise ValueError("Give the complaints rows: id, received, acknowledged, resolved.")
    now = _dt(today) if today else dt.datetime.utcnow()
    out = []
    for c in complaints[:5000]:
        rec = _dt(c.get("received"))
        ack = _dt(c["acknowledged"]) if c.get("acknowledged") else None
        res = _dt(c["resolved"]) if c.get("resolved") else None
        issues = []
        if (ack or now) - rec > dt.timedelta(hours=_f(ack_hours)):
            issues.append("acknowledgement deadline passed" if not ack else "acknowledged late")
        if (res or now) - rec > dt.timedelta(days=_f(resolve_days)):
            issues.append("resolution deadline passed" if not res else "resolved late")
        out.append({"id": c.get("id"), "open": res is None, "issues": issues})
    return {"complaints": out, "late": sum(bool(o["issues"]) for o in out), "open": sum(o["open"] for o in out), "verify": True,
            "note": f"The time limits ({_f(ack_hours):g} hours / {_f(resolve_days):g} days) are the E-Commerce Rules from memory: check them against your own rules and change them if needed.",
            "decider": "The reply and the decision are the grievance officer's."}


def reviews(items: list[dict], burst_per_day: Any = 5) -> dict[str, Any]:
    if not items:
        raise ValueError("Give the items rows: id, user, text, rating, date, verified, incentivised, disclosed.")
    txt = Counter(re.sub(r"\W+", " ", str(i.get("text") or "").lower()).strip() for i in items)
    day5 = Counter(str(i.get("date"))[:10] for i in items if _f(i.get("rating")) >= 5)
    flags = []
    for i in items[:20000]:
        why = []
        t = re.sub(r"\W+", " ", str(i.get("text") or "").lower()).strip()
        if t and txt[t] > 1:
            why.append("same text in several reviews")
        if day5[str(i.get("date"))[:10]] > _f(burst_per_day) and _f(i.get("rating")) >= 5:
            why.append("many 5-star reviews in one day")
        if i.get("verified") in (False, "false", "no", 0, "0"):
            why.append("not a verified buyer")
        if i.get("incentivised") in (True, "true", "yes", 1, "1") and i.get("disclosed") in (False, "false", "no", 0, "0", None):
            why.append("incentive received but not disclosed")
        if why:
            flags.append({"id": i.get("id"), "user": i.get("user"), "why": why})
    return {"flagged": flags, "total": len(items), "kind": "signal, not proof", "decider": "Removing a review is the moderator's decision (with an appeal); nothing was removed here."}


def _gstin_ok(g: str) -> tuple[bool, str]:
    g = g.strip().upper()
    if not re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]", g):
        return False, "wrong format"
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    s = 0
    for i, ch in enumerate(g[:14]):
        v = chars.index(ch) * (1 if i % 2 == 0 else 2)
        s += v // 36 + v % 36
    return (chars[(36 - s % 36) % 36] == g[14]), ("ok" if chars[(36 - s % 36) % 36] == g[14] else "wrong check digit")


def seller_kyc(seller: dict) -> dict[str, Any]:
    if not isinstance(seller, dict) or not seller:
        raise ValueError("Give the seller details: name, gstin, pan, bank_account_name, bank_ifsc, address, category.")
    g, pan = str(seller.get("gstin") or "").strip().upper(), str(seller.get("pan") or "").strip().upper()
    checks = []
    if g:
        ok, why = _gstin_ok(g)
        checks.append({"check": "GSTIN", "ok": ok, "detail": why})
        if pan:
            checks.append({"check": "PAN inside GSTIN", "ok": g[2:12] == pan, "detail": "The middle 10 characters of a GSTIN are the PAN"})
    if pan:
        checks.append({"check": "PAN format", "ok": bool(re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", pan)), "detail": ""})
    ifsc = str(seller.get("bank_ifsc") or "").strip().upper()
    if ifsc:
        checks.append({"check": "IFSC format", "ok": bool(re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", ifsc)), "detail": ""})
    bn, nm = re.sub(r"\W+", "", str(seller.get("bank_account_name") or "").lower()), re.sub(r"\W+", "", str(seller.get("name") or "").lower())
    if bn and nm:
        checks.append({"check": "bank name ~ seller name", "ok": bn in nm or nm in bn, "detail": "The names may differ (firm vs owner): for the trust team to look at"})
    missing = [k for k in ("name", "gstin", "pan", "bank_account_name", "bank_ifsc", "address", "category") if not seller.get(k)]
    return {"checks": checks, "missing_documents": missing, "failed": [c["check"] for c in checks if not c["ok"]],
            "not_checked": "Whether the GSTIN/PAN exist in the real registry, the bank penny-drop, whether the documents are genuine.", "decider": "Approving / rejecting a seller is the trust team's decision."}


_LM = {"name": "product name / common name", "net_quantity": "net quantity", "mrp": "MRP (inclusive of all taxes)", "manufacturer": "address of the manufacturer / packer / importer",
       "month_year": "month and year of manufacture / packing", "consumer_care": "consumer care number / email", "country_of_origin": "country of origin (for imports)"}


def label_check(label: dict) -> dict[str, Any]:
    if not isinstance(label, dict) or not label:
        raise ValueError("Give label {name, net_quantity, mrp, manufacturer, month_year, consumer_care, country_of_origin}.")
    missing = [v for k, v in _LM.items() if not label.get(k)]
    return {"missing": missing, "present": [v for k, v in _LM.items() if label.get(k)], "verify": True,
            "note": "The list of Legal Metrology declarations for packaged goods is from memory: check it against your category's rules (food: FSSAI is separate) and the latest amendment.",
            "decider": "Approving the label is the packaging/compliance team's decision."}


def promise_audit(deliveries: list[dict]) -> dict[str, Any]:
    if not deliveries:
        raise ValueError("Give the deliveries rows: id, promised_days, actual_days.")
    errs = sorted(_f(d.get("actual_days")) - _f(d.get("promised_days")) for d in deliveries)
    n = len(errs)
    late = sum(e > 0 for e in errs)
    p90 = errs[min(n - 1, int(0.9 * n))]
    return {"orders": n, "on_time_pct": round(100 * (n - late) / n, 1), "mean_error_days": round(sum(errs) / n, 2), "p90_error_days": p90,
            "honest_promise_hint": f"90% of orders are within {p90:+g} days: promise only what you can keep 90% of the time.", "decider": "The ETA/slot rule is the ops head's decision."}


def override_rate(decisions: list[dict], alert_pct: Any = 30) -> dict[str, Any]:
    if not decisions:
        raise ValueError("Give the decisions rows: model, ai_decision, human_decision.")
    by = defaultdict(lambda: [0, 0])
    for d in decisions[:100000]:
        by[str(d.get("model"))][0] += 1
        by[str(d.get("model"))][1] += str(d.get("ai_decision")) != str(d.get("human_decision"))
    rows = [{"model": m, "decisions": n, "overridden": o, "override_pct": round(100 * o / n, 1), "alert": 100 * o / n > _f(alert_pct)} for m, (n, o) in by.items()]
    return {"models": sorted(rows, key=lambda r: -r["override_pct"]), "reading": "Many overrides = the model is not trusted or the rule changed; few overrides = people may be accepting it without looking.",
            "decider": "AI governance committee."}


def price_fairness(quotes: list[dict], max_spread_pct: Any = 5) -> dict[str, Any]:
    if not quotes:
        raise ValueError("Give the quotes rows: product, segment, price.")
    by = defaultdict(dict)
    for q in quotes[:50000]:
        by[str(q.get("product"))].setdefault(str(q.get("segment")), []).append(_f(q.get("price")))
    out = []
    for p, segs in by.items():
        avg = {s: sum(v) / len(v) for s, v in segs.items()}
        lo, hi = min(avg.values()), max(avg.values())
        spread = 100 * (hi - lo) / lo if lo else 0
        out.append({"product": p, "segment_avg": {k: round(v, 2) for k, v in avg.items()}, "spread_pct": round(spread, 1), "review": spread > _f(max_spread_pct) and len(avg) > 1})
    return {"products": out, "note": "Price difference by segment (device, city, new/old customer); the cause (delivery cost, tax) may be something else.",
            "decider": "The pricing and compliance teams decide."}
