"""Reading a payment app's notification: is it money COMING IN, how much, from whom, which reference.

The same rules run on the phone (tool/android/kotlin/PayAlerts.kt) so only the result leaves the phone: amount, time,
app, the payer's first name and the last 4 digits of the reference. Anything that is not a plain credit is dropped:
money sent, requests, failures, refunds, cashback, offers, bills, and ANY text with an OTP / PIN / password in it.
Kept in step with PayAlerts.kt (tests check the same samples)."""
from __future__ import annotations

import re

# merchant apps (verified on Google Play, Oct 2026) are on by default; personal UPI apps only if she turns them on
APPS: dict[str, dict] = {
    "com.phonepe.app.business": {"label": "PhonePe Business", "default": True},
    "com.paytm.business": {"label": "Paytm for Business", "default": True},
    "com.google.android.apps.nbu.paisa.merchant": {"label": "Google Pay for Business", "default": True},
    "com.bharatpe.app": {"label": "BharatPe for Business", "default": True},
    "com.phonepe.app": {"label": "PhonePe", "default": False},
    "com.google.android.apps.nbu.paisa.user": {"label": "Google Pay", "default": False},
    "net.one97.paytm": {"label": "Paytm", "default": False},
    "in.org.npci.upiapp": {"label": "BHIM", "default": False},
}

SECRET = re.compile(r"\botp\b|one[\s-]?time|pass(?:word|code)|\bm?pin\b|\bcvv\b|verification code", re.I)
NOT_CREDIT = re.compile(
    r"\b(sent|paid to|you paid|debited|debit|withdrawn|request(?:ed|ing)?|requests|collect request|failed|failure|"
    r"declined|pending|refund(?:ed)?|reversed|cashback|reward|scratch|offer|win|won|bill|due|reminder|recharge|"
    r"loan|emi|insurance|transfer(?:red)? to|kyc|settle|settled|settlement|summary|total|payments|transactions|wallet|"
    r"statement)\b|भेजे|कटे|डेबिट|कुल", re.I)
CREDIT = re.compile(
    r"\b(received|receive|paid you|has paid|credited|credit of|collected|payment successful from)\b|"
    r"जमा|प्राप्त|मिले|मिला|आए|आये", re.I)
AMOUNT = re.compile(r"(?:₹|rs\.?|inr)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", re.I)
PAYER_FROM = re.compile(r"\bfrom\s+([A-Za-z][A-Za-z .'&-]{1,40})", re.I)
PAYER_BY = re.compile(r"\b(?:credited|paid)\b.*?\bby\s+([A-Za-z][A-Za-z .'&-]{1,40})", re.I)
PAYER_PAID = re.compile(r"^\s*([A-Za-z][A-Za-z .'&-]{1,40}?)\s+(?:has\s+)?paid you", re.I)
REF = re.compile(r"(?:utr|rrn|ref(?:erence)?(?:\s*no\.?)?|txn(?:\s*id)?|upi\s*ref(?:\.|erence)?(?:\s*no\.?)?)[\s:#.-]*([0-9]{6,})", re.I)
MAX_RUPEES = 200000


def _first_name(raw: str) -> str:
    w = re.sub(r"[^A-Za-z .'-]", " ", raw or "").strip().split()
    skip = {"mr", "mrs", "ms", "shri", "smt", "dr", "upi", "via", "the"}
    w = [x for x in w if x.lower().strip(".") not in skip]
    return (w[0][:20].title() if w else "")


def parse_alert(title: str, text: str) -> dict | None:
    """{'amount': rupees, 'payer': 'Ramesh', 'ref_tail': '4821'} for a plain credit, else None."""
    full = re.sub(r"\s+", " ", f"{title or ''} {text or ''}").strip()
    if not full or SECRET.search(full):
        return None
    if not CREDIT.search(full) or NOT_CREDIT.search(full):
        return None
    m = AMOUNT.search(full)
    if not m:
        return None
    try:
        amt = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    if not (0 < amt <= MAX_RUPEES):
        return None
    payer = ""
    pm = PAYER_PAID.search(text or "") or PAYER_PAID.search(title or "") or PAYER_FROM.search(full) or PAYER_BY.search(full)
    if pm:
        payer = _first_name(pm.group(1))
    r = REF.search(full)
    return {"amount": round(amt, 2), "payer": payer, "ref_tail": r.group(1)[-4:] if r else ""}
