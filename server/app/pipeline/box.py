"""P1 THE BOX, one part (plan sections 3-5): her ask -> kind + language -> level -> model + two backups.

`choose_for(text, ...)` is what P2 calls for a one-part message; here it only answers (the preview route + the CLI).
Nothing in Hoola routes a message through it yet - `pipeline_on` stays OFF until P7 (plan section 10).

CLI (vps-ops `pipeline_try`): `python -m app.pipeline.box ["her words" ...]` - with no words, a fixed set of asks.
"""
from __future__ import annotations

import sys
import threading
import time
from typing import Any

from . import choose as C
from . import detect as D
from . import levels as L
from . import store

_STICKY: dict[tuple[str, str, str], dict] = {}     # (chat, kind, level) -> {id, at}
_LOCK = threading.Lock()


def remember(chat: str, kind: str, level: str, model_id: str, now: float | None = None) -> None:
    """5.1: the model a chat used for this kind + level (kept 30 minutes while healthy)."""
    if chat and model_id:
        with _LOCK:
            _STICKY[(chat, kind, level)] = {"id": model_id, "at": now if now is not None else time.time()}


def recall(chat: str, kind: str, level: str, now: float | None = None) -> dict | None:
    with _LOCK:
        s = _STICKY.get((chat, kind, level))
    now = now if now is not None else time.time()
    if s and now - s["at"] <= C.STICKY_S:
        return s
    return None


def choose_for(text: str, *, attachments: list[dict] | None = None, surface: str = "chat", doc: dict | None = None,
               her_level: str = "", her_ultra: bool = False, pin: str = "", call_waiting: bool = False,
               size_tokens: int = 0, health: dict | None = None, chat: str = "", floor: str = "",
               now: float | None = None) -> dict[str, Any]:
    """One part, end to end. `doc` = the tables copy this message holds (default: the current tables)."""
    doc = C.snapshot(doc if doc is not None else store.read_current())
    now = now if now is not None else time.time()
    d = D.kind(text, attachments, surface=surface, input_words=int(size_tokens * 0.75))
    sig = L.for_kind(d["kind"], L.signals(text, parts=d["parts"], input_words=int(size_tokens * 0.75)))
    lv = L.level_for(d["kind"], sig, language=d["language"], her_level=her_level, her_ultra=her_ultra,
                     call_waiting=call_waiting or surface == "call", floor=floor)
    need = {"kind": d["kind"], "level": lv["level"], "language": d["language"], "surface": surface, "pin": pin,
            "size_tokens": size_tokens}
    pick = C.choose(doc, need, health=health, sticky=recall(chat, d["kind"], lv["level"], now) if chat else None,
                    now=now)
    return {"kind": d["kind"], "language": d["language"], "parts": d["parts"],
            "several_parts": d["parts"] > 1, "kind_why": d["why"], "level": lv["level"], "level_why": lv["why"],
            "signals": lv["signals"], **{k: pick[k] for k in ("model", "backups", "table", "read_on")},
            "level_used": pick.get("level_used"), "choose_why": pick["why"]}


SAMPLES = [
    ("hi", "chat"), ("Kal ka mausam kaisa rahega Akola mein?", "chat"),
    ("Is photo ka background white kar do", "chat"), ("Ek Diwali sale ka poster banao", "chat"),
    ("Mere customers ko GST invoice ka reminder bhej do", "chat"),
    ("Hindi mein 2 page ka report likho EV market par", "chat"),
    ("Research the top 5 EV makers in India and compare prices", "chat"),
    ("Is PDF ka summary do", "chat"), ("A 15 second reel for my bakery", "chat"),
    ("Translate this letter into Marathi", "chat"), ("Fix the failing test in billing.py", "code"),
    ("Agar 3 machine 5 din mein 120 piece banati hain to 7 machine 9 din mein kitne?", "chat"),
    ("Mujhe ek remind kar do kal 9 baje", "call"),
]


def main(argv: list[str]) -> int:
    doc = store.read_current()
    if not doc:
        print("no tables yet - run the feed first (vps-ops pipeline_feed)")
        return 1
    asks = [(a, "chat") for a in argv] or SAMPLES
    print(f"tables of {doc.get('read_on')} - the Box's choice per ask (nothing is routed yet)")
    for text, surface in asks:
        att = [{"type": "image/png"}] if "photo" in text.lower() and "poster" not in text.lower() else (
            [{"type": "application/pdf"}] if "pdf" in text.lower() else None)
        r = choose_for(text, attachments=att, surface=surface, doc=doc)
        m = (r["model"] or {}).get("id") or "-"
        bk = ", ".join(b["id"] for b in r["backups"]) or "-"
        print(f"\n  {text!r} [{surface}]")
        print(f"    kind {r['kind']} ({r['language']}) - {r['kind_why']}")
        print(f"    level {r['level']}" + (f" (used {r['level_used']})" if r.get("level_used") not in (None, r["level"])
                                            else "") + f" - {'; '.join(r['level_why'])}")
        print(f"    model {m}   backups {bk}")
        if r["choose_why"]:
            print(f"    why: {'; '.join(r['choose_why'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
