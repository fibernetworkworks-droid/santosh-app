"""v0.223 PHASE A: steer a running job (Claude-style).

Before: a message she sent while a long turn held the chat got a quick side-reply, and the real instruction waited
until the WHOLE turn ended (up to 45 minutes) while the job kept working on the old plan. Now the message is offered
here, and the running turn picks it up at its NEXT step boundary (between tool steps): her words ride with that
step's tool results, so the model reads them before its next move and changes course at once.

Race-safe on one event loop:
- `offer` (her message, chat busy) puts an entry in the chat's queue;
- the running turn `take`s every untaken entry at a step boundary (marks it taken, saves her words for memory);
- her message's own queued turn, once it gets the lock, `claim`s its entry: taken = it already reached the job, the
  queued turn does nothing; not taken (the job ended first) = the queued turn runs normally, exactly as before.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

log = logging.getLogger("santosh.steer")

_Q: dict[str, list[dict[str, Any]]] = defaultdict(list)
STATS = {"offered": 0, "delivered": 0, "ran_after": 0}


def offer(conv: str, text: str, client_id: str = "") -> dict[str, Any]:
    e = {"text": (text or "").strip(), "taken": False, "client_id": client_id or ""}
    _Q[conv].append(e)
    del _Q[conv][:-8]                      # never more than a handful waiting
    STATS["offered"] += 1
    return e


def withdraw(conv: str, e: dict[str, Any]) -> None:
    try:
        _Q[conv].remove(e)
    except ValueError:
        pass
    if not _Q[conv]:
        _Q.pop(conv, None)


def take(conv: str, held: set | None = None) -> list[str]:
    """The running turn, at a step boundary: every message she sent since, marked delivered.
    `held` = (conv, client_id) pairs she took back on the console: those never reach the job."""
    out = []
    for e in _Q.get(conv, []):
        if held and e.get("client_id") and (conv, e["client_id"]) in held:
            continue
        if not e["taken"] and e["text"]:
            e["taken"] = True
            out.append(e["text"])
    if out:
        STATS["delivered"] += len(out)
    return out


def claim(conv: str, e: dict[str, Any]) -> bool:
    """Her message's own turn got the lock: True = the running job already took it (do nothing more)."""
    withdraw(conv, e)
    if not e["taken"]:
        STATS["ran_after"] += 1
    return bool(e["taken"])


def note(texts: list[str]) -> str:
    """What the model reads with the step's results."""
    said = " | ".join(f'"{t[:600]}"' for t in texts)
    return ("[The owner just wrote in the MIDDLE of the work: " + said + ". This applies from now. First say in ONE short line "
            "that you understood and what you will do now (what changes), then carry on the work accordingly. To change the "
            "plan use kaam_plan add / a new set; if they ask you to stop, stop right there and say so. If this is "
            "only a question, answer in ONE line and keep working.]")
