"""Bluetooth HID remote: the phone registers as a Bluetooth keyboard + media remote (Android BluetoothHidDevice,
API 28+) that the TV pairs with once. The server turns intents ("volume 3 up", "type arijit") into HID usages; the
phone just sends the reports.

Usage IDs are from the USB HID Usage Tables (Consumer page 0x0C, Keyboard page 0x07).
"""
from __future__ import annotations

import re

from typing import Any

# Consumer page (16-bit usages)
CONSUMER = {
    "POWER": 0x30, "SLEEP": 0x32, "MENU": 0x40, "INFO": 0x60, "CAPTIONS": 0x61, "TV": 0x89, "GUIDE": 0x8D,
    "EXIT": 0x94, "VOL_UP": 0xE9, "VOL_DOWN": 0xEA, "MUTE": 0xE2, "PLAY_PAUSE": 0xCD, "PLAY": 0xB0, "PAUSE": 0xB1,
    "RECORD": 0xB2, "NEXT": 0xB5, "PREVIOUS": 0xB6, "STOP": 0xB7, "FAST_FORWARD": 0xB3, "REWIND": 0xB4,
    "CHANNEL_UP": 0x9C, "CHANNEL_DOWN": 0x9D, "SEARCH": 0x221, "HOME": 0x223, "BACK": 0x224,
}
ALIASES = {"VOLUME_UP": "VOL_UP", "VOLUP": "VOL_UP", "VOLUME_DOWN": "VOL_DOWN", "VOLDOWN": "VOL_DOWN", "SELECT": "OK",
           "CENTER": "OK", "ENTER": "OK", "DPAD_UP": "UP", "DPAD_DOWN": "DOWN", "DPAD_LEFT": "LEFT", "DPAD_RIGHT": "RIGHT",
           "PLAYPAUSE": "PLAY_PAUSE", "FF": "FAST_FORWARD", "REW": "REWIND", "PREV": "PREVIOUS", "CH_UP": "CHANNEL_UP",
           "CH_DOWN": "CHANNEL_DOWN", "DELETE": "BACKSPACE", "DEL": "BACKSPACE", "OFF": "POWER", "ON": "POWER"}
# Keyboard page
KEYBOARD = {"OK": 0x28, "ESC": 0x29, "BACKSPACE": 0x2A, "TAB": 0x2B, "SPACE": 0x2C,
            "RIGHT": 0x4F, "LEFT": 0x50, "DOWN": 0x51, "UP": 0x52, "PAGE_UP": 0x4B, "PAGE_DOWN": 0x4E,
            **{str(d): (0x27 if d == 0 else 0x1D + d) for d in range(10)}}
TV_KEYS = sorted(set(CONSUMER) | set(KEYBOARD))
SHIFT = 0x02
_PUNCT = {"-": (0x2D, 0), "_": (0x2D, SHIFT), "=": (0x2E, 0), "+": (0x2E, SHIFT), ".": (0x37, 0), ",": (0x36, 0),
          "/": (0x38, 0), "?": (0x38, SHIFT), "'": (0x34, 0), "!": (0x1E, SHIFT), "&": (0x24, SHIFT), ":": (0x33, SHIFT)}
MAX_TEXT = 60


def char_usage(ch: str) -> tuple[int, int] | None:
    if "a" <= ch <= "z":
        return 0x04 + ord(ch) - ord("a"), 0
    if "A" <= ch <= "Z":
        return 0x04 + ord(ch) - ord("A"), SHIFT
    if "1" <= ch <= "9":
        return 0x1E + ord(ch) - ord("1"), 0
    if ch == "0":
        return 0x27, 0
    if ch == " ":
        return 0x2C, 0
    return _PUNCT.get(ch)


def norm_key(key: str) -> str:
    k = str(key).strip().upper().replace(" ", "_").replace("-", "_")
    return ALIASES.get(k, k)


def key_op(key: str, repeat: int = 1, hold_ms: int = 0) -> dict[str, Any]:
    k = norm_key(key)
    try:
        repeat = max(1, min(int(repeat or 1), 30))
    except (TypeError, ValueError):
        repeat = 1
    hold = max(0, min(int(hold_ms or 0), 3000))
    if k in CONSUMER:
        op = {"op": "consumer", "usage": CONSUMER[k], "repeat": repeat, "label": k}
    elif k in KEYBOARD:
        op = {"op": "keys", "reports": [[0, KEYBOARD[k]]] * repeat, "label": k}
    else:
        raise ValueError(f"Unknown TV key {key}. Keys: {', '.join(TV_KEYS)}")
    if hold:
        op["hold_ms"] = hold
    return op


def number_ops(number: str, enter: bool = True) -> list[dict[str, Any]]:
    """A channel number typed on the remote's digits (e.g. 101), then OK."""
    digits = "".join(ch for ch in str(number) if ch.isdigit())[:6]
    if not digits:
        raise ValueError("Channel number should be digits, e.g. 101")
    ops = [{"op": "keys", "reports": [[0, KEYBOARD[d]] for d in digits], "label": f"channel {digits}"}]
    if enter:
        ops += [{"op": "wait", "ms": 600}, key_op("OK")]
    return ops


def text_op(text: str) -> tuple[dict[str, Any], list[str]]:
    """Keyboard reports for typing text into a TV search box. Characters a TV keyboard can't type are skipped."""
    reports, skipped = [], []
    for ch in text[:MAX_TEXT]:
        u = char_usage(ch)
        if u is None:
            skipped.append(ch)
            continue
        reports.append([u[1], u[0]])
    return {"op": "keys", "reports": reports, "typing": True, "label": f"type '{text[:MAX_TEXT]}'"}, skipped


# DIAL (Discovery And Launch) app names registered for smart TVs. YouTube and Netflix are in the public DIAL registry.
DIAL_APPS = {"youtube": "YouTube", "netflix": "Netflix"}
# Apps without a DIAL name are opened with the TV's search: SEARCH, type the name, ENTER.
SEARCH_OPEN = {"hotstar": "hotstar", "jiohotstar": "jiohotstar", "prime video": "prime video", "zee5": "zee5",
               "sonyliv": "sonyliv", "jiocinema": "jiohotstar", "spotify": "spotify", "youtube music": "youtube music"}


def open_app_ops(app: str) -> list[dict[str, Any]]:
    a = app.strip().lower()
    if a in DIAL_APPS:
        return [{"op": "dial_launch", "app": DIAL_APPS[a], "fallback": search_ops(a)}]
    name = SEARCH_OPEN.get(a, a)
    return search_ops(name)


def search_ops(query: str) -> list[dict[str, Any]]:
    t, _ = text_op(query)
    return [key_op("SEARCH"), {"op": "wait", "ms": 1500}, t, {"op": "wait", "ms": 300}, key_op("OK")]


def youtube_video_ops(video_id: str, title: str = "") -> list[dict[str, Any]]:
    """v0.125 Play one YouTube video on the TV: DIAL launch of the YouTube app with v=<id> (Android / Google TV, Samsung,
    LG, Fire TV all take it); if the TV has no DIAL, open YouTube through the TV's search and look the title up."""
    if not re.fullmatch(r"[\w-]{11}", video_id or ""):
        raise ValueError("bad video id")
    fallback = search_ops("youtube") + [{"op": "wait", "ms": 2500}] + (search_ops(title[:60]) if title else [])
    return [{"op": "dial_launch", "app": DIAL_APPS["youtube"], "body": f"v={video_id}", "fallback": fallback}]


APP_LABELS = {"youtube": "YouTube", "netflix": "Netflix", "hotstar": "JioHotstar", "jiohotstar": "JioHotstar",
              "prime video": "Prime Video", "zee5": "ZEE5", "sonyliv": "SonyLIV", "spotify": "Spotify",
              "youtube music": "YouTube Music"}
_KEY_WORDS = {"POWER": "Switched power on {tv}", "VOL_UP": "Volume up on {tv}", "VOL_DOWN": "Volume down on {tv}",
              "MUTE": "Muted {tv}", "HOME": "Went to the home screen on {tv}", "BACK": "Went back on {tv}",
              "PLAY_PAUSE": "Play/pause on {tv}", "CHANNEL_UP": "Next channel on {tv}", "CHANNEL_DOWN": "Previous channel on {tv}"}


def keys_message(keys: list[str], tv: str) -> str:
    if len(keys) == 1 and keys[0].upper() in _KEY_WORDS:
        return _KEY_WORDS[keys[0].upper()].format(tv=tv) + "."
    return f"Pressed {', '.join(k.upper() for k in keys)} on {tv}."
