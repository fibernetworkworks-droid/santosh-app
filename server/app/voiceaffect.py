"""v0.201.0 AWAAZ-2, the feeling engine (Phase C's core, pulled forward): the owner's 8-point ear test on
v0.199.0 proved the static delivery block teaches WORDS, not sound - pauses, breathing and soft-on-heavy
news FAILED, because a system-prompt line is too far from the moment. But gemini-3.8-live accepts mid-call
quiet notes (v0.150.1 voicecheck; a 1007 right after one flips the call to queued notes), so the note can
ride the open channel WHILE she is speaking, before he answers. This module turns her words into that one
note. High precision on purpose: a wrong note is worse than no note - a soft sad voice over a joke is
uncanny - so the lexicon is small and sure, phrases only, three states, and the caller debounces (once per
turn, only on change, never two notes close together).

v0.208.0 AWAAZ-3 (Phase C's remainder): the TurnMeter prosody joins as the promised SHARPENING rule, never
as the only signal. Her words still pick the state; her voice THIS turn, measured against HER OWN baseline
(voicestyle profile facts - phone mics lie, but her normal does not), can now VETO a glad note it
contradicts (sarcasm, tiredness - a celebration voice over flat words is exactly the uncanny note the
precision rule forbids), CONFIRM a low one, and her measured thinking-pauses add a 'jaldi mat kaato' rider
(the ear test's list-rush failure, grounded in her own pauses).

v0.220.0 SOORAT (Wave 3 of the PERFECT plan, Phase C's last remainder - prosody AT the moment): the v0.201
note speaks once and dies, while the scripted moments around it keep their own fixed energy - after heavy
news a tool's ack clip can still go bright on 'mil gaya!', and when SHE MOVES (heavy to light, anger to
calm) nothing tells him to move with her. Two pieces here: TAG, a short tone clause per state that the
caller rides on the scripted notes while the state is still fresh (TONE_S), and flip_note(), the one
clause a state FLIP adds so the next reply drops the old energy and follows her."""

import math

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

# ---------------------------------------------------------------- her voice -> sharpen the state (v0.208)
# All prosody here is RELATIVE to her own profile (voicestyle facts), never absolute numbers: a phone mic
# in a purse says nothing about "loud", but -4 dB against her own median does. And prosody only ever
# sharpens a state her words already picked - it never wakes a note alone.
MIN_VOICED_S = 1.2   # less real voice than this in the turn and her prosody proves nothing yet
PAUSE_MS = 600       # a mid-turn gap this long is her THINKING, not a comma
PAUSE_N = 2          # ...and she has done it twice this turn

PAUSE_RIDER = ("(Is baat mein woh beech beech mein ruk ke soch rahi hai, baat adhoori nahi - uske rukne par "
               "usse jaldi mat kaato; apne jawab ke items bhi ek ek saans le ke bolo.)")


def _st_down(pitch, base_hz) -> float | None:
    """How far her voice sits below her own normal right now, in semitones (None when either side is missing
    or absurd - a 30 Hz 'baseline' is a mic artefact, not her voice)."""
    try:
        if not pitch or not base_hz or base_hz < 75 or base_hz > 400:
            return None
        return 12.0 * math.log2(float(pitch) / float(base_hz))
    except Exception:
        return None


def sharpen(state: str, pros: dict | None, base: dict | None) -> tuple[str, str]:
    """The words' state + her prosody this turn (voicestyle.TurnMeter.peek()) + her baseline -> (state, why).
    'why' tells the caller what happened: no_words (prosody never fires alone), words_lead (no sure signal
    from the voice - words win, the v0.202 behaviour), confirmed_low (voice agrees with heavy news), or a
    veto_* (the voice contradicted the words - no note goes out, and the caller must NOT move its debounce
    clock, so stronger evidence later can still speak)."""
    if not state:
        return "", "no_words"
    if not pros or not base or (pros.get("voiced_s") or 0) < MIN_VOICED_S:
        return state, "words_lead"
    down = _st_down(pros.get("pitch"), base.get("pitch_hz"))
    level, base_level = pros.get("level"), base.get("level_db")
    spread, base_spread = pros.get("spread"), base.get("tone_spread_st")
    if state == "glad":
        if down is not None and down <= -2.0:
            return "", "veto_glad_down"        # her voice FELL on the "good news": sarcasm ya thakaan
        if level is not None and base_level is not None and level <= base_level - 4.0:
            return "", "veto_glad_quiet"       # she went quieter, not happier
        if spread is not None and base_spread is not None and spread <= 2.0 and base_spread >= 5.0:
            return "", "veto_glad_flat"        # her expressive voice went flat: no real joy in it
    if state == "low":
        if (down is not None and down <= -1.0) or (level is not None and base_level is not None
                                                   and level <= base_level - 3.0):
            return state, "confirmed_low"      # her voice agrees with her words: the note is safe
    # tense is never vetoed: a raised voice IS the agreement, and her words already said it.
    return state, "words_lead"


def pause_rider(pros: dict | None) -> str | None:
    """Her measured pauses say she is thinking while talking: whatever note goes out gains one 'don't rush
    her' line. Only ever an ADDITION to a word-triggered note - never a note of its own (no_words rule)."""
    if not pros or (pros.get("voiced_s") or 0) < MIN_VOICED_S:
        return None
    if sum(1 for p in (pros.get("pauses") or []) if p >= PAUSE_MS) < PAUSE_N:
        return None
    return PAUSE_RIDER

# ---------------------------------------------------------------- her tone, at the moment (v0.220 SOORAT)
# A state note speaks ONCE for one reply (high precision, debounced); these two pieces let his energy
# FOLLOW her across the moments in between. TAG is what a scripted note carries while the tone is still
# fresh; the caller decides which moments are scripted enough to need it (the ack clips that cannot be
# retuned, the result / stall notes he reads out, the reconnect re-brief). TONE_S is deliberately a
# lifetime, not a debounce: fresh words re-anchor it, and after it lapses his own band is allowed back.
TONE_S = 150

TAG = {
    "low": ("(Awaaz is pal: dheere aur naram - bhaari baat ke beech hain; koi zor ki khushi ya tez 'mil gaya' "
            "wali awaaz nahi.)"),
    "tense": ("(Awaaz is pal: shaant aur pakad ke - woh pareshan ya gusse mein hai; na jaldi, na uchhal.)"),
    "glad": ("(Awaaz is pal: thodi garm aur zinda - acchi khabar chal rahi hai; sookhi helpdesk awaaz nahi.)"),
}

FLIP_FROM = {"low": "bhaari/udaas se", "glad": "khush/halke se", "tense": "gusse/pareshani se"}
FLIP_TO = {"low": "phir bhaari par", "glad": "halke-khush par", "tense": "gusse/pareshani par"}


def flip_note(prev: str, cur: str) -> str | None:
    """A state FLIP (she moved): the clause the note gains so his energy follows her - 'pichli energy abhi
    se chhod do'. None when there is no flip (first note, same state again, or an unknown state)."""
    if not prev or prev == cur or prev not in FLIP_FROM or cur not in FLIP_TO:
        return None
    return (f"(Uski awaaz abhi badli hai - {FLIP_FROM[prev]} {FLIP_TO[cur]} aa gayi; apni awaaz uske saath "
            "le jao, pichli energy isi pal chhod do.)")


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
    Deliberately keyword-first: TurnMeter prosody (pitch/level) is the sharpening rule on top (sharpen,
    v0.208), never the only signal."""
    t = f" {(text or '').lower()} "
    if len(t.strip()) < 4:
        return "", ""
    for state, phrases in ORDER:
        for p in phrases:
            if p in t:
                return state, p
    return "", ""
