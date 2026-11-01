"""v0.365 HOOLA ENGINEERING CALCULATOR: the hand calculations an engineer checks a design with, done exactly.

fit       ISO 286 hole-basis fits (H6-H11 with f, g, h, js, k, m, n, p shafts, 1-500 mm): limits + clearance / interference
stack     tolerance stack-up: worst case, RSS and a Monte-Carlo (100,000 builds) with % outside her limits
bolt      ISO 898-1 bolts M3-M24, grades 4.6-12.9: tensile area, proof load, preload (75 %), tightening torque, shear
          and tension utilisation per bolt (EN 1993-1-8 resistances)
weld      fillet weld (EN 1993-1-8 simplified directional-free method): throat, stress, utilisation
beam      cantilever / simply supported, point or uniform load, rect / round / tube / I section: deflection + stress
pipe      pipe / duct flow (Darcy-Weisbach, Swamee-Jain friction): velocity, Reynolds, pressure drop, regime
Pure Python, no network; every result carries its formula + DRAFT note (a qualified engineer signs, never Hoola)."""
from __future__ import annotations

import math
import random
from typing import Any

NOTE = "Hand calculation by Hoola - DRAFT, for a qualified engineer's review, not certified."

_RANGES = [3, 6, 10, 18, 30, 50, 80, 120, 180, 250, 315, 400, 500]
IT = {5: [4, 5, 6, 8, 9, 11, 13, 15, 18, 20, 23, 25, 27],
      6: [6, 8, 9, 11, 13, 16, 19, 22, 25, 29, 32, 36, 40],
      7: [10, 12, 15, 18, 21, 25, 30, 35, 40, 46, 52, 57, 63],
      8: [14, 18, 22, 27, 33, 39, 46, 54, 63, 72, 81, 89, 97],
      9: [25, 30, 36, 43, 52, 62, 74, 87, 100, 115, 130, 140, 155],
      10: [40, 48, 58, 70, 84, 100, 120, 140, 160, 185, 210, 230, 250],
      11: [60, 75, 90, 110, 130, 160, 190, 220, 250, 290, 320, 360, 400]}
# shaft fundamental deviation, µm: upper (es) for f g h, lower (ei) for k m n p
SHAFT_ES = {"f": [-6, -10, -13, -16, -20, -25, -30, -36, -43, -50, -56, -62, -68],
            "g": [-2, -4, -5, -6, -7, -9, -10, -12, -14, -15, -17, -18, -20], "h": [0] * 13}
SHAFT_EI = {"k": [0, 1, 1, 1, 2, 2, 2, 3, 3, 4, 4, 4, 5], "m": [2, 4, 6, 7, 8, 9, 11, 13, 15, 17, 20, 21, 23],
            "n": [4, 8, 10, 12, 15, 17, 20, 23, 27, 31, 34, 37, 40], "p": [6, 12, 15, 18, 22, 26, 32, 37, 43, 50, 56, 62, 68]}


class CalcError(Exception):
    pass


def _ri(d: float) -> int:
    if not (0 < d <= 500):
        raise CalcError("size 0-500 mm")
    return next(i for i, top in enumerate(_RANGES) if d <= top)


def fit(size: float, fit: str = "H7/g6") -> dict[str, Any]:
    import re
    m = re.fullmatch(r"\s*H(\d{1,2})\s*/\s*(js|[fghkmnp])(\d{1,2})\s*", str(fit))
    if not m:
        raise CalcError("fit like H7/g6, H7/h6, H7/k6, H7/p6, H8/f7 (hole basis H)")
    hg, sl, sg = int(m.group(1)), m.group(2), int(m.group(3))
    if hg not in IT or sg not in IT:
        raise CalcError("grades 5-11")
    i = _ri(float(size))
    th, ts = IT[hg][i], IT[sg][i]
    hole = (0.0, th / 1000)
    if sl in SHAFT_ES:
        es = SHAFT_ES[sl][i]
        shaft = ((es - ts) / 1000, es / 1000)
    elif sl == "js":
        shaft = (-ts / 2000, ts / 2000)
    else:
        ei = SHAFT_EI[sl][i] if not (sl == "k" and sg > 7) else 0
        shaft = (ei / 1000, (ei + ts) / 1000)
    cmax = hole[1] - shaft[0]
    cmin = hole[0] - shaft[1]
    kind = "clearance" if cmin >= 0 else "interference" if cmax <= 0 else "transition"
    use = {"clearance": "parts slide / turn (running or sliding fit)", "transition": "located, light press or tap fit",
           "interference": "press fit - parts stay together, needs a press or heating"}[kind]
    return {"fit": f"H{hg}/{sl}{sg}", "size_mm": size, "kind": kind, "use": use,
            "hole_mm": [round(size + hole[0], 4), round(size + hole[1], 4)],
            "shaft_mm": [round(size + shaft[0], 4), round(size + shaft[1], 4)],
            "clearance_mm": [round(cmin, 4), round(cmax, 4)], "standard": "ISO 286-1/-2", "note": NOTE}


def stack(chain: list[dict[str, Any]], lower: float | None = None, upper: float | None = None,
          runs: int = 100000, seed: int = 7) -> dict[str, Any]:
    """chain: [{name, nominal, plus, minus (positive number), dir: +1 / -1}] adding up to the gap."""
    if not chain or len(chain) > 60:
        raise CalcError("chain: 1-60 dimensions")
    nom = wc_lo = wc_hi = 0.0
    var = 0.0
    rows = []
    for d in chain:
        n = float(d["nominal"])
        p = abs(float(d.get("plus", d.get("tol", 0))))
        mi = abs(float(d.get("minus", d.get("tol", p))))
        s = 1 if float(d.get("dir", 1)) >= 0 else -1
        nom += s * n
        wc_hi += s * n + (p if s > 0 else mi)
        wc_lo += s * n - (mi if s > 0 else p)
        mean_shift = (p - mi) / 2
        var += ((p + mi) / 6) ** 2
        rows.append({"name": d.get("name", ""), "contrib_pct": 0.0, "_t": (p + mi), "_sh": s * mean_shift})
    mean = nom + sum(r["_sh"] for r in rows)
    sd = math.sqrt(var)
    tot = sum(r["_t"] ** 2 for r in rows) or 1
    for r in rows:
        r["contrib_pct"] = round(100 * r["_t"] ** 2 / tot, 1)
        r.pop("_t")
        r.pop("_sh")
    rnd = random.Random(seed)
    n_out = 0
    runs = max(1000, min(int(runs), 200000))
    sims = []
    for _ in range(runs):
        g = 0.0
        for d in chain:
            p = abs(float(d.get("plus", d.get("tol", 0))))
            mi = abs(float(d.get("minus", d.get("tol", p))))
            s = 1 if float(d.get("dir", 1)) >= 0 else -1
            mu = float(d["nominal"]) + (p - mi) / 2
            g += s * rnd.gauss(mu, (p + mi) / 6)
        sims.append(g)
        if (lower is not None and g < lower) or (upper is not None and g > upper):
            n_out += 1
    sims.sort()
    out = {"nominal": round(nom, 4), "worst_case": [round(wc_lo, 4), round(wc_hi, 4)],
           "rss": [round(mean - 3 * sd, 4), round(mean + 3 * sd, 4)],
           "monte_carlo": {"runs": runs, "p0_135": round(sims[int(0.00135 * runs)], 4),
                           "p99_865": round(sims[int(0.99865 * runs) - 1], 4),
                           "outside_pct": round(100 * n_out / runs, 3) if (lower is not None or upper is not None) else None},
           "limits": [lower, upper], "contributors": rows, "note": NOTE}
    if lower is not None or upper is not None:
        out["worst_case_ok"] = (lower is None or wc_lo >= lower) and (upper is None or wc_hi <= upper)
        if sd > 0:
            lim = [x for x in ((mean - lower) / (3 * sd) if lower is not None else None,
                               (upper - mean) / (3 * sd) if upper is not None else None) if x is not None]
            out["cpk"] = round(min(lim), 2)
    return out


AS = {3: 5.03, 4: 8.78, 5: 14.2, 6: 20.1, 8: 36.6, 10: 58.0, 12: 84.3, 14: 115, 16: 157, 18: 192, 20: 245, 22: 303, 24: 353}
GRADES = {"4.6": (400, 240, 225), "5.8": (500, 400, 380), "8.8": (800, 640, 600), "10.9": (1000, 900, 830),
          "12.9": (1200, 1080, 970)}   # fub, fyb, proof stress Sp (M>16 for 8.8; 580 at <=M16)


def bolt(m: float, grade: str = "8.8", count: int = 1, shear_N: float = 0.0, tension_N: float = 0.0,
         k: float = 0.2, shear_planes: int = 1) -> dict[str, Any]:
    m = int(m) if float(m).is_integer() else m
    if m not in AS:
        raise CalcError(f"bolt M{m} table mein nahi ({', '.join(f'M{x}' for x in AS)})")
    if grade not in GRADES:
        raise CalcError(f"grade {', '.join(GRADES)}")
    fub, fyb, sp = GRADES[grade]
    if grade == "8.8" and m <= 16:
        sp = 580
    a_s = AS[m]
    proof = sp * a_s
    preload = 0.75 * proof
    torque = k * preload * m / 1000
    ft_rd = 0.9 * fub * a_s / 1.25
    fv_rd = (0.6 if grade in ("4.6", "5.8", "8.8") else 0.5) * fub * a_s / 1.25 * max(1, int(shear_planes))
    n = max(1, int(count))
    v, t = float(shear_N) / n, float(tension_N) / n
    u_v, u_t = v / fv_rd, t / ft_rd
    u = u_v + u_t / 1.4
    return {"bolt": f"M{m} grade {grade}", "count": n, "tensile_area_mm2": a_s, "proof_load_N": round(proof),
            "preload_N": round(preload), "torque_Nm": round(torque, 1), "shear_resistance_N": round(fv_rd),
            "tension_resistance_N": round(ft_rd), "per_bolt": {"shear_N": round(v, 1), "tension_N": round(t, 1)},
            "utilisation": round(u, 3), "ok": u <= 1.0, "standard": "ISO 898-1, EN 1993-1-8 Table 3.4",
            "formula": "T = K·F·d, Fv,Rd = αv·fub·As/γM2, Ft,Rd = 0.9·fub·As/γM2, Fv/Fv,Rd + Ft/(1.4·Ft,Rd) <= 1",
            "note": NOTE}


def weld(force_N: float, length_mm: float, leg_mm: float = 0.0, throat_mm: float = 0.0,
         fu: float = 360, beta_w: float = 0.8, gamma: float = 1.25) -> dict[str, Any]:
    a = float(throat_mm) or 0.707 * float(leg_mm)
    if a <= 0 or length_mm <= 0:
        raise CalcError("leg_mm (ya throat_mm) aur length_mm do")
    l_eff = max(float(length_mm) - 2 * a, 0.0)
    if l_eff <= 0:
        raise CalcError("weld bahut chhota hai")
    tau = float(force_N) / (a * l_eff)
    f_vw = fu / (math.sqrt(3) * beta_w * gamma)
    return {"throat_mm": round(a, 3), "effective_length_mm": round(l_eff, 2), "stress_MPa": round(tau, 2),
            "design_strength_MPa": round(f_vw, 1), "utilisation": round(tau / f_vw, 3), "ok": tau <= f_vw,
            "standard": "EN 1993-1-8 4.5.3.3 (simplified method), S235 default",
            "formula": "τ = F / (a·(L - 2a)), fvw,d = fu / (√3·βw·γM2)", "note": NOTE}


def _section(sec: dict[str, Any]) -> tuple[float, float, float, str]:
    """(I mm^4, c mm, area mm², label)"""
    k = str(sec.get("type", "rect")).lower()
    if k == "rect":
        b, h = float(sec["b"]), float(sec["h"])
        return b * h ** 3 / 12, h / 2, b * h, f"rect {b:g} x {h:g}"
    if k == "round":
        d = float(sec["d"])
        return math.pi * d ** 4 / 64, d / 2, math.pi * d * d / 4, f"round Ø{d:g}"
    if k == "tube":
        D, t = float(sec["d"]), float(sec["t"])
        di = D - 2 * t
        return math.pi * (D ** 4 - di ** 4) / 64, D / 2, math.pi * (D * D - di * di) / 4, f"tube Ø{D:g} x {t:g}"
    if k == "rect_tube":
        b, h, t = float(sec["b"]), float(sec["h"]), float(sec["t"])
        return (b * h ** 3 - (b - 2 * t) * (h - 2 * t) ** 3) / 12, h / 2, b * h - (b - 2 * t) * (h - 2 * t), f"box {b:g}x{h:g}x{t:g}"
    if k == "i":
        b, h, tw, tf = float(sec["b"]), float(sec["h"]), float(sec["tw"]), float(sec["tf"])
        return (b * h ** 3 - (b - tw) * (h - 2 * tf) ** 3) / 12, h / 2, 2 * b * tf + (h - 2 * tf) * tw, f"I {h:g}x{b:g}"
    raise CalcError("section type: rect / round / tube / rect_tube / i")


def beam(support: str, length_mm: float, section: dict[str, Any], load_N: float = 0.0, udl_N_per_mm: float = 0.0,
         material: str = "steel") -> dict[str, Any]:
    from .fea import material as _mat
    mname, mat = _mat(material)
    E = mat["E"]
    I, c, A, lab = _section(section)
    L, P, w = float(length_mm), float(load_N), float(udl_N_per_mm)
    if support == "cantilever":
        defl = P * L ** 3 / (3 * E * I) + w * L ** 4 / (8 * E * I)
        M = P * L + w * L * L / 2
        f1k = 1.875 ** 2
    elif support in ("simple", "simply_supported"):
        defl = P * L ** 3 / (48 * E * I) + 5 * w * L ** 4 / (384 * E * I)
        M = P * L / 4 + w * L * L / 8
        f1k = math.pi ** 2
    elif support == "fixed_fixed":
        defl = P * L ** 3 / (192 * E * I) + w * L ** 4 / (384 * E * I)
        M = P * L / 8 + w * L * L / 12
        f1k = 4.730 ** 2
    else:
        raise CalcError("support: cantilever / simple / fixed_fixed")
    sigma = M * c / I
    f1 = f1k / (2 * math.pi * L * L) * math.sqrt(E * I / (mat["rho"] * A))
    return {"support": support, "section": lab, "material": mname, "I_mm4": round(I, 1), "max_deflection_mm": round(defl, 4),
            "max_moment_Nmm": round(M, 1), "max_bending_stress_MPa": round(sigma, 2),
            "safety_factor": round(mat["yield"] / sigma, 2) if sigma > 0 else None, "first_natural_hz": round(f1, 1),
            "deflection_ratio": f"L/{L / defl:.0f}" if defl > 0 else None,
            "formula": "Euler-Bernoulli beam tables; σ = M·c/I; f1 = λ²/(2πL²)·√(EI/ρA)", "note": NOTE}


FLUIDS = {"water": (998.0, 1.0e-3), "air": (1.204, 1.81e-5), "oil": (870.0, 0.087), "diesel": (832.0, 2.4e-3)}


def pipe(flow_lpm: float, diameter_mm: float, length_m: float, fluid: str = "water", roughness_mm: float = 0.045,
         fittings_k: float = 0.0) -> dict[str, Any]:
    if fluid not in FLUIDS:
        raise CalcError(f"fluid: {', '.join(FLUIDS)}")
    rho, mu = FLUIDS[fluid]
    q = float(flow_lpm) / 60000.0
    d = float(diameter_mm) / 1000.0
    a = math.pi * d * d / 4
    v = q / a
    re = rho * v * d / mu
    if re < 2300:
        f = 64 / max(re, 1e-9)
        regime = "laminar"
    else:
        f = 0.25 / math.log10(float(roughness_mm) / 1000 / (3.7 * d) + 5.74 / re ** 0.9) ** 2
        regime = "turbulent" if re > 4000 else "transitional (uncertain)"
    dp = (f * float(length_m) / d + float(fittings_k)) * rho * v * v / 2
    return {"velocity_m_s": round(v, 3), "reynolds": round(re), "regime": regime, "friction_factor": round(f, 5),
            "pressure_drop_Pa": round(dp, 1), "pressure_drop_bar": round(dp / 1e5, 4),
            "head_loss_m": round(dp / (rho * 9.81), 3), "pump_power_W": round(dp * q, 1),
            "formula": "ΔP = (f·L/D + ΣK)·ρv²/2, Swamee-Jain f", "note": NOTE}


def run(kind: str, args: dict[str, Any]) -> dict[str, Any]:
    fns = {"fit": fit, "stack": stack, "bolt": bolt, "weld": weld, "beam": beam, "pipe": pipe}
    if kind not in fns:
        raise CalcError(f"calc: {', '.join(fns)}")
    try:
        return fns[kind](**(args or {}))
    except CalcError:
        raise
    except (TypeError, KeyError, ValueError) as e:
        raise CalcError(f"{kind}: {type(e).__name__}: {e}")
