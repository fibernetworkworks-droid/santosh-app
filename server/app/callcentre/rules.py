"""Call Centre Sahayak rules: what the AI line may say, when a person takes over, what is masked, what the law asks.

Research behind it (checked 23 Oct 2026; sources at the bottom):
- Inbound customer-care calls are not "commercial communication" under TRAI TCCCPR 2018 (as amended 12 Feb 2025): the
  140-series (promotional) and 1600-series (service / transactional, for regulated BFSI entities) numbering rules and the
  DLT / UCC complaint rules govern calls a business MAKES. A caller ringing the business's own number is fine; any
  call-back Hoola suggests is made by a person (or later from a registered series), never auto-dialled.
- A business may not interconnect the public phone network with internet telephony itself (that needs a Unified Licence
  authorisation). It rents a number from a licensed / authorised provider (Plivo India, Exotel...) and receives the
  call's audio over the provider's documented media stream. Plivo: only India-registered businesses with KYC may rent
  Indian numbers, and both legs must stay in India ("media anchoring"), so the Hoola server must run in India.
- OSP guidelines (DoT, 23 Jun 2021): no registration for call centres; call detail records must be kept (we keep one row
  per call; the provider keeps the CDR) and logs given to law enforcement on demand.
- DPDP Act 2023 + DPDP Rules notified 14 Nov 2025: notice + consent duties apply from 14 May 2027; processing logs kept
  >= 1 year. So every call starts with a notice (AI assistant, purpose, recording if on, how to reach a person), the
  transcript is masked, audio is never stored by Hoola, and one caller's data can be erased on request.
- No specific TRAI / MeitY rule (Oct 2026) forces an "AI" announcement on INBOUND calls; TRAI's 2026 TCCCPR amendment
  discussion is about outbound AI calls, and IT Rules 2026 labels cover synthetic media on platforms. Hoola discloses
  anyway, in the first line, in code (honesty rule of the house; a caller must never think a machine is a person).
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

NEVER = [
    "Hoola answers ONLY from her approved script and FAQ; anything else = take a message or hand over to a person.",
    "Every call starts by saying it is an AI assistant (and that the call is recorded, if recording is on).",
    "A caller can reach a person at any time: say 'insaan se baat' / 'agent' or press 0.",
    "Hoola never takes OTP, PIN, card, CVV, UPI PIN, passwords, Aadhaar or bank numbers on the line.",
    "Hoola never promises prices, discounts, refunds, dates or anything the script does not say.",
    "Hoola never calls anyone; call-backs are made by her or her staff.",
    "Money never moves on the line: no payment links, no payment details.",
    "Caller ID can be faked: no private account details (dues, orders, addresses) are read out by caller ID alone.",
    "Audio is never stored by Hoola; the transcript is masked (numbers, IDs) and kept for the call note only.",
]

SOURCES = [
    ("Plivo India calling (KYC, India-registered businesses, media anchoring, 140 / landline / 160 series)",
     "https://www.plivo.com/docs/voice/concepts/india-calling.md", "2026-10-23"),
    ("Plivo Audio Streaming guide (bidirectional Stream XML, playAudio / clearAudio, X-Plivo-Signature-V3)",
     "https://www.plivo.com/docs/voice-agents/audio-streaming/concepts/audio-streaming-guide.md", "2026-10-23"),
    ("plivo-python 4.63.0 utils/signature_v3.py (exact V3 HMAC-SHA256 algorithm)", "https://pypi.org/project/plivo/", "2026-10-23"),
    ("Exotel Stream / Voicebot applet (slin 16-bit PCM 8 kHz base64, media / mark / clear, Basic Auth or IP whitelist)",
     "https://developer.exotel.com/docs/agentstream/stream-voicebot-applet", "2026-10-23"),
    ("Twilio India voice guidelines (only toll-free inbound; outbound to India only from non-Indian numbers)",
     "https://www.twilio.com/en-us/guidelines/in/voice", "2026-10-23"),
    ("MediaNama summary of DoT OSP guidelines 23 Jun 2021 (no registration, CDRs kept, logs on demand)",
     "https://www.medianama.com/2021/06/223-summary-government-guidelines-other-service-providers/", "2026-10-23"),
    ("AMS Shardul alert: DPDP Rules notified 14 Nov 2025; notice / consent from 14 May 2027; logs >= 1 year",
     "https://www.amsshardul.com/wp-content/uploads/2025/11/Regulatory-Alert-Enforcement-of-DPDP-Act-and-Notification-of-DPDP-Rules.pdf",
     "2026-10-23"),
    ("caller.digital on TRAI TCCCPR third amendment (13 Mar 2026; outbound AI calls; vendor reading, not the text)",
     "https://caller.digital/blog/trai-third-amendment-2026-ai-ml-spam-detection-ai-calling", "2026-10-23"),
]

PROVIDERS = {
    "plivo": {"name": "Plivo (India number, Audio Streams)", "primary": True, "where": "India (+ many more)",
              "why": "documented bidirectional WebSocket audio, signed webhooks (X-Plivo-Signature-V3), call transfer and "
                     "hang-up APIs, Indian numbers for India-registered businesses after KYC"},
    "exotel": {"name": "Exotel (Voicebot applet)", "primary": False, "where": "India, South-East Asia",
               "why": "Indian cloud telephony, bidirectional stream; no request signatures (Basic Auth / IP whitelist), "
                      "transfer = the flow's next applet after the stream closes"},
    "twilio": {"name": "Twilio (numbers in most countries)", "primary": False, "where": "worldwide",
               "why": "worldwide numbers, Media Streams over WebSocket, X-Twilio-Signature on every webhook, its own "
                      "answering-machine check; in India only toll-free inbound, so Plivo stays first there"},
    "telnyx": {"name": "Telnyx (numbers in 140+ countries)", "primary": False, "where": "worldwide",
               "why": "own global carrier network, TeXML (Twilio-style), bidirectional media streaming, Ed25519-signed "
                      "webhooks, answering-machine check"},
    "vonage": {"name": "Vonage (numbers in many countries)", "primary": False, "where": "worldwide",
               "why": "Voice API with WebSocket audio (16 kHz), signed webhooks, answering-machine check"},
    "signalwire": {"name": "SignalWire (US, Canada, UK and more)", "primary": False, "where": "North America, Europe",
                   "why": "Twilio-compatible cXML and Media Streams, signed webhooks, answering-machine check"},
    "bandwidth": {"name": "Bandwidth (US, Canada, Europe)", "primary": False, "where": "US, Canada, Europe",
                  "why": "its own carrier network, BXML bidirectional streaming, answering-machine check"},
    "sinch": {"name": "Sinch (carrier in 60+ countries)", "primary": False, "where": "worldwide",
              "why": "SVAML with connectStream WebSocket audio, signed callbacks, answering-machine check"},
    "jambonz": {"name": "Any phone carrier, any country (jambonz)", "primary": False, "where": "every country",
                "why": "an open voice gateway: bring the SIP trunk of any local carrier anywhere in the world; listen "
                       "WebSocket audio, signed webhooks, answering-machine check"},
    "fake": {"name": "Test line (no real calls)", "primary": False, "why": "for trying the script without a phone number"},
}
NOT_PRIMARY = {"twilio_in": "Twilio for an Indian business number: only toll-free inbound, and a transfer to her Indian "
                            "mobile would be an international call - use Plivo or Exotel in India, Twilio elsewhere.",
               "ozonetel": "Ozonetel / Knowlarity: no public, documented bidirectional media-stream API found (Oct 2026).",
               "infobip": "Infobip: its live call audio needs a media-stream configuration made on their side first; not "
                          "built yet - use Telnyx, Vonage, Sinch or jambonz with any local carrier meanwhile.",
               "africastalking": "Africa's Talking: no live two-way call audio API; for Africa use Telnyx, Vonage, Sinch or "
                                 "jambonz with a local SIP carrier."}

# v0.999.68 which phone companies give a local number where she is (the first is the suggested one); jambonz works
# everywhere because it fronts any local SIP carrier
_NA = ("US", "CA")
_BW = ("US", "CA", "GB", "IE", "DE", "FR", "ES", "IT", "NL", "BE", "AT", "CH", "SE", "DK", "NO", "FI", "PL", "PT")


def providers_for(country: str) -> list[str]:
    c = (country or "IN").upper()
    if c == "IN":
        return ["plivo", "exotel", "jambonz"]
    out = ["twilio", "telnyx", "vonage", "sinch"]
    if c in _NA:
        out += ["signalwire", "bandwidth"]
    elif c in _BW:
        out += ["bandwidth", "signalwire"]
    if c in ("SG", "ID", "MY", "PH", "TH", "VN"):
        out.append("exotel")
    return out + ["plivo", "jambonz"]


ACTIONS = ("faq", "messages", "appointments", "ticket_status", "complaints")   # what a script may allow


# ---------------------------------------------------------------- text helpers
def norm(text: str) -> str:
    t = (text or "").lower()
    t = re.sub(r"[^\w\sऀ-෿]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


STOP = {"kya", "hai", "hain", "ka", "ki", "ke", "ko", "se", "me", "mein", "main", "aap", "aapka", "aapki", "hum", "ham",
        "the", "is", "a", "an", "of", "to", "do", "for", "and", "or", "in", "on", "you", "your", "i", "my", "me", "please",
        "bhai", "ji", "sir", "madam", "batao", "bataiye", "boliye", "kitna", "kitne", "kitni", "kab", "kahan", "kaise",
        "what", "when", "where", "how", "much", "many", "ye", "yeh", "wo", "woh", "jo", "toh", "to", "bhi", "na", "ho",
        "hota", "hoti", "hote", "kar", "karo", "kare", "karna", "milega", "milegi", "sakta", "sakte", "sakti", "aur",
        "है", "हैं", "का", "की", "के", "को", "से", "में", "क्या", "आप", "आपका", "मुझे"}


def words(text: str) -> set[str]:
    return {w for w in norm(text).split() if len(w) > 1 and w not in STOP}


def digits(v: Any) -> str:
    return re.sub(r"\D", "", str(v or ""))


def phone_e164(v: Any) -> str:
    """Indian number -> +91XXXXXXXXXX ('' if it isn't one)."""
    d = digits(v)
    if d.startswith("0091"):
        d = d[4:]
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return f"+91{d}" if len(d) == 10 and d[0] in "6789123456" else ""


def mask_phone(v: Any) -> str:
    d = digits(v)
    if len(d) < 6:
        return "XXXX"
    return d[-10:-8] + "X" * 4 + d[-4:] if len(d) >= 10 else "X" * (len(d) - 4) + d[-4:]


def phone_key(v: Any) -> str:
    """The last 10 digits: the same caller whatever the format (+91, 0, spaces)."""
    return digits(v)[-10:]


_OTPISH = re.compile(r"\b(otp|o\.t\.p|pin|cvv|password|passcode|upi pin|ओटीपी|पिन|पासवर्ड)\b[^\n]{0,30}?(\d[\d\s-]{2,10}\d)", re.I)
_LONG = re.compile(r"(?<!\d)(\d[\d \-]{6,}\d)(?!\d)")


def mask_text(text: str) -> str:
    """For the saved transcript: OTP / PIN / card / Aadhaar / long numbers hidden, last digits of a phone kept."""
    t = str(text or "")
    t = _OTPISH.sub(lambda m: m.group(0).replace(m.group(2), "••••"), t)

    def _num(m: re.Match) -> str:
        d = digits(m.group(1))
        if len(d) == 10 or (len(d) in (11, 12) and d[-10] in "6789"):
            return mask_phone(d)
        return "•" * min(len(d), 6) + d[-2:] if len(d) >= 8 else m.group(1)
    t = _LONG.sub(_num, t)
    try:
        from ..pii import find
        if find(t):
            t = re.sub(r"\b[A-Z]{5}\d{4}[A-Z]\b", "XXXXX••••X", t)
    except Exception:
        pass
    return t[:2000]


def secret_in(text: str) -> str:
    """A secret the caller is trying to give (OTP / PIN / card / Aadhaar / password) -> its name, else ''."""
    try:
        from ..pii import find
        hits = find(text)
    except Exception:
        hits = []
    if hits:
        return hits[0]
    return "otp_pin" if _OTPISH.search(text or "") else ""


# ---------------------------------------------------------------- handover: when a person must take over
ASK_HUMAN = re.compile(
    r"(insaan|insan|aadmi|manushya|vyakti|real person|human|agent|operator|executive|representative|customer care (wale|se)|"
    r"manager|malik|owner|madam se|sir se|kisi se baat|baat karwao|baat karao|connect karo|transfer karo|"
    r"इंसान|आदमी|व्यक्ति|मैनेजर|किसी से बात|बात कराओ|बात करवाओ|माणसाशी|माणूस|व्यक्तीशी|मॅनेजर|बोलायचं आहे)", re.I)
ANGRY = re.compile(
    r"(bakwas|bekaar|bekar|faltu|ghatiya|pagal|bewakoof|chor|fraud|dhokha|cheat|consumer court|police|complaint karunga|"
    r"complaint karungi|case karunga|shame|worst|useless|nonsense|stupid|idiot|बकवास|बेकार|फालतू|घटिया|धोखा|"
    r"फ्रॉड|पुलिस|फसवणूक|बकवास|भंगार|वाईट)", re.I)
NO_HUMAN_WORDS = re.compile(r"(nahi chahiye|mat karo|no need|not needed|नहीं चाहिए)", re.I)


def handover_reason(caller_text: str) -> str:
    """'asked_human' | 'angry' | '' from one finished caller turn."""
    t = caller_text or ""
    if ASK_HUMAN.search(t) and not NO_HUMAN_WORDS.search(t):
        return "asked_human"
    if ANGRY.search(t) or (len(t) > 12 and sum(1 for c in t if c.isupper()) > 0.6 * sum(1 for c in t if c.isalpha())):
        return "angry"
    return ""


REASON_SAY = {"asked_human": "the caller asked to speak to a person", "angry": "the caller was upset",
              "out_of_script": "the question was not in the script", "low_confidence": "the caller could not be understood clearly",
              "dtmf": "the caller pressed 0", "secret": "the caller was giving a secret number",
              "ai_down": "the AI line could not run", "time_up": "the call time was up"}

PROMISE = re.compile(r"(guarantee|pakka discount|free mein|muft|refund (de|mil) (denge|jayega)|100 ?%|"
                     r"zaroor mil jayega|promise|vaada|वादा|गारंटी|मुफ्त|फ्री में)", re.I)
_NUM = re.compile(r"(?<![\w.])(\d[\d,.]*\d|\d)(?![\w])")


def numbers_in(text: str) -> set[str]:
    out = set()
    for m in _NUM.finditer(text or ""):
        n = m.group(1).replace(",", "").rstrip(".")
        if n and n not in ("0", "1", "2"):
            out.add(n)
    return out


def unscripted(reply: str, allowed_text: str) -> list[str]:
    """Numbers (prices, phone numbers, dates) and promises in Hoola's reply that her script / the tool results never said.
    Spoken numbers often come back as words, so this is a signal for the call note, not a proof."""
    have = numbers_in(allowed_text)
    bad = [n for n in sorted(numbers_in(reply)) if n not in have]
    out = [f"number {n}" for n in bad[:5]]
    if PROMISE.search(reply or "") and not PROMISE.search(allowed_text or ""):
        out.append("promise / guarantee")
    return out


# ---------------------------------------------------------------- disclosure (first line of every call)
DISCLOSE = {
    "hi-IN": ("Namaste, {biz} mein aapka swagat hai. Main {agent}, {biz} ki AI sahayak hoon.{rec} Kisi bhi samay "
              "insaan se baat karne ke liye 'insaan se baat' boliye ya 0 dabaiye."),
    "mr-IN": ("Namaskar, {biz} madhye aapla swagat aahe. Mi {agent}, {biz} chi AI sahayak aahe.{rec} Kadhihi "
              "mansashi bolaycha asel tar 'mansashi bolaycha aahe' mhana kiva 0 daba."),
    "en-IN": ("Hello, welcome to {biz}. I am {agent}, {biz}'s AI assistant.{rec} To talk to a person at any time, "
              "say 'agent' or press 0."),
}
REC = {"hi-IN": " Yeh call record ho rahi hai.", "mr-IN": " Hi call record hot aahe.", "en-IN": " This call is recorded."}
DISCLOSE_HEARD = re.compile(r"\b(ai|a\.i\.|artificial|एआई|ए आई|robot|virtual)\b", re.I)
CLOSED = {
    "hi-IN": "Namaste, {biz} abhi band hai. Hum {hours} khule rehte hain. Aapka number aa gaya hai, team aapko call karegi.",
    "mr-IN": "Namaskar, {biz} aata band aahe. Aamhi {hours} chalu asto. Tumcha number aala aahe, team tumhala call karel.",
    "en-IN": "Hello, {biz} is closed now. We are open {hours}. We have your number and the team will call you back.",
}
BUSY = {
    "hi-IN": "Sabhi line abhi vyast hain. Aapka number aa gaya hai, team aapko jaldi call karegi. Dhanyavaad.",
    "mr-IN": "Saglya line aata vyast aahet. Tumcha number aala aahe, team tumhala lavkar call karel. Dhanyavaad.",
    "en-IN": "All lines are busy right now. We have your number and the team will call you back soon. Thank you.",
}
HOLD = {"hi-IN": "Kripya line par bane rahiye, aapki call jaldi uthayi jayegi.",
        "mr-IN": "Krupaya line var thamba, tumchi call lavkar ghetli jail.",
        "en-IN": "Please stay on the line, your call will be answered shortly."}
CONNECTING = {"hi-IN": "Aapko hamari team se jod rahe hain, kripya ruke.", "mr-IN": "Tumhala aamchya team shi jodat aahot, krupaya thamba.",
              "en-IN": "Connecting you to our team, please hold."}
CALLBACK_SAY = {   # G3: the person did not pick up the warm transfer
    "hi-IN": "Maaf kijiye, abhi team ka koi phone nahi utha paya. Aapki baat likh li hai, team aapko {window} call karegi. Dhanyavaad.",
    "mr-IN": "Maaf kara, aata team madhle koni phone ghenu shakle nahi. Tumchi goshta lihun ghetli aahe, team tumhala {window} call karel. Dhanyavaad.",
    "en-IN": "Sorry, nobody from the team could pick up just now. Your request is noted and the team will call you back {window}. Thank you.",
}
CALLBACK_SOON = {"hi-IN": "jaldi", "mr-IN": "lavkar", "en-IN": "soon"}


def default_lang() -> str:
    """The line's language when neither the caller's record nor the script names one: Indian English when Hoola is
    set to English (the default), Hindi when it follows the user's own language (`hoola_language` = auto)."""
    try:
        from .. import lang as _lang
        return "en-IN" if _lang.english() else "hi-IN"
    except Exception:
        return "en-IN"


def lang3(code: str) -> str:
    return code if code in DISCLOSE else default_lang()


def disclosure(lang: str, biz: str, agent: str, recorded: bool) -> str:
    lg = lang3(lang)
    return DISCLOSE[lg].format(biz=biz or ("our business" if lg == "en-IN" else "hamari dukaan"), agent=agent or "Hoola", rec=REC[lg] if recorded else "")


# ---------------------------------------------------------------- the script (her approved version is the only one that runs)
def script_hash(content: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]


BLANK = re.compile(r"\[(?:blank|[^\]]{0,40}\?)\]|\[\s*\]|_{3,}", re.I)


def blanks(content: dict[str, Any]) -> list[str]:
    out = []
    for f in content.get("faqs") or []:
        if BLANK.search(str(f.get("a", ""))) or not str(f.get("a", "")).strip():
            out.append(str(f.get("q", ""))[:80])
    for k in ("business", "about"):
        if BLANK.search(str(content.get(k, ""))):
            out.append(k)
    return out


def clean_script(c: dict[str, Any]) -> dict[str, Any]:
    """Only known fields, short, no secrets asked for; the AI line is limited to what this says."""
    def s(v: Any, n: int) -> str:
        return re.sub(r"\s+", " ", str(v or "")).strip()[:n]
    faqs, seen = [], set()
    for f in (c.get("faqs") or [])[:80]:
        if not isinstance(f, dict):
            continue
        q, a = s(f.get("q"), 200), s(f.get("a"), 600)
        if not q or norm(q) in seen:
            continue
        seen.add(norm(q))
        ws = [s(w, 30) for w in (f.get("words") or []) if s(w, 30)][:12]
        faqs.append({"id": s(f.get("id"), 12) or hashlib.sha1(q.encode()).hexdigest()[:8], "q": q, "a": a, "words": ws})
    can = c.get("can") if isinstance(c.get("can"), dict) else {}
    langs = [x for x in (c.get("languages") or [default_lang()]) if isinstance(x, str)][:6] or [default_lang()]
    return {
        "business": s(c.get("business"), 120), "about": s(c.get("about"), 500), "greeting": s(c.get("greeting"), 300),
        "languages": langs, "default_lang": s(c.get("default_lang"), 8) or langs[0],
        "faqs": faqs,
        "can": {"appointments": bool(can.get("appointments")), "ticket_status": bool(can.get("ticket_status")),
                "complaints": bool(can.get("complaints", True)), "messages": True},
        "never": [s(x, 200) for x in (c.get("never") or []) if s(x, 200)][:20],
        "handover_words": [s(x, 60) for x in (c.get("handover_words") or []) if s(x, 60)][:20],
        "closing": s(c.get("closing"), 200),
        "hours_text": s(c.get("hours_text"), 120),
        # v0.999.67 call steps (greet -> ask -> answer -> book -> close), each with what to say / aim for
        "steps": [{"name": s(x.get("name"), 40), "say": s(x.get("say"), 400)} for x in (c.get("steps") or [])[:10]
                  if isinstance(x, dict) and s(x.get("name"), 40)],
    }


def parse_faq_text(text: str) -> list[dict[str, str]]:
    """No-model draft: 'Q: ... A: ...', 'sawal - jawab', or 'question? answer' lines."""
    out: list[dict[str, str]] = []
    t = (text or "").replace("\r", "")
    # "Sharma Clinic. Q: Timing? A: 10 se 7" on one line: put every Q: / A: on its own line first
    t = re.sub(r"(?i)(?<=\S)[ \t]+((?:q|a|sawal|jawab|prashn|uttar|प्रश्न|सवाल|उत्तर|जवाब)\s*:)", r"\n\1", t)
    for m in re.finditer(r"(?:^|\n)\s*(?:q|sawal|prashn|प्रश्न|सवाल)\s*[:.\-]\s*(.+?)\n\s*(?:a|jawab|uttar|उत्तर|जवाब)\s*[:.\-]\s*(.+?)(?=\n\s*(?:q|sawal|prashn|प्रश्न|सवाल)\s*[:.\-]|\Z)",
                         t, re.I | re.S):
        out.append({"q": m.group(1).strip(), "a": m.group(2).strip()})
    if out:
        return out
    for line in t.split("\n"):
        line = line.strip(" -•*\t")
        if "?" in line:
            q, _, a = line.partition("?")
            a = a.strip(" -:–")
            if q.strip():
                out.append({"q": q.strip() + "?", "a": a or "[blank]"})
        elif " - " in line and len(line) > 8:
            q, _, a = line.partition(" - ")
            out.append({"q": q.strip(), "a": a.strip()})
    return out


def faq_score(question: str, faq: dict[str, Any]) -> float:
    qw = words(question)
    if not qw:
        return 0.0
    fw = words(faq.get("q", "")) | {w for x in faq.get("words") or [] for w in words(x)}
    if not fw:
        return 0.0
    inter = len(qw & fw)
    # close spellings count a little (Hinglish is written many ways: "timing" / "timings", "daam" / "dam")
    fuzzy = sum(1 for a in qw - fw if any(len(a) > 3 and (a in b or b in a) for b in fw))
    return round((inter + 0.6 * fuzzy) / max(1.0, min(len(qw), len(fw)) ** 0.9 + 0.5 * max(0, len(qw) - len(fw))), 3)


def best_faq(question: str, faqs: list[dict[str, Any]], floor: float = 0.45) -> tuple[dict[str, Any] | None, float]:
    best, score = None, 0.0
    for f in faqs:
        sc = faq_score(question, f)
        if sc > score:
            best, score = f, sc
    return (best, score) if best is not None and score >= floor else (None, score)


def intent_of(tools: list[str], text: str) -> str:
    if "book_appointment" in tools:
        return "appointment"
    if "register_complaint" in tools or ANGRY.search(text or ""):
        return "complaint"
    if "ticket_status" in tools:
        return "status"
    if "transfer_human" in tools:
        return "wanted_person"
    if "take_message" in tools:
        return "message"
    if "faq_answer" in tools:
        return "question"
    return "other"
