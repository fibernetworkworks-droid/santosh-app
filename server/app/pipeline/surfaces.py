"""P5 THE OTHER SURFACES ON THE BOX (plan section 7 + 10): Hoola Code, background jobs and the Create studios.

  Hoola Code   every coding call (the round, the plan pass, the review, compaction, the memory observer, the hint)
               asks the Box for its kind of work - `code` starts at HIGH, `plan` / `summarise` at LOW - ranked score
               first, on the session's OpenRouter brain. Her own composer pick is a pin. The model's failures go to
               the Box's outage record and hand over to the backups (at most two changes). Replaces the fixed
               `dev_qwen_model`, which stays the fallback (Box off / no tables / nothing it can run).
  Background   routine / wake / long-job rounds go through the chat turn's Box with surface `background`
               (reliability first, no level cap, a 30 s first-word limit) - wired in `turnbox`.
  Studios      THE BOX RANKS, THE STUDIO RUNS: video / image keep their own engines, keys and price cards (D6); the Box
               only orders the models the studio can already run, by the video.make / image.make / image.edit tables.
               A Box pick the studio cannot run is never forced. Music (Lyria) and voice-over (Gemini voice) have one
               engine each on this server, so there is nothing to order there yet.

Switches (all need `pipeline_on`): `pipeline_code`, `pipeline_background`, `pipeline_studios`. Off = the old fixed
settings exactly - that is the fallback switch the plan asks for.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from typing import Any

from ..config import get_settings
from . import choose as C
from . import levels as L
from .kinds import LEVELS

log = logging.getLogger("santosh.pipeline")

STATS = {"code_choices": 0, "code_handovers": 0, "code_fallback": 0, "studio_orders": 0, "studio_kept": 0}
_SAID: dict[tuple, float] = {}          # (where, key, kind, model) -> when the choice was last logged
_SLOCK = threading.Lock()
SAY_EVERY_S = 600

# a Hoola Code call's kind of work (plan 7: the plan pass, the reviewer and compaction are their own parts)
CODE_KINDS = {"code", "plan", "check", "summarise"}
# the Box reads `check` from the facts table, which has no tool runs - a review with tools reads the code table
CHECK_WITH_TOOLS = "code"


def on(area: str) -> bool:
    st = get_settings()
    if not bool(getattr(st, "pipeline_on", False)):
        return False
    return bool(getattr(st, f"pipeline_{area}", True))


def _doc_health() -> tuple[dict | None, dict]:
    from . import turnbox as TB
    return TB.tables(), TB.health()


def _say(where: str, key: str, kind: str, level: str, mid: str, extra: str = "") -> None:
    now = time.time()
    k = (where, key, kind, mid)
    with _SLOCK:
        if now - _SAID.get(k, 0) < SAY_EVERY_S:
            return
        _SAID[k] = now
        if len(_SAID) > 2000:
            for old in sorted(_SAID, key=_SAID.get)[:1000]:
                _SAID.pop(old, None)
    log.warning("pipeline box %s%s: %s %s -> %s%s", where, f" {key}" if key else "", kind, level, mid, extra)


# ------------------------------------------------------------------ Hoola Code
def code_choice(kind: str, *, ask: str = "", pin: str = "", tools: bool = True, key: str = "",
                effort: str = "") -> dict[str, Any] | None:
    """The model + backups for one Hoola Code call. None = the Box is off / has no tables / chose nothing it can run
    (the caller keeps `dev_qwen_model`). Only OpenRouter models: Hoola Code talks to OpenRouter."""
    if not on("code"):
        return None
    kind = kind if kind in CODE_KINDS else "code"
    if kind == "check" and tools:
        kind = CHECK_WITH_TOOLS
    try:
        doc, health = _doc_health()
        if not doc:
            STATS["code_fallback"] += 1
            return None
        sig = L.for_kind(kind, L.signals(ask or ""))
        lv = L.level_for(kind, sig)
        level = lv["level"]
        why = list(lv["why"])
        if (effort or "").lower() in ("max", "xhigh") and kind == "code" and level != "ULTRA":
            up = L.up_one(level)
            if up != "ULTRA":
                level = up
                why.append(f"her effort {effort} -> {level}")
        need = {"kind": kind, "level": level, "surface": "code", "tools": bool(tools), "pin": pin,
                "routes": ["openrouter"]}
        from . import box as BX
        sticky = BX.recall("code:" + key, kind, level) if key else None
        pick = C.choose(doc, need, health=health, sticky=sticky, now=time.time())
    except Exception as e:   # noqa: BLE001 - the Box never breaks a coding step
        log.warning("pipeline box code: choosing failed (%s) - dev_qwen_model", str(e)[:120])
        STATS["code_fallback"] += 1
        return None
    m = pick.get("model") or {}
    if not m.get("id") or m.get("route") != "openrouter":
        STATS["code_fallback"] += 1
        return None
    backups = [b for b in pick.get("backups") or [] if b.get("route") == "openrouter" and b.get("id") != m["id"]]
    STATS["code_choices"] += 1
    _say("code", key, kind, pick.get("level_used") or level, m["id"],
         f" [backups {', '.join(b['id'] for b in backups) or 'none'}]")
    return {"kind": kind, "level": pick.get("level_used") or level, "model": m, "backups": backups,
            "why": why + list(pick.get("why") or [])}


def code_used(kind: str, level: str, model_id: str, key: str = "") -> None:
    """The model that answered this session's work: the next call of the same kind keeps it (5.1, 30 minutes)."""
    if key and model_id:
        from . import box as BX
        BX.remember("code:" + key, kind, level, model_id)


def code_failed(old: str, new: str, why: str) -> None:
    from . import runner as R
    R.model_failed("openrouter:" + old, why)
    STATS["code_handovers"] += 1
    log.warning("pipeline box hand-over (code): %s -> %s (%s)", old, new or "-", (why or "")[:140])
    try:   # v0.979 P7
        from . import watch as W
        W.outage(old, "handover", f"code -> {new or '-'}: {(why or '')[:120]}")
    except Exception:   # noqa: BLE001
        pass


def code_ok(model_id: str) -> None:
    try:
        from . import turnbox as TB
        TB.note(model_id, True)
    except Exception:   # noqa: BLE001
        pass


# ------------------------------------------------------------------ the studios
def _norm(s: str) -> str:
    s = str(s or "").lower().rsplit("/", 1)[-1]
    s = re.sub(r"(-preview|-latest|-generate|-\d{6,8})+$", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


def _same(a: str, b: str) -> bool:
    x, y = _norm(a), _norm(b)
    return bool(x) and x == y          # exact only: "seedance-2.0" is not "seedance-2.0-fast"


def ranked(kind: str, level: str, surface: str = "background") -> list[str]:
    """Every model of the kind's table, best first for this level: the level itself, then the levels above, then
    below; inside a level by the surface's order (reliability first for studios). Paused / banned models left out."""
    doc, health = _doc_health()
    if not doc:
        return []
    table, _k, _n = C.table_for(doc, kind)
    if not table:
        return []
    level = level.upper() if level.upper() in LEVELS else "MID"
    i = LEVELS.index(level)
    order = list(range(i, len(LEVELS))) + list(range(i - 1, -1, -1))
    out: list[str] = []
    for j in order:
        rows = list((table.get("levels") or {}).get(LEVELS[j]) or [])
        rows = [dict(m, _pos=p) for p, m in enumerate(rows)
                if m.get("id") and not ((health or {}).get(m["id"]) or {}).get("paused")]
        rows.sort(key=lambda m: C._rank_key(m, surface, health, m["_pos"]))
        out += [m["id"] for m in rows if m["id"] not in out]
    return out


def studio_order(kind: str, level: str, runnable: list[str], names: dict[str, list[str]] | None = None,
                 where: str = "studio") -> dict[str, Any]:
    """The studio's own models, reordered by the Box. `runnable` = the models the studio can run now, in its own
    order; `names` = per model the ids it may carry in the tables (its provider id, its label). Models the tables do
    not know keep their own order after the ones the Box ranked. Off / no tables = the studio's order, untouched."""
    res = {"order": list(runnable), "box": None, "why": ""}
    if not runnable or not on("studios"):
        return res
    try:
        box = ranked(kind, level)
    except Exception as e:   # noqa: BLE001 - the studio's own order stands
        log.warning("pipeline box %s: ranking failed (%s) - its own order", where, str(e)[:120])
        return res
    if not box:
        res["why"] = f"no {kind} table - its own order"
        return res
    names = names or {}
    pos: dict[str, int] = {}
    for m in runnable:
        for i, bid in enumerate(box):
            if any(_same(n, bid) for n in [m] + list(names.get(m) or [])):
                pos[m] = i
                break
    if not pos:
        STATS["studio_kept"] += 1
        res["why"] = f"the {kind} table ranks none of the models this studio can run - its own order"
        return res
    known = sorted(pos, key=lambda m: (pos[m], runnable.index(m)))
    res["order"] = known + [m for m in runnable if m not in pos]
    res["box"] = box[pos[known[0]]]
    res["why"] = f"{kind} {level}: the Box ranks {known[0]} first ({res['box']})"
    STATS["studio_orders"] += 1
    if res["order"][0] != runnable[0]:
        _say(where, "", kind, level, known[0], f" (was {runnable[0]})")
    return res


VIDEO_LEVEL = {"draft": "MID", "final": "HIGH", "premium": "MAX"}
IMAGE_LEVEL = {"fast": "MID", "best": "HIGH"}
