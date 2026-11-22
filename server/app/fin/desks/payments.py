"""F8 of docs/FINANCE_GLOBAL_PLAN.md - Payments (employee `payments`, tool `payments_desk`), for a shop up to a payment firm, any country.

Merchant:
  dispute      a chargeback read: its network (visa | mastercard | amex), reason code -> what kind of dispute it is, the evidence that
               answers it, what she has and what is missing, her response deadline (from HER processor's window), and the
               representment pack: the cover letter and the evidence index. For card-absent fraud on Visa (10.4) the compelling-evidence
               test on her earlier transactions with the same customer is worked out. Reason-code tables are from memory (not confirmed)
               until her processor's guide is checked; Hoola never submits the response.
  prevention   disputes against sales per month and per network, against the monitoring thresholds SHE gives.
  reconcile    orders vs each gateway's settlement lines vs her bank deposits, for several gateways at once: matched, missing,
               mismatched, payouts with no deposit, deposits with no payout, fees and the effective rate per gateway.
  fee_audit    each gateway's fees against the rate in her contract (percent + fixed per transaction).
  dunning      failed recurring payments: the retry plan from her rules and the customer messages; Hoola never charges.
  payouts      marketplace sellers: sales, refunds, her commission and fees -> what each seller is owed; Hoola never pays.
  export       export invoices in other currencies against money received: what is outstanding and the date it must arrive by (her rule).

Payment firm:
  kyb          a business onboarding file: the documents present / missing and the beneficial owners worked out through the ownership
               chain (direct and indirect shares) against HER threshold.
  merchant_risk refund and dispute rates, volume against its own baseline, her high-risk categories.
  safeguarding what the firm owes its customers against what sits in the safeguarding accounts, day by day: shortfalls named.
  iso20022     a pain.001 / pacs.008 message checked: well formed, the parts a bank needs, IBAN check digits, BIC shape, the count and the
               control sum.
  exceptions   payments that were returned, rejected or not matched, by age.
  returns      the figures a licensing return asks for, counted from her own transactions by type and period.

Not legal or scheme advice."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .. import laws as L


class PaymentsError(ValueError):
    pass


NOT_CONFIRMED = " (not confirmed - check this)"
NEVER = "Hoola never submits, charges or pays: you (or your processor) do."

# reason codes - from memory, status verify, until her processor's dispute guide is checked
EVIDENCE = {
    "proof_of_delivery": "proof the goods were delivered (carrier confirmation, tracking showing delivered)",
    "delivery_address_match": "the delivery address matches the billing / account address",
    "signature": "a signed delivery receipt",
    "avs_cvv_match": "address and security-code checks matched at payment",
    "three_ds": "the payment was authenticated (3-D Secure)",
    "prior_transactions": "earlier undisputed payments by the same customer (compelling evidence)",
    "customer_communication": "messages with the customer about this order",
    "description": "what was sold, as described to the customer at the time",
    "terms_accepted": "the customer accepted the terms / refund policy at checkout",
    "usage_logs": "the customer used the service (log-ins, downloads) after paying",
    "refund_issued": "proof a refund or credit was already given",
    "two_separate_sales": "proof the two charges were two separate sales",
    "authorization": "the payment was authorized (approval code)",
    "cancellation_policy": "the cancellation policy and that the customer did not cancel within it",
}
REASONS: dict[str, dict[str, dict[str, Any]]] = {
    "visa": {
        "10.4": {"name": "Other fraud - card absent", "kind": "fraud",
                 "need": ["avs_cvv_match", "three_ds", "prior_transactions", "proof_of_delivery", "delivery_address_match", "usage_logs"],
                 "min": 2},
        "13.1": {"name": "Merchandise / services not received", "kind": "consumer",
                 "need": ["proof_of_delivery", "signature", "customer_communication", "usage_logs"], "min": 1},
        "13.3": {"name": "Not as described or defective", "kind": "consumer",
                 "need": ["description", "customer_communication", "terms_accepted"], "min": 2},
        "12.6.1": {"name": "Duplicate processing", "kind": "processing", "need": ["two_separate_sales", "refund_issued"], "min": 1},
        "13.6": {"name": "Credit not processed", "kind": "consumer", "need": ["refund_issued", "terms_accepted", "cancellation_policy"],
                 "min": 1},
        "11.3": {"name": "No authorization", "kind": "authorization", "need": ["authorization"], "min": 1},
    },
    "mastercard": {
        "4837": {"name": "No cardholder authorization", "kind": "fraud",
                 "need": ["three_ds", "avs_cvv_match", "proof_of_delivery", "delivery_address_match", "prior_transactions"], "min": 2},
        "4855": {"name": "Goods or services not provided", "kind": "consumer",
                 "need": ["proof_of_delivery", "signature", "usage_logs", "customer_communication"], "min": 1},
        "4853": {"name": "Cardholder dispute (not as described / defective)", "kind": "consumer",
                 "need": ["description", "customer_communication", "terms_accepted"], "min": 2},
        "4834": {"name": "Point-of-interaction error (duplicate)", "kind": "processing", "need": ["two_separate_sales", "refund_issued"],
                 "min": 1},
        "4808": {"name": "Authorization-related", "kind": "authorization", "need": ["authorization"], "min": 1},
    },
    "amex": {
        "F29": {"name": "Card not present fraud", "kind": "fraud",
                "need": ["avs_cvv_match", "three_ds", "proof_of_delivery", "delivery_address_match"], "min": 2},
        "C08": {"name": "Goods / services not received", "kind": "consumer", "need": ["proof_of_delivery", "signature", "usage_logs"],
                "min": 1},
        "C31": {"name": "Goods / services not as described", "kind": "consumer", "need": ["description", "customer_communication",
                                                                                         "terms_accepted"], "min": 2},
        "P08": {"name": "Duplicate charge", "kind": "processing", "need": ["two_separate_sales", "refund_issued"], "min": 1},
        "C02": {"name": "Credit not processed", "kind": "consumer", "need": ["refund_issued", "cancellation_policy"], "min": 1},
    },
}


def _f(v: Any, what: str, lo: float | None = None) -> float:
    try:
        x = float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        raise PaymentsError(f"{what}: a number.")
    if lo is not None and x < lo:
        raise PaymentsError(f"{what}: not below {lo}.")
    return x


def _m(v: Any, what: str) -> int:
    return int((Decimal(str(_f(v, what))) * 100).quantize(Decimal(1), ROUND_HALF_UP))


def _u(minor: int) -> float:
    return float(Decimal(int(minor)) / 100)


def _d(s: Any, what: str) -> date:
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        raise PaymentsError(f"{what}: a date as YYYY-MM-DD.")


# ---- disputes ----------------------------------------------------------------------------------------------------------------

def compelling(a: dict[str, Any]) -> dict[str, Any]:
    """Visa compelling evidence for card-absent fraud (the 3.0 shape, from memory): at least 2 earlier transactions by the same customer,
    120 to 365 days before the dispute, not disputed as fraud, each sharing at least 2 of IP address, device id, shipping address,
    account login with the disputed one - and at least one of the shared ones is the IP address or the device id."""
    dd = _d(a.get("dispute_date"), "dispute_date")
    cur = {k: str((a.get("disputed") or {}).get(k) or "").strip().lower() for k in ("ip", "device", "shipping", "account")}
    good, why = [], []
    for k, t in enumerate(a.get("prior") or []):
        days = (dd - _d(t.get("date"), f"prior[{k}].date")).days
        if not 120 <= days <= 365:
            why.append(f"prior {k + 1}: {days} days before the dispute (needs 120-365)")
            continue
        if t.get("disputed"):
            why.append(f"prior {k + 1}: it was itself disputed")
            continue
        same = [x for x in cur if cur[x] and str(t.get(x) or "").strip().lower() == cur[x]]
        if len(same) < 2 or not ({"ip", "device"} & set(same)):
            why.append(f"prior {k + 1}: shares {', '.join(same) or 'nothing'} (needs 2, one of them IP or device)")
            continue
        good.append({"prior": k + 1, "days_before": days, "shared": same})
    return {"qualifies": len(good) >= 2, "qualifying": good, "not_counted": why,
            "rule": "2+ earlier undisputed payments 120-365 days before, each sharing 2+ of IP / device / shipping / account, one of "
                    "them IP or device" + NOT_CONFIRMED}


def dispute(a: dict[str, Any]) -> dict[str, Any]:
    net = str(a.get("network") or "").lower()
    code = str(a.get("reason_code") or "").upper() if net == "amex" else str(a.get("reason_code") or "")
    if net not in REASONS:
        raise PaymentsError("network: visa | mastercard | amex.")
    rc = REASONS[net].get(code)
    if not rc:
        raise PaymentsError(f"reason_code: one of {', '.join(REASONS[net])} for {net} (others: give the processor's description).")
    have = {k for k, v in (a.get("evidence") or {}).items() if v}
    unknown = sorted(have - set(EVIDENCE))
    if unknown:
        raise PaymentsError("evidence keys: " + ", ".join(EVIDENCE))
    out: dict[str, Any] = {}
    if code == "10.4" and a.get("prior"):
        ce = compelling(a)
        out["compelling_evidence"] = ce
        if ce["qualifies"]:
            have.add("prior_transactions")
        else:
            have.discard("prior_transactions")
    got = [k for k in rc["need"] if k in have]
    missing = [k for k in rc["need"] if k not in have]
    if rc["kind"] == "processing" and "refund_issued" in have:
        verdict = "already refunded: answer with the refund proof"
    elif len(got) >= rc["min"]:
        verdict = "the evidence answers this reason code"
    else:
        verdict = f"too little evidence: {rc['min']} of these are usually needed, you have {len(got)}"
    dl = None
    if a.get("received") and a.get("window_days"):
        dl = (_d(a["received"], "received") + timedelta(days=int(_f(a["window_days"], "window_days", 1)))).isoformat()
    amount = _f(a.get("amount", 0), "amount", 0)
    idx = [f"{i + 1}. {EVIDENCE[k]}" for i, k in enumerate(got)]
    letter = "\n".join([
        f"Dispute response - {net.title()} reason code {code} ({rc['name']})",
        f"Transaction {a.get('transaction_id') or '[transaction id]'} of {a.get('transaction_date') or '[date]'}, amount {amount:,.2f} "
        f"{a.get('currency') or ''}".rstrip(),
        "", "We dispute this chargeback. The enclosed evidence shows:", *[f"- {EVIDENCE[k]}" for k in got],
        *(["- the customer's earlier undisputed payments with the same IP / device: " + ", ".join(
            f"#{g['prior']} ({g['days_before']} days before)" for g in out["compelling_evidence"]["qualifying"])]
          if out.get("compelling_evidence", {}).get("qualifies") else []),
        "", "Evidence index:", *idx, "", "[merchant name, contact]"])
    return {**out, "network": net, "reason_code": code, "reason": rc["name"], "kind": rc["kind"], "evidence_needed": rc["need"],
            "evidence_you_have": got, "evidence_missing": missing, "verdict": verdict,
            "respond_by": dl or "give received + window_days (your processor's response window)" + NOT_CONFIRMED,
            "letter": letter, "codes_from": "Hoola's table, from memory" + NOT_CONFIRMED, "says": NEVER}


def prevention(a: dict[str, Any]) -> dict[str, Any]:
    sales = defaultdict(int)
    disp = defaultdict(int)
    for r in a.get("sales") or []:
        sales[(str(r.get("month"))[:7], str(r.get("network") or "all").lower())] += int(_f(r.get("count"), "sales.count", 0))
    for r in a.get("disputes") or []:
        disp[(str(r.get("month") or r.get("date"))[:7], str(r.get("network") or "all").lower())] += int(_f(r.get("count", 1), "count", 0))
    thr = {str(k).lower(): _f(v, f"thresholds.{k}") for k, v in (a.get("thresholds") or {}).items()}
    rows = []
    for k in sorted(set(sales) | set(disp)):
        n, d = sales.get(k, 0), disp.get(k, 0)
        pct = round(d * 100 / n, 2) if n else None
        lim = thr.get(k[1])
        rows.append({"month": k[0], "network": k[1], "sales": n, "disputes": d, "dispute_pct": pct,
                     "over_your_threshold": (pct is not None and lim is not None and pct >= lim) or None})
    return {"months": rows, "over": [r for r in rows if r["over_your_threshold"]],
            "thresholds": thr or "none given: the networks' monitoring programmes have thresholds" + NOT_CONFIRMED}


# ---- reconciliation -----------------------------------------------------------------------------------------------------------

def reconcile(a: dict[str, Any]) -> dict[str, Any]:
    """orders [{id, gateway, amount}], settlements [{gateway, payout_id, payout_date, lines [{order_id, type sale|refund|chargeback|
    fee|adjustment, amount}]}], deposits [{id, date, amount, narration}], window_days."""
    win = int(_f(a.get("window_days", 5), "window_days", 0))
    orders = {str(o["id"]): {**o, "minor": _m(o.get("amount"), "orders.amount"), "gateway": str(o.get("gateway") or "").lower()}
              for o in a.get("orders") or []}
    sold: dict[str, int] = defaultdict(int)
    by_gw: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    payouts = []
    for p in a.get("settlements") or []:
        gw = str(p.get("gateway") or "").lower()
        net = 0
        for ln in p.get("lines") or []:
            t = ln.get("type") or "sale"
            if t not in ("sale", "refund", "chargeback", "fee", "adjustment"):
                raise PaymentsError("settlement line type: sale | refund | chargeback | fee | adjustment.")
            v = _m(ln.get("amount"), "lines.amount")
            v = abs(v) if t == "sale" else -abs(v) if t in ("refund", "chargeback", "fee") else v
            net += v
            by_gw[gw][t] += v
            if t == "sale":
                sold[str(ln.get("order_id"))] += v
        payouts.append({"gateway": gw, "payout_id": str(p.get("payout_id")), "date": _d(p.get("payout_date"), "payout_date"), "net": net})
    order_rows = {"matched": [], "missing_at_gateway": [], "amount_differs": [], "gateway_sale_without_order": []}
    for oid, o in orders.items():
        if oid not in sold:
            order_rows["missing_at_gateway"].append({"order": oid, "gateway": o["gateway"], "amount": _u(o["minor"])})
        elif sold[oid] != o["minor"]:
            order_rows["amount_differs"].append({"order": oid, "order_amount": _u(o["minor"]), "gateway_amount": _u(sold[oid])})
        else:
            order_rows["matched"].append(oid)
    order_rows["gateway_sale_without_order"] = sorted(k for k in sold if k not in orders)
    deps = [{"id": str(d.get("id") or f"d{i + 1}"), "date": _d(d.get("date"), "deposits.date"), "minor": _m(d.get("amount"), "deposits.amount"),
             "narration": str(d.get("narration") or "").lower()} for i, d in enumerate(a.get("deposits") or [])]
    used: set[str] = set()
    pay_rows = []
    for p in sorted(payouts, key=lambda x: (x["date"], x["payout_id"])):
        cands = [d for d in deps if d["id"] not in used and d["minor"] == p["net"] and p["date"] <= d["date"] <= p["date"] + timedelta(days=win)]
        cands.sort(key=lambda d: (p["gateway"] not in d["narration"], (d["date"] - p["date"]).days))
        if cands:
            used.add(cands[0]["id"])
            pay_rows.append({"payout": p["payout_id"], "gateway": p["gateway"], "net": _u(p["net"]), "deposit": cands[0]["id"],
                             "days": (cands[0]["date"] - p["date"]).days})
        else:
            pay_rows.append({"payout": p["payout_id"], "gateway": p["gateway"], "net": _u(p["net"]), "deposit": None})
    fees = {}
    for gw, t in by_gw.items():
        gross = t.get("sale", 0)
        fees[gw] = {"sales": _u(gross), "refunds": _u(-t.get("refund", 0)), "chargebacks": _u(-t.get("chargeback", 0)),
                    "fees": _u(-t.get("fee", 0)), "net": _u(sum(t.values())),
                    "effective_fee_pct": round(-t.get("fee", 0) * 100 / gross, 3) if gross else None}
    return {"orders": order_rows, "payouts": pay_rows, "payouts_without_deposit": [x["payout"] for x in pay_rows if not x["deposit"]],
            "deposits_without_payout": [d["id"] for d in deps if d["id"] not in used], "by_gateway": fees,
            "balanced": not (order_rows["missing_at_gateway"] or order_rows["amount_differs"] or order_rows["gateway_sale_without_order"]
                             or any(not x["deposit"] for x in pay_rows) or len(used) != len(deps))}


def fee_audit(a: dict[str, Any]) -> dict[str, Any]:
    rates = {str(k).lower(): v for k, v in (a.get("contract") or {}).items()}
    if not rates:
        raise PaymentsError("contract: {gateway: {pct, fixed}} - the rates in your agreement.")
    lines, over = [], 0
    for k, t in enumerate(a.get("transactions") or []):
        gw = str(t.get("gateway") or "").lower()
        if gw not in rates:
            raise PaymentsError(f"transactions[{k}]: no contract rate for {gw}.")
        amt = _m(t.get("amount"), "amount")
        want = int((Decimal(amt) * Decimal(str(rates[gw].get("pct", 0))) / 100).quantize(Decimal(1), ROUND_HALF_UP)) + _m(rates[gw].get("fixed", 0), "fixed")
        got = _m(t.get("fee"), "fee")
        if got > want:
            over += got - want
            lines.append({"id": t.get("id"), "gateway": gw, "amount": _u(amt), "charged": _u(got), "contract": _u(want), "over": _u(got - want)})
    return {"overcharged_lines": lines, "overcharged_total": _u(over), "checked": len(a.get("transactions") or []),
            "says": "Raise the lines with the gateway; the contract wording decides."}


def dunning(a: dict[str, Any]) -> dict[str, Any]:
    retry = [int(_f(x, "retry_days", 0)) for x in (a.get("retry_days") or [1, 3, 7])]
    out = []
    for f in a.get("failed") or []:
        d0 = _d(f.get("date"), "failed.date")
        steps = [{"retry_on": (d0 + timedelta(days=x)).isoformat(),
                  "message": f"Your payment of {f.get('amount')} for {f.get('plan') or 'your plan'} did not go through. Please update your "
                             "card on your account page; we will try again on this date."} for x in retry]
        out.append({"customer": f.get("customer"), "amount": f.get("amount"), "plan": steps,
                    "stop_after": (d0 + timedelta(days=max(retry) + 1)).isoformat(), "reason": f.get("reason")})
    return {"customers": out, "says": "Drafts and dates only. " + NEVER}


def payouts(a: dict[str, Any]) -> dict[str, Any]:
    pct = _f(a.get("commission_pct"), "commission_pct (your commission)", 0)
    sel: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in a.get("orders") or []:
        s = str(r.get("seller") or "")
        v = _m(r.get("amount"), "amount")
        kind = r.get("type") or "sale"
        sel[s][kind] += v
        sel[s]["fees"] += _m(r.get("fee", 0), "fee")
    out = []
    for s, t in sorted(sel.items()):
        sales, refunds = t.get("sale", 0), t.get("refund", 0)
        com = int((Decimal(sales - refunds) * Decimal(str(pct)) / 100).quantize(Decimal(1), ROUND_HALF_UP))
        owed = sales - refunds - com - t.get("fees", 0)
        out.append({"seller": s, "sales": _u(sales), "refunds": _u(refunds), "commission": _u(com), "fees": _u(t.get("fees", 0)),
                    "owed": _u(owed), "carry_forward": owed < 0})
    return {"sellers": out, "says": "A seller below zero is carried forward, not paid. " + NEVER}


def export(a: dict[str, Any]) -> dict[str, Any]:
    days = a.get("realise_within_days")
    today = _d(a.get("today") or date.today().isoformat(), "today")
    recv = defaultdict(int)
    for r in a.get("receipts") or []:
        recv[str(r.get("invoice"))] += _m(r.get("amount"), "receipts.amount")
    out = []
    for inv in a.get("invoices") or []:
        amt = _m(inv.get("amount"), "invoices.amount")
        left = amt - recv.get(str(inv.get("id")), 0)
        row = {"invoice": inv.get("id"), "currency": inv.get("currency"), "amount": _u(amt), "received": _u(recv.get(str(inv.get("id")), 0)),
               "outstanding": _u(max(0, left))}
        if days is not None and left > 0:
            due = _d(inv.get("date"), "invoices.date") + timedelta(days=int(_f(days, "realise_within_days", 1)))
            row.update({"must_arrive_by": due.isoformat(), "late": due < today})
        out.append(row)
    return {"invoices": out, "late": [r["invoice"] for r in out if r.get("late")],
            "rule": f"{days} days (your rule)" if days is not None else "give realise_within_days - the period your country allows" + NOT_CONFIRMED}


# ---- payment firm --------------------------------------------------------------------------------------------------------------

def kyb(a: dict[str, Any]) -> dict[str, Any]:
    thr = _f(a.get("threshold_pct"), "threshold_pct (your beneficial-owner threshold, e.g. 25)", 0)
    edges: dict[str, list[tuple[str, float]]] = defaultdict(list)
    people = set()
    for k, e in enumerate(a.get("ownership") or []):
        edges[str(e["owned"])].append((str(e["owner"]), _f(e.get("pct"), f"ownership[{k}].pct", 0) / 100))
        if e.get("person"):
            people.add(str(e["owner"]))
    root = str(a.get("business") or "")
    if not root:
        raise PaymentsError("business: the business being onboarded.")
    share: dict[str, float] = defaultdict(float)

    def walk(node: str, f: float, seen: tuple[str, ...]):
        for owner, p in edges.get(node, []):
            if owner in seen:
                raise PaymentsError(f"The ownership loops through {owner}.")
            if owner in people or owner not in edges:
                share[owner] += f * p
            else:
                walk(owner, f * p, seen + (owner,))
    walk(root, 1.0, (root,))
    bo = [{"owner": o, "pct": round(v * 100, 2), "person": o in people} for o, v in sorted(share.items(), key=lambda x: -x[1])]
    need = [str(x) for x in a.get("required_documents") or ["registration", "address proof", "directors list", "ownership chart",
                                                               "bank account proof", "id of each beneficial owner"]]
    have = {str(x).lower() for x in a.get("documents") or []}
    return {"beneficial_owners": [b for b in bo if b["pct"] >= thr], "all_end_owners": bo,
            "unknown_owners": [b["owner"] for b in bo if not b["person"]],
            "documents_missing": [d for d in need if d.lower() not in have], "threshold_pct": thr,
            "says": "Shares multiplied through the chain. An end owner that is not marked a person must be traced further. "
                    "The onboarding decision is the compliance officer's."}


def merchant_risk(a: dict[str, Any]) -> dict[str, Any]:
    hi = {str(x) for x in a.get("high_risk_mcc") or []}
    out = []
    for m in a.get("merchants") or []:
        vol = [_f(x, "volumes") for x in m.get("monthly_volume") or []]
        flags = []
        if m.get("mcc") and str(m["mcc"]) in hi:
            flags.append(f"category {m['mcc']} is on your high-risk list")
        if len(vol) >= 4:
            base = sum(vol[-4:-1]) / 3
            if base and vol[-1] > base * (1 + _f(a.get("spike_pct", 100), "spike_pct") / 100):
                flags.append(f"volume {vol[-1]:,.0f} vs {base:,.0f} average of the 3 months before")
        for k, lim in (("refund_pct", a.get("max_refund_pct")), ("dispute_pct", a.get("max_dispute_pct"))):
            if lim is not None and m.get(k) is not None and _f(m[k], k) >= _f(lim, k):
                flags.append(f"{k} {m[k]} at or over your limit {lim}")
        out.append({"merchant": m.get("name"), "flags": flags})
    return {"merchants": out, "to_review": [m["merchant"] for m in out if m["flags"]], "says": "Signals for review; the decision is a person's."}


def safeguarding(a: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for d in a.get("days") or []:
        owed, held = _m(d.get("owed_to_customers"), "owed_to_customers"), _m(d.get("safeguarded"), "safeguarded")
        rows.append({"date": str(_d(d.get("date"), "date")), "owed": _u(owed), "safeguarded": _u(held), "difference": _u(held - owed),
                     "shortfall": held < owed})
    return {"days": rows, "shortfall_days": [r["date"] for r in rows if r["shortfall"]],
            "says": "A shortfall day is for the safeguarding officer to put right and to record; how fast is set by your regulator" + NOT_CONFIRMED}


def _iban_ok(iban: str) -> bool:
    s = re.sub(r"\s", "", iban).upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", s):
        return False
    n = "".join(str(int(c, 36)) for c in s[4:] + s[:4])
    return int(n) % 97 == 1


def iso20022(a: dict[str, Any]) -> dict[str, Any]:
    xml = str(a.get("xml") or "")
    if not xml.strip():
        raise PaymentsError("xml: the pain.001 or pacs.008 message.")
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        return {"ok": False, "problems": [f"not well formed: {e}"]}
    ns = re.match(r"\{(.*)\}", root.tag)
    ns = ns.group(1) if ns else ""
    q = (lambda t: f"{{{ns}}}{t}") if ns else (lambda t: t)
    kind = "pain.001" if "pain.001" in ns else "pacs.008" if "pacs.008" in ns else "unknown"
    problems = []
    grp = root.find(f".//{q('GrpHdr')}")
    if grp is None:
        problems.append("GrpHdr missing")
        return {"kind": kind, "ok": False, "problems": problems}
    for t in ("MsgId", "CreDtTm", "NbOfTxs"):
        if grp.find(q(t)) is None:
            problems.append(f"GrpHdr/{t} missing")
    txs = root.findall(f".//{q('CdtTrfTxInf')}")
    amts = []
    for i, tx in enumerate(txs):
        el = tx.find(f".//{q('InstdAmt')}")
        if el is None:
            el = tx.find(f".//{q('IntrBkSttlmAmt')}")
        if el is None or not el.get("Ccy"):
            problems.append(f"transaction {i + 1}: amount with currency missing")
        else:
            amts.append(Decimal(el.text or "0"))
        for iban in tx.findall(f".//{q('IBAN')}"):
            if not _iban_ok(iban.text or ""):
                problems.append(f"transaction {i + 1}: IBAN {iban.text} fails its check digits")
        for bic in tx.findall(f".//{q('BICFI')}") + tx.findall(f".//{q('BIC')}"):
            if not re.fullmatch(r"[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?", (bic.text or "").strip()):
                problems.append(f"transaction {i + 1}: BIC {bic.text} has the wrong shape")
        if tx.find(f".//{q('EndToEndId')}") is None:
            problems.append(f"transaction {i + 1}: EndToEndId missing")
    nb = grp.find(q("NbOfTxs"))
    if nb is not None and (nb.text or "").strip() != str(len(txs)):
        problems.append(f"NbOfTxs says {nb.text}, the message has {len(txs)}")
    cs = grp.find(q("CtrlSum"))
    if cs is not None and Decimal(cs.text or "0") != sum(amts, Decimal(0)):
        problems.append(f"CtrlSum says {cs.text}, the amounts add to {sum(amts, Decimal(0))}")
    for i, iban in enumerate(root.findall(f".//{q('DbtrAcct')}//{q('IBAN')}")):
        if not _iban_ok(iban.text or ""):
            problems.append(f"debtor IBAN {iban.text} fails its check digits")
    return {"kind": kind, "transactions": len(txs), "total": str(sum(amts, Decimal(0))), "ok": not problems, "problems": problems,
            "says": "Checked for the parts a bank needs and the sums; your bank's own validator and usage rules decide."}


def exceptions(a: dict[str, Any]) -> dict[str, Any]:
    today = _d(a.get("today") or date.today().isoformat(), "today")
    buckets = {"0-2 days": [], "3-7 days": [], "8-30 days": [], "over 30 days": []}
    for x in a.get("items") or []:
        age = (today - _d(x.get("date"), "items.date")).days
        b = "0-2 days" if age <= 2 else "3-7 days" if age <= 7 else "8-30 days" if age <= 30 else "over 30 days"
        buckets[b].append({"id": x.get("id"), "kind": x.get("kind"), "amount": x.get("amount"), "age_days": age})
    return {"by_age": buckets, "oldest": max((i["age_days"] for v in buckets.values() for i in v), default=0)}


def returns(a: dict[str, Any]) -> dict[str, Any]:
    tot: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    for t in a.get("transactions") or []:
        d = _d(t.get("date"), "date")
        per = f"{d.year}-Q{(d.month - 1) // 3 + 1}" if a.get("period") == "quarter" else f"{d.year}-{d.month:02d}"
        k = (per, str(t.get("type") or "payment"))
        tot[k][0] += 1
        tot[k][1] += _m(t.get("amount"), "amount")
    return {"figures": [{"period": p, "type": ty, "count": n, "value": _u(v)} for (p, ty), (n, v) in sorted(tot.items())],
            "says": "Counted from your transactions; the return's own boxes and definitions are your regulator's" + NOT_CONFIRMED}


ACTIONS = ("dispute", "prevention", "reconcile", "fee_audit", "dunning", "payouts", "export", "kyb", "merchant_risk", "safeguarding",
           "iso20022", "exceptions", "returns", "reasons")


def run(tenant: str, action: str, a: dict[str, Any], actor: str = "owner") -> dict[str, Any]:
    a = dict(a)
    if re.search(r"submit|charge|pay_out|send", action):
        raise L.Refused("move_money", NEVER)
    f = {k: globals()[k] for k in ACTIONS if k != "reasons"}
    if action == "reasons":
        out = {"reasons": {n: {c: v["name"] for c, v in t.items()} for n, t in REASONS.items()}, "evidence": EVIDENCE,
               "from": "Hoola's table, from memory" + NOT_CONFIRMED}
    elif action in f:
        out = f[action](a)
    else:
        raise PaymentsError("action: " + ", ".join(ACTIONS))
    out.setdefault("not_advice", L.NOT_ADVICE)
    return out
