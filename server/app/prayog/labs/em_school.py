"""Prayogshala lab pack: Class 6-10 electricity, magnetism and static electricity (NCERT Science VI-X and the
Class X laboratory manual). Six studio rigs serve seventeen set-ups:

    school-bulb-circuit   a cell board with a torch bulb      torch-bulb-circuit, cells-in-series, make-a-switch,
                                                              conductors-insulators-tester
    resistors-combination two resistance coils, series/parallel  series-resistors, parallel-resistors
    resistance-factors    a resistance wire of chosen material, length and gauge
    heating-effect-wire   a nichrome coil in a lagged calorimeter
    current-magnetism     a straight wire / coil / solenoid with a plotting compass and a Hall teslameter
                                                              compass-near-wire, field-straight-conductor,
                                                              field-circular-loop, field-solenoid, electromagnet-nail
    bar-magnet-field      a plotting board, bar magnets, compass and a stirrup on a torsionless thread
                                                              field-lines-bar-magnet, like-unlike-poles,
                                                              suspended-magnet-direction, make-a-magnet-stroking
    static-electricity    a polythene rod, a duster, two pith balls and a jar electroscope
                                                              charging-by-rubbing-6-10, jar-electroscope

The physics is the shared `circuit` kernel (a netlist needs no new physics) and the five kernels of
`packs/em_school.py`. Every lab's `check` compares the kernel's simulated reading with the textbook formula to
within 1 %. Learner-facing text is English only.

SAFETY: everything here runs on dry cells or a low-voltage DC supply. No mains wiring is ever shown as something
the learner does by hand.
"""
from __future__ import annotations

from ..catalog import B, board, knob, lab

S6 = {"title": "Science, Textbook for Class VI, NCERT: Electricity and Circuits; Fun with Magnets"}
S7 = {"title": "Science, Textbook for Class VII, NCERT: Electric Current and its Effects"}
S8 = {"title": "Science, Textbook for Class VIII, NCERT: Some Natural Phenomena"}
S10 = {"title": "Science, Textbook for Class X, NCERT: Electricity; Magnetic Effects of Electric Current"}
LM10 = {"title": "Laboratory Manual, Science, Class X, NCERT"}
SIM = {"title": "Hoola Prayogshala kernel", "note": "readings come from the simulation code; each is checked against "
                                                   "the textbook formula in Hoola's tests (1 %)"}
XI = {"title": "NCERT Physics Textbook Class XII: Magnetism and Matter; Moving Charges and Magnetism",
      "note": "the formulas the school activity is checked against"}


# =============================================================================== A. circuits (the shared kernel)
def _cellboard(extra=()) -> list[dict]:
    return [board(1.0, 0.7),
            B("cellA", "cylinder", name="Dry cell (1.5 V)", info="A zinc-carbon cell. Its nominal emf is 1.5 V.",
              r=0.017, h=0.05, pos=[-0.34, 0.02, 0.2], rot=[0, 0, 1.5708], color="#2b2f36"),
            B("holder", "box", name="Cell holder", size=[0.14, 0.02, 0.06], pos=[-0.34, 0.005, 0.2], color="wood"),
            B("bulb", "sphere", name="Torch bulb", info="A 1.5 V torch bulb in a screw holder. It glows when current passes.",
              r=0.018, pos=[0.18, 0.05, 0.2], color="gold"),
            B("bholder", "box", name="Bulb holder", size=[0.06, 0.03, 0.06], pos=[0.18, 0.015, 0.2], color="#8a6a3a"),
            B("key", "box", name="Plug key", size=[0.06, 0.016, 0.04], pos=[-0.08, 0.008, 0.2], color="black"),
            *extra]


def bulb_circuit() -> dict:
    net = {"nodes": 4, "els": [
        {"id": "E", "kind": "V", "a": 1, "b": 0, "value": "Eb"},
        {"id": "RI", "kind": "R", "a": 1, "b": 2, "value": "rint"},
        {"id": "K", "kind": "S", "a": 2, "b": 3, "param": "key"},
        {"id": "AM", "kind": "R", "a": 3, "b": 4, "value": 0.01},
        {"id": "LAMP", "kind": "R", "a": 4, "b": 0, "value": "Rb"},
        {"id": "VM", "kind": "R", "a": 4, "b": 0, "value": 1000000.0}]}
    return lab(
        id="torch-bulb-circuit", rig="school-bulb-circuit", title="A simple circuit: cell, bulb and wires", group="Physics · Electricity",
        level="Class VI", topic="Electricity and Circuits", chapter="Electricity",
        aim="Join a cell, a torch bulb and a key with wires, close the key and measure the current that lights the bulb.",
        kernel="circuit", cfg={"net": net}, params={"Eb": 1.5, "rint": 0.6, "Rb": 4.2, "key": 0.0, "ncell": 1.0},
        autorun=True, camera={"pos": [0.0, 0.9, 0.9], "look": [0, 0, 0.05]}, floor=-0.03,
        bodies=_cellboard(),
        knobs=[knob("key", "Key (0 open / 1 closed)", "key", 0, 1, 1, 0, reset=False)],
        instruments=[{"id": "I", "kind": "readout", "label": "Ammeter", "var": "I_LAMP", "unit": "A", "digits": 3}],
        steps=["Join cell, key, ammeter and bulb in one loop with the leads.",
               "Keep the key open and check that the bulb is dark.", "Close the key: the bulb lights.",
               "Read the ammeter: that is the current in every part of the loop."],
        theory="A circuit must be a complete loop for current to flow. The cell drives the current; the bulb's filament "
               "resists it and glows white hot. With the key open the loop is broken and no current flows. The current "
               "is the same everywhere in a single loop: I = E / (R + r), where r is the cell's own internal resistance.",
        safety="Only dry cells here. Never join the two ends of a cell with a bare wire: that short circuit heats the "
               "wire and ruins the cell. Mains electricity is never used for this activity.",
        questions=[{"q": "The bulb does not light although the cell is new. Which is NOT a possible reason?",
                    "options": ["The key is open", "A lead is loose", "The bulb is fused", "The ammeter is in series"],
                    "answer": 3, "why": "An ammeter belongs in series; that is how it is meant to be joined."}],
        sources=[S6, SIM],
        check={"params": {"key": 1.0}, "measure": {"mode": "value", "vars": ["I_LAMP"]},
               "reading": "I_LAMP", "textbook": "bulb_I"},
    )


def cells_series() -> dict:
    net = {"nodes": 4, "els": [
        {"id": "E", "kind": "V", "a": 1, "b": 0, "value": "Eb"},
        {"id": "RI", "kind": "R", "a": 1, "b": 2, "value": "rint"},
        {"id": "K", "kind": "S", "a": 2, "b": 3, "param": "key"},
        {"id": "AM", "kind": "R", "a": 3, "b": 4, "value": 0.01},
        {"id": "LAMP", "kind": "R", "a": 4, "b": 0, "value": "Rb"},
        {"id": "VM", "kind": "R", "a": 4, "b": 0, "value": 1000000.0}]}
    return lab(
        id="cells-in-series", rig="school-bulb-circuit", title="Cells joined into a battery", group="Physics · Electricity",
        level="Class VII", topic="Electricity: Circuits and their Components", chapter="Electricity",
        aim="Light the same bulb from one cell and then from two cells in series, and compare the current.",
        kernel="circuit", cfg={"net": net}, params={"Eb": 3.0, "rint": 1.2, "Rb": 4.2, "key": 0.0, "ncell": 2.0},
        autorun=True, camera={"pos": [0.0, 0.9, 0.9], "look": [0, 0, 0.05]}, floor=-0.03,
        bodies=_cellboard([B("cellB", "cylinder", name="Second dry cell (1.5 V)", r=0.017, h=0.05,
                             pos=[-0.34, 0.02, 0.1], rot=[0, 0, 1.5708], color="#2b2f36")]),
        knobs=[knob("key", "Key (0 open / 1 closed)", "key", 0, 1, 1, 0, reset=False)],
        instruments=[{"id": "I", "kind": "readout", "label": "Ammeter", "var": "I_LAMP", "unit": "A", "digits": 3}],
        steps=["Put the cells in the holder, + of one touching − of the next: that is a battery.",
               "Close the key and read the ammeter.", "Take one cell out, bridge its place and read again.",
               "Two cells give nearly twice the emf, so the bulb is brighter."],
        theory="Cells joined in series, + to −, add their emfs: two 1.5 V cells give 3 V. Their internal resistances "
               "add as well, so the current is E_total / (R + r_total) and not quite double.",
        safety="Dry cells only. Put the cells in the right way round; a reversed cell works against the others.",
        questions=[{"q": "Two cells are joined + to +. The emf driving the bulb is",
                    "options": ["3 V", "1.5 V", "0 V"], "answer": 2,
                    "why": "Joined that way the two emfs oppose each other and cancel."}],
        sources=[S7, SIM],
        check={"params": {"key": 1.0}, "measure": {"mode": "value", "vars": ["I_LAMP"]},
               "reading": "I_LAMP", "textbook": "bulb_I"},
    )


def make_switch() -> dict:
    net = {"nodes": 4, "els": [
        {"id": "E", "kind": "V", "a": 1, "b": 0, "value": "Eb"},
        {"id": "RI", "kind": "R", "a": 1, "b": 2, "value": "rint"},
        {"id": "K", "kind": "S", "a": 2, "b": 3, "param": "key"},
        {"id": "AM", "kind": "R", "a": 3, "b": 4, "value": 0.01},
        {"id": "LAMP", "kind": "R", "a": 4, "b": 0, "value": "Rb"},
        {"id": "VM", "kind": "R", "a": 4, "b": 0, "value": 1000000.0}]}
    return lab(
        id="make-a-switch", rig="school-bulb-circuit", title="Make a switch from a safety pin", group="Physics · Electricity",
        level="Class VI", topic="Electricity and Circuits", chapter="Electricity",
        aim="Build a switch from two drawing pins and a safety pin, and use it to turn the bulb on and off.",
        kernel="circuit", cfg={"net": net}, params={"Eb": 1.5, "rint": 0.6, "Rb": 4.2, "key": 0.0, "ncell": 1.0},
        autorun=True, camera={"pos": [0.0, 0.9, 0.9], "look": [0, 0, 0.05]}, floor=-0.03,
        bodies=_cellboard([B("pinA", "cylinder", name="Drawing pin A", r=0.006, h=0.004,
                             pos=[-0.1, 0.012, 0.2], color="brass"),
                           B("pinB", "cylinder", name="Drawing pin B", r=0.006, h=0.004,
                             pos=[-0.04, 0.012, 0.2], color="brass"),
                           B("spin", "box", name="Safety pin", size=[0.05, 0.002, 0.004],
                             pos=[-0.07, 0.016, 0.2], color="steel")]),
        knobs=[knob("key", "Switch (0 off / 1 on)", "key", 0, 1, 1, 0, reset=False)],
        instruments=[{"id": "I", "kind": "readout", "label": "Ammeter", "var": "I_LAMP", "unit": "A", "digits": 3}],
        steps=["Press two drawing pins into the wooden board a little apart.",
               "Hook the safety pin under one drawing pin so it can swing.",
               "Join one lead to each drawing pin.",
               "Swing the safety pin on to the second pin: the metal path is complete and the bulb lights."],
        theory="A switch is only a gap in the circuit that you can close with a conductor. Metal conducts, so the "
               "steel safety pin completes the loop; swung away, the gap is air and no current flows.",
        safety="Drawing pins are sharp: press them in with the flat of the thumb. Dry cells only, never the mains.",
        questions=[{"q": "Why must the switch be made of metal?",
                    "options": ["Metal conducts electricity", "Metal is shiny", "Metal is cheap"], "answer": 0,
                    "why": "The switch has to carry the current across the gap."}],
        sources=[S6, SIM],
        check={"params": {"key": 1.0}, "measure": {"mode": "value", "vars": ["I_LAMP"]},
               "reading": "I_LAMP", "textbook": "bulb_I"},
    )


def tester() -> dict:
    net = {"nodes": 5, "els": [
        {"id": "E", "kind": "V", "a": 1, "b": 0, "value": "Eb"},
        {"id": "RI", "kind": "R", "a": 1, "b": 2, "value": "rint"},
        {"id": "K", "kind": "S", "a": 2, "b": 3, "param": "key"},
        {"id": "AM", "kind": "R", "a": 3, "b": 4, "value": 0.01},
        {"id": "LAMP", "kind": "R", "a": 4, "b": 5, "value": "Rb"},
        {"id": "RSAM", "kind": "R", "a": 5, "b": 0, "value": "Rsam"}]}
    return lab(
        id="conductors-insulators-tester", rig="school-bulb-circuit", title="Conductors and insulators: a circuit tester",
        group="Physics · Electricity", level="Class VI", topic="Electricity and Circuits", chapter="Electricity",
        aim="Put each material between the tester's probes and find out whether it lets the current through.",
        kernel="circuit", cfg={"net": net},
        params={"Eb": 1.5, "rint": 0.6, "Rb": 4.2, "Rsam": 0.00185, "Rins": 100000000.0, "key": 0.0, "ncell": 1.0},
        autorun=True, camera={"pos": [0.0, 0.9, 0.9], "look": [0, 0, 0.05]}, floor=-0.03,
        bodies=_cellboard([B("probeA", "cylinder", name="Probe A", r=0.004, h=0.07,
                             pos=[0.36, 0.01, 0.12], rot=[0, 0, 1.5708], color="red"),
                           B("probeB", "cylinder", name="Probe B", r=0.004, h=0.07,
                             pos=[0.36, 0.01, -0.02], rot=[0, 0, 1.5708], color="black"),
                           B("sample", "box", name="Sample under test", size=[0.05, 0.01, 0.06],
                             pos=[0.36, 0.01, 0.05], color="#8a6a3a")]),
        knobs=[knob("key", "Key (0 open / 1 closed)", "key", 0, 1, 1, 0, reset=False)],
        instruments=[{"id": "I", "kind": "readout", "label": "Current through the tester", "var": "I_LAMP",
                      "unit": "A", "digits": 4}],
        steps=["Close the key with the probes touching each other: the bulb must light.",
               "Hold the sample between the two probes.", "Watch the bulb and read the milliammeter.",
               "Sort the materials into conductors (the bulb lights) and insulators (it stays dark)."],
        theory="A material conducts if it has charges free to move. In metals the free electrons do that, so a metal "
               "sample adds almost no resistance and the bulb stays bright. In glass, rubber, dry wood and plastics the "
               "electrons are bound, the resistance is millions of times larger, and the current is far too small to "
               "light the bulb.",
        safety="Dry cells only. Test nothing that is plugged into the mains, and never use your own body as a sample.",
        questions=[{"q": "The bulb glows only dimly with a sample in place. The sample is",
                    "options": ["A poorer conductor than the leads", "A perfect insulator", "A cell"], "answer": 0,
                    "why": "Some current passes, so it conducts, but its resistance is large enough to dim the bulb."}],
        sources=[S6, S10, SIM],
        check={"params": {"key": 1.0}, "measure": {"mode": "value", "vars": ["I_LAMP"]},
               "reading": "I_LAMP", "textbook": "tester_I"},
    )


def _combo_bodies() -> list[dict]:
    return [board(1.0, 0.75),
            B("bat", "box", name="Battery (3 V)", size=[0.12, 0.05, 0.08], pos=[-0.36, 0.025, 0.22], color="#2b2f36"),
            B("key", "box", name="Plug key", size=[0.06, 0.016, 0.04], pos=[-0.16, 0.008, 0.22], color="black"),
            B("am", "box", name="Ammeter", size=[0.12, 0.05, 0.1], pos=[0.06, 0.025, 0.22], color="#2b2f36"),
            B("r1", "spring", name="Resistance coil R1", a=[-0.2, 0.03, -0.14], b=[-0.02, 0.03, -0.14],
              r=0.012, turns=16, wire=0.0015, color="copper"),
            B("r2", "spring", name="Resistance coil R2", a=[0.06, 0.03, -0.14], b=[0.24, 0.03, -0.14],
              r=0.012, turns=16, wire=0.0015, color="copper"),
            B("vm", "box", name="Voltmeter", size=[0.12, 0.05, 0.1], pos=[0.02, 0.025, -0.38], color="#2b2f36")]


def series_resistors() -> dict:
    net = {"nodes": 5, "els": [
        {"id": "E", "kind": "V", "a": 1, "b": 0, "value": "Eb"},
        {"id": "K", "kind": "S", "a": 1, "b": 2, "param": "key"},
        {"id": "RH", "kind": "R", "a": 2, "b": 3, "value": {"param": "Rh", "k": 1, "c": 0.01}},
        {"id": "AM", "kind": "R", "a": 3, "b": 4, "value": 0.01},
        {"id": "R1E", "kind": "R", "a": 4, "b": 5, "value": "R1"},
        {"id": "R2E", "kind": "R", "a": 5, "b": 0, "value": "R2"},
        {"id": "VM", "kind": "R", "a": 4, "b": 0, "value": 1000000.0}]}
    return lab(
        id="series-resistors", rig="resistors-combination", title="Two resistors in series", group="Physics · Electricity", level="Class X",
        topic="Electricity", chapter="Electricity",
        aim="Measure the equivalent resistance of two resistors joined in series and compare it with R1 + R2.",
        kernel="circuit", cfg={"net": net}, params={"Eb": 3.0, "R1": 10.0, "R2": 15.0, "Rh": 2.0, "key": 0.0},
        autorun=True, camera={"pos": [0.0, 0.95, 0.95], "look": [0, 0, -0.05]}, floor=-0.03,
        bodies=_combo_bodies(),
        knobs=[knob("key", "Key (0 open / 1 closed)", "key", 0, 1, 1, 0, reset=False),
               knob("Rh", "Rheostat", "Rh", 0.5, 30, 0.5, 2.0, "Ω"),
               knob("R1", "Coil R1", "R1", 4.7, 100, 0.1, 10, "Ω"),
               knob("R2", "Coil R2", "R2", 4.7, 100, 0.1, 15, "Ω")],
        instruments=[{"id": "I", "kind": "readout", "label": "Ammeter", "var": "I_AM", "unit": "A", "digits": 3},
                     {"id": "V", "kind": "readout", "label": "Voltmeter across both coils", "var": "V_VM",
                      "unit": "V", "digits": 2}],
        steps=["Join the two coils end to end: the same current must pass through both.",
               "Put the ammeter in series and the voltmeter across the pair.",
               "Close the key, read V and I, and work out R = V / I.",
               "Compare the answer with R1 + R2."],
        theory="In series the same current passes through both resistors and the potential differences add: "
               "V = V1 + V2 = I R1 + I R2. So the pair behaves as one resistor Rs = R1 + R2, always larger than "
               "either of them.",
        safety="A 3 V battery only. Take the plug out of the key between readings so the coils stay cool: a hot coil "
               "changes its resistance.",
        questions=[{"q": "Three 10 Ω resistors in series behave as",
                    "options": ["30 Ω", "10 Ω", "3.3 Ω"], "answer": 0, "why": "In series the resistances add."}],
        sources=[LM10, S10, SIM],
        check={"params": {"key": 1.0}, "measure": {"mode": "ratio", "num": "V_VM", "den": "I_AM", "as": "R", "vars": []},
               "reading": "R", "textbook": "ser_R"},
    )


def parallel_resistors() -> dict:
    net = {"nodes": 4, "els": [
        {"id": "E", "kind": "V", "a": 1, "b": 0, "value": "Eb"},
        {"id": "K", "kind": "S", "a": 1, "b": 2, "param": "key"},
        {"id": "RH", "kind": "R", "a": 2, "b": 3, "value": {"param": "Rh", "k": 1, "c": 0.01}},
        {"id": "AM", "kind": "R", "a": 3, "b": 4, "value": 0.01},
        {"id": "R1E", "kind": "R", "a": 4, "b": 0, "value": "R1"},
        {"id": "R2E", "kind": "R", "a": 4, "b": 0, "value": "R2"},
        {"id": "VM", "kind": "R", "a": 4, "b": 0, "value": 1000000.0}]}
    return lab(
        id="parallel-resistors", rig="resistors-combination", title="Two resistors in parallel", group="Physics · Electricity", level="Class X",
        topic="Electricity", chapter="Electricity",
        aim="Measure the equivalent resistance of two resistors joined in parallel and compare it with R1R2/(R1+R2).",
        kernel="circuit", cfg={"net": net}, params={"Eb": 3.0, "R1": 10.0, "R2": 15.0, "Rh": 2.0, "key": 0.0},
        autorun=True, camera={"pos": [0.0, 0.95, 0.95], "look": [0, 0, -0.05]}, floor=-0.03,
        bodies=_combo_bodies(),
        knobs=[knob("key", "Key (0 open / 1 closed)", "key", 0, 1, 1, 0, reset=False),
               knob("Rh", "Rheostat", "Rh", 0.5, 30, 0.5, 2.0, "Ω"),
               knob("R1", "Coil R1", "R1", 4.7, 100, 0.1, 10, "Ω"),
               knob("R2", "Coil R2", "R2", 4.7, 100, 0.1, 15, "Ω")],
        instruments=[{"id": "I", "kind": "readout", "label": "Ammeter (total current)", "var": "I_AM",
                      "unit": "A", "digits": 3},
                     {"id": "V", "kind": "readout", "label": "Voltmeter across the pair", "var": "V_VM",
                      "unit": "V", "digits": 2}],
        steps=["Join both ends of R1 to both ends of R2: both get the same potential difference.",
               "Put the ammeter in the main line and the voltmeter across the pair.",
               "Close the key, read V and I, and work out R = V / I.",
               "Compare the answer with R1R2/(R1 + R2); it is smaller than either coil."],
        theory="In parallel both resistors have the same potential difference and the currents add: "
               "I = V/R1 + V/R2. So 1/Rp = 1/R1 + 1/R2, and the equivalent resistance is always less than the "
               "smaller of the two, because the current has been given a second road.",
        safety="A 3 V battery only. The total current is larger than in series, so take the plug out of the key "
               "between readings.",
        questions=[{"q": "Two 10 Ω resistors in parallel behave as",
                    "options": ["5 Ω", "20 Ω", "10 Ω"], "answer": 0, "why": "1/Rp = 1/10 + 1/10 = 1/5."}],
        sources=[LM10, S10, SIM],
        check={"params": {"key": 1.0}, "measure": {"mode": "ratio", "num": "V_VM", "den": "I_AM", "as": "R", "vars": []},
               "reading": "R", "textbook": "par_R"},
    )


def resistance_factors() -> dict:
    return lab(
        id="resistance-factors", title="What the resistance of a wire depends on", group="Physics · Electricity",
        level="Class X", topic="Electricity", chapter="Electricity",
        aim="Measure the resistance of a wire and see how it changes with the wire's length, thickness and material.",
        kernel="wirecircuit", params={"Eb": 3.0, "rho": 1.09e-6, "Lw": 1.0, "dia": 0.000559, "Rh": 2.0, "key": 1.0},
        autorun=True, camera={"pos": [0.0, 0.95, 0.95], "look": [0, 0, -0.05]}, floor=-0.03,
        bodies=[board(1.0, 0.75),
                B("bat", "box", name="Battery (3 V)", size=[0.12, 0.05, 0.08], pos=[-0.36, 0.025, 0.22], color="#2b2f36"),
                B("key", "box", name="Plug key", size=[0.06, 0.016, 0.04], pos=[-0.16, 0.008, 0.22], color="black"),
                B("am", "box", name="Ammeter", size=[0.12, 0.05, 0.1], pos=[0.06, 0.025, 0.22], color="#2b2f36"),
                B("wire", "spring", name="Resistance wire under test", a=[-0.22, 0.03, -0.12],
                  b=[0.22, 0.03, -0.12], r=0.012, turns=22, wire=0.0012, color="steel"),
                B("vm", "box", name="Voltmeter across the wire", size=[0.12, 0.05, 0.1], pos=[0.0, 0.025, -0.38],
                  color="#2b2f36")],
        knobs=[knob("key", "Key (0 open / 1 closed)", "key", 0, 1, 1, 1, reset=False),
               knob("Lw", "Length of wire in the circuit", "Lw", 0.2, 3.0, 0.1, 1.0, "m"),
               knob("Rh", "Rheostat", "Rh", 0.5, 20, 0.5, 2.0, "Ω")],
        instruments=[{"id": "I", "kind": "readout", "label": "Ammeter", "var": "I_AM", "unit": "A", "digits": 3},
                     {"id": "V", "kind": "readout", "label": "Voltmeter", "var": "V_VM", "unit": "V", "digits": 3}],
        steps=["Clamp one metre of the wire between the terminals and close the key.",
               "Read V and I and work out R = V / I.",
               "Halve the length and measure again: R halves.",
               "Change to a thicker wire of the same material: R falls as the area grows.",
               "Change the material: R changes although the length and thickness are the same."],
        theory="For a uniform wire R = rho L / A: the resistance grows with the length, falls as the area of "
               "cross-section grows, and depends on the material through its resistivity rho. Doubling the diameter "
               "makes the area four times larger, so the resistance falls to a quarter.",
        safety="Low-voltage DC only. Keep the current small with the rheostat: a wire that warms up changes its "
               "resistance while you are measuring it.",
        questions=[{"q": "A wire is drawn out to twice its length (the same material and volume). Its resistance becomes",
                    "options": ["4 times", "2 times", "Half"], "answer": 0,
                    "why": "The length doubles and the area halves, so R = rho L / A grows four times."}],
        sources=[S10, LM10, SIM],
        check={"params": {}, "reading": "R", "textbook": "wire_R"},
    )


def heating_effect() -> dict:
    return lab(
        id="heating-effect-wire", title="Heating effect of an electric current", group="Physics · Electricity",
        level="Class VII", topic="Electric Current and its Effects", chapter="Electricity",
        aim="Pass a current through a nichrome coil in water and measure the temperature rise; compare it with I²Rt.",
        kernel="jouleheat", params={"Eb": 6.0, "rint": 0.5, "rho": 1.09e-6, "Lw": 0.5, "dia": 0.000559,
                                    "mw": 0.1, "cw": 4186.0, "hloss": 0.0, "Ta": 28.0, "tsec": 180.0, "key": 0.0},
        autorun=True, speeds=[1, 2, 5, 10], speed=5,
        camera={"pos": [0.0, 0.85, 0.9], "look": [0, 0.05, 0.0]}, floor=-0.03,
        bodies=[board(1.0, 0.7),
                B("box", "box", name="Battery eliminator (6 V DC)", size=[0.16, 0.08, 0.1],
                  pos=[-0.36, 0.04, 0.18], color="#3a4f6e"),
                B("key", "box", name="Plug key", size=[0.06, 0.016, 0.04], pos=[-0.12, 0.008, 0.2], color="black"),
                B("cal", "cylinder", name="Calorimeter", info="A copper vessel with a lagged jacket holding 100 g of water.",
                  r=0.045, h=0.09, pos=[0.14, 0.045, -0.06], color="copper"),
                B("coil", "spring", name="Nichrome coil", info="The heating coil, dipped in the water.",
                  a=[0.1, 0.03, -0.06], b=[0.18, 0.03, -0.06], r=0.01, turns=14, wire=0.0012, color="steel"),
                B("therm", "cylinder", name="Thermometer", r=0.005, h=0.2, pos=[0.14, 0.12, -0.02], color="glass"),
                B("am", "box", name="Ammeter", size=[0.12, 0.05, 0.1], pos=[-0.1, 0.025, -0.24], color="#2b2f36")],
        knobs=[knob("key", "Key (0 open / 1 closed)", "key", 0, 1, 1, 0, reset=False),
               knob("Eb", "Supply voltage", "Eb", 2, 9, 0.5, 6, "V"),
               knob("mw", "Mass of water", "mw", 0.05, 0.2, 0.01, 0.1, "kg")],
        instruments=[{"id": "T", "kind": "readout", "label": "Thermometer", "var": "T", "unit": "°C", "digits": 1},
                     {"id": "I", "kind": "readout", "label": "Ammeter", "var": "I", "unit": "A", "digits": 2},
                     {"id": "sw", "kind": "stopwatch", "label": "Stopwatch"}],
        steps=["Weigh 100 g of water into the calorimeter and note its temperature.",
               "Dip the nichrome coil in the water and close the key; start the stopwatch together.",
               "Stir gently and read the thermometer every half minute.",
               "After three minutes open the key and note the final temperature.",
               "Work out I²Rt and compare it with m c (change in temperature)."],
        theory="A current does work against the resistance of the wire and that work appears as heat: H = I²Rt "
               "(Joule's law of heating). If all of it goes into m kilograms of water of specific heat capacity c, "
               "the temperature rises by I²Rt / (m c). The coil is nichrome because its resistivity is high and it "
               "does not oxidise quickly when hot.",
        safety="Low-voltage DC supply only, never the mains. The coil gets hot: do not touch it, and keep it under "
               "water while the current is on. This is why a fuse or an immersion heater must never be improvised.",
        questions=[{"q": "The same coil is run at twice the voltage. The heat produced in the same time becomes",
                    "options": ["4 times", "2 times", "The same"], "answer": 0,
                    "why": "H = V²t/R, so doubling V gives four times the heat."}],
        sources=[S7, S10, SIM],
        check={"params": {"key": 1.0}, "reading": "dT", "textbook": "joule_dT"},
    )


# =============================================================================== B. the field of a current
def _cm_bodies(kind: str) -> list[dict]:
    out = [board(1.0, 0.75),
           B("box", "box", name="Battery eliminator (DC)", size=[0.16, 0.08, 0.1], pos=[-0.36, 0.04, 0.2],
             color="#3a4f6e"),
           B("key", "box", name="Plug key", size=[0.06, 0.016, 0.04], pos=[-0.12, 0.008, 0.22], color="black"),
           B("rh", "cylinder", name="Rheostat", r=0.022, h=0.2, pos=[0.22, 0.03, 0.22], rot=[0, 0, 1.5708],
             color="#c9b07a"),
           B("am", "box", name="Ammeter", size=[0.12, 0.05, 0.1], pos=[0.0, 0.025, 0.22], color="#2b2f36"),
           B("comp", "cylinder", name="Plotting compass", r=0.03, h=0.012, pos=[0.0, 0.006, -0.16], color="#2b2f36")]
    if kind == "wire":
        out.append(B("wire", "cylinder", name="Straight conductor", r=0.0012, h=0.6, pos=[0.0, 0.05, -0.16],
                     rot=[0, 0, 1.5708], color="copper"))
    elif kind == "coil":
        out.append(B("coil", "torus", name="Circular coil", r=0.05, tube=0.002, pos=[0.0, 0.06, -0.16],
                     rot=[0, 1.5708, 0], color="copper"))
    else:
        out.append(B("sol", "spring", name="Solenoid", a=[-0.15, 0.06, -0.16], b=[0.15, 0.06, -0.16],
                     r=0.012, turns=40, wire=0.0008, color="copper"))
    return out


def compass_near_wire() -> dict:
    return lab(
        id="compass-near-wire", rig="current-magnetism", title="A compass near a current-carrying wire", group="Physics · Magnetism",
        level="Class VII", topic="Electric Current and its Effects", chapter="Magnetic Effects of Current",
        aim="Lay a compass under a straight wire, pass a current and measure the deflection of the needle.",
        kernel="coilfield", params={"kind": 0.0, "Eb": 3.0, "Rs": 1.5, "d": 0.03, "wireL": 1.0,
                                    "BH": 4.0e-5, "key": 0.0, "rev": 1.0},
        autorun=True, camera={"pos": [0.0, 0.8, 0.85], "look": [0, 0.02, -0.06]}, floor=-0.03,
        bodies=_cm_bodies("wire"),
        knobs=[knob("key", "Key (0 open / 1 closed)", "key", 0, 1, 1, 0, reset=False),
               knob("Rs", "Circuit resistance (sets the current)", "Rs", 1.0, 12.0, 0.5, 1.5, "Ω"),
               knob("d", "Compass below the wire", "d", 0.01, 0.1, 0.005, 0.03, "m"),
               knob("rev", "Current direction (+1 / −1)", "rev", -1, 1, 2, 1)],
        instruments=[{"id": "I", "kind": "readout", "label": "Ammeter", "var": "I", "unit": "A", "digits": 2},
                     {"id": "B", "kind": "readout", "label": "Field at the needle", "var": "B", "k": 1000000.0,
                      "unit": "µT", "digits": 2},
                     {"id": "th", "kind": "readout", "label": "Deflection", "var": "theta", "k": 57.29578,
                      "unit": "°", "digits": 1}],
        steps=["Set the compass on the board and let the needle settle along north-south.",
               "Hold the wire above the needle, along its length, and close the key.",
               "Read the deflection; it grows with the current and falls as the wire is raised.",
               "Reverse the current: the needle swings the other way (Oersted's experiment)."],
        theory="A current makes a magnetic field. Round a long straight wire the field circles the wire, "
               "B = mu0 I / (2 pi d), and close to the middle of a wire of length L the measured field is "
               "mu0 I / (2 pi d) × (L/2)/sqrt(d² + L²/4). The needle sets itself along the resultant of this field and "
               "the earth's horizontal field, so tan(deflection) = B / B_H.",
        safety="Low-voltage DC only, with a rheostat in the circuit. Keep the current on for short spells; a bare wire "
               "carrying amperes gets warm. Never do this with mains wiring.",
        questions=[{"q": "The current is doubled and the compass left where it is. tan(deflection)",
                    "options": ["Doubles", "Halves", "Does not change"], "answer": 0,
                    "why": "B is proportional to I, and tan(deflection) = B / B_H."}],
        sources=[S7, XI, SIM],
        check={"params": {"key": 1.0}, "reading": "B", "textbook": "cfield_B"},
    )


def field_straight() -> dict:
    return lab(
        id="field-straight-conductor", rig="current-magnetism", title="Magnetic field of a straight conductor", group="Physics · Magnetism",
        level="Class X", topic="Magnetic Effects of Electric Current", chapter="Magnetic Effects of Current",
        aim="Map the field round a straight current-carrying conductor and measure how it falls with distance.",
        kernel="coilfield", params={"kind": 0.0, "Eb": 6.0, "Rs": 2.0, "d": 0.02, "wireL": 1.0,
                                    "BH": 4.0e-5, "key": 0.0, "rev": 1.0},
        autorun=True, camera={"pos": [0.0, 0.8, 0.85], "look": [0, 0.02, -0.06]}, floor=-0.03,
        bodies=_cm_bodies("wire"),
        knobs=[knob("key", "Key (0 open / 1 closed)", "key", 0, 1, 1, 0, reset=False),
               knob("Rs", "Circuit resistance (sets the current)", "Rs", 1.0, 12.0, 0.5, 2.0, "Ω"),
               knob("d", "Distance from the wire", "d", 0.01, 0.1, 0.005, 0.02, "m"),
               knob("rev", "Current direction (+1 / −1)", "rev", -1, 1, 2, 1)],
        instruments=[{"id": "I", "kind": "readout", "label": "Ammeter", "var": "I", "unit": "A", "digits": 2},
                     {"id": "B", "kind": "readout", "label": "Field", "var": "B", "k": 1000000.0, "unit": "µT",
                      "digits": 2},
                     {"id": "th", "kind": "readout", "label": "Deflection", "var": "theta", "k": 57.29578,
                      "unit": "°", "digits": 1}],
        steps=["Pass the conductor vertically through a card and sprinkle iron filings on the card.",
               "Close the key: the filings set themselves in circles round the wire.",
               "Replace the filings with a plotting compass and read the deflection at several distances.",
               "Reverse the current and see every compass turn through 180°."],
        theory="The field lines round a straight conductor are concentric circles whose direction is given by the "
               "right-hand thumb rule: thumb along the current, fingers curling the way the field points. Its "
               "magnitude falls off as 1/d, so tan(deflection) halves when the distance doubles.",
        safety="Low-voltage DC and a rheostat. The conductor warms up at several amperes, so take the readings quickly "
               "and open the key between them. No mains wiring.",
        questions=[{"q": "The field lines round a long straight current are",
                    "options": ["Concentric circles", "Straight lines along the wire", "Radial lines"], "answer": 0,
                    "why": "That is what the iron filings show, and the right-hand thumb rule gives their direction."}],
        sources=[S10, XI, SIM],
        check={"params": {"key": 1.0}, "reading": "B", "textbook": "cfield_B"},
    )


def field_loop() -> dict:
    return lab(
        id="field-circular-loop", rig="current-magnetism", title="Magnetic field of a circular coil", group="Physics · Magnetism",
        level="Class X", topic="Magnetic Effects of Electric Current", chapter="Magnetic Effects of Current",
        aim="Measure the field at the centre of a circular coil and see how it grows with the current and the turns.",
        kernel="coilfield", params={"kind": 1.0, "Eb": 3.0, "Rs": 6.0, "N": 5.0, "a": 0.05, "d": 0.0,
                                    "BH": 4.0e-5, "key": 0.0, "rev": 1.0},
        autorun=True, camera={"pos": [0.0, 0.8, 0.85], "look": [0, 0.03, -0.08]}, floor=-0.03,
        bodies=_cm_bodies("coil"),
        knobs=[knob("key", "Key (0 open / 1 closed)", "key", 0, 1, 1, 0, reset=False),
               knob("Rs", "Circuit resistance (sets the current)", "Rs", 2.0, 20.0, 0.5, 6.0, "Ω"),
               knob("N", "Turns in the coil", "N", 1, 20, 1, 5),
               knob("d", "Probe along the axis", "d", 0.0, 0.12, 0.005, 0.0, "m")],
        instruments=[{"id": "I", "kind": "readout", "label": "Ammeter", "var": "I", "unit": "A", "digits": 2},
                     {"id": "B", "kind": "readout", "label": "Teslameter", "var": "B", "k": 1000.0, "unit": "mT",
                      "digits": 3},
                     {"id": "th", "kind": "readout", "label": "Compass deflection", "var": "theta", "k": 57.29578,
                      "unit": "°", "digits": 1}],
        steps=["Wind the given number of turns on the 5 cm former and join the coil in the circuit.",
               "Put the Hall probe at the centre of the coil, its plane facing the coil.",
               "Close the key and read the field; it is proportional to the current and to the number of turns.",
               "Slide the probe along the axis: the field falls away from the centre."],
        theory="Each element of the loop contributes to the field, and on the axis all the contributions point the "
               "same way. Adding them gives B = mu0 N I a² / (2 (a² + z²)^1.5), which at the centre (z = 0) is "
               "mu0 N I / (2a). The field lines pass through the loop in one direction and curl round outside, so a "
               "current loop behaves like a short magnet.",
        safety="Low-voltage DC with a rheostat. Many turns of thin wire heat quickly: keep the current under an ampere "
               "and open the key between readings.",
        questions=[{"q": "The number of turns is doubled at the same current. The field at the centre",
                    "options": ["Doubles", "Halves", "Is unchanged"], "answer": 0,
                    "why": "Every turn adds its own field: B is proportional to N."}],
        sources=[S10, XI, SIM],
        check={"params": {"key": 1.0}, "reading": "B", "textbook": "cfield_B"},
    )


def field_solenoid() -> dict:
    return lab(
        id="field-solenoid", rig="current-magnetism", title="Magnetic field of a solenoid", group="Physics · Magnetism",
        level="Class X", topic="Magnetic Effects of Electric Current", chapter="Magnetic Effects of Current",
        aim="Measure the field inside a solenoid and show that it is uniform and proportional to the turns per metre.",
        kernel="coilfield", params={"kind": 2.0, "Eb": 3.0, "Rs": 6.0, "a": 0.01, "Lsol": 0.3, "nsol": 1000.0,
                                    "mur": 1.0, "BH": 4.0e-5, "key": 0.0, "rev": 1.0},
        autorun=True, camera={"pos": [0.0, 0.8, 0.85], "look": [0, 0.03, -0.08]}, floor=-0.03,
        bodies=_cm_bodies("sol"),
        knobs=[knob("key", "Key (0 open / 1 closed)", "key", 0, 1, 1, 0, reset=False),
               knob("Rs", "Circuit resistance (sets the current)", "Rs", 2.0, 20.0, 0.5, 6.0, "Ω"),
               knob("nsol", "Turns per metre", "nsol", 400, 2000, 100, 1000, "/m")],
        instruments=[{"id": "I", "kind": "readout", "label": "Ammeter", "var": "I", "unit": "A", "digits": 2},
                     {"id": "B", "kind": "readout", "label": "Teslameter", "var": "B", "k": 1000.0, "unit": "mT",
                      "digits": 3}],
        steps=["Join the 30 cm solenoid in series with the key, ammeter and rheostat.",
               "Slide the Hall probe to the middle of the solenoid.",
               "Close the key and read the field; move the probe about inside: it hardly changes.",
               "Compare the reading with mu0 n I."],
        theory="A solenoid is a stack of circular loops. Inside a long one their fields add to a nearly uniform field "
               "along the axis, B = mu0 n I, where n is the turns per metre; for a solenoid of finite length L and "
               "radius a the centre field is mu0 n I × (L/2)/sqrt(a² + L²/4). Outside, the lines spread out and return, "
               "exactly like the field of a bar magnet, which is why one end behaves as N and the other as S.",
        safety="Low-voltage DC with a rheostat. The winding heats up: read quickly and open the key.",
        questions=[{"q": "The field inside a long solenoid depends on",
                    "options": ["The turns per metre and the current", "The total number of turns only",
                                "The radius of the solenoid"], "answer": 0, "why": "B = mu0 n I inside a long solenoid."}],
        sources=[S10, XI, SIM],
        check={"params": {"key": 1.0}, "reading": "B", "textbook": "cfield_B"},
    )


def electromagnet() -> dict:
    return lab(
        id="electromagnet-nail", rig="current-magnetism", title="An electromagnet on an iron nail", group="Physics · Magnetism",
        level="Class VII", topic="Electric Current and its Effects", chapter="Magnetic Effects of Current",
        aim="Wind a coil on an iron nail, measure the field with and without the core and find how much the iron "
            "multiplies it.",
        kernel="coilfield", params={"kind": 2.0, "Eb": 3.0, "Rs": 6.0, "a": 0.004, "Lsol": 0.06, "nsol": 1000.0,
                                    "mur": 180.0, "BH": 4.0e-5, "key": 0.0, "rev": 1.0},
        autorun=True, camera={"pos": [0.0, 0.8, 0.85], "look": [0, 0.03, -0.08]}, floor=-0.03,
        bodies=_cm_bodies("sol") + [B("nail", "cylinder", name="Iron nail (the core)", r=0.004, h=0.06,
                                      pos=[0.0, 0.06, -0.16], rot=[0, 0, 1.5708], color="#6e7276")],
        knobs=[knob("key", "Key (0 open / 1 closed)", "key", 0, 1, 1, 0, reset=False),
               knob("Rs", "Circuit resistance (sets the current)", "Rs", 2.0, 20.0, 0.5, 6.0, "Ω"),
               knob("nsol", "Turns per metre on the nail", "nsol", 500, 2000, 100, 1000, "/m"),
               knob("mur", "Iron core (its effect is hidden)", "mur", 1, 400, 1, 180, hidden=True)],
        instruments=[{"id": "I", "kind": "readout", "label": "Ammeter", "var": "I", "unit": "A", "digits": 2},
                     {"id": "B", "kind": "readout", "label": "Teslameter", "var": "B", "k": 1000.0, "unit": "mT",
                      "digits": 2}],
        steps=["Wind about 60 turns of insulated wire along a 6 cm iron nail.",
               "Measure the field at the middle of the winding with the nail taken out.",
               "Put the nail back and measure again at the same current.",
               "Divide the two readings: that ratio is how much the iron core multiplies the field."],
        theory="The current's field magnetises the iron, and the iron's own magnetisation adds to it, so the field "
               "inside becomes B = mu0 mu_r n I. For a short nail the useful multiplier is far smaller than the "
               "material's textbook permeability, because the poles at the ends push back; what the experiment "
               "measures is this effective multiplier for this nail. Open the key and almost all of it goes: soft iron "
               "keeps very little magnetism, which is what makes an electromagnet useful.",
        safety="Low-voltage DC only. The winding and the nail get hot; open the key between readings and do not lift "
               "heavy things with the magnet.",
        questions=[{"q": "Why is soft iron used for the core of an electromagnet?",
                    "options": ["It is strongly magnetised but keeps almost nothing when the current stops",
                                "It is a better conductor than copper", "It cannot be magnetised at all"],
                    "answer": 0, "why": "The magnet has to switch off when the current does."}],
        sources=[S7, XI, SIM],
        check={"params": {"key": 1.0}, "reading": "B", "textbook": "cfield_B"},
    )


# =============================================================================== C. a bar magnet
def _bm_bodies() -> list[dict]:
    return [B("tbl", "box", name="Plotting board", size=[0.9, 0.012, 0.6], pos=[0, 0, -0.1], color="wood", cut=False),
            B("card", "box", name="Drawing sheet", size=[0.6, 0.001, 0.42], pos=[0, 0.007, -0.1], color="white"),
            B("mag", "box", name="Bar magnet", info="Red end N, blue end S. Its moment is what the experiment finds.",
              size=[0.05, 0.012, 0.012], pos=[0, 0.014, -0.1], color="red"),
            B("comp", "cylinder", name="Plotting compass", r=0.02, h=0.008, pos=[0.14, 0.012, -0.1],
              color="#2b2f36"),
            B("stand", "cylinder", name="Stand for the thread", r=0.008, h=0.5, pos=[-0.34, 0.25, -0.26],
              color="steel")]


def bar_magnet_field() -> dict:
    return lab(
        id="field-lines-bar-magnet", rig="bar-magnet-field", title="Field lines of a bar magnet", group="Physics · Magnetism",
        level="Class X", topic="Magnetic Effects of Electric Current", chapter="Magnetism",
        aim="Plot the field of a bar magnet and find the neutral points, where its field cancels the earth's.",
        kernel="barmagnet", params={"m": 1.0, "Lbar": 0.05, "wbar": 0.01, "mass": 0.03, "BH": 4.0e-5,
                                    "d": 0.07, "theta0": 0.1745, "dnp": 0.13},
        autorun=True, camera={"pos": [0.0, 0.75, 0.8], "look": [0, 0.0, -0.1]}, floor=-0.03,
        bodies=_bm_bodies(),
        knobs=[knob("dnp", "Compass east of the magnet's centre", "dnp", 0.04, 0.3, 0.005, 0.13, "m"),
               knob("m", "Strength of this magnet (hidden)", "m", 0.2, 4.0, 0.05, 1.0, "A·m²", hidden=True)],
        instruments=[{"id": "B", "kind": "readout", "label": "Magnet's field at the compass", "var": "B_eq",
                      "k": 1000000.0, "unit": "µT", "digits": 2}],
        steps=["Lay the magnet on the sheet with its N pole pointing north.",
               "Put the compass beside it and mark the needle's direction; move it on and repeat to draw a field line.",
               "Move the compass east along the line through the magnet's centre until the needle has no settled "
               "direction: that is a neutral point.",
               "Measure its distance from the centre on both sides and take the mean."],
        theory="A bar magnet behaves as two poles of strength q_m at its ends, and on the line through its centre at "
               "right angles to it (the equatorial line) its field points south, straight against the earth's "
               "horizontal field. Where the two are equal the resultant is zero: a neutral point. Setting "
               "mu0 m / (4 pi (d² + l²)^1.5) = B_H gives the magnet's moment m from the measured distance d.",
        safety="Keep the magnet away from phones, watches and the compass's own pivot. Do not drop or heat it: both "
               "weaken a magnet.",
        questions=[{"q": "With the magnet's N pole pointing north, the neutral points lie",
                    "options": ["On its equatorial line, east and west", "On its axis, north and south",
                                "Right at its poles"], "answer": 0,
                    "why": "Only there does the magnet's field point exactly against the earth's."}],
        sources=[S10, XI, SIM],
        check={"params": {}, "reading": "np_d", "textbook": "bm_npeq"},
    )


def like_poles() -> dict:
    return lab(
        id="like-unlike-poles", rig="bar-magnet-field", title="Attraction and repulsion between poles", group="Physics · Magnetism",
        level="Class VI", topic="Fun with Magnets", chapter="Magnetism",
        aim="Bring like poles of two magnets together and measure the force that pushes them apart.",
        kernel="barmagnet", params={"m": 1.0, "Lbar": 0.05, "wbar": 0.01, "mass": 0.03, "BH": 4.0e-5,
                                    "d": 0.07, "theta0": 0.1745, "dnp": 0.13},
        autorun=True, camera={"pos": [0.0, 0.7, 0.8], "look": [0, 0.0, -0.1]}, floor=-0.03,
        bodies=_bm_bodies() + [B("mag2", "box", name="Second bar magnet", size=[0.05, 0.012, 0.012],
                                 pos=[0.12, 0.014, -0.1], color="blue")],
        knobs=[knob("d", "Centre-to-centre distance", "d", 0.055, 0.2, 0.005, 0.07, "m"),
               knob("m", "Strength of each magnet (hidden)", "m", 0.2, 4.0, 0.05, 1.0, "A·m²", hidden=True)],
        instruments=[{"id": "F", "kind": "readout", "label": "Force on the balance", "var": "F", "k": 1000.0,
                      "unit": "mN", "digits": 2}],
        steps=["Fix one magnet on the board and stand the second on the balance, N pole facing N pole.",
               "Read the force at a measured separation.",
               "Move the magnets apart in steps and read the force each time.",
               "Turn one magnet round: like poles repel, unlike poles attract."],
        theory="Each pole acts on each pole with mu0 q1 q2 / (4 pi r²), repelling if the poles are alike. With two bar "
               "magnets, N facing N, the four pairs give "
               "F = mu0 q_m²/(4 pi) [1/(d − 2l)² − 2/d² + 1/(d + 2l)²]. The force falls away very fast with distance, "
               "which is why magnets seem to grab each other only when they are close.",
        safety="Let the magnets come together gently: a strong pair can snap shut and chip, or pinch a finger. Keep "
               "them off anything magnetic.",
        questions=[{"q": "The distance between the magnets is doubled. The force",
                    "options": ["Falls to much less than a quarter", "Doubles", "Is unchanged"], "answer": 0,
                    "why": "Each pole pair falls as 1/r², and the four pairs cancel more and more as d grows."}],
        sources=[S6, XI, SIM],
        check={"params": {}, "reading": "F", "textbook": "bm_F"},
    )


def suspended_magnet() -> dict:
    return lab(
        id="suspended-magnet-direction", rig="bar-magnet-field", title="A suspended magnet points north-south",
        group="Physics · Magnetism", level="Class VI", topic="Fun with Magnets", chapter="Magnetism",
        aim="Hang a bar magnet by a thread, watch it settle north-south, and time its oscillations.",
        kernel="barmagnet", params={"m": 1.0, "Lbar": 0.05, "wbar": 0.01, "mass": 0.03, "BH": 4.0e-5,
                                    "d": 0.07, "theta0": 0.1745, "dnp": 0.13},
        autorun=True, speeds=[0.25, 0.5, 1, 2], speed=1,
        camera={"pos": [0.1, 0.6, 0.8], "look": [-0.05, 0.1, -0.15]}, floor=-0.03,
        bodies=_bm_bodies(),
        knobs=[knob("theta0", "Angle it is turned through to start", "theta0", 0.05, 0.35, 0.01, 0.1745, "rad"),
               knob("m", "Strength of this magnet (hidden)", "m", 0.2, 4.0, 0.05, 1.0, "A·m²", hidden=True)],
        instruments=[{"id": "th", "kind": "readout", "label": "Angle from north", "var": "theta", "k": 57.29578,
                      "unit": "°", "digits": 1},
                     {"id": "sw", "kind": "stopwatch", "label": "Stopwatch (20 oscillations)"}],
        steps=["Hang the magnet in its stirrup on the torsionless thread and let it come to rest.",
               "Note that it settles along north-south: the magnetic meridian.",
               "Turn it through a small angle and let go; time twenty oscillations.",
               "Work out the period and from it the magnet's moment."],
        theory="The earth's horizontal field exerts a couple m B_H sin(theta) on the magnet, so a magnet turned a "
               "little away from north swings to and fro like a pendulum: T = 2 pi sqrt(I / (m B_H)), with "
               "I = M(L² + b²)/12 for a bar of mass M. A needle floated on water does the same thing, which is all a "
               "compass is.",
        safety="Use a fresh untwisted thread so there is no torsion, and keep iron, magnets and phones well away from "
               "the swinging magnet.",
        questions=[{"q": "The same magnet is taken where B_H is smaller. Its period",
                    "options": ["Grows", "Falls", "Does not change"], "answer": 0,
                    "why": "T = 2 pi sqrt(I/(m B_H)): a weaker field means a slower swing."}],
        sources=[S6, XI, SIM],
        check={"params": {}, "reading": "T", "textbook": "bm_T"},
    )


def stroking_magnet() -> dict:
    return lab(
        id="make-a-magnet-stroking", rig="bar-magnet-field", title="Make a magnet by stroking", group="Physics · Magnetism",
        level="Class VI", topic="Fun with Magnets", chapter="Magnetism",
        aim="Stroke an iron strip with one pole of a magnet and measure how strong a magnet it has become.",
        kernel="barmagnet", params={"m": 0.12, "Lbar": 0.08, "wbar": 0.012, "mass": 0.02, "BH": 4.0e-5,
                                    "d": 0.09, "theta0": 0.1745, "dnp": 0.13},
        autorun=True, speeds=[0.25, 0.5, 1, 2], speed=1,
        camera={"pos": [0.1, 0.6, 0.8], "look": [-0.05, 0.1, -0.15]}, floor=-0.03,
        bodies=_bm_bodies() + [B("strip", "box", name="Iron strip", size=[0.08, 0.004, 0.012],
                                 pos=[0.1, 0.012, -0.22], color="#6e7276")],
        knobs=[knob("theta0", "Angle it is turned through to start", "theta0", 0.05, 0.35, 0.01, 0.1745, "rad"),
               knob("m", "Moment given to the strip (hidden)", "m", 0.02, 1.0, 0.01, 0.12, "A·m²", hidden=True)],
        instruments=[{"id": "th", "kind": "readout", "label": "Angle from north", "var": "theta", "k": 57.29578,
                      "unit": "°", "digits": 1},
                     {"id": "sw", "kind": "stopwatch", "label": "Stopwatch (20 oscillations)"}],
        steps=["Stroke the iron strip from end to end with one pole of the bar magnet, always the same way, "
               "thirty times, lifting the magnet clear on the way back.",
               "Hang the strip in the stirrup: it now sets itself north-south, so it has become a magnet.",
               "Time twenty oscillations and work out its period.",
               "Work out its magnetic moment; it is much smaller than the stroking magnet's."],
        theory="Iron is full of tiny magnetic domains pointing every way. Stroking always in one direction turns more "
               "and more of them the same way, and the strip becomes a magnet with poles at its ends. Timing its "
               "oscillations in the earth's field, T = 2 pi sqrt(I/(m B_H)), gives the moment it has gained. Heating "
               "it or hammering it shakes the domains back out of line.",
        safety="Stroke in one direction only and lift the magnet well clear on the return, or the domains are turned "
               "back and the strip stays unmagnetised. Keep the strip away from compasses until you test it.",
        questions=[{"q": "Why must the magnet be lifted clear on the way back?",
                    "options": ["Otherwise it turns the domains back the other way", "Otherwise it scratches the strip",
                                "Otherwise the strip gets hot"], "answer": 0,
                    "why": "Stroking back the other way undoes the alignment you have just made."}],
        sources=[S6, XI, SIM],
        check={"params": {}, "reading": "T", "textbook": "bm_T"},
    )


# =============================================================================== D. static electricity
def _es_bodies() -> list[dict]:
    return [B("tbl", "box", name="Bench top", size=[0.9, 0.012, 0.6], pos=[0, 0, -0.1], color="wood", cut=False),
            B("stand", "cylinder", name="Stand", r=0.008, h=0.5, pos=[-0.18, 0.25, -0.1], color="steel"),
            B("arm", "box", name="Cross arm", size=[0.2, 0.008, 0.008], pos=[-0.08, 0.48, -0.1], color="steel"),
            B("ballA", "sphere", name="Pith ball A", r=0.006, pos=[-0.03, 0.28, -0.1], color="white"),
            B("ballB", "sphere", name="Pith ball B", r=0.006, pos=[0.01, 0.28, -0.1], color="white"),
            B("rod", "cylinder", name="Polythene rod", r=0.006, h=0.3, pos=[0.22, 0.03, 0.0],
              rot=[0, 0, 1.5708], color="black"),
            B("duster", "box", name="Woollen duster", size=[0.08, 0.02, 0.06], pos=[0.22, 0.01, -0.2],
              color="#8a6a3a")]


def rubbing() -> dict:
    return lab(
        id="charging-by-rubbing-6-10", title="Charging by rubbing: attraction and repulsion",
        group="Physics · Electricity", level="Class VIII", topic="Some Natural Phenomena",
        chapter="Static Electricity",
        aim="Charge two pith balls from a rubbed polythene rod and measure how far apart they hang.",
        kernel="estatic", params={"q": 3.4e-9, "Lth": 0.2, "mass": 1.0e-4, "g": 9.8, "charged": 0.0},
        autorun=True, camera={"pos": [0.15, 0.5, 0.7], "look": [0.0, 0.25, -0.1]}, floor=-0.03,
        bodies=_es_bodies(),
        knobs=[knob("charged", "Balls charged (0 no / 1 yes)", "charged", 0, 1, 1, 0, reset=False),
               knob("Lth", "Length of each thread", "Lth", 0.1, 0.3, 0.01, 0.2, "m"),
               knob("q", "Charge given to each ball (hidden)", "q", 1e-9, 8e-9, 1e-10, 3.4e-9, "C", hidden=True)],
        instruments=[{"id": "r", "kind": "readout", "label": "Separation of the balls", "var": "r", "k": 1000.0,
                      "unit": "mm", "digits": 1},
                     {"id": "th", "kind": "readout", "label": "Angle of each thread", "var": "theta", "k": 57.29578,
                      "unit": "°", "digits": 1}],
        steps=["Hang two pith balls side by side on threads of the same length so they just touch.",
               "Rub the polythene rod with the woollen duster and touch it to the balls.",
               "Both balls take the same kind of charge, so they push each other apart; measure the separation.",
               "Work out the charge on each ball from the separation."],
        theory="Rubbing moves electrons from one surface to the other: polythene rubbed with wool takes electrons and "
               "becomes negative, the wool positive. Touching the rod to both balls gives them the same kind of charge, "
               "and like charges repel. Each ball hangs where gravity, the thread's pull and the Coulomb force balance, "
               "and for small angles the separation is r = (2 k q² L / (m g))^(1/3), so measuring r gives q.",
        safety="Everything here is a few nanocoulombs: it cannot hurt you, but it does vanish in damp air, so do the "
               "activity on a dry day and keep your hands off the charged parts.",
        questions=[{"q": "One charged ball is brought near an uncharged one. What happens?",
                    "options": ["They attract at first", "They repel", "Nothing at all"], "answer": 0,
                    "why": "The charge pulls the opposite charge to the near face of the neutral ball, so it is attracted."}],
        sources=[S8, SIM],
        check={"params": {"charged": 1.0}, "reading": "r", "textbook": "es_r"},
    )


def electroscope() -> dict:
    return lab(
        id="jar-electroscope", title="A jar electroscope", group="Physics · Electricity", level="Class VIII",
        topic="Some Natural Phenomena", chapter="Static Electricity",
        aim="Build an electroscope from a jar and two foil strips and use the gap between them to detect charge.",
        kernel="estatic", params={"q": 5.8e-10, "Lth": 0.06, "mass": 1.2e-5, "g": 9.8, "charged": 0.0},
        autorun=True, camera={"pos": [0.12, 0.42, 0.55], "look": [0.0, 0.16, -0.08]}, floor=-0.03,
        bodies=[B("tbl", "box", name="Bench top", size=[0.9, 0.012, 0.6], pos=[0, 0, -0.1], color="wood", cut=False),
                B("jar", "cylinder", name="Glass jar", r=0.05, h=0.16, pos=[0, 0.09, -0.1], color="glass", open=True),
                B("lid", "box", name="Cardboard lid", size=[0.12, 0.004, 0.12], pos=[0, 0.172, -0.1],
                  color="#8a6a3a"),
                B("wire", "cylinder", name="Copper wire through the lid", r=0.0012, h=0.16,
                  pos=[0, 0.14, -0.1], color="copper"),
                B("disc", "cylinder", name="Metal disc on top", r=0.016, h=0.002, pos=[0, 0.222, -0.1],
                  color="brass"),
                B("leafA", "box", name="Foil strip A", size=[0.008, 0.055, 0.0002], pos=[-0.004, 0.085, -0.1],
                  color="#d9d9d9"),
                B("leafB", "box", name="Foil strip B", size=[0.008, 0.055, 0.0002], pos=[0.004, 0.085, -0.1],
                  color="#d9d9d9"),
                B("rod", "cylinder", name="Polythene rod", r=0.006, h=0.3, pos=[0.26, 0.03, 0.02],
                  rot=[0, 0, 1.5708], color="black"),
                B("duster", "box", name="Woollen duster", size=[0.08, 0.02, 0.06], pos=[0.26, 0.01, -0.2],
                  color="#8a6a3a")],
        knobs=[knob("charged", "Charge touched to the disc (0 no / 1 yes)", "charged", 0, 1, 1, 0, reset=False),
               knob("Lth", "Length of each foil strip", "Lth", 0.03, 0.09, 0.005, 0.06, "m"),
               knob("q", "Charge reaching each strip (hidden)", "q", 1e-10, 3e-9, 1e-11, 5.8e-10, "C", hidden=True)],
        instruments=[{"id": "r", "kind": "readout", "label": "Gap between the strip tips", "var": "r", "k": 1000.0,
                      "unit": "mm", "digits": 1},
                     {"id": "th", "kind": "readout", "label": "Angle of each strip", "var": "theta", "k": 57.29578,
                      "unit": "°", "digits": 1}],
        steps=["Push a copper wire through the cardboard lid, bend a hook at the bottom and fix a metal disc on top.",
               "Hang two thin aluminium foil strips side by side on the hook and close the jar.",
               "Rub the polythene rod and touch it to the disc: the charge spreads down the wire to both strips and "
               "they fly apart.",
               "Measure the gap between the tips and work out the charge on each strip.",
               "Touch the disc with your finger: the charge runs to earth and the strips fall together."],
        theory="A conductor shares charge over all of it, so charge put on the disc runs down the wire to both strips. "
               "They then carry the same kind of charge and repel each other. Treating each strip as a small charge "
               "hanging on a hinge of its own length, the gap between the tips obeys the same balance as two charged "
               "balls on threads: r = (2 k q² L / (m g))^(1/3), so the gap tells you how much charge arrived. The glass "
               "jar is there to keep draughts off, not to hold the charge.",
        safety="A few nanocoulombs, quite harmless. Earth the disc with your finger before taking the lid off, and keep "
               "the strips dry: damp air leaks the charge away in seconds.",
        questions=[{"q": "The strips of a charged electroscope fall together when you touch the disc because",
                    "options": ["The charge flows away through you to the earth",
                                "The strips get heavier", "The air pushes them in"], "answer": 0,
                    "why": "You are a conductor joined to the earth, so the charge leaves the electroscope."}],
        sources=[S8, SIM],
        check={"params": {"charged": 1.0}, "reading": "r", "textbook": "es_r"},
    )


BUILDERS = (bulb_circuit, cells_series, make_switch, tester, series_resistors, parallel_resistors,
            resistance_factors, heating_effect, compass_near_wire, field_straight, field_loop, field_solenoid,
            electromagnet, bar_magnet_field, like_poles, suspended_magnet, stroking_magnet, rubbing, electroscope)
