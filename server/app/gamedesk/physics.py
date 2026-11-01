"""v0.419 PHYSICS ENGINE DEVELOPER (Hoola Game Engine plan Phase 7, Game Desk plan role 4): her game's physics set up
and PROVED in the real engine - Godot 4 run headless runs Hoola's physics lab, every case is compared with the
textbook answer in code, and the settings that pass go into her game as Hoola's own HoolaPhysics autoload.

The lab (Hoola's own GDScript, never the model's; `--fixed-fps` so simulated time is exact):
- free fall      : a body dropped for 1 s vs 1/2 g t^2, and vs the integrator's own discrete answer
                   (Godot steps semi-implicit Euler: y_n = g dt^2 n(n+1)/2) - so the error is EXPLAINED, not hidden;
- projectile     : launch (vx, vy) -> range vs 2 vx vy / g;
- collision      : two balls, masses 1 and 2, bounce 1, no friction -> velocities vs the elastic formulas,
                   momentum and kinetic energy kept within stated limits;
- tunnelling     : HER fastest body at HER speed against HER thinnest wall at HER tick rate, with and without
                   continuous collision detection (CCD) - the case that decides the settings;
- stack          : six boxes settle for 3 s - drift and sink measured (a wobbly stack is named);
- 3D drop        : the same free fall in the 3D engine (Jolt since Godot 4.6), engine name reported;
- determinism    : the whole lab runs TWICE; the two result fingerprints must match.

Settings are worked out in CODE from her numbers (speed, wall, ticks, gravity). MEASURED in Godot 4.7.2 by this lab:
without CCD a body whose step can carry its centre past the MIDDLE of the wall goes through or stops depending on
where its steps land (so safe = one step <= half the wall), and of the two CCD modes only cast-ray stopped every case
(cast-shape behaved like no CCD). The fix is enough ticks (ceil(2 x speed / wall)) or cast-ray CCD, and the lab
fires six bullets from six start points per mode to prove the chosen fix stops every one. A setup waits for her OK; approved settings -> HoolaPhysics
(ticks, gravity, CCD helper, jump / range helpers with the same formulas the lab checked).
Fluids are not part of this pack yet (said plainly on the card)."""
from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import service as G

log = logging.getLogger("santosh.gamedesk")
FILE = "hoola_physics.gd"
KEY = "physics_dev"
_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gamephysics")
LIMITS = {"ticks": (30, 240), "gravity": (0.0, 6000.0), "speed": (1.0, 50000.0), "wall": (1.0, 2000.0),
          "g3d": (0.0, 50.0)}
DEFAULTS = {"ticks": 60, "gravity": 980.0, "speed": 900.0, "wall": 16.0, "g3d": 9.8}
TOL = {"fall_discrete_pct": 0.5, "fall_pct": 3.0, "range_pct": 3.0, "momentum_pct": 3.0, "energy_pct": 10.0,
       "stack_px": 2.0, "fall3d_pct": 3.0}


class PhysicsError(G.GameError):
    pass


class GamePhysics(Base):
    __tablename__ = "game_physics"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gp"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    studio_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    words: Mapped[str] = mapped_column(Text, default="")
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)        # her numbers (speed, wall, ticks, gravity, g3d)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)      # what Hoola chose: ticks, gravity, ccd, why
    lab: Mapped[dict] = mapped_column(JSON, default=dict)           # {cases, verdict, fingerprints, engine, seconds}
    status: Mapped[str] = mapped_column(String(12), default="testing")   # testing | draft | approved | rejected | failed
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        GamePhysics.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


# ================================================================ the formulas (the lab is checked against these)
def fall_analytic(g: float, t: float) -> float:
    return 0.5 * g * t * t


def fall_discrete(g: float, ticks: int, n: int) -> float:
    """Semi-implicit (symplectic) Euler, what Godot steps: v += g dt; y += v dt  ->  y_n = g dt^2 n (n + 1) / 2."""
    dt = 1.0 / ticks
    return g * dt * dt * n * (n + 1) / 2.0


def projectile_range(vx: float, vy: float, g: float) -> float:
    return 2.0 * vx * vy / g if g > 0 else float("inf")


def elastic(m1: float, m2: float, v1: float, v2: float = 0.0) -> tuple[float, float]:
    return ((m1 - m2) * v1 + 2 * m2 * v2) / (m1 + m2), ((m2 - m1) * v2 + 2 * m1 * v1) / (m1 + m2)


def tunnel_risk(speed: float, wall: float, ticks: int) -> dict[str, Any]:
    """MEASURED in Godot 4.7.2 (Hoola's lab): without CCD a body is pushed out of the wall on whichever side its
    centre is nearer, so once one step can carry the centre past the MIDDLE of the wall the result depends on where
    the steps happen to land - sometimes it stops, sometimes it goes through. Safe without CCD only when one step
    <= half the wall."""
    step = speed / ticks
    need = math.ceil(2 * speed / wall) if wall > 0 else 10 ** 6
    return {"step_px": round(step, 2), "wall_px": wall, "risk": step > wall / 2, "ticks_needed": min(need, 10 ** 6),
            "ticks_enough": need <= LIMITS["ticks"][1]}


def choose(inputs: dict) -> dict[str, Any]:
    """The settings, worked out in code (never by a model): keep her tick rate when nothing tunnels; otherwise raise
    the ticks if a modest rise is enough (<= 120), else continuous collision (CCD, cast-ray mode - the mode that
    stopped every case in the lab; cast-shape did not in Godot 4.7.2) on the fast bodies at her ticks."""
    ticks, speed, wall = int(inputs["ticks"]), float(inputs["speed"]), float(inputs["wall"])
    r = tunnel_risk(speed, wall, ticks)
    safe = round(wall / 2 * ticks, 1)
    if not r["risk"]:
        return {"ticks": ticks, "gravity": inputs["gravity"], "ccd": False, "ccd_min_speed": safe,
                "why": f"one tick moves {r['step_px']} px, at most half the {wall:g} px wall: no tunnelling at {ticks} ticks"}
    if r["ticks_needed"] <= 120:
        t2 = max(ticks, int(r["ticks_needed"]))
        return {"ticks": t2, "gravity": inputs["gravity"], "ccd": False, "ccd_min_speed": round(wall / 2 * t2, 1),
                "why": f"at {ticks} ticks one step is {r['step_px']} px (more than half the {wall:g} px wall): {t2} ticks "
                       f"makes it {round(speed / t2, 1)} px"}
    return {"ticks": ticks, "gravity": inputs["gravity"], "ccd": True, "ccd_min_speed": safe,
            "why": f"one step is {r['step_px']} px against a {wall:g} px wall and {r['ticks_needed']} ticks would cost too "
                   f"much: continuous collision (CCD, cast-ray) on bodies faster than {round(safe)} px/s"}


def clean_inputs(inputs: dict | None) -> dict:
    out = dict(DEFAULTS)
    for k, v in (inputs or {}).items():
        if k in out:
            try:
                lo, hi = LIMITS[k]
                out[k] = min(max(float(v), lo), hi)
            except (TypeError, ValueError):
                pass
    out["ticks"] = int(round(out["ticks"]))
    return out


def from_words(words: str) -> dict:
    """Numbers she typed ('900 px/s', 'wall 12', '120 ticks', 'gravity 1500') - read by rules, nothing invented."""
    w = (words or "").lower()
    got: dict[str, float] = {}
    pats = {"speed": r"(\d+(?:\.\d+)?)\s*(?:px|pixel)s?\s*(?:/|per)\s*s", "wall": r"(?:wall|deewar|thick\w*)\D{0,12}(\d+(?:\.\d+)?)",
            "ticks": r"(\d+)\s*(?:ticks?|hz|fps physics|physics fps)", "gravity": r"(?:gravity|g)\s*[=:]?\s*(\d+(?:\.\d+)?)"}
    for k, pat in pats.items():
        m = re.search(pat, w)
        if m:
            got[k] = float(m.group(1))
    return got


def from_bible(tenant: str, studio_id: str) -> dict:
    """Her game's own numbers: the biggest 'speed' in the Game Bible (px/s) - a fact from her data, not a guess."""
    try:
        from . import bible as B
        data = B.view(tenant, studio_id).get("data") or {}
    except Exception:                                   # noqa: BLE001
        return {}
    best = 0.0

    def walk(x: Any) -> None:
        nonlocal best
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(v, (int, float)) and "speed" in str(k).lower():
                    best = max(best, float(v))
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(data)
    return {"speed": best} if best > 0 else {}


# ================================================================ the lab (Hoola's own GDScript)
LAB = '''extends Node
# Hoola physics lab (written by Hoola, not by a model). Each case runs far from the others; results print as one line.
const CFG := __CFG__
var frame := 0
var res := {}
var fall: RigidBody2D
var proj: RigidBody2D
var proj_y0 := 0.0
var proj_done := false
var b1: RigidBody2D
var b2: RigidBody2D
var bullets := {"off": [], "ray": [], "shape": []}
var boxes: Array = []
var box_start: Array = []
var fall3d: RigidBody3D

func _body(pos: Vector2, r: float, mass: float, gscale: float, vel: Vector2, bounce: float, ccd: int) -> RigidBody2D:
	var b := RigidBody2D.new()
	var cs := CollisionShape2D.new()
	var sh := CircleShape2D.new()
	sh.radius = r
	cs.shape = sh
	b.add_child(cs)
	b.position = pos
	b.mass = mass
	b.gravity_scale = gscale
	b.linear_damp_mode = RigidBody2D.DAMP_MODE_REPLACE
	b.linear_damp = 0.0
	b.angular_damp_mode = RigidBody2D.DAMP_MODE_REPLACE
	b.angular_damp = 0.0
	b.can_sleep = false
	b.linear_velocity = vel
	var m := PhysicsMaterial.new()
	m.bounce = bounce
	m.friction = 0.0
	b.physics_material_override = m
	b.continuous_cd = ccd
	add_child(b)
	return b

func _wall(pos: Vector2, size: Vector2) -> void:
	var s := StaticBody2D.new()
	var cs := CollisionShape2D.new()
	var sh := RectangleShape2D.new()
	sh.size = size
	cs.shape = sh
	s.add_child(cs)
	s.position = pos
	add_child(s)

func _ready() -> void:
	Engine.physics_ticks_per_second = int(CFG["ticks"])
	Engine.max_physics_steps_per_frame = 16
	var space := get_viewport().world_2d.space
	PhysicsServer2D.area_set_param(space, PhysicsServer2D.AREA_PARAM_GRAVITY, float(CFG["gravity"]))
	PhysicsServer2D.area_set_param(space, PhysicsServer2D.AREA_PARAM_GRAVITY_VECTOR, Vector2(0, 1))
	fall = _body(Vector2(0, 0), 8, 1.0, 1.0, Vector2.ZERO, 0.0, 0)
	proj = _body(Vector2(20000, 0), 8, 1.0, 1.0, Vector2(CFG["vx"], -float(CFG["vy"])), 0.0, 0)
	proj_y0 = 0.0
	b1 = _body(Vector2(40000, 0), 10, 1.0, 0.0, Vector2(CFG["v1"], 0), 1.0, 0)
	b2 = _body(Vector2(40100, 0), 10, 2.0, 0.0, Vector2.ZERO, 1.0, 0)
	# tunnelling: six bullets per mode, each starting at a different point within one step (a lucky landing cannot pass)
	var step := float(CFG["speed"]) / float(CFG["ticks"])
	var modes := {"off": RigidBody2D.CCD_MODE_DISABLED, "ray": RigidBody2D.CCD_MODE_CAST_RAY, "shape": RigidBody2D.CCD_MODE_CAST_SHAPE}
	var row := 0
	for m in modes:
		for k in 6:
			var y := float(row) * 1000.0
			_wall(Vector2(60400, y), Vector2(CFG["wall"], 400))
			bullets[m].append(_body(Vector2(60000 + step * k / 6.0, y), 2, 1.0, 0.0, Vector2(CFG["speed"], 0), 0.0, modes[m]))
			row += 1
	_wall(Vector2(80000, 200), Vector2(2000, 40))
	for i in 6:
		var b := RigidBody2D.new()
		var cs := CollisionShape2D.new()
		var sh := RectangleShape2D.new()
		sh.size = Vector2(32, 32)
		cs.shape = sh
		b.add_child(cs)
		b.position = Vector2(80000, 180 - 16 - i * 32)
		add_child(b)
		boxes.append(b)
		box_start.append(b.position)
	var w3: Variant = PhysicsServer3D.area_get_param(get_viewport().world_3d.space, PhysicsServer3D.AREA_PARAM_GRAVITY)
	res["g3d_world"] = w3
	PhysicsServer3D.area_set_param(get_viewport().world_3d.space, PhysicsServer3D.AREA_PARAM_GRAVITY, float(CFG["g3d"]))
	fall3d = RigidBody3D.new()
	var c3 := CollisionShape3D.new()
	c3.shape = SphereShape3D.new()
	fall3d.add_child(c3)
	fall3d.linear_damp_mode = RigidBody3D.DAMP_MODE_REPLACE
	fall3d.linear_damp = 0.0
	fall3d.can_sleep = false
	add_child(fall3d)
	res["engine3d"] = String(ProjectSettings.get_setting("physics/3d/physics_engine", "DEFAULT"))
	res["engine2d"] = String(ProjectSettings.get_setting("physics/2d/physics_engine", "DEFAULT"))

func _physics_process(_delta: float) -> void:
	frame += 1
	var steps := frame - 1
	var t := int(CFG["ticks"])
	if steps == t:
		res["fall_y"] = fall.position.y
		res["fall_steps"] = steps
		res["fall3d_y"] = -fall3d.position.y
	if not proj_done and steps > 2 and proj.position.y >= proj_y0:
		proj_done = true
		var prev_y: float = proj.position.y - proj.linear_velocity.y / t
		var f: float = (proj_y0 - prev_y) / maxf(0.0001, proj.position.y - prev_y)
		res["proj_x"] = proj.position.x - 20000.0 - (1.0 - f) * proj.linear_velocity.x / t
	if steps == int(t * 0.8):
		res["v1"] = b1.linear_velocity.x
		res["v2"] = b2.linear_velocity.x
	if steps == t * 2:
		var wall_left := 60400.0 - float(CFG["wall"]) / 2.0
		for m in bullets:
			var through := 0
			for b in bullets[m]:
				if b.position.x > wall_left + 1.0:
					through += 1
			res["through_" + m] = through
	if steps == t * 3:
		var drift := 0.0
		var sink := 0.0
		for i in boxes.size():
			drift = maxf(drift, absf(boxes[i].position.x - box_start[i].x))
			sink = maxf(sink, boxes[i].position.y - box_start[i].y)
		res["stack_drift"] = drift
		res["stack_sink"] = sink
		res["top_y"] = boxes[5].position.y
		print("HOOLA_PHYS " + JSON.stringify(res))
		get_tree().quit()
'''


def _lab_cfg(st: dict) -> dict:
    return {"ticks": int(st["ticks"]), "gravity": float(st["gravity"]), "speed": float(st["speed"]), "wall": float(st["wall"]),
            "vx": 300.0, "vy": 400.0, "v1": 300.0, "g3d": float(st.get("g3d", 9.8))}


def _run_lab(job: Path, cfg: dict) -> dict:
    from . import engine, template
    from .bible import _gd
    shutil.rmtree(job / "proj", ignore_errors=True)
    (job / "proj").mkdir(parents=True)
    scripts = {"main.gd": LAB.replace("__CFG__", _gd(cfg))}
    for name, txt in template.files("Hoola physics lab", "landscape", scripts).items():
        (job / "proj" / name).write_text(txt, encoding="utf-8")
    frames = int(cfg["ticks"]) * 3 + 30
    code, logtxt, to = engine._run(job, ["--path", "proj", "--fixed-fps", "60", "--quit-after", str(frames * 4 + 60)],
                                   "lab.log", 120)
    m = re.search(r"HOOLA_PHYS (\{.*\})", logtxt or "")
    if not m:
        errs = engine.errors_in(logtxt or "") or [(logtxt or "").strip()[-300:] or "the lab printed nothing"]
        raise PhysicsError("Physics lab nahi chala: " + "; ".join(errs[:3])[:400])
    return json.loads(m.group(1))


def _pct(a: float, b: float) -> float:
    return round(abs(a - b) / abs(b) * 100, 2) if b else (0.0 if a == 0 else 100.0)


def judge(raw: dict, raw2: dict | None, st: dict) -> dict:
    """Every case against its formula, in code. PASS / FAIL per case + one verdict."""
    t = int(st["ticks"])
    g = float(st["gravity"])
    cases: list[dict] = []

    def case(name: str, ok: bool, measured: Any, expected: Any, note: str) -> None:
        cases.append({"case": name, "ok": bool(ok), "measured": measured, "expected": expected, "note": note})
    y = float(raw.get("fall_y", 0))
    disc = fall_discrete(g, t, int(raw.get("fall_steps", t)))
    ana = fall_analytic(g, 1.0)
    case("free fall (1 s)", _pct(y, disc) <= TOL["fall_discrete_pct"] and _pct(y, ana) <= TOL["fall_pct"],
         round(y, 2), round(ana, 2),
         f"{_pct(y, ana)}% from 1/2 g t^2; {_pct(y, disc)}% from the integrator's own step answer ({round(disc, 2)}) - the "
         f"gap is semi-implicit Euler at {t} ticks, it halves when the ticks double")
    rx = float(raw.get("proj_x", 0))
    er = projectile_range(300.0, 400.0, g)
    case("projectile range", _pct(rx, er) <= TOL["range_pct"], round(rx, 1), round(er, 1), f"{_pct(rx, er)}% from 2 vx vy / g")
    v1, v2 = float(raw.get("v1", 0)), float(raw.get("v2", 0))
    e1, e2 = elastic(1.0, 2.0, 300.0)
    p0, p1 = 300.0, v1 + 2 * v2
    k0, k1 = 0.5 * 300.0 ** 2, 0.5 * v1 ** 2 + 0.5 * 2 * v2 ** 2
    case("elastic collision", _pct(p1, p0) <= TOL["momentum_pct"] and _pct(k1, k0) <= TOL["energy_pct"],
         {"v1": round(v1, 1), "v2": round(v2, 1)}, {"v1": round(e1, 1), "v2": round(e2, 1)},
         f"momentum kept within {_pct(p1, p0)}%, kinetic energy within {_pct(k1, k0)}%")
    thr = {m: int(raw.get("through_" + m, 6)) for m in ("off", "ray", "shape")}
    mode = "ray" if st.get("ccd") else "off"
    word = {m: ("stopped 6 of 6" if thr[m] == 0 else f"WENT THROUGH {thr[m]} of 6") for m in thr}
    case("tunnelling at your speed", thr[mode] == 0,
         {"without_ccd": word["off"], "ccd_cast_ray": word["ray"], "ccd_cast_shape": word["shape"]}, "stopped 6 of 6",
         f"{st['speed']:g} px/s into a {st['wall']:g} px wall at {t} ticks ({round(st['speed'] / t, 1)} px a step), six "
         f"start points each; the chosen setup ({'CCD cast-ray' if st.get('ccd') else 'no CCD'}) "
         f"{'stops every one' if thr[mode] == 0 else 'does NOT stop every one'}"
         + ("; cast-shape CCD let some through in this engine version - Hoola uses cast-ray" if thr["shape"] else ""))
    drift, sink = float(raw.get("stack_drift", 99)), float(raw.get("stack_sink", 99))
    case("box stack (3 s)", drift <= TOL["stack_px"] and sink <= TOL["stack_px"] + 2, {"drift_px": round(drift, 2), "sink_px": round(sink, 2)},
         f"<= {TOL['stack_px']} px", "six 32 px boxes settle without sliding or sinking")
    y3 = float(raw.get("fall3d_y", 0))
    a3 = fall_analytic(float(st.get("g3d", 9.8)), 1.0)
    case("3D free fall (1 s)", _pct(y3, a3) <= TOL["fall3d_pct"], round(y3, 3), round(a3, 3),
         f"{_pct(y3, a3)}% from 1/2 g t^2 in the 3D engine ({raw.get('engine3d') or 'default'})")
    fp1 = hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()[:16]
    fp2 = hashlib.sha256(json.dumps(raw2, sort_keys=True).encode()).hexdigest()[:16] if raw2 is not None else ""
    if raw2 is not None:
        case("same run twice", fp1 == fp2, fp2, fp1, "the whole lab ran twice; the results must be identical")
    ok = all(c["ok"] for c in cases)
    return {"cases": cases, "verdict": "PASS" if ok else "FAIL", "fingerprints": [fp1, fp2],
            "engine3d": raw.get("engine3d", ""), "engine2d": raw.get("engine2d", ""),
            "passed": sum(1 for c in cases if c["ok"]), "total": len(cases)}


# ================================================================ store + jobs
def _root(tenant: str) -> Path:
    return G.root() / (re.sub(r"[^\w-]", "_", tenant)[:64] or "t") / "physics"


def _studio(tenant: str, ref: str):
    from . import studio as S
    with session() as s:
        r = S._studio(s, tenant, ref)
        s.expunge(r)
    return r


def _get(s, tenant: str, ref: str) -> GamePhysics:
    ref = str(ref or "").strip()
    q = select(GamePhysics).where(GamePhysics.tenant_id == tenant)
    r = s.scalars(q.where(GamePhysics.id == ref)).first() or s.scalars(q.where(GamePhysics.number == ref.upper())).first()
    if r is None:
        raise PhysicsError("Yeh physics setup nahi mila (P-001 dijiye).")
    return r


def view(r: GamePhysics) -> dict[str, Any]:
    return {"id": r.id, "number": r.number, "status": r.status, "words": r.words, "inputs": r.inputs or {},
            "settings": r.settings or {}, "lab": r.lab or {}, "error": r.error, "studio_id": r.studio_id,
            "risk": tunnel_risk(float((r.inputs or DEFAULTS)["speed"]), float((r.inputs or DEFAULTS)["wall"]),
                                int((r.inputs or DEFAULTS)["ticks"])),
            "fluids": "not built yet", "at": r.created_at.isoformat() if r.created_at else ""}


def setup(tenant: str, words: str = "", inputs: dict | None = None, studio: str = "", run_now: bool = True) -> dict[str, Any]:
    """Her numbers (typed, read from her words or from the Game Bible) -> settings worked out in code -> the lab runs
    in the background in the real engine. Free."""
    ensure_table()
    sid = _studio(tenant, studio).id if studio else ""
    got = {**(from_bible(tenant, sid) if sid else {}), **from_words(words), **(inputs or {})}
    inp = clean_inputs(got)
    st = {**choose(inp), "speed": inp["speed"], "wall": inp["wall"], "g3d": inp["g3d"]}
    with session() as s:
        n = len(s.scalars(select(GamePhysics.id).where(GamePhysics.tenant_id == tenant)).all()) + 1
        r = GamePhysics(tenant_id=tenant, studio_id=sid, number=f"P-{n:03d}", words=(words or "")[:600], inputs=inp,
                        settings=st, status="testing")
        s.add(r)
        s.flush()
        s.expunge(r)
    if run_now:
        _POOL.submit(_safe_lab, r.id)
    return view(r)


def _safe_lab(pid: str) -> None:
    try:
        run_lab(pid)
    except Exception as e:                              # noqa: BLE001
        log.exception("physics lab %s", pid)
        with session() as s:
            r = s.get(GamePhysics, pid)
            if r is not None:
                r.status, r.error = "failed", str(e)[:400]


def run_lab(pid: str) -> dict[str, Any]:
    with session() as s:
        r = s.get(GamePhysics, pid)
        s.expunge(r)
    job = _root(r.tenant_id) / r.id
    t0 = time.time()
    cfg = _lab_cfg(r.settings)
    raw = _run_lab(job / "a", cfg)
    raw2 = _run_lab(job / "b", cfg)
    lab = judge(raw, raw2, r.settings)
    inp = r.inputs or {}
    if int(r.settings.get("ticks", 0)) != int(inp.get("ticks", 0)) or r.settings.get("ccd"):
        # the evidence for the change: HER settings as they were (her ticks, no CCD), same six start points
        before = _run_lab(job / "before", {**cfg, "ticks": int(inp.get("ticks", 60))})
        n = int(before.get("through_off", 0))
        lab["before"] = {"ticks": int(inp.get("ticks", 60)), "ccd": False, "through": n,
                         "say": (f"at your {int(inp.get('ticks', 60))} ticks without CCD {n} of 6 bullets went through the wall"
                                 if n else f"at your {int(inp.get('ticks', 60))} ticks without CCD all 6 stopped this time - "
                                           "but one step is over half the wall, so it depends on where the steps land")}
    lab["seconds"] = round(time.time() - t0, 1)
    lab["raw"] = raw
    with session() as s:
        row = s.get(GamePhysics, pid)
        row.lab = lab
        row.status = "draft" if lab["verdict"] == "PASS" else "failed"
        row.error = "" if lab["verdict"] == "PASS" else "; ".join(c["case"] + ": " + c["note"] for c in lab["cases"] if not c["ok"])[:400]
        row.updated_at = now()
        s.flush()
        s.expunge(row)
    shutil.rmtree(job, ignore_errors=True)
    return view(row)


def approve(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _get(s, tenant, ref)
        if r.status != "draft":
            raise PhysicsError("Sirf PASS hua physics setup OK ho sakta hai." if r.status != "testing" else "Lab abhi chal raha hai.")
        for o in s.scalars(select(GamePhysics).where(GamePhysics.tenant_id == tenant, GamePhysics.studio_id == r.studio_id,
                                                     GamePhysics.status == "approved")).all():
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
        q = select(GamePhysics).where(GamePhysics.tenant_id == tenant)
        if sid is not None:
            q = q.where(GamePhysics.studio_id == sid)
        rows = s.scalars(q.order_by(GamePhysics.created_at.desc())).all()[:30]
        for r in rows:
            s.expunge(r)
    return [view(r) for r in rows]


def get(tenant: str, ref: str) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        r = _get(s, tenant, ref)
        s.expunge(r)
    return view(r)


GD = '''extends Node
# HoolaPhysics (an autoload): her game's physics settings, PROVED in Hoola's physics lab (verdict below).
# Written by Hoola Studio; do not edit (approve a physics setup in the Studio and rebuild).
const SETTINGS := __S__

func _ready() -> void:
	Engine.physics_ticks_per_second = int(SETTINGS["ticks"])
	Engine.max_physics_steps_per_frame = 16
	var vp := get_viewport()
	if vp and vp.world_2d:
		PhysicsServer2D.area_set_param(vp.world_2d.space, PhysicsServer2D.AREA_PARAM_GRAVITY, float(SETTINGS["gravity"]))

func gravity() -> float:
	return float(SETTINGS["gravity"])

func fast(body: RigidBody2D) -> void:
	# continuous collision for a fast body (it then cannot pass through a thin wall in one step)
	# cast-ray: the mode Hoola's lab measured stopping every case (cast-shape did not, Godot 4.7.2)
	body.continuous_cd = RigidBody2D.CCD_MODE_CAST_RAY

func needs_ccd(speed: float) -> bool:
	return bool(SETTINGS["ccd"]) and speed >= float(SETTINGS["ccd_min_speed"])

func step_ok(speed: float, thickness: float) -> bool:
	# safe without CCD only when one step is at most half the wall (measured in Hoola's lab)
	return speed / float(SETTINGS["ticks"]) <= thickness / 2.0

func jump_velocity(height_px: float) -> float:
	# the take-off speed that reaches height_px under this gravity: v = sqrt(2 g h)
	return sqrt(2.0 * gravity() * max(0.0, height_px))

func jump_height(v: float) -> float:
	return v * v / (2.0 * gravity())

func air_time(v: float) -> float:
	return 2.0 * v / gravity()

func range_of(vx: float, vy: float) -> float:
	return 2.0 * vx * vy / gravity()
'''


def gd(st: dict, verdict: str) -> str:
    from .bible import _gd
    keep = {k: st[k] for k in ("ticks", "gravity", "ccd", "ccd_min_speed") if k in st}
    keep["verdict"] = verdict
    return GD.replace("__S__", _gd(keep))


def for_game(tenant: str, game_id: str) -> tuple[str, dict[str, Path]] | None:
    from . import studio as S
    ensure_table()
    with session() as s:
        st = s.scalars(select(S.GameStudio).where(S.GameStudio.tenant_id == tenant, S.GameStudio.game_id == game_id)).first()
        if st is None:
            return None
        r = s.scalars(select(GamePhysics).where(GamePhysics.tenant_id == tenant, GamePhysics.studio_id == st.id,
                                                GamePhysics.status == "approved").order_by(GamePhysics.created_at.desc())).first()
        if r is None:
            return None
        s.expunge(r)
    return gd(r.settings, (r.lab or {}).get("verdict", "")), {}


def apply(tenant: str, studio: str) -> dict[str, Any]:
    st = _studio(tenant, studio)
    if for_game(tenant, st.game_id) is None:
        raise PhysicsError("Koi approved physics setup nahi; pehle lab PASS karke OK kijiye.")
    try:
        from . import bible as B
        bv = B.view(tenant, st.id)["version"]
    except Exception:                                   # noqa: BLE001
        bv = 0
    G.data_build(tenant, st.game_id, bv, words="Physics settings game mein")
    return {"ok": True, "say": "Physics settings game mein ja rahi hain (rebuild chal raha hai)."}
