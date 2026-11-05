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
