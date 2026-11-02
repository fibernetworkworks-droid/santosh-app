"""v0.432 HOOLA GEAR STRENGTH: will the tooth BREAK off, or wear out, before her gear's life is up?

A gear's shape being right says nothing about whether it will last. Two different things kill a tooth:
  BENDING  the tooth snaps off at its root, where the bending stress is highest (ISO 6336-3)
  PITTING  the flanks press so hard they crumble into pits, and then the gear is scrap (ISO 6336-2)
Both are computed here, and both need the shape of the tooth ROOT, which is where this module starts:

1. THE REAL ROOT. A hobbed gear's root is not a circle and not a sharp corner - it is the TROCHOID swept by the
   rounded tip of the cutting rack as it rolls past. `profile()` generates it (the envelope of the rack tip circle),
   so the gear Hoola draws has the same root a real cut gear has - and `spur_gear` now uses it, which also takes
   the sharp stress-raising corner out of the model.
2. THE CRITICAL SECTION, two independent ways, which must agree or something is wrong:
   - MEASURED: walk the generated fillet and find where its tangent sits at 30 degrees to the tooth centre line
     (ISO's definition of the weakest section of an external tooth), then read the chord s_Fn, the arm h_Fa and the
     fillet radius rho_F off the real curve.
   - FROM THE STANDARD: ISO 6336-3's own closed-form equations (G, E, H, theta ...).
   The tests check the two against each other, and the finished bending stress against a real FEA of the same tooth.
3. THE FACTORS she cannot be expected to know are computed, not guessed: K_v from the pitch-line speed and the
   gear's quality grade (AGMA 2001 dynamic factor), K_A from the words she used about the drive, Z_H / Z_E / Z_eps
   from the geometry and the materials. Anything assumed is NAMED in the result.
WHAT WAS TRIED AND DID NOT WORK, said so nobody repeats it: the bending stress was also checked against Hoola's
own FEA of the same tooth (a tooth on a rim, the normal force on the tip along the real line of action). The load
and the reaction balanced to 0 %, and the peak landed exactly on the loaded side of the fillet - but the recovered
peak FELL as the mesh was refined (89 -> 46 MPa), which cannot be right at a stress raiser. The same solver
converges correctly upward to Kt 2.98 against the textbook 3.0 on a plate with a hole, so the solver is sound and
the gear ROOT FILLET is simply too small and too curved for its point-cloud mesher. So the gear check is NOT
validated against our FEA; it rests on the standard's own equations, on the two independent geometry methods
agreeing, and on the published factor values (Z_H 2.495 for 20 degrees).

Limits said out loud: straight spur teeth only (no helix / bevel / worm), ISO 6336 Method B / C factors, no
scuffing or micropitting check, and the allowable stresses are the standard's published grades - her gear maker's
own figures override them."""
from __future__ import annotations

import math
from typing import Any

import numpy as np

# Reference (cutting-rack) profile, in modules - ISO 53 basic rack, the one a standard hob cuts:
#   h_aP tooth height above the pitch line, h_fP below it, rho_fP the rounded tip that cuts the root fillet.
REF = {"h_aP": 1.0, "h_fP": 1.25, "rho_fP": 0.38}

# ISO 6336-5 allowable stresses, MPa: (sigma_Flim bending, sigma_Hlim pitting) for the material grades a small
# Indian shop actually buys. These are the standard's own MQ-grade figures; her gear maker's certificate wins.
GRADES = {
    "cast iron":        (90.0, 350.0),
    "mild steel":       (140.0, 370.0),      # normalized plain carbon (St 50 / C45 as-rolled)
    "steel":            (200.0, 500.0),      # through-hardened ~200 HB
    "steel 300hb":      (260.0, 650.0),      # quenched and tempered, 300 HB (EN8 / EN19 Q&T)
    "stainless":        (190.0, 470.0),
    "case hardened":    (430.0, 1300.0),     # 20MnCr5 / 16MnCr5 carburised and ground
    "nitrided":         (370.0, 1000.0),
    "bronze":           (60.0, 230.0),
    "brass":            (50.0, 200.0),
    "nylon":            (35.0, 60.0),
    "pom":              (40.0, 70.0),
    "abs":              (22.0, 40.0),
    "pla":              (22.0, 40.0),
    "petg":             (22.0, 40.0),
}
# How rough the drive is - ISO 6336-1 / AGMA application factor K_A, by the words she uses.
APPLICATION = {"uniform": 1.0, "smooth": 1.0, "electric motor": 1.0, "light shock": 1.25, "light": 1.25,
               "medium shock": 1.5, "medium": 1.5, "heavy shock": 1.75, "heavy": 1.75, "severe": 2.0}


class GearError(Exception):
    pass


def grade_for(material: str) -> tuple[str, float, float]:
    """Her material -> (name, sigma_Flim, sigma_Hlim). Longest match wins, so 'case hardened steel' beats 'steel'."""
    n = (material or "steel").lower().strip()
    for key in sorted(GRADES, key=len, reverse=True):
        if key in n:
            return key, *GRADES[key]
    return "steel", *GRADES["steel"]


def _inv(a: float) -> float:
    return math.tan(a) - a


def _inv_inverse(v: float) -> float:
    """The angle whose involute function is v (Newton; the involute is monotonic so this is safe)."""
    a = max(0.02, (3 * v) ** (1 / 3))
    for _ in range(60):
        f = math.tan(a) - a - v
        d = math.tan(a) ** 2
        if abs(d) < 1e-14:
            break
        step = f / d
        a -= step
        if abs(step) < 1e-14:
            break
    return a


def profile(m: float, z: int, alpha_deg: float = 20.0, x: float = 0.0, ref: dict | None = None,
            n_flank: int = 26, n_fillet: int = 26) -> dict[str, Any]:
    """One tooth of a hobbed external spur gear, centred on +Y: the trochoid root fillet the rack tip cuts, the
    involute flank, and the tip. Returns the half tooth (root centre -> tip) and the whole closed outline."""
    r = dict(REF, **(ref or {}))
    if z < 6:
        raise GearError("gear: at least 6 teeth")
    al = math.radians(alpha_deg)
    rp = m * z / 2.0                                      # pitch radius
    rb = rp * math.cos(al)                                # base radius
    ra = rp + m * (r["h_aP"] + x)                         # tip radius
    rf = rp - m * (r["h_fP"] - x)                         # root radius (the rack tip line)
    rho = m * r["rho_fP"]                                 # rack tip corner radius
    if rf <= 0.25 * rp:
        raise GearError("gear: root radius too small - check module / teeth / shift")
    # --- the trochoid: the rack tip corner rolls past, its CENTRE draws a curve, and the fillet it cuts is that
    # curve offset by rho. The rack's generating pitch line is y = rp (it rolls on the gear's pitch circle without
    # slipping: the rack moves rp*phi while the gear turns phi); with a profile shift the rack's own reference line
    # sits x*m further out, which is already in rf. The rack TOOTH cuts the gear's tooth SPACE, so at phi = 0 its
    # centre line stands half a circular pitch (pi*m/2) from our tooth's centre, and its corner that cuts OUR right
    # flank is E*m back from that centre, where (exactly ISO 6336-3's E)
    #     E/m = pi/4 - h_fP*tan(alpha) - rho_fP*(1 - sin alpha)/cos(alpha)
    # is the distance from the rack tooth's centre to the corner centre (a circle of radius rho tangent to both the
    # sloping flank and the flat tip).
    E = m * (math.pi / 4.0 - r["h_fP"] * math.tan(al) - r["rho_fP"] * (1.0 - math.sin(al)) / math.cos(al))
    u0 = math.pi * m / 2.0 - E                            # along-rack position of that corner centre at phi = 0
    yc = rf + rho                                         # its height: a radius above the rack's flat tip

    def corner(phi: float) -> tuple[float, float]:
        """The rack tip corner CENTRE in the gear frame, for a roll angle phi."""
        sx, sy = u0 + rp * phi, yc                        # in the fixed frame while the rack has moved rp*phi
        c, s = math.cos(phi), math.sin(phi)
        return sx * c - sy * s, sx * s + sy * c           # rotate the gear back by phi

    phi0 = -u0 / rp                                       # the roll angle that brings the corner to the root
    phis = np.linspace(phi0 - 2.6 / math.sqrt(z), phi0 + 2.6 / math.sqrt(z), 2400)
    pts = np.array([corner(p) for p in phis])
    # the fillet = the corner-centre curve offset by rho. The rack's material is up and inward from the corner, so
    # the surface it leaves is the branch on the SMALLER-radius side (its lowest point touches the root circle).
    d = np.gradient(pts, axis=0)
    nrm = np.stack([d[:, 1], -d[:, 0]], 1)
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
    up, dn = pts + rho * nrm, pts - rho * nrm
    cand = dn if np.linalg.norm(dn, axis=1).min() < np.linalg.norm(up, axis=1).min() else up
    # The fillet bottoms out near the middle of the tooth gap and rises on BOTH sides - one branch climbs toward
    # OUR tooth's flank, the other toward the next tooth's. Ours is the one whose angle from the tooth centre line
    # FALLS as the radius grows (it comes back toward the tooth); the other one's rises.
    rad = np.linalg.norm(cand, axis=1)
    i_low = int(np.argmin(rad))
    best = None
    for half_c in (cand[i_low:], cand[: i_low + 1][::-1]):
        if len(half_c) < 8:
            continue
        rr_c = np.linalg.norm(half_c, axis=1)
        keep_c = np.r_[True, np.diff(rr_c) > 1e-9]        # strictly outwards, so theta(r) is a function
        hc, rr_c = half_c[keep_c], rr_c[keep_c]
        th_c = np.arctan2(hc[:, 0], hc[:, 1])
        if len(hc) < 8:
            continue
        drop = float(th_c[0] - th_c[-1])                  # positive = it comes back toward the tooth
        if best is None or drop > best[0]:
            best = (drop, hc, rr_c, th_c)
    if best is None or best[0] <= 0:
        raise GearError("gear: the root fillet could not be generated")
    _d, side, rr, th_f = best
    # --- the involute flank of the right side of the tooth, as theta(r) from the base circle to the tip
    half_p = math.pi / (2.0 * z) + 2.0 * x * math.tan(al) / z + _inv(al)   # half tooth angle at r = rb
    def th_inv(rv):
        rv = np.maximum(np.asarray(rv, float), rb)
        return half_p - (np.tan(np.arccos(np.minimum(1.0, rb / rv))) - np.arccos(np.minimum(1.0, rb / rv)))
    # --- where they meet. The real surface at any radius is whichever curve lies CLOSER to the tooth centre line,
    # so the junction is where the two cross. For a normal gear the trochoid runs into the involute exactly at the
    # base circle (checked: the two angles agree to 4e-5 rad on a standard 20-tooth gear). With many teeth the base
    # circle falls BELOW the root circle and the crossing sits higher up; with too few teeth the rack tip reaches
    # past the interference point, crosses ABOVE the base circle and eats part of the working flank - UNDERCUT,
    # a real weakening, so it is reported.
    # The involute only exists from the base circle up, and never below the root circle, so compare the two curves
    # from there. Walking outwards, the gap between them NARROWS to (almost) nothing and then opens again: that
    # turning point is where the fillet runs into the flank. (A standard 20-tooth gear touches at the base circle
    # itself, to 4e-5 rad; with many teeth the base circle is below the root and the touch sits a little higher.)
    r_lo = max(rf, rb) + 1e-9
    r_hi = min(float(rr.max()), ra) - 1e-9
    r_j, undercut = r_lo, False
    if r_hi > r_lo:
        rs = np.linspace(r_lo, r_hi, 800)
        diff = np.interp(rs, rr, th_f) - th_inv(rs)       # fillet further out in the gap than the flank = positive
        k = int(np.argmax(np.diff(diff) > 0)) if np.any(np.diff(diff) > 0) else len(rs) - 1
        neg = np.where(diff <= 0)[0]
        if len(neg) and neg[0] <= k:                      # it actually crosses: take the crossing
            j = int(neg[0])
            if j > 0 and diff[j - 1] != diff[j]:
                t = diff[j - 1] / (diff[j - 1] - diff[j])
                r_j = float(rs[j - 1] + t * (rs[j] - rs[j - 1]))
            else:
                r_j = float(rs[j])
        else:
            r_j = float(rs[k])
        # UNDERCUT: the rack tip has eaten into the flank where the involute should start
        undercut = bool(rb > rf and float(diff[0]) < -0.001)
    r_j = float(np.clip(r_j, max(rf, float(rr.min())) + 1e-6, ra - 1e-6))
    z_min = 2.0 * (r["h_aP"] - x) / math.sin(al) ** 2      # the classical limit (17 for a standard 20 deg gear)
    nf = max(6, int(n_fillet))
    r_fil = np.linspace(float(rr.min()), r_j, nf)
    fil_pts = np.stack([r_fil * np.sin(np.interp(r_fil, rr, th_f)), r_fil * np.cos(np.interp(r_fil, rr, th_f))], 1)
    r_in = np.linspace(r_j, ra, max(6, int(n_flank)))
    inv_pts = np.stack([r_in * np.sin(th_inv(r_in)), r_in * np.cos(th_inv(r_in))], 1)
    right = np.vstack([fil_pts, inv_pts[1:]])
    gap = float(np.linalg.norm(fil_pts[-1] - inv_pts[0]))
    # the root centre: the lowest fillet point swung round to the middle of the gap
    root_a = math.pi / z - math.atan2(right[0][0], right[0][1])
    rr0 = float(np.linalg.norm(right[0]))
    root = np.array([[rr0 * math.sin(root_a), rr0 * math.cos(root_a)]])
    half = np.vstack([root, right])
    whole = np.vstack([half, np.stack([-half[::-1, 0], half[::-1, 1]], 1)])
    return {"half": half, "whole": whole, "fillet": fil_pts, "rp": rp, "rb": rb, "ra": ra, "rf": rf, "rho_fP": rho,
            "alpha": al, "m": float(m), "z": int(z), "x": float(x), "ref": r, "join_gap_mm": gap,
            "join_r_mm": float(r_j), "undercut": undercut, "teeth_for_no_undercut": round(z_min, 2),
            "below_classical_limit": bool(z < z_min)}


def measured_root(pr: dict[str, Any]) -> dict[str, Any]:
    """The critical section MEASURED on the generated tooth: the point on the real fillet whose tangent stands at
    30 degrees to the tooth centre line (ISO's weakest-section rule for an external tooth), with the root chord
    s_Fn, the bending arm h_Fa to a tip load and the fillet radius rho_F read off that curve. This is the check on
    the geometry - the numbers used for the stress come from the standard's own equations in iso_root()."""
    fil, m = np.asarray(pr["fillet"], float), pr["m"]
    if len(fil) < 6:
        raise GearError("gear: fillet too short to measure")
    seg = np.linalg.norm(np.diff(fil, axis=0), axis=1)        # resample by arc length so the tangent is smooth
    sarc = np.r_[0.0, np.cumsum(seg)]
    u = np.linspace(0.0, sarc[-1], 200)
    cx = np.interp(u, sarc, fil[:, 0])
    cy = np.interp(u, sarc, fil[:, 1])
    t = np.gradient(np.stack([cx, cy], 1), axis=0)
    ang = np.degrees(np.arctan2(np.abs(t[:, 0]), np.abs(t[:, 1])))   # tangent vs the centre line (+Y)
    i = int(np.clip(np.argmin(np.abs(ang - 30.0)), 2, len(u) - 3))
    px, py = float(cx[i]), float(cy[i])
    s_Fn = 2.0 * abs(px)
    w = max(4, len(u) // 7)                                      # least-squares circle through the fillet around it
    lo_i, hi_i = max(0, i - w), min(len(u), i + w + 1)
    X, Y = cx[lo_i:hi_i], cy[lo_i:hi_i]
    A = np.stack([X, Y, np.ones_like(X)], 1)
    try:
        sol, *_ = np.linalg.lstsq(A, X ** 2 + Y ** 2, rcond=None)
        xc, yc2 = sol[0] / 2.0, sol[1] / 2.0
        rho_F = float(math.sqrt(max(sol[2] + xc * xc + yc2 * yc2, 1e-12)))
    except Exception:
        rho_F = float(pr["rho_fP"])
    # the bending arm: ISO measures to where the LINE OF ACTION of a tip load crosses the tooth centre line, not to
    # the tip itself. That line is the common normal of the involute, which is the tangent to the base circle, so it
    # is drawn from the real tip point of this profile and followed to x = 0.
    rb_, ra_ = pr["rb"], pr["ra"]
    tip = np.asarray(pr["half"][-1], float)
    L = math.sqrt(max(ra_ ** 2 - rb_ ** 2, 1e-12))               # length of the tangent from the tip to the base circle
    bt = math.atan2(tip[0], tip[1]) - math.acos(min(1.0, rb_ / ra_))   # the tangency point on the base circle
    T = np.array([rb_ * math.sin(bt), rb_ * math.cos(bt)])
    dirv = tip - T
    dirv = dirv / max(float(np.linalg.norm(dirv)), 1e-12)
    y_load = float(tip[1] - dirv[1] * (tip[0] / dirv[0])) if abs(dirv[0]) > 1e-9 else float(ra_)
    h_Fa = float(y_load - py)
    return {"s_Fn": s_Fn, "rho_F": rho_F, "h_Fa": h_Fa, "at_mm": [round(px, 4), round(py, 4)],
            "load_line_y_mm": round(y_load, 4), "tangent_len_mm": round(L, 4),
            "tangent_deg": round(float(ang[i]), 2), "s_Fn_m": s_Fn / m, "rho_F_m": rho_F / m, "h_Fa_m": h_Fa / m,
            "undercut": bool(pr.get("undercut"))}


def iso_root(m: float, z: int, alpha_deg: float = 20.0, x: float = 0.0, ref: dict | None = None) -> dict[str, Any]:
    """The same critical section from ISO 6336-3's own closed-form equations (Method B, load at the tooth tip),
    with the form factor Y_Fa and the stress correction factor Y_Sa. Spur teeth, so z_n = z and Y_beta = 1."""
    r = dict(REF, **(ref or {}))
    al = math.radians(alpha_deg)
    h_fP, rho_fP, s_pr = r["h_fP"], r["rho_fP"], r.get("s_pr", 0.0)
    G = rho_fP - h_fP + x
    E = (math.pi / 4.0) - h_fP * math.tan(al) + s_pr / math.cos(al) - (1.0 - math.sin(al)) * rho_fP / math.cos(al)
    H = (2.0 / z) * (math.pi / 2.0 - E) - math.pi / 3.0
    th = math.pi / 6.0
    for _ in range(80):
        nt = (2.0 * G / z) * math.tan(th) - H
        if abs(nt - th) < 1e-13:
            th = nt
            break
        th = nt
    s_Fn = z * math.sin(math.pi / 3.0 - th) + math.sqrt(3.0) * (G / math.cos(th) - rho_fP)
    rho_F = rho_fP + (2.0 * G * G) / (math.cos(th) * (z * math.cos(th) ** 2 - 2.0 * G))
    # load at the tooth tip
    d_b, d_a = z * m * math.cos(al), m * (z + 2.0 * (r["h_aP"] + x))
    al_a = math.acos(min(1.0, d_b / d_a))
    ga = (0.5 * math.pi + 2.0 * x * math.tan(al)) / z + _inv(al) - _inv(al_a)
    al_Fa = al_a - ga
    h_Fa = 0.5 * ((math.cos(ga) - math.sin(ga) * math.tan(al_Fa)) * (d_a / m)
                  - z * math.cos(math.pi / 3.0 - th) - G / math.cos(th) + rho_fP)
    Y_Fa = (6.0 * h_Fa) / (s_Fn ** 2 * math.cos(al_Fa) / math.cos(al))
    L = s_Fn / h_Fa
    q_s = s_Fn / (2.0 * rho_F)
    Y_Sa = (1.2 + 0.13 * L) * q_s ** (1.0 / (1.21 + 2.3 / L))
    return {"theta_deg": round(math.degrees(th), 3), "G": round(G, 5), "E": round(E, 6), "H": round(H, 6),
            "s_Fn_m": s_Fn, "rho_F_m": rho_F, "h_Fa_m": h_Fa, "q_s": round(q_s, 4), "L": round(L, 4),
            "alpha_Fa_deg": round(math.degrees(al_Fa), 3), "Y_Fa": round(Y_Fa, 4), "Y_Sa": round(Y_Sa, 4),
            "Y_FS": round(Y_Fa * Y_Sa, 4), "q_s_in_range": bool(1.0 <= q_s <= 8.0),
            "s_Fn": s_Fn * m, "rho_F": rho_F * m, "h_Fa": h_Fa * m}


def kv_agma(v_m_s: float, quality: int) -> tuple[float, str]:
    """AGMA 2001-D04 dynamic factor from the pitch-line speed and the quality grade Qv (6 commercial-cut,
    8 good hobbed and shaved, 10 ground). A rough, fast gear feels its own teeth as hammer blows."""
    qv = float(np.clip(quality, 5, 11))
    B = 0.25 * (12.0 - qv) ** 0.667
    A = 50.0 + 56.0 * (1.0 - B)
    v_max = (A + (qv - 3.0)) ** 2 / 200.0                     # the speed Qv is allowed up to
    kv = ((A + math.sqrt(200.0 * max(v_m_s, 0.0))) / A) ** B
    note = "" if v_m_s <= v_max else (f"{v_m_s:.1f} m/s is above the {v_max:.1f} m/s this Qv{int(qv)} quality is "
                                      "rated for - the gear must be cut finer (higher Qv) or run slower")
    return kv, note


def _khb(b_mm: float, d1_mm: float, stiff: str = "commercial") -> tuple[float, str]:
    """Face load factor K_Hbeta, ISO 6336-1 Method C simplified: a wide tooth on a bending shaft does not carry
    its load evenly. Rated by how the gear is mounted; her own measured number always wins."""
    base = {"rigid": 1.05, "good": 1.15, "commercial": 1.25, "overhung": 1.4, "poor": 1.6}.get(str(stiff).lower(), 1.25)
    k = base + 0.12 * max(0.0, b_mm / max(d1_mm, 1e-9) - 1.0)      # wider than its own diameter = worse
    return round(min(k, 2.2), 3), f"mounting '{stiff}', face/dia {b_mm / max(d1_mm, 1e-9):.2f}"


def pair(module: float, pinion_teeth: int, wheel_teeth: int, width_mm: float, torque_Nm: float, rpm: float,
         material: str = "steel", wheel_material: str | None = None, alpha_deg: float = 20.0,
         quality: int = 8, application: str = "uniform", life_hours: float = 20000.0, shift: float = 0.0,
         mounting: str = "commercial", min_sf: float = 1.4, ka: float | None = None, khb: float | None = None,
         sigma_flim: float | None = None, sigma_hlim: float | None = None) -> dict[str, Any]:
    """Will this gear pair live? Bending (ISO 6336-3) and pitting (ISO 6336-2) on the PINION, which is the one
    that gets hurt first: it sees every tooth more often and its teeth are smaller. torque_Nm and rpm are the
    PINION's. Returns the stresses, the safety factors and a row per check."""
    m, z1, z2 = float(module), int(pinion_teeth), int(wheel_teeth)
    b, T, n = float(width_mm), abs(float(torque_Nm)), abs(float(rpm))
    if min(z1, z2) < 6 or m <= 0 or b <= 0:
        raise GearError("gear pair: module, teeth (>= 6) and width must be real numbers")
    al = math.radians(alpha_deg)
    d1, d2 = m * z1, m * z2
    u = z2 / z1                                                 # gear ratio
    Ft = 2000.0 * T / d1                                        # tangential force at the pitch circle, N
    v = math.pi * d1 * n / 60000.0                              # pitch-line speed, m/s
    K_A = float(ka) if ka else APPLICATION.get(str(application).lower().strip(), 1.5)
    K_v, kv_note = kv_agma(v, quality)
    K_Hb, kh_note = (float(khb), "her number") if khb else _khb(b, d1, mounting)
    K_Fb = K_Hb ** 0.9                                          # ISO 6336-3: a little kinder than the flank factor
    K_a = 1.1                                                   # transverse load factor, spur, well-cut
    g1, sF1, sH1 = grade_for(material)
    g2, sF2, sH2 = grade_for(wheel_material or material)
    if sigma_flim:
        sF1 = sF2 = float(sigma_flim)
    if sigma_hlim:
        sH1 = sH2 = float(sigma_hlim)
    # ---- bending, the pinion
    iso = iso_root(m, z1, alpha_deg, shift)
    pr = profile(m, z1, alpha_deg, shift)
    meas = measured_root(pr)
    Y_FS = iso["Y_FS"]
    sigma_F0 = (Ft / (b * m)) * Y_FS
    sigma_F = sigma_F0 * K_A * K_v * K_Fb * K_a
    Y_NT, Y_ST = 1.0, 2.0                                       # 3e6 cycles reference, ISO's test-gear factor
    cycles = 60.0 * n * float(life_hours)
    if cycles < 1e5:                                            # ISO 6336-3 life factor, static to endurance
        Y_NT = 2.5
    elif cycles < 3e6:
        Y_NT = 2.5 * (1e5 / max(cycles, 1.0)) ** 0.1157 if cycles > 1e5 else 2.5
        Y_NT = max(1.0, min(2.5, 1.0 + 1.5 * (math.log10(3e6 / cycles) / math.log10(30.0))))
    sigma_FP = sF1 * Y_ST * Y_NT / 2.0                          # Y_ST / S_Fmin(=2.0 reference) folded in
    sf_bend = sigma_FP / max(sigma_F, 1e-9)
    # ---- pitting, the pinion flank
    al_wt = al                                                  # no centre-distance change: working angle = alpha
    Z_H = math.sqrt(2.0 * math.cos(al_wt) / (math.cos(al) ** 2 * math.sin(al_wt)))
    try:                                                        # the box imports flat, the server as a package
        from fea import material as _mat
    except ImportError:
        from .fea import material as _mat
    _n1, mt1 = _mat(material)
    _n2, mt2 = _mat(wheel_material or material)
    Z_E = math.sqrt(1.0 / (math.pi * ((1 - mt1["nu"] ** 2) / mt1["E"] + (1 - mt2["nu"] ** 2) / mt2["E"])))
    ra1, ra2, rb1, rb2 = d1 / 2 + m, d2 / 2 + m, d1 / 2 * math.cos(al), d2 / 2 * math.cos(al)
    a = (d1 + d2) / 2.0
    eps = (math.sqrt(max(ra1 ** 2 - rb1 ** 2, 0)) + math.sqrt(max(ra2 ** 2 - rb2 ** 2, 0)) - a * math.sin(al)) / \
        (math.pi * m * math.cos(al))                            # transverse contact ratio
    Z_eps = math.sqrt((4.0 - max(eps, 1.0)) / 3.0) if eps < 4 else 0.5
    sigma_H0 = Z_H * Z_E * Z_eps * math.sqrt(Ft / (d1 * b) * (u + 1.0) / u)
    sigma_H = sigma_H0 * math.sqrt(K_A * K_v * K_Hb * K_a)
    Z_NT = 1.0
    if cycles < 1e5:
        Z_NT = 1.6
    elif cycles < 5e7:
        Z_NT = max(1.0, min(1.6, 1.0 + 0.6 * (math.log10(5e7 / cycles) / math.log10(500.0))))
    sigma_HP = sH1 * Z_NT / 1.0
    sf_pit = sigma_HP / max(sigma_H, 1e-9)
    need = float(min_sf or 1.4)
    rows = [
        {"check": "Tooth bending (ISO 6336-3)", "measured": f"{sigma_F:.1f} MPa at the root",
         "limit": f"<= {sigma_FP:.0f} MPa ({g1}), safety {sf_bend:.2f} vs {need:g}",
         "ok": bool(sf_bend >= need),
         "fix": "a bigger module (the strongest single move: stress falls as 1/m²), a wider face, more teeth on the "
                "pinion, a profile shift, or a harder / case-hardened steel"},
        {"check": "Flank pitting (ISO 6336-2)", "measured": f"{sigma_H:.0f} MPa contact",
         "limit": f"<= {sigma_HP:.0f} MPa ({g1}), safety {sf_pit:.2f} vs {need:g}",
         "ok": bool(sf_pit >= need),
         "fix": "a bigger pitch diameter (more teeth or a bigger module), a wider face, or a case-hardened and "
                "ground flank - pitting is beaten by size and hardness, not by a tougher core"},
        {"check": "Contact ratio", "measured": f"{eps:.2f} teeth in mesh",
         "limit": ">= 1.2 (below 1.0 the drive stops and restarts every tooth)", "ok": bool(eps >= 1.2),
         "fix": "more teeth, a smaller pressure angle, or a longer addendum"},
    ]
    if kv_note:
        rows.append({"check": "Gear quality for this speed", "measured": f"{v:.2f} m/s, Qv{quality}", "limit": kv_note,
                     "ok": False, "fix": "cut the gear finer (Qv 8-10), or turn it slower"})
    if not iso["q_s_in_range"]:
        rows.append({"check": "Root notch sharpness (q_s)", "measured": f"q_s {iso['q_s']:.2f}",
                     "limit": "1 - 8 for ISO 6336 to hold", "ok": False,
                     "fix": "a different root fillet (hob tip radius) - outside this range the standard's stress "
                            "correction does not apply and this number must not be trusted"})
    assumed = [f"K_A {K_A:g} (drive: {application})" if not ka else f"K_A {K_A:g} (hers)",
               f"K_v {K_v:.3f} (Qv{quality} at {v:.2f} m/s)", f"K_Hbeta {K_Hb:g} ({kh_note})",
               f"allowables {g1}: bending {sF1:g} / pitting {sH1:g} MPa" + (" (hers)" if sigma_flim else " (ISO 6336-5 MQ)")]
    return {"ok": all(r["ok"] for r in rows), "rows": rows, "module": m, "pinion_teeth": z1, "wheel_teeth": z2,
            "width_mm": b, "ratio": round(u, 4), "d1_mm": round(d1, 3), "d2_mm": round(d2, 3),
            "tangential_N": round(Ft, 1), "speed_m_s": round(v, 3), "torque_Nm": T, "rpm": n,
            "bending_MPa": round(sigma_F, 2), "bending_allow_MPa": round(sigma_FP, 1), "bending_sf": round(sf_bend, 3),
            "contact_MPa": round(sigma_H, 1), "contact_allow_MPa": round(sigma_HP, 1), "pitting_sf": round(sf_pit, 3),
            "contact_ratio": round(eps, 4), "cycles": float(f"{cycles:.4g}"), "life_hours": float(life_hours),
            "need_sf": need, "material": g1, "wheel_material": g2,
            "factors": {"K_A": K_A, "K_v": round(K_v, 4), "K_Hbeta": K_Hb, "K_Fbeta": round(K_Fb, 4), "K_alpha": K_a,
                        "Y_Fa": iso["Y_Fa"], "Y_Sa": iso["Y_Sa"], "Y_NT": round(Y_NT, 3), "Z_H": round(Z_H, 4),
                        "Z_E": round(Z_E, 1), "Z_eps": round(Z_eps, 4), "Z_NT": round(Z_NT, 3)},
            "root": {"from_the_standard": {k: iso[k] for k in ("s_Fn", "rho_F", "h_Fa", "q_s", "theta_deg")},
                     "measured_on_the_tooth": {"s_Fn": round(meas["s_Fn"], 4), "rho_F": round(meas["rho_F"], 4),
                                               "h_Fa": round(meas["h_Fa"], 4), "at_mm": meas["at_mm"]}},
            "assumed": assumed,
            "note": "ISO 6336 Method B/C on straight spur teeth, the pinion checked (it fails first). No scuffing "
                    "or micropitting check, no helix / bevel / worm. DRAFT for an engineer's signature."}
