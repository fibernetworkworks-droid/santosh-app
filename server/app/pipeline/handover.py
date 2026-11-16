"""P1 HAND-OVER (plan 5.2 + 5.3): what to do when a part's model goes wrong - pure decisions, no model call.

  error / refusal / empty answer      -> the next backup at the SAME level, at once
  no first word in time               -> the next backup at the same level (call: started side by side, first wins)
  the answer failed Hoola's check     -> ONE level up, once per part; failed again -> deliver, problem said plainly
  the part outgrew the model's window -> a same-level model with a bigger window
  she asked for better                -> one level up

A part changes model at most TWO times; after that it stops and says plainly what could not be done. Never a loop.
Running these against real models is P4; P1 is the rule book and its tests.
"""
from __future__ import annotations

from typing import Any

from .levels import up_one

FIRST_WORD_S = {"call": 3.0, "chat": 8.0, "background": 30.0, "code": 30.0}
MAX_CHANGES = 2


def first_word_limit(surface: str) -> float:
    return FIRST_WORD_S.get(surface or "chat", FIRST_WORD_S["chat"])


def late(surface: str, waited_s: float) -> bool:
    return waited_s >= first_word_limit(surface)


def new_part(kind: str, level: str, surface: str = "chat") -> dict[str, Any]:
    """The hand-over state one part carries on its job sheet."""
    return {"kind": kind, "level": level, "surface": surface, "changes": 0, "checks_failed": 0, "moved_up": False,
            "backups_used": 0, "log": []}


def next_move(part: dict, event: str, **info: Any) -> dict[str, Any]:
    """event: error | refusal | empty | late | failed_check | too_long | better.
    Returns {action, level, ...} - action is backup | up | bigger | race | deliver | stop - and updates `part`."""
    surface = part.get("surface") or "chat"
    level = part["level"]
    if event == "failed_check":
        part["checks_failed"] += 1
        if part["checks_failed"] >= 2 or part["moved_up"]:
            return _log(part, event, {"action": "deliver", "level": level,
                                      "say": "the answer did not pass the check twice - sent with the problem said"})
    if part["changes"] >= MAX_CHANGES:
        if event == "failed_check":
            return _log(part, event, {"action": "deliver", "level": level,
                                      "say": "no model changes left - sent with the problem said"})
        return _log(part, event, {"action": "stop", "level": level,
                                  "say": "changed model twice already - stopped and said what could not be done"})
    if event in ("error", "refusal", "empty"):
        mv = {"action": "backup", "level": level, "backup": part["backups_used"]}
        part["backups_used"] += 1
    elif event == "late":
        mv = {"action": "race" if surface == "call" else "backup", "level": level, "backup": part["backups_used"],
              "after_s": first_word_limit(surface)}
        part["backups_used"] += 1
    elif event == "too_long":
        mv = {"action": "bigger", "level": level, "size_tokens": int(info.get("size_tokens") or 0)}
    elif event in ("failed_check", "better"):
        new = up_one(level)
        if new == level:
            return _log(part, event, {"action": "deliver", "level": level, "say": "already at the top level"})
        mv = {"action": "up", "level": new, "from": level}
        if event == "failed_check":
            mv["problems"] = list(info.get("problems") or [])
        part["level"] = new
        part["moved_up"] = part["moved_up"] or event == "failed_check"
        part["backups_used"] = 0
    else:
        raise ValueError(f"unknown event {event!r}")
    part["changes"] += 1
    return _log(part, event, mv)


def _log(part: dict, event: str, mv: dict) -> dict:
    part["log"].append({"event": event, **mv})
    return mv
