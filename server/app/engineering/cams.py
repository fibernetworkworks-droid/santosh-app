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
                    "rho_min": rho_min, "s0": s0, "rho_profile": rho - r, "roller_radius": r})
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
                    "face_width": width, "rho_profile": rho})
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


# ---------------------------------------------------------------- v0.427 cam CONTACT: the force at the cam, the spring
# that keeps the follower on it, the Hertz stress, the guide's side load.
# Allowable contact (surface fatigue) stress, MPa - STARTING POINTS: steel = AGMA 2001 grade 1 through-hardened at
# ~200 HB (Sc = 2.22 HB + 200), 'hardened' = AGMA carburised grade 1; the others are common handbook figures. Her
# number (contact_allow_mpa) always wins.
CONTACT_ALLOW = {"hardened": 1240.0, "steel": 640.0, "stainless": 600.0, "cast iron": 450.0, "titanium": 800.0,
                 "brass": 300.0, "copper": 250.0, "aluminium": 200.0, "aluminum": 200.0, "nylon": 40.0, "pom": 45.0,
                 "abs": 25.0, "pla": 25.0, "petg": 25.0, "polycarbonate": 30.0, "wood": 10.0}


def allow_for(material: str) -> tuple[str, float]:
    n = (material or "steel").lower()
    for k in sorted(CONTACT_ALLOW, key=len, reverse=True):
        if k in n:
            return k, CONTACT_ALLOW[k]
    return "steel", CONTACT_ALLOW["steel"]


def geometry(des: dict[str, Any], every: int = 2) -> dict[str, list[float]]:
    """What the contact check needs per cam angle (kept small enough to travel in the job result)."""
    pg = des["program"]
    sl = slice(None, None, every)
    return {"theta": [float(x) for x in pg["theta"][sl]], "s": [float(x) for x in pg["s"][sl]],
            "v": [float(x) for x in pg["v"][sl]], "a": [float(x) for x in pg["a"][sl]],
            "phi": [float(x) for x in des["phi_deg"][sl]], "rho": [float(x) for x in des["rho_profile"][sl]]}


def _spring(F: np.ndarray, s_m: np.ndarray, k_given: float | None, p_given: float | None, sf: float = 1.3):
    """The return spring: k (N/m), preload P (N). The cam can only PUSH, so the follower stays on only where
    F_need + k s + P > 0. Designed (when she gave none) as the smallest preload for each stiffness, then the
    stiffness that gives the lowest peak cam force; floor = 2 % of the peak need (>= 0.5 N)."""
    floor = max(0.5, 0.02 * float(np.max(np.abs(F))))
    deficit = sf * np.maximum(0.0, -F) + floor            # what the spring must give at each angle
    if k_given is not None or p_given is not None:
        return float(k_given or 0.0), float(p_given or 0.0), False
    if float(np.max(-F)) < -floor:                          # gravity / the load alone keeps it on
        return 0.0, 0.0, True
    lift = float(np.max(s_m) - np.min(s_m)) or 1e-3
    best = None
    for k in np.linspace(0, 6 * float(np.max(deficit)) / lift, 121):
        P = max(0.0, float(np.max(deficit - k * s_m)))
        peak = float(np.max(F + k * s_m + P))
        if best is None or peak < best[2] - 1e-9:
            best = (float(k), P, peak)
    return best[0], best[1], True


def contact(geo: dict, F_need, rpm: float, *, kind: str = "roller", roller_radius: float = 5.0,
            width: float = 10.0, cam_material: str = "steel", roller_material: str = "steel",
            spring_k: float | None = None, preload: float | None = None, guide_mu: float = 0.0,
            guide_len: float | None = None, overhang: float | None = None,
            allow_mpa: float | None = None, E=None) -> dict[str, Any]:
    """F_need(theta) = the force (N, along +lift) the follower needs to make its motion (inertia + gravity + its
    load + joint friction). Returns the spring, the normal contact force N, Hertz stress and the cam torque.
    Units: s mm, s' mm/rad, rpm; spring k reported in N/mm."""
    th = np.asarray(geo["theta"], float)
    F = np.asarray(F_need, float)
    s_m = np.asarray(geo["s"], float) / 1000.0
    ds = np.asarray(geo["v"], float) / 1000.0              # m/rad
    phi = np.radians(np.asarray(geo["phi"], float))
    rho = np.asarray(geo["rho"], float)                    # profile radius of curvature, + convex, mm
    w = rpm * 2 * math.pi / 60
    k, P, designed = _spring(F, s_m, None if spring_k is None else float(spring_k) * 1000.0, preload)
    C = F + k * s_m + P                                    # axial push the cam must give
    amp = 1.0 + (2.0 * float(overhang) / float(guide_len) if guide_len and overhang else 0.0)
    side = guide_mu * np.abs(np.sin(phi)) * amp            # guide friction per unit normal force
    vsign = np.sign(ds)
    D = np.cos(phi) - side * np.where(C >= 0, vsign, -vsign)
    D_worst = np.cos(phi) - side
    Nn = np.where(D > 1e-6, C / np.maximum(D, 1e-6), np.inf)
    # Hertz line contact: roller (or flat face) on the cam profile
    (E1, n1), (E2, n2) = E or ((200000.0, 0.29), (200000.0, 0.29))
    Es = 1.0 / ((1 - n1 * n1) / E1 + (1 - n2 * n2) / E2)
    with np.errstate(divide="ignore"):
        inv = (1.0 / roller_radius if kind == "roller" else 0.0) + np.where(np.abs(rho) > 1e-9, 1.0 / rho, 0.0)
    Rs = np.where(inv > 1e-12, 1.0 / np.maximum(inv, 1e-12), np.inf)
    Np = np.maximum(Nn, 0.0)
    p = np.where(np.isfinite(Rs) & np.isfinite(Np), np.sqrt(Np * Es / (math.pi * width * np.where(np.isfinite(Rs), Rs, 1.0))), 0.0)
    b = np.where(np.isfinite(Rs) & np.isfinite(Np), np.sqrt(4 * Np * np.where(np.isfinite(Rs), Rs, 1.0) / (math.pi * width * Es)), 0.0)
    mat_key, allow = allow_for(cam_material)
    if allow_mpa:
        allow, mat_key = float(allow_mpa), "her number"
    if kind == "roller":
        rk, ra = allow_for(roller_material)
        if not allow_mpa and ra < allow:
            allow, mat_key = ra, f"roller {rk}"
    torque = C * ds + guide_mu * np.where(np.isfinite(Nn), Nn, 0.0) * np.abs(np.sin(phi)) * amp * np.abs(ds)
    i_min = int(np.argmin(C))
    rows = []
    rows.append({"check": "Follower stays on the cam", "ok": bool(np.min(C) > 0),
                 "measured": f"min push {np.min(C):.3g} N at {math.degrees(th[i_min]):.0f}°", "limit": "> 0 N",
                 "fix": "a stiffer return spring / more preload (or let Hoola design it: leave spring_k / preload out), "
                        "a lower rpm or a gentler law"})
    if designed:
        sp = "not needed: gravity / the load keeps the follower on" if k == 0 and P == 0 else \
            f"k {k / 1000:.3g} N/mm, preload {P:.3g} N, max {float(np.max(k * s_m + P)):.3g} N (x1.3 on the pull-off)"
    else:
        sp = f"her spring k {k / 1000:.3g} N/mm, preload {P:.3g} N"
    rows.append({"check": "Return spring", "ok": True, "measured": sp, "limit": "-", "fix": ""})
    rows.append({"check": "Contact force", "ok": bool(np.all(np.isfinite(Nn))),
                 "measured": f"max {np.max(np.where(np.isfinite(Nn), Nn, 0)):.3g} N normal to the profile",
                 "limit": "roller bearing / follower rated above this", "fix": "lower the pressure angle"})
    rows.append({"check": "Contact stress (Hertz)", "ok": bool(np.max(p) <= allow),
                 "measured": f"max {np.max(p):.0f} MPa, contact band {2 * float(np.max(b)):.3f} mm",
                 "limit": f"<= {allow:.0f} MPa ({mat_key})",
                 "fix": "a wider cam / roller, a bigger roller or base circle, a harder material, a lower rpm"})
    if guide_mu:
        rows.append({"check": "Follower guide does not jam", "ok": bool(np.min(D_worst) >= 0.5),
                     "measured": f"min cos φ - μ·sin φ·(1+2b/l) = {np.min(D_worst):.3g}", "limit": ">= 0.5",
                     "fix": "a lower pressure angle, a longer guide, less overhang, a lower-friction guide"})
    return {"rows": rows, "spring_k_n_mm": round(k / 1000, 5), "preload_n": round(P, 4), "spring_designed": designed,
            "min_push_n": round(float(np.min(C)), 4), "max_normal_n": round(float(np.max(np.where(np.isfinite(Nn), Nn, 0))), 4),
            "max_hertz_mpa": round(float(np.max(p)), 2), "allow_mpa": allow,
            "cam_torque_peak": round(float(np.max(np.abs(torque))), 5),
            "curve": {"deg": [round(math.degrees(x), 2) for x in th[::3]], "push": [round(float(x), 4) for x in C[::3]],
                      "normal": [round(float(x), 4) if np.isfinite(x) else None for x in Nn[::3]],
                      "hertz": [round(float(x), 2) for x in p[::3]]}}


def need_from_motion(geo: dict, mass_kg: float, rpm: float, g_along: float) -> np.ndarray:
    """F_need for a rigid follower in pure translation: m (s'' w^2 - g.u), with g.u the gravity along +lift (m/s^2)."""
    w = rpm * 2 * math.pi / 60
    return mass_kg * (np.asarray(geo["a"], float) * w * w / 1000.0 - g_along)
