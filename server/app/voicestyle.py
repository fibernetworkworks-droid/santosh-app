"""v0.119 Hoola sunke seekhta hai: how SHE speaks, kept as numbers and words only (never audio).

Research behind it (report "Hoola voice listening and native speech", 22 Oct 2026): copying a user's accent or voice is
neither possible in Gemini Live (no rate / pitch control, prebuilt voices only) nor wise (people find mimicry creepy; the
evidence for "entrainment" is about matching pace, energy and turn length within a band). What helps is:
  1. her PAUSES: someone who stops to think mid-sentence gets cut off by a 700 ms end-of-turn; the call's
     silence_duration_ms is set from her own mid-sentence pauses (p90 + margin, 500-1000 ms) and from her "cut off" ratings,
  2. a 1-3 line STYLE HINT (pace, turn length, tone spread, aap / tum, her yes-words and everyday particles),
  3. her WORDS (names, contacts, products) as vocabulary for the transcript and the model,
  4. CORRECTIONS "heard X -> she meant Y", picked from her own corrections ("Ramesh nahi, Rameshwar"), used only when
     they came twice or she added / confirmed them.
Only the owner's own speech teaches it (Awaaz Pehchaan says owner, or nobody known is talking) and she can switch learning
off or forget everything (Profile > "<name> ne kya seekha"). DPDP: numbers and words only, deletable, purpose = calls.
"""
from __future__ import annotations

import difflib
import json
import math
import re
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, delete, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, now, session

MAX_SAMPLES = 300          # rolling per-turn samples kept per owner
MAX_FIXES = 60
MAX_WORDS = 100
READY_TURNS = 15           # turns before the style hint is used
READY_PAUSES = 20          # mid-sentence pauses before her own end-of-turn wait is used
SILENCE_MIN, SILENCE_MAX = 420, 1000   # v0.181 floor 500 -> 420: quick people get a quick reply; her own pauses still raise it


class SpeechProfile(Base):
    __tablename__ = "voice_speech_profiles"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    learn: Mapped[bool] = mapped_column(Boolean, default=True)
    calls: Mapped[int] = mapped_column(Integer, default=0)
    turns: Mapped[int] = mapped_column(Integer, default=0)
    wps: Mapped[str] = mapped_column(Text, default="[]")          # words per second of speech, per turn
    pauses: Mapped[str] = mapped_column(Text, default="[]")       # mid-sentence pauses (ms)
    turn_words: Mapped[str] = mapped_column(Text, default="[]")
    pitch: Mapped[str] = mapped_column(Text, default="[]")        # median Hz per turn
    spread: Mapped[str] = mapped_column(Text, default="[]")       # pitch range per turn (semitones, p10..p90)
    level: Mapped[str] = mapped_column(Text, default="[]")        # loudness per turn (dBFS, phone mic: relative only)
    counts: Mapped[str] = mapped_column(Text, default="{}")       # {"formal": {aap: n}, "assent": {...}, "particles": {...}}
    cut_offs: Mapped[int] = mapped_column(Integer, default=0)     # calls she rated "beech mein kaat diya"
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class VoiceFix(Base):
    __tablename__ = "voice_fixes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    heard: Mapped[str] = mapped_column(String(80))
    meant: Mapped[str] = mapped_column(String(80))
    count: Mapped[int] = mapped_column(Integer, default=1)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(10), default="call")   # call | her
    last_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class VoiceWord(Base):
    __tablename__ = "voice_words"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    term: Mapped[str] = mapped_column(String(60))
    source: Mapped[str] = mapped_column(String(10), default="her")    # her | fix
    uses: Mapped[int] = mapped_column(Integer, default=0)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class StyleError(Exception):
    pass


_LOCK = threading.Lock()


def _j(s: str, d):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(d)) else d
    except Exception:
        return d


def _pct(xs: list[float], q: float) -> float | None:
    if not xs:
        return None
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))]


# ------------------------------------------------------------------ the audio side: one turn of her mic at a time
def _pitch(x) -> float | None:
    """Fundamental frequency of one voiced chunk (autocorrelation, 75-400 Hz), None when not clearly voiced."""
    import numpy as np
    if len(x) < 480:
        return None
    x = x - x.mean()
    n = len(x)
    f = np.fft.rfft(x, 2 * n)
    r = np.fft.irfft(f * np.conj(f))[:n]
    if r[0] <= 0:
        return None
    lo, hi = 16000 // 400, min(n - 1, 16000 // 75)
    if hi <= lo:
        return None
    seg = r[lo:hi]
    k = int(np.argmax(seg)) + lo
    if r[k] / r[0] < 0.45:
        return None
    return 16000.0 / k


class TurnMeter:
    """Fed every mic chunk of the call (16 kHz PCM16). Between two of her turns it measures: speaking time, the pauses
    INSIDE her turn (150 ms - 2.5 s gaps between voiced stretches), loudness and pitch of voiced chunks."""
    LOUD_RMS = 0.02

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.voiced_ms = 0.0
        self.pause_ms = 0.0
        self.pauses: list[int] = []
        self._gap = 0.0
        self._started = False
        self._levels: list[float] = []
        self._pitches: list[float] = []
        self._n = 0

    def add(self, pcm: bytes) -> None:
        try:
            import numpy as np
        except Exception:
            return
        n = len(pcm) // 2 * 2
        if n < 64:
            return
        x = np.frombuffer(pcm[:n], dtype=np.int16).astype(np.float32) / 32768.0
        ms = len(x) / 16.0
        rms = float(math.sqrt(float((x * x).mean())))
        if rms >= self.LOUD_RMS:
            if self._started and 150 <= self._gap <= 2500:
                self.pauses.append(int(self._gap))
                self.pause_ms += self._gap
            self._started = True
            self._gap = 0.0
            self.voiced_ms += ms
            self._levels.append(20 * math.log10(max(rms, 1e-6)))
            self._n += 1
            if self._n % 2 == 0 and len(self._pitches) < 400:
                p = _pitch(x)
                if p:
                    self._pitches.append(p)
        elif self._started:
            self._gap += ms

    def _snapshot(self) -> dict[str, Any]:
        return {"voiced_s": self.voiced_ms / 1000, "speech_s": (self.voiced_ms + self.pause_ms) / 1000,
                "pauses": list(self.pauses), "level": _pct(self._levels, .5),
                "pitch": _pct(self._pitches, .5) if len(self._pitches) >= 3 else None,
                "spread": (12 * math.log2(_pct(self._pitches, .9) / _pct(self._pitches, .1))
                           if len(self._pitches) >= 6 else None)}

    def peek(self) -> dict[str, Any]:
        """v0.208 the same numbers take() returns, read MID-TURN without resetting: the feeling engine listens to
        her prosody while she is still speaking (the turn is not over, take() must keep its data for the
        end-of-turn learning). Cheap - a few list medians on the transcription path."""
        return self._snapshot()

    def take(self) -> dict[str, Any]:
        out = self._snapshot()
        self.reset()
        return out


# ------------------------------------------------------------------ the words side
FORMAL = {"aap": "aap", "aapko": "aap", "aapka": "aap", "aapki": "aap", "aapne": "aap", "ji": "aap", "tumhi": "aap",
          "आप": "aap", "आपको": "aap", "जी": "aap", "तुम्ही": "aap",
          "tum": "tum", "tumko": "tum", "tumhara": "tum", "tumhe": "tum", "tumne": "tum", "तुम": "tum", "तुम्हें": "tum",
          "tu": "tu", "tera": "tu", "teri": "tu", "tujhe": "tu", "tula": "tu", "tujha": "tu", "तू": "tu", "तेरा": "tu", "तुला": "tu"}
ASSENT = ["haan ji", "theek hai", "thik hai", "ho na", "haan", "haa", "han", "ho", "hoy", "ji", "achha", "accha", "acha", "ok",
          "okay", "bilkul", "chalega", "barobar", "chal", "sahi", "हाँ", "हां", "हो", "ठीक है", "बरं", "बरोबर", "चालेल", "अच्छा", "जी"]
PARTICLES = ["na", "re", "yaar", "bhai", "bhau", "ga", "bas", "arre", "accha", "matlab", "bolo", "dekho", "bro", "ना", "रे",
             "यार", "भाऊ", "ग", "अरे", "बस", "मतलब"]
_WORD = re.compile(r"[\wऀ-෿']+", re.U)


def words_of(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text or "")]


def text_counts(text: str) -> dict[str, dict[str, int]]:
    ws = words_of(text)
    out: dict[str, dict[str, int]] = {"formal": {}, "assent": {}, "particles": {}}
    for w in ws:
        k = FORMAL.get(w)
        if k:
            out["formal"][k] = out["formal"].get(k, 0) + 1
    low = " ".join(ws)
    if 0 < len(ws) <= 4:      # a short answer: which word does she use for yes?
        for a in ASSENT:
            if re.match(rf"^{re.escape(a)}\b", low):
                out["assent"][a] = 1
                break
    seen = set(ws)
    for p in PARTICLES:
        if p in seen:
            out["particles"][p] = 1
    return out


# ------------------------------------------------------------------ per call: collected in memory, saved once at hang-up
class CallStyle:
    def __init__(self) -> None:
        self.turns: list[dict[str, Any]] = []
        self.fixes: list[tuple[str, str]] = []

    def turn(self, measured: dict[str, Any], text: str) -> None:
        n = len(words_of(text))
        if not n:
            return
        rec = {"words": n, "counts": text_counts(text), "pauses": measured.get("pauses") or [],
               "level": measured.get("level"), "pitch": measured.get("pitch"), "spread": measured.get("spread")}
        sp = measured.get("speech_s") or 0
        if n >= 4 and sp >= 1.0:
            rec["wps"] = round(n / sp, 2)
        self.turns.append(rec)
        del self.turns[:-200]


def _merge(counts: dict, add: dict) -> None:
    for k, d in add.items():
        box = counts.setdefault(k, {})
        for w, c in d.items():
            box[w] = box.get(w, 0) + c


def save_call(tenant: str, cs: CallStyle) -> dict[str, Any]:
    """After a call (owner's speech only): add this call's turns to her profile, count her corrections."""
    if not cs.turns and not cs.fixes:
        return {"saved": False}
    with _LOCK, session() as s:
        p = s.get(SpeechProfile, tenant)
        if p is None:
            p = SpeechProfile(tenant_id=tenant)
            s.add(p)
        if p.learn is False:
            return {"saved": False, "why": "learning off"}
        if cs.turns:
            lists = {k: _j(getattr(p, k), []) for k in ("wps", "pauses", "turn_words", "pitch", "spread", "level")}
            counts = _j(p.counts, {})
            for t in cs.turns:
                lists["turn_words"].append(t["words"])
                lists["pauses"].extend(t["pauses"])
                for k in ("wps", "pitch", "spread", "level"):
                    if t.get(k) is not None:
                        lists[k].append(round(float(t[k]), 2))
                _merge(counts, t["counts"])
            for k, v in lists.items():
                setattr(p, k, json.dumps(v[-MAX_SAMPLES:]))
            p.counts = json.dumps(counts)
            p.calls = (p.calls or 0) + 1
            p.turns = (p.turns or 0) + len(cs.turns)
            p.updated_at = now()
        s.commit()
    learned = [note_fix(tenant, h, m) for h, m in cs.fixes]
    return {"saved": True, "turns": len(cs.turns), "fixes": learned}


def note_cut_off(tenant: str) -> None:
    """She rated a call 'beech mein kaat diya': wait a little longer at the end of her turn next time."""
    with _LOCK, session() as s:
        p = s.get(SpeechProfile, tenant)
        if p is None:
            p = SpeechProfile(tenant_id=tenant)
            s.add(p)
        if p.learn is False:
            return
        p.cut_offs = min(3, (p.cut_offs or 0) + 1)
        s.commit()


# ------------------------------------------------------------------ corrections: "heard X -> she meant Y"
NUMBER_PAIRS = {("thirteen", "thirty"), ("fourteen", "forty"), ("fifteen", "fifty"), ("sixteen", "sixty"),
                ("seventeen", "seventy"), ("eighteen", "eighty"), ("nineteen", "ninety"), ("terah", "tees"),
                ("pandrah", "pachaas"), ("satrah", "sattar"), ("atharah", "assi"), ("unnis", "nabbe"),
                ("chaudah", "chalis"), ("solah", "saath")}
STOP = {"nahi", "nahin", "no", "na", "galat", "maine", "bola", "kaha", "tha", "thi", "hai", "ka", "ki", "ke", "ko", "se", "aur",
        "the", "is", "not", "i", "said", "नहीं", "नाही", "मैंने", "कहा", "था", "बोला", "मी", "म्हटलं"}
_NOT = r"(?:nahi|nahin|nahi\s+re|not|नहीं|नाही)"
FIX_PATTERNS = [
    # "Rames nahi, Ramesh" / "रमेश नहीं, रमेश्वर"
    re.compile(rf"^(?:arre\s+|nahi[,\s]+|no[,\s]+)?(?P<heard>[\wऀ-෿']+(?:\s+[\wऀ-෿']+)?)\s+{_NOT}[,.\s]+"
               rf"(?P<meant>[\wऀ-෿']+(?:\s+[\wऀ-෿']+)?)", re.I | re.U),
    # "nahi, maine Ramesh bola" / "maine Ramesh kaha tha"
    re.compile(r"(?:maine|mai|main|मैंने|मी)\s+(?P<meant>[\wऀ-෿']+(?:\s+[\wऀ-෿']+)?)\s+"
               r"(?:bola|kaha|bol\s+rahi|bol\s+raha|कहा|बोला|म्हटलं|सांगितलं)", re.I | re.U),
    # "Ramesh, Rames nahi"
    re.compile(rf"^(?P<meant>[\wऀ-෿']+)[,\s]+(?P<heard>[\wऀ-෿']+)\s+{_NOT}\b", re.I | re.U),
]


def sounds_alike(a: str, b: str) -> bool:
    a, b = a.lower().strip(), b.lower().strip()
    if not a or not b or a == b:
        return False
    if (a, b) in NUMBER_PAIRS or (b, a) in NUMBER_PAIRS:
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.45


def find_fix(user: str, prev_reply: str) -> tuple[str, str] | None:
    """Her correction of what Hoola just said -> (heard, meant), only when Hoola really said the 'heard' words and the two
    sound alike (a change of mind like 'chai nahi, coffee' is not a mis-hearing)."""
    text = (user or "").strip()
    if not text or not prev_reply or len(words_of(text)) > 14:
        return None
    reply_words = words_of(prev_reply)
    for i, rx in enumerate(FIX_PATTERNS):
        m = rx.search(text)
        if not m:
            continue
        meant = " ".join(w for w in _WORD.findall(m.group("meant")) if w.lower() not in STOP)   # her spelling kept
        if not meant or len(meant) < 2:
            continue
        heard = " ".join(w for w in words_of(m.groupdict().get("heard") or "") if w not in STOP)
        if not heard:   # "maine X bola": the closest-sounding word Hoola used
            best, score = "", 0.0
            for w in reply_words:
                if w in STOP or w == meant.lower():
                    continue
                r = difflib.SequenceMatcher(None, w, meant.lower()).ratio()
                if r > score:
                    best, score = w, r
            heard = best if score >= 0.5 else ""
        if not heard or heard == meant.lower() or not sounds_alike(heard, meant):
            continue
        if not all(w in reply_words for w in heard.split()):
            continue
        return heard[:80], meant[:80]
    return None


def note_fix(tenant: str, heard: str, meant: str, by_her: bool = False) -> dict[str, Any]:
    heard, meant = heard.strip().lower()[:80], meant.strip()[:80]
    if not heard or not meant or heard == meant.lower():
        raise StyleError("heard aur meant dono chahiye, alag alag")
    with _LOCK, session() as s:
        row = s.scalars(select(VoiceFix).where(VoiceFix.tenant_id == tenant, VoiceFix.heard == heard)).first()
        if row is not None and row.meant.lower() != meant.lower():
            if by_her:
                row.meant, row.count = meant, 1
            else:
                row.count = max(0, row.count - 1)   # mixed signals: weaker, not switched
                s.commit()
                return {"id": row.id, "heard": row.heard, "meant": row.meant, "confirmed": row.confirmed}
        if row is None:
            row = VoiceFix(tenant_id=tenant, heard=heard, meant=meant, count=0, source="her" if by_her else "call")
            s.add(row)
        row.count += 1
        row.last_at = now()
        if by_her:
            row.confirmed, row.source = True, "her"
        elif row.count >= 2:
            row.confirmed = True
        s.commit()
        out = {"id": row.id, "heard": row.heard, "meant": row.meant, "confirmed": row.confirmed}
        olds = s.scalars(select(VoiceFix).where(VoiceFix.tenant_id == tenant)
                         .order_by(VoiceFix.confirmed.desc(), VoiceFix.last_at.desc())).all()
        for o in olds[MAX_FIXES:]:
            s.delete(o)
        s.commit()
    if out["confirmed"] and (by_her or re.match(r"[A-Zऀ-෿]", meant)):   # a name: also a vocabulary word
        try:
            add_word(tenant, meant, "fix")
        except StyleError:
            pass
    return out


def confirm_fix(tenant: str, fix_id: int) -> dict[str, Any]:
    with session() as s:
        row = s.get(VoiceFix, fix_id)
        if row is None or row.tenant_id != tenant:
            raise StyleError("Yeh sudhaar nahi mila")
        row.confirmed, row.source = True, "her"
        s.commit()
        return {"id": row.id, "heard": row.heard, "meant": row.meant, "confirmed": True}


def remove_fix(tenant: str, fix_id: int) -> bool:
    with session() as s:
        row = s.get(VoiceFix, fix_id)
        if row is None or row.tenant_id != tenant:
            return False
        s.delete(row)
        s.commit()
        return True


def fixes(tenant: str, confirmed_only: bool = False) -> list[dict[str, Any]]:
    with session() as s:
        q = select(VoiceFix).where(VoiceFix.tenant_id == tenant)
        if confirmed_only:
            q = q.where(VoiceFix.confirmed.is_(True))
        rows = s.scalars(q.order_by(VoiceFix.confirmed.desc(), VoiceFix.count.desc(), VoiceFix.last_at.desc())).all()
        return [{"id": r.id, "heard": r.heard, "meant": r.meant, "count": r.count, "confirmed": bool(r.confirmed),
                 "source": r.source} for r in rows]


# ------------------------------------------------------------------ her words (names, contacts, products)
_SECRETISH = re.compile(r"\d{4,}|@|otp|pin|password|cvv", re.I)


def add_word(tenant: str, term: str, source: str = "her") -> dict[str, Any]:
    term = re.sub(r"\s+", " ", (term or "").strip())[:60]
    if len(term) < 2 or _SECRETISH.search(term):
        raise StyleError("Sirf naam / shabd (2-60 akshar, number ya password nahi)")
    with _LOCK, session() as s:
        rows = s.scalars(select(VoiceWord).where(VoiceWord.tenant_id == tenant)).all()
        for r in rows:
            if r.term.lower() == term.lower():
                if source == "her" and r.source != "her":
                    r.source = "her"
                    s.commit()
                return {"id": r.id, "term": r.term, "source": r.source}
        if len(rows) >= MAX_WORDS:
            drop = [r for r in rows if r.source != "her"] or rows
            s.delete(min(drop, key=lambda r: (r.uses, r.added_at)))
        w = VoiceWord(tenant_id=tenant, term=term, source=source)
        s.add(w)
        s.commit()
        return {"id": w.id, "term": w.term, "source": w.source}


def remove_word(tenant: str, word_id: int) -> bool:
    with session() as s:
        row = s.get(VoiceWord, word_id)
        if row is None or row.tenant_id != tenant:
            return False
        s.delete(row)
        s.commit()
        return True


def own_words(tenant: str) -> list[dict[str, Any]]:
    with session() as s:
        rows = s.scalars(select(VoiceWord).where(VoiceWord.tenant_id == tenant).order_by(VoiceWord.added_at.desc())).all()
        return [{"id": r.id, "term": r.term, "source": r.source} for r in rows]


def vocab(tenant: str, limit: int = MAX_WORDS) -> list[str]:
    """Words the call should hear right: hers first, then corrected words, the avatar's name, her contacts' names."""
    out: list[str] = []
    seen: set[str] = set()

    def put(t: str) -> None:
        t = re.sub(r"\s+", " ", (t or "").strip())[:60]
        if len(t) >= 2 and t.lower() not in seen and not _SECRETISH.search(t):
            seen.add(t.lower())
            out.append(t)

    for w in own_words(tenant):
        put(w["term"])
    for f in fixes(tenant, True):
        put(f["meant"])
    try:
        from .avatar import service as av
        put(av.get(tenant).get("name") or "")
    except Exception:
        pass
    try:
        from .db import MailContact
        with session() as s:
            for c in s.scalars(select(MailContact).where(MailContact.tenant_id == tenant)
                               .order_by(MailContact.score.desc()).limit(25)).all():
                put((c.name or "").split(" <")[0])
    except Exception:
        pass
    try:
        from .bazar.db import Contact
        with session() as s:
            for c in s.scalars(select(Contact).where(Contact.user_id == tenant).limit(40)).all():
                put(c.name)
    except Exception:
        pass
    return out[:limit]


# ------------------------------------------------------------------ what was learned -> how the next call behaves
def _profile(tenant: str) -> SpeechProfile | None:
    with session() as s:
        p = s.get(SpeechProfile, tenant)
        if p is not None:
            s.expunge(p)
        return p


def _top(d: dict[str, int], n: int, min_share: float, total: int) -> list[str]:
    items = sorted(d.items(), key=lambda kv: -kv[1])
    return [w for w, c in items if total and c / total >= min_share][:n]


def profile_view(tenant: str, base_silence: int | None = None) -> dict[str, Any]:
    from .config import get_settings
    st = get_settings()
    base = base_silence if base_silence is not None else st.voice_silence_ms
    p = _profile(tenant)
    if p is None:
        return {"learn": True, "calls": 0, "turns": 0, "ready": False, "silence_ms": base, "silence_why": "default",
                "hint": [], "facts": {}}
    wps, pauses = _j(p.wps, []), _j(p.pauses, [])
    tw, pitch, spread, level = _j(p.turn_words, []), _j(p.pitch, []), _j(p.spread, []), _j(p.level, [])
    counts = _j(p.counts, {})
    facts: dict[str, Any] = {
        "pace_wps": _pct(wps, .5), "pause_p50_ms": _pct(pauses, .5), "pause_p90_ms": _pct(pauses, .9),
        "pauses_heard": len(pauses), "turn_words_median": _pct(tw, .5), "pitch_hz": _pct(pitch, .5),
        "pitch_low_hz": _pct(pitch, .1), "pitch_high_hz": _pct(pitch, .9), "tone_spread_st": _pct(spread, .5),
        "level_db": _pct(level, .5), "cut_offs": p.cut_offs or 0}
    # her own end-of-turn wait: her long mid-sentence pauses must not end her turn
    silence, why = base, "default"
    if len(pauses) >= READY_PAUSES:
        silence = max(SILENCE_MIN, int(round((facts["pause_p90_ms"] + 150) / 10.0) * 10))
        why = "pauses"
    if p.cut_offs:
        silence += 100 * p.cut_offs
        why = why + "+cut_offs" if why != "default" else "cut_offs"
    silence = max(SILENCE_MIN, min(SILENCE_MAX, silence))
    ready = (p.turns or 0) >= READY_TURNS
    hint: list[str] = []
    if ready:
        pace, med = facts["pace_wps"], facts["turn_words_median"]
        bits = []
        if pace is not None and pace >= 3.3:
            bits.append(f"She speaks fast (about {pace:.1f} words a second): keep up, answer short and quick, no slow fillers.")
        elif pace is not None and pace <= 2.0:
            bits.append(f"She speaks slowly and thinks while talking (about {pace:.1f} words a second): speak calmly, don't "
                        "rush her, never jump in during her pauses.")
        if med is not None and med <= 4:
            bits.append("She talks in short bits: keep your replies to one short sentence.")
        elif med is not None and med >= 15:
            bits.append("She explains at length: let her finish, then say the main point back in one line before acting.")
        if bits:
            hint.append(" ".join(bits[:2]))
        sp = facts["tone_spread_st"]
        if sp is not None and sp >= 7:
            hint.append("Her voice is lively and expressive: react with warmth and energy (not louder, not filmy).")
        elif sp is not None and sp <= 3.5:
            hint.append("She talks in a calm, even tone: keep yours calm and steady, no over-excitement.")
        fm = counts.get("formal") or {}
        tot = sum(fm.values())
        words = []
        if tot >= 8:
            casual = (fm.get("tum", 0) + fm.get("tu", 0)) / tot
            if casual >= 0.6:
                words.append("She talks to you casually (tum / tu): you still say aap, but keep it relaxed and friendly, "
                             "not formal.")
            elif fm.get("aap", 0) / tot >= 0.8:
                words.append("She is polite and formal (aap / ji): match it.")
        nt = p.turns or 0
        yes = _top(counts.get("assent") or {}, 3, 0.03, nt)
        if yes:
            words.append("Her yes-words: " + ", ".join(f"'{w}'" for w in yes) + " (they mean haan).")
        parts = _top(counts.get("particles") or {}, 3, 0.10, nt)
        if parts:
            words.append("Her everyday words: " + ", ".join(f"'{w}'" for w in parts) + " - use them naturally, sparingly.")
        if words:
            hint.append(" ".join(words))
    return {"learn": p.learn is not False, "calls": p.calls or 0, "turns": p.turns or 0, "ready": ready,
            "silence_ms": silence, "silence_why": why, "hint": hint[:3], "facts": facts,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None}


def for_call(tenant: str) -> dict[str, Any]:
    """Everything one call needs, read once at the start: end-of-turn wait, style block for the prompt, vocabulary."""
    from .config import get_settings
    st = get_settings()
    out: dict[str, Any] = {"silence_ms": None, "block": "", "vocab": [], "fixes": 0, "styled": False}
    if not st.voice_adapt:
        return out
    try:
        pv = profile_view(tenant)
    except Exception:
        pv = {"learn": True, "silence_ms": None, "silence_why": "default", "hint": []}
    if pv.get("learn") is False:
        return out
    if pv.get("silence_why") != "default":
        out["silence_ms"] = pv["silence_ms"]
    lines: list[str] = []
    if pv.get("hint"):
        lines.append("HOW SHE SPEAKS (learned from her own calls; match her within reason, never copy her accent or voice):")
        lines += [f"- {h}" for h in pv["hint"]]
    fx = fixes(tenant, True)[:15]
    if fx:
        lines.append("WORDS YOU MISHEARD BEFORE (the transcript may show the left one; she means the right one):")
        lines += [f"- '{f['heard']}' -> {f['meant']}" for f in fx]
    vc = vocab(tenant)
    if vc:
        lines.append("HER NAMES AND WORDS (hear and say them exactly like this): " + ", ".join(vc[:60]))
    out.update(block=("\n\n" + "\n".join(lines) + "\n") if lines else "", vocab=vc, fixes=len(fx),
               styled=bool(pv.get("hint")),
               facts=(pv.get("facts") or {}))   # v0.208 her prosody baseline (pitch/spread/level medians) for the feeling engine
    return out


def set_learn(tenant: str, on: bool) -> dict[str, Any]:
    with session() as s:
        p = s.get(SpeechProfile, tenant)
        if p is None:
            p = SpeechProfile(tenant_id=tenant)
            s.add(p)
        p.learn = bool(on)
        s.commit()
    return {"learn": bool(on)}


def forget(tenant: str, part: str = "all") -> dict[str, Any]:
    part = part or "all"
    if part not in ("all", "profile", "fixes", "words", "language"):
        raise StyleError("part = all | profile | fixes | words | language")
    with session() as s:
        if part in ("all", "profile"):
            p = s.get(SpeechProfile, tenant)
            if p is not None:
                learn = p.learn
                s.delete(p)
                s.flush()
                if learn is False:
                    s.add(SpeechProfile(tenant_id=tenant, learn=False))
        if part in ("all", "fixes"):
            s.execute(delete(VoiceFix).where(VoiceFix.tenant_id == tenant))
        if part in ("all", "words"):
            s.execute(delete(VoiceWord).where(VoiceWord.tenant_id == tenant))
        s.commit()
    if part in ("all", "language"):
        from . import voicelang
        voicelang.forget(tenant)
    return {"forgot": part}


def view(tenant: str) -> dict[str, Any]:
    """Profile > '<name> ne kya seekha': the language, how she speaks, what was misheard, her words."""
    from . import voicelang
    lang = voicelang.learned(tenant)
    pv = profile_view(tenant)
    return {"language": ({"code": lang.get("base"), "name": voicelang.LANGS.get(lang.get("base"), {}).get("name", ""),
                          "mix": lang.get("mix")} if lang else None),
            "profile": pv, "fixes": fixes(tenant), "words": own_words(tenant), "vocab": vocab(tenant),
            "privacy": "Sirf numbers aur shabd rakhe jaate hain, aapki awaaz ki recording kabhi nahi. Sirf aapki apni awaaz "
                       "se seekhta hai (Awaaz Pehchaan). Jab chahein band karein ya mita dein."}


def say(tenant: str) -> str:
    v = view(tenant)
    pv, bits = v["profile"], []
    if v["language"]:
        bits.append(f"bhasha {v['language']['name']}")
    if pv.get("silence_why") != "default":
        bits.append(f"aapke rukne ka samay {pv['silence_ms']} ms tak sunta hoon")
    if pv.get("hint"):
        bits.append("bolne ka tareeka: " + " ".join(pv["hint"]))
    if v["fixes"]:
        bits.append(f"{sum(1 for f in v['fixes'] if f['confirmed'])} galat suni baatein sudhaari")
    if v["words"]:
        bits.append(f"{len(v['words'])} aapke shabd")
    return ("Abhi tak: " + "; ".join(bits)) if bits else "Abhi kuch khaas nahi seekha: 2-3 call ke baad dikhega."
