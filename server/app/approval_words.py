"""v0.191 SAMAJHDAR CARD — ek hi jagah approval ki boli (owner: "NOT ONLY HAAN, ANY KARDO, APPROVE HAI ETC").

Jab koi PC / browser step uski manzoori ka intezaar karta hai aur woh BOLTI ya LIKHTI hai, to yeh module
tay karta hai ki uske shabdon ka matlab manzoori hai, mana karna hai, ya paise wali manzoori hai (jo bol se
kabhi nahi hoti). Teen sawaal:

  * is_approval("haan karo" / "approve hai" / "theek hai" / "confirm" / "yes" / "kar do" ...) -> True
  * is_rejection("nahi" / "mat karo" / "rehne do" / "cancel" ...) -> True (rejection hamesha jeet'ti hai)
  * is_pure_approval / approve_lead  -> kya POORA uttar hi manzoori hai (turant card resolve), ya manzoori
    ke aage baat bhi hai (card resolve + baaki baat ka jawab normal tarike se)
  * money_risk("pay kar do" / "₹500" / "otp" / "card number" ...) -> True = bol se manzoori KABHI nahi
    (money / UPI / bank-OTP card par hi: tap + PIN/fingerprint — wahi purana safety gate)

Hinglish + English + Devanagari (हाँ / नहीं / ठीक है ...) — transcripts dono script mein aate hain.
Rejection hamesha approval par bhaari: "haan... nahi ruko" ko manzoori nahi maana jayega.
"""
from __future__ import annotations

import re

# ---- tokens ----------------------------------------------------------------
APPROVAL_TOKENS = {
    # haan family
    "haan", "han", "haa", "haanji", "hanji", "haanye", "हाँ", "हां", "हा", "जी",
    # english yes family
    "yes", "yeah", "yess", "yep", "yup", "sure", "okay", "ok", "okie", "okey",
    # theek / sahi
    "theek", "thik", "tik", "sahi", "barabar", "ठीक", "सही", "बराबर",
    # manzoori
    "manzoor", "manzuri", "qabool", "kabool", "मंज़ूर", "मंजूर", "क़बूल", "कबूल",
    # approve / confirm
    "approve", "approved", "approval", "confirm", "confirmed",
    # karo family
    "karo", "kardo", "krdo", "kariye", "kardijiye", "kardena", "karlo", "krlo", "karlena",
    "kar", "do", "dijiye", "dedo", "dena", "lo", "lena", "करो", "कर", "दो", "करदो", "कीजिए", "दीजिए",
    # aage badho family
    "badho", "badhao", "aage", "chalo", "shuru", "start", "proceed", "continue", "go", "ahead", "आगे", "बढ़ो", "चलो",
    # bhejo / submit
    "bhejo", "bhejdo", "bhej", "send", "submit", "भेजो", "भेज",
    # pakka / done
    "pakka", "pukka", "पक्का", "done", "होजाए", "होजाये",
}
FILLER_TOKENS = {"ji", "hai", "hain", "naa", "please", "plz", "pls", "bhai", "yaar", "arre", "arey", "achha",
                 "अच्छा", "जी", "है", "हैं", "par", "per", "lekin", "magar", "bhi", "पर", "लेकिन", "भी"}
REJECT_TOKENS = {
    "nahi", "nahin", "nai", "nhin", "no", "nope", "na", "नहीं", "ना", "नहि",
    "mat", "मत", "ruko", "ruk", "rukna", "rukiye", "roko", "rok", "rokna", "rukjao", "रुको", "रोको", "रुक",
    "cancel", "cancelled", "रद्द", "band", "बंद", "chhodo", "chhod", "chodo", "rehne", "छोड़ो", "रहने",
    "leave", "skip", "later", "wait", "hold", "intezaar", "इंतज़ार", "galat", "wrong", "गलत", "wapis", "wapas", "वापस",
}
# money /OTP / password: bol se manzoori KABHI nahi (card par hi: tap + PIN / fingerprint)
MONEY_RE = re.compile(
    r"(₹|\$\s?\d|\brs\.?\s*\d|\b\d+\s*(rs|rupees?|rupaye|rupya)\b|\b(pay|payment|paid|paise|paisa|rupaye|rupya|"
    r"rupaiya|rupees?|rupee|money|upi|bank|netbanking|netbank|imps|neft|wallet|paytm|phonepe|gpay|googlepay|"
    r"credit|debit|cvv|otp|one\s?time\s?password|password|passcode|pincode|pin|card|cheque)\b)", re.I)
MAX_PURE_TOKENS = 5      # "haan karo" / "haan sahi hai" — poora uttar hi manzoori
MAX_LEAD_TOKENS = 7      # "haan, address yeh raha" / "haan par cheese burst bhi add karo" — manzoori shuru mein

# latin words OR poore Devanagari runs (candrabindu/anusvara/nukta marks beech mein na kate — Python \w inhe tor deta hai)
_TOK = re.compile(r"[a-z]+|[\u0900-\u097F]+", re.UNICODE)


def tokens(text: str) -> list[str]:
    """Significant tokens (numbers dropped; Hinglish + Devanagari dono)."""
    return _TOK.findall((text or "").lower())


def _has(toks: list[str], bag: set[str]) -> bool:
    return any(t in bag for t in toks)


# ---- the three questions ---------------------------------------------------
def is_rejection(text: str) -> bool:
    """'nahi' / 'mat karo' / 'rehne do' / 'cancel' ... — rejection hamesha jeet'ti hai."""
    return _has(tokens(text), REJECT_TOKENS)


def is_approval(text: str) -> bool:
    """Approval words present AND no rejection word anywhere."""
    toks = tokens(text)
    return bool(toks) and _has(toks, APPROVAL_TOKENS) and not _has(toks, REJECT_TOKENS)


def might_answer(text: str) -> bool:
    """Cheap pre-check before touching the DB: could these words be an answer to a pending approval?"""
    toks = tokens(text)
    return _has(toks, APPROVAL_TOKENS) or _has(toks, REJECT_TOKENS)


def is_pure_approval(text: str) -> bool:
    """POORA uttar hi manzoori hai: 'haan', 'haan karo', 'approve hai', 'theek hai', 'yes confirm', 'हाँ कर दो'."""
    toks = tokens(text)
    if not toks or len(toks) > MAX_PURE_TOKENS:
        return False
    if _has(toks, REJECT_TOKENS) or not _has(toks, APPROVAL_TOKENS):
        return False
    return all(t in APPROVAL_TOKENS or t in FILLER_TOKENS for t in toks)


def approve_lead(text: str) -> bool:
    """Manzoori shuru mein hai aur uttar chhota hai: 'haan, address yeh raha' (card resolve + baaki baat normal).
    'pizza order karo' jaise NAYE kaam ke commands yahan NAHI aate — pehla shabd manzoori ka nahi hai."""
    toks = tokens(text)
    if not toks or len(toks) > MAX_LEAD_TOKENS:
        return False
    if _has(toks, REJECT_TOKENS) or toks[0] not in APPROVAL_TOKENS:
        return False
    return True


def is_pure_rejection(text: str) -> bool:
    """Poora uttar hi mana karna hai: 'nahi', 'mat karo', 'cancel karo', 'rehne do'. 'mat' / 'nahi' ke BAAD ke
    approval shabd ulte ho jate hain ('mat karo' = mana, manzoori nahi), isliye unhe nikaal kar dekha jata hai."""
    toks = tokens(text)
    if not toks or len(toks) > 4 or not _has(toks, REJECT_TOKENS):
        return False
    first = next(i for i, t in enumerate(toks) if t in REJECT_TOKENS)
    kept = [t for i, t in enumerate(toks) if i < first or t in REJECT_TOKENS or t in FILLER_TOKENS]
    return bool(kept) and all(t in REJECT_TOKENS or t in FILLER_TOKENS for t in kept)


def money_risk(text: str) -> bool:
    """Paise / UPI / bank-OTP / password / card wali baat: bol se manzoori nahi hoti, card par hoti hai."""
    return bool(MONEY_RE.search(text or ""))
