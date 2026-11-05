"""Lab pack `elec11`: the Class XI / XII electricity, AC, optics and electronics set-ups of the CBSE / NCERT
laboratory manual that the first 22 labs did not cover (see `labs/__init__.py` and `docs/PRAYOG_STUDIO.md`).

Most of these need no new physics at all: the shared `circuit` kernel is a general modified-nodal-analysis solver
driven by `lab.cfg.net`, so a galvanometer bridge, a potentiometer wire and a conversion circuit are each just a
netlist plus knobs. The rest use the kernels in `packs/elec11.py`. Every lab names the studio RIG that draws it.

These labs carry no `table` block: their result is worked out by the studio rig (the observation table lives in the
rig's record book), not by one of the shared `CALCS` formulas.
"""
from __future__ import annotations

import math
from typing import Any

from ..catalog import B, S12, SIM, board, dial, inst, knob, lab, needle

DEG = math.pi / 180
MANUAL = {"title": "NCERT Laboratory Manual Physics Class XII, Section A (Current Electricity experiments)"}
MANUAL_B = {"title": "NCERT Laboratory Manual Physics Class XII, Section B (Optics and Semiconductor experiments)"}


def _w(id: str, pts: list[list[float]], color: str = "red") -> dict:
    return B(id, "wire", pts=pts, r=0.003, color=color)


def _decade(id: str, x: float, z: float, name: str, info: str = "") -> list[dict]:
    """A four-dial decade resistance box drawn as data (the rig draws the real one)."""
    out = [B(id, "box", name=name, info=info, size=[0.22, 0.06, 0.12], pos=[x, 0.03, z], color="#2b2f36"),
           B(id + "_top", "box", size=[0.2, 0.002, 0.1], pos=[x, 0.061, z], color="black")]
    for i in range(4):
        out.append(B(id + "_d%d" % i, "cylinder", r=0.018, h=0.008, pos=[x - 0.075 + i * 0.05, 0.066, z], color="brass"))
    return out


# ================================================================================================== galvanometer board
_GALV_BODIES_COMMON = [
    board(1.0, 0.6),
    B("bat", "cylinder", name="Battery", info="A steady source for the circuit.", r=0.028, h=0.11,
      pos=[-0.4, 0.028, 0.2], rot=[0, 0, 1.5708], color="#2b2f36"),
    B("key1", "box", name="Plug key K₁", size=[0.06, 0.02, 0.04], pos=[-0.18, 0.02, 0.22], color="black"),
    B("key1p", "cylinder", r=0.008, h=0.014, pos=[-0.18, 0.034, 0.22], color="brass"),
]


def _galv_views(extra: list[dict]) -> list[dict]:
    g = dial("g", [0.0, 0.0, -0.22], "Moving-coil galvanometer (30-0-30)",
             "A centre-zero galvanometer: the deflection is proportional to the current through its coil.")
    return list(_GALV_BODIES_COMMON) + g + [needle("gn", [0.0, 0.0, -0.22], "I_G", -2500.0)] + extra


def galv_half_deflection() -> dict:
    net = {"nodes": 4, "els": [
        {"id": "E", "kind": "V", "a": 1, "b": 0, "value": "Eb"},
        {"id": "K1", "kind": "S", "a": 1, "b": 2, "param": "k1"},
        {"id": "RH", "kind": "R", "a": 2, "b": 3, "value": "Rh"},
        {"id": "G", "kind": "R", "a": 3, "b": 0, "value": "Rg"},
        {"id": "SH", "kind": "R", "a": 3, "b": 4, "value": "Sh"},
        {"id": "K2", "kind": "S", "a": 4, "b": 0, "param": "k2"}]}
    return lab(
        id="galvanometer-half-deflection", rig="galvanometer-board",
        title="Galvanometer: resistance by half deflection", group="Physics · Electricity", level="Class XII",
        topic="Current Electricity", chapter="Current Electricity",
        aim="Find the resistance G of a moving-coil galvanometer by the half-deflection method, and its figure of merit.",
        kernel="circuit", cfg={"net": net},
        params={"Eb": 2.0, "Rh": 5000.0, "Rg": 60.0, "Sh": 59.0, "k1": 1.0, "k2": 0.0, "FOM": 1.6e-5},
        autorun=True, camera={"pos": [0.0, 0.8, 0.95], "look": [0, 0, -0.1]}, floor=-0.03,
        bodies=_galv_views(_decade("rh", -0.05, 0.2, "High resistance box R", "A four-dial box, 1 Ω to 9999 Ω.")
                           + _decade("sb", 0.33, -0.05, "Shunt resistance box S", "A three-dial box, 1 Ω to 999 Ω.")
                           + [B("key2", "box", name="Plug key K₂", size=[0.06, 0.02, 0.04], pos=[0.33, 0.02, 0.2], color="black"),
                              _w("w1", [[-0.37, 0.03, 0.2], [-0.21, 0.03, 0.22]]),
                              _w("w2", [[-0.15, 0.03, 0.22], [-0.05, 0.03, 0.26]]),
                              _w("w3", [[0.05, 0.03, 0.2], [0.05, 0.03, -0.1], [0.04, 0.03, -0.17]]),
                              _w("w4", [[-0.04, 0.03, -0.17], [-0.43, 0.03, -0.1], [-0.43, 0.03, 0.2]], "black"),
                              _w("w5", [[0.05, 0.03, -0.13], [0.33, 0.03, -0.11]], "#d9a520"),
                              _w("w6", [[0.33, 0.03, 0.01], [0.36, 0.03, 0.18]], "#d9a520")]),
        knobs=[knob("Rh", "High resistance box R", "Rh", 1000, 9999, 1, 5000, "Ω"),
               knob("Sh", "Shunt resistance box S", "Sh", 1, 999, 1, 59, "Ω"),
               knob("k1", "Key K₁ (0 open / 1 closed)", "k1", 0, 1, 1, 1),
               knob("k2", "Key K₂ (0 open / 1 closed)", "k2", 0, 1, 1, 0),
               knob("Rg", "Galvanometer (G hidden)", "Rg", 20, 200, 1, 60, "Ω", hidden=True)],
        instruments=[inst("d", "readout", "Galvanometer deflection", "I_G", k=62500.0, unit="div", digits=1),
                     inst("ig", "readout", "Current through the coil", "I_G", k=1e6, unit="µA", digits=1)],
        steps=["Close K₁ with K₂ open and set R so the deflection is nearly full scale. Note θ.",
               "Close K₂ and change the shunt box S until the deflection is exactly θ/2.",
               "Record R and S: G = RS / (R − S).",
               "Repeat with three or four other values of R.",
               "Figure of merit k = E / ((R + G) θ) ampere per division."],
        theory="With K₂ open the whole current passes through the galvanometer: θ ∝ E/(R + G). Closing K₂ puts the "
               "shunt S across the galvanometer. The deflection falls to half when the shunt carries half the "
               "current, that is when S equals the parallel combination of R and G, and then G = RS/(R − S). "
               "R must be large (a few thousand ohms) for this to hold; the current the galvanometer needs for one "
               "division, k = E/((R + G)θ), is its figure of merit.",
        safety="Keep R large before closing K₁: a bare galvanometer across a cell is destroyed at once. Open the keys "
               "between readings.",
        tour=[{"say": "Battery, key K₁, the high resistance box R and the galvanometer, all in series."},
              {"set": {"k2": 1}, "say": "Key K₂ closed: the shunt box S is now across the galvanometer and the deflection falls."}],
        questions=[{"q": "Why must R be large in this experiment?", "options": [
            "So that the current stays small and the half-deflection formula holds", "To heat the shunt",
            "So the galvanometer reads zero"], "answer": 0,
            "why": "G = RS/(R − S) assumes the current drawn from the cell hardly changes when the shunt is put in, which needs R ≫ G."},
            {"q": "The figure of merit of a galvanometer is", "options": [
                "The current needed for one division of deflection", "Its resistance", "Its full-scale deflection"],
             "answer": 0, "why": "k = I/θ, in ampere per division."}],
        sources=[S12, MANUAL, SIM],
        check={"params": {"k1": 1.0, "k2": 1.0, "Rh": 5000.0, "Sh": 100.0},
               "measure": {"mode": "value", "vars": ["I_G"]}, "reading": "I_G", "textbook": "galv_half_ig"},
    )


def galv_to_voltmeter() -> dict:
    net = {"nodes": 4, "els": [
        {"id": "E", "kind": "V", "a": 1, "b": 0, "value": "Eb"},
        {"id": "RI", "kind": "R", "a": 1, "b": 2, "value": "Rint"},
        {"id": "K1", "kind": "S", "a": 2, "b": 3, "param": "k1"},
        {"id": "RS", "kind": "R", "a": 3, "b": 4, "value": "Rser"},
        {"id": "G", "kind": "R", "a": 4, "b": 0, "value": "Rg"},
        {"id": "VM", "kind": "R", "a": 3, "b": 0, "value": 1e6}]}
    return lab(
        id="galvanometer-to-voltmeter", rig="galvanometer-board",
        title="Galvanometer into a voltmeter of a given range", group="Physics · Electricity", level="Class XII",
        topic="Current Electricity", chapter="Current Electricity",
        aim="Convert a galvanometer into a voltmeter of a chosen range by adding a high resistance in series, and verify it.",
        kernel="circuit", cfg={"net": net},
        params={"Eb": 1.0, "Rint": 2.0, "Rser": 6190.0, "Rg": 60.0, "k1": 1.0, "FOM": 1.6e-5, "Vrange": 3.0},
        autorun=True, camera={"pos": [0.0, 0.8, 0.95], "look": [0, 0, -0.1]}, floor=-0.03,
        bodies=_galv_views(_decade("rs", -0.05, 0.2, "High resistance box R", "The series resistance that makes the voltmeter.")
                           + dial("vm", [0.36, 0.0, -0.2], "Standard voltmeter (0-3 V)", "The meter the converted one is checked against.")
                           + [needle("vmn", [0.36, 0.0, -0.2], "V_VM", 0.8),
                              B("psu", "box", name="Variable DC supply", size=[0.2, 0.07, 0.12], pos=[-0.4, 0.035, 0.18], color="#3a4f6e"),
                              _w("w1", [[-0.32, 0.03, 0.2], [-0.15, 0.03, 0.22]]),
                              _w("w2", [[0.05, 0.03, 0.2], [0.04, 0.03, -0.17]]),
                              _w("w3", [[-0.04, 0.03, -0.17], [-0.44, 0.03, -0.08], [-0.44, 0.03, 0.16]], "black"),
                              _w("w4", [[0.06, 0.03, -0.15], [0.32, 0.03, -0.15]], "#d9a520"),
                              _w("w5", [[0.4, 0.03, -0.15], [0.46, 0.03, 0.1], [-0.44, 0.03, 0.14]], "blue")]),
        knobs=[knob("Eb", "Supply voltage", "Eb", 0, 3, 0.05, 1, "V"),
               knob("Rser", "Series resistance box R", "Rser", 100, 9999, 1, 6190, "Ω"),
               knob("k1", "Key K₁ (0 open / 1 closed)", "k1", 0, 1, 1, 1),
               knob("Rg", "Galvanometer (G hidden)", "Rg", 20, 200, 1, 60, "Ω", hidden=True)],
        instruments=[inst("d", "readout", "Galvanometer deflection", "I_G", k=62500.0, unit="div", digits=1),
                     inst("vs", "readout", "Standard voltmeter", "V_VM", unit="V", lc=0.01, digits=2)],
        steps=["Work out the full-scale current of the galvanometer: Iɢ = k × 30 divisions.",
               "Work out the series resistance for the range you want: R = V/Iɢ − G.",
               "Set that value on the high resistance box and join it in series with the galvanometer.",
               "Apply a few voltages and read the standard voltmeter and the deflection each time.",
               "The deflection should be proportional to the voltage, and 30 divisions should mean the full range."],
        theory="A galvanometer is already a voltmeter of a very small range: the voltage across it at full-scale "
               "deflection is only Iɢ G. Adding a high resistance R in series makes the same full-scale current flow "
               "at a larger voltage V = Iɢ (G + R), so R = V/Iɢ − G. The converted meter is verified against a "
               "standard voltmeter: the plot of the standard reading against the deflection is a straight line "
               "through the origin, and its slope times 30 divisions is the real range.",
        safety="Set the series resistance before switching the supply on, and never apply more than the designed range.",
        tour=[{"say": "The galvanometer with the high resistance box in series is the converted voltmeter; the standard voltmeter is across the same two points."},
              {"set": {"Eb": 2.0}, "say": "Two volts applied: both meters move together."}],
        questions=[{"q": "To increase a voltmeter's range you", "options": [
            "Add a high resistance in series", "Add a low resistance in parallel", "Change the coil"], "answer": 0,
            "why": "R = V/Iɢ − G, in series."},
            {"q": "An ideal voltmeter has", "options": ["Infinite resistance", "Zero resistance", "The coil's resistance"],
             "answer": 0, "why": "So that it draws no current from the circuit it measures."}],
        sources=[S12, MANUAL, SIM],
        check={"params": {"k1": 1.0, "Eb": 2.0}, "measure": {"mode": "value", "vars": ["I_G"]},
               "reading": "I_G", "textbook": "galv_volt_ig"},
    )


def galv_to_ammeter() -> dict:
    net = {"nodes": 4, "els": [
        {"id": "E", "kind": "V", "a": 1, "b": 0, "value": "Eb"},
        {"id": "K1", "kind": "S", "a": 1, "b": 2, "param": "k1"},
        {"id": "RL", "kind": "R", "a": 2, "b": 3, "value": "Rl"},
        {"id": "AM", "kind": "R", "a": 3, "b": 4, "value": "Ram"},
        {"id": "G", "kind": "R", "a": 4, "b": 0, "value": "Rg"},
        {"id": "SH", "kind": "R", "a": 4, "b": 0, "value": "Sht"}]}
    return lab(
        id="galvanometer-to-ammeter", rig="galvanometer-board",
        title="Galvanometer into an ammeter of a given range", group="Physics · Electricity", level="Class XII",
        topic="Current Electricity", chapter="Current Electricity",
        aim="Convert a galvanometer into an ammeter of a chosen range with a shunt wire, and verify it against a standard ammeter.",
        kernel="circuit", cfg={"net": net},
        params={"Eb": 6.0, "Rl": 20.0, "Ram": 0.05, "Rg": 60.0, "Sht": 0.058, "k1": 1.0, "FOM": 1.6e-5,
                "Irange": 0.5, "lam": 1.209},
        autorun=True, camera={"pos": [0.0, 0.8, 0.95], "look": [0, 0, -0.1]}, floor=-0.03,
        bodies=_galv_views([
            B("rheo", "cylinder", name="Rheostat (load)", info="Changes the current in the circuit.", r=0.025, h=0.22,
              pos=[-0.1, 0.03, 0.22], rot=[0, 0, 1.5708], color="#c9b07a"),
            B("shb", "box", name="Shunt wire board", info="A thick manganin wire; a sliding contact sets its length.",
              size=[0.2, 0.014, 0.06], pos=[0.3, 0.007, -0.02], color="wood"),
            B("shw", "cylinder", name="Shunt wire", r=0.0005, h=0.16, pos=[0.3, 0.018, -0.02], rot=[0, 0, 1.5708], color="copper"),
            B("shc", "box", name="Sliding contact", size=[0.012, 0.02, 0.03], pos=[0.26, 0.024, -0.02], color="brass"),
            *dial("am", [0.36, 0.0, 0.18], "Standard ammeter (0-0.5 A)", "The meter the converted one is checked against."),
            needle("amn", [0.36, 0.0, 0.18], "I_AM", 4.0),
            _w("w1", [[-0.37, 0.03, 0.2], [-0.21, 0.03, 0.22]]),
            _w("w2", [[0.01, 0.03, 0.22], [0.3, 0.03, 0.14]]),
            _w("w3", [[0.36, 0.03, 0.26], [0.1, 0.03, -0.05], [0.04, 0.03, -0.17]], "#d9a520"),
            _w("w4", [[-0.04, 0.03, -0.17], [-0.43, 0.03, -0.1], [-0.43, 0.03, 0.2]], "black"),
            _w("w5", [[0.22, 0.03, -0.02], [0.05, 0.03, -0.14]], "blue"),
            _w("w6", [[0.38, 0.03, -0.02], [0.2, 0.03, -0.1], [-0.42, 0.03, -0.14]], "blue")]),
        knobs=[knob("Rl", "Rheostat (load)", "Rl", 12, 60, 0.5, 20, "Ω"),
               knob("ls", "Shunt wire length l", "Sht", 1, 10, 0.1, 4.8, "cm", 0.01209),
               knob("k1", "Key K₁ (0 open / 1 closed)", "k1", 0, 1, 1, 1),
               knob("Rg", "Galvanometer (G hidden)", "Rg", 20, 200, 1, 60, "Ω", hidden=True)],
        instruments=[inst("d", "readout", "Galvanometer deflection", "I_G", k=62500.0, unit="div", digits=1),
                     inst("as", "readout", "Standard ammeter", "I_AM", unit="A", lc=0.01, digits=3)],
        steps=["Work out the full-scale current of the galvanometer: Iɢ = k × 30 divisions.",
               "Work out the shunt for the range you want: S = G Iɢ / (I − Iɢ).",
               "Set that length of the manganin shunt wire across the galvanometer (1.209 Ω per metre).",
               "Change the rheostat and read the standard ammeter and the deflection each time.",
               "The slope of the standard current against the deflection, times 30 divisions, is the real range."],
        theory="A galvanometer takes only its small full-scale current Iɢ. A low resistance S in parallel (a shunt) "
               "carries the rest, so a much larger line current I gives full-scale deflection: S = G Iɢ / (I − Iɢ). "
               "The shunt also lowers the meter's own resistance to GS/(G + S), which is what an ammeter needs. The "
               "converted meter is verified against a standard ammeter in series with it.",
        safety="Keep the rheostat at its highest resistance when the key is closed, and never leave the circuit on.",
        tour=[{"say": "The shunt wire is across the galvanometer; the standard ammeter is in series with the pair."},
              {"set": {"Rl": 50}, "say": "More resistance in the circuit: both the line current and the deflection fall together."}],
        questions=[{"q": "A shunt is", "options": ["A low resistance in parallel with the galvanometer",
                                                   "A high resistance in series", "A second cell"], "answer": 0,
                    "why": "It carries the current the coil cannot take."},
                   {"q": "After shunting, the meter's resistance is", "options": ["GS/(G + S), which is small",
                                                                                 "G + S", "Unchanged"], "answer": 0,
                    "why": "The two are in parallel, so an ammeter hardly disturbs the circuit."}],
        sources=[S12, MANUAL, SIM],
        check={"params": {"k1": 1.0}, "measure": {"mode": "value", "vars": ["I_G"]},
               "reading": "I_G", "textbook": "galv_amm_ig"},
    )



# ================================================================================================ potentiometer board
def _pot_bodies(extra: list[dict]) -> list[dict]:
    return [
        board(1.25, 0.6),
        B("wire", "rope", name="Potentiometer wire (1 m)", info="A uniform manganin wire of about 4 Ω end to end.",
          a=[-0.5, 0.014, -0.32], b=[0.5, 0.014, -0.32], r=0.0012, color="steel"),
        B("ruler", "scale", name="Metre scale", length=1.0, spacing=0.01, major=10, labels=True, label_step=10,
          tick=0.012, font=0.02, pos=[-0.5, 0.003, -0.27], rot=[-1.5708, 0, 0]),
        B("jockey", "cone", name="Jockey", info="Touch the wire lightly where the galvanometer reads zero.",
          r=0.01, h=0.05, pos=[-0.5, 0.042, -0.32], rot=[3.1416, 0, 0], color="brass", bind={"x": "p.lj"}),
        B("drv", "cylinder", name="Driver battery (6 V)", r=0.03, h=0.12, pos=[-0.45, 0.03, -0.62],
          rot=[0, 0, 1.5708], color="#2b2f36"),
        B("rh", "cylinder", name="Rheostat", info="Sets the current in the wire, and so the potential gradient.",
          r=0.025, h=0.24, pos=[0.0, 0.03, -0.62], rot=[0, 0, 1.5708], color="#c9b07a"),
        B("key1", "box", name="Plug key K₁", size=[0.06, 0.02, 0.04], pos=[0.38, 0.02, -0.62], color="black"),
        _w("d1", [[-0.39, 0.03, -0.62], [-0.13, 0.03, -0.62]]),
        _w("d2", [[0.13, 0.03, -0.62], [0.35, 0.03, -0.62]]),
        _w("d3", [[0.41, 0.03, -0.62], [0.56, 0.03, -0.5], [0.5, 0.03, -0.32]]),
        _w("d4", [[-0.5, 0.03, -0.32], [-0.56, 0.03, -0.5], [-0.51, 0.03, -0.62]], "black"),
    ] + extra


def pot_compare_emf() -> dict:
    net = {"nodes": 6, "els": [
        {"id": "E0", "kind": "V", "a": 3, "b": 0, "value": "E0"},
        {"id": "RH", "kind": "R", "a": 3, "b": 1, "value": "Rh"},
        {"id": "WA", "kind": "R", "a": 1, "b": 2, "value": {"param": "lj", "k": 4.0}},
        {"id": "WB", "kind": "R", "a": 2, "b": 0, "value": {"param": "lj", "k": -4.0, "c": 4.0}},
        {"id": "EC1", "kind": "V", "a": 1, "b": 4, "value": "Ec"},
        {"id": "SW1", "kind": "S", "a": 4, "b": 5, "param": "sw1"},
        {"id": "EC2", "kind": "V", "a": 1, "b": 6, "value": "Ec2"},
        {"id": "SW2", "kind": "S", "a": 6, "b": 5, "param": "sw2"},
        {"id": "G", "kind": "R", "a": 5, "b": 2, "value": 50.0}]}
    return lab(
        id="potentiometer-compare-emf", rig="potentiometer-board",
        title="Potentiometer: comparing the emfs of two cells", group="Physics · Electricity", level="Class XII",
        topic="Current Electricity", chapter="Current Electricity",
        aim="Find the balancing length of each of two primary cells on a potentiometer and compare their emfs: E₁/E₂ = l₁/l₂.",
        kernel="circuit", cfg={"net": net},
        params={"E0": 6.0, "Rh": 2.0, "Rw": 4.0, "lj": 0.3, "Ec": 1.5, "Ec2": 1.08, "sw1": 1.0, "sw2": 0.0,
                "FOM": 1.6e-5},
        autorun=True, camera={"pos": [0.0, 0.85, 0.8], "look": [0, 0, -0.2]}, floor=-0.03,
        bodies=_pot_bodies([
            B("twk", "box", name="Two-way key", info="One plug for each cell: only one cell is in the circuit at a time.",
              size=[0.1, 0.022, 0.05], pos=[-0.08, 0.022, 0.04], color="black"),
            B("c1", "cylinder", name="Cell 1 (Leclanché, 1.5 V)", r=0.03, h=0.09, pos=[0.16, 0.045, -0.04], color="glass", opacity=0.4),
            B("c1r", "cylinder", name="Carbon rod", r=0.005, h=0.11, pos=[0.16, 0.055, -0.04], color="black"),
            B("c2", "cylinder", name="Cell 2 (Daniell, 1.08 V)", r=0.03, h=0.09, pos=[0.16, 0.045, 0.1], color="glass", opacity=0.4),
            B("c2r", "cylinder", name="Copper rod", r=0.005, h=0.11, pos=[0.16, 0.055, 0.1], color="copper"),
            *dial("g", [-0.42, 0.0, 0.02], "Galvanometer", "At the balance point no current flows from the cell."),
            needle("gn", [-0.42, 0.0, 0.02], "I_G", -40000.0),
            _w("g1", [[-0.42, 0.03, 0.08], [-0.13, 0.03, 0.05]], "blue"),
            _w("g2", [[-0.38, 0.03, -0.02], [-0.3, 0.03, -0.3]], "blue"),
            _w("c1w", [[0.13, 0.03, -0.04], [-0.04, 0.03, 0.03]], "#d9a520"),
            _w("c2w", [[0.13, 0.03, 0.1], [-0.03, 0.03, 0.06]], "#d9a520"),
        ]),
        knobs=[knob("lj", "Jockey position l", "lj", 1, 99, 0.1, 30, "cm", 0.01),
               knob("sw1", "Plug for cell 1 (0 out / 1 in)", "sw1", 0, 1, 1, 1),
               knob("sw2", "Plug for cell 2 (0 out / 1 in)", "sw2", 0, 1, 1, 0),
               knob("Rh", "Rheostat", "Rh", 1, 10, 0.5, 2, "Ω"),
               knob("Ec2", "Second cell (emf hidden)", "Ec2", 0.8, 1.45, 0.01, 1.08, "V", hidden=True)],
        instruments=[inst("G", "readout", "Galvanometer", "I_G", k=1e6, unit="µA", digits=1)],
        steps=["Close K₁ so a steady current flows through the potentiometer wire.",
               "Put the plug in for cell 1 only. Slide the jockey until the galvanometer reads zero: that is l₁.",
               "Take the plug out, put in the plug for cell 2, and find l₂ the same way.",
               "Change the rheostat a little and repeat both.",
               "E₁/E₂ = l₁/l₂. If E₁ is known, E₂ follows."],
        theory="The driver cell sends a steady current through the whole potentiometer wire, so the potential falls "
               "uniformly along it: the drop across a length l is k l, where k is the potential gradient. At the "
               "balance point the galvanometer reads zero, no current flows from the cell under test, and the cell's "
               "full emf equals k l. Because k is the same for both cells, E₁/E₂ = l₁/l₂ and the gradient itself "
               "never has to be measured. The driver emf must be larger than either cell, or there is no balance "
               "point on the wire.",
        safety="Touch the jockey gently and never drag it along the wire: scraping changes the wire's resistance. "
               "Only one plug of the two-way key may be in at a time.",
        tour=[{"say": "A steady current runs along the potentiometer wire. The cell under test is joined through the galvanometer to the jockey."},
              {"set": {"lj": 37.5}, "say": "At about 37 centimetres the galvanometer reads zero: the cell's emf equals the drop along that length."},
              {"set": {"sw1": 0, "sw2": 1}, "say": "Now the second cell is in the circuit: its balance point is at a shorter length, so its emf is smaller."}],
        questions=[{"q": "At the balance point the current drawn from the cell under test is",
                    "options": ["Zero", "The largest", "Equal to the driver's current"], "answer": 0,
                    "why": "That is why a potentiometer measures the emf and not the terminal voltage."},
                   {"q": "If the driver emf is less than the cell being tested", "options": [
                       "No balance point is found on the wire", "The balance comes at the far end", "Nothing changes"],
                    "answer": 0, "why": "The drop along the whole wire would still be less than the cell's emf."}],
        sources=[S12, MANUAL, SIM],
        check={"params": {"sw1": 1.0, "sw2": 0.0},
               "measure": {"mode": "null", "param": "lj", "var": "I_G", "lo": 0.01, "hi": 0.99},
               "reading": "lj", "textbook": "pot_balance"},
    )


def pot_potential_drop() -> dict:
    net = {"nodes": 4, "els": [
        {"id": "E0", "kind": "V", "a": 3, "b": 0, "value": "E0"},
        {"id": "K1", "kind": "S", "a": 3, "b": 4, "param": "key"},
        {"id": "RH", "kind": "R", "a": 4, "b": 1, "value": "Rh"},
        {"id": "WA", "kind": "R", "a": 1, "b": 2, "value": {"param": "lj", "k": 4.0}},
        {"id": "WB", "kind": "R", "a": 2, "b": 0, "value": {"param": "lj", "k": -4.0, "c": 4.0}},
        {"id": "VM", "kind": "R", "a": 1, "b": 2, "value": 1e6}]}
    return lab(
        id="potential-drop-with-length", rig="potentiometer-board",
        title="Potential drop along a wire carrying a steady current", group="Physics · Electricity", level="Class XII",
        topic="Current Electricity", chapter="Current Electricity",
        aim="Measure the potential difference across different lengths of a wire carrying a steady current and find the potential gradient.",
        kernel="circuit", cfg={"net": net},
        params={"E0": 6.0, "Rh": 6.0, "Rw": 4.0, "lj": 0.5, "key": 1.0},
        autorun=True, camera={"pos": [0.0, 0.85, 0.8], "look": [0, 0, -0.2]}, floor=-0.03,
        bodies=_pot_bodies([
            *dial("vm", [-0.42, 0.0, 0.02], "Voltmeter (0-3 V)", "Reads the potential difference between end A and the jockey."),
            needle("vmn", [-0.42, 0.0, 0.02], "V_VM", 0.8),
            _w("v1", [[-0.42, 0.03, 0.08], [-0.5, 0.03, -0.26]], "blue"),
            _w("v2", [[-0.38, 0.03, -0.02], [-0.3, 0.03, -0.3]], "blue"),
        ]),
        knobs=[knob("lj", "Jockey position l", "lj", 1, 99, 0.1, 50, "cm", 0.01),
               knob("key", "Key K₁ (0 open / 1 closed)", "key", 0, 1, 1, 1),
               knob("Rh", "Rheostat (sets the current)", "Rh", 2, 12, 0.5, 6, "Ω")],
        instruments=[inst("V", "readout", "Voltmeter", "V_VM", unit="V", lc=0.02, digits=2),
                     inst("gr", "graph", "V against l", "V_VM", x="p.lj", xk=100.0, xlabel="l (cm)", dots=True)],
        steps=["Close K₁ so a steady current flows along the whole wire.",
               "Touch the jockey at 20 cm and read the voltmeter.",
               "Repeat at 40, 55, 70 and 90 cm.",
               "Plot V against l: a straight line through the origin.",
               "Its slope is the potential gradient, in volts per metre."],
        theory="A uniform wire carrying a steady current has the same resistance per unit length everywhere, so the "
               "potential falls uniformly along it: V = I R l / L, which is a straight line through the origin. The "
               "slope V/l is the potential gradient, the quantity every potentiometer measurement depends on. Making "
               "the current smaller with the rheostat makes the gradient smaller, so a longer length is needed for "
               "the same potential difference.",
        safety="Close the key only while reading, and touch the jockey gently on the wire.",
        tour=[{"say": "A steady current flows along the whole wire; the voltmeter reads the drop from end A to the jockey."},
              {"set": {"lj": 90}, "say": "Near the far end of the wire the voltmeter reads the drop across almost the whole metre."},
              {"set": {"Rh": 12}, "say": "More resistance in series: a smaller current, so a smaller drop across the same length."}],
        questions=[{"q": "The graph of V against l for a uniform wire is", "options": [
            "A straight line through the origin", "A curve", "A horizontal line"], "answer": 0,
            "why": "V = (I R / L) l, and I R / L is constant."},
            {"q": "If the current is halved, the potential gradient", "options": ["Is halved", "Doubles", "Is unchanged"],
             "answer": 0, "why": "The gradient is I R / L, proportional to the current."}],
        sources=[S12, MANUAL, SIM],
        check={"params": {"key": 1.0, "lj": 0.5}, "measure": {"mode": "value", "vars": ["V_VM"]},
               "reading": "V_VM", "textbook": "pot_drop"},
    )


BUILDERS: tuple[Any, ...] = (galv_half_deflection, galv_to_voltmeter, galv_to_ammeter,
                             pot_compare_emf, pot_potential_drop)
