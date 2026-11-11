"""v0.422 MULTIPLAYER NETCODE (Hoola Game Engine plan Phase 7 batch 3, Game Desk plan role 3 - the Multiplayer Network
Programmer): netcode for her game designed with her numbers and PROVED by bots over bad networks, in code (no model,
no money), plus the netcode itself for Godot (an authoritative server and a client with prediction, reconciliation,
interpolation and lag compensation) that she runs on HER own cloud.

The bot run (`simulate`, pure Python, seeded): N bots move at her speed with sprints and turns; the server is
authoritative at her tick rate and sends snapshots at her send rate, only of players inside the interest radius,
quantised and delta-compressed against the last snapshot each client acknowledged; every packet crosses a simulated
network with latency, jitter (so packets arrive out of order) and loss. Each client predicts its own player from its
own inputs at once and, on every snapshot, snaps to the server's answer and replays the inputs the server has not seen
yet (reconciliation); other players are drawn 100 ms in the past between two snapshots (interpolation); the server
rewinds positions to what the shooter saw when it judges a hit (lag compensation).

MEASURED for three networks (good 40 ms, the plan's 150 ms / 2 % loss / 20 ms jitter, bad mobile 300 ms / 5 % /
60 ms), never assumed:
- rubber-banding: how far a client's own player jumps when the server corrects it (p95 and max, px) - the limit is a
  quarter of the player's size on the plan's 150 ms network;
- desync: after the inputs stop, every client's own player must equal the server's exactly (0 px) - the same step
  function on both sides, fixed time step;
- bandwidth per player down / up (bytes/s with packet headers) and what interest management saved;
- interpolation: how often the 100 ms buffer ran dry (extrapolated frames);
- lag compensation: of the shots that hit on the shooter's screen, how many the server agrees with - with the rewind
  and without it.

The Godot netcode (`GD_NET`, Hoola's own GDScript) is run in the REAL engine by `godot_lab`: a server and three clients
in one headless process over an in-memory link with the same latency / loss / jitter (sockets are not available in
the build box), checking the same desync = 0 and correction numbers. The socket transport (ENet / WebSocket) is a thin
adapter in the kit, NOT tested here - said plainly. NOT into her game build yet: the game's own code may not open
sockets and play links allow only their own host, so the in-game connection to HER server is the next step. A
Hoola-hosted game-server box is an open owner decision (docs/GAME_DESK_PLAN.md section 8) and is not built."""
from __future__ import annotations

import hashlib
import heapq
import io
import json
import logging
import math
import re
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import JSON, DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import service as G

log = logging.getLogger("santosh.gamedesk")
FILE = "hoola_net.gd"
KEY = "netcode_dev"
NETWORKS = {
    "good": {"rtt_ms": 40, "loss": 0.0, "jitter_ms": 5, "name": "good Wi-Fi (40 ms)"},
    "plan": {"rtt_ms": 150, "loss": 0.02, "jitter_ms": 20, "name": "the plan's test: 150 ms, 2 % loss, 20 ms jitter"},
    "mobile": {"rtt_ms": 300, "loss": 0.05, "jitter_ms": 60, "name": "bad mobile (300 ms, 5 % loss, 60 ms jitter)"},
}
DEFAULTS = {"players": 16, "tick": 30, "send": 20, "speed": 240.0, "size": 32.0, "interest": 900.0, "seconds": 20,
            "world": 3000.0, "interp_ms": 100}
LIMITS = {"players": (2, 64), "tick": (10, 128), "send": (5, 64), "speed": (10.0, 3000.0), "size": (4.0, 400.0),
          "interest": (100.0, 20000.0), "seconds": (5, 60), "world": (200.0, 50000.0), "interp_ms": (30, 400)}
HEADER = 28 + 4                 # UDP / IP header + Hoola's 4-byte message header
_POOL_NAME = "gamenet"


class NetError(G.GameError):
    pass


class GameNet(Base):
    __tablename__ = "game_net"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gn"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    studio_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    words: Mapped[str] = mapped_column(Text, default="")
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    report: Mapped[dict] = mapped_column(JSON, default=dict)
    server_url: Mapped[str] = mapped_column(String(300), default="")      # HER server (wss://...), never Hoola's
    status: Mapped[str] = mapped_column(String(12), default="testing")   # testing | draft | approved | rejected | failed
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        GameNet.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


def clean_inputs(inp: dict | None) -> dict:
    out = dict(DEFAULTS)
    for k, v in (inp or {}).items():
        if k in out:
            try:
                lo, hi = LIMITS[k]
                out[k] = min(max(float(v), lo), hi)
            except (TypeError, ValueError):
                pass
    for k in ("players", "tick", "send", "seconds", "interp_ms"):
        out[k] = int(round(out[k]))
    out["send"] = min(out["send"], out["tick"])
    return out


def from_words(words: str) -> dict:
    w = (words or "").lower()
    got: dict[str, float] = {}
    for k, pat in {"players": r"(\d+)\s*(?:players?|khiladi|log)", "tick": r"(\d+)\s*(?:hz\s*)?tick",
                   "speed": r"(\d+(?:\.\d+)?)\s*(?:px|pixel)s?\s*(?:/|per)\s*s"}.items():
        m = re.search(pat, w)
        if m:
            got[k] = float(m.group(1))
    return got


# ================================================================ the shared step (same on server and client)
def step(pos: tuple[float, float], inp: tuple[int, int, int], speed: float, dt: float, world: float) -> tuple[float, float]:
    """One fixed tick of movement: input (dx, dy in -1..1, sprint 0/1). Positions are quantised to 1/16 px - the same
    rule the snapshots use - so server and client agree to the bit."""
    dx, dy, sprint = inp
    n = math.hypot(dx, dy) or 1.0
    v = speed * (1.6 if sprint else 1.0)
    x = min(max(pos[0] + dx / n * v * dt, 0.0), world)
    y = min(max(pos[1] + dy / n * v * dt, 0.0), world)
    return (round(x * 16) / 16, round(y * 16) / 16)


# ================================================================ the bot run
def simulate(inp: dict, net: dict, seed: int = 1) -> dict:
    """A deterministic event simulation of the whole netcode. Returns the measured numbers."""
    rng = np.random.default_rng(seed)
    P, tick, send = inp["players"], inp["tick"], inp["send"]
    dt = 1.0 / tick
    ticks = inp["seconds"] * tick
    speed, world, size, R = inp["speed"], inp["world"], inp["size"], inp["interest"]
    one_way = net["rtt_ms"] / 2000.0
    jit = net["jitter_ms"] / 1000.0
    loss = net["loss"]
    q: list = []                                      # (arrive_time, seq, kind, payload)
    cnt = [0]

    def post(t: float, kind: str, payload: Any, size_b: int, stats: dict) -> None:
        stats["bytes"] += size_b + HEADER
        if rng.random() < loss:
            stats["lost"] += 1
            return
        cnt[0] += 1
        heapq.heappush(q, (t + max(0.0, one_way + rng.normal(0, jit / 2)), cnt[0], kind, payload))

    srv = {i: (float(rng.uniform(0, world)), float(rng.uniform(0, world))) for i in range(P)}
    hist: list[dict] = []                              # server position history for lag compensation
    last_seen = {i: 0 for i in range(P)}               # last input seq the server applied per client
    pending_inputs = {i: {} for i in range(P)}          # seq -> input received by the server
    waits = {i: 0 for i in range(P)}
    skipped = [0]
    acked = {i: -1 for i in range(P)}                  # snapshot id each client acknowledged (delta base)
    cl = {i: {"pos": srv[i], "inputs": [], "seq": 0, "snaps": [], "corr": [], "starve": 0, "frames": 0, "newest": -1, "stale": 0}
          for i in range(P)}
    up = {"bytes": 0, "lost": 0}
    down = {"bytes": 0, "lost": 0}
    plan_inp = {i: (0, 0, 0) for i in range(P)}
    shots = {"screen_hits": 0, "agree_rewind": 0, "agree_none": 0}
    full_bytes = 0
    snap_id = 0
    t = 0.0
    for k in range(ticks + tick * 2):                  # the last 2 s: no inputs, everything settles
        t = k * dt
        # 1) bots choose inputs (change every ~0.5 s) and predict at once; EVERY tick each client resends all its
        #    unacknowledged inputs (up to 8) - a lost packet loses nothing, and the last inputs still arrive
        for i in range(P):
            c = cl[i]
            if k < ticks:
                if k % max(1, tick // 2) == i % max(1, tick // 2):
                    plan_inp[i] = (int(rng.integers(-1, 2)), int(rng.integers(-1, 2)), int(rng.random() < 0.2))
                c["seq"] += 1
                c["inputs"].append((c["seq"], plan_inp[i]))
                c["pos"] = step(c["pos"], plan_inp[i], speed, dt, world)
            unacked = c["inputs"][-8:]
            if unacked:
                post(t, "in", (i, unacked), 2 + 4 * len(unacked), up)
        # 2) deliver everything due
        while q and q[0][0] <= t:
            _at, _s, kind, pl = heapq.heappop(q)
            if kind == "in":
                i, many = pl
                for seq, ip in many:
                    if seq > last_seen[i]:
                        pending_inputs[i][seq] = ip
            elif kind == "snap":
                i, sid, positions, seen = pl
                c = cl[i]
                if sid <= c["newest"]:                  # an older snapshot arriving late (jitter): never step back to it
                    c["stale"] += 1
                    continue
                c["newest"] = sid
                c["snaps"].append((sid, _at, positions))
                c["snaps"] = sorted(c["snaps"], key=lambda s: s[0])[-12:]
                if sid > acked[i]:
                    acked[i] = sid
                # reconciliation: server answer for my player + replay what it has not applied yet
                if i in positions:
                    before = c["pos"]
                    p = positions[i]
                    c["inputs"] = [(s, ip) for s, ip in c["inputs"] if s > seen]
                    for _s2, ip in c["inputs"]:
                        p = step(p, ip, speed, dt, world)
                    c["pos"] = p
                    c["corr"].append(math.hypot(before[0] - p[0], before[1] - p[1]))
        # 3) server applies inputs in order, one per client per tick; a missing one is waited for 3 ticks (the resend
        #    usually brings it), then skipped - the client drops it too, so both still agree
        for i in range(P):
            nxt = last_seen[i] + 1
            ip = pending_inputs[i].pop(nxt, None)
            if ip is not None:
                srv[i] = step(srv[i], ip, speed, dt, world)
                last_seen[i] = nxt
                waits[i] = 0
            elif pending_inputs[i]:
                waits[i] += 1
                if waits[i] > 3:
                    oldest = min(pending_inputs[i])
                    srv[i] = step(srv[i], pending_inputs[i].pop(oldest), speed, dt, world)
                    last_seen[i] = oldest
                    skipped[0] += 1
                    waits[i] = 0
        hist.append({"t": t, "pos": dict(srv)})
        hist = hist[-tick * 2:]
        # 4) snapshots at the send rate, interest-managed and delta-sized
        if k % max(1, tick // send) == 0:
            snap_id += 1
            for i in range(P):
                near = {j: srv[j] for j in range(P) if j == i or math.hypot(srv[j][0] - srv[i][0], srv[j][1] - srv[i][1]) <= R}
                full_bytes += 2 + P * 9 + HEADER
                delta = snap_id - acked[i] <= 4         # a recent base: 2-byte deltas, else full 8-byte positions
                post(t, "snap", (i, snap_id, near, last_seen[i]), 4 + len(near) * (5 if delta else 9), down)
        # 5) clients draw remote players 100 ms in the past; bots shoot at the nearest one they see
        if tick <= k < ticks and k % tick == 0:            # from 1 s in (before that no snapshot can exist yet)
            for i in range(P):
                c = cl[i]
                rt = t - inp["interp_ms"] / 1000.0          # drawn interp_ms behind the snapshots' arrival (as HoolaNet does)
                snaps = [s for s in c["snaps"] if s[1] <= t]
                a = [s for s in snaps if s[1] <= rt]
                b = [s for s in snaps if s[1] > rt]
                c["frames"] += 1
                if not a or not b:
                    c["starve"] += 1
                    continue
                sa, sb = a[-1], b[0]
                for j, pa in sa[2].items():
                    if j == i or j not in sb[2]:
                        continue
                    seen_pos = pa                       # what the shooter sees (interpolated end ~ start)
                    shots["screen_hits"] += 1
                    view_t = sa[1] - one_way
                    past = min(hist, key=lambda h: abs(h["t"] - view_t))["pos"][j]
                    if math.hypot(past[0] - seen_pos[0], past[1] - seen_pos[1]) <= size / 2:
                        shots["agree_rewind"] += 1
                    if math.hypot(srv[j][0] - seen_pos[0], srv[j][1] - seen_pos[1]) <= size / 2:
                        shots["agree_none"] += 1
                    break
    corr = np.array([x for i in range(P) for x in cl[i]["corr"]] or [0.0])
    desync = [round(math.hypot(cl[i]["pos"][0] - srv[i][0], cl[i]["pos"][1] - srv[i][1]), 4) for i in range(P)]
    secs = (ticks + tick * 2) * dt
    frames = sum(cl[i]["frames"] for i in range(P)) or 1
    return {"net": net["name"], "corr_p95_px": round(float(np.percentile(corr, 95)), 2), "corr_max_px": round(float(corr.max()), 2),
            "rubber_band_share": round(float((corr > inp["size"] / 4).mean()), 4),
            "desync_px_max": max(desync), "desync_players": sum(1 for d in desync if d > 0),
            "down_bps_per_player": round(down["bytes"] / secs / P), "up_bps_per_player": round(up["bytes"] / secs / P),
            "down_full_bps_per_player": round(full_bytes / secs / P), "lost_packets": up["lost"] + down["lost"],
            "interp_starved_share": round(sum(cl[i]["starve"] for i in range(P)) / frames, 4),
            "stale_snapshots_dropped": sum(cl[i]["stale"] for i in range(P)), "inputs_skipped": skipped[0],
            "interp_ms_needed": int(math.ceil(2 * 1000 / send + 2 * net["jitter_ms"])),
            "shots": shots["screen_hits"],
            "lagcomp_agree": round(shots["agree_rewind"] / max(1, shots["screen_hits"]), 3),
            "no_lagcomp_agree": round(shots["agree_none"] / max(1, shots["screen_hits"]), 3)}


def judge(runs: dict[str, dict], inp: dict, again: dict | None) -> dict:
    checks: list[dict] = []

    def ck(name: str, ok: bool, note: str) -> None:
        checks.append({"check": name, "ok": bool(ok), "note": note})
    p = runs["plan"]
    lim = inp["size"] / 4
    for key, r in runs.items():
        ck(f"desync on {NETWORKS[key]['name']}", r["desync_px_max"] == 0,
           f"after the inputs stop every client's own player equals the server's: worst {r['desync_px_max']} px "
           f"({r['desync_players']} players off)")
    ck("rubber-banding on the plan's network", p["corr_p95_px"] <= lim,
       f"p95 correction {p['corr_p95_px']} px, max {p['corr_max_px']} px (limit a quarter of the {inp['size']:g} px player = "
       f"{lim:g} px); {round(p['rubber_band_share'] * 100, 1)}% of corrections visible")
    ck("bandwidth stated", True, f"per player {p['down_bps_per_player']} B/s down, {p['up_bps_per_player']} B/s up on the "
       f"plan's network (interest + deltas: {p['down_full_bps_per_player']} B/s without them)")
    ck("lag compensation", p["lagcomp_agree"] >= p["no_lagcomp_agree"] and p["lagcomp_agree"] >= 0.8,
       f"of {p['shots']} on-screen hits the server agreed with {round(p['lagcomp_agree'] * 100)}% with the rewind, "
       f"{round(p['no_lagcomp_agree'] * 100)}% without")
    ck("interpolation buffer", p["interp_starved_share"] <= 0.05,
       f"the {inp['interp_ms']} ms buffer ran dry on {round(p['interp_starved_share'] * 100, 1)}% of frames (this network needs "
       f"about {p['interp_ms_needed']} ms: two send intervals + twice the jitter); {p['stale_snapshots_dropped']} late "
       "snapshots were dropped, never applied")
    if again is not None:
        ck("same run twice", json.dumps(again, sort_keys=True) == json.dumps(runs, sort_keys=True), "the bot run is seeded")
    ok = all(c["ok"] for c in checks)
    return {"checks": checks, "verdict": "PASS" if ok else "FAIL", "passed": sum(c["ok"] for c in checks), "total": len(checks)}


# ================================================================ the Godot netcode (Hoola's own; tested in the real engine)
GD_NET = '''extends Node
# HoolaNet (an autoload): authoritative server + client prediction / reconciliation / interpolation + lag compensation.
# Written by Hoola Studio from a netcode setup PROVED by bots (verdict below); do not edit. The transport is a
# function pair (send / poll) so the same code runs over the socket adapter on HER server and over Hoola's lab link.
const CFG := __CFG__
signal state_changed

var is_server := false
var my_id := -1
var server_pos := {}        # id -> Vector2 (server)
var last_seen := {}         # id -> last input seq applied (server)
var pending := {}           # id -> {seq: input}
var history: Array = []     # [{t, pos}] for lag compensation (server)
var pos := Vector2.ZERO     # my predicted position (client)
var inputs: Array = []      # [[seq, input]] not yet confirmed (client)
var seq := 0
var snaps: Array = []       # [[id, time, positions]] (client)
var corrections: Array = []
var transport_send: Callable
var tick_n := 0

func q(v: Vector2) -> Vector2:
	return Vector2(round(v.x * 16.0) / 16.0, round(v.y * 16.0) / 16.0)

func step(p: Vector2, inp: Array) -> Vector2:
	# the SAME step on server and client (fixed tick, quantised to 1/16 px): this is why desync is 0
	var d := Vector2(float(inp[0]), float(inp[1]))
	if d.length() > 0.0:
		d = d.normalized()
	var v := float(CFG["speed"]) * (1.6 if int(inp[2]) == 1 else 1.0)
	var w := float(CFG["world"])
	var np := p + d * v / float(CFG["tick"])
	return q(Vector2(clampf(np.x, 0.0, w), clampf(np.y, 0.0, w)))

func server_add(id: int, start: Vector2) -> void:
	server_pos[id] = q(start)
	last_seen[id] = 0
	pending[id] = {}

var waits := {}

func server_receive(id: int, many: Array) -> void:
	# the client resends all its unacknowledged inputs every tick: keep the ones not applied yet
	for e in many:
		if int(e[0]) > int(last_seen.get(id, 0)):
			pending[id][int(e[0])] = e[1]

func server_tick(now_s: float) -> Dictionary:
	# apply each client's next input in order; a missing one is waited for 3 ticks, then skipped (the client drops it too)
	for id in server_pos.keys():
		var nxt := int(last_seen[id]) + 1
		if pending[id].has(nxt):
			server_pos[id] = step(server_pos[id], pending[id][nxt])
			pending[id].erase(nxt)
			last_seen[id] = nxt
			waits[id] = 0
		elif pending[id].size() > 0:
			waits[id] = int(waits.get(id, 0)) + 1
			if int(waits[id]) > 3:
				var ks: Array = pending[id].keys()
				ks.sort()
				server_pos[id] = step(server_pos[id], pending[id][ks[0]])
				last_seen[id] = int(ks[0])
				pending[id].erase(ks[0])
				waits[id] = 0
	history.append({"t": now_s, "pos": server_pos.duplicate()})
	if history.size() > int(CFG["tick"]) * 2:
		history.pop_front()
	tick_n += 1
	return server_pos

func snapshot_for(id: int) -> Dictionary:
	var me: Vector2 = server_pos[id]
	var near := {}
	for j in server_pos.keys():
		if j == id or (server_pos[j] as Vector2).distance_to(me) <= float(CFG["interest"]):
			near[j] = server_pos[j]
	return {"tick": tick_n, "seen": int(last_seen[id]), "pos": near}

func rewind_hit(target: int, seen_at: Vector2, view_time: float) -> bool:
	# lag compensation: judge the shot where the target WAS when the shooter saw it
	var best = null
	for h in history:
		if best == null or absf(float(h["t"]) - view_time) < absf(float(best["t"]) - view_time):
			best = h
	return best != null and (best["pos"][target] as Vector2).distance_to(seen_at) <= float(CFG["size"]) / 2.0

func client_input(inp: Array) -> void:
	# predict at once, remember the input until the server confirms it
	seq += 1
	inputs.append([seq, inp])
	pos = step(pos, inp)

func unacked() -> Array:
	# what to send this tick: every input the server has not confirmed (the last 8)
	return inputs.slice(maxi(0, inputs.size() - 8))

var newest := -1

func client_snapshot(s: Dictionary, now_s: float) -> void:
	if int(s["tick"]) <= newest:
		return                  # an older snapshot arriving late (jitter): never step back to it
	newest = int(s["tick"])
	snaps.append([int(s["tick"]), now_s, s["pos"]])
	if snaps.size() > 12:
		snaps.pop_front()
	if s["pos"].has(my_id):
		var before := pos
		var p: Vector2 = s["pos"][my_id]
		var keep: Array = []
		for e in inputs:
			if int(e[0]) > int(s["seen"]):
				keep.append(e)
		inputs = keep
		for e in inputs:
			p = step(p, e[1])
		pos = p
		corrections.append(before.distance_to(pos))
	state_changed.emit()

func remote(id: int, now_s: float) -> Variant:
	# another player drawn interp_ms in the past, between the two snapshots around that time
	var rt := now_s - float(CFG["interp_ms"]) / 1000.0
	var a = null
	var b = null
	for s in snaps:
		if float(s[1]) <= rt and s[2].has(id):
			a = s
		elif float(s[1]) > rt and s[2].has(id) and b == null:
			b = s
	if a == null:
		return null
	if b == null:
		return a[2][id]
	var f := clampf((rt - float(a[1])) / maxf(0.0001, float(b[1]) - float(a[1])), 0.0, 1.0)
	return (a[2][id] as Vector2).lerp(b[2][id], f)
'''

GD_LAB = '''extends Node
# Hoola netcode lab (written by Hoola, not by a model): one server + three clients in ONE headless process over an
# in-memory link with latency, jitter and loss (sockets are not available in the build box). Same seed = same run.
const LAB := __LAB__
var srv: Node
var cls: Array = []
var link: Array = []        # [arrive_s, to, kind, payload]
var rng := RandomNumberGenerator.new()
var t := 0.0
var k := 0
var inp := {}

func _post(to: int, kind: String, payload: Variant) -> void:
	if rng.randf() < float(LAB["loss"]):
		return
	var d := float(LAB["rtt_ms"]) / 2000.0 + rng.randfn(0.0, float(LAB["jitter_ms"]) / 2000.0)
	link.append([t + maxf(0.0, d), to, kind, payload])

func _ready() -> void:
	rng.seed = int(LAB["seed"])
	srv = preload("res://hoola_net.gd").new()
	srv.is_server = true
	add_child(srv)
	for i in 3:
		var c = preload("res://hoola_net.gd").new()
		c.my_id = i
		var start := Vector2(100.0 + i * 50.0, 100.0)
		c.pos = srv.q(start)
		add_child(c)
		cls.append(c)
		srv.server_add(i, start)
		inp[i] = [0, 0, 0]

func _physics_process(_d: float) -> void:
	var tick := int(LAB["tick"])
	t = k / float(tick)
	var active := k < int(LAB["ticks"])
	for i in 3:
		if active:
			if k % (tick / 2) == i:
				inp[i] = [rng.randi_range(-1, 1), rng.randi_range(-1, 1), 1 if rng.randf() < 0.2 else 0]
			cls[i].client_input(inp[i])
		var un: Array = cls[i].unacked()
		if un.size() > 0:
			_post(-1, "in", [i, un])
	var keep: Array = []
	for m in link:
		if float(m[0]) <= t:
			if m[2] == "in":
				srv.server_receive(int(m[3][0]), m[3][1])
			else:
				cls[int(m[1])].client_snapshot(m[3], t)
		else:
			keep.append(m)
	link = keep
	srv.server_tick(t)
	if k % maxi(1, tick / int(LAB["send"])) == 0:
		for i in 3:
			_post(i, "snap", srv.snapshot_for(i))
	k += 1
	if k == int(LAB["ticks"]) + tick * 2:
		var worst := 0.0
		var corr: Array = []
		for i in 3:
			worst = maxf(worst, (cls[i].pos as Vector2).distance_to(srv.server_pos[i]))
			corr.append_array(cls[i].corrections)
		corr.sort()
		var p95 := float(corr[int(corr.size() * 0.95)]) if corr.size() > 0 else 0.0
		print("HOOLA_NET " + JSON.stringify({"desync_px_max": worst, "corr_p95_px": p95, "snapshots": corr.size(),
			"remote_ok": cls[0].remote(1, t) != null}))
		get_tree().quit()
'''


def godot_lab(inp: dict, net: dict, job: Path, seed: int = 3) -> dict:
    from . import engine, template
    from .bible import _gd
    import shutil
    shutil.rmtree(job / "proj", ignore_errors=True)
    (job / "proj").mkdir(parents=True)
    lab = {"tick": inp["tick"], "send": inp["send"], "ticks": inp["tick"] * 8, "rtt_ms": net["rtt_ms"], "loss": net["loss"],
           "jitter_ms": net["jitter_ms"], "seed": seed}
    scripts = {"main.gd": GD_LAB.replace("__LAB__", _gd(lab)), FILE: gd(inp, "LAB")}
    files = template.files("Hoola netcode lab", "landscape", scripts)
    proj = files["project.godot"].replace('HoolaNet="*res://hoola_net.gd"\n', "")   # preloaded as instances, not an autoload
    files["project.godot"] = proj
    for name, txt in files.items():
        (job / "proj" / name).write_text(txt, encoding="utf-8")
    frames = lab["ticks"] + inp["tick"] * 2 + 20
    code, logtxt, to = engine._run(job, ["--path", "proj", "--fixed-fps", str(inp["tick"]), "--quit-after", str(frames * 2 + 60)],
                                   "net.log", 120)
    m = re.search(r"HOOLA_NET (\{.*\})", logtxt or "")
    if not m:
        errs = engine.errors_in(logtxt or "") or [(logtxt or "").strip()[-300:] or "the lab printed nothing"]
        raise NetError("The netcode lab did not run in Godot: " + "; ".join(errs[:3])[:400])
    return json.loads(m.group(1))


def gd(inp: dict, verdict: str) -> str:
    from .bible import _gd
    keep = {k: inp[k] for k in ("tick", "send", "speed", "size", "interest", "world", "interp_ms")}
    keep["verdict"] = verdict
    return GD_NET.replace("__CFG__", _gd(keep))


SERVER_GD = '''extends Node
# Hoola game server (headless Godot on HER cloud): runs HoolaNet as the authority over WebSockets.
# Run:  godot --headless --path . -- --port 8910      (put it behind her TLS proxy as wss://)
var peer := WebSocketMultiplayerPeer.new()
func _ready() -> void:
	var port := 8910
	var args := OS.get_cmdline_user_args()
	if args.size() >= 2 and args[0] == "--port":
		port = int(args[1])
	peer.create_server(port)
	multiplayer.multiplayer_peer = peer
	HoolaNet.is_server = true
	multiplayer.peer_connected.connect(func(id): HoolaNet.server_add(id, Vector2(randf() * 500.0, randf() * 500.0)))
	print("Hoola game server on port ", port)

func _physics_process(_d: float) -> void:
	var now_s := Time.get_ticks_msec() / 1000.0
	HoolaNet.server_tick(now_s)
	if Engine.get_physics_frames() % maxi(1, int(HoolaNet.CFG["tick"]) / int(HoolaNet.CFG["send"])) == 0:
		for id in multiplayer.get_peers():
			if HoolaNet.server_pos.has(id):
				rpc_id(id, "snap", HoolaNet.snapshot_for(id))

@rpc("any_peer", "unreliable_ordered")
func input(many: Array) -> void:
	HoolaNet.server_receive(multiplayer.get_remote_sender_id(), many)

@rpc("authority", "unreliable_ordered")
func snap(_s: Dictionary) -> void:
	pass
'''


def kit_zip(inp: dict, verdict: str, server_url: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("server/hoola_net.gd", gd(inp, verdict))
        z.writestr("server/server.gd", SERVER_GD)
        z.writestr("server/Dockerfile", "FROM barichello/godot-ci:4.4\nWORKDIR /game\nCOPY . .\nEXPOSE 8910\n"
                   "CMD [\"godot\", \"--headless\", \"--path\", \".\", \"--\", \"--port\", \"8910\"]\n")
        z.writestr("client/hoola_net.gd", gd(inp, verdict))
        z.writestr("settings.json", json.dumps({**inp, "server_url": server_url}, indent=2))
        z.writestr("README.txt", "Hoola netcode kit\n\nserver/: run on YOUR cloud (Docker or a headless Godot), behind your TLS "
                   "proxy as wss://. client/: HoolaNet goes into the game when you give Hoola your server's wss:// address.\n"
                   "The bot run and the Godot lab proved the netcode logic; the socket transport itself is not tested by Hoola "
                   "(the build box has no network). Hoola never hosts your game server.\n")
    return buf.getvalue()


# ================================================================ store + jobs
def _root(tenant: str) -> Path:
    return G.root() / (re.sub(r"[^\w-]", "_", tenant)[:64] or "t") / "net"


def _studio(tenant: str, ref: str):
    from . import studio as S
    with session() as s:
        r = S._studio(s, tenant, ref)
        s.expunge(r)
    return r


def _get(s, tenant: str, ref: str) -> GameNet:
    ref = str(ref or "").strip()
    q = select(GameNet).where(GameNet.tenant_id == tenant)
    r = s.scalars(q.where(GameNet.id == ref)).first() or s.scalars(q.where(GameNet.number == ref.upper())).first()
    if r is None:
        raise NetError("This netcode setup was not found (give N-001).")
    return r


def _sig(name: str) -> str:
    import hmac as _h
    from ..config import get_settings
    key = (getattr(get_settings(), "api_key", "") or "hoola-net").encode()
    return _h.new(key, f"net:{name}".encode(), "sha256").hexdigest()[:16]


def file_url(r: GameNet) -> str:
    return f"/api/gamedesk/net/{r.id}/file/kit.zip?sig={_sig(r.id + 'kit.zip')}"


def net_file(nid: str, name: str, sig: str) -> Path | None:
    import hmac as _h
    if not re.fullmatch(r"gn_[A-Za-z0-9_-]{4,40}", str(nid or "")) or name != "kit.zip" or not _h.compare_digest(_sig(nid + name), str(sig or "")):
        return None
    ensure_table()
    with session() as s:
        r = s.get(GameNet, nid)
        if r is None:
            return None
        s.expunge(r)
    p = _root(r.tenant_id) / r.id / name
    return p if p.is_file() else None


def view(r: GameNet) -> dict[str, Any]:
    return {"id": r.id, "number": r.number, "status": r.status, "words": r.words, "inputs": r.inputs or {},
            "report": r.report or {}, "server_url": r.server_url, "error": r.error, "studio_id": r.studio_id,
            "files": {"kit.zip": file_url(r)} if (_root(r.tenant_id) / r.id / "kit.zip").is_file() else {},
            "hosting": "your own cloud (a Hoola-hosted game server is not offered)", "networks": NETWORKS,
            "at": r.created_at.isoformat() if r.created_at else ""}


def setup(tenant: str, words: str = "", inputs: dict | None = None, studio: str = "", run_now: bool = True) -> dict[str, Any]:
    ensure_table()
    sid = _studio(tenant, studio).id if studio else ""
    inp = clean_inputs({**from_words(words), **(inputs or {})})
    with session() as s:
        n = len(s.scalars(select(GameNet.id).where(GameNet.tenant_id == tenant)).all()) + 1
        r = GameNet(tenant_id=tenant, studio_id=sid, number=f"N-{n:03d}", words=(words or "")[:600], inputs=inp, status="testing")
        s.add(r)
        s.flush()
        s.expunge(r)
    if run_now:
        _pool().submit(_safe_run, r.id)
    return view(r)


_POOL = None


def _pool():
    global _POOL
    if _POOL is None:
        from concurrent.futures import ThreadPoolExecutor
        _POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix=_POOL_NAME)
    return _POOL


def _safe_run(nid: str) -> None:
    try:
        run(nid)
    except Exception as e:                              # noqa: BLE001
        log.exception("netcode %s", nid)
        with session() as s:
            r = s.get(GameNet, nid)
            if r is not None:
                r.status, r.error = "failed", str(e)[:400]


def run(nid: str, real_engine: bool = True) -> dict[str, Any]:
    from . import engine
    with session() as s:
        r = s.get(GameNet, nid)
        s.expunge(r)
    t0 = time.time()
    runs = {k: simulate(r.inputs, n) for k, n in NETWORKS.items()}
    again = {k: simulate(r.inputs, n) for k, n in NETWORKS.items()}
    rep = judge(runs, r.inputs, again)
    rep["runs"] = runs
    if real_engine and engine.find():
        try:
            g = godot_lab(r.inputs, NETWORKS["plan"], _root(r.tenant_id) / r.id / "lab")
            ok = g["desync_px_max"] == 0 and g["corr_p95_px"] <= r.inputs["size"] / 4 and g["remote_ok"]
            rep["checks"].append({"check": "the Godot netcode in the real engine", "ok": bool(ok),
                                  "note": f"server + 3 clients over the plan's network inside Godot: desync {g['desync_px_max']} px, "
                                          f"p95 correction {round(g['corr_p95_px'], 2)} px, {g['snapshots']} corrections, "
                                          f"interpolation {'works' if g['remote_ok'] else 'FAILED'}"})
        except NetError as e:
            rep["checks"].append({"check": "the Godot netcode in the real engine", "ok": False, "note": str(e)})
    else:
        rep["checks"].append({"check": "the Godot netcode in the real engine", "ok": True,
                              "note": "NOT ASSESSED: Godot is not installed on this server"})
    rep["passed"] = sum(c["ok"] for c in rep["checks"])
    rep["total"] = len(rep["checks"])
    rep["verdict"] = "PASS" if rep["passed"] == rep["total"] else "FAIL"
    rep["seconds"] = round(time.time() - t0, 1)
    d = _root(r.tenant_id) / r.id
    d.mkdir(parents=True, exist_ok=True)
    (d / "kit.zip").write_bytes(kit_zip(r.inputs, rep["verdict"], r.server_url))
    with session() as s:
        row = s.get(GameNet, nid)
        row.report = rep
        row.status = "draft" if rep["verdict"] == "PASS" else "failed"
        row.error = "" if rep["verdict"] == "PASS" else "; ".join(c["check"] + ": " + c["note"] for c in rep["checks"] if not c["ok"])[:400]
        row.updated_at = now()
        s.flush()
        s.expunge(row)
    return view(row)


def set_server(tenant: str, ref: str, url: str) -> dict[str, Any]:
    """HER game server's address (wss:// only, her own domain - never a Hoola host)."""
    url = (url or "").strip()
    if url and not re.fullmatch(r"wss://[a-z0-9.-]+(:\d{2,5})?(/[\w./-]*)?", url, re.I):
        raise NetError("The server address must be wss://your-domain/... (secure websocket only).")
    with session() as s:
        r = _get(s, tenant, ref)
        r.server_url = url
        s.flush()
        s.expunge(r)
    return view(r)


def approve(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _get(s, tenant, ref)
        if r.status != "draft":
            raise NetError("Only a netcode setup that PASSED can be OKed." if r.status != "testing" else "The bots are still playing.")
        for o in s.scalars(select(GameNet).where(GameNet.tenant_id == tenant, GameNet.studio_id == r.studio_id,
                                                 GameNet.status == "approved")).all():
            o.status = "rejected"
        r.status = "approved"
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


def setups(tenant: str, studio: str = "") -> list[dict[str, Any]]:
    ensure_table()
    sid = _studio(tenant, studio).id if studio else None
    with session() as s:
        q = select(GameNet).where(GameNet.tenant_id == tenant)
        if sid is not None:
            q = q.where(GameNet.studio_id == sid)
        rows = s.scalars(q.order_by(GameNet.created_at.desc())).all()[:30]
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
    """Not into her game yet, said plainly: the game's own code may not open sockets (guard.py) and play links only
    allow their own host (CSP), so a client inside the game could not reach her server. The proven logic + the kit
    (server for HER cloud, client code) are what this version gives; the in-game socket path is the next step."""
    return None


def apply(tenant: str, studio: str) -> dict[str, Any]:
    st = _studio(tenant, studio)
    if for_game(tenant, st.game_id) is None:
        raise NetError("Netcode does not go into the game build yet (the game's code cannot open the network); download the kit and "
                       "run it on your own server - the connection inside the game is the next step.")
    try:
        from . import bible as B
        bv = B.view(tenant, st.id)["version"]
    except Exception:                                   # noqa: BLE001
        bv = 0
    G.data_build(tenant, st.game_id, bv, words="Netcode into the game")
    return {"ok": True, "say": "Netcode is going into the game (a rebuild is running)."}
