"""v0.728 SAB ENGLISH (owner: "MAKE ENTIRE HOOLA IN ENGLISH - MOST IMPORTANT").

One switch for the language Hoola writes and speaks in: `hoola_language` = "en" (default: everything in English) or
"auto" (the old behaviour: answer in the user's own language and script). The two language rules the model reads -
the system prompt's "Reply in the user's language and script..." and the reply rulebook's "Her language, first and
always" - are swapped for an English rule here, so the rest of the prompt text is untouched; tool step labels come
from `agent/labels_en.py`; a voice call is locked to Indian English."""
from __future__ import annotations

import re

from .config import get_settings

EN_RULE = (
    "- Always write in clear, simple English: every reply, every line you write while you work, card text and the "
    "files you make. Do this even when she writes in Hinglish, Hindi, Marathi or any other language - understand "
    "her fully, answer in English. Write in another language only when she explicitly asks for it (\"Hindi mein "
    "likho\", \"reply in Marathi\") or asks you to translate, and only for that piece. Names of people, places, "
    "products and Indian terms (GST, UPI, khata) stay as they are.")

_CHAT_EN = (
    "- Answer in clear, simple English, whatever language she writes in. This holds for the whole reply, for the "
    "lines you write while you work, and for the last sentence. Another language only when she explicitly asks for "
    "it or asks for a translation.")

# the system prompt's language sentence (agent/prompts.py SYSTEM, "How you talk")
_SYS_RULE = re.compile(r"- Reply in the user's language and script\..*?asks you to\.", re.S)
# the reply rulebook's first rule (agent/replystyle.py CHAT)
_CHAT_RULE = re.compile(r"- Answer in the language and script SHE used in her message\.[^\n]*")


def english() -> bool:
    """True when Hoola writes and speaks English (the default)."""
    try:
        return str(getattr(get_settings(), "hoola_language", "en") or "en").lower().startswith("en")
    except Exception:
        return True


def call_english() -> bool:
    """v0.876 EK BHASHA CALL: True when a voice call speaks English. `voice_language` = "hinglish" (default: the call
    speaks Hinglish / her own language even while the rest of Hoola is English) or "en" (calls in English too)."""
    if not english():
        return False
    try:
        return str(getattr(get_settings(), "voice_language", "hinglish") or "hinglish").lower().startswith("en")
    except Exception:
        return False


def on_call() -> bool:
    """True while the running turn was asked by a live call (the call brain or a call's delegated job)."""
    try:
        from .agent import turnchannel
        return turnchannel.current()[0] == turnchannel.CALL
    except Exception:
        return False


def apply(text: str) -> str:
    """The system prompt with its language rules set to English (unchanged when the setting is 'auto', and on a call
    turn when calls speak her language - the voice reads this answer aloud, so it must be in the call's language)."""
    if not english() or not text:
        return text
    if on_call() and not call_english():
        return text
    text = _SYS_RULE.sub(lambda _m: EN_RULE, text, count=1)
    text = _CHAT_RULE.sub(lambda _m: _CHAT_EN, text, count=1)
    return text.replace("Her language, first and always", "Language: English, first and always", 1)


def quick(text: str) -> str:
    return text.replace("in her language", "in English") if english() and not (on_call() and not call_english()) else text


def label(name: str, fallback: str | None = None) -> str:
    """The working-row label of a tool, in English when Hoola is set to English."""
    from .agent.tools import TOOL_LABELS
    if english():
        from .agent.labels_en import LABELS_EN
        if name in LABELS_EN:
            return LABELS_EN[name]
        return fallback if fallback is not None else name.replace("_", " ").capitalize()
    return TOOL_LABELS.get(name, fallback if fallback is not None else name)


def call_lang(lang: str) -> str:
    """The language a voice call is locked to: Indian English when Hoola is set to English."""
    if call_english():
        return "en-IN"
    # v0.876 the console always asks for en-IN and the phone sends its app language: on a Hinglish call an English
    # ask means the app's language, not hers - the call speaks Hinglish (hi-IN = Hindi grammar + everyday English)
    return "hi-IN" if (not lang or str(lang).lower().startswith("en")) else lang
