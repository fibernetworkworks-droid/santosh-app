"""P1 CHOOSE (plan section 4): one main model + two backups for one part, from the level tables - code only.

  step 1  remove every model that cannot do the part (not in the table / not ready / wrong input or output / no
          tools when tools are needed / window under the input + 30 % / paused for recent failures / route not allowed)
  step 2  rank what is left: reliability, speed, leaderboard score - weighted by where the ask came from
          (call = speed first, Hoola Code = score first, background = reliability first)
  step 3  keep one main model + two backups, from different companies where possible

Rules from section 3-5 also kept here: her model pick is a pin for the parts it can do; ULTRA = one model (D7), its
backups come from MAX; an empty level uses the nearest filled level above (8.3); the same model is kept for the same
kind + level in a chat for 30 minutes while it is healthy (5.1). Pure: the same tables + the same need + the same
health give the same choice; a message keeps the tables copy it started with (`snapshot`).
"""
from __future__ import annotations

import copy
from typing import Any

from .kinds import KINDS, LEVELS, SAME
from .detect import BOARD_LANG
from .levels import INDIAN

STICKY_S = 30 * 60
ROOM = 1.3                             # a window must hold the input + 30 %
UNKNOWN_SPEED = 3                      # first-word bucket (seconds) for a model with no timing yet

# what a kind gives / takes (beyond the feed's own `out`)
OUT = {"speech.out": "audio", "speech.out.indian": "audio", "music.make": "audio"}
IN = {"read.image": "image", "image.edit": "image", "read.pdf": "file", "speech.in": "audio",
      "speech.in.indian": "audio"}
TOOLS_NEEDED = {"tools", "code", "research"}

# step 2 weights: the order of the sort keys per surface
ORDER = {"call": ("speed", "reliability", "score"), "code": ("score", "reliability", "speed"),
         "background": ("reliability", "score", "speed"), "chat": ("reliability", "speed", "score")}


def snapshot(doc: dict | None) -> dict:
    """The copy of the tables a message keeps from start to end (a refresh never changes a running answer)."""
    return copy.deepcopy(doc or {})


def company(m: dict) -> str:
    mid = str(m.get("id") or "")
    return mid.split("/", 1)[0] if "/" in mid else str(m.get("route") or mid)


def out_of(kind: str) -> str:
    return OUT.get(kind) or (KINDS.get(kind) or {}).get("out", "text")


def table_for(doc: dict, kind: str, language: str = "") -> tuple[dict | None, str, list[str]]:
    """(table, the kind whose table is read, notes). Follows `same_as` (route -> chat ...), picks the language view
    for writing / translation, and says plainly when a language has no board of its own (thin)."""
    tables = (doc or {}).get("tables") or {}
    notes: list[str] = []
    k, seen = kind, 0
    if k == "speech.in" and (language or "") in INDIAN | {"hinglish"}:
        k = "speech.in.indian"
    if k == "speech.out" and (language or "") in INDIAN | {"hinglish"}:
        k = "speech.out.indian"
    while (tables.get(k) or {}).get("same_as") and seen < 4:
        notes.append(f"{k} reads the {tables[k]['same_as']} table")
        k, seen = tables[k]["same_as"], seen + 1
    if k == "translate":
        k = SAME.get("translate", "write.lang")
    t = tables.get(k)
    if not t or t.get("not_ranked"):
        notes.append((t or {}).get("not_ranked") or f"no table for {k}")
        return None, k, notes
    if k == "write.lang" and language:
        board = BOARD_LANG.get(language)
        lt = (t.get("by_language") or {}).get(board or "")
        if lt and lt.get("n"):
            notes.append(f"{language}: its own language board")
            return lt, k, notes
        if language in INDIAN or language == "hinglish":
            notes.append(f"{language}: no public board ranks this language yet - the pooled non-English vote (thin)")
        else:
            notes.append(f"{language}: no board of its own - the pooled non-English vote")
    return t, k, notes


def _can(m: dict, info: dict | None, kind: str, need: dict) -> str:
    """'' = can do the part, else why not (step 1)."""
    if m.get("status", "ready") != "ready":
        return f"route not ready ({m.get('status')})"
    routes = need.get("routes")
    if routes and m.get("route") not in routes:
        return f"route {m.get('route')} not allowed here"
    if company(m) in set(need.get("block") or []):
        return f"{company(m)} not allowed for this user"
    if info:
        if out_of(kind) not in (info.get("outs") or []):
            return f"cannot give {out_of(kind)}"
        want = IN.get(kind)
        ins = set(info.get("ins") or [])
        if want == "file" and not ({"file", "image"} & ins):
            return "cannot read files"
        if want in ("image", "audio") and want not in ins:
            return f"cannot take {want}"
        if (need.get("tools") or kind in TOOLS_NEEDED) and not info.get("tools"):
            return "cannot use tools"
        size = int(need.get("size_tokens") or 0)
        ctx = int(info.get("ctx") or 0)
        if size and ctx and ctx < size * ROOM:
            return f"window {ctx} under {int(size * ROOM)}"
    return ""


def _health(health: dict | None, mid: str) -> dict:
    return (health or {}).get(mid) or {}


def _rank_key(m: dict, surface: str, health: dict | None, pos: int) -> tuple:
    h = _health(health, m["id"])
    rel = -round(float(h.get("ok_rate", 1.0)), 2)
    fw = h.get("first_word_s")
    speed = UNKNOWN_SPEED if fw is None else round(float(fw))
    pts = m.get("points")
    score = float(pts) if pts is not None else float(pos)
    keys = {"reliability": rel, "speed": speed, "score": score}
    return tuple(keys[k] for k in ORDER.get(surface, ORDER["chat"])) + (m["id"],)


def _usable(table: dict, level: str, kind: str, need: dict, models: dict, health: dict | None,
            dropped: dict) -> list[dict]:
    out = []
    for pos, m in enumerate((table.get("levels") or {}).get(level) or []):
        why = _can(m, models.get(m["id"]), kind, need)
        if not why and _health(health, m["id"]).get("paused"):
            why = "paused after recent failures"
        if why:
            dropped.setdefault(m["id"], why)
            continue
        out.append({**m, "level": level, "_pos": pos})
    return out


def _spread(ranked: list[dict], first: dict, n: int) -> list[dict]:
    """n backups after `first`: other companies first, in rank order, then the same company."""
    seen = {company(first)}
    pick: list[dict] = []
    for m in ranked:
        if m["id"] != first["id"] and company(m) not in seen and len(pick) < n:
            pick.append(m)
            seen.add(company(m))
    for m in ranked:
        if len(pick) >= n:
            break
        if m["id"] != first["id"] and m not in pick:
            pick.append(m)
    return pick


def _public(m: dict) -> dict:
    return {k: m.get(k) for k in ("id", "route", "level", "points", "name")}


def choose(doc: dict, need: dict, *, health: dict | None = None, sticky: dict | None = None,
           now: float = 0.0) -> dict[str, Any]:
    """need = {kind, level, language?, tools?, size_tokens?, surface?, pin?, routes?, block?}."""
    kind, level = need["kind"], need["level"].upper()
    surface = need.get("surface") or "chat"
    why: list[str] = []
    res: dict[str, Any] = {"kind": kind, "level": level, "read_on": (doc or {}).get("read_on"), "model": None,
                           "backups": [], "why": why, "dropped": {}}
    table, tkind, notes = table_for(doc, kind, need.get("language") or "")
    res["table"] = tkind
    why.extend(notes)
    if table is None:
        why.append("the Box does not choose for this part")
        return res
    models = (doc or {}).get("models") or {}
    dropped: dict[str, str] = res["dropped"]

    # her pick wins for the parts it can do
    pin = str(need.get("pin") or "").split(":", 1)[-1] if need.get("pin") else ""
    pin_m = None
    if pin:
        info = models.get(pin)
        bad = _can({"id": pin, "route": "openrouter", "status": "ready"}, info, kind, need)
        if not info and out_of(kind) != "text":
            bad = f"her pick is a text model; this part gives {out_of(kind)}"
        if bad:
            why.append(f"her pick {pin} cannot do this part ({bad}) - the Box chooses")
        else:
            pin_m = {"id": pin, "route": "openrouter", "level": level, "points": None, "name": pin}

    # the level to read: this level, else the nearest filled level above (8.3), else below
    start = LEVELS.index(level)
    order = list(range(start, len(LEVELS))) + list(range(start - 1, -1, -1))
    cands: list[dict] = []
    used = level
    for i in order:
        cands = _usable(table, LEVELS[i], kind, need, models, health, dropped)
        if cands:
            used = LEVELS[i]
            break
    if used != level:
        why.append(f"no usable model at {level} - used {used}")
    res["level_used"] = used
    if not cands and not pin_m:
        why.append("no model in the table can do this part")
        return res
    ranked = sorted(cands, key=lambda m: _rank_key(m, surface, health, m["_pos"]))
    if used == "ULTRA":
        # D7: ULTRA is one model - the best score of the band; backups come from MAX
        ranked = sorted(cands, key=lambda m: (float(m["points"]) if m.get("points") is not None else m["_pos"],
                                              m["id"]))
        first = ranked[0]
        below = sorted(_usable(table, "MAX", kind, need, models, health, dropped),
                       key=lambda m: _rank_key(m, surface, health, m["_pos"]))
        backs = _spread(below, first, 2)
        why.append("ULTRA is one model; backups from MAX")
    else:
        first = ranked[0]
        backs = _spread(ranked, first, 2)
        if len(backs) < 2:                         # a thin level: top up from the next level above
            for i in range(LEVELS.index(used) + 1, len(LEVELS)):
                more = sorted(_usable(table, LEVELS[i], kind, need, models, health, {}),
                              key=lambda m: _rank_key(m, surface, health, m["_pos"]))
                backs += [m for m in _spread(more, first, 2 - len(backs)) if m["id"] not in {b["id"] for b in backs}]
                if len(backs) >= 2:
                    break
    why.append(f"ranked by {', '.join(ORDER.get(surface, ORDER['chat']))} ({surface})")
    if sticky and sticky.get("id") and now - float(sticky.get("at") or 0) <= STICKY_S and not pin_m:
        keep = next((m for m in ranked if m["id"] == sticky["id"]), None)
        if keep and keep["id"] != first["id"]:
            backs = _spread(ranked, keep, 2)
            first = keep
            why.append("kept the model this chat used for the same work in the last 30 minutes")
    if pin_m:
        backs = _spread([first] + backs, pin_m, 2)
        first = pin_m
        why.append("her own pick")
    res["model"] = _public(first)
    res["backups"] = [_public(b) for b in backs[:2]]
    return res
