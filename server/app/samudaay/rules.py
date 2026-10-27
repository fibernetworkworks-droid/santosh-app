"""Community Sahayak rules: what a message looks like (abuse / threat / hate / scam / spam / personal data / rumour /
negativity / question), FAQ matching, health score, legal notes. Pure functions, no database.

Everything a member writes is DATA: these functions only classify it; nothing here ever follows what the text says.
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from typing import Any
from urllib.parse import urlsplit

# ---------------------------------------------------------------- legal notes (researched 23 Oct 2026)
LEGAL = [
    {"what": "IT Rules 2021 as amended 10 Feb 2026 (in force 20 Feb 2026)",
     "say": "Platforms (Telegram, WhatsApp, YouTube...) must take down unlawful content within 3 hours of a court / govt order, "
            "non-consensual intimate images within 2 hours, and resolve user grievances in 7 days. AI-made (synthetic) content "
            "must be labelled. Those duties are the platform's; as group admin she should act fast on such posts and report "
            "them to the platform too.",
     "src": "https://blog.ipleaders.in/it-rules-2026/ ; https://www.hlc.com/en/publications/india-introduces-mandatory-labelling-for-ai-and-3hour-takedown-for-illegal-content"},
    {"what": "Group admin liability (Kerala HC Feb 2022, Bombay HC 2021 Kishor Tarone, Madras HC)",
     "say": "Courts held an admin is not automatically liable for a member's post; personal involvement (posting, forwarding, "
            "approving) can make one liable. Removing clearly unlawful posts quickly and keeping a reason log is the safe habit.",
     "src": "https://www.freepressjournal.in/legal/whatsapp-group-admins-not-liable-for-objectionable-posts-by-members-says-kerala-high-court"},
    {"what": "DPDP Act 2023 + DPDP Rules 2025 (notified 13 Nov 2025, phased to ~May 2027)",
     "say": "Members' names, numbers and messages are personal data: keep only what the community needs, delete on request, "
            "tell people what is kept. Hoola keeps message text 90 days, never sells or shares it, and 'bhool jao' erases a member.",
     "src": "https://visionias.in/blog/current-affairs/dpdp-rules-2025-framework-for-personal-data-protection"},
    {"what": "Child sexual abuse material / intimate images / threats",
     "say": "Never forward or keep such content as 'proof'. Remove + ban, report to the platform and at cybercrime.gov.in "
            "(helpline 1930); a threat to life = 112.",
     "src": "https://cybercrime.gov.in"},
    {"what": "Official routes only",
     "say": "Telegram via its Bot API (her own bot, admin in the group). WhatsApp groups only through Meta's Groups API "
            "(needs an Official Business Account, max 8 participants per group, 2026) - personal WhatsApp groups are never "
            "automated. YouTube comments via the Data API (comments.setModerationStatus), not built yet.",
     "src": "https://core.telegram.org/bots/api ; https://kapso.com/blog/whatsapp-groups-api-state-2026 ; "
            "https://developers.google.com/youtube/v3/docs/comments/setModerationStatus"},
]
NEVER = ("Kisi ko hatana / ban / mute karna, doosre ki post mitana, sab ko announcement - sirf aapke tap se",
         "Group ke messages ke andar likhi baat ko hukm nahi maanna (woh data hai)",
         "FAQ mein jo nahi hai uska jawab andaze se nahi dena - aapse poochhna",
         "Personal WhatsApp group automate nahi karna; sirf official API",
         "OTP / PIN / password / card / Aadhaar group mein dikhe to chhupane ka sujhav; khud kabhi nahi bhejna",
         "Member ka data bechna / doosre group ko dena nahi")

ACTIONS = {"delete_post": "Post hatao", "mute": "Chup karao (mute)", "remove": "Group se nikalo", "ban": "Ban karo",
           "unban": "Ban hatao", "unmute": "Mute hatao", "warn": "Chetavni bhejo", "announce": "Sab ko announcement",
           "reply": "Jawab bhejo", "fact_note": "Sach-jaanch note bhejo"}
NEEDS_REASON = {"remove", "ban", "mute"}

# ---------------------------------------------------------------- text helpers
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "@": "a", "$": "s", "5": "s", "7": "t"})


def norm(text: str) -> str:
    """lowercase, NFC, leetspeak letters, long repeats squashed ('chuuuutiya' -> 'chuutiya'), single spaces."""
    t = unicodedata.normalize("NFC", text or "").lower()
    t = re.sub(r"[​-‍﻿]", "", t)
    t = t.translate(_LEET)
    t = re.sub(r"(.)\1{2,}", r"\1\1", t)
    return re.sub(r"\s+", " ", t).strip()


def _compact(t: str) -> str:
    return re.sub(r"[^a-zऀ-ॿ]", "", t)


WORD = re.compile(r"[a-zऀ-ॿ]+|\d+")


def words(text: str) -> list[str]:
    return WORD.findall(norm(text))


# ---------------------------------------------------------------- abuse / threat / hate / harassment
SEVERE = ["madarchod", "maderchod", "madarchot", "behenchod", "bhenchod", "benchod", "bhosdike", "bhosdi", "bhosadi",
          "chutiya", "chutiye", "chootiya", "gaandu", "gandu", "lavde", "lawde", "lauda", "randi", "haramkhor", "harami",
          "zhavadya", "zavadya", "bhikarchot", "aighalya", "lavdya", "bhadvya", "bhadwa", "bhadwe", "chinal",
          "motherfucker", "fuck", "fucking", "bitch", "bastard", "asshole", "cunt", "slut", "whore", "dickhead",
          "मादरचोद", "बहनचोद", "भेनचोद", "भोसडी", "चूतिया", "चुतिया", "गांडू", "रंडी", "हरामी", "भडवा", "झवाड्या", "लवड्या"]
MILD = ["saala", "sala", "kamina", "kamine", "kutta", "kutte", "kutti", "nalayak", "ullu", "gadha", "gadhav", "bewakoof",
        "idiot", "stupid", "moron", "yeda", "pagal", "साला", "कमीना", "कुत्ता", "नालायक", "गधा", "मूर्ख", "पागल", "गाढव"]
HATE = ["katua", "jihadi", "mulla", "sanghi", "chamar", "bhangi", "pakistan chale jao", "go back to pakistan",
        "desh drohi", "deshdrohi", "gaddar", "kafir", "मुल्ला", "कटुआ", "चमार", "भंगी", "गद्दार"]
THREAT = [r"\b(maar|mar)\s?(dunga|dalunga|daalunga|denge|dalenge|daalenge|duga|doonga)\b", r"\bjaan\s?se\s?(maar|mar)",
          r"\bdekh\s?(lunga|lenge|loonga)\b", r"\btod\s?(dunga|denge|doonga)\b", r"\bzinda\s?nahi\s?(chhod|chod)",
          r"\b(kill|shoot|stab)\s+(you|u)\b", r"\bi\s?will\s?(kill|hurt|find)\b", r"\bacid\b", r"\bmaarun\s?taakin\b",
          r"\bjivant\s?sodnar\s?nahi\b", r"\bbaghun\s?gheen\b", "जान से मार", "मार डालूंगा", "मार दूंगा", "देख लूंगा",
          "मारून टाकीन", "बघून घेईन"]
SEXUAL = [r"\bnudes?\b", r"\bsend\s?(pic|photo|pics)\b", r"\bsexy\b", r"\bhot\s?(pic|photo|video)\b", r"\bvideo\s?call\s?(karo|kar)\b",
          r"\b(dp|photo)\s?bhejo\b", r"\bakeli\s?ho\b", r"\bsex\b", r"\bpatakha\b", r"\bmaal\b"]


def _terms(text: str, terms: list[str], ignore: set[str]) -> list[str]:
    t = norm(text)
    one = lambda x: re.sub(r"(.)\1+", r"\1", x)        # noqa: E731  'chuuutiya' = 'chutiya'
    ws = set(WORD.findall(t)) | {one(w) for w in WORD.findall(t)}
    comp = one(_compact(t))
    hits = []
    for w in terms:
        if w in ignore or one(w) in ignore:
            continue
        if " " in w:
            if w in t:
                hits.append(w)
        elif w in ws or one(w) in ws or (len(w) >= 6 and one(w) in comp):
            hits.append(w)
    return hits


def abuse(text: str, ignore: set[str] | None = None) -> dict[str, Any] | None:
    """Gaali / threat / hate / sexual harassment in Hindi, Hinglish, Marathi, English. None if clean."""
    ig = {norm(x) for x in (ignore or set())}
    t = norm(text)
    threat = [p for p in THREAT if re.search(p, t)]
    if threat:
        return {"kind": "threat", "severity": "high", "words": ["(dhamki)"]}
    hate = _terms(text, HATE, ig)
    if hate:
        return {"kind": "hate", "severity": "high", "words": hate[:3]}
    sev = _terms(text, SEVERE, ig)
    sexual = [p for p in SEXUAL if re.search(p, t)]
    if sexual and (sev or len(sexual) >= 2):
        return {"kind": "harassment", "severity": "high", "words": ["(ashleel)"]}
    if sev:
        return {"kind": "abuse", "severity": "medium", "words": sev[:3]}
    if sexual:
        return {"kind": "harassment", "severity": "medium", "words": ["(ashleel)"]}
    mild = _terms(text, MILD, ig)
    if len(mild) >= 2 or (mild and re.search(r"\b(tu|tum|tera|teri|aap|you)\b", t)):
        return {"kind": "abuse", "severity": "low", "words": mild[:3]}
    return None


# ---------------------------------------------------------------- links, scams, spam
URL = re.compile(r"(?i)\b((?:https?://|www\.)[^\s<>\"']+|(?:[a-z0-9-]+\.)+(?:com|in|net|org|xyz|top|click|link|info|io|co|me|"
                 r"site|online|shop|live|app|ly|gl|gd|cc|ru|cn|pk|tk|ml|ga|cf|icu|buzz|cfd|sbs|rest|loan|work)(?:/[^\s<>\"']*)?)")
SHORTENERS = {"bit.ly", "tinyurl.com", "t.ly", "cutt.ly", "is.gd", "rb.gy", "shorturl.at", "goo.gl", "ow.ly", "tiny.cc",
              "rebrand.ly", "s.id", "v.gd", "shorte.st", "adf.ly", "bitly.com", "tny.im"}
RISKY_TLD = {"xyz", "top", "click", "loan", "work", "rest", "icu", "buzz", "cfd", "sbs", "tk", "ml", "ga", "cf", "live", "shop"}
BRANDS = {"sbi": ("sbi.co.in", "onlinesbi.sbi", "sbi.bank.in"), "hdfc": ("hdfcbank.com", "hdfc.bank.in"),
          "icici": ("icicibank.com", "icici.bank.in"), "axis": ("axisbank.com",), "paytm": ("paytm.com",),
          "phonepe": ("phonepe.com",), "gpay": ("pay.google.com",), "npci": ("npci.org.in",), "uidai": ("uidai.gov.in",),
          "aadhaar": ("uidai.gov.in",), "incometax": ("incometax.gov.in",), "amazon": ("amazon.in", "amazon.com"),
          "flipkart": ("flipkart.com",), "irctc": ("irctc.co.in",), "epfo": ("epfindia.gov.in",), "lic": ("licindia.in",),
          "jio": ("jio.com",), "airtel": ("airtel.in",), "bsnl": ("bsnl.co.in",), "rbi": ("rbi.org.in",)}
INVITE = re.compile(r"(?i)(chat\.whatsapp\.com/|t\.me/(?:joinchat/|\+)|telegram\.me/joinchat|discord\.gg/|wa\.me/)")
APP_FILE = re.compile(r"(?i)\.(apk|xapk|apks|exe|msi|bat|scr|jar)(\?|$)")
VPA = re.compile(r"\b[\w.\-]{2,64}@(?:ok\w+|ybl|ibl|axl|paytm|upi|apl|okicici|oksbi|okhdfcbank|okaxis|ptyes|ptaxis|pthdfc|ptsbi|"
                 r"jupiteraxis|fbl|kotak|icici|sbi|hdfcbank|axisbank|freecharge|airtel|jio)\b", re.I)
SCAM = [r"work\s?from\s?home", r"ghar\s?baithe", r"daily\s?(income|earning|payment|kamai)", r"part[- ]?time\s?job",
        r"task\s?(based|job|complete)", r"(like|subscribe).{0,30}(earn|kamao|paise)", r"invest\w*.{0,20}(double|guarantee|pakka)",
        r"double\s?(money|paisa|paise)", r"guaranteed?\s?(return|profit|income)", r"\bcrypto\b", r"\bforex\b", r"\busdt\b",
        r"trading\s?(tips|signal|call)", r"binary\s?option", r"loan\s?(approved|instant|turant)", r"\bkyc\b.{0,20}(update|expire|pending|band)",
        r"account.{0,15}(block|band|suspend)", r"(electricity|bijli).{0,15}(cut|kat|disconnect)", r"sim.{0,10}(block|band)",
        r"lucky\s?draw", r"you\s?(have\s?)?won", r"(aap|tum)\s?jeet\s?gaye", r"(registration|processing|advance|joining)\s?fee",
        r"earn\s?(rs|₹|inr)?\s?\d", r"₹\s?\d[\d,]*\s?(daily|per\s?day|roz)", r"\bbetting\b", r"\bsatta\b", r"\bjackpot\b",
        r"free\s?(recharge|iphone|laptop|gift)", r"refund\s?(milega|claim)", r"customer\s?care\s?(number|no)", r"anydesk|teamviewer|quicksupport"]


def links(text: str, entities: list[str] | None = None) -> list[str]:
    found = [m.group(1).rstrip(".,)!?") for m in URL.finditer(text or "")]
    for u in entities or []:
        if u and u not in found:
            found.append(u)
    return found[:20]


def host_of(url: str) -> str:
    u = url if re.match(r"(?i)^[a-z]+://", url) else "http://" + url
    try:
        return (urlsplit(u).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def _base(host: str) -> str:
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in ("co", "gov", "org", "net", "ac", "nic", "bank") and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def link_risk(url: str, allowed: set[str] | None = None) -> dict[str, Any]:
    """Score one link: 0 = fine, 1-2 = watch, 3+ = likely scam. Reasons in Hinglish."""
    allowed = {_base(a.lower().removeprefix("www.")) for a in (allowed or set()) if a}
    h = host_of(url)
    why: list[str] = []
    score = 0
    if not h:
        return {"url": url, "host": "", "score": 0, "why": []}
    if _base(h) in allowed:
        return {"url": url, "host": h, "score": 0, "why": ["aapka allowed site"], "allowed": True}
    if h in SHORTENERS:
        score += 2; why.append("chhota (short) link - asli pata chhupta hai")
    if re.fullmatch(r"[\d.]+", h):
        score += 3; why.append("seedha IP address wala link")
    if "xn--" in h:
        score += 3; why.append("nakli akshar wala domain (punycode)")
    if h.rsplit(".", 1)[-1] in RISKY_TLD:
        score += 1; why.append(f".{h.rsplit('.', 1)[-1]} domain - scam mein aam")
    if APP_FILE.search(url):
        score += 4; why.append("app / program file download (APK / EXE)")
    if INVITE.search(url):
        score += 1; why.append("doosre group / chat ka invite link")
    flat = re.sub(r"[^a-z]", "", h)
    for brand, official in BRANDS.items():
        if brand in flat and not any(h == o or h.endswith("." + o) for o in official):
            score += 3; why.append(f"'{brand}' naam wala nakli jaisa site (asli: {official[0]})")
            break
    return {"url": url, "host": h, "score": score, "why": why}


def scam(text: str, entity_links: list[str] | None = None, allowed: set[str] | None = None, new_member: bool = False,
         links_policy: str = "new_no") -> dict[str, Any] | None:
    """Scam / spam check of one message. links_policy: allow | new_no (new members can't post links) | none."""
    t = norm(text)
    ls = [link_risk(u, allowed) for u in links(text, entity_links)]
    words_hit = [p for p in SCAM if re.search(p, t)]
    vpa = bool(VPA.search(text or ""))
    score = max([l["score"] for l in ls] or [0]) + 2 * min(len(words_hit), 2) + (1 if vpa else 0)
    why = [w for l in ls for w in l["why"] if not l.get("allowed")]
    if words_hit:
        why.append("paise / naukri / inaam ka lalach wale shabd")
    if vpa:
        why.append("UPI ID dali hai (paise maangne ka shak)")
    outside = [l for l in ls if not l.get("allowed")]
    if outside and new_member:
        score += 2; why.append("naye member ka pehla link")
    if outside and links_policy == "none":
        score += 2; why.append("is group mein link mana hai")
    elif outside and links_policy == "new_no" and new_member:
        score += 1
    if score < 2:
        return None
    sev = "high" if score >= 5 else "medium" if score >= 3 else "low"
    kind = "scam" if (words_hit or score >= 4 or vpa) else "spam"
    return {"kind": kind, "severity": sev, "score": score, "why": why[:5], "links": [l["host"] for l in ls][:5]}


def personal_data(text: str) -> list[str]:
    """Aadhaar / PAN / card / OTP / bank details posted in a group (hide it, don't keep it)."""
    try:
        from .. import pii
        return pii.find(text or "")
    except Exception:
        return []


def mask(text: str) -> str:
    """What we keep: personal numbers masked."""
    t = re.sub(r"(?<!\d)(\d[ -]?){12,19}(?!\d)", lambda m: "X" * 4 + re.sub(r"\D", "", m.group(0))[-4:], text or "")
    t = re.sub(r"\b[A-Z]{3}[ABCFGHLJPT][A-Z]\d{4}[A-Z]\b", "PAN-XXXX", t)
    return re.sub(r"(?i)\b(otp|pin|cvv|password)\W{0,6}(is|hai|:|=)?\W{0,4}\S+", r"\1 ••••", t)


# ---------------------------------------------------------------- rumours (flag, never "truth" verdicts)
RUMOUR = [r"forward.{0,20}(\d+|sab|saare|all).{0,10}(group|logo|people|contacts)", r"share\s?(karo|kare|kijiye).{0,15}(warna|nahi\s?to)", r"\d+\s?(group|groups|logo|logon|log|contacts)\w*\s?(mein|me|ko)?\s?(forward|bhej|share)",
          r"(forward|share|bhej\w*)\s?(karo|kare|kijiye|do|kar\s?do)?.{0,10}(warna|nahi\s?to)",
          r"100\s?%\s?(sach|true|confirm)", r"breaking\s?news", r"(sarkar|government|modi|pm).{0,25}(free|muft).{0,15}(de\s?rahi|giving|milega)",
          r"rbi.{0,15}(new\s?rule|naya\s?niyam|band)", r"whatsapp.{0,15}(band|closed|paid)\s?(hoga|ho\s?jayega|will)",
          r"cure[sd]?\s?(cancer|diabetes|corona|covid|bp|sugar)", r"(cancer|sugar|diabetes).{0,20}(khatam|jad\s?se|ilaaj\s?pakka)",
          r"\bchamatkar\b", r"\bmiracle\b", r"aaj\s?raat\s?\d+\s?baje\s?se", r"\b5g\b.{0,30}(corona|virus|cancer)",
          r"note(bandi|ban).{0,15}(phir|again)", r"(fake|jhooth).{0,10}nahi\s?hai", r"media\s?nahi\s?dikhayega"]


def rumour(text: str, forwarded: bool = False) -> dict[str, Any] | None:
    t = norm(text)
    hits = [p for p in RUMOUR if re.search(p, t)]
    if not hits:
        return None
    sev = "medium" if (forwarded or len(hits) >= 2) else "low"
    return {"kind": "misinfo", "severity": sev, "why": ["aage bhejo / chamatkar / sarkari muft jaise afwah ke nishaan"],
            "check": "PIB Fact Check (factcheck.pib.gov.in, WhatsApp +91 8799711259) ya asli source se jaanchiye."}


# ---------------------------------------------------------------- mood, complaints, questions
NEG = ["kharab", "bekar", "bekaar", "worst", "bad", "pathetic", "fraud", "cheat", "cheated", "dhokha", "loot", "chor", "naraz",
       "gussa", "complaint", "shikayat", "refund", "not working", "kaam nahi", "nahi aaya", "nahi mila", "late", "delay", "ghatiya",
       "bakwas", "waste", "bura", "vait", "fasavla", "useless", "disappointed", "angry", "irritate", "pareshan", "pareshaan",
       "kab tak", "abhi tak", "band hai", "chalta nahi", "slow", "वाईट", "खराब", "बेकार", "घटिया", "धोखा", "फसवणूक", "तक्रार",
       "शिकायत", "परेशान", "नाराज"]
POS = ["thanks", "thank you", "thanku", "dhanyavaad", "dhanyawad", "shukriya", "badhiya", "mast", "accha", "achha", "great",
       "awesome", "love", "superb", "excellent", "nice", "best", "chhan", "khup chhan", "धन्यवाद", "बढ़िया", "मस्त", "छान", "शुक्रिया"]
TOPICS = {"delivery": ["delivery", "parcel", "courier", "order nahi", "pahuncha nahi", "deliver"],
          "payment": ["refund", "payment", "paisa", "paise", "upi", "deduct", "kat gaya", "kata", "paid", "bill", "charge"],
          "quality": ["quality", "kharab", "toota", "tuta", "damage", "defect", "fake", "nakli"],
          "service": ["staff", "rude", "behaviour", "behavior", "response", "reply nahi", "phone nahi", "uthata nahi", "support"],
          "internet": ["internet", "net", "wifi", "wi-fi", "speed", "slow", "signal", "connection", "router", "fiber", "ont", "los"],
          "price": ["mehenga", "mehnga", "price", "rate", "daam", "costly", "expensive", "badha"],
          "timing": ["late", "time", "der", "delay", "kab tak", "abhi tak", "wait"]}


def mood(text: str) -> int:
    t = " " + norm(text) + " "
    n = sum(1 for w in NEG if (" " + w + " ") in t or (len(w) > 5 and w in t))
    p = sum(1 for w in POS if (" " + w + " ") in t)
    return -1 if n > p else 1 if p > n else 0


def topic(text: str) -> str:
    t = " " + norm(text) + " "
    best, score = "", 0
    for k, ws in TOPICS.items():
        s = sum(1 for w in ws if (" " + w + " ") in t or (len(w) > 4 and w in t))
        if s > score:
            best, score = k, s
    return best


Q_START = re.compile(r"^(kya|kab|kaise|kaisa|kitna|kitne|kitni|kahan|kaha|kaun|kyun|kyu|konsa|kis|what|when|how|where|who|why|which|"
                     r"is there|can i|can we|do you|does|kay|kasa|kashi|kiti|kuthe|kevha|kon|का|क्या|कब|कैसे|कितना|कहाँ|कौन|"
                     r"काय|कसे|किती|कुठे|केव्हा)\b")
Q_INSIDE = re.compile(r"\b(kab|kaise|kitna|kitne|kitni|kahan|kaun|konsa|batao|bataiye|bataye|pata hai|milega|milegi|hoga|hogi|"
                      r"hai kya|ho sakta|sakte hai|when|how much|what time|where is|kiti|kuthe|kevha|sangaa|सांगा|बताइए|बताओ)\b")


def is_question(text: str) -> bool:
    t = norm(text)
    if len(t) < 4 or len(t) > 400:
        return False
    return t.endswith("?") or bool(Q_START.search(t)) or bool(Q_INSIDE.search(t))


# ---------------------------------------------------------------- FAQ matching (word based, deterministic)
STOP = {"hai", "h", "he", "hain", "ka", "ki", "ke", "ko", "se", "me", "mein", "main", "to", "toh", "the", "is", "a", "an", "of",
        "please", "plz", "pls", "sir", "madam", "mam", "ji", "bhai", "bhaiya", "didi", "aap", "hum", "mera", "meri", "mere", "apna",
        "kar", "karo", "kare", "karna", "sakte", "sakta", "sakti", "ye", "yeh", "wo", "woh", "kya", "koi", "bhi", "and", "or", "for",
        "in", "on", "at", "do", "does", "i", "we", "you", "my", "our", "it", "are", "be", "will", "can", "hello", "hi", "namaste",
        "batao", "bataiye", "bataye", "tell", "me", "us", "pata", "na", "ne", "par", "pe", "aur", "ho", "hota", "hoti", "hoga", "ya"}
SYN = {"kab": "when", "kitne baje": "time", "baje": "time", "timing": "time", "timings": "time", "samay": "time", "waqt": "time",
       "time": "time", "kevha": "when", "fees": "fee", "fee": "fee", "charges": "fee", "charge": "fee", "shulk": "fee",
       "kitna": "price", "kitne": "price", "kiti": "price", "price": "price", "rate": "price", "daam": "price", "cost": "price",
       "kahan": "where", "kaha": "where", "kuthe": "where", "address": "where", "location": "where", "jagah": "where",
       "kaise": "how", "kasa": "how", "kashi": "how", "join": "join", "judna": "join", "jude": "join", "registration": "join",
       "register": "join", "admission": "join", "pravesh": "join", "refund": "refund", "wapas": "refund", "return": "refund",
       "contact": "contact", "number": "contact", "phone": "contact", "mobile": "contact", "call": "contact", "class": "class",
       "classes": "class", "batch": "class", "holiday": "holiday", "chutti": "holiday", "chhutti": "holiday", "band": "closed",
       "closed": "closed", "open": "open", "khula": "open", "khulta": "open", "delivery": "delivery", "deliver": "delivery",
       "payment": "pay", "pay": "pay", "upi": "pay", "online": "online", "offline": "offline", "rules": "rules", "niyam": "rules",
       "certificate": "certificate", "praman": "certificate", "recording": "recording", "video": "recording", "link": "link"}
GENERIC = {"how", "what", "why", "who", "when", "where", "price", "time"}


def tokens(text: str) -> list[str]:
    t = norm(text)
    t = t.replace("kitne baje", " time ")
    out = []
    for w in WORD.findall(t):
        if w in STOP or (len(w) < 2 and not w.isdigit()):
            continue
        out.append(SYN.get(w, w))
    return out


def faq_score(q: str, faq_q: str, keywords: list[str] | None = None) -> float:
    a = set(tokens(q))
    b = set(tokens(faq_q)) | {SYN.get(k, k) for k in (tokens(" ".join(keywords or [])))}
    if not a or not b:
        return 0.0
    hit = set()
    for x in a:
        if x in b:
            hit.add(x)
            continue
        if len(x) >= 4 and any(len(y) >= 4 and difflib.SequenceMatcher(None, x, y).ratio() >= 0.84 for y in b):
            hit.add(x)
    if not hit or not (hit - GENERIC):
        return 0.0
    strong = hit - GENERIC
    return round(min(1.0, (2 * len(hit) / (len(a) + len(b))) * 0.7 + (len(strong) / max(1, len(a - GENERIC))) * 0.3 +
                     (0.1 if len(strong) >= 2 else 0)), 3)


def best_faq(q: str, faqs: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, float]:
    best, score = None, 0.0
    for f in faqs:
        s = faq_score(q, f.get("question", ""), f.get("keywords") or [])
        if s > score:
            best, score = f, s
    return best, score


AUTO_ANSWER = 0.55       # her approved FAQ goes out by itself at or above this
SUGGEST = 0.35           # below auto but above this: her card shows the likely FAQ


def similar(a: str, b: str) -> float:
    ta, tb = " ".join(sorted(set(tokens(a)))), " ".join(sorted(set(tokens(b))))
    if not ta or not tb:
        return 0.0
    return difflib.SequenceMatcher(None, ta, tb).ratio()


# ---------------------------------------------------------------- templates
def render(template: str, **vals: Any) -> str:
    def rep(m: re.Match) -> str:
        v = vals.get(m.group(1))
        return str(v) if v not in (None, "") else ""
    out = re.sub(r"\{(\w+)\}", rep, template or "")
    return re.sub(r"[ \t]+", " ", out).strip()


DEFAULT_WELCOME = {
    "hinglish": "Namaste {name}! {community} mein aapka swagat hai 🙏 Group ke niyam: {rules}. Koi sawal ho to yahan poochhiye.",
    "hindi": "नमस्ते {name}! {community} में आपका स्वागत है 🙏 ग्रुप के नियम: {rules}. कोई सवाल हो तो यहाँ पूछिए।",
    "marathi": "नमस्कार {name}! {community} मध्ये तुमचं स्वागत आहे 🙏 ग्रुपचे नियम: {rules}. काही प्रश्न असल्यास इथे विचारा.",
    "english": "Hello {name}! Welcome to {community} 🙏 Group rules: {rules}. Ask your questions here anytime.",
}
DEFAULT_RULES = {"hinglish": "izzat se baat, spam / link / paise ki maang nahi, personal number / OTP share mat kijiye",
                 "hindi": "इज़्ज़त से बात, स्पैम / लिंक / पैसे की माँग नहीं, निजी नंबर / OTP शेयर न करें",
                 "marathi": "आदराने बोला, स्पॅम / लिंक / पैशांची मागणी नको, वैयक्तिक नंबर / OTP शेअर करू नका",
                 "english": "be respectful, no spam / links / money requests, never share personal numbers or OTPs"}
LANGS = tuple(DEFAULT_WELCOME)


def template_problems(text: str) -> list[str]:
    out = []
    t = text or ""
    if not t.strip():
        out.append("Khaali hai.")
    if len(t) > 1000:
        out.append("1000 akshar se lamba.")
    try:
        from ..net.policy import secret_found
        if secret_found(t):
            out.append("Ismein OTP / PIN / card jaisi cheez hai.")
    except Exception:
        pass
    if re.search(r"\[[^\]]+\]", t):
        out.append("[khaali jagah] bharni baaki hai.")
    for m in re.finditer(r"\{(\w+)\}", t):
        if m.group(1) not in ("name", "community", "rules", "username"):
            out.append(f"{{{m.group(1)}}} samajh nahi aaya (chalega: {{name}}, {{community}}, {{rules}}).")
    return out


# ---------------------------------------------------------------- health score + escalation
def strike_step(warnings: int, severity: str) -> list[str]:
    """Suggested actions for a member by their history and this message's severity (she decides)."""
    if severity == "high":
        return ["delete_post", "ban", "remove"]
    if severity == "medium":
        return ["delete_post", "mute", "warn"] if warnings >= 1 else ["delete_post", "warn", "mute"]
    return ["warn", "delete_post"] if warnings < 2 else ["delete_post", "mute"]


def health(stats: dict[str, Any]) -> dict[str, Any]:
    """0-100 with the reasons. stats: members, joins, leaves, active, posts, neg_share, prev_neg_share, open_alerts,
    high_alerts, unanswered, answered."""
    score = 80.0
    why = []
    m = max(1, int(stats.get("members") or 0))
    act = (stats.get("active") or 0) / m
    score += min(15, act * 40)
    if act < 0.05 and m >= 20:
        why.append("bahut kam log baat kar rahe hain")
    net = (stats.get("joins") or 0) - (stats.get("leaves") or 0)
    if stats.get("leaves", 0) >= 3 and stats.get("leaves", 0) > stats.get("joins", 0):
        score -= min(20, (stats["leaves"] / m) * 200)
        why.append(f"jaane wale zyada ({stats['leaves']} gaye, {stats.get('joins', 0)} aaye)")
    elif net > 0:
        score += min(5, net)
    ns = stats.get("neg_share") or 0.0
    if ns > 0.15:
        score -= min(20, ns * 60)
        why.append(f"{round(ns * 100)}% baatein naraazgi wali")
    score -= min(20, 6 * (stats.get("high_alerts") or 0) + 2 * (stats.get("open_alerts") or 0))
    if stats.get("high_alerts"):
        why.append(f"{stats['high_alerts']} gambhir alert")
    un = stats.get("unanswered") or 0
    if un:
        score -= min(10, un * 2)
        why.append(f"{un} sawal bina jawab")
    s = int(max(0, min(100, round(score))))
    return {"score": s, "label": "achha" if s >= 75 else "theek" if s >= 55 else "dhyaan chahiye", "why": why}
