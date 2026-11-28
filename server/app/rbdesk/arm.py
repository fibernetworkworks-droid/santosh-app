"""A robot arm worked out from its Denavit-Hartenberg table: where the tool is for given joint values (forward kinematics), the joint
values that reach a target (inverse kinematics by damped least squares, within the joint limits), the Jacobian with how close the
arm is to a singularity, and the torque each joint must hold for a payload at the tool. Standard (Denavit-Hartenberg) and modified
(Craig) tables both work. All in code from the table she gives."""
from __future__ import annotations

import math
import re
from typing import Any

import numpy as np


class ArmError(ValueError):
    pass


G = 9.80665
_LEN = {"m": 1.0, "mm": 0.001, "cm": 0.01, "in": 0.0254}


def _len(v: str, what: str) -> float:
    m = re.fullmatch(r"\s*([-+]?\d*\.?\d+(?:e[-+]?\d+)?)\s*(m|mm|cm|in)?\s*", str(v), re.I)
    if not m:
        raise ArmError(f"{what}: a length such as 0.333 or 333mm.")
    return float(m.group(1)) * _LEN[(m.group(2) or "m").lower()]


def _ang(v: str, what: str, unit: str = "deg") -> float:
    m = re.fullmatch(r"\s*([-+]?\d*\.?\d+(?:e[-+]?\d+)?)\s*(deg|rad|°)?\s*", str(v), re.I)
    if not m:
        raise ArmError(f"{what}: an angle such as -90 or 1.57rad.")
    u = (m.group(2) or unit).lower()
    return float(m.group(1)) if u in ("deg", "°") else math.degrees(float(m.group(1)))


def parse(text: str, length_unit: str = "m") -> dict[str, Any]:
    """One joint per line: name, revolute | prismatic | fixed, and d= a= alpha= theta= (offset) min= max=. A line named tool (or
    flange / tcp / ee) is a fixed transform after the last joint."""
    joints: list[dict[str, Any]] = []
    tool = None
    for n, raw in enumerate(str(text or "").splitlines(), 1):
        ln = raw.split("#")[0].strip()
        if not ln or re.match(r"^(name|joint)\s+(type|d)\b", ln, re.I):
            continue
        toks = ln.replace(",", " ").split()
        kv: dict[str, str] = {}
        rest: list[str] = []
        for t in toks:
            if "=" in t:
                k, v = t.split("=", 1)
                kv[k.lower()] = v
            else:
                rest.append(t)
        if not rest:
            raise ArmError(f"Line {n}: start with the joint's name.")
        name = rest[0]
        kind = next((r.lower() for r in rest[1:] if r.lower() in ("revolute", "prismatic", "fixed", "r", "p", "continuous")), "")
        kind = {"r": "revolute", "p": "prismatic", "continuous": "revolute"}.get(kind, kind)
        istool = name.lower() in ("tool", "flange", "tcp", "ee", "end", "gripper")
        if istool:
            kind = "fixed"
        if not kind:
            kind = "revolute"
        bad = set(kv) - {"d", "a", "alpha", "theta", "min", "max", "offset", "vmax", "effort"}
        if bad:
            raise ArmError(f"Line {n}: {', '.join(sorted(bad))} is not a column - use d=, a=, alpha=, theta=, min=, max=.")
        conv = lambda v, w: _len(v if re.search(r"[a-z]$", v, re.I) else v + length_unit, w)   # noqa: E731
        j = {"name": name, "type": kind, "line": n,
             "d": conv(kv.get("d", "0"), f"Line {n} d"), "a": conv(kv.get("a", "0"), f"Line {n} a"),
             "alpha": math.radians(_ang(kv.get("alpha", "0"), f"Line {n} alpha")),
             "theta": math.radians(_ang(kv.get("theta", kv.get("offset", "0")), f"Line {n} theta")) if kind != "prismatic" else math.radians(_ang(kv.get("theta", "0"), f"Line {n} theta")),
             "min": None, "max": None}
        for k in ("min", "max"):
            if k in kv:
                j[k] = math.radians(_ang(kv[k], f"Line {n} {k}")) if kind == "revolute" else conv(kv[k], f"Line {n} {k}")
        if j["min"] is not None and j["max"] is not None and j["min"] >= j["max"]:
            raise ArmError(f"Line {n}: min must be below max.")
        if istool:
            if tool is not None:
                raise ArmError("Only one tool line.")
            tool = j
        else:
            if tool is not None:
                raise ArmError(f"Line {n}: the tool line comes last.")
            joints.append(j)
    if not [j for j in joints if j["type"] != "fixed"]:
        raise ArmError("No moving joint found. One per line: 'j1 revolute d=0.333 a=0 alpha=-90'.")
    if len(joints) > 12:
        raise ArmError("Up to 12 joints.")
    return {"joints": joints, "tool": tool}


def _dh(j: dict[str, Any], q: float, mode: str) -> tuple[np.ndarray, np.ndarray]:
    """Returns (before, after): the transform up to where the joint moves, and the whole link transform."""
    th, d = j["theta"], j["d"]
    if j["type"] == "revolute":
        th += q
    elif j["type"] == "prismatic":
        d += q
    ca, sa, ct, st = math.cos(j["alpha"]), math.sin(j["alpha"]), math.cos(th), math.sin(th)
    rz = np.array([[ct, -st, 0, 0], [st, ct, 0, 0], [0, 0, 1, d], [0, 0, 0, 1.0]])
    rx = np.array([[1, 0, 0, j["a"]], [0, ca, -sa, 0], [0, sa, ca, 0], [0, 0, 0, 1.0]])
    if mode == "modified":
        return rx, rx @ rz
    return np.eye(4), rz @ rx


def fk(model: dict[str, Any], q: list[float], mode: str) -> dict[str, Any]:
    T = np.eye(4)
    frames, axes = [T[:3, 3].copy()], []
    mv = [j for j in model["joints"]]
    qi = iter(q)
    for j in mv:
        v = next(qi) if j["type"] != "fixed" else 0.0
        before, link = _dh(j, v, mode)
        if j["type"] != "fixed":
            J0 = T @ before
            axes.append((J0[:3, 2].copy(), J0[:3, 3].copy(), j["type"]))
        T = T @ link
        frames.append(T[:3, 3].copy())
    if model.get("tool"):
        _, link = _dh(model["tool"], 0.0, mode)
        T = T @ link
        frames.append(T[:3, 3].copy())
    return {"T": T, "frames": frames, "axes": axes}


def jacobian(model: dict[str, Any], q: list[float], mode: str) -> np.ndarray:
    f = fk(model, q, mode)
    p = f["T"][:3, 3]
    cols = []
    for z, o, kind in f["axes"]:
        cols.append(np.concatenate([np.cross(z, p - o), z]) if kind == "revolute" else np.concatenate([z, np.zeros(3)]))
    return np.array(cols).T


def rpy(R: np.ndarray) -> tuple[float, float, float]:
    """Roll, pitch, yaw (Z-Y-X, as ROS uses) in degrees."""
    sy = -R[2, 0]
    pitch = math.asin(max(-1.0, min(1.0, sy)))
    if abs(abs(sy) - 1) < 1e-9:
        roll, yaw = 0.0, math.atan2(-R[0, 1], R[1, 1])
    else:
        roll, yaw = math.atan2(R[2, 1], R[2, 2]), math.atan2(R[1, 0], R[0, 0])
    return math.degrees(roll), math.degrees(pitch), math.degrees(yaw)


def _rot(r: float, p: float, y: float) -> np.ndarray:
    r, p, y = map(math.radians, (r, p, y))
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    return np.array([[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr], [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr], [-sp, cp * sr, cp * cr]])


def _qparse(v: Any, model: dict[str, Any], what: str, length_unit: str) -> list[float]:
    mv = [j for j in model["joints"] if j["type"] != "fixed"]
    if v in (None, ""):
        return [0.0] * len(mv)
    vals = [x for x in re.split(r"[\s,;]+", str(v).strip()) if x]
    if len(vals) != len(mv):
        raise ArmError(f"{what}: {len(mv)} values, one per moving joint ({', '.join(j['name'] for j in mv)}).")
    out = []
    for j, x in zip(mv, vals):
        out.append(math.radians(_ang(x, what)) if j["type"] == "revolute" else _len(x if re.search(r"[a-z]$", x, re.I) else x + length_unit, what))
    return out


def _err(T: np.ndarray, pos: np.ndarray, R: np.ndarray | None) -> np.ndarray:
    e = pos - T[:3, 3]
    if R is None:
        return e
    Re = R @ T[:3, :3].T
    w = 0.5 * np.array([Re[2, 1] - Re[1, 2], Re[0, 2] - Re[2, 0], Re[1, 0] - Re[0, 1]])
    return np.concatenate([e, w])


def ik(model: dict[str, Any], pos: np.ndarray, R: np.ndarray | None, q0: list[float], mode: str, tol_m: float = 1e-4) -> dict[str, Any]:
    mv = [j for j in model["joints"] if j["type"] != "fixed"]
    lo = np.array([j["min"] if j["min"] is not None else -1e9 for j in mv])
    hi = np.array([j["max"] if j["max"] is not None else 1e9 for j in mv])
    seeds = [np.array(q0)]
    rng = np.random.default_rng(7)
    for _ in range(11):
        seeds.append(np.array([rng.uniform(max(l, -math.pi), min(h, math.pi)) if j["type"] == "revolute" else rng.uniform(max(l, -0.5), min(h, 0.5))
                               for j, l, h in zip(mv, lo, hi)]))
    best = None
    for s in seeds:
        q = np.clip(s, lo, hi)
        lam = 0.05
        for it in range(300):
            T = fk(model, list(q), mode)["T"]
            e = _err(T, pos, R)
            if np.linalg.norm(e[:3]) < tol_m and (R is None or np.linalg.norm(e[3:]) < 1e-3):
                break
            J = jacobian(model, list(q), mode)
            if R is None:
                J = J[:3]
            dq = J.T @ np.linalg.solve(J @ J.T + lam ** 2 * np.eye(J.shape[0]), e)
            n = np.linalg.norm(dq)
            if n > 0.4:
                dq *= 0.4 / n
            q = np.clip(q + dq, lo, hi)
        T = fk(model, list(q), mode)["T"]
        e = _err(T, pos, R)
        pe, oe = float(np.linalg.norm(e[:3])), float(np.linalg.norm(e[3:])) if R is not None else 0.0
        score = pe + oe * 0.1
        if best is None or score < best["score"]:
            best = {"q": q, "pos_err": pe, "ori_err": math.degrees(oe), "iters": it + 1, "score": score}
        if pe < tol_m and (R is None or oe < 1e-3):
            break
    best["ok"] = best["pos_err"] < tol_m * 10 and (R is None or best["ori_err"] < 0.5)
    return best


def _qview(model: dict[str, Any], q: list[float]) -> list[dict[str, Any]]:
    mv = [j for j in model["joints"] if j["type"] != "fixed"]
    out = []
    for j, v in zip(mv, q):
        val = round(math.degrees(v), 3) if j["type"] == "revolute" else round(v, 5)
        lim = None
        if j["min"] is not None or j["max"] is not None:
            f = (lambda x: round(math.degrees(x), 2)) if j["type"] == "revolute" else (lambda x: round(x, 5))
            lim = [f(j["min"]) if j["min"] is not None else None, f(j["max"]) if j["max"] is not None else None]
        out.append({"name": j["name"], "type": j["type"], "value": val, "unit": "°" if j["type"] == "revolute" else "m", "limit": lim,
                    "out": bool((j["min"] is not None and v < j["min"] - 1e-9) or (j["max"] is not None and v > j["max"] + 1e-9))})
    return out


def analyse(text: str, q: Any = "", target: Any = "", payload: Any = 0, mode: str = "standard", length_unit: str = "m") -> dict[str, Any]:
    if mode not in ("standard", "modified"):
        raise ArmError("Table kind: standard (Denavit-Hartenberg) or modified (Craig).")
    model = parse(text, length_unit)
    mv = [j for j in model["joints"] if j["type"] != "fixed"]
    qv = _qparse(q, model, "Joint values", length_unit)
    f = fk(model, qv, mode)
    T = f["T"]
    J = jacobian(model, qv, mode)
    sv = np.linalg.svd(J, compute_uv=False)
    Jv = J[:3]
    manip = float(math.sqrt(max(0.0, np.linalg.det(J @ J.T)))) if J.shape[1] >= 6 else float(math.sqrt(max(0.0, np.linalg.det(Jv @ Jv.T)))) if J.shape[1] >= 3 else 0.0
    ranks = int(np.sum(sv > 1e-6 * max(1.0, sv[0])))
    issues: list[dict[str, Any]] = []
    qvw = _qview(model, qv)
    for x in qvw:
        if x["out"]:
            issues.append({"sev": "bad", "area": "Limits", "text": f"{x['name']} is at {x['value']}{x['unit']}, outside its limits {x['limit'][0]} to {x['limit'][1]}.", "fix": "Pick joint values inside the limits."})
    dof = len(mv)
    if dof < 6:
        issues.append({"sev": "info", "area": "Freedom", "text": f"{dof} moving joints: the tool cannot take every position and orientation (6 are needed for that) - inverse kinematics solves the position only unless you give fewer constraints.", "fix": ""})
    elif dof > 6:
        issues.append({"sev": "info", "area": "Freedom", "text": f"{dof} moving joints: one pose has many joint solutions - the one closest to where the arm is now is kept.", "fix": ""})
    full = min(6, dof)
    near = False
    if dof >= 1 and ranks < full:
        issues.append({"sev": "bad", "area": "Singularity", "text": f"At these joint values the arm is in a singularity: it has lost {full - ranks} way(s) to move the tool, and joint speeds blow up near here.", "fix": "Keep the path away from these joint values (often a straight wrist or a stretched-out arm)."})
        near = True
    elif dof >= 6 and sv[-1] < 0.02 * sv[0]:
        issues.append({"sev": "warn", "area": "Singularity", "text": f"Close to a singularity: the weakest direction moves {sv[-1] / sv[0] * 100:.1f}% as easily as the strongest.", "fix": "Plan paths around this pose, or slow down here."})
        near = True
    reach = sum(abs(j["a"]) + abs(j["d"]) for j in model["joints"]) + (abs(model["tool"]["a"]) + abs(model["tool"]["d"]) if model.get("tool") else 0)
    reach += sum(max(abs(j["min"] or 0), abs(j["max"] or 0)) for j in mv if j["type"] == "prismatic")
    lims = {x["name"]: x["limit"] for x in qvw}
    rows = [{"name": j["name"], "type": j["type"], "d": round(j["d"], 6), "a": round(j["a"], 6), "alpha": round(math.degrees(j["alpha"]), 3),
             "theta": round(math.degrees(j["theta"]), 3), "limit": lims.get(j["name"])} for j in model["joints"] + ([model["tool"]] if model.get("tool") else [])]
    z0 = lambda v: 0.0 if abs(v) < 5e-13 else v   # noqa: E731
    out: dict[str, Any] = {"mode": mode, "dof": dof, "joints": rows,
                           "tool": bool(model.get("tool")), "q": qvw,
                           "pose": {"xyz": [z0(round(float(v), 6)) for v in T[:3, 3]], "rpy": [z0(round(v, 3)) for v in rpy(T[:3, :3])], "R": [[z0(round(float(v), 6)) for v in r] for r in T[:3, :3]]},
                           "frames": [[round(float(v), 5) for v in p] for p in f["frames"]],
                           "singular_values": [round(float(v), 6) for v in sv], "manipulability": round(manip, 6), "rank": ranks, "near_singular": near,
                           "reach": round(reach, 4), "jacobian": [[round(float(v), 5) for v in r] for r in J]}
    tg = str(target or "").strip()
    if tg:
        vals = [x for x in re.split(r"[\s,;]+", tg) if x]
        if len(vals) not in (3, 6):
            raise ArmError("Target: x y z (metres) and, if the tool's orientation matters, roll pitch yaw (degrees).")
        pos = np.array([_len(v if re.search(r"[a-z]$", v, re.I) else v + length_unit, "Target") for v in vals[:3]])
        R = _rot(*[_ang(v, "Target") for v in vals[3:]]) if len(vals) == 6 else None
        if R is not None and dof < 6:
            issues.append({"sev": "warn", "area": "Inverse kinematics", "text": "An orientation was given but the arm has fewer than 6 joints - only the position is solved.", "fix": ""})
            R = None
        dist = float(np.linalg.norm(pos - f["frames"][0]))
        r = ik(model, pos, R, qv, mode)
        out["ik"] = {"target": [round(float(v), 6) for v in pos], "rpy": [round(_ang(v, "Target"), 3) for v in vals[3:]] if R is not None else None,
                     "ok": r["ok"], "q": _qview(model, list(r["q"])), "pos_err_mm": round(r["pos_err"] * 1000, 4), "ori_err_deg": round(r["ori_err"], 4),
                     "iters": r["iters"], "distance": round(dist, 4)}
        if not r["ok"]:
            why = "farther than the arm reaches" if dist > reach else "outside what the joint limits allow, or the orientation cannot be taken there"
            issues.append({"sev": "bad", "area": "Inverse kinematics", "text": f"The target is not reached: best attempt is {r['pos_err'] * 1000:.1f} mm off - it is probably {why}.", "fix": "Move the target, widen the limits if the hardware allows, or drop the orientation."})
        else:
            Jt = jacobian(model, list(r["q"]), mode)
            s2 = np.linalg.svd(Jt, compute_uv=False)
            if dof >= 6 and s2[-1] < 0.02 * s2[0]:
                issues.append({"sev": "warn", "area": "Inverse kinematics", "text": "The solution is close to a singularity: small target moves need big joint moves there.", "fix": ""})
    try:
        m = float(payload or 0)
    except (TypeError, ValueError):
        raise ArmError("Payload: kilograms.")
    if m < 0 or m > 5000:
        raise ArmError("Payload: 0 to 5000 kg.")
    if m:
        F = np.array([0, 0, -m * G])
        tau = Jv.T @ F
        out["torque"] = [{"name": j["name"], "type": j["type"], "value": z0(round(float(t), 3)), "unit": "N·m" if j["type"] == "revolute" else "N"} for j, t in zip(mv, tau)]
        out["payload"] = m
    bad = sum(1 for i in issues if i["sev"] == "bad")
    out["issues"] = issues
    out["counts"] = {s: sum(1 for i in issues if i["sev"] == s) for s in ("bad", "warn", "info")}
    x, y, z = out["pose"]["xyz"]
    out["verdict"] = (f"Tool at x {x:.4g} m, y {y:.4g} m, z {z:.4g} m" + (" - " + str(bad) + " problem" + ("s" if bad > 1 else "") if bad else "")
                      + (f"; the target is {'reached' if out['ik']['ok'] else 'not reached'}" if "ik" in out else ""))
    out["note"] = ("Worked out from the table you gave, with the base at the origin and z up. A wrong sign or offset in one row moves every "
                   "frame after it - check the result against the real arm at a known pose (for example all zeros). Payload torques are for "
                   "the payload alone held still; the arm's own weight and accelerations come on top.")
    return out
