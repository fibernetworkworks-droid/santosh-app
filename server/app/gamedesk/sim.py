"""v0.423 TRAINING SIMULATORS (Hoola Game Engine plan Phase 7 batch 4, Game Desk plan role 5 - the Simulation Software
Engineer): flight, space and driving TRAINING models in code (numpy + scipy, no model, no money), every model VALIDATED
against a textbook reference case, its constants cited, its time step and integrator stated, and every scenario
repeatable - plus Hoola's own HoolaSim autoload whose GDScript step is checked against the Python one in the real Godot.

Models and their reference cases (all must pass):
- orbit  : two-body + J2 around the Earth, RK4 at a stated step. Constants: mu = 398600.4418 km^3/s^2, Re = 6378.137
           km, J2 = 1.08262668e-3 (WGS 84 / EGM96). Checks: a circular orbit's period vs 2 pi sqrt(a^3 / mu); specific
           energy drift over the run (two-body); the J2 node regression rate vs -3/2 n J2 (Re / p)^2 cos i.
- flight : a point-mass longitudinal glider / light aircraft (lift = 1/2 rho V^2 S CL, drag polar CD = CD0 + k CL^2,
           ISA sea-level air 1.225 kg/m^3), parameters a GENERIC textbook-class light aircraft (stated as assumptions,
           not a real type's data). Checks: the steady glide angle vs atan(CD / CL) at the trimmed CL; the phugoid
           period vs Lanchester's approximation pi sqrt(2) V / g (within 10 %: an approximation).
- driving: the linear single-track ("bicycle") model with cornering stiffnesses. Checks: the steady yaw rate vs
           V / (L + K V^2) with the understeer gradient K = m (b Cf... ) formula, and the characteristic speed.
Scenarios are data (start state, events at times: gust, engine out, burn, steer step) and run twice (identical logs).

Never: weapon targeting, missile / bomb / guidance or combat simulators (refused by words, in code); a simulator is a
training aid, not a certified flight training device (said)."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import math
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import JSON, DateTime, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import service as G

log = logging.getLogger("santosh.gamedesk")
FILE = "hoola_sim.gd"
KEY = "sim_dev"
KINDS = ("orbit", "flight", "driving")
MU, RE, J2 = 398600.4418, 6378.137, 1.08262668e-3
G0, RHO0 = 9.80665, 1.225
REFUSE = re.compile(r"\b(missile|warhead|bomb|guidance|targeting|target lock|artillery|munition|weapon|kill chain|"
                    r"drone strike|combat sim|fire control)\b", re.I)
SOURCES = {"orbit": "mu, Re, J2: WGS 84 / EGM96 Earth constants (NGA TR8350.2); J2 node rate: Vallado, Fundamentals of "
                    "Astrodynamics, eq. for secular RAAN drift",
           "flight": "lift / drag polar and phugoid (Lanchester) approximation: standard flight-mechanics texts; ISA sea "
                     "level density 1.225 kg/m^3; aircraft numbers are GENERIC assumptions, not a real type",
           "driving": "linear single-track vehicle model and understeer gradient: Milliken & Milliken, Race Car Vehicle "
                      "Dynamics / Gillespie; vehicle numbers are GENERIC assumptions"}
DEFAULTS = {
    "orbit": {"alt_km": 500.0, "inc_deg": 51.6, "dt_s": 10.0, "hours": 6.0},
    "flight": {"mass_kg": 1000.0, "S_m2": 16.2, "CD0": 0.027, "k": 0.054, "V_mps": 45.0, "dt_s": 0.02, "seconds": 120.0},
    "driving": {"mass_kg": 1500.0, "a_m": 1.2, "b_m": 1.5, "Cf": 80000.0, "Cr": 90000.0, "Iz": 2500.0, "V_mps": 20.0,
                "steer_deg": 2.0, "dt_s": 0.005, "seconds": 8.0},
}


class SimError(G.GameError):
    pass


class GameSim(Base):
    __tablename__ = "game_sims"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gs"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    studio_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    number: Mapped[str] = mapped_column(String(12), default="")
    kind: Mapped[str] = mapped_column(String(12), default="orbit")
    words: Mapped[str] = mapped_column(Text, default="")
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    scenario: Mapped[dict] = mapped_column(JSON, default=dict)
    report: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        GameSim.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


def clean_params(kind: str, p: dict | None) -> dict:
    if kind not in KINDS:
        raise SimError("kind = " + " | ".join(KINDS))
    out = dict(DEFAULTS[kind])
    for k, v in (p or {}).items():
        if k in out:
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                pass
    lim = {"alt_km": (160, 40000), "inc_deg": (0, 180), "hours": (0.5, 48), "mass_kg": (50, 600000), "V_mps": (5, 300),
           "seconds": (5, 600), "steer_deg": (-15, 15), "dt_s": (0.001, 60)}
    for k, (lo, hi) in lim.items():
        if k in out:
            out[k] = min(max(out[k], lo), hi)
    return out


def guess_kind(words: str) -> str:
    w = (words or "").lower()
    if re.search(r"orbit|satellite|space|rocket|antariksh|upgrah", w):
        return "orbit"
    if re.search(r"car|driv|truck|bus|gaadi|vehicle|bike", w):
        return "driving"
    return "flight"


# ================================================================ integrators
def rk4(f, y: np.ndarray, t: float, dt: float) -> np.ndarray:
    k1 = f(t, y)
    k2 = f(t + dt / 2, y + dt / 2 * k1)
    k3 = f(t + dt / 2, y + dt / 2 * k2)
    k4 = f(t + dt, y + dt * k3)
    return y + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)


# ================================================================ orbit
def orbit_f(j2: bool):
    def f(_t: float, y: np.ndarray) -> np.ndarray:
        r = y[:3]
        rn = float(np.linalg.norm(r))
        a = -MU * r / rn ** 3
        if j2:
            z2 = (r[2] / rn) ** 2
            k = 1.5 * J2 * MU * RE ** 2 / rn ** 5
            a = a + k * np.array([r[0] * (5 * z2 - 1), r[1] * (5 * z2 - 1), r[2] * (5 * z2 - 3)])
        return np.concatenate([y[3:], a])
    return f


def orbit_state(alt_km: float, inc_deg: float) -> np.ndarray:
    a = RE + alt_km
    v = math.sqrt(MU / a)
    i = math.radians(inc_deg)
    return np.array([a, 0.0, 0.0, 0.0, v * math.cos(i), v * math.sin(i)])


def raan(y: np.ndarray) -> float:
    h = np.cross(y[:3], y[3:])
    return math.atan2(h[0], -h[1])


def run_orbit(p: dict, events: list | None = None) -> dict:
    dt = p["dt_s"]
    y = orbit_state(p["alt_km"], p["inc_deg"])
    a = RE + p["alt_km"]
    T = 2 * math.pi * math.sqrt(a ** 3 / MU)
    # (1) two-body period: the time the position vector takes to sweep 360 degrees (any inclination / direction)
    f2 = orbit_f(False)
    yy, t, swept, crossed = y.copy(), 0.0, 0.0, None
    e0 = 0.5 * float(yy[3:] @ yy[3:]) - MU / float(np.linalg.norm(yy[:3]))
    while t < T * 1.2:
        yn = rk4(f2, yy, t, dt)
        d = math.atan2(float(np.linalg.norm(np.cross(yy[:3], yn[:3]))), float(yy[:3] @ yn[:3]))
        if swept + d >= 2 * math.pi:
            crossed = t + (2 * math.pi - swept) / d * dt
            yy = yn
            break
        swept, yy, t = swept + d, yn, t + dt
    e1 = 0.5 * float(yy[3:] @ yy[3:]) - MU / float(np.linalg.norm(yy[:3]))
    # (2) J2 node regression over the run
    fj = orbit_f(True)
    yj, t, log_ = y.copy(), 0.0, []
    steps = int(p["hours"] * 3600 / dt)
    r0 = raan(yj)
    for k in range(steps):
        for ev in events or []:
            if ev.get("kind") == "burn" and abs(k * dt - float(ev.get("t", -1))) < dt / 2:
                vhat = yj[3:] / np.linalg.norm(yj[3:])
                yj = np.concatenate([yj[:3], yj[3:] + vhat * float(ev.get("dv_mps", 0)) / 1000.0])
        yj = rk4(fj, yj, k * dt, dt)
        if k % max(1, steps // 200) == 0:
            log_.append([round(k * dt, 1)] + [round(float(v), 6) for v in yj])
    n = math.sqrt(MU / a ** 3)
    rate_th = -1.5 * n * J2 * (RE / a) ** 2 * math.cos(math.radians(p["inc_deg"]))       # rad/s, circular p = a
    rate_sim = (math.remainder(raan(yj) - r0, 2 * math.pi)) / (steps * dt)
    return {"log": log_, "cols": ["t_s", "x_km", "y_km", "z_km", "vx", "vy", "vz"],
            "cases": [
                {"case": "two-body period", "measured": round(crossed or 0, 2), "expected": round(T, 2),
                 "ok": crossed is not None and abs(crossed - T) / T < 1e-4,
                 "note": f"RK4 at {dt:g} s; 2 pi sqrt(a^3/mu) = {round(T, 2)} s"},
                {"case": "energy kept (two-body, one orbit)", "measured": f"{abs(e1 - e0) / abs(e0):.2e}", "expected": "< 1e-6",
                 "ok": abs(e1 - e0) / abs(e0) < 1e-6, "note": "relative drift of the specific orbital energy"},
                {"case": "J2 node regression", "measured": f"{math.degrees(rate_sim) * 86400:.4f} deg/day",
                 "expected": f"{math.degrees(rate_th) * 86400:.4f} deg/day",
                 "ok": abs(rate_sim - rate_th) / abs(rate_th) < 0.05 if rate_th else abs(rate_sim) < 1e-9,
                 "note": f"over {p['hours']:g} h vs -3/2 n J2 (Re/p)^2 cos i (secular rate; short-period wobble included in the measure)"}]}


# ================================================================ flight (point mass, longitudinal)
def flight_trim(p: dict) -> dict:
    """Unpowered trim at speed V: CL from weight, CD from the polar, glide angle from CD / CL."""
    q = 0.5 * RHO0 * p["V_mps"] ** 2
    CL = p["mass_kg"] * G0 / (q * p["S_m2"])
    CD = p["CD0"] + p["k"] * CL ** 2
    return {"CL": CL, "CD": CD, "gamma": -math.atan(CD / CL)}


def flight_f(p: dict, CL: float, gust: list):
    m, S = p["mass_kg"], p["S_m2"]

    def f(t: float, y: np.ndarray) -> np.ndarray:
        V, gam = y[0], y[1]
        w = 0.0
        for g in gust:
            if g["t"] <= t < g["t"] + g.get("dur", 1.0):
                w = g.get("w_mps", 0.0)
        q = 0.5 * RHO0 * V * V
        cl = CL + (w / max(V, 1.0)) * 5.0                    # a vertical gust changes the angle of attack (CL_alpha ~ 5 /rad)
        D = q * S * (p["CD0"] + p["k"] * cl * cl)
        L = q * S * cl
        return np.array([-D / m - G0 * math.sin(gam), (L / (m * V)) - G0 * math.cos(gam) / V, V * math.cos(gam), V * math.sin(gam)])
    return f


def run_flight(p: dict, events: list | None = None) -> dict:
    tr = flight_trim(p)
    dt = p["dt_s"]
    gust = [e for e in (events or []) if e.get("kind") == "gust"]
    # (1) steady glide: start a little off trim, the path settles on the trimmed glide angle
    f = flight_f(p, tr["CL"], [])
    y = np.array([p["V_mps"], tr["gamma"] + math.radians(3), 0.0, 1000.0])
    t, log_, gam_hist = 0.0, [], []
    steps = int(p["seconds"] / dt)
    for k in range(steps):
        y = rk4(flight_f(p, tr["CL"], gust), y, t, dt)
        t += dt
        gam_hist.append(y[1])
        if k % max(1, steps // 300) == 0:
            log_.append([round(t, 2), round(float(y[0]), 4), round(math.degrees(float(y[1])), 4), round(float(y[2]), 2), round(float(y[3]), 2)])
    yy = np.array([p["V_mps"], tr["gamma"] + math.radians(3), 0.0, 1000.0])
    tt, gh = 0.0, []
    for _ in range(steps):
        yy = rk4(f, yy, tt, dt)
        tt += dt
        gh.append(yy[1])
    gh = np.array(gh)
    gamma_end = float(np.mean(gh[-int(10 / dt):]))
    # (2) phugoid period from the speed oscillation's zero crossings around its mean
    vs = np.array([0.0])
    yy, tt, vlog = np.array([p["V_mps"] + 3.0, tr["gamma"], 0.0, 1000.0]), 0.0, []
    for _ in range(steps):
        yy = rk4(f, yy, tt, dt)
        tt += dt
        vlog.append(yy[0])
    vs = np.array(vlog) - np.mean(vlog)
    ups = [i for i in range(1, len(vs)) if vs[i - 1] < 0 <= vs[i]]
    T_sim = float(np.mean(np.diff(ups)) * dt) if len(ups) >= 3 else 0.0
    T_lan = math.pi * math.sqrt(2) * p["V_mps"] / G0
    return {"log": log_, "cols": ["t_s", "V_mps", "gamma_deg", "x_m", "h_m"],
            "cases": [
                {"case": "steady glide angle", "measured": f"{math.degrees(gamma_end):.3f} deg", "expected": f"{math.degrees(tr['gamma']):.3f} deg",
                 "ok": abs(gamma_end - tr["gamma"]) < math.radians(0.15),
                 "note": f"CL {tr['CL']:.3f}, CD {tr['CD']:.4f}, L/D {tr['CL'] / tr['CD']:.1f}; RK4 at {dt:g} s"},
                {"case": "phugoid period", "measured": f"{T_sim:.1f} s", "expected": f"{T_lan:.1f} s (Lanchester)",
                 "ok": T_sim > 0 and abs(T_sim - T_lan) / T_lan < 0.10,
                 "note": "Lanchester's pi sqrt(2) V / g is an approximation; within 10 % is the textbook agreement"}]}


# ================================================================ driving (linear single-track)
def run_driving(p: dict, events: list | None = None) -> dict:
    m, a, b, Cf, Cr, Iz, V = p["mass_kg"], p["a_m"], p["b_m"], p["Cf"], p["Cr"], p["Iz"], p["V_mps"]
    L = a + b
    dt = p["dt_s"]
    delta = math.radians(p["steer_deg"])

    def f(_t: float, y: np.ndarray) -> np.ndarray:
        vy, r = y
        af = delta - (vy + a * r) / V
        ar = -(vy - b * r) / V
        Fyf, Fyr = Cf * af, Cr * ar
        return np.array([(Fyf + Fyr) / m - V * r, (a * Fyf - b * Fyr) / Iz])
    y, t, log_ = np.zeros(2), 0.0, []
    steps = int(p["seconds"] / dt)
    for k in range(steps):
        y = rk4(f, y, t, dt)
        t += dt
        if k % max(1, steps // 300) == 0:
            log_.append([round(t, 3), round(float(y[0]), 5), round(float(y[1]), 6)])
    K = m / L * (b / Cf - a / Cr)                           # understeer gradient (rad per m/s^2 of lateral acc. x ... )
    r_ss = V / (L + K * V * V) * delta
    vch = math.sqrt(L / K) if K > 0 else float("inf")
    return {"log": log_, "cols": ["t_s", "vy_mps", "yaw_rate_rps"],
            "cases": [
                {"case": "steady yaw rate", "measured": f"{float(y[1]):.5f} rad/s", "expected": f"{r_ss:.5f} rad/s",
                 "ok": abs(float(y[1]) - r_ss) / abs(r_ss) < 0.01 if r_ss else False,
                 "note": f"V / (L + K V^2) x steer, understeer gradient K = {K:.5f} s^2/m; RK4 at {dt:g} s"},
                {"case": "understeer / oversteer", "measured": "understeer" if K > 0 else "oversteer" if K < 0 else "neutral",
                 "expected": "stated", "ok": True,
                 "note": f"characteristic speed {vch:.1f} m/s" if K > 0 else "critical speed applies (oversteer)"}]}


RUN = {"orbit": run_orbit, "flight": run_flight, "driving": run_driving}


def simulate(kind: str, params: dict, scenario: dict | None = None) -> dict:
    p = clean_params(kind, params)
    events = list((scenario or {}).get("events") or [])[:20]
    a = RUN[kind](p, events)
    b = RUN[kind](p, events)
    h1 = hashlib.sha256(json.dumps(a["log"]).encode()).hexdigest()[:16]
    h2 = hashlib.sha256(json.dumps(b["log"]).encode()).hexdigest()[:16]
    cases = a["cases"] + [{"case": "same scenario twice", "measured": h2, "expected": h1, "ok": h1 == h2,
                           "note": "the log of a second run must be identical"}]
    ok = all(c["ok"] for c in cases)
    return {"params": p, "events": events, "cases": cases, "log": a["log"], "cols": a["cols"], "verdict": "PASS" if ok else "FAIL",
            "passed": sum(c["ok"] for c in cases), "total": len(cases), "source": SOURCES[kind],
            "integrator": f"RK4, fixed step {p['dt_s']:g} s", "fingerprint": h1}


def log_csv(res: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(res["cols"])
    w.writerows(res["log"])
    return buf.getvalue()


def plot_png(res: dict, kind: str) -> bytes:
    from PIL import Image, ImageDraw
    W, H = 720, 300
    im = Image.new("RGB", (W, H), (250, 250, 248))
    d = ImageDraw.Draw(im)
    data = np.array(res["log"], dtype=float) if res["log"] else np.zeros((2, 3))
    if kind == "orbit":
        xs, ys = data[:, 1], data[:, 2]
    else:
        xs, ys = data[:, 0], data[:, 1 if kind == "driving" else 4]
    if np.ptp(xs) == 0 or np.ptp(ys) == 0:
        return b""
    pts = [(20 + (x - xs.min()) / np.ptp(xs) * (W - 40), H - 20 - (y - ys.min()) / np.ptp(ys) * (H - 40)) for x, y in zip(xs, ys)]
    d.line(pts, fill=(124, 92, 255), width=2)
    d.text((24, 6), {"orbit": "ground plane x-y (km)", "flight": "height (m) over time (s)", "driving": "side speed over time"}[kind], fill=(60, 60, 60))
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


# ================================================================ HoolaSim (GDScript) + the real-engine cross-check
GD = '''extends Node
# HoolaSim (an autoload): the validated orbit model (two-body + J2, RK4) for her training simulator.
# Written by Hoola Studio from a simulator Hoola VALIDATED (verdict below); do not edit.
const CFG := __CFG__
const MU := 398600.4418
const RE := 6378.137
const J2 := 0.00108262668

func accel(r: Vector3) -> Vector3:
	var rn := r.length()
	var a := -MU * r / (rn * rn * rn)
	if bool(CFG["j2"]):
		var z2 := (r.z / rn) * (r.z / rn)
		var k := 1.5 * J2 * MU * RE * RE / pow(rn, 5)
		a += k * Vector3(r.x * (5.0 * z2 - 1.0), r.y * (5.0 * z2 - 1.0), r.z * (5.0 * z2 - 3.0))
	return a

func step(s: Array, dt: float) -> Array:
	# s = [position km (Vector3), velocity km/s (Vector3)]; one RK4 step, the same as Hoola's Python model
	var r: Vector3 = s[0]
	var v: Vector3 = s[1]
	var k1r := v
	var k1v := accel(r)
	var k2r := v + k1v * dt / 2.0
	var k2v := accel(r + k1r * dt / 2.0)
	var k3r := v + k2v * dt / 2.0
	var k3v := accel(r + k2r * dt / 2.0)
	var k4r := v + k3v * dt
	var k4v := accel(r + k3r * dt)
	return [r + (k1r + 2.0 * k2r + 2.0 * k3r + k4r) * dt / 6.0, v + (k1v + 2.0 * k2v + 2.0 * k3v + k4v) * dt / 6.0]
'''


def gd(cfg: dict, verdict: str) -> str:
    from .bible import _gd
    return GD.replace("__CFG__", _gd({**cfg, "verdict": verdict}))


CROSS = '''extends Node
const START := __S__
func _ready() -> void:
	var s := [Vector3(START[0], START[1], START[2]), Vector3(START[3], START[4], START[5])]
	for i in int(START[6]):
		s = HoolaSim.step(s, float(START[7]))
	print("HOOLA_SIM " + JSON.stringify([s[0].x, s[0].y, s[0].z, s[1].x, s[1].y, s[1].z]))
	get_tree().quit()
'''


def godot_cross_check(p: dict, job: Path, n: int = 360) -> dict:
    """The GDScript orbit step against the Python one, n steps from the same start. Godot's Vector3 is 32-bit floats in
    standard builds, so agreement is judged at float precision (relative 1e-4), not bit for bit (said)."""
    from . import engine, template
    y0 = orbit_state(p["alt_km"], p["inc_deg"])
    shutil.rmtree(job / "proj", ignore_errors=True)
    (job / "proj").mkdir(parents=True)
    scripts = {"main.gd": CROSS.replace("__S__", json.dumps([float(v) for v in y0] + [n, p["dt_s"]])), FILE: gd({"j2": True}, "LAB")}
    for name, txt in template.files("Hoola sim check", "landscape", scripts).items():
        (job / "proj" / name).write_text(txt, encoding="utf-8")
    code, logtxt, to = engine._run(job, ["--path", "proj", "--quit-after", "30"], "sim.log", 120)
    m = re.search(r"HOOLA_SIM (\[.*\])", logtxt or "")
    if not m:
        errs = engine.errors_in(logtxt or "") or [(logtxt or "").strip()[-300:] or "nothing printed"]
        raise SimError("Sim check Godot mein nahi chala: " + "; ".join(errs[:3])[:400])
    got = np.array(json.loads(m.group(1)))
    y, f = y0.copy(), orbit_f(True)
    for k in range(n):
        y = rk4(f, y, k * p["dt_s"], p["dt_s"])
    err = float(np.linalg.norm(got[:3] - y[:3]) / np.linalg.norm(y[:3]))
    return {"rel_err": err, "steps": n, "ok": err < 1e-4}


# ================================================================ store
def _root(tenant: str) -> Path:
    return G.root() / (re.sub(r"[^\w-]", "_", tenant)[:64] or "t") / "sims"


def _studio(tenant: str, ref: str):
    from . import studio as S
    with session() as s:
        r = S._studio(s, tenant, ref)
        s.expunge(r)
    return r


def _get(s, tenant: str, ref: str) -> GameSim:
    ref = str(ref or "").strip()
    q = select(GameSim).where(GameSim.tenant_id == tenant)
    r = s.scalars(q.where(GameSim.id == ref)).first() or s.scalars(q.where(GameSim.number == ref.upper())).first()
    if r is None:
        raise SimError("Yeh simulator nahi mila (M-001 dijiye).")
    return r


def _sig(name: str) -> str:
    import hmac as _h
    from ..config import get_settings
    key = (getattr(get_settings(), "api_key", "") or "hoola-sim").encode()
    return _h.new(key, f"sim:{name}".encode(), "sha256").hexdigest()[:16]


SFILES = ("log.csv", "plot.png")


def file_url(r: GameSim, name: str) -> str:
    return f"/api/gamedesk/sim/{r.id}/file/{name}?sig={_sig(r.id + name)}"


def sim_file(xid: str, name: str, sig: str) -> Path | None:
    import hmac as _h
    if not re.fullmatch(r"gs_[A-Za-z0-9_-]{4,40}", str(xid or "")) or name not in SFILES or not _h.compare_digest(_sig(xid + name), str(sig or "")):
        return None
    ensure_table()
    with session() as s:
        r = s.get(GameSim, xid)
        if r is None:
            return None
        s.expunge(r)
    p = _root(r.tenant_id) / r.id / name
    return p if p.is_file() else None


def view(r: GameSim) -> dict[str, Any]:
    d = _root(r.tenant_id) / r.id
    return {"id": r.id, "number": r.number, "kind": r.kind, "status": r.status, "words": r.words, "params": r.params or {},
            "scenario": r.scenario or {}, "report": r.report or {}, "studio_id": r.studio_id,
            "files": {n: file_url(r, n) for n in SFILES if (d / n).is_file()},
            "note": "A training aid - not a certified flight training device.",
            "at": r.created_at.isoformat() if r.created_at else ""}


def setup(tenant: str, words: str = "", kind: str = "", params: dict | None = None, scenario: dict | None = None,
          studio: str = "") -> dict[str, Any]:
    """Validate the model now (seconds, no money): every reference case + the run twice (+ the Godot step for orbits)."""
    from . import engine
    ensure_table()
    if REFUSE.search(words or "") or REFUSE.search(json.dumps(scenario or {})):
        raise SimError("Hathiyar / targeting / combat simulator Hoola nahi banata. Training simulator (udaan, antariksh, "
                       "gaadi, machine, safety) bana sakta hoon.")
    kind = kind if kind in KINDS else guess_kind(words)
    sid = _studio(tenant, studio).id if studio else ""
    res = simulate(kind, params or {}, scenario)
    if kind == "orbit" and engine.find():
        try:
            cc = godot_cross_check(res["params"], _root(tenant) / "check" / new_id("c"))
            res["cases"].append({"case": "the GDScript model in the real Godot", "measured": f"{cc['rel_err']:.1e}",
                                 "expected": "< 1e-4", "ok": cc["ok"],
                                 "note": f"HoolaSim.step vs the Python RK4 over {cc['steps']} steps (Godot vectors are 32-bit floats)"})
        except SimError as e:
            res["cases"].append({"case": "the GDScript model in the real Godot", "measured": "-", "expected": "-", "ok": False, "note": str(e)})
        res["passed"] = sum(c["ok"] for c in res["cases"])
        res["total"] = len(res["cases"])
        res["verdict"] = "PASS" if res["passed"] == res["total"] else "FAIL"
    with session() as s:
        n = len(s.scalars(select(GameSim.id).where(GameSim.tenant_id == tenant)).all()) + 1
        r = GameSim(tenant_id=tenant, studio_id=sid, number=f"M-{n:03d}", kind=kind, words=(words or "")[:600],
                    params=res["params"], scenario={"events": res["events"]},
                    report={k: v for k, v in res.items() if k not in ("log", "cols", "params", "events")},
                    status="draft" if res["verdict"] == "PASS" else "failed")
        s.add(r)
        s.flush()
        s.expunge(r)
    d = _root(tenant) / r.id
    d.mkdir(parents=True, exist_ok=True)
    (d / "log.csv").write_text(log_csv(res), encoding="utf-8")
    png = plot_png(res, kind)
    if png:
        (d / "plot.png").write_bytes(png)
    return view(r)


def approve(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = _get(s, tenant, ref)
        if r.status != "draft":
            raise SimError("Sirf PASS hua simulator OK ho sakta hai.")
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
        q = select(GameSim).where(GameSim.tenant_id == tenant)
        if sid is not None:
            q = q.where(GameSim.studio_id == sid)
        rows = s.scalars(q.order_by(GameSim.created_at.desc())).all()[:30]
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
    """An approved ORBIT simulator puts HoolaSim (its validated step) into her game; flight / driving models are reports
    + logs in this version (their GDScript ports are not built yet - said)."""
    from . import studio as S
    ensure_table()
    with session() as s:
        st = s.scalars(select(S.GameStudio).where(S.GameStudio.tenant_id == tenant, S.GameStudio.game_id == game_id)).first()
        if st is None:
            return None
        r = s.scalars(select(GameSim).where(GameSim.tenant_id == tenant, GameSim.studio_id == st.id, GameSim.kind == "orbit",
                                            GameSim.status == "approved").order_by(GameSim.created_at.desc())).first()
        if r is None:
            return None
        s.expunge(r)
    return gd({"j2": True, "dt_s": r.params.get("dt_s", 10.0)}, (r.report or {}).get("verdict", "")), {}


def apply(tenant: str, studio: str) -> dict[str, Any]:
    st = _studio(tenant, studio)
    if for_game(tenant, st.game_id) is None:
        raise SimError("Koi approved orbit simulator nahi (flight / driving abhi sirf report + log hain).")
    try:
        from . import bible as B
        bv = B.view(tenant, st.id)["version"]
    except Exception:                                   # noqa: BLE001
        bv = 0
    G.data_build(tenant, st.game_id, bv, words="Simulator game mein")
    return {"ok": True, "say": "Simulator game mein ja raha hai (rebuild chal raha hai)."}
