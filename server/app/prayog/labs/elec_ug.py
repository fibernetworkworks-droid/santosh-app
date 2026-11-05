"""Lab pack `elec_ug`: the undergraduate ANALOG and DIGITAL electronics set-ups of `syllabus/physics/ug.json`
(chapters "Analog electronics and devices" and "Digital electronics, microprocessors and microcontrollers").

Three benches carry them all, so the apparatus is built once and built well (see `docs/PRAYOG_STUDIO.md`):

  rig `elec-ug-bench`     a solderless breadboard with a variable DC bench supply, a second low-voltage source and
                          two 4.5-digit digital multimeters: every DC characteristic and amplifier set-up
  rig `digital-trainer`   a digital trainer: 5 V rail, 7400 NAND ICs, input slide switches, output LEDs
  rig `rectifier-bench`   a bench transformer, a diode board, the filter capacitor, a true-RMS meter and a CRO

The physics is in `packs/elec_ug.py` (fet, opamp, zenreg, solar, rectifier, logic_gate, logic_arith) except the
common-emitter transistor, which `packs/elec11.py` already carries and which is reused here unchanged.

These labs carry no `table` block: the result is worked out by the studio rig from the record book it keeps, not by
one of the shared `CALCS` formulas. Every lab's `check` compares the kernel's own reading with its textbook formula.
"""
from __future__ import annotations

from typing import Any

from ..catalog import B, SIM, board, dial, inst, knob, lab, needle

# ------------------------------------------------------------------------------------------------------- sources
SED = {"title": "S. O. Kasap, Principles of Electronic Materials and Devices / A. S. Sedra and K. C. Smith, "
                "Microelectronic Circuits (square-law FET, op-amp and rectifier analysis)"}
MILL = {"title": "J. Millman and C. C. Halkias, Integrated Electronics; and A. P. Malvino, Electronic Principles "
                 "(rectifier ripple, Zener shunt regulator, CE amplifier)"}
TTL = {"title": "Texas Instruments SN5400/SN7400 quadruple 2-input positive-NAND gate datasheet (SDLS025)",
       "note": "5 V supply, V_IH 2 V, V_IL 0.8 V, V_OH 2.4 V min, V_OL 0.4 V max"}
MANO = {"title": "M. Morris Mano, Digital Design (NAND-only realisations, adders and subtractors)"}
PV = {"title": "M. A. Green, Solar Cells: Operating Principles, Technology and System Applications "
               "(single-diode model, fill factor)"}
UGC = {"title": "University of Delhi UGCF 2022 B.Sc. (Hons.) Physics, Analog Systems and Applications / Digital "
                "Systems and Applications laboratory lists"}


def _w(wid: str, pts: list[list[float]], color: str = "red") -> dict:
    return B(wid, "wire", pts=pts, r=0.003, color=color)


def _bench_bodies(extra: list[dict], *, two_meters: bool = True, second: bool = False) -> list[dict]:
    """The shared bench as LSL data: board, breadboard, supply (and a second source), one or two meters."""
    out: list[dict] = [
        board(1.0, 0.6),
        B("bb", "box", name="Solderless breadboard", info="830 tie points in two banks with a central channel for "
          "the integrated circuits, and a red and a blue power rail down each side.",
          size=[0.33, 0.01, 0.1], pos=[0.0, 0.015, -0.02], color="white"),
        B("bbch", "box", size=[0.33, 0.002, 0.008], pos=[0.0, 0.021, -0.02], color="#d9d9d4"),
        B("psu", "box", name="Variable DC bench supply (0-30 V)", info="The VOLTAGE knob sets the voltage applied "
          "to the circuit; the POWER rocker switches it on. Always start at zero.",
          size=[0.24, 0.12, 0.17], pos=[0.4, 0.06, -0.3], color="#2b2f36"),
        B("psuk", "cylinder", name="Voltage knob", r=0.02, h=0.016, pos=[0.37, 0.09, -0.21], rot=[1.5708, 0, 0],
          color="black"),
    ]
    if second:
        out.append(B("psu2", "box", name="Low-voltage source (0-5 V)", info="A second, small supply for the gate or "
                     "base circuit, so the input and the output can be set independently.",
                     size=[0.14, 0.07, 0.1], pos=[-0.4, 0.035, -0.26], color="#30353d"))
        out.append(B("psu2k", "cylinder", name="Input knob", r=0.013, h=0.012, pos=[-0.4, 0.05, -0.21],
                     rot=[1.5708, 0, 0], color="black"))
    out += dial("dm1", [-0.16, 0.0, -0.33], "Digital multimeter 1", "Reads the input or gate voltage.")
    if two_meters:
        out += dial("dm2", [0.1, 0.0, -0.33], "Digital multimeter 2", "Reads the output voltage or the current.")
    return out + extra


# ====================================================================================== BJT common emitter (reused kernel)
def bjt_ce() -> dict:
    return lab(
        id="bjt-ce-current-gain", rig="elec-ug-bench",
        title="BJT in common emitter: characteristics and current gain",
        group="Physics · Electronics", level="B.Sc. (Hons.) Physics", topic="Analog electronics and devices",
        chapter="Analog electronics and devices",
        aim="Bias an n-p-n transistor in common emitter, measure the base and collector currents as the base "
            "supply is raised, and find the current gain beta from the slope of I_C against I_B.",
        kernel="transistor",
        params={"Vbb": 1.0, "Rb": 100000.0, "Vcc": 10.0, "Rc": 470.0, "beta": 200.0},
        autorun=True, camera={"pos": [0.0, 0.7, 0.8], "look": [0, 0, -0.1]}, floor=-0.03,
        bodies=_bench_bodies([
            B("q1", "cylinder", name="n-p-n transistor (TO-92)", info="The flat face carries the type number; the "
              "three leads are the collector, the base and the emitter.", r=0.0023, h=0.005,
              pos=[0.0, 0.023, -0.02], color="black"),
            B("rb", "box", name="Base resistor R_B = 100 kOhm", size=[0.016, 0.006, 0.006],
              pos=[-0.1, 0.023, -0.05], color="#d9b46a"),
            B("rc", "box", name="Collector resistor R_C = 470 Ohm", size=[0.016, 0.006, 0.006],
              pos=[0.1, 0.023, -0.05], color="#d9b46a"),
            needle("n1", [-0.16, 0.0, -0.33], "I_b", -40000.0),
            needle("n2", [0.1, 0.0, -0.33], "I_c", -200.0),
            _w("w1", [[-0.3, 0.02, -0.22], [-0.12, 0.02, -0.05]]),
            _w("w2", [[0.3, 0.02, -0.22], [0.12, 0.02, -0.05]]),
            _w("w3", [[0.0, 0.02, 0.03], [-0.3, 0.02, 0.03]], "black"),
        ], second=True),
        knobs=[knob("Vbb", "Base supply V_BB", "Vbb", 0, 5, 0.05, 1.0, "V"),
               knob("Vcc", "Collector supply V_CC", "Vcc", 2, 15, 0.5, 10.0, "V"),
               knob("beta", "Transistor (current gain hidden)", "beta", 50, 500, 1, 200, hidden=True)],
        instruments=[inst("Ib", "readout", "Base current I_B", "I_b", k=1e6, unit="µA", digits=2),
                     inst("Ic", "readout", "Collector current I_C", "I_c", k=1000.0, unit="mA", digits=3),
                     inst("Vbe", "readout", "Base-emitter voltage", "V_be", unit="V", digits=3),
                     inst("Vce", "readout", "Collector-emitter voltage", "V_ce", unit="V", digits=3),
                     inst("gr", "graph", "I_C against I_B", "I_c", k=1000.0, x="I_b", xk=1e6, xlabel="I_B (µA)",
                          dots=True)],
        steps=["Wire the transistor in common emitter: R_B from the base supply to the base, R_C from the "
               "collector supply to the collector, emitter to the common negative rail.",
               "Set V_CC = 10 V and keep it there: the collector voltage stays well above the knee.",
               "Raise the base supply V_BB in steps and record I_B, I_C, V_BE and V_CE each time.",
               "Plot I_C against I_B. The straight line's slope is the current gain beta.",
               "Notice V_BE hardly moves while I_B changes many times over: the base-emitter junction is a diode."],
        theory="In common emitter the base current is the input and the collector current the output. The "
               "base-emitter junction is an ordinary diode, so V_BB = I_B R_B + V_BE fixes I_B, and the collector "
               "then carries I_C = beta I_B as long as the collector-base junction stays reverse biased "
               "(V_CE above the knee of about 0.3 V). The slope of the I_C against I_B line is the current gain; "
               "it is slightly larger than the low-frequency beta because the collector current also rises a "
               "little with V_CE (the Early effect).",
        safety="Bench voltages only. Keep R_B in the base lead: the base-emitter junction takes a destructive "
               "current if it is connected straight across a supply.",
        tour=[{"say": "An n-p-n transistor in common emitter, with a 100 kilohm base resistor and a 470 ohm "
                      "collector resistor."},
              {"set": {"Vbb": 1.0}, "say": "One volt on the base supply: the base current is a few microamperes "
                                           "and the collector current about a milliampere."},
              {"set": {"Vbb": 3.0}, "say": "Three volts: the base current has grown five times and so has the "
                                           "collector current. Their ratio is the current gain."}],
        questions=[{"q": "Why does V_BE hardly change while I_B grows five times over?",
                    "options": ["The base-emitter junction is a diode, so its voltage changes logarithmically",
                                "The base resistor holds it fixed", "V_BE does not depend on current at all"],
                    "answer": 0, "why": "V_BE = n V_T ln(I_B/I_S): a five-fold current change is only about 40 mV."},
                   {"q": "If V_CE falls below about 0.3 V, what happens to I_C?",
                    "options": ["It falls well below beta I_B (saturation)", "It keeps rising", "It does not change"],
                    "answer": 0, "why": "The collector junction is then forward biased and the transistor saturates."}],
        sources=[UGC, MILL, SIM],
        check={"params": {"Vbb": 2.0}, "reading": "I_c", "textbook": "trans_ic"},
    )


# ====================================================================================== JFET / MOSFET transfer curve
def _fet_lab(lab_id: str, kind: float, title: str, aim: str, unknown_knob: dict, params: dict,
             extra_theory: str, qs: list[dict], tour: list[dict], chk_vgs: float) -> dict:
    return lab(
        id=lab_id, rig="elec-ug-bench", title=title, group="Physics · Electronics",
        level="B.Sc. (Hons.) Physics", topic="Analog electronics and devices",
        chapter="Analog electronics and devices", aim=aim,
        kernel="fet", params=dict(params, kind=kind), autorun=True,
        camera={"pos": [0.0, 0.7, 0.8], "look": [0, 0, -0.1]}, floor=-0.03,
        bodies=_bench_bodies([
            B("j1", "cylinder", name="Field-effect transistor", info="Three leads: the gate, the drain and the "
              "source. The gate draws no current worth measuring.", r=0.0023, h=0.005,
              pos=[0.0, 0.023, -0.02], color="black"),
            B("rd", "box", name="Drain resistor R_D = 47 Ohm", info="Small, so the drain stays well past the knee "
              "and the device sits in saturation throughout.", size=[0.016, 0.006, 0.006],
              pos=[0.1, 0.023, -0.05], color="#d9b46a"),
            needle("n1", [-0.16, 0.0, -0.33], "V_gs", 0.3),
            needle("n2", [0.1, 0.0, -0.33], "I_d", -60.0),
            _w("w1", [[0.3, 0.02, -0.22], [0.12, 0.02, -0.05]]),
            _w("w2", [[-0.3, 0.02, -0.2], [-0.02, 0.02, -0.02]], "gold"),
            _w("w3", [[0.0, 0.02, 0.03], [-0.3, 0.02, 0.03]], "black"),
        ], second=True),
        knobs=[knob("Vgs", "Gate-source voltage V_GS", "Vgs", -10, 6, 0.01, 0.0, "V"),
               knob("Vdd", "Drain supply V_DD", "Vdd", 2, 20, 0.5, 12.0, "V"), unknown_knob],
        instruments=[inst("Vgs", "readout", "Gate-source voltage", "V_gs", unit="V", digits=3),
                     inst("Id", "readout", "Drain current I_D", "I_d", k=1000.0, unit="mA", digits=3),
                     inst("Vds", "readout", "Drain-source voltage", "V_ds", unit="V", digits=2),
                     inst("gr", "graph", "I_D against V_GS (transfer characteristic)", "I_d", k=1000.0,
                          x="V_gs", xlabel="V_GS (V)", dots=True)],
        steps=["Wire the source to the common negative rail, the drain through R_D to the drain supply and the "
               "gate to the low-voltage source.",
               "Set the drain supply to 12 V and leave it there.",
               "Set the gate voltage, read the drain current, and record both.",
               "Take eight or more readings spread across the working range of the gate.",
               "Plot the square root of I_D against V_GS: it is a straight line, and where it cuts the voltage "
               "axis is the voltage at which the channel closes."],
        theory="The channel of a field-effect transistor is squeezed by the gate voltage, and past the knee the "
               "drain current follows a square law. " + extra_theory + " Taking the square root of the drain "
               "current turns that square law into a straight line in V_GS, so the voltage at which the channel "
               "closes is read off as the intercept of that line on the voltage axis. Channel-length modulation "
               "tilts the saturation curves a little, which is why R_D is kept small: the drain-source voltage "
               "then hardly changes across the whole sweep.",
        safety="Bench voltages only. Handle the device by its body: a field-effect transistor's gate insulation "
               "is damaged by static, so touch the earthed bench before picking it up.",
        tour=tour, questions=qs, sources=[UGC, SED, SIM],
        check={"params": {"Vgs": chk_vgs}, "reading": "I_d", "textbook": "fet_id"},
    )


def jfet_transfer() -> dict:
    return _fet_lab(
        "jfet-transfer-characteristic", 0.0,
        "JFET: transfer characteristic and pinch-off voltage",
        "Measure the drain current of an n-channel JFET as the gate is taken negative, and find the pinch-off "
        "voltage V_P and the transconductance from the transfer characteristic.",
        knob("Vp", "Device (pinch-off voltage hidden)", "Vp", -10, -0.2, 0.01, -1.6, "V", hidden=True),
        {"Idss": 0.006, "Vp": -1.6, "lam": 0.02, "Vgs": 0.0, "Vdd": 12.0, "Rd": 47.0},
        "For a junction FET the gate junction is reverse biased, so the gate takes no current, and "
        "I_D = I_DSS (1 - V_GS/V_P)^2, where I_DSS is the drain current at zero gate voltage and V_P the "
        "negative pinch-off voltage at which the channel closes.",
        [{"q": "Why does the gate of a JFET draw no current?",
          "options": ["Its junction is reverse biased", "It is insulated by oxide", "It is shorted to the source"],
          "answer": 0, "why": "A junction FET works with the gate junction reverse biased; only the leakage flows."},
         {"q": "Taking the square root of I_D makes the transfer characteristic a straight line because",
          "options": ["the square law becomes linear", "the meter is logarithmic", "the drain resistor is small"],
          "answer": 0, "why": "sqrt(I_D) = sqrt(I_DSS)(1 - V_GS/V_P) is linear in V_GS."}],
        [{"say": "An n-channel JFET with its source on the negative rail and a small 47 ohm drain resistor."},
         {"set": {"Vgs": 0.0}, "say": "With the gate at zero the drain carries its largest current, I_DSS."},
         {"set": {"Vgs": -1.0}, "say": "One volt negative on the gate and the current has fallen steeply. Take the "
                                       "gate further negative and the channel closes completely."}],
        -0.8)


def mosfet_transfer() -> dict:
    return _fet_lab(
        "mosfet-transfer-characteristic", 1.0,
        "MOSFET: transfer characteristic and threshold voltage",
        "Measure the drain current of an n-channel enhancement MOSFET as the gate voltage is raised, and find the "
        "threshold voltage V_th from the transfer characteristic.",
        knob("Vth", "Device (threshold voltage hidden)", "Vth", 0.4, 6, 0.01, 2.1, "V", hidden=True),
        {"kn": 0.02, "Vth": 2.1, "lam": 0.02, "Vgs": 0.0, "Vdd": 12.0, "Rd": 47.0},
        "An enhancement MOSFET has no channel at all until the gate voltage passes the threshold V_th; past it "
        "I_D = (k/2)(V_GS - V_th)^2, where k is set by the oxide and the shape of the channel.",
        [{"q": "Below the threshold voltage the drain current is",
          "options": ["almost zero: there is no channel", "the largest it will be", "negative"],
          "answer": 0, "why": "An enhancement MOSFET is normally off; the gate has to build the channel."},
         {"q": "Why must a MOSFET be handled by its body and on an earthed bench?",
          "options": ["Static can puncture the thin gate oxide", "The leads bend", "It gets hot"],
          "answer": 0, "why": "The gate oxide is a few tens of nanometres thick and breaks down at a few tens of volts."}],
        [{"say": "An n-channel enhancement MOSFET with the source on the negative rail and a small drain resistor."},
         {"set": {"Vgs": 1.5}, "say": "One and a half volts on the gate and nothing flows: the threshold has not "
                                      "been reached."},
         {"set": {"Vgs": 3.0}, "say": "Three volts and the drain current is several milliamperes. The channel has "
                                      "been built by the gate."}],
        3.0)


# ====================================================================================== Zener shunt regulator
def zener_regulator() -> dict:
    return lab(
        id="zener-shunt-regulator", rig="elec-ug-bench",
        title="Zener diode as a shunt voltage regulator",
        group="Physics · Electronics", level="B.Sc. (Hons.) Physics", topic="Analog electronics and devices",
        chapter="Analog electronics and devices",
        aim="Load a Zener diode past breakdown through a series resistor, raise the input voltage and measure how "
            "little the output moves: the line regulation of the regulator.",
        kernel="zenreg",
        params={"Vin": 9.0, "Rs": 220.0, "Vz": 5.1, "Rz": 7.0, "RL": 1000.0, "Is": 5e-9, "knee": 0.02},
        autorun=True, camera={"pos": [0.0, 0.7, 0.8], "look": [0, 0, -0.1]}, floor=-0.03,
        bodies=_bench_bodies([
            B("zd", "cylinder", name="Zener diode", info="The band marks the cathode, which goes to the positive "
              "side: a Zener regulator works in reverse breakdown.", r=0.004, h=0.016,
              pos=[0.0, 0.024, -0.02], rot=[0, 0, 1.5708], color="black"),
            B("zdb", "cylinder", r=0.0043, h=0.003, pos=[-0.007, 0.024, -0.02], rot=[0, 0, 1.5708], color="white"),
            B("rs", "box", name="Series resistor R_S", info="It takes the difference between the input and the "
              "Zener voltage, and limits the diode current.", size=[0.016, 0.006, 0.006],
              pos=[-0.1, 0.023, -0.05], color="#d9b46a"),
            B("rl", "box", name="Load resistor R_L", size=[0.016, 0.006, 0.006], pos=[0.1, 0.023, -0.05],
              color="#d9b46a"),
            needle("n1", [-0.16, 0.0, -0.33], "V_Rs", -0.1),
            needle("n2", [0.1, 0.0, -0.33], "V_o", -0.2),
            _w("w1", [[-0.3, 0.02, -0.22], [-0.12, 0.02, -0.05]]),
            _w("w2", [[0.0, 0.02, 0.03], [-0.3, 0.02, 0.03]], "black"),
            _w("w3", [[0.02, 0.02, -0.02], [0.1, 0.02, -0.04]], "gold"),
        ]),
        knobs=[knob("Vin", "Input voltage V_in", "Vin", 0, 30, 0.1, 9.0, "V"),
               knob("RL", "Load resistance R_L", "RL", 100, 10000, 10, 1000, "Ω"),
               knob("Vz", "Diode (breakdown voltage hidden)", "Vz", 2.4, 24, 0.1, 5.1, "V", hidden=True)],
        instruments=[inst("Vin", "readout", "Input voltage", "V_Rs", unit="V", digits=3),
                     inst("Vo", "readout", "Output voltage across the load", "V_o", unit="V", digits=3),
                     inst("Iz", "readout", "Zener current", "I_z", k=1000.0, unit="mA", digits=2),
                     inst("IL", "readout", "Load current", "I_L", k=1000.0, unit="mA", digits=2),
                     inst("gr", "graph", "Output against input", "V_o", x="p.Vin", xlabel="V_in (V)", dots=True)],
        steps=["Wire the series resistor from the supply to the Zener's cathode, the Zener's anode to the common "
               "negative rail, and the load across the Zener.",
               "Raise the input until the Zener is well past breakdown and carries a few milliamperes.",
               "Raise the input in one-volt steps and record the input and the output each time.",
               "The slope of the output against the input, in millivolts per volt, is the line regulation.",
               "Change the load resistor and repeat: the output again hardly moves, which is load regulation."],
        theory="Past its breakdown voltage a Zener diode holds a nearly constant voltage, because on that part of "
               "its characteristic V = V_Z + I r_z with a dynamic resistance r_z of only a few ohms. Put it across "
               "the load, feed it through a series resistor R_S, and any extra input voltage is dropped across "
               "R_S instead of the load: the node gives "
               "V_o = (V_in/R_S + V_Z/r_z)/(1/R_S + 1/r_z + 1/R_L). Because r_z is small compared with R_S, a "
               "large change in the input makes only a small change in the output. The regulator stops working if "
               "the input falls so low that the diode leaves breakdown, or if the load takes so much current that "
               "nothing is left for the diode.",
        safety="Bench voltages only. The series resistor must always be in place: without it the Zener takes a "
               "destructive current the instant it breaks down. Keep the diode's power well under its rating.",
        tour=[{"say": "A Zener diode in reverse breakdown with a series resistor and a load across it."},
              {"set": {"Vin": 9.0}, "say": "Nine volts in and about five at the load: the Zener is holding it."},
              {"set": {"Vin": 15.0}, "say": "Fifteen volts in. The output has risen by only about a tenth of a "
                                            "volt: the extra six volts went to the series resistor."}],
        questions=[{"q": "Why does the output hardly change when the input rises?",
                    "options": ["The Zener's dynamic resistance is far smaller than R_S",
                                "The load resistance rises too", "The diode stops conducting"],
                    "answer": 0, "why": "The input change divides between R_S and r_z, and r_z is a few ohms."},
                   {"q": "The regulator fails if the load takes too much current because",
                    "options": ["no current is left to keep the Zener in breakdown",
                                "the Zener voltage rises", "the series resistor shorts"],
                    "answer": 0, "why": "R_S passes a fixed current; the diode only gets what the load leaves."}],
        sources=[UGC, MILL, SIM],
        check={"params": {"Vin": 12.0, "RL": 1000.0}, "reading": "V_o", "textbook": "zenreg_vo"},
    )


# ====================================================================================== solar cell
def solar_cell() -> dict:
    return lab(
        id="solar-cell-characteristic", rig="elec-ug-bench",
        title="Solar cell: I-V curve, maximum power point and fill factor",
        group="Physics · Electronics", level="B.Sc. (Hons.) Physics", topic="Analog electronics and devices",
        chapter="Analog electronics and devices",
        aim="Light a silicon solar cell, vary the load from short circuit to open circuit, plot the current against "
            "the voltage, find the maximum power point and work out the fill factor.",
        kernel="solar",
        params={"Iph": 0.12, "Is": 1e-9, "nD": 1.3, "ns": 1.0, "Rser": 0.3, "Rsh": 10000.0, "RL": 10.0},
        autorun=True, camera={"pos": [0.0, 0.7, 0.8], "look": [0, 0, -0.1]}, floor=-0.03,
        bodies=_bench_bodies([
            B("cell", "box", name="Silicon solar cell", info="A single crystalline cell. Its open-circuit voltage "
              "is about six tenths of a volt whatever the light; the current is what the light sets.",
              size=[0.08, 0.003, 0.08], pos=[0.0, 0.025, -0.02], color="#2747a8"),
            B("lamp", "sphere", name="Filament lamp", info="The light source. Its distance sets how much light "
              "falls on the cell.", r=0.025, pos=[0.0, 0.2, -0.02], color="gold"),
            B("lampst", "cylinder", r=0.008, h=0.18, pos=[0.0, 0.1, -0.12], color="steel"),
            B("pot", "cylinder", name="Load potentiometer", info="The load across the cell, from almost a short "
              "circuit to almost an open circuit.", r=0.02, h=0.02, pos=[0.14, 0.03, -0.02], color="#30353d"),
            needle("n1", [-0.16, 0.0, -0.33], "V_o", -1.8),
            needle("n2", [0.1, 0.0, -0.33], "I_o", -9.0),
            _w("w1", [[0.04, 0.02, -0.02], [0.12, 0.02, -0.02]]),
            _w("w2", [[-0.04, 0.02, -0.02], [-0.16, 0.02, -0.25]], "black"),
        ], second=False),
        knobs=[knob("RL", "Load resistance", "RL", 0.1, 5000, 0.1, 10.0, "Ω"),
               knob("Iph", "Light on the cell (photocurrent hidden)", "Iph", 0.005, 0.5, 0.001, 0.12, "A",
                    hidden=True)],
        instruments=[inst("V", "readout", "Cell voltage", "V_o", unit="V", digits=3),
                     inst("I", "readout", "Cell current", "I_o", k=1000.0, unit="mA", digits=1),
                     inst("P", "readout", "Power delivered", "P_o", k=1000.0, unit="mW", digits=2),
                     inst("gr", "graph", "I against V", "I_o", k=1000.0, x="V_o", xlabel="V (V)", dots=True)],
        steps=["Light the cell and leave the lamp where it is for the whole experiment.",
               "Set the load almost to a short circuit and read the current: that is the short-circuit current.",
               "Raise the load step by step, recording the voltage and the current each time; take plenty of "
               "readings around the knee of the curve, where the power is largest.",
               "Finish with the load almost open: the voltage there is the open-circuit voltage.",
               "The fill factor is the largest power in the table divided by the product of the short-circuit "
               "current and the open-circuit voltage."],
        theory="A lit solar cell is a current source of I_ph in parallel with its own p-n junction, with a small "
               "series resistance in the contacts and a large shunt resistance at the edges: "
               "I = I_ph - I_s(e^((V + I R_s)/(n V_T)) - 1) - (V + I R_s)/R_sh. At short circuit the whole "
               "photocurrent comes out and the voltage is zero; at open circuit all of it goes back through the "
               "junction and the voltage is V_oc = n V_T ln(I_ph/I_s + 1). Neither of those delivers any power. "
               "Somewhere between them the product I V is largest, and the fill factor FF = P_max/(I_sc V_oc) "
               "says how square the curve is: a good silicon cell reaches about 0.7 to 0.8.",
        safety="The lamp gets hot: do not touch the bulb, and keep it clear of the wiring. Bench voltages only.",
        tour=[{"say": "A silicon solar cell under a lamp, with a potentiometer as its load and meters for the "
                      "voltage and the current."},
              {"set": {"RL": 0.1}, "say": "The load is almost a short circuit: all the voltage is zero and the "
                                          "current is the largest it gets."},
              {"set": {"RL": 5000}, "say": "Now the load is almost open. The voltage has reached about six tenths "
                                           "of a volt and the current has gone. No power either way."},
              {"set": {"RL": 5}, "say": "Between the two the cell delivers its most power. That is the maximum "
                                        "power point."}],
        questions=[{"q": "Why is no power delivered at short circuit or at open circuit?",
                    "options": ["One of the voltage and the current is zero in each case",
                                "The cell is damaged", "The lamp is too far"],
                    "answer": 0, "why": "Power is the product I V, and one factor is zero at each end."},
                   {"q": "Doubling the light on the cell roughly doubles",
                    "options": ["the short-circuit current", "the open-circuit voltage", "the fill factor"],
                    "answer": 0, "why": "I_sc follows the photocurrent, while V_oc only grows logarithmically."}],
        sources=[UGC, PV, SIM],
        check={"params": {}, "reading": "V_oc", "textbook": "solar_voc"},
    )


# ====================================================================================== op-amp
def _opamp_bodies(label: str) -> list[dict]:
    return _bench_bodies([
        B("ic", "box", name=label, info="An 8-pin dual-in-line package across the breadboard's central channel. "
          "Pin 1 is marked by the notch; the inverting input, the non-inverting input and the output are pins 2, "
          "3 and 6.", size=[0.01, 0.004, 0.008], pos=[0.0, 0.024, -0.02], color="black"),
        B("icn", "cylinder", r=0.0012, h=0.001, pos=[-0.004, 0.0265, -0.02], color="#30353d"),
        B("r1", "box", name="Input resistor R_1", size=[0.016, 0.006, 0.006], pos=[-0.09, 0.023, -0.05],
          color="#d9b46a"),
        B("rf", "box", name="Feedback resistor R_f", size=[0.016, 0.006, 0.006], pos=[0.0, 0.023, -0.07],
          color="#d9b46a"),
        needle("n1", [-0.16, 0.0, -0.33], "V_1", 0.5),
        needle("n2", [0.1, 0.0, -0.33], "V_o", -0.08),
        _w("w1", [[-0.3, 0.02, -0.2], [-0.1, 0.02, -0.05]], "gold"),
        _w("w2", [[0.02, 0.02, -0.02], [0.1, 0.02, -0.3]], "blue"),
        _w("w3", [[0.0, 0.02, 0.03], [-0.3, 0.02, 0.03]], "black"),
    ], second=True)


def opamp_inverting() -> dict:
    return lab(
        id="opamp-inverting-amplifier", rig="elec-ug-bench",
        title="Op-amp inverting amplifier: DC gain",
        group="Physics · Electronics", level="B.Sc. (Hons.) Physics", topic="Analog electronics and devices",
        chapter="Analog electronics and devices",
        aim="Build an inverting amplifier of a given gain with an operational amplifier, measure the output against "
            "the input, and check the gain against the ratio of the two resistors.",
        kernel="opamp",
        params={"A0": 200000.0, "Vsat": 13.5, "R1": 1000.0, "R2": 1e9, "R3": 1e9, "Rf": 10000.0,
                "Ra": 0.0, "Rb": 1e9, "V1": 0.0, "V2": 0.0, "V3": 0.0, "V4": 0.0, "open": 0.0},
        autorun=True, camera={"pos": [0.0, 0.7, 0.8], "look": [0, 0, -0.1]}, floor=-0.03,
        bodies=_opamp_bodies("Operational amplifier (8-pin DIL)"),
        knobs=[knob("V1", "Input voltage V_in", "V1", -5, 5, 0.01, 0.0, "V"),
               knob("Rf", "Feedback resistor R_f", "Rf", 1000, 100000, 100, 10000, "Ω"),
               knob("R1", "Input resistor R_1", "R1", 100, 100000, 100, 1000, "Ω")],
        instruments=[inst("Vin", "readout", "Input voltage", "V_1", unit="V", digits=3),
                     inst("Vo", "readout", "Output voltage", "V_o", unit="V", digits=3),
                     inst("Vn", "readout", "Voltage at the inverting input", "V_n", unit="V", digits=4),
                     inst("gr", "graph", "Output against input", "V_o", x="V_1", xlabel="V_in (V)", dots=True)],
        steps=["Wire R_1 from the input source to the inverting input, R_f from the inverting input to the output, "
               "and earth the non-inverting input.",
               "Switch on the supplies and check that the output is near zero with the input at zero.",
               "Set the input, read the output and record both. Work through negative and positive inputs.",
               "Plot the output against the input. The slope is the gain, and it is negative.",
               "Compare the slope with -R_f/R_1, and notice that the inverting input stays within a millivolt of "
               "earth throughout: that is the virtual earth."],
        theory="An operational amplifier has an open-loop gain of a few hundred thousand, so when the output is "
               "fed back to the inverting input the amplifier does whatever it takes to keep its two inputs at "
               "the same voltage. With the non-inverting input earthed, the inverting input becomes a virtual "
               "earth, the input current V_in/R_1 has nowhere to go but R_f, and the output must sit at "
               "V_o = -(R_f/R_1) V_in. The gain is set by two resistors and not by the amplifier, which is the "
               "whole point of feedback; the residual error is of the order of the closed-loop gain divided by "
               "the open-loop gain. The output cannot go past the supply rails, so beyond a certain input it "
               "saturates.",
        safety="Bench voltages only. The amplifier needs both a positive and a negative supply; connect them the "
               "right way round, since reversed supplies destroy the device.",
        tour=[{"say": "An operational amplifier on the breadboard with a 1 kilohm input resistor and a 10 kilohm "
                      "feedback resistor."},
              {"set": {"V1": -1.0}, "say": "Minus one volt in: the output is ten volts positive. The gain is ten "
                                           "and the sign is inverted."},
              {"set": {"V1": 1.0}, "say": "Plus one volt in and the output is ten volts negative. The same gain "
                                          "the other way."}],
        questions=[{"q": "The gain of an inverting amplifier is set by",
                    "options": ["the ratio R_f/R_1", "the open-loop gain of the amplifier", "the supply voltage"],
                    "answer": 0, "why": "Feedback makes the gain depend on the two resistors, not on the device."},
                   {"q": "Why does the inverting input stay within a millivolt of earth?",
                    "options": ["The open-loop gain is enormous, so the input difference must be tiny",
                                "It is wired to earth", "R_f is small"],
                    "answer": 0, "why": "V_o = A_0 (V_p - V_n) with A_0 about 200000, so V_n - V_p is microvolts."}],
        sources=[UGC, SED, SIM],
        check={"params": {"V1": -1.0}, "reading": "V_o", "textbook": "opamp_vo"},
    )


def opamp_summing() -> dict:
    return lab(
        id="opamp-summing-amplifier", rig="elec-ug-bench",
        title="Adding DC voltages with an op-amp: the summing amplifier",
        group="Physics · Electronics", level="B.Sc. (Hons.) Physics", topic="Analog electronics and devices",
        chapter="Analog electronics and devices",
        aim="Feed three DC voltages into the virtual earth of an op-amp through equal resistors and show that the "
            "output is the sum of the inputs, multiplied by the ratio of the feedback to the input resistance.",
        kernel="opamp",
        params={"A0": 200000.0, "Vsat": 13.5, "R1": 10000.0, "R2": 10000.0, "R3": 10000.0, "Rf": 10000.0,
                "Ra": 0.0, "Rb": 1e9, "V1": 0.0, "V2": 0.0, "V3": 0.0, "V4": 0.0, "open": 0.0},
        autorun=True, camera={"pos": [0.0, 0.7, 0.8], "look": [0, 0, -0.1]}, floor=-0.03,
        bodies=_opamp_bodies("Operational amplifier as a summing amplifier"),
        knobs=[knob("V1", "First input V_1", "V1", -4, 4, 0.01, 0.0, "V"),
               knob("V2", "Second input V_2", "V2", -4, 4, 0.01, 0.0, "V"),
               knob("V3", "Third input V_3", "V3", -4, 4, 0.01, 0.0, "V"),
               knob("Rf", "Feedback resistor R_f", "Rf", 1000, 100000, 100, 10000, "Ω")],
        instruments=[inst("V1", "readout", "First input", "V_1", unit="V", digits=3),
                     inst("V2", "readout", "Second input", "V_2", unit="V", digits=3),
                     inst("V3", "readout", "Third input", "V_3", unit="V", digits=3),
                     inst("Vo", "readout", "Output voltage", "V_o", unit="V", digits=3),
                     inst("gr", "graph", "Output against the first input", "V_o", x="V_1", xlabel="V_1 (V)",
                          dots=True)],
        steps=["Wire three equal 10 kilohm resistors from the three input sources to the inverting input, and a "
               "10 kilohm feedback resistor from the inverting input to the output.",
               "Earth the non-inverting input and switch on the supplies.",
               "Set a combination of the three inputs, read the output, and record all four numbers.",
               "Take at least eight combinations, including some that cancel one another.",
               "Plot the output against the sum of the three inputs: a straight line whose slope is -R_f/R."],
        theory="Because the inverting input of a fed-back op-amp is a virtual earth, each input resistor carries "
               "its own current V/R into that node without knowing about the others, and all of those currents "
               "must leave through the feedback resistor. So "
               "V_o = -R_f(V_1/R_1 + V_2/R_2 + V_3/R_3), which with equal input resistors is simply "
               "-(R_f/R) times the sum of the inputs. That independence is what makes the virtual earth a true "
               "summing point, and it is the basis of the weighted-resistor digital-to-analogue converter: give "
               "the inputs resistances in the ratio 1, 2, 4, 8 and the output is the binary number.",
        safety="Bench voltages only. Connect the positive and the negative supply the right way round.",
        tour=[{"say": "Three input resistors into one virtual earth, with a single feedback resistor: a summing "
                      "amplifier."},
              {"set": {"V1": 1.0, "V2": 2.0, "V3": 0.5}, "say": "One, two and half a volt in. The output is minus "
                                                                "three and a half volts: the sum, inverted."},
              {"set": {"V1": 2.0, "V2": -2.0, "V3": 0.0}, "say": "Two volts and minus two volts cancel, and the "
                                                                 "output goes back to zero."}],
        questions=[{"q": "Why do the three inputs not interfere with one another?",
                    "options": ["Each resistor feeds a virtual earth, so its current does not depend on the others",
                                "The amplifier isolates them", "The resistors are equal"],
                    "answer": 0, "why": "The summing node sits at zero volts whatever the inputs do."},
                   {"q": "To build a 4-bit weighted-resistor digital-to-analogue converter the input resistors "
                         "should be in the ratio",
                    "options": ["1 : 2 : 4 : 8", "1 : 1 : 1 : 1", "8 : 4 : 4 : 1"],
                    "answer": 0, "why": "Each bit must contribute half of the one above it."}],
        sources=[UGC, SED, SIM],
        check={"params": {"V1": 1.0, "V2": 2.0, "V3": 0.5}, "reading": "V_o", "textbook": "opamp_vo"},
    )


# ====================================================================================== digital trainer
def _digital_bodies(chip_names: list[str]) -> list[dict]:
    out: list[dict] = [
        board(1.0, 0.6),
        B("tr", "box", name="Digital trainer", info="A 5 volt regulated rail, slide switches for the inputs and "
          "light-emitting diodes on the outputs.", size=[0.5, 0.05, 0.22], pos=[0.0, 0.025, -0.1],
          color="#30353d"),
        B("bb", "box", name="Solderless breadboard", info="The integrated circuits straddle the central channel.",
          size=[0.33, 0.01, 0.1], pos=[0.0, 0.055, -0.02], color="white"),
    ]
    for i, nm in enumerate(chip_names[:3]):
        out.append(B("ic%d" % i, "box", name=nm, info="A 14-pin dual-in-line package. Pin 14 is the 5 V supply "
                     "and pin 7 is ground.", size=[0.02, 0.004, 0.008],
                     pos=[-0.1 + i * 0.1, 0.064, -0.02], color="black"))
    for i in range(3):
        out.append(B("sw%d" % i, "box", name="Input switch", size=[0.014, 0.012, 0.02],
                     pos=[-0.18 + i * 0.05, 0.056, -0.17], color="#d9d9d4"))
    for i in range(4):
        out.append(B("led%d" % i, "sphere", name="Output lamp", r=0.006, pos=[0.08 + i * 0.03, 0.056, -0.17],
                     color="red"))
    out.append(B("rail", "box", name="5 V supply rail", size=[0.44, 0.004, 0.006], pos=[0.0, 0.052, -0.04],
                 color="red"))
    return out


def nand_gates() -> dict:
    return lab(
        id="nand-universal-gates", rig="digital-trainer",
        title="AND, OR, NOT and XOR gates built from NAND gates",
        group="Physics · Electronics", level="B.Sc. (Hons.) Physics",
        topic="Digital electronics, microprocessors and microcontrollers",
        chapter="Digital electronics, microprocessors and microcontrollers",
        aim="Build each basic gate out of 2-input NAND gates on a 7400 integrated circuit, verify its truth table "
            "switch by switch, and so show that NAND is a universal gate.",
        kernel="logic_gate", params={"A": 0.0, "B": 0.0, "fn": 4.0, "Vcc": 5.0}, autorun=True,
        camera={"pos": [0.0, 0.6, 0.7], "look": [0, 0.05, -0.08]}, floor=-0.03,
        bodies=_digital_bodies(["7400 quad 2-input NAND", "7400 quad 2-input NAND"]) + [
            needle("n1", [0.26, 0.0, -0.33], "Y", -1.0),
            *dial("probe", [0.26, 0.0, -0.33], "Logic probe", "Reads a node as HIGH or LOW."),
        ],
        knobs=[knob("A", "Input A", "A", 0, 1, 1, 0),
               knob("B", "Input B", "B", 0, 1, 1, 0),
               knob("fn", "Gate being built (1 NOT, 2 AND, 3 OR, 4 XOR)", "fn", 1, 7, 1, 4)],
        instruments=[inst("Y", "readout", "Output Y", "Y", digits=0),
                     inst("n1", "readout", "First NAND output", "n1", digits=0),
                     inst("n4", "readout", "Last NAND output", "n4", digits=0)],
        steps=["Connect pin 14 of the 7400 to the 5 volt rail and pin 7 to ground.",
               "Wire the chosen gate out of NAND gates: NOT is one NAND with both inputs joined, AND is a NAND "
               "followed by that inverter, OR is two inverters into a NAND, and XOR takes four NAND gates.",
               "Set the input switches to each combination in turn and read the output lamp.",
               "Write the truth table down, row by row, and compare it with the Boolean expression.",
               "Repeat for the next gate: the same chip builds them all."],
        theory="NAND is a universal gate: every Boolean function can be built out of NAND gates alone. "
               "NOT A is A NAND A, because a NAND with both inputs tied together inverts. A AND B is NOT(A NAND "
               "B), so a NAND followed by that inverter. A OR B is (NOT A) NAND (NOT B), by De Morgan's theorem, "
               "which says that the complement of a product is the sum of the complements. Exclusive-OR needs "
               "four: n1 = A NAND B, n2 = A NAND n1, n3 = B NAND n1 and Y = n2 NAND n3, which works out to "
               "A.B' + A'.B. On a 7400 in transistor-transistor logic a LOW is below 0.8 V and a HIGH above 2 V, "
               "and the outputs are guaranteed below 0.4 V and above 2.4 V, so the gap between the two leaves "
               "room for noise.",
        safety="The trainer's 5 volt rail only. Never wire an output straight to the supply rail or to another "
               "output: a transistor-transistor logic output pulls hard both ways and will be destroyed.",
        tour=[{"say": "Two 7400 chips on the breadboard, with input switches and output lamps."},
              {"set": {"fn": 1, "A": 1}, "say": "One NAND with both inputs joined: the output is the opposite of "
                                                "the input. That is the NOT gate."},
              {"set": {"fn": 4, "A": 1, "B": 0}, "say": "Four NAND gates make exclusive-OR: the lamp is on only "
                                                        "when the two inputs differ."}],
        questions=[{"q": "A NAND gate with both inputs tied together behaves as",
                    "options": ["a NOT gate", "an AND gate", "a short circuit"],
                    "answer": 0, "why": "A NAND A = (A.A)' = A'."},
                   {"q": "Building OR from NAND gates uses",
                    "options": ["De Morgan's theorem", "the distributive law", "the absorption law"],
                    "answer": 0, "why": "A + B = (A'.B')', which is a NAND of the two complements."}],
        sources=[UGC, MANO, TTL, SIM],
        check={"params": {"A": 1.0, "B": 0.0, "fn": 4.0}, "reading": "Y", "textbook": "logic_y"},
    )


def _arith_lab(lab_id: str, title: str, aim: str, fn: float, fn_label: str, theory: str,
               qs: list[dict], tour: list[dict], chk: dict) -> dict:
    return lab(
        id=lab_id, rig="digital-trainer", title=title, group="Physics · Electronics",
        level="B.Sc. (Hons.) Physics", topic="Digital electronics, microprocessors and microcontrollers",
        chapter="Digital electronics, microprocessors and microcontrollers", aim=aim,
        kernel="logic_arith", params={"A": 0.0, "B": 0.0, "Cin": 0.0, "fn": fn, "An": 0.0, "Bn": 0.0},
        autorun=True, camera={"pos": [0.0, 0.6, 0.7], "look": [0, 0.05, -0.08]}, floor=-0.03,
        bodies=_digital_bodies(["7400 quad 2-input NAND", "7400 quad 2-input NAND",
                                "7400 quad 2-input NAND"]) + [
            needle("n1", [0.26, 0.0, -0.33], "value", -0.3),
            *dial("probe", [0.26, 0.0, -0.33], "Logic probe", "Reads a node as HIGH or LOW."),
        ],
        knobs=[knob("A", "Input A", "A", 0, 1, 1, 0), knob("B", "Input B", "B", 0, 1, 1, 0),
               knob("Cin", "Carry or borrow in", "Cin", 0, 1, 1, 0),
               knob("An", "Four-bit word A", "An", 0, 15, 1, 0),
               knob("Bn", "Four-bit word B", "Bn", 0, 15, 1, 0),
               knob("fn", fn_label, "fn", 1, 5, 1, fn)],
        instruments=[inst("S", "readout", "Sum output S", "S", digits=0),
                     inst("C", "readout", "Carry output", "Cout", digits=0),
                     inst("D", "readout", "Difference output D", "D", digits=0),
                     inst("Bo", "readout", "Borrow output", "Bout", digits=0),
                     inst("val", "readout", "Arithmetic value on the lamps", "value", digits=0)],
        steps=["Connect every chip's pin 14 to the 5 volt rail and pin 7 to ground.",
               "Wire the circuit out of NAND gates only, following the gate diagram in the theory.",
               "Set the input switches to each combination in turn.",
               "Read the output lamps and write the row of the table down.",
               "Check every row against plain binary arithmetic on the inputs."],
        theory=theory,
        safety="The trainer's 5 volt rail only. Never join two logic outputs together, and never wire an output "
               "to the supply rail.",
        tour=tour, questions=qs, sources=[UGC, MANO, TTL, SIM], check=chk,
    )


def binary_adders() -> dict:
    return _arith_lab(
        "nand-binary-adders", "Half adder, full adder and a 4-bit binary adder",
        "Build a half adder, then a full adder, then a four-bit ripple-carry adder out of NAND gates, and verify "
        "every row of each truth table against binary arithmetic.",
        1.0, "Circuit (1 half adder, 2 full adder, 5 four-bit adder)",
        "A half adder adds two bits: the sum is the exclusive-OR of them and the carry is their AND, so it is four "
        "NAND gates for the XOR and two more for the AND. It cannot take a carry coming in, which is why adding "
        "more than one bit needs the full adder: two half adders in cascade, with the two carries combined by an "
        "OR. Its sum is A xor B xor C_in and its carry is A.B + C_in(A xor B). Chain four full adders, each one's "
        "carry out feeding the next one's carry in, and the circuit adds two four-bit words: that is the "
        "ripple-carry adder, and its slowness is exactly the time the carry takes to ripple along the chain. "
        "In every case the lamps read S + 2C, which is just the arithmetic sum of the inputs.",
        [{"q": "Why can a half adder not be chained to add multi-bit numbers?",
          "options": ["It has no carry input", "It has no carry output", "Its sum is wrong"],
          "answer": 0, "why": "Each stage after the first must accept the carry from the stage below."},
         {"q": "In a ripple-carry adder the delay grows",
          "options": ["in proportion to the number of bits", "as the square of the number of bits",
                      "not at all"],
          "answer": 0, "why": "The carry has to pass through one full adder per bit."}],
        [{"say": "Three 7400 chips: enough NAND gates for a full adder."},
         {"set": {"fn": 1, "A": 1, "B": 1}, "say": "Half adder with both inputs high: the sum lamp is off and the "
                                                   "carry lamp is on. One plus one is binary two."},
         {"set": {"fn": 2, "A": 1, "B": 1, "Cin": 1}, "say": "Full adder with a carry in as well: sum one, carry "
                                                             "one, which reads three."}],
        {"params": {"A": 1.0, "B": 1.0, "Cin": 1.0, "fn": 2.0}, "reading": "value", "textbook": "arith_value"})


def binary_subtractors() -> dict:
    return _arith_lab(
        "nand-binary-subtractors", "Half subtractor and full subtractor from NAND gates",
        "Build a half subtractor and then a full subtractor out of NAND gates, and verify every row of the "
        "difference and borrow table against binary arithmetic.",
        3.0, "Circuit (3 half subtractor, 4 full subtractor)",
        "A half subtractor takes A minus B. The difference is the exclusive-OR of the two bits, exactly as in the "
        "adder, but the borrow is A'.B: a borrow is needed only when nothing is being taken from something. The "
        "full subtractor also takes a borrow coming in, so its difference is A xor B xor B_in and its borrow out "
        "is A'.B + B_in(A xor B)'. The difference output is the same function as the adder's sum, which is why one "
        "circuit with exclusive-OR gates on the B inputs can be made to add or to subtract on the turn of a "
        "single control line. The lamps read D - 2B_out, which is the arithmetic difference of the inputs.",
        [{"q": "The borrow of a half subtractor is",
          "options": ["A'.B", "A.B", "A xor B"],
          "answer": 0, "why": "A borrow is needed only when A is 0 and B is 1."},
         {"q": "The difference output of a subtractor is the same function as",
          "options": ["the sum output of an adder", "the carry output of an adder", "neither"],
          "answer": 0, "why": "Both are the exclusive-OR of the inputs and the carry or borrow in."}],
        [{"say": "The same NAND chips, rewired as a subtractor."},
         {"set": {"fn": 3, "A": 0, "B": 1}, "say": "Zero minus one: the difference lamp is on and so is the borrow "
                                                   "lamp. Binary arithmetic says minus one."},
         {"set": {"fn": 4, "A": 1, "B": 0, "Cin": 1}, "say": "Full subtractor: one minus zero minus a borrow in "
                                                             "leaves zero, with no borrow out."}],
        {"params": {"A": 1.0, "B": 0.0, "Cin": 0.0, "fn": 3.0}, "reading": "value", "textbook": "arith_value"})


# ====================================================================================== rectifier and filter
def rectifier_supply() -> dict:
    return lab(
        id="rectifier-filter-supply", rig="rectifier-bench",
        title="Rectifiers and a filtered power supply: ripple factor",
        group="Physics · Electronics", level="B.Sc. (Hons.) Physics", topic="Analog electronics and devices",
        chapter="Analog electronics and devices",
        aim="Rectify the output of a bench transformer, watch the waveform on the oscilloscope, measure the DC "
            "level and the ripple with a true-RMS meter, and work out the ripple factor with and without a "
            "capacitor filter.",
        kernel="rectifier",
        params={"Vp": 12.0, "f": 50.0, "kind": 2.0, "C": 0.0, "RL": 1000.0, "Vd": 0.7, "Rs": 1.0},
        autorun=True, camera={"pos": [0.0, 0.75, 0.85], "look": [0, 0.02, -0.12]}, floor=-0.03,
        bodies=[
            board(1.0, 0.6),
            B("tx", "box", name="Bench transformer, centre-tapped secondary", info="A safety-isolated transformer "
              "on the bench supply. Only its low-voltage secondary is used; the mains side is enclosed.",
              size=[0.14, 0.1, 0.12], pos=[-0.34, 0.05, -0.2], color="#30353d"),
            B("bb", "box", name="Diode board", info="Four rectifier diodes on brass terminals, so a half-wave, a "
              "centre-tap full-wave or a bridge circuit can be wired up.",
              size=[0.26, 0.012, 0.11], pos=[0.0, 0.016, -0.02], color="#e9e2cf"),
            B("d1", "cylinder", name="Rectifier diode", r=0.004, h=0.016, pos=[-0.07, 0.028, -0.04],
              rot=[0, 0, 1.5708], color="black"),
            B("d2", "cylinder", name="Rectifier diode", r=0.004, h=0.016, pos=[0.0, 0.028, -0.04],
              rot=[0, 0, 1.5708], color="black"),
            B("d3", "cylinder", name="Rectifier diode", r=0.004, h=0.016, pos=[-0.07, 0.028, 0.0],
              rot=[0, 0, 1.5708], color="black"),
            B("d4", "cylinder", name="Rectifier diode", r=0.004, h=0.016, pos=[0.0, 0.028, 0.0],
              rot=[0, 0, 1.5708], color="black"),
            B("cap", "cylinder", name="Filter capacitor", info="An electrolytic capacitor across the load. Its "
              "marked lead is the negative one.", r=0.016, h=0.04, pos=[0.1, 0.036, -0.02], color="#2747a8"),
            B("rl", "box", name="Load resistor R_L", size=[0.02, 0.008, 0.008], pos=[0.17, 0.02, -0.02],
              color="#d9b46a"),
            B("cro", "box", name="Oscilloscope", info="The waveform of the rectified output, with the time base "
              "set to show two cycles.", size=[0.3, 0.2, 0.26], pos=[0.26, 0.1, -0.36], color="#2b2f36"),
            B("croscr", "plane", name="Oscilloscope screen", size=[0.2, 0.15], pos=[0.26, 0.12, -0.23],
              color="#30353d"),
            *dial("dm", [-0.12, 0.0, -0.34], "True-RMS multimeter", "DC volts gives the average; AC volts gives "
                  "the ripple alone."),
            needle("dmn", [-0.12, 0.0, -0.34], "V_o", -0.12),
            _w("w1", [[-0.28, 0.02, -0.16], [-0.1, 0.02, -0.06]]),
            _w("w2", [[-0.28, 0.02, -0.24], [-0.1, 0.02, 0.02]], "black"),
            _w("w3", [[0.04, 0.02, -0.02], [0.16, 0.02, -0.02]], "gold"),
        ],
        knobs=[knob("kind", "Rectifier (1 half-wave, 2 centre-tap full-wave, 3 bridge)", "kind", 1, 3, 1, 2),
               knob("C", "Filter capacitor", "C", 0, 2000, 10, 0, "µF", 1e-6),
               knob("RL", "Load resistance", "RL", 100, 10000, 10, 1000, "Ω"),
               knob("Vp", "Secondary peak voltage", "Vp", 4, 24, 0.5, 12, "V")],
        instruments=[inst("Vdc", "readout", "DC output (average)", "V_o", unit="V", digits=3),
                     inst("Vin", "readout", "Secondary voltage", "V_in", unit="V", digits=2),
                     inst("IL", "readout", "Load current", "I_L", k=1000.0, unit="mA", digits=2),
                     inst("gr", "graph", "Output waveform", "V_o", xlabel="t (s)")],
        steps=["Wire the half-wave circuit first: one diode from the secondary to the load, the other side of the "
               "load back to the transformer's common.",
               "Look at the oscilloscope: one hump per cycle, and nothing in between.",
               "Read the DC volts and then the AC volts on the true-RMS meter, and record both.",
               "Rewire as a centre-tap full-wave circuit and then as a bridge, recording both readings each time.",
               "Put the filter capacitor across the load and record again: the hum shrinks and the DC level "
               "climbs towards the peak.",
               "The ripple factor is the AC reading divided by the DC reading."],
        theory="A rectifier turns alternating current into one-way current, but not into a steady voltage. A "
               "single diode passes one half cycle and the average works out at V_p/pi; a centre-tapped "
               "transformer with two diodes, or four diodes in a bridge, passes both halves and the average is "
               "2 V_p/pi, at twice the ripple frequency. What is left over is the ripple, and the ripple factor "
               "is the RMS of that ripple divided by the DC level, which is what a true-RMS meter reads on AC "
               "volts and on DC volts in turn. A capacitor across the load holds the voltage up between the "
               "peaks: it charges through the diode when the rectified voltage is above it and discharges into "
               "the load, with a time constant R_L C, so the bigger the capacitor and the lighter the load the "
               "smaller the ripple and the closer the output sits to the peak. Each conducting diode costs about "
               "0.7 volt, and the bridge has two of them in the path at any instant.",
        safety="Only the transformer's low-voltage secondary is handled; the mains side stays enclosed and is "
               "never probed. Switch off before rewiring. An electrolytic capacitor must go in the right way "
               "round and must be discharged through a resistor before it is touched.",
        tour=[{"say": "A bench transformer, a board of four rectifier diodes, a filter capacitor, a load and an "
                      "oscilloscope."},
              {"set": {"kind": 1, "C": 0}, "say": "Half-wave and no filter: one hump per cycle, and the average "
                                                  "is only about a third of the peak."},
              {"set": {"kind": 3, "C": 0}, "say": "A bridge uses both halves. Twice the average, and the ripple "
                                                  "comes at twice the frequency."},
              {"set": {"kind": 3, "C": 470}, "say": "Now the capacitor is across the load. The output has climbed "
                                                    "near the peak and the ripple is a small saw-tooth."}],
        questions=[{"q": "Why does a full-wave rectifier give twice the DC output of a half-wave one?",
                    "options": ["It uses both halves of each cycle", "Its diodes drop less",
                                "Its frequency is higher"],
                    "answer": 0, "why": "The average of |sin| is twice the average of the positive half alone."},
                   {"q": "Making the filter capacitor larger",
                    "options": ["lowers the ripple, because R_L C is longer", "raises the ripple frequency",
                                "lowers the DC output"],
                    "answer": 0, "why": "The capacitor discharges less between peaks."},
                   {"q": "The ripple factor of a supply is",
                    "options": ["the RMS of the ripple divided by the DC level", "the peak divided by the average",
                                "the AC frequency divided by the DC level"],
                    "answer": 0, "why": "It is a pure ratio: how much hum rides on the DC."}],
        sources=[UGC, MILL, SIM],
        check={"params": {"Vd": 0.0, "Rs": 1e-6, "C": 0.0, "kind": 2.0}, "reading": "V_dc",
               "textbook": "rect_vdc"},
    )


BUILDERS: tuple[Any, ...] = (bjt_ce, jfet_transfer, mosfet_transfer, zener_regulator, solar_cell,
                             opamp_inverting, opamp_summing, nand_gates, binary_adders, binary_subtractors,
                             rectifier_supply)
