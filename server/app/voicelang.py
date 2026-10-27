"""v0.114 Bhasha pakki: the call's language is decided by the SERVER, not by the voice model's mood.

Why: Gemini Live native-audio models pick and switch languages by themselves (no language_code for them), Hoola's
persona invited a flip ("follow them if they switch"), and the caller's transcript was auto-detected per utterance, so
one English sentence, one wrong-script transcript or a voice from the TV could move the whole call to another language.

    detect(text)          -> {lang, script, english, words, strong}: script by Unicode block, Hindi vs Marathi (and
                             their Roman forms) by grammar words, English share of Latin words
    LangState             -> base language (sticky), mix level (how much English she mixes), switch rules:
                             an explicit ask switches at once; otherwise two full sentences in a row in another language;
                             a few English words, greetings, numbers, OTPs and short fragments never switch
    lock_block(state)     -> Google's documented lock ("RESPOND UNMISTAKABLY IN ...") + what that language means +
                             3-5 example exchanges IN that language; goes at the top AND the end of the system prompt
    transcription_codes   -> language_codes hint for input_audio_transcription (base + English)
    check_reply(reply)    -> a reply that drifted to another language -> one quiet correction note (with a cooldown)
    remember / learned    -> her language carried to the next call (owner only)
"""
from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path
from typing import Any

log = logging.getLogger("santosh.voicelang")

LANGS: dict[str, dict[str, str]] = {
    "hi-IN": {"name": "Hindi (spoken Hinglish)", "short": "Hindi", "script": "deva"},
    "mr-IN": {"name": "Marathi", "short": "Marathi", "script": "deva"},
    "en-IN": {"name": "Indian English", "short": "English", "script": "latn"},
    "gu-IN": {"name": "Gujarati", "short": "Gujarati", "script": "gujr"},
    "bn-IN": {"name": "Bengali", "short": "Bengali", "script": "beng"},
    "pa-IN": {"name": "Punjabi", "short": "Punjabi", "script": "guru"},
    "ta-IN": {"name": "Tamil", "short": "Tamil", "script": "taml"},
    "te-IN": {"name": "Telugu", "short": "Telugu", "script": "telu"},
    "kn-IN": {"name": "Kannada", "short": "Kannada", "script": "knda"},
    "ml-IN": {"name": "Malayalam", "short": "Malayalam", "script": "mlym"},
    "or-IN": {"name": "Odia", "short": "Odia", "script": "orya"},
    "ur-IN": {"name": "Urdu", "short": "Urdu", "script": "arab"},
}
SCRIPT_LANG = {"gujr": "gu-IN", "beng": "bn-IN", "guru": "pa-IN", "taml": "ta-IN", "telu": "te-IN", "knda": "kn-IN",
               "mlym": "ml-IN", "orya": "or-IN", "arab": "ur-IN"}
BLOCKS = [("deva", 0x0900, 0x097F), ("beng", 0x0980, 0x09FF), ("guru", 0x0A00, 0x0A7F), ("gujr", 0x0A80, 0x0AFF),
          ("orya", 0x0B00, 0x0B7F), ("taml", 0x0B80, 0x0BFF), ("telu", 0x0C00, 0x0C7F), ("knda", 0x0C80, 0x0CFF),
          ("mlym", 0x0D00, 0x0D7F), ("arab", 0x0600, 0x06FF)]

# grammar words (not nouns): Marathi vs Hindi, in Devanagari and in Roman letters
MR_DEVA = {"आहे", "आहेत", "आहेस", "नाही", "होते", "होता", "होती", "झाला", "झाली", "झालं", "केलं", "केला", "केली", "करतो",
           "करते", "करतोय", "करतेय", "मला", "तुला", "तुम्ही", "आम्ही", "आपण", "काय", "कसं", "कसा", "कशी", "का", "पाहिजे",
           "हवं", "हवा", "सांग", "सांगा", "बोला", "बघ", "बघा", "आता", "उद्या", "आज", "मी", "तू", "त्याला", "तिला", "जा",
           "येतो", "येते", "गेलो", "गेले", "दे", "द्या", "करा", "कर", "ना", "हो", "बरं", "ठीक", "चालेल", "नको", "पण"}
HI_DEVA = {"है", "हैं", "हूँ", "हूं", "हो", "था", "थी", "थे", "नहीं", "मैं", "मुझे", "मेरा", "मेरी", "आप", "आपका", "तुम",
           "क्या", "कैसे", "कैसा", "क्यों", "रहा", "रही", "रहे", "गया", "गई", "गए", "करो", "करना", "कर", "दो", "दीजिए",
           "बताओ", "बताइए", "अभी", "कल", "आज", "भी", "तो", "और", "लेकिन", "चाहिए", "वाला", "वाली", "कि", "को", "से", "में"}
MR_ROMAN = {"aahe", "ahe", "aahet", "ahet", "nahi", "hote", "hota", "hoti", "zala", "jhala", "zali", "jhali", "zhala",
            "kela", "keli", "kela", "karto", "karte", "kartoy", "kartey", "mala", "tula", "tumhi", "amhi", "aamhi", "apan",
            "kay", "kasa", "kasa", "kashi", "pahije", "hava", "havay", "sang", "sanga", "bagh", "bagha", "ata", "aata",
            "udya", "mi", "tu", "tyala", "tila", "yeto", "yete", "gelo", "gele", "dya", "kara", "nako", "pan", "bara",
            "chalel", "kuthe", "kiti", "ka"}
HI_ROMAN = {"hai", "hain", "hoon", "hu", "hun", "tha", "thi", "nahin", "nahi", "main", "mein", "mujhe", "mera",
            "meri", "aap", "aapka", "tum", "kya", "kaise", "kaisa", "kyun", "kyon", "raha", "rahi", "rahe", "gaya", "gayi",
            "gaye", "karo", "karna", "kar", "dijiye", "batao", "bataiye", "abhi", "kal", "aaj", "bhi", "toh", "aur",
            "lekin", "chahiye", "wala", "wali", "ki", "ko", "se", "ka", "ke", "yaar", "accha", "achha", "theek", "thik"}
EN_WORDS = {"the", "is", "are", "was", "were", "you", "your", "please", "what", "how", "why", "when", "where", "can",
            "could", "would", "should", "i", "my", "me", "it", "to", "of", "and", "or", "do", "does", "did", "this", "that",
            "for", "with", "have", "has", "will", "not", "don't", "it's", "i'm", "we", "they", "he", "she", "be", "an",
            "a", "in", "on", "at", "from", "about", "just", "need", "want", "tell", "send", "call", "check", "there",
            "here", "if", "so", "but", "yes", "no", "okay", "ok", "thanks", "thank", "hello", "hi", "sorry", "let", "us"}
FILLERS = {"haan", "han", "hmm", "hm", "ok", "okay", "achha", "accha", "theek", "thik", "ji", "hello", "hi", "haa",
           "ho", "hoy", "bara", "nahi", "na", "yes", "no", "हाँ", "हां", "हो", "ठीक", "नाही", "नहीं", "जी"}
ASK_SWITCH = [  # her own request to change the language
    (re.compile(r"\b(english|angrezi|इंग्लिश|अंग्रेज़ी|अंग्रेजी)\s*(me|mein|madhe|मध्ये|में|mai)?\s*(bolo|boliye|baat|bola|बोलो|बोलिए|बोला|बात)|\b(speak|talk|reply)\s+(in\s+)?english\b", re.I), "en-IN"),
    (re.compile(r"\b(marathi|मराठी)\s*(me|mein|madhe|मध्ये|में|t|त)?\s*(bolo|boliye|baat|bola|बोलो|बोलिए|बोला|बात|bol|बोल)|\b(speak|talk|reply)\s+(in\s+)?marathi\b", re.I), "mr-IN"),
    (re.compile(r"\b(hindi|हिंदी|हिन्दी)\s*(me|mein|madhe|मध्ये|में|mai|t)?\s*(bolo|boliye|baat|bola|बोलो|बोलिए|बोला|बात|bol)|\b(speak|talk|reply)\s+(in\s+)?hindi\b", re.I), "hi-IN"),
    (re.compile(r"\b(gujarati|ગુજરાતી)\b.*\b(bolo|boliye|baat|bolo|speak|talk)", re.I), "gu-IN"),
    (re.compile(r"\b(bengali|bangla|বাংলা)\b.*\b(bolo|boliye|baat|speak|talk|bolun)", re.I), "bn-IN"),
    (re.compile(r"\b(tamil|தமிழ்)\b.*\b(bolo|boliye|baat|speak|talk|pesu|pesungal)", re.I), "ta-IN"),
    (re.compile(r"\b(telugu|తెలుగు)\b.*\b(bolo|boliye|baat|speak|talk|matladu)", re.I), "te-IN"),
    (re.compile(r"\b(kannada|ಕನ್ನಡ)\b.*\b(bolo|boliye|baat|speak|talk|maatadi)", re.I), "kn-IN"),
    (re.compile(r"\b(malayalam|മലയാളം)\b.*\b(bolo|boliye|baat|speak|talk)", re.I), "ml-IN"),
    (re.compile(r"\b(punjabi|ਪੰਜਾਬੀ)\b.*\b(bolo|boliye|baat|speak|talk)", re.I), "pa-IN"),
]


def norm_code(code: str) -> str:
    c = (code or "").strip().replace("_", "-")
    if not c:
        return "hi-IN"
    low = c.lower()
    for k in LANGS:
        if k.lower() == low or k.split("-")[0] == low.split("-")[0]:
            return k
    return "hi-IN"


def _scripts(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for ch in text or "":
        o = ord(ch)
        if ch.isalpha():
            if o < 0x250:
                out["latn"] = out.get("latn", 0) + 1
                continue
            for name, lo, hi in BLOCKS:
                if lo <= o <= hi:
                    out[name] = out.get(name, 0) + 1
                    break
            else:
                out["other"] = out.get("other", 0) + 1
        elif 0x0900 <= o <= 0x0DFF or 0x0600 <= o <= 0x06FF:   # Indic signs / matras are not "alpha" for every char
            for name, lo, hi in BLOCKS:
                if lo <= o <= hi:
                    out[name] = out.get(name, 0) + 1
                    break
    return out


def detect(text: str) -> dict[str, Any]:
    """What language one line is in. `strong` = enough real words to count for a switch."""
    t = (text or "").strip()
    sc = _scripts(t)
    total = sum(sc.values())
    words = re.findall(r"[\w'ऀ-ॿঀ-৿਀-੿઀-૿଀-୿஀-௿ఀ-౿ಀ-೿ഀ-ൿ؀-ۿ]+", t.lower())
    real = [w for w in words if w not in FILLERS and not w.isdigit()]
    out: dict[str, Any] = {"lang": "", "script": "", "english": 0.0, "words": len(words), "strong": False}
    if not total or not real:
        return out
    script = max(sc, key=sc.get)
    out["script"] = script
    if script == "other":
        out["lang"] = "other"           # Georgian, Cyrillic, CJK...: a mis-transcription, never her language
        return out
    if script in SCRIPT_LANG:
        out["lang"] = SCRIPT_LANG[script]
    elif script == "deva":
        mr = sum(1 for w in words if w in MR_DEVA)
        hi = sum(1 for w in words if w in HI_DEVA)
        out["lang"] = "mr-IN" if mr > hi else "hi-IN"
        out["grammar"] = abs(mr - hi)
    else:   # Latin letters: English, or Hindi / Marathi written in Roman letters
        en = sum(1 for w in words if w in EN_WORDS)
        mr = sum(1 for w in words if w in MR_ROMAN and w not in HI_ROMAN)
        hi = sum(1 for w in words if w in HI_ROMAN and w not in MR_ROMAN)
        both = sum(1 for w in words if w in HI_ROMAN and w in MR_ROMAN)
        indic = mr + hi + both
        out["english"] = round(en / max(1, len(words)), 2)
        if en >= 2 and en >= len(words) * 0.35 and indic <= max(0, int(en * 0.2)):
            out["lang"] = "en-IN"
        elif mr > hi:
            out["lang"] = "mr-IN"
        elif indic:
            out["lang"] = "hi-IN"
        else:
            out["lang"] = "en-IN" if en else ""
        out["grammar"] = abs(mr - hi)
    out["strong"] = len(real) >= 4 and (script != "deva" and script != "latn" or out.get("grammar", 0) >= 1
                                        or out["lang"] == "en-IN")
    return out


def asked_switch(text: str) -> str:
    """Her explicit 'Marathi mein bolo' / 'speak in English' -> that language code, else ''."""
    for rx, code in ASK_SWITCH:
        if rx.search(text or ""):
            return code
    return ""


class LangState:
    """One call's language: sticky base, English-mix level, switch rules (Bolna-style)."""

    def __init__(self, base: str, source: str = "app"):
        self.base = norm_code(base)
        self.source = source
        self.mix = 0.25 if self.base == "hi-IN" else 0.1    # share of English words she uses
        self._cand = ""
        self._streak = 0
        self.turns = 0
        self.by_lang: dict[str, int] = {}
        self.switches: list[str] = []
        self.drifts = 0
        self.unclear = 0
        self._last_note_turn = -10

    @property
    def name(self) -> str:
        return LANGS.get(self.base, LANGS["hi-IN"])["name"]

    def mix_words(self) -> str:
        if self.base not in ("hi-IN", "mr-IN") and self.base != "en-IN":
            return "everyday English words only where she uses them herself"
        if self.mix < 0.15:
            return "very few English words (she mostly speaks pure " + LANGS[self.base]["short"] + ")"
        if self.mix < 0.4:
            return "some everyday English words (work / tech words), like she does"
        return "plenty of English words mixed in, the way she talks (heavy Hinglish), but the sentence grammar stays " \
               + LANGS[self.base]["short"]

    def hear(self, user_text: str) -> dict[str, Any]:
        """Her finished turn. Returns {switched: code|'', unclear: bool, lang}."""
        d = detect(user_text)
        res = {"switched": "", "unclear": False, "lang": d["lang"]}
        if not d["lang"] and not d["words"]:
            return res
        self.turns += 1
        if d["lang"] == "other" or (d["script"] == "arab" and self.base != "ur-IN"):
            self.unclear += 1
            res["unclear"] = True
            return res
        if d["lang"]:
            self.by_lang[d["lang"]] = self.by_lang.get(d["lang"], 0) + 1
        if d["script"] == "latn" and self.base in ("hi-IN", "mr-IN") and d["lang"] in ("hi-IN", "mr-IN"):
            self.mix = round(0.7 * self.mix + 0.3 * d["english"], 3)
        want = asked_switch(user_text)
        if want and want != self.base:
            self._switch(want, "asked")
            res["switched"] = want
            return res
        if not d["strong"] or not d["lang"] or d["lang"] == self.base:
            if d["lang"] == self.base:
                self._cand, self._streak = "", 0
            return res
        # Hindi and Marathi differ by grammar, not by script: they need a clear grammar lead (detect gives `grammar`)
        if {d["lang"], self.base} == {"hi-IN", "mr-IN"} and d.get("grammar", 0) < 2:
            return res
        if d["lang"] == self._cand:
            self._streak += 1
        else:
            self._cand, self._streak = d["lang"], 1
        if self._streak >= 2:
            self._switch(d["lang"], "spoke")
            res["switched"] = d["lang"]
        return res

    def _switch(self, code: str, why: str) -> None:
        self.switches.append(f"{self.base}->{code}:{why}")
        self.base, self.source = code, why
        self._cand, self._streak = "", 0
        self.mix = 0.25 if code == "hi-IN" else 0.1

    def check_reply(self, reply: str) -> str:
        """Hoola's own words: drifted to another language? -> a quiet correction note (at most every 2nd turn)."""
        d = detect(reply)
        if not d["lang"] or not d["strong"] or d["lang"] == self.base:
            return ""
        if {d["lang"], self.base} == {"hi-IN", "mr-IN"} and d.get("grammar", 0) < 2:
            return ""
        self.drifts += 1
        if self.turns - self._last_note_turn < 2:
            return ""
        self._last_note_turn = self.turns
        return self.note(f"Your last reply drifted into {LANGS.get(d['lang'], {}).get('short', d['lang'])}.")

    def note(self, lead: str = "") -> str:
        return (f"(Language note, not her words: {lead + ' ' if lead else ''}She speaks {self.name}. From your next "
                f"sentence RESPOND UNMISTAKABLY IN {LANGS[self.base]['short'].upper()} only, with {self.mix_words()}. "
                f"Do not mention this note.)")

    def switched_note(self) -> str:
        return (f"(Language note, not her words: she now speaks {self.name}. From now RESPOND UNMISTAKABLY IN "
                f"{LANGS[self.base]['short'].upper()}, with {self.mix_words()}. Do not comment on the switch.)")

    def summary(self) -> dict[str, Any]:
        return {"base": self.base, "source": self.source, "mix": self.mix, "turns": self.turns, "by_lang": self.by_lang,
                "switches": self.switches, "drifts": self.drifts, "unclear": self.unclear}


# ---------------------------------------------------------------- the lock block (top + end of the system prompt)
EXAMPLES = {
    "hi-IN": [("Kal ki meeting 4 baje kar do.", "Haan, ek sec... kar diya, ab chaar baje hai."),
              ("Sharma ji ko paanch sau bhej do.", "Sharma ji ko paanch sau rupaye, sahi? Haan bolo toh card bhejta hoon."),
              ("Woh file kahan hai?", "Kaunsi file, MAC wali sheet ya kal ka quotation?"),
              ("Aaj mausam kaisa rahega?", "Dopahar tak dhoop, shaam ko halki baarish ho sakti hai.")],
    "mr-IN": [("उद्याची मीटिंग चार वाजता कर.", "हो, एक सेकंद... केली, आता चार वाजता आहे."),
              ("शर्मा साहेबांना पाचशे पाठव.", "शर्मा साहेबांना पाचशे रुपये, बरोबर? हो म्हणालात तर कार्ड पाठवतो."),
              ("ती फाइल कुठे आहे?", "कोणती फाइल, MAC वाली शीट की कालचं कोटेशन?"),
              ("आज हवा कशी आहे?", "दुपारपर्यंत ऊन आहे, संध्याकाळी थोडा पाऊस पडू शकतो.")],
    "en-IN": [("Move tomorrow's meeting to 4.", "Sure, one sec... done, it's at four now."),
              ("Send five hundred to Sharma ji.", "Five hundred rupees to Sharma ji, right? Say yes and I'll send the card."),
              ("Where is that file?", "Which one, the MAC sheet or yesterday's quotation?")],
    "gu-IN": [("કાલની મીટિંગ ચાર વાગ્યે કરી દો.", "હા, એક સેકન્ડ... કરી દીધી, હવે ચાર વાગ્યે છે."),
              ("શર્માભાઈને પાંચસો મોકલો.", "શર્માભાઈને પાંચસો રૂપિયા, બરાબર? હા કહો તો કાર્ડ મોકલું."),
              ("પેલી ફાઇલ ક્યાં છે?", "કઈ ફાઇલ, MAC વાળી શીટ કે ગઈકાલનું કોટેશન?")],
    "bn-IN": [("কালকের মিটিং চারটেয় করে দাও।", "হ্যাঁ, এক সেকেন্ড... করে দিয়েছি, এখন চারটেয়।"),
              ("শর্মাজিকে পাঁচশো পাঠাও।", "শর্মাজিকে পাঁচশো টাকা, ঠিক তো? হ্যাঁ বললে কার্ড পাঠাচ্ছি।"),
              ("ওই ফাইলটা কোথায়?", "কোন ফাইল, MAC-এর শিট না কালকের কোটেশন?")],
    "pa-IN": [("ਕੱਲ੍ਹ ਦੀ ਮੀਟਿੰਗ ਚਾਰ ਵਜੇ ਕਰ ਦਿਓ।", "ਹਾਂ ਜੀ, ਇੱਕ ਸਕਿੰਟ... ਕਰ ਦਿੱਤੀ, ਹੁਣ ਚਾਰ ਵਜੇ ਹੈ।"),
              ("ਸ਼ਰਮਾ ਜੀ ਨੂੰ ਪੰਜ ਸੌ ਭੇਜ ਦਿਓ।", "ਸ਼ਰਮਾ ਜੀ ਨੂੰ ਪੰਜ ਸੌ ਰੁਪਏ, ਠੀਕ ਹੈ? ਹਾਂ ਕਹੋ ਤਾਂ ਕਾਰਡ ਭੇਜਦਾ ਹਾਂ।")],
    "ta-IN": [("நாளைய மீட்டிங்கை நான்கு மணிக்கு மாத்துங்க.", "சரி, ஒரு செகண்ட்... மாத்திட்டேன், இப்போ நான்கு மணிக்கு."),
              ("சர்மா சாருக்கு ஐநூறு அனுப்புங்க.", "சர்மா சாருக்கு ஐநூறு ரூபாய், சரியா? ஆமா சொன்னா கார்டு அனுப்பறேன்.")],
    "te-IN": [("రేపటి మీటింగ్ నాలుగు గంటలకు మార్చండి.", "సరే, ఒక్క సెకను... మార్చాను, ఇప్పుడు నాలుగు గంటలకు."),
              ("శర్మ గారికి ఐదు వందలు పంపండి.", "శర్మ గారికి ఐదు వందల రూపాయలు, సరేనా? అవును అంటే కార్డ్ పంపిస్తాను.")],
    "kn-IN": [("ನಾಳೆಯ ಮೀಟಿಂಗ್ ನಾಲ್ಕು ಗಂಟೆಗೆ ಮಾಡಿ.", "ಸರಿ, ಒಂದು ಸೆಕೆಂಡ್... ಮಾಡಿದೆ, ಈಗ ನಾಲ್ಕು ಗಂಟೆಗೆ."),
              ("ಶರ್ಮಾ ಅವರಿಗೆ ಐನೂರು ಕಳಿಸಿ.", "ಶರ್ಮಾ ಅವರಿಗೆ ಐನೂರು ರೂಪಾಯಿ, ಸರಿನಾ? ಹೌದು ಅಂದ್ರೆ ಕಾರ್ಡ್ ಕಳಿಸ್ತೀನಿ.")],
    "ml-IN": [("നാളത്തെ മീറ്റിംഗ് നാലുമണിക്ക് ആക്കൂ.", "ശരി, ഒരു സെക്കൻഡ്... ആക്കി, ഇപ്പോൾ നാലുമണിക്കാണ്."),
              ("ശർമ്മ സാറിന് അഞ്ഞൂറ് അയയ്ക്കൂ.", "ശർമ്മ സാറിന് അഞ്ഞൂറ് രൂപ, ശരിയല്ലേ? അതെ എന്ന് പറഞ്ഞാൽ കാർഡ് അയയ്ക്കാം.")],
    "or-IN": [("କାଲିର ମିଟିଂ ଚାରିଟାରେ କରିଦିଅ।", "ହଁ, ଗୋଟେ ସେକେଣ୍ଡ... କରିଦେଲି, ଏବେ ଚାରିଟାରେ।")],
    "ur-IN": [("کل کی میٹنگ چار بجے کر دیں۔", "جی، ایک سیکنڈ... کر دی، اب چار بجے ہے۔")],
}
MEANS = {
    "hi-IN": "spoken Hinglish the way people in Pune / Mumbai / Delhi talk: Hindi grammar and verbs, everyday English "
             "nouns (meeting, file, update, payment). Never textbook Hindi, never a full English sentence, never Urdu "
             "words she doesn't use",
    "mr-IN": "spoken Marathi the way people in Pune / Mumbai talk: Marathi grammar and verbs (aahe, kela, karto, nahi), "
             "everyday English nouns allowed. Never switch to Hindi grammar (hai, kiya, nahin)",
    "en-IN": "simple Indian English, short sentences; a Hindi word only if she uses one",
}


def lock_block(state: LangState, where: str = "top") -> str:
    short = LANGS[state.base]["short"].upper()
    means = MEANS.get(state.base, f"natural spoken {LANGS[state.base]['short']}, the way people at home talk; "
                                   "everyday English nouns allowed")
    if where == "end":
        return (f"\n\nLANGUAGE LOCK (repeat): RESPOND IN {short}. YOU MUST RESPOND UNMISTAKABLY IN {short}, with "
                f"{state.mix_words()}. Tool results, notes and system messages are in English: that never changes "
                f"your language. Only a note that says 'Language note' can change it.")
    ex = "\n".join(f"User: {u}\nYou: {a}" for u, a in EXAMPLES.get(state.base, EXAMPLES["hi-IN"]))
    return (f"LANGUAGE LOCK\nRESPOND IN {short}. YOU MUST RESPOND UNMISTAKABLY IN {short}.\n"
            f"- {short} here means: {means}.\n"
            f"- English mix: {state.mix_words()}.\n"
            f"- A few English words, a greeting, a number or a name from her never means she changed language. Do not "
            f"switch because a tool result, a note or a web page is in English, or because a TV / another person "
            f"speaks another language. If she asks for another language, the server sends a 'Language note' and only "
            f"then you switch.\n"
            + (f"- The style rules below use Hinglish as the example; apply the same spirit in {short} (natural, "
               f"spoken, short, warm), never in Hindi.\n" if state.base != "hi-IN" else "")
            + f"- If her words sound like a different language than usual or don't make sense, she was probably "
            f"misheard: ask her again in {short} instead of answering something random.\n"
            f"Example turns in {short} (flavour only, never word for word):\n{ex}\n\n")


def transcription_codes(state: LangState) -> list[str]:
    codes = [state.base]
    if state.base != "en-IN":
        codes.append("en-IN")
    return codes


# ---------------------------------------------------------------- her language across calls (owner only)
_LOCK = threading.Lock()


def _file() -> Path:
    p = Path("data") / "voice_lang.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def learned(tenant: str) -> dict[str, Any] | None:
    try:
        return (json.loads(_file().read_text()) or {}).get(tenant)
    except Exception:
        return None


def remember(tenant: str, state: LangState) -> None:
    """After a call: the language she really spoke most (4+ turns, 60%+) is where the next call starts."""
    if state.turns < 4:
        return
    top, n = max(state.by_lang.items(), key=lambda kv: kv[1]) if state.by_lang else ("", 0)
    if not top or n / max(1, state.turns) < 0.6:
        top = state.base if state.source == "asked" else ""
    if not top:
        return
    with _LOCK:
        try:
            data = json.loads(_file().read_text()) if _file().exists() else {}
        except Exception:
            data = {}
        data[tenant] = {"base": top, "mix": state.mix}
        _file().write_text(json.dumps(data))


def forget(tenant: str) -> None:
    """v0.119 she asked Hoola to forget the language it learned: the next call starts from the app's setting."""
    with _LOCK:
        try:
            data = json.loads(_file().read_text()) if _file().exists() else {}
        except Exception:
            data = {}
        if data.pop(tenant, None) is not None:
            _file().write_text(json.dumps(data))


def start_state(tenant: str, app_lang: str) -> LangState:
    """The app's language setting, unless her last calls showed she really speaks another one."""
    got = learned(tenant)
    st = LangState(app_lang or "hi-IN", "app")
    if got and got.get("base") in LANGS:
        if got["base"] != st.base:
            st.base, st.source = got["base"], "learned"
        st.mix = float(got.get("mix", st.mix))
    return st


ASK_AGAIN = re.compile(r"(phir se|ek baar phir|dobara|samajh nahi|samjha nahi|samjhi nahi|kya kaha|kya bola|sunai nahi|"
                       r"repeat|pardon|didn't catch|पुन्हा|परत सांगा|समजलं नाही|फिर से|दोबारा|समझ नहीं)", re.I)
HER_FIX = re.compile(r"^(nahi nahi|nahin nahin|no no|arre nahi|galat|maine .{0,30} (bola|kaha) tha|मैंने .{0,30} कहा|"
                     r"नहीं नहीं|नाही नाही|चुकीचं)", re.I)


def repair_signals(user: str, reply: str) -> dict[str, int]:
    """Cheap counters: Hoola asked her to repeat, she corrected Hoola."""
    return {"asked_again": 1 if ASK_AGAIN.search(reply or "") else 0,
            "her_corrections": 1 if HER_FIX.search((user or "").strip()) else 0}
