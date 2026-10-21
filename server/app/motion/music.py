"""Background music made on the server from plain maths (no samples, no licences needed).

moods:
  upbeat  - 112 bpm pop: I-V-vi-IV pad, plucked arpeggio, kick / clap / hats
  calm    - 80 bpm: soft maj7 pads and sparse bell plucks
  festive - 124 bpm Indian feel: tanpura drone (Sa-Pa), tabla-like dha / tin pattern, pentatonic (Sa Re Ga Pa Dha) plucks
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 44100
MOODS = ("upbeat", "calm", "festive", "none")


def _note(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def _env(n: int, a: float, d: float) -> np.ndarray:
    t = np.arange(n) / SR
    return np.minimum(1.0, t / max(a, 1e-4)) * np.exp(-t / d)


def _pluck(f: float, dur: float, decay: float = .35, bright: int = 4) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * f * k * t) / k ** 1.4 for k in range(1, bright + 1))
    return x * _env(n, .004, decay)


def _pad(freqs: list[float], dur: float) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for f in freqs:
        for det in (-0.6, 0.6):                       # two slightly detuned voices: wide and warm
            ff = f * 2 ** (det / 1200)
            x += np.sin(2 * np.pi * ff * t) + .3 * np.sin(2 * np.pi * 2 * ff * t) + .12 * np.sin(2 * np.pi * 3 * ff * t)
    att = np.minimum(1.0, t / .35) * np.minimum(1.0, (dur - t) / .35)
    return x * att / (len(freqs) * 2)


def _kick(dur: float = .35) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 50 + 90 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def _noise_hit(dur: float, decay: float, rng: np.random.Generator, hp: bool = True) -> np.ndarray:
    n = int(dur * SR)
    x = rng.standard_normal(n)
    if hp:
        x = np.diff(x, prepend=0)
    return x * np.exp(-np.arange(n) / SR / decay)


def _tabla(kind: str, rng: np.random.Generator) -> np.ndarray:
    n = int(.4 * SR)
    t = np.arange(n) / SR
    if kind == "dha":      # bass bayan + treble
        f = 95 + 60 * np.exp(-t * 18)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6) + .5 * np.sin(2 * np.pi * 330 * t) * np.exp(-t * 14)
    else:                  # tin / na: ringing treble
        x = np.sin(2 * np.pi * 360 * t) * np.exp(-t * 16) + .35 * np.sin(2 * np.pi * 720 * t) * np.exp(-t * 22)
    return x + .08 * _noise_hit(.4, .02, rng)


def _add(buf: np.ndarray, x: np.ndarray, at: float, gain: float) -> None:
    i = int(at * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(x))
    buf[i:j] += x[: j - i] * gain


def make(mood: str, seconds: float, seed: int = 7) -> np.ndarray:
    """Mono float array in [-1, 1]."""
    rng = np.random.default_rng(seed)
    n = int((seconds + 1) * SR)
    buf = np.zeros(n)
    if mood == "calm":
        bpm, prog = 80, [[65, 69, 72, 76], [64, 67, 71, 74], [62, 65, 69, 72], [60, 64, 67, 71]]   # Fmaj7 Em7 Dm7 Cmaj7
    elif mood == "festive":
        bpm, prog = 124, None
    else:
        bpm, prog = 112, [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]                  # C G Am F
    beat = 60 / bpm
    bar = 4 * beat
    bars = int(np.ceil(seconds / bar)) + 1
    if mood == "festive":
        sa = 50                                                       # D as Sa
        for b in range(bars):                                         # tanpura: Pa Sa Sa Sa(low), slowly
            for k, m in enumerate([sa + 7, sa + 12, sa + 12, sa]):
                _add(buf, _pluck(_note(m), bar, decay=1.4, bright=7), b * bar + k * beat, .16)
        pattern = ["dha", "dha", "tin", "dha", "dha", "dha", "tin", "na"]   # a keherwa-like groove
        scale = [0, 2, 4, 7, 9, 12, 14, 16]                                  # Sa Re Ga Pa Dha (sa'..)
        for b in range(bars):
            for k, hit in enumerate(pattern):
                _add(buf, _tabla(hit, rng), b * bar + k * beat / 2, .55 if hit == "dha" else .35)
            if b % 2 == 0:
                for k in range(8):
                    m = sa + 12 + scale[int(rng.integers(0, len(scale)))]
                    _add(buf, _pluck(_note(m), .5, decay=.22, bright=5), b * bar + k * beat / 2 + beat / 4, .18)
    else:
        for b in range(bars):
            chord = prog[b % len(prog)]
            _add(buf, _pad([_note(m - 12) for m in chord], bar), b * bar, .22 if mood == "upbeat" else .3)
            steps = 8 if mood == "upbeat" else 4
            for k in range(steps):
                if mood == "calm" and rng.random() < .35:
                    continue
                m = chord[k % len(chord)] + (12 if k % 4 == 3 else 0)
                _add(buf, _pluck(_note(m + 12), .6, decay=.25 if mood == "upbeat" else .6, bright=3 if mood == "calm" else 5),
                     b * bar + k * bar / steps, .17 if mood == "upbeat" else .14)
            if mood == "upbeat":
                for k in range(4):
                    _add(buf, _kick(), b * bar + k * beat, .7)
                    if k in (1, 3):
                        _add(buf, _noise_hit(.25, .06, rng), b * bar + k * beat, .22)
                for k in range(8):
                    _add(buf, _noise_hit(.08, .012, rng), b * bar + k * beat / 2, .08)
            elif b % 2 == 0:
                _add(buf, _kick(.5), b * bar, .3)
    buf = buf[: int(seconds * SR)]
    # gentle echo, then normalise with headroom
    d = int(beat * .75 * SR)
    if d < len(buf):
        buf[d:] += buf[:-d] * .18
    peak = np.max(np.abs(buf)) or 1.0
    return np.tanh(buf / peak * 1.2) * .8


def write(mood: str, seconds: float, path: Path, seed: int = 7) -> Path | None:
    if mood not in MOODS or mood == "none" or seconds <= 0:
        return None
    x = make(mood, seconds, seed)
    stereo = np.stack([x, np.roll(x, int(.012 * SR))], axis=1)     # a touch of width
    pcm = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path
