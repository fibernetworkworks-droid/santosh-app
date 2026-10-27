"""v0.201.0 AWAAZ-2, the feeling engine (Phase C's core, pulled forward): the owner's 8-point ear test on
v0.199.0 proved the static delivery block teaches WORDS, not sound - pauses, breathing and soft-on-heavy
news FAILED, because a system-prompt line is too far from the moment. But gemini-3.8-live accepts mid-call
quiet notes (v0.150.1 voicecheck; a 1007 right after one flips the call to queued notes), so the note can
ride the open channel WHILE she is speaking, before he answers. This module turns her words (and, later,
TurnMeter prosody) into that one note. High precision on purpose: a wrong note is worse than no note -
a soft sad voice over a joke is uncanny - so the lexicon is small and sure, phrases only, three states,
and the caller debounces (once per turn, only on change, never two notes close together)."""

# ---------------------------------------------------------------- her words -> one state
# Each entry is a phrase she would actually say. Single risky words ("roti", "darr") stay out; a phrase
# must survive a transcript glitch to be here. Latin Hinglish first, then Devanagari, then English.

_LOW = ("bura din", "bura haal", "bura waqt", "pareshan", "udaas", "dukhi", " dukh ",
        "ro rahi", "ro raha", "rona aa", "aansu", "ansu aa", "bimar", "bimaar", "tabiyat", "hospital",
        "operation", "accident", "mar gay", "marr gay", "gujar gay", "man nahi lag", "akela feel",
        "sad", "upset", "depress", "not well", "not feeling well", "passed away", "worried",
        "दुख", "परेशान", "उदास", "बीमार", "तबीयत", "हॉस्पिटल", "ऑपरेशन", "एक्सीडेंट", "अकेल", "डर लग", "रो रही", "आंसू")

_GLAD = ("badhai", "congrat", "promot", "double ho gay", "triple ho gay", "jeet gay", "khushkhabri",
         "khush khabri", "acchi khabar", "achhi khabar", "khushi ki khabar", "sagai", "shaadi pakki",
         "order mil gaya", "deal final", "deal ho gay", "party dena", "gift mila", "selection ho gay",
         "bahut khushi", "बधाई", "खुशखबरी", "अच्छी खबर", "शादी पक्की", "सगाई", "प्रमोशन")

_TENSE = ("gussa aa", "gussa ho", "naraz", "bakwas", "jhooth", "jhuut", "fraud", "chilla raha", "chilla rahi",
          "dhamki", "pareshan kar", "tang kar", "galat bill", "galat kaam", "गुस्सा", "नाराज़", "झूठ", "धमकी")

# low wins over glad and tense (heavy news is the moment that most needs the right voice);
# tense wins over glad (an angry "party dena hogi" joke must not get a celebration voice).
ORDER = (("low", _LOW), ("tense", _TENSE), ("glad", _GLAD))

NOTE = {
    "low": ("(Deli ka note: uski baat mein dukh ya bhaari pan hai - is jawab mein dheere bolo, awaaz thodi "
            "neeche aur naram, ek chhota pause pehle. Uske saath raho, kaam ki baat baad mein, koi zor wali "
            "khushi nahi.)"),
    "glad": ("(Deli ka note: acchi khabar hai - khushi apne aap jhalke jawab mein, thodi si energy aur garmi, "
             "muskaan awaaz mein sunai de; apne apne band mein, over the top nahi.)"),
    "tense": ("(Deli ka note: wo pareshan ya gussa hai - pehle poori baat suno, phir shaant aur pakad ke jawab "
              "do, bina jaldi aur bina samjhane ki bhag-daud.)"),
}


def decide(text: str) -> tuple[str, str]:
    """Her words -> (state, the phrase that gave it away). ('', '') when nothing sure is heard.
    Deliberately keyword-first: TurnMeter prosody (pitch/level) joins later as a sharpening rule,
    never as the only signal."""
    t = f" {(text or '').lower()} "
    if len(t.strip()) < 4:
        return "", ""
    for state, phrases in ORDER:
        for p in phrases:
            if p in t:
                return state, p
    return "", ""
