"""The Prayogshala catalogue, L1: 22 physics practicals from the NCERT Class XI / XII laboratory manuals, written as LSL
data (no code). Every lab passes `lsl.check` and its own NCERT check (`lsl.run_check`, 1 %) in the tests.

All learner-facing text is English (owner, 1 Nov 2026: "FIRST MAKE ENTIRE THING IN ENGLISH").
Coordinates are metres in the 3D stage unless a lab scales them (vernier / screw gauge are magnified and say so)."""
from __future__ import annotations

import math
from typing import Any

DEG = math.pi / 180
R2D = 180 / math.pi
S11 = {"title": "NCERT Physics Textbook Class XI + Laboratory Manual Physics Class XI"}
S12 = {"title": "NCERT Physics Textbook Class XII + Laboratory Manual Physics Class XII"}
SIM = {"title": "Hoola Prayogshala kernel", "note": "readings come from the simulation code; checked against the NCERT formula in Hoola's tests"}


def B(id: str, kind: str, **kw: Any) -> dict:
    return {"id": id, "kind": kind, **kw}


def knob(id, label, param, mn, mx, st, val, unit="", k=1.0, **kw) -> dict:
    d = {"id": id, "label": label, "param": param, "min": mn, "max": mx, "step": st, "value": val}
    if unit:
        d["unit"] = unit
    if k != 1.0:
        d["k"] = k
    d.update(kw)
    return d


def inst(id, kind, label, var=None, **kw) -> dict:
    d = {"id": id, "kind": kind, "label": label}
    if var:
        d["var"] = var
    d.update(kw)
    return d


def col(id, label, frm="manual", unit="", k=1.0, **kw) -> dict:
    d = {"id": id, "label": label, "from": frm}
    if unit:
        d["unit"] = unit
    if k != 1.0:
        d["k"] = k
    d.update(kw)
    return d


def lab(**kw) -> dict:
    d = {"lsl": 1, "field": "physics", "lang": "en-IN"}
    d.update(kw)
    return d


def board(w=1.0, d=0.6, y=-0.01) -> dict:
    return B("board", "box", name="Wooden board", size=[w, 0.02, d], pos=[0, y, 0], color="wood", cut=False)


def dial(id, pos, name, info="") -> list[dict]:
    x, y, z = pos
    return [B(id + "_box", "box", name=name, info=info, size=[0.12, 0.04, 0.1], pos=[x, y + 0.02, z], color="#2b2f36"),
            B(id + "_face", "box", size=[0.1, 0.001, 0.07], pos=[x, y + 0.041, z + 0.005], color="white"),
            B(id + "_scale", "torus", r=0.035, tube=0.0012, arc=2.4, pos=[x, y + 0.043, z + 0.02], rot=[-1.5708, 0, 0.37], color="ink")]


def needle(id, pos, var, k, c=0.0, mn=-1.2, mx=1.2) -> dict:
    x, y, z = pos
    return B(id, "needle", length=0.038, pos=[x, y + 0.044, z + 0.02], rot=[-1.5708, 0, 0],
             bind={"rz": {"var": var, "k": k, "c": c, "min": mn, "max": mx}}, color="red")


# ======================================================================================================== MECHANICS
def pendulum() -> dict:
    return lab(
        id="simple-pendulum", title="Simple pendulum: L and T", group="Physics · Mechanics", level="Class XI",
        topic="Oscillations", aim="Change the length L, measure the time period T and find g.",
        kernel="pendulum", params={"b": 0.0}, speed=1, speeds=[0.25, 0.5, 1, 2],
        camera={"pos": [0.5, 0.0, 2.7], "look": [0, -0.15, 0]}, floor=-1.02,
        bodies=[
            B("base", "box", name="Stand base", size=[0.6, 0.04, 0.4], pos=[0, -1.0, 0], color="wood"),
            B("rod", "cylinder", name="Stand rod", r=0.012, h=1.66, pos=[-0.25, -0.17, 0], color="steel"),
            B("arm", "box", size=[0.3, 0.02, 0.02], pos=[-0.12, 0.62, 0], color="steel"),
            B("clamp", "box", name="Split cork / clamp", info="The thread hangs from here: this is the point of suspension.",
              size=[0.05, 0.05, 0.05], pos=[0, 0.62, 0], color="black"),
            B("bob", "sphere", name="Bob", info="A heavy metal sphere. Its mass does not change T.", r=0.035,
              pos=[0, 0.6, 0], color="brass", bind={"x": "bob_x", "y": "bob_y"}),
            B("thread", "rope", name="Thread", info="Light, inextensible thread. L = from the point of suspension to the centre of the bob.",
              a=[0, 0.6, 0], b="bob", r=0.0015, color="ink"),
            B("lbl", "text", text="Pivot", size=0.04, pos=[0.12, 0.66, 0]),
        ],
        knobs=[knob("L", "Length L", "L", 20, 150, 1, 100, "cm", 0.01),
               knob("amp", "Starting angle", "theta0", 2, 30, 1, 5, "°", DEG, hint="Keep the angle small (< 10°): then T = 2π√(L/g)"),
               knob("g", "Planet's g (Moon 1.6, Earth 9.8, Jupiter 24.8)", "g", 1.6, 24.8, 0.1, 9.8, "m/s²")],
        instruments=[inst("sw", "stopwatch", "Stopwatch (count 20 oscillations)"),
                     inst("ang", "readout", "Angle θ", "theta", k=R2D, unit="°", digits=1),
                     inst("gr", "graph", "θ against time", "theta", k=R2D, xlabel="t (s)")],
        table={"columns": [col("L", "L", "knob:L", "cm", 0.01), col("T", "T = t₂₀ ÷ 20", "inst:sw", "s", div=20, digits=3)],
               "calc": "pendulum_g", "rows_min": 3, "truth": "p.g", "result_digits": 2,
               "hint": "For each L: start the stopwatch, count 20 oscillations, stop it, then tap 'Record reading'."},
        steps=["Set the length L = 100 cm and the angle to 5°.", "Tap Run; start the stopwatch when the bob is at one end.",
               "Count 20 full oscillations, stop the stopwatch and record the reading.",
               "Repeat with L = 80, 60 and 40 cm.", "Read the average g = 4π²L/T² from the table."],
        theory="For small angles, the time period of a simple pendulum is T = 2π√(L/g). So T² is proportional to L, "
               "and the slope of the T² vs L graph is 4π²/g. The mass of the bob does not change T.",
        safety="In a real lab, keep the stand firm on the table and do not swing the bob hard.",
        tour=[{"cam": [0.5, 0.0, 2.7], "look": [0, -0.15, 0], "say": "This is a simple pendulum: a heavy bob hanging from a thread. The clamp at the top is the pivot."},
              {"cam": [0.25, 0.1, 1.2], "look": [0, -0.35, 0], "say": "We release the bob at 5 degrees. Watch: one oscillation takes about two seconds.", "run": True},
              {"set": {"L": 40}, "say": "Now the length is 40 centimetres. The swings are faster: T got shorter, because T changes with the square root of L."},
              {"set": {"g": 1.6}, "say": "This is the Moon's g. There the pendulum swings very slowly."},
              {"set": {"g": 9.8, "L": 100}, "say": "Now open the Table tab and record the time for 20 oscillations at each length. Hoola will work out g."}],
        questions=[{"q": "If the length is made 4 times longer, what happens to T?", "options": ["2 times", "4 times", "Unchanged", "16 times"], "answer": 0,
                    "why": "T ∝ √L, and √4 = 2."},
                   {"q": "What happens to T with a heavier bob?", "options": ["Increases", "Decreases", "Does not change"], "answer": 2,
                    "why": "Mass does not appear in T = 2π√(L/g)."}],
        sources=[S11, SIM],
        check={"params": {"L": 1.0, "theta0": 0.0873}, "reading": "T", "textbook": "pendulum_T"},
    )


def _spring_bodies(name_info: str) -> list[dict]:
    return [
        B("stand", "box", name="Stand", size=[0.04, 0.9, 0.04], pos=[-0.25, 0.15, 0], color="steel"),
        B("base", "box", size=[0.6, 0.04, 0.35], pos=[-0.1, -0.32, 0], color="wood"),
        B("arm", "box", size=[0.3, 0.02, 0.03], pos=[-0.1, 0.6, 0], color="steel"),
        B("hook", "box", size=[0.03, 0.02, 0.03], pos=[0, 0.59, 0], color="black"),
        B("pan", "cylinder", name="Hanger + masses", info=name_info, r=0.03, h=0.03, pos=[0, 0.58, 0], color="brass",
          bind={"y": "bob_y"}),
        B("spring", "spring", name="Spring", info="Hooke's law: restoring force F = k x (within the elastic limit).",
          a=[0, 0.58, 0], b={"body": "pan", "off": [0, 0.015, 0]}, r=0.018, turns=16, wire=0.0018, color="steel"),
        B("ptr", "box", name="Pointer", size=[0.06, 0.003, 0.003], pos=[-0.06, 0.58, 0], color="red", bind={"y": "bob_y"}),
        B("ruler", "scale", name="Metre scale (cm)", length=0.6, spacing=0.01, major=10, labels=True, label_step=10,
          tick=0.012, font=0.02, pos=[-0.1, 0.58, 0.001], rot=[0, 0, -1.5708]),
    ]


def hooke() -> dict:
    return lab(
        id="hookes-law", title="Hooke's law: spring constant", group="Physics · Mechanics", level="Class XI",
        topic="Mechanical Properties of Solids", aim="Add masses, measure the extension of the spring and find the spring constant k.",
        kernel="spring", params={"c": 0.6, "x0": 0.0}, autorun=True,
        camera={"pos": [0.35, 0.25, 1.3], "look": [-0.05, 0.25, 0]}, floor=-0.34,
        bodies=_spring_bodies("Slotted masses of 50 g each."),
        knobs=[knob("m", "Mass hung", "m", 50, 500, 50, 100, "g", 0.001),
               knob("k", "Change the spring (k hidden)", "k", 10, 40, 1, 20, "N/m", hidden=True)],
        instruments=[inst("ext", "readout", "Extension (pointer on the scale)", "ext", k=100, unit="cm", lc=0.1, digits=1),
                     inst("gr", "graph", "Extension vs mass", "ext", k=100, x="knob:m", xlabel="m (g)", dots=True)],
        table={"columns": [col("m", "Mass m", "knob:m", "g", 0.001), col("ext", "Extension x", "inst:ext", "cm", 0.01, digits=1)],
               "calc": "spring_k_static", "rows_min": 3, "truth": "p.k", "result_digits": 1,
               "hint": "After each mass, wait for the pointer to settle, then record the reading."},
        steps=["Note the pointer position with no mass.", "Hang 50 g, 100 g, 150 g...",
               "Each time the pointer settles, record the extension.", "Is the graph a straight line? Its slope gives k = mg/x."],
        theory="Within the elastic limit, the extension x of a spring is proportional to the load: mg = k x. The x vs m graph is a straight line.",
        safety="Do not stretch the spring beyond its limit: it will not return fully.",
        tour=[{"say": "The spring hangs from the stand; masses go on the hanger below. The pointer shows the extension on the scale."},
              {"set": {"m": 300}, "say": "300 grams: the spring stretched more. Twice the load, twice the extension."},
              {"set": {"m": 100}, "say": "Now record the extension for each mass in the Table. Hoola will work out k."}],
        questions=[{"q": "If the load is made 3 times larger, the extension is?", "options": ["3 times", "9 times", "Unchanged"], "answer": 0,
                    "why": "mg = kx: x is proportional to the load."}],
        sources=[S11, SIM],
        check={"params": {"m": 0.2, "c": 0.6, "x0": 0.0}, "reading": "ext", "textbook": "spring_ext"},
    )


def shm() -> dict:
    return lab(
        id="spring-oscillation", title="Spring-mass oscillation: T and m", group="Physics · Mechanics", level="Class XI",
        topic="Oscillations", aim="Measure the time period of a mass oscillating on a spring and find k (T = 2π√(m/k)).",
        kernel="spring", params={"c": 0.0, "x0": 0.03}, speeds=[0.25, 0.5, 1, 2],
        camera={"pos": [0.35, 0.25, 1.3], "look": [-0.05, 0.25, 0]}, floor=-0.34,
        bodies=_spring_bodies("The mass is pulled down 3 cm and released."),
        knobs=[knob("m", "Mass m", "m", 50, 500, 50, 200, "g", 0.001),
               knob("k", "Change the spring (k hidden)", "k", 10, 40, 1, 20, "N/m", hidden=True)],
        instruments=[inst("sw", "stopwatch", "Stopwatch (10 oscillations)"),
                     inst("gr", "graph", "x against time", "x", k=100, xlabel="t (s)")],
        table={"columns": [col("m", "m", "knob:m", "g", 0.001), col("T", "T = t₁₀ ÷ 10", "inst:sw", "s", div=10, digits=3)],
               "calc": "spring_k_shm", "rows_min": 3, "truth": "p.k", "result_digits": 1},
        steps=["Set the mass to 200 g and tap Run.", "Time 10 oscillations and record the reading.",
               "Change the mass and repeat.", "Read the average k = 4π²m/T²."],
        theory="A mass hanging on a spring performs simple harmonic motion (SHM): T = 2π√(m/k). A heavier mass oscillates more slowly.",
        tour=[{"say": "The mass was pulled down 3 centimetres and released. Watch: a steady up-and-down oscillation.", "run": True},
              {"set": {"m": 450}, "say": "A heavier mass: slower oscillation. T grows with the square root of the mass."}],
        questions=[{"q": "If the mass is made 4 times larger, T becomes?", "options": ["2 times", "4 times", "Half"], "answer": 0,
                    "why": "T ∝ √m."}],
        sources=[S11, SIM],
        check={"params": {"m": 0.2}, "reading": "T", "textbook": "spring_T"},
    )


def incline() -> dict:
    return lab(
        id="inclined-plane-friction", title="Inclined plane and friction", group="Physics · Mechanics", level="Class XI",
        topic="Laws of Motion", aim="Find the least force that moves a block up an inclined plane and work out the coefficient of friction μ.",
        kernel="incline", params={"len": 1.4}, autorun=True,
        camera={"pos": [0.3, 0.2, 2.2], "look": [0.1, -0.1, 0]}, floor=-0.62,
        bodies=[
            B("table", "box", name="Table", size=[2.0, 0.04, 0.6], pos=[0.2, -0.6, 0], color="wood", cut=False),
            B("pivot", "box", size=[0.02, 0.02, 0.32], pos=[-0.6, -0.56, 0], color="black", bind={"rz": "p.angle"}),
            B("plank", "box", name="Inclined plane (plank)", info="Change its angle θ with the knob.", size=[1.5, 0.03, 0.3],
              pos=[0.75, 0, 0], parent="pivot", color="wood"),
            B("block", "box", name="Wooden block", info="The block stays at rest as long as friction can hold it.",
              size=[0.12, 0.08, 0.1], pos=[0, 0.055, 0], parent="pivot", color="#8c5a2b", bind={"x": "s"}),
            B("pulley", "torus", name="Pulley", r=0.03, tube=0.008, pos=[1.52, 0.03, 0], parent="pivot", color="steel"),
            B("hanger", "box", size=[0.001, 0.001, 0.001], pos=[1.52, 0.03, 0], parent="pivot", bind={"rz": {"var": "p.angle", "k": -1}}),
            B("pan", "cylinder", name="Pan + masses", info="The weight in the pan pulls the block up the slope through the thread.", r=0.05,
              h=0.02, pos=[0.035, -0.4, 0], parent="hanger", color="brass"),
            B("str1", "rope", a={"body": "block", "off": [0.06, 0, 0]}, b={"body": "pulley", "off": [0, 0.03, 0]}, r=0.0012, color="ink"),
            B("str2", "rope", a={"body": "pulley", "off": [0.03, 0, 0]}, b={"body": "pan", "off": [0, 0.01, 0]}, r=0.0012, color="ink"),
        ],
        knobs=[knob("ang", "Angle of the plane θ", "angle", 5, 45, 1, 20, "°", DEG, reset=True),
               knob("F", "Mass in the pan", "F", 0, 1200, 10, 0, "g", 0.0098, reset=True,
                    hint="Increase slowly; record the mass at which the block just starts moving up."),
               knob("mu", "Surface (μ hidden)", "mu", 0.1, 0.6, 0.05, 0.3, hidden=True, reset=True)],
        instruments=[inst("mv", "readout", "Is the block moving? (1 = yes)", "moving", digits=0),
                     inst("acc", "readout", "Acceleration a", "a", unit="m/s²", digits=2)],
        table={"columns": [col("angle", "Angle θ", "knob:ang", "°", DEG, digits=0), col("F", "Least mass", "knob:F", "g", 0.0098, digits=0)],
               "calc": "incline_mu", "rows_min": 2, "truth": "p.mu", "result_digits": 2},
        steps=["Set the angle to 20°.", "Increase the mass in the pan in 10 g steps.", "Record the mass at which the block starts moving up.",
               "Repeat at 25° and 30°.", "Read the average μ = (F - mg sinθ)/(mg cosθ)."],
        theory="The force needed to move the block up the plane is F = mg(sinθ + μcosθ). Friction acts along the surface, against the motion. "
               "In this lab the static and kinetic friction coefficients are taken as the same μ.",
        tour=[{"say": "A 1 kilogram block on an inclined plane. The thread runs over the pulley to the pan."},
              {"set": {"F": 500}, "say": "500 grams: the block is still at rest. Friction and part of its weight hold it back."},
              {"set": {"F": 800}, "say": "800 grams: now the block moves up. The limit lies in between: that is what we measure."}],
        questions=[{"q": "When the angle increases, the mass needed to move the block up is?", "options": ["More", "Less", "The same"],
                    "answer": 0, "why": "sinθ grows: the part of the weight pulling down the slope grows."}],
        sources=[S11, SIM],
        check={"params": {"angle": 0.3491}, "reading": "F_min", "textbook": "incline_Fmin"},
    )


def stokes() -> dict:
    return lab(
        id="terminal-velocity", title="Stokes' law: terminal velocity", group="Physics · Mechanics", level="Class XI",
        topic="Mechanical Properties of Fluids", aim="Measure the terminal velocity of a steel ball falling through glycerine and find the viscosity η.",
        kernel="stokes", speeds=[1, 5, 20, 50], speed=5,
        camera={"pos": [0.4, -0.3, 1.5], "look": [0, -0.4, 0]}, floor=-1.0,
        bodies=[
            B("jar", "cylinder", name="Glycerine jar", info="A tall, wide jar: the walls have little effect.", r=0.05, h=0.9, open=True,
              pos=[0, -0.45, 0], color="glass", opacity=0.25),
            B("liq", "cylinder", name="Glycerine", r=0.048, h=0.86, pos=[0, -0.47, 0], color="glycerine", opacity=0.35),
            B("m1", "torus", name="First mark (0.30 m)", r=0.052, tube=0.002, pos=[0, -0.3, 0], rot=[1.5708, 0, 0], color="red"),
            B("m2", "torus", name="Second mark (0.60 m)", r=0.052, tube=0.002, pos=[0, -0.6, 0], rot=[1.5708, 0, 0], color="red"),
            B("ball", "sphere", name="Steel ball", info="Drawn 10 times larger so you can see it.", r=0.01, pos=[0, 0, 0],
              color="steel", bind={"y": "ball_y", "sx": {"var": "p.r", "k": 1000}, "sy": {"var": "p.r", "k": 1000}, "sz": {"var": "p.r", "k": 1000}}),
            B("base", "box", size=[0.2, 0.02, 0.2], pos=[0, -0.91, 0], color="wood"),
        ],
        knobs=[knob("r", "Ball radius r", "r", 0.5, 3, 0.1, 1, "mm", 0.001, reset=True),
               knob("eta", "Liquid (η hidden)", "eta", 0.5, 2.0, 0.01, 1.49, "Pa·s", hidden=True, reset=True)],
        instruments=[inst("sw", "stopwatch", "Stopwatch (between the two marks)"),
                     inst("v", "readout", "Photogate speed", "v", k=100, unit="cm/s", digits=3)],
        table={"columns": [col("r", "r", "knob:r", "mm", 0.001), col("v", "Terminal velocity", "inst:v", "cm/s", 0.01, digits=3)],
               "calc": "stokes_eta", "rows_min": 2, "truth": "p.eta", "result_digits": 2,
               "hint": "Wait until the ball has passed the first mark (steady speed), then record the reading."},
        steps=["Set r = 1 mm and tap Run.", "Between the two marks the ball falls at a steady speed: time it, or read the photogate.",
               "Record the reading.", "Change r and repeat; v ∝ r²."],
        theory="On the ball act its weight (down), buoyancy and the viscous force 6πηrv (up). When they balance, the terminal velocity is v = 2r²(ρ-σ)g / 9η.",
        tour=[{"say": "Glycerine is a very thick liquid. A steel ball is dropped into it.", "run": True},
              {"say": "Within moments the ball's speed becomes steady: this is the terminal velocity."},
              {"set": {"r": 2}, "say": "Twice the radius: four times the terminal velocity, because v grows with the square of r."}],
        questions=[{"q": "If the radius is doubled, the terminal velocity is?", "options": ["2 times", "4 times", "Unchanged"], "answer": 1, "why": "v ∝ r²."}],
        sources=[S11, SIM],
        check={"params": {"r": 0.001}, "reading": "v_t", "textbook": "stokes_v"},
    )


# ======================================================================================================== HEAT
def _thermo(id, x, var, name) -> list[dict]:
    return [B(id + "_glass", "cylinder", name=name, r=0.006, h=0.3, pos=[x, 0.13, 0], color="glass", opacity=0.35),
            B(id + "_bulb", "sphere", r=0.009, pos=[x, -0.02, 0], color="mercury"),
            B(id + "_hg", "cylinder", r=0.0028, h=0.01, pos=[x, -0.01, 0], color="mercury",
              bind={"sy": {"var": var, "k": 0.25, "min": 0.01}, "y": {"var": var, "k": 0.00125}}),
            B(id + "_sc", "scale", length=0.25, spacing=0.0025, major=10, labels=True, label_step=10, tick=0.006, font=0.012,
              pos=[x + 0.008, -0.01, 0], rot=[0, 0, 1.5708], down=True)]


def cooling() -> dict:
    return lab(
        id="newtons-cooling", title="Newton's law of cooling", group="Physics · Heat", level="Class XI",
        topic="Thermal Properties of Matter", aim="Plot the cooling curve of hot water and find the cooling constant k.",
        kernel="cooling", speed=10, speeds=[1, 5, 10, 30],
        camera={"pos": [0.25, 0.12, 0.6], "look": [0, 0.07, 0]}, floor=-0.1,
        bodies=[
            B("stand", "box", size=[0.3, 0.02, 0.2], pos=[0, -0.08, 0], color="wood"),
            B("beaker", "cylinder", name="Calorimeter / beaker", r=0.06, h=0.14, open=True, pos=[0, 0, 0], color="glass", opacity=0.3),
            B("water", "cylinder", name="Hot water", r=0.057, h=0.11, pos=[0, -0.013, 0], color="water", opacity=0.55),
            *_thermo("t1", 0.02, "T", "Thermometer (0-100 °C)"),
        ],
        knobs=[knob("T0", "Starting temperature", "T0", 60, 95, 1, 90, "°C", reset=True),
               knob("Ts", "Room temperature", "Ts", 15, 40, 1, 30, "°C", reset=True),
               knob("k", "Vessel + air (k hidden)", "k", 0.005, 0.05, 0.001, 0.02, "1/s", hidden=True, reset=True)],
        instruments=[inst("T", "readout", "Thermometer", "T", unit="°C", lc=0.5, digits=1),
                     inst("sw", "stopwatch", "Time"),
                     inst("gr", "graph", "T against time (cooling curve)", "T", xlabel="t (s)")],
        table={"columns": [col("t", "Time t", "inst:sw", "s", digits=0), col("T", "Temperature T", "inst:T", "°C", digits=1)],
               "calc": "cooling_k", "rows_min": 3, "truth": "p.k", "result_digits": 4,
               "hint": "Start the stopwatch together with Run; record a reading every 30-60 s."},
        steps=["Water at 90 °C, room at 30 °C.", "Start Run and the stopwatch together.", "Record T every 30 s (about 10 readings).",
               "Look at the graph: it cools fast at first, then slowly."],
        theory="Newton's law: the rate of cooling dT/dt = -k(T - Ts). So T - Ts falls exponentially with time.",
        tour=[{"say": "Water at 90 degrees in a beaker, the room at 30 degrees. The simulation runs 10 times faster.", "run": True},
              {"say": "At first the water cools quickly, because it differs most from the room. Open the graph."}],
        questions=[{"q": "Does water cool from 90 to 80 °C faster, or from 50 to 40 °C?", "options": ["90 to 80", "50 to 40", "Same"], "answer": 0,
                    "why": "The bigger the difference from the room, the faster it cools."}],
        sources=[S11, SIM],
        check={"params": {}, "reading": "T60", "textbook": "cooling_T60"},
    )


def boyle() -> dict:
    return lab(
        id="boyles-law", title="Boyle's law: P and V", group="Physics · Heat", level="Class XI",
        topic="Kinetic Theory", aim="Change the volume of a gas at constant temperature and measure its pressure: does PV stay constant?",
        kernel="boyle", autorun=True,
        camera={"pos": [0.25, 0.15, 0.7], "look": [0.04, 0.1, 0]}, floor=-0.02,
        bodies=[
            B("base", "box", size=[0.35, 0.02, 0.2], pos=[0.05, -0.01, 0], color="wood"),
            B("barrel", "cylinder", name="Syringe barrel", r=0.03, h=0.3, open=True, pos=[0, 0.15, 0], color="glass", opacity=0.25),
            B("gas", "gas", name="Gas molecules", info="Molecules are illustrative; the pressure comes from the ideal gas law.", size=[0.05, 0.1, 0.05],
              count=60, r=0.004, pos=[0, 0, 0], color="blue", illustrative=True, bind={"h": "piston_h"}),
            B("piston", "cylinder", name="Piston", r=0.029, h=0.01, pos=[0, 0, 0], color="black", bind={"y": "piston_h"}),
            B("prod", "cylinder", r=0.004, h=0.2, pos=[0, 0.105, 0], parent="piston", color="steel"),
            B("dialc", "cylinder", name="Pressure gauge (kPa)", r=0.05, h=0.01, pos=[0.13, 0.08, 0], rot=[1.5708, 0, 0], color="white"),
            B("ring", "torus", r=0.05, tube=0.003, pos=[0.13, 0.08, 0.006], color="ink"),
            B("ndl", "needle", length=0.042, pos=[0.13, 0.08, 0.008], color="red",
              bind={"rz": {"var": "P_kPa", "k": -0.012, "c": 1.2, "min": -1.3, "max": 1.3}}),
            B("lbl", "text", text="kPa", size=0.015, pos=[0.13, 0.055, 0.01]),
        ],
        knobs=[knob("V", "Volume V", "V", 20, 200, 5, 100, "mL", 1e-6),
               knob("T", "Temperature (constant in Boyle's law)", "Temp", 250, 400, 10, 300, "K")],
        instruments=[inst("P", "readout", "Pressure P", "P_kPa", unit="kPa", digits=1),
                     inst("PV", "readout", "P × V", "PV", unit="J", digits=3),
                     inst("gr", "graph", "P vs V", "P_kPa", x="V_mL", xlabel="V (mL)", dots=True)],
        table={"columns": [col("P", "Pressure P", "inst:P", "kPa", 1000, digits=1), col("V", "Volume V", "knob:V", "mL", 1e-6)],
               "calc": "boyle_pv", "rows_min": 3, "result_digits": 3},
        steps=["V = 100 mL: read the pressure and record it.", "Set V to 80, 60, 40 mL; record each time.",
               "Look at the average PV: is it about the same in every reading?", "The P vs V graph is a hyperbola."],
        theory="For a fixed amount of gas at constant temperature, P ∝ 1/V, i.e. PV = nRT is constant. With less room, the molecules hit the walls more often.",
        tour=[{"say": "Gas sealed in a syringe. Pushing the piston down reduces the volume."},
              {"set": {"V": 50}, "say": "Half the volume: twice the pressure. The molecules hit the walls twice as often."},
              {"set": {"V": 100}, "say": "Record P and V in the Table: P times V comes out about the same every time."}],
        questions=[{"q": "If the volume is halved, the pressure becomes?", "options": ["Double", "Half", "Unchanged"], "answer": 0, "why": "PV is constant."}],
        sources=[S11, SIM],
        check={"params": {"V": 5e-5}, "reading": "P", "textbook": "boyle_P"},
    )


def mixtures() -> dict:
    return lab(
        id="specific-heat-mixtures", title="Method of mixtures: specific heat", group="Physics · Heat", level="Class XI",
        topic="Thermal Properties of Matter", aim="Drop a hot metal into water, measure the final temperature and find the metal's specific heat c.",
        kernel="mixtures", speed=20, speeds=[5, 20, 60],
        camera={"pos": [0.25, 0.12, 0.55], "look": [0, 0.05, 0]}, floor=-0.08,
        bodies=[
            B("jacket", "cylinder", name="Outer vessel (insulation)", r=0.07, h=0.12, open=True, pos=[0, 0, 0], color="#cfd4da", opacity=0.25),
            B("cal", "cylinder", name="Copper calorimeter", r=0.05, h=0.1, open=True, pos=[0, -0.005, 0], color="copper", opacity=0.6),
            B("water", "cylinder", name="Water", r=0.048, h=0.07, pos=[0, -0.018, 0], color="water", opacity=0.55),
            B("solid", "box", name="Hot piece of metal", info="Heated to 100 °C in boiling water.", size=[0.03, 0.03, 0.03],
              pos=[-0.015, -0.035, 0], color="steel"),
            B("stir", "cylinder", name="Stirrer", r=0.002, h=0.16, pos=[-0.03, 0.04, 0.02], rot=[0, 0, 0.2], color="copper"),
            *_thermo("tw", 0.025, "Tw", "Thermometer: water"),
        ],
        knobs=[knob("m1", "Mass of the metal", "m1", 50, 200, 10, 100, "g", 0.001, reset=True),
               knob("T1", "Temperature of the metal", "T1", 60, 100, 1, 100, "°C", reset=True),
               knob("m2", "Mass of the water", "m2", 100, 250, 10, 150, "g", 0.001, reset=True),
               knob("c1", "Metal (c hidden)", "c1", 380, 900, 10, 900, "J/(kg·K)", hidden=True, reset=True)],
        instruments=[inst("Ts", "readout", "Metal temperature", "Ts", unit="°C", lc=0.1, digits=1),
                     inst("Tw", "readout", "Water + calorimeter", "Tw", unit="°C", lc=0.1, digits=1),
                     inst("gr", "graph", "Water temperature", "Tw", xlabel="t (s)")],
        table={"columns": [col("Tf", "Final temperature", "inst:Tw", "°C", digits=1)], "calc": "mix_c", "rows_min": 1,
               "truth": "p.c1", "result_digits": 0, "hint": "When both temperatures are equal, record Tf."},
        steps=["Metal 100 g at 100 °C; water 150 g at 25 °C.", "Tap Run: the metal is in the water.",
               "Wait until both temperatures meet; record Tf.", "c = (m₂c₂ + m_c c_c)(Tf - T₂) / m₁(T₁ - Tf)."],
        theory="Heat balance: heat given by the metal = heat taken by the water + calorimeter (no heat assumed lost to the outside).",
        safety="In a real lab, lift the hot metal with tongs; boiling water can burn.",
        tour=[{"say": "Water at 25 degrees in a copper calorimeter. A metal at 100 degrees has been dropped in.", "run": True},
              {"say": "The metal cools and the water warms: both will meet at one temperature."}],
        questions=[{"q": "With a metal of lower specific heat (like copper), the water's temperature rises?", "options": ["Less", "More", "The same"],
                    "answer": 0, "why": "A lower c stores less heat, so it warms the water less."}],
        sources=[S11, SIM],
        check={"params": {}, "reading": "Tf", "textbook": "mix_Tf"},
    )


# ======================================================================================================== WAVES
def resonance() -> dict:
    return lab(
        id="resonance-tube", title="Resonance tube: speed of sound", group="Physics · Waves", level="Class XI",
        topic="Waves", aim="Change the water level to find two resonance lengths l₁, l₂ and work out v = 2f(l₂ - l₁).",
        kernel="resonance", params={"h": 0.1}, autorun=True,
        camera={"pos": [0.45, -0.3, 1.5], "look": [0.05, -0.45, 0]}, floor=-1.05,
        bodies=[
            B("tube", "cylinder", name="Resonance tube", info="Water from below: open at the top, closed by the water.", r=0.02, h=1.0, open=True,
              pos=[0, -0.5, 0], color="glass", opacity=0.25),
            B("water", "cylinder", name="Water level", r=0.019, h=1.0, pos=[0, -0.5, 0], color="water", opacity=0.6,
              bind={"y": {"var": "p.h", "k": -0.5}, "sy": {"var": "p.h", "k": -1, "c": 1}}),
            B("fork1", "box", name="Tuning fork", info="It sounds a single frequency f.", size=[0.006, 0.1, 0.006], pos=[-0.012, 0.08, 0], color="steel"),
            B("fork2", "box", size=[0.006, 0.1, 0.006], pos=[0.012, 0.08, 0], color="steel"),
            B("forkb", "box", size=[0.03, 0.008, 0.006], pos=[0, 0.03, 0], color="steel"),
            B("forkh", "cylinder", r=0.003, h=0.05, pos=[0, 0.005, 0], color="steel"),
            B("ruler", "scale", name="Metre scale (cm)", length=1.0, spacing=0.01, major=10, labels=True, label_step=10, tick=0.01, font=0.02,
              pos=[0.03, 0, 0], rot=[0, 0, -1.5708]),
            B("lvl", "box", name="Water mark", size=[0.06, 0.002, 0.002], pos=[0.03, 0, 0], color="red", bind={"y": {"var": "p.h", "k": -1}}),
            *dial("db", [0.25, -0.35, 0], "Loudness meter", "When the air column resonates, the sound is loudest."),
            needle("dbn", [0.25, -0.35, 0], "loud", -2.4, 1.2),
            B("stand", "box", size=[0.3, 0.03, 0.3], pos=[0, -1.02, 0], color="wood"),
        ],
        knobs=[knob("h", "Air column (down to the water)", "h", 2, 95, 0.1, 10, "cm", 0.01,
                    hint="Lower it slowly; record where the sound is loudest."),
               knob("f", "Tuning fork", "f", 256, 512, 1, 512, "Hz"),
               knob("Tc", "Room temperature", "Tc", 0, 40, 1, 20, "°C")],
        instruments=[inst("ld", "meter", "Loudness", "loud", range=[0, 1], digits=2),
                     inst("gr", "graph", "Loudness vs air column", "loud", x="p.h", xk=100, xlabel="h (cm)", dots=True)],
        table={"columns": [col("h", "Resonance length", "knob:h", "cm", 0.01, digits=1)], "calc": "res_v", "rows_min": 2,
               "result_digits": 1, "hint": "Record both the first loud sound (l₁) and the second (l₂)."},
        steps=["Fork 512 Hz, air column 10 cm.", "Slowly lengthen the column; record at the first loud sound (l₁ ≈ 15-16 cm).",
               "Go further; record at the second loud sound (l₂ ≈ 49 cm).", "v = 2f(l₂ - l₁): the end correction cancels out."],
        theory="In a tube closed at one end, resonance happens when l + e = λ/4, 3λ/4, ... (e = 0.3d end correction). "
               "So l₂ - l₁ = λ/2 and v = fλ = 2f(l₂ - l₁). At 0 °C v = 331.3 m/s; it rises by about 0.6 m/s per °C.",
        tour=[{"say": "The tube holds water; a tuning fork sounds at the top. Lowering the water lengthens the air column."},
              {"set": {"h": 15.6}, "say": "The sound is loudest here: the first resonance. The air column is about a quarter of a wavelength."},
              {"set": {"h": 49.1}, "say": "This is the second resonance. The difference between the two is half a wavelength: it gives the speed of sound."}],
        questions=[{"q": "If the room gets warmer, the resonance length?", "options": ["Increases", "Decreases", "Stays the same"], "answer": 0,
                    "why": "In warmer air v is higher, so λ = v/f is longer."}],
        sources=[S11, SIM],
        check={"params": {}, "rows": [{"take": {"l1": "h"}}, {"take": {"l2": "h"}}], "calc": "res_v", "textbook": "sound_v"},
    )


def sonometer() -> dict:
    return lab(
        id="sonometer", title="Sonometer: frequency of a wire", group="Physics · Waves", level="Class XI",
        topic="Waves", aim="Slide the bridge to bring the wire into resonance with a tuning fork; use l and T to find the wire's μ.",
        kernel="sonometer", params={"l": 0.3}, autorun=True,
        camera={"pos": [0.5, 0.4, 1.35], "look": [0.5, -0.05, 0]}, floor=-0.3,
        bodies=[
            B("box", "box", name="Hollow sonometer box", size=[1.1, 0.08, 0.16], pos=[0.47, -0.04, 0], color="wood"),
            B("brA", "box", name="Fixed bridge", size=[0.012, 0.03, 0.12], pos=[0, 0.015, 0], color="#d8c8a8"),
            B("brB", "box", name="Sliding bridge", info="Slide it to change the wire length l.", size=[0.012, 0.03, 0.12],
              pos=[0, 0.015, 0], color="#d8c8a8", bind={"x": "p.l"}),
            B("wire0", "rope", a=[-0.06, 0.03, 0], b=[1.03, 0.03, 0], r=0.0008, color="steel"),
            B("wire", "rope", name="Vibrating wire", a=[0, 0.031, 0], b={"body": "brB", "off": [0, 0.016, 0]}, bow="amp", color="steel"),
            B("rider", "cone", name="Paper rider", info="At resonance it jumps and falls off.", r=0.008, h=0.012,
              pos=[0, 0.04, 0], rot=[3.1416, 0, 0], color="red", bind={"x": {"var": "p.l", "k": 0.5}, "y": {"var": "loud", "k": 0.03}}),
            B("pulley", "torus", r=0.025, tube=0.006, pos=[1.05, 0.005, 0], color="steel"),
            B("hang", "rope", a=[1.075, 0.005, 0], b=[1.075, -0.22, 0], r=0.0008, color="ink"),
            B("wt", "cylinder", name="Hanging mass (tension T)", r=0.025, h=0.06, pos=[1.075, -0.25, 0], color="brass"),
            B("ruler", "scale", length=1.0, spacing=0.01, major=10, labels=True, label_step=10, tick=0.008, font=0.016, pos=[0, 0.0, 0.081]),
            *dial("db", [0.45, -0.2, 0.25], "Resonance meter"),
            needle("dbn", [0.45, -0.2, 0.25], "loud", -2.4, 1.2),
        ],
        knobs=[knob("l", "Length between the bridges l", "l", 10, 90, 0.1, 30, "cm", 0.01),
               knob("Tn", "Hanging mass", "Tn", 1, 6, 0.5, 4, "kg", 9.8),
               knob("f", "Tuning fork", "f", 256, 512, 1, 256, "Hz"),
               knob("mu", "Wire (μ hidden)", "mu", 0.0005, 0.003, 0.0001, 0.001, "kg/m", hidden=True)],
        instruments=[inst("ld", "meter", "Vibration", "loud", range=[0, 1], digits=2)],
        table={"columns": [col("f", "Fork f", "knob:f", "Hz"), col("l", "Resonance length l", "knob:l", "cm", 0.01, digits=1),
                           col("Tn", "Mass", "knob:Tn", "kg", 9.8)],
               "calc": "sono_mu", "rows_min": 2, "truth": "p.mu", "result_digits": 5},
        steps=["Mass 4 kg, fork 256 Hz.", "Slide the bridge: where the rider jumps (meter full), record.",
               "Repeat with other forks (320, 384, 512 Hz): is f × l constant?", "μ = T / (4 l² f²)."],
        theory="The fundamental frequency of a wire is f = (1/2l)√(T/μ). At constant T, f × l is constant; at constant f, l ∝ √T.",
        tour=[{"say": "A sonometer: one wire, two bridges, and a hanging mass that gives the tension."},
              {"set": {"l": 38.7}, "say": "Here the wire resonates with the fork: the rider is jumping."},
              {"set": {"f": 512, "l": 19.3}, "say": "A fork of twice the frequency: half the length. f times l stays constant."}],
        questions=[{"q": "If the tension is made 4 times larger, the resonance length (same fork)?", "options": ["2 times", "4 times", "Half"], "answer": 0,
                    "why": "l ∝ √T."}],
        sources=[S11, SIM],
        check={"params": {}, "reading": "l_res", "textbook": "sono_l"},
    )


# ======================================================================================================== ELECTRICITY
def _wire(id, pts, color="red") -> dict:
    return B(id, "wire", pts=pts, r=0.003, color=color)


def ohm() -> dict:
    net = {"nodes": 4, "els": [
        {"id": "E", "kind": "V", "a": 1, "b": 0, "value": "Eb"}, {"id": "K", "kind": "S", "a": 1, "b": 4, "param": "key"},
        {"id": "AM", "kind": "R", "a": 4, "b": 2, "value": 0.01}, {"id": "RH", "kind": "R", "a": 2, "b": 3, "value": {"param": "Rh", "k": 1, "c": 0.01}},
        {"id": "RX", "kind": "R", "a": 3, "b": 0, "value": "Rx"}, {"id": "VM", "kind": "R", "a": 3, "b": 0, "value": 1e6}]}
    return lab(
        id="ohms-law", title="Ohm's law: V and I", group="Physics · Electricity", level="Class XII",
        topic="Current Electricity", aim="Change the current with a rheostat, measure V and I, and find the wire's resistance R from V/I.",
        kernel="circuit", cfg={"net": net}, params={"Eb": 3.0, "Rh": 10.0, "Rx": 5.0, "key": 1.0}, autorun=True,
        camera={"pos": [0.0, 0.95, 0.95], "look": [0, 0, 0]}, floor=-0.03,
        bodies=[
            board(1.0, 0.75),
            B("bat", "cylinder", name="Battery (3 V)", r=0.03, h=0.12, pos=[-0.38, 0.03, 0.22], rot=[0, 0, 1.5708], color="#2b2f36"),
            *dial("am", [0.0, 0.0, 0.22], "Ammeter (0-1.5 A)", "In series: the whole current passes through it."),
            needle("amn", [0.0, 0.0, 0.22], "I_AM", -1.6, 1.2),
            B("rh", "cylinder", name="Rheostat", info="Slide it to change the resistance, and so the current.", r=0.025, h=0.22,
              pos=[0.35, 0.03, 0.22], rot=[0, 0, 1.5708], color="#c9b07a"),
            B("rhs", "box", name="Rheostat slider", size=[0.02, 0.03, 0.06], pos=[0.25, 0.065, 0.22], color="black",
              bind={"x": {"var": "p.Rh", "k": 0.01}}),
            B("rx", "spring", name="Resistance wire (coil)", info="Its resistance is what we measure.", a=[-0.15, 0.03, -0.12], b=[0.15, 0.03, -0.12],
              r=0.012, turns=18, wire=0.0015, color="copper"),
            *dial("vm", [0.0, 0.0, -0.3], "Voltmeter (0-3 V)", "In parallel with the wire: the potential difference across it."),
            needle("vmn", [0.0, 0.0, -0.3], "V_VM", -0.8, 1.2),
            _wire("w1", [[-0.32, 0.03, 0.22], [-0.06, 0.03, 0.22]]), _wire("w2", [[0.06, 0.03, 0.22], [0.24, 0.03, 0.22]]),
            _wire("w3", [[0.46, 0.03, 0.22], [0.46, 0.03, -0.12], [0.15, 0.03, -0.12]]),
            _wire("w4", [[-0.15, 0.03, -0.12], [-0.44, 0.03, -0.12], [-0.44, 0.03, 0.22]], "black"),
            _wire("w5", [[-0.15, 0.03, -0.12], [-0.06, 0.03, -0.3]], "black"), _wire("w6", [[0.15, 0.03, -0.12], [0.06, 0.03, -0.3]]),
        ],
        knobs=[knob("Rh", "Rheostat", "Rh", 0, 20, 0.5, 10, "Ω"), knob("key", "Key (0 open / 1 closed)", "key", 0, 1, 1, 1),
               knob("Rx", "Change the wire (R hidden)", "Rx", 2, 10, 0.5, 5, "Ω", hidden=True)],
        instruments=[inst("I", "readout", "Ammeter", "I_AM", unit="A", lc=0.01, digits=2),
                     inst("V", "readout", "Voltmeter", "V_VM", unit="V", lc=0.01, digits=2),
                     inst("gr", "graph", "V vs I", "V_VM", x="I_AM", xlabel="I (A)", dots=True)],
        table={"columns": [col("V", "V", "inst:V", "V", digits=2), col("I", "I", "inst:I", "A", digits=2)], "calc": "ohm_R",
               "rows_min": 3, "truth": "p.Rx", "result_digits": 2},
        steps=["Close the key.", "Start with the rheostat at 20 Ω: record V and I.", "Rheostat at 15, 10, 5 Ω: record each time.",
               "The V vs I graph is a straight line: its slope = R."],
        theory="Ohm's law: at constant temperature V = IR. The ammeter goes in series (very low resistance), the voltmeter in parallel (very high).",
        safety="In a real circuit do not leave the current on for long: the wire heats up and R changes.",
        tour=[{"say": "Battery, key, ammeter, rheostat and wire: all in series. The voltmeter is in parallel with the wire."},
              {"set": {"Rh": 2}, "say": "Rheostat turned down: the current rose, and so did the voltage across the wire."},
              {"set": {"Rh": 10}, "say": "In every reading V divided by I comes out about the same: that is R."}],
        questions=[{"q": "What happens if the voltmeter is connected in series?", "options": ["The current almost stops", "Nothing changes", "The current rises"],
                    "answer": 0, "why": "A voltmeter has a very high resistance."}],
        sources=[S12, SIM],
        check={"params": {"key": 1.0}, "measure": {"mode": "ratio", "num": "V_VM", "den": "I_AM", "as": "R", "vars": []},
               "reading": "R", "textbook": "ohm_R"},
    )


def meter_bridge() -> dict:
    net = {"nodes": 4, "els": [
        {"id": "E", "kind": "V", "a": 1, "b": 4, "value": 2.0}, {"id": "K", "kind": "S", "a": 4, "b": 0, "param": "key"},
        {"id": "WA", "kind": "R", "a": 1, "b": 2, "value": {"param": "lj", "k": 2.0}},
        {"id": "WB", "kind": "R", "a": 2, "b": 0, "value": {"param": "lj", "k": -2.0, "c": 2.0}},
        {"id": "RK", "kind": "R", "a": 1, "b": 3, "value": "Rk"}, {"id": "SX", "kind": "R", "a": 3, "b": 0, "value": "Sx"},
        {"id": "G", "kind": "R", "a": 3, "b": 2, "value": 50.0}]}
    return lab(
        id="meter-bridge", title="Meter bridge: unknown resistance", group="Physics · Electricity", level="Class XII",
        topic="Current Electricity", aim="Slide the jockey until the galvanometer reads zero (the null point) and find S = R(100 - l)/l.",
        kernel="circuit", cfg={"net": net}, params={"lj": 0.5, "Rk": 4.0, "Sx": 6.0, "key": 1.0}, autorun=True,
        camera={"pos": [0.0, 0.7, 0.8], "look": [0, 0, 0.02]}, floor=-0.03,
        bodies=[
            board(1.25, 0.6),
            B("strip", "box", name="Copper strips", size=[1.1, 0.006, 0.03], pos=[0, 0.006, -0.12], color="copper"),
            B("wire", "rope", name="1 m manganin wire", a=[-0.5, 0.012, 0.05], b=[0.5, 0.012, 0.05], r=0.0012, color="steel"),
            B("ruler", "scale", name="Metre scale", length=1.0, spacing=0.01, major=10, labels=True, label_step=10, tick=0.012, font=0.02,
              pos=[-0.5, 0.002, 0.09], rot=[-1.5708, 0, 0]),
            B("jockey", "cone", name="Jockey", info="Touch the wire lightly: do not press, scraping changes R.", r=0.01, h=0.05,
              pos=[-0.5, 0.04, 0.05], rot=[3.1416, 0, 0], color="brass", bind={"x": "p.lj"}),
            B("rk", "box", name="Resistance box R", info="A known resistance: choose it with the knob.", size=[0.14, 0.05, 0.08], pos=[-0.25, 0.025, -0.2], color="#2b2f36"),
            B("sx", "spring", name="Unknown wire S", a=[0.18, 0.02, -0.2], b=[0.32, 0.02, -0.2], r=0.01, turns=14, wire=0.0015, color="copper"),
            *dial("g", [0.0, 0.0, -0.2], "Galvanometer", "At zero (the null point) no current flows."),
            needle("gn", [0.0, 0.0, -0.2], "I_G", -40000.0),
            B("bat", "cylinder", name="Cell + key", r=0.025, h=0.1, pos=[0, 0.025, 0.24], rot=[0, 0, 1.5708], color="#2b2f36"),
            _wire("w1", [[-0.55, 0.015, -0.12], [-0.55, 0.015, 0.24], [-0.05, 0.015, 0.24]]),
            _wire("w2", [[0.55, 0.015, -0.12], [0.55, 0.015, 0.24], [0.05, 0.015, 0.24]], "black"),
            B("gw", "rope", a=[0.0, 0.04, -0.15], b={"body": "jockey", "off": [0, -0.02, 0]}, r=0.0012, color="ink"),
        ],
        knobs=[knob("lj", "Jockey position l", "lj", 1, 99, 0.1, 50, "cm", 0.01, hint="Where does the galvanometer read zero?"),
               knob("Rk", "Resistance box R", "Rk", 1, 20, 1, 4, "Ω"),
               knob("Sx", "Unknown wire (S hidden)", "Sx", 2, 15, 0.5, 6, "Ω", hidden=True)],
        instruments=[inst("G", "readout", "Galvanometer", "I_G", k=1e6, unit="µA", digits=1),
                     inst("gm", "meter", "Galvanometer (|current|, lower is better)", "I_G", k=-1e5, range=[-1, 1], digits=2)],
        table={"columns": [col("R", "R", "knob:Rk", "Ω"), col("l", "Null point l", "knob:lj", "cm", 0.01, digits=1)], "calc": "bridge_S",
               "rows_min": 2, "truth": "p.Sx", "result_digits": 2},
        steps=["Choose R = 4 Ω.", "Slide the jockey: where does the galvanometer read zero?", "Record the null point l.",
               "Change R (keep the null point between 30 and 70 cm) and repeat.", "Average S = R(100 - l)/l."],
        theory="A meter bridge is a Wheatstone bridge: at the null point R/S = l/(100 - l). The error is smallest when the null point is near the middle.",
        tour=[{"say": "A one-metre wire, a resistance box R on one side, the unknown wire S on the other, and a galvanometer between them."},
              {"set": {"lj": 40}, "say": "At 40 centimetres the galvanometer reads almost zero: this is the null point."},
              {"set": {"lj": 70}, "say": "Here current flows: the needle swings to one side. At the null point R over S equals l over 100 minus l."}],
        questions=[{"q": "At the null point, the current through the galvanometer is?", "options": ["Zero", "The largest", "Equal to the battery's"], "answer": 0,
                    "why": "Points B and J are at the same potential."}],
        sources=[S12, SIM],
        check={"params": {"Rk": 4.0, "Sx": 6.0}, "measure": {"mode": "null", "param": "lj", "var": "I_G", "lo": 0.01, "hi": 0.99},
               "reading": "lj", "textbook": "bridge_l"},
    )


def potentiometer() -> dict:
    net = {"nodes": 6, "els": [
        {"id": "E0", "kind": "V", "a": 3, "b": 0, "value": "E0"}, {"id": "RH", "kind": "R", "a": 3, "b": 1, "value": "Rh"},
        {"id": "WA", "kind": "R", "a": 1, "b": 2, "value": {"param": "lj", "k": 4.0}},
        {"id": "WB", "kind": "R", "a": 2, "b": 0, "value": {"param": "lj", "k": -4.0, "c": 4.0}},
        {"id": "EC", "kind": "V", "a": 1, "b": 4, "value": "Ec"}, {"id": "RI", "kind": "R", "a": 4, "b": 5, "value": "r_int"},
        {"id": "G", "kind": "R", "a": 5, "b": 2, "value": 50.0}, {"id": "K2", "kind": "S", "a": 5, "b": 6, "param": "k2"},
        {"id": "RB", "kind": "R", "a": 6, "b": 1, "value": "Rb"}]}
    return lab(
        id="potentiometer-internal-resistance", title="Potentiometer: internal resistance of a cell", group="Physics · Electricity",
        level="Class XII", topic="Current Electricity",
        aim="Find two balancing lengths l₁, l₂ with K₂ open and closed; r = R(l₁ - l₂)/l₂.",
        kernel="circuit", cfg={"net": net}, params={"lj": 0.3, "E0": 6.0, "Rh": 2.0, "Ec": 1.5, "r_int": 1.0, "Rb": 10.0, "k2": 0.0},
        autorun=True, camera={"pos": [0.0, 0.7, 0.85], "look": [0, 0, 0]}, floor=-0.03,
        bodies=[
            board(1.25, 0.65),
            B("wire", "rope", name="Potentiometer wire (4 m, drawn shorter)", a=[-0.5, 0.012, 0.05], b=[0.5, 0.012, 0.05], r=0.0012, color="steel"),
            B("ruler", "scale", name="Scale (0-400 cm)", length=1.0, spacing=0.0125, major=8, labels=True, label_step=50, tick=0.012,
              font=0.02, pos=[-0.5, 0.002, 0.09], rot=[-1.5708, 0, 0]),
            B("jockey", "cone", name="Jockey", r=0.01, h=0.05, pos=[-0.5, 0.04, 0.05], rot=[3.1416, 0, 0], color="brass", bind={"x": "p.lj"}),
            B("drv", "box", name="Driver battery (6 V) + rheostat", size=[0.2, 0.05, 0.08], pos=[-0.35, 0.025, 0.25], color="#2b2f36"),
            B("cell", "cylinder", name="Cell under test (Leclanché)", info="Its internal resistance r is what we measure.", r=0.025, h=0.09,
              pos=[-0.3, 0.025, -0.2], rot=[0, 0, 1.5708], color="#5b3a1e"),
            B("rb", "box", name="Resistance box R + key K₂", size=[0.14, 0.05, 0.08], pos=[0.3, 0.025, -0.2], color="#2b2f36"),
            *dial("g", [0.0, 0.0, -0.2], "Galvanometer"), needle("gn", [0.0, 0.0, -0.2], "I_G", -40000.0),
            B("gw", "rope", a=[0.0, 0.04, -0.15], b={"body": "jockey", "off": [0, -0.02, 0]}, r=0.0012, color="ink"),
            _wire("w1", [[-0.5, 0.015, 0.05], [-0.55, 0.015, 0.05], [-0.55, 0.015, 0.25], [-0.45, 0.015, 0.25]]),
            _wire("w2", [[0.5, 0.015, 0.05], [0.55, 0.015, 0.05], [0.55, 0.015, 0.25], [-0.25, 0.015, 0.25]], "black"),
            _wire("w3", [[-0.55, 0.015, 0.05], [-0.55, 0.015, -0.2], [-0.345, 0.015, -0.2]]),
            _wire("w4", [[-0.255, 0.015, -0.2], [-0.06, 0.015, -0.2]], "black"),
        ],
        knobs=[knob("lj", "Jockey position l", "lj", 4, 396, 0.5, 120, "cm", 0.0025),
               knob("k2", "Key K₂ (0 open / 1 closed)", "k2", 0, 1, 1, 0),
               knob("Rb", "Resistance box R", "Rb", 2, 20, 1, 10, "Ω"),
               knob("ri", "Cell (r hidden)", "r_int", 0.5, 3, 0.1, 1, "Ω", hidden=True)],
        instruments=[inst("G", "readout", "Galvanometer", "I_G", k=1e6, unit="µA", digits=1)],
        table={"columns": [col("k2", "K₂", "knob:k2", digits=0), col("l", "Balancing length", "knob:lj", "cm", 0.0025, digits=1)],
               "calc": "pot_r", "rows_min": 2, "truth": "p.r_int", "result_digits": 2,
               "hint": "Record the balance l₁ with K₂ open (0); then record the balance l₂ with K₂ closed (1)."},
        steps=["Keep K₂ open. Slide the jockey until the galvanometer reads zero: record l₁ (K₂ = 0).",
               "Close K₂ (R = 10 Ω). Record the new balance l₂ (K₂ = 1).", "r = R(l₁ - l₂)/l₂.", "Change R and repeat."],
        theory="A potentiometer draws no current, so at balance the cell's full emf E = k l₁. With the shunt R the terminal voltage V = k l₂. "
               "r = R(E/V - 1) = R(l₁ - l₂)/l₂.",
        tour=[{"say": "A long wire carries a steady current. The cell under test connects to the jockey through the galvanometer."},
              {"set": {"lj": 150}, "say": "At balance the galvanometer reads zero: no current from the cell, so we measure its full emf."},
              {"set": {"k2": 1}, "say": "K2 closed: current flows from the cell, voltage drops across its internal resistance, and the balance comes earlier."}],
        questions=[{"q": "When K₂ is closed, the balancing length?", "options": ["Decreases", "Increases", "Stays the same"], "answer": 0,
                    "why": "The terminal voltage is less than the emf."}],
        sources=[S12, SIM],
        check={"params": {}, "rows": [
            {"set": {"k2": 0}, "measure": {"mode": "null", "param": "lj", "var": "I_G"}, "take": {"lj": "l"}, "add": {"k2": 0}},
            {"set": {"k2": 1}, "measure": {"mode": "null", "param": "lj", "var": "I_G"}, "take": {"lj": "l"}, "add": {"k2": 1}}],
            "calc": "pot_r", "textbook": "pot_r"},
    )


def diode() -> dict:
    net = {"nodes": 2, "els": [
        {"id": "E", "kind": "V", "a": 1, "b": 0, "value": "Eb"}, {"id": "R", "kind": "R", "a": 1, "b": 2, "value": "Rs"},
        {"id": "D1", "kind": "D", "a": 2, "b": 0, "Is": "Is", "n": "nD"}, {"id": "VM", "kind": "R", "a": 2, "b": 0, "value": 1e6}]}
    return lab(
        id="pn-junction-diode", title="p-n diode: forward I-V", group="Physics · Electricity", level="Class XII",
        topic="Semiconductor Electronics", aim="Raise the voltage in forward bias, measure the diode current and find the knee voltage.",
        kernel="circuit", cfg={"net": net}, params={"Eb": 0.5, "Rs": 100.0, "Is": 7e-9, "nD": 1.8}, autorun=True,
        camera={"pos": [0.0, 0.6, 0.65], "look": [0, 0, 0]}, floor=-0.03,
        bodies=[
            board(0.9, 0.6),
            B("bat", "box", name="Variable DC source", size=[0.16, 0.06, 0.1], pos=[-0.3, 0.03, 0.18], color="#2b2f36"),
            B("rs", "box", name="Resistor 100 Ω", info="Limits the current.", size=[0.06, 0.012, 0.012], pos=[0.0, 0.02, 0.18], color="#d9b46a"),
            B("dio", "cylinder", name="Silicon diode", info="The black band = cathode (n-side).", r=0.008, h=0.05, pos=[0.25, 0.02, 0.0],
              rot=[1.5708, 0, 0], color="black"),
            B("band", "cylinder", r=0.0085, h=0.006, pos=[0.25, 0.02, -0.018], rot=[1.5708, 0, 0], color="white"),
            *dial("ma", [0.0, 0.0, -0.18], "Milliammeter (0-25 mA)"), needle("man", [0.0, 0.0, -0.18], "I_D1", -96.0, 1.2),
            *dial("vm", [0.3, 0.0, -0.2], "Voltmeter (0-1 V)"), needle("vmn", [0.3, 0.0, -0.2], "V_D1", -2.4, 1.2),
            _wire("w1", [[-0.22, 0.02, 0.18], [-0.03, 0.02, 0.18]]), _wire("w2", [[0.03, 0.02, 0.18], [0.25, 0.02, 0.18], [0.25, 0.02, 0.025]]),
            _wire("w3", [[0.25, 0.02, -0.025], [0.25, 0.02, -0.08], [-0.38, 0.02, -0.08], [-0.38, 0.02, 0.18]], "black"),
        ],
        knobs=[knob("Eb", "Source voltage", "Eb", 0, 3, 0.05, 0.5, "V")],
        instruments=[inst("V", "readout", "Voltage across the diode", "V_D1", unit="V", lc=0.01, digits=2),
                     inst("I", "readout", "Current", "I_D1", k=1000, unit="mA", digits=2),
                     inst("gr", "graph", "I vs V (characteristic)", "I_D1", k=1000, x="V_D1", xlabel="V (V)", dots=True)],
        table={"columns": [col("V", "V", "inst:V", "V", digits=2), col("I", "I", "inst:I", "mA", 0.001, digits=2)], "calc": "diode_knee",
               "rows_min": 4, "result_digits": 2},
        steps=["Raise the source from 0 in steps of 0.1 V.", "Record V and I each time (at least 8 readings).",
               "Look at the graph: beyond one voltage the current rises sharply: the knee voltage.", "For a silicon diode it is about 0.6-0.7 V."],
        theory="In forward bias the diode current is I = Is(e^(V/nV_T) - 1): almost zero at first, rising sharply after the knee. "
               "This lab's model behaves like a silicon diode such as the 1N4007 (Is = 7 nA, n = 1.8).",
        safety="In a real lab always use a series resistor; without it the diode can burn out.",
        tour=[{"say": "A source, a 100 ohm resistor and a silicon diode in forward bias."},
              {"set": {"Eb": 0.5}, "say": "Half a volt: almost no current. The diode has not 'opened' yet."},
              {"set": {"Eb": 2}, "say": "2 volts: the current is in milliamperes, yet only about 0.65 volt is across the diode. The rest is across the resistor."}],
        questions=[{"q": "Past the knee, as the source rises, the diode's voltage?", "options": ["Rises only a little", "Rises by the same amount", "Falls"],
                    "answer": 0, "why": "The current grows exponentially; the extra voltage drops across the resistor."}],
        sources=[S12, SIM],
        check={"params": {"Eb": 2.0}, "measure": {"mode": "value", "vars": ["V_D1"]}, "reading": "V_D1", "textbook": "diode_V"},
    )


def rc() -> dict:
    net = {"nodes": 3, "els": [
        {"id": "E", "kind": "V", "a": 1, "b": 0, "value": 5.0}, {"id": "K", "kind": "S", "a": 1, "b": 2, "param": "key"},
        {"id": "R", "kind": "R", "a": 2, "b": 3, "value": "Rr"}, {"id": "C1", "kind": "C", "a": 3, "b": 0, "value": "Cc"}]}
    return lab(
        id="rc-charging", title="Charging a capacitor: τ = RC", group="Physics · Electricity", level="Class XII",
        topic="Electrostatic Potential and Capacitance", aim="Close the switch and watch the capacitor's voltage; measure the time τ to reach 63%.",
        kernel="circuit", cfg={"net": net}, params={"Rr": 10000.0, "Cc": 1e-4, "key": 0.0}, autorun=True,
        camera={"pos": [0.0, 0.55, 0.6], "look": [0, 0, 0]}, floor=-0.03,
        bodies=[
            board(0.9, 0.55),
            B("bat", "box", name="Battery 5 V", size=[0.14, 0.05, 0.08], pos=[-0.3, 0.025, 0.15], color="#2b2f36"),
            B("sw", "box", name="Switch", size=[0.05, 0.02, 0.03], pos=[0.0, 0.02, 0.15], color="black",
              bind={"rz": {"var": "p.key", "k": 0.5, "c": -0.5}}),
            B("res", "box", name="Resistor R", size=[0.06, 0.012, 0.012], pos=[0.25, 0.02, 0.05], rot=[0, 1.5708, 0], color="#d9b46a"),
            B("cap", "cylinder", name="Capacitor C", info="Two plates; charge builds up on them.", r=0.03, h=0.07, pos=[0.25, 0.04, -0.15], color="#3e63dd"),
            B("lvl", "box", name="Charge (illustration)", size=[0.012, 0.1, 0.012], pos=[0.32, 0.0, -0.15], color="gold",
              illustrative=True, bind={"sy": {"var": "V_C1", "k": 0.2, "min": 0.001}, "y": {"var": "V_C1", "k": 0.01}}),
            *dial("vm", [-0.15, 0.0, -0.15], "Voltmeter (0-5 V)"), needle("vmn", [-0.15, 0.0, -0.15], "V_C1", -0.48, 1.2),
            _wire("w1", [[-0.23, 0.02, 0.15], [-0.03, 0.02, 0.15]]), _wire("w2", [[0.03, 0.02, 0.15], [0.25, 0.02, 0.15], [0.25, 0.02, 0.08]]),
            _wire("w3", [[0.25, 0.02, 0.02], [0.25, 0.02, -0.12]]),
            _wire("w4", [[0.25, 0.02, -0.19], [0.25, 0.02, -0.24], [-0.38, 0.02, -0.24], [-0.38, 0.02, 0.15]], "black"),
        ],
        knobs=[knob("key", "Switch (0 open / 1 closed)", "key", 0, 1, 1, 0, reset=False),
               knob("Rr", "Resistance R", "Rr", 1, 20, 1, 10, "kΩ", 1000.0, reset=True),
               knob("Cc", "Capacitance C", "Cc", 50, 500, 10, 100, "µF", 1e-6, reset=True)],
        instruments=[inst("V", "readout", "Voltage across the capacitor", "V_C1", unit="V", lc=0.01, digits=2),
                     inst("sw", "stopwatch", "Stopwatch (start with the switch)"),
                     inst("gr", "graph", "V_C against time", "V_C1", range=[0, 5], xlabel="t (s)")],
        table={"columns": [col("tau", "Time to 63% (3.16 V)", "inst:sw", "s", digits=2)], "calc": "rc_tau", "rows_min": 1,
               "result_digits": 2, "hint": "Start the stopwatch with the switch; stop it when the voltage reaches 3.16 V."},
        steps=["R = 10 kΩ, C = 100 µF: τ = RC should be 1 s.", "Start the stopwatch and close the switch (1) at once.",
               "Stop the stopwatch at 3.16 V (63% of 5 V); record it.", "Double R or C and repeat: does τ double?"],
        theory="The voltage of a charging capacitor is V = E(1 - e^(-t/RC)). At t = RC, V = 0.632 E. So τ = RC is the 'time constant'.",
        tour=[{"say": "A battery, a switch, a resistor and a capacitor. The switch is open."},
              {"set": {"key": 1}, "say": "Switch closed: the capacitor is charging. Fast at first, then slower.", "run": True},
              {"say": "In one second the voltage reached 63 percent: R times C equals one second."}],
        questions=[{"q": "If R is doubled, the time to reach 63% is?", "options": ["Doubled", "Halved", "Unchanged"], "answer": 0,
                    "why": "τ = RC."}],
        sources=[S12, SIM],
        check={"params": {"key": 1.0}, "measure": {"mode": "time_to", "var": "V_C1", "final": 5.0}, "reading": "t_V_C1",
               "textbook": "rc_tau"},
    )


# ======================================================================================================== OPTICS
def _bench(left=-0.05, right=1.05, y=-0.12) -> list[dict]:
    w = right - left
    return [B("bench", "box", name="Optical bench", size=[w, 0.03, 0.08], pos=[left + w / 2, y, 0], color="wood", cut=False),
            B("ruler", "scale", name="Bench scale (cm)", length=round(w, 3), spacing=0.01, major=10, labels=True, label_step=10, tick=0.01,
              font=0.016, start=round(left * 100), pos=[left, y + 0.017, 0.041], rot=[-1.5708, 0, 0])]


def mirror() -> dict:
    return lab(
        id="concave-mirror", title="Concave mirror: f from u and v", group="Physics · Optics", level="Class XII",
        topic="Ray Optics and Optical Instruments", aim="Change the object distance u, find the sharp image on the screen (v); f = uv/(u + v).",
        kernel="mirror", params={"h": 0.05}, autorun=True,
        camera={"pos": [0.35, 0.18, 0.95], "look": [0.3, 0.0, 0]}, floor=-0.15,
        bodies=[
            *_bench(-0.05, 1.0),
            B("mir", "dish", name="Concave mirror (R = 30 cm)", info="So f = R/2 = 15 cm.", R=0.3, r=0.06, pos=[0, 0, 0], color="#c8d4e0"),
            B("ms", "cylinder", r=0.004, h=0.1, pos=[-0.01, -0.06, 0], color="steel"),
            B("obj", "arrow", name="Object (in place of a lit candle)", dir=[0, 1, 0], len=0.05, head=0.012, pos=[0, 0, 0], color="red",
              bind={"x": "p.u"}),
            B("img", "arrow", name="Image", info="When it is real and inverted, it forms on the screen.", dir=[0, 1, 0], len=0.05, head=0.012,
              pos=[0, 0, 0], color="blue", bind={"x": "img_x", "len": "img_h"}),
            B("scr", "plane", name="Screen", size=[0.1, 0.1], pos=[0, 0, 0], rot=[0, 1.5708, 0], color="white", opacity=0.8,
              bind={"x": "p.scr"}),
            B("rays", "rays", name="Rays", var="rays", color="ray"),
        ],
        knobs=[knob("u", "Object distance u", "u", 20, 80, 0.5, 45, "cm", 0.01, hint="Keep u > f so the image is real."),
               knob("scr", "Screen distance", "scr", 5, 100, 0.5, 30, "cm", 0.01, hint="Slide the screen until the image is sharpest.")],
        instruments=[inst("sh", "meter", "Image sharpness on the screen", "sharp", range=[0, 1], digits=2),
                     inst("mg", "readout", "Magnification (m)", "img_h", k=20, digits=2, hint=True)],
        table={"columns": [col("u", "u", "knob:u", "cm", 0.01, digits=1), col("v", "v (sharp screen)", "knob:scr", "cm", 0.01, digits=1)],
               "calc": "mirror_f", "rows_min": 3, "result_k": 100, "result_unit": "cm", "result_digits": 1},
        steps=["Set u = 45 cm.", "Slide the screen: stop when the meter is full (sharpest).", "Record u and v.",
               "Repeat at u = 40, 35, 30, 25 cm.", "Average f = uv/(u + v): it should be R/2 = 15 cm."],
        theory="Mirror formula 1/v + 1/u = 1/f (here all distances are taken positive from the mirror, for a real image). "
               "The rays in this lab are traced on the real spherical surface; for small angles the formula holds within 1%.",
        tour=[{"say": "A concave mirror on the optical bench. The red arrow is the object; the rays reflect off the mirror and meet."},
              {"set": {"scr": 22.5}, "say": "With the screen here, the image is sharpest. Inverted and smaller, because the object is beyond 2f."},
              {"set": {"u": 30, "scr": 30}, "say": "The object at C, that is 30 centimetres: the image is there too, and the same size."}],
        questions=[{"q": "If the object is between f and 2f, the image is?", "options": ["Beyond 2f, enlarged", "Inside f", "Virtual"], "answer": 0,
                    "why": "As u decreases, v increases."}],
        sources=[S12, SIM],
        check={"params": {"u": 0.45}, "reading": "v", "textbook": "mirror_v"},
    )


def lens() -> dict:
    return lab(
        id="convex-lens", title="Convex lens: f from u and v", group="Physics · Optics", level="Class XII",
        topic="Ray Optics and Optical Instruments", aim="Change the object distance from the lens, find the sharp image on the screen; f = uv/(u + v).",
        kernel="lens", params={"h": 0.05}, autorun=True,
        camera={"pos": [0.0, 0.2, 1.2], "look": [0.0, 0.0, 0]}, floor=-0.15,
        bodies=[
            *_bench(-0.85, 0.85),
            B("lens", "lens", name="Convex lens (f ≈ 20 cm)", info="Glass n = 1.5, both surfaces R = 20 cm.", r=0.025, thick=0.008, pos=[0, 0, 0],
              color="glass", opacity=0.45),
            B("ls", "cylinder", r=0.004, h=0.07, pos=[0, -0.075, 0], color="steel"),
            B("obj", "arrow", name="Object", dir=[0, 1, 0], len=0.05, head=0.012, pos=[0, 0, 0], color="red", bind={"x": {"var": "p.u", "k": -1}}),
            B("img", "arrow", name="Image", dir=[0, 1, 0], len=0.05, head=0.012, pos=[0, 0, 0], color="blue",
              bind={"x": "img_x", "len": "img_h"}),
            B("scr", "plane", name="Screen", size=[0.1, 0.1], pos=[0, 0, 0], rot=[0, 1.5708, 0], color="white", opacity=0.8, bind={"x": "p.scr"}),
            B("rays", "rays", name="Rays", var="rays", color="ray"),
        ],
        knobs=[knob("u", "Object distance u", "u", 25, 80, 0.5, 40, "cm", 0.01),
               knob("scr", "Screen distance", "scr", 5, 85, 0.5, 30, "cm", 0.01)],
        instruments=[inst("sh", "meter", "Image sharpness on the screen", "sharp", range=[0, 1], digits=2)],
        table={"columns": [col("u", "u", "knob:u", "cm", 0.01, digits=1), col("v", "v (sharp screen)", "knob:scr", "cm", 0.01, digits=1)],
               "calc": "lens_f", "rows_min": 3, "result_k": 100, "result_unit": "cm", "result_digits": 1},
        steps=["u = 40 cm.", "Slide the screen until the image is sharpest.", "Record u and v; repeat at u = 35, 30, 50, 60 cm.",
               "Average f = uv/(u + v)."],
        theory="Lens formula 1/v + 1/u = 1/f (real image, distances from the lens). Lensmaker's formula: 1/f = (n - 1)(1/R₁ + 1/R₂) = 0.5 × 10 → f = 20 cm. "
               "A real lens's thickness makes a small difference (less than 1% here).",
        tour=[{"say": "The convex lens in the middle, the object on the left, the screen on the right."},
              {"set": {"scr": 40.4}, "say": "At u = 40 the screen is at about 40: the object is at 2f, so the image is at 2f too."},
              {"set": {"u": 30, "scr": 60}, "say": "Object moved closer: the image moved further away and got larger."}],
        questions=[{"q": "If the object is closer than f?", "options": ["No image on the screen (virtual)", "A small real image", "Image at 2f"], "answer": 0,
                    "why": "The rays spread out; a virtual image forms on the same side as the object."}],
        sources=[S12, SIM],
        check={"params": {"u": 0.4}, "reading": "v", "textbook": "lens_v"},
    )


def prism() -> dict:
    return lab(
        id="prism-minimum-deviation", title="Prism: angle of minimum deviation", group="Physics · Optics", level="Class XII",
        topic="Ray Optics and Optical Instruments", aim="Change the angle of incidence i, plot the deviation δ and find n from δm.",
        kernel="prism", params={"i": 0.8}, autorun=True,
        camera={"pos": [0.0, 0.06, 0.5], "look": [0.0, 0.05, 0]}, floor=-0.05,
        bodies=[
            B("paper", "box", name="Drawing board", size=[0.5, 0.004, 0.3], pos=[0, -0.03, 0], color="white", cut=False),
            B("pr", "prism", name="Glass prism (A = 60°)", angle="A", side=0.12, depth=0.04, pos=[0, 0, 0], color="glass", opacity=0.45),
            B("rays", "rays", name="Ray (from the pins)", var="rays", color="ray", virtual="ink"),
        ],
        knobs=[knob("i", "Angle of incidence i", "i", 30, 75, 0.5, 46, "°", DEG),
               knob("n", "Glass (n hidden)", "n", 1.4, 1.8, 0.01, 1.5, hidden=True)],
        instruments=[inst("d", "readout", "Angle of deviation δ (protractor)", "dev", k=R2D, unit="°", lc=0.1, digits=1),
                     inst("gr", "graph", "δ vs i", "dev", k=R2D, x="p.i", xk=R2D, xlabel="i (°)", dots=True)],
        table={"columns": [col("i", "i", "knob:i", "°", DEG, digits=1), col("d", "δ", "inst:d", "°", DEG, digits=1)],
               "calc": "prism_n", "rows_min": 5, "truth": "p.n", "result_digits": 3},
        steps=["Take i from 35° to 70° in steps of 5°.", "Record δ for each i.", "Graph: δ first falls, then rises; the lowest point is δm.",
               "n = sin((A + δm)/2) / sin(A/2)."],
        theory="At minimum deviation the ray travels inside the prism parallel to its base, and i = e. Then n = sin((A + δm)/2) / sin(A/2).",
        tour=[{"say": "A 60 degree glass prism. The ray falls on the left face and bends towards the base."},
              {"set": {"i": 35}, "say": "A small angle of incidence: large deviation."},
              {"set": {"i": 48.5}, "say": "Here the deviation is smallest: the ray goes straight through the prism, parallel to the base."}],
        questions=[{"q": "At minimum deviation, i and e are?", "options": ["Equal", "i is double", "e is zero"], "answer": 0, "why": "The ray follows a symmetric path."}],
        sources=[S12, SIM],
        check={"params": {}, "reading": "dm", "textbook": "prism_dm"},
    )


def slab() -> dict:
    return lab(
        id="glass-slab-apparent-depth", title="Glass slab: apparent depth", group="Physics · Optics", level="Class XII",
        topic="Ray Optics and Optical Instruments", aim="A mark under a slab appears raised: find n from the real and apparent depths.",
        kernel="slab", autorun=True,
        camera={"pos": [0.12, 0.05, 0.32], "look": [0.0, -0.03, 0]}, floor=-0.12,
        bodies=[
            B("slab", "box", name="Glass slab", size=[0.2, 0.05, 0.12], pos=[0, 0, 0], color="glass", opacity=0.3,
              bind={"sy": {"var": "p.t", "k": 20}, "y": {"var": "p.t", "k": -0.5}}),
            B("mk1", "box", name="Mark (real position)", size=[0.03, 0.002, 0.004], pos=[0, 0, 0], color="black", bind={"y": {"var": "p.t", "k": -1}}),
            B("mk2", "box", size=[0.004, 0.002, 0.03], pos=[0, 0, 0], color="black", bind={"y": {"var": "p.t", "k": -1}}),
            B("ghost", "box", name="Where the mark appears", info="Seen from above.", size=[0.03, 0.002, 0.004], pos=[0, 0, 0], color="red",
              opacity=0.6, illustrative=True, bind={"y": {"var": "app", "k": -1}}),
            B("micro", "cylinder", name="Travelling microscope", r=0.012, h=0.08, pos=[0, 0.09, 0], color="#2b2f36"),
            B("rays", "rays", name="Rays", var="rays", color="ray"),
        ],
        knobs=[knob("t", "Slab thickness", "t", 2, 10, 0.1, 5, "cm", 0.01),
               knob("n", "Material (water 1.33, glass 1.5, diamond 2.42)", "n", 1.33, 2.42, 0.01, 1.5)],
        instruments=[inst("a", "readout", "Microscope: apparent depth", "app", k=100, unit="cm", lc=0.01, digits=2),
                     inst("s", "readout", "How far the mark rose", "shift", k=100, unit="cm", lc=0.01, digits=2)],
        table={"columns": [col("t", "Real depth", "knob:t", "cm", 0.01, digits=2), col("a", "Apparent depth", "inst:a", "cm", 0.01, digits=2)],
               "calc": "slab_n", "rows_min": 2, "truth": "p.n", "result_digits": 3},
        steps=["Slab 5 cm, glass.", "Read the apparent depth with the microscope and record it.", "Change the thickness and repeat.", "n = real / apparent."],
        theory="Going from a denser medium into air, a ray bends away from the normal, so an object below appears raised. Seen from straight above: n = real depth / apparent depth.",
        tour=[{"say": "A mark under a glass slab. Seen from above, it appears raised."},
              {"set": {"n": 2.42}, "say": "Diamond: the mark appears even higher, because n is larger."}],
        questions=[{"q": "The depth of a pond filled with water, seen from above?", "options": ["Looks less", "Looks more", "Looks the same"], "answer": 0,
                    "why": "Apparent = real / n."}],
        sources=[S12, SIM],
        check={"params": {}, "reading": "app", "textbook": "slab_app"},
    )


# ======================================================================================================== MAGNETISM
def induction() -> dict:
    return lab(
        id="electromagnetic-induction", title="Faraday: magnet and coil", group="Physics · Magnetism", level="Class XII",
        topic="Electromagnetic Induction", aim="Pass a magnet through a coil at different speeds: how does the peak emf change with speed?",
        kernel="induction", autorun=True, speeds=[0.1, 0.25, 0.5, 1],
        speed=0.25, camera={"pos": [0.0, 0.2, 0.42], "look": [0.0, -0.03, -0.04]}, floor=-0.08,
        bodies=[
            B("tbl", "box", size=[0.5, 0.01, 0.25], pos=[0, -0.06, 0], color="wood", cut=False),
            B("coil", "spring", name="Coil (N turns)", info="An emf appears when the magnetic flux through it changes.", a=[-0.04, 0, 0], b=[0.04, 0, 0],
              r=0.026, turns=24, wire=0.0018, color="copper"),
            B("mag", "box", name="Bar magnet", size=[0.001, 0.001, 0.001], pos=[0, 0, 0], bind={"x": "z"}),
            B("magN", "box", name="Magnet: N pole", size=[0.03, 0.012, 0.012], pos=[0.015, 0, 0], parent="mag", color="red"),
            B("magS", "box", name="Magnet: S pole", size=[0.03, 0.012, 0.012], pos=[-0.015, 0, 0], parent="mag", color="blue"),
            *dial("g", [0.0, -0.055, -0.15], "Galvanometer", "The needle's direction = the current's direction (Lenz)."),
            needle("gn", [0.0, -0.055, -0.15], "emf", -6.0),
            _wire("w1", [[-0.04, -0.026, 0], [-0.04, -0.05, -0.1], [-0.05, -0.04, -0.15]]),
            _wire("w2", [[0.04, -0.026, 0], [0.04, -0.05, -0.1], [0.05, -0.04, -0.15]], "black"),
        ],
        knobs=[knob("v", "Magnet speed", "v", -2, 2, 0.1, 0.5, "m/s", reset=True, hint="In the opposite direction (minus) the needle swings the other way."),
               knob("N", "Turns in the coil", "N", 50, 500, 10, 200)],
        instruments=[inst("e", "readout", "Emf (now)", "emf", k=1000, unit="mV", digits=1),
                     inst("pk", "readout", "Peak emf (cleared by Reset)", "emf", k=1000, unit="mV", digits=1, peak=True),
                     inst("gr", "graph", "Emf against time", "emf", k=1000, xlabel="t (s)")],
        table={"columns": [col("v", "Speed v", "knob:v", "m/s", digits=1), col("emf", "Peak emf", "inst:pk", "mV", 0.001, digits=1)],
               "calc": "induct_ratio", "rows_min": 2, "result_digits": 4, "hint": "For each speed: Reset, let the magnet pass once, record the peak."},
        steps=["Speed 0.5 m/s: the magnet passes through the coil and the needle moves.", "Record the peak emf.",
               "Repeat at 1.0 and 1.5 m/s: is emf / v constant?", "Double the turns: the emf doubles."],
        theory="Faraday: emf = -N dΦ/dt. A faster magnet changes the flux faster, giving more emf. Lenz: the needle swings opposite ways as the magnet enters and leaves.",
        tour=[{"say": "The bar magnet approaches the coil: the flux increases and the needle swings one way.", "run": True},
              {"say": "Leaving the coil the flux decreases: the needle swings the other way. This is Lenz's law."},
              {"set": {"v": 1.5}, "say": "Three times the speed: three times the peak emf."}],
        questions=[{"q": "If the magnet stays still inside the coil, the emf is?", "options": ["Zero", "The largest", "Reversed"], "answer": 0, "why": "The flux is not changing."}],
        sources=[S12, SIM],
        check={"params": {}, "reading": "emf_peak", "textbook": "induct_peak"},
    )


# ======================================================================================================== MEASUREMENT
def vernier() -> dict:
    s = 10.0                       # 1 m = 10 stage units: 1 mm = 1 cm on screen (10x magnified)
    return lab(
        id="vernier-callipers", title="Measuring with vernier callipers", group="Physics · Measurement", level="Class XI",
        topic="Units and Measurement", aim="Read the main scale and the vernier to measure the diameter of a sphere (least count 0.1 mm).",
        kernel="gauge", params={"kind": 0.0}, autorun=True,
        camera={"pos": [0.25, -0.02, 0.75], "look": [0.25, -0.05, 0]}, floor=-0.36,
        bodies=[
            B("beam", "box", name="Main scale (mm)", info="Each small division is 1 mm. Magnified 10 times on screen.", size=[1.1, 0.06, 0.01],
              pos=[0.5, 0.03, 0], color="steel"),
            B("ms", "scale", length=1.0, spacing=0.01, major=10, labels=True, label_step=1, tick=0.012, font=0.018, down=True,
              pos=[0, 0.06, 0.006]),
            B("jaw0", "box", name="Fixed jaw", size=[0.03, 0.34, 0.01], pos=[-0.015, -0.14, 0], color="steel"),
            B("slider", "box", name="Vernier (sliding jaw)", info="10 vernier divisions = 9 mm: least count 0.1 mm.",
              size=[0.001, 0.001, 0.001], pos=[0, 0, 0], bind={"x": {"var": "jaw", "k": s}}),
            B("vplate", "box", size=[0.12, 0.04, 0.012], pos=[0.06, 0.08, 0.002], parent="slider", color="#b8c0c8"),
            B("jaw1", "box", size=[0.03, 0.34, 0.01], pos=[0.015, -0.14, 0], parent="slider", color="steel"),
            B("vs", "scale", name="Vernier scale", length=0.09, spacing=0.009, major=5, labels=True, label_step=5, tick=0.012, font=0.014,
              pos=[0, 0.06, 0.01], parent="slider", bind={"mark": "div"}),
            B("ball", "cylinder", name="Sphere being measured", r=0.5, h=0.02, pos=[0, -0.2, -0.012], rot=[1.5708, 0, 0], color="brass",
              bind={"x": {"var": "p.L", "k": s / 2}, "sx": {"var": "p.L", "k": s}, "sz": {"var": "p.L", "k": s}}),
        ],
        knobs=[knob("L", "Take another sphere (true size hidden)", "L", 5, 60, 0.05, 23.45, "mm", 0.001, hidden=True),
               knob("ze", "Zero error", "ze", -0.5, 0.5, 0.1, 0, "mm", 0.001, hint="With the jaws closed, how far the vernier zero is from the main zero.")],
        instruments=[inst("lc", "readout", "Least count", "lc", k=1000, unit="mm", digits=2),
                     inst("msr", "readout", "Main scale reading (help)", "main", k=1000, unit="mm", digits=1, hint=True),
                     inst("vsd", "readout", "Coinciding vernier division (help)", "div", digits=0, hint=True)],
        table={"columns": [col("reading", "Diameter (MSR + VSD × LC - zero error)", "manual", "mm", 0.001)], "calc": "gauge_mean", "rows_min": 1,
               "truth": "p.L", "result_k": 1000, "result_unit": "mm", "result_digits": 2},
        steps=["Where is the vernier zero on the main scale: the mm just before it = MSR.", "Which vernier division lines up with a main scale line (red) = VSD.",
               "Reading = MSR + VSD × 0.1 mm - zero error.", "Type it in the Table yourself; repeat with 3 spheres."],
        theory="10 vernier divisions = 9 main scale divisions, so the least count = 1 mm - 0.9 mm = 0.1 mm.",
        tour=[{"say": "Vernier callipers: the main scale on top, the vernier scale on the sliding jaw. Everything is magnified 10 times on screen."},
              {"cam": [0.25, 0.06, 0.25], "look": [0.25, 0.06, 0], "say": "The vernier zero is between 23 and 24 millimetres. The MSR is 23 millimetres."},
              {"say": "The red division lines up with the main scale. Add its number times 0.1 millimetre."}],
        questions=[{"q": "Why is the least count 0.1 mm?", "options": ["10 VSD = 9 MSD", "The scale is small", "The jaws are thin"], "answer": 0,
                    "why": "1 MSD - 1 VSD = 0.1 mm."}],
        sources=[S11, SIM],
        check={"params": {"L": 0.02345}, "reading": "reading", "textbook": "gauge_L"},
    )


def screw_gauge() -> dict:
    s = 100.0                      # 1 mm = 0.1 stage unit (100x magnified)
    return lab(
        id="screw-gauge", title="Diameter of a wire with a screw gauge", group="Physics · Measurement", level="Class XI",
        topic="Units and Measurement", aim="Pitch 0.5 mm, 50 divisions: least count 0.01 mm. Measure the diameter of a wire.",
        kernel="gauge", params={"kind": 1.0, "L": 0.000512}, autorun=True,
        camera={"pos": [0.1, 0.12, 0.6], "look": [0.1, 0.0, 0]}, floor=-0.25,
        bodies=[
            B("frame", "box", name="U-frame", size=[0.04, 0.3, 0.03], pos=[-0.06, -0.08, 0], color="#2b2f36"),
            B("frameb", "box", size=[0.5, 0.04, 0.03], pos=[0.17, -0.21, 0], color="#2b2f36"),
            B("anvil", "cylinder", name="Anvil (fixed end)", r=0.015, h=0.04, pos=[-0.02, 0, 0], rot=[0, 0, 1.5708], color="steel"),
            B("wire", "cylinder", name="Wire", info="Drawn 100 times thicker on screen.", r=0.5, h=0.12, pos=[0, 0, 0], rot=[1.5708, 0, 0], color="copper",
              bind={"x": {"var": "p.L", "k": s / 2}, "sx": {"var": "p.L", "k": s}, "sz": {"var": "p.L", "k": s}}),
            B("sleeve", "cylinder", name="Sleeve (linear scale, 0.5 mm)", r=0.02, h=0.4, pos=[0.3, 0, 0], rot=[0, 0, 1.5708], color="#c4ccd4"),
            B("ls", "scale", length=0.3, spacing=0.05, major=2, labels=True, label_step=1, tick=0.01, font=0.016, pos=[0.1, 0.02, 0.012]),
            B("sp", "box", name="Spindle", size=[0.001, 0.001, 0.001], pos=[0, 0, 0], bind={"x": {"var": "jaw", "k": s}}),
            B("spin", "cylinder", r=0.012, h=0.1, pos=[0.05, 0, 0], rot=[0, 0, 1.5708], parent="sp", color="steel"),
            B("thimble", "cylinder", name="Thimble (50 divisions)", info="One turn = 0.5 mm; one division = 0.01 mm.", r=0.03, h=0.12,
              pos=[0.16, 0, 0], rot=[0, 0, 1.5708], parent="sp", color="#9aa3ad", bind={"rx": {"var": "jaw", "k": 12566.37}}),
            B("tm", "box", size=[0.12, 0.004, 0.004], pos=[0, 0.0, 0.03], parent="thimble", color="red"),
        ],
        knobs=[knob("L", "Take another wire (true size hidden)", "L", 0.2, 3.0, 0.001, 0.512, "mm", 0.001, hidden=True),
               knob("ze", "Zero error", "ze", -0.05, 0.05, 0.01, 0, "mm", 0.001)],
        instruments=[inst("lc", "readout", "Least count", "lc", k=1000, unit="mm", digits=3),
                     inst("psr", "readout", "Pitch scale reading (help)", "main", k=1000, unit="mm", digits=2, hint=True),
                     inst("hsr", "readout", "Thimble division (help)", "div", digits=0, hint=True)],
        table={"columns": [col("reading", "Diameter (PSR + HSR × LC - zero error)", "manual", "mm", 0.001)], "calc": "gauge_mean", "rows_min": 1,
               "truth": "p.L", "result_k": 1000, "result_unit": "mm", "result_digits": 3},
        steps=["The last visible line on the sleeve = PSR (steps of 0.5 mm).", "The thimble division on the line = HSR.",
               "Diameter = PSR + HSR × 0.01 mm - zero error.", "Measure the wire at 3 places; take the average."],
        theory="Least count = pitch / thimble divisions = 0.5 mm / 50 = 0.01 mm.",
        tour=[{"say": "A screw gauge: the wire sits between the anvil and the spindle. Turning the thimble moves the spindle forward."},
              {"say": "One full turn is 0.5 millimetre. The thimble has 50 divisions: each is 0.01 millimetre."}],
        questions=[{"q": "With a 1 mm pitch and 100 divisions, the least count is?", "options": ["0.01 mm", "0.1 mm", "1 mm"], "answer": 0, "why": "1/100 mm."}],
        sources=[S11, SIM],
        check={"params": {}, "reading": "reading", "textbook": "gauge_L"},
    )


BUILDERS = (pendulum, hooke, shm, incline, stokes, cooling, boyle, mixtures, resonance, sonometer, ohm, meter_bridge,
            potentiometer, diode, rc, mirror, lens, prism, slab, induction, vernier, screw_gauge)
