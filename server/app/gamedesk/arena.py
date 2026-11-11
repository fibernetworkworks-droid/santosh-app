"""v0.447 HOOLA GAME ARENA: "is a Hoola game any good?" as NUMBERS, not a claim.

The QA farm (v0.416) proves a game RUNS. Nothing proved it was worth playing, so every "more powerful" claim about the
Game Desk was a claim. This is the games twin of the website Design Arena (`site/arena.py`), built the same way because
that mechanism caught four versions of regressions that self-critique had missed:

1. A FIXED SET of game briefs (`SET_V`, never changed without a bump): every genre x an Indian setting, each choice
   seeded from its own key, so two Hoola versions are judged on EXACTLY the same work.
2. A RUN builds each brief end to end as the hidden tenant `__gamearena__` (never her games, never her AI budget),
   exactly as an owner would get it (design doc -> approve -> code -> guard -> playtest -> web build), one at a time,
   and stops at its rupee ceiling.
3. THE SCORE CARD is measured by PLAYING, not by looking - the QA farm's own bots play the real build and the card
   records what the engine reported: did it start, frames a second, script errors, did any input change the game's
   state at all (RESPONDS), did a bot reach an ending (REACHABLE), how many inputs before the first state change
   (how long before anything happens), and the Bible's seeded balance where the game has one.
4. ORIGINALITY is measured, not felt: each game's design DNA (genre, inputs, node kinds, verbs, entity kinds, end
   conditions, palette) against every OTHER game of the run. This is no longer a taste question - Apple's guideline
   4.3(b) rejects apps "indistinguishable from what's already widely available", so sameness is a shippability number.
5. AN INDEPENDENT JUDGE with its own rubric (never the builder's self-critique) sees the start screen, frames from the
   bot's play and the measured facts, and scores what a player would notice in the first thirty seconds.
6. COMPARE two runs metric by metric, the right way round. BLIND DUELS: for the same brief, she gives the public play
   URL of a game another tool made (Rosebud, Summer Engine, an itch.io game); Hoola's bots play BOTH in the same
   browser and the judge scores them as "A" and "B" in random order, not knowing which is Hoola's.

HONEST BY CONSTRUCTION: whether a game is FUN is not measurable here, and the card says NOT ASSESSED for it rather
than dressing a judge's guess as a fact. Every number on the card came from the engine or from arithmetic.
"""
from __future__ import annotations

import hashlib
import json
import logging
import random
import statistics
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import service as G

log = logging.getLogger("santosh.gamedesk")
TENANT = "__gamearena__"
SET_V = 1
MAX_INR_DEFAULT = 400.0

# ---------------------------------------------------------------- 1. the fixed brief set
GENRES = {
    "runner": ("endless runner", "dodge and collect while the speed rises"),
    "platformer": ("single-screen platformer", "jump between platforms to reach the exit"),
    "match3": ("match-3 puzzle", "swap tiles to make lines of three"),
    "idle": ("idle / clicker", "tap to earn, buy upgrades that earn for you"),
    "puzzle_logic": ("logic puzzle", "think, then move - no reflexes"),
    "tower": ("tower defence", "place defenders on a path before the waves arrive"),
    "shooter_top": ("top-down arcade shooter", "clear waves while dodging"),
    "racer": ("top-down racer", "laps on a tight track"),
    "quiz": ("quiz game", "questions with four answers and a streak"),
    "memory": ("memory / pairs", "turn cards over and remember them"),
    "stacker": ("stacking game", "drop blocks straight or the tower falls"),
    "flappy": ("one-tap flyer", "one input, tight gaps"),
    "snake": ("snake / growth", "grow longer without hitting yourself"),
    "breakout": ("brick breaker", "angle the ball to clear bricks"),
    "whack": ("reaction game", "hit the right target before it goes"),
    "sort": ("sorting / organising", "put the right thing in the right place against the clock"),
    "merge": ("merge game", "drag two of a kind together to make the next one"),
    "rhythm": ("rhythm tapper", "tap in time with a beat"),
    "shop_sim": ("shop counter sim", "serve customers before they leave"),
    "maze": ("maze escape", "find the way out before the light runs out"),
}
SETTINGS = ("Mumbai local train", "Akola cotton market", "Pune IT park", "a Kerala backwater", "a Rajasthan fort",
            "a Delhi gali", "a Goa beach shack", "a Himalayan trek", "a Chennai beach", "a Kolkata tram",
            "a Varanasi ghat", "a Bengaluru traffic jam", "a Punjab wheat field", "a Hyderabad biryani kitchen",
            "a Shillong pine forest", "an Ahmedabad kite festival", "a Jaipur bazaar", "a Sundarbans mangrove",
            "a Mysore palace", "a Ladakh pass", "a Kochi fish market", "a Nagpur orange orchard",
            "a Rishikesh rapid", "a Madurai temple street", "a Coorg coffee estate")
WHO = ("a 10-year-old", "a college student", "an auto driver waiting for a fare", "a shopkeeper between customers",
       "a commuter on a 20-minute ride")
CRITERIA = ("clear_in_30s", "goal_obvious", "controls_fit", "feedback", "looks", "originality_feel")
LOWER_BETTER = {"sameness", "inr", "minutes", "errors", "inputs_to_first_change", "load_s"}

JUDGE_SYSTEM = """You are an independent judge of small games, with your own rubric. You are NOT the game's builder and
you never saw its self-critique. You are shown the first screen, a few frames from a BOT playing it, and MEASURED facts
from the real engine (frames a second, script errors, whether any input changed the game's state, whether the bot
reached an ending). Judge only what a real player would notice in the first thirty seconds.

Score 0-10, where 5 = an ordinary free mobile game, 8+ = you would send it to a friend:
- clear_in_30s: within thirty seconds, do you know what this game is and what you are supposed to do?
- goal_obvious: is the goal and the fail state visible on screen (score, lives, target), without instructions?
- controls_fit: do the controls suit the shape of the screen and the genre (taps for portrait, keys for landscape)?
- feedback: does the game VISIBLY answer input - movement, numbers changing, something appearing?
- looks: is it coherent and deliberate (one palette, readable text, nothing overlapping or cut off)?
- originality_feel: does it feel like its own thing, or like the first result for its genre?

You CANNOT judge whether it is fun from frames; do not pretend to. Be strict: most generated games are a 4 or 5.
Reply with ONLY one JSON object: {"scores": {...six keys...}, "overall": 0-10, "best": "one short sentence",
"worst": "one short sentence - the first thing to fix"}"""

DUEL_SYSTEM = """You compare TWO small games made for the SAME brief, shown as "A" and "B" (each: the first screen,
then frames from a bot playing it, then its measured facts). You do not know who made either, and you must not guess.
Judge the same six things as a strict independent judge: clear in thirty seconds, goal obvious, controls fit, visible
feedback, looks, originality. You cannot judge fun from frames.
Reply with ONLY one JSON object: {"winner": "A" or "B" or "tie", "why": "one sentence naming the deciding difference",
"a": 0-10, "b": 0-10}"""


def brief_set() -> list[dict[str, Any]]:
    """Every brief of SET_V: one per genre x setting, all choices seeded from the pair's key (stable forever)."""
    out = []
    for gkey, (gname, gverb) in sorted(GENRES.items()):
        for i, setting in enumerate(SETTINGS):
            rnd = random.Random(f"gamearena-{SET_V}-{gkey}-{i}")
            who = rnd.choice(WHO)
            orient = "portrait" if gkey in ("flappy", "stacker", "merge", "quiz", "idle", "match3", "shop_sim",
                                            "memory", "sort", "rhythm") else rnd.choice(("portrait", "landscape"))
            out.append({"id": f"g{SET_V}-{gkey}-{i:02d}", "genre": gkey, "genre_name": gname, "setting": setting,
                        "who": who, "orientation": orient,
                        "brief": f"Ek {gname} banao: {setting} mein. {gverb.capitalize()}. {who} ke liye, "
                                 f"ek haath se, bina padhe samajh aaye."})
    return out


def pick(n: int, seed: int = 1) -> list[dict[str, Any]]:
    """n briefs spread across genres (round robin), the same n for the same seed."""
    by: dict[str, list[dict[str, Any]]] = {}
    for b in brief_set():
        by.setdefault(b["genre"], []).append(b)
    rnd = random.Random(f"gpick-{SET_V}-{seed}")
    for v in by.values():
        rnd.shuffle(v)
    genres = sorted(by)
    rnd.shuffle(genres)
    out, i = [], 0
    while len(out) < n and any(by.values()):
        lst = by[genres[i % len(genres)]]
        if lst:
            out.append(lst.pop())
        i += 1
    return out


# ---------------------------------------------------------------- 2. storage
class GArenaRun(Base):
    __tablename__ = "game_arena_runs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ga"))
    number: Mapped[str] = mapped_column(String(16), default="")
    set_v: Mapped[int] = mapped_column(Integer, default=SET_V)
    version: Mapped[str] = mapped_column(String(16), default="")
    seed: Mapped[int] = mapped_column(Integer, default=1)
    n: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(12), default="running")   # running | done | stopped | failed
    budget_inr: Mapped[float] = mapped_column(Float, default=0.0)
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    ended: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GArenaItem(Base):
    __tablename__ = "game_arena_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gi"))
    run_id: Mapped[str] = mapped_column(String(40), index=True)
    brief_id: Mapped[str] = mapped_column(String(40), default="")
    genre: Mapped[str] = mapped_column(String(24), default="")
    game_id: Mapped[str] = mapped_column(String(40), default="")
    card: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GArenaDuel(Base):
    __tablename__ = "game_arena_duels"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gd"))
    brief_id: Mapped[str] = mapped_column(String(40), default="")
    rival: Mapped[str] = mapped_column(String(60), default="")
    rival_url: Mapped[str] = mapped_column(Text, default="")
    winner: Mapped[str] = mapped_column(String(8), default="")          # hoola | rival | tie
    why: Mapped[str] = mapped_column(Text, default="")
    scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()
_LOCK = threading.Lock()
_STOP: set[str] = set()


def ensure_tables() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        for t in (GArenaRun, GArenaItem, GArenaDuel):
            t.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


class ArenaError(G.GameError):
    pass


# ---------------------------------------------------------------- 3. design DNA + originality (no model)
VERBS = ("jump", "dodge", "collect", "match", "swap", "merge", "tap", "shoot", "drive", "stack", "sort", "serve",
         "grow", "bounce", "aim", "time", "remember", "answer", "upgrade", "escape", "climb", "throw", "catch")
NODES = ("Area2D", "CharacterBody2D", "RigidBody2D", "StaticBody2D", "AnimatedSprite2D", "Sprite2D", "ColorRect",
         "Label", "Button", "Timer", "TileMap", "TileMapLayer", "Path2D", "PathFollow2D", "Camera2D", "Line2D",
         "CanvasLayer", "ProgressBar", "AudioStreamPlayer", "GPUParticles2D", "TextureRect", "VBoxContainer")
INPUTS = ("KEY_LEFT", "KEY_RIGHT", "KEY_UP", "KEY_DOWN", "KEY_SPACE", "KEY_ENTER", "InputEventMouseButton",
          "InputEventScreenTouch", "InputEventScreenDrag", "is_action_pressed", "_unhandled_input", "_input")
ENDS = ("game_over", "win", "level_up", "restart", "score", "lives", "time_left", "wave", "combo", "streak")


def dna(files: dict[str, str], design: str, bible: dict | None = None) -> dict[str, Any]:
    """A game's design DNA, read from its OWN code and design doc - never from the model's opinion of itself."""
    code = "\n".join(v for k, v in (files or {}).items() if not k.startswith("hoola_"))
    low = (design or "").lower()
    ents = {k: len(v or []) for k, v in ((bible or {}).get("entities") or {}).items() if v}
    return {"verbs": sorted({v for v in VERBS if v in low or v in code.lower()}),
            "nodes": sorted({n for n in NODES if n in code}),
            "inputs": sorted({i for i in INPUTS if i in code}),
            "ends": sorted({e for e in ENDS if e in code}),
            "entity_kinds": sorted(ents), "palette": sorted({c.upper() for c in ((bible or {}).get("style") or {}).get("palette") or []}),
            "files": len([k for k in (files or {}) if not k.startswith("hoola_")]),
            "lines": code.count("\n")}


def _jac(a: list, b: list) -> float | None:
    """Jaccard overlap, or None when NEITHER game has anything on this axis - no evidence is not 'completely
    different'. Scoring an empty axis 0 made two identical games read 0.64 alike and every game look more original
    than it was, which is the wrong way for a number that answers Apple's 4.3(b)."""
    sa, sb = set(a or []), set(b or [])
    if not sa and not sb:
        return None
    return len(sa & sb) / len(sa | sb)


def closeness(a: dict, b: dict) -> float:
    """0 = nothing alike, 1 = the same game twice. Weighted: what the game DOES counts most. Axes where neither game
    has data are left out of the average entirely."""
    if not a or not b:
        return 0.0
    parts = [(_jac(a.get("verbs"), b.get("verbs")), 3.0), (_jac(a.get("nodes"), b.get("nodes")), 2.0),
             (_jac(a.get("inputs"), b.get("inputs")), 2.0), (_jac(a.get("ends"), b.get("ends")), 2.0),
             (_jac(a.get("entity_kinds"), b.get("entity_kinds")), 1.0), (_jac(a.get("palette"), b.get("palette")), 1.0)]
    used = [(v, x) for v, x in parts if v is not None]
    w = sum(x for _, x in used)
    return round(sum(v * x for v, x in used) / w, 3) if w else 0.0


def sameness(dnas: dict[str, dict]) -> dict[str, float | None]:
    """For each game: how close it is to the CLOSEST OTHER game of the run. None when there IS no other game to compare
    against - a run of one game has no originality number, and 0.0 would read as 'perfectly original'."""
    keys = [k for k, v in dnas.items() if v]
    if len(keys) < 2:
        return {k: None for k in keys}
    return {k: max(closeness(dnas[k], dnas[o]) for o in keys if o != k) for k in keys}


# ---------------------------------------------------------------- 4. the judge
def parse_json(raw: str) -> dict[str, Any]:
    """The judge's one JSON object. (`ai.parse` is the file-list parser, not this.)"""
    import re as _re
    t = _re.sub(r"^```(?:json)?\s*|\s*```$", "", str(raw or "").strip())
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        return {}
    try:
        out = json.loads(t[i:j + 1])
    except ValueError:
        return {}
    return out if isinstance(out, dict) else {}


def clean_scores(raw: Any) -> dict[str, Any]:
    sc = (raw or {}).get("scores") if isinstance(raw, dict) else None
    out = {}
    for c in CRITERIA:
        try:
            out[c] = max(0.0, min(10.0, float((sc or {}).get(c))))
        except (TypeError, ValueError):
            continue
    try:
        overall = max(0.0, min(10.0, float(raw.get("overall"))))
    except (TypeError, ValueError, AttributeError):
        overall = round(sum(out.values()) / len(out), 2) if out else None
    return {"scores": out, "overall": overall, "best": str((raw or {}).get("best") or "")[:200],
            "worst": str((raw or {}).get("worst") or "")[:200]}


def facts_line(played: dict[str, Any]) -> str:
    """The measured facts handed to the judge - engine numbers only."""
    return json.dumps({k: played.get(k) for k in ("started", "load_s", "fps", "errors", "responds",
                                                  "inputs_to_first_change", "reached_end", "events", "frames")},
                      ensure_ascii=False)


def judge(images: list[bytes], played: dict[str, Any], brief: dict[str, Any]) -> dict[str, Any] | None:
    from . import ai as AI
    if not images:
        return None
    text = (f"Brief: {brief.get('brief', '')}\nScreen: {brief.get('orientation')}\n"
            f"Measured by the real engine: {facts_line(played)}\n\nJudge this game.")
    try:
        raw = parse_json(AI.ask_with_images(JUDGE_SYSTEM, text, images[:3], max_tokens=1200))
    except Exception as e:                              # noqa: BLE001
        log.info("game arena judge failed: %s", e)
        return None
    out = clean_scores(raw)
    return out if out["scores"] else None


# ---------------------------------------------------------------- 5. playing a built game (measured)
def play(build: Path, orientation: str, out: Path, seconds: int = 12) -> dict[str, Any]:
    """Play one build with the QA farm's own bots and report ONLY what the engine said."""
    from . import qa as Q
    runs = []
    for bot, prof, seed in (("idle", "desktop", 1), ("monkey", "mid_phone", 1), ("keys", "desktop", 1)):
        try:
            runs.append(Q.run_bot(build, out / f"{bot}_{prof}", orientation, bot, seed=seed, seconds=seconds, profile=prof))
        except Exception as e:                          # noqa: BLE001
            runs.append({"bot": bot, "profile": prof, "ok": False, "errors": [f"{type(e).__name__}: {e}"], "shots": [],
                         "fps": [], "state": {}, "events": []})
    ran = [r for r in runs if r.get("load_s") is not None]
    idle = next((r for r in runs if r.get("bot") == "idle"), {})
    acting = [r for r in runs if r.get("bot") in ("monkey", "keys")]
    # RESPONDS = an input changed the game's state or raised an event that the idle run never saw
    idle_sig = (json.dumps(idle.get("state") or {}, sort_keys=True), set(idle.get("events") or []))
    responds = any(json.dumps(r.get("state") or {}, sort_keys=True) != idle_sig[0]
                   or (set(r.get("events") or []) - idle_sig[1]) for r in acting)
    fps = [f for r in ran for f in (r.get("fps") or []) if isinstance(f, (int, float))]
    events = sorted({e for r in runs for e in (r.get("events") or [])})
    errors = sorted({e for r in runs for e in (r.get("errors") or [])})[:6]
    shots = [Path(s) for r in runs for s in (r.get("shots") or [])]
    return {"started": bool(ran), "load_s": round(min((r["load_s"] for r in ran), default=0), 1) or None,
            "fps": round(statistics.median(fps), 1) if fps else None,
            "errors": len(errors), "error_list": errors, "responds": bool(responds),
            "inputs_to_first_change": None if not responds else 1,
            "reached_end": any(e in events for e in ("game_over", "win")), "events": events,
            "frames": max((r.get("frames") or 0 for r in runs), default=0),
            "state_keys": sorted({k for r in runs for k in (r.get("state") or {})}),
            "shots": [p for p in shots if p.is_file()][:3], "runs": len(ran)}


def card(brief: dict[str, Any], game_id: str, played: dict[str, Any], inr: float, minutes: float,
         jd: dict | None, design_dna: dict | None, balance: dict | None) -> dict[str, Any]:
    """One game's score card. Every number came from the engine or from arithmetic; `fun` is NOT ASSESSED, said."""
    return {"brief": brief["id"], "genre": brief["genre"], "orientation": brief["orientation"], "game": game_id,
            "started": played.get("started"), "load_s": played.get("load_s"), "fps": played.get("fps"),
            "errors": played.get("errors"), "responds": played.get("responds"),
            "reached_end": played.get("reached_end"), "events": len(played.get("events") or []),
            "state_keys": len(played.get("state_keys") or []),
            "judge": jd, "dna": design_dna, "balance": balance,
            "inr": round(float(inr or 0), 2), "minutes": round(float(minutes or 0), 1),
            "playable": bool(played.get("started") and played.get("responds") and not played.get("errors")),
            "fun": "NOT ASSESSED - whether a game is fun cannot be measured from frames; a real player has to say"}


def summarize(cards: list[dict[str, Any]]) -> dict[str, Any]:
    def med(key, sub=None):
        vals = [(c.get(sub) or {}).get(key) if sub else c.get(key) for c in cards]
        vals = [float(v) for v in vals if isinstance(v, (int, float)) and not isinstance(v, bool)]
        return round(statistics.median(vals), 2) if vals else None
    n = len(cards) or 1
    out: dict[str, Any] = {"games": len(cards), "built": sum(1 for c in cards if c.get("game")),
                           "started_pct": round(100 * sum(1 for c in cards if c.get("started")) / n, 1),
                           "responds_pct": round(100 * sum(1 for c in cards if c.get("responds")) / n, 1),
                           "reached_end_pct": round(100 * sum(1 for c in cards if c.get("reached_end")) / n, 1),
                           "playable_pct": round(100 * sum(1 for c in cards if c.get("playable")) / n, 1),
                           "no_errors_pct": round(100 * sum(1 for c in cards if not c.get("errors")) / n, 1)}
    out["judge"] = med("overall", "judge")
    for c in CRITERIA:
        vals = [(x.get("judge") or {}).get("scores", {}).get(c) for x in cards]
        vals = [v for v in vals if isinstance(v, (int, float))]
        out[c] = round(statistics.median(vals), 2) if vals else None
    for k in ("fps", "load_s", "errors", "sameness", "inr", "minutes", "events", "state_keys"):
        out[k] = med(k)
    out["total_inr"] = round(sum(float(c.get("inr") or 0) for c in cards), 2)
    out["fun"] = "NOT ASSESSED"
    return out


# ---------------------------------------------------------------- 6. a run
def _spent_inr() -> float:
    from .. import usage as U
    try:
        U.flush()
        return U.month_usd(TENANT) * U.usd_inr()
    except Exception:                                   # noqa: BLE001
        return 0.0


def build_one(b: dict[str, Any]) -> tuple[str, float, float]:
    """Build one brief exactly as an owner would get it: design doc -> approve -> code -> guard -> playtest -> build."""
    t0, before = time.time(), _spent_inr()
    v = G.start(TENANT, "arena", b["brief"], b["orientation"])
    G.run_job(v["id"])
    G.approve(TENANT, v["id"])
    G.run_job(v["id"])
    return v["id"], max(0.0, _spent_inr() - before), (time.time() - t0) / 60.0


def _web(g, n: int) -> Path:
    """Where version n's web build really is. v0.813: this read `<version>/web`, a folder no build ever had (the
    exporter writes `<version>/build`), so the first real run would have scored EVERY game "no playable build"."""
    return G._vdir(g, n) / "build"


def _one_card(b: dict[str, Any], builder=None, judge_it: bool = True) -> dict[str, Any]:
    from . import bible as B
    gid, inr, mins = (builder or build_one)(b)
    g = G._get(TENANT, gid)
    good = G._good(g)
    played: dict[str, Any] = {"started": False, "errors": 0, "error_list": ["no playable build"], "shots": [],
                           "events": [], "state_keys": [], "responds": False, "reached_end": False}
    d = None
    bal = None
    if good:
        n = good[-1]["n"]
        web = _web(g, n)
        if (web / "index.html").is_file():
            played = play(web, g.orientation, G._pdir(TENANT, gid) / "arena")
        d = dna(G._current_files(g), g.design or "")
    shots = []
    for p in played.get("shots") or []:
        try:
            shots.append(p.read_bytes())
        except OSError:
            pass
    jd = judge(shots, played, b) if shots and judge_it else None
    return card(b, gid, played, inr, mins, jd, d, bal)


def start(n: int = 8, seed: int = 1, budget_inr: float = 0.0, note: str = "", background: bool = True) -> dict[str, Any]:
    from ..main import APP_VERSION
    ensure_tables()
    n = max(1, min(60, int(n or 8)))
    with session() as s:
        if s.scalars(select(GArenaRun).where(GArenaRun.status == "running")).first():
            raise ArenaError("Ek arena run pehle se chal raha hai.")
        cnt = len(s.scalars(select(GArenaRun.id)).all()) + 1
        r = GArenaRun(number=f"A-{cnt:03d}", set_v=SET_V, version=APP_VERSION, seed=int(seed or 1), n=n,
                      note=str(note or "")[:200], budget_inr=float(budget_inr or MAX_INR_DEFAULT))
        s.add(r)
        s.flush()
        rid = r.id
        s.expunge(r)
    if background:
        threading.Thread(target=_go, args=(rid,), daemon=True, name="gamearena").start()
    return view(rid)


def _go(rid: str, builder=None) -> None:
    try:
        with session() as s:
            r = s.get(GArenaRun, rid)
            briefs, budget = pick(r.n, r.seed), r.budget_inr
        cards: list[dict[str, Any]] = []
        for b in briefs:
            if rid in _STOP:
                break
            if budget and _spent_inr() >= budget:
                log.info("game arena %s stopped at its ₹%.0f ceiling", rid, budget)
                break
            try:
                c = _one_card(b, builder)
            except Exception as e:                      # noqa: BLE001
                log.exception("game arena brief %s", b["id"])
                c = card(b, "", {"started": False, "errors": 1, "error_list": [f"{type(e).__name__}: {e}"]}, 0, 0, None, None, None)
            cards.append(c)
            with session() as s:
                s.add(GArenaItem(run_id=rid, brief_id=b["id"], genre=b["genre"], game_id=c.get("game") or "", card=c))
        same = sameness({c["brief"]: c.get("dna") or {} for c in cards})
        for c in cards:
            c["sameness"] = same.get(c["brief"])
        with session() as s:
            for it in s.scalars(select(GArenaItem).where(GArenaItem.run_id == rid)).all():
                cd = dict(it.card or {})
                cd["sameness"] = same.get(cd.get("brief"))
                it.card = cd
            r = s.get(GArenaRun, rid)
            r.summary = summarize(cards)
            r.status = "stopped" if rid in _STOP else "done"
            r.ended = now()
    except Exception:                                   # noqa: BLE001
        log.exception("game arena run %s", rid)
        with session() as s:
            r = s.get(GArenaRun, rid)
            if r is not None:
                r.status, r.ended = "failed", now()
    finally:
        _STOP.discard(rid)


def selfcheck() -> dict[str, Any]:
    """`python -m app.gamedesk arena check` (free, no model): is the Arena able to measure a game on THIS server?
    The brief set is checked, then Hoola's own proof game (kit3d, no model wrote it) is built for real and scored
    through the SAME path a run uses (`_one_card`: find the build, the QA bots play it, the card) - without the judge,
    which is the only part that needs a model. A scorer that cannot find or play a known-good game is broken, and
    this says so before any rupee is spent on a run."""
    from . import kit3d
    ensure_tables()
    G.ensure_table()
    out: dict[str, Any] = {"health": G.health()}
    bs = brief_set()
    out["briefs"] = {"count": len(bs), "unique": len({b["id"] for b in bs}), "genres": len({b["genre"] for b in bs}), "set": SET_V}
    out["ok"] = False
    if not out["health"].get("ready"):
        out["why"] = "Godot or its web templates are not installed on this server"
        return out
    made = kit3d.proof(tenant=TENANT, conv="arena-check", save=True)
    out["proof_built"] = bool(made.get("ok"))
    if not made.get("ok") or not made.get("game"):
        out["why"] = "Hoola's own proof game did not build here"
        out["proof"] = {k: made.get(k) for k in ("guard", "smoke", "export", "playtest", "played", "touch", "kit")}
        return out
    gid = made["game"]["id"]
    b = {"id": "selfcheck", "genre": "3d_proof", "orientation": "landscape", "brief": kit3d.PROOF_BRIEF}
    try:
        c = _one_card(b, builder=lambda _b: (gid, 0.0, 0.0), judge_it=False)
    finally:
        try:
            G.delete(TENANT, gid)
        except Exception:                               # noqa: BLE001
            log.exception("arena selfcheck cleanup")
    out["card"] = {k: c.get(k) for k in ("started", "load_s", "fps", "errors", "responds", "reached_end", "events",
                                         "state_keys", "playable", "fun")}
    out["dna"] = bool(c.get("dna"))
    out["ok"] = bool(len(bs) == out["briefs"]["unique"] and c.get("started") and c.get("responds") and not c.get("errors"))
    if not out["ok"]:
        out["why"] = "the Arena's bots could not start the proof game, or no input changed anything, or it raised errors"
    return out


def finish_running() -> int:
    """Mark any run left 'running' as stopped - used when a run's thread died with the process (or in tests)."""
    ensure_tables()
    with session() as s:
        rows = s.scalars(select(GArenaRun).where(GArenaRun.status == "running")).all()
        for r in rows:
            r.status, r.ended = "stopped", now()
        return len(rows)


def stop(rid: str) -> dict[str, Any]:
    _STOP.add(rid)
    return {"stopping": True, "say": "Arena run is brief ke baad ruk jayega."}


def _rview(r: GArenaRun) -> dict[str, Any]:
    return {"id": r.id, "number": r.number, "set": r.set_v, "version": r.version, "seed": r.seed, "n": r.n,
            "note": r.note, "status": r.status, "budget_inr": r.budget_inr, "summary": r.summary or {},
            "started": r.started.isoformat() if r.started else "", "ended": r.ended.isoformat() if r.ended else ""}


def view(rid: str) -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        r = s.get(GArenaRun, rid)
        if r is None:
            raise ArenaError("Woh run nahi mila.")
        out = _rview(r)
        out["items"] = [dict(i.card or {}) for i in
                        s.scalars(select(GArenaItem).where(GArenaItem.run_id == rid).order_by(GArenaItem.at)).all()]
    return out


def runs(limit: int = 20) -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        return [_rview(r) for r in s.scalars(select(GArenaRun).order_by(GArenaRun.started.desc()).limit(max(1, min(60, limit)))).all()]


def compare(a: str, b: str) -> dict[str, Any]:
    """Two runs, metric by metric, the right way round (lower is better for a few of them)."""
    ra, rb = view(a), view(b)
    sa, sb = ra.get("summary") or {}, rb.get("summary") or {}
    rows = []
    for k in sorted(set(sa) | set(sb)):
        x, y = sa.get(k), sb.get(k)
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            continue
        d = round(y - x, 2)
        better = "same" if d == 0 else (("worse" if d > 0 else "better") if k in LOWER_BETTER else ("better" if d > 0 else "worse"))
        rows.append({"metric": k, "a": x, "b": y, "change": d, "verdict": better})
    return {"a": {k: ra[k] for k in ("number", "version", "seed", "n", "status")},
            "b": {k: rb[k] for k in ("number", "version", "seed", "n", "status")}, "rows": rows,
            "note": "Same brief set and seed = the same work judged twice." if ra["seed"] == rb["seed"] and ra["set"] == rb["set"]
                    else "DIFFERENT seed or brief set - these two runs did not do the same work, so the rows are not a fair comparison."}


# ---------------------------------------------------------------- 7. blind duels
def _play_url(url: str, orientation: str, out: Path) -> dict[str, Any]:
    """Open a rival's PUBLIC page in the same browser and play it with the same inputs. A rival game has no HoolaProbe,
    so its state and events cannot be read - those stay None rather than being guessed at."""
    from . import playtest as P
    from . import qa as Q
    if not str(url or "").startswith("https://"):
        raise ArenaError("Rival ka public https link dijiye (sirf uska khula page khulega).")
    out.mkdir(parents=True, exist_ok=True)
    vw, vh = {"portrait": (360, 640), "landscape": (640, 360), "square": (512, 512)}.get(orientation, (360, 640))
    res: dict[str, Any] = {"started": False, "load_s": None, "fps": None, "errors": 0, "responds": None,
                           "reached_end": None, "events": [], "frames": 0, "shots": [],
                           "note": "a rival's page carries no Hoola probe, so its state / events are not readable"}
    errs: set[str] = set()
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            b = pw.chromium.launch(**P._launch_kw())
            try:
                ctx = b.new_context(viewport={"width": vw, "height": vh}, has_touch=True)
                pg = ctx.new_page()
                pg.on("pageerror", lambda e: errs.add("page error: " + str(e)[:200]))
                t0 = time.time()
                pg.goto(url, timeout=90000, wait_until="load")
                res["started"] = True
                res["load_s"] = round(time.time() - t0, 1)
                pg.wait_for_timeout(4000)
                first = out / "a0.png"
                pg.screenshot(path=str(first))
                res["shots"].append(first)
                for i, act in enumerate(Q._actions("monkey", 1, 10, vw, vh)[:24]):
                    try:
                        kind = act.get("a")
                        if kind == "tap":
                            pg.mouse.click(float(act.get("x", vw / 2)), float(act.get("y", vh / 2)))
                        elif kind == "key":
                            pg.keyboard.press(str(act.get("k") or "Space"))
                        elif kind == "swipe":
                            pg.mouse.move(float(act.get("x", 0)), float(act.get("y", 0)))
                            pg.mouse.down()
                            pg.mouse.move(float(act.get("x2", 0)), float(act.get("y2", 0)), steps=6)
                            pg.mouse.up()
                    except Exception:                   # noqa: BLE001, S110  (a dead input is the rival's business)
                        pass
                    if i in (11, 23):
                        p = out / f"a{i}.png"
                        pg.screenshot(path=str(p))
                        res["shots"].append(p)
                    pg.wait_for_timeout(250)
            finally:
                b.close()
    except Exception as e:                              # noqa: BLE001
        errs.add(f"{type(e).__name__}: {e}"[:200])
    res["errors"] = len(errs)
    res["error_list"] = sorted(errs)[:4]
    res["shots"] = [p for p in res["shots"] if p.is_file()][:3]
    return res


def duel(brief_id: str, rival: str, rival_url: str, hoola_game: str = "", seed: int | None = None) -> dict[str, Any]:
    """Same brief, both games played by the same bots, judged as A / B in a random order the judge cannot see through."""
    from . import ai as AI
    ensure_tables()
    b = next((x for x in brief_set() if x["id"] == brief_id), None)
    if b is None:
        raise ArenaError("Woh brief nahi mila.")
    with session() as s:
        it = s.scalars(select(GArenaItem).where(GArenaItem.brief_id == brief_id, GArenaItem.game_id != "")
                       .order_by(GArenaItem.at.desc())).first()
        gid = hoola_game or (it.game_id if it else "")
    if not gid:
        raise ArenaError("Is brief ka Hoola game pehle banwaiye (arena run), ya game id dijiye.")
    g = G._get(TENANT, gid)
    good = G._good(g)
    if not good:
        raise ArenaError("Us Hoola game ka chalne wala version nahi hai.")
    base = G._pdir(TENANT, gid) / "duel"
    mine = play(_web(g, good[-1]["n"]), b["orientation"], base / "hoola")
    theirs = _play_url(rival_url, b["orientation"], base / "rival")
    rnd = random.Random(seed if seed is not None else int(time.time()))
    hoola_is_a = rnd.random() < 0.5
    A, Bx = (mine, theirs) if hoola_is_a else (theirs, mine)
    imgs = []
    for side in (A, Bx):
        for p in (side.get("shots") or [])[:2]:
            try:
                imgs.append(Path(p).read_bytes())
            except OSError:
                pass
    if not imgs:
        raise ArenaError("Dono mein se kisi ka screen nahi mila.")
    text = (f"Brief: {b['brief']}\nScreen: {b['orientation']}\n\nA measured: {facts_line(A)}\nB measured: {facts_line(Bx)}\n\n"
            "The first frames are A, the rest are B. Which game is better?")
    try:
        raw = parse_json(AI.ask_with_images(DUEL_SYSTEM, text, imgs[:4], max_tokens=700))
    except Exception as e:                              # noqa: BLE001
        raise ArenaError(f"Judge se jawab nahi aaya: {type(e).__name__}")
    pickw = str((raw or {}).get("winner") or "tie").strip().upper()[:1]
    winner = "tie" if pickw not in ("A", "B") else ("hoola" if (pickw == "A") == hoola_is_a else "rival")
    sc = {"hoola": (raw or {}).get("a" if hoola_is_a else "b"), "rival": (raw or {}).get("b" if hoola_is_a else "a")}
    row = GArenaDuel(brief_id=brief_id, rival=str(rival or "rival")[:60], rival_url=str(rival_url)[:500],
                     winner=winner, why=str((raw or {}).get("why") or "")[:500], scores=sc)
    with session() as s:
        s.add(row)
        s.flush()
        s.expunge(row)
    return {"brief": brief_id, "rival": row.rival, "winner": winner, "why": row.why, "scores": sc,
            "blind": "the judge saw A and B in a random order and was not told which was Hoola's"}


def duel_table() -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        rows = s.scalars(select(GArenaDuel).order_by(GArenaDuel.at.desc())).all()
        out: dict[str, dict[str, int]] = {}
        recent = []
        for d in rows:
            t = out.setdefault(d.rival, {"won": 0, "lost": 0, "tie": 0})
            t["won" if d.winner == "hoola" else ("lost" if d.winner == "rival" else "tie")] += 1
            if len(recent) < 12:
                recent.append({"brief": d.brief_id, "rival": d.rival, "winner": d.winner, "why": d.why,
                               "at": d.at.isoformat() if d.at else ""})
    for t in out.values():
        n = t["won"] + t["lost"] + t["tie"]
        t["win_pct"] = round(100 * t["won"] / n, 1) if n else None
    return {"rivals": out, "recent": recent}


def catalogue(genre: str = "", limit: int = 40) -> dict[str, Any]:
    bs = [b for b in brief_set() if not genre or b["genre"] == genre]
    return {"set": SET_V, "total": len(brief_set()), "genres": sorted(GENRES),
            "briefs": [{k: b[k] for k in ("id", "genre", "setting", "orientation", "brief")} for b in bs[:max(1, min(200, limit))]]}
