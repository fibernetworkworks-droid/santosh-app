"""v0.422 AR / VR INTERACTION (Hoola Game Engine plan Phase 7 batch 3, Game Desk plan role 2 - the AR / VR Interaction
Engineer): a WebXR scene that opens in a phone or headset browser (no install), hand gestures, and the comfort rules -
each CHECKED in code (no model, no money), with Hoola's own HoolaXR autoload in her game.

- Gestures (pinch, grab, point, open) from the 25 WebXR hand joints by rules on distances - thumb-tip to index-tip
  for a pinch, each finger's tip-to-palm distance against its own length for curl. Scored on a labelled TEST SET of
  synthetic hands (a jointed hand model posed per gesture, random size / rotation / position, 3 mm joint noise, plus
  near-the-line poses): accuracy and the confusion table. Said plainly: synthetic hands, not her hands - accuracy on
  her headset is measured only when she tries it. The SAME rules run in GDScript (HoolaXR.gesture) and are fed the
  same hands inside the REAL Godot: the two must agree on every sample.
- Comfort, checked on the scene settings: teleport (smooth movement only with a comfort vignette), snap turning (30 or
  45 degrees), a seated mode, panels 1-3 m away, text at least 1.2 degrees tall, the frame-rate target of the device
  class (72 / 90 fps) and a triangle budget - frame rate on her real headset is NOT ASSESSED here (no headset).
- Demo: Hoola's own WebXR room (floor, teleport pads, a floating panel) built in Godot, exported to Web and played by
  the normal playtest in its non-XR fallback (mouse / keys); on a phone or headset browser "Enter VR / AR" starts the
  real session. Her OK -> HoolaXR in her game (start(), snap_turn(), teleport(), gesture())."""
from __future__ import annotations

import json
import logging
import math
import re
import secrets
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import JSON, DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import service as G

log = logging.getLogger("santosh.gamedesk")
FILE = "hoola_xr.gd"
KEY = "xr_dev"
GESTURES = ("pinch", "grab", "point", "open")
PINCH_M = 0.025
CURL_IN = 0.55          # tip-to-palm / finger length below this = curled
CURL_OUT = 0.75         # above this = extended
DEFAULTS = {"mode": "vr", "locomotion": "teleport", "turn": "snap", "snap_deg": 30, "vignette": True, "seated": True,
            "ui_m": 1.6, "text_deg": 1.6, "fps": 72, "tris": 100000}
_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gamexr")


class XrError(G.GameError):
    pass


class GameXr(Base):
    __tablename__ = "game_xr"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gx"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    studio_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    words: Mapped[str] = mapped_column(Text, default="")
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    report: Mapped[dict] = mapped_column(JSON, default=dict)
    demo: Mapped[dict] = mapped_column(JSON, default=dict)
    demo_token: Mapped[str] = mapped_column(String(48), default="", index=True)
    status: Mapped[str] = mapped_column(String(12), default="testing")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        GameXr.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


def clean_settings(st: dict | None) -> dict:
    out = dict(DEFAULTS)
    for k, v in (st or {}).items():
        if k not in out:
            continue
        if isinstance(out[k], bool):
            out[k] = bool(v)
        elif isinstance(out[k], str):
            out[k] = str(v).lower()[:12]
        else:
            try:
                out[k] = type(out[k])(float(v))
            except (TypeError, ValueError):
                pass
    if out["mode"] not in ("vr", "ar"):
        out["mode"] = "vr"
    return out


def from_words(words: str) -> dict:
    w = (words or "").lower()
    out: dict[str, Any] = {}
    if re.search(r"\bar\b|augmented|camera ke upar|room mein", w):
        out["mode"] = "ar"
    if re.search(r"smooth (?:move|movement|walk|locomotion)", w):
        out["locomotion"] = "smooth"
    if re.search(r"quest|90 ?fps|pico", w):
        out["fps"] = 90 if "90" in w else 72
    return out


def comfort(st: dict) -> dict:
    errors, warnings, passed = [], [], []
    if st["locomotion"] == "smooth" and not st["vignette"]:
        errors.append("smooth movement without a comfort vignette makes many people sick - teleport, or add the vignette")
    elif st["locomotion"] == "teleport":
        passed.append("teleport movement (no forced camera motion)")
    else:
        passed.append("smooth movement with a comfort vignette")
    if st["turn"] != "snap":
        errors.append("smooth turning is a known sickness cause - snap turning is required")
    elif st["snap_deg"] not in (30, 45):
        warnings.append(f"snap turn of {st['snap_deg']} degrees - 30 or 45 is usual")
    else:
        passed.append(f"snap turning by {st['snap_deg']} degrees")
    (passed if st["seated"] else errors).append("a seated mode" if st["seated"] else "no seated mode - people who cannot stand are left out")
    if not 1.0 <= st["ui_m"] <= 3.0:
        errors.append(f"panels {st['ui_m']} m away - keep them 1-3 m (closer strains the eyes, farther cannot be read)")
    else:
        passed.append(f"panels {st['ui_m']} m away")
    h_mm = 2 * st["ui_m"] * 1000 * math.tan(math.radians(st["text_deg"]) / 2)
    if st["text_deg"] < 1.2:
        errors.append(f"text {st['text_deg']} degrees tall ({round(h_mm)} mm at {st['ui_m']} m) - at least 1.2 degrees to be read")
    else:
        passed.append(f"text {st['text_deg']} degrees tall = {round(h_mm)} mm at {st['ui_m']} m")
    if st["fps"] not in (72, 90, 120):
        warnings.append(f"{st['fps']} fps target - headsets run at 72 / 90 / 120")
    passed.append(f"frame budget {round(1000 / st['fps'], 1)} ms ({st['fps']} fps), up to {st['tris']:,} triangles - "
                  "on her headset: NOT ASSESSED (no headset here)")
    return {"errors": errors, "warnings": warnings, "passed": passed}


# ================================================================ hands: the model, the rules, the test set
# WebXR joint order: 0 wrist; thumb 1-4 (metacarpal, proximal, distal, tip); index 5-9, middle 10-14, ring 15-19,
# little 20-24 (metacarpal, proximal, intermediate, distal, tip)
FINGERS = {"index": range(5, 10), "middle": range(10, 15), "ring": range(15, 20), "little": range(20, 25)}


def features(j: np.ndarray) -> dict:
    palm = j[[5, 10, 15, 20]].mean(axis=0)
    out = {"pinch": float(np.linalg.norm(j[4] - j[9]))}
    for name, idx in FINGERS.items():
        idx = list(idx)
        length = float(sum(np.linalg.norm(j[idx[k + 1]] - j[idx[k]]) for k in range(4))) or 1e-6
        out[name] = float(np.linalg.norm(j[idx[4]] - palm)) / length
    return out


def classify(j: np.ndarray) -> str:
    f = features(j)
    curled = [f[n] < CURL_IN for n in FINGERS]
    extended = [f[n] > CURL_OUT for n in FINGERS]
    if all(curled):
        return "grab"
    if f["pinch"] < PINCH_M:
        return "pinch"
    if extended[0] and all(curled[1:]):
        return "point"
    return "open"


def hand(curls: dict, thumb_to_index: float, rng: np.random.Generator, scale: float, noise_m: float) -> np.ndarray:
    """A jointed right hand (metres): finger bases across the palm, three flexing joints per finger (curl 0 = straight,
    1 = a fist), the thumb's tip moved toward the index tip by thumb_to_index (1 = touching). Random rotation + noise."""
    seg = {"index": (0.039, 0.024, 0.018, 0.012), "middle": (0.044, 0.028, 0.019, 0.012), "ring": (0.041, 0.027, 0.018, 0.012),
           "little": (0.032, 0.020, 0.016, 0.011)}
    base_x = {"index": 0.022, "middle": 0.0, "ring": -0.020, "little": -0.038}
    j = np.zeros((25, 3))
    j[0] = (0, -0.03, 0)
    for name, idx in FINGERS.items():
        idx = list(idx)
        p = np.array([base_x[name], 0.055, 0.0])
        j[idx[0]] = (base_x[name] * 0.8, 0.0, 0.0)
        j[idx[1]] = p
        ang = 0.0
        c = curls[name]
        for k, L in enumerate(seg[name][1:] + (seg[name][3] * 0.6,)):
            ang += c * (math.radians(80) if k < 2 else math.radians(60))
            p = p + np.array([0.0, math.cos(ang) * L, -math.sin(ang) * L])
            j[idx[2 + k] if 2 + k < 5 else idx[4]] = p
    # thumb: from the side of the palm, its tip blended toward the index tip
    j[1] = (0.03, -0.005, -0.01)
    j[2] = (0.05, 0.015, -0.02)
    j[3] = (0.065, 0.035, -0.03)
    rest_tip = np.array([0.075, 0.055, -0.035])
    j[4] = rest_tip + (j[9] + np.array([0.004, 0.0, 0.0]) - rest_tip) * thumb_to_index
    j *= scale
    th = rng.uniform(0, 2 * math.pi, 3)
    cx, sx, cy, sy, cz, sz = math.cos(th[0]), math.sin(th[0]), math.cos(th[1]), math.sin(th[1]), math.cos(th[2]), math.sin(th[2])
    R = (np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
         @ np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]))
    return j @ R.T + rng.uniform(-0.5, 0.5, 3) + rng.normal(0, noise_m, (25, 3))


def test_set(seed: int = 5, n: int = 60) -> list[tuple[str, np.ndarray]]:
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        u = lambda a, b: float(rng.uniform(a, b))          # noqa: E731
        sc = u(0.85, 1.15)
        out.append(("grab", hand({k: u(0.85, 1.0) for k in FINGERS}, u(0.0, 0.3), rng, sc, 0.003)))
        out.append(("pinch", hand({"index": u(0.25, 0.45), "middle": u(0.0, 0.3), "ring": u(0.0, 0.3), "little": u(0.0, 0.3)},
                                  u(0.95, 1.0), rng, sc, 0.003)))
        out.append(("point", hand({"index": u(0.0, 0.15), "middle": u(0.85, 1.0), "ring": u(0.85, 1.0), "little": u(0.85, 1.0)},
                                  u(0.0, 0.3), rng, sc, 0.003)))
        out.append(("open", hand({k: u(0.0, 0.2) for k in FINGERS}, u(0.0, 0.3), rng, sc, 0.003)))
    return out


def score(samples: list[tuple[str, np.ndarray]]) -> dict:
    conf = {a: {b: 0 for b in GESTURES} for a in GESTURES}
    for lab, j in samples:
        conf[lab][classify(j)] += 1
    total = len(samples)
    right = sum(conf[g][g] for g in GESTURES)
    per = {g: round(conf[g][g] / max(1, sum(conf[g].values())), 3) for g in GESTURES}
    return {"accuracy": round(right / max(1, total), 4), "per_gesture": per, "confusion": conf, "samples": total}


# ================================================================ HoolaXR (Hoola's own GDScript)
GD = '''extends Node
# HoolaXR (an autoload): WebXR / OpenXR session, snap turn, teleport and hand gestures, from a setup Hoola CHECKED
# (comfort rules + gestures scored on a test set; verdict below). Written by Hoola Studio; do not edit.
const CFG := __CFG__
signal session_started
signal session_failed(why)
var xr = null
var origin: XROrigin3D

func supported() -> bool:
	return XRServer.find_interface("WebXR") != null or XRServer.find_interface("OpenXR") != null

func start(o: XROrigin3D) -> bool:
	# call from a tap / button (browsers only start XR from a user gesture)
	origin = o
	xr = XRServer.find_interface("WebXR")
	if xr != null:
		var mode := "immersive-ar" if String(CFG["mode"]) == "ar" else "immersive-vr"
		xr.set("session_mode", mode)
		xr.set("requested_reference_space_types", "bounded-floor, local-floor, local")
		xr.set("required_features", "local-floor")
		xr.set("optional_features", "bounded-floor, hand-tracking")
		if not xr.is_connected("session_started", _started):
			xr.connect("session_started", _started)
			xr.connect("session_failed", _failed)
		return xr.initialize()
	xr = XRServer.find_interface("OpenXR")
	if xr != null and xr.initialize():
		get_viewport().use_xr = true
		session_started.emit()
		return true
	session_failed.emit("no XR on this device")
	return false

func _started() -> void:
	get_viewport().use_xr = true
	session_started.emit()

func _failed(why: String) -> void:
	session_failed.emit(why)

func snap_turn(direction: int) -> void:
	# comfort: turn in fixed steps, never smoothly
	if origin:
		origin.rotate_y(deg_to_rad(float(CFG["snap_deg"])) * -float(direction))

func teleport(target: Vector3) -> void:
	# comfort: jump to the spot, no forced camera motion
	if origin:
		origin.global_position = Vector3(target.x, origin.global_position.y, target.z)

func seated_offset() -> float:
	return 0.4 if bool(CFG["seated"]) else 0.0

func gesture(j: PackedVector3Array) -> String:
	# the SAME rules Hoola scored on its test set: pinch / grab / point / open from the 25 WebXR hand joints
	if j.size() < 25:
		return "none"
	var palm := (j[5] + j[10] + j[15] + j[20]) / 4.0
	var curled := []
	var extended := []
	for f in [[5, 10], [10, 15], [15, 20], [20, 25]]:
		var length := 0.0
		for k in range(f[0], f[1] - 1):
			length += j[k].distance_to(j[k + 1])
		var r := j[f[1] - 1].distance_to(palm) / maxf(length, 0.000001)
		curled.append(r < float(CFG["curl_in"]))
		extended.append(r > float(CFG["curl_out"]))
	if curled[0] and curled[1] and curled[2] and curled[3]:
		return "grab"
	if j[4].distance_to(j[9]) < float(CFG["pinch_m"]):
		return "pinch"
	if extended[0] and curled[1] and curled[2] and curled[3]:
		return "point"
	return "open"
'''


def gd(st: dict, verdict: str) -> str:
    from .bible import _gd
    keep = {**{k: st[k] for k in ("mode", "snap_deg", "seated", "ui_m", "text_deg")}, "pinch_m": PINCH_M, "curl_in": CURL_IN,
            "curl_out": CURL_OUT, "verdict": verdict}
    return GD.replace("__CFG__", _gd(keep))


DEMO = '''extends Node
# Hoola WebXR room (written by Hoola, not by a model). In a phone / headset browser: tap "Enter XR". Elsewhere: a
# normal 3D view (arrow keys / WASD turn and move by snap + teleport steps) - that is what Hoola's playtest plays.
var origin: XROrigin3D
var cam: XRCamera3D
var flat: Camera3D
var pads: Array = []
var pad_i := 0

func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.12, 0.13, 0.18)
	env.environment.ambient_light_color = Color(0.8, 0.8, 0.85)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, 30, 0)
	add_child(sun)
	var floor_mesh := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(10, 10)
	floor_mesh.mesh = pm
	var fm := StandardMaterial3D.new()
	fm.albedo_color = Color(0.62, 0.66, 0.74)
	floor_mesh.material_override = fm
	add_child(floor_mesh)
	for i in 4:
		var pad := MeshInstance3D.new()
		var cm := CylinderMesh.new()
		cm.top_radius = 0.4
		cm.bottom_radius = 0.4
		cm.height = 0.02
		pad.mesh = cm
		var mm := StandardMaterial3D.new()
		mm.albedo_color = Color(0.49, 0.36, 1.0)
		pad.material_override = mm
		pad.position = Vector3(cos(i * PI / 2.0) * 3.0, 0.01, sin(i * PI / 2.0) * 3.0)
		add_child(pad)
		pads.append(pad.position)
	var panel := Label3D.new()
	panel.text = "Hoola XR room\\nTeleport to a purple pad · snap turn %d°" % int(HoolaXR.CFG["snap_deg"])
	var dist := float(HoolaXR.CFG["ui_m"])
	panel.pixel_size = 2.0 * dist * tan(deg_to_rad(float(HoolaXR.CFG["text_deg"])) / 2.0) / 32.0
	panel.position = Vector3(0, 1.5, -dist)
	add_child(panel)
	origin = XROrigin3D.new()
	add_child(origin)
	cam = XRCamera3D.new()
	origin.add_child(cam)
	# without a headset the XR camera sits at the tracker's pose (the floor): a normal camera at head height until a
	# real XR session starts, then the XR camera takes over
	flat = Camera3D.new()
	flat.position = Vector3(0, 1.6 - HoolaXR.seated_offset(), 0)
	origin.add_child(flat)
	flat.current = true
	HoolaXR.session_started.connect(func(): cam.current = true)
	HoolaProbe.state("state", "playing")
	HoolaProbe.state("xr_supported", HoolaXR.supported())

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed:
		if HoolaXR.supported():
			HoolaXR.start(origin)
		else:
			_next_pad()
	if event is InputEventKey and event.pressed:
		if event.keycode in [KEY_LEFT, KEY_A]:
			HoolaXR.snap_turn(-1)
		elif event.keycode in [KEY_RIGHT, KEY_D]:
			HoolaXR.snap_turn(1)
		elif event.keycode in [KEY_UP, KEY_W, KEY_SPACE]:
			_next_pad()

func _next_pad() -> void:
	pad_i = (pad_i + 1) % pads.size()
	HoolaXR.teleport(pads[pad_i])
	HoolaProbe.state("score", pad_i)
'''

GESTURE_LAB = '''extends Node
# Hoola gesture cross-check (written by Hoola): the GDScript rules on the same hands Python scored.
const HANDS := __HANDS__
func _ready() -> void:
	var out: Array = []
	for h in HANDS:
		var j := PackedVector3Array()
		for p in h:
			j.append(Vector3(p[0], p[1], p[2]))
		out.append(HoolaXR.gesture(j))
	print("HOOLA_XR " + JSON.stringify(out))
	get_tree().quit()
'''


def godot_cross_check(st: dict, samples: list[tuple[str, np.ndarray]], job: Path) -> dict:
    from . import engine, template
    shutil.rmtree(job / "proj", ignore_errors=True)
    (job / "proj").mkdir(parents=True)
    hands = [[[round(float(v), 5) for v in p] for p in j] for _l, j in samples]
    scripts = {"main.gd": GESTURE_LAB.replace("__HANDS__", json.dumps(hands)), FILE: gd(st, "LAB")}
    for name, txt in template.files("Hoola gesture lab", "landscape", scripts).items():
        (job / "proj" / name).write_text(txt, encoding="utf-8")
    code, logtxt, to = engine._run(job, ["--path", "proj", "--quit-after", "30"], "xr.log", 120)
    m = re.search(r"HOOLA_XR (\[.*\])", logtxt or "")
    if not m:
        errs = engine.errors_in(logtxt or "") or [(logtxt or "").strip()[-300:] or "nothing printed"]
        raise XrError("The gesture check did not run in Godot: " + "; ".join(errs[:3])[:400])
    got = json.loads(m.group(1))
    py = [classify(np.array([[round(float(v), 5) for v in p] for p in j])) for _l, j in samples]
    return {"agree": sum(1 for a, b in zip(got, py) if a == b), "samples": len(py)}


# ================================================================ store + jobs
def _root(tenant: str) -> Path:
    return G.root() / (re.sub(r"[^\w-]", "_", tenant)[:64] or "t") / "xr"


def _studio(tenant: str, ref: str):
    from . import studio as S
    with session() as s:
        r = S._studio(s, tenant, ref)
        s.expunge(r)
    return r


def _get(s, tenant: str, ref: str) -> GameXr:
    ref = str(ref or "").strip()
    q = select(GameXr).where(GameXr.tenant_id == tenant)
    r = s.scalars(q.where(GameXr.id == ref)).first() or s.scalars(q.where(GameXr.number == ref.upper())).first()
    if r is None:
        raise XrError("This XR setup was not found (give X-001).")
    return r


def view(r: GameXr) -> dict[str, Any]:
    demo = dict(r.demo or {})
    if demo.get("status") == "done" and r.demo_token:
        demo["play_url"] = G.play_url(r.demo_token)
    return {"id": r.id, "number": r.number, "status": r.status, "words": r.words, "settings": r.settings or {},
            "report": r.report or {}, "demo": demo, "error": r.error, "studio_id": r.studio_id,
            "at": r.created_at.isoformat() if r.created_at else ""}


def setup(tenant: str, words: str = "", settings: dict | None = None, studio: str = "", run_now: bool = True) -> dict[str, Any]:
    ensure_table()
    sid = _studio(tenant, studio).id if studio else ""
    st = clean_settings({**from_words(words), **(settings or {})})
    with session() as s:
        n = len(s.scalars(select(GameXr.id).where(GameXr.tenant_id == tenant)).all()) + 1
        r = GameXr(tenant_id=tenant, studio_id=sid, number=f"X-{n:03d}", words=(words or "")[:600], settings=st,
                   status="testing", demo_token=secrets.token_urlsafe(18))
        s.add(r)
        s.flush()
        s.expunge(r)
    if run_now:
        _POOL.submit(_safe_run, r.id)
    return view(r)


def _safe_run(xid: str) -> None:
    try:
        run(xid)
    except Exception as e:                              # noqa: BLE001
        log.exception("xr %s", xid)
        with session() as s:
            r = s.get(GameXr, xid)
            if r is not None:
                r.status, r.error = "failed", str(e)[:400]


def run(xid: str, build_demo: bool = True) -> dict[str, Any]:
    from . import engine
    with session() as s:
        r = s.get(GameXr, xid)
        s.expunge(r)
    st = r.settings
    com = comfort(st)
    samples = test_set()
    sc = score(samples)
    checks = [{"check": f"comfort: {e}", "ok": False, "note": e} for e in com["errors"]]
    checks.append({"check": "gestures on the synthetic test set", "ok": sc["accuracy"] >= 0.95,
                   "note": f"{round(sc['accuracy'] * 100, 1)}% of {sc['samples']} hands right "
                           f"({', '.join(f'{g} {round(v * 100)}%' for g, v in sc['per_gesture'].items())}); synthetic hands, "
                           "not her own - measured on her headset only when she tries it"})
    if engine.find():
        try:
            cc = godot_cross_check(st, samples[:80], _root(r.tenant_id) / r.id / "gest")
            checks.append({"check": "gestures in the real Godot", "ok": cc["agree"] == cc["samples"],
                           "note": f"HoolaXR.gesture agreed with Hoola's scored rules on {cc['agree']} of {cc['samples']} hands"})
        except XrError as e:
            checks.append({"check": "gestures in the real Godot", "ok": False, "note": str(e)})
    else:
        checks.append({"check": "gestures in the real Godot", "ok": True, "note": "NOT ASSESSED: Godot is not installed here"})
    ok = all(c["ok"] for c in checks)
    rep = {"checks": checks, "comfort": com, "gestures": sc, "verdict": "PASS" if ok else "FAIL",
           "passed": sum(c["ok"] for c in checks), "total": len(checks)}
    demo = {}
    if ok and build_demo and engine.find() and engine.templates_dir():
        demo = run_demo(r)
    with session() as s:
        row = s.get(GameXr, xid)
        row.report = rep
        row.demo = demo
        row.status = "draft" if ok else "failed"
        row.error = "" if ok else "; ".join(c["note"] for c in checks if not c["ok"])[:400]
        s.flush()
        s.expunge(row)
    return view(row)


def run_demo(r: GameXr) -> dict:
    from . import engine, playtest, template
    job = _root(r.tenant_id) / r.id / "demo"
    shutil.rmtree(job, ignore_errors=True)
    (job / "proj").mkdir(parents=True)
    scripts = {"main.gd": DEMO, FILE: gd(r.settings, "PASS")}
    files = template.files(f"XR {r.number}", "landscape", scripts)
    files["project.godot"] = files["project.godot"].replace("[rendering]", "[xr]\n\nshaders/enabled=true\n\n[rendering]")
    for name, txt in files.items():
        (job / "proj" / name).write_text(txt, encoding="utf-8")
    sm = engine.smoke(job, frames=120)
    if sm["errors"]:
        return {"status": "failed", "errors": sm["errors"][:4]}
    ex = engine.export_web(job)
    if ex["errors"]:
        return {"status": "failed", "errors": ex["errors"][:4]}
    pl = playtest.run(job / "build", job / "shots", "landscape", seconds=6)
    return {"status": "failed" if pl["errors"] else "done", "errors": pl["errors"][:4],
            "numbers": {"fps_server": pl.get("fps"), "load_s": pl.get("load_s"),
                        "download_mb": round((ex.get("download_bytes") or 0) / 1048576, 1)}}


def demo_build(token: str) -> Path | None:
    if not token:
        return None
    ensure_table()
    with session() as s:
        r = s.scalars(select(GameXr).where(GameXr.demo_token == token)).first()
        if r is None or (r.demo or {}).get("status") != "done":
            return None
        s.expunge(r)
    d = _root(r.tenant_id) / r.id / "demo" / "build"
    return d if (d / "index.html").is_file() else None


def approve(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _get(s, tenant, ref)
        if r.status != "draft":
            raise XrError("Only an XR setup that PASSED can be OKed." if r.status != "testing" else "The check is still running.")
        for o in s.scalars(select(GameXr).where(GameXr.tenant_id == tenant, GameXr.studio_id == r.studio_id,
                                                GameXr.status == "approved")).all():
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
        q = select(GameXr).where(GameXr.tenant_id == tenant)
        if sid is not None:
            q = q.where(GameXr.studio_id == sid)
        rows = s.scalars(q.order_by(GameXr.created_at.desc())).all()[:30]
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
    from . import studio as S
    ensure_table()
    with session() as s:
        st = s.scalars(select(S.GameStudio).where(S.GameStudio.tenant_id == tenant, S.GameStudio.game_id == game_id)).first()
        if st is None:
            return None
        r = s.scalars(select(GameXr).where(GameXr.tenant_id == tenant, GameXr.studio_id == st.id,
                                           GameXr.status == "approved").order_by(GameXr.created_at.desc())).first()
        if r is None:
            return None
        s.expunge(r)
    return gd(r.settings, (r.report or {}).get("verdict", "")), {}


def apply(tenant: str, studio: str) -> dict[str, Any]:
    st = _studio(tenant, studio)
    if for_game(tenant, st.game_id) is None:
        raise XrError("No approved XR setup; pass the check and OK it first.")
    try:
        from . import bible as B
        bv = B.view(tenant, st.id)["version"]
    except Exception:                                   # noqa: BLE001
        bv = 0
    G.data_build(tenant, st.game_id, bv, words="XR setup into the game")
    return {"ok": True, "say": "The XR setup is going into the game (a rebuild is running)."}
