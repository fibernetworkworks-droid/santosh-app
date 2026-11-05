"""Lab pack: the Class XI-XII mechanics / properties-of-matter / heat set-ups of the NCERT laboratory manual that the
first 22 labs did not cover. Physics lives in `app/prayog/packs/mech11.py` (with its JavaScript twin); the studio rigs
live in `app/static/prayog/exp/<rig>.js`. Several labs share one rig through the `rig` field.

Sources for every constant are named on each lab (`sources`) and in the family files beside it.
"""
from __future__ import annotations

import math

from ..catalog import B, S11, SIM, col, inst, knob, lab

DEG = math.pi / 180
CRC = {"title": "CRC Handbook of Chemistry and Physics",
       "note": "surface tension of water, specific heats, Young's modulus and expansion coefficients"}
SWG = {"title": "BS 3737 standard wire gauge table", "note": "nominal diameters of the wires used"}
WOOD = {"title": "USDA Forest Service, Wood Handbook (Wood as an Engineering Material)",
        "note": "modulus of elasticity of wood along the grain"}


# =============================================================================== surface tension by capillary rise
def _capillary_bodies(liquid: str) -> list[dict]:
    return [
        B("bench", "box", name="Wooden board", size=[0.5, 0.02, 0.3], pos=[0, -0.01, 0], color="wood", cut=False),
        B("trough", "cylinder", name="Glass trough", info="Holds the liquid the capillary tube dips into.",
          r=0.055, h=0.04, open=True, pos=[0, 0.02, 0], color="glass", opacity=0.3),
        B("liq", "cylinder", name=liquid, r=0.052, h=0.03, pos=[0, 0.015, 0], color=("water" if liquid.startswith("Water") else "glycerine")),
        B("stand", "box", name="Stand base", size=[0.16, 0.02, 0.12], pos=[-0.13, 0.01, -0.02], color="#2b3138"),
        B("rod", "cylinder", name="Stand rod", r=0.008, h=0.34, pos=[-0.13, 0.19, -0.02], color="steel"),
        B("arm", "box", size=[0.1, 0.012, 0.012], pos=[-0.08, 0.23, -0.02], color="steel"),
        B("clamp", "box", name="Clamp", info="Holds the capillary tube upright.", size=[0.022, 0.022, 0.022],
          pos=[-0.035, 0.23, -0.02], color="black"),
        B("tube", "cylinder", name="Capillary tube", info="A fine glass tube. The narrower the bore, the higher the liquid climbs.",
          r=0.0025, h=0.2, pos=[-0.035, 0.12, -0.02], color="glass", opacity=0.4),
        B("col", "cylinder", name="Liquid column", info="The liquid stands higher inside the tube than outside: that is the rise h.",
          r=0.0018, h=1.0, pos=[-0.035, 0.03, -0.02], color="water",
          bind={"sy": {"var": "h", "k": 1.0, "min": 0.001}, "y": {"var": "h", "k": 0.5, "c": 0.03}}),
        B("micro", "box", name="Travelling microscope (pillar)", info="Its carriage slides up and down against a vernier scale.",
          size=[0.03, 0.26, 0.03], pos=[0.11, 0.13, -0.04], color="#2b3138"),
        B("mscale", "scale", name="Vertical scale (cm)", length=0.22, spacing=0.001, major=10, labels=True,
          label_step=10, tick=0.008, font=0.012, pos=[0.126, 0.03, -0.024]),
        B("mtube", "cylinder", name="Microscope tube", r=0.012, h=0.09, pos=[0.055, 0.12, -0.04], rot=[0, 0, 1.5708], color="black"),
        B("lbl", "text", text="h", size=0.016, pos=[-0.01, 0.1, -0.02]),
    ]


def _capillary(lab_id: str, title: str, aim: str, T: float, r: float, liquid: str, rig: str | None,
               extra_sources: list[dict], theory_tail: str, chapter: str) -> dict:
    d = lab(
        id=lab_id, title=title, group="Physics · Properties of matter", level="Class XI",
        topic="Mechanical Properties of Fluids", chapter=chapter, aim=aim,
        kernel="capillary", params={"T": T, "r": r, "rho": 998.2, "theta": 0.0}, autorun=True,
        camera={"pos": [0.12, 0.2, 0.42], "look": [-0.02, 0.08, -0.02]}, floor=-0.02,
        bodies=_capillary_bodies(liquid),
        knobs=[knob("tube", "Capillary tube (bore radius r)", "r", 0.15, 0.6, 0.05, round(r * 1000, 3), "mm", 0.001,
                    hint="Each tube's bore is measured with the microscope and printed on it."),
               knob("T", "Liquid (surface tension hidden)", "T", 0.02, 0.085, 0.0005, T, "N/m", hidden=True)],
        instruments=[inst("h", "readout", "Rise of the liquid h", "h_cm", unit="cm", lc=0.001, digits=3),
                     inst("heq", "readout", "Settled rise (help)", "heq", k=100, unit="cm", digits=3, hint=True),
                     inst("gr", "graph", "Rise against time", "h_cm", xlabel="t (s)")],
        table={"columns": [col("r", "Bore radius r", "knob:tube", "mm", 0.001, digits=2),
                           col("h", "Rise h", "inst:h", "cm", 0.01, digits=3)],
               "calc": "cap_T", "rows_min": 2, "truth": "p.T", "result_digits": 4,
               "hint": "For each tube: let the meniscus settle, read the meniscus and the liquid surface, record h."},
        steps=["Dip the capillary tube in the liquid and wait for the meniscus to settle.",
               "Focus the travelling microscope on the lowest point of the meniscus and read the scale.",
               "Read the scale for the liquid surface in the trough. h is the difference.",
               "Repeat with tubes of two more bores.", "T = h r ρ g / 2 for each tube; take the mean."],
        theory="A liquid that wets glass climbs a fine tube until the upward pull of surface tension round the circle of "
               "contact, 2πrT cosθ, balances the weight of the raised column, πr²hρg. So h = 2T cosθ / (rρg): a narrower "
               "bore gives a higher rise. " + theory_tail,
        safety="Glass capillary tubes break easily. Clean the tube and the trough: grease changes the rise badly.",
        tour=[{"say": "A fine glass tube dips into the liquid. The liquid has climbed inside it, well above the level outside."},
              {"set": {"tube": 0.15}, "say": "A narrower tube: the liquid climbs higher, because h goes as 1 / r."},
              {"set": {"tube": 0.5}, "say": "A wide tube: only a small rise. Now record h for each bore in the Table."}],
        questions=[{"q": "If the bore radius is halved, the rise h becomes", "options": ["Twice as much", "Half", "Unchanged", "Four times"],
                    "answer": 0, "why": "h = 2T cosθ / (rρg), so h is inversely proportional to r."},
                   {"q": "Why must the tube be clean?", "options": ["Grease changes the angle of contact and the rise",
                                                                    "Dirt makes the tube heavier", "Dirt blocks the light"],
                    "answer": 0, "why": "A greasy tube is not wetted, so cosθ and the rise both change."}],
        sources=[S11, SIM] + extra_sources,
        check={"params": {"r": 0.00025}, "reading": "h", "textbook": "cap_h"},
    )
    if rig:
        d["rig"] = rig
    return d


def capillary_rise() -> dict:
    return _capillary(
        "capillary-rise", "Surface tension of water by capillary rise",
        "Measure the rise of water in capillary tubes of different bore and work out the surface tension of water.",
        0.07275, 0.00025, "Water", None, [CRC],
        "The surface tension of clean water against air is 72.8 mN/m at 20 °C.", "Mechanical Properties of Fluids")


def detergent_capillary() -> dict:
    d = _capillary(
        "detergent-capillary", "Effect of a detergent on surface tension",
        "Measure the capillary rise in water, then in water with a detergent, and see how the surface tension changes.",
        0.0300, 0.00025, "Water with detergent", "capillary-rise",
        [{"title": "NCERT Laboratory Manual Physics Class XI, Section B, Activities",
          "note": "effect of a detergent on the surface tension of water, observed by capillary rise"}],
        "A detergent is a surface-active substance: its molecules crowd into the surface and lower the surface tension, "
        "so the same tube lifts a shorter column.", "Mechanical Properties of Fluids")
    d["steps"] = ["Measure the rise h in clean water first (the other experiment on this bench).",
                  "Add a drop of detergent, stir, and dip the same tube again.",
                  "Read the new, smaller rise with the travelling microscope.",
                  "Repeat with two more bores.", "Work out T for the detergent solution and compare it with water."]
    return d


BUILDERS = (capillary_rise, detergent_capillary)
