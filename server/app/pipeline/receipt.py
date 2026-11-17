"""P6 THE RECEIPT LINE (plan section 9 + 10): under a reply, which model did which part.

  "Research: Claude Sonnet 4.6 (5 parts) · Writing: Claude Opus 4.6"

One `model_receipt` event per Box message, published when the sheet closes (`turnbox.end`), so it lands under the
reply on the console and the phone and comes back on reload like any stored card. It names only what really ran:
a part not run through the Box is left out (its words came from the server's own chat model, which the Box did not
choose), a hand-over names the model that took over and keeps the one it replaced in the details. No price - pricing
is a later phase (D5). Switch `pipeline_receipt` (needs `pipeline_on`).
"""
from __future__ import annotations

import logging
import re
from typing import Any

from ..config import get_settings
from .parts import LABEL

log = logging.getLogger("santosh.pipeline")

UPPER = {"gpt": "GPT", "glm": "GLM", "ai": "AI", "vl": "VL", "oss": "OSS", "r1": "R1", "v3": "V3", "mimo": "MiMo",
         "qwq": "QwQ", "xai": "xAI", "llm": "LLM"}
DROP = {"preview", "latest", "exp", "experimental"}
STATES = {"done": "", "failed": "did not finish", "waiting_tap": "waiting for your tap", "waiting": "not started",
          "running": "still running", "cut": "stopped (time limit)"}


def pretty(mid: str) -> str:
    """'anthropic/claude-opus-4.6' -> 'Claude Opus 4.6', 'z-ai/glm-5.3-flash' -> 'GLM 5.3 Flash'."""
    tail = str(mid or "").rsplit("/", 1)[-1].split(":", 1)[0]
    tail = re.sub(r"-\d{6,8}$", "", tail)
    words = []
    for w in re.split(r"[-_ ]+", tail):
        if not w or w.lower() in DROP:
            continue
        lw = w.lower()
        if lw in UPPER:
            words.append(UPPER[lw])
        elif re.fullmatch(r"[a-z]?\d+(?:\.\d+)*[a-z]?", lw):
            words.append(w if not w[0].isalpha() else w[0].upper() + w[1:])
        else:
            words.append(w[:1].upper() + w[1:])
    return " ".join(words) or str(mid or "")


def _label(p: dict) -> str:
    return p.get("label") or LABEL.get(p.get("kind") or "", "Answer")


def build(sh: dict | None) -> dict[str, Any] | None:
    """The receipt of one closed sheet, or None when no part ran through the Box."""
    if not sh:
        return None
    rows: list[dict] = []
    for p in sh.get("parts") or []:
        if not p.get("applied"):
            continue
        chosen = (p.get("model") or {}).get("id") or ""
        ran = p.get("ran_on") or chosen
        if not ran:
            continue
        hand = [{"from": pretty(h.get("from") or ""), "to": pretty(h.get("to") or ""),
                 "why": _why(h)} for h in p.get("handover") or [] if h.get("to") and h.get("from")]
        rows.append({"n": p.get("n"), "label": _label(p), "kind": p.get("kind"), "model": ran, "name": pretty(ran),
                     "level": p.get("level_used") or p.get("level") or "", "state": p.get("state") or "",
                     "note": STATES.get(p.get("state") or "", ""), "handover": hand,
                     "chosen": pretty(chosen) if chosen and chosen != ran else ""})
    if not rows:
        return None
    groups: dict[tuple[str, str], int] = {}
    for r in rows:
        groups[(r["label"], r["name"])] = groups.get((r["label"], r["name"]), 0) + 1
    say = " · ".join(f"{lab}: {name}" + (f" ({n} parts)" if n > 1 else "") for (lab, name), n in groups.items())
    return {"sheet": sh.get("id"), "say": say, "parts": rows, "multi": bool(sh.get("multi")),
            "surface": sh.get("surface") or "chat", "handovers": sum(len(r["handover"]) for r in rows)}


def _why(h: dict) -> str:
    ev = h.get("event") or ""
    return {"error": "it failed", "refusal": "it refused", "empty": "it sent nothing", "late": "it was too slow",
            "too_long": "the job was too long for it", "failed_check": "the check found a problem"}.get(ev, ev)


def publish(sh: dict | None) -> dict[str, Any] | None:
    """Put the receipt under the reply (the chat the sheet belongs to). Never breaks the turn."""
    try:
        st = get_settings()
        if not bool(getattr(st, "pipeline_receipt", True)):
            return None
        r = build(sh)
        if not r:
            return None
        from ..events import bus
        bus.publish(sh["conv"], "model_receipt", r)
        return r
    except Exception as e:   # noqa: BLE001
        log.warning("pipeline receipt failed (%s)", str(e)[:120])
        return None
