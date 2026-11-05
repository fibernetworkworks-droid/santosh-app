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
R2D = 180 / math.pi
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


# ============================================================================================== semiconductor board
def _semi_bodies(extra: list[dict]) -> list[dict]:
    return [
        board(1.0, 0.6),
        B("bb", "box", name="Breadboard", info="The components are pushed into its rows of contacts.",
          size=[0.3, 0.012, 0.16], pos=[0.0, 0.006, -0.02], color="white"),
        B("psu", "box", name="Variable DC power supply", info="Turn the knob to change the voltage applied to the circuit.",
          size=[0.22, 0.1, 0.14], pos=[-0.4, 0.05, -0.3], color="#3a4f6e"),
        B("psuk", "cylinder", name="Voltage knob", r=0.018, h=0.012, pos=[-0.44, 0.085, -0.235], rot=[1.5708, 0, 0], color="black"),
    ] + extra


def zener_characteristic() -> dict:
    return lab(
        id="zener-characteristic", rig="semiconductor-board",
        title="Zener diode: reverse characteristic and breakdown", group="Physics · Electronics", level="Class XII",
        topic="Semiconductor Electronics", chapter="Semiconductor Electronics",
        aim="Draw the characteristic of a Zener diode in reverse bias and find its breakdown voltage.",
        kernel="zener",
        params={"Eb": -1.0, "Rs": 1000.0, "Vz": 5.1, "Rz": 10.0, "Is": 5e-9, "nD": 1.8, "knee": 0.02},
        autorun=True, camera={"pos": [0.0, 0.7, 0.72], "look": [0, 0, -0.12]}, floor=-0.03,
        bodies=_semi_bodies([
            B("zd", "cylinder", name="Zener diode", info="The band marks the cathode. In this experiment it faces the + side: reverse bias.",
              r=0.004, h=0.018, pos=[0.02, 0.018, -0.02], rot=[0, 0, 1.5708], color="black"),
            B("zdb", "cylinder", r=0.0043, h=0.003, pos=[0.012, 0.018, -0.02], rot=[0, 0, 1.5708], color="white"),
            B("rs", "box", name="Series resistor (1 kΩ)", info="Limits the current so the diode is not destroyed.",
              size=[0.018, 0.006, 0.006], pos=[-0.1, 0.018, -0.02], color="#d9b46a"),
            *dial("vm", [0.18, 0.0, -0.3], "Voltmeter (0-10 V)", "Across the Zener diode."),
            needle("vmn", [0.18, 0.0, -0.3], "V_Z", -0.22),
            *dial("ma", [-0.14, 0.0, -0.3], "Milliammeter (0-25 mA)", "In series with the diode."),
            needle("man", [-0.14, 0.0, -0.3], "I_Z", -120.0),
            _w("w1", [[-0.3, 0.02, -0.26], [-0.11, 0.02, -0.04]]),
            _w("w2", [[-0.09, 0.02, -0.02], [0.0, 0.02, -0.02]]),
            _w("w3", [[0.04, 0.02, -0.02], [0.16, 0.02, -0.24]], "#d9a520"),
            _w("w4", [[0.0, 0.02, 0.04], [-0.12, 0.02, -0.24]], "blue"),
        ]),
        knobs=[knob("Eb", "Applied voltage (negative = reverse bias)", "Eb", -12, 3, 0.1, -1, "V"),
               knob("Vz", "Diode (breakdown voltage hidden)", "Vz", 2.5, 10, 0.1, 5.1, "V", hidden=True)],
        instruments=[inst("V", "readout", "Voltage across the diode", "V_Z", unit="V", lc=0.05, digits=2),
                     inst("I", "readout", "Current", "I_Z", k=1000.0, unit="mA", digits=2),
                     inst("gr", "graph", "I against V", "I_Z", k=1000.0, x="V_Z", xlabel="V (V)", dots=True)],
        steps=["Join the diode in reverse bias: the banded end (cathode) to the + terminal.",
               "Raise the supply from 0 in steps of 1 V and record V and I each time.",
               "Below the breakdown voltage the current is only a few microamperes.",
               "Past breakdown the current rises steeply while V hardly changes.",
               "The intercept of the steep part on the voltage axis is the breakdown voltage Vz."],
        theory="A Zener diode is made with heavily doped sides, so in reverse bias it breaks down at a low, sharply "
               "defined voltage. Below that voltage only the tiny leakage current flows. Past it the current rises "
               "steeply while the voltage across the diode stays almost constant, which is what makes a Zener diode "
               "a voltage regulator. On the steep part V = Vz + I rz, where rz is the small dynamic resistance, so "
               "the straight part extended back to zero current cuts the axis at Vz.",
        safety="A series resistor must always be in the circuit: without it the Zener diode burns out as soon as it "
               "breaks down. Keep the current well below the diode's power rating.",
        tour=[{"say": "The Zener diode is in reverse bias, with a 1 kΩ resistor in series and meters for V and I."},
              {"set": {"Eb": -3}, "say": "Three volts in reverse: almost no current. The diode has not broken down."},
              {"set": {"Eb": -10}, "say": "Ten volts: now several milliamperes flow, yet the voltage across the diode is near five volts. That is the breakdown voltage."}],
        questions=[{"q": "Past breakdown, the voltage across a Zener diode", "options": [
            "Stays nearly constant", "Rises with the current", "Falls to zero"], "answer": 0,
            "why": "That is why it is used as a voltage regulator."},
            {"q": "Why is a series resistor needed?", "options": [
                "To limit the current past breakdown", "To raise the breakdown voltage", "To make the meter read"],
             "answer": 0, "why": "Past breakdown the diode's own resistance is only a few ohms."}],
        sources=[S12, MANUAL_B, SIM],
        check={"params": {"Eb": -10.0}, "reading": "V_Z", "textbook": "zener_Vr"},
    )


def transistor_ce() -> dict:
    return lab(
        id="transistor-ce-characteristics", rig="semiconductor-board",
        title="Transistor in common emitter: characteristics and gain", group="Physics · Electronics", level="Class XII",
        topic="Semiconductor Electronics", chapter="Semiconductor Electronics",
        aim="Measure the base and collector currents of an n-p-n transistor in common emitter at a fixed collector voltage and find its current gain.",
        kernel="transistor",
        params={"Vbb": 2.0, "Rb": 100000.0, "Vcc": 6.0, "Rc": 1000.0, "beta": 200.0, "VA": 80.0,
                "Is": 1e-14, "nB": 1.0, "Vsat": 0.06},
        autorun=True, camera={"pos": [0.0, 0.7, 0.72], "look": [0, 0, -0.12]}, floor=-0.03,
        bodies=_semi_bodies([
            B("tr", "cylinder", name="n-p-n transistor", info="Three leads: emitter, base and collector.",
              r=0.0045, h=0.005, pos=[0.0, 0.0145, -0.02], color="black"),
            B("trf", "box", size=[0.009, 0.005, 0.002], pos=[0.0, 0.0145, -0.0245], color="black"),
            B("rb", "box", name="Base resistor (100 kΩ)", size=[0.018, 0.006, 0.006], pos=[-0.1, 0.018, 0.02], color="#d9b46a"),
            B("rc", "box", name="Collector resistor (1 kΩ)", size=[0.018, 0.006, 0.006], pos=[0.1, 0.018, -0.06], color="#d9b46a"),
            B("psu2", "box", name="Base supply", info="Sets the base current.", size=[0.18, 0.09, 0.12],
              pos=[0.42, 0.045, -0.3], color="#3a4f6e"),
            *dial("ua", [-0.14, 0.0, -0.3], "Microammeter (0-50 µA)", "Reads the base current."),
            needle("uan", [-0.14, 0.0, -0.3], "I_b", -40000.0),
            *dial("ma", [0.14, 0.0, -0.3], "Milliammeter (0-10 mA)", "Reads the collector current."),
            needle("man", [0.14, 0.0, -0.3], "I_c", -200.0),
            _w("w1", [[0.34, 0.02, -0.26], [-0.11, 0.02, 0.02]], "#d9a520"),
            _w("w2", [[-0.09, 0.02, 0.02], [-0.01, 0.02, -0.014]], "#d9a520"),
            _w("w3", [[-0.3, 0.02, -0.26], [0.1, 0.02, -0.06]]),
            _w("w4", [[0.11, 0.02, -0.06], [0.01, 0.02, -0.024]]),
            _w("w5", [[0.0, 0.02, 0.0], [-0.12, 0.02, -0.24]], "blue"),
        ]),
        knobs=[knob("Vbb", "Base supply", "Vbb", 0.6, 3.5, 0.05, 2.0, "V"),
               knob("Vcc", "Collector supply", "Vcc", 0, 10, 0.1, 6.0, "V"),
               knob("beta", "Transistor (current gain hidden)", "beta", 80, 500, 5, 200, hidden=True)],
        instruments=[inst("Ib", "readout", "Base current", "I_b", k=1e6, unit="µA", digits=1),
                     inst("Ic", "readout", "Collector current", "I_c", k=1000.0, unit="mA", digits=2),
                     inst("Vce", "readout", "Collector-emitter voltage", "V_ce", unit="V", lc=0.05, digits=2),
                     inst("gr", "graph", "I_C against I_B", "I_c", k=1000.0, x="I_b", xk=1e6, xlabel="I_B (µA)", dots=True)],
        steps=["Set the collector supply so that V_CE is 4 V.",
               "Set the base supply for the first base current and read I_B and I_C.",
               "Each time the base current is changed, bring V_CE back to 4 V before reading.",
               "Take five readings over the whole range of the microammeter.",
               "The slope of the I_C against I_B graph is the current gain β."],
        theory="In common emitter the base-emitter junction is forward biased and the collector-base junction is "
               "reverse biased. A small base current controls a much larger collector current: I_C = β I_B, where β "
               "is the current gain, typically a hundred or more. The collector current hardly depends on V_CE once "
               "V_CE is past the knee (about 0.3 V), which is why the readings are all taken at one fixed V_CE: the "
               "slope of I_C against I_B is then the current gain at that working point. The voltage gain of the "
               "stage is β times the ratio of the collector resistor to the input resistance.",
        safety="Never join the base straight to the supply: the base resistor must always be in place, or the "
               "junction is destroyed. Keep the collector current inside the milliammeter's range.",
        tour=[{"say": "An n-p-n transistor in common emitter: the base supply through 100 kΩ, the collector supply through 1 kΩ."},
              {"set": {"Vbb": 1.0}, "say": "A base current of about five microamperes gives a collector current of about one milliampere: two hundred times larger."},
              {"set": {"Vbb": 3.0}, "say": "Five times the base current, five times the collector current. That ratio is the current gain."}],
        questions=[{"q": "In common emitter, the current gain β is", "options": [
            "I_C / I_B", "I_C / I_E", "I_E / I_B"], "answer": 0, "why": "β = I_C/I_B, usually 100 or more."},
            {"q": "Why must V_CE be the same for every reading?", "options": [
                "So that β is measured at one working point", "To protect the meter", "To keep I_B constant"],
             "answer": 0, "why": "The collector current depends a little on V_CE through the Early effect."}],
        sources=[S12, MANUAL_B, SIM],
        check={"params": {"Vbb": 2.0, "Vcc": 6.0}, "reading": "I_c", "textbook": "trans_ic"},
    )


def ldr_intensity() -> dict:
    return lab(
        id="ldr-light-intensity", rig="ldr-bench",
        title="Light-dependent resistor: resistance and light", group="Physics · Electronics", level="Class XII",
        topic="Semiconductor Electronics", chapter="Semiconductor Electronics",
        aim="Move a lamp to different distances from a light-dependent resistor and find how its resistance depends on the illumination.",
        kernel="ldr",
        params={"d": 0.2, "Iv": 2.0, "Eamb": 0.0, "A": 60000.0, "gamma": 0.8, "Eb": 5.0, "Rs": 1000.0},
        autorun=True, camera={"pos": [0.1, 0.5, 0.8], "look": [0.1, 0.02, -0.1]}, floor=-0.14,
        bodies=[
            B("bench", "box", name="Optical bench", size=[1.0, 0.03, 0.08], pos=[0.0, -0.12, 0], color="wood", cut=False),
            B("ruler", "scale", name="Bench scale (cm)", length=1.0, spacing=0.01, major=10, labels=True,
              label_step=10, tick=0.01, font=0.016, pos=[-0.5, -0.103, 0.041], rot=[-1.5708, 0, 0]),
            B("lamp", "sphere", name="Lamp", info="A small filament lamp of fixed brightness.", r=0.022,
              pos=[0.0, -0.04, 0], color="gold", bind={"x": {"var": "p.d", "k": 1}}),
            B("lampst", "cylinder", r=0.005, h=0.07, pos=[0.0, -0.085, 0], color="steel", bind={"x": {"var": "p.d", "k": 1}}),
            B("ldr", "cylinder", name="Light-dependent resistor", info="A cadmium sulphide cell: its resistance falls as the light on it grows.",
              r=0.006, h=0.004, pos=[-0.4, -0.04, 0], rot=[1.5708, 0, 0], color="#d9b46a"),
            B("ldrst", "cylinder", r=0.005, h=0.07, pos=[-0.4, -0.085, 0], color="steel"),
            B("mm", "box", name="Multimeter", info="Set to ohms: it reads the resistance of the cell.",
              size=[0.14, 0.04, 0.1], pos=[0.3, -0.1, -0.2], color="#2b2f36"),
            B("mmd", "box", size=[0.1, 0.002, 0.04], pos=[0.3, -0.079, -0.22], color="white"),
            _w("w1", [[-0.4, -0.06, 0.0], [0.0, -0.08, -0.22], [0.26, -0.08, -0.22]]),
            _w("w2", [[-0.4, -0.06, 0.01], [0.0, -0.08, -0.26], [0.34, -0.08, -0.22]], "black"),
        ],
        knobs=[knob("d", "Lamp distance", "d", 0.08, 0.6, 0.01, 0.2, "m"),
               knob("gamma", "Cell (its exponent is hidden)", "gamma", 0.5, 1.0, 0.01, 0.8, hidden=True)],
        instruments=[inst("R", "readout", "Multimeter (resistance)", "R_ldr", unit="Ω", digits=0),
                     inst("E", "readout", "Illumination on the cell", "E_lux", unit="lx", digits=1),
                     inst("gr", "graph", "Resistance against distance", "R_ldr", x="p.d", xk=100.0, xlabel="d (cm)", dots=True)],
        steps=["Darken the room so that only the lamp lights the cell.",
               "Put the lamp 10 cm from the cell and read the resistance on the multimeter.",
               "Move the lamp to 15, 20, 30, 40 and 50 cm and read it each time.",
               "The illumination falls as the square of the distance.",
               "Plot log R against log d: the slope is twice the cell's exponent γ."],
        theory="A light-dependent resistor is a photoconductive cell: light frees charge carriers in it, so the more "
               "light falls on it the lower its resistance. Over a wide range the resistance follows R = A E^(−γ), "
               "where E is the illumination and γ is a number near 0.8 for a cadmium sulphide cell. A small lamp "
               "lights the cell with E = I/d², so doubling the distance quarters the illumination. Taking logarithms, "
               "log R = constant + 2γ log d, so the log-log plot is a straight line whose slope gives γ.",
        safety="The lamp gets hot: move it by its stand, not by the bulb. The cell must be shielded from other light.",
        tour=[{"say": "A small lamp on the optical bench lights a cadmium sulphide cell; the multimeter reads the cell's resistance."},
              {"set": {"d": 0.1}, "say": "The lamp close by: the cell is brightly lit and its resistance is low."},
              {"set": {"d": 0.5}, "say": "Five times as far away: a twenty-fifth of the light, and the resistance has risen many times over."}],
        questions=[{"q": "As the light on an LDR grows, its resistance", "options": ["Falls", "Rises", "Does not change"],
                    "answer": 0, "why": "More light frees more charge carriers."},
                   {"q": "If the lamp is moved twice as far away, the illumination becomes", "options": [
                       "One quarter", "One half", "Twice"], "answer": 0, "why": "The inverse-square law: E = I/d²."}],
        sources=[S12, MANUAL_B, SIM],
        check={"params": {"d": 0.3}, "reading": "R_ldr", "textbook": "ldr_R"},
    )


# ================================================================================================== wave optics
def single_slit() -> dict:
    return lab(
        id="single-slit-diffraction", rig="laser-diffraction",
        title="Diffraction of light at a single slit", group="Physics · Optics", level="Class XII",
        topic="Wave Optics", chapter="Wave Optics",
        aim="Send laser light through a narrow slit, measure the dark fringes on the screen and find the width of the slit.",
        kernel="diffraction",
        params={"a": 0.00012, "lam": 6.5e-7, "D": 0.8, "x": 0.0, "I0": 1.0},
        autorun=True, camera={"pos": [0.0, 0.5, 0.9], "look": [0.0, 0.06, -0.1]}, floor=-0.12,
        bodies=[
            B("bench", "box", name="Optical bench", size=[1.1, 0.03, 0.08], pos=[0.0, -0.1, -0.1], color="wood", cut=False),
            B("laser", "cylinder", name="Laser", info="A low-power laser of one fixed wavelength.", r=0.012, h=0.1,
              pos=[-0.5, -0.04, -0.1], rot=[0, 0, 1.5708], color="#2b2f36"),
            B("slit", "box", name="Single slit", info="A narrow slit in a metal slide. Its width is what we measure.",
              size=[0.004, 0.05, 0.05], pos=[-0.36, -0.03, -0.1], color="steel"),
            B("screen", "plane", name="Screen", info="The diffraction pattern is formed here.", size=[0.14, 0.12],
              pos=[0.4, -0.01, -0.1], rot=[0, 1.5708, 0], color="white", bind={"x": {"var": "p.D", "k": 1, "c": -0.36}}),
            B("cursor", "box", name="Cursor", info="Slides across the screen; its vernier reads to 0.1 mm.",
              size=[0.002, 0.02, 0.004], pos=[0.4, -0.01, -0.1], color="black", bind={"y": {"var": "p.x", "k": 1}}),
            B("beam", "cylinder", name="Laser beam", r=0.0008, h=0.14, pos=[-0.43, -0.04, -0.1], rot=[0, 0, 1.5708],
              color="red", illustrative=True),
        ],
        knobs=[knob("D", "Slit to screen distance", "D", 0.5, 1.0, 0.01, 0.8, "m"),
               knob("x", "Cursor position on the screen", "x", -0.04, 0.04, 0.0001, 0.0, "m"),
               knob("a", "Slit (its width is hidden)", "a", 0.00005, 0.0003, 0.00001, 0.00012, "m", hidden=True)],
        instruments=[inst("x1", "readout", "First dark fringe from the centre", "x_first_min", k=1000.0, unit="mm", digits=2),
                     inst("I", "readout", "Brightness at the cursor", "inten", digits=3)],
        steps=["Darken the room and let the laser beam fall on the slit.",
               "Look at the screen: a bright central band with dark gaps and fainter bands on both sides.",
               "Slide the cursor to the first dark fringe on the left and on the right, and note both readings.",
               "Do the same for the second and third dark fringes.",
               "For the m-th dark fringe, a = m λ D / x, where x is half the distance between the two sides."],
        theory="A slit narrow enough to be comparable with the wavelength spreads light instead of casting a sharp "
               "shadow. Light from the two halves of the slit arrives at the screen with different path lengths; the "
               "waves cancel completely in the direction where the extra path across the whole slit is a whole "
               "number of wavelengths, which gives dark fringes at a sin θ = m λ. For small angles sin θ is x/D, so "
               "the m-th dark fringe is at x = m λ D / a: the narrower the slit, the wider the pattern.",
        safety="Never look into the laser beam or at its reflection, and keep the beam below eye level.",
        tour=[{"say": "The laser lights a single narrow slit; the pattern forms on the screen a little under a metre away."},
              {"set": {"D": 1.0}, "say": "The screen moved further back: the whole pattern has spread out in proportion."},
              {"set": {"a": 0.00006}, "say": "A narrower slit spreads the light more: the fringes are twice as far apart."}],
        questions=[{"q": "If the slit is made narrower, the central band", "options": [
            "Becomes wider", "Becomes narrower", "Does not change"], "answer": 0, "why": "x = λD/a: narrower slit, wider pattern."},
            {"q": "The dark fringes of a single slit are at", "options": [
                "a sin θ = m λ", "a sin θ = (m + ½) λ", "a = m λ"], "answer": 0,
             "why": "The waves from the two halves of the slit cancel in those directions."}],
        sources=[S12, MANUAL_B, SIM],
        check={"params": {"D": 1.0}, "reading": "x1", "textbook": "diff_x1"},
    )


def polaroids() -> dict:
    return lab(
        id="polaroid-polarisation", rig="polaroid-bench",
        title="Polarisation of light with two polaroids", group="Physics · Optics", level="Class XII",
        topic="Wave Optics", chapter="Wave Optics",
        aim="Turn one polaroid in front of another, measure the light that gets through and verify Malus's law.",
        kernel="polaroid",
        params={"I0": 1200.0, "theta": 0.0, "theta0": 0.5236, "k1": 0.8, "k2": 0.8, "leak": 0.002},
        autorun=True, camera={"pos": [0.0, 0.45, 0.85], "look": [0.0, 0.08, -0.12]}, floor=-0.12,
        bodies=[
            B("bench", "box", name="Optical bench", size=[0.9, 0.03, 0.08], pos=[0.0, -0.1, -0.12], color="wood", cut=False),
            B("lamp", "sphere", name="Lamp", info="An ordinary lamp: its light is unpolarised.", r=0.025,
              pos=[-0.34, -0.03, -0.12], color="gold"),
            B("pol", "cylinder", name="Polariser", info="Fixed. It lets through only the light vibrating along its own axis.",
              r=0.03, h=0.004, pos=[-0.12, -0.02, -0.12], rot=[0, 0, 1.5708], color="#3a3a44", opacity=0.6),
            B("ana", "cylinder", name="Analyser", info="Turns in its mount; its scale reads the angle.",
              r=0.03, h=0.004, pos=[0.08, -0.02, -0.12], rot=[0, 0, 1.5708], color="#3a3a44", opacity=0.6,
              bind={"rx": {"var": "p.theta", "k": 1}}),
            B("cell", "box", name="Photocell", info="The meter behind it reads how much light gets through.",
              size=[0.01, 0.04, 0.04], pos=[0.3, -0.02, -0.12], color="#2b2f36"),
            *dial("lux", [0.3, -0.1, 0.1], "Light meter", "Reads the light falling on the photocell, in lux."),
            needle("luxn", [0.3, -0.1, 0.1], "inten", 0.0028),
        ],
        knobs=[knob("th", "Analyser angle", "theta", 0, 360, 1, 0, "°", DEG),
               knob("t0", "Polariser axis (hidden)", "theta0", 0, 179, 1, 30, "°", DEG, hidden=True)],
        instruments=[inst("I", "readout", "Light meter", "inten", unit="lx", lc=1.0, digits=0),
                     inst("gr", "graph", "Light against the analyser angle", "inten", x="p.theta", xk=R2D, xlabel="θ (°)", dots=True)],
        steps=["Switch the lamp on and let its light pass through both polaroids onto the photocell.",
               "Turn the analyser from 0° to 360° in steps of 15° and read the meter each time.",
               "The light is brightest twice and almost dark twice in one whole turn.",
               "Plot the reading against the angle: it follows cos² of the angle between the two axes.",
               "The angle at which the reading is largest is the polariser's own axis on the analyser's scale."],
        theory="Light from a lamp vibrates in every direction across the beam. The first polaroid, the polariser, "
               "lets through only the vibrations along its own axis, so the light beyond it is plane polarised and "
               "half as bright. The second polaroid, the analyser, passes a fraction cos²θ of that, where θ is the "
               "angle between the two axes: this is Malus's law. Turning the analyser through a whole circle gives "
               "two maxima and two minima, and the reading never falls quite to zero because no polaroid is perfect.",
        safety="The lamp gets hot. Hold the polaroids by their mounts: a fingerprint on the film changes the readings.",
        tour=[{"say": "An unpolarised lamp, a fixed polariser, and an analyser that turns in its own mount."},
              {"set": {"th": 30}, "say": "Here the two axes are parallel: the reading is the largest it can be."},
              {"set": {"th": 120}, "say": "A quarter turn further the axes are crossed and almost no light gets through."}],
        questions=[{"q": "When two polaroids are crossed, the light that gets through is", "options": [
            "Almost nothing", "Half", "Unchanged"], "answer": 0, "why": "cos²90° = 0."},
            {"q": "Unpolarised light passing through one polaroid loses", "options": [
                "Half its intensity", "All of it", "None of it"], "answer": 0,
             "why": "Only the vibrations along one direction get through, and the average of cos² over all directions is ½."}],
        sources=[S12, MANUAL_B, SIM],
        check={"params": {"theta": 1.0}, "reading": "inten", "textbook": "malus_I"},
    )


# ============================================================================================ metre bridge: combinations
def bridge_combination() -> dict:
    net = {"nodes": 6, "els": [
        {"id": "E", "kind": "V", "a": 1, "b": 4, "value": "Eb"},
        {"id": "K", "kind": "S", "a": 4, "b": 0, "param": "key"},
        {"id": "WA", "kind": "R", "a": 1, "b": 2, "value": {"param": "lj", "k": 2.0}},
        {"id": "WB", "kind": "R", "a": 2, "b": 0, "value": {"param": "lj", "k": -2.0, "c": 2.0}},
        {"id": "RK", "kind": "R", "a": 1, "b": 3, "value": "Rk"},
        {"id": "X1", "kind": "R", "a": 3, "b": 5, "value": "R1"},
        {"id": "KA", "kind": "S", "a": 5, "b": 0, "param": "ka"},
        {"id": "KB", "kind": "S", "a": 3, "b": 6, "param": "kb"},
        {"id": "X2", "kind": "R", "a": 6, "b": 0, "value": "R2"},
        {"id": "KS", "kind": "S", "a": 5, "b": 6, "param": "ser"},
        {"id": "G", "kind": "R", "a": 3, "b": 2, "value": 50.0}]}
    return lab(
        id="metre-bridge-combination", rig="bridge-combination",
        title="Metre bridge: laws of combination of resistances", group="Physics · Electricity", level="Class XII",
        topic="Current Electricity", chapter="Current Electricity",
        aim="Find two resistances with a metre bridge, then their series and parallel combinations, and verify the laws of combination.",
        kernel="circuit", cfg={"net": net},
        params={"Eb": 2.0, "lj": 0.5, "Rk": 4.0, "R1": 3.0, "R2": 6.0, "key": 1.0, "ka": 1.0, "kb": 0.0, "ser": 0.0},
        autorun=True, camera={"pos": [0.0, 1.25, 1.08], "look": [0, 0.02, -0.32]}, floor=-0.03,
        bodies=[
            board(1.25, 0.6),
            B("strip", "box", name="Copper strips", size=[1.1, 0.006, 0.03], pos=[0, 0.006, -0.46], color="copper"),
            B("wire", "rope", name="1 m manganin wire", a=[-0.5, 0.012, -0.3], b=[0.5, 0.012, -0.3], r=0.0012, color="steel"),
            B("ruler", "scale", name="Metre scale", length=1.0, spacing=0.01, major=10, labels=True, label_step=10,
              tick=0.012, font=0.02, pos=[-0.5, 0.002, -0.26], rot=[-1.5708, 0, 0]),
            B("jockey", "cone", name="Jockey", info="Touch the wire lightly where the galvanometer reads zero.",
              r=0.01, h=0.05, pos=[-0.5, 0.04, -0.3], rot=[3.1416, 0, 0], color="brass", bind={"x": "p.lj"}),
            *_decade("rb", -0.32, -0.66, "Resistance box R", "The known resistance in the left gap."),
            B("cb", "box", name="Combination board", info="Two coils R₁ and R₂ with three link keys.",
              size=[0.26, 0.03, 0.12], pos=[0.28, 0.015, -0.66], color="wood"),
            B("coil1", "spring", name="Coil R₁", a=[0.18, 0.036, -0.66], b=[0.26, 0.036, -0.66], r=0.009, turns=12,
              wire=0.0014, color="copper"),
            B("coil2", "spring", name="Coil R₂", a=[0.3, 0.036, -0.66], b=[0.38, 0.036, -0.66], r=0.009, turns=12,
              wire=0.0014, color="copper"),
            B("bat", "cylinder", name="Accumulator (2 V) and key K₁", r=0.028, h=0.1, pos=[-0.66, 0.028, -0.6],
              rot=[0, 0, 1.5708], color="#2b2f36"),
            B("key1", "box", name="Plug key K₁", size=[0.06, 0.02, 0.04], pos=[0.06, 0.02, 0.02], color="black"),
            *dial("g", [-0.3, 0.0, 0.02], "Galvanometer", "At the null point no current flows through it."),
            needle("gn", [-0.3, 0.0, 0.02], "I_G", -40000.0),
            _w("w1", [[-0.62, 0.03, -0.56], [-0.56, 0.03, -0.46]]),
            _w("w2", [[0.56, 0.03, -0.46], [0.6, 0.03, -0.1], [0.1, 0.03, 0.02]], "black"),
            _w("w3", [[0.02, 0.03, 0.02], [-0.66, 0.03, -0.14], [-0.7, 0.03, -0.56]], "black"),
            _w("w4", [[-0.4, 0.03, -0.6], [-0.26, 0.03, -0.48]], "#d9a520"),
            _w("w5", [[-0.24, 0.03, -0.6], [-0.1, 0.03, -0.48]], "#d9a520"),
            _w("w6", [[0.16, 0.03, -0.6], [0.1, 0.03, -0.48]], "blue"),
            _w("w7", [[0.4, 0.03, -0.6], [0.5, 0.03, -0.48]], "blue"),
            _w("w8", [[-0.3, 0.03, -0.04], [-0.02, 0.03, -0.44]], "black"),
        ],
        knobs=[knob("lj", "Jockey position l", "lj", 1, 99, 0.1, 50, "cm", 0.01),
               knob("Rk", "Resistance box R", "Rk", 1, 20, 1, 4, "Ω"),
               knob("ka", "Link key A (R₁ to the strip)", "ka", 0, 1, 1, 1),
               knob("kb", "Link key B (R₂ to the strip)", "kb", 0, 1, 1, 0),
               knob("ser", "Link key S (R₁ and R₂ end to end)", "ser", 0, 1, 1, 0),
               knob("key", "Key K₁ (0 open / 1 closed)", "key", 0, 1, 1, 1),
               knob("R1", "Coil R₁ (hidden)", "R1", 1, 15, 0.5, 3, "Ω", hidden=True),
               knob("R2", "Coil R₂ (hidden)", "R2", 1, 15, 0.5, 6, "Ω", hidden=True)],
        instruments=[inst("G", "readout", "Galvanometer", "I_G", k=1e6, unit="µA", digits=1)],
        steps=["Put the resistance box in the left gap and the combination board in the right gap.",
               "With link A alone in, R₁ is in the right gap: find the null point and work out R₁.",
               "With link B alone in, R₂ is in the right gap: find the null point and work out R₂.",
               "With link S alone in, the two coils are in series; with A and B both in, they are in parallel.",
               "Check that the series value is R₁ + R₂ and that the parallel value is R₁R₂/(R₁ + R₂)."],
        theory="A metre bridge is a Wheatstone bridge: at the null point the unknown X in the right gap satisfies "
               "R/X = l/(100 − l), so X = R(100 − l)/l. Measuring the two coils one at a time and then together is "
               "the direct test of the laws of combination: in series the same current passes through both and the "
               "potential differences add, so X = R₁ + R₂; in parallel the same potential difference is across both "
               "and the currents add, so 1/X = 1/R₁ + 1/R₂. The series value is larger than either coil and the "
               "parallel value smaller than either.",
        safety="Touch the jockey gently and never drag it along the wire. Keep the key out between readings, or the "
               "wire heats up and its resistance changes.",
        tour=[{"say": "The resistance box is in the left gap and the combination board in the right gap; the three link keys choose what is in that gap."},
              {"set": {"lj": 57.1}, "say": "With link A alone the gap holds R1, and the balance point is at about 57 centimetres."},
              {"set": {"ka": 0, "ser": 1, "lj": 30.8}, "say": "With link S the coils are end to end, in series: a larger resistance, so the balance point moves back towards A."}],
        questions=[{"q": "In series the combined resistance is", "options": [
            "Larger than either coil", "Smaller than either coil", "The average of the two"], "answer": 0,
            "why": "X = R₁ + R₂."},
            {"q": "Why should the null point be kept between 30 and 70 cm?", "options": [
                "The bridge is most sensitive there", "The wire is thicker there", "The scale is only marked there"],
             "answer": 0, "why": "Away from the middle a small error in l makes a large error in X."}],
        sources=[S12, MANUAL, SIM],
        check={"params": {"ka": 0.0, "kb": 0.0, "ser": 1.0, "key": 1.0},
               "measure": {"mode": "null", "param": "lj", "var": "I_G", "lo": 0.01, "hi": 0.99},
               "reading": "lj", "textbook": "bridge_comb_l"},
    )


BUILDERS: tuple[Any, ...] = (galv_half_deflection, galv_to_voltmeter, galv_to_ammeter,
                             pot_compare_emf, pot_potential_drop,
                             zener_characteristic, transistor_ce, ldr_intensity,
                             single_slit, polaroids, bridge_combination)
