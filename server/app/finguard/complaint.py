"""Paisa Sahayak COMPLAINT drafter (register #8 complaint and Ombudsman drafter).

Builds the letter and the checklist; she sends it herself. Pure text: no network, no model, nothing stored, nothing sent. Any detail she
did not give stays a [blank] (never guessed). A long account / card number is cut to its last 4 digits: a complaint never needs the full one.

Scheme facts (the escalation ladder, response time, who to write to) come from memory, not from a primary source read today: each carries
`verify: true`. Check the bank's grievance page and the RBI Complaint Management System (cms.rbi.org.in) before relying on a date or a limit.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

ISSUES = {
    "unauthorised_txn": {"label": "Unauthorised / fraud transaction", "urgent": True,
                         "evidence": ["Transaction ID / UTR, date, time, amount", "Screenshot of the SMS / email alert", "Screenshot of the number the call / link came from", "Acknowledgement number from 1930 / cybercrime.gov.in",
                                      "When you first told the bank (date, time, call reference)"],
                         "ask": "The unauthorised transaction be reversed at once and the amount credited back to my account, and a written report of the investigation into the cause be given."},
    "failed_txn": {"label": "Transaction failed but money debited", "urgent": False,
                   "evidence": ["Transaction ID / UTR and date", "Account statement showing the debit", "Screenshot of 'failed' in the app", "The merchant's / biller's reply, if you told them"],
                   "ask": "The debited amount be credited back at once, and compensation for the delay be paid as per the rules."},
    "charges": {"label": "Wrong / unexplained charges", "urgent": False,
                "evidence": ["Statement with the charge line marked", "The relevant part of the product terms / fee schedule", "Reference number, if you told anyone earlier"],
                "ask": "The breakup and basis of this charge be given in writing; if it is wrong, it be refunded."},
    "harassment": {"label": "Recovery harassment / threats", "urgent": True,
                   "evidence": ["Call logs (number, date, time)", "Screenshots of messages / recordings", "The agent's name / company, if given", "Any threats or messages sent to others"],
                   "ask": "The harassment of me or my family in the name of recovery be stopped at once and action be taken against the agent / agency involved."},
    "kyc_block": {"label": "Account / card blocked or KYC problem", "urgent": False,
                  "evidence": ["The block / restriction message or screenshot", "KYC documents submitted and the dates", "Any earlier reply from the bank"],
                  "ask": "The reason for the block be given in writing and it be set right within the time limit."},
    "other": {"label": "Other banking / lending complaint", "urgent": False, "evidence": ["All related papers and dates", "Reference of the earlier complaint"],
              "ask": "A written reply and resolution be given on my complaint."},
}

# every line below is from memory: verify
LADDER = [
    {"step": 1, "who": "The bank's / NBFC's complaint service (branch, customer care, app, email)", "do": "Give a written complaint and get a complaint number / receipt.", "verify": False},
    {"step": 2, "who": "The bank's Nodal / Principal Nodal Officer", "do": "If there is no reply or you are not satisfied, write to the officer named on the bank's grievance redressal page (name / email on the bank's site).", "verify": True},
    {"step": 3, "who": "RBI Integrated Ombudsman (cms.rbi.org.in)", "do": "Usually, about 30 days after complaining to the bank, with no reply or an unsatisfactory one, you can complain online; see the scheme's time limits and eligibility on RBI's site.", "verify": True},
    {"step": 4, "who": "Separately, for money fraud", "do": "At once on 1930 / cybercrime.gov.in (do not wait for the ladder).", "verify": True},
]
ESCALATE_AFTER_DAYS = 30            # as recalled from the Ombudsman scheme: verify


def _mask(text: str) -> tuple[str, bool]:
    hit = False

    def sub(m: re.Match) -> str:
        nonlocal hit
        hit = True
        d = re.sub(r"\D", "", m.group(0))
        return "XXXX" + d[-4:]
    return re.sub(r"\b\d(?:[ -]?\d){8,18}\b", sub, text), hit


def _s(v: Any, n: int = 400) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def _day(v: Any) -> str:
    try:
        return date.fromisoformat(str(v or "").strip()[:10]).isoformat()
    except ValueError:
        return ""


def draft(c: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    kind = _s(c.get("issue_type"), 30).lower()
    iss = ISSUES.get(kind) or ISSUES["other"]
    bank = _s(c.get("bank"), 80) or "[bank / NBFC name]"
    who = _s(c.get("name"), 60) or "[your name]"
    narr, m1 = _mask(_s(c.get("narrative"), 1500))
    acct, m2 = _mask(_s(c.get("account"), 40))
    ref, _ = _mask(_s(c.get("txn_ref"), 60))
    amt = _s(c.get("amount"), 20)
    tdate = _day(c.get("txn_date"))
    prior_no, prior_d = _s(c.get("prior_complaint_no"), 40), _day(c.get("prior_date"))
    outcome = _s(c.get("outcome"), 300) or iss["ask"]
    t = today or date.today()
    waited = (t - date.fromisoformat(prior_d)).days if prior_d else None
    esc = ""
    if prior_no and prior_d and waited is not None:
        esc = (f"The earlier complaint ({prior_no}) was made {waited} days ago. " +
               ("It may now be time to go to the Ombudsman (general rule ~30 days: verify on RBI's site)." if waited >= ESCALATE_AFTER_DAYS
                else f"Before the Ombudsman, the bank has about {ESCALATE_AFTER_DAYS - waited} more days to reply (verify the rule)."))
    lines = [f"To,", f"The Nodal / Grievance Officer,", f"{bank}" + (f", {_s(c.get('branch'), 60)}" if c.get("branch") else ""), "",
             f"Date: {t.isoformat()}", f"Subject: Complaint - {iss['label']}" + (f" - Rs {amt}" if amt else ""), "",
             "Respected Sir / Madam,", "",
             f"I, {who}, hold account / card ending {acct[-4:] if acct else '[last 4 digits]'} with you. " + (f"On {tdate} " if tdate else "On [date] ") +
             (f"a transaction of Rs {amt} " if amt else "a transaction ") + (f"(reference {ref}) " if ref else "([reference no.]) ") + "is the subject of this complaint.", "",
             narr or "[Write here in clear words what happened, when, and how you found out.]", ""]
    if prior_no:
        lines += [f"I had earlier raised this with you on {prior_d or '[date]'} (complaint no. {prior_no}) and have not received a satisfactory resolution.", ""]
    lines += [f"I request that: {outcome}", "", "I am attaching the supporting documents listed below. Please acknowledge this complaint with a reference number and reply in writing within the time limit that applies.",
              "", "Yours faithfully,", who, "[Contact number / email]"]
    return {"issue": iss["label"], "letter": "\n".join(lines), "evidence_checklist": iss["evidence"], "urgent": iss["urgent"],
            "urgent_note": "Money fraud or threats: first call the bank and get it blocked and report on 1930 / cybercrime.gov.in, then send this written complaint." if iss["urgent"] else "",
            "escalation": esc, "ladder": LADDER, "masked": bool(m1 or m2),
            "mask_note": "Long account / card numbers were shortened to the last 4 digits: the full number is not needed in the complaint." if (m1 or m2) else "",
            "blanks": [x for x in ("[bank / NBFC name]", "[your name]", "[date]", "[reference no.]", "[last 4 digits]", "[Contact number / email]") if x in "\n".join(lines)],
            "facts_note": "The ladder's time limits and the scheme's rules are written from memory (verify: true): check the bank's grievance page and cms.rbi.org.in.",
            "note": "This is only a draft: sending it is up to you (Hoola sends nothing). Never write the full account / card number, PIN or OTP."}
