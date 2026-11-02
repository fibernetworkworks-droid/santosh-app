"""v0.425 HOOLA DYNAMICS (box side): the mechanism really MOVED in MuJoCo, with its motors' limits.

The package's own MJCF (bodies, inertias, joints, loops as <connect>, gear / belt couplings as joint equalities)
is loaded WITHOUT its meshes (no collisions: the range sweep already checked those), a payload body is added
where she put it, and every driven coordinate follows a smooth move in her time:
  independent joints   0 -> top of the free range -> bottom -> 0 (minimum-jerk quintic pieces)
  continuous / cams    a steady turn at her rpm (cams) or one turn in the time
  cam followers        the cam's own lift curve s(theta(t)) - their force is turned into cam torque by virtual work
A computed-torque controller (MuJoCo's own bias forces + the mass matrix diagonal + PD at 15 Hz) gives the torque
each motor must make; it is CLIPPED to the motor's effort, so a motor that is too weak shows up as saturation and a
tracking error - exactly what would happen on the bench. Reported per motor: peak / RMS torque, peak speed, worst
tracking error, % of the time saturated, energy; and the loops' worst constraint gap. DRAFT: no friction, no
backlash, rigid links."""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from typing import Any

import numpy as np


def _quintic(q0, q1, T, t):
    x = np.clip(t / T, 0.0, 1.0)
    d = q1 - q0
    s = 10 * x ** 3 - 15 * x ** 4 + 6 * x ** 5
    v = (30 * x ** 2 - 60 * x ** 3 + 30 * x ** 4) / T
    a = (60 * x - 180 * x ** 2 + 120 * x ** 3) / T ** 2
    return q0 + d * s, d * v, d * a


def _sim_xml(mjcf: str, payload: dict | None, frames: dict, safe: dict, gravity) -> str:
    root = ET.fromstring(mjcf)
    for tag in ("asset", "actuator"):
        for el in root.findall(tag):
            root.remove(el)
    for parent in root.iter():
        for g in list(parent.findall("geom")):
            parent.remove(g)
    root.find("compiler").set("meshdir", ".")
    opt = root.find("option")
    opt.set("timestep", "0.0002")
    opt.set("gravity", " ".join(f"{x:.6g}" for x in gravity))
    eq = root.find("equality")
    if eq is not None:
        for e in eq:
            e.set("solref", "0.001 1")                       # stiff loops (>= 2 x timestep)
    if payload:
        name = safe.get(payload["part"], payload["part"])
        for b in root.iter("body"):
            if b.get("name") == name:
                pos = (np.asarray(payload["at"], float) - frames[payload["part"]]) / 1000
                pb = ET.SubElement(b, "body", {"name": "payload", "pos": " ".join(f"{x:.6g}" for x in pos)})
                ET.SubElement(pb, "inertial", {"pos": "0 0 0", "mass": f"{float(payload['kg']):.6g}",
                                               "diaginertia": "1e-7 1e-7 1e-7"})
                break
    return ET.tostring(root, encoding="unicode")


def _limit(j: dict) -> float:
    """Her motor's effort clips the torque; with no motor named the sim measures what one would need."""
    return float(j["effort_given"]) if j.get("effort_given") is not None else 1e9


def _full_m(mujoco, model, data, M) -> None:
    """The dense mass matrix - MuJoCo >= 3.3 takes (m, d, dst), older versions (m, dst, d.qM)."""
    try:
        mujoco.mj_fullM(model, data, M)
    except TypeError:
        mujoco.mj_fullM(model, M, data.qM)


def simulate(mjcf: str, mech, ranges: list[dict], robot: dict, frames: dict, safe: dict, cams: dict) -> dict[str, Any]:
    try:
        import mujoco
    except ImportError:
        return {"ok": None, "note": "MuJoCo is not installed on this server (pip install mujoco) - simulation not run"}
    T = float(robot.get("move_time_s") or 2.0)
    payload = None
    if robot.get("payload"):
        pl = robot["payload"]
        payload = {"part": str(pl["part"]), "kg": float(pl["kg"]), "at": pl.get("at")}
        if payload["at"] is None:
            payload["at"] = list(frames.get(payload["part"], np.zeros(3)))
    gravity = robot.get("gravity") or (0, 0, -9.80665)
    xml = _sim_xml(mjcf, payload, frames, safe, gravity)
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    # what drives what
    plans = []                                     # (joint name, kind, ref(t) -> (q, qd, qdd), effort, unit)
    for j in mech.indep:
        rng = next((r for r in ranges if r["joint"] == j["name"]), None)
        cam = next((c for c in cams.values() if c.get("cam_joint") == j["name"]), None)
        if j["kind"] == "continuous" or cam:
            w = (float(cam["rpm"]) if cam else 60.0 / T) * 2 * math.pi / 60

            def ref(t, w=w):
                return w * t, w, 0.0
            plans.append((j["name"], "turn", ref, _limit(j), "N·m", w))
            continue
        lo, hi = rng["free"] if rng else (0.0, 0.0)
        k = math.pi / 180 if j["kind"] != "prismatic" else 0.001
        lo, hi = lo * k * 0.9, hi * k * 0.9

        def ref(t, lo=lo, hi=hi):
            seg = T / 3
            if t < seg:
                return _quintic(0.0, hi, seg, t)
            if t < 2 * seg:
                return _quintic(hi, lo, seg, t - seg)
            return _quintic(lo, 0.0, seg, t - 2 * seg)
        plans.append((j["name"], "move", ref, _limit(j), "N·m" if j["kind"] != "prismatic" else "N", 0.0))
    for f, c in mech.coup.items():                 # cam followers follow the cam's lift curve
        if not c.get("table"):
            continue
        lead = next(p for p in plans if p[0] == c["leader"])
        th_t = np.asarray(c["table"]["theta"])
        s_t = np.asarray(c["table"]["s"])
        ds = np.gradient(s_t, th_t)
        dds = np.gradient(ds, th_t)

        def ref(t, lead=lead, th_t=th_t, s_t=s_t, ds=ds, dds=dds, off=c["offset"]):
            th, w, _ = lead[2](t)
            x = th % (2 * math.pi)
            per = lambda arr: float(np.interp(x, np.append(th_t, 2 * math.pi), np.append(arr, arr[0])))
            return per(s_t) + off, per(ds) * w, per(dds) * w * w
        plans.append((f, "follower", ref, 1e9, "N", 0.0))
    dof = {}
    for name, *_ in plans:
        jid = model.joint(name).id
        dof[name] = (int(model.jnt_qposadr[jid]), int(model.jnt_dofadr[jid]))
    for name, kind, ref, *_r in plans:          # start on the trajectory
        q, qd, _ = ref(0.0)
        data.qpos[dof[name][0]] = q
        data.qvel[dof[name][1]] = qd
    mujoco.mj_forward(model, data)
    M = np.zeros((model.nv, model.nv))
    idx = np.array([dof[p[0]][1] for p in plans], int)
    wn, zeta = 2 * math.pi * 15.0, 1.0
    steps = int(T / model.opt.timestep)
    rec = {p[0]: {"tau": [], "err": [], "qd": [], "sat": 0} for p in plans}
    ts, eq_gap = [], 0.0
    energy = {p[0]: 0.0 for p in plans}
    for k in range(steps):
        t = k * model.opt.timestep
        _full_m(mujoco, model, data, M)
        data.qfrc_applied[:] = 0.0
        acc = np.zeros(model.nv)                   # wanted acceleration of every driven coordinate
        errs = {}
        for name, kind, ref, effort, unit, _w in plans:
            qa, va = dof[name]
            q, qd, qdd = ref(t)
            e, ed = q - data.qpos[qa], qd - data.qvel[va]
            acc[va] = qdd + wn * wn * e + 2 * zeta * wn * ed
            errs[name] = e
        need = data.qfrc_bias[idx] + M[np.ix_(idx, idx)] @ acc[idx]     # full mass block: coupled links stay stable
        for i, (name, kind, ref, effort, unit, _w) in enumerate(plans):
            qa, va = dof[name]
            e = errs[name]
            tau = float(need[i])
            if abs(tau) > effort:
                tau = math.copysign(effort, tau)
                rec[name]["sat"] += 1
            data.qfrc_applied[va] = tau
            energy[name] += abs(tau * data.qvel[va]) * model.opt.timestep
            if k % 20 == 0:
                rec[name]["tau"].append(tau)
                rec[name]["err"].append(e)
                rec[name]["qd"].append(data.qvel[va])
        if k % 20 == 0:
            ts.append(t)
            if model.neq:
                eq_gap = max(eq_gap, float(np.max(np.abs(data.efc_pos[: data.nefc]))) if data.nefc else 0.0)
        mujoco.mj_step(model, data)
        if not np.all(np.isfinite(data.qacc)) or data.warning[mujoco.mjtWarning.mjWARN_BADQACC].number:
            return {"ok": False, "move_time_s": T, "rows": [], "loop_gap_m": None,
                    "note": f"the simulation went unstable at {t:.3f} s - numbers not trusted, motors not sized from it"}
    rows = []
    cam_tau = {}
    for name, kind, ref, effort, unit, _w in plans:
        r = rec[name]
        tau = np.asarray(r["tau"])
        err = np.asarray(r["err"])
        prismatic = unit == "N"
        err_show = float(np.max(np.abs(err))) * (1000 if prismatic else 180 / math.pi)
        row = {"joint": name, "kind": kind, "unit": unit, "peak": round(float(np.max(np.abs(tau))), 4),
               "rms": round(float(np.sqrt(np.mean(tau ** 2))), 4),
               "peak_speed": round(float(np.max(np.abs(r["qd"]))) * (1000 if prismatic else 180 / math.pi), 2),
               "speed_unit": "mm/s" if prismatic else "deg/s", "worst_error": round(err_show, 3),
               "error_unit": "mm" if prismatic else "deg", "saturated_pct": round(100 * r["sat"] / max(steps, 1), 2),
               "energy_J": round(float(energy[name]), 4), "effort": effort if effort < 1e8 else None}
        row["ok"] = row["saturated_pct"] < 2.0 and err_show < (0.5 if prismatic else 1.0)
        rows.append(row)
        if kind == "follower":
            c = mech.coup[name]
            cam_tau[c["leader"]] = cam_tau.get(c["leader"], 0.0)
    # cam torque by virtual work: tau_cam = F_follower * ds/dtheta (+ the cam's own inertia torque)
    for name, kind, ref, effort, unit, _w in plans:
        if kind != "follower":
            continue
        c = mech.coup[name]
        lead = next(p for p in plans if p[0] == c["leader"])
        F = np.asarray(rec[name]["tau"])
        dsdth = []
        for t in ts:
            _q, qd, _a = ref(t)
            dsdth.append(qd / max(lead[5], 1e-9))
        fol = F * np.asarray(dsdth)
        tq = fol + np.asarray(rec[c["leader"]]["tau"])
        row = next(r for r in rows if r["joint"] == c["leader"])
        row["follower_peak"] = round(max(row.get("follower_peak", 0.0), float(np.max(np.abs(fol)))), 5)
        row["cam_peak"] = round(float(np.max(np.abs(tq))), 4)
        row["note"] = "cam torque = follower force x ds/dtheta + the cam's own (its unbalance under gravity, inertia)"
    stride = max(1, len(ts) // 200)
    trace = {"t": [round(x, 4) for x in ts[::stride]],
             "tau": {n: [round(float(x), 5) for x in rec[n]["tau"][::stride]] for n in rec}}
    return {"ok": all(r["ok"] for r in rows), "move_time_s": T, "rows": rows, "loop_gap_m": round(eq_gap, 6),
            "trace": trace, "payload_kg": payload["kg"] if payload else 0.0,
            "note": "MuJoCo, rigid links, no friction / backlash; motors clipped at their effort"}
