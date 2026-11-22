"""G3 of docs/SUPPORT_GLOBAL_PLAN.md: what the line hears, in code (no model).

- `classify(text)`: the first words of a call Hoola made, read by meaning: a person, a phone menu, a voicemail
  greeting, a full mailbox, or the network's "number not reachable" message (incl. the Indian operator lines in Hindi /
  Hinglish). A second opinion beside the phone company's own machine check (not every company has one, and none of
  them know the Indian operator messages).
- `MenuWatch`: on a phone menu, notices when the same menu comes back after a key press (a loop) so Hoola stops.
- `keys_ok(digits)`: the only keys Hoola may press on a menu: 1-3 menu keys at a time, never a number that looks like
  an account / card / PIN.
- `ReplyWait`: the wait before Hoola answers learns from each caller's own pauses (a slow speaker gets more time, a
  quick one less) between a floor and a ceiling; remembered per caller for the next call.
- `wait_words(text)`: the caller asked Hoola to hold on ("one minute", "ek minute ruko") - idle checks wait longer.
Idea sources: LiveKit Agents voice/amd, voice/ivr, DynamicEndpointing (Apache-2.0; ideas only, nothing copied).
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

# ---------------------------------------------------------------- what answered a call Hoola made
_PAT = {
    "unreachable": [
        r"number (you|u) (are|have) (calling|called|dialled|dialed)", r"(is|are) (currently )?(switched off|not reachable|out of coverage|"
        r"unreachable|busy on another call|not in service|temporarily out of service)", r"does not exist", r"not a valid number",
        r"please check the number", r"the subscriber", r"cannot be (completed|reached)", r"no longer in service",
        r"aap jis (number|nambar) (par|pe|ko) (call|kol|sampark)", r"(band|switch off|switched off) hai", r"pahunch se bahar",
        r"(uplabdh|upalabdh) nahi", r"vyast hai", r"जिस नंबर", r"बंद है", r"पहुंच से बाहर", r"उपलब्ध नहीं", r"व्यस्त है",
        r"ज्या (नंबर|क्रमांकावर)", r"el número que (usted )?(marc|llam)", r"fuera de servicio", r"o número (que|chamado)",
        r"le numéro (que vous|demandé)", r"nomor yang anda tuju", r"الرقم المطلوب",
    ],
    "mailbox_full": [
        r"mail ?box (is )?full", r"voice ?mail (box )?(is )?full", r"cannot (accept|take) (any )?(new )?messages",
        r"not (been )?set up", r"has not set up", r"buzón (de voz )?(está )?lleno", r"caixa (postal )?(está )?cheia",
    ],
    "voicemail": [
        r"leave (a|your) (message|name)", r"after the (tone|beep)", r"at the (tone|beep)", r"(not available|unavailable) (right now|to take)",
        r"can'?t (come|get) to the phone", r"record your message", r"voice ?mail", r"you have reached", r"you'?ve reached",
        r"please leave", r"beep ke baad", r"sandesh (chhod|chod)", r"message (chhod|chod)", r"संदेश छोड़", r"बीप के बाद",
        r"deje (su|un) mensaje", r"después del tono", r"deixe (sua|uma) mensagem", r"laissez (un|votre) message", r"après le bip",
        r"tinggalkan pesan", r"اترك رسالة",
    ],
    "ivr": [
        r"\bpress\s+(one|two|three|four|five|six|seven|eight|nine|zero|star|hash|pound|\d)\b", r"\bdial\s+(\d|one|two|zero)\b",
        r"for (english|hindi|sales|support|billing|accounts|customer care|service)[, ]+press", r"\bmain menu\b",
        r"your call (is|may be) (important|recorded|monitored)", r"all (our|of our) (agents|executives|representatives|lines) are busy",
        r"please (stay|remain) on the line", r"(dabaye|dabaaye|dabayen|dabaiye)\b", r"\b(ek|do|teen|char|shunya) dabaa?",
        r"दबाएं", r"दबाइए", r"दाबा", r"pulse (el )?(uno|dos|\d)", r"marque (o )?(\d|um|dois)", r"appuyez sur", r"tekan (angka )?\d",
        r"اضغط",
    ],
}
_RX = {k: [re.compile(p, re.I) for p in v] for k, v in _PAT.items()}
_HUMAN = re.compile(r"^\s*(hello|hallo|hi|hey|haan|han|ji|haanji|yes|yeah|speaking|bol(o|iye|a)?|kaun|who is (this|it)|namaste|namaskar|"
                    r"hola|al[oó]|allo|bonjour|halo|ha+lo|हाँ|हां|हैलो|हेलो|नमस्ते|बोलिए|कौन)\b", re.I)

KINDS = ("human", "ivr", "voicemail", "mailbox_full", "unreachable", "unknown")


def classify(text: str) -> dict[str, Any]:
    """The first seconds of words on a call Hoola made -> {kind, sure, why}. sure=False = keep listening."""
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    if not t:
        return {"kind": "unknown", "sure": False, "why": "nothing heard yet"}
    hits = {k: [r.pattern for r in rx if r.search(t)] for k, rx in _RX.items()}
    for k in ("unreachable", "mailbox_full", "voicemail", "ivr"):     # the network message wins over a voicemail greeting
        if hits[k]:
            strong = len(hits[k]) >= 2 or len(t.split()) >= 6 or k in ("unreachable", "mailbox_full")
            return {"kind": k, "sure": strong, "why": hits[k][0]}
    words = len(t.split())
    if _HUMAN.search(t) and words <= 12:
        return {"kind": "human", "sure": True, "why": "a greeting a person says"}
    if words >= 25:          # a long monologue with no question back = a recorded message, not a person
        return {"kind": "voicemail", "sure": False, "why": "a long message with no pause for us"}
    return {"kind": "human" if words >= 2 else "unknown", "sure": words >= 4, "why": "words that are not a recording"}


# ---------------------------------------------------------------- phone menus: which keys, and the loop stop
_NUMWORD = {"zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8",
            "nine": "9", "star": "*", "hash": "#", "pound": "#"}


def keys_ok(digits: Any) -> tuple[bool, str]:
    """Only short menu choices. Never account / card / PIN-like numbers on a menu (those are hers to type, not Hoola's)."""
    d = re.sub(r"\s+", "", str(digits or "").lower())
    d = "".join(_NUMWORD.get(w, w) for w in re.split(r"[,;\-]+", d)) if re.search(r"[a-z]", d) else d
    if not d or not re.fullmatch(r"[0-9*#]+", d):
        return False, "Only the keys 0-9, * and # can be pressed."
    if len(re.sub(r"[*#]", "", d)) > 3:
        return False, ("A menu choice is one to three keys. A longer number (an account, card, PIN or date of birth) is never "
                       "typed by Hoola: say the menu is asking for it and end the call politely.")
    return True, d


def _tokens(text: str) -> Counter:
    return Counter(w for w in re.findall(r"[a-zऀ-ॿ]+", str(text or "").lower()) if len(w) > 2)


def cosine(a: str, b: str) -> float:
    x, y = _tokens(a), _tokens(b)
    if not x or not y:
        return 0.0
    dot = sum(x[k] * y[k] for k in x)
    return dot / (math.sqrt(sum(v * v for v in x.values())) * math.sqrt(sum(v * v for v in y.values())))


class MenuWatch:
    """The menu prompts heard on this call. The same menu again after a key press, twice = a loop: stop."""

    def __init__(self, same: float = 0.8, max_presses: int = 12):
        self.prompts: list[str] = []
        self.presses: list[str] = []
        self.repeats = 0
        self.same, self.max_presses = same, max_presses

    def heard(self, text: str) -> bool:
        """-> True when the menu is going round in a loop."""
        t = str(text or "").strip()
        if len(t.split()) < 4:
            return False
        if self.presses and any(cosine(t, p) >= self.same for p in self.prompts):
            self.repeats += 1
        self.prompts.append(t)
        del self.prompts[:-12]
        return self.repeats >= 2

    def press(self, keys: str) -> tuple[bool, str]:
        if len(self.presses) >= self.max_presses:
            return False, "Too many menu keys on one call: end the call politely and leave it for a person."
        self.presses.append(keys)
        return True, keys


# ---------------------------------------------------------------- the wait before replying learns from the caller
class ReplyWait:
    """Pauses INSIDE the caller's own turns (silence that ended because they spoke again before Hoola did) move the
    wait between FLOOR and CEIL: the 75th percentile of their pauses + a margin. Simple maths, no model."""
    FLOOR, CEIL, START, MARGIN = 600, 1500, 800, 250

    def __init__(self, start_ms: int = 0):
        self.start = int(start_ms) if self.FLOOR <= int(start_ms or 0) <= self.CEIL else self.START
        self.pauses: list[int] = []
        self._voiced = False
        self._quiet_ms = 0.0
        self._had_speech = False

    def frame(self, voiced: bool, ms: float, ai_talking: bool = False) -> None:
        """One frame of caller audio (only while Hoola is not talking)."""
        if ai_talking:
            self._voiced, self._quiet_ms = False, 0.0
            return
        if voiced:
            if self._voiced is False and 150 <= self._quiet_ms <= 3000 and self._had_speech:
                self.pauses.append(int(self._quiet_ms))
                del self.pauses[:-60]
            self._voiced, self._quiet_ms, self._had_speech = True, 0.0, True
        else:
            if self._voiced:
                self._voiced = False
            self._quiet_ms += ms

    def turn_ended(self) -> None:
        """Hoola started answering: the silence before it was the end of a turn, not a pause inside one."""
        self._voiced, self._quiet_ms, self._had_speech = False, 0.0, False

    def learned(self) -> int:
        if len(self.pauses) < 3:
            return self.start
        p = sorted(self.pauses)
        q = p[min(len(p) - 1, int(round(0.75 * (len(p) - 1))))]
        new = max(self.FLOOR, min(self.CEIL, q + self.MARGIN))
        k = min(1.0, len(p) / 10)                     # few pauses = move only part of the way from what we knew
        return int(round(self.start + k * (new - self.start)))


def blend(old_ms: int, new_ms: int) -> int:
    """The caller's remembered wait after another call (old ones count, but the newest call counts most)."""
    if not old_ms:
        return int(new_ms)
    return int(round(0.4 * old_ms + 0.6 * new_ms))


# ---------------------------------------------------------------- the caller asked Hoola to hold on
_WAIT = re.compile(r"\b(one|a|just a|give me a) (minute|moment|second|sec)\b|\bhold on\b|\bhang on\b|\bwait\b|\b(ek|do) (minute|min|second|sec|"
                   r"pal)\b|\bruk(o|iye|na|ie)\b|\bthahr|\bथोड़ा रुक|\bएक (मिनट|सेकंड)|\bरुको|\bरुकिए|\bthamba|\bथांबा|\bun momento\b|"
                   r"\bespere\b|\bun instant\b|\btunggu\b", re.I)


def wait_words(text: str) -> bool:
    return bool(_WAIT.search(str(text or "")))


IDLE_ASK_S = 10        # nobody spoke since Hoola finished: ask once if they are still there
IDLE_END_S = 25        # still nothing after that: a short goodbye and the call ends
HOLD_S = 60            # she asked to hold on: wait this long before asking
FILLER_S = 1.2         # a tool that takes longer than this gets one short spoken "one moment"
