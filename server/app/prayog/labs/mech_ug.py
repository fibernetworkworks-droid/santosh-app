"""Lab pack: the undergraduate (B.Sc.) mechanics, measurement and properties-of-matter benches of the UGC / Delhi
University LOCF practical lists. Physics lives in `app/prayog/packs/mech_ug.py` (with its exact JavaScript twin);
the studio rigs live in `app/static/prayog/exp/<rig>.js`. Several labs share one rig through the `rig` field:

    torsional-pendulum   torsional pendulum + inertia table (one torsion bench)
    static-torsion       statical (Barton's) torsion of a rod
    flywheel-bench       moment of inertia of a flywheel
    bar-pendulum         bar (compound) pendulum
    poiseuille-flow      viscosity by capillary flow
    jaeger-bubble        surface tension by Jaeger's bubble method
    uniform-bending      Young's modulus by uniform bending
    travelling-microscope  least count / repeated readings (two labs)
    air-track            collisions of two gliders
    free-fall-timer      g by digital timing of a falling ball

Every constant used here is a published value with its source named on the lab (`sources`) and in the family files
beside it: elastic and shear moduli from the CRC Handbook, wire diameters from BS 3737, viscosities and surface
tensions of water from the CRC Handbook.
"""
from __future__ import annotations

import math

from ..catalog import col, inst, knob, lab, B

DEG = math.pi / 180
R2D = 180 / math.pi

UGC = {"title": "Learning Outcomes based Curriculum Framework for the B.Sc. (Physics) Programme, University Grants "
                "Commission (2019), Mechanics and Properties of Matter practical lists"}
DU = {"title": "B.Sc. (Honours) Physics syllabus, Department of Physics and Astrophysics, University of Delhi "
               "(LOCF 2019 / UGCF 2022), Mechanics and Waves & Oscillations laboratory lists"}
IP = {"title": "Indu Prakash and Ramakrishna, A Text Book of Practical Physics (properties of matter: torsional "
               "pendulum, flywheel, bar pendulum, Poiseuille's method, Jaeger's method, bending of beams)"}
SIMK = {"title": "Hoola Prayogshala kernel", "note": "readings come from the simulation code in packs/mech_ug.py; "
                                                     "checked against the textbook formula in Hoola's tests"}
CRC = {"title": "CRC Handbook of Chemistry and Physics",
       "note": "elastic and shear moduli of metals, viscosity and surface tension of water, densities"}
SWG = {"title": "BS 3737 standard wire gauge table", "note": "nominal diameters of the wires used"}


# ============================================================================ the torsion bench (one rig, two labs)
def _torsion_bodies(body_name: str, body_info: str) -> list[dict]:
    return [
        B("beam", "box", name="Wall bracket", info="A rigid bracket: the wire must hang from something that cannot twist.",
          size=[0.26, 0.03, 0.12], pos=[0, 0.92, -0.18], color="#2b3138"),
        B("post", "cylinder", name="Support pillar", r=0.02, h=0.9, pos=[-0.17, 0.45, -0.18], color="steel"),
        B("foot", "box", name="Heavy cast base", size=[0.3, 0.03, 0.2], pos=[-0.17, 0.015, -0.18], color="#2b3138"),
        B("chuckA", "cylinder", name="Upper chuck", info="Grips the wire at the top; the wire's effective length is measured from here.",
          r=0.016, h=0.03, pos=[0, 0.895, -0.18], color="brass"),
        B("wire", "rope", name="Suspension wire", info="The wire that is twisted. A longer or thinner wire twists more easily.",
          a=[0, 0.89, -0.18], b=[0, 0.3, -0.18], r=0.0008, color="steel"),
        B("chuckB", "cylinder", name="Lower chuck", r=0.016, h=0.03, pos=[0, 0.3, -0.18], color="brass"),
        B("disc", "cylinder", name=body_name, info=body_info, r=0.075, h=0.014, pos=[0, 0.28, -0.18], color="brass",
          bind={"ry": {"var": "th", "k": 1.0}}),
        B("mark", "box", name="Reference mark", info="A chalk line on the rim. You count an oscillation each time it passes the pointer.",
          size=[0.016, 0.0016, 0.07], pos=[0.05, 0.288, -0.145], color="white", bind={"ry": {"var": "th", "k": 1.0}}),
        B("ptr", "box", name="Fixed pointer", info="A pin on a small stand, level with the rim: the fixed mark to count against.",
          size=[0.004, 0.004, 0.05], pos=[0.0, 0.288, 0.0], color="red"),
        B("ptrpost", "cylinder", r=0.006, h=0.28, pos=[0.0, 0.14, 0.02], color="#2b3138"),
        B("mscale", "scale", name="Metre scale (cm)", length=0.6, spacing=0.001, major=10, labels=True,
          label_step=10, tick=0.008, font=0.012, pos=[-0.1, 0.3, -0.18], rot=[0, 0, -1.5708]),
        B("lbl", "text", text="Torsion bench", size=0.022, pos=[0.0, 0.98, -0.18]),
    ]


def torsional_pendulum() -> dict:
    return lab(
        id="torsional-pendulum", title="Torsional pendulum: modulus of rigidity of a wire",
        group="Physics · Mechanics", level="B.Sc.", topic="Elasticity and rotational motion",
        chapter="Mechanics",
        aim="Time the torsional oscillations of a disc hung on a wire for several wire lengths and find the modulus of "
            "rigidity of the wire.",
        kernel="torsion", params={"eta": 7.93e10, "rw": 0.0004, "Lw": 0.8, "I": 0.0012, "th0": 0.35, "b": 0.0},
        speeds=[0.25, 0.5, 1, 2],
        camera={"pos": [0.55, 0.75, 1.0], "look": [0.0, 0.45, -0.16]}, floor=-0.02,
        bodies=_torsion_bodies("Brass disc", "A heavy brass disc of known mass and radius, so its moment of inertia I is known."),
        knobs=[knob("len", "Wire length L", "Lw", 40, 100, 5, 80, "cm", 0.01,
                    hint="Measured from the lower face of the upper chuck to the upper face of the lower chuck."),
               knob("eta", "Wire material (η hidden)", "eta", 20, 120, 0.1, 79.3, "GPa", 1e9, hidden=True),
               knob("amp", "Starting twist", "th0", 5, 30, 1, 20, "°", DEG,
                    hint="Keep the twist small: the period must not depend on the amplitude.")],
        instruments=[inst("ang", "readout", "Twist angle θ", "th_deg", unit="°", digits=1),
                     inst("sw", "stopwatch", "Stopwatch (time 20 oscillations)"),
                     inst("gr", "graph", "Twist against time", "th_deg", xlabel="t (s)")],
        table={"columns": [col("Lw", "Wire length L", "knob:len", "cm", 0.01, digits=1),
                           col("T", "T = t₂₀ ÷ 20", "inst:sw", "s", div=20, digits=3)],
               "calc": "torsion_eta", "rows_min": 3, "truth": "p.eta", "result_digits": 0,
               "hint": "For each wire length: give the disc a small twist, time 20 oscillations and record the reading."},
        steps=["Measure the length of the wire between the chucks with the metre scale.",
               "Twist the disc through about 20° and let it go: it oscillates in its own plane.",
               "Time 20 complete oscillations with the stopwatch and work out T.",
               "Shorten the wire in the chuck and repeat for at least three lengths.",
               "η = 8π I L / (r⁴ T²) for each length; take the mean."],
        theory="A wire twisted through an angle θ pushes back with a couple Cθ, where C = π η r⁴ / (2L) for a wire of "
               "radius r and length L made of a material of rigidity modulus η. A body of moment of inertia I hung on "
               "that wire therefore oscillates in its own plane with T = 2π√(I/C), so η = 8π I L / (r⁴ T²). Because the "
               "radius comes in as the fourth power, the wire's diameter must be measured very carefully with a screw "
               "gauge: a 1 % error in r gives a 4 % error in η.",
        safety="Do not twist the wire past a few tens of degrees: beyond the elastic limit it keeps a permanent set and "
               "every later reading is wrong. Keep fingers clear of the spinning disc.",
        tour=[{"say": "A heavy brass disc hangs on a thin steel wire. Twist it and it oscillates in its own plane."},
              {"set": {"len": 40}, "say": "A short wire is stiffer, so the oscillations are faster."},
              {"set": {"len": 100}, "say": "A long wire is easier to twist: the period is longer. T² goes as L."}],
        questions=[{"q": "If the wire's radius is doubled, the torsional constant C becomes",
                    "options": ["16 times", "4 times", "Twice", "Unchanged"], "answer": 0,
                    "why": "C = πηr⁴/2L, so C goes as the fourth power of the radius."},
                   {"q": "Why must the starting twist be small?",
                    "options": ["So the wire stays within its elastic limit", "So the disc looks still",
                                "So the stopwatch works"], "answer": 0,
                    "why": "Beyond the elastic limit the couple is no longer proportional to the twist."}],
        sources=[UGC, DU, IP, SIMK, CRC, SWG],
        check={"params": {"Lw": 0.8, "th0": 0.1}, "reading": "T", "textbook": "torsion_T"},
    )


def inertia_table() -> dict:
    d = lab(
        id="inertia-table", title="Moment of inertia of an irregular body (inertia table)",
        group="Physics · Mechanics", level="B.Sc.", topic="Rotational motion", chapter="Mechanics",
        aim="Hang an irregular body on a calibrated torsion wire, time its torsional oscillations and work out its "
            "moment of inertia.",
        kernel="torsion", params={"eta": 7.93e10, "rw": 0.0004, "Lw": 0.8, "I": 0.0021, "th0": 0.35, "b": 0.0},
        speeds=[0.25, 0.5, 1, 2],
        camera={"pos": [0.55, 0.75, 1.0], "look": [0.0, 0.45, -0.16]}, floor=-0.02,
        bodies=_torsion_bodies("Inertia table with the body on it",
                               "A light circular table on the wire. The irregular body is clamped on it, at the centre."),
        knobs=[knob("len", "Wire length L", "Lw", 40, 100, 5, 80, "cm", 0.01,
                    hint="Measured between the chucks with a metre scale."),
               knob("I", "Body on the table (I hidden)", "I", 0.0005, 0.004, 0.00001, 0.0021, "kg·m²", hidden=True),
               knob("amp", "Starting twist", "th0", 5, 30, 1, 20, "°", DEG)],
        instruments=[inst("ang", "readout", "Twist angle θ", "th_deg", unit="°", digits=1),
                     inst("sw", "stopwatch", "Stopwatch (time 20 oscillations)"),
                     inst("gr", "graph", "Twist against time", "th_deg", xlabel="t (s)")],
        table={"columns": [col("Lw", "Wire length L", "knob:len", "cm", 0.01, digits=1),
                           col("T", "T = t₂₀ ÷ 20", "inst:sw", "s", div=20, digits=3)],
               "calc": "torsion_I", "rows_min": 3, "truth": "p.I", "result_digits": 5,
               "hint": "The wire is already calibrated (η and r are printed on it), so each period gives I at once."},
        steps=["Note the rigidity modulus η and the radius r printed on the wire.",
               "Measure the wire's length between the chucks.",
               "Twist the table through about 20° and time 20 oscillations.",
               "Repeat for at least three wire lengths.",
               "I = C T² / 4π² with C = π η r⁴ / 2L: take the mean."],
        theory="The suspension wire of this bench has already been calibrated on a body of known moment of inertia, so "
               "its torsional constant C = π η r⁴ / (2L) is known for any length L. Hanging an unknown body on the same "
               "wire and timing its torsional oscillations therefore gives its moment of inertia at once: from "
               "T = 2π√(I/C), I = C T² / 4π². The body need not have any regular shape - nothing in the method assumes "
               "one - which is why this is the standard way of measuring I for a casting or a machine part.",
        safety="Clamp the body firmly at the centre of the table: a body that slips while the table swings makes every "
               "reading useless and can fly off.",
        tour=[{"say": "An irregular body is clamped on the light table hanging from the calibrated wire."},
              {"set": {"len": 40}, "say": "On a short, stiff wire the same body oscillates faster."},
              {"set": {"len": 100}, "say": "On a long wire it swings slowly. T² is proportional to I at a fixed length."}],
        questions=[{"q": "Why can this method handle a body of any shape?",
                    "options": ["The period depends only on I, not on the shape",
                                "The body is melted down first", "Irregular bodies have no I"], "answer": 0,
                    "why": "T = 2π√(I/C) contains the moment of inertia alone."},
                   {"q": "If the same body is hung on a wire of twice the length, its period becomes",
                    "options": ["√2 times as long", "Twice as long", "Half as long"], "answer": 0,
                    "why": "C halves, and T goes as 1/√C."}],
        sources=[UGC, DU, IP, SIMK, CRC, SWG],
        check={"params": {"Lw": 0.8, "th0": 0.1}, "reading": "T", "textbook": "torsion_T"},
    )
    d["rig"] = "torsional-pendulum"
    return d


# ================================================================================ statical (Barton's) torsion
def static_torsion() -> dict:
    return lab(
        id="static-torsion", title="Modulus of rigidity by the statical (Barton's) method",
        group="Physics · Properties of matter", level="B.Sc.", topic="Elasticity",
        chapter="Properties of matter: elasticity, viscosity, surface tension",
        aim="Twist a clamped rod with a known couple, read the steady twist on a circular scale and find the modulus of "
            "rigidity of the rod.",
        kernel="stattorsion", params={"eta": 7.93e10, "rr": 0.002, "Lr": 0.6, "a": 0.05, "m": 0.0, "tau": 0.6},
        autorun=True,
        camera={"pos": [0.5, 0.45, 0.85], "look": [0.0, 0.18, -0.1]}, floor=-0.02,
        bodies=[
            B("bed", "box", name="Cast-iron bed", size=[0.9, 0.03, 0.2], pos=[0, 0.015, -0.1], color="#2b3138"),
            B("clamp", "box", name="Fixed chuck", info="One end of the rod is gripped here and cannot turn.",
              size=[0.07, 0.09, 0.09], pos=[-0.36, 0.075, -0.1], color="#5a6068"),
            B("rod", "cylinder", name="Experimental rod", info="The rod being twisted. Its radius comes in as r⁴, so measure it with care.",
              r=0.004, h=0.6, pos=[-0.03, 0.09, -0.1], rot=[0, 0, 1.5708], color="steel"),
            B("brg1", "box", name="Bearing", size=[0.04, 0.07, 0.06], pos=[-0.18, 0.06, -0.1], color="#5a6068"),
            B("brg2", "box", name="Bearing", size=[0.04, 0.07, 0.06], pos=[0.12, 0.06, -0.1], color="#5a6068"),
            B("wheel", "cylinder", name="Torsion wheel", info="Two cords leave opposite sides of this wheel, so the pull is a pure couple.",
              r=0.05, h=0.012, pos=[0.28, 0.09, -0.1], rot=[0, 0, 1.5708], color="brass",
              bind={"rx": {"var": "th", "k": 1.0}}),
            B("spoke", "box", name="Pointer on the wheel", size=[0.004, 0.09, 0.004], pos=[0.287, 0.09, -0.1],
              color="red", bind={"rx": {"var": "th", "k": 1.0}}),
            B("dialr", "torus", name="Circular scale", info="Degrees round the wheel: the pointer reads the twist directly.",
              r=0.057, tube=0.0015, pos=[0.3, 0.09, -0.1], rot=[0, 1.5708, 0], color="ink"),
            B("pul1", "torus", name="Pulley", r=0.018, tube=0.005, pos=[0.37, 0.09, -0.148], rot=[0, 1.5708, 0], color="steel"),
            B("pul2", "torus", name="Pulley", r=0.018, tube=0.005, pos=[0.37, 0.09, -0.052], rot=[0, 1.5708, 0], color="steel"),
            B("cord1", "rope", name="Cord", a={"body": "wheel", "off": [0, 0.05, -0.048]}, b={"body": "pul1", "off": [0, 0.018, 0]},
              r=0.0008, color="ink"),
            B("cord2", "rope", name="Cord", a={"body": "wheel", "off": [0, -0.05, 0.048]}, b={"body": "pul2", "off": [0, 0.018, 0]},
              r=0.0008, color="ink"),
            B("pan1", "cylinder", name="Scale pan", info="Equal weights go on both pans, so the rod is twisted and not bent.",
              r=0.03, h=0.01, pos=[0.4, 0.035, -0.148], color="brass"),
            B("pan2", "cylinder", name="Scale pan", r=0.03, h=0.01, pos=[0.4, 0.035, -0.052], color="brass"),
            B("lbl", "text", text="Statical torsion", size=0.022, pos=[0.0, 0.2, -0.1]),
        ],
        knobs=[knob("m", "Weight on each pan", "m", 0, 1.0, 0.1, 0, "kg"),
               knob("eta", "Rod material (η hidden)", "eta", 20, 120, 0.1, 79.3, "GPa", 1e9, hidden=True),
               knob("Lr", "Twisted length L", "Lr", 30, 70, 5, 60, "cm", 0.01,
                    hint="From the fixed chuck to the wheel.")],
        instruments=[inst("th", "readout", "Twist θ", "th_deg", unit="°", lc=0.1, digits=2),
                     inst("cp", "readout", "Couple applied", "couple", unit="N·m", digits=4),
                     inst("gr", "graph", "Twist against load", "th_deg", x="knob:m", xlabel="m (kg)", dots=True)],
        table={"columns": [col("m", "Weight m on each pan", "knob:m", "kg", digits=2),
                           col("theta", "Twist θ", "inst:th", "°", DEG, digits=2)],
               "calc": "stat_eta", "rows_min": 3, "truth": "p.eta", "result_digits": 0,
               "hint": "Load both pans equally, wait for the pointer to come to rest, then read the circular scale."},
        steps=["Measure the rod's diameter at several places with a screw gauge, and the twisted length with a metre scale.",
               "With the pans empty, set the pointer to zero on the circular scale.",
               "Put equal weights on both pans and read the twist when the pointer settles.",
               "Repeat in steps up to 1 kg, then unload in the same steps.",
               "η = 4 m g a L / (π r⁴ θ) for each load; take the mean."],
        theory="Two cords leaving opposite sides of a wheel of radius a, each carrying a weight mg, apply a pure couple "
               "τ = 2 m g a to the end of the rod: the rod is twisted but not bent. For a rod of radius r and twisted "
               "length L made of a material of rigidity modulus η, the steady twist is θ = 2 τ L / (π η r⁴), so "
               "η = 4 m g a L / (π r⁴ θ). A graph of θ against m is a straight line through the origin while the rod is "
               "within its elastic limit.",
        safety="Load both pans by the same amount every time; an unequal load bends the rod as well as twisting it. "
               "Stop at once if the pointer does not return to zero on unloading: the rod has been overstrained.",
        tour=[{"say": "The rod is gripped at the left and carries a wheel at the right. Two cords pull on opposite sides of the wheel."},
              {"set": {"m": 0.5}, "say": "Half a kilogram on each pan: the pointer has swung round the circular scale."},
              {"set": {"m": 1.0}, "say": "Twice the couple, twice the twist. Record the twist against each load in the Table."}],
        questions=[{"q": "Why are two cords used instead of one?",
                    "options": ["To apply a pure couple, with no sideways force on the rod",
                                "To double the weight", "To keep the wheel clean"], "answer": 0,
                    "why": "Two equal, opposite pulls give a couple whose resultant force is zero."},
                   {"q": "A rod of half the radius, under the same couple, twists",
                    "options": ["16 times as much", "4 times as much", "Twice as much"], "answer": 0,
                    "why": "θ goes as 1/r⁴."}],
        sources=[UGC, DU, IP, SIMK, CRC],
        check={"params": {"m": 0.5}, "reading": "theta", "textbook": "stat_theta"},
    )


# ============================================================================ moment of inertia of a flywheel
def flywheel_bench() -> dict:
    return lab(
        id="flywheel-bench", title="Moment of inertia of a flywheel", group="Physics · Mechanics", level="B.Sc.",
        topic="Rotational motion", chapter="Mechanics",
        aim="Let a known mass fall and spin up a flywheel, time the fall and count the rotations afterwards, and work "
            "out the flywheel's moment of inertia and the work lost to friction.",
        kernel="flywheel", params={"I": 0.012, "m": 0.5, "ra": 0.012, "n": 5.0, "tf": 0.006},
        speeds=[0.5, 1, 2, 4],
        camera={"pos": [0.6, 0.55, 1.05], "look": [0.0, 0.3, -0.12]}, floor=-0.52,
        bodies=[
            B("wall", "box", name="Wall plate", size=[0.34, 0.5, 0.03], pos=[0, 0.33, -0.26], color="#2b3138"),
            B("brkt", "box", name="Bearing bracket", info="The axle turns in ball bearings here: the friction is small but not zero.",
              size=[0.07, 0.09, 0.09], pos=[0, 0.42, -0.19], color="#5a6068"),
            B("wheel", "cylinder", name="Flywheel", info="A heavy cast-iron wheel. Almost all of its mass is in the rim, so its moment of inertia is large.",
              r=0.16, h=0.022, pos=[0, 0.42, -0.1], rot=[1.5708, 0, 0], color="#5a6068",
              bind={"rz": {"var": "ph", "k": 1.0}}),
            B("hub", "cylinder", name="Hub", r=0.035, h=0.03, pos=[0, 0.42, -0.1], rot=[1.5708, 0, 0], color="#2b3138"),
            B("axle", "cylinder", name="Axle", info="The cord is wound on this axle. Its radius r is measured with a vernier calliper.",
              r=0.012, h=0.1, pos=[0, 0.42, -0.04], rot=[1.5708, 0, 0], color="steel"),
            B("spoke1", "box", name="Spoke", size=[0.012, 0.3, 0.012], pos=[0, 0.42, -0.1], color="#3a4149",
              bind={"rz": {"var": "ph", "k": 1.0}}),
            B("spoke2", "box", name="Spoke", size=[0.3, 0.012, 0.012], pos=[0, 0.42, -0.1], color="#3a4149",
              bind={"rz": {"var": "ph", "k": 1.0}}),
            B("chalk", "box", name="Chalk mark", info="You count the rotations after the mass drops off by watching this mark.",
              size=[0.02, 0.03, 0.024], pos=[0, 0.575, -0.1], color="white",
              bind={"rz": {"var": "ph", "k": 1.0}}),
            B("cord", "rope", name="Cord", info="Wound n turns on the axle, with a loop that slips off when it runs out.",
              a=[0.012, 0.42, -0.02], b=[0.012, 0.1, -0.02], r=0.001, color="ink"),
            B("mass", "cylinder", name="Falling mass", info="Slotted weights on a hanger. Their fall spins the wheel up.",
              r=0.03, h=0.03, pos=[0.012, 0.08, -0.02], color="brass", bind={"y": {"var": "drop", "k": -1.0, "c": 0.08}}),
            B("tape", "scale", name="Steel tape (cm)", length=0.6, spacing=0.001, major=10, labels=True,
              label_step=10, tick=0.008, font=0.012, pos=[0.07, -0.1, -0.02], rot=[0, 0, -1.5708]),
            B("lbl", "text", text="Flywheel", size=0.024, pos=[0.0, 0.64, -0.1]),
        ],
        knobs=[knob("m", "Falling mass", "m", 0.2, 1.0, 0.1, 0.5, "kg"),
               knob("n", "Turns of cord on the axle", "n", 3, 8, 1, 5, "turns"),
               knob("I", "Flywheel (I hidden)", "I", 0.004, 0.03, 0.0001, 0.012, "kg·m²", hidden=True)],
        instruments=[inst("rpm", "readout", "Flywheel speed", "rpm", unit="rev/min", digits=0),
                     inst("sw", "stopwatch", "Stopwatch"),
                     inst("tn", "readout", "Rotations counted", "turns", digits=1),
                     inst("gr", "graph", "Speed against time", "rpm", xlabel="t (s)")],
        table={"columns": [col("m", "Falling mass m", "knob:m", "kg", digits=2),
                           col("n", "Turns of cord n", "knob:n", "turns", digits=0),
                           col("t1", "Time of fall t₁", "inst:sw", "s", digits=2),
                           col("N", "Rotations after the drop N", "manual", digits=0)],
               "calc": "fly_I", "rows_min": 2, "truth": "p.I", "result_digits": 5,
               "hint": "Time the fall, then count the rotations the wheel makes on its own until it stops."},
        steps=["Measure the axle's radius with a vernier calliper and wind the cord n full turns on it.",
               "Release the mass and start the stopwatch at the same moment; stop it as the cord slips off.",
               "Count the rotations N the wheel makes on its own after that, until it comes to rest.",
               "Repeat with two more masses or numbers of turns.",
               "I = m (2gh − v²) r² / (v² (1 + n/N)), with h = 2πnr and v = 2(2πn)r / t₁."],
        theory="While the mass falls through h = 2πnr the cord does work mgh on the system. Part of it becomes the "
               "kinetic energy of the falling mass, ½mv², part the kinetic energy of the wheel, ½Iω², and part is lost "
               "to friction at the bearings. After the cord slips off, the wheel turns N more times on that friction "
               "alone, so the loss while the mass fell was n/N of the wheel's kinetic energy. Hence "
               "mgh = ½mv² + ½Iω²(1 + n/N), which gives I = m(2gh − v²)r² / (v²(1 + n/N)). The uniform couple makes the "
               "angular acceleration constant, so ω = 2(2πn)/t₁.",
        safety="Keep your feet out from under the falling weights and stand clear of the rim: a heavy flywheel stores a "
               "lot of energy and takes a long time to stop.",
        tour=[{"say": "A heavy cast-iron flywheel on a wall bracket, with a cord wound on its axle carrying a hanger."},
              {"set": {"m": 1.0}, "say": "A heavier mass spins the wheel up faster, so the fall takes less time."},
              {"set": {"m": 0.5, "n": 8}, "say": "More turns of cord mean a longer fall and a higher final speed."}],
        questions=[{"q": "Why are the rotations after the cord slips off counted?",
                    "options": ["They measure the work lost to friction", "They measure the mass",
                                "They measure the axle's radius"], "answer": 0,
                    "why": "On that run-down the only couple acting is friction, so it calibrates the friction loss."},
                   {"q": "Most of a flywheel's mass is put in the rim because",
                    "options": ["mass far from the axis adds most to I", "it looks better", "it is cheaper"],
                    "answer": 0, "why": "I = Σmr², so distance from the axis counts twice over."}],
        sources=[UGC, DU, IP, SIMK],
        check={"params": {"m": 0.5}, "reading": "t1", "textbook": "fly_t1"},
    )


# ============================================================================ bar (compound) pendulum
def bar_pendulum() -> dict:
    return lab(
        id="bar-pendulum", title="g and the radius of gyration with a bar pendulum",
        group="Physics · Mechanics", level="B.Sc.", topic="Oscillations", chapter="Mechanics",
        aim="Hang a uniform bar on a knife edge through each of its holes, time its oscillations and find g and the "
            "bar's radius of gyration.",
        kernel="barpend", params={"Lb": 1.0, "h": 0.35, "th0": 0.0873, "b": 0.0},
        speeds=[0.25, 0.5, 1, 2],
        camera={"pos": [0.6, 0.1, 1.5], "look": [0.0, -0.2, -0.08]}, floor=-0.92,
        bodies=[
            B("wall", "box", name="Wall bracket", size=[0.3, 0.04, 0.1], pos=[0, 0.46, -0.14], color="#2b3138"),
            B("post", "cylinder", name="Support pillar", r=0.018, h=1.3, pos=[-0.2, -0.2, -0.14], color="steel"),
            B("foot", "box", name="Heavy base", size=[0.3, 0.03, 0.22], pos=[-0.2, -0.85, -0.14], color="#2b3138"),
            B("knife", "box", name="Knife edge", info="A hardened steel wedge resting in the hole: the point of suspension.",
              size=[0.05, 0.012, 0.012], pos=[0, 0.44, -0.1], color="#c3c8ce"),
            B("bar", "box", name="Metal bar", info="A uniform steel bar about a metre long with holes 5 cm apart along it.",
              size=[0.028, 1.0, 0.008], pos=[0, -0.06, -0.1], color="steel",
              bind={"rz": {"var": "th", "k": 1.0}}),
            B("cgmark", "box", name="Centre of gravity", info="The bar balances here. h is measured from this mark to the knife edge.",
              size=[0.032, 0.003, 0.01], pos=[0, -0.06, -0.094], color="red",
              bind={"rz": {"var": "th", "k": 1.0}}),
            B("scale", "scale", name="Metre scale (cm)", length=0.6, spacing=0.001, major=10, labels=True,
              label_step=10, tick=0.008, font=0.012, pos=[0.09, -0.2, -0.14], rot=[0, 0, -1.5708]),
            B("tele", "cylinder", name="Telescope", info="A telescope with a vertical cross-wire: you count an oscillation each time the bar's mark crosses it.",
              r=0.016, h=0.14, pos=[0.26, -0.3, 0.1], rot=[0, 0, 1.5708], color="black"),
            B("telepost", "cylinder", r=0.008, h=0.5, pos=[0.26, -0.55, 0.1], color="#2b3138"),
            B("lbl", "text", text="Bar pendulum", size=0.03, pos=[0.0, 0.54, -0.12]),
        ],
        knobs=[knob("h", "Hole used (distance from the centre of gravity)", "h", 5, 45, 5, 35, "cm", 0.01),
               knob("g", "Place (g hidden)", "g", 9.6, 10.0, 0.001, 9.8, "m/s²", hidden=True),
               knob("amp", "Starting angle", "th0", 2, 10, 1, 5, "°", DEG,
                    hint="Keep it below about 5°, so T = 2π√((k²+h²)/gh) holds.")],
        instruments=[inst("ang", "readout", "Angle θ", "th_deg", unit="°", digits=1),
                     inst("sw", "stopwatch", "Stopwatch (time 20 oscillations)"),
                     inst("leq", "readout", "Equivalent simple pendulum length", "L_eq", k=100, unit="cm", digits=2, hint=True),
                     inst("gr", "graph", "Angle against time", "th_deg", xlabel="t (s)")],
        table={"columns": [col("h", "Distance h from the C.G.", "knob:h", "cm", 0.01, digits=1),
                           col("T", "T = t₂₀ ÷ 20", "inst:sw", "s", div=20, digits=3)],
               "calc": "bar_g", "rows_min": 3, "truth": "p.g", "result_digits": 3,
               "hint": "For each hole: set the bar swinging through a small angle, time 20 oscillations, record it."},
        steps=["Balance the bar on a knife edge to find its centre of gravity and mark it.",
               "Hang the bar on the knife edge through a hole and measure h from the mark.",
               "Set it swinging through about 5° and time 20 oscillations.",
               "Repeat for at least three holes on both sides of the centre.",
               "g = 4π²(k² + h²) / (T² h) with k² = L²/12 for a uniform bar; take the mean."],
        theory="A rigid body swinging about a horizontal axis is a compound pendulum. If its centre of gravity is a "
               "distance h below the axis and its radius of gyration about a parallel axis through the centre of gravity "
               "is k, its period is T = 2π√((k² + h²)/(g h)): the same as a simple pendulum of length "
               "L = (k² + h²)/h, the equivalent length. For a uniform bar of length L_bar, k² = L_bar²/12, so timing the "
               "bar at several holes gives g = 4π²(k² + h²)/(T² h). The period is a minimum when h = k, and it rises "
               "again both for holes near the centre of gravity and for holes near the end.",
        safety="Make sure the knife edge is seated in the hole before letting go, and keep your head clear of the "
               "swinging bar. Stop the bar by hand, never with your foot.",
        tour=[{"say": "A metre-long steel bar hangs on a knife edge through one of its holes. Its centre of gravity is marked in red."},
              {"set": {"h": 10}, "say": "Close to the centre of gravity the swing is slow: the restoring couple is small."},
              {"set": {"h": 45}, "say": "Near the end it is faster. Somewhere in between the period is a minimum, where h = k."}],
        questions=[{"q": "For a uniform bar of length L, the radius of gyration about its centre is",
                    "options": ["L/√12", "L/2", "L/√3", "L"], "answer": 0,
                    "why": "k² = L²/12 for a thin uniform bar about an axis through its centre."},
                   {"q": "The period of a bar pendulum is least when",
                    "options": ["h equals the radius of gyration k", "h is zero", "h is the whole length"],
                    "answer": 0, "why": "T = 2π√((k²+h²)/gh) is a minimum at h = k."}],
        sources=[UGC, DU, IP, SIMK],
        check={"params": {"h": 0.35, "th0": 0.0349}, "reading": "T", "textbook": "bar_T"},
    )


# ============================================================================ viscosity by capillary flow
def poiseuille_flow() -> dict:
    return lab(
        id="poiseuille-flow", title="Viscosity of water by capillary flow (Poiseuille's method)",
        group="Physics · Properties of matter", level="B.Sc.", topic="Viscosity",
        chapter="Properties of matter: elasticity, viscosity, surface tension",
        aim="Measure the rate at which water flows out of a capillary tube under a steady head and work out the "
            "coefficient of viscosity.",
        kernel="poiseuille", params={"eta": 0.0010016, "rho": 998.2, "rc": 0.0005, "lc": 0.15, "hh": 0.25,
                                     "Vt": 1.0e-5},
        autorun=True,
        camera={"pos": [0.55, 0.5, 0.95], "look": [0.0, 0.22, -0.1]}, floor=-0.02,
        bodies=[
            B("stand", "box", name="Stand base", size=[0.2, 0.02, 0.16], pos=[-0.3, 0.01, -0.12], color="#2b3138"),
            B("rod", "cylinder", name="Stand rod", r=0.008, h=0.52, pos=[-0.3, 0.28, -0.12], color="steel"),
            B("tank", "cylinder", name="Constant-head reservoir", info="Water runs in at the top and out of an overflow, so the head stays the same all through the run.",
              r=0.055, h=0.16, open=True, pos=[-0.22, 0.4, -0.12], color="glass", opacity=0.3),
            B("water", "cylinder", name="Water", r=0.052, h=0.12, pos=[-0.22, 0.4, -0.12], color="water"),
            B("over", "cylinder", name="Overflow tube", info="Fixes the water level: the surplus runs away here.",
              r=0.004, h=0.07, pos=[-0.16, 0.47, -0.12], rot=[0, 0, 1.0], color="glass", opacity=0.5),
            B("down", "cylinder", name="Down tube", r=0.005, h=0.2, pos=[-0.22, 0.22, -0.12], color="glass", opacity=0.45),
            B("cap", "cylinder", name="Capillary tube", info="A fine, uniform horizontal tube. Its bore radius comes in as r⁴, so it is measured with a travelling microscope.",
              r=0.0035, h=0.3, pos=[-0.05, 0.12, -0.12], rot=[0, 0, 1.5708], color="glass", opacity=0.4),
            B("capm", "cylinder", name="Bore of the capillary", r=0.0012, h=0.3, pos=[-0.05, 0.12, -0.12],
              rot=[0, 0, 1.5708], color="water"),
            B("jar", "cylinder", name="Measuring jar", info="The water that runs out is collected here; 10 ml is one reading.",
              r=0.035, h=0.13, open=True, pos=[0.22, 0.065, -0.1], color="glass", opacity=0.3),
            B("coll", "cylinder", name="Collected water", r=0.032, h=0.1, pos=[0.22, 0.012, -0.1], color="water",
              bind={"sy": {"var": "V_ml", "k": 0.05, "min": 0.01}, "y": {"var": "V_ml", "k": 0.0025, "c": 0.012}}),
            B("jscale", "scale", name="Jar scale (ml)", length=0.1, spacing=0.002, major=5, labels=True,
              label_step=5, tick=0.006, font=0.01, pos=[0.256, 0.01, -0.066], rot=[0, 0, -1.5708]),
            B("hscale", "scale", name="Metre scale (cm)", length=0.5, spacing=0.001, major=10, labels=True,
              label_step=10, tick=0.008, font=0.012, pos=[-0.12, 0.0, -0.2], rot=[0, 0, -1.5708]),
            B("lbl", "text", text="Poiseuille's apparatus", size=0.02, pos=[-0.1, 0.56, -0.12]),
        ],
        knobs=[knob("h", "Head of water h", "hh", 10, 40, 5, 25, "cm", 0.01,
                    hint="The height of the water surface above the axis of the capillary."),
               knob("eta", "Liquid (η hidden)", "eta", 0.3, 1.6, 0.0001, 1.0016, "mPa·s", 0.001, hidden=True)],
        instruments=[inst("q", "readout", "Flow rate Q", "Q_ml", unit="ml/s", digits=4),
                     inst("v", "readout", "Water collected", "V_ml", unit="ml", lc=0.1, digits=2),
                     inst("sw", "stopwatch", "Stopwatch"),
                     inst("gr", "graph", "Flow rate against head", "Q_ml", x="knob:h", xlabel="h (cm)", dots=True)],
        table={"columns": [col("hh", "Head h", "knob:h", "cm", 0.01, digits=1),
                           col("Q", "Flow rate Q", "inst:q", "ml/s", 1e-6, digits=4)],
               "calc": "pois_eta", "rows_min": 3, "truth": "p.eta", "result_digits": 6,
               "hint": "For each head: collect 10 ml, time it, and Q is the volume divided by the time."},
        steps=["Measure the capillary's length and its bore radius (travelling microscope, several diameters).",
               "Set the overflow so the head h above the capillary's axis is steady, and measure h.",
               "Collect 10 ml in the measuring jar and time it: Q = V / t.",
               "Change the head and repeat for at least three values.",
               "η = π ρ g h r⁴ / (8 l Q) for each head; take the mean."],
        theory="For slow, steady flow through a narrow tube the liquid moves in layers and the volume passing per second "
               "is Q = π P r⁴ / (8 η l), where P = ρgh is the pressure difference across a tube of length l and bore "
               "radius r. So η = π ρ g h r⁴ / (8 l Q). The fourth power of the radius dominates everything: a tube 1 % "
               "wider passes 4 % more liquid. The head must be small enough to keep the flow in layers - if it becomes "
               "turbulent, Q no longer rises in proportion to h and the straight-line graph bends over.",
        safety="Clamp the reservoir firmly and keep the capillary horizontal. Wipe up spilled water at once: a wet "
               "bench and a glass tube are a bad pair.",
        tour=[{"say": "Water from the constant-head reservoir runs through the fine horizontal capillary into the measuring jar."},
              {"set": {"h": 40}, "say": "A larger head drives the water faster: Q is proportional to h."},
              {"set": {"h": 10}, "say": "A small head gives a slow, steady trickle. Record Q against h in the Table."}],
        questions=[{"q": "If the bore radius is 10 % larger, the flow rate rises by about",
                    "options": ["46 %", "10 %", "20 %", "It does not change"], "answer": 0,
                    "why": "Q goes as r⁴, and 1.1⁴ = 1.46."},
                   {"q": "Why is a constant-head reservoir used?",
                    "options": ["So the driving pressure does not fall as the liquid runs out",
                                "To warm the water", "To filter the water"], "answer": 0,
                    "why": "A falling level would change h, and so Q, during the reading."}],
        sources=[UGC, DU, IP, SIMK, CRC],
        check={"params": {"hh": 0.25}, "reading": "Q", "textbook": "pois_Q"},
    )


# ============================================================================ Jaeger's bubble method
def jaeger_bubble() -> dict:
    return lab(
        id="jaeger-bubble", title="Surface tension by Jaeger's bubble method",
        group="Physics · Properties of matter", level="B.Sc.", topic="Surface tension",
        chapter="Properties of matter: elasticity, viscosity, surface tension",
        aim="Read the manometer pressure at which a bubble just breaks away from a fine orifice under the liquid, and "
            "work out the surface tension.",
        kernel="jaeger", params={"Tst": 0.07275, "r": 0.0003, "hd": 0.04, "rhol": 998.2, "rhom": 998.2, "tau": 1.2},
        autorun=True,
        camera={"pos": [0.55, 0.5, 0.95], "look": [0.0, 0.2, -0.1]}, floor=-0.02,
        bodies=[
            B("asp", "cylinder", name="Aspirator bottle", info="Water drips out of it, so air is pushed slowly into the apparatus.",
              r=0.055, h=0.2, pos=[-0.34, 0.1, -0.14], color="glass", opacity=0.28),
            B("aspw", "cylinder", name="Water in the aspirator", r=0.052, h=0.13, pos=[-0.34, 0.075, -0.14], color="water"),
            B("tap", "cylinder", name="Stopcock", info="Turned a little open, so one bubble forms every few seconds.",
              r=0.006, h=0.04, pos=[-0.34, -0.005, -0.09], rot=[1.5708, 0, 0], color="glass", opacity=0.5),
            B("tube1", "cylinder", name="Air line", r=0.004, h=0.26, pos=[-0.2, 0.22, -0.14], rot=[0, 0, 1.5708],
              color="glass", opacity=0.4),
            B("mano1", "cylinder", name="Manometer (left limb)", info="A water manometer. Its difference of level H is the pressure inside the bubble.",
              r=0.006, h=0.3, pos=[-0.1, 0.17, -0.14], color="glass", opacity=0.35),
            B("mano2", "cylinder", name="Manometer (right limb)", r=0.006, h=0.3, pos=[-0.04, 0.17, -0.14],
              color="glass", opacity=0.35),
            B("manobend", "cylinder", r=0.006, h=0.06, pos=[-0.07, 0.03, -0.14], rot=[0, 0, 1.5708], color="glass", opacity=0.35),
            B("manow1", "cylinder", name="Manometer water", r=0.0045, h=0.14, pos=[-0.1, 0.1, -0.14], color="water",
              bind={"sy": {"var": "H_cm", "k": -0.06, "c": 1.0, "min": 0.3}, "y": {"var": "H_cm", "k": -0.0042, "c": 0.1}}),
            B("manow2", "cylinder", name="Manometer water", r=0.0045, h=0.14, pos=[-0.04, 0.1, -0.14], color="water",
              bind={"sy": {"var": "H_cm", "k": 0.06, "c": 1.0, "min": 0.3}, "y": {"var": "H_cm", "k": 0.0042, "c": 0.1}}),
            B("manoscale", "scale", name="Manometer scale (cm)", length=0.3, spacing=0.001, major=10, labels=True,
              label_step=10, tick=0.007, font=0.011, pos=[-0.015, 0.02, -0.148], rot=[0, 0, -1.5708]),
            B("beaker", "cylinder", name="Beaker of the liquid", info="The liquid under test. The orifice dips a measured depth below its surface.",
              r=0.055, h=0.14, open=True, pos=[0.22, 0.07, -0.1], color="glass", opacity=0.28),
            B("liq", "cylinder", name="Liquid under test", r=0.052, h=0.1, pos=[0.22, 0.05, -0.1], color="water"),
            B("tube2", "cylinder", name="Air line to the jet", r=0.004, h=0.2, pos=[0.06, 0.32, -0.12],
              rot=[0, 0, 1.5708], color="glass", opacity=0.4),
            B("jet", "cylinder", name="Capillary jet", info="Drawn to a fine orifice. Its radius r is measured with a travelling microscope.",
              r=0.0035, h=0.22, pos=[0.22, 0.2, -0.1], color="glass", opacity=0.45),
            B("bub", "sphere", name="Bubble at the orifice", info="The bubble grows until its radius equals the orifice radius; then it breaks away and the manometer falls back.",
              r=0.006, pos=[0.22, 0.086, -0.1], color="white", opacity=0.35),
            B("depth", "scale", name="Depth scale (cm)", length=0.12, spacing=0.001, major=10, labels=True,
              label_step=10, tick=0.006, font=0.01, pos=[0.26, 0.03, -0.055], rot=[0, 0, -1.5708]),
            B("lbl", "text", text="Jaeger's apparatus", size=0.02, pos=[-0.05, 0.44, -0.14]),
        ],
        knobs=[knob("hd", "Depth of the orifice below the surface", "hd", 2, 8, 0.5, 4, "cm", 0.01),
               knob("T", "Liquid (surface tension hidden)", "Tst", 0.02, 0.085, 0.0001, 0.07275, "N/m", hidden=True),
               knob("r", "Orifice radius r", "r", 0.15, 0.6, 0.01, 0.3, "mm", 0.001,
                    hint="Measured with a travelling microscope before the jet is dipped.")],
        instruments=[inst("h", "readout", "Manometer difference H", "H_cm", unit="cm", lc=0.1, digits=2),
                     inst("heq", "readout", "Settled value (help)", "H_eq_cm", unit="cm", digits=2, hint=True),
                     inst("gr", "graph", "H against time", "H_cm", xlabel="t (s)")],
        table={"columns": [col("hd", "Depth h of the orifice", "knob:hd", "cm", 0.01, digits=1),
                           col("H", "Manometer difference H", "inst:h", "cm", 0.01, digits=2)],
               "calc": "jaeger_T", "rows_min": 3, "truth": "p.Tst", "result_digits": 5,
               "hint": "Watch the manometer through several bubbles and take the highest steady reading for each depth."},
        steps=["Measure the orifice radius with a travelling microscope.",
               "Dip the jet a measured depth h below the liquid surface.",
               "Open the stopcock a little so one bubble forms every few seconds.",
               "Read the greatest manometer difference H just as a bubble breaks away; repeat for three depths.",
               "T = r g (H ρ_m − h ρ_l) / 2 for each depth; take the mean."],
        theory="Air is forced slowly through a fine orifice held a depth h below the surface of the liquid. The bubble "
               "grows, and its radius of curvature falls until it equals the radius r of the orifice: at that moment the "
               "excess pressure inside it is greatest, 2T/r, and the bubble breaks away. The manometer therefore reads a "
               "maximum H just then, and that pressure H ρ_m g must balance the hydrostatic pressure h ρ_l g at the "
               "orifice plus the excess pressure in the bubble: H ρ_m g = h ρ_l g + 2T/r. So "
               "T = r g (H ρ_m − h ρ_l) / 2. Because a fresh surface is made for every bubble, the method gives the "
               "surface tension of a clean surface, and it follows the surface tension as the liquid is warmed.",
        safety="Open the stopcock only a little: a fast stream of air throws liquid out of the beaker and the manometer "
               "reading means nothing. Glass jets are sharp and break easily.",
        tour=[{"say": "Air from the aspirator is pushed through the fine jet dipping in the liquid. Each bubble sends the manometer up."},
              {"set": {"hd": 8}, "say": "The deeper the orifice, the larger the manometer reading: more hydrostatic pressure to beat."},
              {"set": {"hd": 2}, "say": "Near the surface most of the pressure is the bubble's own. Record H for each depth."}],
        questions=[{"q": "Why is the manometer reading a maximum just as the bubble breaks away?",
                    "options": ["Its radius of curvature is then least, so the excess pressure is greatest",
                                "The air runs out", "The liquid cools"], "answer": 0,
                    "why": "Excess pressure is 2T/R, and R is least when it equals the orifice radius."},
                   {"q": "A wider orifice gives, for the same liquid,",
                    "options": ["a smaller manometer reading", "a larger reading", "the same reading"],
                    "answer": 0, "why": "The excess pressure 2T/r falls as r rises."}],
        sources=[UGC, DU, IP, SIMK, CRC],
        check={"params": {"hd": 0.04}, "reading": "H", "textbook": "jaeger_H"},
    )


# ============================================================================ Young's modulus by uniform bending
def uniform_bending() -> dict:
    return lab(
        id="uniform-bending", title="Young's modulus by uniform bending of a beam",
        group="Physics · Properties of matter", level="B.Sc.", topic="Elasticity",
        chapter="Properties of matter: elasticity, viscosity, surface tension",
        aim="Load a beam resting on two knife edges at both its overhanging ends, measure the rise of its middle with a "
            "travelling microscope and find Young's modulus.",
        kernel="unibend", params={"Y": 2.0e11, "b": 0.025, "d": 0.005, "L": 0.7, "a": 0.12, "m": 0.0, "tau": 0.5},
        autorun=True,
        camera={"pos": [0.3, 0.42, 0.95], "look": [0.0, 0.14, -0.1]}, floor=-0.02,
        bodies=[
            B("bench", "box", name="Levelled table", size=[1.1, 0.02, 0.3], pos=[0, -0.01, -0.1], color="wood", cut=False),
            B("ke1", "box", name="Knife edge", info="A hardened steel wedge. The beam only rests on it; it is not clamped.",
              size=[0.02, 0.1, 0.07], pos=[-0.35, 0.05, -0.1], color="#5a6068"),
            B("ke2", "box", name="Knife edge", size=[0.02, 0.1, 0.07], pos=[0.35, 0.05, -0.1], color="#5a6068"),
            B("beam", "box", name="Experimental beam", info="A uniform rectangular bar. Its breadth b and depth d are measured with a vernier and a screw gauge.",
              size=[0.94, 0.005, 0.025], pos=[0, 0.1025, -0.1], color="steel"),
            B("hook1", "cylinder", name="Hook", r=0.003, h=0.04, pos=[-0.47, 0.08, -0.1], color="#c3c8ce"),
            B("hook2", "cylinder", name="Hook", r=0.003, h=0.04, pos=[0.47, 0.08, -0.1], color="#c3c8ce"),
            B("pan1", "cylinder", name="Weight hanger", info="Equal loads hang at the two ends, a measured distance a beyond each knife edge.",
              r=0.03, h=0.012, pos=[-0.47, 0.03, -0.1], color="brass",
              bind={"y": {"var": "delta", "k": -1.0, "c": 0.03}}),
            B("pan2", "cylinder", name="Weight hanger", r=0.03, h=0.012, pos=[0.47, 0.03, -0.1], color="brass",
              bind={"y": {"var": "delta", "k": -1.0, "c": 0.03}}),
            B("pin", "cylinder", name="Pin at the centre", info="A fine pin stuck upright on the middle of the beam: the travelling microscope follows its tip.",
              r=0.0006, h=0.03, pos=[0, 0.12, -0.1], color="#c3c8ce",
              bind={"y": {"var": "delta", "k": 1.0, "c": 0.12}}),
            B("mpost", "box", name="Travelling microscope (pillar)", info="Its carriage runs up and down against a vernier reading to 0.001 cm.",
              size=[0.035, 0.3, 0.035], pos=[0.14, 0.15, 0.08], color="#2b3138"),
            B("mscale", "scale", name="Vertical scale (cm)", length=0.26, spacing=0.001, major=10, labels=True,
              label_step=10, tick=0.008, font=0.012, pos=[0.158, 0.02, 0.098]),
            B("mtube", "cylinder", name="Microscope tube", r=0.013, h=0.11, pos=[0.075, 0.135, 0.08],
              rot=[0, 0, 1.5708], color="black"),
            B("lbl", "text", text="Uniform bending", size=0.022, pos=[0.0, 0.2, -0.1]),
        ],
        knobs=[knob("m", "Load on each hanger", "m", 0, 2.5, 0.5, 0, "kg"),
               knob("Y", "Beam material (Y hidden)", "Y", 50, 250, 1, 200, "GPa", 1e9, hidden=True),
               knob("L", "Distance between the knife edges L", "L", 50, 90, 5, 70, "cm", 0.01),
               knob("a", "Overhang a of each load", "a", 6, 18, 1, 12, "cm", 0.01)],
        instruments=[inst("d", "readout", "Rise of the middle δ", "delta_mm", unit="mm", lc=0.01, digits=3),
                     inst("ld", "readout", "Load on each hanger", "load_N", unit="N", digits=1),
                     inst("gr", "graph", "Rise against load", "delta_mm", x="knob:m", xlabel="m (kg)", dots=True)],
        table={"columns": [col("m", "Load m on each hanger", "knob:m", "kg", digits=1),
                           col("delta", "Rise of the middle δ", "inst:d", "mm", 0.001, digits=3)],
               "calc": "uni_Y", "rows_min": 3, "truth": "p.Y", "result_digits": 0,
               "hint": "Read the pin's tip with the microscope at each load, loading and then unloading."},
        steps=["Measure the beam's breadth b with a vernier calliper and its depth d with a screw gauge.",
               "Rest the beam on the two knife edges and measure the distance L between them and the overhang a.",
               "Focus the travelling microscope on the pin at the middle and note the reading with no load.",
               "Add equal loads to both hangers in steps and read the microscope each time; then unload in the same steps.",
               "Y = 3 m g a L² / (2 b d³ δ) from the mean of the loading and unloading readings."],
        theory="When equal loads W hang beyond each knife edge the bending moment between the edges is the same "
               "everywhere, W a: the beam bends into an arc of a single radius, which is why this is called uniform "
               "bending. The middle therefore rises above the knife edges by δ = W a L² / (8 Y I), and for a rectangular "
               "section I = b d³ / 12, so Y = 3 m g a L² / (2 b d³ δ). The depth comes in as the cube: a 1 % error in d "
               "gives a 3 % error in Y, so d must be measured with a screw gauge at several places and averaged. The "
               "beam only rests on the knife edges, so nothing is clamped and the ends are free to turn.",
        safety="Add and remove the loads on both sides together: a one-sided load tips the beam off its knife edges. "
               "Keep the loads well clear of your feet.",
        tour=[{"say": "A steel bar rests on two knife edges, with equal loads hanging beyond each end. A pin stands on its middle."},
              {"set": {"m": 2.5}, "say": "Under 2.5 kg at each end the middle has risen by a fraction of a millimetre."},
              {"set": {"m": 1.0}, "say": "Half the load, half the rise: δ is proportional to the load. Record δ against m."}],
        questions=[{"q": "Why is the bending called uniform here?",
                    "options": ["The bending moment is the same all along the beam between the knife edges",
                                "The beam has uniform density", "The load is spread evenly"], "answer": 0,
                    "why": "With equal loads beyond the supports the moment between them is constant, W a."},
                   {"q": "If the depth d is measured 2 % too large, Y comes out",
                    "options": ["about 6 % too small", "2 % too small", "unchanged"], "answer": 0,
                    "why": "Y goes as 1/d³, so a 2 % error in d gives about 6 % in Y."}],
        sources=[UGC, DU, IP, SIMK, CRC],
        check={"params": {"m": 1.0}, "reading": "delta", "textbook": "uni_delta"},
    )


# =========================================================== travelling microscope: least count, repeated readings
def _tm_bodies(sample_name: str, sample_info: str) -> list[dict]:
    return [
        B("slab", "box", name="Levelled base", size=[0.5, 0.025, 0.3], pos=[0, -0.0125, -0.1], color="#2b3138"),
        B("rail", "box", name="Horizontal rail", info="The microscope's carriage slides along this rail against a vernier scale.",
          size=[0.42, 0.02, 0.05], pos=[0, 0.012, -0.2], color="#5a6068"),
        B("hscale", "scale", name="Horizontal scale (cm)", length=0.4, spacing=0.001, major=10, labels=True,
          label_step=10, tick=0.007, font=0.011, pos=[-0.2, 0.023, -0.178], rot=[0, 0, -1.5708], down=True),
        B("pillar", "box", name="Vertical pillar", size=[0.035, 0.26, 0.035], pos=[0.0, 0.14, -0.2], color="#2b3138"),
        B("vscale", "scale", name="Vertical scale (cm)", length=0.22, spacing=0.001, major=10, labels=True,
          label_step=10, tick=0.007, font=0.011, pos=[0.019, 0.03, -0.182]),
        B("vern", "box", name="Vernier plate", info="Fifty divisions of the vernier cover forty-nine of the main scale: least count 0.001 cm.",
          size=[0.016, 0.03, 0.004], pos=[0.021, 0.12, -0.18], color="brass"),
        B("carr", "box", name="Microscope carriage", size=[0.05, 0.05, 0.05], pos=[0.045, 0.12, -0.2], color="#5a6068"),
        B("tube", "cylinder", name="Microscope tube", info="A low-power microscope with cross-wires in the eyepiece.",
          r=0.014, h=0.14, pos=[0.045, 0.12, -0.11], rot=[1.5708, 0, 0], color="black"),
        B("eye", "cylinder", name="Eyepiece", r=0.011, h=0.03, pos=[0.045, 0.12, -0.028], rot=[1.5708, 0, 0], color="#1b1b1d"),
        B("obj", "cylinder", name="Objective", r=0.009, h=0.02, pos=[0.045, 0.12, -0.19], rot=[1.5708, 0, 0], color="#c3c8ce"),
        B("knob1", "cylinder", name="Fine screw", info="Turns the carriage a little at a time; the vernier reads how far it has moved.",
          r=0.012, h=0.01, pos=[-0.07, 0.022, -0.2], rot=[0, 0, 1.5708], color="brass"),
        B("stage", "box", name="Glass stage", size=[0.13, 0.006, 0.1], pos=[0.045, 0.004, -0.06], color="glass", opacity=0.3),
        B("sample", "cylinder", name=sample_name, info=sample_info, r=0.012, h=0.008, pos=[0.045, 0.011, -0.06],
          color="steel"),
        B("lamp", "cylinder", name="Lamp", info="Lights the object from the side so the cross-wire can be set on its edge.",
          r=0.02, h=0.04, pos=[-0.14, 0.03, -0.05], rot=[0, 0, 1.2], color="#3a4149"),
        B("lbl", "text", text="Travelling microscope", size=0.018, pos=[0.0, 0.3, -0.2]),
    ]


def travelling_microscope() -> dict:
    return lab(
        id="travelling-microscope", title="Least count and use of a travelling microscope",
        group="Physics · Measurement", level="B.Sc.", topic="Measurement and error analysis",
        chapter="Measurement and error analysis",
        aim="Work out the least count of a travelling microscope, measure a small dimension with it several times over, "
            "and report the mean with its standard error.",
        kernel="travmicro", params={"L": 0.025, "pitch": 0.0005, "ndiv": 50.0, "sigma": 0.00008, "nrep": 10.0,
                                    "seed": 7.0, "idx": 0.0, "ze": 0.0},
        camera={"pos": [0.34, 0.33, 0.45], "look": [0.02, 0.09, -0.12]}, floor=-0.03,
        bodies=_tm_bodies("Steel disc on the stage",
                          "The object whose diameter is measured: the cross-wire is set on one edge and then the other."),
        knobs=[knob("L", "Object on the stage (true size hidden)", "L", 5, 50, 0.001, 25, "mm", 0.001, hidden=True),
               knob("n", "Readings to take", "nrep", 5, 20, 1, 10, "readings"),
               knob("idx", "Reading number", "idx", 0, 19, 1, 0, "")],
        instruments=[inst("x", "readout", "This reading", "x_mm", unit="mm", lc=0.01, digits=3),
                     inst("mean", "readout", "Mean so far (help)", "mean_mm", unit="mm", digits=3, hint=True),
                     inst("sd", "readout", "Spread of the readings (help)", "sd_mm", unit="mm", digits=3, hint=True),
                     inst("lc", "readout", "Least count", "lc_mm", unit="mm", digits=3)],
        table={"columns": [col("x", "Reading", "inst:x", "mm", 0.001, digits=3)],
               "calc": "tm_mean", "rows_min": 5, "truth": "p.L", "result_digits": 6,
               "hint": "Set the cross-wire on each edge in turn and take the difference; do it ten times over."},
        steps=["Count the main-scale pitch and the number of vernier divisions, and work out the least count.",
               "Set the cross-wire on one edge of the object and read the main scale and the vernier.",
               "Move the carriage to the other edge, read again, and take the difference.",
               "Repeat the whole measurement ten times, setting the cross-wire afresh each time.",
               "Report the mean, the standard deviation and the standard error of the mean."],
        theory="The least count of an instrument is the smallest difference it can show: for a vernier it is one "
               "main-scale division divided by the number of vernier divisions, here 0.5 mm / 50 = 0.01 mm = 0.001 cm. "
               "Setting the cross-wire on an edge is a judgement, so repeated readings of the same object are not all "
               "the same. The best estimate is their mean; the spread is the standard deviation "
               "s = √(Σ(x − x̄)² / (n − 1)); and the uncertainty of the mean is the standard error s/√n, which falls as "
               "more readings are taken. A result is written as mean ± standard error, to no more decimal places than "
               "the least count justifies.",
        safety="Move the carriage with the fine screw only, and never force it past the end of the rail. Do not touch "
               "the objective lens.",
        tour=[{"say": "A travelling microscope: the carriage slides along the rail and the vernier reads how far it moved."},
              {"set": {"idx": 3}, "say": "A second setting of the cross-wire gives a slightly different reading. That is the random error."},
              {"set": {"idx": 0}, "say": "Take ten readings in the Table; the mean of them is far better than any one of them."}],
        questions=[{"q": "The least count of a travelling microscope whose main scale is in half-millimetres with a "
                         "50-division vernier is",
                    "options": ["0.001 cm", "0.01 cm", "0.05 cm", "0.1 cm"], "answer": 0,
                    "why": "0.5 mm / 50 = 0.01 mm = 0.001 cm."},
                   {"q": "Taking four times as many readings reduces the standard error of the mean to",
                    "options": ["half", "a quarter", "the same", "a sixteenth"], "answer": 0,
                    "why": "The standard error goes as 1/√n."}],
        sources=[UGC, DU, SIMK],
        check={"params": {"nrep": 10.0}, "reading": "mean", "textbook": "tm_L"},
    )


def random_errors() -> dict:
    d = lab(
        id="random-errors", title="Random errors in repeated observations",
        group="Physics · Measurement", level="B.Sc.", topic="Measurement and error analysis",
        chapter="Measurement and error analysis",
        aim="Take twenty readings of the same small dimension near the least count of the instrument and study how the "
            "readings scatter about their mean.",
        kernel="travmicro", params={"L": 0.025, "pitch": 0.0005, "ndiv": 50.0, "sigma": 0.00012, "nrep": 20.0,
                                    "seed": 11.0, "idx": 0.0, "ze": 0.0},
        camera={"pos": [0.34, 0.33, 0.45], "look": [0.02, 0.09, -0.12]}, floor=-0.03,
        bodies=_tm_bodies("Glass plate on the stage",
                          "A plate whose thickness is read again and again: the same object, twenty separate settings."),
        knobs=[knob("L", "Object on the stage (true size hidden)", "L", 5, 50, 0.001, 25, "mm", 0.001, hidden=True),
               knob("n", "Readings to take", "nrep", 10, 25, 1, 20, "readings"),
               knob("idx", "Reading number", "idx", 0, 24, 1, 0, "")],
        instruments=[inst("x", "readout", "This reading", "x_mm", unit="mm", lc=0.01, digits=3),
                     inst("mean", "readout", "Mean so far (help)", "mean_mm", unit="mm", digits=3, hint=True),
                     inst("sd", "readout", "Standard deviation (help)", "sd_mm", unit="mm", digits=3, hint=True),
                     inst("lc", "readout", "Least count", "lc_mm", unit="mm", digits=3)],
        table={"columns": [col("x", "Reading", "inst:x", "mm", 0.001, digits=3)],
               "calc": "tm_mean", "rows_min": 10, "truth": "p.L", "result_digits": 6,
               "hint": "Twenty independent settings of the cross-wire on the same object."},
        steps=["Work out the least count of the instrument.",
               "Take twenty readings of the same dimension, setting the cross-wire afresh every time.",
               "Make a frequency table of the readings and draw a histogram.",
               "Work out the mean, the standard deviation and the standard error of the mean.",
               "Compare the histogram with the Gaussian curve of that mean and standard deviation."],
        theory="Random errors come from the limit of the observer's judgement, not from a fault in the instrument: they "
               "are as likely to be above the true value as below it, so they can be reduced by taking more readings but "
               "never removed by a correction. If the readings of one quantity are x₁ … xₙ, their mean x̄ is the best "
               "estimate, the standard deviation s = √(Σ(x − x̄)²/(n − 1)) measures the scatter of a single reading, and "
               "the standard error s/√n measures the uncertainty of the mean. A histogram of a large set of such readings "
               "follows the Gaussian curve: about 68 % of them lie within one standard deviation of the mean and about "
               "95 % within two. A systematic error, by contrast, shifts every reading the same way and the mean does not "
               "improve with n.",
        safety="Nothing in this experiment is dangerous, but do not lean on the bench: a knock moves the carriage and "
               "spoils the reading you are taking.",
        tour=[{"say": "The same object, measured again and again. Watch how much the readings differ."},
              {"set": {"idx": 5}, "say": "This setting reads a little high; another will read a little low. The errors are random."},
              {"set": {"idx": 0}, "say": "Take twenty readings into the Table and look at how they bunch about the mean."}],
        questions=[{"q": "Taking more readings reduces",
                    "options": ["the random error of the mean", "a systematic error", "the least count"],
                    "answer": 0, "why": "The standard error of the mean falls as 1/√n; a systematic error does not."},
                   {"q": "About what fraction of readings lies within one standard deviation of the mean?",
                    "options": ["About 68 %", "About 50 %", "About 95 %", "All of them"], "answer": 0,
                    "why": "That is the Gaussian 1σ band."}],
        sources=[UGC, DU, SIMK],
        check={"params": {"nrep": 20.0}, "reading": "mean", "textbook": "tm_L"},
    )
    d["rig"] = "travelling-microscope"
    return d


# ============================================================================ collisions on an air track
def air_track() -> dict:
    return lab(
        id="air-track", title="Conservation of linear momentum in collisions on an air track",
        group="Physics · Mechanics", level="B.Sc.", topic="Collisions and momentum", chapter="Mechanics",
        aim="Send one glider into another on an air track, time both of them through photo-gates, and check that the "
            "momentum before the collision equals the momentum after it.",
        kernel="collide1d", params={"m1": 0.2, "m2": 0.3, "u1": 0.4, "e": 1.0, "gap": 0.4, "x20": 0.4},
        speeds=[0.25, 0.5, 1, 2],
        camera={"pos": [0.3, 0.42, 0.95], "look": [0.0, 0.1, -0.1]}, floor=-0.02,
        bodies=[
            B("track", "box", name="Air track", info="Air blown out of fine holes along the top lifts the gliders clear of the metal, so friction is almost nothing.",
              size=[1.9, 0.05, 0.08], pos=[0, 0.08, -0.1], color="#aeb4ba"),
            B("leg1", "box", name="Levelling foot", size=[0.05, 0.055, 0.1], pos=[-0.8, 0.0275, -0.1], color="#5a6068"),
            B("leg2", "box", name="Levelling foot", size=[0.05, 0.055, 0.1], pos=[0.8, 0.0275, -0.1], color="#5a6068"),
            B("blow", "box", name="Air blower", info="Keeps the air cushion up. The track must be level before any reading is taken.",
              size=[0.16, 0.12, 0.14], pos=[-1.0, 0.06, -0.1], color="#3a4149"),
            B("hose", "cylinder", name="Hose", r=0.016, h=0.14, pos=[-0.9, 0.08, -0.1], rot=[0, 0, 1.5708], color="#2b3138"),
            B("g1", "box", name="Glider 1", info="The glider that is pushed. Its mass m₁ is weighed on a balance.",
              size=[0.1, 0.06, 0.1], pos=[-0.5, 0.135, -0.1], color="#cdd2d7",
              bind={"x": {"var": "x1", "k": 1.0, "c": -0.5}}),
            B("g2", "box", name="Glider 2", info="The glider that waits at rest. Its mass m₂ is what you work out from the collision.",
              size=[0.1, 0.06, 0.1], pos=[-0.1, 0.135, -0.1], color="#d8c08a",
              bind={"x": {"var": "x2", "k": 1.0, "c": -0.5}}),
            B("spr1", "box", name="Spring bumper", info="For an elastic collision. Swap it for a wax pad and the gliders stick together.",
              size=[0.012, 0.03, 0.03], pos=[-0.444, 0.135, -0.1], color="#c3c8ce",
              bind={"x": {"var": "x1", "k": 1.0, "c": -0.444}}),
            B("spr2", "box", name="Spring bumper", size=[0.012, 0.03, 0.03], pos=[-0.156, 0.135, -0.1], color="#c3c8ce",
              bind={"x": {"var": "x2", "k": 1.0, "c": -0.156}}),
            B("gate1", "box", name="Photo-gate 1", info="A light beam across the track. The flag on the glider cuts it, and the timer reads how long for.",
              size=[0.016, 0.14, 0.03], pos=[-0.62, 0.15, -0.16], color="#2b3138"),
            B("gate2", "box", name="Photo-gate 2", size=[0.016, 0.14, 0.03], pos=[0.18, 0.15, -0.16], color="#2b3138"),
            B("gate3", "box", name="Photo-gate 3", size=[0.016, 0.14, 0.03], pos=[0.62, 0.15, -0.16], color="#2b3138"),
            B("timer", "box", name="Digital timer", info="Reads the time each flag takes to cross a gate, to a millisecond.",
              size=[0.18, 0.06, 0.12], pos=[0.42, 0.03, 0.12], color="#1b1b1d"),
            B("tscale", "scale", name="Track scale (cm)", length=1.6, spacing=0.002, major=5, labels=True,
              label_step=25, tick=0.006, font=0.012, pos=[-0.8, 0.106, -0.062], rot=[0, 0, -1.5708]),
            B("lbl", "text", text="Air track", size=0.024, pos=[0.0, 0.26, -0.1]),
        ],
        knobs=[knob("u1", "Push given to glider 1", "u1", 0.15, 0.6, 0.05, 0.4, "m/s"),
               knob("m2", "Glider 2 (its mass is hidden)", "m2", 0.1, 0.5, 0.01, 0.3, "kg", hidden=True),
               knob("e", "Bumpers: 1 = springs (elastic), 0 = wax (sticking)", "e", 0, 1, 1, 1, "")],
        instruments=[inst("v1", "readout", "Glider 1 after the collision", "v1", unit="m/s", lc=0.001, digits=3),
                     inst("v2", "readout", "Glider 2 after the collision", "v2", unit="m/s", lc=0.001, digits=3),
                     inst("pb", "readout", "Momentum before", "p_before", unit="kg·m/s", digits=4, hint=True),
                     inst("pa", "readout", "Momentum after", "p_after", unit="kg·m/s", digits=4, hint=True)],
        table={"columns": [col("u1", "u₁ before", "knob:u1", "m/s", digits=3),
                           col("v1", "v₁ after", "inst:v1", "m/s", digits=3),
                           col("v2", "v₂ after", "inst:v2", "m/s", digits=3)],
               "calc": "coll_m2", "rows_min": 2, "truth": "p.m2", "result_digits": 3,
               "hint": "One run gives u₁, v₁ and v₂; repeat at two or three different pushes."},
        steps=["Level the track with the blower running: a glider left alone must not drift either way.",
               "Weigh glider 1 and fit spring bumpers to both gliders.",
               "Push glider 1 so it goes through the first gate at a steady speed and strikes glider 2 at rest.",
               "Read the timer for all three gates and work out u₁, v₁ and v₂.",
               "Check that m₁u₁ = m₁v₁ + m₂v₂, and work out m₂ from it. Repeat with wax pads for a sticking collision."],
        theory="Nothing pushes the pair along the track while they strike, so their total momentum cannot change: "
               "m₁u₁ = m₁v₁ + m₂v₂, whatever happens to the kinetic energy. With spring bumpers the collision is nearly "
               "elastic and the kinetic energy is almost the same afterwards; with wax pads the gliders stick, move off "
               "together, and a definite amount of kinetic energy is lost - but the momentum is unchanged in both cases. "
               "The coefficient of restitution e = (v₂ − v₁)/u₁ is 1 for the springs and 0 for the pads, and the "
               "measured velocities give the unknown mass m₂ = m₁(u₁ − v₁)/v₂.",
        safety="Do not run the gliders off the ends of the track: keep the end stops in place. Switch the blower off "
               "before lifting a glider, or it will slide away.",
        tour=[{"say": "Two gliders float on a cushion of air. The left one is pushed; the right one waits at rest."},
              {"set": {"e": 0}, "say": "With wax pads they stick together and move off as one. Momentum is still conserved."},
              {"set": {"e": 1}, "say": "With springs the lighter glider bounces back. Record u₁, v₁ and v₂ in the Table."}],
        questions=[{"q": "In a sticking (perfectly inelastic) collision, what is conserved?",
                    "options": ["Momentum only", "Kinetic energy only", "Both momentum and kinetic energy",
                                "Neither"], "answer": 0,
                    "why": "No outside force acts along the track, so momentum is conserved; some kinetic energy becomes heat."},
                   {"q": "A light glider striking a heavier one head on, elastically,",
                    "options": ["bounces back", "stops dead", "goes on at the same speed"], "answer": 0,
                    "why": "v₁ = (m₁ − m₂)u₁/(m₁ + m₂) is negative when m₂ > m₁."}],
        sources=[UGC, DU, SIMK],
        check={"params": {"u1": 0.4}, "reading": "v2", "textbook": "coll_v2"},
    )


# ============================================================================ g by free fall (digital timing)
def free_fall_timer() -> dict:
    return lab(
        id="free-fall-timer", title="g by digital timing of a freely falling body",
        group="Physics · Mechanics", level="B.Sc.", topic="Motion under gravity", chapter="Mechanics",
        aim="Drop a steel ball from an electromagnet through a measured height, time the fall with a digital timer and "
            "find the acceleration due to gravity.",
        kernel="freefall", params={"g": 9.8, "h": 0.5, "t0": 0.0}, speeds=[0.1, 0.25, 0.5, 1],
        camera={"pos": [0.6, 0.55, 1.1], "look": [0.0, 0.42, -0.12]}, floor=-0.02,
        bodies=[
            B("base", "box", name="Heavy base", size=[0.3, 0.03, 0.22], pos=[-0.22, 0.015, -0.12], color="#2b3138"),
            B("col", "cylinder", name="Vertical column", info="A rigid steel column carrying the magnet and the gates.",
              r=0.016, h=1.3, pos=[-0.22, 0.65, -0.12], color="steel"),
            B("arm", "box", size=[0.2, 0.016, 0.016], pos=[-0.12, 1.26, -0.12], color="steel"),
            B("mag", "box", name="Electromagnet", info="Holds the ball until the switch is pressed; the same press starts the timer.",
              size=[0.05, 0.04, 0.05], pos=[-0.02, 1.24, -0.12], color="#3a4149"),
            B("ball", "sphere", name="Steel ball", info="A smooth steel ball. Air resistance over this short fall is negligible.",
              r=0.009, pos=[-0.02, 1.21, -0.12], color="steel", bind={"y": {"var": "y", "k": -1.0, "c": 1.21}}),
            B("gate", "box", name="Receiver pad", info="A switch pad. The ball landing on it stops the timer.",
              size=[0.1, 0.02, 0.1], pos=[-0.02, 0.21, -0.12], color="#2b3138",
              bind={"y": {"var": "t_fall", "k": 0.0, "c": 0.21}}),
            B("gpost", "cylinder", name="Pad clamp", r=0.012, h=0.2, pos=[-0.12, 0.11, -0.12], color="#5a6068"),
            B("scale", "scale", name="Metre scale (cm)", length=1.1, spacing=0.001, major=10, labels=True,
              label_step=10, tick=0.008, font=0.012, pos=[-0.195, 0.16, -0.095], rot=[0, 0, -1.5708]),
            B("timer", "box", name="Digital timer", info="Reads the fall to a millisecond. It starts when the magnet lets go and stops when the ball lands.",
              size=[0.2, 0.07, 0.13], pos=[0.26, 0.035, 0.06], color="#1b1b1d"),
            B("tface", "box", name="Timer display", size=[0.14, 0.001, 0.05], pos=[0.26, 0.072, 0.055], color="#9eab8b"),
            B("lbl", "text", text="Free fall", size=0.024, pos=[0.0, 1.33, -0.12]),
        ],
        knobs=[knob("h", "Height of fall h", "h", 20, 100, 10, 50, "cm", 0.01,
                    hint="From the bottom of the ball at the magnet to the top of the pad."),
               knob("g", "Place (g hidden)", "g", 9.6, 10.0, 0.001, 9.8, "m/s²", hidden=True)],
        instruments=[inst("y", "readout", "Distance fallen", "y", k=100, unit="cm", digits=1),
                     inst("v", "readout", "Speed now", "v", unit="m/s", digits=2),
                     inst("sw", "stopwatch", "Digital timer"),
                     inst("gr", "graph", "Distance fallen against time", "y", k=100, xlabel="t (s)")],
        table={"columns": [col("h", "Height of fall h", "knob:h", "cm", 0.01, digits=1),
                           col("t", "Time of fall t", "inst:sw", "s", digits=4)],
               "calc": "ff_g", "rows_min": 3, "truth": "p.g", "result_digits": 3,
               "hint": "For each height: hold the ball on the magnet, press the release and read the timer."},
        steps=["Measure the height h from the ball on the magnet to the pad with a metre scale.",
               "Press the release: the magnet lets the ball go and the timer starts.",
               "Read the time when the ball lands on the pad and stops the timer.",
               "Repeat for at least three heights, three drops at each.",
               "g = 2h / t² for each height; or take the slope of h against t²."],
        theory="A body let go from rest and acted on by gravity alone falls h = ½gt² in a time t, so g = 2h/t². The "
               "whole difficulty is the timing: at h = 0.5 m the fall lasts about 0.32 s, so a hand-held stopwatch with "
               "a reaction time of 0.2 s is useless and the timing has to be done electrically. The electromagnet "
               "releases the ball and starts the timer at the same instant, and the ball itself stops the timer when it "
               "lands. A graph of h against t² is a straight line through the origin of slope g/2, which also shows up "
               "any constant delay in the release as an intercept.",
        safety="Do not stand under the ball, and keep the base clear so a bouncing ball cannot reach anyone's feet. "
               "Switch the magnet off before putting your hand near it.",
        tour=[{"say": "A steel ball hangs from the electromagnet at the top of the column, with the receiver pad below."},
              {"set": {"h": 100}, "say": "From a metre up the fall lasts about 0.45 seconds."},
              {"set": {"h": 20}, "say": "From 20 cm it is only 0.2 seconds - far too quick for a hand-held stopwatch."}],
        questions=[{"q": "Why is a digital timer needed instead of a stopwatch?",
                    "options": ["The fall lasts a fraction of a second, less than a human reaction time",
                                "Stopwatches cannot read seconds", "The ball is too small"], "answer": 0,
                    "why": "A reaction time of about 0.2 s is comparable with the whole fall."},
                   {"q": "The graph of h against t² for a freely falling body is",
                    "options": ["a straight line of slope g/2", "a parabola", "a horizontal line"], "answer": 0,
                    "why": "h = ½gt²."}],
        sources=[UGC, DU, SIMK],
        check={"params": {"h": 0.5}, "reading": "t", "textbook": "ff_t"},
    )


BUILDERS = (torsional_pendulum, inertia_table, static_torsion, flywheel_bench, bar_pendulum, poiseuille_flow,
            jaeger_bubble, uniform_bending, travelling_microscope, random_errors, air_track, free_fall_timer)
