"""v0.266 ASLI SAANS - a real breath SOUND before a cued reply on the OpenAI real voice.

Owner after v0.265: "BREATH AND HMM NOT AVAILABLE -- INSTEAD IT TALKS 'MAIN SAANS LE RAHI HU'". A realtime model asked in
words to breathe SAYS it; it cannot make the sound on request. So the breath is audio we play ourselves, just before his
first word of a reply the delivery cue marked as a breath moment. A breath is voiceless (noise through an open mouth,
no vocal-fold tone), so it does not have to match his voice the way an "ek second" clip would.

Where the sound comes from, best first:
1. Gemini TTS with its OFFICIAL `<breath>` tag (gemini-3.8-flash-tts speech docs list <breath>, <exhales> ...), a few
   takes rendered once and cached in data/voice_acks. Every take must pass `is_breath()`: 0.2-1.4 s long and VOICELESS
   (high zero-crossing rate in its loud frames) - a spoken word ("breath", "saans") has voiced vowels and is refused.
2. `synth()` - a soft inhale built from band-limited noise with a rise-and-fall envelope (always available, so the very
   first call already breathes while the TTS takes are made in the background).
"""
from __future__ import annotations

import contextlib
import logging
import math
import random
import threading
from array import array
from pathlib import Path

log = logging.getLogger("santosh.breath")

RATE = 24000
GEN = "br1"
DIR = Path("data") / "voice_acks"
TAKES = 4
_LOCK = threading.Lock()
_READY: list[bytes] = []
_BUSY = {"on": False, "done": False}
STATS = {"tts_kept": 0, "tts_refused": 0, "synth": 0}


def synth(seed: int = 0, dur: float = 0.42, peak: int = 3600) -> bytes:
    """A soft mouth inhale: noise band-passed to ~350-2600 Hz, a raised-cosine rise (40%) and a longer fall."""
    rnd = random.Random(seed)
    n = int(dur * RATE)
    a_lo = 1 - math.exp(-2 * math.pi * 350 / RATE)
    a_hi = 1 - math.exp(-2 * math.pi * 2600 / RATE)
    lo = hi = 0.0
    raw = []
    for _ in range(n):
        x = rnd.gauss(0, 1)
        hi += a_hi * (x - hi)          # low-pass at 2.6 kHz
        lo += a_lo * (hi - lo)         # ... minus a 350 Hz low-pass = band-pass
        raw.append(hi - lo)
    rise = int(n * 0.4)
    out = array("h")
    m = max(1e-9, max(abs(x) for x in raw))
    for i, x in enumerate(raw):
        env = (0.5 - 0.5 * math.cos(math.pi * i / rise)) if i < rise else \
              (0.5 + 0.5 * math.cos(math.pi * (i - rise) / max(1, n - rise)))
        out.append(int(max(-32767, min(32767, x / m * peak * env))))
    return out.tobytes()


def _frames(pcm: bytes, ms: int = 20):
    a = array("h")
    a.frombytes(pcm[: len(pcm) // 2 * 2])
    step = RATE * ms // 1000
    for i in range(0, len(a) - step + 1, step):
        yield a[i:i + step]


def is_breath(pcm: bytes) -> bool:
    """0.2-1.4 s of sound, and voiceless: >= 70% of its loud 20 ms frames have a high zero-crossing rate."""
    fr = list(_frames(pcm))
    if not fr:
        return False
    rms = [math.sqrt(sum(x * x for x in f) / len(f)) for f in fr]
    top = max(rms)
    if top < 150:
        return False
    loud = [i for i, r in enumerate(rms) if r > top * 0.15]
    span = (loud[-1] - loud[0] + 1) * 0.02
    if not 0.2 <= span <= 1.4:
        return False
    def zcr(f):
        return sum(1 for j in range(1, len(f)) if (f[j - 1] < 0) != (f[j] < 0)) / len(f)
    noisy = sum(1 for i in loud if zcr(fr[i]) > 0.18)
    return noisy / len(loud) >= 0.7


def _trim_to_sound(pcm: bytes) -> bytes:
    fr = list(_frames(pcm, 10))
    if not fr:
        return pcm
    rms = [math.sqrt(sum(x * x for x in f) / len(f)) for f in fr]
    top = max(rms) or 1
    loud = [i for i, r in enumerate(rms) if r > top * 0.08]
    if not loud:
        return b""
    step = RATE // 100 * 2
    return pcm[loud[0] * step:(loud[-1] + 1) * step]


def _file(i: int) -> Path:
    return DIR / f"breath_{i}_{GEN}.pcm"


def _build() -> None:
    """Load cached takes, render the missing ones with Gemini TTS <breath>, keep only real breaths."""
    kept: list[bytes] = []
    try:
        DIR.mkdir(parents=True, exist_ok=True)
        client = None
        for i in range(TAKES):
            f = _file(i)
            if f.exists():
                kept.append(f.read_bytes())
                continue
            try:
                from . import voice
                from .config import get_settings
                if not get_settings().gemini_api_key:
                    break
                if client is None:
                    from google.genai import Client
                    client = Client(api_key=get_settings().gemini_api_key)
                raw = voice._tts_clip("<breath>", ("Puck", "Kore")[i % 2], client)
            except Exception as e:
                log.info("breath take %s not made: %r", i, e)
                continue
            clip = _trim_to_sound(raw)
            if is_breath(clip):
                STATS["tts_kept"] += 1
                with contextlib.suppress(OSError):
                    f.write_bytes(clip)
                kept.append(clip)
            else:
                STATS["tts_refused"] += 1
                log.warning("breath take %s refused: not a voiceless breath (%d bytes)", i, len(clip))
    finally:
        with _LOCK:
            if kept:
                _READY[:] = kept
            _BUSY["on"], _BUSY["done"] = False, True


def clips() -> list[bytes]:
    """The breath takes to play. Until the TTS takes are ready (or if none passed), generated ones."""
    with _LOCK:
        if _READY:
            return list(_READY)
        start = not _BUSY["on"] and not _BUSY["done"]
        if start:
            _BUSY["on"] = True
    if start:
        threading.Thread(target=_build, daemon=True, name="santosh-breath").start()
    STATS["synth"] += 1
    return [synth(seed, dur) for seed, dur in ((1, 0.38), (2, 0.45), (3, 0.52))]


def pick(level: float = 0.0, last: int = -1) -> tuple[bytes, int]:
    """One take (never the same as `last`), quieter than his voice: ~30% of his running loudness when known."""
    cs = clips()
    if not cs:
        return b"", -1
    i = random.randrange(len(cs))
    if i == last and len(cs) > 1:
        i = (i + 1) % len(cs)
    pcm = cs[i]
    if level > 0:
        from .voice import _level
        pcm = _level(pcm, level * 0.3)
    return pcm, i
