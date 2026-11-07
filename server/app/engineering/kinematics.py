"""v0.406 / v0.409 HOOLA MECHANISMS (box side): joints between an assembly's named parts -> the mechanism moves, is
checked, sized and leaves as a robot / simulator description.

- Joints in the WORLD frame of the assembly as modelled (the zero pose): H.joint(name, parent, child, kind=
  'revolute' | 'continuous' | 'prismatic' | 'fixed', origin, axis, limits (deg / mm), effort, velocity, driver).
  The tree joints make a spanning tree from one root; a joint whose child already has a parent (or closure=True)
  CLOSES A LOOP (four-bar, scissor, parallel gripper ...).
- v0.409 LOOPS: for given driver values the passive joints of each loop are solved by least squares on the closure
  joint (its point on both sides + its axis on both sides), walked step by step from the zero pose. Where no solution
  exists the linkage locks (dead point / out of reach) - that is its real range. Four-bar: link lengths, Grashof
  class, transmission angle over the motion.
- v0.409 COUPLINGS: H.couple(follower, leader, ratio, offset) - gears (ratio = -z_leader / z_follower), belts /
  pulleys (+ratio) - the follower moves with the leader everywhere (pose, sweep, torque, URDF / SDF <mimic>, MJCF
  joint equality).
- Mass properties from the B-rep (OCC GProp). v0.409 JOINT TORQUE: holding torque / force for every independent
  joint by virtual work (dV/dq of the gravity + payload potential, loops solved inside), worst case over sampled
  poses, plus I·alpha when she gives an acceleration; an effort she gave is checked, a missing one = need x 1.5.
- Range check: solid overlap sweep with bisection, through the loop solver and the couplings.
- One package: URDF (tree; loops listed, mimic for couplings), SDF (loops as joints, mimic), MJCF for MuJoCo (nested
  bodies, loops as <connect>, couplings as joint equality, motors), SRDF for MoveIt (planning group chain, end
  effector, zero pose, disable_collisions Adjacent / Never / Default / Always from sampled poses) - each parsed back
  and checked; MuJoCo's own compiler loads the MJCF when it is installed.
- Motion frames + exploded pose for the server's GIF / picture."""
from __future__ import annotations

import json
import math
import random
import shutil
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

KINDS = ("revolute", "continuous", "prismatic", "fixed", "slot")
G = 9.80665


class KinError(Exception):
    pass


def _rot(axis, ang) -> np.ndarray:
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    x, y, z = a
    c, s, C = math.cos(ang), math.sin(ang), 1 - math.cos(ang)
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
                     [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])


def _joint_tf(j: dict, q: float) -> np.ndarray:
    """4x4 motion of the child (world frame of the zero pose, mm) for joint value q (rad, or m for prismatic)."""
    T = np.eye(4)
    o = np.asarray(j["origin"], float)
    if j["kind"] in ("revolute", "continuous"):
        R = _rot(j["axis"], q)
        T[:3, :3] = R
        T[:3, 3] = o - R @ o
    elif j["kind"] == "prismatic":
        a = np.asarray(j["axis"], float)
        T[:3, 3] = a / np.linalg.norm(a) * q * 1000.0
    return T


def tree(names: list[str], joints: list[dict]) -> dict[str, Any]:
    """Validate the joint list into a spanning tree + loop-closing joints. Problems are NAMED."""
    probs = []
    jn = [j["name"] for j in joints]
    if len(set(jn)) != len(jn):
        probs.append("two joints share a name")
    parent_of, by_child, closures = {}, {}, []
    for j in joints:
        if j["kind"] not in KINDS:
            probs.append(f"joint {j['name']}: kind {j['kind']} (revolute / continuous / prismatic / fixed)")
        for end in ("parent", "child"):
            if j[end] not in names:
                probs.append(f"joint {j['name']}: {end} '{j[end]}' is not a part of the assembly ({', '.join(names)})")
        ax = np.asarray(j["axis"], float)
        if j["kind"] != "fixed" and np.linalg.norm(ax) < 1e-9:
            probs.append(f"joint {j['name']}: axis is zero")
        if j["kind"] not in ("fixed", "continuous") and j.get("limits") is not None:
            lo, hi = j["limits"]
            if not lo < hi:
                probs.append(f"joint {j['name']}: limits {lo} .. {hi} must go low to high")
        if j.get("closure") or j["child"] in parent_of or j["kind"] == "slot":
            closures.append(j)                                   # a slot is always a loop-closing pin-in-slot
            continue
        parent_of[j["child"]] = j["parent"]
        by_child[j["child"]] = j
    for n in names:
        seen, cur = set(), n
        while cur in parent_of:
            if cur in seen:
                probs.append(f"tree joints loop through {cur}: mark one joint of the loop closure=True")
                break
            seen.add(cur)
            cur = parent_of[cur]
    roots = [n for n in names if n not in parent_of]
    root = roots[0] if roots else names[0]
    loose = roots[1:]
    children: dict[str, list[str]] = {n: [] for n in names}
    for c, p in parent_of.items():
        if p in children:
            children[p].append(c)
    order, stack = [], [root]
    while stack:
        n = stack.pop(0)
        if n in order:
            break
        order.append(n)
        stack += children.get(n, [])
    for c in closures:
        if c["kind"] not in ("revolute", "fixed", "continuous", "slot"):
            probs.append(f"loop joint {c['name']}: only revolute / slot / fixed loop-closing joints are solved")
        if c["kind"] == "slot" and np.linalg.norm(np.asarray(c.get("direction") or (0, 0, 0), float)) < 1e-9:
            probs.append(f"slot {c['name']}: direction (the slot's length) is missing")
    return {"root": root, "loose": loose, "parent_of": parent_of, "children": children, "order": order,
            "by_child": by_child, "closures": closures, "problems": probs}


def _ancestors(t: dict, n: str) -> list[str]:
    out = [n]
    while out[-1] in t["parent_of"]:
        out.append(t["parent_of"][out[-1]])
    return out


def loop_paths(t: dict, c: dict) -> dict[str, Any]:
    ap, ac = _ancestors(t, c["parent"]), _ancestors(t, c["child"])
    lca = next(x for x in ap if x in ac)
    return {"lca": lca, "from_parent": [t["by_child"][x] for x in ap[:ap.index(lca)]],
            "from_child": [t["by_child"][x] for x in ac[:ac.index(lca)]]}


class Mech:
    """Independent joint values -> every joint value (couplings applied, loops solved) -> part motions."""

    def __init__(self, t: dict, joints: list[dict], couplings: list[dict]):
        self.t = t
        self.joints = {j["name"]: j for j in joints}
        self.coup = {c["follower"]: c for c in couplings}
        self.loops = [loop_paths(t, c) | {"closure": c} for c in t["closures"]]
        movable = [t["by_child"][n] for n in t["order"][1:] if t["by_child"][n]["kind"] != "fixed"]
        drivers = {j["name"] for j in movable if j.get("driver")}
        passive: list[str] = []
        for lp in self.loops:
            path = [j for j in lp["from_parent"][::-1] + lp["from_child"][::-1] if j["kind"] != "fixed"]
            if path and not any(j["name"] in drivers for j in path):
                d0 = [j for j in path if j["name"] not in self.coup]
                if d0:
                    drivers.add(d0[0]["name"])                   # the first joint at the ground drives (said)
            passive += [j["name"] for j in path if j["name"] not in drivers and j["name"] not in self.coup
                        and j["name"] not in passive]
        self.passive = passive
        self.indep = [j for j in movable if j["name"] not in passive and j["name"] not in self.coup]
        self.drivers = drivers
        self._warm = {p: 0.0 for p in passive}

    def full(self, q: dict[str, float]) -> dict[str, float]:
        out = dict(q)
        for _ in range(4):
            for f, c in self.coup.items():
                if c.get("table"):                               # a cam: follower lift from the cam's turn
                    th = out.get(c["leader"], 0.0) % (2 * math.pi)
                    tb = c["table"]
                    out[f] = float(np.interp(th, tb["theta"] + [2 * math.pi], tb["s"] + [tb["s"][0]])) + c["offset"]
                else:
                    out[f] = c["ratio"] * out.get(c["leader"], 0.0) + c["offset"]
        return out

    def tf(self, q: dict[str, float]) -> dict[str, np.ndarray]:
        q = self.full(q)
        t = self.t
        out = {t["root"]: np.eye(4)}
        for n in t["order"][1:]:
            j = t["by_child"][n]
            out[n] = out[j["parent"]] @ _joint_tf(j, q.get(j["name"], 0.0))
        for n in t["loose"]:
            out[n] = np.eye(4)
        return out

    def residual(self, q: dict[str, float]) -> np.ndarray:
        W = self.tf(q)
        res = []
        for lp in self.loops:
            c = lp["closure"]
            o = np.append(np.asarray(c["origin"], float), 1.0)
            a = np.asarray(c["axis"], float)
            if c["kind"] == "slot":                              # the pin stays on the slot's line, may turn + slide
                d = W[c["parent"]][:3, :3] @ (np.asarray(c["direction"], float) / np.linalg.norm(c["direction"]))
                r = (W[c["child"]] @ o - W[c["parent"]] @ o)[:3]
                res += list(r - np.dot(r, d) * d)
                res += list(np.cross(W[c["parent"]][:3, :3] @ a, W[c["child"]][:3, :3] @ a) * 100.0)
                continue
            res += list((W[c["parent"]] @ o - W[c["child"]] @ o)[:3])
            if c["kind"] in ("revolute", "continuous"):
                res += list(np.cross(W[c["parent"]][:3, :3] @ a, W[c["child"]][:3, :3] @ a) * 100.0)
            elif c["kind"] == "fixed":
                res += list((W[c["parent"]][:3, :3] - W[c["child"]][:3, :3]).ravel() * 100.0)
        return np.array(res)

    def slot_travel(self, q: dict[str, float]) -> dict[str, float]:
        """How far (mm) each slot's pin sits from where it was drawn, along the slot."""
        out = {}
        W = self.tf(q)
        for lp in self.loops:
            c = lp["closure"]
            if c["kind"] != "slot":
                continue
            o = np.append(np.asarray(c["origin"], float), 1.0)
            d = W[c["parent"]][:3, :3] @ (np.asarray(c["direction"], float) / np.linalg.norm(c["direction"]))
            out[c["name"]] = float(np.dot((W[c["child"]] @ o - W[c["parent"]] @ o)[:3], d))
        return out

    def slots_ok(self, q: dict[str, float]) -> bool:
        for lp in self.loops:
            c = lp["closure"]
            if c["kind"] == "slot" and c.get("travel"):
                lo, hi = c["travel"]
                if not lo - 1e-6 <= self.slot_travel(q).get(c["name"], 0.0) <= hi + 1e-6:
                    return False                                 # the pin has hit the end of the slot
        return True

    def solve(self, q_ind: dict[str, float], size: float) -> tuple[dict[str, float], bool, float]:
        q = dict(q_ind)
        if not self.passive:
            if self.loops:
                err = float(np.linalg.norm(self.residual(q)))
                return self.full(q), err < 1e-4 * max(size, 1.0), err
            return self.full(q), True, 0.0
        from scipy.optimize import least_squares
        x0 = np.array([self._warm.get(p, 0.0) for p in self.passive])

        def f(x):
            qq = dict(q)
            qq.update(dict(zip(self.passive, x)))
            return self.residual(qq)
        r = least_squares(f, x0, xtol=1e-12, ftol=1e-12, gtol=1e-12, max_nfev=300)
        err = float(np.linalg.norm(r.fun))
        q.update(dict(zip(self.passive, r.x)))
        ok = err < 1e-4 * max(size, 1.0) and self.slots_ok(q)
        if ok:
            self._warm = dict(zip(self.passive, r.x))
        return self.full(q), ok, err


def solve_path(mech: Mech, target: dict[str, float], size: float, steps: int = 8):
    """Walk the independent joints from the zero pose to the target in small steps (keeps the loop on its branch)."""
    mech._warm = {p: 0.0 for p in mech.passive}
    if not mech.passive:
        return mech.solve(target, size)
    q, ok, err = {}, True, 0.0
    for k in range(1, steps + 1):
        q, ok, err = mech.solve({n: v * k / steps for n, v in target.items()}, size)
        if not ok:
            return q, False, err
    return q, ok, err


def _move(shape, T):
    import cadquery as cq
    from OCP.gp import gp_Trsf
    tr = gp_Trsf()
    tr.SetValues(*[float(T[i, k]) for i in range(3) for k in range(4)])
    return cq.Shape.cast(shape.moved(cq.Location(tr)).wrapped)


def mass_props(shape, rho_kg_mm3: float) -> dict[str, Any]:
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape.wrapped, g)
    v = g.Mass()
    c = g.CentreOfMass()
    M = g.MatrixOfInertia()
    I = np.array([[M.Value(i, k) for k in range(1, 4)] for i in range(1, 4)]) * rho_kg_mm3 * 1e-6
    return {"volume_mm3": v, "mass_kg": v * rho_kg_mm3, "com_mm": [c.X(), c.Y(), c.Z()], "inertia": I}


def _overlap(a, b) -> float:
    try:
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
        import cadquery as cq
        bb1, bb2 = a.BoundingBox(), b.BoundingBox()
        if (bb1.xmax < bb2.xmin or bb2.xmax < bb1.xmin or bb1.ymax < bb2.ymin or bb2.ymax < bb1.ymin
                or bb1.zmax < bb2.zmin or bb2.zmax < bb1.zmin):
            return 0.0
        op = BRepAlgoAPI_Common(a.wrapped, b.wrapped)
        if not op.IsDone():
            return 0.0
        return float(cq.Shape.cast(op.Shape()).Volume())
    except Exception:
        return 0.0


def _subtree(t: dict, n: str) -> list[str]:
    out, stack = [], [n]
    while stack:
        x = stack.pop()
        out.append(x)
        stack += t["children"].get(x, [])
    return out


def _lim(j) -> tuple[float, float]:
    return j["limits_si"] if j["kind"] != "continuous" else (-math.pi, math.pi)


def _show(j, v):
    return round(math.degrees(v), 2) if j["kind"] != "prismatic" else round(v * 1000, 2)


def sweep(parts: dict[str, Any], mech: Mech, size: float, steps: int = 12) -> list[dict[str, Any]]:
    """Each independent joint swept to each limit: where its loop locks and where solids collide (bisected)."""
    t = mech.t
    out = []
    vols = {n: max(float(s.Volume()), 1e-9) for n, s in parts.items()}
    pair_ok = {(j["parent"], j["child"]) for j in [*t["by_child"].values(), *t["closures"]]}
    pair_ok |= {(b, a) for a, b in pair_ok}
    for j in mech.indep:
        lo, hi = _lim(j)
        moving = set(_subtree(t, j["child"]))
        for lp in mech.loops:
            if any(x["name"] == j["name"] for x in lp["from_parent"] + lp["from_child"]):
                for x in lp["from_parent"] + lp["from_child"]:
                    moving |= set(_subtree(t, x["child"]))
        for f, c in mech.coup.items():
            if c["leader"] == j["name"]:
                moving |= set(_subtree(t, mech.joints[f]["child"]))
        others = [m for m in parts if m not in moving]

        def state(qv):
            qq, ok, _err = solve_path(mech, {j["name"]: qv}, size)
            if not ok:
                return {"q": qv, "lock": True}
            W = mech.tf(qq)
            for a in moving:
                sa = _move(parts[a], W[a])
                for b in others:
                    if (a, b) in pair_ok:
                        continue
                    ov = _overlap(sa, parts[b])
                    if ov > 0.005 * min(vols[a], vols[b]):
                        return {"q": qv, "parts": [a, b], "overlap_mm3": round(ov, 1)}
            return None
        found = {"lo": None, "hi": None}
        for side, end in (("hi", hi), ("lo", lo)):
            if (side == "hi" and end <= 0) or (side == "lo" and end >= 0):
                continue
            prev = 0.0
            for k in range(1, steps + 1):
                qv = end * k / steps
                hit = state(qv)
                if hit:
                    a_, b_ = prev, qv
                    for _ in range(6):
                        m_ = (a_ + b_) / 2
                        h2 = state(m_)
                        if h2:
                            b_, hit = m_, h2
                        else:
                            a_ = m_
                    found[side] = {**hit, "q": b_}
                    break
                prev = qv
        out.append({"joint": j["name"], "kind": j["kind"], "asked": [_show(j, lo), _show(j, hi)],
                    "unit": "deg" if j["kind"] != "prismatic" else "mm",
                    "free": [_show(j, found["lo"]["q"]) if found["lo"] else _show(j, lo),
                             _show(j, found["hi"]["q"]) if found["hi"] else _show(j, hi)],
                    "collides": [{"at": _show(j, h["q"]), "parts": h["parts"], "overlap_mm3": h["overlap_mm3"]}
                                 for h in (found["lo"], found["hi"]) if h and not h.get("lock")],
                    "locks": [_show(j, h["q"]) for h in (found["lo"], found["hi"]) if h and h.get("lock")]})
    return out


# ---------------------------------------------------------------- loads: holding torque by virtual work
def _potential(mech: Mech, q_ind: dict, props: dict, payload: dict | None, size: float, gvec) -> float | None:
    qq, ok, _ = mech.solve(q_ind, size)
    if not ok:
        return None
    W = mech.tf(qq)
    V = 0.0
    for n, p in props.items():
        c = W[n] @ np.append(p["com_mm"], 1.0)
        V -= p["mass_kg"] * float(np.dot(gvec, c[:3])) / 1000.0
    if payload:
        c = W[payload["part"]] @ np.append(payload["at"], 1.0)
        V -= payload["kg"] * float(np.dot(gvec, c[:3])) / 1000.0
    return V


def torques(mech: Mech, props: dict, robot: dict, size: float) -> list[dict[str, Any]]:
    """Worst-case holding torque (N m) / force (N) of each independent joint = |dV/dq| over sampled poses."""
    gvec = np.asarray(robot.get("gravity") or (0, 0, -G), float)
    payload = None
    if robot.get("payload"):
        pl = robot["payload"]
        payload = {"part": str(pl["part"]), "kg": float(pl["kg"]),
                   "at": np.asarray(pl.get("at") or props[str(pl["part"])]["com_mm"], float)}
    ind = mech.indep
    if not ind:
        return []
    import itertools
    if len(ind) <= 3:
        axes = [np.linspace(*_lim(j), 9 if len(ind) == 1 else 7) for j in ind]
        grids = [dict(zip([j["name"] for j in ind], combo)) for combo in itertools.product(*axes)]
    else:
        rnd = random.Random(3)
        grids = [{j["name"]: rnd.uniform(*_lim(j)) for j in ind} for _ in range(250)]
        grids.append({j["name"]: 0.0 for j in ind})
    worst = {j["name"]: (0.0, None) for j in ind}
    h = 1e-4
    for g in grids:
        if mech.passive:
            _q, ok, _e = solve_path(mech, g, size)
            if not ok:
                continue
        for j in ind:
            qa, qb = dict(g), dict(g)
            qa[j["name"]] -= h
            qb[j["name"]] += h
            va = _potential(mech, qa, props, payload, size, gvec)
            vb = _potential(mech, qb, props, payload, size, gvec)
            if va is None or vb is None:
                continue
            tau = abs((vb - va) / (2 * h))
            if tau > worst[j["name"]][0]:
                worst[j["name"]] = (tau, g)
    acc = robot.get("accel_deg_s2")
    out = []
    for j in ind:
        tau, pose = worst[j["name"]]
        dyn = 0.0
        if acc and j["kind"] in ("revolute", "continuous") and not mech.loops:
            W = mech.tf(pose or {})
            o = W[j["parent"]] @ np.append(j["origin"], 1.0)
            a = W[j["parent"]][:3, :3] @ (np.asarray(j["axis"], float) / np.linalg.norm(j["axis"]))
            Ia = 0.0
            for n in _subtree(mech.t, j["child"]):
                p = props[n]
                R = W[n][:3, :3]
                c = (W[n] @ np.append(p["com_mm"], 1.0))[:3]
                r = (c - o[:3]) / 1000.0
                Ia += float(a @ (R @ p["inertia"] @ R.T) @ a) + p["mass_kg"] * float(np.dot(r, r) - np.dot(r, a) ** 2)
            dyn = Ia * math.radians(float(acc))
        need = tau + dyn
        given = j.get("effort_given")
        out.append({"joint": j["name"], "static": round(tau, 4), "dynamic": round(dyn, 4), "need": round(need, 4),
                    "unit": "N·m" if j["kind"] != "prismatic" else "N",
                    "worst_pose": {k: _show(mech.joints[k], v) for k, v in (pose or {}).items()},
                    "given": given, "ok": (given is None) or (given >= need)})
    return out


# ---------------------------------------------------------------- four-bar
def fourbar(mech: Mech, size: float) -> list[dict[str, Any]]:
    out = []
    for lp in mech.loops:
        seq = lp["from_parent"][::-1] + [lp["closure"]] + lp["from_child"]
        if len(seq) != 4 or any(j["kind"] not in ("revolute", "continuous") for j in seq):
            continue
        a0 = np.asarray(seq[0]["axis"], float)
        a0 = a0 / np.linalg.norm(a0)
        if any(abs(abs(np.dot(a0, np.asarray(j["axis"], float) / np.linalg.norm(j["axis"]))) - 1) > 1e-6 for j in seq):
            continue
        P = [np.asarray(j["origin"], float) for j in seq]

        def flat(v):
            return v - np.dot(v, a0) * a0
        L = [float(np.linalg.norm(flat(P[(i + 1) % 4] - P[i]))) for i in range(4)]
        inp, coupler, outp, ground = L[0], L[1], L[2], L[3]
        s, l = min(L), max(L)
        pq = sum(L) - s - l
        if abs(s + l - pq) < 1e-6 * max(L):
            kind = "change point (s + l = p + q)"
        elif s + l < pq:
            i_s = L.index(s)
            kind = ["crank-rocker (the input turns fully)", "double rocker (Grashof)",
                    "rocker-crank (the output turns fully)", "double crank (drag link)"][i_s]
        else:
            kind = "triple rocker (non-Grashof: no link turns fully)"
        drv = next((j for j in seq if j["name"] in mech.drivers), seq[0])
        lo, hi = _lim(drv)
        mus = []
        for k in range(25):
            qv = lo + (hi - lo) * k / 24
            qq, ok, _ = solve_path(mech, {drv["name"]: qv}, size, steps=12)
            if not ok:
                continue
            W = mech.tf(qq)
            pts = [(W[j["parent"]] @ np.append(j["origin"], 1.0))[:3] for j in seq]
            v1, v2 = pts[1] - pts[2], pts[3] - pts[2]
            cosm = float(np.dot(v1, v2) / max(np.linalg.norm(v1) * np.linalg.norm(v2), 1e-12))
            mu = math.degrees(math.acos(max(-1.0, min(1.0, cosm))))
            mus.append(min(mu, 180 - mu))
        out.append({"loop": lp["closure"]["name"], "links_mm": {"input": round(inp, 3), "coupler": round(coupler, 3),
                    "output": round(outp, 3), "ground": round(ground, 3)}, "grashof": kind, "driver": drv["name"],
                    "min_transmission_deg": round(min(mus), 1) if mus else None,
                    "ok": bool(mus) and min(mus) >= 40.0})
    return out


# ---------------------------------------------------------------- exports
def _fmt(v) -> str:
    return " ".join(f"{float(x):.6g}" for x in v)


def _frames(t: dict) -> dict[str, np.ndarray]:
    frame = {t["root"]: np.zeros(3)}
    for n in t["order"][1:]:
        frame[n] = np.asarray(t["by_child"][n]["origin"], float)
    for n in t["loose"]:
        frame[n] = np.zeros(3)
    return frame


def write_all(robot: str, parts: dict[str, Any], mech: Mech, props: dict[str, dict], cm: dict,
              out_dir: Path) -> dict[str, Any]:
    import cadquery as cq
    from xml.sax.saxutils import quoteattr as qa
    t = mech.t
    frame = _frames(t)
    mdir = out_dir / "urdf_meshes"
    mdir.mkdir(parents=True, exist_ok=True)
    safe = {n: "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in n) or "part" for n in parts}
    links = [*t["order"], *t["loose"]]
    for n in links:
        cq.exporters.export(parts[n].translate(cq.Vector(*(-frame[n]))), str(mdir / f"{safe[n]}.stl"),
                            tolerance=0.05, angularTolerance=0.2)
    tree_j = [t["by_child"][n] for n in t["order"][1:]] + [
        {"name": f"fixed_{safe[n]}", "parent": t["root"], "child": n, "kind": "fixed", "origin": (0, 0, 0),
         "axis": (0, 0, 1)} for n in t["loose"]]

    def eff(j):
        return float(j.get("effort") or 1.0)
    # URDF
    U = ['<?xml version="1.0"?>', f'<robot name={qa(robot)}>',
         '  <!-- Made by Hoola CAD Engineer. Units: m, kg, rad. Meshes in mm (scale 0.001). DRAFT. -->']
    if t["closures"]:
        U.append("  <!-- Closed loops / slots (" + ", ".join(c["name"] for c in t["closures"]) + ") cannot be written in URDF "
                 "(a tree); they are in robot.sdf and robot.xml (MJCF). -->")
    for n in links:
        p, f = props[n], frame[n]
        I = p["inertia"]
        U += [f'  <link name={qa(safe[n])}>', '    <inertial>',
              f'      <origin xyz="{_fmt((np.asarray(p["com_mm"]) - f) / 1000)}" rpy="0 0 0"/>',
              f'      <mass value="{p["mass_kg"]:.6g}"/>',
              f'      <inertia ixx="{I[0, 0]:.6g}" ixy="{I[0, 1]:.6g}" ixz="{I[0, 2]:.6g}" iyy="{I[1, 1]:.6g}" '
              f'iyz="{I[1, 2]:.6g}" izz="{I[2, 2]:.6g}"/>', '    </inertial>']
        for tag in ("visual", "collision"):
            U += [f'    <{tag}>', '      <origin xyz="0 0 0" rpy="0 0 0"/>',
                  f'      <geometry><mesh filename="meshes/{safe[n]}.stl" scale="0.001 0.001 0.001"/></geometry>',
                  f'    </{tag}>']
        U.append('  </link>')
    for j in tree_j:
        o = (np.asarray(j["origin"], float) - frame[j["parent"]]) / 1000
        U += [f'  <joint name={qa(j["name"])} type="{j["kind"]}">', f'    <parent link={qa(safe[j["parent"]])}/>',
              f'    <child link={qa(safe[j["child"]])}/>', f'    <origin xyz="{_fmt(o)}" rpy="0 0 0"/>']
        if j["kind"] != "fixed":
            a = np.asarray(j["axis"], float)
            U.append(f'    <axis xyz="{_fmt(a / np.linalg.norm(a))}"/>')
            if j["kind"] in ("revolute", "prismatic"):
                lo, hi = j["limits_si"]
                U.append(f'    <limit lower="{lo:.6g}" upper="{hi:.6g}" effort="{eff(j):.6g}" velocity="{j["velocity"]:.6g}"/>')
            else:
                U.append(f'    <limit effort="{eff(j):.6g}" velocity="{j["velocity"]:.6g}"/>')
            if j.get("friction") or j.get("damping"):
                U.append(f'    <dynamics damping="{float(j.get("damping") or 0):.6g}" friction="{float(j.get("friction") or 0):.6g}"/>')
            c = mech.coup.get(j["name"])
            if c and not c.get("table"):
                U.append(f'    <mimic joint={qa(c["leader"])} multiplier="{c["ratio"]:.6g}" offset="{c["offset"]:.6g}"/>')
            elif c:
                U.append(f'    <!-- driven by the cam on {c["leader"]} (a lift curve, not a ratio): see the cam table -->')
        U.append('  </joint>')
    U.append('</robot>')
    urdf = "\n".join(U) + "\n"
    # SDF
    ver = "1.11" if any(not c.get("table") for c in mech.coup.values()) else "1.9"
    S = ['<?xml version="1.0"?>', f'<sdf version="{ver}">', f'  <model name={qa(robot)}>']
    for n in links:
        p, f = props[n], frame[n]
        I = p["inertia"]
        S += [f'    <link name={qa(safe[n])}>', f'      <pose>{_fmt(f / 1000)} 0 0 0</pose>', '      <inertial>',
              f'        <pose>{_fmt((np.asarray(p["com_mm"]) - f) / 1000)} 0 0 0</pose>',
              f'        <mass>{p["mass_kg"]:.6g}</mass>',
              f'        <inertia><ixx>{I[0, 0]:.6g}</ixx><ixy>{I[0, 1]:.6g}</ixy><ixz>{I[0, 2]:.6g}</ixz>'
              f'<iyy>{I[1, 1]:.6g}</iyy><iyz>{I[1, 2]:.6g}</iyz><izz>{I[2, 2]:.6g}</izz></inertia>', '      </inertial>']
        for tag in ("visual", "collision"):
            S += [f'      <{tag} name="{tag}">', f'        <geometry><mesh><uri>meshes/{safe[n]}.stl</uri>'
                  '<scale>0.001 0.001 0.001</scale></mesh></geometry>', f'      </{tag}>']
        S.append('    </link>')
    S.append(f'    <joint name="world_fixed" type="fixed"><parent>world</parent><child>{safe[t["root"]]}</child></joint>')
    for j in [*tree_j, *[c for c in t["closures"] if c["kind"] != "slot"]]:
        o = (np.asarray(j["origin"], float) - frame[j["child"]]) / 1000           # SDF: pose in the child frame
        S += [f'    <joint name={qa(j["name"])} type="{j["kind"]}">', f'      <parent>{safe[j["parent"]]}</parent>',
              f'      <child>{safe[j["child"]]}</child>', f'      <pose>{_fmt(o)} 0 0 0</pose>']
        if j["kind"] != "fixed":
            a = np.asarray(j["axis"], float)
            S += ['      <axis>', f'        <xyz expressed_in="__model__">{_fmt(a / np.linalg.norm(a))}</xyz>']
            if j["kind"] in ("revolute", "prismatic"):
                lo, hi = j["limits_si"]
                S.append(f'        <limit><lower>{lo:.6g}</lower><upper>{hi:.6g}</upper>'
                         f'<effort>{eff(j):.6g}</effort><velocity>{j.get("velocity", 1.0):.6g}</velocity></limit>')
            c = mech.coup.get(j["name"])
            if c and not c.get("table"):
                S.append(f'        <mimic joint={qa(c["leader"])}><multiplier>{c["ratio"]:.6g}</multiplier>'
                         f'<offset>{c["offset"]:.6g}</offset><reference>0</reference></mimic>')
            if j.get("friction") or j.get("damping"):
                S.append(f'        <dynamics><damping>{float(j.get("damping") or 0):.6g}</damping>'
                         f'<friction>{float(j.get("friction") or 0):.6g}</friction></dynamics>')
            S.append('      </axis>')
        S.append('    </joint>')
    S += ['  </model>', '</sdf>']
    sdf = "\n".join(S) + "\n"
    # MJCF
    M = [f'<mujoco model={qa(robot)}>', '  <compiler angle="radian" meshdir="meshes" inertiafromgeom="false"/>',
         '  <option gravity="0 0 -9.80665"/>', '  <asset>']
    M += [f'    <mesh name={qa("m_" + safe[n])} file="{safe[n]}.stl" scale="0.001 0.001 0.001"/>' for n in links]
    M += ['  </asset>', '  <worldbody>']

    def body(n, parent_frame, depth):
        p, f = props[n], frame[n]
        I = p["inertia"]
        pad = "  " * (depth + 2)
        L = [f'{pad}<body name={qa(safe[n])} pos="{_fmt((f - parent_frame) / 1000)}">']
        j = t["by_child"].get(n)
        if j and j["kind"] != "fixed":
            a = np.asarray(j["axis"], float)
            typ = "slide" if j["kind"] == "prismatic" else "hinge"
            rng = "" if j["kind"] == "continuous" else \
                f' limited="true" range="{j["limits_si"][0]:.6g} {j["limits_si"][1]:.6g}"'
            dyn_ = (f' damping="{float(j["damping"]):.6g}"' if j.get("damping") else "") + \
                (f' frictionloss="{float(j["friction"]):.6g}"' if j.get("friction") else "")
            L.append(f'{pad}  <joint name={qa(j["name"])} type="{typ}" pos="0 0 0" axis="{_fmt(a / np.linalg.norm(a))}"{rng}{dyn_}/>')
        L.append(f'{pad}  <inertial pos="{_fmt((np.asarray(p["com_mm"]) - f) / 1000)}" mass="{max(p["mass_kg"], 1e-9):.6g}" '
                 f'fullinertia="{I[0, 0]:.6g} {I[1, 1]:.6g} {I[2, 2]:.6g} {I[0, 1]:.6g} {I[0, 2]:.6g} {I[1, 2]:.6g}"/>')
        L.append(f'{pad}  <geom type="mesh" mesh={qa("m_" + safe[n])} contype="0" conaffinity="0"/>')
        for c in t["closures"]:                                   # a slot = a tiny slider body on its parent
            if c["kind"] == "slot" and c["parent"] == n:
                dd = np.asarray(c["direction"], float)
                aa = np.asarray(c["axis"], float)
                tr = c.get("travel")
                rng = f' limited="true" range="{tr[0] / 1000:.6g} {tr[1] / 1000:.6g}"' if tr else ""
                L += [f'{pad}  <body name={qa("slot_" + c["name"])} pos="{_fmt((np.asarray(c["origin"], float) - f) / 1000)}">',
                      f'{pad}    <joint name={qa(c["name"] + "_slide")} type="slide" axis="{_fmt(dd / np.linalg.norm(dd))}"{rng}/>',
                      f'{pad}    <joint name={qa(c["name"] + "_turn")} type="hinge" axis="{_fmt(aa / np.linalg.norm(aa))}"/>',
                      f'{pad}    <inertial pos="0 0 0" mass="1e-5" diaginertia="1e-9 1e-9 1e-9"/>', f'{pad}  </body>']
        for ch in t["children"].get(n, []):
            L += body(ch, f, depth + 1)
        L.append(f'{pad}</body>')
        return L
    M += body(t["root"], np.zeros(3), 0)
    for n in t["loose"]:
        M += body(n, np.zeros(3), 0)
    M.append('  </worldbody>')
    eq = []
    for c in t["closures"]:
        if c["kind"] == "slot":
            eq.append(f'    <connect name={qa(c["name"])} body1={qa("slot_" + c["name"])} body2={qa(safe[c["child"]])} '
                      'anchor="0 0 0"/>')
            continue
        anchor = (np.asarray(c["origin"], float) - frame[c["parent"]]) / 1000
        eq.append(f'    <connect name={qa(c["name"])} body1={qa(safe[c["parent"]])} body2={qa(safe[c["child"]])} '
                  f'anchor="{_fmt(anchor)}"/>')
    for f_, c in mech.coup.items():
        if c.get("table"):
            continue                                              # a cam lift curve is not a polynomial
        eq.append(f'    <joint name={qa("couple_" + f_)} joint1={qa(f_)} joint2={qa(c["leader"])} '
                  f'polycoef="{c["offset"]:.6g} {c["ratio"]:.6g} 0 0 0"/>')
    if eq:
        M += ['  <equality>', *eq, '  </equality>']
    if mech.indep:
        M.append('  <actuator>')
        M += [f'    <motor name={qa("motor_" + j["name"])} joint={qa(j["name"])} ctrllimited="true" '
              f'ctrlrange="{-eff(j):.6g} {eff(j):.6g}"/>' for j in mech.indep]
        M.append('  </actuator>')
    M.append('</mujoco>')
    mjcf = "\n".join(M) + "\n"
    srdf = _srdf(robot, safe, mech, cm)
    (out_dir / "robot.urdf").write_text(urdf, encoding="utf-8")
    rows = validate(urdf, sdf, mjcf, srdf, mdir)
    with zipfile.ZipFile(out_dir / "robot_urdf.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in (("robot.urdf", urdf), ("robot.sdf", sdf), ("robot.xml", mjcf), ("robot.srdf", srdf)):
            z.writestr(f"{robot}/{name}", text)
        for f_ in sorted(mdir.glob("*.stl")):
            z.write(f_, f"{robot}/meshes/{f_.name}")
        z.writestr(f"{robot}/README.txt",
                   "Robot package by Hoola CAD Engineer (DRAFT for review).\n"
                   "robot.urdf  ROS / MoveIt (a tree; closed loops are only in the SDF / MJCF)\n"
                   "robot.srdf  MoveIt semantic description (planning group, end effector, collision pairs to skip)\n"
                   "robot.sdf   Gazebo (loops as joints, couplings as mimic)\n"
                   "robot.xml   MuJoCo MJCF (loops as <connect>, couplings as joint equality, one motor per input)\n"
                   "Units m / kg / rad; meshes in mm with scale 0.001. Effort limits = the joint's worst-case holding "
                   "torque x 1.5 unless she gave them.\n")
    (out_dir / "robot_mjcf.xml").write_text(mjcf, encoding="utf-8")
    shutil.rmtree(mdir, ignore_errors=True)
    return {"rows": rows, "links": len(links), "joints": len(tree_j) + len(t["closures"]),
            "formats": ["URDF", "SRDF", "SDF " + ver, "MJCF"]}


def _srdf(robot: str, safe: dict, mech: Mech, cm: dict) -> str:
    from xml.sax.saxutils import quoteattr as qa
    t = mech.t
    best = [t["root"]]
    for n in t["order"]:
        chain = _ancestors(t, n)[::-1]
        if len(chain) > len(best):
            best = chain
    L = ['<?xml version="1.0"?>', f'<robot name={qa(robot)}>']
    tip = best[-2] if len(best) >= 3 else best[-1]
    if len(best) >= 2:
        L += ['  <group name="arm">', f'    <chain base_link={qa(safe[best[0]])} tip_link={qa(safe[tip])}/>', '  </group>']
    if len(best) >= 3:
        L += ['  <group name="end_effector">', f'    <link name={qa(safe[best[-1]])}/>', '  </group>',
              f'  <end_effector name="tool" parent_link={qa(safe[tip])} group="end_effector" parent_group="arm"/>']
    chain_j = [t["by_child"][n] for n in best[1:best.index(tip) + 1]] if len(best) >= 2 else []
    chain_j = [j for j in chain_j if j["kind"] != "fixed"]
    if chain_j:
        L.append('  <group_state name="zero" group="arm">')
        L += [f'    <joint name={qa(j["name"])} value="0"/>' for j in chain_j]
        L.append('  </group_state>')
    for (a, b), why in sorted(cm.get("disable", {}).items()):
        L.append(f'  <disable_collisions link1={qa(safe[a])} link2={qa(safe[b])} reason="{why}"/>')
    for p in mech.passive:
        L.append(f'  <passive_joint name={qa(p)}/>')
    L.append('</robot>')
    return "\n".join(L) + "\n"


def collision_matrix(parts: dict[str, Any], mech: Mech, size: float, n_poses: int = 40) -> dict[str, Any]:
    """MoveIt-style pairs to skip: Adjacent (joined), Default (touching at zero), Always / Never (sampled poses)."""
    t = mech.t
    names = list(parts)
    adj = {tuple(sorted((j["parent"], j["child"]))) for j in [*t["by_child"].values(), *t["closures"]]}
    vols = {n: max(float(s.Volume()), 1e-9) for n, s in parts.items()}

    def hits(W):
        moved = {n: _move(parts[n], W[n]) for n in names}
        out = set()
        for i in range(len(names)):
            for k in range(i + 1, len(names)):
                pr = tuple(sorted((names[i], names[k])))
                if pr in adj:
                    continue
                if _overlap(moved[names[i]], moved[names[k]]) > 0.001 * min(vols[names[i]], vols[names[k]]):
                    out.add(pr)
        return out
    zero = hits(mech.tf({}))
    rnd = random.Random(7)
    counts: dict[tuple, int] = {}
    done = 0
    for _ in range(n_poses if mech.indep else 0):
        q = {j["name"]: rnd.uniform(*_lim(j)) for j in mech.indep}
        qq, ok, _ = solve_path(mech, q, size, steps=6)
        if not ok:
            continue
        done += 1
        for pr in hits(mech.tf(qq)):
            counts[pr] = counts.get(pr, 0) + 1
    disable = {pr: "Adjacent" for pr in adj}
    for i in range(len(names)):
        for k in range(i + 1, len(names)):
            pr = tuple(sorted((names[i], names[k])))
            if pr in disable:
                continue
            c = counts.get(pr, 0)
            if pr in zero and done and c == done:
                disable[pr] = "Always"
            elif pr in zero:
                disable[pr] = "Default"
            elif done and c == 0:
                disable[pr] = "Never"
    return {"disable": disable, "poses": done, "can_collide": sorted([list(p) for p, c in counts.items() if c])}


def validate(urdf: str, sdf: str, mjcf: str, srdf: str, mdir: Path) -> list[dict[str, Any]]:
    """Our own checks on the written files (parsed back), plus MuJoCo's compiler when it is installed."""
    import xml.etree.ElementTree as ET
    rows, parsed = [], {}
    for name, text in (("URDF", urdf), ("SDF", sdf), ("MJCF", mjcf), ("SRDF", srdf)):
        try:
            parsed[name] = ET.fromstring(text)
            rows.append({"check": f"{name} parses as XML", "ok": True, "note": ""})
        except ET.ParseError as e:
            rows.append({"check": f"{name} parses as XML", "ok": False, "note": str(e)})
    root = parsed.get("URDF")
    if root is not None:
        links = [l.get("name") for l in root.findall("link")]
        joints = root.findall("joint")
        children = [j.find("child").get("link") for j in joints]
        roots = [l for l in links if l not in children]
        rows.append({"check": "URDF one root, a tree", "ok": len(roots) == 1 and len(set(children)) == len(children)
                     and len(set(links)) == len(links), "note": f"{len(links)} links, root {roots[0] if roots else '-'}"})
        bad = []
        for l in root.findall("link"):
            m = float(l.find("inertial/mass").get("value"))
            I = l.find("inertial/inertia")
            Mx = np.array([[float(I.get("ixx")), float(I.get("ixy")), float(I.get("ixz"))],
                           [float(I.get("ixy")), float(I.get("iyy")), float(I.get("iyz"))],
                           [float(I.get("ixz")), float(I.get("iyz")), float(I.get("izz"))]])
            ev = np.linalg.eigvalsh(Mx)
            ix, iy, iz = np.diag(Mx)
            tol = 1e-9 * max(abs(ev).max(), 1e-12)
            if m <= 0 or ev.min() < -tol or ix + iy < iz - tol or iy + iz < ix - tol or ix + iz < iy - tol:
                bad.append(l.get("name"))
        rows.append({"check": "Masses + inertias physical", "ok": not bad, "note": ", ".join(bad)})
        lim_bad = [j.get("name") for j in joints if j.find("limit") is not None and j.find("limit").get("lower")
                   and float(j.find("limit").get("lower")) >= float(j.find("limit").get("upper"))]
        rows.append({"check": "Limits low < high", "ok": not lim_bad, "note": ", ".join(lim_bad)})
        sr = parsed.get("SRDF")
        if sr is not None:
            lk = set(links)
            refs = set()
            for e in sr.iter():
                for k in ("link1", "link2", "base_link", "tip_link", "parent_link"):
                    if e.get(k):
                        refs.add(e.get(k))
                if e.tag == "link" and e.get("name"):
                    refs.add(e.get("name"))
            unknown = sorted(r for r in refs if r not in lk)
            rows.append({"check": "SRDF names real links", "ok": not unknown, "note": ", ".join(unknown)})
    sd = parsed.get("SDF")
    if sd is not None:
        lk = {l.get("name") for l in sd.iter("link")} | {"world"}
        bad = [j.get("name") for j in sd.iter("joint")
               if j.find("parent").text not in lk or j.find("child").text not in lk]
        rows.append({"check": "SDF joints name real links", "ok": not bad, "note": ", ".join(bad)})
    try:
        import mujoco
        tmp = mdir / "robot.xml"
        tmp.write_text(mjcf.replace('meshdir="meshes"', f'meshdir="{mdir}"'), encoding="utf-8")
        m = mujoco.MjModel.from_xml_path(str(tmp))
        rows.append({"check": "MuJoCo loads the MJCF", "ok": True,
                     "note": f"{m.nbody - 1} bodies, {m.njnt} joints, {m.neq} equality constraints"})
    except ImportError:
        rows.append({"check": "MuJoCo loads the MJCF", "ok": True, "note": "MuJoCo not installed here (not run)"})
    except Exception as e:
        rows.append({"check": "MuJoCo loads the MJCF", "ok": False, "note": str(e)[:200]})
    return rows


def backlash_play(parts: dict, mech: Mech, robot: dict) -> list[dict[str, Any]]:
    """v0.427 the play each gear / belt backlash leaves at the far end of what it carries (zero pose, worst case):
    angle x the farthest point of the downstream parts from the joint axis; a prismatic follower's play is itself."""
    out = []
    for f, c in mech.coup.items():
        if not c.get("backlash") or c.get("table"):
            continue
        j = mech.joints[f]
        if j["kind"] == "prismatic":
            reach, play = None, float(c["backlash"])
        else:
            o = np.asarray(j["origin"], float)
            a = np.asarray(j["axis"], float)
            a = a / (np.linalg.norm(a) or 1.0)
            reach = 0.0
            for n in _subtree(mech.t, j["child"]):
                bb = parts[n].BoundingBox()
                for x in (bb.xmin, bb.xmax):
                    for y in (bb.ymin, bb.ymax):
                        for z in (bb.zmin, bb.zmax):
                            d = np.array([x, y, z]) - o
                            reach = max(reach, float(np.linalg.norm(d - np.dot(d, a) * a)))
            play = math.radians(float(c["backlash"])) * reach
        out.append({"joint": f, "leader": c["leader"], "backlash": float(c["backlash"]),
                    "unit": "mm" if j["kind"] == "prismatic" else "deg",
                    "reach_mm": round(reach, 2) if reach is not None else None, "tip_play_mm": round(play, 4)})
    acc = robot.get("accuracy_mm")
    tot = sum(r["tip_play_mm"] for r in out)
    for r in out:
        r["total_mm"] = round(tot, 4)
        r["ok"] = acc is None or tot <= float(acc)
        r["accuracy_mm"] = acc
    return out


def cam_contact(mech: Mech, props: dict, robot: dict, dyn: dict | None, material: str) -> dict[str, Any]:
    """v0.427 each cam's contact check: the follower force (from the MuJoCo move when it covered the whole turn,
    else m (s'' w^2 - g.u) for the follower and everything it carries), then the spring, push, Hertz, jam."""
    import cams as _cams
    import fea
    out = {}
    g = np.asarray(robot.get("gravity") or (0, 0, -G), float)
    mats = robot.get("materials") or {}
    for name, cm_ in (robot.get("cams") or {}).items():
        cj, fj = cm_.get("cam_joint"), cm_.get("follower_joint")
        if not cj or not fj or cj not in mech.joints or fj not in mech.joints or not cm_.get("geo"):
            continue
        geo = cm_["geo"]
        jf = mech.joints[fj]
        ax = np.asarray(jf["axis"], float)
        ax = ax / (np.linalg.norm(ax) or 1.0)
        mass = sum(props[n]["mass_kg"] for n in _subtree(mech.t, jf["child"]))
        F = _cams.need_from_motion(geo, mass, float(cm_["rpm"]), float(np.dot(g, ax)))
        src = "motion (m s'' w² - g)"
        sim = ((dyn or {}).get("cam_force") or {}).get(fj)
        if sim and len(sim["theta"]) > 20:
            th = np.asarray(sim["theta"])
            Fs = np.asarray(sim["F"])
            o = np.argsort(th)
            th, Fs = th[o], Fs[o]
            gaps = np.diff(np.append(th, th[0] + 2 * math.pi))
            if float(np.max(gaps)) < math.radians(5):
                F = np.interp(np.asarray(geo["theta"]), th, Fs, period=2 * math.pi)
                src = "the MuJoCo move"
        cpart = mech.joints[cj]["child"]
        _k1, m1 = fea.material(mats.get(cpart) or material)
        ct = cm_.get("contact") or {}
        rmat = ct.get("roller_material") or "steel"
        _k2, m2 = fea.material(rmat)
        res = _cams.contact(geo, F, float(cm_["rpm"]), kind=cm_.get("kind", "roller"),
                            roller_radius=float(cm_.get("roller_radius") or 5.0), width=float(cm_.get("thickness") or 10.0),
                            cam_material=mats.get(cpart) or material, roller_material=rmat,
                            spring_k=ct.get("spring_k"), preload=ct.get("preload"), guide_mu=float(ct.get("guide_mu") or 0.0),
                            guide_len=ct.get("guide_len"), overhang=ct.get("overhang"), allow_mpa=ct.get("allow_mpa"),
                            E=((m1["E"], m1["nu"]), (m2["E"], m2["nu"])))
        res["follower_kg"] = round(mass, 5)
        res["force_from"] = src
        out[name] = res
    return out


# ---------------------------------------------------------------- the whole job
def run(part_list: list[tuple[str, Any]], spec_joints: list[dict], spec_robot: dict, material: str,
        out_dir: Path, couplings: list[dict] | None = None) -> dict[str, Any]:
    import fea
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    parts = {n: s for n, s, *_ in part_list}
    names = list(parts)
    joints = []
    for j in spec_joints:
        kind = str(j.get("kind", "revolute")).lower()
        lim = tuple(float(x) for x in (j.get("limits") or ((-180, 180) if kind != "prismatic" else (0, 100))))
        si = (math.radians(lim[0]), math.radians(lim[1])) if kind in ("revolute", "continuous") else \
            (lim[0] / 1000, lim[1] / 1000)
        joints.append({"name": str(j["name"]), "parent": str(j["parent"]), "child": str(j["child"]), "kind": kind,
                       "origin": [float(x) for x in j.get("origin", (0, 0, 0))],
                       "axis": [float(x) for x in j.get("axis", (0, 0, 1))], "limits": lim, "limits_si": si,
                       "effort_given": float(j["effort"]) if j.get("effort") else None,
                       "effort": float(j.get("effort") or 0.0),
                       "velocity": float(j.get("velocity") or (1.0 if kind != "prismatic" else 0.1)),
                       "driver": bool(j.get("driver")), "closure": bool(j.get("closure")),
                       "direction": [float(x) for x in j["direction"]] if j.get("direction") else None,
                       "travel": [float(x) for x in j["travel"]] if j.get("travel") else None,
                       "bearing": j.get("bearing"), "pin_d": j.get("pin_d"), "friction": j.get("friction"),
                       "damping": j.get("damping"),
                       "assumed": [k for k in ("effort", "velocity") if not j.get(k)]})
    t = tree(names, joints)
    if t["problems"]:
        return {"ok": False, "problems": t["problems"]}
    jn = {j["name"] for j in joints}
    coup = []
    for c in couplings or []:
        if c["follower"] not in jn or c["leader"] not in jn:
            return {"ok": False, "problems": [f"couple: joint '{c['follower']}' / '{c['leader']}' not found"]}
        entry = {"follower": str(c["follower"]), "leader": str(c["leader"]), "ratio": float(c.get("ratio") or 0.0),
                 "offset": float(c.get("offset") or 0.0)}
        if c.get("backlash"):                                    # v0.427 play at the follower (deg / mm)
            entry["backlash"] = float(c["backlash"])
        if c.get("table"):                                       # a cam's lift curve (theta rad -> m)
            entry["table"] = {"theta": list(c["table"]["theta"]), "s": list(c["table"]["s"])}
            entry["cam"] = c.get("cam")
        coup.append(entry)
    off = []                                                     # every pin must sit on both of its parts
    for j in joints:
        if j["kind"] == "fixed":                                 # a fixed joint's origin is only a frame
            continue
        o = np.asarray(j["origin"], float)
        ax = np.asarray(j["axis"], float)
        ax = ax / (np.linalg.norm(ax) or 1.0)
        for end in ("parent", "child"):
            bb = parts[j[end]].BoundingBox()
            m = 2.0 + 0.25 * max(bb.xlen, bb.ylen, bb.zlen)              # near the part, not on its surface
            span = 2 * max(bb.xlen, bb.ylen, bb.zlen) + float(np.linalg.norm(o)) + 10
            line = [o + ax * tv for tv in np.linspace(-span, span, 201)]
            if not any(bb.xmin - m <= p_[0] <= bb.xmax + m and bb.ymin - m <= p_[1] <= bb.ymax + m
                       and bb.zmin - m <= p_[2] <= bb.zmax + m for p_ in line):   # a pin passes through layers
                off.append(f"joint {j['name']}: origin {[round(float(x), 2) for x in o]} is not on part '{j[end]}' "
                           "(the pin must be where the two parts meet in the model as drawn)")
    if off:
        return {"ok": False, "problems": off}
    mech = Mech(t, joints, coup)
    mats = spec_robot.get("materials") or {}
    props = {}
    for n, s in parts.items():
        _mn, mat = fea.material(mats.get(n) or material)
        props[n] = mass_props(s, mat["rho"] * 1000.0)
    size = max(max(s.BoundingBox().xlen, s.BoundingBox().ylen, s.BoundingBox().zlen) for s in parts.values())
    _q0, ok0, err0 = mech.solve({}, size)
    if not ok0:
        return {"ok": False, "problems": [f"the loops do not close at the zero pose (gap {err0:.3g} mm): the "
                                          "loop joint's origin must sit on the joint in the model as drawn"]}
    rng = sweep(parts, mech, size)
    tq = torques(mech, props, spec_robot, size)
    for j in joints:                                             # effort = her number, else the need x 1.5
        row = next((r for r in tq if r["joint"] == j["name"]), None)
        if j["effort_given"] is None:
            need = row["need"] if row else 0.0
            j["effort"] = max(round(need * 1.5, 3), 0.1 if j["kind"] != "prismatic" else 1.0)
    fb = fourbar(mech, size)
    cm = collision_matrix(parts, mech, size)
    robot = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in str(spec_robot.get("name") or "hoola_robot"))
    pkg = write_all(robot, parts, mech, props, cm, out_dir)
    dyn = None
    if spec_robot.get("simulate", True) and mech.indep:          # v0.425 the mechanism really moves (MuJoCo)
        try:
            import dynamics
            rb = dict(spec_robot)
            if rb.get("payload") and not rb["payload"].get("at"):
                rb["payload"] = {**rb["payload"], "at": props[str(rb["payload"]["part"])]["com_mm"]}
            safe = {n: "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in n) or "part" for n in parts}
            dyn = dynamics.simulate((out_dir / "robot_mjcf.xml").read_text(encoding="utf-8"), mech, rng, rb,
                                    _frames(t), safe, spec_robot.get("cams") or {})
            if dyn.get("trace"):
                (out_dir / "dyn.json").write_text(json.dumps(dyn.pop("trace")), encoding="utf-8")
            changed = False                                      # size unnamed motors for the real move, not statics
            for row in dyn.get("rows") or []:
                j = mech.joints.get(row["joint"])
                if j is not None and j.get("effort_given") is None and row["peak"] * 1.25 > j["effort"]:
                    j["effort"] = round(row["peak"] * 1.25, 4)
                    row["sized_to"] = j["effort"]
                    changed = True
            if changed:
                pkg = write_all(robot, parts, mech, props, cm, out_dir)
        except Exception as e:
            dyn = {"ok": False, "note": f"simulation failed: {type(e).__name__}: {str(e)[:200]}"}
    contact = cam_contact(mech, props, spec_robot, dyn, material) if spec_robot.get("cams") else {}
    if dyn:
        dyn.pop("cam_force", None)
    play = backlash_play(parts, mech, spec_robot)
    frames, N = [], 16
    for k in range(N):
        q = {}
        for j in mech.indep:
            r = next((x for x in rng if x["joint"] == j["name"]), None)
            lo, hi = _lim(j)
            if r:
                f0, f1 = r["free"]
                lo, hi = ((math.radians(f0), math.radians(f1)) if j["kind"] != "prismatic" else (f0 / 1000, f1 / 1000))
            q[j["name"]] = (lo + hi) / 2 + (hi - lo) / 2 * 0.95 * math.sin(2 * math.pi * k / N)
        qq, ok, _ = solve_path(mech, q, size)
        if ok:
            W = mech.tf(qq)
            frames.append({n: W[n].round(6).tolist() for n in names})
    allc = np.array([props[n]["com_mm"] for n in names])
    centre = allc.mean(0)
    depth = {n: 0 for n in names}
    for n in t["order"]:
        for c in t["children"].get(n, []):
            depth[c] = depth[n] + 1
    explode = {}
    for n in names:
        d = np.asarray(props[n]["com_mm"]) - centre
        L = np.linalg.norm(d)
        d = d / L if L > 1e-6 else np.array([0, 0, 1.0])
        explode[n] = (d * size * 0.45 * (1 + 0.5 * depth[n])).round(3).tolist()
    (out_dir / "kin.json").write_text(json.dumps({"names": names, "explode": explode,
                                                  "frames": frames or [{n: np.eye(4).tolist() for n in names}]}),
                                      encoding="utf-8")
    return {"ok": True, "robot": robot, "root": t["root"], "loose": t["loose"],
            "joints": [{k: j[k] for k in ("name", "parent", "child", "kind", "origin", "axis", "limits", "effort",
                                          "velocity", "assumed", "driver", "closure")} for j in joints],
            "loops": [c["name"] for c in t["closures"]], "passive": mech.passive, "drivers": sorted(mech.drivers),
            "couplings": [{k: v for k, v in c.items() if k != "table"} for c in coup], "links": [{"name": n, "mass_kg": round(props[n]["mass_kg"], 4),
                                          "com_mm": [round(x, 2) for x in props[n]["com_mm"]]} for n in names],
            "range": rng, "torque": tq, "fourbar": fb, "dynamics": dyn, "cam_contact": contact, "backlash": play,
            "slots": [c["name"] for c in t["closures"] if c["kind"] == "slot"],
            "collisions": {"poses": cm["poses"], "can_collide": cm["can_collide"], "disabled": len(cm["disable"])},
            "urdf": pkg}
