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
                         "evidence": ["Transaction ID / UTR, tareekh, samay, rakam", "SMS / email alert ki screenshot", "Jis number se call / link aaya uska screenshot", "1930 / cybercrime.gov.in ki acknowledgement number",
                                      "Bank ko pehli baar kab bataya (tareekh, samay, call reference)"],
                         "ask": "Anadhikrit transaction ko turant reverse karke raashi mere khate mein wapas daali jaye, aur kaaran ki jaanch ki likhit report di jaye."},
    "failed_txn": {"label": "Transaction failed but money debited", "urgent": False,
                   "evidence": ["Transaction ID / UTR aur tareekh", "Khate ka statement jis mein debit dikhe", "App par 'failed' ka screenshot", "Merchant / biller ko bataya to uska jawab"],
                   "ask": "Debit hui raashi turant wapas credit ki jaye, aur niyam ke mutabik deri ka muavza diya jaye."},
    "charges": {"label": "Wrong / unexplained charges", "urgent": False,
                "evidence": ["Statement jis mein charge ki line chinhit ho", "Product ke terms / fee schedule ka hissa", "Pehle se kisi ko bataya ho to reference number"],
                "ask": "Is charge ka breakup aur adhaar likhit mein bataya jaye; galat ho to wapas kiya jaye."},
    "harassment": {"label": "Recovery harassment / threats", "urgent": True,
                   "evidence": ["Call logs (number, tareekh, samay)", "Message / recording ki screenshot", "Agent ka naam / company agar bataya ho", "Koi dhamki ya doosron ko bheje message"],
                   "ask": "Recovery ke naam par mujhe ya mere parivar ko pareshan karna turant roka jaye aur ismein shaamil agent / agency par karyavahi ki jaye."},
    "kyc_block": {"label": "Account / card blocked or KYC problem", "urgent": False,
                  "evidence": ["Block / restriction ka message ya screenshot", "Diye gaye KYC dastavez aur tareekh", "Bank ka koi bhi pichla jawab"],
                  "ask": "Rok ka kaaran likhit mein bataya jaye aur samay-seema ke andar sahi kiya jaye."},
    "other": {"label": "Other banking / lending complaint", "urgent": False, "evidence": ["Sab sambandhit kaagaz aur tareekhein", "Pehle ki shikayat ka reference"],
              "ask": "Meri shikayat par likhit jawab aur samadhan diya jaye."},
}

# every line below is from memory: verify
LADDER = [
    {"step": 1, "who": "Bank / NBFC ki shikayat sewa (branch, customer care, app, email)", "do": "Likhit shikayat dijiye aur complaint number / receipt le lijiye.", "verify": False},
    {"step": 2, "who": "Bank ke Nodal / Principal Nodal Officer", "do": "Agar jawab nahi aaya ya santusht nahi, bank ke grievance redressal page par diye adhikari ko likhiye (naam / email bank ki site par).", "verify": True},
    {"step": 3, "who": "RBI Integrated Ombudsman (cms.rbi.org.in)", "do": "Aam taur par bank ko shikayat ke ~30 din baad bina jawab ya asantushti par online shikayat kar sakte hain; scheme ki samay-seema aur paatrata RBI ki site par dekhiye.", "verify": True},
    {"step": 4, "who": "Paise ki dhokhadhadi ke liye alag", "do": "1930 / cybercrime.gov.in par turant (ladder ka intezaar mat kijiye).", "verify": True},
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
    bank = _s(c.get("bank"), 80) or "[bank / NBFC ka naam]"
    who = _s(c.get("name"), 60) or "[aapka naam]"
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
        esc = (f"Pichli shikayat ({prior_no}) ko {waited} din ho gaye. " +
               ("Ab Ombudsman tak jaane ka samay ho sakta hai (aam niyam ~30 din: RBI site par verify kijiye)." if waited >= ESCALATE_AFTER_DAYS
                else f"Ombudsman se pehle bank ko jawab ke liye ~{ESCALATE_AFTER_DAYS - waited} din aur (niyam verify kijiye)."))
    lines = [f"To,", f"The Nodal / Grievance Officer,", f"{bank}" + (f", {_s(c.get('branch'), 60)}" if c.get("branch") else ""), "",
             f"Date: {t.isoformat()}", f"Subject: Complaint - {iss['label']}" + (f" - Rs {amt}" if amt else ""), "",
             "Respected Sir / Madam,", "",
             f"I, {who}, hold account / card ending {acct[-4:] if acct else '[last 4 digits]'} with you. " + (f"On {tdate} " if tdate else "On [date] ") +
             (f"a transaction of Rs {amt} " if amt else "a transaction ") + (f"(reference {ref}) " if ref else "([reference no.]) ") + "is the subject of this complaint.", "",
             narr or "[Yahan saaf shabdon mein likhiye kya hua, kab, aur kaise pata chala.]", ""]
    if prior_no:
        lines += [f"I had earlier raised this with you on {prior_d or '[date]'} (complaint no. {prior_no}) and have not received a satisfactory resolution.", ""]
    lines += [f"I request that: {outcome}", "", "I am attaching the supporting documents listed below. Please acknowledge this complaint with a reference number and reply in writing within the time limit that applies.",
              "", "Yours faithfully,", who, "[Contact number / email]"]
    return {"issue": iss["label"], "letter": "\n".join(lines), "evidence_checklist": iss["evidence"], "urgent": iss["urgent"],
            "urgent_note": "Paise ki dhokhadhadi ya dhamki: pehle bank ko call karke band karwaiye aur 1930 / cybercrime.gov.in par report kijiye, phir yeh likhit shikayat bhejiye." if iss["urgent"] else "",
            "escalation": esc, "ladder": LADDER, "masked": bool(m1 or m2),
            "mask_note": "Lambe account / card number aakhri 4 ank tak chhote kar diye gaye: shikayat mein poora number zaroori nahi." if (m1 or m2) else "",
            "blanks": [x for x in ("[bank / NBFC ka naam]", "[aapka naam]", "[date]", "[reference no.]", "[last 4 digits]", "[Contact number / email]") if x in "\n".join(lines)],
            "facts_note": "Ladder ki samay-seemaein aur scheme ke niyam yaad se likhe hain (verify: true): bank ki grievance page aur cms.rbi.org.in par dekh lijiye.",
            "note": "Yeh sirf draft hai: bhejna aapka kaam hai (Hoola kuch nahi bhejta). Poora account / card number, PIN ya OTP kabhi mat likhiye."}
