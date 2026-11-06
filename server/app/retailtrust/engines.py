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
    raise ValueError(f"Samay samajh nahi aaya: '{v}' (2026-11-05 ya 2026-11-05T10:00:00).")


def fraud_flags(orders: list[dict], max_per_customer: Any = 5, window_hours: Any = 24, shared_address_accounts: Any = 3, high_value: Any = None) -> dict[str, Any]:
    if not orders:
        raise ValueError("orders rows do: id, customer, ts, amount, address, device, cod.")
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
    return {"rule_hits": hits, "kind": "rule hit, not a verdict", "not_checked": "Customer ka asli itihaas, payment-gateway risk score, identity.",
            "decider": "Order roko / chhodo ya account par karwai risk investigator karta hai; yahan kuch roka nahi gaya."}


def return_abuse(customers: list[dict], min_orders: Any = 5, max_return_rate_pct: Any = 40) -> dict[str, Any]:
    if not customers:
        raise ValueError("customers rows do: id, orders, returns, refund_value.")
    out = []
    for c in customers[:20000]:
        n, r = _f(c.get("orders")), _f(c.get("returns"))
        if n >= _f(min_orders) and r / n * 100 > _f(max_return_rate_pct):
            out.append({"customer": c.get("id"), "orders": n, "returns": r, "return_rate_pct": round(100 * r / n, 1), "refund_value": _f(c.get("refund_value"))})
    return {"above_threshold": sorted(out, key=lambda x: -x["return_rate_pct"]), "min_orders": _f(min_orders),
            "kind": "pattern flag - bahut se asli customers (size / quality ki wajah se) bhi yahan aate hain",
            "decider": "Policy badalna ya kisi par rok lagana returns manager tay karta hai, appeal ke raaste ke saath."}


_DARK = [(r"\b(only|just|hurry)\b.{0,12}\b(\d+)\s*(left|minutes?|mins?|hours?)\b", "urgency / scarcity - sach hona chahiye"),
         (r"\b(\d+\s*(people|persons|users)\s*(are\s*)?(viewing|watching|bought))\b", "social-proof counter - asli data se hi"),
         (r"\b(pre[- ]?(ticked|selected|checked))\b", "pre-ticked add-on"), (r"\b(no thanks,? i (don'?t|do not) want|i prefer to pay more)\b", "confirm-shaming"),
         (r"\b(convenience|handling|platform|processing) fee\b.{0,20}\b(at|on) (the )?(last|final|payment)\b", "drip pricing (fee late)"),
         (r"\b(cancel|unsubscribe)\b.{0,30}\b(call|email|visit)\b", "cancel harder than sign-up"), (r"\b(limited time|offer ends|sale ends)\b", "timer - asli ho to hi")]


def dark_patterns(flow_text: str, checks: dict | None = None) -> dict[str, Any]:
    t = str(flow_text or "")
    if not t.strip() and not checks:
        raise ValueError("flow_text (screens / copy) ya checks {key: true/false} do.")
    hits = [{"pattern": why, "words": m.group(0)} for pat, why in _DARK for m in re.finditer(pat, t, re.I)]
    asks = {"price_shown_up_front": "Kul keemat shuru mein dikhti hai?", "addons_off_by_default": "Add-on default band hain?", "cancel_as_easy_as_signup": "Cancel utna hi aasaan?",
            "timer_is_real": "Timer / 'sirf N bache' asli data se?", "reasons_for_ranking_shown": "Sponsored / ranking ka tag dikhta hai?"}
    fails = [q for k, q in asks.items() if checks and checks.get(k) is False]
    return {"text_hits": hits, "checklist_failed": fails, "kind": "shabd-suchi + checklist, kaanooni raay nahi",
            "note": "Dark-pattern ki parakh kaanoon (CCPA guidelines, verify) aur sandarbh par nirbhar hai.", "decider": "Product aur legal/compliance tay karte hain."}


def grievance_clock(complaints: list[dict], today: Any = None, ack_hours: Any = 48, resolve_days: Any = 30) -> dict[str, Any]:
    if not complaints:
        raise ValueError("complaints rows do: id, received, acknowledged, resolved.")
    now = _dt(today) if today else dt.datetime.utcnow()
    out = []
    for c in complaints[:5000]:
        rec = _dt(c.get("received"))
        ack = _dt(c["acknowledged"]) if c.get("acknowledged") else None
        res = _dt(c["resolved"]) if c.get("resolved") else None
        issues = []
        if (ack or now) - rec > dt.timedelta(hours=_f(ack_hours)):
            issues.append("acknowledge deadline nikal gayi" if not ack else "acknowledge der se hua")
        if (res or now) - rec > dt.timedelta(days=_f(resolve_days)):
            issues.append("resolution deadline nikal gayi" if not res else "resolve der se hua")
        out.append({"id": c.get("id"), "open": res is None, "issues": issues})
    return {"complaints": out, "late": sum(bool(o["issues"]) for o in out), "open": sum(o["open"] for o in out), "verify": True,
            "note": f"Samay-seema ({_f(ack_hours):g} ghante / {_f(resolve_days):g} din) E-Commerce Rules ke yaad se hain: apne niyam se milaiye aur zaroorat ho to badliye.",
            "decider": "Jawab aur faisla grievance officer ka hai."}


def reviews(items: list[dict], burst_per_day: Any = 5) -> dict[str, Any]:
    if not items:
        raise ValueError("items rows do: id, user, text, rating, date, verified, incentivised, disclosed.")
    txt = Counter(re.sub(r"\W+", " ", str(i.get("text") or "").lower()).strip() for i in items)
    day5 = Counter(str(i.get("date"))[:10] for i in items if _f(i.get("rating")) >= 5)
    flags = []
    for i in items[:20000]:
        why = []
        t = re.sub(r"\W+", " ", str(i.get("text") or "").lower()).strip()
        if t and txt[t] > 1:
            why.append("same text kai reviews mein")
        if day5[str(i.get("date"))[:10]] > _f(burst_per_day) and _f(i.get("rating")) >= 5:
            why.append("ek din mein bahut 5-star")
        if i.get("verified") in (False, "false", "no", 0, "0"):
            why.append("verified buyer nahi")
        if i.get("incentivised") in (True, "true", "yes", 1, "1") and i.get("disclosed") in (False, "false", "no", 0, "0", None):
            why.append("inaam mila par bataya nahi")
        if why:
            flags.append({"id": i.get("id"), "user": i.get("user"), "why": why})
    return {"flagged": flags, "total": len(items), "kind": "signal, not proof", "decider": "Review hatana moderator ka faisla hai (appeal ke saath); yahan kuch hataya nahi gaya."}


def _gstin_ok(g: str) -> tuple[bool, str]:
    g = g.strip().upper()
    if not re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]", g):
        return False, "format galat"
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    s = 0
    for i, ch in enumerate(g[:14]):
        v = chars.index(ch) * (1 if i % 2 == 0 else 2)
        s += v // 36 + v % 36
    return (chars[(36 - s % 36) % 36] == g[14]), ("ok" if chars[(36 - s % 36) % 36] == g[14] else "check-digit galat")


def seller_kyc(seller: dict) -> dict[str, Any]:
    if not isinstance(seller, dict) or not seller:
        raise ValueError("seller details do: name, gstin, pan, bank_account_name, bank_ifsc, address, category.")
    g, pan = str(seller.get("gstin") or "").strip().upper(), str(seller.get("pan") or "").strip().upper()
    checks = []
    if g:
        ok, why = _gstin_ok(g)
        checks.append({"check": "GSTIN", "ok": ok, "detail": why})
        if pan:
            checks.append({"check": "PAN GSTIN mein", "ok": g[2:12] == pan, "detail": "GSTIN ke beech ke 10 akshar PAN hote hain"})
    if pan:
        checks.append({"check": "PAN format", "ok": bool(re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", pan)), "detail": ""})
    ifsc = str(seller.get("bank_ifsc") or "").strip().upper()
    if ifsc:
        checks.append({"check": "IFSC format", "ok": bool(re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", ifsc)), "detail": ""})
    bn, nm = re.sub(r"\W+", "", str(seller.get("bank_account_name") or "").lower()), re.sub(r"\W+", "", str(seller.get("name") or "").lower())
    if bn and nm:
        checks.append({"check": "bank naam ~ seller naam", "ok": bn in nm or nm in bn, "detail": "Naam alag ho sakta hai (firm vs malik): trust team dekhe"})
    missing = [k for k in ("name", "gstin", "pan", "bank_account_name", "bank_ifsc", "address", "category") if not seller.get(k)]
    return {"checks": checks, "missing_documents": missing, "failed": [c["check"] for c in checks if not c["ok"]],
            "not_checked": "GSTIN/PAN ki asli registry mein maujoodgi, bank ka penny-drop, documents ki asliyat.", "decider": "Seller manzoor/namanzoor trust team karti hai."}


_LM = {"name": "product ka naam / common name", "net_quantity": "net maatra", "mrp": "MRP (sabhi karon ke saath)", "manufacturer": "nirmaata / packer / importer ka pata",
       "month_year": "banane / pack karne ka mahina-saal", "consumer_care": "consumer care ka number / email", "country_of_origin": "country of origin (import par)"}


def label_check(label: dict) -> dict[str, Any]:
    if not isinstance(label, dict) or not label:
        raise ValueError("label {name, net_quantity, mrp, manufacturer, month_year, consumer_care, country_of_origin} do.")
    missing = [v for k, v in _LM.items() if not label.get(k)]
    return {"missing": missing, "present": [v for k, v in _LM.items() if label.get(k)], "verify": True,
            "note": "Packaged saaman ke Legal Metrology declarations ki suchi yaad se hai: apni category ke niyam (food: FSSAI alag) aur taaza amendment se milaiye.",
            "decider": "Label ki manzoori packaging/compliance team ki hai."}


def promise_audit(deliveries: list[dict]) -> dict[str, Any]:
    if not deliveries:
        raise ValueError("deliveries rows do: id, promised_days, actual_days.")
    errs = sorted(_f(d.get("actual_days")) - _f(d.get("promised_days")) for d in deliveries)
    n = len(errs)
    late = sum(e > 0 for e in errs)
    p90 = errs[min(n - 1, int(0.9 * n))]
    return {"orders": n, "on_time_pct": round(100 * (n - late) / n, 1), "mean_error_days": round(sum(errs) / n, 2), "p90_error_days": p90,
            "honest_promise_hint": f"90% order {p90:+g} din ke andar: wada utna hi rakhiye jitna 90% par nibha sakein.", "decider": "ETA/slot ka niyam ops head tay karta hai."}


def override_rate(decisions: list[dict], alert_pct: Any = 30) -> dict[str, Any]:
    if not decisions:
        raise ValueError("decisions rows do: model, ai_decision, human_decision.")
    by = defaultdict(lambda: [0, 0])
    for d in decisions[:100000]:
        by[str(d.get("model"))][0] += 1
        by[str(d.get("model"))][1] += str(d.get("ai_decision")) != str(d.get("human_decision"))
    rows = [{"model": m, "decisions": n, "overridden": o, "override_pct": round(100 * o / n, 1), "alert": 100 * o / n > _f(alert_pct)} for m, (n, o) in by.items()]
    return {"models": sorted(rows, key=lambda r: -r["override_pct"]), "reading": "Zyada override = model bharose ka nahi ya niyam badla; kam override = log bina dekhe maan rahe ho sakte hain.",
            "decider": "AI governance committee."}


def price_fairness(quotes: list[dict], max_spread_pct: Any = 5) -> dict[str, Any]:
    if not quotes:
        raise ValueError("quotes rows do: product, segment, price.")
    by = defaultdict(dict)
    for q in quotes[:50000]:
        by[str(q.get("product"))].setdefault(str(q.get("segment")), []).append(_f(q.get("price")))
    out = []
    for p, segs in by.items():
        avg = {s: sum(v) / len(v) for s, v in segs.items()}
        lo, hi = min(avg.values()), max(avg.values())
        spread = 100 * (hi - lo) / lo if lo else 0
        out.append({"product": p, "segment_avg": {k: round(v, 2) for k, v in avg.items()}, "spread_pct": round(spread, 1), "review": spread > _f(max_spread_pct) and len(avg) > 1})
    return {"products": out, "note": "Segment (device, shahar, naya/purana customer) ke hisaab se bhaav ka antar; kaaran (delivery cost, tax) alag ho sakta hai.",
            "decider": "Pricing aur compliance team tay karte hain."}
