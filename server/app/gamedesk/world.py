"""v0.420 PROCEDURAL WORLD GENERATION (Hoola Game Engine plan Phase 7, Game Desk plan role 6 - the Procedural World
Generation Engineer): terrain, dungeons, cities and platformer levels from RULES and a SEED, made by CODE (numpy, no
model, no money), checked in code, previewed, walkable, and put into her game as Hoola's own HoolaWorld autoload.

What "good" means here (GAME_DESK_PLAN.md section 1) and how each is CHECKED, never assumed:
- same seed = same world: every world is generated TWICE and the two fingerprints (sha256 of the tiles + points)
  must match, or it is not saved;
- playable: reachability by flood fill from the spawn - every village / room / exit / goal must be reachable, the
  spawn may not be stuck, a cut-off landmass is NAMED with its share; a platformer level is walked by a jump graph
  built from HER jump height and width (a gap one tile too wide fails);
- generation time and size stated (ms, cells, bytes);
- a preview picture, a walkable link (Hoola builds a small explorer game around the world - its own code, no model -
  and plays it like any game: Godot headless run, Web export, Playwright playtest), and exports: world.json, the
  16-bit heightmap PNG and a terrain .glb mesh (checked by reading it back).

Kinds: terrain (fbm value noise, island mask, biomes from height + moisture, rivers by steepest descent, mountain
passes carved so the land joins up, villages), dungeon (rooms, a minimum spanning tree of corridors + a few loops,
exit = the farthest room), city (road grid with gaps, blocks, plots that each touch a road, buildings taller near
the centre, parks), level (side view: ground, gaps, steps, floating platforms, hazards, a goal flag).

A world waits for her OK (draft -> approved). Approved worlds of a Studio project go into every build as
HoolaWorld (`HoolaWorld.tile(x, y)`, `walkable`, `spawn`, `points`, `sprite`...), rebuilt with G.data_build - no
model call. Original by construction: rules + a seed, never a copy of a real game's map."""
from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import logging
import re
import secrets
import shutil
import struct
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import JSON, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import service as G

log = logging.getLogger("santosh.gamedesk")
FILE = "hoola_world.gd"
KEY = "procgen_dev"
KINDS = ("terrain", "dungeon", "city", "level")
MAX_CELLS = 256 * 256
_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gameworld")


class WorldError(G.GameError):
    pass


class GameWorld(Base):
    __tablename__ = "game_worlds"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gw"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    studio_id: Mapped[str] = mapped_column(String(40), default="", index=True)   # "" = a world of her own (no project)
    number: Mapped[str] = mapped_column(String(12), default="")
    key: Mapped[str] = mapped_column(String(40), default="")       # the name the game uses: HoolaWorld.tile(x, y, key)
    kind: Mapped[str] = mapped_column(String(12), default="terrain")
    seed: Mapped[int] = mapped_column(Integer, default=0)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(12), default="draft")   # draft | approved | rejected | failed
    words: Mapped[str] = mapped_column(Text, default="")
    checks: Mapped[dict] = mapped_column(JSON, default=dict)          # {errors, warnings, passed}
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
    fingerprint: Mapped[str] = mapped_column(String(64), default="")
    demo: Mapped[dict] = mapped_column(JSON, default=dict)            # {status, token, numbers, errors}
    demo_token: Mapped[str] = mapped_column(String(48), default="", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        GameWorld.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


# ================================================================ legends (tile id -> name, colour, walkable)
LEGEND: dict[str, list[tuple[str, str, bool]]] = {
    "terrain": [("deep_water", "#1d3f8f", False), ("shallow_water", "#3b6fd1", False), ("sand", "#e3d29b", True),
                ("grass", "#6fb24a", True), ("forest", "#2f7a35", True), ("hills", "#9a8f5a", True),
                ("mountain", "#7d7470", False), ("snow", "#f2f4f7", False), ("river", "#4f8ff0", True),
                ("village", "#d1563b", True), ("pass", "#b3a074", True)],
    "dungeon": [("wall", "#2a2a33", False), ("floor", "#b9ad94", True), ("corridor", "#8c826e", True),
                ("door", "#a0522d", True)],
    "city": [("park", "#79b85a", True), ("road", "#55585e", True), ("plot", "#d9d2c3", True),
             ("building", "#9c6b4e", False), ("water", "#3b6fd1", False), ("square", "#c9b48a", True)],
    "level": [("air", "#9fd3f5", True), ("ground", "#7a5230", False), ("platform", "#b07a43", False),
              ("hazard", "#d33b3b", True), ("goal", "#f2c230", True)],
}
VIEW = {"terrain": "top", "dungeon": "top", "city": "top", "level": "side"}


def _ids(kind: str) -> dict[str, int]:
    return {n: i for i, (n, _c, _w) in enumerate(LEGEND[kind])}


def _walk_mask(kind: str, tiles: np.ndarray) -> np.ndarray:
    ok = np.array([w for (_n, _c, w) in LEGEND[kind]], dtype=bool)
    return ok[tiles]


# ================================================================ params (her words -> numbers, clamped in code)
DEFAULTS = {
    "terrain": {"w": 160, "h": 160, "sea": 0.38, "mountains": 0.12, "moisture": 0.5, "island": True, "rivers": 5,
                "villages": 6},
    "dungeon": {"w": 64, "h": 48, "rooms": 12, "room_min": 4, "room_max": 10, "loops": 0.15, "treasure": 6},
    "city": {"w": 96, "h": 96, "block_min": 10, "block_max": 16, "road_gaps": 0.1, "parks": 0.1, "max_storeys": 12},
    "level": {"w": 220, "h": 18, "jump_h": 3, "jump_w": 4, "gaps": 0.12, "platforms": 0.08, "hazards": 0.05,
              "coins": 20},
}
LIMITS = {"w": (16, 400), "h": (12, 256), "sea": (0.0, 0.8), "mountains": (0.0, 0.4), "moisture": (0.0, 1.0),
          "rivers": (0, 20), "villages": (0, 30), "rooms": (2, 40), "room_min": (3, 12), "room_max": (4, 20),
          "loops": (0.0, 1.0), "treasure": (0, 40), "block_min": (6, 30), "block_max": (8, 40), "road_gaps": (0.0, 0.4),
          "parks": (0.0, 0.6), "max_storeys": (1, 80), "jump_h": (1, 8), "jump_w": (2, 10), "gaps": (0.0, 0.4),
          "platforms": (0.0, 0.4), "hazards": (0.0, 0.3), "coins": (0, 200)}


def clean_params(kind: str, params: dict | None) -> dict:
    if kind not in KINDS:
        raise WorldError("kind = " + " | ".join(KINDS))
    out = dict(DEFAULTS[kind])
    for k, v in (params or {}).items():
        if k not in out:
            continue
        if isinstance(out[k], bool):
            out[k] = bool(v)
            continue
        try:
            v = float(v)
        except (TypeError, ValueError):
            continue
        lo, hi = LIMITS.get(k, (v, v))
        v = min(max(v, lo), hi)
        out[k] = int(round(v)) if isinstance(out[k], int) else round(v, 3)
    if kind == "level":
        out["h"] = min(out["h"], 40)
    if kind == "dungeon" and out["room_max"] < out["room_min"] + 1:
        out["room_max"] = out["room_min"] + 1
    if kind == "city" and out["block_max"] < out["block_min"] + 1:
        out["block_max"] = out["block_min"] + 1
    while out["w"] * out["h"] > MAX_CELLS:
        out["w"] = int(out["w"] * 0.9)
        out["h"] = int(out["h"] * 0.9)
    return out


PLAN = """You set up a procedural world generator for a game. From her words pick the kind and the numbers.
kinds: terrain (open world / island / map), dungeon (rooms + corridors, caves), city (streets, blocks, buildings),
level (a side-view platformer level). Only these keys, numbers only:
terrain: w, h (cells, <= 256), sea (0-0.8 share of water), mountains (0-0.4), moisture (0-1), island (true/false),
rivers (0-20), villages (0-30)
dungeon: w, h, rooms (2-40), room_min, room_max (cells), loops (0-1 extra corridors), treasure (0-40)
city: w, h, block_min, block_max (cells), road_gaps (0-0.4), parks (0-0.6), max_storeys (1-80)
level: w (length in tiles), h (<= 40), jump_h (tiles the player jumps up), jump_w (tiles across), gaps, platforms,
hazards (0-0.4), coins
OUTPUT only JSON: {"kind": "...", "key": "short_snake_name", "params": {...}}"""


def plan_from_words(words: str, kind: str = "") -> dict:
    """Her words -> {kind, key, params}. The model only PICKS numbers; clean_params clamps them in code. Without a
    model (or on any error) the words are read by simple rules."""
    w = (words or "").lower()
    guess = kind if kind in KINDS else (
        "dungeon" if re.search(r"dungeon|cave|gufa|tahkhana|maze|bhool", w) else
        "city" if re.search(r"city|shahar|town|street|sadak|nagar", w) else
        "level" if re.search(r"platform|jump|level|mario|side.?scroll", w) else "terrain")
    got: dict = {}
    try:
        from . import ai
        raw = ai.ask(PLAN, f"Her words: {words}\nKind (if she named one): {kind or '-'}", max_tokens=400)
        m = re.search(r"\{.*\}", raw or "", re.S)
        got = json.loads(m.group(0)) if m else {}
    except Exception:                                   # noqa: BLE001 - rules are enough
        got = {}
    k = got.get("kind") if got.get("kind") in KINDS else guess
    if kind in KINDS:
        k = kind
    key = re.sub(r"[^a-z0-9_]", "", str(got.get("key") or k).lower().replace(" ", "_"))[:30] or k
    return {"kind": k, "key": key, "params": clean_params(k, got.get("params") if isinstance(got.get("params"), dict) else {})}


# ================================================================ generators (pure: same seed + params = same world)
def _fbm(rng: np.random.Generator, w: int, h: int, octaves: int = 5, base: int = 3) -> np.ndarray:
    out = np.zeros((h, w))
    amp, total = 1.0, 0.0
    for o in range(octaves):
        cells = base * (2 ** o)
        grid = rng.random((cells + 1, cells + 1))
        ys = np.linspace(0, cells, h, endpoint=False)
        xs = np.linspace(0, cells, w, endpoint=False)
        y0 = np.floor(ys).astype(int)
        x0 = np.floor(xs).astype(int)
        fy = ys - y0
        fx = xs - x0
        fy = fy * fy * (3 - 2 * fy)
        fx = fx * fx * (3 - 2 * fx)
        a = grid[np.ix_(y0, x0)]
        b = grid[np.ix_(y0, x0 + 1)]
        c = grid[np.ix_(y0 + 1, x0)]
        d = grid[np.ix_(y0 + 1, x0 + 1)]
        top = a + (b - a) * fx[None, :]
        bot = c + (d - c) * fx[None, :]
        out += amp * (top + (bot - top) * fy[:, None])
        total += amp
        amp *= 0.5
    out /= total
    lo, hi = out.min(), out.max()
    return (out - lo) / (hi - lo + 1e-12)


N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
N8 = N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))


def _components(mask: np.ndarray) -> tuple[np.ndarray, list[int]]:
    """4-connected components of a boolean mask: (labels, sizes) - label 0 = not in the mask."""
    h, w = mask.shape
    lab = np.zeros((h, w), dtype=np.int32)
    sizes = [0]
    cur = 0
    for y0 in range(h):
        for x0 in range(w):
            if not mask[y0, x0] or lab[y0, x0]:
                continue
            cur += 1
            n = 0
            q = deque([(y0, x0)])
            lab[y0, x0] = cur
            while q:
                y, x = q.popleft()
                n += 1
                for dy, dx in N4:
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and not lab[yy, xx]:
                        lab[yy, xx] = cur
                        q.append((yy, xx))
            sizes.append(n)
    return lab, sizes


def _bfs(mask: np.ndarray, start: tuple[int, int]) -> np.ndarray:
    """Steps from start over walkable cells (-1 = not reachable)."""
    h, w = mask.shape
    dist = np.full((h, w), -1, dtype=np.int32)
    y0, x0 = start
    if not (0 <= y0 < h and 0 <= x0 < w) or not mask[y0, x0]:
        return dist
    dist[y0, x0] = 0
    q = deque([(y0, x0)])
    while q:
        y, x = q.popleft()
        for dy, dx in N4:
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and dist[yy, xx] < 0:
                dist[yy, xx] = dist[y, x] + 1
                q.append((yy, xx))
    return dist


def _line(t: np.ndarray, a: tuple[int, int], b: tuple[int, int], val: int, only: set[int] | None = None) -> None:
    (y0, x0), (y1, x1) = a, b
    n = max(abs(y1 - y0), abs(x1 - x0), 1)
    for i in range(n + 1):
        y = int(round(y0 + (y1 - y0) * i / n))
        x = int(round(x0 + (x1 - x0) * i / n))
        if only is None or int(t[y, x]) in only:
            t[y, x] = val


def gen_terrain(seed: int, p: dict) -> dict:
    rng = np.random.default_rng(seed)
    w, h = p["w"], p["h"]
    I = _ids("terrain")
    height = _fbm(rng, w, h, 6, 3)
    if p["island"]:
        yy, xx = np.mgrid[0:h, 0:w]
        d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        height = height * 0.6 + (1 - np.clip(d, 0, 1.2) ** 2) * 0.55
        height = (height - height.min()) / (height.max() - height.min() + 1e-12)
    moist = _fbm(rng, w, h, 4, 2)
    moist = np.clip(moist + (p["moisture"] - 0.5), 0, 1)
    sea_q = float(np.quantile(height, p["sea"])) if p["sea"] > 0 else -1.0
    mtn_q = float(np.quantile(height, max(0.0, 1 - p["mountains"]))) if p["mountains"] > 0 else 2.0
    snow_q = float(np.quantile(height, max(0.0, 1 - p["mountains"] * 0.3))) if p["mountains"] > 0 else 2.0
    t = np.full((h, w), I["grass"], dtype=np.uint8)
    t[moist > 0.58] = I["forest"]
    t[height > (sea_q + (mtn_q - sea_q) * 0.72)] = I["hills"]
    t[height >= mtn_q] = I["mountain"]
    t[height >= snow_q] = I["snow"]
    t[height < sea_q + 0.025] = I["sand"]
    t[height < sea_q] = I["shallow_water"]
    t[height < sea_q - 0.06] = I["deep_water"]
    # rivers: from high land down the steepest slope to water (or a lake where it stops)
    land = (t != I["deep_water"]) & (t != I["shallow_water"])
    cand = np.argwhere(land & (height > (sea_q + mtn_q) / 2))
    rivers = to_sea = 0
    for _ in range(p["rivers"]):
        if not len(cand):
            break
        y, x = (int(v) for v in cand[rng.integers(len(cand))])
        seen: set[tuple[int, int]] = set()
        for _step in range(2 * (w + h)):
            if t[y, x] in (I["deep_water"], I["shallow_water"]):
                to_sea += 1
                break
            seen.add((y, x))
            if t[y, x] != I["snow"]:
                t[y, x] = I["river"]
            # downhill first; in a pit the river carves on through its lowest unvisited neighbour (like a real
            # river filling a hollow and spilling over), so rivers reach the sea instead of stopping as dashes
            nb = [(height[y + dy, x + dx], y + dy, x + dx) for dy, dx in N4
                  if 0 <= y + dy < h and 0 <= x + dx < w and (y + dy, x + dx) not in seen]
            if not nb:
                t[y, x] = I["shallow_water"]
                break
            _hv, y, x = min(nb)
        rivers += 1
    # passes: every other landmass of a real size joins the biggest one (a straight cut through mountains)
    walk = _walk_mask("terrain", t)
    lab, sizes = _components(walk)
    passes = 0
    if len(sizes) > 2:
        main = int(np.argmax(sizes))
        main_cells = np.argwhere(lab == main)
        for li in range(1, len(sizes)):
            if li == main or sizes[li] < 20:
                continue
            cells = np.argwhere(lab == li)
            c = cells[len(cells) // 2]
            dd = np.abs(main_cells - c).sum(axis=1)
            tgt = main_cells[int(np.argmin(dd))]
            before = t.copy()
            _line(t, (int(c[0]), int(c[1])), (int(tgt[0]), int(tgt[1])), I["pass"],
                  only={I["mountain"], I["snow"]})
            if (before != t).any():
                passes += 1
    walk = _walk_mask("terrain", t)
    lab, sizes = _components(walk)
    main = int(np.argmax(sizes)) if len(sizes) > 1 else 0
    spawn = _near_centre(lab == main, t == I["grass"])
    # villages: on grass of the main land, apart from each other
    vill: list[list[int]] = []
    grass = np.argwhere((lab == main) & (t == I["grass"]))
    gap = max(6, int(min(w, h) / 8))
    tries = 0
    while len(vill) < p["villages"] and len(grass) and tries < 400:
        tries += 1
        y, x = (int(v) for v in grass[rng.integers(len(grass))])
        if all(abs(y - vy) + abs(x - vx) >= gap for vx, vy in vill):
            vill.append([x, y])
            t[y, x] = I["village"]
    return {"tiles": t, "height": height, "points": {"spawn": spawn, "villages": vill},
            "extra": {"rivers": rivers, "rivers_to_sea": to_sea, "passes": passes}}


def _near_centre(mask: np.ndarray, prefer: np.ndarray | None = None) -> list[int]:
    h, w = mask.shape
    for m in ([mask & prefer] if prefer is not None else []) + [mask]:
        cells = np.argwhere(m)
        if len(cells):
            d = (cells[:, 0] - h / 2) ** 2 + (cells[:, 1] - w / 2) ** 2
            y, x = cells[int(np.argmin(d))]
            return [int(x), int(y)]
    return [0, 0]


def gen_dungeon(seed: int, p: dict) -> dict:
    rng = np.random.default_rng(seed)
    w, h = p["w"], p["h"]
    I = _ids("dungeon")
    t = np.full((h, w), I["wall"], dtype=np.uint8)
    rooms: list[tuple[int, int, int, int]] = []
    for _ in range(p["rooms"] * 30):
        if len(rooms) >= p["rooms"]:
            break
        rw = int(rng.integers(p["room_min"], p["room_max"] + 1))
        rh = int(rng.integers(p["room_min"], max(p["room_min"] + 1, int(p["room_max"] * 0.8)) + 1))
        if rw >= w - 2 or rh >= h - 2:
            continue
        x = int(rng.integers(1, w - rw - 1))
        y = int(rng.integers(1, h - rh - 1))
        if any(x < ox + ow + 1 and ox < x + rw + 1 and y < oy + oh + 1 and oy < y + rh + 1 for ox, oy, ow, oh in rooms):
            continue
        rooms.append((x, y, rw, rh))
        t[y:y + rh, x:x + rw] = I["floor"]
    cen = [(x + rw // 2, y + rh // 2) for x, y, rw, rh in rooms]
    edges: list[tuple[int, int]] = []
    if len(cen) > 1:                                    # Prim's minimum spanning tree over the room centres
        inside = {0}
        while len(inside) < len(cen):
            best = None
            for a in inside:
                for b in range(len(cen)):
                    if b in inside:
                        continue
                    d = abs(cen[a][0] - cen[b][0]) + abs(cen[a][1] - cen[b][1])
                    if best is None or d < best[0]:
                        best = (d, a, b)
            edges.append((best[1], best[2]))
            inside.add(best[2])
        extra = [(a, b) for a in range(len(cen)) for b in range(a + 1, len(cen)) if (a, b) not in edges and (b, a) not in edges]
        extra.sort(key=lambda e: abs(cen[e[0]][0] - cen[e[1]][0]) + abs(cen[e[0]][1] - cen[e[1]][1]))
        for e in extra[: max(0, int(round(len(cen) * p["loops"])))]:
            edges.append(e)
    for a, b in edges:
        (x0, y0), (x1, y1) = cen[a], cen[b]
        if rng.random() < 0.5:
            _line(t, (y0, x0), (y0, x1), I["corridor"], only={I["wall"]})
            _line(t, (y0, x1), (y1, x1), I["corridor"], only={I["wall"]})
        else:
            _line(t, (y0, x0), (y1, x0), I["corridor"], only={I["wall"]})
            _line(t, (y1, x0), (y1, x1), I["corridor"], only={I["wall"]})
    spawn = [cen[0][0], cen[0][1]] if cen else [1, 1]
    dist = _bfs(_walk_mask("dungeon", t), (spawn[1], spawn[0]))
    far = max(range(len(cen)), key=lambda i: dist[cen[i][1], cen[i][0]]) if cen else 0
    exit_ = [cen[far][0], cen[far][1]] if cen else spawn
    treasure: list[list[int]] = []
    for i in range(min(p["treasure"], len(rooms))):
        x, y, rw, rh = rooms[(i * 7 + 1) % len(rooms)]
        tx, ty = x + int(rng.integers(0, rw)), y + int(rng.integers(0, rh))
        if [tx, ty] not in (spawn, exit_) and [tx, ty] not in treasure:
            treasure.append([tx, ty])
    return {"tiles": t, "points": {"spawn": spawn, "exit": [exit_], "treasure": treasure,
                                   "rooms": [[c[0], c[1]] for c in cen]},
            "extra": {"rooms": len(rooms), "corridors": len(edges)}}


def gen_city(seed: int, p: dict) -> dict:
    rng = np.random.default_rng(seed)
    w, h = p["w"], p["h"]
    I = _ids("city")
    t = np.full((h, w), I["plot"], dtype=np.uint8)

    def cuts(n: int) -> list[int]:
        out, c = [0], 0
        while True:
            c += int(rng.integers(p["block_min"], p["block_max"] + 1))
            if c >= n - 4:
                break
            out.append(c)
        out.append(n - 2)
        return out

    xs, ys = cuts(w), cuts(h)
    for x in xs:
        t[:, x:x + 2] = I["road"]
    for y in ys:
        t[y:y + 2, :] = I["road"]
    # gaps: some inner road pieces become plots (never the outer ring) - then put back any that cut the network
    gaps = 0
    for i in range(1, len(xs) - 1):
        for j in range(len(ys) - 1):
            if rng.random() < p["road_gaps"]:
                y0, y1 = ys[j] + 2, ys[j + 1]
                seg = t[y0:y1, xs[i]:xs[i] + 2].copy()
                t[y0:y1, xs[i]:xs[i] + 2] = I["plot"]
                lab, sizes = _components(t == I["road"])
                if len(sizes) > 2:
                    t[y0:y1, xs[i]:xs[i] + 2] = seg
                else:
                    gaps += 1
    storeys = np.zeros((h, w), dtype=np.uint8)
    blocks = parks = buildings = 0
    cx, cy = w / 2, h / 2
    maxd = np.hypot(cx, cy)
    for j in range(len(ys) - 1):
        for i in range(len(xs) - 1):
            x0, x1 = xs[i] + 2, xs[i + 1]
            y0, y1 = ys[j] + 2, ys[j + 1]
            if x1 - x0 < 3 or y1 - y0 < 3:
                continue
            blocks += 1
            if rng.random() < p["parks"]:
                t[y0:y1, x0:x1] = I["park"]
                parks += 1
                continue
            # plots along the block edges facing a road, a building inset one cell; the inner core = a square
            for yy in range(y0, y1, 5):
                for xx in range(x0, x1, 5):
                    bx1, by1 = min(xx + 4, x1), min(yy + 4, y1)
                    ry0, ry1, rx0, rx1 = max(0, yy - 2), min(h, by1 + 2), max(0, xx - 2), min(w, bx1 + 2)
                    edge = bool((t[ry0:ry1, rx0:rx1] == I["road"]).any())   # a REAL road beside it, not a removed one
                    if not edge:
                        t[yy:by1, xx:bx1] = I["square"]
                        continue
                    if bx1 - xx >= 2 and by1 - yy >= 2:
                        t[yy:by1, xx:bx1] = I["building"]
                        d = np.hypot((xx + bx1) / 2 - cx, (yy + by1) / 2 - cy) / maxd
                        s = max(1, int(round(p["max_storeys"] * (1 - d) ** 1.6 * (0.6 + 0.4 * rng.random()))))
                        storeys[yy:by1, xx:bx1] = min(s, 255)
                        buildings += 1
    spawn = _near_centre(t == I["road"])
    return {"tiles": t, "height": storeys.astype(float) / max(1, p["max_storeys"]),
            "points": {"spawn": spawn}, "extra": {"blocks": blocks, "parks": parks, "buildings": buildings,
                                                  "road_gaps": gaps, "storeys_max": int(storeys.max())}}


def gen_level(seed: int, p: dict) -> dict:
    """A side-view level (y = 0 is the TOP row). Ground columns walk up / down by at most jump_h - 1, gaps are at
    most jump_w - 1 wide, so the rules make it passable; the jump-graph check below PROVES it."""
    rng = np.random.default_rng(seed)
    w, h = p["w"], p["h"]
    I = _ids("level")
    jh, jw = int(p["jump_h"]), int(p["jump_w"])
    t = np.full((h, w), I["air"], dtype=np.uint8)
    ground = h - 4
    x = 0
    surf = []
    coins: list[list[int]] = []
    while x < w:
        after_gap = bool(surf) and surf[-1] is None     # never two gaps in a row (that is one gap too wide to jump)
        if 8 < x < w - 10 and not after_gap and rng.random() < p["gaps"]:
            gw = int(rng.integers(1, max(2, jw)))
            if rng.random() < p["platforms"] * 3 and gw >= 2:
                py = max(2, ground - int(rng.integers(1, max(2, jh))))
                t[py, x:x + gw] = I["platform"]
            surf += [None] * gw
            x += gw
            continue
        if 6 < x < w - 8 and surf and surf[-1] is not None and rng.random() < 0.18:   # steps only from solid ground
            ground = int(np.clip(ground + int(rng.integers(-(jh - 1), jh)), 4, h - 2))
        run = int(rng.integers(3, 9))
        for i in range(run):
            if x >= w:
                break
            t[ground:, x] = I["ground"]
            surf.append(ground)
            mid = (0 < i < run - 1 and (len(surf) < 2 or surf[-2] == ground)      # spikes never on a jump edge or
                   and t[ground - 1, x - 1] != I["hazard"])                         # a step, never two side by side
            if 6 < x < w - 8 and mid and rng.random() < p["hazards"] and t[ground - 1, x] == I["air"]:
                t[ground - 1, x] = I["hazard"]
            elif rng.random() < 0.08 and len(coins) < p["coins"]:
                coins.append([x, max(1, ground - 2)])
            x += 1
    goal_x = w - 3
    gy = next((surf[i] for i in range(goal_x, -1, -1) if i < len(surf) and surf[i] is not None), h - 4)
    t[gy - 1, goal_x] = I["goal"]
    return {"tiles": t, "points": {"spawn": [1, int(surf[1] - 1 if surf[1] is not None else h - 5)],
                                   "goal": [[goal_x, int(gy - 1)]], "coins": coins},
            "extra": {"jump_h": jh, "jump_w": jw}}


GEN = {"terrain": gen_terrain, "dungeon": gen_dungeon, "city": gen_city, "level": gen_level}


# ================================================================ checks (in code; a failed one is named)
def _fingerprint(g: dict) -> str:
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(g["tiles"]).tobytes())
    h.update(json.dumps(g["points"], sort_keys=True).encode())
    return h.hexdigest()


def can_jump(rise: float, across: float, jump_h: float, jump_w: float) -> bool:
    """A jump of `across` tiles that ends `rise` tiles higher (negative = lower). The arc is a parabola that peaks at
    jump_h halfway along jump_w and the player may steer in the air, so up to half the width the full height is
    there; past it the arc comes down: rise <= jump_h * (1 - (2a/w - 1)^2). Never wider than jump_w."""
    a = abs(across)
    if a > jump_w + 1e-9:
        return False
    if a <= jump_w / 2:
        return rise <= jump_h + 1e-9
    return rise <= jump_h * (1 - (2 * a / jump_w - 1) ** 2) + 1e-9


def level_reach(tiles: np.ndarray, spawn: list[int], jump_h: int, jump_w: int) -> np.ndarray:
    """Standable cells reachable from the spawn by walking, falling and jumping along the real arc (can_jump), with
    head room checked on the way. Returns a boolean mask over the grid (y = 0 is the top row)."""
    I = _ids("level")
    h, w = tiles.shape
    solid = (tiles == I["ground"]) | (tiles == I["platform"])
    free = ~solid & (tiles != I["hazard"])
    stand = np.zeros_like(solid)
    stand[:-1, :] = free[:-1, :] & solid[1:, :]
    seen = np.zeros_like(stand)
    sx, sy = spawn
    while sy < h - 1 and not stand[sy, sx] and free[sy, sx]:
        sy += 1
    if not stand[sy, sx]:
        return seen
    q = deque([(sy, sx)])
    seen[sy, sx] = True
    while q:
        y, x = q.popleft()
        for dx in range(-jump_w, jump_w + 1):
            xx = x + dx
            if not (0 <= xx < w):
                continue
            for yy in range(max(0, y - jump_h), h):
                if not stand[yy, xx] or seen[yy, xx]:
                    continue
                rise = y - yy
                lo, hi = (x, xx) if x <= xx else (xx, x)
                if abs(dx) <= 1 and rise <= 0:          # walk, or step off the edge and fall down that column
                    ok = bool(free[y:yy + 1, xx].all()) and bool(free[y, lo:hi + 1].all())
                else:
                    top = min(y, yy)
                    # the arc flies OVER the standing row (a spike between is jumped), so the head-room row above the
                    # higher end must be clear all the way across, plus the column it rises from and lands in
                    ok = (can_jump(rise, dx, jump_h, jump_w) and top >= 1 and bool(free[top - 1:y + 1, x].all())
                          and bool(free[top - 1, lo:hi + 1].all()) and bool(free[top - 1:yy + 1, xx].all()))
                if ok:
                    seen[yy, xx] = True
                    q.append((yy, xx))
    return seen


def check(kind: str, g: dict, p: dict) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    passed: list[str] = []
    t = g["tiles"]
    pts = g["points"]
    walk = _walk_mask(kind, t)
    sx, sy = pts["spawn"]
    if kind == "level":
        reach = level_reach(t, pts["spawn"], int(p["jump_h"]), int(p["jump_w"]))
        gx, gy = pts["goal"][0]
        if reach[gy, gx]:
            passed.append(f"the goal is reachable with jump height {p['jump_h']} and width {p['jump_w']} tiles")
        else:
            errors.append(f"the goal at x={gx} cannot be reached with jumps of {p['jump_h']} up / {p['jump_w']} across")
        far = int(np.argwhere(reach)[:, 1].max()) if reach.any() else 0
        if far < gx:
            errors.append(f"the player gets stuck at x={far} of {t.shape[1]}")
        coins_ok = sum(1 for cx, cy in pts.get("coins", [])
                       if reach[cy:min(t.shape[0], cy + int(p["jump_h"]) + 2), max(0, cx - 1):cx + 2].any())
        if pts.get("coins"):
            passed.append(f"{coins_ok} of {len(pts['coins'])} coins over a reachable spot")
        return {"errors": errors, "warnings": warnings, "passed": passed, "reachable_share": round(float(reach.sum()) /
                max(1, int(level_reach(t, pts['spawn'], 99, 99).sum())), 3)}
    if not walk[sy, sx]:
        errors.append(f"the spawn at {sx},{sy} is not on walkable ground")
    dist = _bfs(walk, (sy, sx))
    open_n = sum(1 for dy, dx in N4 if 0 <= sy + dy < t.shape[0] and 0 <= sx + dx < t.shape[1] and walk[sy + dy, sx + dx])
    if walk[sy, sx] and open_n == 0:
        errors.append("the spawn is stuck: no walkable cell next to it")
    elif walk[sy, sx]:
        passed.append("the spawn has room to move")
    reach = int((dist >= 0).sum())
    total = int(walk.sum())
    share = reach / max(1, total)
    for name, lst in pts.items():
        if name in ("spawn",) or not isinstance(lst, list):
            continue
        bad = [q for q in lst if isinstance(q, list) and len(q) == 2 and dist[q[1], q[0]] < 0]
        if bad:
            errors.append(f"{len(bad)} of {len(lst)} {name} cannot be reached from the spawn (first at {bad[0][0]},{bad[0][1]})")
        elif lst:
            passed.append(f"all {len(lst)} {name} reachable from the spawn")
    if kind == "terrain":
        if share < 0.85:
            warnings.append(f"{round((1 - share) * 100)}% of the land is cut off from the spawn (islands or walled valleys)")
        else:
            passed.append(f"{round(share * 100)}% of the walkable land is reachable")
        water = float(np.isin(t, [0, 1]).mean())
        passed.append(f"water {round(water * 100)}% (asked {round(p['sea'] * 100)}%)")
        if g["extra"].get("rivers"):
            passed.append(f"{g['extra']['rivers_to_sea']} of {g['extra']['rivers']} rivers reach the sea or a lake")
    if kind == "dungeon" and pts.get("exit"):
        ex, ey = pts["exit"][0]
        if dist[ey, ex] >= 0:
            passed.append(f"the exit is {int(dist[ey, ex])} steps from the spawn")
        if g["extra"]["rooms"] < max(2, p["rooms"] // 2):
            warnings.append(f"only {g['extra']['rooms']} of {p['rooms']} rooms fitted (the map is small for that many)")
    if kind == "city":
        lab, sizes = _components(t == _ids("city")["road"])
        if len(sizes) > 2:
            errors.append(f"the roads fall into {len(sizes) - 1} separate pieces")
        else:
            passed.append("every road joins one network")
        b = t == _ids("city")["building"]
        rd = t == _ids("city")["road"]
        lab_b, bsz = _components(b)
        no_front = 0
        for li in range(1, len(bsz)):
            cells = np.argwhere(lab_b == li)
            near = False
            for y, x in cells:
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < t.shape[0] and 0 <= xx < t.shape[1] and rd[yy, xx]:
                            near = True
                            break
                    if near:
                        break
                if near:
                    break
            no_front += 0 if near else 1
        if no_front:
            warnings.append(f"{no_front} buildings have no road within 2 cells")
        else:
            passed.append(f"all {len(bsz) - 1} buildings face a road")
    return {"errors": errors, "warnings": warnings, "passed": passed, "reachable_share": round(share, 3)}


def generate(kind: str, seed: int, params: dict) -> dict:
    """Generate TWICE (same seed must give the same world), check, and return everything."""
    p = clean_params(kind, params)
    t0 = time.perf_counter()
    g = GEN[kind](int(seed), p)
    ms = round((time.perf_counter() - t0) * 1000, 1)
    g2 = GEN[kind](int(seed), p)
    fp, fp2 = _fingerprint(g), _fingerprint(g2)
    ch = check(kind, g, p)
    if fp != fp2:
        ch["errors"].insert(0, "the same seed gave a different world (not repeatable)")
    else:
        ch["passed"].insert(0, "same seed = same world (generated twice, fingerprints match)")
    counts = {LEGEND[kind][i][0]: int(n) for i, n in enumerate(np.bincount(g["tiles"].ravel(), minlength=len(LEGEND[kind]))) if n}
    stats = {"ms": ms, "w": p["w"], "h": p["h"], "cells": p["w"] * p["h"], "tiles": counts, **g.get("extra", {}),
             "reachable_share": ch.pop("reachable_share", None)}
    return {"g": g, "p": p, "fingerprint": fp, "checks": ch, "stats": stats}


# ================================================================ files: preview, json, heightmap, glb, autoload
def _rgb(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def preview_png(kind: str, g: dict, scale: int = 0) -> bytes:
    from PIL import Image
    t = g["tiles"]
    h, w = t.shape
    scale = scale or max(1, min(6, 768 // max(w, h)))
    pal = np.array([_rgb(c) for (_n, c, _w) in LEGEND[kind]], dtype=np.uint8)
    img = pal[t]
    if kind == "terrain" and g.get("height") is not None:      # light shading from the height (reads as relief)
        sh = np.clip(0.82 + 0.35 * (g["height"] - 0.5), 0.6, 1.15)[..., None]
        img = np.clip(img.astype(float) * sh, 0, 255).astype(np.uint8)
    im = Image.fromarray(img, "RGB").resize((w * scale, h * scale), Image.NEAREST)
    from PIL import ImageDraw
    d = ImageDraw.Draw(im)
    sx, sy = g["points"]["spawn"]
    r = max(2, scale)
    d.ellipse([sx * scale - r, sy * scale - r, sx * scale + scale + r, sy * scale + scale + r], outline=(255, 255, 255), width=2)
    for name, col in (("exit", (255, 220, 0)), ("goal", (255, 220, 0)), ("villages", (255, 255, 255)), ("treasure", (255, 200, 60))):
        for q in g["points"].get(name, []):
            d.rectangle([q[0] * scale, q[1] * scale, q[0] * scale + scale, q[1] * scale + scale], outline=col)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def heightmap_png(g: dict) -> bytes | None:
    if g.get("height") is None:
        return None
    from PIL import Image
    a = (np.clip(g["height"], 0, 1) * 65535).astype(np.uint16)
    buf = io.BytesIO()
    Image.fromarray(a).save(buf, "PNG")
    return buf.getvalue()


def terrain_glb(kind: str, g: dict, cell: float = 1.0, relief: float = 12.0, step: int = 0) -> bytes:
    """A glTF 2.0 binary mesh of the world (vertex colours from the legend, heights from the height field). Plain
    numpy -> bytes; read back by read_glb() before it is kept."""
    t = g["tiles"]
    h, w = t.shape
    step = step or max(1, int(np.ceil(max(w, h) / 160)))
    ys = np.arange(0, h, step)
    xs = np.arange(0, w, step)
    hf = g.get("height")
    hh = (hf[np.ix_(ys, xs)] if hf is not None else np.zeros((len(ys), len(xs)))) * relief
    if kind == "terrain":
        water = np.isin(t[np.ix_(ys, xs)], [0, 1])
        sea = float(np.min(hh[~water])) if (~water).any() else 0.0
        hh = np.where(water, min(sea, float(hh.min())), hh)
    gx, gz = np.meshgrid(xs * cell, ys * cell)
    pos = np.stack([gx, hh, gz], axis=-1).reshape(-1, 3).astype(np.float32)
    pal = np.array([_rgb(c) for (_n, c, _w) in LEGEND[kind]], dtype=np.float32) / 255.0
    col = np.concatenate([pal[t[np.ix_(ys, xs)]].reshape(-1, 3), np.ones((pos.shape[0], 1), np.float32)], axis=1).astype(np.float32)
    ny, nx = len(ys), len(xs)
    idx = []
    for y in range(ny - 1):
        a = y * nx + np.arange(nx - 1)
        b = a + 1
        c = a + nx
        d = c + 1
        idx.append(np.stack([a, c, b, b, c, d], axis=1).ravel())
    ind = np.concatenate(idx).astype(np.uint32) if idx else np.zeros(0, np.uint32)
    blobs = [pos.tobytes(), col.tobytes(), ind.tobytes()]
    offs, cur = [], 0
    for b in blobs:
        offs.append(cur)
        cur += len(b)
        cur += (-cur) % 4
    binbuf = b"".join(b + b"\0" * ((-len(b)) % 4) for b in blobs)
    gltf = {"asset": {"version": "2.0", "generator": "Hoola procedural world"},
            "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0, "name": "world"}],
            "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "COLOR_0": 1}, "indices": 2, "mode": 4}]}],
            "buffers": [{"byteLength": len(binbuf)}],
            "bufferViews": [{"buffer": 0, "byteOffset": offs[0], "byteLength": len(blobs[0]), "target": 34962},
                            {"buffer": 0, "byteOffset": offs[1], "byteLength": len(blobs[1]), "target": 34962},
                            {"buffer": 0, "byteOffset": offs[2], "byteLength": len(blobs[2]), "target": 34963}],
            "accessors": [{"bufferView": 0, "componentType": 5126, "count": int(pos.shape[0]), "type": "VEC3",
                           "min": [float(v) for v in pos.min(axis=0)], "max": [float(v) for v in pos.max(axis=0)]},
                          {"bufferView": 1, "componentType": 5126, "count": int(col.shape[0]), "type": "VEC4"},
                          {"bufferView": 2, "componentType": 5125, "count": int(ind.shape[0]), "type": "SCALAR"}]}
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * ((-len(js)) % 4)
    total = 12 + 8 + len(js) + 8 + len(binbuf)
    return (struct.pack("<III", 0x46546C67, 2, total) + struct.pack("<II", len(js), 0x4E4F534A) + js
            + struct.pack("<II", len(binbuf), 0x004E4942) + binbuf)


def read_glb(data: bytes) -> dict:
    """Parse a .glb back: header, JSON chunk, BIN chunk lengths and that every accessor fits its buffer view."""
    magic, ver, total = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67 or ver != 2 or total != len(data):
        raise WorldError("glb header wrong")
    jl, jt = struct.unpack_from("<II", data, 12)
    js = json.loads(data[20:20 + jl])
    bl, bt = struct.unpack_from("<II", data, 20 + jl)
    if jt != 0x4E4F534A or bt != 0x004E4942 or bl != js["buffers"][0]["byteLength"]:
        raise WorldError("glb chunks wrong")
    size = {"VEC3": 12, "VEC4": 16, "SCALAR": 4}
    for a in js["accessors"]:
        v = js["bufferViews"][a["bufferView"]]
        if a["count"] * size[a["type"]] > v["byteLength"] or v["byteOffset"] + v["byteLength"] > bl:
            raise WorldError("glb accessor out of its buffer")
    n_ind = js["accessors"][2]["count"]
    return {"vertices": js["accessors"][0]["count"], "triangles": n_ind // 3}


def world_data(r: GameWorld, g: dict) -> dict:
    t = g["tiles"]
    d = {"kind": r.kind, "view": VIEW[r.kind], "w": int(t.shape[1]), "h": int(t.shape[0]), "seed": int(r.seed),
         "version": int(r.version), "fingerprint": r.fingerprint[:16],
         "legend": [{"id": i, "name": n, "color": c, "walk": wk} for i, (n, c, wk) in enumerate(LEGEND[r.kind])],
         "tiles_b64": base64.b64encode(np.ascontiguousarray(t, dtype=np.uint8).tobytes()).decode(),
         "points": g["points"], "params": r.params}
    if g.get("height") is not None:
        d["height_b64"] = base64.b64encode((np.clip(g["height"], 0, 1) * 255).astype(np.uint8).tobytes()).decode()
    return d


GD_FUNCS = '''
var _cache := {}

func keys() -> Array:
	return WORLDS.keys()

func _w(key: String) -> Dictionary:
	if key == "":
		return WORLDS[WORLDS.keys()[0]] if WORLDS.size() > 0 else {}
	return WORLDS.get(key, {})

func _key(key: String) -> String:
	return key if key != "" else (String(WORLDS.keys()[0]) if WORLDS.size() > 0 else "")

func _tiles(key: String) -> PackedByteArray:
	var k := _key(key)
	if not _cache.has(k):
		_cache[k] = Marshalls.base64_to_raw(String(_w(k).get("tiles_b64", "")))
	return _cache[k]

func size(key: String = "") -> Vector2i:
	var w := _w(key)
	return Vector2i(int(w.get("w", 0)), int(w.get("h", 0)))

func tile(x: int, y: int, key: String = "") -> int:
	var s := size(key)
	if x < 0 or y < 0 or x >= s.x or y >= s.y:
		return -1
	return _tiles(key)[y * s.x + x]

func tile_name(id: int, key: String = "") -> String:
	var lg: Array = _w(key).get("legend", [])
	return String(lg[id]["name"]) if id >= 0 and id < lg.size() else ""

func walkable(x: int, y: int, key: String = "") -> bool:
	var id := tile(x, y, key)
	var lg: Array = _w(key).get("legend", [])
	return id >= 0 and id < lg.size() and bool(lg[id]["walk"])

func solid(x: int, y: int, key: String = "") -> bool:
	return tile(x, y, key) >= 0 and not walkable(x, y, key)

func color(id: int, key: String = "") -> Color:
	var lg: Array = _w(key).get("legend", [])
	return Color(String(lg[id]["color"])) if id >= 0 and id < lg.size() else Color.BLACK

func height(x: int, y: int, key: String = "") -> float:
	var w := _w(key)
	if not w.has("height_b64"):
		return 0.0
	var k := _key(key) + "#h"
	if not _cache.has(k):
		_cache[k] = Marshalls.base64_to_raw(String(w["height_b64"]))
	var s := size(key)
	if x < 0 or y < 0 or x >= s.x or y >= s.y:
		return 0.0
	return float(_cache[k][y * s.x + x]) / 255.0

func spawn(key: String = "") -> Vector2i:
	var p: Array = _w(key).get("points", {}).get("spawn", [0, 0])
	return Vector2i(int(p[0]), int(p[1]))

func points(name: String, key: String = "") -> Array:
	var out: Array = []
	for p in _w(key).get("points", {}).get(name, []):
		out.append(Vector2i(int(p[0]), int(p[1])))
	return out

func image(key: String = "") -> Image:
	var s := size(key)
	var img := Image.create(max(1, s.x), max(1, s.y), false, Image.FORMAT_RGBA8)
	var cols: Array = []
	for e in _w(key).get("legend", []):
		cols.append(Color(String(e["color"])))
	var t := _tiles(key)
	for y in s.y:
		for x in s.x:
			var id: int = t[y * s.x + x]
			img.set_pixel(x, y, cols[id] if id < cols.size() else Color.BLACK)
	return img

func texture(key: String = "") -> ImageTexture:
	var k := _key(key) + "#tex"
	if not _cache.has(k):
		_cache[k] = ImageTexture.create_from_image(image(key))
	return _cache[k]

func sprite(key: String = "", cell: float = 8.0) -> Sprite2D:
	var sp := Sprite2D.new()
	sp.texture = texture(key)
	sp.centered = false
	sp.scale = Vector2(cell, cell)
	sp.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	return sp
'''


def gd(worlds: dict[str, dict]) -> str:
    """HoolaWorld autoload: written by Hoola from the approved worlds, never by the model."""
    from .bible import _gd
    return ('extends Node\n# HoolaWorld (an autoload): the game\'s approved generated worlds (tiles, points, heights).\n'
            '# Written by Hoola Studio from a seed + rules; do not edit (approve a world in the Studio and rebuild).\n'
            f'const WORLDS := {_gd(worlds)}\n' + GD_FUNCS)


# ================================================================ store + jobs
def _root(tenant: str) -> Path:
    return G.root() / (re.sub(r"[^\w-]", "_", tenant)[:64] or "t") / "worlds"


def _wdir(r: GameWorld) -> Path:
    return _root(r.tenant_id) / r.id


def _studio(tenant: str, ref: str):
    from . import studio as S
    with session() as s:
        r = S._studio(s, tenant, ref)
        s.expunge(r)
    return r


def _get(s, tenant: str, ref: str) -> GameWorld:
    ref = str(ref or "").strip()
    q = select(GameWorld).where(GameWorld.tenant_id == tenant)
    r = s.scalars(q.where(GameWorld.id == ref)).first() or s.scalars(q.where(GameWorld.number == ref.upper())).first()
    if r is None:
        raise WorldError("Yeh world nahi mila (W-001 dijiye).")
    return r


def _next_number(s, tenant: str) -> str:
    n = len(s.scalars(select(GameWorld.id).where(GameWorld.tenant_id == tenant)).all()) + 1
    return f"W-{n:03d}"


def _sig(token: str) -> str:
    from ..config import get_settings
    key = (getattr(get_settings(), "api_key", "") or "hoola-world").encode()
    return hmac.new(key, f"world:{token}".encode(), "sha256").hexdigest()[:16]


def file_url(r: GameWorld, name: str) -> str:
    return f"/api/gamedesk/world/{r.id}/file/{name}?sig={_sig(r.id + name)}"


def world_file(wid: str, name: str, sig: str) -> Path | None:
    if not re.fullmatch(r"gw_[A-Za-z0-9_-]{4,40}", str(wid or "")) or name not in FILES or not hmac.compare_digest(_sig(wid + name), str(sig or "")):
        return None
    ensure_table()
    with session() as s:
        r = s.get(GameWorld, wid)
        if r is None:
            return None
        s.expunge(r)
    p = _wdir(r) / name
    return p if p.is_file() else None


FILES = ("preview.png", "world.json", "heightmap.png", "world.glb")


def view(r: GameWorld) -> dict[str, Any]:
    files = {n: file_url(r, n) for n in FILES if (_wdir(r) / n).is_file()}
    demo = dict(r.demo or {})
    if demo.get("token") and demo.get("status") == "done":
        demo["play_url"] = G.play_url(demo["token"])
    return {"id": r.id, "number": r.number, "key": r.key, "kind": r.kind, "seed": r.seed, "params": r.params,
            "version": r.version, "status": r.status, "words": r.words, "studio_id": r.studio_id,
            "checks": r.checks or {}, "stats": r.stats or {}, "fingerprint": (r.fingerprint or "")[:16],
            "files": files, "demo": demo, "at": r.created_at.isoformat() if r.created_at else ""}


def make(tenant: str, words: str = "", kind: str = "", seed: int | None = None, params: dict | None = None,
         studio: str = "", key: str = "") -> dict[str, Any]:
    """Generate a world from her words (or exact params) -> checked, files written, a DRAFT for her OK. No money."""
    ensure_table()
    plan = plan_from_words(words, kind) if (words and not params) else {"kind": kind or "terrain", "key": key, "params": params or {}}
    k = plan["kind"]
    if k not in KINDS:
        raise WorldError("kind = " + " | ".join(KINDS))
    p = clean_params(k, {**plan.get("params", {}), **(params or {})})
    sid = _studio(tenant, studio).id if studio else ""
    seed = int(seed) if seed is not None else secrets.randbelow(2_000_000_000)
    res = generate(k, seed, p)
    key = re.sub(r"[^a-z0-9_]", "", (key or plan.get("key") or k).lower())[:30] or k
    with session() as s:
        prev = s.scalars(select(GameWorld).where(GameWorld.tenant_id == tenant, GameWorld.studio_id == sid,
                                                GameWorld.key == key)).all()
        r = GameWorld(tenant_id=tenant, studio_id=sid, number=_next_number(s, tenant), key=key, kind=k, seed=seed,
                      params=p, version=max([x.version for x in prev] or [0]) + 1, words=(words or "")[:600],
                      status="failed" if res["checks"]["errors"] else "draft", checks=res["checks"], stats=res["stats"],
                      fingerprint=res["fingerprint"])
        s.add(r)
        s.flush()
        s.expunge(r)
    _write_files(r, res["g"])
    return view(r)


def _write_files(r: GameWorld, g: dict) -> None:
    d = _wdir(r)
    d.mkdir(parents=True, exist_ok=True)
    (d / "preview.png").write_bytes(preview_png(r.kind, g))
    (d / "world.json").write_text(json.dumps(world_data(r, g), separators=(",", ":")), encoding="utf-8")
    hm = heightmap_png(g)
    if hm:
        (d / "heightmap.png").write_bytes(hm)
    if r.kind in ("terrain", "city"):
        glb = terrain_glb(r.kind, g)
        info = read_glb(glb)
        (d / "world.glb").write_bytes(glb)
        with session() as s:
            row = s.get(GameWorld, r.id)
            row.stats = {**(row.stats or {}), "glb": info, "glb_kb": round(len(glb) / 1024)}
            r.stats = row.stats


def regenerate(tenant: str, ref: str) -> GameWorld:
    """The saved world back from its seed + params (the files are rebuilt, the fingerprint must match)."""
    with session() as s:
        r = _get(s, tenant, ref)
        s.expunge(r)
    g = GEN[r.kind](r.seed, clean_params(r.kind, r.params))
    if _fingerprint(g) != r.fingerprint:
        raise WorldError(f"{r.number} ka seed ab alag world deta hai (generator badla?) - naya world banaiye.")
    return r


def _load_g(r: GameWorld) -> dict:
    return GEN[r.kind](r.seed, clean_params(r.kind, r.params))


def approve(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _get(s, tenant, ref)
        if r.status == "failed":
            raise WorldError("Is world ki jaanch fail hai: " + "; ".join((r.checks or {}).get("errors", [])[:2]))
        for o in s.scalars(select(GameWorld).where(GameWorld.tenant_id == tenant, GameWorld.studio_id == r.studio_id,
                                                   GameWorld.key == r.key, GameWorld.status == "approved")).all():
            if o.id != r.id:
                o.status = "rejected"
        r.status = "approved"
        r.updated_at = now()
        s.flush()
        s.expunge(r)
    return view(r)


def reject(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _get(s, tenant, ref)
        r.status = "rejected"
        s.flush()
        s.expunge(r)
    return view(r)


def worlds(tenant: str, studio: str = "") -> list[dict[str, Any]]:
    ensure_table()
    sid = _studio(tenant, studio).id if studio else None
    with session() as s:
        q = select(GameWorld).where(GameWorld.tenant_id == tenant)
        if sid is not None:
            q = q.where(GameWorld.studio_id == sid)
        rows = s.scalars(q.order_by(GameWorld.created_at.desc())).all()[:40]
        for r in rows:
            s.expunge(r)
    return [view(r) for r in rows]


def get(tenant: str, ref: str) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        r = _get(s, tenant, ref)
        s.expunge(r)
    return view(r)


def for_game(tenant: str, game_id: str) -> tuple[str, dict[str, Path]] | None:
    """(hoola_world.gd, {}) from the APPROVED worlds of this game's Studio project, else None."""
    from . import studio as S
    ensure_table()
    with session() as s:
        st = s.scalars(select(S.GameStudio).where(S.GameStudio.tenant_id == tenant, S.GameStudio.game_id == game_id)).first()
        if st is None:
            return None
        rows = s.scalars(select(GameWorld).where(GameWorld.tenant_id == tenant, GameWorld.studio_id == st.id,
                                                 GameWorld.status == "approved").order_by(GameWorld.created_at)).all()
        for r in rows:
            s.expunge(r)
    if not rows:
        return None
    data = {}
    for r in rows:
        p = _wdir(r) / "world.json"
        data[r.key] = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else world_data(r, _load_g(r))
    return gd(data), {}


def apply(tenant: str, studio: str) -> dict[str, Any]:
    """The approved worlds into the live game: same code + HoolaWorld, the usual checks (no model call)."""
    st = _studio(tenant, studio)
    if for_game(tenant, st.game_id) is None:
        raise WorldError("Koi approved world nahi; pehle world OK kijiye.")
    try:
        from . import bible as B
        bv = B.view(tenant, st.id)["version"]
    except Exception:                                   # noqa: BLE001
        bv = 0
    G.data_build(tenant, st.game_id, bv, words="World game mein")
    return {"ok": True, "say": "Approved worlds game mein ja rahe hain (rebuild chal raha hai)."}


# ================================================================ walk-it demo (Hoola's own explorer, no model)
DEMO_TOP = '''extends Node
# Hoola world explorer (written by Hoola, not by a model): walk the generated world with arrows / WASD or a tap.
var cell := 8.0
var key := ""
var pos := Vector2i.ZERO
var root: Node2D
var me: ColorRect
var cam: Camera2D
var hold := 0.0
var steps := 0

func _ready() -> void:
	key = String(HoolaWorld.keys()[0])
	var s := HoolaWorld.size(key)
	cell = clamp(floor(900.0 / max(s.x, s.y)), 3.0, 14.0)
	root = Node2D.new()
	add_child(root)
	root.add_child(HoolaWorld.sprite(key, cell))
	me = ColorRect.new()
	me.color = Color(1, 1, 1)
	me.size = Vector2(cell, cell)
	root.add_child(me)
	cam = Camera2D.new()
	cam.zoom = Vector2(2, 2)
	root.add_child(cam)
	cam.make_current()
	pos = HoolaWorld.spawn(key)
	_place()
	HoolaProbe.state("state", "playing")

func _place() -> void:
	me.position = Vector2(pos) * cell
	cam.position = me.position
	HoolaProbe.state("score", steps)

func _try(d: Vector2i) -> void:
	var n := pos + d
	if HoolaWorld.walkable(n.x, n.y, key):
		pos = n
		steps += 1
		_place()

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed:
		var vp := get_viewport().get_visible_rect().size
		var v: Vector2 = event.position - vp / 2
		if abs(v.x) > abs(v.y):
			_try(Vector2i(sign(v.x), 0))
		else:
			_try(Vector2i(0, sign(v.y)))

func _process(delta: float) -> void:
	hold -= delta
	if hold > 0:
		return
	var d := Vector2i.ZERO
	if Input.is_key_pressed(KEY_LEFT) or Input.is_key_pressed(KEY_A):
		d.x = -1
	elif Input.is_key_pressed(KEY_RIGHT) or Input.is_key_pressed(KEY_D):
		d.x = 1
	elif Input.is_key_pressed(KEY_UP) or Input.is_key_pressed(KEY_W):
		d.y = -1
	elif Input.is_key_pressed(KEY_DOWN) or Input.is_key_pressed(KEY_S):
		d.y = 1
	if d != Vector2i.ZERO:
		_try(d)
		hold = 0.08
'''

DEMO_SIDE = '''extends Node
# Hoola level runner (written by Hoola, not by a model): run and jump through the generated level. The jump is
# worked out from the level's own jump height / width, so if the level check passed, this player can finish it.
var cell := 32.0
var key := ""
var root: Node2D
var me: ColorRect
var cam: Camera2D
var p := Vector2.ZERO
var v := Vector2.ZERO
var g := 0.0
var jump_v := 0.0
var run := 0.0
var on_floor := false
var won := false
var tap_jump := false

func _ready() -> void:
	key = String(HoolaWorld.keys()[0])
	var prm: Dictionary = HoolaWorld.WORLDS[key]["params"]
	var jh := float(prm.get("jump_h", 3)) + 0.4
	var jw := float(prm.get("jump_w", 4)) + 0.6
	g = 60.0 * cell
	jump_v = sqrt(2.0 * g * jh * cell)
	run = jw * cell / (2.0 * jump_v / g)
	root = Node2D.new()
	add_child(root)
	root.add_child(HoolaWorld.sprite(key, cell))
	me = ColorRect.new()
	me.color = Color(1, 1, 1)
	me.size = Vector2(cell * 0.8, cell * 0.9)
	root.add_child(me)
	cam = Camera2D.new()
	root.add_child(cam)
	cam.make_current()
	var s := HoolaWorld.spawn(key)
	p = Vector2(s.x * cell, s.y * cell)
	RenderingServer.set_default_clear_color(HoolaWorld.color(0, key))
	HoolaProbe.state("state", "playing")

func _solid_at(x: float, y: float) -> bool:
	return HoolaWorld.solid(int(floor(x / cell)), int(floor(y / cell)), key)

func _box_hits(pp: Vector2) -> bool:
	var w := cell * 0.8
	var h := cell * 0.9
	for q in [Vector2(1, 1), Vector2(w - 1, 1), Vector2(1, h - 1), Vector2(w - 1, h - 1), Vector2(w / 2, h - 1)]:
		if _solid_at(pp.x + q.x, pp.y + q.y):
			return true
	return false

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed:
		tap_jump = true

func _physics_process(delta: float) -> void:
	if won:
		return
	var dir := 1.0
	if Input.is_key_pressed(KEY_LEFT) or Input.is_key_pressed(KEY_A):
		dir = -1.0
	v.x = dir * run
	if on_floor and (Input.is_key_pressed(KEY_SPACE) or Input.is_key_pressed(KEY_UP) or Input.is_key_pressed(KEY_W) or tap_jump):
		v.y = -jump_v
	tap_jump = false
	v.y += g * delta
	var nx := Vector2(p.x + v.x * delta, p.y)
	if not _box_hits(nx):
		p = nx
	var ny := Vector2(p.x, p.y + v.y * delta)
	on_floor = false
	if _box_hits(ny):
		if v.y > 0:
			on_floor = true
		v.y = 0
	else:
		p = ny
	var s := HoolaWorld.size(key)
	if p.y > s.y * cell:
		var sp := HoolaWorld.spawn(key)
		p = Vector2(sp.x * cell, sp.y * cell)
		v = Vector2.ZERO
		HoolaProbe.event("fell")
	var tx := int(floor((p.x + cell * 0.4) / cell))
	var ty := int(floor((p.y + cell * 0.45) / cell))
	if HoolaWorld.tile_name(HoolaWorld.tile(tx, ty, key), key) == "goal":
		won = true
		HoolaProbe.event("win")
		HoolaProbe.state("state", "won")
	if HoolaWorld.tile_name(HoolaWorld.tile(tx, ty, key), key) == "hazard":
		var sp2 := HoolaWorld.spawn(key)
		p = Vector2(sp2.x * cell, sp2.y * cell)
		HoolaProbe.event("hurt")
	me.position = p
	cam.position = p
	HoolaProbe.state("score", int(p.x / cell))
'''


def demo_build(token: str) -> Path | None:
    ensure_table()
    with session() as s:
        r = s.scalars(select(GameWorld).where(GameWorld.demo_token == str(token or ""))).first() if token else None
        if r is None or (r.demo or {}).get("status") != "done":
            return None
        s.expunge(r)
    d = _wdir(r) / "demo" / "build"
    return d if (d / "index.html").is_file() else None


def demo(tenant: str, ref: str) -> dict[str, Any]:
    """Build the walk-it demo in the background (Godot headless run, Web export, Hoola plays it). Free."""
    with session() as s:
        r = _get(s, tenant, ref)
        if r.status == "failed":
            raise WorldError("Is world ki jaanch fail hai; pehle theek world banaiye.")
        if (r.demo or {}).get("status") == "building":
            raise WorldError("Demo ban raha hai.")
        r.demo = {"status": "building", "token": r.demo_token or secrets.token_urlsafe(18)}
        r.demo_token = r.demo["token"]
        s.flush()
        s.expunge(r)
    _POOL.submit(_safe_demo, r.id)
    return view(r)


def _safe_demo(wid: str) -> None:
    try:
        run_demo(wid)
    except Exception as e:                              # noqa: BLE001
        log.exception("world demo %s", wid)
        with session() as s:
            r = s.get(GameWorld, wid)
            if r is not None:
                r.demo = {**(r.demo or {}), "status": "failed", "errors": [str(e)[:300]]}


def run_demo(wid: str) -> dict[str, Any]:
    from . import engine, playtest, template
    with session() as s:
        r = s.get(GameWorld, wid)
        s.expunge(r)
    job = _wdir(r) / "demo"
    shutil.rmtree(job, ignore_errors=True)
    (job / "proj").mkdir(parents=True)
    wj = _wdir(r) / "world.json"
    data = json.loads(wj.read_text(encoding="utf-8")) if wj.is_file() else world_data(r, _load_g(r))
    orient = "landscape"
    scripts = {"main.gd": DEMO_SIDE if VIEW[r.kind] == "side" else DEMO_TOP, FILE: gd({r.key: data})}
    for name, txt in template.files(f"World {r.number}", orient, scripts).items():
        (job / "proj" / name).write_text(txt, encoding="utf-8")
    errors: list[str] = []
    numbers: dict[str, Any] = {}
    sm = engine.smoke(job, frames=240)
    errors += sm["errors"]
    if not errors:
        ex = engine.export_web(job)
        errors += ex["errors"]
        if not errors:
            pl = playtest.run(job / "build", job / "shots", orient, seconds=6)
            errors += pl["errors"]
            numbers = {"fps_server": pl.get("fps"), "load_s": pl.get("load_s"),
                       "download_mb": round((ex.get("download_bytes") or 0) / 1048576, 1)}
    with session() as s:
        row = s.get(GameWorld, wid)
        row.demo = {"status": "failed" if errors else "done", "token": (row.demo or {}).get("token"),
                    "errors": errors[:6], "numbers": numbers}
        out = dict(row.demo)
    return out
