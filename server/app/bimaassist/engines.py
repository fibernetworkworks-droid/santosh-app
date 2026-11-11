"""Health insurance Wave 2 engines (#11 plan compare, #12 proposal check, #13 material facts, #33 pre-auth checks, #34 query reply, #44 medical timeline,
#45 coverage check, #47 rejection letter, #65 grievance reply, #66 ombudsman packet, #73 wording review, #74 mis-selling review, #93 FHIR claim skeleton,
#94 code map). Pure functions. Terms, clause text, package rates and code maps are HERS; nothing is built in except keyword lists marked heuristic."""
from __future__ import annotations

import datetime as dt
import re
from typing import Any

SIGNER = "[name and designation of the decision-maker]"


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
    raise ValueError(f"Could not understand the date: '{v}' (2026-11-05).")


_ATTR = [("premium", "lower"), ("sum_insured", "higher"), ("room_rent_cap", "higher"), ("copay_pct", "lower"), ("waiting_ped_months", "lower"),
         ("network_count", "higher"), ("claim_settlement_pct", "higher")]


def plan_compare(plans: list[dict]) -> dict[str, Any]:
    if len(plans or []) < 2:
        raise ValueError("Give at least 2 plans: name, premium, sum_insured, room_rent_cap, copay_pct, waiting_ped_months, network_count.")
    rows, lines = [], []
    for a, better in _ATTR:
        vals = [(str(p.get("name")), p.get(a)) for p in plans if p.get(a) not in (None, "")]
        if len(vals) < 2:
            continue
        pick = (min if better == "lower" else max)(vals, key=lambda x: _f(x[1]))
        tie = len({_f(v) for _, v in vals}) == 1
        rows.append({"attribute": a, "values": dict(vals), "better_on_paper": None if tie else pick[0]})
        if not tie:
            lines.append(f"{a}: {pick[0]} has the better number ({pick[1]}).")
    return {"table": rows, "plain_lines": lines, "decider": "the adviser / the customer: suitability is their call",
            "note": "Numbers only, as given. No plan is recommended; cover wording, exclusions and the insurer's service are not compared.", "not_checked": ["exclusions", "sub-limits not given", "claim experience"]}


_COND = ("diabetes", "sugar", "bp", "blood pressure", "hypertension", "thyroid", "asthma", "heart", "cardiac", "cancer", "kidney", "stone", "surgery", "operation", "migraine",
         "arthritis", "epilepsy", "ulcer", "hernia", "cholesterol", "stroke", "tb", "hepatitis", "depression")


def material_facts(answers: list[dict], history_notes: str = "") -> dict[str, Any]:
    if not answers:
        raise ValueError("Give answers as rows: q, answer (yes/no/text).")
    hist = (history_notes or "").lower()
    found = sorted({c for c in _COND if re.search(r"\b" + re.escape(c) + r"\b", hist)})
    flags, said_no = [], 0
    for a in answers[:200]:
        q, ans = str(a.get("q", "")).lower(), str(a.get("answer", "")).strip().lower()
        ped_q = any(w in q for w in ("pre-existing", "ailment", "disease", "treatment", "medical history", "surgery", "hospital"))
        if ped_q and ans in ("no", "n", "nahi", "none", "nil", ""):
            said_no += 1
            if found:
                flags.append({"question": a.get("q"), "answered": ans or "(blank)", "history_mentions": found, "ask": "History notes mention these. Is 'no' correct? Disclose everything known."})
            elif ans == "":
                flags.append({"question": a.get("q"), "answered": "(blank)", "ask": "Blank answer: fill it in."})
    return {"flags": flags, "conditions_seen_in_history": found, "no_answers_on_health_questions": said_no, "decider": "the customer answers and signs; the adviser reviews",
            "note": "Under-declaring is the commonest start of a rejection. Keyword match is heuristic; it cannot know what is true. Never answer for the customer.", "not_checked": ["truth of any answer", "records not pasted"]}


def proposal_check(fields: dict, required: list | None = None) -> dict[str, Any]:
    if not fields:
        raise ValueError("fields do: name, dob, age, sum_insured, members, nominee, address...")
    req = required or ["name", "dob", "address", "nominee", "sum_insured", "members"]
    miss = [r for r in req if not fields.get(r)]
    contra = []
    if fields.get("dob") and fields.get("age"):
        try:
            a = (dt.date.today() - _d(fields["dob"])).days // 365
            if abs(a - int(_f(fields["age"]))) > 1:
                contra.append(f"age {fields['age']} does not match dob (about {a}).")
        except ValueError as e:
            contra.append(str(e))
    if fields.get("members") and isinstance(fields["members"], list) and fields.get("sum_insured") and _f(fields["sum_insured"]) <= 0:
        contra.append("sum_insured must be above zero.")
    return {"missing": miss, "contradictions": contra, "declaration_signed": bool(fields.get("declaration_signed")),
            "decider": "the customer signs the declaration; the agent submits", "note": "Fill from the customer's documents only; the declaration is theirs to sign.", "not_checked": ["accuracy against documents"]}


def coverage_check(policy: dict, claim: dict) -> dict[str, Any]:
    """policy: {start, initial_waiting_days, ped_waiting_months, moratorium_months, specific_waiting{name:months}, sublimits{name:amt}, room_rent_cap, copay_pct, clauses{key:text}}"""
    if not policy or not claim:
        raise ValueError("give both policy and claim.")
    cl = policy.get("clauses") or {}
    adm = _d(claim.get("admission"))
    start = _d(policy.get("start"))
    days = (adm - start).days
    out = []

    def add(key, status, text):
        out.append({"check": key, "status": status, "finding": text, "clause": cl.get(key, "[clause text not given: attach before use]")})
    iw = _f(policy.get("initial_waiting_days"))
    if iw:
        add("initial_waiting", "fails" if days < iw and not claim.get("accident") else "ok", f"admission on day {days} of the policy; initial waiting {int(iw)} days" + (" (accident exempt only if the policy says so)" if claim.get("accident") else ""))
    dx = str(claim.get("diagnosis", "")).lower()
    for nm, mo in (policy.get("specific_waiting") or {}).items():
        if nm.lower() in dx:
            add("specific_waiting:" + nm, "fails" if days < _f(mo) * 30 else "ok", f"{nm} waiting {mo} months, policy age {days // 30} months")
    if claim.get("is_ped"):
        mor, ped = _f(policy.get("moratorium_months")), _f(policy.get("ped_waiting_months"))
        if mor and days >= mor * 30:
            add("moratorium", "ok", f"continuous cover for {days // 30} months; moratorium {int(mor)} months: pre-existing exclusion cannot be used (as per the clause given)")
        elif ped:
            add("ped_waiting", "fails" if days < ped * 30 else "ok", f"pre-existing waiting {int(ped)} months, policy age {days // 30} months")
    for nm, amt in (policy.get("sublimits") or {}).items():
        if nm.lower() in dx and _f(claim.get("amount")) > _f(amt):
            add("sublimit:" + nm, "limits", f"claimed {claim.get('amount')} above sub-limit {amt}; payable up to {amt}")
    cap, chg = _f(policy.get("room_rent_cap")), _f(claim.get("room_charged"))
    if cap and chg > cap:
        add("room_rent", "limits", f"room rent {chg} above cap {cap}: proportionate deduction ratio {round(cap / chg, 4)} on related charges (if the policy applies it)")
    if _f(policy.get("copay_pct")):
        add("copay", "limits", f"co-pay {policy['copay_pct']}% applies")
    return {"findings": out, "decider": "claims adjudicator", "note": "Every line shows the clause text YOU supplied; missing clause text is marked. A finding is a flag, not a decision.",
            "not_checked": ["medical necessity", "exclusions not given", "disclosure"], "verify": True}


def preauth_checks(policy: dict, request: dict, package_rates: dict | None = None, today: Any = None) -> dict[str, Any]:
    if not request:
        raise ValueError("request do: procedure, estimate, admission, diagnosis.")
    chk = []
    start, end = policy.get("start"), policy.get("end")
    adm = _d(request.get("admission"))
    if start and end:
        chk.append({"check": "policy in force on admission", "result": "pass" if _d(start) <= adm <= _d(end) else "fail"})
    else:
        chk.append({"check": "policy in force on admission", "result": "unknown", "why": "start / end not given"})
    cv = coverage_check({**policy, "start": start or request.get("admission")}, {"admission": request.get("admission"), "diagnosis": request.get("diagnosis"),
                        "amount": request.get("estimate"), "is_ped": request.get("is_ped"), "room_charged": request.get("room_charged")}) if start else None
    if cv:
        chk += [{"check": f["check"], "result": "fail" if f["status"] == "fails" else "flag" if f["status"] == "limits" else "pass", "finding": f["finding"]} for f in cv["findings"]]
    pr = (package_rates or {}).get(str(request.get("procedure", "")).lower())
    if pr is not None:
        over = _f(request.get("estimate")) - _f(pr)
        chk.append({"check": "estimate vs package rate", "result": "flag" if over > 0 else "pass", "finding": f"estimate {request.get('estimate')} vs package {pr}" + (f" (over by {over})" if over > 0 else "")})
    else:
        chk.append({"check": "estimate vs package rate", "result": "unknown", "why": "no package rate given for this procedure"})
    return {"checks": chk, "decider": "medical officer (approval or denial is theirs)", "note": "Necessity criteria are not judged here.", "not_checked": ["medical necessity"]}


def query_reply(queries: list[str], chart: dict) -> dict[str, Any]:
    if not queries:
        raise ValueError("give a queries list (the insurer's questions).")
    items = []
    for q in queries[:30]:
        words = [w for w in re.findall(r"[a-z]{3,}", q.lower()) if w not in ("the", "please", "send", "for", "and", "with", "any", "reason", "report", "copy", "provide")]
        hit = next(((k, v) for k, v in (chart or {}).items() if any(w in k.lower() or w in str(v).lower() for w in words)), None)
        items.append({"query": q, "draft": f"{hit[0]}: {hit[1]}" if hit else "[answer from the chart: not found in the facts given]", "from_chart": bool(hit)})
    return {"items": items, "unanswered": [i["query"] for i in items if not i["from_chart"]], "decider": "TPA desk / treating doctor reviews before it goes", "note": "Draft from the chart facts given only; nothing is sent."}


def medical_timeline(events: list[dict], gap_days: Any = 3, expected: dict | None = None) -> dict[str, Any]:
    if not events:
        raise ValueError("events rows do: date, type (admission/investigation/procedure/discharge), text.")
    ev = sorted(events[:2000], key=lambda e: _d(e.get("date")))
    flags = []
    for a, b in zip(ev, ev[1:]):
        g = (_d(b["date"]) - _d(a["date"])).days
        if g > _f(gap_days):
            flags.append(f"{g} days between {a['date']} and {b['date']}: no entry in between")
    types = {str(e.get("type", "")).lower() for e in ev}
    for need in ("admission", "discharge"):
        if need not in types:
            flags.append(f"no '{need}' entry")
    dx = " ".join(str(e.get("text", "")) for e in ev if str(e.get("type", "")).lower() == "diagnosis").lower()
    proc = " ".join(str(e.get("text", "")) for e in ev if str(e.get("type", "")).lower() == "procedure").lower()
    for d, plist in (expected or {}).items():
        if d.lower() in dx and not any(p.lower() in proc for p in plist):
            flags.append(f"diagnosis '{d}' but none of the expected procedures {plist} appear (your list)")
    return {"timeline": [{"date": e["date"], "type": e.get("type"), "text": e.get("text")} for e in ev], "flags": flags,
            "decider": "claims medical officer", "note": "Gaps and mismatches are questions, not conclusions. The expected-procedure list is yours."}


def rejection_letter(claim_id: str, reasons: list[dict], documents_considered: list | None = None, appeal_path: str = "", ombudsman: str = "", kind: str = "rejection") -> dict[str, Any]:
    """reasons: [{reason, clause_ref, clause_text}]. No clause -> no letter."""
    if not reasons:
        raise ValueError("reasons do: reason, clause_ref, clause_text.")
    bad = [r.get("reason") for r in reasons if not (r.get("clause_ref") and r.get("clause_text"))]
    if bad:
        raise ValueError("Every reason needs a policy clause (ref + text). These have no clause: " + "; ".join(map(str, bad)))
    body = [f"Re: claim {claim_id}", "", "We have examined the claim against the policy terms. Reasons:"]
    for i, r in enumerate(reasons, 1):
        body.append(f"{i}. {r['reason']} - policy clause {r['clause_ref']}: \"{r['clause_text']}\"")
    body += ["", "Documents considered: " + (", ".join(map(str, documents_considered)) if documents_considered else "[list the documents]"),
             "If you disagree: " + (appeal_path or "[internal appeal / grievance route and period]"),
             "You may also approach the Insurance Ombudsman: " + (ombudsman or "[office details and time limit: verify current rules]"), "", "Signed: " + SIGNER]
    return {"kind": kind, "letter": "\n".join(body), "send": False, "decider": "claims head signs; a named decision-maker owns it", "note": "Draft only. It carries no decision of its own; every reason needs its clause."}


def grievance_reply(complaint: str, facts: list[str], clause: str = "", remedies: list[str] | None = None) -> dict[str, Any]:
    if not complaint:
        raise ValueError("complaint text do.")
    body = ["Dear [name],", "", "We acknowledge your complaint: " + complaint.strip()[:400], "", "Facts from our file:"] + [f"- {f}" for f in (facts or ["[add facts from the file]"])]
    body += ["", "Policy clause relied on: " + (clause or "[clause ref and text]"), "", "Options open to you:"] + [f"- {r}" for r in (remedies or ["[remedy options]"])]
    body += ["", "If you remain unsatisfied you may escalate as per the grievance route and to the Insurance Ombudsman [details: verify].", "", "Regards, " + SIGNER]
    return {"letter": "\n".join(body), "send": False, "decider": "grievance officer reviews and signs", "note": "Draft from the facts given; admits nothing and promises nothing beyond what you add."}


_PACK = ["policy copy", "claim form", "rejection / repudiation letter", "complaint to insurer with date", "insurer's final reply (or proof of no reply)",
         "medical records and bills", "ID and address proof", "correspondence index"]


def ombudsman_packet(have: list | None = None, insurer_reply_on: Any = None, complaint_on: Any = None, today: Any = None, claim_amount: Any = None) -> dict[str, Any]:
    got = [str(h).lower() for h in (have or [])]
    missing = [p for p in _PACK if not any(p.split()[0] in g for g in got)]
    t = _d(today) if today else dt.date.today()
    out: dict[str, Any] = {"packet": _PACK, "missing": missing, "decider": "the complainant (and a lawyer if she wants one) files; the ombudsman decides", "verify": True,
                           "note": "Rules 2017 as remembered: complaint first to the insurer, the ombudsman only after its reply or about 30 days of no reply, within about one year of that reply; value limit applies. Verify the current Rules.",
                           "not_checked": ["current limitation", "jurisdiction / office", "value limit"]}
    if insurer_reply_on:
        out["one_year_from_reply"] = (_d(insurer_reply_on) + dt.timedelta(days=365)).isoformat()
        out["days_left"] = (_d(insurer_reply_on) + dt.timedelta(days=365) - t).days
    elif complaint_on:
        w = _d(complaint_on) + dt.timedelta(days=30)
        out["may_approach_ombudsman_after"] = w.isoformat() + " if the insurer has not replied"
    return out


_JARGON = ("subrogation", "indemnity", "contra", "ex-gratia", "proximate cause", "moratorium", "co-payment", "sub-limit", "pro-rata", "proportionate", "cumulative bonus", "ailment", "domiciliary")
_VAGUE = ("reasonable", "customary", "usual", "as decided by the company", "at its discretion", "sole discretion", "may be", "from time to time", "as applicable", "deemed", "not limited to")


def wording_review(text: str) -> dict[str, Any]:
    if not text or len(text) < 30:
        raise ValueError("Paste the policy text.")
    low = text.lower()
    sents = [s.strip() for s in re.split(r"(?<=[.;])\s+", text) if s.strip()]
    long_ = [s[:160] for s in sents if len(s.split()) > 60][:10]
    excl = [s[:200] for s in sents if re.search(r"\b(exclu|not covered|shall not|no claim|not payable)", s.lower())][:15]
    return {"jargon": sorted(w for w in _JARGON if w in low), "vague_terms": sorted(w for w in _VAGUE if w in low), "very_long_sentences": long_, "exclusion_sentences": excl,
            "decider": "legal and product teams", "note": "Flags where a reader may be misled; an ambiguity can be read against the drafter (contra proferentem): a lawyer judges. Keyword lists are heuristic."}


_MIS = ("guaranteed", "no medical", "no need to tell", "don't tell", "dont tell", "tax free returns", "double your money", "fd se behtar", "investment", "bonus guaranteed", "no waiting", "no exclusion", "limited time", "sign here")


def missell_review(calls: list[dict] | None = None, policies: list[dict] | None = None, today: Any = None, freelook_days: Any = 15) -> dict[str, Any]:
    if not calls and not policies:
        raise ValueError("calls [{id, text}] ya policies [{id, issued, cancelled, proposal_dob, id_dob}] do.")
    t = _d(today) if today else dt.date.today()
    hits = []
    for c in (calls or [])[:2000]:
        low = str(c.get("text", "")).lower()
        k = [w for w in _MIS if w in low]
        if k:
            hits.append({"call": c.get("id"), "phrases": k})
    fl, disc = [], []
    for p in (policies or [])[:5000]:
        if p.get("issued"):
            left = int(_f(freelook_days)) - (t - _d(p["issued"])).days
            fl.append({"policy": p.get("id"), "free_look_days_left": left, "open": left >= 0})
        if p.get("proposal_dob") and p.get("id_dob") and str(p["proposal_dob"]) != str(p["id_dob"]):
            disc.append({"policy": p.get("id"), "issue": "dob on proposal differs from ID"})
    return {"phrase_hits": hits, "free_look": fl, "discrepancies": disc, "decider": "compliance head", "verify": True,
            "note": "Phrase hits are for a human to listen to; none proves mis-selling. Free-look period is the number given (default from memory)."}


def fhir_claim(claim: dict) -> dict[str, Any]:
    need = ["id", "patient_id", "insurer_id", "provider_id", "diagnosis_code", "total", "service_date"]
    miss = [n for n in need if not claim.get(n)]
    if miss:
        raise ValueError("These fields are required: " + ", ".join(miss))
    res = {"resourceType": "Claim", "id": str(claim["id"]), "status": "active", "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/claim-type", "code": claim.get("type", "institutional")}]},
           "use": "claim", "patient": {"reference": f"Patient/{claim['patient_id']}"}, "created": str(claim["service_date"]), "insurer": {"reference": f"Organization/{claim['insurer_id']}"},
           "provider": {"reference": f"Organization/{claim['provider_id']}"}, "priority": {"coding": [{"code": "normal"}]},
           "diagnosis": [{"sequence": 1, "diagnosisCodeableConcept": {"coding": [{"system": claim.get("diagnosis_system", "http://hl7.org/fhir/sid/icd-10"), "code": str(claim["diagnosis_code"])}]}}],
           "insurance": [{"sequence": 1, "focal": True, "coverage": {"reference": f"Coverage/{claim.get('coverage_id', '[coverage id]')}"}}],
           "item": [{"sequence": i + 1, "productOrService": {"coding": [{"code": str(it.get("code", ""))}], "text": it.get("name")}, "net": {"value": _f(it.get("amount")), "currency": "INR"}} for i, it in enumerate(claim.get("items") or [])],
           "total": {"value": _f(claim["total"]), "currency": "INR"}}
    s = round(sum(_f(it.get("amount")) for it in claim.get("items") or []), 2)
    return {"resource": res, "items_sum": s, "total_matches_items": (not claim.get("items")) or abs(s - _f(claim["total"])) < 0.01, "submitted": False,
            "decider": "integration lead", "verify": True, "note": "A plain FHIR R4 Claim skeleton. NHCX / HCX profile fields, consent artefacts and signing are not added; nothing is submitted."}


def code_map(codes: list[str], mapping: dict[str, Any]) -> dict[str, Any]:
    if not codes:
        raise ValueError("codes list do.")
    if not mapping:
        raise ValueError("Give your own mapping table (code -> payer code or list). There is no built-in table.")
    out = []
    for c in codes[:2000]:
        m = mapping.get(c)
        if m is None:
            out.append({"code": c, "status": "unmapped", "payer": None})
        elif isinstance(m, list) and len(m) > 1:
            out.append({"code": c, "status": "ambiguous", "payer": m, "ask": "clinical coder picks"})
        else:
            out.append({"code": c, "status": "mapped", "payer": m[0] if isinstance(m, list) else m})
    return {"rows": out, "unmapped": [r["code"] for r in out if r["status"] == "unmapped"], "ambiguous": [r["code"] for r in out if r["status"] == "ambiguous"],
            "decider": "clinical coder", "note": "Only the mapping table you gave is used."}
