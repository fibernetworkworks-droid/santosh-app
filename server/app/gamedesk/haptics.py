"""v0.421 HAPTICS (Hoola Game Engine plan Phase 7 batch 2, Game Desk plan role 10 - the Haptic Feedback Systems Engineer):
vibration patterns as DATA, one pattern per meaning, checked in code, exported for every place a buzz can happen, and
Hoola's own HoolaHaptics autoload in her game.

A pattern = a list of events {t_ms, dur_ms, amp 0-1, sharp 0-1}. From her words Hoola picks meanings (jump, coin,
hit, game over...) and maps each to a library pattern by rules; she can edit the numbers. No model, no money.

CHECKED in code, a failure is named:
- timing: every pulse at least the actuator's shortest felt pulse (phone LRA 10 ms, ERM motor 30 ms - it must spin
  up, controller rumble 40 ms), gaps of at least 20 ms so two pulses are felt as two, feedback patterns under 1.5 s;
- one pattern per meaning: every pair is compared on its 5 ms envelope (and its pulse count); two that feel the same
  are named - "buzz for everything" fails;
- battery: energy per play from on-time x amplitude^2 x the actuator's stated drive power (assumption printed), and
  per 1,000 plays;
- accessibility: an off switch and an intensity slider are ALWAYS in HoolaHaptics (saved in the game's own user://
  file) and in every exported kit - a kit without them is not written;
- the exports: Core Haptics AHAP JSON (validated against its shape), Android VibrationEffect waveforms (timings /
  amplitudes 0-255 checked), the Godot autoload, and a DRV2605 driver in C for her own device that is COMPILED here
  with gcc against a stand-in Wire / Arduino header (no compiler on the server = NOT ASSESSED, said plainly).

Her OK -> HoolaHaptics in every build: play(name) on a phone (Input.vibrate_handheld; on the web Android Chrome's
navigator.vibrate - iPhone browsers have no vibration, said plainly) and on game controllers (start_joy_vibration)."""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import JSON, DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import service as G

log = logging.getLogger("santosh.gamedesk")
FILE = "hoola_haptics.gd"
KEY = "haptics_dev"
ACTUATORS = {   # shortest felt pulse (ms), drive power assumption (mW) - starting points, her device's datasheet wins
    "phone_lra": {"min_ms": 10, "mw": 90, "name": "phone (linear motor)"},
    "phone_erm": {"min_ms": 30, "mw": 150, "name": "phone (spinning motor)"},
    "controller": {"min_ms": 40, "mw": 400, "name": "game controller rumble"},
    "drv2605_lra": {"min_ms": 10, "mw": 120, "name": "your device: DRV2605 + LRA"},
    "drv2605_erm": {"min_ms": 30, "mw": 180, "name": "your device: DRV2605 + ERM"},
}
MIN_GAP_MS = 20
MAX_FEEDBACK_MS = 1500
SAME_LIMIT = 0.18          # envelopes closer than this (0..1) feel the same

LIBRARY: dict[str, list[dict]] = {
    "tap": [{"t": 0, "d": 15, "a": 0.6, "s": 0.9}],
    "button": [{"t": 0, "d": 12, "a": 0.4, "s": 1.0}],
    "double_tap": [{"t": 0, "d": 15, "a": 0.7, "s": 0.9}, {"t": 80, "d": 15, "a": 0.7, "s": 0.9}],
    "success": [{"t": 0, "d": 20, "a": 0.5, "s": 0.6}, {"t": 90, "d": 40, "a": 0.9, "s": 0.4}],
    "coin": [{"t": 0, "d": 12, "a": 0.5, "s": 1.0}, {"t": 45, "d": 12, "a": 0.8, "s": 1.0}],
    "jump": [{"t": 0, "d": 25, "a": 0.45, "s": 0.7}],
    "hit": [{"t": 0, "d": 60, "a": 1.0, "s": 0.3}],
    "warning": [{"t": 0, "d": 50, "a": 0.8, "s": 0.5}, {"t": 120, "d": 50, "a": 0.8, "s": 0.5}, {"t": 240, "d": 50, "a": 0.8, "s": 0.5}],
    "error": [{"t": 0, "d": 120, "a": 0.9, "s": 0.2}, {"t": 180, "d": 120, "a": 0.9, "s": 0.2}],
    "game_over": [{"t": 0, "d": 300, "a": 1.0, "s": 0.1}, {"t": 380, "d": 200, "a": 0.6, "s": 0.1}, {"t": 650, "d": 120, "a": 0.3, "s": 0.1}],
    "heartbeat": [{"t": 0, "d": 30, "a": 0.9, "s": 0.3}, {"t": 140, "d": 40, "a": 0.6, "s": 0.3}],
    "level_up": [{"t": 0, "d": 20, "a": 0.4, "s": 0.8}, {"t": 70, "d": 20, "a": 0.6, "s": 0.8}, {"t": 140, "d": 30, "a": 0.9, "s": 0.8}],
    "rumble_light": [{"t": 0, "d": 400, "a": 0.3, "s": 0.0}],
    "rumble_heavy": [{"t": 0, "d": 600, "a": 1.0, "s": 0.0}],
    "notification": [{"t": 0, "d": 40, "a": 0.6, "s": 0.6}, {"t": 100, "d": 40, "a": 0.4, "s": 0.6}],
}
WORDS = {"jump": "jump", "kood": "jump", "coin": "coin", "sikka": "coin", "hit": "hit", "chot": "hit", "damage": "hit",
         "game over": "game_over", "khatam": "game_over", "win": "success", "jeet": "success", "level up": "level_up",
         "warning": "warning", "error": "error", "galti": "error", "button": "button", "tap": "tap", "explosion": "rumble_heavy",
         "dhamaka": "rumble_heavy", "engine": "rumble_light", "heart": "heartbeat", "notification": "notification"}


class HapticsError(G.GameError):
    pass


class GameHaptics(Base):
    __tablename__ = "game_haptics"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gh"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    studio_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    words: Mapped[str] = mapped_column(Text, default="")
    actuator: Mapped[str] = mapped_column(String(20), default="phone_lra")
    patterns: Mapped[dict] = mapped_column(JSON, default=dict)      # {meaning: [events]}
    report: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="draft")    # draft | approved | rejected | failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        GameHaptics.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


# ================================================================ patterns
def clean_events(events: list | None) -> list[dict]:
    out = []
    for e in (events or [])[:24]:
        try:
            out.append({"t": int(min(max(float(e.get("t", 0)), 0), 5000)), "d": int(min(max(float(e.get("d", 10)), 1), 5000)),
                        "a": round(min(max(float(e.get("a", 0.5)), 0.0), 1.0), 2), "s": round(min(max(float(e.get("s", 0.5)), 0.0), 1.0), 2)})
        except (TypeError, ValueError, AttributeError):
            continue
    return sorted(out, key=lambda e: e["t"])


def from_words(words: str) -> dict[str, list[dict]]:
    """Meanings she named -> library patterns (her words are matched, nothing invented). Nothing named = a starter set."""
    w = (words or "").lower()
    got: dict[str, list[dict]] = {}
    for word, lib in WORDS.items():
        if re.search(r"\b" + re.escape(word) + r"\b", w):
            key = lib if word in LIBRARY or lib == word else lib
            got.setdefault(key, [dict(e) for e in LIBRARY[lib]])
    return got or {k: [dict(e) for e in LIBRARY[k]] for k in ("tap", "success", "hit", "game_over")}


def fit(patterns: dict[str, list[dict]], actuator: str) -> tuple[dict[str, list[dict]], int]:
    """Library patterns stretched to what this actuator can play: a pulse shorter than its shortest felt pulse is
    lengthened and the pulses after it move on to keep the 20 ms gap. Only for patterns Hoola picked - numbers she
    typed herself are checked as they are, never changed."""
    act = ACTUATORS.get(actuator, ACTUATORS["phone_lra"])
    out, changed = {}, 0
    for name, ev in patterns.items():
        new, shift, end = [], 0, -10 ** 9
        for e in ev:
            d = max(e["d"], act["min_ms"])
            t = max(e["t"] + shift, end + MIN_GAP_MS) if new else e["t"]
            changed += (d != e["d"]) or (t != e["t"])
            shift = t - e["t"]
            new.append({**e, "t": t, "d": d})
            end = t + d
        out[name] = new
    return out, changed


def envelope(events: list[dict], step_ms: int = 5, total_ms: int = 2000) -> np.ndarray:
    n = total_ms // step_ms
    env = np.zeros(n)
    for e in events:
        a, b = e["t"] // step_ms, min(n, (e["t"] + e["d"]) // step_ms + 1)
        env[a:b] = np.maximum(env[a:b], e["a"])
    return env


def distance(p: list[dict], q: list[dict]) -> float:
    """0 = feel the same, 1 = nothing alike: the 5 ms envelopes (L1 over the longer one) and the pulse counts."""
    a, b = envelope(p), envelope(q)
    span = max(int(np.nonzero(a)[0].max()) if a.any() else 0, int(np.nonzero(b)[0].max()) if b.any() else 0) + 1
    d_env = float(np.abs(a[:span] - b[:span]).sum()) / max(1.0, float(np.maximum(a[:span], b[:span]).sum()))
    d_cnt = abs(len(p) - len(q)) / max(len(p), len(q), 1)
    return round(0.7 * d_env + 0.3 * d_cnt, 3)


def check(patterns: dict[str, list[dict]], actuator: str) -> dict:
    act = ACTUATORS.get(actuator, ACTUATORS["phone_lra"])
    errors, warnings, passed = [], [], []
    rows = {}
    for name, ev in patterns.items():
        if not ev:
            errors.append(f"'{name}' has no pulses")
            continue
        short = [e for e in ev if e["d"] < act["min_ms"]]
        if short:
            errors.append(f"'{name}': a {short[0]['d']} ms pulse is shorter than {act['min_ms']} ms, the shortest a {act['name']} can be felt")
        for x, y in zip(ev, ev[1:]):
            gap = y["t"] - (x["t"] + x["d"])
            if gap < 0:
                errors.append(f"'{name}': two pulses overlap at {y['t']} ms")
                break
            if gap < MIN_GAP_MS:
                errors.append(f"'{name}': a {gap} ms gap - under {MIN_GAP_MS} ms two pulses feel like one")
                break
        length = max(e["t"] + e["d"] for e in ev)
        if length > MAX_FEEDBACK_MS and not name.startswith("rumble"):
            warnings.append(f"'{name}' lasts {length} ms - long for feedback (rumble patterns may be long)")
        mj = sum(e["d"] / 1000 * e["a"] ** 2 * act["mw"] for e in ev)
        rows[name] = {"ms": length, "pulses": len(ev), "energy_mj": round(mj, 2), "per_1000_plays_mwh": round(mj * 1000 / 3600, 2)}
    names = sorted(patterns)
    same = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            dist_ = distance(patterns[a], patterns[b])
            if dist_ < SAME_LIMIT:
                same.append((a, b, dist_))
    for a, b, d_ in same:
        errors.append(f"'{a}' and '{b}' feel the same (difference {d_}, needs {SAME_LIMIT}) - one pattern per meaning")
    if not same and len(names) > 1:
        passed.append(f"all {len(names)} patterns feel different from each other")
    if not errors:
        passed.append(f"every pulse >= {act['min_ms']} ms and every gap >= {MIN_GAP_MS} ms for a {act['name']}")
    passed.append("an off switch and an intensity slider are built in (saved on the player's device)")
    return {"errors": errors, "warnings": warnings, "passed": passed, "rows": rows,
            "battery_note": f"energy = on-time x amplitude^2 x {act['mw']} mW drive (a {act['name']} starting assumption; your datasheet wins)"}


# ================================================================ exports
def ahap(events: list[dict]) -> dict:
    pat = []
    for e in events:
        transient = e["d"] <= 30
        ev = {"Time": round(e["t"] / 1000, 3), "EventType": "HapticTransient" if transient else "HapticContinuous",
              "EventParameters": [{"ParameterID": "HapticIntensity", "ParameterValue": e["a"]},
                                  {"ParameterID": "HapticSharpness", "ParameterValue": e["s"]}]}
        if not transient:
            ev["EventDuration"] = round(e["d"] / 1000, 3)
        pat.append({"Event": ev})
    return {"Version": 1.0, "Pattern": pat}


def ahap_ok(doc: dict) -> list[str]:
    bad = []
    if doc.get("Version") != 1.0 or not isinstance(doc.get("Pattern"), list):
        return ["AHAP needs Version 1.0 and a Pattern list"]
    for i, p in enumerate(doc["Pattern"]):
        ev = (p or {}).get("Event") or {}
        if ev.get("EventType") not in ("HapticTransient", "HapticContinuous"):
            bad.append(f"event {i}: EventType")
        if not isinstance(ev.get("Time"), (int, float)) or ev["Time"] < 0:
            bad.append(f"event {i}: Time")
        if ev.get("EventType") == "HapticContinuous" and not (0 < float(ev.get("EventDuration", 0)) <= 30):
            bad.append(f"event {i}: EventDuration")
        ids = {x.get("ParameterID"): x.get("ParameterValue") for x in ev.get("EventParameters", [])}
        for k in ("HapticIntensity", "HapticSharpness"):
            if not (0 <= float(ids.get(k, -1)) <= 1):
                bad.append(f"event {i}: {k}")
    return bad


def android_waveform(events: list[dict]) -> tuple[list[int], list[int]]:
    """VibrationEffect.createWaveform(timings, amplitudes, -1): alternating off / on segments, amplitudes 0-255."""
    timings, amps, t = [], [], 0
    for e in events:
        timings.append(max(0, e["t"] - t))
        amps.append(0)
        timings.append(e["d"])
        amps.append(max(1, int(round(e["a"] * 255))))
        t = e["t"] + e["d"]
    return timings, amps


def kotlin(patterns: dict[str, list[dict]]) -> str:
    rows = []
    for name, ev in patterns.items():
        tm, am = android_waveform(ev)
        rows.append(f'        "{name}" to (longArrayOf({", ".join(f"{x}L" for x in tm)}) to intArrayOf({", ".join(map(str, am))})),')
    return ("// Hoola haptics for Android (made by Hoola from the approved patterns). Needs <uses-permission "
            "android:name=\"android.permission.VIBRATE\"/>.\npackage hoola.haptics\n\nimport android.content.Context\n"
            "import android.os.Build\nimport android.os.VibrationEffect\nimport android.os.Vibrator\nimport android.os.VibratorManager\n\n"
            "object HoolaHaptics {\n    var enabled = true          // the player's off switch - keep it in your settings screen\n"
            "    var intensity = 1.0f        // 0..1 slider\n    private val PATTERNS = mapOf(\n" + "\n".join(rows) + "\n    )\n\n"
            "    fun play(ctx: Context, name: String) {\n        if (!enabled || intensity <= 0f) return\n"
            "        val (timings, amps) = PATTERNS[name] ?: return\n"
            "        val v: Vibrator = if (Build.VERSION.SDK_INT >= 31) (ctx.getSystemService(VibratorManager::class.java)).defaultVibrator\n"
            "            else @Suppress(\"DEPRECATION\") ctx.getSystemService(Vibrator::class.java)\n"
            "        if (!v.hasVibrator()) return\n"
            "        val scaled = IntArray(amps.size) { i -> if (amps[i] == 0) 0 else (amps[i] * intensity).toInt().coerceIn(1, 255) }\n"
            "        if (v.hasAmplitudeControl()) v.vibrate(VibrationEffect.createWaveform(timings, scaled, -1))\n"
            "        else v.vibrate(VibrationEffect.createWaveform(timings, -1))\n    }\n}\n")


def swift(patterns: dict[str, list[dict]]) -> str:
    return ("// Hoola haptics for iPhone (made by Hoola from the approved patterns): plays the .ahap files in your bundle.\n"
            "import CoreHaptics\nimport UIKit\n\nfinal class HoolaHaptics {\n    static let shared = HoolaHaptics()\n"
            "    var enabled = true      // the player's off switch - keep it in your settings screen\n"
            "    var intensity: Float = 1.0\n    private var engine: CHHapticEngine?\n\n"
            "    init() { if CHHapticEngine.capabilitiesForHardware().supportsHaptics { engine = try? CHHapticEngine(); try? engine?.start() } }\n\n"
            "    func play(_ name: String) {\n        guard enabled, intensity > 0 else { return }\n"
            "        guard let engine = engine, let url = Bundle.main.url(forResource: name, withExtension: \"ahap\") else {\n"
            "            UIImpactFeedbackGenerator(style: .medium).impactOccurred(intensity: CGFloat(intensity)); return }\n"
            "        try? engine.playPattern(from: url)\n    }\n}\n// Patterns: " + ", ".join(sorted(patterns)) + "\n")


def drv2605_c(patterns: dict[str, list[dict]], lra: bool) -> str:
    """Real-time playback (RTP) driver for a TI DRV2605 over I2C: each pattern is a list of (amplitude, ms) steps the
    loop writes to the RTP register. Arduino / ESP32 Wire API."""
    tables = []
    for name, ev in patterns.items():
        steps, t = [], 0
        for e in ev:
            if e["t"] > t:
                steps.append((0, e["t"] - t))
            steps.append((int(round(e["a"] * 127)), e["d"]))
            t = e["t"] + e["d"]
        c = re.sub(r"[^a-z0-9_]", "_", name)
        tables.append(f"static const HoolaStep P_{c}[] = {{ " + ", ".join(f"{{{a}, {d}}}" for a, d in steps) + " };")
    names = [re.sub(r"[^a-z0-9_]", "_", n) for n in patterns]
    index = ",\n".join(f'  {{"{n}", P_{n}, sizeof(P_{n}) / sizeof(P_{n}[0])}}' for n in names)
    return f"""// Hoola haptics driver for a TI DRV2605 ({'LRA' if lra else 'ERM'}) - made by Hoola from the approved patterns.
// Real-time playback: amplitude 0-127 written to the RTP register for each step. Check the motor's datasheet
// (rated / overdrive voltage) and run the DRV2605 auto-calibration once before use.
#include <Arduino.h>
#include <Wire.h>
#include <string.h>

#define DRV2605_ADDR 0x5A
#define REG_MODE 0x01
#define REG_RTP 0x02
#define REG_LIBRARY 0x03
#define REG_FEEDBACK 0x1A
#define REG_CONTROL3 0x1D
#define MODE_RTP 0x05

typedef struct {{ uint8_t amp; uint16_t ms; }} HoolaStep;
typedef struct {{ const char *name; const HoolaStep *steps; size_t n; }} HoolaPattern;

{chr(10).join(tables)}

static const HoolaPattern PATTERNS[] = {{
{index}
}};

static bool hoola_enabled = true;      // the user's off switch - wire it to your settings
static uint8_t hoola_intensity = 255;  // 0-255 scale on top of each pattern

static void drv_write(uint8_t reg, uint8_t val) {{
  Wire.beginTransmission(DRV2605_ADDR);
  Wire.write(reg);
  Wire.write(val);
  Wire.endTransmission();
}}

void hoola_haptics_begin(void) {{
  Wire.begin();
  drv_write(REG_MODE, 0x00);                         // out of standby
  drv_write(REG_FEEDBACK, {'0xB6' if lra else '0x36'});  // {'LRA' if lra else 'ERM'} mode
  drv_write(REG_LIBRARY, {'6' if lra else '1'});            // {'LRA library' if lra else 'ERM library A'}
  drv_write(REG_CONTROL3, 0xA0);                     // RTP data unsigned
  drv_write(REG_MODE, MODE_RTP);
}}

void hoola_haptics_set(bool enabled, uint8_t intensity) {{ hoola_enabled = enabled; hoola_intensity = intensity; }}

bool hoola_haptics_play(const char *name) {{
  if (!hoola_enabled || hoola_intensity == 0) return false;
  for (size_t i = 0; i < sizeof(PATTERNS) / sizeof(PATTERNS[0]); i++) {{
    if (strcmp(PATTERNS[i].name, name) != 0) continue;
    for (size_t k = 0; k < PATTERNS[i].n; k++) {{
      drv_write(REG_RTP, (uint8_t)((PATTERNS[i].steps[k].amp * (uint16_t)hoola_intensity) / 255));
      delay(PATTERNS[i].steps[k].ms);
    }}
    drv_write(REG_RTP, 0);
    return true;
  }}
  return false;
}}
"""


STUB_H = {"Arduino.h": "#pragma once\n#include <stdint.h>\n#include <stddef.h>\n#include <stdbool.h>\nvoid delay(unsigned long ms);\n",
          "Wire.h": "#pragma once\n#include <stdint.h>\ntypedef struct { void (*begin)(void); void (*beginTransmission)(uint8_t); "
                    "unsigned (*write)(uint8_t); uint8_t (*endTransmission)(void); } TwoWire;\nextern TwoWire Wire;\n"}


def compile_c(code: str) -> dict:
    """gcc -fsyntax-only against stand-in Arduino / Wire headers (the real ones are C++; this proves the driver's own
    C is valid). No compiler = NOT ASSESSED."""
    cc = shutil.which("gcc") or shutil.which("cc") or shutil.which("clang")
    if not cc:
        return {"status": "NOT ASSESSED", "note": "no C compiler on this server"}
    with tempfile.TemporaryDirectory() as d:
        for n, txt in STUB_H.items():
            Path(d, n).write_text(txt)
        src = code.replace("Wire.begin()", "Wire.begin()").replace("Wire.", "Wire.")
        Path(d, "drv.c").write_text(src)
        try:
            p = subprocess.run([cc, "-std=c11", "-Wall", "-Werror", "-fsyntax-only", "-I", d, str(Path(d, "drv.c"))],
                               capture_output=True, text=True, timeout=60)
        except Exception as e:                          # noqa: BLE001
            return {"status": "NOT ASSESSED", "note": str(e)[:200]}
    return {"status": "PASS" if p.returncode == 0 else "FAIL", "note": (p.stderr or "").strip()[-400:], "compiler": Path(cc).name}


def envelope_png(patterns: dict[str, list[dict]]) -> bytes:
    from PIL import Image, ImageDraw
    names = sorted(patterns)
    w, row = 640, 46
    im = Image.new("RGB", (w, row * max(1, len(names)) + 10), (250, 250, 248))
    d = ImageDraw.Draw(im)
    for i, n in enumerate(names):
        y0 = 8 + i * row
        d.text((8, y0 + 14), n[:16], fill=(40, 40, 40))
        for e in patterns[n]:
            x0 = 130 + int(e["t"] / 1500 * (w - 140))
            x1 = 130 + int(min(1500, e["t"] + e["d"]) / 1500 * (w - 140))
            h = int(e["a"] * (row - 14))
            d.rectangle([x0, y0 + row - 8 - h, max(x0 + 1, x1), y0 + row - 8], fill=(124, 92, 255))
        d.line([130, y0 + row - 8, w - 10, y0 + row - 8], fill=(200, 200, 200))
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def kit_zip(patterns: dict[str, list[dict]], actuator: str) -> tuple[bytes, dict]:
    files: dict[str, str | bytes] = {}
    bad = []
    for n, ev in patterns.items():
        doc = ahap(ev)
        bad += [f"{n}: {b}" for b in ahap_ok(doc)]
        files[f"ios/{n}.ahap"] = json.dumps(doc, indent=2)
    files["ios/HoolaHaptics.swift"] = swift(patterns)
    files["android/HoolaHaptics.kt"] = kotlin(patterns)
    c = drv2605_c(patterns, lra=not actuator.endswith("erm"))
    files["device/hoola_haptics_drv2605.c"] = c
    files["patterns.json"] = json.dumps(patterns, indent=2)
    files["patterns.png"] = envelope_png(patterns)
    for n, ev in patterns.items():
        tm, am = android_waveform(ev)
        if len(tm) != len(am) or any(t < 0 for t in tm) or any(not 0 <= a <= 255 for a in am):
            bad.append(f"{n}: android waveform")
    comp = compile_c(c)
    files["README.txt"] = ("Hoola haptics kit\n\nios/: Core Haptics .ahap files + HoolaHaptics.swift (iPhone 8 and newer have the Taptic "
                           "Engine).\nandroid/: HoolaHaptics.kt (VibrationEffect waveforms; needs the VIBRATE permission).\ndevice/: a "
                           "DRV2605 driver (Arduino / ESP32).\nEvery file has the player's off switch and intensity. The browser "
                           "build vibrates on Android Chrome only (iPhone browsers have no vibration).\n")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n, v in files.items():
            z.writestr(n, v)
    return buf.getvalue(), {"ahap_errors": bad, "drv2605_compile": comp}


# ================================================================ store
def _root(tenant: str) -> Path:
    return G.root() / (re.sub(r"[^\w-]", "_", tenant)[:64] or "t") / "haptics"


def _studio(tenant: str, ref: str):
    from . import studio as S
    with session() as s:
        r = S._studio(s, tenant, ref)
        s.expunge(r)
    return r


def _get(s, tenant: str, ref: str) -> GameHaptics:
    ref = str(ref or "").strip()
    q = select(GameHaptics).where(GameHaptics.tenant_id == tenant)
    r = s.scalars(q.where(GameHaptics.id == ref)).first() or s.scalars(q.where(GameHaptics.number == ref.upper())).first()
    if r is None:
        raise HapticsError("This haptics set was not found (give H-001).")
    return r


def _sig(name: str) -> str:
    import hmac as _h
    from ..config import get_settings
    key = (getattr(get_settings(), "api_key", "") or "hoola-haptics").encode()
    return _h.new(key, f"haptics:{name}".encode(), "sha256").hexdigest()[:16]


KFILES = ("kit.zip", "patterns.png")


def file_url(r: GameHaptics, name: str) -> str:
    return f"/api/gamedesk/haptics/{r.id}/file/{name}?sig={_sig(r.id + name)}"


def haptics_file(hid: str, name: str, sig: str) -> Path | None:
    import hmac as _h
    if not re.fullmatch(r"gh_[A-Za-z0-9_-]{4,40}", str(hid or "")) or name not in KFILES or not _h.compare_digest(_sig(hid + name), str(sig or "")):
        return None
    ensure_table()
    with session() as s:
        r = s.get(GameHaptics, hid)
        if r is None:
            return None
        s.expunge(r)
    p = _root(r.tenant_id) / r.id / name
    return p if p.is_file() else None


def view(r: GameHaptics) -> dict[str, Any]:
    d = _root(r.tenant_id) / r.id
    return {"id": r.id, "number": r.number, "status": r.status, "words": r.words, "actuator": r.actuator,
            "actuator_name": ACTUATORS.get(r.actuator, {}).get("name", r.actuator), "patterns": r.patterns or {},
            "report": r.report or {}, "studio_id": r.studio_id, "library": sorted(LIBRARY),
            "files": {n: file_url(r, n) for n in KFILES if (d / n).is_file()},
            "at": r.created_at.isoformat() if r.created_at else ""}


def make(tenant: str, words: str = "", patterns: dict | None = None, actuator: str = "phone_lra", studio: str = "") -> dict[str, Any]:
    """Her meanings -> patterns -> checked + the kit written. A set with an error is saved as failed (named)."""
    ensure_table()
    if actuator not in ACTUATORS:
        raise HapticsError("actuator = " + " | ".join(ACTUATORS))
    sid = _studio(tenant, studio).id if studio else ""
    mine = isinstance(patterns, dict) and bool(patterns)
    pats = {re.sub(r"[^a-z0-9_]", "", str(k).lower())[:24] or "p": clean_events(v)
            for k, v in (patterns if mine else from_words(words)).items()}
    moved = 0
    if not mine:
        pats, moved = fit(pats, actuator)
    rep = check(pats, actuator)
    if moved:
        rep["passed"].append(f"{moved} pulses lengthened / moved so a {ACTUATORS[actuator]['name']} can play them")
    data, kit = kit_zip(pats, actuator)
    rep["kit"] = kit
    if kit["ahap_errors"]:
        rep["errors"] = rep["errors"] + kit["ahap_errors"]
    if kit["drv2605_compile"]["status"] == "FAIL":
        rep["errors"] = rep["errors"] + ["the DRV2605 driver did not compile: " + kit["drv2605_compile"]["note"][:200]]
    rep["verdict"] = "FAIL" if rep["errors"] else "PASS"
    with session() as s:
        n = len(s.scalars(select(GameHaptics.id).where(GameHaptics.tenant_id == tenant)).all()) + 1
        r = GameHaptics(tenant_id=tenant, studio_id=sid, number=f"H-{n:03d}", words=(words or "")[:600], actuator=actuator,
                        patterns=pats, report=rep, status="failed" if rep["errors"] else "draft")
        s.add(r)
        s.flush()
        s.expunge(r)
    d = _root(tenant) / r.id
    d.mkdir(parents=True, exist_ok=True)
    (d / "kit.zip").write_bytes(data)
    (d / "patterns.png").write_bytes(envelope_png(pats))
    return view(r)


def approve(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _get(s, tenant, ref)
        if r.status != "draft":
            raise HapticsError("Only a haptics set that PASSED can be OKed.")
        for o in s.scalars(select(GameHaptics).where(GameHaptics.tenant_id == tenant, GameHaptics.studio_id == r.studio_id,
                                                     GameHaptics.status == "approved")).all():
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


def sets(tenant: str, studio: str = "") -> list[dict[str, Any]]:
    ensure_table()
    sid = _studio(tenant, studio).id if studio else None
    with session() as s:
        q = select(GameHaptics).where(GameHaptics.tenant_id == tenant)
        if sid is not None:
            q = q.where(GameHaptics.studio_id == sid)
        rows = s.scalars(q.order_by(GameHaptics.created_at.desc())).all()[:30]
        for r in rows:
            s.expunge(r)
    return [view(r) for r in rows]


def get(tenant: str, ref: str) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        r = _get(s, tenant, ref)
        s.expunge(r)
    return view(r)


GD = '''extends Node
# HoolaHaptics (an autoload): her game's vibration patterns, one per meaning, CHECKED by Hoola. Every player can turn
# them off or down (saved in the game's own user:// file). Written by Hoola Studio; do not edit.
const PATTERNS := __P__
const SAVE := "user://hoola_haptics.cfg"
var enabled := true
var intensity := 1.0

func _ready() -> void:
	var cf := ConfigFile.new()
	if cf.load(SAVE) == OK:
		enabled = bool(cf.get_value("haptics", "enabled", true))
		intensity = clampf(float(cf.get_value("haptics", "intensity", 1.0)), 0.0, 1.0)

func set_enabled(on: bool) -> void:
	enabled = on
	_save()

func set_intensity(v: float) -> void:
	intensity = clampf(v, 0.0, 1.0)
	_save()

func _save() -> void:
	var cf := ConfigFile.new()
	cf.set_value("haptics", "enabled", enabled)
	cf.set_value("haptics", "intensity", intensity)
	cf.save(SAVE)

func names() -> Array:
	return PATTERNS.keys()

func play(name: String) -> void:
	# phone (Android browser / app) + any game controller; iPhone browsers have no vibration
	if not enabled or intensity <= 0.0 or not PATTERNS.has(name):
		return
	var t := 0
	for e in PATTERNS[name]:
		var wait_ms := int(e["t"]) - t
		if wait_ms > 0:
			await get_tree().create_timer(wait_ms / 1000.0).timeout
		var amp := clampf(float(e["a"]) * intensity, 0.0, 1.0)
		Input.vibrate_handheld(int(e["d"]), amp)
		for pad in Input.get_connected_joypads():
			Input.start_joy_vibration(pad, amp * float(e["s"]), amp * (1.0 - float(e["s"]) * 0.5), float(e["d"]) / 1000.0)
		t = int(e["t"])
'''


def gd(patterns: dict) -> str:
    from .bible import _gd
    return GD.replace("__P__", _gd(patterns))


def for_game(tenant: str, game_id: str) -> tuple[str, dict[str, Path]] | None:
    from . import studio as S
    ensure_table()
    with session() as s:
        st = s.scalars(select(S.GameStudio).where(S.GameStudio.tenant_id == tenant, S.GameStudio.game_id == game_id)).first()
        if st is None:
            return None
        r = s.scalars(select(GameHaptics).where(GameHaptics.tenant_id == tenant, GameHaptics.studio_id == st.id,
                                                GameHaptics.status == "approved").order_by(GameHaptics.created_at.desc())).first()
        if r is None:
            return None
        s.expunge(r)
    return gd(r.patterns), {}


def apply(tenant: str, studio: str) -> dict[str, Any]:
    st = _studio(tenant, studio)
    if for_game(tenant, st.game_id) is None:
        raise HapticsError("No approved haptics set; OK one first.")
    try:
        from . import bible as B
        bv = B.view(tenant, st.id)["version"]
    except Exception:                                   # noqa: BLE001
        bv = 0
    G.data_build(tenant, st.game_id, bv, words="Haptics into the game")
    return {"ok": True, "say": "Haptics are going into the game (a rebuild is running)."}
