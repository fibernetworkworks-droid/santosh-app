"""F1 of docs/FINANCE_GLOBAL_PLAN.md - Money Safety for every country (employee `safety`, tool `paisa_sahayak`).

Parts: check before paying, scam refund claim, card dispute, complaint + ombudsman route, credit report dispute, identity theft recovery,
deposit protection check, and for an institution the case file its staff decide on. Every country rule comes from fin.pack, at the
level decision D3 asks for:

    names, channels, steps        shown at any level; a rule not confirmed is labelled "not confirmed - check this"
    reminders, estimates          need source_read (Hoola read the official page)
    a legal deadline, a refund
    right, a limit applied        need checked (a qualified person confirmed it)

So Hoola never states a deadline it has not confirmed: it shows the rule it has, says it is not confirmed, and asks her to check.
A country with no pack gets the safe steps that are true everywhere and no country rule. Nothing here moves money, files, decides
or sends: letters are drafts she sends, cases are papers a named person decides.
"""
from __future__ import annotations

import calendar
import json
import re
from datetime import date, timedelta
from typing import Any

from .. import laws as L
from .. import pack as P

NOT_CONFIRMED = "not confirmed - check this"
FLOOR_STEPS = [
    "Call your bank or card provider now on the number printed on your card or their official app - not a number from a message.",
    "Ask them to stop or recall the payment and to block the card or account if needed.",
    "Write down what happened, when, the amounts and every reference number; keep screenshots.",
    "Report it to the police or the national fraud reporting service of your country.",
    "Never share a PIN, OTP, password or card security code with anyone who calls or messages you.",
]


class SafetyError(ValueError):
    pass


# ---- reading the pack at the right level -------------------------------------------------------------------------------------

def _cc(a: dict[str, Any]) -> str:
    cc = str(a.get("country") or "").strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", cc):
        raise SafetyError("country: the two-letter country code (for example GB, US, IN, AE, SG, AU, CA, IE, DE, SA).")
    return cc


def rule(cc: str, path: str, need: str = "checked") -> dict[str, Any]:
    """What Hoola has for one rule: its value, its level, whether it is good enough for `need`, and the words to say if not."""
    p = P.load(cc)
    if p is None:
        return {"path": path, "value": None, "status": "missing", "usable": False,
                "says": f"Hoola has no rules for {cc} yet - check this with the official source."}
    try:
        r = P.value_of(cc, path, need=need)
        return {"path": path, "value": r["value"], "status": r["status"], "usable": True, "source": r["source"], "says": ""}
    except P.Unchecked as e:
        val = P.peek(cc, path)
        return {"path": path, "value": val, "status": e.have, "usable": False, "says": str(e)}


def shown(cc: str, path: str) -> Any:
    """A name / channel / step for display. A value below source_read carries the 'not confirmed' label."""
    r = rule(cc, path, need="source_read")
    if r["value"] in (None, "", []):
        return None
    if r["usable"]:
        return r["value"]
    if isinstance(r["value"], list):
        return [f"{x} ({NOT_CONFIRMED})" for x in r["value"]]
    return f"{r['value']} ({NOT_CONFIRMED})"


def _day(s: Any, what: str) -> date:
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        raise SafetyError(f"{what}: a date as YYYY-MM-DD.")


def add_period(start: date, n: int, unit: str) -> date:
    """Calendar arithmetic only. Working days skip Saturday and Sunday; public holidays are NOT known here, so a working-day
    deadline says a public holiday can push it later (see deadline())."""
    n = int(n)
    if unit == "days":
        return start + timedelta(days=n)
    if unit == "weeks":
        return start + timedelta(weeks=n)
    if unit == "working_days":
        d, left = start, n
        while left > 0:
            d += timedelta(days=1)
            if d.weekday() < 5:
                left -= 1
        return d
    if unit in ("months", "years"):
        m = n * (12 if unit == "years" else 1)
        y, mo = divmod(start.month - 1 + m, 12)
        y, mo = start.year + y, mo + 1
        return date(y, mo, min(start.day, calendar.monthrange(y, mo)[1]))
    raise SafetyError(f"unit {unit}")


def deadline(cc: str, path: str, start: date, what: str) -> dict[str, Any]:
    """A time limit from the pack, said at the level it has:
    checked      -> a legal deadline with its date
    source_read  -> a reminder date, said NOT to be a legal deadline
    verify / no  -> no date; the rule Hoola has, labelled not confirmed, and what to check."""
    r = rule(cc, path, need="checked")
    v = r["value"]
    base = {"what": what, "rule_path": path, "status": r["status"]}
    if not isinstance(v, dict) or "n" not in v:
        return {**base, "date": None, "kind": "unknown",
                "says": f"Hoola has no time limit for this in {cc} - check this with your bank or the official source."}
    period = f"{v['n']} {str(v['unit']).replace('_', ' ')}"
    end = add_period(start, v["n"], v["unit"])
    if r["usable"]:
        hol = " (a public holiday can push it later; Hoola does not know the holidays, so act before this date)" if v["unit"] == "working_days" else ""
        return {**base, "date": end.isoformat(), "kind": "deadline", "period": period,
                "says": f"{what}: by {end.isoformat()}{hol} - {period} from {start.isoformat()}."}
    if r["status"] == "source_read":
        return {**base, "date": end.isoformat(), "kind": "reminder", "period": period,
                "says": f"Reminder for {end.isoformat()} ({period} from {start.isoformat()}). This is not a confirmed legal deadline - "
                        f"check it with your bank or the official source."}
    return {**base, "date": None, "kind": "not_confirmed", "period": period,
            "says": f"Hoola's rule for {cc} is {period} for this, but it is {NOT_CONFIRMED}. Act as early as you can and check the "
                    f"real time limit with your bank or the official source."}


def _money(cc: str, x: Any) -> str:
    cur = P.currency_of(cc) or ""
    try:
        return f"{cur} {float(x):,.2f}".strip()
    except (TypeError, ValueError):
        return ""


def _route(cc: str) -> list[dict[str, Any]]:
    """Who to go to, in order. The steps are the same everywhere; the names come from her country's pack."""
    out = [{"step": 1, "who": "Your bank, card provider or payment app", "how": "Their official number or app - never a number from a message."}]
    omb = shown(cc, "ombudsman.name")
    if omb:
        first = rule(cc, "ombudsman.firm_first", need="source_read")
        fv = first["value"]
        wait = f" after {fv['n']} {str(fv['unit']).replace('_', ' ')} without a final answer" if isinstance(fv, dict) else \
               " after the firm's final answer, or if it does not answer"
        if isinstance(fv, dict) and not first["usable"]:
            wait += f" ({NOT_CONFIRMED})"
        out.append({"step": 2, "who": omb, "how": f"Free. Go to them{wait}.", "site": shown(cc, "ombudsman.site")})
    pol = shown(cc, "fraud_report.police")
    if pol:
        out.append({"step": len(out) + 1, "who": pol, "how": "Report the crime; keep the reference number.",
                    "phone": shown(cc, "fraud_report.bank_hotline"), "site": shown(cc, "fraud_report.portal")})
    return out


def _floor(cc: str) -> dict[str, Any]:
    return {"country": cc, "pack": False, "steps": FLOOR_STEPS,
            "says": f"Hoola has no country rules for {cc} yet, so these are the steps that hold everywhere. Check the time limits and "
                    f"who to complain to with your bank or your country's financial regulator."}


def _letter(lines: list[str]) -> str:
    return "\n".join(lines).strip() + "\n"


def _mask(acct: Any) -> str:
    d = re.sub(r"\D", "", str(acct or ""))
    return f"ending {d[-4:]}" if d else "[account, last 4 digits]"


def _b(x: Any, blank: str) -> str:
    s = str(x or "").strip()
    return s if s else f"[{blank}]"


# ---- the parts -------------------------------------------------------------------------------------------------------------

def check_pay(a: dict[str, Any]) -> dict[str, Any]:
    """Before she pays: the message read for scam signs (never opened), plus what to do in HER country if she already paid."""
    cc = _cc(a)
    from ...finguard import scam as SC
    text = str(a.get("text") or "")
    res = SC.check(text, str(a.get("sender") or "")) if text.strip() else {"verdict": "no message given", "families": []}
    extra = []
    if a.get("payee_new"):
        extra.append("A new payee you have not paid before.")
    if a.get("pressure"):
        extra.append("You are being rushed or told to keep it secret.")
    out = {"country": cc, "scam_check": res, "extra_signs": extra,
           "before_paying": ["Stop. Call the person or company back on a number you find yourself.",
                             "A real bank, police or tax office never asks you to move money to keep it safe.",
                             "Never share a PIN, OTP, password or card security code."],
           "if_already_paid": FLOOR_STEPS[:4]}
    if P.load(cc) is None:
        out.update(_floor(cc))
        return out
    out["route"] = _route(cc)
    out["scam_refund_regime"] = shown(cc, "scam_refund.regime")
    return out


def refund_claim(a: dict[str, Any]) -> dict[str, Any]:
    """A scam / unauthorised payment refund claim to her bank, under her country's regime, with the time limit at its level."""
    cc = _cc(a)
    when = _day(a.get("txn_date"), "txn_date")
    seen = _day(a.get("noticed_on") or a.get("txn_date"), "noticed_on")
    if P.load(cc) is None:
        return _floor(cc)
    regime = shown(cc, "scam_refund.regime")
    report = deadline(cc, "scam_refund.report_within", seen, "Tell your bank")
    answer = deadline(cc, "scam_refund.firm_answer_within", seen, "The bank should answer or refund")
    cap = rule(cc, "scam_refund.max_claim", need="checked")
    amount = a.get("amount")
    cap_note = ""
    if cap["value"] not in (None, "") and amount not in (None, ""):
        if cap["usable"]:
            if float(amount) > float(cap["value"]):
                cap_note = f"The most this scheme refunds is {_money(cc, cap['value'])}; your claim is above it."
        else:
            cap_note = f"Hoola's figure for the most this scheme refunds is {_money(cc, cap['value'])}, but it is {NOT_CONFIRMED}."
    kind = str(a.get("kind") or "scam")
    body = _letter([
        f"To: {_b(a.get('bank'), 'your bank')} - fraud / disputes team",
        f"Account: {_mask(a.get('account'))}",
        "",
        f"I am asking for a refund of {_money(cc, amount) or '[amount]'} paid on {when.isoformat()}"
        f" (reference {_b(a.get('txn_ref'), 'transaction reference')}).",
        ("I did not make or allow this payment." if kind == "unauthorised" else
         "I was tricked into making this payment by a scam."),
        f"What happened: {_b(a.get('narrative'), 'what happened, in your words')}",
        f"I noticed it on {seen.isoformat()} and I am reporting it now.",
        (f"I ask you to deal with it under {str(regime).replace(' (' + NOT_CONFIRMED + ')', '')}." if regime else ""),
        "Please confirm in writing that you have received this claim and give me a reference number.",
        "",
        f"{_b(a.get('name'), 'your name')}",
    ])
    return {"country": cc, "part": "refund_claim", "regime": regime, "covers": shown(cc, "scam_refund.covers"),
            "time_limits": [report, answer], "cap": cap_note, "letter": body,
            "evidence": ["Bank statement line or app screenshot", "The scam messages / call log", "Police or fraud report number",
                         "Dates you noticed and reported it"],
            "route": _route(cc), "she_sends": True}


def card_dispute(a: dict[str, Any]) -> dict[str, Any]:
    cc = _cc(a)
    when = _day(a.get("statement_date") or a.get("txn_date"), "txn_date")
    if P.load(cc) is None:
        return _floor(cc)
    lim = deadline(cc, "card_dispute.report_within", when, "Raise the dispute with your card provider")
    reason = str(a.get("reason") or "not_received")
    why = {"not_received": "I paid but the goods or service never arrived.", "not_as_described": "What arrived was not what was described.",
           "charged_twice": "I was charged twice for one purchase.", "cancelled": "I cancelled and was still charged.",
           "unauthorised": "I did not make or allow this payment."}.get(reason, _b(a.get("narrative"), "what went wrong"))
    body = _letter([
        f"To: {_b(a.get('bank'), 'your card provider')} - card disputes",
        f"Card: {_mask(a.get('account'))}",
        "",
        f"I dispute a payment of {_money(cc, a.get('amount')) or '[amount]'} to {_b(a.get('merchant'), 'the shop')} on {when.isoformat()}.",
        why,
        f"I contacted the shop on {_b(a.get('contacted_on'), 'date')} and it did not put this right.",
        "Please raise a chargeback (and any claim my card's law gives me) and confirm in writing.",
        "",
        f"{_b(a.get('name'), 'your name')}",
    ])
    return {"country": cc, "part": "card_dispute", "law": shown(cc, "card_dispute.law"), "time_limits": [lim], "letter": body,
            "evidence": ["Receipt or order confirmation", "Messages with the shop", "Proof it did not arrive or was wrong"],
            "route": _route(cc), "she_sends": True}


def complaint(a: dict[str, Any]) -> dict[str, Any]:
    """A complaint to the firm, and when she may go to her country's ombudsman."""
    cc = _cc(a)
    sent = _day(a.get("complained_on") or date.today().isoformat(), "complained_on")
    if P.load(cc) is None:
        return _floor(cc)
    wait = deadline(cc, "ombudsman.firm_first", sent, "The firm's time to answer before you can go to the ombudsman")
    final = a.get("final_answer_on")
    refer = deadline(cc, "ombudsman.refer_within", _day(final, "final_answer_on"), "Take it to the ombudsman") if final else None
    body = _letter([
        f"To: {_b(a.get('bank'), 'the firm')} - complaints",
        f"Account: {_mask(a.get('account'))}",
        "",
        "This is a formal complaint.",
        f"What went wrong: {_b(a.get('narrative'), 'what happened')}",
        f"What I want: {_b(a.get('outcome'), 'what would put it right')}",
        f"Please send me your final answer in writing. If I am not happy with it I will go to {shown(cc, 'ombudsman.name') or 'the ombudsman'}.",
        "",
        f"{_b(a.get('name'), 'your name')}",
    ])
    return {"country": cc, "part": "complaint", "ombudsman": shown(cc, "ombudsman.name"), "site": shown(cc, "ombudsman.site"),
            "time_limits": [t for t in (wait, refer) if t], "letter": body, "route": _route(cc), "she_sends": True}


def credit_dispute(a: dict[str, Any]) -> dict[str, Any]:
    cc = _cc(a)
    sent = _day(a.get("sent_on") or date.today().isoformat(), "sent_on")
    if P.load(cc) is None:
        return _floor(cc)
    bureaus = shown(cc, "credit_bureaus.list") or []
    answer = deadline(cc, "credit_bureaus.answer_within", sent, "The bureau should answer")
    body = _letter([
        f"To: {_b(a.get('bureau'), 'the credit bureau')} - disputes",
        f"Name: {_b(a.get('name'), 'your name')}   Date of birth: [date of birth]   Address: [address]",
        "",
        f"This entry on my credit report is wrong: {_b(a.get('item'), 'the lender and account shown')}.",
        f"Why it is wrong: {_b(a.get('narrative'), 'why')}",
        "Please investigate, correct or remove it, and send me an updated report.",
    ])
    return {"country": cc, "part": "credit_dispute", "bureaus": bureaus, "free_report": shown(cc, "credit_bureaus.free_report"),
            "time_limits": [answer], "letter": body, "she_sends": True,
            "also": "Send the same dispute to the lender that reported it."}


def id_theft(a: dict[str, Any]) -> dict[str, Any]:
    cc = _cc(a)
    lost = [str(x).lower() for x in (a.get("lost") or [])]
    steps = ["Call each bank and card provider on their official number: block cards, change passwords, ask for a fraud marker.",
             "Change your email password first, then every money app; turn on two-step sign-in."]
    if P.load(cc) is None:
        return {**_floor(cc), "steps": steps + FLOOR_STEPS[3:]}
    rep = shown(cc, "identity_theft.report_to")
    frz = shown(cc, "identity_theft.freeze")
    bur = shown(cc, "credit_bureaus.list") or []
    if rep:
        steps.append(f"Report it: {rep}.")
    if frz:
        steps.append(f"Protect your credit file: {frz}.")
    if bur:
        steps.append("Get your report from each bureau and dispute anything you did not open: " + ", ".join(bur) + ".")
    if any(x in ("passport", "id", "id card", "driving licence", "license") for x in lost):
        steps.append("Report the lost ID document to the office that issued it and ask how to cancel it.")
    if "phone" in lost or "sim" in lost:
        steps.append("Ask your mobile network to block the SIM so codes cannot be read.")
    return {"country": cc, "part": "id_theft", "steps": steps, "route": _route(cc)}


def deposit_check(a: dict[str, Any]) -> dict[str, Any]:
    """Her balances per bank against her country's deposit protection. A conclusion only when the limit is checked."""
    cc = _cc(a)
    if P.load(cc) is None:
        return _floor(cc)
    per: dict[str, float] = {}
    for b in a.get("balances") or []:
        name = str(b.get("bank") or "").strip()
        if not name:
            raise SafetyError("balances: [{bank, amount}].")
        per[name] = per.get(name, 0.0) + float(b.get("amount") or 0)
    lim = rule(cc, "deposit_insurance.limit", need="checked")
    est = rule(cc, "deposit_insurance.limit", need="source_read")
    rows = []
    for name, amt in sorted(per.items()):
        row = {"bank": name, "total": round(amt, 2)}
        if lim["value"] not in (None, ""):
            over = max(0.0, amt - float(lim["value"]))
            if lim["usable"]:
                row.update(protected=round(min(amt, float(lim["value"])), 2), above_limit=round(over, 2))
            elif est["usable"]:
                row.update(estimate_above_limit=round(over, 2))
            else:
                row.update(above_unconfirmed_limit=round(over, 2))
        rows.append(row)
    if lim["value"] in (None, ""):
        says = f"Hoola has no deposit protection limit for {cc}: {shown(cc, 'deposit_insurance.scheme') or 'check with the regulator'}."
    elif lim["usable"]:
        says = f"Protected up to {_money(cc, lim['value'])} {P.peek(cc, 'deposit_insurance.per') or ''}.".strip()
    else:
        says = (f"Hoola's figure is {_money(cc, lim['value'])} {P.peek(cc, 'deposit_insurance.per') or ''}, but it is {NOT_CONFIRMED}; "
                f"banks in one group may share one limit.").strip()
    return {"country": cc, "part": "deposit_check", "scheme": shown(cc, "deposit_insurance.scheme"), "banks": rows, "says": says}


def case_prep(a: dict[str, Any], ws: dict[str, Any] | None = None) -> dict[str, Any]:
    """Institution side: the case file a named member of staff decides. Hoola prepares; it never decides, refunds or closes."""
    cc = _cc(a)
    kind = str(a.get("case_kind") or "scam")
    opened = _day(a.get("opened_on") or date.today().isoformat(), "opened_on")
    if kind not in ("scam", "dispute", "complaint"):
        raise SafetyError("case_kind: scam | dispute | complaint.")
    clocks = []
    if P.load(cc) is not None:
        if kind == "scam":
            clocks.append(deadline(cc, "scam_refund.firm_answer_within", opened, "Answer or reimburse the customer"))
        elif kind == "dispute":
            clocks.append(deadline(cc, "card_dispute.report_within", _day(a.get("txn_date") or opened.isoformat(), "txn_date"),
                                   "Customer's own time limit to dispute"))
        else:
            clocks.append(deadline(cc, "ombudsman.firm_first", opened, "Final answer before the customer may go to the ombudsman"))
    need = {"scam": ["Customer statement in their words", "Payment details and timestamps", "Warnings shown at payment time",
                     "Receiving bank contact made"],
            "dispute": ["Transaction record", "Merchant contact evidence", "Chargeback reason code"],
            "complaint": ["The complaint as received", "Account notes", "What the customer wants"]}[kind]
    have = [str(x) for x in (a.get("evidence") or [])]
    missing = [n for n in need if not any(n.split()[0].lower() in h.lower() for h in have)]
    decider = L.decider(ws or {}, "safety")
    return {"country": cc, "part": "case_prep", "case_kind": kind, "clocks": clocks, "evidence_have": have, "evidence_missing": missing,
            "decision": {"outcome": "", "decided_by": "", "decider_role": decider,
                         "says": "Left blank on purpose: a named member of staff decides. Hoola does not decide, refund or close cases."},
            "draft_to_customer": _letter(["Thank you for telling us. We have opened a case and will write to you with our answer.",
                                          "We will not ask you for your PIN, password or one-time code."]),
            "regime": shown(cc, "scam_refund.regime") if P.load(cc) else None}


PARTS = {"check_pay": check_pay, "refund_claim": refund_claim, "card_dispute": card_dispute, "complaint_global": complaint,
         "credit_dispute": credit_dispute, "id_theft": id_theft, "deposit_check": deposit_check, "case_prep": case_prep}
LETTERS = ("refund_claim", "card_dispute", "complaint_global", "credit_dispute", "case_prep")


# ---- cases (stored, so she can track them) ----------------------------------------------------------------------------------

def save_case(tenant: str, part: str, out: dict[str, Any], workspace_id: str = "") -> str:
    from ... import db
    from .. import models as M
    M.ensure()
    due = ""
    for t in out.get("time_limits") or out.get("clocks") or []:
        if t.get("kind") == "deadline" and t.get("date"):
            due = t["date"] if not due else min(due, t["date"])
    title = {"refund_claim": "Refund claim", "card_dispute": "Card dispute", "complaint_global": "Complaint",
             "credit_dispute": "Credit report dispute", "case_prep": "Case file"}.get(part, part)
    with db.session() as s:
        c = M.FinCase(tenant_id=tenant, workspace_id=workspace_id, employee="safety", part=part,
                      title=f"{title} ({out.get('country', '')})", state="drafted", due=due,
                      decider=(out.get("decision") or {}).get("decider_role", "") if part == "case_prep" else "you")
        s.add(c)
        s.flush()
        body = out.get("letter") or out.get("draft_to_customer") or ""
        from ..evidence import digest
        s.add(M.FinDraft(tenant_id=tenant, workspace_id=workspace_id, case_id=c.id, kind="letter", body=body,
                         hash=digest({"body": body}), state="waiting"))
        s.commit()
        return c.id


def cases(tenant: str) -> list[dict[str, Any]]:
    from ... import db
    from .. import models as M
    M.ensure()
    with db.session() as s:
        rows = s.query(M.FinCase).filter(M.FinCase.tenant_id == tenant, M.FinCase.employee == "safety") \
            .order_by(M.FinCase.created_at.desc()).limit(100).all()
        return [{"id": r.id, "part": r.part, "title": r.title, "state": r.state, "due": r.due, "decider": r.decider,
                 "created_at": r.created_at.isoformat() if r.created_at else ""} for r in rows]


def run(tenant: str, action: str, a: dict[str, Any]) -> dict[str, Any]:
    if action == "cases":
        return {"cases": cases(tenant)}
    fn = PARTS.get(action)
    if fn is None:
        raise SafetyError(f"Unknown part {action}.")
    if action == "case_prep":
        ws = None
        if a.get("workspace"):
            from .. import profile as PR
            ws = PR.get(tenant, str(a["workspace"]))
        out = case_prep(a, ws)
    else:
        out = fn(a)
    if action in LETTERS and out.get("pack", True) is not False and a.get("save", True) is not False:
        out["case_id"] = save_case(tenant, action, out, str(a.get("workspace") or ""))
    out.setdefault("not_advice", L.NOT_ADVICE)
    return json.loads(json.dumps(out, default=str))
