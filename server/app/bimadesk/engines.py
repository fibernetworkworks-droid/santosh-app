"""Health insurance Wave 1 engines: #14 KYC check, #17 renewals, #42/#50/#78 claim checklist + deadlines, #46/#79 payable worksheet,
#48 settlement match, #49 status message, #53 ageing, #64 grievance triage, #80 appeal outline.
Pure functions: no DB, no file, no network. Limits, periods and lists are HERS (the policy / IRDAI text she reads); defaults are from memory and say verify."""
from __future__ import annotations

import datetime as dt
import re
from typing import Any

DECIDER = "claims officer / TPA / insurer (claim decisions are theirs); the policyholder decides what to file"


def _f(v: Any) -> float:
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _d(v: Any) -> dt.date:
    s = str(v or "").strip()[:10]
    for f in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(s, f).date()
        except ValueError:
            pass
    raise ValueError(f"Could not read the date: '{v}' (use 2026-11-05).")


def _today(v: Any) -> dt.date:
    return _d(v) if v else dt.date.today()


_BASE_DOCS = ["claim form (signed)", "policy / e-card copy", "photo ID of the patient", "discharge summary", "final hospital bill (itemised)",
              "payment receipts", "doctor's prescriptions and investigation reports", "cancelled cheque / bank proof"]
_EXTRA = {
    "accident": ["FIR / MLC copy where applicable", "accident details in the claim form"],
    "maternity": ["maternity / delivery certificate", "antenatal records"],
    "daycare": ["procedure note from the hospital"],
    "pre_post": ["bills and reports for the pre / post period", "doctor's advice for the follow-up"],
    "opd": ["OPD bills with prescription", "pharmacy bills matching the prescription"],
}


def claim_checklist(claim_type: str = "reimbursement", have: list | None = None, admission: Any = None, discharge: Any = None, today: Any = None,
                    intimate_hours: Any = 48, file_days: Any = 30, kind: Any = None) -> dict[str, Any]:
    ct = (claim_type or "reimbursement").lower().strip()
    need = list(_BASE_DOCS) + _EXTRA.get(str(kind or "").lower(), [])
    if ct == "cashless":
        need = ["pre-authorisation request (hospital fills)", "policy / e-card", "photo ID", "doctor's note with diagnosis and plan", "estimate from hospital",
                "final bill and discharge summary at discharge"] + _EXTRA.get(str(kind or "").lower(), [])
    elif ct not in ("reimbursement", "cashless"):
        raise ValueError("claim_type: cashless ya reimbursement.")
    got = [str(h).lower() for h in (have or [])]
    missing = [n for n in need if not any(w in g or g in n.lower() for g in got for w in [n.lower().split()[0]])]
    out: dict[str, Any] = {"claim_type": ct, "needed": need, "have": have or [], "missing": missing, "complete": not missing,
                           "decider": DECIDER, "note": "Insurer / TPA can ask for more; the list is a self-check, not their rule.",
                           "verify": True, "not_checked": ["policy-specific document list", "authenticity of any document"]}
    if admission:
        a = _d(admission)
        t = _today(today)
        ds = {"intimate_before": (a + dt.timedelta(hours=_f(intimate_hours))).isoformat() + " (planned: before admission; emergency: within the policy's hours)"}
        if discharge:
            dd = _d(discharge)
            last = dd + dt.timedelta(days=int(_f(file_days)))
            ds.update({"file_by": last.isoformat(), "days_left": (last - t).days, "overdue": t > last,
                       "note": "periods are policy terms; the defaults here are from memory (verify)"})
        out["deadlines"] = ds
    return out


def payable(items: list[dict], sum_insured: Any = 0, room_rent_cap: Any = 0, room_rent_charged: Any = 0, copay_pct: Any = 0, deductible: Any = 0,
            non_payable: list | None = None, settled: Any = None) -> dict[str, Any]:
    if not items:
        raise ValueError("items rows do: name, billed (optional: payable_cap).")
    npl = [str(x).lower() for x in (non_payable or [])]
    rows, tot, np_amt, capd = [], 0.0, 0.0, 0.0
    for it in items[:2000]:
        nm, b = str(it.get("name", "")), _f(it.get("billed"))
        tot += b
        if any(w and w in nm.lower() for w in npl):
            np_amt += b
            rows.append({"name": nm, "billed": b, "allowed": 0.0, "reason": "on the non-payable list given"})
            continue
        cap = _f(it.get("payable_cap")) if it.get("payable_cap") not in (None, "") else None
        al = min(b, cap) if cap is not None else b
        capd += b - al
        rows.append({"name": nm, "billed": b, "allowed": round(al, 2), "reason": "tariff cap" if cap is not None and al < b else "allowed"})
    allowed = tot - np_amt - capd
    ratio, prop = 1.0, 0.0
    cap_rr, chg = _f(room_rent_cap), _f(room_rent_charged)
    if cap_rr and chg > cap_rr:
        ratio = cap_rr / chg
        prop = round(allowed * (1 - ratio), 2)
        allowed *= ratio
    allowed = max(allowed - _f(deductible), 0)
    cp = round(allowed * _f(copay_pct) / 100, 2)
    pay = allowed - cp
    si = _f(sum_insured)
    if si and pay > si:
        pay = si
    res = {"billed_total": round(tot, 2), "non_payable": round(np_amt, 2), "tariff_cap_cut": round(capd, 2), "room_rent_proportion_cut": prop,
           "deductible": _f(deductible), "copay": cp, "estimated_payable": round(pay, 2), "rows": rows[:200], "decider": DECIDER,
           "note": "A worksheet from the terms YOU gave; the insurer's settlement is what counts.", "not_checked": ["medical necessity", "policy exclusions / waiting periods", "sub-limits not given"]}
    if settled not in (None, ""):
        gap = round(_f(settled) - res["estimated_payable"], 2)
        res["settled"] = _f(settled)
        res["gap"] = gap
        res["questions_to_ask"] = ([] if abs(gap) < 1 else ["Ask the insurer for the line-wise deduction sheet and the policy clause for each cut."]
                                   + (["Room-rent proportion cut was %s: ask whether the policy applies it to every line." % prop] if prop else []))
    return res


def settlement_match(payments: list[dict], expected: list[dict], tolerance: Any = 1) -> dict[str, Any]:
    if not expected:
        raise ValueError("expected rows do: claim, payable (optional tds).")
    tol = _f(tolerance)
    by: dict[str, float] = {}
    utr_seen: dict[str, int] = {}
    for p in payments or []:
        by[str(p.get("claim"))] = by.get(str(p.get("claim")), 0) + _f(p.get("amount"))
        u = str(p.get("utr") or "")
        if u:
            utr_seen[u] = utr_seen.get(u, 0) + 1
    rows = []
    for e in expected:
        c = str(e.get("claim"))
        want = _f(e.get("payable")) - _f(e.get("tds"))
        got = by.pop(c, 0.0)
        st = "matched" if abs(got - want) <= tol else ("not received" if got == 0 else ("short" if got < want else "excess"))
        rows.append({"claim": c, "expected": round(want, 2), "received": round(got, 2), "status": st, "diff": round(got - want, 2)})
    return {"rows": rows, "unmatched_payments": [{"claim": k, "amount": round(v, 2)} for k, v in by.items()],
            "duplicate_utr": [u for u, n in utr_seen.items() if n > 1], "decider": "finance head", "not_checked": ["bank statement itself", "GST / TDS rates"]}


_STATUS = {
    "registered": ("Aapka claim {id} register ho gaya hai. Hum documents check kar rahe hain.", "Your claim {id} is registered. Documents are being checked."),
    "docs_pending": ("Claim {id} ke liye kuch documents baaki hain: {extra}. Kripya bhej dein.", "Claim {id} needs a few more documents: {extra}. Please send them."),
    "approved": ("Claim {id} ka payable amount {extra} tay hua hai. Payment ki details jald milengi.", "Claim {id} is approved for {extra}. Payment details will follow."),
    "paid": ("Claim {id} ka payment ho gaya hai (reference {extra}).", "Claim {id} has been paid (reference {extra})."),
    "query": ("Claim {id} par insurer ka sawaal aaya hai: {extra}.", "The insurer has a query on claim {id}: {extra}."),
    "rejected": ("Claim {id} par insurer ka faisla aaya hai. Kaaran aur aage ke raaste ke liye hamare adhikari aapse baat karenge.", "The insurer has given a decision on claim {id}. Our officer will call you about the reasons and next options."),
}


def status_message(status: str, claim_id: str = "", extra: str = "", language: str = "en") -> dict[str, Any]:
    s = (status or "").lower().strip()
    if s not in _STATUS:
        raise ValueError("status: " + ", ".join(_STATUS))
    hi, en = _STATUS[s]
    txt = (en if str(language).lower().startswith("en") else hi).format(id=claim_id or "-", extra=extra or "-")
    return {"message": txt, "status": s, "send": False, "decider": "claims desk sends it; this only drafts",
            "note": "A rejection is never sent as a bare text: a person calls first."}


def ageing(claims: list[dict], today: Any = None, tat_days: Any = 30, warn_days: Any = 5) -> dict[str, Any]:
    if not claims:
        raise ValueError("claims rows do: id, received, status (closed/open), last_doc_date.")
    t = _today(today)
    rows, late, soon = [], [], []
    for c in claims[:20000]:
        if str(c.get("status", "open")).lower() in ("closed", "paid", "settled", "rejected"):
            continue
        base = _d(c.get("last_doc_date") or c.get("received"))
        due = base + dt.timedelta(days=int(_f(tat_days)))
        left = (due - t).days
        r = {"id": c.get("id"), "due": due.isoformat(), "days_left": left}
        rows.append(r)
        if left < 0:
            late.append(r)
        elif left <= _f(warn_days):
            soon.append(r)
    rows.sort(key=lambda r: r["days_left"])
    return {"open": len(rows), "past_timeline": late, "due_soon": soon, "rows": rows[:300], "decider": "claims head",
            "verify": True, "note": "Timeline is the number you gave (default 30 days from last document, from memory: check the current IRDAI circular)."}


def renewals(policies: list[dict], today: Any = None, window_days: Any = 60, portability_days: Any = 45) -> dict[str, Any]:
    if not policies:
        raise ValueError("policies rows do: id, holder, renewal_date, premium (optional ncb_pct, claims_this_year).")
    t = _today(today)
    due = []
    for p in policies[:20000]:
        rd = _d(p.get("renewal_date"))
        n = (rd - t).days
        if n <= _f(window_days):
            due.append({"id": p.get("id"), "holder": p.get("holder"), "renewal_date": rd.isoformat(), "days": n, "premium": _f(p.get("premium")),
                        "lapsed": n < 0, "ncb_pct": p.get("ncb_pct"),
                        "portability_note": "port-in request is usually due well before renewal (policy / insurer period)" if 0 <= n <= _f(portability_days) else None})
    due.sort(key=lambda r: r["days"])
    return {"due": due, "count": len(due), "decider": "the policyholder (and her adviser); this is a reminder list",
            "verify": True, "note": "Portability and grace-period rules are from memory; read the current policy text. No advice on switching insurers."}


_CATS = [("claim", ("claim", "reject", "repudiat", "settle", "deduction", "cashless")), ("premium", ("premium", "refund", "increase", "gst")),
         ("mis-selling", ("mis-sold", "mis sold", "misled", "promised", "agent said")), ("policy servicing", ("endorse", "address", "nominee", "e-card", "policy copy", "renew")),
         ("portability", ("portab",)), ("network", ("network", "hospital refused", "cashless denied"))]


def grievance(items: list[dict], today: Any = None, ack_days: Any = 3, resolve_days: Any = 14) -> dict[str, Any]:
    if not items:
        raise ValueError("items rows do: id, received, text (optional acknowledged).")
    t = _today(today)
    out = []
    for it in items[:5000]:
        txt = str(it.get("text", "")).lower()
        cat = next((c for c, ws in _CATS if any(w in txt for w in ws)), "other")
        rec = _d(it.get("received"))
        a_due, r_due = rec + dt.timedelta(days=int(_f(ack_days))), rec + dt.timedelta(days=int(_f(resolve_days)))
        out.append({"id": it.get("id"), "category": cat, "ack_due": a_due.isoformat(), "resolve_due": r_due.isoformat(),
                    "ack_late": (not it.get("acknowledged")) and t > a_due, "resolve_late": t > r_due and not it.get("resolved"),
                    "needs_human_now": any(w in txt for w in ("death", "icu", "emergency", "suicide", "legal notice", "ombudsman"))})
    return {"items": out, "decider": "grievance officer", "verify": True,
            "note": "Periods are the numbers given or the defaults from memory (verify against the current IRDAI rules). Category is a keyword guess, a person confirms."}


def appeal(reasons: list[str], rejected_on: Any = None, today: Any = None, insurer_replied_on: Any = None) -> dict[str, Any]:
    if not reasons:
        raise ValueError("reasons list do (the insurer's own words).")
    t = _today(today)
    pts = []
    for r in reasons[:20]:
        low = str(r).lower()
        docs = ["copy of the rejection letter", "policy wording with the clause quoted"]
        if "pre-exist" in low or "ped" in low:
            docs += ["earlier medical records / proposal form copy", "treating doctor's note on onset"]
        elif "waiting" in low:
            docs += ["policy start date and port history", "diagnosis date evidence"]
        elif "document" in low or "incomplete" in low:
            docs += ["the missing documents the insurer named"]
        elif "not medically necessary" in low or "necessity" in low:
            docs += ["treating doctor's letter on why admission was needed"]
        pts.append({"insurer_reason": r, "supporting_documents": docs, "her_point": "[write in your own words: what the record shows]"})
    steps = ["1. Written grievance to the insurer's grievance officer (keep the acknowledgement).", "2. If no answer in the policy's period or you disagree, escalate to the insurer's head of grievance.",
             "3. Insurance Ombudsman complaint (limitation commonly counted from the insurer's final reply): check the current rules and dates."]
    out = {"points": pts, "steps": steps, "letter_outline": ["Subject: grievance on claim [no.]", "Facts: dates, hospital, diagnosis [from record]", "Their reason, one by one, with our answer",
                                                              "Documents attached", "What I ask: reconsideration within [period]"],
           "decider": "the policyholder files; a lawyer or adviser may review; the ombudsman / insurer decides", "verify": True,
           "not_checked": ["whether the rejection is right", "limitation law"], "note": "Not legal or medical advice."}
    if insurer_replied_on:
        r = _d(insurer_replied_on)
        out["one_year_from_reply"] = (r + dt.timedelta(days=365)).isoformat()
        out["days_left_if_one_year"] = (r + dt.timedelta(days=365) - t).days
    return out


def _pan_ok(p: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", p.upper()))


def kyc_check(docs: dict) -> dict[str, Any]:
    if not docs:
        raise ValueError("docs dikhao: {aadhaar, pan, bank_account, ifsc, dob, name}.")
    out, ok = [], True
    a = re.sub(r"\D", "", str(docs.get("aadhaar", "")))
    if a:
        out.append({"field": "aadhaar", "ok": len(a) == 12, "shown": "XXXX XXXX " + a[-4:], "note": "store the masked form only"})
        ok &= len(a) == 12
    p = str(docs.get("pan", "")).strip()
    if p:
        out.append({"field": "pan", "ok": _pan_ok(p), "shown": p[:2] + "XXXXXX" + p[-2:] if len(p) >= 4 else "XX"})
        ok &= _pan_ok(p)
    i = str(docs.get("ifsc", "")).strip().upper()
    if i:
        g = bool(re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", i))
        out.append({"field": "ifsc", "ok": g})
        ok &= g
    b = re.sub(r"\D", "", str(docs.get("bank_account", "")))
    if b:
        g = 9 <= len(b) <= 18
        out.append({"field": "bank_account", "ok": g, "shown": "XXXX" + b[-4:]})
        ok &= g
    for k in ("name", "dob"):
        if not docs.get(k):
            out.append({"field": k, "ok": False, "note": "missing"})
            ok = False
    return {"checks": out, "all_ok": ok, "decider": "claims / KYC officer", "note": "Format checks only; names are not matched against the ID image and no ID is verified with any authority."}
