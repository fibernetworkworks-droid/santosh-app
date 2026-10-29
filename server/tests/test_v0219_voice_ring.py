"""v0.219.0 VOICE RING - Wave 2 of the voice-to-voice PERFECT plan.

The server half has been live since v0.214 (NEVER SILENT): kaam_followup publishes kind=voice_ring,
push.on_event gates it hard (tenant-tz quiet hours 22-8, a small daily budget, never while a call is
live on that chat) and FCM carries it as a RAW data push. The setting stayed OFF because the phone
did not know the kind. Wave 2 teaches it:

1. SantoshPush.kt learns "voice_ring": skip when the app is open (the live stream takes it), refuse
   stale and repeated pushes, hand the mic over from the wake listener, and ring - an incoming-call
   style full-screen alert that opens Hoola with the SAME santosh.WAKE action the wake word uses, so
   over-the-lock-screen, auto-call and mic handover are the code that already works.
2. state.dart answers the live stream itself: a fresh (never replayed) voice_ring event wakes the app
   into the same auto-call.
3. The setting flips ON. Old APKs keep working: an old SantoshPush gets a data push with no body and
   shows nothing, exactly like today.

The phone is still not an alarm clock: the gates are re-pinned here so the flip did not relax them.
"""
import os
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

ROOT = Path(__file__).resolve().parents[2]


def _kt(name: str) -> str:
    return (ROOT / "tool" / "android" / "kotlin" / name).read_text()


# ---------------- 1. the setting flips ON, the gates stay exactly as hard ----------------

def test_ring_setting_is_on():
    from app.config import Settings
    s = Settings()
    assert s.voice_ring is True                      # the promise kept: ON when the native side learns the kind
    assert s.voice_ring_max_day == 2                 # the phone is still not an alarm clock
    assert s.voice_ring_quiet == "22-8"              # quiet hours unchanged


def test_ring_gates_survive_the_flip(monkeypatch):
    import app.push as push
    import app.voice as v
    push._RING_DAY.clear()
    now_h = __import__("datetime").datetime.now(__import__("zoneinfo").ZoneInfo("Asia/Kolkata")).hour
    monkeypatch.setattr(v, "ACTIVE", {})
    monkeypatch.setattr(push, "get_settings", lambda: types.SimpleNamespace(
        voice_ring=True, voice_ring_max_day=2, voice_ring_quiet=f"{now_h}-{(now_h + 1) % 24}"))
    assert push._ring_allowed("default", "c1") is False          # quiet hours hold even with the flag on
    # a wrap-around window that surely EXCLUDES the current hour: the ring goes through until the budget is spent
    outside = f"{(now_h + 1) % 24}-{now_h}"
    monkeypatch.setattr(push, "get_settings", lambda: types.SimpleNamespace(
        voice_ring=True, voice_ring_max_day=2, voice_ring_quiet=outside))
    assert push._ring_allowed("default", "c1") is True
    assert push._ring_allowed("default", "c1") is True
    assert push._ring_allowed("default", "c1") is False          # the daily budget is spent (2)
    push._RING_DAY.clear()
    monkeypatch.setattr(v, "ACTIVE", {"c1": [("loop", "call")]})
    assert push._ring_allowed("default", "c1") is False          # never ring a phone already talking
    push._RING_DAY.clear()


def test_ring_off_still_means_off(monkeypatch):
    import app.push as push
    push._RING_DAY.clear()
    monkeypatch.setattr(push, "get_settings", lambda: types.SimpleNamespace(
        voice_ring=False, voice_ring_max_day=2, voice_ring_quiet="22-8"))
    assert push._ring_allowed("default", "c1") is False          # the kill switch outlives the flip
    push._RING_DAY.clear()


# ---------------- 2. the phone's contract: the push is raw data the phone runs itself ----------------

def test_ring_push_is_raw_and_carries_the_reason():
    import app.push as push
    assert "voice_ring" in push.RAW_KINDS and "voice_ring" in push.PUSH_KINDS
    body = push.build("tok", {"kind": "voice_ring", "id": "kf9", "at": "",
                              "payload": {"reason": "kaam done: sheet", "ref": "kf9", "conv": "c"}})
    data = body["message"]["data"]
    assert data["kind"] == "voice_ring" and "sheet" in data["payload"]
    assert "title" not in data and "body" not in data            # raw: no notification text, the phone rings itself
    assert body["message"]["android"]["priority"] == "HIGH"
    assert body["message"]["android"]["ttl"] == "600s"           # a stale ring expires in ten minutes


def test_kaam_followup_publishes_the_ring():
    src = (ROOT / "server" / "app" / "kaam_followup.py").read_text()
    assert "settings.voice_ring" in src and '"kind": "voice_ring"' in src
    assert '"reason"' in src and '"ref"' in src                  # the reason rides to the lock screen


# ---------------- 3. the native shell: SantoshPush learns the kind ----------------

def test_santosh_push_learns_voice_ring():
    src = _kt("SantoshPush.kt")
    assert '"voice_ring" ->' in src
    assert "MainActivity.visible" in src.split('"voice_ring" ->')[1].split("else ->")[0]
    assert "Actions.tooOld" in src.split('"voice_ring" ->')[1].split("else ->")[0]      # stale never rings
    assert 'Store.claim(this, "ring$rid")' in src                                       # a retry never double-rings
    assert "WakeService.pauseFor" in src.split('"voice_ring" ->')[1].split("else ->")[0]  # mic hands to the call
    assert 'Notify.ring(this, payload.optString("reason"))' in src


def test_ring_enters_through_the_wake_path():
    n = _kt("Notify.kt")
    ring = n.split("fun ring(")[1].split("fun cancel(")[0]
    assert "WakeService.ACTION_WAKE" in ring            # the EXACT action "Hey Santosh" opens the app with
    assert ".setFullScreenIntent(pi, true)" in ring     # over the lock screen
    assert "Notification.CATEGORY_CALL" in ring
    assert "santosh_ring" in n                          # its own channel: she controls the ring, not the messages
    assert "CH_RING" in n and '"santosh_ring"' in n
    assert "setTimeoutAfter" in ring                    # an unanswered ring fades, it never nags


# ---------------- 4. the app answers the live stream too ----------------

def test_state_dart_auto_calls_on_a_fresh_ring():
    src = (ROOT / "lib" / "state.dart").read_text()
    case = src.split("case 'voice_ring':")[1].split("break;")[0]
    assert "!_replaying" in case                        # history replay never rings
    assert "wake(locked: false)" in case                # the same auto-call "Hey Santosh" uses


# ---------------- 5. the version ----------------

def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.227.0"
