"""Patrakar Sahayak rules: pure functions (no DB), so they are easy to test.

Legal checks here are RED FLAGS in plain words, never legal advice: the editor / her lawyer decides. Hard blocks are only
the things where the law is clear and the harm cannot be undone (a sexual-offence victim's or a child's identity, a source's
identity, a quote nobody said, election silence, an embargo, unfilled blanks)."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

# ---------------------------------------------------------------- vocab
STORY_KINDS = ("news", "feature", "explainer", "interview", "opinion", "video", "followup", "brief", "sponsored")
STATUSES = ("pitch", "reporting", "draft", "factcheck", "ready", "waiting", "published", "killed")
SOURCE_KINDS = ("official", "eyewitness", "expert", "document", "insider", "whistleblower", "victim", "accused", "other")
TERMS = ("on_record", "background", "deep_background", "off_record", "anonymous")
TERMS_LABEL = {"on_record": "On record (with name)", "background": "Background (no name; role / place can be given)",
               "deep_background": "Deep background (information only, no identification)",
               "off_record": "Off record (do not publish)", "anonymous": "Anonymous (name never)"}
CLAIM_KINDS = ("number", "quote", "allegation", "date", "name", "stat", "other")
CLAIM_STATUS = ("unchecked", "supported", "attributed", "contradicted", "unclear", "cut")
CORR_KINDS = ("correction", "clarification", "update", "retraction", "apology")
CARD_KINDS = ("publish", "reply", "pitch", "correction", "grievance")
CARD_TITLE = {"publish": "Publish / post the story", "reply": "Chance to reply (right of reply)", "pitch": "Story pitch",
              "correction": "Publish a correction", "grievance": "Reply to a complaint"}
DEST = ("copy", "wordpress")
IST = timezone(timedelta(hours=5, minutes=30))
GRIEVANCE_DAYS = 15          # IT Rules 2021, publisher's grievance officer decides within 15 days


def digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def clean(text: Any, n: int = 4000) -> str:
    """Her / outside words: OTP / PIN / password values and card / Aadhaar-like numbers are never kept."""
    t = str(text or "")
    t = re.sub(r"\b(otp|pin|cvv|password|upi pin)\b\s*(?:is|hai|:|=)?\s*\S+", lambda m: f"{m.group(1)} [hataya]", t, flags=re.I)
    t = re.sub(r"\b(?:\d[ -]?){12,19}\b", "[hataya]", t)
    return t.strip()[:n]


def phone(text: Any) -> str:
    d = re.sub(r"\D", "", str(text or ""))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return d if re.fullmatch(r"[6-9]\d{9}", d) else ""


def email(text: Any) -> str:
    t = str(text or "").strip()
    return t if re.fullmatch(r"[^@\s]{1,64}@[^@\s]+\.[A-Za-z]{2,}", t) else ""


def words(text: str) -> list[str]:
    return re.findall(r"[\wऀ-ॿ']+", (text or "").lower())


def numbers(text: str) -> list[str]:
    t = (text or "").translate(str.maketrans("०१२३४५६७८९", "0123456789"))
    return [x.replace(",", "") for x in re.findall(r"\d[\d,]*(?:\.\d+)?", t)]


def sentences(text: str) -> list[str]:
    t = re.sub(r"\b(No|Rs|Dr|Mr|Mrs|Ms|St|Pvt|Ltd|vs|Sr|Jr|Smt|Shri|approx|etc)\.\s+", r"\1 ", text or "")
    return [x.strip() for x in re.split(r"(?<=[.!?।])\s+|\n+", t) if len(x.strip()) > 3]


def overlap(a: str, b: str) -> float:
    wa = {w for w in words(a) if len(w) > 2}
    wb = set(words(b))
    return len(wa & wb) / max(1, len(wa))


def norm_quote(t: str) -> str:
    t = (t or "").lower().translate(str.maketrans("०१२३४५६७८९", "0123456789"))
    return re.sub(r"[\s\W_]+", " ", t, flags=re.U).strip()


QUOTE_RE = re.compile(r"[\"“”]([^\"“”]{12,600})[\"“”]")


def quotes_in(text: str) -> list[str]:
    return [m.group(1).strip() for m in QUOTE_RE.finditer(text or "")]


def blanks_in(text: str) -> list[str]:
    return re.findall(r"\[(?:[^\]\n]{0,40}\?|blank|____+|[^\]\n]{0,30}chahiye)\]", text or "", flags=re.I)


# ---------------------------------------------------------------- claim extraction (fact-check sheet)
ALLEGE = (r"\b(ghotala|ghotale|scam|fraud|dhokha|dhokhadhadi|rishwat|bribe|bhrasht|corrupt\w*|loot\w*|chori|chor|ghoos|"
          r"embezzl\w*|hadap\w*|hafta|vasooli|extort\w*|rape\w*|balatkar|molest\w*|chhedchhad|hatya|murder\w*|qatl|"
          r"killer|hatyara|apradhi|criminal|mafia|goonda|dalal|land grab|kabza|kabze|milawat|adulterat\w*|"
          r"fake degree|farzi|jaali|forg\w*|misappropriat\w*|kickback|commission khaya|"
          r"घोटाला|घोटाले|भ्रष्ट|रिश्वत|धोखाधड़ी|चोरी|बलात्कार|हत्या|फर्जी|जाली|कब्जा|मिलावट)\b")
ATTRIB = (r"\b(aarop|aaropi|allegedly|alleged|reportedly|kathit|kathith|police ke mutabik|police ne kaha|fir mein|fir ke anusaar|"
          r"according to|ke anusaar|ke mutabik|ne aarop lagaya|claimed|daava|chargesheet|court record|shikayat mein|"
          r"आरोप|आरोपी|कथित|के अनुसार|के मुताबिक|शिकायत)\b")


def extract_claims(text: str) -> list[dict]:
    """Every sentence a careful desk would check: numbers / stats / dates, quotes, allegations against someone."""
    out, seen = [], set()
    for q in quotes_in(text):
        k = norm_quote(q)[:120]
        if k and k not in seen:
            seen.add(k)
            out.append({"text": q[:600], "kind": "quote"})
    for s in sentences(re.sub(QUOTE_RE, " ", text or "")):
        low = s.lower()
        kind = ""
        if re.search(ALLEGE, low, re.I):
            kind = "allegation"
        elif re.search(r"\d", s) and not re.fullmatch(r"[\d\W]+", s):
            kind = "stat" if re.search(r"%|percent|pratishat|lakh|crore|hazaar|करोड़|लाख", low) else (
                "date" if re.search(r"\b(19|20)\d\d\b|janvari|january|farvari|february|march|april|may|june|july|august|"
                                    r"september|october|november|december|\d{1,2}[/-]\d{1,2}", low) else "number")
        if not kind:
            continue
        k = low[:120]
        if k in seen:
            continue
        seen.add(k)
        out.append({"text": s[:600], "kind": kind})
    return out[:60]


def attributed(sentence: str) -> bool:
    return bool(re.search(ATTRIB, sentence or "", re.I))


def match_page(claim: str, page_text: str) -> tuple[bool, str, float]:
    """Does a page Hoola actually read say this? Every number in the claim must be on the page, and the words must overlap.
    Returns (found, best sentence, score). Never a verdict on truth: only 'this page says it'."""
    nums = numbers(claim)
    pn = set(numbers(page_text))
    if nums and not all(n in pn for n in nums):
        return False, "", 0.0
    best, sc = "", 0.0
    for sent in re.split(r"(?<=[.!?।])\s+|\n+", page_text or ""):
        ov = overlap(claim, sent)
        if ov > sc:
            best, sc = sent.strip()[:300], ov
    need = 0.3 if nums else 0.55
    return sc >= need, best, round(sc, 2)


def quote_found(q: str, hay: list[str]) -> bool:
    nq = norm_quote(q)
    if len(nq) < 8:
        return True
    for h in hay:
        if nq in norm_quote(h):
            return True
    return False


# ---------------------------------------------------------------- risk checker
SEXUAL = (r"\b(rape\w*|balatkar|sexual (assault|abuse|harass\w*)|yaun (shoshan|utpeedan|hinsa)|molest\w*|chhedchhad|chhed chhad|"
          r"pocso|gang ?rape|sex(ual)? offen[cs]e|outraging modesty|stalking|voyeur\w*|acid attack|"
          r"बलात्कार|यौन|छेड़छाड़|पॉक्सो|दुष्कर्म)\b")
MINOR = (r"\b(minor|nabalig|naabalig|bachchi|bachcha|bachche|child|children|kishori|kishor|juvenile|baal|student of class|"
         r"class \d+|kaksha \d+|\d{1,2}[- ]?(saal|sal|varsh|year)[- ]?(ki|ka|old)|नाबालिग|बच्ची|बच्चा|किशोरी|छात्रा)\b")
ID_CUES = (r"\b(beti|bete|patni|pati|behen|bhai|maa|pita|father|mother|daughter|son|wife|husband|sister|brother|"
           r"school|college|vidyalaya|mohalla|gali|colony|village|gaon|gaanv|ward|address|ghar|photo|tasveer|video|"
           r"बेटी|पत्नी|बहन|स्कूल|कॉलेज|गांव|मोहल्ला|फोटो)\b")
COURT = (r"\b(court|adalat|nyayalaya|high court|supreme court|sessions court|magistrate|judge|nyayadhish|bail|zamanat|"
         r"hearing|sunwai|trial|mukadma|case pending|sub judice|विचाराधीन|अदालत|न्यायालय|जमानत|सुनवाई)\b")
CONTEMPT = (r"\b(judge (biased|bik gaya|corrupt)|bika hua judge|court ne galat|fixed (verdict|judgment)|court ko chahiye|"
            r"zaroor saza (milegi|hogi)|definitely guilty|doshi hai|dosh saabit|"
            r"faisla (fix|bika)|setting (ho|hui) gayi court|न्यायाधीश बिका|फैसला फिक्स)\b")
GUILT = (r"\b(hatyara|killer|rapist|balatkari|chor|doshi|guilty|apradhi|criminal|terrorist|aatanki|"
         r"हत्यारा|बलात्कारी|दोषी|अपराधी|आतंकी)\b")
CASTE_REL = (r"\b(dalit|brahmin|thakur|yadav|jat|muslim|hindu|sikh|isai|christian|maratha|kunbi|obc|sc/st|"
             r"jaati|dharm|samuday|community member|jati|मुस्लिम|हिंदू|दलित|जाति|धर्म|समुदाय)\b")
HATE = (r"\b(gaddar|deshdrohi|jihadi|anti-?national|kaafir|katua|mulla|bhakt|sickular|pakistani agent|"
        r"गद्दार|देशद्रोही|जिहादी)\b")
SUICIDE = (r"\b(suicide|aatmhatya|atmahatya|khudkushi|faansi|fansi|zehar kha|jaan de di|hanged himself|hanged herself|"
           r"आत्महत्या|खुदकुशी|फांसी)\b")
SUICIDE_METHOD = (r"\b(faansi|fansi|phanda|rassi|zehar|poison|pesticide|keetnashak|naas|sleeping pills|kood|jumped|chhalang|"
                  r"rail ke aage|nas kaati|wrist|फांसी|फंदा|जहर|कूद)\b")
ELECTION = (r"\b(election|chunav|matdan|voting|vote|candidate|ummeedwar|pratyashi|rally|prachar|campaign|party|bjp|congress|"
            r"evm|poll|चुनाव|मतदान|प्रत्याशी|उम्मीदवार|प्रचार)\b")
EXIT_POLL = r"\b(exit ?poll|opinion ?poll|survey (result|batata)|kaun jeetega|seat (prediction|anumaan)|एग्जिट पोल|ओपिनियन पोल)\b"
VIRAL = r"\b(viral|forward(ed)?|whatsapp (par|pe) (aaya|chal)|social media par chal|unverified|bataya ja raha|sutron ke mutabik)\b"
AI_MEDIA = r"\b(ai (generated|se bana|image|video|photo)|deepfake|synthetic|morphed|edited photo)\b"
PAID = r"\b(sponsored|advertorial|paid (news|partnership|post)|promoted|vigyapan|प्रायोजित)\b"
STING = r"\b(sting|hidden camera|chhupa camera|secret(ly)? record\w*|sting operation)\b"
INNOCENT_WORDS = r"\b(aaropi|accused|allegedly|kathit|आरोपी|कथित)\b"

NOTE = {
    "victim_name": "BNS s.72: publishing the name / identity of a victim of a sexual offence (s.64-71) is punishable with up to 2 years. POCSO s.23 / JJ Act s.74: "
                   "a child's identity must never be revealed.",
    "victim_cues": "In a report on a sexual offence, the relationship / school / village / locality / photo can identify the victim (BNS s.72 'any "
                   "matter which may make known the identity'). Remove these or make them very general.",
    "minor_cues": "Crime report involving a child (under 18): POCSO s.23 / JJ Act 2015 s.74 - no name, home, school, photo, relatives, "
                  "nothing that could identify the child.",
    "court_sexual": "BNS s.73: publishing court proceedings in such a case without the court's permission is prohibited (except an HC / SC judgment).",
    "source_identity": "The story reveals the identity of a confidential source (background / anonymous / off record). You had promised protection.",
    "off_record": "The off-record remark was not meant for publication (PCI norms: respect off-record).",
    "quote_unknown": "This quote was not found in any interview transcript, source note or page that was read. Hoola does not make up quotes.",
    "allegation_unbacked": "An allegation against someone (BNS s.356 defamation): there is no attribution such as 'alleged / according to police', and no proof in the fact sheet. "
                           "You need truth + public interest, or clear attribution + the other side's reply.",
    "no_reply": "A story with allegations: PCI norms require giving the accused a chance to reply (right of reply). "
                "Create a reply card or write 'no reply received'.",
    "presumed_guilt": "Words like 'murderer / guilty / thief' before sentencing = media trial (PCI norms). Write 'accused'.",
    "contempt": "Writing about a court / judge in a way that interferes with justice or lowers the court: Contempt of Courts Act "
                "1971 s.2(c). A fair and accurate report of proceedings (s.4) is fine; guessing the outcome is not.",
    "sub_judice": "The case is in court: report accurately only what happened in court; do not announce guilty / not guilty yourself.",
    "caste_religion": "In a crime / dispute report, mention caste / religion only when the news needs it (PCI norms).",
    "hate": "Words that incite hatred (provisions like BNS s.196 / s.353, PCI norms). Remove them.",
    "suicide": "Suicide report (PCI 2019, WHO basis): no method, no description of the place, no details of a note, no sensational headline; "
               "give a helpline: Tele-MANAS 14416 / 1-800-891-4416.",
    "suicide_method": "The method of suicide is described: remove it (PCI suicide-reporting guidelines).",
    "election_silence": "Publishing / showing election matter in the 48 hours before polling ends is prohibited (RP Act 1951 s.126; the ECI applied it to digital "
                        "/ social media as well).",
    "exit_poll": "An exit / opinion poll result in the RP Act s.126A ban period (from the start of polling in the first phase until half an hour after the last phase ends) is prohibited."
                 "",
    "viral_unverified": "A 'viral / forwarded / according to sources' item: check it yourself first, or write 'not confirmed'.",
    "ai_media": "AI-made / altered photo or video: needs a clear 'AI-generated' label (IT Rules amendment 2026, G.S.R. 120(E)).",
    "paid": "Paid content needs a 'Sponsored / Advertisement' label (PCI paid-news guidelines). Not without the label.",
    "sting": "Sting / hidden camera: PCI norms - only when it is in the public interest and there is no other way; keep the editor's written approval.",
    "blanks": "Some [ ] blanks are still empty.",
    "embargo": "The embargo has not ended yet.",
    "unchecked": "Some claims in the fact sheet have not been checked yet.",
    "contradicted": "A claim in the fact sheet was found wrong, but it is still in the copy.",
    "headline_long": "The headline is long (over 80 characters).",
    "avoid_word": "A word your style sheet bans.",
    "no_byline": "There is no byline / dateline.",
}


def check_copy(*, headline: str, body: str, kind: str = "news", protect: list[str] | None = None,
               secret_names: list[str] | None = None, off_record: list[str] | None = None,
               quote_pool: list[str] | None = None, claims: list[dict] | None = None,
               reply_state: str = "", election: dict | None = None, at: datetime | None = None,
               embargo: datetime | None = None, ai_media: bool = False, avoid: list[str] | None = None,
               labelled_sponsored: bool = False) -> dict:
    """Red flags for a story before it goes out. block = must be fixed (only her fix, never 'force'); warn = she decides."""
    text = f"{headline}\n{body}"
    low = text.lower()
    block: list[dict] = []
    warn: list[dict] = []

    def add(lst, code, detail=""):
        lst.append({"code": code, "say": NOTE.get(code, code), "detail": str(detail)[:300]})

    sexual = bool(re.search(SEXUAL, low, re.I))
    minor = bool(re.search(MINOR, low, re.I))
    for n in protect or []:
        n = (n or "").strip()
        if len(n) >= 3 and re.search(r"(?<![\wऀ-ॿ])" + re.escape(n.lower()) + r"(?![\wऀ-ॿ])", low):
            add(block, "victim_name", "A name that must be protected is in the copy")
    if sexual:
        cues = sorted({m.group(0) for m in re.finditer(ID_CUES, low, re.I)})
        if cues:
            add(warn, "victim_cues", ", ".join(cues[:6]))
        if re.search(COURT, low, re.I):
            add(warn, "court_sexual")
    if minor and (sexual or re.search(ALLEGE, low, re.I) or re.search(r"\b(apradh|crime|arrest|giraftar|fir)\b", low)):
        add(warn, "minor_cues")
    for n in secret_names or []:
        n = (n or "").strip()
        if len(n) >= 3 and n.lower() in low:
            add(block, "source_identity")
            break
        d = phone(n)
        if d and d in re.sub(r"\D", "", text):
            add(block, "source_identity")
            break
    pool = list(quote_pool or [])
    for q in quotes_in(body):
        if not quote_found(q, pool):
            add(block, "quote_unknown", q[:120])
    for frag in off_record or []:
        if frag and len(norm_quote(frag)) > 12 and norm_quote(frag)[:60] in norm_quote(text):
            add(block, "off_record", frag[:80])
    cl = claims or []
    allegation_sents = [s for s in sentences(text) if re.search(ALLEGE, s, re.I)]
    backed = {norm_quote(c.get("text", ""))[:80] for c in cl if c.get("status") in ("supported", "attributed")}
    for s in allegation_sents:
        if not attributed(s) and norm_quote(s)[:80] not in backed:
            add(warn, "allegation_unbacked", s[:160])
    if allegation_sents and reply_state not in ("sent", "answered", "no_response", "not_needed"):
        add(warn, "no_reply")
    if re.search(GUILT, low, re.I) and not re.search(r"\b(convicted|saza (sunai|mili)|dosh siddh|दोषी करार)\b", low):
        add(warn, "presumed_guilt")
    if re.search(COURT, low, re.I):
        if re.search(CONTEMPT, low, re.I):
            add(warn, "contempt")
        elif re.search(r"\b(pending|chal raha|sunwai|hearing|trial)\b", low):
            add(warn, "sub_judice")
    if re.search(CASTE_REL, low, re.I) and (re.search(ALLEGE, low, re.I) or re.search(r"\b(jhagda|dange|riot|maarpeet)\b", low)):
        add(warn, "caste_religion")
    if re.search(HATE, low, re.I):
        add(warn, "hate")
    if re.search(SUICIDE, low, re.I):
        add(warn, "suicide")
        if re.search(SUICIDE_METHOD, low, re.I):
            add(warn, "suicide_method")
        if re.search(SUICIDE, (headline or "").lower(), re.I):
            add(warn, "suicide", "headline mein")
    if re.search(VIRAL, low, re.I):
        add(warn, "viral_unverified")
    if ai_media or re.search(AI_MEDIA, low, re.I):
        if not re.search(r"ai se bana|ai-generated|ai generated label|एआई से बना", low):
            add(warn if not ai_media else block, "ai_media")
    if (kind == "sponsored" or re.search(PAID, low, re.I)) and not labelled_sponsored:
        add(block, "paid")
    if re.search(STING, low, re.I):
        add(warn, "sting")
    if blanks_in(text):
        add(block, "blanks", ", ".join(blanks_in(text)[:4]))
    when = _naive(at or datetime.now(timezone.utc))
    if embargo is not None and when < _naive(embargo):
        add(block, "embargo", _naive(embargo).isoformat(" ", "minutes"))
    if election and re.search(ELECTION, low, re.I):
        st = election_state(election, when)
        if st.get("silence"):
            add(block, "election_silence", st.get("say", ""))
        if st.get("exit_poll_ban") and re.search(EXIT_POLL, low, re.I):
            add(block, "exit_poll", st.get("say", ""))
    for c in cl:
        if c.get("status") == "contradicted" and norm_quote(c.get("text", ""))[:60] in norm_quote(text):
            add(warn, "contradicted", c.get("text", "")[:120])
    unchecked = [c for c in cl if c.get("status") in ("unchecked", "unclear")]
    if unchecked:
        add(warn, "unchecked", f"{len(unchecked)} daave")
    if len(headline or "") > 80:
        add(warn, "headline_long")
    for w in avoid or []:
        w = (w or "").strip().lower()
        if w and re.search(r"(?<![\wऀ-ॿ])" + re.escape(w) + r"(?![\wऀ-ॿ])", low):
            add(warn, "avoid_word", w)
    # unique by code + detail
    def uniq(lst):
        seen, out = set(), []
        for x in lst:
            k = (x["code"], x["detail"])
            if k not in seen:
                seen.add(k)
                out.append(x)
        return out
    block, warn = uniq(block), uniq(warn)
    return {"block": block, "warn": warn, "ok": not block,
            "say": ("Fit to publish (check the warnings)." if not block and warn else
                    "No red flags." if not block else f"{len(block)} item(s) must be fixed before this can be published.")}


# ---------------------------------------------------------------- election silence (RP Act s.126 / s.126A)
def _naive(d: datetime) -> datetime:
    """Compare in her local clock (IST): aware times are converted to IST, then the zone is dropped."""
    if d.tzinfo is None:
        return d
    return (d.astimezone(IST)).replace(tzinfo=None)


def _dt(v) -> datetime | None:
    if isinstance(v, datetime):
        return _naive(v)
    if not v:
        return None
    s = str(v).strip().replace("T", " ")
    for f, n in (("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d %H:%M", 16), ("%d-%m-%Y %H:%M", 16), ("%Y-%m-%d", 10), ("%d-%m-%Y", 10)):
        try:
            return datetime.strptime(s[:n], f)
        except ValueError:
            pass
    return None


def election_state(e: dict, at: datetime) -> dict:
    """e = {area, phases: [{start: 'YYYY-MM-DD HH:MM', end: 'YYYY-MM-DD HH:MM'}]} in her local clock (IST, naive).
    silence = within 48 h before the END of a phase's poll (s.126) until it ends; exit-poll ban = from the first phase start
    to 30 min after the last phase end (s.126A, as notified by ECI)."""
    at = _naive(at)
    phases = []
    for p in e.get("phases") or []:
        s, en = _dt(p.get("start")), _dt(p.get("end"))
        if en:
            phases.append((s or en - timedelta(hours=11), en))
    if not phases:
        return {}
    phases.sort()
    silence = any(en - timedelta(hours=48) <= at < en for _, en in phases)
    ban = phases[0][0] <= at < phases[-1][1] + timedelta(minutes=30)
    nxt = [en - timedelta(hours=48) for _, en in phases if en - timedelta(hours=48) > at]
    say = []
    if silence:
        say.append(f"{e.get('area') or 'This area'} is in the 48-hour election silence")
    if ban:
        say.append("exit poll ban period")
    return {"silence": silence, "exit_poll_ban": ban, "next_silence": nxt[0].isoformat(" ", "minutes") if nxt else "",
            "say": "; ".join(say)}


# ---------------------------------------------------------------- style
def style_fix(text: str, rules: list[dict]) -> tuple[str, list[str]]:
    """Her style sheet: [{from, to}] word swaps (e.g. 'chor' -> 'aaropi' is HER choice). Applied only as shown suggestions."""
    out, changed = text or "", []
    for r in rules or []:
        a, b = str(r.get("from") or "").strip(), str(r.get("to") or "").strip()
        if not a or a == b:
            continue
        pat = re.compile(r"(?<![\wऀ-ॿ])" + re.escape(a) + r"(?![\wऀ-ॿ])", re.I)
        if pat.search(out):
            out = pat.sub(b, out)
            changed.append(f"{a} -> {b}")
    return out, changed


def reply_letter(*, outlet: str, reporter: str, party: str, allegations: list[str], questions: list[str], deadline: str,
                 contact: str) -> str:
    al = "\n".join(f"{i}. {a}" for i, a in enumerate(allegations, 1)) or "1. [write the allegation]"
    qs = "\n".join(f"{i}. {q}" for i, q in enumerate(questions, 1)) or "1. What is your response to this?"
    return (f"Dear {party or '[name]'},\n\nI am {reporter or '[reporter]'} from {outlet or '[organisation]'}. We are working on a story "
            f"that includes the following about you:\n{al}\n\nFor fair reporting we also want to publish your side. Please answer "
            f"these questions by {deadline or '[date]'}:\n{qs}\n\nYour reply (or the absence of one) will be stated clearly in the "
            f"story. Contact: {contact or '[contact]'}.\n\nThank you")


def correction_line(kind: str, wrong: str, right: str, when: date) -> str:
    lab = {"correction": "Correction", "clarification": "Clarification", "update": "Update", "retraction": "Retraction",
           "apology": "Apology"}.get(kind, "Correction")
    d = when.strftime("%d-%m-%Y")
    if kind == "retraction":
        return f"{lab} ({d}): This story has been withdrawn. Reason: {right or wrong}"
    if kind == "update":
        return f"{lab} ({d}): {right}"
    return f"{lab} ({d}): It earlier said \"{wrong}\". Correct: {right}."
