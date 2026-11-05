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


# ============================================================== Young's modulus of a wire (Searle's apparatus)
def searle_young_modulus() -> dict:
    return lab(
        id="searle-young-modulus", title="Young's modulus of a wire (Searle's apparatus)",
        group="Physics · Properties of matter", level="Class XI", topic="Mechanical Properties of Solids",
        chapter="Mechanical Properties of Solids",
        aim="Load a wire step by step, measure the tiny extension with Searle's apparatus and find Young's modulus.",
        kernel="searle", params={"Y": 2.0e11, "L": 1.0, "d": 0.000559, "m": 0.0}, autorun=True,
        camera={"pos": [0.5, 0.8, 1.5], "look": [0.0, 0.6, -0.3]}, floor=-0.9,
        bodies=[
            B("bracket", "box", name="Rigid bracket", info="Both wires hang from the same rigid support.",
              size=[0.3, 0.03, 0.06], pos=[0, 1.22, -0.3], color="#2b3138"),
            B("post", "cylinder", name="Support pillar", r=0.018, h=1.2, pos=[-0.16, 0.6, -0.3], color="steel"),
            B("foot", "box", name="Heavy base", size=[0.3, 0.03, 0.22], pos=[-0.16, 0.015, -0.3], color="#2b3138"),
            B("wireA", "rope", name="Reference wire", info="Carries a constant dead load, so the support's own sag is cancelled.",
              a=[-0.04, 1.2, -0.3], b=[-0.04, 0.2, -0.3], r=0.0012, color="steel"),
            B("wireB", "rope", name="Experimental wire", info="The wire whose Young's modulus you measure.",
              a=[0.04, 1.2, -0.3], b=[0.04, 0.2, -0.3], r=0.0012, color="steel"),
            B("frameA", "box", name="Reference frame", size=[0.05, 0.08, 0.04], pos=[-0.04, 0.17, -0.3], color="brass"),
            B("frameB", "box", name="Experimental frame", info="Hangs on the loaded wire and goes down as the wire stretches.",
              size=[0.05, 0.08, 0.04], pos=[0.04, 0.17, -0.3], color="brass",
              bind={"y": {"var": "e", "k": -1.0, "c": 0.17}}),
            B("level", "box", name="Spirit level", info="One end rests on the micrometer screw: the bubble shows when the frames are level again.",
              size=[0.1, 0.014, 0.022], pos=[0, 0.215, -0.3], color="#1b1b1d"),
            B("micro", "cylinder", name="Micrometer screw", info="Pitch 0.5 mm, 50 divisions: least count 0.01 mm.",
              r=0.012, h=0.05, pos=[0.04, 0.24, -0.3], color="steel"),
            B("hanger", "cylinder", name="Hanger with slotted weights", info="Half-kilogram slotted weights are added one at a time.",
              r=0.035, h=0.03, pos=[0.04, 0.1, -0.3], color="brass", bind={"y": {"var": "e", "k": -1.0, "c": 0.1}}),
            B("dead", "cylinder", name="Dead load", r=0.03, h=0.025, pos=[-0.04, 0.105, -0.3], color="brass"),
            B("lbl", "text", text="Searle's apparatus", size=0.03, pos=[0.0, 1.3, -0.3]),
        ],
        knobs=[knob("load", "Load on the wire", "m", 0, 2.5, 0.5, 0, "kg"),
               knob("Y", "Wire material (Y hidden)", "Y", 50, 250, 1, 200, "GPa", 1e9, hidden=True),
               knob("d", "Wire gauge (diameter)", "d", 0.3, 1.2, 0.001, 0.559, "mm", 0.001,
                    hint="Measured with a screw gauge at several places.")],
        instruments=[inst("e", "readout", "Extension e", "e_mm", unit="mm", lc=0.01, digits=3),
                     inst("ld", "readout", "Load", "load_N", unit="N", digits=1),
                     inst("gr", "graph", "Extension against load", "e_mm", x="knob:load", xlabel="m (kg)", dots=True)],
        table={"columns": [col("m", "Load m", "knob:load", "kg", digits=1),
                           col("e", "Extension e", "inst:e", "mm", 0.001, digits=3)],
               "calc": "searle_Y", "rows_min": 3, "truth": "p.Y", "result_digits": 0,
               "hint": "After each weight, bring the bubble back to the centre with the micrometer and read it."},
        steps=["Note the micrometer reading with only the dead load on the hanger.",
               "Add 0.5 kg, bring the spirit-level bubble back to the centre and read the micrometer.",
               "Repeat up to 2.5 kg, then unload in the same steps.",
               "The difference from the zero reading is the extension e.",
               "Y = 4 m g L / (π d² e): take the slope of the e against m graph."],
        theory="Stress is the load per unit area of cross-section, mg / (πd²/4); strain is the extension per unit length, "
               "e / L. Within the elastic limit their ratio is a constant of the material, Young's modulus "
               "Y = stress / strain = 4mgL / (πd²e). Searle's apparatus measures e, which is only a fraction of a "
               "millimetre, by keeping a reference wire beside the loaded one so that room temperature and the support's "
               "own yielding affect both equally.",
        safety="Do not load past the elastic limit: the wire will not come back to its length. Keep your feet clear of the "
               "weights and add them gently.",
        tour=[{"say": "Two long wires hang from the same bracket. The left one is the reference wire, the right one is loaded."},
              {"set": {"load": 1.5}, "say": "One and a half kilograms: the wire stretches by a fraction of a millimetre, far too little to see."},
              {"set": {"load": 2.5}, "say": "The micrometer and the spirit level measure that tiny extension to 0.01 millimetre."}],
        questions=[{"q": "Why is a second (reference) wire used?", "options": ["To cancel the effect of temperature and of the support's own sag",
                                                                               "To make the apparatus heavier", "To double the load"],
                    "answer": 0, "why": "Both wires change alike with temperature, so the difference measures the stretch from the load alone."},
                   {"q": "If a wire of twice the diameter is used, the extension under the same load is",
                    "options": ["One quarter", "Half", "Twice", "Unchanged"], "answer": 0,
                    "why": "e is inversely proportional to d²."}],
        sources=[S11, SIM, CRC, SWG],
        check={"params": {"m": 2.0}, "reading": "e", "textbook": "searle_e"},
    )


# ===================================================================== limiting friction on a horizontal surface
def _friction(lab_id, title, aim, mu, m, body, rig, steps, theory, qs, chapter, topic) -> dict:
    d = lab(
        id=lab_id, title=title, group="Physics · Mechanics", level="Class XI", topic=topic, chapter=chapter, aim=aim,
        kernel="friction", params={"mu": mu, "m": m, "add": 0.0, "len": 0.3}, autorun=True,
        camera={"pos": [0.45, 0.42, 0.85], "look": [0.0, 0.14, -0.05]}, floor=-0.02,
        bodies=[
            B("stand1", "box", name="Support block", size=[0.06, 0.12, 0.2], pos=[-0.3, 0.06, -0.08], color="wood"),
            B("stand2", "box", name="Support block", size=[0.06, 0.12, 0.2], pos=[0.22, 0.06, -0.08], color="wood"),
            B("board", "box", name="Horizontal plank", info="The surface the body slides or rolls on.",
              size=[0.72, 0.02, 0.24], pos=[-0.02, 0.13, -0.08], color="wood"),
            B("body", "box", name=body, info="Its weight presses on the plank: that is the normal reaction R.",
              size=[0.09, 0.05, 0.07], pos=[-0.2, 0.165, -0.08], color="#8c5a2b", bind={"x": {"var": "s", "k": 1.0, "c": -0.2}}),
            B("pulley", "torus", name="Pulley at the edge", info="Turns the horizontal pull of the thread into the weight of the pan.",
              r=0.025, tube=0.006, pos=[0.33, 0.155, -0.08], color="steel"),
            B("brkt", "box", size=[0.04, 0.06, 0.02], pos=[0.33, 0.12, -0.08], color="#2b3138"),
            B("thread", "rope", name="Thread", a={"body": "body", "off": [0.05, 0, 0]}, b={"body": "pulley", "off": [0, 0.025, 0]},
              r=0.0012, color="ink"),
            B("pan", "cylinder", name="Scale pan", info="Weights are added to it until the body just begins to move.",
              r=0.04, h=0.012, pos=[0.355, 0.055, -0.08], color="brass"),
            B("pthread", "rope", a={"body": "pulley", "off": [0.025, 0, 0]}, b={"body": "pan", "off": [0, 0.006, 0]}, r=0.0012, color="ink"),
            B("box", "box", name="Weight box", size=[0.22, 0.05, 0.1], pos=[0.6, 0.025, 0.06], color="#7a4e2c"),
        ],
        knobs=[knob("F", "Weight in the pan", "F", 0, 400, 2, 0, "g", 0.0098, reset=True,
                    hint="Add the weights in small steps and note when the body just begins to move."),
               knob("add", "Extra weight on the body", "add", 0, 1000, 50, 0, "g", 0.001, reset=True),
               knob("mu", "Surface (coefficient hidden)", "mu", 0.01, 0.8, 0.005, mu, hidden=True, reset=True)],
        instruments=[inst("R", "readout", "Normal reaction R", "R", unit="N", digits=2),
                     inst("mv", "readout", "Is it moving? (1 = yes)", "moving", digits=0),
                     inst("gr", "graph", "Pull against normal reaction", "F_now", x="R", xlabel="R (N)", dots=True)],
        table={"columns": [col("R", "Normal reaction R", "inst:R", "N", digits=2),
                           col("F", "Least pull F", "knob:F", "g", 0.0098, digits=0)],
               "calc": "friction_mu", "rows_min": 3, "truth": "p.mu", "result_digits": 3,
               "hint": "For each load on the body: add pan weights in small steps until it just moves, and record."},
        steps=steps,
        theory=theory,
        safety="Keep the thread horizontal and in line with the body. Add the weights gently, without jerking the thread.",
        tour=[{"say": "The body rests on a horizontal plank. A thread from it runs over the pulley at the edge to the scale pan."},
              {"set": {"F": 40}, "say": "A small weight in the pan: nothing moves. Friction is still holding the body back."},
              {"set": {"F": 120}, "say": "More weight: now it moves. The least weight that moves it measures the limiting friction."}],
        questions=qs,
        sources=[S11, SIM],
        check={"params": {"add": 0.0}, "reading": "F_min", "textbook": "friction_Fmin"},
    )
    if rig:
        d["rig"] = rig
    return d


def limiting_friction() -> dict:
    return _friction(
        "limiting-friction", "Limiting friction and normal reaction",
        "Find the least force that moves a block along a horizontal plank, repeat with extra weights on the block, and "
        "get the coefficient of limiting friction from the graph of F against R.",
        0.30, 0.2, "Wooden block", None,
        ["Put the block on the plank and run the thread over the pulley to the pan.",
         "Add weights to the pan in small steps until the block just begins to move.",
         "Record the least pull F and the normal reaction R = (weight of the block + weights on it).",
         "Put 100 g, 200 g... on the block and repeat.",
         "Plot F against R: the slope is the coefficient of limiting friction \u03bc."],
        "The force of friction between two surfaces at rest grows with the force trying to move them, up to a greatest "
        "value called limiting friction. Experiment shows that this limiting value is proportional to the normal "
        "reaction between the surfaces: F = \u03bc R, where \u03bc is the coefficient of limiting friction. It depends on the "
        "pair of surfaces, not on the area of contact.",
        [{"q": "When the weights on the block are doubled, the least pull that moves it", "options": ["Doubles", "Stays the same", "Halves"],
          "answer": 0, "why": "F = \u03bcR and R doubles."},
         {"q": "What does the slope of the F against R graph give?", "options": ["The coefficient of limiting friction", "The weight of the block", "g"],
          "answer": 0, "why": "F = \u03bcR is a straight line through the origin of slope \u03bc."}],
        "Laws of Motion", "Laws of Motion")


def rolling_friction() -> dict:
    return _friction(
        "rolling-friction", "Limiting friction for a rolling roller",
        "Measure the least force that sets a roller rolling on a horizontal plank and compare it with the force needed "
        "to slide a block on the same plank.",
        0.03, 2.0, "Metal roller", "limiting-friction",
        ["Lay the roller on the plank and run the thread over the pulley to the pan.",
         "Add weights to the pan in small steps until the roller just begins to roll.",
         "Record the least pull F and the normal reaction R.",
         "Repeat with extra weights on the roller.",
         "Compare the slope with the one for a sliding block: rolling friction is far smaller."],
        "A roller does not rub along the surface: it turns about the line where it touches. What resists it is the small "
        "deformation of the roller and the plank at that line, and it is far smaller than sliding friction. It still "
        "grows in proportion to the normal reaction, F = \u03bc_r R, so the same graph gives its coefficient - a number "
        "ten times smaller than for sliding. This is why wheels and ball bearings are used.",
        [{"q": "Rolling friction is usually", "options": ["Much smaller than sliding friction", "Much larger", "Exactly the same"],
          "answer": 0, "why": "That is why wheels and rollers are used to move heavy loads."},
         {"q": "The coefficient of rolling friction is found from", "options": ["The slope of F against R", "The weight of the roller alone", "The radius alone"],
          "answer": 0, "why": "F = \u03bc_r R, so the slope is the coefficient."}],
        "Laws of Motion", "Laws of Motion")


# ======================================================== mass of a body by the principle of moments (metre scale)
def metre_scale_moments() -> dict:
    return lab(
        id="metre-scale-moments", title="Mass of a body with a metre scale (principle of moments)",
        group="Physics · Mechanics", level="Class XI", topic="System of Particles and Rotational Motion",
        chapter="System of Particles and Rotational Motion",
        aim="Balance a metre scale on a knife edge, hang the body on one side and a known mass on the other, and find "
            "the mass of the body from the principle of moments.",
        kernel="moments", params={"m": 0.0523, "M": 0.05, "x": 0.2, "y": 0.2, "c": 8.0}, autorun=True,
        camera={"pos": [0.0, 0.5, 1.0], "look": [0.0, 0.2, -0.08]}, floor=-0.02,
        bodies=[
            B("stand", "box", name="Stand", size=[0.1, 0.16, 0.12], pos=[0, 0.08, -0.08], color="#7a4e2c"),
            B("wedge", "box", name="Knife edge", info="The metre scale rests on this sharp edge at its centre of gravity.",
              size=[0.02, 0.03, 0.09], pos=[0, 0.175, -0.08], color="steel"),
            B("beam", "box", name="Metre scale", info="Balanced at its own centre of gravity, so its weight has no moment.",
              size=[1.0, 0.006, 0.03], pos=[0, 0.195, -0.08], color="wood", bind={"rz": "th"}),
            B("ms", "scale", name="Printed centimetre scale", length=1.0, spacing=0.01, major=10, labels=True,
              label_step=10, tick=0.01, font=0.016, pos=[-0.5, 0.2, -0.065], rot=[0, 0, 1.5708]),
            B("tl", "rope", name="Loop of thread (body)", a=[-0.2, 0.195, -0.08], b=[-0.2, 0.13, -0.08], r=0.001, color="ink"),
            B("body", "sphere", name="Body of unknown mass", info="Hung from a loop of thread at a measured distance from the knife edge.",
              r=0.025, pos=[-0.2, 0.105, -0.08], color="#5f646b"),
            B("tr", "rope", name="Loop of thread (known mass)", a=[0.2, 0.195, -0.08], b=[0.2, 0.14, -0.08], r=0.001, color="ink"),
            B("known", "cylinder", name="Known mass", info="A weight of known mass, slid along the scale until it balances.",
              r=0.02, h=0.016, pos=[0.2, 0.13, -0.08], color="brass"),
            B("lbl", "text", text="Principle of moments", size=0.026, pos=[0, 0.3, -0.08]),
        ],
        knobs=[knob("x", "Distance of the body from the knife edge", "x", 5, 45, 0.5, 20, "cm", 0.01),
               knob("y", "Distance of the known mass", "y", 2, 48, 0.1, 20, "cm", 0.01),
               knob("M", "Known mass", "M", 20, 100, 5, 50, "g", 0.001),
               knob("m", "Body (mass hidden)", "m", 10, 200, 0.1, 52.3, "g", 0.001, hidden=True)],
        instruments=[inst("tl", "readout", "Tilt of the scale", "tilt_deg", unit="°", digits=2),
                     inst("bal", "readout", "Balanced? (1 = yes)", "balanced", digits=0)],
        table={"columns": [col("x", "Distance of the body x", "knob:x", "cm", 0.01, digits=1),
                           col("y", "Distance of the known mass y", "knob:y", "cm", 0.01, digits=1)],
               "calc": "moments_m", "rows_min": 3, "truth": "p.m", "result_k": 1000, "result_unit": "g",
               "result_digits": 1, "hint": "Slide the known mass until the scale is level, then record both distances."},
        steps=["Balance the bare metre scale on the knife edge and note the balancing point: that is its centre of gravity.",
               "Hang the body at a measured distance x on the left of the knife edge.",
               "Slide the known mass on the right until the scale is level again; note its distance y.",
               "Repeat for two more positions of the body.",
               "m x = M y, so the mass of the body m = M y / x."],
        theory="A body that is not turning has no net moment about any point. For the metre scale resting on the knife "
               "edge, the weight of the body on one side and of the known mass on the other give moments in opposite "
               "senses: m g x anticlockwise and M g y clockwise. When the scale is level these are equal, so m x = M y. "
               "The scale is balanced at its own centre of gravity first, so its own weight has no moment about the "
               "knife edge.",
        safety="Use thin thread loops, and make sure the knife edge is exactly at the balancing point before you start.",
        tour=[{"say": "A metre scale rests on a knife edge at its centre of gravity. The unknown body hangs on the left."},
              {"set": {"y": 10}, "say": "The known mass is too near the knife edge: its moment is too small and the scale tips to the left."},
              {"set": {"y": 20.9}, "say": "Slid further out, the moments are equal and the scale is level. Now m x = M y gives the mass."}],
        questions=[{"q": "If the known mass is moved twice as far out, its moment", "options": ["Doubles", "Halves", "Does not change"],
                    "answer": 0, "why": "Moment = force × distance from the pivot."},
                   {"q": "Why is the scale balanced at its centre of gravity first?",
                    "options": ["So that its own weight has no moment about the knife edge", "To make it lighter", "To straighten it"],
                    "answer": 0, "why": "The weight acts at the centre of gravity, whose distance from the pivot is then zero."}],
        sources=[S11, SIM],
        check={"params": {"x": 0.2}, "reading": "y", "textbook": "moments_y"},
    )


# ================================================================= radius of curvature with a spherometer
def spherometer_radius() -> dict:
    return lab(
        id="spherometer-radius", title="Radius of curvature of a spherical surface (spherometer)",
        group="Physics · Measurement", level="Class XI", topic="Units and Measurement",
        chapter="Units and Measurements",
        aim="Measure the sagitta of a spherical surface with a spherometer and work out its radius of curvature.",
        kernel="spherometer", params={"R": 0.15, "l": 0.045, "pitch": 0.001, "ndiv": 100.0}, autorun=True,
        camera={"pos": [0.16, 0.18, 0.3], "look": [0.0, 0.05, -0.04]}, floor=-0.02,
        bodies=[
            B("plate", "box", name="Plane glass plate", info="The flat surface the zero reading is taken on.",
              size=[0.11, 0.006, 0.11], pos=[-0.1, 0.003, -0.04], color="glass", opacity=0.35),
            B("glass", "dish", name="Spherical surface", info="A watch glass: convex on one side, concave on the other.",
              R=0.15, r=0.05, convex=True, pos=[0.0, 0.004, -0.04], color="glass", opacity=0.4),
            B("frame", "box", name="Spherometer frame", info="Three legs on the corners of an equilateral triangle, with the screw at its centre.",
              size=[0.06, 0.006, 0.052], pos=[0.0, 0.052, -0.04], color="brass"),
            B("leg1", "cylinder", name="Leg", r=0.0016, h=0.05, pos=[-0.026, 0.027, -0.055], color="steel"),
            B("leg2", "cylinder", name="Leg", r=0.0016, h=0.05, pos=[0.026, 0.027, -0.055], color="steel"),
            B("leg3", "cylinder", name="Leg", r=0.0016, h=0.05, pos=[0.0, 0.027, -0.009], color="steel"),
            B("screw", "cylinder", name="Central screw", info="Pitch 1 mm; the disc has 100 divisions, so the least count is 0.01 mm.",
              r=0.0025, h=0.07, pos=[0.0, 0.055, -0.04], color="steel", bind={"y": {"var": "h", "k": -1.0, "c": 0.055}}),
            B("disc", "cylinder", name="Circular disc scale (100 divisions)", r=0.022, h=0.006, pos=[0.0, 0.082, -0.04],
              color="brass", bind={"y": {"var": "h", "k": -1.0, "c": 0.082}, "ry": {"var": "h", "k": -6283.2}}),
            B("vscale", "scale", name="Vertical millimetre scale", length=0.03, spacing=0.001, major=5, labels=True,
              label_step=5, tick=0.004, font=0.006, pos=[0.016, 0.054, -0.028], rot=[0, 0, 0]),
            B("lbl", "text", text="Spherometer", size=0.012, pos=[0.0, 0.1, -0.04]),
        ],
        knobs=[knob("R", "Spherical surface (radius hidden)", "R", 0.05, 0.6, 0.001, 0.15, "m", hidden=True),
               knob("l", "Distance between the legs l", "l", 30, 60, 0.1, 45, "mm", 0.001,
                    hint="Pressed on paper, the three leg marks make an equilateral triangle; l is the mean of its sides.")],
        instruments=[inst("h", "readout", "Sagitta h", "h_mm", unit="mm", lc=0.01, digits=3),
                     inst("turns", "readout", "Whole turns of the screw (help)", "turns", digits=0, hint=True),
                     inst("div", "readout", "Disc division (help)", "div", digits=0, hint=True)],
        table={"columns": [col("l", "Distance between the legs l", "knob:l", "mm", 0.001, digits=1),
                           col("h", "Sagitta h", "manual", "mm", 0.001, digits=3)],
               "calc": "sph_R", "rows_min": 2, "truth": "p.R", "result_digits": 3,
               "hint": "Take the zero reading on the plane plate, then the reading on the surface; h is the difference."},
        steps=["Put the spherometer on the plane glass plate and turn the screw until its tip just touches: that is the zero reading.",
               "Put it on the convex side of the surface and turn the screw down until it just touches; read again.",
               "The difference of the two readings is the sagitta h.",
               "Turn the glass over and repeat on the concave side.",
               "R = l² / (6h) + h / 2, with l the mean distance between the legs."],
        theory="The three legs of a spherometer stand on a circle of radius l/\u221a3, where l is the distance between any "
               "two legs. When the tip of the central screw just touches a sphere of radius R, the height h of the tip "
               "above (or below) the plane of the legs is the sagitta of that circle, and simple geometry gives "
               "R = l\u00b2/(6h) + h/2. A flatter surface has a bigger R and a smaller h.",
        safety="Lower the screw gently: pressing it hard on a glass surface scratches the glass and bends the tip.",
        tour=[{"say": "A spherometer: three fixed legs and a screw at the centre that carries a disc of 100 divisions."},
              {"say": "On the plane glass plate the tip and the three legs are in one plane: that reading is the zero."},
              {"set": {"R": 0.4}, "say": "A flatter surface: the screw hardly moves, because h falls as R grows."}],
        questions=[{"q": "For a flatter surface (larger R), the sagitta h is", "options": ["Smaller", "Larger", "Unchanged"],
                    "answer": 0, "why": "h \u2248 l\u00b2/(6R), so h falls as R grows."},
                   {"q": "The least count of this spherometer is", "options": ["0.01 mm", "0.1 mm", "1 mm"],
                    "answer": 0, "why": "Pitch 1 mm divided by 100 divisions on the disc."}],
        sources=[S11, SIM],
        check={"params": {"l": 0.045}, "reading": "R", "textbook": "sph_R"},
    )


# ======================================================= parallelogram law of vectors (Gravesand's apparatus)
def parallelogram_law() -> dict:
    return lab(
        id="parallelogram-law", title="Parallelogram law of vectors: weight of a body",
        group="Physics · Mechanics", level="Class XI", topic="Motion in a Plane", chapter="Motion in a Plane",
        aim="Hold up an unknown weight with two known weights over pulleys, measure the angle between them and find the "
            "unknown weight from the parallelogram law.",
        kernel="vecforce", params={"P": 1.47, "Q": 1.47, "W": 1.96}, autorun=True,
        camera={"pos": [0.0, 0.62, 1.05], "look": [0.0, 0.45, -0.3]}, floor=-0.02,
        bodies=[
            B("board", "box", name="Drawing board", info="A vertical board with a sheet of paper pinned to it.",
              size=[0.8, 0.6, 0.02], pos=[0, 0.42, -0.34], color="wood"),
            B("paper", "box", name="Paper sheet", size=[0.7, 0.5, 0.001], pos=[0, 0.42, -0.328], color="white"),
            B("foot", "box", name="Stand", size=[0.4, 0.04, 0.16], pos=[0, 0.02, -0.3], color="#2b3138"),
            B("pulL", "torus", name="Left pulley", r=0.028, tube=0.006, pos=[-0.3, 0.66, -0.31], color="steel"),
            B("pulR", "torus", name="Right pulley", r=0.028, tube=0.006, pos=[0.3, 0.66, -0.31], color="steel"),
            B("knot", "sphere", name="Knot", info="The three threads are tied here; the three forces meet at this point.",
              r=0.006, pos=[0, 0.42, -0.31], color="red"),
            B("thL", "rope", name="Thread to P", a=[-0.3, 0.66, -0.31], b="knot", r=0.0012, color="ink"),
            B("thR", "rope", name="Thread to Q", a=[0.3, 0.66, -0.31], b="knot", r=0.0012, color="ink"),
            B("thW", "rope", name="Thread to the body", a="knot", b=[0, 0.16, -0.31], r=0.0012, color="ink"),
            B("hP", "cylinder", name="Hanger P", r=0.022, h=0.02, pos=[-0.3, 0.3, -0.31], color="brass"),
            B("hQ", "cylinder", name="Hanger Q", r=0.022, h=0.02, pos=[0.3, 0.3, -0.31], color="brass"),
            B("body", "cylinder", name="Body of unknown weight", r=0.026, h=0.03, pos=[0, 0.14, -0.31], color="#5f646b"),
            B("lbl", "text", text="Parallelogram law", size=0.03, pos=[0, 0.76, -0.33]),
        ],
        knobs=[knob("P", "Weight P (left)", "P", 50, 300, 10, 150, "g", 0.0098),
               knob("Q", "Weight Q (right)", "Q", 50, 300, 10, 150, "g", 0.0098),
               knob("W", "Body (weight hidden)", "W", 50, 400, 1, 200, "g", 0.0098, hidden=True)],
        instruments=[inst("th", "readout", "Angle between the threads", "theta_deg", unit="°", lc=0.5, digits=1),
                     inst("al", "readout", "Left thread from the vertical", "alpha", k=57.2958, unit="°", digits=1),
                     inst("R", "readout", "Resultant of P and Q", "R", unit="N", digits=3, hint=True)],
        table={"columns": [col("P", "Weight P", "knob:P", "g", 0.0098, digits=0),
                           col("Q", "Weight Q", "knob:Q", "g", 0.0098, digits=0),
                           col("th", "Angle θ between them", "inst:th", "°", 0.0174533, digits=1)],
               "calc": "vec_W_calc", "rows_min": 3, "truth": "p.W", "result_digits": 3,
               "hint": "For each pair of weights: let the knot settle, mark the three directions, measure θ and record."},
        steps=["Hang the known weights P and Q from the two threads over the pulleys, and the body from the third.",
               "Let the knot come to rest; tap the board gently so that the threads run free.",
               "Mark the three directions on the paper with pins and join them.",
               "Measure the angle θ between the threads carrying P and Q.",
               "The resultant of P and Q is R = √(P² + Q² + 2PQ cos θ); it must be equal and opposite to the weight of the body."],
        theory="Three forces that keep a point at rest must add to zero, so the resultant of the two known weights is "
               "equal and opposite to the weight of the body. The parallelogram law gives that resultant: if P and Q act "
               "at an angle θ, their resultant is R = √(P² + Q² + 2PQ cos θ), along the diagonal of the parallelogram "
               "drawn on them. Measuring θ therefore weighs the body without a balance.",
        safety="Make sure the pulleys turn freely and the threads do not rub the board, or the angles will be wrong.",
        tour=[{"say": "Two threads run over the pulleys to the known weights P and Q; the third holds the body."},
              {"set": {"P": 250}, "say": "A heavier weight on the left: the knot moves and the angles change, but the three forces still balance."},
              {"set": {"P": 150}, "say": "Measure the angle between the two upper threads: that is all the parallelogram law needs."}],
        questions=[{"q": "The resultant of P and Q must be", "options": ["Equal and opposite to the weight of the body",
                                                                         "Equal to P + Q always", "Zero"],
                    "answer": 0, "why": "Three forces in equilibrium at a point add to zero."},
                   {"q": "If the angle between P and Q is made larger, their resultant",
                    "options": ["Gets smaller", "Gets larger", "Does not change"], "answer": 0,
                    "why": "cos θ falls as θ grows, so R = √(P² + Q² + 2PQ cos θ) falls."}],
        sources=[S11, SIM],
        check={"params": {}, "reading": "W_calc", "textbook": "vec_W"},
    )


# ============================================================== depression of a loaded metre scale (bending)
def metre_scale_depression() -> dict:
    return lab(
        id="metre-scale-depression", title="Effect of load on the depression of a metre scale",
        group="Physics · Properties of matter", level="Class XI", topic="Mechanical Properties of Solids",
        chapter="Mechanical Properties of Solids",
        aim="Clamp a metre scale at one end, load its free end step by step, measure the depression and see that it is "
            "proportional to the load and to the cube of the length.",
        kernel="beambend", params={"Y": 1.0e10, "b": 0.028, "t": 0.005, "L": 0.5, "m": 0.0, "mode": 0.0}, autorun=True,
        camera={"pos": [0.4, 0.5, 0.95], "look": [0.05, 0.16, -0.1]}, floor=-0.02,
        bodies=[
            B("tablec", "box", name="Clamp", info="Holds one end of the scale firmly, so that end cannot turn.",
              size=[0.12, 0.07, 0.1], pos=[-0.4, 0.22, -0.1], color="#2b3138"),
            B("post", "cylinder", name="Clamp pillar", r=0.018, h=0.2, pos=[-0.4, 0.1, -0.1], color="steel"),
            B("foot", "box", name="Heavy base", size=[0.22, 0.02, 0.18], pos=[-0.4, 0.01, -0.1], color="#2b3138"),
            B("beam", "box", name="Metre scale", info="A wooden metre scale, clamped at one end and free at the other.",
              size=[0.9, 0.005, 0.028], pos=[0.05, 0.22, -0.1], color="wood"),
            B("ms", "scale", name="Printed centimetre scale", length=0.9, spacing=0.01, major=10, labels=True,
              label_step=10, tick=0.008, font=0.012, pos=[-0.4, 0.223, -0.088], rot=[0, 0, 1.5708]),
            B("hook", "cylinder", name="Hook for the load", r=0.003, h=0.03, pos=[0.46, 0.205, -0.1], color="steel",
              bind={"y": {"var": "delta", "k": -1.0, "c": 0.205}}),
            B("pan", "cylinder", name="Hanger with slotted weights", r=0.03, h=0.02, pos=[0.46, 0.17, -0.1], color="brass",
              bind={"y": {"var": "delta", "k": -1.0, "c": 0.17}}),
            B("pin", "box", name="Pointer pin", info="A pin fixed at the free end; its tip is read against the vertical scale.",
              size=[0.002, 0.03, 0.002], pos=[0.5, 0.21, -0.1], color="red", bind={"y": {"var": "delta", "k": -1.0, "c": 0.21}}),
            B("vscale", "scale", name="Vertical scale (mm)", length=0.16, spacing=0.001, major=10, labels=True,
              label_step=10, tick=0.006, font=0.01, pos=[0.52, 0.13, -0.09]),
            B("lbl", "text", text="Cantilever", size=0.024, pos=[0.0, 0.3, -0.1]),
        ],
        knobs=[knob("m", "Load at the free end", "m", 0, 500, 50, 0, "g", 0.001),
               knob("L", "Length from the clamp L", "L", 20, 60, 5, 50, "cm", 0.01),
               knob("Y", "Material of the scale (Y hidden)", "Y", 2, 20, 0.1, 10, "GPa", 1e9, hidden=True)],
        instruments=[inst("d", "readout", "Depression \u03b4", "delta_mm", unit="mm", lc=0.1, digits=2),
                     inst("ld", "readout", "Load", "load_N", unit="N", digits=2),
                     inst("gr", "graph", "Depression against load", "delta_mm", x="knob:m", xlabel="m (g)", dots=True)],
        table={"columns": [col("m", "Load m", "knob:m", "g", 0.001, digits=0),
                           col("delta", "Depression \u03b4", "inst:d", "mm", 0.001, digits=2)],
               "calc": "beam_Y", "rows_min": 3, "truth": "p.Y", "result_digits": 0,
               "hint": "After each weight, wait for the scale to stop quivering and read the pin against the vertical scale."},
        steps=["Clamp the metre scale at one end so that 50 cm of it is free.",
               "Note the reading of the pointer pin with no load.",
               "Hang 50 g at the free end, wait, and read the pin again: the difference is the depression \u03b4.",
               "Repeat up to 250 g; \u03b4 should grow in proportion to the load.",
               "Y = m g L\u00b3 / (3 I \u03b4) with I = b t\u00b3 / 12."],
        theory="A beam clamped at one end and loaded at the other bends into an arc. Each layer above the middle of its "
               "thickness is stretched and each layer below is compressed, and the resistance of the material to that "
               "stretching holds the load up. For a load W at the free end of a cantilever of length L, width b and "
               "thickness t, the depression is \u03b4 = W L\u00b3 / (3 Y I) with I = b t\u00b3/12. The same beam supported at both ends "
               "and loaded in the middle sags only W L\u00b3 / (48 Y I): sixteen times less.",
        safety="Do not load so far that the scale takes a permanent bend; take the weights off when you have finished.",
        tour=[{"say": "A metre scale is clamped at one end; 50 centimetres of it stick out free."},
              {"set": {"m": 150}, "say": "150 grams at the free end: the scale bends and the pointer pin moves down the vertical scale."},
              {"set": {"m": 300}, "say": "Twice the load, twice the depression: \u03b4 is proportional to the load."},
              {"set": {"m": 150, "L": 25}, "say": "Half the free length: the depression falls to an eighth, because \u03b4 goes as L cubed."}],
        questions=[{"q": "If the free length is doubled, the depression under the same load becomes",
                    "options": ["8 times", "2 times", "4 times", "Half"], "answer": 0, "why": "\u03b4 is proportional to L\u00b3."},
                   {"q": "A scale of twice the thickness, same load and length, bends",
                    "options": ["8 times less", "2 times less", "4 times less"], "answer": 0,
                    "why": "I = b t\u00b3/12, so I grows 8 times and \u03b4 falls 8 times."}],
        sources=[S11, SIM, WOOD],
        check={"params": {"m": 0.2}, "reading": "delta", "textbook": "beam_delta"},
    )


BUILDERS = (capillary_rise, detergent_capillary, searle_young_modulus, limiting_friction, rolling_friction,
            metre_scale_moments, spherometer_radius, parallelogram_law, metre_scale_depression)
