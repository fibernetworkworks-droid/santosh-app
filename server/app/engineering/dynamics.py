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
tracking error, % of the time saturated, energy; and the loops' worst constraint gap.
v0.427 FRICTION: every joint with a bearing gets mu x |its real joint load| (MuJoCo's own reaction, radial part) x
the pin radius + her constant friction + damping, against the motion (smoothed through zero speed); the motors pay
for it (feed-forward), and the energy lost is reported. BACKLASH: a gear / belt coupling with play is NOT a rigid
equality in the sim - the follower floats in the gap and is pushed only when a flank touches (mesh stiffness from the
follower's own inertia, a stiff 150 Hz contact): lost motion, flank changes (knocks) and the peak mesh torque come out.
CAM FOLLOWERS: the force the follower needs at every cam angle is handed back for the contact check (spring, Hertz).
DRAFT: rigid links, no flexing gear teeth beyond the mesh spring."""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from typing import Any

import numpy as np

# Friction coefficients (starting points from bearing makers' published figures: SKF deep-groove ball 0.0015,
# cylindrical roller 0.0011-0.002, needle 0.0025; lubricated plain bush ~0.08, dry 0.2; profile rail ~0.003-0.005,
# plain slideway with oil ~0.1-0.15). Her own friction= / damping= add to these.
BEARINGS = {"ball": 0.0015, "roller": 0.002, "needle": 0.0025, "bush": 0.08, "dry": 0.2, "rail": 0.005, "slide": 0.12}


def _quintic(q0, q1, T, t):
    x = np.clip(t / T, 0.0, 1.0)
    d = q1 - q0
    s = 10 * x ** 3 - 15 * x ** 4 + 6 * x ** 5
    v = (30 * x ** 2 - 60 * x ** 3 + 30 * x ** 4) / T
    a = (60 * x - 180 * x ** 2 + 120 * x ** 3) / T ** 2
    return q0 + d * s, d * v, d * a


def _sim_xml(mjcf: str, payload: dict | None, frames: dict, safe: dict, gravity, drop_eq=()) -> str:
    root = ET.fromstring(mjcf)
    for tag in ("asset", "actuator"):
        for el in root.findall(tag):
            root.remove(el)
    for parent in root.iter():
        for g in list(parent.findall("geom")):
            parent.remove(g)
    for jt in root.iter("joint"):                        # friction is applied by hand (load-dependent), never twice
        for a in ("damping", "frictionloss"):
            jt.attrib.pop(a, None)
    root.find("compiler").set("meshdir", ".")
    opt = root.find("option")
    opt.set("timestep", "0.0002")
    opt.set("gravity", " ".join(f"{x:.6g}" for x in gravity))
    eq = root.find("equality")
    if eq is not None:
        for e in list(eq):
            if e.get("name") in drop_eq:
                eq.remove(e)                             # a coupling with backlash is modelled as a gap, not rigid
                continue
            e.set("solref", "0.001 1")                   # stiff loops (>= 2 x timestep)
        if not len(eq):
            root.remove(eq)
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


def friction_of(j: dict) -> dict | None:
    """The joint's friction settings, or None when it has none."""
    mu = BEARINGS.get(str(j.get("bearing") or "").lower(), 0.0)
    if j.get("bearing") and str(j["bearing"]).lower() not in BEARINGS:
        raise ValueError(f"joint {j['name']}: bearing {' / '.join(BEARINGS)}")
    c0, dmp = float(j.get("friction") or 0.0), float(j.get("damping") or 0.0)
    if not (mu or c0 or dmp):
        return None
    pris = j["kind"] == "prismatic"
    r = 0.0 if pris else float(j.get("pin_d") or 10.0) / 2000.0          # pin radius, m
    return {"mu": mu, "r": r, "c0": c0, "damping": dmp, "eps": 0.002 if pris else 0.02, "prismatic": pris}


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
    lash = {f: c for f, c in mech.coup.items() if c.get("backlash") and not c.get("table")}
    xml = _sim_xml(mjcf, payload, frames, safe, gravity, {f"couple_{f}" for f in lash})
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    # what drives what
    plans = []                                     # (joint name, kind, ref(t) -> (q, qd, qdd), effort, unit, w)
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

    def addr(name):
        jid = model.joint(name).id
        return int(model.jnt_qposadr[jid]), int(model.jnt_dofadr[jid]), jid
    dof = {p[0]: addr(p[0]) for p in plans}
    fric = {}                                      # every joint with friction, driven or not
    for name, j in mech.joints.items():
        fr = friction_of(j)
        if fr and j["kind"] != "fixed":
            qa, va, jid = addr(name)
            fr.update({"va": va, "jid": jid, "body": int(model.jnt_bodyid[jid])})
            fric[name] = fr
    for name, kind, ref, *_r in plans:            # start on the trajectory
        q, qd, _ = ref(0.0)
        data.qpos[dof[name][0]] = q
        data.qvel[dof[name][1]] = qd
    lash_state = {}
    for f, c in lash.items():                      # backlash couplings start centred in the gap
        qf, vf, _ = addr(f)
        ql, vl, _ = addr(c["leader"])
        lq = data.qpos[ql]
        data.qpos[qf] = c["ratio"] * lq + c["offset"]
        data.qvel[vf] = c["ratio"] * data.qvel[vl]
        pris = mech.joints[f]["kind"] == "prismatic"
        lash_state[f] = {"qf": qf, "vf": vf, "ql": ql, "vl": vl, "hb": c["backlash"] / 2 * (0.001 if pris else math.pi / 180),
                         "prismatic": pris, "side": 0, "knocks": 0, "gap": 0.0, "peak": 0.0, "c": c}
    mujoco.mj_forward(model, data)
    for f, st in lash_state.items():               # rest on the flank its load presses it against (no fake impact)
        b = float(data.qfrc_bias[st["vf"]])
        if abs(b) > 1e-12:
            data.qpos[st["qf"]] -= math.copysign(st["hb"], b)
            st["side"] = -1 if b > 0 else 1
    mujoco.mj_forward(model, data)
    M = np.zeros((model.nv, model.nv))
    _full_m(mujoco, model, data, M)
    for f, st in lash_state.items():               # a stiff mesh (150 Hz on the follower's own inertia)
        I = max(float(M[st["vf"], st["vf"]]), 1e-9)
        st["k"] = I * (2 * math.pi * 150.0) ** 2
        st["cd"] = 2 * 0.2 * math.sqrt(st["k"] * I)
    idx = np.array([dof[p[0]][1] for p in plans], int)
    wn, zeta = 2 * math.pi * 15.0, 1.0
    steps = int(T / model.opt.timestep)
    dt = model.opt.timestep
    rec = {p[0]: {"tau": [], "err": [], "qd": [], "sat": 0, "th": [], "F": []} for p in plans}
    fric_E = {n: 0.0 for n in fric}
    fric_pk = {n: 0.0 for n in fric}
    ts, eq_gap = [], 0.0
    energy = {p[0]: 0.0 for p in plans}
    cam_of = {f: next((p for p in plans if p[0] == c["leader"]), None) for f, c in mech.coup.items() if c.get("table")}
    for k in range(steps):
        t = k * dt
        _full_m(mujoco, model, data, M)
        if fric:
            mujoco.mj_rnePostConstraint(model, data)
        data.qfrc_applied[:] = 0.0
        ff = np.zeros(model.nv)                    # friction force on each dof this step
        for n, fr in fric.items():
            F = data.cfrc_int[fr["body"], 3:6]
            ax = data.xaxis[fr["jid"]]
            Fr = float(np.linalg.norm(F - np.dot(F, ax) * ax))          # the load across the bearing
            mag = fr["c0"] + fr["mu"] * Fr * (1.0 if fr["prismatic"] else fr["r"])
            v = float(data.qvel[fr["va"]])
            f_ = -mag * math.tanh(v / fr["eps"]) - fr["damping"] * v
            ff[fr["va"]] += f_
            fric_E[n] += abs(f_ * v) * dt
            fric_pk[n] = max(fric_pk[n], abs(f_))
        for f, st in lash_state.items():           # the gap: no force until a flank touches
            c = st["c"]
            g = data.qpos[st["qf"]] - (c["ratio"] * data.qpos[st["ql"]] + c["offset"])
            gd = data.qvel[st["vf"]] - c["ratio"] * data.qvel[st["vl"]]
            hb = st["hb"]
            if abs(g) > hb:
                side = 1 if g > 0 else -1
                pen = g - side * hb
                tf = -st["k"] * pen - st["cd"] * gd
                if tf * side > 0:                  # a flank can only push
                    tf = 0.0
                if side != st["side"] and st["side"] != 0:
                    st["knocks"] += 1
                st["side"] = side
            else:
                tf = 0.0
            ff[st["vf"]] += tf
            ff[st["vl"]] += -c["ratio"] * tf
            st["gap"] = max(st["gap"], abs(g))
            st["peak"] = max(st["peak"], abs(tf))
        acc = np.zeros(model.nv)                   # wanted acceleration of every driven coordinate
        errs = {}
        for name, kind, ref, effort, unit, _w in plans:
            qa, va, _ = dof[name]
            q, qd, qdd = ref(t)
            e, ed = q - data.qpos[qa], qd - data.qvel[va]
            acc[va] = qdd + wn * wn * e + 2 * zeta * wn * ed
            errs[name] = e
        need = data.qfrc_bias[idx] + M[np.ix_(idx, idx)] @ acc[idx] - ff[idx]   # full mass block + pay for friction
        for i, (name, kind, ref, effort, unit, _w) in enumerate(plans):
            qa, va, _ = dof[name]
            e = errs[name]
            tau = float(need[i])
            if abs(tau) > effort:
                tau = math.copysign(effort, tau)
                rec[name]["sat"] += 1
            data.qfrc_applied[va] = tau
            energy[name] += abs(tau * data.qvel[va]) * dt
            if k % 20 == 0:
                rec[name]["tau"].append(tau)
                rec[name]["err"].append(e)
                rec[name]["qd"].append(data.qvel[va])
            if kind == "follower" and cam_of.get(name) and k % 4 == 0:      # the force per cam angle, finely
                rec[name]["th"].append(cam_of[name][2](t)[0] % (2 * math.pi))
                rec[name]["F"].append(tau)
        data.qfrc_applied[:] += ff
        if k % 20 == 0:
            ts.append(t)
            if model.neq:
                eq_gap = max(eq_gap, float(np.max(np.abs(data.efc_pos[: data.nefc]))) if data.nefc else 0.0)
        mujoco.mj_step(model, data)
        if not np.all(np.isfinite(data.qacc)) or data.warning[mujoco.mjtWarning.mjWARN_BADQACC].number:
            return {"ok": False, "move_time_s": T, "rows": [], "loop_gap_m": None,
                    "note": f"the simulation went unstable at {t:.3f} s - numbers not trusted, motors not sized from it"}
    rows = []
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
    # cam torque by virtual work: tau_cam = F_follower * ds/dtheta (+ the cam's own inertia / unbalance torque)
    cam_force = {}
    for name, kind, ref, effort, unit, _w in plans:
        if kind != "follower":
            continue
        c = mech.coup[name]
        lead = next(p for p in plans if p[0] == c["leader"])
        F = np.asarray(rec[name]["tau"])
        dsdth = np.asarray([ref(t)[1] / max(lead[5], 1e-9) for t in ts])
        fol = F * dsdth
        tq = fol + np.asarray(rec[c["leader"]]["tau"])
        row = next(r for r in rows if r["joint"] == c["leader"])
        row["follower_peak"] = round(max(row.get("follower_peak", 0.0), float(np.max(np.abs(fol)))), 5)
        row["cam_peak"] = round(float(np.max(np.abs(tq))), 4)
        row["note"] = "cam torque = follower force x ds/dtheta + the cam's own (its unbalance under gravity, inertia)"
        cam_force[name] = {"theta": [float(x) for x in rec[name]["th"]], "F": [float(x) for x in rec[name]["F"]]}
    motor_E = sum(energy.values())
    friction = [{"joint": n, "peak": round(fric_pk[n], 5), "energy_J": round(fric_E[n], 5),
                 "unit": "N" if fr["prismatic"] else "N·m", "mu": fr["mu"], "bearing": mech.joints[n].get("bearing")}
                for n, fr in fric.items()]
    backlash = []
    for f, st in lash_state.items():
        k_ = 1000 if st["prismatic"] else 180 / math.pi
        backlash.append({"joint": f, "leader": st["c"]["leader"], "play": st["c"]["backlash"],
                         "unit": "mm" if st["prismatic"] else "deg", "lost_motion": round(float(st["gap"]) * k_, 4),
                         "knocks": st["knocks"], "peak_mesh": round(float(st["peak"]), 4),
                         "mesh_unit": "N" if st["prismatic"] else "N·m"})
    stride = max(1, len(ts) // 200)
    trace = {"t": [round(x, 4) for x in ts[::stride]],
             "tau": {n: [round(float(x), 5) for x in rec[n]["tau"][::stride]] for n in rec}}
    out = {"ok": all(r["ok"] for r in rows), "move_time_s": T, "rows": rows, "loop_gap_m": round(eq_gap, 6),
           "trace": trace, "payload_kg": payload["kg"] if payload else 0.0, "cam_force": cam_force,
           "friction": friction, "backlash": backlash,
           "note": "MuJoCo, rigid links; bearing friction and gear backlash where she named them; motors clipped at their effort"}
    if friction:
        lost = sum(fric_E.values())
        out["friction_share_pct"] = round(100 * lost / motor_E, 2) if motor_E > 1e-12 else None
    return out
