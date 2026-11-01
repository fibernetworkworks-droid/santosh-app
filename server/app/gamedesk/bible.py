"""v0.395 GAME BIBLE + SPECS AS DATA (Hoola Game Engine plan, Phase 3).

One source of truth per Studio Project, as DATA, not prose:
- meta (pillars, genre, audience), style (the palette every colour must come from, tone), terms (glossary + banned
  words), player (the numbers the player starts with), curves (how numbers grow by tier), economy (soft currency only);
- ENTITIES by kind - character, enemy, item, level, quest, screen - each kind a TEMPLATE (`KINDS`): typed fields with
  ranges, enums and references, so the 50th enemy has exactly the shape of the 1st.

Precision, all in code (no model):
- `check()` validators: types / ranges / enums, unique ids, every reference exists (a level's waves name real enemies,
  a quest's `requires` names real quests, no loops), colours only from the palette (style lock), glossary / banned
  words, text that fits (names <= 24 characters), no real-money fields (soft currency only), size budgets.
- `simulate()` balance: Monte-Carlo runs of every level with the player's numbers, SEEDED from the Bible's hash - the
  same Bible always gives the same numbers. Win rate, health left, score per level; flags an impossible level, a spike,
  a too-hard first level, a too-easy late level; the economy (coins per level vs item prices: levels to afford each).
- `gd()` writes the Bible into the game as `hoola_bible.gd` (`HoolaBible.DATA`), so the code reads names and numbers from
  the Bible; a balance change is then a DATA-ONLY rebuild (`apply`) - no model call, the same checks and playtest.

Generators: the model proposes only words (names, looks, behaviour, which enemies a level uses); the NUMBERS come from
the Bible's curves by tier in code, every draft is validated, and a model-made change waits as a DRAFT for her OK. Her
own edits apply at once (still validated: an error is refused, a warning is shown)."""
from __future__ import annotations

import copy
import hashlib
import json
import logging
import random
import re
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session

log = logging.getLogger("santosh.gamedesk")

MAX_ENTITIES = 400
MAX_BYTES = 200_000
NAME_MAX = 24
SIM_RUNS = 200
SIM_DT = 0.25
SIM_MAX_S = 300
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
ID = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
MONEY_FIELD = re.compile(r"(inr|rupee|usd|dollar|real_?money|cash|price_real|gems?_?pack|iap)", re.I)
MONEY_WORDS = re.compile(r"\b(real money|real-money|betting|gambl\w*|casino|loot ?box(es)?|satta|paise jeeto|cash prize)\b", re.I)

# ---------------------------------------------------------------- templates (one per kind)
# field: (type, default, options) - type: str | text | int | float | enum | color | ref | refs | waves | bool
KINDS: dict[str, dict[str, Any]] = {
    "character": {"label": "Character", "fields": {
        "name": ("str", "", {}), "role": ("enum", "hero", {"of": ["hero", "friend", "rival", "boss", "guide", "npc"]}),
        "bio": ("text", "", {"max": 600}), "age": ("int", 0, {"min": 0, "max": 500}), "color": ("color", "", {})}},
    "enemy": {"label": "Enemy", "curve": True, "fields": {
        "name": ("str", "", {}), "tier": ("int", 1, {"min": 1, "max": 20}),
        "hp": ("int", 10, {"min": 1, "max": 100000}), "damage": ("int", 5, {"min": 0, "max": 10000}),
        "attack_rate": ("float", 0.5, {"min": 0, "max": 20}), "accuracy": ("float", 0.5, {"min": 0, "max": 1}),
        "speed": ("float", 120, {"min": 0, "max": 2000}), "size": ("int", 48, {"min": 8, "max": 512}),
        "score": ("int", 10, {"min": 0, "max": 100000}), "coins": ("int", 1, {"min": 0, "max": 10000}),
        "behaviour": ("enum", "chase", {"of": ["chase", "patrol", "shoot", "zigzag", "dash", "still"]}),
        "shape": ("enum", "circle", {"of": ["circle", "square", "triangle", "diamond", "hexagon"]}),
        "color": ("color", "", {}), "notes": ("text", "", {"max": 300})}},
    "item": {"label": "Item", "curve": True, "fields": {
        "name": ("str", "", {}), "tier": ("int", 1, {"min": 1, "max": 20}),
        "effect": ("enum", "heal", {"of": ["heal", "speed", "shield", "damage", "score", "magnet", "life"]}),
        "value": ("float", 10, {"min": 0, "max": 100000}), "duration_s": ("float", 0, {"min": 0, "max": 600}),
        "price": ("int", 0, {"min": 0, "max": 1000000}), "color": ("color", "", {}), "notes": ("text", "", {"max": 300})}},
    "level": {"label": "Level", "curve": True, "fields": {
        "name": ("str", "", {}), "order": ("int", 1, {"min": 1, "max": 999}),
        "duration_s": ("int", 60, {"min": 10, "max": 600}), "waves": ("waves", [], {}),
        "target_score": ("int", 0, {"min": 0, "max": 10000000}), "reward_coins": ("int", 0, {"min": 0, "max": 1000000}),
        "background": ("color", "", {}), "notes": ("text", "", {"max": 400})}},
    "quest": {"label": "Quest", "fields": {
        "name": ("str", "", {}), "goal": ("enum", "defeat", {"of": ["defeat", "collect", "survive", "reach", "score"]}),
        "target": ("str", "", {"max": 40}), "count": ("int", 1, {"min": 1, "max": 100000}),
        "reward_coins": ("int", 0, {"min": 0, "max": 1000000}), "requires": ("refs", [], {"kind": "quest"}),
        "text": ("text", "", {"max": 400})}},
    "screen": {"label": "UI screen", "fields": {
        "name": ("str", "", {}), "purpose": ("text", "", {"max": 300}),
        "elements": ("list", [], {"max": 20, "item_max": 60})}},
}
DEFAULT_PLAYER = {"hp": 100, "damage": 10, "fire_rate": 2.0, "hit_chance": 0.7, "speed": 300}
DEFAULT_CURVES = {"enemy": {"hp": [20, 1.35], "damage": [5, 1.2], "score": [10, 1.3], "coins": [1, 1.25]},
                  "item": {"price": [50, 1.6], "value": [10, 1.25]},
                  "level": {"duration_s": [45, 1.08], "reward_coins": [20, 1.3], "count": [4, 1.2]}}


def empty() -> dict[str, Any]:
    return {"meta": {"title": "", "pillars": [], "genre": "", "audience": "", "rating": "everyone"},
            "style": {"palette": [], "tone": "", "font_sizes": [24, 36, 56]},
            "terms": {"glossary": {}, "banned": []}, "player": dict(DEFAULT_PLAYER),
            "curves": copy.deepcopy(DEFAULT_CURVES), "economy": {"currency": "coins"},
            "entities": {k: [] for k in KINDS}}


# ---------------------------------------------------------------- storage
class GameBible(Base):
    __tablename__ = "game_bibles"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gb"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    studio_id: Mapped[str] = mapped_column(String(40), index=True, unique=True)
    version: Mapped[int] = mapped_column(Integer, default=0)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    draft: Mapped[dict] = mapped_column(JSON, default=dict)        # a model-made change waiting for her OK
    history: Mapped[list] = mapped_column(JSON, default=list)      # [{v, at, by, what, hash}]
    applied: Mapped[int] = mapped_column(Integer, default=0)       # the Bible version inside the live game
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class BibleError(Exception):
    pass


_READY: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        GameBible.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


def _row(s, tenant: str, studio_id: str, make: bool = True) -> GameBible | None:
    ensure_table()
    b = s.scalars(select(GameBible).where(GameBible.studio_id == studio_id)).first()
    if b is not None and b.tenant_id != tenant:
        raise BibleError("Yeh Bible nahi mili.")
    if b is None and make:
        b = GameBible(tenant_id=tenant, studio_id=studio_id, data=empty(), history=[])
        s.add(b)
        s.flush()
    return b


def fingerprint(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


# ---------------------------------------------------------------- normalising + validating
def _num(v: Any, typ: str) -> Any:
    if isinstance(v, bool):
        raise ValueError("not a number")
    return int(round(float(v))) if typ == "int" else round(float(v), 4)


def clean_entity(kind: str, e: dict) -> tuple[dict, list[str]]:
    """Her (or a generator's) entity -> the template's exact shape. Returns (entity, errors). Unknown fields are
    dropped; missing ones take the template default; numbers are coerced, never silently clamped (out of range = error)."""
    if kind not in KINDS:
        return {}, [f"unknown kind '{kind}' (use {', '.join(KINDS)})"]
    errs: list[str] = []
    out: dict[str, Any] = {}
    eid = str((e or {}).get("id") or "").strip().lower()
    if not eid:
        eid = re.sub(r"[^a-z0-9]+", "_", str((e or {}).get("name") or "").lower()).strip("_")[:40]
    if eid and not eid[0].isalpha():
        eid = f"{kind[0]}_{eid}"[:40]
    if not ID.match(eid or ""):
        errs.append(f"{kind}: id '{eid}' must be lowercase letters / digits / _ (e.g. red_bat)")
    out["id"] = eid
    for f, (typ, default, opt) in KINDS[kind]["fields"].items():
        v = (e or {}).get(f, copy.deepcopy(default))
        try:
            if typ in ("int", "float"):
                v = _num(v if v not in (None, "") else default, typ)
                if "min" in opt and v < opt["min"] or "max" in opt and v > opt["max"]:
                    errs.append(f"{kind} {eid}.{f} = {v} is outside {opt.get('min')}..{opt.get('max')}")
            elif typ == "enum":
                v = str(v or default)
                if v not in opt["of"]:
                    errs.append(f"{kind} {eid}.{f} = '{v}' (allowed: {', '.join(opt['of'])})")
            elif typ == "color":
                v = str(v or "").strip()
                if v and not HEX.match(v):
                    errs.append(f"{kind} {eid}.{f} = '{v}' is not a colour like #FF8800")
                v = v.upper()
            elif typ in ("str", "text"):
                v = re.sub(r"\s+", " ", str(v or "")).strip()
                if len(v) > opt.get("max", 2000):
                    errs.append(f"{kind} {eid}.{f} is longer than {opt.get('max')} characters")
            elif typ == "refs":
                v = [str(x).strip().lower() for x in (v or []) if str(x).strip()][:30]
            elif typ == "list":
                v = [re.sub(r"\s+", " ", str(x)).strip()[: opt.get("item_max", 80)] for x in (v or []) if str(x).strip()]
                if len(v) > opt.get("max", 30):
                    errs.append(f"{kind} {eid}.{f} has more than {opt.get('max')} entries")
            elif typ == "waves":
                waves = []
                for w in (v or [])[:40]:
                    if not isinstance(w, dict):
                        errs.append(f"{kind} {eid}.waves: each wave is {{enemy, count, at_s}}")
                        continue
                    waves.append({"enemy": str(w.get("enemy") or "").strip().lower(),
                                  "count": int(_num(w.get("count", 1), "int")), "at_s": _num(w.get("at_s", 0), "float")})
                v = waves
        except (TypeError, ValueError):
            errs.append(f"{kind} {eid}.{f} = {v!r} is not a {typ}")
            v = copy.deepcopy(default)
        out[f] = v
    if "name" in out and not out["name"]:
        errs.append(f"{kind} {eid}: name is empty")
    for f in (e or {}):
        if f not in out and MONEY_FIELD.search(str(f)):
            errs.append(f"{kind} {eid}: '{f}' looks like real money - Hoola games use soft currency only")
    return out, errs


def _texts(e: dict) -> str:
    return " ".join(str(v) for v in e.values() if isinstance(v, str))


def check(data: dict) -> dict[str, list[str]]:
    """Every rule of the Bible, in code. errors block a change; warnings are shown."""
    errors: list[str] = []
    warns: list[str] = []
    ents = data.get("entities") or {}
    palette = {c.upper() for c in (data.get("style") or {}).get("palette") or [] if isinstance(c, str)}
    for c in palette:
        if not HEX.match(c):
            errors.append(f"palette colour '{c}' is not like #FF8800")
    banned = [w.lower() for w in (data.get("terms") or {}).get("banned") or [] if str(w).strip()]
    total = sum(len(v or []) for v in ents.values())
    if total > MAX_ENTITIES:
        errors.append(f"{total} entities (max {MAX_ENTITIES})")
    if len(json.dumps(data, ensure_ascii=False)) > MAX_BYTES:
        errors.append(f"Bible too big (max {MAX_BYTES // 1000} KB)")
    ids: dict[str, set] = {k: set() for k in KINDS}
    names: dict[str, str] = {}
    for kind, rows in ents.items():
        if kind not in KINDS:
            errors.append(f"unknown kind '{kind}'")
            continue
        for e in rows or []:
            clean, errs = clean_entity(kind, e)
            errors += errs
            eid = clean.get("id", "")
            if eid in ids[kind]:
                errors.append(f"{kind} id '{eid}' is used twice")
            ids[kind].add(eid)
            nm = clean.get("name", "")
            if len(nm) > NAME_MAX:
                warns.append(f"{kind} {eid}: name '{nm}' is {len(nm)} characters (fits on screen up to {NAME_MAX})")
            key = nm.lower()
            if key and key in names and names[key] != f"{kind}:{eid}":
                warns.append(f"name '{nm}' is used by {names[key]} and {kind}:{eid}")
            names.setdefault(key, f"{kind}:{eid}")
            for f, (typ, _d, _o) in KINDS[kind]["fields"].items():
                if typ == "color" and clean.get(f) and palette and clean[f] not in palette:
                    errors.append(f"{kind} {eid}.{f} {clean[f]} is not in the palette (style lock: {', '.join(sorted(palette))})")
            txt = _texts(clean).lower()
            for w in banned:
                if re.search(rf"\b{re.escape(w)}\b", txt):
                    errors.append(f"{kind} {eid} uses the banned word '{w}'")
            if MONEY_WORDS.search(txt):
                errors.append(f"{kind} {eid}: real-money / gambling words are not allowed")
    for lv in ents.get("level") or []:
        c, _ = clean_entity("level", lv)
        for w in c.get("waves") or []:
            if w["enemy"] not in ids["enemy"]:
                errors.append(f"level {c['id']}: wave enemy '{w['enemy']}' is not in the Bible")
            if w["at_s"] > c["duration_s"]:
                warns.append(f"level {c['id']}: a wave at {w['at_s']} s comes after the level ends ({c['duration_s']} s)")
        if not c.get("waves"):
            warns.append(f"level {c['id']}: no waves yet")
    orders = [clean_entity("level", lv)[0].get("order") for lv in ents.get("level") or []]
    if len(orders) != len(set(orders)):
        warns.append("two levels have the same order number")
    quests = {clean_entity("quest", q)[0]["id"]: clean_entity("quest", q)[0] for q in ents.get("quest") or []}
    for qid, q in quests.items():
        for r in q.get("requires") or []:
            if r not in quests:
                errors.append(f"quest {qid} requires '{r}', which is not in the Bible")
    # a quest loop (A needs B needs A) can never be finished
    state: dict[str, int] = {}

    def visit(q: str, path: list[str]) -> None:
        if state.get(q) == 2 or q not in quests:
            return
        if state.get(q) == 1:
            errors.append("quest loop: " + " -> ".join(path[path.index(q):] + [q]))
            return
        state[q] = 1
        for r in quests[q].get("requires") or []:
            visit(r, path + [q])
        state[q] = 2
    for q in quests:
        visit(q, [])
    for q in quests.values():
        if q["goal"] == "defeat" and q["target"] and q["target"] not in ids["enemy"]:
            warns.append(f"quest {q['id']}: target '{q['target']}' is not an enemy in the Bible")
    p = data.get("player") or {}
    for k, lo, hi in (("hp", 1, 1000000), ("damage", 0, 100000), ("fire_rate", 0, 50), ("hit_chance", 0, 1), ("speed", 0, 5000)):
        try:
            v = float(p.get(k, DEFAULT_PLAYER[k]))
            if not lo <= v <= hi:
                errors.append(f"player.{k} = {v} is outside {lo}..{hi}")
        except (TypeError, ValueError):
            errors.append(f"player.{k} is not a number")
    if ents.get("item") and not any(clean_entity("item", i)[0]["price"] for i in ents["item"]):
        warns.append("coins have nothing to buy (no item has a price)")
    return {"errors": list(dict.fromkeys(errors)), "warnings": list(dict.fromkeys(warns))}


# ---------------------------------------------------------------- balance simulation (seeded = repeatable)
def _sim_level(lv: dict, enemies: dict[str, dict], player: dict, rnd: random.Random, runs: int) -> dict[str, Any]:
    dur = min(int(lv["duration_s"]), SIM_MAX_S)
    spawns = sorted([(w["at_s"], w["enemy"]) for w in lv.get("waves") or [] for _ in range(max(0, w["count"]))
                     if w["enemy"] in enemies], key=lambda x: x[0])
    php, dmg, rate, hit = float(player["hp"]), float(player["damage"]), float(player["fire_rate"]), float(player["hit_chance"])
    wins = 0
    hp_left = score_sum = coins_sum = fail_t = 0.0
    fails = 0
    steps = int(dur / SIM_DT)
    for _ in range(runs):
        hp = php
        alive: list[list] = []          # [hp, enemy, attack_timer]
        nxt = 0
        fire_t = 0.0
        score = coins = 0
        dead_at = None
        for i in range(steps):
            t = i * SIM_DT
            while nxt < len(spawns) and spawns[nxt][0] <= t:
                e = enemies[spawns[nxt][1]]
                alive.append([float(e["hp"]), e, 0.0])
                nxt += 1
            if alive and rate > 0:
                fire_t += SIM_DT * rate
                while fire_t >= 1 and alive:
                    fire_t -= 1
                    if rnd.random() < hit:
                        alive[0][0] -= dmg
                        if alive[0][0] <= 0:
                            score += alive[0][1]["score"]
                            coins += alive[0][1]["coins"]
                            alive.pop(0)
            for a in alive:
                e = a[1]
                a[2] += SIM_DT * e["attack_rate"]
                while a[2] >= 1:
                    a[2] -= 1
                    if rnd.random() < e["accuracy"]:
                        hp -= e["damage"]
            if hp <= 0:
                dead_at = t
                break
        won = dead_at is None and score >= int(lv.get("target_score") or 0)
        if won:
            wins += 1
            hp_left += max(0.0, hp) / php
            coins += int(lv.get("reward_coins") or 0)
        if dead_at is not None:
            fails += 1
            fail_t += dead_at
        score_sum += score
        coins_sum += coins
    return {"id": lv["id"], "name": lv["name"], "order": lv["order"], "win_rate": round(wins / runs, 3),
            "hp_left": round(hp_left / wins, 2) if wins else 0.0, "avg_score": round(score_sum / runs, 1),
            "avg_coins": round(coins_sum / runs, 1), "avg_death_s": round(fail_t / fails, 1) if fails else None,
            "enemies": len(spawns)}


def simulate(data: dict, runs: int = SIM_RUNS) -> dict[str, Any]:
    """Thousands of simulated plays, seeded from the Bible: the same Bible always gives the same numbers."""
    c = check(data)
    if c["errors"]:
        return {"ok": False, "errors": c["errors"][:10], "levels": [], "flags": [], "economy": {}}
    seed = int(fingerprint(data), 16) % (2 ** 31)
    rnd = random.Random(seed)
    enemies = {e["id"]: e for e in (clean_entity("enemy", x)[0] for x in (data.get("entities") or {}).get("enemy") or [])}
    levels = sorted((clean_entity("level", x)[0] for x in (data.get("entities") or {}).get("level") or []),
                    key=lambda lv: lv["order"])[:30]
    player = {**DEFAULT_PLAYER, **(data.get("player") or {})}
    runs = max(20, min(int(runs), 2000))
    out = [_sim_level(lv, enemies, player, rnd, runs) for lv in levels]
    flags: list[str] = []
    for i, r in enumerate(out):
        if r["enemies"] == 0:
            continue
        if r["win_rate"] < 0.05:
            flags.append(f"{r['name']}: almost nobody wins ({round(r['win_rate'] * 100)}%) - too hard")
        if i == 0 and r["win_rate"] < 0.8:
            flags.append(f"{r['name']} is the FIRST level and only {round(r['win_rate'] * 100)}% win - new players quit here")
        if i and out[i - 1]["enemies"] and out[i - 1]["win_rate"] - r["win_rate"] > 0.35:
            flags.append(f"difficulty spike: {out[i - 1]['name']} {round(out[i - 1]['win_rate'] * 100)}% -> "
                         f"{r['name']} {round(r['win_rate'] * 100)}%")
        if len(out) >= 3 and i >= len(out) * 2 // 3 and r["win_rate"] > 0.98:
            flags.append(f"{r['name']} is a late level and {round(r['win_rate'] * 100)}% win - too easy")
    items = [clean_entity("item", x)[0] for x in (data.get("entities") or {}).get("item") or []]
    econ: dict[str, Any] = {"coins_per_level": [r["avg_coins"] for r in out], "items": []}
    cum = 0.0
    totals = []
    for r in out:
        cum += r["avg_coins"]
        totals.append(cum)
    for it in sorted(items, key=lambda x: x["price"]):
        if not it["price"]:
            continue
        need = next((i + 1 for i, tot in enumerate(totals) if tot >= it["price"]), None)
        econ["items"].append({"id": it["id"], "name": it["name"], "price": it["price"], "levels_to_afford": need})
        if need is None and out:
            flags.append(f"{it['name']} costs {it['price']} coins - not affordable even after the last level")
    return {"ok": True, "seed": seed, "runs": runs, "levels": out, "flags": flags, "economy": econ,
            "hash": fingerprint(data)}


# ---------------------------------------------------------------- curves + generators
def curve(data: dict, kind: str, field: str, tier: float, default: float) -> float:
    c = ((data.get("curves") or {}).get(kind) or {}).get(field) or (DEFAULT_CURVES.get(kind) or {}).get(field)
    if not c:
        return default
    base, growth = float(c[0]), float(c[1])
    return base * growth ** (max(1.0, float(tier)) - 1)


def apply_curves(data: dict, kind: str, e: dict) -> dict:
    """The template's numbers from the Bible's curves, by tier / level order (the model never picks a number)."""
    e = dict(e)
    if kind == "enemy":
        t = int(e.get("tier") or 1)
        for f in ("hp", "damage", "score", "coins"):
            e[f] = max(1 if f == "hp" else 0, int(round(curve(data, "enemy", f, t, KINDS["enemy"]["fields"][f][1]))))
    elif kind == "item":
        t = int(e.get("tier") or 1)
        e["price"] = int(round(curve(data, "item", "price", t, 0)))
        e["value"] = round(curve(data, "item", "value", t, 10), 2)
    elif kind == "level":
        o = int(e.get("order") or 1)
        e["duration_s"] = min(600, int(round(curve(data, "level", "duration_s", o, 60))))
        e["reward_coins"] = int(round(curve(data, "level", "reward_coins", o, 0)))
        n = max(1, int(round(curve(data, "level", "count", o, 4))))
        pool = [w.get("enemy") for w in e.get("waves") or [] if w.get("enemy")] or \
            [x["id"] for x in (data.get("entities") or {}).get("enemy") or []][:1]
        if pool:
            step = max(1.0, e["duration_s"] / (len(pool) + 1))
            e["waves"] = [{"enemy": en, "count": n, "at_s": round(step * (i + 0.5), 1)} for i, en in enumerate(pool[:6])]
    return e


GEN = """You add {n} new {label} entries to a game's Game Bible. Follow the Bible exactly: its pillars, tone, palette
and glossary. Only WORDS and choices are yours; numbers are set by Hoola's balance curves, so give only the fields
listed. Original names only (never names from existing games), no real money, no gambling, nothing unkind to real
groups. OUTPUT: only a JSON array of objects with these keys: {keys}."""
GEN_KEYS = {"character": "id, name, role, bio, age, color",
            "enemy": "id, name, tier (1 = first enemy; higher = later), behaviour, shape, size, speed, attack_rate, accuracy, color, notes",
            "item": "id, name, tier, effect, duration_s, color, notes",
            "level": "id, name, order (after the existing levels), waves (list of {enemy: an existing enemy id}), background, notes",
            "quest": "id, name, goal, target, count, reward_coins, requires (quest ids), text",
            "screen": "id, name, purpose, elements (short labels)"}


def _summary(data: dict) -> str:
    d = {k: data.get(k) for k in ("meta", "style", "terms", "player")}
    d["entities"] = {k: [{f: e.get(f) for f in ("id", "name", "tier", "order", "behaviour", "effect") if f in e}
                         for e in v][:60] for k, v in (data.get("entities") or {}).items() if v}
    return json.dumps(d, ensure_ascii=False)[:20000]


def generate_items(data: dict, kind: str, n: int, words: str, design: str = "") -> tuple[list[dict], list[str]]:
    from . import ai
    if kind not in KINDS:
        raise BibleError(f"kind = {', '.join(KINDS)}")
    n = max(1, min(int(n or 3), 12))
    raw = ai.ask(GEN.format(n=n, label=KINDS[kind]["label"].lower(), keys=GEN_KEYS[kind]),
                 f"The Game Bible now:\n{_summary(data)}\n\nThe design doc:\n{design[:6000]}\n\n"
                 + (f"What she wants: {words}\n\n" if words else "") + f"Write {n} new {kind} entries.", max_tokens=4000)
    m = re.search(r"\[.*\]", raw or "", re.S)
    try:
        items = json.loads(m.group(0)) if m else []
    except ValueError:
        items = []
    have = {e.get("id") for e in (data.get("entities") or {}).get(kind) or []}
    made, errs = [], []
    order0 = max([int(e.get("order") or 0) for e in (data.get("entities") or {}).get("level") or []] or [0])
    for i, it in enumerate(x for x in items if isinstance(x, dict)):
        if kind == "level":
            it["order"] = order0 + i + 1
        e = apply_curves(data, kind, it) if KINDS[kind].get("curve") else it
        clean, ee = clean_entity(kind, e)
        if clean.get("id") in have:
            base, k = clean["id"][:36], 2
            while f"{base}_{k}" in have:
                k += 1
            clean["id"] = f"{base}_{k}"
        have.add(clean.get("id"))
        if ee:
            errs += ee
            continue
        made.append(clean)
    return made[:n], errs


SEED = """Turn this game design doc into a Game Bible as DATA. OUTPUT only one JSON object with keys: meta {title,
pillars (3-5 short), genre, audience}, style {palette (4-6 hex colours from the doc), tone}, terms {glossary {term:
meaning}, banned []}, player {hp, damage, fire_rate, hit_chance, speed}, entities {enemy [...], item [...], level [...],
character [...]} using these keys - enemy: id, name, tier, behaviour, shape, size, speed, attack_rate, accuracy, color;
item: id, name, tier, effect, duration_s, color; level: id, name, order, waves [{enemy}], background; character: id,
name, role, bio, color. Colours only from the palette. Up to 6 enemies, 4 items, 5 levels. Original names only."""


def seed_from_design(design: str, title: str = "") -> dict:
    from . import ai
    raw = ai.ask(SEED, f"Design doc:\n{design[:8000]}", max_tokens=6000)
    m = re.search(r"\{.*\}", raw or "", re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except ValueError:
        d = {}
    out = empty()
    for k in ("meta", "style", "terms"):
        if isinstance(d.get(k), dict):
            out[k].update({kk: vv for kk, vv in d[k].items() if kk in out[k]})
    out["meta"]["title"] = out["meta"]["title"] or title
    out["style"]["palette"] = [str(c).upper() for c in out["style"].get("palette") or [] if HEX.match(str(c))][:12]
    if isinstance(d.get("player"), dict):
        for k in DEFAULT_PLAYER:
            try:
                out["player"][k] = float(d["player"].get(k, DEFAULT_PLAYER[k]))
            except (TypeError, ValueError):
                pass
    ents = d.get("entities") or {}
    for kind in ("enemy", "item", "character", "level"):
        for e in (ents.get(kind) or [])[:8]:
            if not isinstance(e, dict):
                continue
            e = apply_curves(out, kind, e) if KINDS[kind].get("curve") else e
            clean, errs = clean_entity(kind, e)
            if clean.get("color") and out["style"]["palette"] and clean["color"] not in out["style"]["palette"]:
                clean["color"] = out["style"]["palette"][0]
            if kind == "level":
                clean["background"] = "" if clean.get("background") not in out["style"]["palette"] else clean["background"]
                clean["waves"] = [w for w in clean["waves"] if w["enemy"] in {x["id"] for x in out["entities"]["enemy"]}]
            if not errs:
                out["entities"][kind].append(clean)
    return out


# ---------------------------------------------------------------- into the game
def _gd(v: Any, ind: int = 0) -> str:
    pad = "\t" * (ind + 1)
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    if isinstance(v, (int, float)):
        return repr(v) if isinstance(v, int) else repr(float(v))
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=True)       # \" \\ \n \uXXXX - all valid GDScript string escapes
    if isinstance(v, (list, tuple)):
        return "[]" if not v else "[\n" + ",\n".join(pad + _gd(x, ind + 1) for x in v) + "\n" + "\t" * ind + "]"
    if isinstance(v, dict):
        return "{}" if not v else "{\n" + ",\n".join(f"{pad}{json.dumps(str(k))}: {_gd(x, ind + 1)}" for k, x in v.items()) \
            + "\n" + "\t" * ind + "}"
    return json.dumps(str(v))


def gd(data: dict, version: int) -> str:
    """The Bible as GDScript, loaded as the HoolaBible autoload: `HoolaBible.DATA["entities"]["enemy"]` etc. Written by
    Hoola, never by the model. An autoload (not class_name) because a headless run has no global class cache."""
    body = {k: data.get(k) for k in ("meta", "style", "terms", "player", "economy")}
    body["entities"] = {k: [clean_entity(k, e)[0] for e in v] for k, v in (data.get("entities") or {}).items() if k in KINDS}
    body["by_id"] = {k: {e["id"]: e for e in v} for k, v in body["entities"].items()}
    return ("extends Node\n# HoolaBible (an autoload): the Game Bible (Hoola Studio) - names and numbers come from here.\n"
            "# Written by Hoola from the approved Bible; do not edit by hand (edit the Bible and rebuild).\n"
            f"const VERSION := {int(version)}\nconst DATA := {_gd(body)}\n")


# ---------------------------------------------------------------- service
def _studio(tenant: str, ref: str):
    from . import studio as S
    with session() as s:
        r = S._studio(s, tenant, ref)
        s.expunge(r)
    return r


def view(tenant: str, ref: str) -> dict[str, Any]:
    r = _studio(tenant, ref)
    with session() as s:
        b = _row(s, tenant, r.id)
        s.expunge(b)
    c = check(b.data or empty())
    counts = {k: len(v or []) for k, v in ((b.data or {}).get("entities") or {}).items()}
    return {"studio": r.id, "number": r.number, "version": b.version, "applied": b.applied, "data": b.data or empty(),
            "draft": b.draft or {}, "check": c, "counts": counts, "hash": fingerprint(b.data or empty()),
            "history": list(reversed((b.history or [])[-30:])),
            "templates": {k: {"label": v["label"], "fields": {f: {"type": t, "default": d, **o} for f, (t, d, o) in v["fields"].items()}}
                          for k, v in KINDS.items()}}


def _save(tenant: str, sid: str, data: dict, by: str, what: str) -> dict[str, Any]:
    c = check(data)
    if c["errors"]:
        raise BibleError("Bible mein galti: " + "; ".join(c["errors"][:5]))
    with session() as s:
        b = _row(s, tenant, sid)
        b.data = data
        b.version = (b.version or 0) + 1
        b.history = ((b.history or []) + [{"v": b.version, "at": now().isoformat(), "by": by, "what": what[:200],
                                           "hash": fingerprint(data)}])[-200:]
        b.updated_at = now()
    try:
        from . import studio as S
        with session() as s:
            st = s.get(S.GameStudio, sid)
            st.updated_at = now()
            st_obj = st
            s.expunge(st_obj)
        S._decide(st_obj, f"Bible v{(b.version)}: {what[:120]}", "", by=by)
    except Exception:                                   # noqa: BLE001 - the Bible itself is saved
        log.exception("bible decision log")
    return c


def _data(tenant: str, sid: str) -> dict:
    with session() as s:
        b = _row(s, tenant, sid)
        return copy.deepcopy(b.data or empty())


def set_entity(tenant: str, ref: str, kind: str, entity: dict, by: str = "her") -> dict[str, Any]:
    r = _studio(tenant, ref)
    clean, errs = clean_entity(kind, entity or {})
    if errs:
        raise BibleError("; ".join(errs[:5]))
    data = _data(tenant, r.id)
    rows = data["entities"].setdefault(kind, [])
    i = next((n for n, e in enumerate(rows) if e.get("id") == clean["id"]), None)
    if i is None:
        rows.append(clean)
        what = f"{KINDS[kind]['label']} '{clean['name']}' added"
    else:
        rows[i] = clean
        what = f"{KINDS[kind]['label']} '{clean['name']}' changed"
    _save(tenant, r.id, data, by, what)
    return view(tenant, r.id)


def remove_entity(tenant: str, ref: str, kind: str, eid: str) -> dict[str, Any]:
    r = _studio(tenant, ref)
    data = _data(tenant, r.id)
    rows = data["entities"].get(kind) or []
    keep = [e for e in rows if e.get("id") != eid]
    if len(keep) == len(rows):
        raise BibleError(f"{kind} '{eid}' Bible mein nahi hai.")
    data["entities"][kind] = keep
    _save(tenant, r.id, data, "her", f"{KINDS.get(kind, {}).get('label', kind)} '{eid}' removed")
    return view(tenant, r.id)


def set_section(tenant: str, ref: str, section: str, value: Any) -> dict[str, Any]:
    """meta / style / terms / player / curves / economy - her edits, validated."""
    r = _studio(tenant, ref)
    if section not in ("meta", "style", "terms", "player", "curves", "economy") or not isinstance(value, dict):
        raise BibleError("section = meta | style | terms | player | curves | economy (an object)")
    data = _data(tenant, r.id)
    base = data.get(section) or {}
    if section == "style" and "palette" in value:
        value = {**value, "palette": [str(c).strip().upper() for c in value.get("palette") or [] if str(c).strip()][:16]}
    if section == "curves":
        cur = copy.deepcopy(base)
        for k, fields in value.items():
            if k in DEFAULT_CURVES and isinstance(fields, dict):
                for f, pair in fields.items():
                    if f in DEFAULT_CURVES[k] and isinstance(pair, (list, tuple)) and len(pair) == 2:
                        b0, g0 = float(pair[0]), float(pair[1])
                        if not (0 <= b0 <= 1e6 and 0.5 <= g0 <= 3):
                            raise BibleError(f"curve {k}.{f}: base 0..1000000, growth 0.5..3")
                        cur.setdefault(k, {})[f] = [b0, g0]
        value = cur
    if section == "player":
        value = {k: float(value.get(k, base.get(k, DEFAULT_PLAYER[k]))) for k in DEFAULT_PLAYER}
    data[section] = {**base, **value} if section != "curves" else value
    _save(tenant, r.id, data, "her", f"{section} changed")
    return view(tenant, r.id)


def recurve(tenant: str, ref: str, kind: str) -> dict[str, Any]:
    """Re-derive every entity's numbers of a kind from the curves (after she changed a curve)."""
    r = _studio(tenant, ref)
    if not KINDS.get(kind, {}).get("curve"):
        raise BibleError("curves only for enemy / item / level")
    data = _data(tenant, r.id)
    data["entities"][kind] = [clean_entity(kind, apply_curves(data, kind, e))[0] for e in data["entities"].get(kind) or []]
    _save(tenant, r.id, data, "her", f"{kind} numbers re-made from the curves")
    return view(tenant, r.id)


def generate(tenant: str, ref: str, kind: str, n: int = 3, words: str = "") -> dict[str, Any]:
    """A DRAFT for her OK: the model's words + the curves' numbers, validated with the whole Bible."""
    from .. import usage
    from . import service as G
    r = _studio(tenant, ref)
    why = G.problem(words or "")
    if why:
        raise BibleError(why)
    data = _data(tenant, r.id)
    g = None
    try:
        g = G._get(tenant, r.game_id)
    except G.GameError:
        pass
    with usage.scope(tenant, "game"):
        made, errs = generate_items(data, kind, n, re.sub(r"\s+", " ", words or "").strip()[:800], (g.design if g else "") or r.goal)
    if not made:
        raise BibleError("Kuch naya nahi bana" + (": " + "; ".join(errs[:3]) if errs else "; apne shabdon mein bataiye."))
    trial = copy.deepcopy(data)
    trial["entities"][kind] = (trial["entities"].get(kind) or []) + made
    c = check(trial)
    draft = {"kind": kind, "add": made, "words": words[:300], "at": now().isoformat(), "check": c, "base": fingerprint(data)}
    with session() as s:
        b = _row(s, tenant, r.id)
        b.draft = draft
    return view(tenant, r.id)


def seed(tenant: str, ref: str) -> dict[str, Any]:
    """First Bible from the approved design doc - as a DRAFT (her OK makes it the Bible)."""
    from .. import usage
    from . import service as G
    r = _studio(tenant, ref)
    data = _data(tenant, r.id)
    if any(data["entities"].get(k) for k in KINDS):
        raise BibleError("Bible mein pehle se cheezein hain; naya seed nahi. 'generate' se aur jodiye.")
    g = G._get(tenant, r.game_id)
    with usage.scope(tenant, "game"):
        new = seed_from_design(g.design or r.goal, r.title)
    c = check(new)
    with session() as s:
        b = _row(s, tenant, r.id)
        b.draft = {"kind": "seed", "replace": new, "at": now().isoformat(), "check": c, "base": fingerprint(data)}
    return view(tenant, r.id)


def accept(tenant: str, ref: str, ids: list[str] | None = None) -> dict[str, Any]:
    """Her OK on the draft (all, or only some ids). The Bible must not have changed under it."""
    r = _studio(tenant, ref)
    with session() as s:
        b = _row(s, tenant, r.id)
        draft = copy.deepcopy(b.draft or {})
    if not draft:
        raise BibleError("Koi draft OK ke liye nahi hai.")
    data = _data(tenant, r.id)
    if draft.get("base") != fingerprint(data):
        raise BibleError("Draft ke baad Bible badal gayi; naya draft banaiye.")
    if draft["kind"] == "seed":
        data, what = draft["replace"], "first Bible from the design doc"
    else:
        add = [e for e in draft["add"] if not ids or e["id"] in ids]
        if not add:
            raise BibleError("Koi entry nahi chuni.")
        data["entities"][draft["kind"]] = (data["entities"].get(draft["kind"]) or []) + add
        what = f"{len(add)} {KINDS[draft['kind']]['label'].lower()}(s) added: " + ", ".join(e["name"] for e in add)[:150]
    _save(tenant, r.id, data, "her", what)
    with session() as s:
        _row(s, tenant, r.id).draft = {}
    return view(tenant, r.id)


def reject(tenant: str, ref: str) -> dict[str, Any]:
    r = _studio(tenant, ref)
    with session() as s:
        _row(s, tenant, r.id).draft = {}
    return view(tenant, r.id)


def sim(tenant: str, ref: str, runs: int = SIM_RUNS) -> dict[str, Any]:
    r = _studio(tenant, ref)
    return simulate(_data(tenant, r.id), runs)


def for_game(tenant: str, game_id: str) -> tuple[str, int] | None:
    """(hoola_bible.gd, version) for a game that has a Studio Bible with something in it, else None."""
    from . import studio as S
    ensure_table()
    with session() as s:
        st = s.scalars(select(S.GameStudio).where(S.GameStudio.tenant_id == tenant, S.GameStudio.game_id == game_id)).first()
        if st is None:
            return None
        b = _row(s, tenant, st.id, make=False)
        if b is None or not b.version:
            return None
        return gd(b.data or empty(), b.version), b.version


def mark_applied(tenant: str, game_id: str, version: int) -> None:
    from . import studio as S
    with session() as s:
        st = s.scalars(select(S.GameStudio).where(S.GameStudio.tenant_id == tenant, S.GameStudio.game_id == game_id)).first()
        if st is not None:
            b = _row(s, tenant, st.id, make=False)
            if b is not None:
                b.applied = max(b.applied or 0, int(version))


def apply(tenant: str, ref: str) -> dict[str, Any]:
    """The Bible into the live game WITHOUT a model call: same code + the new hoola_bible.gd, then the usual checks."""
    from . import service as G
    r = _studio(tenant, ref)
    with session() as s:
        b = _row(s, tenant, r.id)
        v = b.version
    if not v:
        raise BibleError("Bible abhi khaali hai.")
    c = check(_data(tenant, r.id))
    if c["errors"]:
        raise BibleError("Pehle Bible ki galtiyan theek kijiye: " + "; ".join(c["errors"][:3]))
    G.data_build(tenant, r.game_id, v)
    return view(tenant, r.id)
