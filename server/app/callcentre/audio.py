"""Phone-line audio <-> Gemini Live audio.

Telephony sends 8 kHz G.711 mu-law (Plivo default) or 8 / 16 kHz 16-bit PCM (Plivo L16, Exotel slin); Gemini Live takes
16 kHz PCM16 in and speaks 24 kHz PCM16 out. Python 3.13 has no `audioop`, so the codec and a small stateful polyphase
resampler (windowed-sinc low-pass, keeps its history between chunks so there are no clicks) are written here with numpy.
"""
from __future__ import annotations

from math import gcd

import numpy as np

# ---------------------------------------------------------------- G.711 mu-law (ITU-T G.711, as used by every PSTN gateway)
_BIAS, _CLIP = 0x84, 32635


def _build_decode() -> np.ndarray:
    out = np.zeros(256, dtype=np.int16)
    for i in range(256):
        u = ~i & 0xFF
        sign, exp, man = u & 0x80, (u >> 4) & 0x07, u & 0x0F
        s = ((man << 3) + _BIAS) << exp
        s -= _BIAS
        out[i] = -s if sign else s
    return out


_DECODE = _build_decode()
_EXP = np.array([0, 0, 1, 1, 2, 2, 2, 2] + [3] * 8 + [4] * 16 + [5] * 32 + [6] * 64 + [7] * 128, dtype=np.int32)


def ulaw_to_pcm(data: bytes) -> bytes:
    if not data:
        return b""
    return _DECODE[np.frombuffer(data, dtype=np.uint8)].astype("<i2").tobytes()


def pcm_to_ulaw(pcm: bytes) -> bytes:
    if not pcm:
        return b""
    x = np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype="<i2").astype(np.int32)
    sign = np.where(x < 0, 0x80, 0)
    x = np.minimum(np.abs(x), _CLIP) + _BIAS
    exp = _EXP[(x >> 7) & 0xFF]
    man = (x >> (exp + 3)) & 0x0F
    return (~(sign | (exp << 4) | man) & 0xFF).astype(np.uint8).tobytes()


# ---------------------------------------------------------------- resampling
class Resampler:
    """Rational resampler src -> dst for 16-bit mono PCM, fed in any chunk size."""

    def __init__(self, src: int, dst: int, taps_per_phase: int = 16):
        g = gcd(src, dst)
        self.up, self.down = dst // g, src // g
        self.same = src == dst
        if self.same:
            return
        n = taps_per_phase * self.up * 2 + 1
        cutoff = 0.92 / max(self.up, self.down)            # a bit below Nyquist of the slower side
        t = np.arange(n) - (n - 1) / 2
        h = np.sinc(cutoff * t) * cutoff * np.hamming(n) * self.up
        self.h = h.astype(np.float64)
        self.hist = np.zeros(n - 1, dtype=np.float64)       # previous (upsampled) input, so chunks join smoothly
        self.phase = 0                                        # where the next output sample sits in the upsampled stream

    def __call__(self, pcm: bytes) -> bytes:
        if self.same or not pcm:
            return pcm
        x = np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype="<i2").astype(np.float64)
        up = np.zeros(len(x) * self.up, dtype=np.float64)
        up[:: self.up] = x
        buf = np.concatenate([self.hist, up])
        y = np.convolve(buf, self.h, mode="valid")           # one value per upsampled input sample
        out = y[self.phase:: self.down]
        used = len(y)
        self.phase = (self.phase - used) % self.down
        self.hist = buf[-(len(self.h) - 1):]
        return np.clip(np.round(out), -32768, 32767).astype("<i2").tobytes()


def rms(pcm: bytes) -> float:
    if len(pcm) < 4:
        return 0.0
    x = np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype="<i2").astype(np.float64) / 32768.0
    return float(np.sqrt(np.mean(x * x)))


class Chunker:
    """Some providers want audio in fixed sizes (Exotel: multiples of 320 bytes, >= 100 ms)."""

    def __init__(self, size: int):
        self.size, self.buf = max(2, size), b""

    def add(self, data: bytes) -> list[bytes]:
        self.buf += data
        out = []
        while len(self.buf) >= self.size:
            out.append(self.buf[: self.size])
            self.buf = self.buf[self.size:]
        return out

    def flush(self, multiple: int = 2) -> bytes:
        b, self.buf = self.buf, b""
        if not b:
            return b""
        pad = (-len(b)) % multiple
        return b + b"\x00" * pad


# ---------------------------------------------------------------- v0.999.101 key tones for a phone menu (G3)
_DTMF = {"1": (697, 1209), "2": (697, 1336), "3": (697, 1477), "4": (770, 1209), "5": (770, 1336), "6": (770, 1477),
         "7": (852, 1209), "8": (852, 1336), "9": (852, 1477), "*": (941, 1209), "0": (941, 1336), "#": (941, 1477)}


def dtmf(keys: str, rate: int = 8000, tone_ms: int = 120, gap_ms: int = 100, level: float = 0.35) -> bytes:
    """In-band key tones (the two frequencies of each key, ITU-T Q.23) as 16-bit PCM at the line's rate. The phone
    companies' audio streams cannot send key events, so the tones ride the call audio like a phone keypad's."""
    import numpy as np
    out = []
    for k in str(keys or ""):
        if k not in _DTMF:
            continue
        lo, hi = _DTMF[k]
        t = np.arange(int(rate * tone_ms / 1000)) / rate
        w = (np.sin(2 * np.pi * lo * t) + np.sin(2 * np.pi * hi * t)) * (level / 2)
        out.append((w * 32767).astype("<i2").tobytes())
        out.append(b"\x00\x00" * int(rate * gap_ms / 1000))
    return b"".join(out)
