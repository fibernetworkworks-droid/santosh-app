"""IS 1200 measurement formulae as a pure library (v0.531.0, Wave 2 C8 - plan docs/CONSTRUCTION_EMPLOYEE_PLAN.md
§7 C8). Every function returns the SAME trail shape: {qty, unit, formula, inputs, is_ref} - the quantity,
the rule it came from and exactly the inputs fed in. A recompute feeds the stored inputs back through the
same function and must reproduce the number bit-for-bit (the trail law; tested).

Honest limits, said on every output:
- document-level, PDF/DWG-first: the DIMENSIONS here are read by a human (or the vision model in chat) off
  the drawing - Hoola does the rule arithmetic on them; it never claims a model-level take-off.
- measurement CERTIFICATION is the billing engineer's act (tier C, construction/gates.py). This library
  prepares; it never certifies.

Only parts with rules Hoola can state without guessing are here:
- Part 1  earthwork: L x B x D, lead/lift recorded as fed.
- Part 2  concrete: net volume, openings/fittings up to 0.1 m2 are NOT deducted.
- Part 3  brickwork: L x H x T, openings above 0.1 m2 deducted (thickness x area).
- Part 5  formwork: the contact area of the surface shuttered, L x H.
- Part 8  steelwork: weight by length x unit weight; the bar identity d^2/162 kg/m derives from
          pi/4 x d^2 x 7850 kg/m3 (physics, not a notification).
- Part 12 plaster & pointing: openings up to 0.5 m2 not deducted; 0.5-3 m2 half deducted (jambs
          compensate); above 3 m2 fully deducted, jambs measured separately.

Anything else (DPC, painting, flooring, horticulture...) is not here until its rule is stated - an
absent formula refuses, it never improvises."""
from __future__ import annotations

import math

TRAIL_KEYS = ("qty", "unit", "formula", "inputs", "is_ref")


def _trail(qty: float, unit: str, formula: str, inputs: dict, is_ref: str) -> dict:
    """One trail dict: the number, its rule, its inputs - round(3) is the stored precision."""
    q = round(float(qty), 3)
    return {"qty": q, "unit": unit, "formula": formula, "inputs": {k: v for k, v in inputs.items() if v is not None},
            "is_ref": is_ref}


# ---------------------------------------------------------------- the library (kind -> (fn, label))
def earthwork(length: float, breadth: float, depth: float, lead_m: float = 0.0, lift_m: float = 0.0) -> dict:
    """IS 1200 (Part 1) earthwork: L x B x D in m3; lead & lift recorded as fed, never assumed."""
    ins = {"length": length, "breadth": breadth, "depth": depth, "lead_m": lead_m, "lift_m": lift_m}
    if length <= 0 or breadth <= 0 or depth <= 0:
        raise ValueError("Earthwork ke liye length, breadth, depth - teeno positive chahiye.")
    f = "L x B x D" + (f" | lead {lead_m:g} m, lift {lift_m:g} m (recorded as fed)" if lead_m or lift_m else "")
    return _trail(length * breadth * depth, "m3", f, ins, "IS 1200 (Part 1) earthwork")


def concrete(length: float, breadth: float, depth: float, openings_m2: float = 0.0) -> dict:
    """IS 1200 (Part 2) concrete: net volume; openings / fittings up to 0.1 m2 are NOT deducted."""
    ins = {"length": length, "breadth": breadth, "depth": depth, "openings_m2": openings_m2}
    if length <= 0 or breadth <= 0 or depth <= 0:
        raise ValueError("Concrete ke liye length, breadth, depth - teeno positive chahiye.")
    gross = length * breadth * depth
    if openings_m2 > 0.1:
        net = gross - openings_m2 * depth
        f = f"L x B x D - openings {openings_m2:g} m2 x depth (> 0.1 m2 deducted)"
    else:
        net = gross
        f = "L x B x D (openings <= 0.1 m2 - koi katauti nahi)"
    return _trail(max(net, 0.0), "m3", f, ins, "IS 1200 (Part 2) concrete")


def brickwork(length: float, height: float, thickness: float, openings_m2: float = 0.0) -> dict:
    """IS 1200 (Part 3) brickwork: L x H x T in m3; openings above 0.1 m2 deducted (area x thickness)."""
    ins = {"length": length, "height": height, "thickness": thickness, "openings_m2": openings_m2}
    if length <= 0 or height <= 0 or thickness <= 0:
        raise ValueError("Brickwork ke liye length, height, thickness - teeno positive chahiye.")
    gross = length * height * thickness
    if openings_m2 > 0.1:
        net = gross - openings_m2 * thickness
        f = f"L x H x T - openings {openings_m2:g} m2 x T (> 0.1 m2 deducted)"
    else:
        net = gross
        f = "L x H x T (openings <= 0.1 m2 - koi katauti nahi)"
    return _trail(max(net, 0.0), "m3", f, ins, "IS 1200 (Part 3) brickwork")


def plaster(length: float, height: float, openings_m2: float = 0.0) -> dict:
    """IS 1200 (Part 12) plaster: L x H in m2; openings <= 0.5 m2 no deduction; 0.5-3 m2 HALF
    deducted (jambs compensate); above 3 m2 fully deducted (jambs measured separately)."""
    ins = {"length": length, "height": height, "openings_m2": openings_m2}
    if length <= 0 or height <= 0:
        raise ValueError("Plaster ke liye length aur height positive chahiye.")
    area = length * height
    if openings_m2 <= 0.5:
        net, f = area, "L x H (openings <= 0.5 m2 - koi katauti nahi)"
    elif openings_m2 <= 3.0:
        net = area - openings_m2 * 0.5
        f = f"L x H - 50% of openings {openings_m2:g} m2 (jambs compensate)"
    else:
        net = area - openings_m2
        f = f"L x H - openings {openings_m2:g} m2 full (jambs alag naape jaate hain)"
    return _trail(max(net, 0.0), "m2", f, ins, "IS 1200 (Part 12) plaster & pointing")


def formwork(length: float, height: float) -> dict:
    """IS 1200 (Part 5) formwork: the contact area actually shuttered, L x H in m2."""
    ins = {"length": length, "height": height}
    if length <= 0 or height <= 0:
        raise ValueError("Formwork ke liye length aur height positive chahiye.")
    return _trail(length * height, "m2", "L x H (contact area)", ins, "IS 1200 (Part 5) formwork")


BAR_D2_162 = 162.0   # kg/m: pi/4 * d^2 * 7850 kg/m3 = d^2 * 0.6165... x 10^-3; the site identity d^2/162


def steel_weight(length_m: float, dia_mm: float, nos: float = 1.0) -> dict:
    """IS 1200 (Part 8) steelwork: n x L x d^2/162 kg - the identity shown in the formula string."""
    ins = {"length_m": length_m, "dia_mm": dia_mm, "nos": nos}
    if length_m <= 0 or dia_mm <= 0 or nos <= 0:
        raise ValueError("Steel ke liye length, dia, nos - sab positive chahiye.")
    w = nos * length_m * dia_mm * dia_mm / BAR_D2_162
    return _trail(w, "kg", f"{nos:g} x {length_m:g} m x {dia_mm:g}^2 / 162 (pi/4 x d^2 x 7850 kg/m3)", ins,
                  "IS 1200 (Part 8) steelwork")


def bbs(bars: list) -> dict:
    """Bar-bending schedule DRAFT (#73): rows {shape, dia, length, nos} -> per-row weight (Part 8
    identity) + the total. A DRAFT for the site engineer to check against the drawing - the
    structural designer's sign stays where it always was."""
    rows, total = [], 0.0
    for i, b in enumerate(bars or []):
        if not isinstance(b, dict):
            raise ValueError(f"bar #{i + 1} samajh nahi aayi ({{shape, dia, length, nos}} bhejo).")
        w = steel_weight(_n(b.get("length")), _n(b.get("dia")), _n(b.get("nos"), 1.0))
        rows.append({"shape": str(b.get("shape", ""))[:60], "dia": _n(b.get("dia")),
                     "length": _n(b.get("length")), "nos": _n(b.get("nos"), 1.0),
                     "weight_kg": w["qty"], "formula": w["formula"]})
        total += w["qty"]
    if not rows:
        raise ValueError("BBS ke liye bars bhejo [{shape, dia, length, nos}].")
    return {"rows": rows, "total_kg": round(total, 2), "qty": round(total, 3), "unit": "kg",
            "formula": "sum of n x L x d^2/162 per row", "inputs": {"bars": len(rows)},
            "is_ref": "IS 1200 (Part 8) steelwork; shapes per SP 34",
            "say": f"BBS DRAFT: {len(rows)} bar types, total {total:,.1f} kg. Site engineer drawing se check "
                   "karega - yeh working paper hai, schedule ka final check usi ka."}


def _n(v, default=0.0) -> float:
    try:
        f = float(str(v).replace(",", "").strip())
        return f
    except (TypeError, ValueError):
        return default


# kind -> (fn, the arg names the tool schema advertises)
LIBRARY: dict[str, tuple] = {
    "earthwork": (earthwork, ("length", "breadth", "depth", "lead_m", "lift_m")),
    "concrete": (concrete, ("length", "breadth", "depth", "openings_m2")),
    "brickwork": (brickwork, ("length", "height", "thickness", "openings_m2")),
    "plaster": (plaster, ("length", "height", "openings_m2")),
    "formwork": (formwork, ("length", "height")),
    "steel": (steel_weight, ("length_m", "dia_mm", "nos")),
}

KINDS = ", ".join(sorted(LIBRARY))


def compute(kind: str, params: dict) -> dict:
    """Dispatch one take-off through the library; an unknown kind refuses with the menu."""
    fn = LIBRARY.get((kind or "").strip().lower())
    if fn is None:
        raise ValueError(f"Yeh formula library mein nahi hai ({KINDS}). Jo nahi hai woh refuse hota hai - "
                         "guess nahi karta; rule ke saath batao to pack jud jayega.")
    f, keys = fn
    return f(**{k: _n(params.get(k)) for k in keys})


def recompute(trail: dict) -> float:
    """The trail law: stored inputs through the same formula - the SAME float, bit-for-bit."""
    fn = LIBRARY.get((trail.get("kind") or "").strip().lower())
    if fn is None:
        raise ValueError("trail ka kind library mein nahi")
    f, keys = fn
    out = f(**{k: _n((trail.get("inputs") or {}).get(k)) for k in keys})
    return out["qty"]
