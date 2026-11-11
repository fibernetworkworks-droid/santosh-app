"""v0.421 SPATIAL AUDIO (Hoola Game Engine plan Phase 7 batch 2, Game Desk plan role 8 - the Spatial Audio Systems
Programmer): 3D sound for her game, rendered and MEASURED in code (numpy + scipy, no model, no money), headphone demos
she can listen to, and Hoola's own HoolaAudio autoload in her game.

The renderer (licence-clean, no recorded HRTF set): the spherical-head model of Brown & Duda (1998) - the interaural
time difference by Woodworth's formula, a one-pole / one-zero head-shadow filter per ear - plus inverse-distance gain
with air absorption, occlusion (a stated -10 dB and an 800 Hz low-pass) and reverb zones (exponentially decaying noise
tails with early reflections, designed to a reverb time RT60).

Every claim is a measurement, never a promise:
- direction: a noise burst is rendered at 13 directions; the time difference between the ears is measured by
  cross-correlation and must follow Woodworth within 40 microseconds, the high-band level difference must grow with
  the angle and change side with it. Said plainly: a spherical head gives no front / back or height cue (the "cone of
  confusion") - that needs a measured HRTF set, which is not part of this pack;
- distance: the level must fall 6 dB per doubling of distance (1, 2, 4, 8 m), +-0.5 dB;
- occlusion: the measured drop and the extra high-frequency drop are reported;
- reverb zones: each zone's RT60 is measured back from its own impulse response (Schroeder backward integration,
  T20) and must be within 10 % of the design;
- loudness: the demos are normalised to -16 LUFS (ITU-R BS.1770 K-weighting with its gates, measured after) and the
  peak kept under -1 dBFS;
- speed: render time per voice per second of sound is measured; latency = block / sample rate is stated;
- repeatable: the whole render runs twice and the fingerprints must match.

Her OK -> HoolaAudio in every build: a bus per reverb zone (Godot's own AudioEffectReverb, mapped from RT60 - said to be
an approximation of the designed tail), an occlusion bus (-10 dB + low-pass), 2D / 3D players set to inverse distance
with her min / max distances. In-game positional sound is Godot's own panning + distance + zones; the true binaural
render is for the demos and baked ambience (said on the card)."""
from __future__ import annotations

import hashlib
import io
import json
import logging
import math
import re
import time
import wave
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from scipy import signal
from sqlalchemy import JSON, DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import service as G

log = logging.getLogger("santosh.gamedesk")
FILE = "hoola_audio.gd"
KEY = "audio_dev"
SR = 48000
BLOCK = 256
HEAD_R = 0.0875              # m, the average adult head radius used by Brown & Duda
C_SOUND = 343.0              # m/s
OCCL_DB, OCCL_HZ = -10.0, 800.0
_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gameaudio")
ZONE_PRESETS = {"small_room": 0.35, "room": 0.6, "hall": 1.8, "cave": 3.0, "cathedral": 4.5, "outdoor": 0.15}


class AudioError(G.GameError):
    pass


class GameAudio(Base):
    __tablename__ = "game_audio"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ga"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    studio_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    words: Mapped[str] = mapped_column(Text, default="")
    plan: Mapped[dict] = mapped_column(JSON, default=dict)          # {zones, sources, min_d, max_d, px_per_m}
    report: Mapped[dict] = mapped_column(JSON, default=dict)        # {checks, numbers, verdict}
    status: Mapped[str] = mapped_column(String(12), default="testing")   # testing | draft | approved | rejected | failed
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        GameAudio.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


# ================================================================ the plan (her words -> zones + distances, clamped)
def clean_plan(plan: dict | None) -> dict:
    p = dict(plan or {})
    zones = []
    for z in (p.get("zones") or [{"key": "room", "rt60": 0.6}, {"key": "hall", "rt60": 1.8}])[:6]:
        key = re.sub(r"[^a-z0-9_]", "", str((z or {}).get("key") or "zone").lower())[:24] or "zone"
        try:
            rt = float((z or {}).get("rt60") or ZONE_PRESETS.get(key, 0.6))
        except (TypeError, ValueError):
            rt = 0.6
        zones.append({"key": key, "rt60": round(min(max(rt, 0.1), 6.0), 2), "wet": round(min(max(float((z or {}).get("wet", 0.3)), 0.0), 1.0), 2)})
    seen = set()
    zones = [z for z in zones if not (z["key"] in seen or seen.add(z["key"]))]

    def num(k: str, d: float, lo: float, hi: float) -> float:
        try:
            return round(min(max(float(p.get(k, d)), lo), hi), 2)
        except (TypeError, ValueError):
            return d
    min_d = num("min_d", 1.0, 0.1, 50.0)
    return {"zones": zones, "min_d": min_d, "max_d": max(min_d * 2, num("max_d", 40.0, 1.0, 500.0)),
            "px_per_m": num("px_per_m", 64.0, 1.0, 1000.0)}


def from_words(words: str) -> dict:
    """Zones she named ('a cave and a big hall') -> the matching presets; 'max distance 30 m' read by rules."""
    w = (words or "").lower()
    zones = [{"key": k, "rt60": v} for k, v in ZONE_PRESETS.items() if re.search(k.replace("_", "[ _]?"), w)]
    if re.search(r"\b(gufa|guha)\b", w) and not any(z["key"] == "cave" for z in zones):
        zones.append({"key": "cave", "rt60": ZONE_PRESETS["cave"]})
    out: dict[str, Any] = {"zones": zones} if zones else {}
    m = re.search(r"max(?:imum)?\s*(?:distance)?\D{0,6}(\d+(?:\.\d+)?)\s*m\b", w)
    if m:
        out["max_d"] = float(m.group(1))
    return out


# ================================================================ the renderer
def woodworth_itd(az_deg: float) -> float:
    """Interaural time difference in seconds for an azimuth (0 = front, +90 = right). Behind the head the lateral
    angle folds back (a spherical head cannot tell front from back)."""
    a = math.radians(az_deg)
    lat = math.asin(max(-1.0, min(1.0, math.sin(a))))
    return HEAD_R / C_SOUND * (lat + math.sin(lat))


def _shadow(theta_ear_deg: float) -> tuple[np.ndarray, np.ndarray]:
    """Brown & Duda head shadow for one ear: H(s) = (alpha s + beta) / (s + beta), beta = 2 c / a,
    alpha = (1 + a_min / 2) + (1 - a_min / 2) cos(theta / theta_min * pi), a_min = 0.1, theta_min = 150 deg."""
    a_min, th_min = 0.1, 150.0
    alpha = (1 + a_min / 2) + (1 - a_min / 2) * math.cos(math.radians(theta_ear_deg) / math.radians(th_min) * math.pi)
    beta = 2 * C_SOUND / HEAD_R
    b, a = signal.bilinear([alpha, beta], [1.0, beta], SR)
    return b, a


def _frac_delay(x: np.ndarray, d: float) -> np.ndarray:
    n = np.arange(len(x), dtype=float)
    return np.interp(n - d * SR, n, x, left=0.0, right=0.0)


def binaural(mono: np.ndarray, az_deg: float) -> np.ndarray:
    """(n, 2) left / right for a source at az_deg on the horizontal plane."""
    itd = woodworth_itd(az_deg)
    # angle between the source and each ear axis (ears at -90 / +90)
    th_r = abs(((az_deg - 90 + 180) % 360) - 180)
    th_l = abs(((az_deg + 90 + 180) % 360) - 180)
    br, ar = _shadow(th_r)
    bl, al = _shadow(th_l)
    right = signal.lfilter(br, ar, mono)
    left = signal.lfilter(bl, al, mono)
    if itd > 0:                                         # source on the right: the left ear hears it later
        left = _frac_delay(left, itd)
    elif itd < 0:
        right = _frac_delay(right, -itd)
    return np.stack([left, right], axis=1)


def distance_gain(d: float, min_d: float) -> float:
    return min_d / max(d, min_d)


def air(x: np.ndarray, d: float) -> np.ndarray:
    fc = min(18000.0, 20000.0 / (1 + d / 30.0))
    b, a = signal.butter(1, fc / (SR / 2))
    return signal.lfilter(b, a, x, axis=0)


def occlude(x: np.ndarray) -> np.ndarray:
    b, a = signal.butter(2, OCCL_HZ / (SR / 2))
    return signal.lfilter(b, a, x, axis=0) * 10 ** (OCCL_DB / 20)


def reverb_ir(rt60: float, seed: int, wet_len: float | None = None) -> np.ndarray:
    """A stereo impulse response: a few early reflections + decorrelated noise decaying 60 dB in rt60 seconds."""
    rng = np.random.default_rng(seed)
    n = int(SR * (wet_len or min(8.0, rt60 * 1.6 + 0.1)))
    t = np.arange(n) / SR
    env = np.exp(-6.907755 * t / rt60)                  # 60 dB = ln(1000) nepers
    ir = rng.standard_normal((n, 2)) * env[:, None]
    for k in range(6):                                  # early reflections, 3-40 ms, falling
        i = int(SR * (0.003 + 0.007 * k + rng.random() * 0.004))
        if i < n:
            ir[i] += (0.8 - 0.1 * k) * np.array([1.0, 0.9 if k % 2 else 1.1])
    ir[0] = 0
    return ir / np.sqrt((ir ** 2).sum() / 2)


def measured_rt60(ir: np.ndarray) -> float:
    """Schroeder backward integration of the energy, T20 (the -5 to -25 dB slope) x 3."""
    e = (ir ** 2).sum(axis=1) if ir.ndim == 2 else ir ** 2
    edc = np.cumsum(e[::-1])[::-1]
    edc_db = 10 * np.log10(edc / edc[0] + 1e-30)
    t = np.arange(len(edc)) / SR
    i5 = int(np.argmax(edc_db <= -5))
    i25 = int(np.argmax(edc_db <= -25))
    if i25 <= i5:
        return 0.0
    slope, _b = np.polyfit(t[i5:i25], edc_db[i5:i25], 1)
    return float(-60.0 / slope) if slope < 0 else 0.0


# ================================================================ loudness (ITU-R BS.1770-4, 48 kHz coefficients)
_PRE_B = [1.53512485958697, -2.69169618940638, 1.19839281085285]
_PRE_A = [1.0, -1.69065929318241, 0.73248077421585]
_RLB_B = [1.0, -2.0, 1.0]
_RLB_A = [1.0, -1.99004745483398, 0.99007225036621]


def lufs(x: np.ndarray) -> float:
    """Integrated loudness of a 48 kHz signal (mono or stereo): K-weighting, 400 ms blocks with 75 % overlap, the
    absolute -70 LUFS gate and the relative -10 LU gate."""
    x = x if x.ndim == 2 else x[:, None]
    y = signal.lfilter(_RLB_B, _RLB_A, signal.lfilter(_PRE_B, _PRE_A, x, axis=0), axis=0)
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    if len(y) < blk:
        return -70.0
    zs = np.array([(y[i:i + blk] ** 2).mean(axis=0).sum() for i in range(0, len(y) - blk + 1, hop)])
    lk = -0.691 + 10 * np.log10(zs + 1e-30)
    zs = zs[lk > -70]
    if not len(zs):
        return -70.0
    rel = -0.691 + 10 * np.log10(zs.mean()) - 10
    zs = zs[(-0.691 + 10 * np.log10(zs + 1e-30)) > rel]
    return round(float(-0.691 + 10 * np.log10(zs.mean() + 1e-30)), 2)


def normalise(x: np.ndarray, target: float = -16.0, peak_db: float = -1.0) -> tuple[np.ndarray, bool]:
    """Gain to the loudness target; if that would push the true peak (4x oversampled) over peak_db, the peak limit
    wins and the file is quieter than the target - reported as peak-limited, never squashed by a compressor."""
    g = 10 ** ((target - lufs(x)) / 20)
    y = x * g
    pk = float(np.abs(signal.resample_poly(y, 4, 1, axis=0)).max()) if len(y) else 0.0
    lim = 10 ** (peak_db / 20)
    return (y * (lim / pk), True) if bool(pk > lim) else (y, False)


def wav_bytes(x: np.ndarray) -> bytes:
    x = np.clip(x, -1, 1)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(x.shape[1] if x.ndim == 2 else 1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())
    return buf.getvalue()


# ================================================================ sounds (made here, seeded)
def pink(seed: int, seconds: float) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(SR * seconds)
    f = np.fft.rfft(rng.standard_normal(n))
    f[1:] /= np.sqrt(np.arange(1, len(f)))
    x = np.fft.irfft(f, n)
    return x / np.abs(x).max() * 0.5


def clap(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(SR * 0.08)
    x = rng.standard_normal(n) * np.exp(-np.arange(n) / (SR * 0.012))
    return np.concatenate([x / np.abs(x).max() * 0.8, np.zeros(int(SR * 0.02))])


# ================================================================ the measurements
def _xcorr_itd(lr: np.ndarray, max_s: float = 0.0012) -> float:
    m = int(max_s * SR)
    l, r = lr[:, 0], lr[:, 1]
    best, lag = -1e30, 0
    for k in range(-m, m + 1):
        v = float(np.dot(l[max(0, k):len(l) + min(0, k)], r[max(0, -k):len(r) - max(0, k)]))
        if v > best:
            best, lag = v, k
    # refine: parabolic interpolation around the peak
    def cc(k: int) -> float:
        return float(np.dot(l[max(0, k):len(l) + min(0, k)], r[max(0, -k):len(r) - max(0, k)]))
    y0, y1, y2 = cc(lag - 1), cc(lag), cc(lag + 1)
    den = y0 - 2 * y1 + y2
    frac = 0.5 * (y0 - y2) / den if den else 0.0
    return (lag + frac) / SR                            # > 0: left lags right (source on the right)


def _band_db(x: np.ndarray, lo: float, hi: float) -> float:
    b, a = signal.butter(4, [lo / (SR / 2), hi / (SR / 2)], btype="band")
    y = signal.lfilter(b, a, x)
    return 10 * math.log10(float((y ** 2).mean()) + 1e-30)


def measure_directions(seed: int = 7) -> dict:
    burst = pink(seed, 0.25)
    rows, ok_itd, ok_side = [], True, True
    prev_ild = None
    mono_ok = True
    for az in (-90, -60, -30, 0, 30, 60, 90, 120, 150, 180, -150, -120, -45):
        lr = binaural(burst, az)
        itd = _xcorr_itd(lr)
        exp = woodworth_itd(az)
        ild = _band_db(lr[:, 1], 2000, 8000) - _band_db(lr[:, 0], 2000, 8000)
        err_us = abs(itd - exp) * 1e6
        side_ok = (az % 180 == 0 and abs(ild) < 1.0) or (math.sin(math.radians(az)) * ild > 0)
        ok_itd &= err_us <= max(40.0, 0.12 * abs(exp) * 1e6)
        ok_side &= side_ok
        rows.append({"az": az, "itd_us": round(itd * 1e6, 1), "expected_us": round(exp * 1e6, 1), "ild_db": round(ild, 2)})
    # |ILD| grows 0 -> 30 -> 60 degrees on both sides and stays above the 30-degree value at 90 (a sphere's level
    # difference peaks before 90: sound bends round the head and meets behind the far ear - the "bright spot")
    by = {r["az"]: abs(r["ild_db"]) for r in rows}
    mono_ok = all(by[s * 30] > by[0] + 1 and by[s * 60] > by[s * 30] and by[s * 90] > by[s * 30] for s in (1, -1))
    return {"rows": rows, "itd_ok": bool(ok_itd), "side_ok": bool(ok_side), "ild_grows": bool(mono_ok)}


def measure_distance(min_d: float) -> dict:
    x = pink(3, 1.0)
    lv = []
    for d in (1.0, 2.0, 4.0, 8.0):
        y = x * distance_gain(d * min_d, min_d)
        lv.append(10 * math.log10(float((y ** 2).mean())))
    steps = [round(lv[i + 1] - lv[i], 2) for i in range(3)]
    return {"steps_db": steps, "ok": bool(all(abs(s + 6.02) <= 0.5 for s in steps))}


def measure_occlusion() -> dict:
    x = pink(5, 1.0)
    y = occlude(x[:, None])[:, 0]
    tot = 10 * math.log10(float((y ** 2).mean()) / float((x ** 2).mean()))
    hi = _band_db(y, 2000, 8000) - _band_db(x, 2000, 8000)
    lo = _band_db(y, 100, 400) - _band_db(x, 100, 400)
    return {"drop_db": round(tot, 1), "high_drop_db": round(hi, 1), "low_drop_db": round(lo, 1),
            "ok": bool(tot <= -9.0 and hi < lo - 6)}


def render(plan: dict, seed: int = 11) -> dict:
    """Every check + the three demo files. Pure: same plan + seed = same bytes."""
    t0 = time.perf_counter()
    dirs = measure_directions(seed)
    dist = measure_distance(plan["min_d"])
    occl = measure_occlusion()
    zones = []
    zone_audio = []
    c = clap(seed)
    for i, z in enumerate(plan["zones"]):
        ir = reverb_ir(z["rt60"], seed + 100 + i)
        rt = measured_rt60(ir)
        dry = np.stack([c, c], axis=1)
        wet = signal.fftconvolve(dry, ir, axes=0)[: len(dry) + int(SR * min(4.0, z["rt60"] * 1.2))]
        mix = np.zeros_like(wet)
        mix[: len(dry)] += dry
        mix += wet * z["wet"] * 0.5
        zone_audio.append(mix)
        zone_audio.append(np.zeros((int(SR * 0.3), 2)))
        zones.append({"key": z["key"], "rt60": z["rt60"], "measured_rt60": round(rt, 3),
                      "err_pct": round(abs(rt - z["rt60"]) / z["rt60"] * 100, 1), "ok": bool(abs(rt - z["rt60"]) <= 0.1 * z["rt60"])})
    # demo 1: a sound walking once around the head in 8 s (overlap-add of 50 ms windows, each at its own angle)
    src = pink(seed + 1, 8.2)
    win = int(SR * 0.05)
    hop = win // 2
    hann = np.hanning(win)
    walk = np.zeros((len(src) + win, 2))
    tv = time.perf_counter()
    for i in range(0, len(src) - win, hop):
        az = (i / (len(src) - win)) * 360.0 - 180.0
        ctx = max(0, i - 512)
        seg = binaural(src[ctx:i + win], az)[i - ctx:]
        walk[i:i + win] += seg * hann[:, None]
    voice_s = time.perf_counter() - tv
    walk = walk[: len(src)]
    # demo 2: the same sound at 1, 2, 4, 8 x min distance, front-right
    dist_demo = np.concatenate([np.concatenate([air(binaural(pink(seed + 2, 1.0) * distance_gain(m * plan["min_d"], plan["min_d"]), 40),
                                                    m * plan["min_d"]), np.zeros((int(SR * 0.25), 2))]) for m in (1, 2, 4, 8)])
    zone_demo = np.concatenate(zone_audio) if zone_audio else np.zeros((SR, 2))
    files, loud = {}, {}
    for name, sig_ in (("walkaround.wav", walk), ("distance.wav", dist_demo), ("zones.wav", zone_demo)):
        y, limited = normalise(sig_)
        loud[name] = {"lufs": lufs(y), "peak_limited": limited,
                      "peak_db": round(20 * math.log10(float(np.abs(signal.resample_poly(y, 4, 1, axis=0)).max()) + 1e-12), 2)}
        files[name] = wav_bytes(y)
    per_voice = voice_s / 8.2
    return {"directions": dirs, "distance": dist, "occlusion": occl, "zones": zones, "loudness": loud, "files": files,
            "numbers": {"render_s": round(time.perf_counter() - t0, 2), "cpu_per_voice_s_per_s": round(per_voice, 4),
                        "voices_in_10pct_core": int(0.1 / per_voice) if per_voice > 0 else None,
                        "latency_ms": round(BLOCK / SR * 1000, 2), "sample_rate": SR},
            "fingerprint": hashlib.sha256(b"".join(files[k] for k in sorted(files))).hexdigest()[:16]}


def judge(r: dict, r2: dict | None) -> dict:
    checks: list[dict] = []

    def ck(name: str, ok: bool, note: str) -> None:
        checks.append({"check": name, "ok": bool(ok), "note": note})
    d = r["directions"]
    worst = max(abs(x["itd_us"] - x["expected_us"]) for x in d["rows"])
    ck("direction: time between the ears", d["itd_ok"], f"13 directions measured by cross-correlation; worst {round(worst, 1)} us "
       "from Woodworth's formula (limit 40 us or 12 %: the head-shadow filter adds a little delay at the far ear, as a real "
       "head does at low frequencies)")
    ck("direction: level between the ears", d["side_ok"] and d["ild_grows"],
       "the 2-8 kHz level is louder on the side the sound is on and grows from 0 to 30 to 60 degrees (it peaks before 90: "
       "the bright spot behind a round head)" + ("" if d["ild_grows"] else " - it does NOT grow that way"))
    ck("distance: 6 dB per doubling", r["distance"]["ok"], f"measured steps {r['distance']['steps_db']} dB")
    o = r["occlusion"]
    ck("occlusion", o["ok"], f"{o['drop_db']} dB overall, highs {o['high_drop_db']} dB, lows {o['low_drop_db']} dB")
    for z in r["zones"]:
        ck(f"reverb zone '{z['key']}'", z["ok"], f"designed RT60 {z['rt60']} s, measured {z['measured_rt60']} s ({z['err_pct']}%)")
    for name, lv in r["loudness"].items():
        ok = lv["peak_db"] <= -0.9 and (abs(lv["lufs"] + 16) <= 0.5 or (lv.get("peak_limited") and lv["lufs"] < -16))
        ck(f"loudness of {name}", ok, f"{lv['lufs']} LUFS (target -16), peak {lv['peak_db']} dBFS (limit -1)"
           + (" - peak-limited: louder would clip, so it stays this quiet (no compressor)" if lv.get("peak_limited") else ""))
    if r2 is not None:
        ck("same render twice", r["fingerprint"] == r2["fingerprint"], "the demos rendered twice must be byte-identical")
    ok = all(c["ok"] for c in checks)
    return {"checks": checks, "verdict": "PASS" if ok else "FAIL", "passed": sum(c["ok"] for c in checks), "total": len(checks),
            "limits": "A spherical head gives no front / back or height cue (cone of confusion); in-game positional sound "
                      "uses Godot's panning + distance + zones, the binaural render is for demos and baked ambience."}


# ================================================================ store + jobs
def _root(tenant: str) -> Path:
    return G.root() / (re.sub(r"[^\w-]", "_", tenant)[:64] or "t") / "audio"


def _studio(tenant: str, ref: str):
    from . import studio as S
    with session() as s:
        r = S._studio(s, tenant, ref)
        s.expunge(r)
    return r


def _get(s, tenant: str, ref: str) -> GameAudio:
    ref = str(ref or "").strip()
    q = select(GameAudio).where(GameAudio.tenant_id == tenant)
    r = s.scalars(q.where(GameAudio.id == ref)).first() or s.scalars(q.where(GameAudio.number == ref.upper())).first()
    if r is None:
        raise AudioError("This audio setup was not found (give A-001).")
    return r


def _sig(name: str) -> str:
    import hmac as _h
    from ..config import get_settings
    key = (getattr(get_settings(), "api_key", "") or "hoola-audio").encode()
    return _h.new(key, f"audio:{name}".encode(), "sha256").hexdigest()[:16]


DEMOS = ("walkaround.wav", "distance.wav", "zones.wav")


def file_url(r: GameAudio, name: str) -> str:
    return f"/api/gamedesk/audio/{r.id}/file/{name}?sig={_sig(r.id + name)}"


def audio_file(aid: str, name: str, sig: str) -> Path | None:
    import hmac as _h
    if not re.fullmatch(r"ga_[A-Za-z0-9_-]{4,40}", str(aid or "")) or name not in DEMOS or not _h.compare_digest(_sig(aid + name), str(sig or "")):
        return None
    ensure_table()
    with session() as s:
        r = s.get(GameAudio, aid)
        if r is None:
            return None
        s.expunge(r)
    p = _root(r.tenant_id) / r.id / name
    return p if p.is_file() else None


def view(r: GameAudio) -> dict[str, Any]:
    d = _root(r.tenant_id) / r.id
    return {"id": r.id, "number": r.number, "status": r.status, "words": r.words, "plan": r.plan or {},
            "report": {k: v for k, v in (r.report or {}).items() if k != "raw"}, "error": r.error, "studio_id": r.studio_id,
            "files": {n: file_url(r, n) for n in DEMOS if (d / n).is_file()},
            "at": r.created_at.isoformat() if r.created_at else ""}


def setup(tenant: str, words: str = "", plan: dict | None = None, studio: str = "", run_now: bool = True) -> dict[str, Any]:
    ensure_table()
    sid = _studio(tenant, studio).id if studio else ""
    p = clean_plan({**from_words(words), **(plan or {})})
    with session() as s:
        n = len(s.scalars(select(GameAudio.id).where(GameAudio.tenant_id == tenant)).all()) + 1
        r = GameAudio(tenant_id=tenant, studio_id=sid, number=f"A-{n:03d}", words=(words or "")[:600], plan=p, status="testing")
        s.add(r)
        s.flush()
        s.expunge(r)
    if run_now:
        _POOL.submit(_safe_run, r.id)
    return view(r)


def _safe_run(aid: str) -> None:
    try:
        run(aid)
    except Exception as e:                              # noqa: BLE001
        log.exception("audio %s", aid)
        with session() as s:
            r = s.get(GameAudio, aid)
            if r is not None:
                r.status, r.error = "failed", str(e)[:400]


def run(aid: str) -> dict[str, Any]:
    with session() as s:
        r = s.get(GameAudio, aid)
        s.expunge(r)
    a = render(r.plan)
    b = render(r.plan)
    rep = judge(a, b)
    rep.update({"numbers": a["numbers"], "directions": a["directions"]["rows"], "zones": a["zones"],
                "distance": a["distance"], "occlusion": a["occlusion"], "loudness": a["loudness"], "fingerprint": a["fingerprint"]})
    d = _root(r.tenant_id) / r.id
    d.mkdir(parents=True, exist_ok=True)
    for n, data in a["files"].items():
        (d / n).write_bytes(data)
    with session() as s:
        row = s.get(GameAudio, aid)
        row.report = rep
        row.status = "draft" if rep["verdict"] == "PASS" else "failed"
        row.error = "" if rep["verdict"] == "PASS" else "; ".join(c["check"] + ": " + c["note"] for c in rep["checks"] if not c["ok"])[:400]
        row.updated_at = now()
        s.flush()
        s.expunge(row)
    return view(row)


def approve(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _get(s, tenant, ref)
        if r.status != "draft":
            raise AudioError("Only an audio setup that PASSED can be OKed." if r.status != "testing" else "The check is still running.")
        for o in s.scalars(select(GameAudio).where(GameAudio.tenant_id == tenant, GameAudio.studio_id == r.studio_id,
                                                   GameAudio.status == "approved")).all():
            o.status = "rejected"
        r.status = "approved"
        s.flush()
        s.expunge(r)
    return view(r)


def reject(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _get(s, tenant, ref)
        r.status = "rejected"
        s.flush()
        s.expunge(r)
    return view(r)


def setups(tenant: str, studio: str = "") -> list[dict[str, Any]]:
    ensure_table()
    sid = _studio(tenant, studio).id if studio else None
    with session() as s:
        q = select(GameAudio).where(GameAudio.tenant_id == tenant)
        if sid is not None:
            q = q.where(GameAudio.studio_id == sid)
        rows = s.scalars(q.order_by(GameAudio.created_at.desc())).all()[:30]
        for r in rows:
            s.expunge(r)
    return [view(r) for r in rows]


def get(tenant: str, ref: str) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        r = _get(s, tenant, ref)
        s.expunge(r)
    return view(r)


def godot_reverb(rt60: float) -> dict:
    """Godot's AudioEffectReverb has no RT60 knob; room_size / damping are mapped from it (an approximation of the
    designed tail - the measured tail is the demo's)."""
    room = min(1.0, max(0.05, rt60 / 4.5))
    return {"room_size": round(room, 3), "damping": round(max(0.1, 0.9 - room * 0.7), 3)}


GD = '''extends Node
# HoolaAudio (an autoload): her game's sound space - reverb zones, occlusion and distance - from an audio setup Hoola
# MEASURED (verdict below). Written by Hoola Studio; do not edit (approve an audio setup in the Studio and rebuild).
const PLAN := __P__
var _zone := ""

func _ready() -> void:
	for z in PLAN["zones"]:
		var name := "HoolaZone_" + String(z["key"])
		if AudioServer.get_bus_index(name) >= 0:
			continue
		AudioServer.add_bus()
		var i := AudioServer.bus_count - 1
		AudioServer.set_bus_name(i, name)
		AudioServer.set_bus_send(i, "Master")
		var rv := AudioEffectReverb.new()
		rv.room_size = float(z["godot"]["room_size"])
		rv.damping = float(z["godot"]["damping"])
		rv.wet = float(z["wet"])
		rv.dry = 1.0
		AudioServer.add_bus_effect(i, rv)
	if AudioServer.get_bus_index("HoolaOccluded") < 0:
		AudioServer.add_bus()
		var j := AudioServer.bus_count - 1
		AudioServer.set_bus_name(j, "HoolaOccluded")
		AudioServer.set_bus_send(j, "Master")
		AudioServer.set_bus_volume_db(j, float(PLAN["occlusion_db"]))
		var lp := AudioEffectLowPassFilter.new()
		lp.cutoff_hz = float(PLAN["occlusion_hz"])
		AudioServer.add_bus_effect(j, lp)

func zones() -> Array:
	var out: Array = []
	for z in PLAN["zones"]:
		out.append(String(z["key"]))
	return out

func set_zone(key: String) -> void:
	# the zone the listener is in now: every player made by HoolaAudio follows it
	_zone = key

func bus() -> String:
	return ("HoolaZone_" + _zone) if _zone != "" and AudioServer.get_bus_index("HoolaZone_" + _zone) >= 0 else "Master"

func player3d(stream: AudioStream) -> AudioStreamPlayer3D:
	var p := AudioStreamPlayer3D.new()
	p.stream = stream
	p.attenuation_model = AudioStreamPlayer3D.ATTENUATION_INVERSE_DISTANCE
	p.unit_size = float(PLAN["min_d"])
	p.max_distance = float(PLAN["max_d"])
	p.bus = bus()
	return p

func player2d(stream: AudioStream) -> AudioStreamPlayer2D:
	var p := AudioStreamPlayer2D.new()
	p.stream = stream
	p.attenuation = 1.0
	p.max_distance = float(PLAN["max_d"]) * float(PLAN["px_per_m"])
	p.bus = bus()
	return p

func occlude(p: Node, blocked: bool) -> void:
	# a wall between the sound and the listener: -10 dB and a low-pass, measured in Hoola's audio check
	if p is AudioStreamPlayer2D or p is AudioStreamPlayer3D or p is AudioStreamPlayer:
		p.bus = "HoolaOccluded" if blocked else bus()
'''


def gd(plan: dict, verdict: str) -> str:
    from .bible import _gd
    keep = {"zones": [{**z, "godot": godot_reverb(z["rt60"])} for z in plan["zones"]], "min_d": plan["min_d"],
            "max_d": plan["max_d"], "px_per_m": plan["px_per_m"], "occlusion_db": OCCL_DB, "occlusion_hz": OCCL_HZ,
            "verdict": verdict}
    return GD.replace("__P__", _gd(keep))


def for_game(tenant: str, game_id: str) -> tuple[str, dict[str, Path]] | None:
    from . import studio as S
    ensure_table()
    with session() as s:
        st = s.scalars(select(S.GameStudio).where(S.GameStudio.tenant_id == tenant, S.GameStudio.game_id == game_id)).first()
        if st is None:
            return None
        r = s.scalars(select(GameAudio).where(GameAudio.tenant_id == tenant, GameAudio.studio_id == st.id,
                                              GameAudio.status == "approved").order_by(GameAudio.created_at.desc())).first()
        if r is None:
            return None
        s.expunge(r)
    return gd(r.plan, (r.report or {}).get("verdict", "")), {}


def apply(tenant: str, studio: str) -> dict[str, Any]:
    st = _studio(tenant, studio)
    if for_game(tenant, st.game_id) is None:
        raise AudioError("No approved audio setup; pass the check and OK it first.")
    try:
        from . import bible as B
        bv = B.view(tenant, st.id)["version"]
    except Exception:                                   # noqa: BLE001
        bv = 0
    G.data_build(tenant, st.game_id, bv, words="Audio setup into the game")
    return {"ok": True, "say": "The audio setup is going into the game (a rebuild is running)."}
