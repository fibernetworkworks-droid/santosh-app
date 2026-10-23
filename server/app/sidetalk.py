"""v0.142 Doosre se baat: Hoola never answers talk that is not for it.

Two people talking to each other near the phone, her phone / WhatsApp call to a friend, the TV: Gemini Live hears all of
it as "the user". This module holds the small, testable rules the call uses:

- `wants_hold(text)`: her own words that put Hoola on hold ("ek minute, main kisi se baat kar rahi hoon", "chup raho",
  "phone aa gaya"...).
- `called(text, names)`: she called Hoola by name ("Santosh, ab batao", "हूला सुनो") - the only way a side-talk hold ends
  by voice. A name used ABOUT Hoola to someone else ("Santosh ko bolti hoon", "Hoola ne kaha tha") is not a call.
- `names_for(tenant, avatar)`: the names that count (her avatar's name, "Hoola", the ways the transcript misheard the name
  that she corrected before).
- the notes Gemini gets when the hold starts / ends, and the `side_talk` tool Gemini itself calls when it judges that the
  talk is between other people.

While on hold the call drops every reply Gemini makes, refuses every tool, keeps none of that talk in the chat / memory /
learning, and (for a phone call) sends no microphone audio at all.
"""
from __future__ import annotations

import difflib
import re

from .gyaan.norm import phon

# words after a name that make it a mention ABOUT Hoola, not a call TO it
_ABOUT = {"ko", "ne", "se", "ka", "ki", "ke", "par", "pe", "mein", "me", "wala", "wali", "wale", "jaisa", "jaisi", "ne", "la",
          "ni", "chi", "cha", "che", "kaise", "kitna", "kitni", "ki"}
# words before a name that make it a call ("hey Santosh", "arey Hoola", "haan Santosh", "suno Santosh")
_CALL_BEFORE = {"hey", "hi", "he", "hello", "helo", "ok", "okay", "oke", "are", "arey", "arre", "aare", "oye", "oy", "suno",
                "sun", "suniye", "haan", "han", "ha", "acha", "accha", "achha", "bas", "ab", "chalo", "o", "ae", "ey", "ji"}

# she asks Hoola to go quiet because she is talking to someone else (phrases, not single words: a bare "ruko" means "stop
# this sentence", which the interrupt already does)
_HOLD = [
    r"\bkisi\s+(aur|or|dusr\w*|doosr\w*)?\s*se\s+baat", r"\b(dost|friend|bhai|didi|mummy|papa|sir|madam|customer|uncle|aunty)"
    r"\s+se\s+baat\s+kar\s+(rah[ai]|rahi|raha)", r"\bmain\s+baat\s+kar\s+(rah[ai])\s+(hoon|hu|hun)\b",
    r"\bchup\s+(raho|rahiye|ho\s+jao|ho\s+jaiye|baitho|kar\s*ja)", r"\b(mat|na)\s+bolo\b", r"\bbolna\s+mat\b",
    r"\b(phone|call)\s+(aa\s+gaya|aaya|aa\s+gayi|aayi|aa\s+raha|aa\s+rahi|pe\s+hoon|par\s+hoon|pe\s+hu|par\s+hu)",
    r"\bhold\s+(karo|kar\s+do|pe|par|rakho)\b", r"\bek\s+(minute|min|second|sec)\s+(ruko|rukiye|ruk\s+jao|chup)",
    r"\bthod[ia]\s+(der|der\s+ke\s+liye)\s+(ruko|rukiye|chup|ruk\s+jao)",
    r"\b(abhi|baad)\s+(mein|me)\s+baat\s+(karte|karenge|karti|karta)", r"\btum\s+mat\s+(bolo|bolna|suno)",
    r"\b(be\s+quiet|stay\s+quiet|hold\s+on|one\s+(sec|second|minute)\s+(please)?\s*i'?m\s+(talking|on\s+a\s+call)|"
    r"i'?m\s+talking\s+to\s+(someone|somebody|my))",
    # Devanagari: "चुप रहो", "मत बोलो", "किसी से बात", "फोन आ गया"
    r"चुप\s*(रहो|रहिए|हो\s*जाओ)", r"मत\s*बोलो", r"किसी\s*(और\s*)?से\s*बात", r"(फोन|फ़ोन|कॉल)\s*आ\s*(गया|गई|गयी|रहा)",
    # Marathi: "गप्प बस", "थांब जरा", "मी बोलतेय/बोलतोय"
    r"गप्प\s*(बस|रहा|राहा)", r"थांब(ा)?\s*जरा", r"(gapp|gap)\s+(bas|raha)\b",
]
_HOLD_RE = re.compile("|".join(_HOLD), re.I)


def wants_hold(text: str) -> bool:
    """Her words ask Hoola to stay out of a conversation with someone else."""
    t = re.sub(r"\s+", " ", (text or "").lower())
    return bool(t) and bool(_HOLD_RE.search(t))


def _key(w: str) -> str:
    return re.sub(r"[^a-z0-9]", "", phon(w))


def _same(a: str, b: str) -> bool:
    if not a or not b:
        return False
    if a == b:
        return True
    if min(len(a), len(b)) < 4:
        return False
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.8


def call_start(text: str, names: list[str], last_words: int = 0) -> int:
    """Where in `text` she calls Hoola by name (index of the name or the calling word before it), -1 if she doesn't.
    The name must open or close what she said (or follow a calling word like 'hey / arey / suno'), and must not be
    followed by a word that makes it talk ABOUT Hoola ('Santosh ko', 'Hoola ne'). `last_words` > 0 = only the name in
    the last N words counts (a long held turn: the start of a new sentence there)."""
    found = [(m.start(), _key(m.group())) for m in re.finditer(r"[\w'ऀ-ॿ]+", text or "")]
    found = [(p, w) for p, w in found if w]
    keys = [k for k in (_key(n) for n in names) if k]
    if not found or not keys:
        return -1
    words = [w for _, w in found]
    lo = max(0, len(words) - last_words) if last_words else 0
    for i in range(lo, len(words)):
        w = words[i]
        if not any(_same(w, k) for k in keys):
            continue
        nxt = words[i + 1] if i + 1 < len(words) else ""
        if nxt in _ABOUT:
            continue
        prev = words[i - 1] if i > 0 else ""
        if prev in _CALL_BEFORE:
            return found[i - 1][0]
        # the start of what she said, the end of it, or right after a pause-like break (". Santosh")
        before = (text or "")[:found[i][0]].rstrip()
        if i <= 1 or i >= len(words) - 2 or before.endswith((".", "!", "?", ",", "।", "-", "…")):
            return found[i][0] if i > 1 or i == 0 else found[0][0]
    return -1


def called(text: str, names: list[str]) -> bool:
    """She called Hoola by name in these words (see call_start)."""
    return call_start(text, names) >= 0


def names_for(tenant: str, avatar: str) -> list[str]:
    """Her avatar's name, 'Hoola', and the ways the transcript wrote her avatar's name that she corrected before."""
    out = [avatar or "Santosh", "Hoola"]
    try:
        from . import voicestyle
        for f in voicestyle.fixes(tenant):
            if _same(_key(f.get("meant", "")), _key(avatar or "")) and f.get("heard"):
                out.append(f["heard"])
    except Exception:
        pass
    seen, keep = set(), []
    for n in out:
        k = _key(n)
        if k and k not in seen:
            seen.add(k)
            keep.append(n)
    return keep


REASONS = {
    "phone_call": "Aap phone par kisi se baat kar rahi hain",
    "asked": "Aapne kaha ki aap kisi aur se baat kar rahi hain",
    "model": "Lag raha hai aap kisi aur se baat kar rahi hain",
    "button": "Aapne chup karaya",
}


def hold_note(reason: str, name: str) -> str:
    if reason == "phone_call":
        return (f"(HOLD: she is on another phone call now. Everything you hear is NOT for you. Say nothing, call no tools. "
                f"You will be told when her call ends.)")
    return (f"(HOLD: she is talking to someone else now, not to you. Whatever you hear until she says your name '{name}' "
            "is NOT for you: say NOTHING at all, don't comment, don't answer, don't call any tool. Stay completely silent.)")


def release_note(reason: str, by: str, name: str) -> str:
    if reason == "phone_call":
        return ("(HOLD OVER: her other phone call has ended and you can hear her again. Don't start talking on your own; "
                "answer only when she speaks to you.)")
    if by == "name":
        return (f"(HOLD OVER: she called you by name, '{name}'. Answer only what she is asking you NOW. What she said to the "
                "other person while you were on hold was not for you: don't bring it up unless she asks about it.)")
    return ("(HOLD OVER: she wants to talk to you again. Don't start talking on your own; answer when she speaks. "
            "What was said while you were on hold was not for you.)")


DROPPED_NOTE = ("(System: your last reply was NOT played - she was talking to someone else, not to you. Stay silent until "
                "she says your name.)")

PERSONA_BLOCK = """Who is she talking to? (very important)
- Not everything you hear is for you. She may be talking to someone in the room, to someone on another phone, to a family
  member, or a TV / radio may be on. Signs: she calls another person by name or as bhai / didi / mummy / beta / sir; she
  answers a question you never asked; she talks ABOUT you ("ye {name} ..."); two other voices talk to each other; it sounds
  like one side of a phone call.
- Then that talk is NOT for you: say nothing at all (no "theek hai", no comment), call no tool, and call side_talk once.
  It puts you on hold; you come back when she says your name. Never act on things she says to other people ("paise bhej
  dena", "kal aa jaana" to someone else is not a task for you).
- If you are not sure whether it is for you, stay silent rather than guess. A "(HOLD ...)" or "(HOLD OVER ...)" note is
  from the system: always obey it."""

TOOL = {
    "name": "side_talk",
    "description": ("Call this (and say NOTHING) when the talk you hear is clearly not for you: she is talking to another "
                    "person in the room or on another phone, two other people are talking, or a TV / radio is on. It puts "
                    "you on hold: replies are not played and tools are refused until she says your name. Don't call it "
                    "when she is talking to you, even if she mentions other people."),
    "input_schema": {"type": "object", "properties": {
        "why": {"type": "string", "description": "a few words: who she seems to be talking to"}}},
}
