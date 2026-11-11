"""Lab pack `ug_em_w7`: the B.Sc. ELECTRICITY AND MAGNETISM set-ups of `syllabus/physics/ug.json` that were still
unbuilt (DU LOCF 2019 / UGCF 2022 practical lists; Indu Prakash and Ramakrishna's Practical Physics). The physics is
in `packs/ug_em_w7.py` (and its JavaScript twin). Two studio rigs draw the benches:

  rig `bg-lamp-scale`       a ballistic galvanometer read with a lamp and scale, and the accessory each set-up
                            needs: constants of the instrument, a high resistance by leakage, Rayleigh's method,
                            mutual inductance, the earth inductor, the field along a solenoid
  rig `em-ug-instruments`   the instrument bench: Carey Foster's bridge, a low resistance on the potentiometer,
                            Anderson's bridge, a universal R / L / C bridge, the Q-meter, RC and RL time constants,
                            a transformer, a DC motor, a generator, a magnet falling through a coil, a galvanometer
                            made into a meter, a regulated source, the magnetometers, and the B-H loop

Every lab's `check` compares one reading the kernel finds on its own simulated circuit or motion with the textbook
relation. Nothing here is at mains voltage: the transformer and the generator run on a low-voltage laboratory supply.
Values not taken from a table are marked "from memory - verify" or "illustrative" in the lab that uses them.
"""
from __future__ import annotations

from ..catalog import B, SIM, board, inst, knob, lab

GROUP = "Physics · Electricity and magnetism"
LEVEL = "B.Sc. (Hons.) Physics"
CH_EM = "Electricity and magnetism"
CH_AC = "AC circuits and bridges"
CH_NET = "Network theorems and electrical skills"
BG_RIG = "bg-lamp-scale"
IN_RIG = "em-ug-instruments"

DU = {"title": "University of Delhi B.Sc. (Hons.) Physics practical lists (LOCF 2019 C-III Electricity and Magnetism "
               "Lab, SEC Electrical Circuits and Network Skills; UGCF 2022 DSC 5, DSC 6, SEC 1, SEC 11)"}
IP = {"title": "Indu Prakash and Ramakrishna, A Text Book of Practical Physics (ballistic galvanometer, Carey Foster "
               "bridge, magnetometers, earth inductor)", "note": "cited from memory, not fetched - verify"}
WF = {"title": "B. L. Worsnop and H. T. Flint, Advanced Practical Physics for Students (ballistic galvanometer, "
               "Rayleigh's method, mutual inductance, Anderson's bridge)",
      "note": "cited from memory, not fetched - verify"}
SAW = {"title": "A. K. Sawhney, A Course in Electrical and Electronic Measurements and Instrumentation (AC bridges, "
                "Q-meter, potentiometers)", "note": "cited from memory, not fetched - verify"}
THER = {"title": "B. L. Theraja, A Textbook of Electrical Technology, Vol. II (transformers, DC machines)",
        "note": "cited from memory, not fetched - verify"}
ILLUS = {"title": "Illustrative laboratory values", "note": "The instrument constants and the hidden component values "
         "of this lab are chosen to be typical of a teaching laboratory; they are not properties of a named material."}
MEM_FIELD = {"title": "Earth's field values used here (horizontal about 35 to 36 microtesla, dip about 42 degrees, "
                      "typical of north India)", "note": "from memory - verify against the IGRF / WMM model for a real site"}
MEM_BH = {"title": "Soft iron and hardened carbon steel loop values (coercive field of order 80 A/m and 4 kA/m, "
                   "saturation about 2.1 T and 2.0 T)", "note": "from memory - verify against Cullity and Graham, "
          "Introduction to Magnetic Materials, or Bozorth, Ferromagnetism"}
MEM_MAG = {"title": "Neodymium magnet moment of about 0.75 A m2 for a 10 mm x 10 mm cylinder (remanence about 1.2 T)",
           "note": "from memory - verify against the maker's data sheet"}


def _q(q, opts, ans, why):
    return {"q": q, "options": opts, "answer": ans, "why": why}


def _bodies(name: str, info: str, extra: list[dict] | None = None) -> list[dict]:
    return [board(1.2, 0.6),
            B("main", "box", name=name, info=info, size=[0.36, 0.08, 0.2], pos=[0.0, 0.04, -0.15], color="#2b2f36"),
            B("meter", "box", name="Meter", info="The reading is taken here.", size=[0.12, 0.06, 0.1],
              pos=[0.38, 0.03, -0.1], color="#3a4f6e")] + list(extra or [])


def _mk(id, rig, title, aim, kernel, params, knobs, insts, theory, steps, questions, sources, check, chapter,
        safety=None, name="Apparatus", info="The apparatus of this experiment.", tour=None, topic=None):
    return lab(
        id=id, rig=rig, title=title, group=GROUP, level=LEVEL, topic=topic or chapter, chapter=chapter, aim=aim,
        kernel=kernel, params=params, autorun=True, camera={"pos": [0.0, 0.75, 0.95], "look": [0, 0.05, -0.1]},
        floor=-0.03, bodies=_bodies(name, info), knobs=knobs, instruments=insts, steps=steps, theory=theory,
        safety=safety or "Low-voltage bench supplies only. Switch off before changing a connection, and press a "
                         "tapping key only for a moment.",
        tour=tour or [{"say": "The apparatus is on the bench, its meter beside it and the record book on the left."}],
        questions=questions, sources=sources, check=check)


_BG_INST = [inst("d", "readout", "Spot of light on the scale", "d", k=1000, unit="mm", lc=0.5, digits=1)]
_BG_SAFETY = ("The suspension of a ballistic galvanometer is a fine strip: never jolt the instrument, and close the "
              "damping key to bring the coil to rest instead of touching it. Use the tapping keys only for a moment.")


# ============================================================================================ ballistic galvanometer
def bg_constants() -> dict:
    return _mk(
        "ballistic-galvanometer-constants", BG_RIG,
        "Current and charge sensitivity and CDR of a ballistic galvanometer",
        "Find the current sensitivity of a ballistic galvanometer from a steady deflection, its charge sensitivity "
        "from the throw when a capacitor is discharged through it, and its critical damping resistance.",
        "w7_bg", {"mode": 0.0},
        [knob("R", "Series resistance box", "R", 0, 5000, 1, 350, "Ω"),
         knob("Vq", "Capacitor charging voltage", "Vq", 0.2, 2.5, 0.1, 2.0, "V"),
         knob("Kc", "Coil constant nAB (hidden)", "Kc", 0.002, 0.05, 0.0001, 0.01, "N m/A", hidden=True)],
        _BG_INST,
        "A moving-coil galvanometer with a heavy coil and a long period is ballistic: a charge passed quickly gives "
        "the coil a kick, and the first throw is proportional to the charge. A steady current i gives a steady "
        "deflection, and d / i is the current sensitivity. For a charge q the throw d1, corrected for damping by the "
        "factor (1 + λ/2) where λ is the logarithmic decrement, gives the charge sensitivity d1 (1 + λ/2) / q. The "
        "two are related through the period: Sq = Si 2π / T. When the coil swings in a closed circuit it induces a "
        "current that brakes it; the external resistance at which the motion just ceases to oscillate is the "
        "critical damping resistance.",
        ["Level the galvanometer and bring the spot of light to zero on the scale one metre away.",
         "Steady deflection: a 2 V cell across 9999 Ω and 1 Ω in series; the potential difference across the 1 Ω "
         "drives the galvanometer through the series box. Read the deflection for two box values.",
         "Charge the 0.1 µF standard capacitor to a known voltage, discharge it through the galvanometer and read "
         "the first throw and the next throw on the other side.",
         "Find λ = ln(d1 / d2) and the charge sensitivity d1 (1 + λ/2) / (C V).",
         "Close the galvanometer through less and less resistance until the spot returns to zero without crossing it."],
        [_q("A galvanometer is ballistic when", ["Its period is long compared with the time the charge takes to pass",
                                                  "Its coil is very light", "Its scale is far away"], 0,
            "The whole charge must pass before the coil has moved appreciably."),
         _q("At the critical damping resistance the spot", ["Returns to zero in the least time without crossing it",
                                                             "Oscillates for longest", "Does not move"], 0,
            "Less resistance over-damps the coil; more lets it oscillate.")],
        [DU, IP, WF, ILLUS, SIM], {"reading": "Sq", "textbook": "w7_bg_sq"}, CH_EM, safety=_BG_SAFETY,
        name="Ballistic galvanometer with lamp and scale", info="A suspended-coil galvanometer; a mirror on the coil "
        "throws a spot of light on a scale one metre away.")


def bg_leakage() -> dict:
    return _mk(
        "high-resistance-leakage", BG_RIG, "High resistance by the leakage of a capacitor",
        "Charge a capacitor, let it leak through a very high resistance for a measured time, and find the "
        "resistance from the fall in the ballistic throw.",
        "w7_bg", {"mode": 1.0, "tl": 20.0},
        [knob("tl", "Leakage time", "tl", 0, 60, 1, 20, "s"),
         knob("Rx", "High resistance (hidden)", "Rx", 5, 500, 1, 50, "MΩ", 1e6, hidden=True)],
        _BG_INST,
        "A capacitor C charged to a potential V holds the charge q0 = C V. If its plates are joined by a high "
        "resistance R the charge leaks away as q = q0 exp(-t / RC). The charge left after a time t is measured by "
        "discharging the capacitor through a ballistic galvanometer, whose first throw is proportional to the "
        "charge. So d0 / dt = exp(t / RC), and R = t / (C ln(d0 / dt)). A graph of ln(d0 / dt) against t is a "
        "straight line of slope 1 / RC. The damping correction is the same for every throw and cancels.",
        ["Charge the 0.5 µF capacitor from the 1 V source and discharge it at once through the galvanometer: this "
         "throw is d0.",
         "Charge it again, connect the high resistance across it and start the stop-watch.",
         "After a measured time disconnect the resistance and discharge the capacitor through the galvanometer.",
         "Repeat for several leakage times and plot ln(d0 / dt) against t.",
         "R = t / (C ln(d0 / dt)), or 1 / (C x slope)."],
        [_q("Why is a ballistic galvanometer used here?", ["Its throw measures the charge left on the capacitor",
                                                            "It measures resistance directly", "It is cheap"], 0,
            "The throw is proportional to the charge passed through it."),
         _q("A larger high resistance makes the throw fall", ["More slowly", "Faster", "Not at all"], 0,
            "The time constant RC is longer.")],
        [DU, WF, ILLUS, SIM], {"params": {"tl": 20.0}, "reading": "Rest", "textbook": "w7_bg_rx"}, CH_EM,
        safety=_BG_SAFETY, name="Ballistic galvanometer with lamp and scale", info="Measures the charge left on "
        "the capacitor.")


def bg_rayleigh() -> dict:
    return _mk(
        "rayleigh-self-inductance", BG_RIG, "Self-inductance of a coil by Rayleigh's method",
        "Balance a Wheatstone bridge with the coil in one arm for steady current, read the ballistic throw when "
        "the battery circuit is broken, and compare it with the steady deflection a small added resistance gives.",
        "w7_bg", {"mode": 2.0},
        [knob("rs", "Small resistance put in the coil arm", "rs", 0.01, 0.07, 0.01, 0.05, "Ω"),
         knob("Lx", "Self-inductance of the coil (hidden)", "Lx", 5, 200, 0.1, 50, "mH", 0.001, hidden=True)],
        _BG_INST,
        "With the bridge balanced for steady current, breaking the battery circuit lets the flux L i of the coil "
        "collapse. The induced emf sends a charge through the galvanometer proportional to L i, which gives a "
        "throw θ. A small resistance r put in series with the coil upsets the steady balance by an emf i r in the "
        "same arm, which gives a steady deflection φ. Both act through the same network, so the network factor "
        "cancels and L = (r T / 2π) (θ / φ) (1 + λ/2), where T is the period of the galvanometer on open circuit "
        "and λ the logarithmic decrement.",
        ["Connect the coil in the third arm of the bridge and balance for steady current with the battery key "
         "closed first, then the galvanometer key.",
         "With the galvanometer key closed, break the battery key and read the first throw and the next one.",
         "Put the small resistance r in series with the coil and read the steady deflection.",
         "Time the oscillations of the galvanometer on open circuit to find T.",
         "L = (r T / 2π) (θ / φ) (1 + λ/2)."],
        [_q("Why is the bridge balanced for steady current first?", ["So that only the changing current gives a throw",
                                                                      "To protect the battery", "To heat the coil"], 0,
            "With a steady balance, the galvanometer responds only to the induced emf."),
         _q("The small resistance r is used to", ["Calibrate the galvanometer in the same network",
                                                   "Increase the inductance", "Stop the throw"], 0,
            "Its steady deflection measures the same network factor that the throw contains.")],
        [DU, WF, IP, ILLUS, SIM], {"reading": "Lest", "textbook": "w7_bg_lx"}, CH_EM, safety=_BG_SAFETY,
        name="Ballistic galvanometer with lamp and scale", info="The detector of the bridge.")


def bg_mutual() -> dict:
    return _mk(
        "mutual-inductance-absolute", BG_RIG, "Mutual inductance of two coils by the absolute method",
        "Reverse a measured current in the primary coil, read the ballistic throw in the secondary circuit, and "
        "calibrate the galvanometer with a steady current from a standard low resistance in the same circuit.",
        "w7_bg", {"mode": 3.0},
        [knob("Ip", "Primary current", "Ip", 0.1, 0.9, 0.05, 0.5, "A"),
         knob("Mx", "Mutual inductance (hidden)", "Mx", 0.5, 8, 0.01, 4, "mH", 0.001, hidden=True)],
        _BG_INST,
        "When the current I in the primary is reversed the flux through the secondary changes by 2 M I, and a "
        "charge q = 2 M I / R flows round the secondary circuit of resistance R. It gives the throw θ. The "
        "galvanometer is calibrated without knowing R: the same current I is passed through a standard low "
        "resistance r joined in the secondary circuit, so a steady current I r / R flows and gives the deflection "
        "φ. Dividing, M = (T / 2π) (r / 2) (θ / φ) (1 + λ/2), with T the period of the galvanometer on open "
        "circuit and λ its logarithmic decrement in this circuit.",
        ["Connect the primary through the reversing key, an ammeter and a rheostat to the accumulator.",
         "Connect the secondary in series with the galvanometer, a resistance box and the standard low resistance.",
         "Reverse the primary current and read the first throw and the next one on the other side.",
         "Send the primary current through the standard low resistance and read the steady deflection.",
         "M = (T / 2π) (r / 2) (θ / φ) (1 + λ/2)."],
        [_q("Reversing the current instead of breaking it", ["Doubles the change of flux", "Halves the throw",
                                                              "Has no effect"], 0, "The flux goes from +MI to -MI."),
         _q("The method is called absolute because", ["M comes out in terms of a resistance and a time",
                                                       "No galvanometer is needed", "It needs a standard inductance"], 0,
            "Only r, T and a ratio of deflections are needed.")],
        [DU, WF, IP, ILLUS, SIM], {"reading": "Mest", "textbook": "w7_bg_mx"}, CH_EM, safety=_BG_SAFETY,
        name="Ballistic galvanometer with lamp and scale", info="In the secondary circuit.")


def bg_earth() -> dict:
    return _mk(
        "earth-inductor", BG_RIG, "Angle of dip and Earth's field with an earth inductor",
        "Turn the coil of an earth inductor through 180 degrees, first about a vertical axis and then about a "
        "horizontal one, and find the angle of dip and both components of the Earth's field from the two throws.",
        "w7_bg", {"mode": 4.0},
        [knob("axis", "Coil plane (0 vertical, 1 horizontal)", "axis", 0, 1, 1, 0, ""),
         knob("BH", "Horizontal field (hidden)", "BH", 10, 60, 0.1, 35, "µT", 1e-6, hidden=True),
         knob("BV", "Vertical field (hidden)", "BV", 5, 70, 0.1, 32, "µT", 1e-6, hidden=True)],
        _BG_INST,
        "A coil of N turns and area A whose plane is vertical and at right angles to the magnetic meridian links "
        "the flux N A B_H of the horizontal field. Turning it quickly through 180 degrees about a vertical axis "
        "changes the flux by 2 N A B_H and sends the charge 2 N A B_H / R through the ballistic galvanometer. "
        "With the plane horizontal and the turn made about a horizontal axis, the vertical field B_V is cut in "
        "the same way. The throws are in the ratio of the fields, so tan δ = θ_V / θ_H, and each field follows "
        "from its throw and the charge constant of the galvanometer.",
        ["Set the frame so that the coil's plane is vertical and at right angles to the magnetic meridian.",
         "Release the spring so the coil turns through 180 degrees and read the first throw and the next one.",
         "Turn the frame so that the coil's plane is horizontal and repeat.",
         "tan δ = θ_V / θ_H.",
         "B = k_q θ (1 + λ/2) R / (2 N A) for each component, with k_q the charge constant on the calibration card."],
        [_q("The dip angle is found from", ["The ratio of the two throws", "The sum of the two throws",
                                             "The period of the galvanometer"], 0, "tan δ = B_V / B_H."),
         _q("Why must the coil be turned quickly?", ["The whole charge must pass before the galvanometer coil moves",
                                                      "To heat the coil", "To reduce friction"], 0,
            "That is the condition for a ballistic throw.")],
        [IP, DU, MEM_FIELD, ILLUS, SIM], {"reading": "dip", "textbook": "w7_bg_dip"}, CH_EM, safety=_BG_SAFETY,
        name="Ballistic galvanometer with lamp and scale", info="Measures the charge the earth inductor sends.")


def bg_solenoid() -> dict:
    return _mk(
        "solenoid-field", BG_RIG, "Field along the axis of a solenoid with a search coil",
        "Move a small search coil along the axis of a solenoid, reverse the solenoid current at each place and "
        "find the field from the ballistic throw; plot the field and its gradient dB/dx.",
        "w7_bg", {"mode": 5.0},
        [knob("x", "Search coil position from the centre", "x", -25, 25, 0.5, 0, "cm", 0.01),
         knob("ns", "Turns per metre of the solenoid (hidden)", "ns", 500, 5000, 1, 2000, "1/m", hidden=True)],
        _BG_INST,
        "On the axis of a solenoid of n turns per metre, length L and radius a carrying a current I, the field at "
        "a distance x from the centre is B = (μ0 n I / 2)(cos α1 - cos α2), α1 and α2 being the angles the two "
        "ends subtend. It is nearly uniform in the middle and falls to about half at each end, where dB/dx is "
        "greatest. A search coil of N turns and area A at that place links the flux N A B; reversing the solenoid "
        "current changes it by 2 N A B and sends the charge 2 N A B / R through the ballistic galvanometer. With "
        "a Hall-probe gaussmeter the field is read directly instead.",
        ["Slide the search coil to the centre of the solenoid and close the secondary circuit through the "
         "galvanometer.",
         "Reverse the solenoid current and read the first throw and the next one.",
         "B = k_q θ (1 + λ/2) R / (2 N A), with k_q the charge constant on the calibration card.",
         "Repeat every few centimetres to beyond both ends and plot B against x.",
         "Find dB/dx from the slope of the curve: it is greatest at the ends."],
        [_q("At the end of a long solenoid the axial field is about", ["Half the field at the centre",
                                                                       "Equal to the field at the centre", "Zero"], 0,
            "Only half of the turns lie to one side of the end."),
         _q("Where is dB/dx greatest?", ["Near the ends", "At the centre", "Far outside"], 0,
            "The field changes fastest where the winding stops.")],
        [DU, IP, ILLUS, SIM], {"reading": "Best", "textbook": "w7_bg_bsol"}, CH_EM, safety=_BG_SAFETY,
        name="Solenoid with a search coil", info="A long winding on a tube; the search coil slides inside.")


# ============================================================================================ DC bridges
def carey_foster() -> dict:
    return _mk(
        "carey-foster-bridge", IN_RIG, "Low resistance with a Carey Foster bridge",
        "Find the resistance per unit length of the bridge wire with a known fractional resistance, and then an "
        "unknown low resistance, from the shift of the null point when the two outer gaps are interchanged.",
        "w7_carey", {},
        [knob("std", "Fractional standard resistance", "std", 0.1, 1.0, 0.1, 0.5, "Ω"),
         knob("Xu", "Unknown low resistance (hidden)", "Xu", 0.05, 1.0, 0.01, 0.37, "Ω", hidden=True),
         knob("rho", "Resistance per metre of the wire (hidden)", "rho", 0.8, 3.0, 0.01, 1.4, "Ω/m", hidden=True)],
        [inst("g", "readout", "Galvanometer current", "I_G", k=1e6, unit="µA", digits=2)],
        "Carey Foster's bridge is a metre bridge with four gaps. Equal resistances P and Q fill the inner gaps; "
        "X and Y fill the outer gaps, in series with the two parts of the wire. If the null point is at l1, and "
        "at l2 when X and Y are interchanged, then X - Y = ρ (l2 - l1), where ρ is the resistance of unit length "
        "of the wire. The end resistances and the ratio P / Q cancel out, which is why the bridge measures a small "
        "difference of resistance well. With a known X and a thick copper strip as Y the same relation gives ρ.",
        ["Put equal resistances in the two inner gaps, the fractional resistance box in the left outer gap and the "
         "copper strip in the right one.",
         "Find the null point l1, interchange the box and the strip, and find l2.",
         "ρ = r / (l2 - l1) for the known resistance r. Repeat for another r.",
         "Replace the box by the unknown resistance and find l1 and l2 again.",
         "X = ρ (l2 - l1)."],
        [_q("Interchanging the gaps removes the effect of", ["The end resistances of the wire", "The battery",
                                                              "The galvanometer"], 0,
            "They appear in both positions and cancel in the difference."),
         _q("The bridge is most suited to measuring", ["A small difference between two nearly equal resistances",
                                                        "Very high resistances", "Capacitance"], 0,
            "The whole wire spans only about an ohm.")],
        [DU, IP, WF, ILLUS, SIM], {"reading": "diff", "textbook": "w7_carey_diff"}, CH_EM,
        name="Carey Foster bridge", info="A metre wire on a board with four gaps.")


def pot_low() -> dict:
    return _mk(
        "potentiometer-low-resistance", IN_RIG, "Low resistance with a potentiometer",
        "Send one current through an unknown low resistance and a standard low resistance in series, balance the "
        "potential difference across each on a potentiometer, and find the unknown from the ratio of the lengths.",
        "w7_potlow", {},
        [knob("R2", "Rheostat in the test circuit", "R2", 4, 12, 0.5, 6, "Ω"),
         knob("Rx", "Unknown low resistance (hidden)", "Rx", 0.05, 0.6, 0.01, 0.27, "Ω", hidden=True)],
        [inst("g", "readout", "Galvanometer current", "I_G", k=1e6, unit="µA", digits=2)],
        "A potentiometer compares potential differences without drawing current at balance. The driver cell and a "
        "series resistance keep a small, steady fall of potential along the ten-metre wire. A second circuit "
        "sends the same current I through the unknown R and a standard low resistance S in series. The potential "
        "difference I R balances a length l1 of the wire and I S balances l2, so R / S = l1 / l2. Lead and contact "
        "resistances do not matter because no current flows in the potential leads at balance, which is why this "
        "is a good method for a low resistance.",
        ["Connect the driver cell, its key and a resistance box in series with the potentiometer wire.",
         "Connect the second cell through a rheostat to R and S in series.",
         "Join the potential leads across R and find the balancing length l1.",
         "Move the potential leads to S, without changing the current, and find l2.",
         "R = S l1 / l2. Repeat for other currents."],
        [_q("Why do lead resistances not matter?", ["No current flows in the potential leads at balance",
                                                     "The leads are very thick", "The current is large"], 0,
            "At the null point the galvanometer branch carries no current."),
         _q("R and S must carry", ["The same current", "Different currents", "No current"], 0,
            "Only then is the ratio of the potential differences the ratio of the resistances.")],
        [DU, SAW, IP, ILLUS, SIM], {"reading": "Rest", "textbook": "w7_potlow_rx"}, CH_EM,
        name="Ten-wire potentiometer", info="Ten metres of wire on a board with a jockey.")


# ============================================================================================ AC bridges
def anderson() -> dict:
    return _mk(
        "anderson-bridge", IN_RIG, "Self-inductance with Anderson's bridge",
        "Balance Anderson's bridge first for steady current and then for alternating current, and find the "
        "self-inductance of a coil in terms of a standard capacitor and the resistances.",
        "w7_anderson", {},
        [knob("C", "Standard capacitor", "C", 0.02, 0.1, 0.01, 0.1, "µF", 1e-6),
         knob("Lx", "Self-inductance of the coil (hidden)", "Lx", 110, 400, 1, 150, "mH", 0.001, hidden=True)],
        [inst("g", "readout", "Detector current", "I_G", k=1e6, unit="µA", digits=2)],
        "Anderson's bridge is Maxwell's inductance-capacitance bridge with one extra resistance r, which lets the "
        "two balance conditions be met one after the other with a fixed capacitor. The coil L with its resistance "
        "and a series resistance r1 forms one arm, R2, R3 and R4 the others; r joins the R2-R4 junction to the "
        "capacitor C, and the detector is between the coil-R3 junction and the capacitor. The steady balance needs "
        "r1 + r_coil = R2 R3 / R4 and is found with r1. The alternating balance is then found with r alone, and "
        "L = C (R3 / R4) [ r (R4 + R2) + R2 R4 ].",
        ["Connect the coil, the three 1000 Ω arms, the capacitor and the resistance r as in the diagram.",
         "With the battery and galvanometer, balance for steady current by adjusting r1.",
         "Replace them by the oscillator and headphones and adjust r for the least sound.",
         "Touch up r1 and r in turn until neither moves.",
         "L = C (R3 / R4) [ r (R4 + R2) + R2 R4 ]. Repeat with another capacitor."],
        [_q("What does the extra resistance r do?", ["Lets the AC balance be made without disturbing the DC balance",
                                                      "Reduces the inductance", "Protects the capacitor"], 0,
            "r does not appear in the steady balance condition."),
         _q("A larger capacitor needs", ["A smaller r", "A larger r", "The same r"], 0,
            "L is fixed, and L is proportional to C times a term that grows with r.")],
        [DU, WF, SAW, ILLUS, SIM], {"reading": "Lest", "textbook": "w7_anderson_l"}, CH_AC,
        safety="The oscillator gives only a few volts. Keep the headphones' volume low before the bridge is "
               "roughly balanced.",
        name="Anderson's bridge board", info="Four arms, a standard capacitor and the resistance r.")


def universal() -> dict:
    return _mk(
        "lcr-universal-bridge", IN_RIG, "Inductance of a coil with a universal LCR bridge",
        "Set a universal bridge to its L function, balance it with the main dial and the loss dial on three "
        "ranges, and read the inductance of an unmarked coil.",
        "w7_unibridge", {"fn": 1.0},
        [knob("Rr", "Range resistor", "Rr", 100, 10000, 100, 1000, "Ω"),
         knob("Lx", "Inductance of the coil (hidden)", "Lx", 5, 800, 0.1, 82, "mH", 0.001, hidden=True)],
        [inst("g", "readout", "Detector current", "I_G", k=1e6, unit="µA", digits=2)],
        "A universal bridge is one four-arm frame whose function switch puts the right standards in the arms. For "
        "R it is a Wheatstone bridge: Rx = Rr Dm / Ra. For L it is the Maxwell-Wien bridge: the coil is balanced "
        "against a standard capacitor Cs in parallel with the loss dial, and Lx = Rr Dm Cs with the coil's "
        "resistance Rr Dm / Dl. For C it compares the unknown with Cs in series with the loss dial: "
        "Cx = Cs Dm / Rr. On L and C there are two things to balance, the reactance and the loss, so the main "
        "dial Dm and the loss dial Dl are turned in turn until the detector is quietest.",
        ["Connect the unknown to the UNKNOWN terminals and set the function switch.",
         "Choose a range so that the main dial balances near the middle of its travel.",
         "Turn the main dial for the least detector reading, then the loss dial, and repeat until neither moves.",
         "Read the value from the dial and the range multiplier.",
         "Repeat on the neighbouring ranges and take the mean."],
        [_q("Why are two dials needed on the L and C functions?", ["The reactance and the loss must both be balanced",
                                                                   "One dial is a spare", "To set the frequency"], 0,
            "An alternating bridge balances in magnitude and in phase."),
         _q("On the L function the coil is balanced against", ["A standard capacitor", "A standard inductor",
                                                                "A battery"], 0,
            "The Maxwell-Wien bridge measures inductance in terms of capacitance.")],
        [DU, SAW, ILLUS, SIM], {"reading": "val", "textbook": "w7_uni_val"}, CH_AC,
        safety="The internal oscillator gives a few volts. Discharge a capacitor before connecting it.",
        name="Universal LCR bridge", info="A function switch, a range switch, a main dial and a loss dial.")


def q_meter() -> dict:
    return _mk(
        "q-meter", IN_RIG, "Q of a coil and its frequency dependence with a Q-meter",
        "Resonate a coil with the tuning capacitor of a Q-meter at several frequencies, read Q at each, and find "
        "the coil's inductance and self-capacitance from two resonances an octave apart.",
        "w7_qmeter", {},
        [knob("f", "Oscillator frequency", "f", 0.4, 1.7, 0.01, 1.0, "MHz", 1e6),
         knob("L", "Inductance of the coil (hidden)", "L", 100, 600, 1, 250, "µH", 1e-6, hidden=True)],
        [inst("q", "readout", "Q reading", "Q", digits=0)],
        "A Q-meter injects a small known voltage e in series with the coil and a calibrated tuning capacitor C. At "
        "resonance the voltage across C is Q times e, so a voltmeter across C is marked directly in Q. The coil "
        "also has a self-capacitance Cd, so resonance is at ω² L (C + Cd) = 1. Tuning at f needs C1 and at 2f "
        "needs C2, which gives Cd = (C1 - 4 C2) / 3 and L = 1 / (ω² (C1 + Cd)). The indicated Q is lower than the "
        "coil's own ωL / R by the factor (1 + Cd / C), so Q rises with frequency at first and then falls as C "
        "becomes small.",
        ["Connect the coil to the COIL terminals and set the oscillator frequency.",
         "Set the injected voltage to the mark and turn the tuning capacitor for the largest Q reading.",
         "Record the frequency, the capacitance and Q.",
         "Repeat over the range, taking pairs of frequencies an octave apart.",
         "Cd = (C1 - 4 C2) / 3, L = 1 / (ω² (C1 + Cd)); plot Q against frequency."],
        [_q("At resonance the voltage across the tuning capacitor is", ["Q times the injected voltage",
                                                                        "Equal to the injected voltage", "Zero"], 0,
            "That is the voltage magnification of a series resonant circuit."),
         _q("The coil's self-capacitance makes the indicated Q", ["Lower than the true Q", "Higher than the true Q",
                                                                  "Infinite"], 0,
            "Part of the circulating current goes through Cd instead of the tuning capacitor.")],
        [DU, SAW, ILLUS, SIM], {"reading": "Lest", "textbook": "w7_q_l"}, CH_AC,
        name="Q-meter", info="An oscillator, an injection circuit, a tuning capacitor and a Q voltmeter.")


def rc_rl() -> dict:
    return _mk(
        "rc-rl-time-constant", IN_RIG, "Time constant of an RC circuit",
        "Apply a square wave to a resistance and a capacitor in series, watch the capacitor voltage on an "
        "oscilloscope and measure the time it takes to reach 63.2 % of its final value for several resistances.",
        "w7_tau", {"mode": 0.0},
        [knob("R", "Resistance box", "R", 2000, 20000, 1000, 10000, "Ω"),
         knob("C", "Capacitor (hidden)", "C", 0.01, 1.0, 0.001, 0.1, "µF", 1e-6, hidden=True)],
        [inst("v", "readout", "Trace voltage", "v", unit="V", digits=2)],
        "When a steady voltage is switched on to R and C in series the capacitor charges as "
        "v = V0 (1 - exp(-t / τ)) with the time constant τ = R C, where R includes the generator's own output "
        "resistance. After one time constant the voltage has reached 63.2 % of its final value. For a resistance "
        "and a coil the current grows in the same way with τ = L / R, where R includes the coil's resistance. A "
        "square wave whose half period is many time constants repeats the switch-on, so the oscilloscope shows a "
        "steady trace on which the time to 63.2 % is read with the cursors.",
        ["Connect the function generator to R and C in series and the oscilloscope across C.",
         "Set a square wave slow enough for the trace to flatten before each edge.",
         "Measure the time from the edge to 63.2 % of the final height.",
         "Repeat for several resistances and plot τ against R.",
         "The slope of the line is C; its intercept shows the generator's output resistance."],
        [_q("After one time constant a charging capacitor has reached", ["63.2 % of its final voltage", "50 %",
                                                                         "100 %"], 0, "1 - 1/e = 0.632."),
         _q("Doubling R makes the time constant of an RC circuit", ["Double", "Half", "Unchanged"], 0, "τ = R C.")],
        [DU, SAW, ILLUS, SIM], {"reading": "tau", "textbook": "w7_tau"}, CH_AC,
        name="RC board with function generator and oscilloscope", info="The square wave charges the capacitor "
        "through the resistance.")


# ============================================================================================ machines
def transformer() -> dict:
    return _mk(
        "transformer-step-up-down", IN_RIG, "Step-down transformer: turns ratio and efficiency",
        "Find the turns ratio of a small transformer from its open-circuit voltages, then load it and find its "
        "efficiency from the input power and the output power.",
        "w7_xfmr", {"nr": 0.5, "RL": 20.0},
        [knob("RL", "Load resistance", "RL", 5, 200, 1, 20, "Ω"),
         knob("nr", "Turns ratio Ns / Np (hidden)", "nr", 0.1, 4, 0.01, 0.5, "", hidden=True)],
        [inst("v2", "readout", "Secondary voltage", "V2", unit="V", digits=2),
         inst("eta", "readout", "Efficiency", "eta", k=100, unit="%", digits=1)],
        "In an ideal transformer the voltages are in the ratio of the turns, Vs / Vp = Ns / Np, and the power in "
        "equals the power out. A real one has copper loss I² R in both windings and iron loss in the core. On "
        "open circuit the secondary voltage divided by the primary voltage gives the turns ratio very nearly, and "
        "the small input power is the iron loss. On load the efficiency is the output power Vs Is divided by the "
        "input power read by the wattmeter. It is low at light load, where the iron loss dominates, passes "
        "through a maximum, and falls again when the copper loss grows.",
        ["Connect the primary to the 12 V laboratory AC supply through an ammeter and a wattmeter.",
         "With the secondary open, read both voltages: their ratio is the turns ratio.",
         "Connect the load rheostat with an ammeter and a voltmeter on the secondary.",
         "For several loads read the primary power and the secondary voltage and current.",
         "Efficiency = Vs Is / P_in; plot it against the load current."],
        [_q("The turns ratio is found with the secondary", ["Open", "Short-circuited", "Fully loaded"], 0,
            "With no secondary current there is almost no voltage drop in the windings."),
         _q("The input power on open circuit is mostly", ["Iron loss in the core", "Copper loss", "Output power"], 0,
            "Only the small magnetising current flows.")],
        [DU, THER, ILLUS, SIM], {"reading": "ratio", "textbook": "w7_xfmr_ratio"}, CH_NET,
        safety="The transformer is fed from a 12 V laboratory AC supply, never from the mains. A step-up winding "
               "can still give tens of volts: switch off before touching the terminals.",
        name="Demonstration transformer", info="Two windings on a laminated iron core.")


def motor() -> dict:
    return _mk(
        "dc-motor-speed", IN_RIG, "Speed of a DC motor against its supply voltage",
        "Run a small permanent-magnet DC motor at several supply voltages, read its speed with a tachometer and "
        "its armature current, and find its back-emf constant.",
        "w7_motor", {},
        [knob("V", "Supply voltage", "V", 1, 12, 0.5, 6, "V"),
         knob("k", "Back-emf constant (hidden)", "k", 0.005, 0.04, 0.0001, 0.012, "V s/rad", hidden=True)],
        [inst("rpm", "readout", "Tachometer", "rpm", unit="rev/min", digits=0),
         inst("i", "readout", "Armature current", "I", unit="A", digits=3)],
        "A turning armature generates a back emf proportional to its speed, E = k ω. The supply voltage is shared "
        "between this and the drop in the armature resistance: V = I Ra + k ω. Running light, the current is "
        "small and nearly constant, just enough to overcome friction, so the speed rises almost in a straight "
        "line with the voltage. From each reading k = (V - I Ra) / ω, the armature resistance Ra being measured "
        "with the rotor held still. The same constant gives the torque per ampere.",
        ["Measure the armature resistance with the rotor held: it is printed on the board for this motor.",
         "Connect the motor to the variable DC supply through the ammeter.",
         "Set a voltage, let the speed settle, and read the tachometer and the current.",
         "Repeat from 1 V to 12 V and plot the speed against the voltage.",
         "k = (V - I Ra) / ω with ω = 2π N / 60."],
        [_q("The back emf of a motor is proportional to its", ["Speed", "Current", "Resistance"], 0, "E = k ω."),
         _q("Running light, a higher supply voltage mainly", ["Raises the speed", "Raises the current", "Does nothing"], 0,
            "The back emf must rise to nearly equal the supply.")],
        [DU, THER, ILLUS, SIM], {"reading": "w", "textbook": "w7_motor_w"}, CH_NET,
        safety="Keep fingers, hair and leads clear of the spinning disc. Do not hold the shaft with the supply on.",
        name="DC motor with tachometer disc", info="A small permanent-magnet motor on a bracket.")


def generator() -> dict:
    return _mk(
        "ac-dc-generator", IN_RIG, "AC generator with slip rings: emf against speed",
        "Turn the coil of a demonstration generator at several speeds, watch the emf on an oscilloscope, and find "
        "the flux linkage N B A from the way the peak emf grows with the speed.",
        "w7_gen", {"mode": 0.0},
        [knob("f", "Speed of the coil", "f", 2, 25, 1, 10, "rev/s"),
         knob("B", "Field of the magnet (hidden)", "B", 0.01, 0.2, 0.001, 0.05, "T", hidden=True)],
        [inst("e", "readout", "Emf at the brushes", "emf", unit="V", digits=3)],
        "A coil of N turns and area A turning at an angular speed ω in a field B links the flux N B A cos ωt, so "
        "by Faraday's law the emf is N B A ω sin ωt. With slip rings each end of the coil stays on its own brush "
        "and the output alternates: an AC generator. With a split-ring commutator the connections are swapped "
        "every half turn, just as the emf changes sign, so the output is always one way, a pulsating direct "
        "voltage: a DC generator. In both the peak emf is N B A ω, proportional to the speed.",
        ["Connect the brushes to the oscilloscope.",
         "Turn the coil at a steady speed with the drive motor and read the speed on the counter.",
         "Read the peak emf from the trace and note the shape of the wave.",
         "Repeat for several speeds and plot the peak emf against ω.",
         "The slope of the line is N B A."],
        [_q("Doubling the speed of the coil makes the peak emf", ["Double", "Half", "Unchanged"], 0, "ε = N B A ω."),
         _q("A split-ring commutator makes the output", ["Always of one sign", "Larger", "Zero"], 0,
            "It reverses the connections every half turn.")],
        [DU, THER, ILLUS, SIM], {"reading": "peak", "textbook": "w7_gen_peak"}, CH_NET,
        safety="Keep fingers clear of the turning coil and the drive belt.",
        name="Demonstration generator", info="A coil between the poles of a magnet, with slip rings and brushes.")


def falling_magnet() -> dict:
    return _mk(
        "faraday-lenz-falling-magnet", IN_RIG, "Faraday's and Lenz's laws: a magnet falling through a coil",
        "Drop a small magnet through a coil from several heights, record the induced emf against time with an "
        "Arduino, and find the dipole moment of the magnet from the peak emf.",
        "w7_fallmag", {},
        [knob("h", "Drop height above the coil", "h", 0.15, 0.6, 0.05, 0.4, "m"),
         knob("m", "Dipole moment of the magnet (hidden)", "m", 0.2, 1.5, 0.01, 0.75, "A m²", hidden=True)],
        [inst("e", "readout", "Induced emf", "emf", unit="V", digits=3)],
        "As the magnet approaches the coil the flux through it grows, and as it leaves the flux falls, so the "
        "induced emf is a pulse of one sign followed by a pulse of the other: Lenz's law. The two pulses have "
        "equal and opposite areas, because the flux returns to zero, but the second is taller and narrower since "
        "the magnet is moving faster. For a short magnet of moment m on the axis of a coil of N turns and radius "
        "a, the emf is greatest when the magnet is a/2 from the plane of the coil, and the peak is "
        "0.4293 μ0 N m v / a², proportional to the speed v = √(2 g h): Faraday's law.",
        ["Fix the coil round the guide tube and connect it to the Arduino's analogue input through the bias board.",
         "Hold the magnet at a measured height above the centre of the coil and release it.",
         "Read the two peaks from the plotted trace.",
         "Repeat from several heights and plot the mean peak against √h.",
         "m = ε_peak a² / (0.4293 μ0 N v) with v = √(2 g h)."],
        [_q("Why are the two pulses of opposite sign?", ["The flux first rises and then falls", "The magnet turns over",
                                                         "The coil is reversed"], 0,
            "The emf follows the rate of change of flux, which changes sign."),
         _q("Dropping the magnet from a greater height makes the peaks", ["Taller and narrower", "Shorter and wider",
                                                                          "Unchanged"], 0,
            "The flux changes faster, but the total change is the same.")],
        [DU, MEM_MAG, ILLUS, SIM], {"reading": "pk", "textbook": "w7_fall_pk"}, CH_EM,
        safety="Neodymium magnets are brittle and pinch fingers: catch the magnet on the foam pad and keep it away "
               "from cards and watches.",
        name="Guide tube with a pick-up coil", info="The magnet falls down the tube through the coil.")


def galv_conversion() -> dict:
    return _mk(
        "galvanometer-conversion", IN_RIG, "Making a voltmeter from a galvanometer",
        "Find the resistance and the figure of merit of a galvanometer by half deflection, work out the series "
        "resistance that makes it a 0 - 3 V voltmeter, and calibrate it against a standard voltmeter.",
        "w7_gconv", {"mode": 0.0},
        [knob("R", "High resistance box", "R", 3500, 8000, 100, 4000, "Ω"),
         knob("G", "Galvanometer resistance (hidden)", "G", 40, 200, 0.1, 96, "Ω", hidden=True),
         knob("kf", "Figure of merit (hidden)", "kf", 10, 40, 0.1, 20, "µA/div", 1e-6, hidden=True)],
        [inst("th", "readout", "Galvanometer deflection", "theta", unit="div", lc=0.1, digits=1)],
        "A galvanometer of resistance G that needs the current Ig for full-scale deflection becomes a voltmeter of "
        "range V when a resistance Rs = V / Ig - G is put in series with it, and an ammeter of range I when a "
        "shunt S = Ig G / (I - Ig) is put across it. G is found by half deflection: with a high resistance R in "
        "series, a shunt S' across the galvanometer that halves the deflection satisfies G = R S' / (R - S'). The "
        "figure of merit k, the current per division, follows from the full deflection θ: k = E / ((R + G) θ), and "
        "Ig = n k for a scale of n divisions.",
        ["Connect the cell, the high resistance box and the galvanometer in series and note the deflection.",
         "Put the shunt box across the galvanometer and adjust it until the deflection is halved.",
         "G = R S' / (R - S') and k = E / ((R + G) θ). Repeat for another R.",
         "Work out the series resistance (or the shunt) for the chosen range and connect it.",
         "Compare the converted meter with a standard meter at several points."],
        [_q("To make a voltmeter, the extra resistance goes", ["In series with the galvanometer", "In parallel with it",
                                                               "Across the cell"], 0,
            "It limits the current to the full-scale value at the chosen voltage."),
         _q("A shunt for an ammeter is", ["A low resistance in parallel", "A high resistance in series",
                                          "A capacitor"], 0, "Most of the current bypasses the coil.")],
        [DU, IP, ILLUS, SIM], {"reading": "need", "textbook": "w7_gconv_need"}, CH_EM,
        name="Galvanometer with resistance boxes", info="A 30-0-30 moving-coil galvanometer.")


def source_reg() -> dict:
    return _mk(
        "constant-current-voltage-source", IN_RIG, "Performance of a constant-voltage source",
        "Load a regulated constant-voltage source with a decade box, read its terminal voltage and current, and "
        "find its output resistance, its load regulation and where its current limit begins.",
        "w7_srcreg", {"mode": 0.0},
        [knob("RL", "Load resistance", "RL", 3, 90, 1, 30, "Ω"),
         knob("ro", "Output resistance (hidden)", "ro", 0.05, 1.0, 0.01, 0.25, "Ω", hidden=True)],
        [inst("v", "readout", "Terminal voltage", "V", unit="V", digits=3),
         inst("i", "readout", "Load current", "I", unit="A", digits=3)],
        "An ideal constant-voltage source keeps the same terminal voltage whatever current is drawn, which means "
        "zero output resistance. A real one behaves as its set voltage V0 behind a small output resistance ro: "
        "V = V0 - I ro, so ro is minus the slope of the V against I line, and the load regulation is the fall "
        "from no load to full load as a fraction of V0. An ideal constant-current source keeps the same current "
        "whatever the load, which means infinite output resistance; a real one is I0 in parallel with a large Ro, "
        "I = I0 - V / Ro, up to its compliance voltage. Each stops regulating at its limit.",
        ["Connect the source to the decade load box with an ammeter in series and a voltmeter across the load.",
         "Start with a large load resistance and read the voltage and the current.",
         "Reduce the load resistance in steps, reading both each time, until the output collapses.",
         "Plot V against I and find the slope of the flat part.",
         "ro = -ΔV / ΔI; regulation = (V_no load - V_full load) / V_no load."],
        [_q("An ideal constant-voltage source has an output resistance of", ["Zero", "Infinity", "One ohm"], 0,
            "Its voltage does not change with the current drawn."),
         _q("An ideal constant-current source has an output resistance of", ["Infinity", "Zero", "One ohm"], 0,
            "Its current does not change with the voltage across the load.")],
        [DU, SAW, ILLUS, SIM], {"reading": "rout", "textbook": "w7_src_rout"}, CH_EM,
        name="Regulated source with a decade load", info="A bench source, a decade box and two digital meters.")


def magnetometer() -> dict:
    return _mk(
        "earth-field-magnetometer", IN_RIG, "Magnetic moment and Earth's field with magnetometers",
        "Find M / H for a bar magnet with a deflection magnetometer in the Tan A and Tan B positions and M H "
        "with a vibration magnetometer, and from the two find the magnetic moment and Earth's horizontal field.",
        "w7_magneto", {},
        [knob("d", "Distance of the magnet from the needle", "d", 0.1, 0.3, 0.01, 0.2, "m"),
         knob("pos", "Position (0 Tan A, 1 Tan B)", "pos", 0, 1, 1, 0, ""),
         knob("M", "Magnetic moment (hidden)", "M", 0.1, 1.5, 0.01, 0.5, "A m²", hidden=True),
         knob("H", "Earth's horizontal field (hidden)", "H", 20, 60, 0.1, 36, "µT", 1e-6, hidden=True)],
        [inst("th", "readout", "Needle deflection", "theta", unit="°", lc=0.1, digits=1)],
        "In a deflection magnetometer the field B of the magnet is at right angles to the Earth's horizontal "
        "field H, and the needle settles where tan θ = B / H. With the magnet end-on (Tan A), "
        "B = (μ0 / 4π) 2 M d / (d² - l²)², and broadside-on (Tan B), B = (μ0 / 4π) M / (d² + l²)^(3/2), so each "
        "deflection gives M / H. In a vibration magnetometer the same magnet swings in H alone with the period "
        "T = 2π √(I / (M H)), I being its moment of inertia, which gives M H. Multiplying and dividing the two "
        "results gives M and H separately.",
        ["Set the arms of the deflection magnetometer east-west and turn the box until the pointer reads 0 - 0.",
         "Tan A: put the magnet on the arm, end-on, at a measured distance and read the deflection.",
         "Tan B: turn the arms north-south, put the magnet broadside-on and read the deflection.",
         "Hang the magnet in the vibration magnetometer and time ten small swings.",
         "M / H from the deflections, M H = 4π² I / T², then M = √((M/H)(M H)) and H = √((M H)/(M/H))."],
        [_q("The deflection magnetometer gives", ["M / H", "M H", "M alone"], 0, "tan θ = B / H and B is proportional to M."),
         _q("The vibration magnetometer gives", ["M H", "M / H", "H alone"], 0, "T = 2π √(I / (M H)).")],
        [IP, DU, MEM_FIELD, ILLUS, SIM], {"reading": "Hest", "textbook": "w7_mag_h"}, CH_EM,
        safety="Keep other magnets, iron stands and current-carrying wires well away from the magnetometer.",
        name="Deflection magnetometer", info="A compass box with a long pointer at the centre of a metre scale.")


def bh_curve() -> dict:
    return _mk(
        "bh-curve", IN_RIG, "B-H curve and hysteresis loss of soft iron",
        "Trace the B-H loop of a soft-iron ring on an oscilloscope, drive it to saturation, and read its "
        "coercivity, its retentivity and the hysteresis loss per cycle from the loop.",
        "msc_loop", {"H": 0.0, "Ms": 2.1, "Hc": 80.0, "a": 100.0, "H0": 400.0, "br": 1.0, "kind": 1.0},
        [knob("H0", "Peak magnetising field", "H0", 20, 800, 1, 400, "A/m"),
         knob("Hc", "Coercivity of the ring (hidden)", "Hc", 20, 8000, 1, 80, "A/m", hidden=True)],
        [inst("M", "readout", "Flux density at this field", "M", unit="T", digits=3)],
        "When the magnetising field H in a ferromagnet is taken round a cycle the flux density B lags behind it "
        "and traces a closed loop. The value of B left when H returns to zero is the retentivity, and the reverse "
        "field needed to bring B to zero is the coercivity. The area of the loop is the energy lost as heat in "
        "each unit volume of the material in one cycle: the hysteresis loss. Soft iron has a narrow loop and a "
        "small loss, which suits transformer cores; hard steel has a wide loop, which suits permanent magnets. "
        "The loop shows the material's own coercivity only when it is driven to saturation.",
        ["Connect the primary of the ring through the sensing resistor to the low-voltage 50 Hz supply and the "
         "secondary through the integrator to the Y input.",
         "Calibrate the axes: H = N1 V_x / (R l) and B = R C V_y / (N2 A).",
         "Raise the drive in steps and capture the loop each time.",
         "On the saturated loop read where it cuts the H axis (coercivity) and the B axis (retentivity).",
         "Find the area of the loop: it is the hysteresis loss per cycle per unit volume."],
        [_q("The area of the B-H loop is", ["The energy lost per cycle per unit volume", "The retentivity",
                                             "The permeability"], 0, "The integral of H dB round the cycle is an energy density."),
         _q("A good transformer core needs", ["A narrow loop", "A wide loop", "No loop at all"], 0,
            "A small loop area means little energy is lost each cycle.")],
        [DU, MEM_BH, ILLUS, SIM], {"reading": "Hc", "textbook": "mss_Hc", "tol": 0.01}, CH_EM,
        safety="The ring is fed from a low-voltage laboratory AC supply. The primary winding becomes warm at "
               "large drives: do not leave it at full drive.",
        name="Ring specimen with two windings", info="A ring of the material with a magnetising and a search winding.")


BUILDERS = (bg_constants, bg_leakage, bg_rayleigh, bg_mutual, bg_earth, bg_solenoid, carey_foster, pot_low, anderson,
            universal, q_meter, rc_rl, transformer, motor, generator, falling_magnet, galv_conversion, source_reg,
            magnetometer, bh_curve)
