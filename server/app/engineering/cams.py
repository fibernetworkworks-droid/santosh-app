"""v0.425 HOOLA CAMS: a disc cam DESIGNED from the follower motion she wants (box side).

She gives the follower's program as segments around one turn - rise / dwell / return / dwell with a motion law
(cycloidal, harmonic, 3-4-5 polynomial) - and the follower kind:
  translating ROLLER (roller radius, offset e)   pitch curve -> profile = the pitch curve moved in by the roller
  translating FLAT-FACED                          profile = the envelope of the face lines
The cam is made from the motion (not the other way round), and checked the way a cam designer checks it:
  pressure angle (roller: <= 30° for a translating follower), pitch-curve radius of curvature > roller radius
  (else the profile UNDERCUTS and the follower cannot follow the asked motion), flat face: rho = Rb + s + s'' > 0
  (else cusps) and the face width the contact point needs, velocity / acceleration / jerk at her rpm.
Laws are the textbook closed forms (Norton, Design of Machinery; Shigley), checked in tests at known points."""
from __future__ import annotations

import math
from typing import Any

import numpy as np

LAWS = ("cycloidal", "harmonic", "345")


def _law(law: str, h: float, beta: float, t: np.ndarray):
    """(s, s', s'', s''') for a RISE of h over beta radians, t = local angle in [0, beta] (derivatives per radian)."""
    x = t / beta
    if law == "cycloidal":
        s = h * (x - np.sin(2 * np.pi * x) / (2 * np.pi))
        v = h / beta * (1 - np.cos(2 * np.pi * x))
        a = 2 * np.pi * h / beta ** 2 * np.sin(2 * np.pi * x)
        j = 4 * np.pi ** 2 * h / beta ** 3 * np.cos(2 * np.pi * x)
    elif law == "harmonic":
        s = h / 2 * (1 - np.cos(np.pi * x))
        v = np.pi * h / (2 * beta) * np.sin(np.pi * x)
        a = np.pi ** 2 * h / (2 * beta ** 2) * np.cos(np.pi * x)
        j = -np.pi ** 3 * h / (2 * beta ** 3) * np.sin(np.pi * x)
    elif law == "345":
        s = h * (10 * x ** 3 - 15 * x ** 4 + 6 * x ** 5)
        v = h / beta * (30 * x ** 2 - 60 * x ** 3 + 30 * x ** 4)
        a = h / beta ** 2 * (60 * x - 180 * x ** 2 + 120 * x ** 3)
        j = h / beta ** 3 * (60 - 360 * x + 360 * x ** 2)
    else:
        raise ValueError(f"cam law '{law}' (cycloidal / harmonic / 345)")
    return s, v, a, j


def program(segments: list[dict], n: int = 720) -> dict[str, np.ndarray]:
    """theta (rad, 0..2pi) -> s (mm), s', s'', s''' per radian for the whole turn."""
    tot = sum(float(sg["deg"]) for sg in segments)
    if abs(tot - 360) > 1e-6:
        raise ValueError(f"cam segments must add up to 360° (they add up to {tot:g}°)")
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    s, v, a, j = (np.zeros(n) for _ in range(4))
    start, level = 0.0, 0.0
    for sg in segments:
        kind = sg.get("type", "rise")
        beta = math.radians(float(sg["deg"]))
        m = (th >= start - 1e-12) & (th < start + beta - 1e-12)
        loc = th[m] - start
        if kind == "dwell":
            s[m] = level
        else:
            h = float(sg.get("lift", 0.0)) * (1 if kind == "rise" else -1)
            ss, vv, aa, jj = _law(sg.get("law", "cycloidal"), h, beta, loc)
            s[m], v[m], a[m], j[m] = level + ss, vv, aa, jj
            level += h
        start += beta
    if abs(level) > 1e-6:
        raise ValueError(f"cam must end where it started: rises - returns = {level:g} mm, not 0")
    return {"theta": th, "s": s, "v": v, "a": a, "j": j}


def design(spec: dict[str, Any]) -> dict[str, Any]:
    """The cam's pitch / profile points (cam frame, mm) and the designer's checks."""
    pg = program(spec["segments"], int(spec.get("points") or 720))
    th, s, v, a = pg["theta"], pg["s"], pg["v"], pg["a"]
    rb = float(spec["base_radius"])
    kind = spec.get("follower", "roller")
    rpm = float(spec.get("rpm") or 60)
    w = rpm * 2 * math.pi / 60                                   # rad/s
    rows, out = [], {}
    if kind == "roller":
        r = float(spec.get("roller_radius") or 5.0)
        e = float(spec.get("offset") or 0.0)
        s0 = math.sqrt((rb + r) ** 2 - e ** 2)
        # follower moves along +Y at x = e; the cam turns +theta, so the point in the cam frame turns -theta
        yp = s0 + s
        px = e * np.cos(th) + yp * np.sin(th)
        py = -e * np.sin(th) + yp * np.cos(th)
        phi = np.degrees(np.arctan2(v - e, yp))                  # pressure angle
        # pitch-curve curvature (numeric, periodic)
        dx, dy = np.gradient(px, th), np.gradient(py, th)
        ddx, ddy = np.gradient(dx, th), np.gradient(dy, th)
        k = (dx * ddy - dy * ddx) / np.maximum((dx * dx + dy * dy) ** 1.5, 1e-12)
        area = 0.5 * float(np.sum(px * np.roll(py, -1) - np.roll(px, -1) * py))
        k = k * (1.0 if area > 0 else -1.0)                      # convex = positive whichever way the curve runs
        rho = 1.0 / np.where(np.abs(k) < 1e-12, 1e-12, k)
        convex = rho > 0
        rho_min = float(np.min(rho[convex])) if convex.any() else math.inf
        # profile = pitch curve moved toward the cam centre by r along the normal
        nx, ny = dy, -dx
        L = np.hypot(nx, ny)
        nx, ny = nx / L, ny / L
        cx, cy = px - r * nx, py - r * ny
        if np.mean(np.hypot(cx, cy)) > np.mean(np.hypot(px, py)):
            cx, cy = px + r * nx, py + r * ny
        lim_phi = float(spec.get("max_pressure_deg") or 30.0)
        rows.append({"check": "Pressure angle", "measured": f"max {np.max(np.abs(phi)):.1f}°", "limit": f"<= {lim_phi:g}°",
                     "ok": bool(np.max(np.abs(phi)) <= lim_phi),
                     "fix": "bigger base circle, a gentler law / longer rise angle, or an offset toward the rise"})
        rows.append({"check": "Undercut (pitch curve vs roller)", "measured": f"min radius {rho_min:.2f} mm",
                     "limit": f"> roller {r:g} mm", "ok": bool(rho_min > r * 1.05),
                     "fix": "bigger base circle or a smaller roller"})
        out.update({"pitch": np.stack([px, py], 1), "profile": np.stack([cx, cy], 1), "phi_deg": phi,
                    "rho_min": rho_min, "s0": s0})
    elif kind == "flat":
        ang = th
        cx = (rb + s) * np.sin(ang) + v * np.cos(ang)
        cy = (rb + s) * np.cos(ang) - v * np.sin(ang)
        rho = rb + s + a
        width = 2 * float(np.max(np.abs(v))) + 4.0
        rows.append({"check": "Cusps (radius of curvature)", "measured": f"min {np.min(rho):.2f} mm", "limit": "> 0",
                     "ok": bool(np.min(rho) > 0.5), "fix": "bigger base circle or a gentler law"})
        rows.append({"check": "Face width needed", "measured": f"{width:.1f} mm", "limit": "the follower face",
                     "ok": True, "fix": ""})
        out.update({"profile": np.stack([cx, cy], 1), "phi_deg": np.zeros_like(th), "rho_min": float(np.min(rho)),
                    "face_width": width})
    else:
        raise ValueError("cam follower: roller / flat")
    vel = v * w                                                  # mm/s
    acc = a * w * w / 1000.0                                     # m/s²
    jerk = pg["j"] * w ** 3 / 1000.0                             # m/s³
    rows.append({"check": f"Follower motion at {rpm:g} rpm", "measured": f"v max {np.max(np.abs(vel)):.1f} mm/s, "
                 f"a max {np.max(np.abs(acc)):.2f} m/s², jerk max {np.max(np.abs(jerk)):.1f} m/s³", "limit": "-",
                 "ok": True, "fix": ""})
    lift = float(np.max(s) - np.min(s))
    return {"program": pg, "rows": rows, "lift": lift, "rpm": rpm, "kind": kind, "vel": vel, "acc": acc, "jerk": jerk,
            **out}


def solid(spec: dict[str, Any], des: dict[str, Any]):
    """The cam disc: the profile as a closed spline, extruded along +Z from z=0, with a centre bore."""
    import cadquery as cq
    pts = des["profile"][::max(1, len(des["profile"]) // 360)]
    vs = [cq.Vector(float(x), float(y), 0) for x, y in pts]
    edge = cq.Edge.makeSpline(vs + [vs[0]], periodic=False)
    wire = cq.Wire.assembleEdges([edge])
    t = float(spec.get("thickness") or 10.0)
    body = cq.Workplane("XY").add(cq.Solid.extrudeLinear(cq.Face.makeFromWires(wire), cq.Vector(0, 0, t)))
    bore = float(spec.get("bore") or 0)
    if bore > 0:
        body = body.cut(cq.Workplane("XY").circle(bore / 2).extrude(t))
    return body


def table(des: dict[str, Any]) -> dict[str, list[float]]:
    """theta (rad) -> follower lift (m) for the joint coupling."""
    return {"theta": [float(x) for x in des["program"]["theta"]], "s": [float(x) / 1000.0 for x in des["program"]["s"]]}
