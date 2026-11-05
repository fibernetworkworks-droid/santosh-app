"""Lab pack `em_ug`: the UNDERGRADUATE electricity, magnetism, AC-circuit, network and instrumentation set-ups of
the B.Sc. physics practical lists (DU / UGC LOCF), built on the rigs in `app/static/prayog/exp/`.

The four network-theorem set-ups are ONE panel and ONE netlist read four different ways, which is exactly what a
network-theorems trainer board is: two bench supplies E1 and E2 feed the junction through R1 and R2, R3 hangs
from the junction to earth, and the load branch is R4 in series with a decade load box RL. Kirchhoff's laws,
Thevenin, Norton, superposition and maximum power transfer are then four procedures on that one board, so they
share the rig `network-board` and need no new physics at all - the shared `circuit` kernel (modified nodal
analysis) solves the panel, and `packs/em_ug.py` carries only the hand-written textbook formulas each reading is
checked against.

The alternating-current set-ups use the new kernels in `packs/em_ug.py` (`lcr`, `rcfilter`, `acbridge`): the
circuit solver has no inductor and no sinusoidal source, and a lab's `cfg` may carry a netlist for the `circuit`
kernel alone, so that physics is done in phasor algebra there.

These labs carry no `table` block: the observation table and the result live in the rig's record book.
"""
from __future__ import annotations

import math
from typing import Any

from ..catalog import B, SIM, board, inst, knob, lab

PI = math.pi
UG = {"title": "B.Sc. (Honours) Physics practical syllabus, University of Delhi (LOCF 2019 / UGCF 2022), "
               "Electricity, Magnetism and Electronics laboratory lists"}
E24 = {"title": "IEC 60063: preferred number series for resistors and capacitors (E12 / E24 values)"}
NET_BOOK = {"title": "B. L. Theraja, A Textbook of Electrical Technology, Vol. I, chapter on network theorems"}
AC_BOOK = {"title": "A. K. Sawhney, A Course in Electrical and Electronic Measurements and Instrumentation, "
                    "chapters on alternating-current bridges and resonance"}


# ============================================================================== the network-theorems trainer panel
def _w(id: str, pts: list[list[float]], color: str = "red") -> dict:
    return B(id, "wire", pts=pts, r=0.0025, color=color)


def _net() -> dict:
    """One panel: E1 - R1 - junction - R2 - E2, R3 from the junction to earth, and the load branch R4 + RL.
    VM is the digital voltmeter permanently across the load terminals (10 MΩ, so it changes nothing)."""
    return {"nodes": 4, "els": [
        {"id": "V1", "kind": "V", "a": 1, "b": 0, "value": "E1"},
        {"id": "R1", "kind": "R", "a": 1, "b": 2, "value": "R1"},
        {"id": "V2", "kind": "V", "a": 3, "b": 0, "value": "E2"},
        {"id": "R2", "kind": "R", "a": 3, "b": 2, "value": "R2"},
        {"id": "R3", "kind": "R", "a": 2, "b": 0, "value": "R3"},
        {"id": "R4", "kind": "R", "a": 2, "b": 4, "value": "R4"},
        {"id": "RL", "kind": "R", "a": 4, "b": 0, "value": "RL"},
        {"id": "VM", "kind": "R", "a": 4, "b": 0, "value": 1e7}]}


def _panel_bodies() -> list[dict]:
    """The panel as LSL data. The studio rig draws the real trainer board; this is the plain fallback view."""
    out = [board(0.9, 0.5),
           B("panel", "box", name="Network theorems trainer panel",
             info="A laminate panel with the network printed on it, real resistors on the printed branches and "
                  "a brass test point at every node.", size=[0.78, 0.014, 0.36], pos=[0, 0.007, -0.1],
             color="#1d2b33"),
           B("rr1", "cylinder", name="Resistor R₁", r=0.008, h=0.05, pos=[-0.25, 0.024, -0.22],
             rot=[0, 0, 1.5708], color="#c9b07a"),
           B("rr2", "cylinder", name="Resistor R₂", r=0.008, h=0.05, pos=[0.25, 0.024, -0.22],
             rot=[0, 0, 1.5708], color="#c9b07a"),
           B("rr3", "cylinder", name="Resistor R₃", r=0.008, h=0.05, pos=[-0.08, 0.024, -0.1],
             color="#c9b07a"),
           B("rr4", "cylinder", name="Resistor R₄", r=0.008, h=0.05, pos=[0.08, 0.024, -0.14],
             color="#c9b07a"),
           B("tp1", "cylinder", name="Test point 1 (supply E₁)", r=0.006, h=0.012, pos=[-0.34, 0.02, -0.22],
             color="brass"),
           B("tp2", "cylinder", name="Test point 2 (the junction)", r=0.006, h=0.012, pos=[0, 0.02, -0.22],
             color="brass"),
           B("tp3", "cylinder", name="Test point 3 (supply E₂)", r=0.006, h=0.012, pos=[0.34, 0.02, -0.22],
             color="brass"),
           B("tp4", "cylinder", name="Load terminal", r=0.006, h=0.012, pos=[0.08, 0.02, -0.06],
             color="brass"),
           B("tp0", "cylinder", name="Earth rail test point", r=0.006, h=0.012, pos=[0, 0.02, 0.02],
             color="brass"),
           B("ps1", "box", name="Bench supply E₁", size=[0.12, 0.08, 0.1], pos=[-0.4, 0.04, -0.46],
             color="#3a4f6e"),
           B("ps2", "box", name="Bench supply E₂", size=[0.12, 0.08, 0.1], pos=[0.4, 0.04, -0.46],
             color="#3a4f6e"),
           B("lbox", "box", name="Decade load box R_L", info="The load: a four-dial resistance box.",
             size=[0.22, 0.06, 0.12], pos=[0.3, 0.03, 0.1], color="#2b2f36"),
           B("dmm", "box", name="Digital multimeter", info="Reads volts between any two test points, or the "
             "current in a branch when its shorting link is taken out.", size=[0.1, 0.035, 0.15],
             pos=[-0.3, 0.018, 0.1], color="#e0a93c"),
           _w("wl1", [[0.08, 0.026, -0.06], [0.18, 0.026, 0.06], [0.22, 0.026, 0.1]]),
           _w("wl2", [[0.0, 0.026, 0.02], [0.2, 0.026, 0.04], [0.38, 0.026, 0.1]], "black"),
           _w("wp1", [[-0.34, 0.026, -0.22], [-0.4, 0.026, -0.34], [-0.4, 0.026, -0.42]]),
           _w("wp2", [[0.34, 0.026, -0.22], [0.4, 0.026, -0.34], [0.4, 0.026, -0.42]]),
           ]
    return out


_NET_KNOBS = [knob("E1", "Bench supply E₁", "E1", 0, 15, 0.5, 6, "V"),
              knob("E2", "Bench supply E₂", "E2", 0, 15, 0.5, 4, "V"),
              knob("RL", "Decade load box R_L", "RL", 1, 200, 1, 50, "Ω"),
              knob("R1", "Panel resistor R₁ (hidden)", "R1", 5, 120, 1, 20, "Ω", hidden=True),
              knob("R2", "Panel resistor R₂ (hidden)", "R2", 5, 120, 1, 20, "Ω", hidden=True),
              knob("R3", "Panel resistor R₃ (hidden)", "R3", 5, 120, 1, 10, "Ω", hidden=True),
              knob("R4", "Panel resistor R₄ (hidden)", "R4", 5, 120, 1, 10, "Ω", hidden=True)]
_NET_INST = [inst("V", "readout", "Multimeter (volts)", "V_RL", unit="V", lc=0.001, digits=3),
             inst("IL", "readout", "Load current", "I_RL", unit="A", lc=0.0001, digits=4),
             inst("I3", "readout", "Current in R₃", "I_R3", unit="A", lc=0.0001, digits=4)]
_NET_PARAMS = {"E1": 6.0, "E2": 4.0, "R1": 20.0, "R2": 20.0, "R3": 10.0, "R4": 10.0, "RL": 50.0}
_NET_CAM = {"pos": [0.0, 1.05, 1.0], "look": [0, 0.02, -0.14]}
_NET_SAFETY = ("Keep both bench supplies below 15 V and switch them off before changing a lead. Never put the "
               "multimeter across a supply while it is set to read current: that is a short circuit through the "
               "meter. Take the shorting link out of a branch before plugging the ammeter into it.")


def _netlab(**kw) -> dict:
    d = dict(lsl=1, field="physics", lang="en-IN", rig="network-board",
             group="Physics · Networks", level="B.Sc. (UG)", topic="Network theorems",
             chapter="Network theorems and electrical skills", kernel="circuit", cfg={"net": _net()},
             params=dict(_NET_PARAMS), autorun=True, camera=dict(_NET_CAM), floor=-0.03,
             bodies=_panel_bodies(), knobs=[dict(k) for k in _NET_KNOBS],
             instruments=[dict(m) for m in _NET_INST], safety=_NET_SAFETY)
    d.update(kw)
    return d


def kirchhoff() -> dict:
    return _netlab(
        id="kirchhoff-laws", title="Verification of Kirchhoff's laws",
        aim="Measure every branch current and every branch voltage on the panel, test the junction rule and the "
            "loop rule against them, and find the hidden resistor R₃ from the laws.",
        steps=["Set the two bench supplies to 6 V and 4 V and the load box to 50 Ω.",
               "Take the shorting link out of branch R₁ and read the current in it with the ammeter; put the link back.",
               "Do the same for R₂, R₃ and R₄: four branch currents.",
               "Add the three currents that meet at the junction: the sum into it must equal the sum out of it.",
               "Read the voltage across R₁ and across R₃, and check that E₁ equals their sum (the loop rule).",
               "From the loop rule, R₃ = (E₁ − I₁R₁) / I₃."],
        theory="Kirchhoff's junction rule says the currents meeting at a junction add to zero, because charge "
               "does not pile up there. His loop rule says the potential differences round any closed loop add "
               "to zero, because the potential at a point has one value. On this panel the junction carries "
               "I₁ and I₂ in and I₃ and I₄ out, and the left loop gives E₁ = I₁R₁ + I₃R₃. Those two statements "
               "are enough to find any one unknown resistance in the panel from the measured currents.",
        tour=[{"say": "Two supplies feed the junction through R1 and R2. R3 goes from the junction to the earth rail and R4 feeds the load box."},
              {"set": {"E2": 0}, "say": "With the second supply turned down to zero its branch carries current the other way: the junction rule still holds."},
              {"set": {"E2": 4}, "say": "Both supplies on again. Add the currents at the junction: what goes in comes out."}],
        questions=[{"q": "The junction rule follows from", "options": ["Conservation of charge",
                    "Conservation of energy", "Ohm's law"], "answer": 0,
                    "why": "Charge cannot collect at a point of the circuit."},
                   {"q": "The loop rule follows from", "options": ["Conservation of energy",
                    "Conservation of charge", "Faraday's law"], "answer": 0,
                    "why": "Carrying a charge round a closed loop does no net work."}],
        sources=[UG, NET_BOOK, E24, SIM],
        check={"params": {"RL": 50.0}, "measure": {"mode": "value", "vars": ["I_R3"]},
               "reading": "I_R3", "textbook": "net_i3"},
    )


def thevenin_norton() -> dict:
    return _netlab(
        id="thevenin-norton", title="Thevenin's and Norton's theorems",
        aim="Measure the open-circuit voltage and the short-circuit current at the load terminals, work out the "
            "equivalent source, and check that it predicts the load current at any load.",
        steps=["Set the supplies to 6 V and 4 V.",
               "Take the load box off and read the open-circuit voltage across the load terminals: that is V_Th.",
               "Put the ammeter straight across the load terminals and read the short-circuit current: that is I_N.",
               "R_Th = V_Th / I_N, and the Norton source is the same I_N with R_N = R_Th in parallel.",
               "Put the load box back at several values, measure the load current each time, and compare it with "
               "V_Th / (R_Th + R_L)."],
        theory="Thevenin's theorem says that everything to the left of the load terminals, however many sources "
               "and resistances it holds, behaves at those terminals exactly like one source V_Th in series with "
               "one resistance R_Th. Norton's theorem is the same statement with a current source I_N in "
               "parallel with R_N. V_Th is the voltage the open terminals show, I_N the current they pass when "
               "shorted, and R_Th = R_N = V_Th / I_N. On this panel R_Th should come out as R₄ in series with "
               "R₁, R₂ and R₃ in parallel, because replacing a bench supply by a link is replacing it by its own "
               "(negligible) internal resistance.",
        tour=[{"say": "The load terminals are the two brass points on the load branch; everything behind them is the network we are replacing."},
              {"set": {"RL": 200}, "say": "With a very large load the terminals are almost open: the voltmeter is reading the Thevenin voltage."},
              {"set": {"RL": 1}, "say": "With a very small load almost the whole short-circuit current flows: that is the Norton current."}],
        questions=[{"q": "R_Th is found by", "options": ["V_Th divided by the short-circuit current",
                    "Adding every resistance in the network", "Measuring the load resistance"], "answer": 0,
                    "why": "The equivalent source's own resistance limits the short-circuit current."},
                   {"q": "In finding R_Th by calculation, an ideal voltage source in the network is",
                    "options": ["Replaced by a short circuit", "Left as it is", "Removed, leaving a gap"],
                    "answer": 0, "why": "Its internal resistance is zero, so it is replaced by a link."}],
        sources=[UG, NET_BOOK, E24, SIM],
        check={"params": {}, "rows": [
            {"set": {"RL": 1e9}, "measure": {"mode": "value", "vars": ["V_RL", "I_RL"]},
             "take": {"V_RL": "V", "I_RL": "I"}, "add": {"kind": 0}},
            {"set": {"RL": 1e-6}, "measure": {"mode": "value", "vars": ["V_RL", "I_RL"]},
             "take": {"V_RL": "V", "I_RL": "I"}, "add": {"kind": 1}}],
            "calc": "net_rth", "textbook": "net_rth"},
    )


def superposition() -> dict:
    return _netlab(
        id="superposition-theorem", title="Verification of the superposition theorem",
        aim="Measure the load current with both supplies on, then with each supply alone, and check that the two "
            "separate currents add up to the first.",
        steps=["Set the supplies to 6 V and 4 V and the load box to 50 Ω; read the load current.",
               "Turn the second supply down to zero (its branch is then just a link) and read the load current again.",
               "Turn the first supply down to zero and the second back to 4 V; read the load current.",
               "Add the last two readings and compare the sum with the first reading.",
               "Repeat at another load value: the theorem holds at every load, because the panel is linear."],
        theory="Every resistance in the panel obeys Ohm's law, so the whole network is linear: a current "
               "anywhere is a sum of terms, each proportional to one source. The superposition theorem is that "
               "statement in working form - the current in any branch with all the sources acting is the sum of "
               "the currents that each source would drive on its own, with every other source replaced by its "
               "internal resistance (a link for a voltage source). It is why a network can be taken apart one "
               "source at a time, and it is the reason Thevenin's theorem works at all.",
        tour=[{"say": "Both supplies on: the load box carries the current we are going to take apart."},
              {"set": {"E2": 0}, "say": "Second supply turned down to zero, its branch now a link: this is the first supply acting alone."},
              {"set": {"E1": 0, "E2": 4}, "say": "And now the second supply alone. The two currents should add up to the first reading."}],
        questions=[{"q": "Superposition holds because the network is", "options": ["Linear", "Symmetrical",
                    "At a steady temperature"], "answer": 0,
                    "why": "Every element's current is proportional to the voltage across it."},
                   {"q": "Superposition may NOT be used to add", "options": ["Powers", "Currents", "Voltages"],
                    "answer": 0, "why": "Power depends on the square of the current, which is not linear."}],
        sources=[UG, NET_BOOK, E24, SIM],
        check={"params": {"RL": 50.0}, "measure": {"mode": "value", "vars": ["I_RL"]},
               "reading": "I_RL", "textbook": "net_il"},
    )


def max_power() -> dict:
    return _netlab(
        id="max-power-transfer", title="Verification of the maximum power transfer theorem",
        aim="Change the load box over a wide range, work out the power it takes at each setting, and show that "
            "the power is greatest when the load equals the network's own resistance.",
        steps=["Set the supplies to 6 V and 4 V; take the load box off and read the open-circuit voltage.",
               "Put the load box back and read the load voltage at 2, 5, 10, 15, 20, 30, 50 and 100 Ω.",
               "Work out the power in the load at each setting from V²/R_L, and plot it against R_L.",
               "The curve has a flat maximum: read off the load at which it peaks.",
               "Each reading also gives the network's own resistance exactly, from R = R_L(V_oc/V − 1); the peak "
               "sits at that value."],
        theory="A source of open-circuit voltage V_oc and internal resistance R_Th drives a current "
               "V_oc/(R_Th + R_L) through a load R_L, so the load takes a power V_oc²R_L/(R_Th + R_L)². "
               "Differentiating with respect to R_L shows the power is greatest at R_L = R_Th, where exactly "
               "half the open-circuit voltage appears across the load and the efficiency is 50 per cent. A "
               "transmission line is therefore never matched, but a measuring instrument or an aerial is.",
        tour=[{"say": "The load box is the only thing we change. Everything behind the terminals stays as it is."},
              {"set": {"RL": 15}, "say": "At fifteen ohms the load voltage is half the open-circuit voltage: this is the matched load."},
              {"set": {"RL": 100}, "say": "At a hundred ohms the load voltage is higher but the current much smaller, so the power has fallen again."}],
        questions=[{"q": "At maximum power transfer the load voltage is", "options": [
            "Half the open-circuit voltage", "Equal to the open-circuit voltage", "A quarter of it"], "answer": 0,
            "why": "The load and the equivalent resistance are equal, so they divide the voltage equally."},
            {"q": "The efficiency at maximum power transfer is", "options": ["50 %", "100 %", "25 %"],
             "answer": 0, "why": "As much power is lost inside the source as reaches the load."}],
        sources=[UG, NET_BOOK, E24, SIM],
        check={"params": {"RL": 15.0}, "measure": {"mode": "value", "vars": ["V_RL"]},
               "reading": "V_RL", "textbook": "net_vl"},
    )


BUILDERS: tuple[Any, ...] = (kirchhoff, thevenin_norton, superposition, max_power)


# ============================================================================== the alternating-current bench
def _ac_bodies(extra: list[dict]) -> list[dict]:
    """The AC bench as LSL data. The studio rig `ac-bench` draws the real instruments; this is the plain view."""
    return [board(1.0, 0.56),
            B("fg", "box", name="Function generator", info="A sine generator with a frequency dial and a "
              "calibrated output. Its amplitude is held the same all through the experiment.",
              size=[0.2, 0.1, 0.14], pos=[-0.42, 0.05, -0.4], color="#5f646b"),
            B("fgs", "box", name="Generator display", size=[0.1, 0.002, 0.034], pos=[-0.42, 0.101, -0.44],
              color="#121214"),
            B("cro", "box", name="Oscilloscope", info="Two traces: the generator's own voltage and the voltage "
              "across the part being measured, so their sizes and their phase can both be read off the screen.",
              size=[0.3, 0.2, 0.26], pos=[0.18, 0.1, -0.42], color="#3c4149"),
            B("scr", "box", name="Screen", size=[0.17, 0.002, 0.13], pos=[0.14, 0.201, -0.42], color="#0d2a16"),
            B("mtr", "box", name="Alternating-current milliammeter", size=[0.12, 0.09, 0.1],
              pos=[-0.14, 0.045, -0.1], color="#17181b"),
            B("rbx", "box", name="Decade resistance box", size=[0.19, 0.05, 0.11], pos=[-0.38, 0.025, 0.05],
              color="#2b2f36"),
            B("lbx", "box", name="Decade inductance box", size=[0.19, 0.05, 0.11], pos=[-0.14, 0.025, 0.12],
              color="#2b2f36"),
            B("cbx", "box", name="Decade capacitance box", size=[0.19, 0.05, 0.11], pos=[0.1, 0.025, 0.12],
              color="#2b2f36"),
            _w("aw1", [[-0.34, 0.03, -0.34], [-0.3, 0.03, -0.12], [-0.2, 0.03, -0.08]]),
            _w("aw2", [[-0.08, 0.03, -0.08], [-0.1, 0.03, 0.04], [-0.14, 0.03, 0.07]], "black"),
            _w("aw3", [[-0.3, 0.03, 0.05], [-0.22, 0.03, 0.1], [-0.2, 0.03, 0.12]]),
            _w("aw4", [[-0.06, 0.03, 0.12], [0.0, 0.03, 0.12], [0.04, 0.03, 0.12]]),
            _w("aw5", [[0.18, 0.03, 0.12], [0.3, 0.03, -0.1], [0.22, 0.03, -0.3]], "black"),
            *extra]


_AC_SAFETY = ("The whole experiment runs on the function generator's own output, a volt or two: nothing here is "
              "at mains voltage. Keep the generator's amplitude the same for every reading, or the resonance "
              "curve means nothing, and do not short its output.")
_AC_CAM = {"pos": [0.0, 1.0, 1.0], "look": [0, 0.04, -0.16]}


def _aclab(**kw) -> dict:
    d = dict(lsl=1, field="physics", lang="en-IN", rig="ac-bench",
             group="Physics · AC circuits", level="B.Sc. (UG)", topic="Alternating-current circuits",
             chapter="AC circuits and bridges", autorun=True, camera=dict(_AC_CAM), floor=-0.03,
             safety=_AC_SAFETY)
    d.update(kw)
    return d


def series_resonance() -> dict:
    return _aclab(
        id="series-lcr-resonance", title="Series LCR resonance: frequency, Q and bandwidth",
        aim="Sweep the generator's frequency through resonance, plot the current against frequency, and find the "
            "resonant frequency, the unknown inductance, the half-power bandwidth and the quality factor.",
        kernel="lcr", params={"R": 47.0, "L": 0.022, "C": 4.7e-8, "f": 1000.0, "V": 1.0, "mode": 0.0},
        bodies=_ac_bodies([]),
        knobs=[knob("f", "Generator frequency", "f", 100, 20000, 10, 1000, "Hz"),
               knob("R", "Resistance in the circuit", "R", 5, 2000, 1, 47, "Ω"),
               knob("C", "Capacitance", "C", 0.001, 10, 0.001, 0.047, "µF", 1e-6),
               knob("V", "Generator amplitude", "V", 0.2, 5, 0.1, 1, "V"),
               knob("L", "Coil (L hidden)", "L", 0.1, 1000, 0.1, 22, "mH", 1e-3, hidden=True)],
        instruments=[inst("I", "readout", "Milliammeter", "I", k=1000, unit="mA", lc=0.01, digits=2),
                     inst("Z", "readout", "Impedance", "Z", unit="Ω", digits=1),
                     inst("gr", "graph", "Current against frequency", "I", k=1000, x="p.f", xlabel="f (Hz)",
                          dots=True)],
        steps=["Set the resistance box to 47 Ω and the capacitance box to 0.047 µF.",
               "Sweep the generator from a few hundred hertz upwards, reading the milliammeter at each setting.",
               "The current rises to a sharp maximum and falls again: that maximum is resonance.",
               "Take close readings either side of the peak to fix the resonant frequency.",
               "L = 1/(4π²f₀²C). Read the two frequencies at which the current is 1/√2 of its peak: their "
               "difference is the bandwidth, and Q = f₀ / bandwidth."],
        theory="In a series LCR circuit the inductive reactance 2πfL grows with frequency and the capacitive "
               "reactance 1/(2πfC) falls, so at one frequency they are equal and opposite and cancel. There the "
               "impedance is just R, the smallest it can be, and the current is greatest: that is series "
               "resonance, at f₀ = 1/(2π√(LC)). The current falls to 1/√2 of its peak (half the power) at two "
               "frequencies whose difference is R/(2πL), so the sharpness of the curve measures the coil: "
               "Q = f₀/Δf = (1/R)√(L/C). A series resonant circuit is an acceptor: at f₀ it offers the least "
               "opposition, which is how a receiver is tuned to one station.",
        tour=[{"say": "The generator, the milliammeter, the resistance box, the coil and the capacitor are all in one series loop."},
              {"set": {"f": 4950}, "say": "At about five kilohertz the current jumps: the two reactances have cancelled and only the resistance is left."},
              {"set": {"f": 12000}, "say": "Well above resonance the inductive reactance dominates and the current has fallen away again."}],
        questions=[{"q": "At series resonance the impedance is", "options": ["The smallest, and equal to R",
                    "The largest", "Zero"], "answer": 0, "why": "The two reactances cancel, leaving R alone."},
                   {"q": "A sharper resonance curve means", "options": ["A larger Q", "A larger R",
                    "A larger C"], "answer": 0, "why": "Q = f₀/Δf, so a narrow curve is a high Q."}],
        sources=[UG, AC_BOOK, E24, SIM],
        check={"params": {}, "reading": "fr", "textbook": "lcr_fr"},
    )


def parallel_resonance() -> dict:
    return _aclab(
        id="parallel-lcr-resonance", title="Parallel LCR circuit: anti-resonance and Q",
        aim="Put the coil in parallel with the capacitor, sweep the frequency, and find the anti-resonant "
            "frequency where the current drawn from the generator is least, with the dynamic impedance and Q.",
        kernel="lcr", params={"R": 22.0, "L": 0.047, "C": 1e-7, "f": 1000.0, "V": 1.0, "mode": 1.0},
        bodies=_ac_bodies([]),
        knobs=[knob("f", "Generator frequency", "f", 100, 20000, 10, 1000, "Hz"),
               knob("R", "Resistance of the coil", "R", 2, 500, 1, 22, "Ω"),
               knob("C", "Capacitance in parallel", "C", 0.001, 10, 0.001, 0.1, "µF", 1e-6),
               knob("V", "Generator amplitude", "V", 0.2, 5, 0.1, 1, "V"),
               knob("L", "Coil (L hidden)", "L", 0.1, 1000, 0.1, 47, "mH", 1e-3, hidden=True)],
        instruments=[inst("I", "readout", "Milliammeter (supply lead)", "I", k=1000, unit="mA", lc=0.001,
                          digits=3),
                     inst("Z", "readout", "Impedance of the combination", "Z", unit="Ω", digits=0),
                     inst("gr", "graph", "Supply current against frequency", "I", k=1000, x="p.f",
                          xlabel="f (Hz)", dots=True)],
        steps=["Join the coil and the capacitor in parallel across the generator, with the milliammeter in the "
               "supply lead.",
               "Sweep the frequency and read the current at each setting.",
               "The current falls to a minimum and rises again: that minimum is anti-resonance.",
               "Take close readings either side of it to fix the frequency.",
               "The impedance there is the dynamic impedance L/(CR), and Q = 2πf L/R."],
        theory="A coil and a capacitor in parallel across a generator carry currents in nearly opposite phase, "
               "so they largely cancel in the supply lead. At one frequency the cancellation is at its best: "
               "the impedance of the combination reaches its greatest value and the current drawn from the "
               "generator its least. This is anti-resonance, and a parallel circuit is therefore a rejector. "
               "With a real coil of resistance R the greatest impedance is about L/(CR), not infinite, and it "
               "sits very slightly below 1/(2π√(LC)); the familiar formula √(1/(LC) − R²/L²) is the frequency at "
               "which the combination behaves as a pure resistance, which is lower again.",
        tour=[{"say": "The coil and the capacitor now sit side by side across the generator, and the milliammeter is in the lead that feeds them both."},
              {"set": {"f": 2320}, "say": "At about two and a third kilohertz the current has fallen to almost nothing: the two branch currents are cancelling."},
              {"set": {"f": 8000}, "say": "Far above anti-resonance the capacitor takes a large current and the meter reads high again."}],
        questions=[{"q": "At anti-resonance the current drawn from the generator is", "options": [
            "The least", "The greatest", "Unchanged"], "answer": 0,
            "why": "The impedance of the combination is greatest there."},
            {"q": "The dynamic impedance of the parallel circuit is about", "options": ["L/(CR)", "R", "1/(CR)"],
             "answer": 0, "why": "The two branch currents cancel all but a small resistive part."}],
        sources=[UG, AC_BOOK, E24, SIM],
        check={"params": {}, "reading": "fr", "textbook": "lcr_far"},
    )


def series_rc() -> dict:
    return _aclab(
        id="series-rc-characteristics", title="Characteristics of a series RC circuit",
        aim="Measure the impedance and the phase of a series RC circuit over a wide range of frequency, and find "
            "the unknown capacitance from the frequency at which the reactance equals the resistance.",
        kernel="rcfilter", params={"R": 4700.0, "C": 2.2e-8, "f": 1000.0, "V": 1.0, "mode": 0.0},
        bodies=_ac_bodies([]),
        knobs=[knob("f", "Generator frequency", "f", 20, 50000, 10, 1000, "Hz"),
               knob("R", "Resistance in series", "R", 100, 100000, 100, 4700, "Ω"),
               knob("V", "Generator amplitude", "V", 0.2, 5, 0.1, 1, "V"),
               knob("C", "Capacitor (C hidden)", "C", 0.001, 10, 0.001, 0.022, "µF", 1e-6, hidden=True)],
        instruments=[inst("Zm", "readout", "Impedance", "Z", unit="Ω", digits=0),
                     inst("ph", "readout", "Phase of the current", "phase", k=57.29577951308232, unit="°",
                          digits=1),
                     inst("gr", "graph", "Output against frequency", "gain", x="p.f", xlabel="f (Hz)",
                          dots=True)],
        steps=["Put the resistance box and the capacitor in series across the generator, with the oscilloscope "
               "across the capacitor.",
               "At each frequency read the generator's own amplitude and the amplitude across the capacitor.",
               "Their ratio is the fraction of the applied voltage the capacitor keeps.",
               "The two are equal to 1/√2 at the frequency where the reactance equals the resistance.",
               "C = 1/(2πR f_c), and every single reading gives f_c on its own from the measured ratio."],
        theory="A resistance and a capacitance in series across an alternating supply divide the voltage in the "
               "ratio of their impedances, R and 1/(2πfC), and the current leads the applied voltage by "
               "arctan(1/(2πfCR)). At low frequency the reactance is large, so almost all the voltage is across "
               "the capacitor and the current leads by nearly 90 degrees; at high frequency the reactance is "
               "small, the resistance takes the voltage and the current is almost in phase. The two impedances "
               "are equal at f_c = 1/(2πRC), where the capacitor keeps 1/√2 = 0.707 of the applied voltage and "
               "the phase is 45 degrees. Measuring that frequency with a known resistance measures the "
               "capacitance.",
        tour=[{"say": "The resistance box and the capacitor are in series; the oscilloscope shows the generator's own voltage and the voltage across the capacitor."},
              {"set": {"f": 1540}, "say": "Here the two traces are in the ratio 0.707 and the phase is forty-five degrees: the reactance has become equal to the resistance."},
              {"set": {"f": 20000}, "say": "Far above that frequency the capacitor keeps almost nothing: it is nearly a short circuit to the alternating voltage."}],
        questions=[{"q": "At the cut-off frequency the output is", "options": ["0.707 of the input",
                    "Half the input", "Equal to the input"], "answer": 0,
                    "why": "The two impedances are equal, so the sum in quadrature gives a factor √2."},
                   {"q": "In a series RC circuit the current", "options": ["Leads the applied voltage",
                    "Lags it", "Is in phase with it"], "answer": 0,
                    "why": "The capacitor's current leads the voltage across it by 90 degrees."}],
        sources=[UG, AC_BOOK, E24, SIM],
        check={"params": {}, "reading": "fc", "textbook": "rc_fc"},
    )


def rc_response() -> dict:
    return _aclab(
        id="rc-frequency-response", title="Frequency response of an RC filter",
        aim="Measure the gain of an RC filter in decibels from well below to well above its cut-off, plot the "
            "response, and find the cut-off frequency and the roll-off.",
        kernel="rcfilter", params={"R": 10000.0, "C": 1e-8, "f": 1000.0, "V": 1.0, "mode": 0.0},
        bodies=_ac_bodies([]),
        knobs=[knob("f", "Generator frequency", "f", 20, 50000, 10, 1000, "Hz"),
               knob("R", "Resistance of the filter", "R", 100, 100000, 100, 10000, "Ω"),
               knob("V", "Generator amplitude", "V", 0.2, 5, 0.1, 1, "V"),
               knob("C", "Capacitor (C hidden)", "C", 0.001, 10, 0.001, 0.01, "µF", 1e-6, hidden=True)],
        instruments=[inst("g", "readout", "Output / input", "gain", digits=4),
                     inst("db", "readout", "Gain", "dB", unit="dB", digits=2),
                     inst("gr", "graph", "Gain against frequency", "dB", x="p.f", xlabel="f (Hz)", dots=True)],
        steps=["Build the filter: the resistance box and the capacitor in series, the output taken across one of "
               "them.",
               "Hold the generator's amplitude the same and read the output at frequencies spread over three "
               "decades.",
               "Work out the gain in decibels, 20 log(output/input), at each frequency.",
               "Plot the gain against the logarithm of the frequency: the response is flat in the pass band and "
               "falls in a straight line beyond the corner.",
               "The corner is where the gain has fallen by 3 dB; the slope beyond it is 20 dB per decade."],
        theory="An RC filter is a frequency-dependent potential divider. With the output across the capacitor "
               "the gain is 1/√(1 + (f/f_c)²): flat below the corner and falling as 1/f above it, which on a "
               "decibel against logarithm plot is a straight line of −20 dB per decade. With the output across "
               "the resistance the gain is (f/f_c)/√(1 + (f/f_c)²), the mirror image: a high-pass filter rising "
               "at 20 dB per decade and then flat. Either way the corner is at f_c = 1/(2πRC), where the gain "
               "is 1/√2, which is 3 dB down, and the phase shift is 45 degrees.",
        tour=[{"say": "The same two parts, but now we are interested in the output over three decades of frequency, not at one setting."},
              {"set": {"f": 1590}, "say": "This is the corner: three decibels down from the flat part of the response."},
              {"set": {"f": 16000}, "say": "A decade past the corner the output has fallen by a further twenty decibels: that is the roll-off."}],
        questions=[{"q": "Beyond its corner a single-section RC filter falls at", "options": [
            "20 dB per decade", "6 dB per decade", "40 dB per decade"], "answer": 0,
            "why": "The gain goes as 1/f, which is a factor of ten, or 20 dB, per decade."},
            {"q": "With the output taken across the resistance the filter is", "options": ["High-pass",
             "Low-pass", "Band-pass"], "answer": 0, "why": "The resistance keeps the voltage at high frequency."}],
        sources=[UG, AC_BOOK, E24, SIM],
        check={"params": {}, "reading": "fc", "textbook": "rc_fc"},
    )


BUILDERS = BUILDERS + (series_resonance, parallel_resonance, series_rc, rc_response)


# ============================================================================== alternating-current bridges
def _bridge_bodies() -> list[dict]:
    """The bridge bench as LSL data. The studio rig `ac-bridge` draws the real box."""
    return [board(0.95, 0.52),
            B("bbox", "box", name="Bridge box", info="A bakelite panel with the four arms of the bridge printed "
              "on it and a terminal pair for each arm.", size=[0.46, 0.05, 0.3], pos=[0, 0.025, -0.22],
              color="#17181b"),
            B("osc", "box", name="Audio oscillator (1 kHz)", info="Feeds one diagonal of the bridge at a few "
              "volts. Nothing here is at mains voltage.", size=[0.2, 0.1, 0.14], pos=[-0.46, 0.05, -0.4],
              color="#5f646b"),
            B("det", "box", name="Tuned detector", info="An amplifier and a null meter, with headphones. At "
              "balance the note dies away.", size=[0.17, 0.09, 0.13], pos=[0.42, 0.045, -0.38], color="#3c4149"),
            B("hp", "torus", name="Headphones", r=0.035, tube=0.008, pos=[0.42, 0.012, -0.12],
              rot=[-1.5708, 0, 0], color="black"),
            B("rdial", "box", name="Variable resistance arm", size=[0.19, 0.05, 0.11], pos=[-0.24, 0.025, 0.08],
              color="#2b2f36"),
            B("cdial", "box", name="Variable capacitance arm", size=[0.19, 0.05, 0.11], pos=[0.06, 0.025, 0.1],
              color="#2b2f36"),
            B("unk", "cylinder", name="The unknown", info="Clipped into the arm under test.", r=0.018, h=0.05,
              pos=[0.3, 0.025, 0.06], rot=[0, 0, 1.5708], color="#c9b07a"),
            _w("bw1", [[-0.38, 0.03, -0.34], [-0.3, 0.03, -0.26], [-0.2, 0.03, -0.22]]),
            _w("bw2", [[0.2, 0.03, -0.22], [0.34, 0.03, -0.3], [0.38, 0.03, -0.34]], "black"),
            _w("bw3", [[-0.16, 0.03, -0.1], [-0.2, 0.03, 0.02], [-0.24, 0.03, 0.04]]),
            _w("bw4", [[-0.14, 0.03, 0.08], [-0.04, 0.03, 0.1], [0.0, 0.03, 0.1]], "black"),
            _w("bw5", [[0.14, 0.03, 0.1], [0.24, 0.03, 0.08], [0.28, 0.03, 0.07]], "blue")]


_BR_SAFETY = ("Everything here runs from the audio oscillator at a few volts: nothing is at mains voltage. "
              "Turn the detector's gain down before listening, and keep the oscillator at one frequency while "
              "balancing, because the balance of a bridge with a coil in it is hunted with two dials at once.")


def _brlab(**kw) -> dict:
    d = dict(lsl=1, field="physics", lang="en-IN", rig="ac-bridge", group="Physics · AC bridges",
             level="B.Sc. (UG)", topic="Alternating-current bridges", chapter="AC circuits and bridges",
             kernel="acbridge", autorun=True, camera={"pos": [0.0, 0.95, 0.9], "look": [0, 0.04, -0.16]},
             floor=-0.03, bodies=_bridge_bodies(), safety=_BR_SAFETY)
    d.update(kw)
    return d


def de_sauty() -> dict:
    return _brlab(
        id="de-sauty-bridge", title="De Sauty's bridge: comparison of capacitances",
        aim="Balance a De Sauty bridge against a standard capacitor and find the unknown capacitance from the "
            "ratio of the two resistive arms.",
        cfg={"measure": {"param": "R2", "lo": 50.0, "hi": 50000.0}},
        params={"f": 1000.0, "V": 5.0, "Rg": 1000.0,
                "R1": 1000.0, "L1": 0.0, "C1": 0.0, "R2": 1000.0, "L2": 0.0, "C2": 0.0,
                "R3": 0.0, "L3": 0.0, "C3": 2.2e-7, "R4": 0.0, "L4": 0.0, "C4": 1e-7, "bal": 1000.0},
        knobs=[knob("R2", "Variable arm R₂", "R2", 50, 50000, 10, 1000, "Ω"),
               knob("R1", "Fixed ratio arm R₁", "R1", 100, 10000, 100, 1000, "Ω"),
               knob("f", "Oscillator frequency", "f", 200, 5000, 100, 1000, "Hz"),
               knob("C4", "Standard capacitor C₄", "C4", 0.001, 10, 0.001, 0.1, "µF", 1e-6),
               knob("C3", "Unknown capacitor (C₃ hidden)", "C3", 0.001, 10, 0.001, 0.22, "µF", 1e-6,
                    hidden=True)],
        instruments=[inst("G", "readout", "Detector current", "I_G", k=1e6, unit="µA", digits=2),
                     inst("Z3", "readout", "Reactance of the unknown arm", "Z3", unit="Ω", digits=0)],
        steps=["Clip the unknown capacitor into arm 3 and the standard capacitor into arm 4.",
               "Set the fixed ratio arm R₁ to 1000 Ω and switch the oscillator on at 1 kHz.",
               "Turn the variable arm R₂ while listening: the note in the headphones falls to its quietest at "
               "balance.",
               "Record R₂ at balance. C₃ = C₄ R₂ / R₁.",
               "Change R₁ and balance again: the answer must not change."],
        theory="A De Sauty bridge compares two capacitances directly. Two resistive arms R₁ and R₂ form one "
               "pair and the two capacitors the other, and the bridge balances when the products of opposite "
               "arms are equal: R₂ × (1/jωC₃) = R₁ × (1/jωC₄), which gives C₃ = C₄ R₂/R₁. The frequency has "
               "cancelled out, so the balance is the same at any frequency, and the comparison is as accurate "
               "as the standard capacitor and the two resistances. The simple form assumes both capacitors are "
               "loss-free; a real lossy capacitor needs resistances added in series with the arms (Grover's "
               "modification), and then the bridge also measures the loss angle.",
        tour=[{"say": "Two resistive arms on the left, the unknown capacitor and the standard capacitor on the right, the oscillator across one diagonal and the detector across the other."},
              {"set": {"R2": 2200}, "say": "At two thousand two hundred ohms the detector has gone quiet: the bridge is balanced."},
              {"set": {"R2": 4000}, "say": "Away from balance the note comes back at once, which is what makes a null method so sensitive."}],
        questions=[{"q": "At balance the De Sauty bridge gives", "options": ["C₃ = C₄ R₂ / R₁",
                    "C₃ = C₄ R₁ / R₂", "C₃ = C₄ R₁ R₂"], "answer": 0,
                    "why": "Equal products of opposite arms, with the capacitive reactances inversely as the "
                           "capacitances."},
                   {"q": "The balance of this bridge depends on the frequency", "options": ["Not at all",
                    "Directly", "As its square"], "answer": 0,
                    "why": "ω cancels from both sides of the balance equation."}],
        sources=[UG, AC_BOOK, E24, SIM],
        check={"params": {}, "reading": "R2", "textbook": "desauty_r2"},
    )


def owen_bridge() -> dict:
    return _brlab(
        id="owen-bridge", title="Owen's bridge: self-inductance of a coil",
        aim="Balance an Owen bridge with its two dials and find the self-inductance of a coil, and its "
            "resistance, from the standard capacitor and the two resistances.",
        cfg={"measure": {"param": "R2", "lo": 50.0, "hi": 50000.0,
                         "param2": "C2", "lo2": 1e-8, "hi2": 1e-5}},
        params={"f": 1000.0, "V": 5.0, "Rg": 1000.0,
                "R1": 20.0, "L1": 0.047, "C1": 0.0, "R2": 1000.0, "L2": 0.0, "C2": 1e-6,
                "R3": 500.0, "L3": 0.0, "C3": 0.0, "R4": 0.0, "L4": 0.0, "C4": 1e-7, "bal": 1000.0},
        knobs=[knob("R2", "Variable resistance dial R₂", "R2", 50, 50000, 10, 1000, "Ω"),
               knob("C2", "Variable capacitance dial C₂", "C2", 0.01, 10, 0.01, 1, "µF", 1e-6),
               knob("f", "Oscillator frequency", "f", 200, 5000, 100, 1000, "Hz"),
               knob("R3", "Fixed arm R₃", "R3", 100, 5000, 100, 500, "Ω"),
               knob("C4", "Standard capacitor C₄", "C4", 0.001, 10, 0.001, 0.1, "µF", 1e-6),
               knob("L1", "Coil (L₁ hidden)", "L1", 1, 1000, 1, 47, "mH", 1e-3, hidden=True),
               knob("R1", "Coil resistance (hidden)", "R1", 1, 500, 1, 20, "Ω", hidden=True)],
        instruments=[inst("G", "readout", "Detector current", "I_G", k=1e6, unit="µA", digits=2),
                     inst("Z1", "readout", "Impedance of the coil arm", "Z1", unit="Ω", digits=1)],
        steps=["Clip the coil into arm 1, the fixed resistance R₃ into arm 3 and the standard capacitor C₄ "
               "into arm 4.",
               "Switch the oscillator on at 1 kHz and turn the resistance dial R₂ for the quietest note.",
               "Now turn the capacitance dial C₂ for the quietest note, and go back to R₂ again.",
               "Two or three such rounds bring the detector to a true silence: that is the balance.",
               "L₁ = R₂ R₃ C₄ and the coil's own resistance R₁ = R₃ C₄ / C₂.",
               "Change the oscillator's frequency and balance again: the inductance must come out the same."],
        theory="Owen's bridge measures a self-inductance against a capacitance, with the coil in one arm and a "
               "resistance in series with a variable capacitor in the arm beside it. Equating the products of "
               "opposite arms, (R₂ − j/ωC₂) R₃ = (R₁ + jωL₁)(−j/ωC₄), and separating the real and imaginary "
               "parts gives L₁ = R₂ R₃ C₄ and R₁ = R₃ C₄ / C₂. Neither answer contains the frequency, which is "
               "the great advantage of this bridge: an imperfect oscillator or a harmonic in its output does "
               "not shift the balance. Because a coil has both resistance and reactance, two dials must be "
               "turned alternately: one kills the in-phase part of the detector current and the other the "
               "quadrature part, and neither alone can silence the detector.",
        tour=[{"say": "The coil is in the left arm, a resistance and a variable capacitor in the arm beside it, and the standard capacitor below."},
              {"set": {"R2": 940}, "say": "The resistance dial alone takes the note down but cannot kill it: there is still a quadrature current through the detector."},
              {"set": {"C2": 2.5}, "say": "Now the capacitance dial. With both dials set the detector is truly silent, and the bridge is balanced."}],
        questions=[{"q": "Owen's bridge needs two dials because", "options": [
            "A coil has resistance as well as reactance", "The oscillator drifts", "The detector is deaf"],
            "answer": 0, "why": "Both the real and the imaginary part of the detector current must be killed."},
            {"q": "The inductance found from Owen's bridge depends on the frequency", "options": ["Not at all",
             "Directly", "Inversely"], "answer": 0, "why": "L₁ = R₂R₃C₄ contains no ω."}],
        sources=[UG, AC_BOOK, E24, SIM],
        check={"params": {}, "reading": "R2", "textbook": "owen_r2"},
    )


BUILDERS = BUILDERS + (de_sauty, owen_bridge)
