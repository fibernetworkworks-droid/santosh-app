"""In a call: listen to the user's speech as it arrives, and say who it is (owner, Maa, Papa...) once there is enough
of it. Guesses are made per utterance (a pause of 1.2 s starts a new one), first after ~1.6 s of speech, then
again with more speech, on a worker thread so the call never waits."""
from __future__ import annotations

import time
from array import array

from ..config import get_settings
from .permissions import allowed

SPEECH_RMS = 450          # 16-bit RMS of a 40 ms chunk that counts as someone talking (noise is ~100-300)
SPEECH_PROB = 0.5        # v0.53 Silero VAD: below this a loud chunk is not a voice
NEW_UTTERANCE_S = 1.2
KEEP_S = 6.0


def _rms(pcm: bytes) -> float:
    a = array("h")
    a.frombytes(pcm[: len(pcm) // 2 * 2])
    if not a:
        return 0.0
    xs = a[::2]
    return (sum(x * x for x in xs) / len(xs)) ** 0.5


class Listener:
    def __init__(self, people: list[dict], mode: str):
        self.people = people
        self.mode = mode
        self.owner = next((p for p in people if p["relation"] == "self"), None)
        self.buf = bytearray()
        self.speech_s = 0.0
        self.last_speech = 0.0
        self.guessed_at = 0.0     # speech seconds of this utterance at the last guess
        self.busy = False
        self.current: dict | None = None   # the last person recognised for sure
        self.latest_sure = False           # was the guess for the latest utterance sure?
        self.guesses = 0
        self.sure_guesses = 0
        self.vad = None                    # v0.53 Silero VAD: only real speech goes into the fingerprint
        self._vad_tried = False
        self.not_speech = 0

    @property
    def owner_name(self) -> str:
        return self.owner["name"] if self.owner else "malik"

    def add(self, chunk: bytes) -> bool:
        """One mic chunk. True when it is time to guess who is talking."""
        if _rms(chunk) < SPEECH_RMS:
            return False
        if self.vad is None and not self._vad_tried:
            self._vad_tried = True
            from .. import vad
            self.vad = vad.Stream() if get_settings().voiceid_vad and vad.available() else None
        if self.vad is not None:
            p = self.vad.prob(chunk)
            if p is not None and p < SPEECH_PROB:
                self.not_speech += 1        # loud but not a human voice (TV hum, fan, clatter, music)
                return False
        now = time.monotonic()
        if now - self.last_speech > NEW_UTTERANCE_S:
            self.buf.clear()
            self.speech_s = 0.0
            self.guessed_at = 0.0
            self.latest_sure = False
        self.last_speech = now
        self.buf += chunk
        self.speech_s += len(chunk) / 2 / 16000
        extra = len(self.buf) - int(KEEP_S * 16000) * 2
        if extra > 0:
            del self.buf[:extra]
        if self.busy:
            return False
        first = get_settings().voiceid_min_speech_s
        if self.guessed_at == 0 and self.speech_s >= first:
            return True
        return self.guessed_at > 0 and self.speech_s - self.guessed_at >= 2.5 and self.speech_s <= 9

    def pending(self) -> bool:
        """Speech of the latest utterance that has not been looked at yet (enough to try)."""
        return not self.busy and self.speech_s >= 0.8 and self.speech_s > self.guessed_at

    def snapshot(self) -> bytes:
        self.busy = True
        self.guessed_at = max(self.speech_s, 0.01)
        return bytes(self.buf)

    def record(self, res: dict) -> dict | None:
        """The result of a guess. Returns the person when it is someone new (to tell Gemini and the phone)."""
        self.busy = False
        self.guesses += 1
        self.latest_sure = bool(res.get("sure"))
        m = res.get("member")
        if not m:
            return None
        self.sure_guesses += 1
        changed = self.current is None or self.current["id"] != m["id"]
        self.current = m
        return m if changed else None

    def level(self) -> str | None:
        """Whose rights apply right now. None = the owner's (nothing known that says otherwise)."""
        if self.current is not None and (self.latest_sure or self.mode != "strict"):
            return self.current["level"]
        return "family" if self.mode == "strict" else None

    def check(self, tool: str) -> str | None:
        """None if this tool may run for the current voice, else what to tell the user."""
        lv = self.level()
        if allowed(lv, tool):
            return None
        who = self.current
        if who is None or who.get("owner"):
            return (f"Awaaz pakki nahi hui ki {self.owner_name} khud bol rahe hain. Yeh kaam sirf {self.owner_name} ki "
                    "awaaz se hota hai: thoda saaf, phone ke paas se phir boliye, ya app mein khud kar lijiye.")
        return (f"Yeh kaam sirf {self.owner_name} ke liye hai; {who['name']} ki awaaz se yeh nahi ho sakta. "
                f"{who['name']} ko pyaar se batao ki yeh {self.owner_name} se karwayein.")

    def note_for(self, m: dict) -> str:
        """What Gemini is told when the speaker changes (context only; not to be read out)."""
        if m.get("owner"):
            return f"(Awaaz se pehchana: ab {m['name']} khud bol rahe hain. Yeh note padhkar mat sunana.)"
        verb = "rahi" if m.get("gender") == "f" else "rahe"
        return (f"(Awaaz se pehchana: ab {m['name']} ({m['relation_label']}) bol {verb} hain, {self.owner_name} nahi. "
                f"Unse unke naam se, pyaar aur izzat se baat karo. {self.owner_name} ki private baatein (email, paise, "
                f"files, calendar ki details, Hoola Network, yaadein) unhe mat batao; maangein to pyaar se kaho ki yeh "
                f"sirf {self.owner_name} ke liye hai. Yeh note padhkar mat sunana.)")
