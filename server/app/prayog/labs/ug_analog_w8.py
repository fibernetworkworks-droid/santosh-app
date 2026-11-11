"""Lab pack `ug_analog_w8`: undergraduate ANALOG ELECTRONICS, DEVICES and INSTRUMENT set-ups of `syllabus/physics/ug.json`
(wave 8; chapters "Analog electronics and devices" and "Electronic instrumentation and sensors"). The physics is in
`packs/ug_analog_w8.py` and its JavaScript twin; every lab here runs on ONE studio rig:

  rig `ug8-analog-bench`  a breadboard whose parts follow the lab, a bench supply / function generator panel whose dials
                          the hand turns, two digital multimeters and a two-channel digital scope. The scope shows either
                          the sampled waveforms of the lab's own kernel or, for a DC characteristic, an X-Y plot of the
                          readings taken so far.

Every lab's `check` compares one reading the kernel finds on its own simulated circuit (bisection, scanning, a DFT, an
RK4 run, a bit-by-bit SAR loop) with an exact textbook relation. Device constants are either a named data sheet's typical
value, written "from memory - verify" because they were not looked up for this build, or plainly "illustrative".
Bench supplies only: every voltage here is a low-voltage laboratory source; the 7805 set-up works on a step-down
transformer's secondary in a closed box, never on mains.
"""
from __future__ import annotations

from ..catalog import B, board, dial, inst, knob, lab

GROUP = "Physics · Electronics"
LEVEL = "B.Sc. (Hons.) Physics"
CH_ANA = "Analog electronics and devices"
CH_INS = "Electronic instrumentation and sensors"
RIG = "ug8-analog-bench"

DU = {"title": "University of Delhi B.Sc. (Hons.) Physics laboratory lists (LOCF 2019 / UGCF 2022): C-X Analog Systems, "
               "DSE Physics of Devices and Communication, DSE Experimental Techniques, SEC Basic of Instruments"}
UGC = {"title": "UGC LOCF B.Sc. Physics (2019): Digital, Analog and Instrumentation Lab"}
SEDRA = {"title": "A. S. Sedra and K. C. Smith, Microelectronic Circuits (diodes, BJT and JFET small-signal models, "
                  "class B / AB output stages, op-amp frequency response, active filters)"}
GAYAKWAD = {"title": "R. A. Gayakwad, Op-Amps and Linear Integrated Circuits (difference amplifier, analog computation, "
                     "active filters, the 565 PLL, sample-and-hold, R-2R DAC and SAR ADC)"}
SZE = {"title": "S. M. Sze and K. K. Ng, Physics of Semiconductor Devices: the Shockley diode equation and the tunnel-diode "
                "empirical I-V (tunnel, excess and diffusion currents)"}
SI_K = {"title": "SI Brochure, 9th ed. (BIPM 2019): k = 1.380649e-23 J/K and e = 1.602176634e-19 C, both exact"}
ILLU = {"title": "Illustrative settings", "note": "Values marked illustrative are lab settings chosen to be typical, not "
        "taken from a table; the relations that produce the readings are the textbook ones"}
MEMO = {"title": "Device constants from memory - verify", "note": "Typical data-sheet values written from memory for this "
        "build and not looked up; check them against the named data sheet before relying on them"}


def _bodies() -> list[dict]:
    out = [board(1.1, 0.62),
           B("panel", "box", name="Bench supply and function generator", info="The dials the hand turns.",
             size=[0.26, 0.1, 0.12], pos=[-0.44, 0.05, -0.24], color="#cdc9bf"),
           B("scope", "box", name="Digital storage oscilloscope", info="Two channels, or an X-Y plot of the readings.",
             size=[0.5, 0.3, 0.26], pos=[0.06, 0.15, -0.42], color="#cdc9bf")]
    out += dial("dm1", [0.42, 0.0, -0.05], "Digital multimeter 1", "The first reading.")
    out += dial("dm2", [0.42, 0.0, 0.12], "Digital multimeter 2", "The second reading.")
    return out


def _mk(id, title, aim, kernel, params, knobs, insts, theory, steps, questions, sources, check, chapter=CH_ANA, safety=None):
    return lab(
        id=id, rig=RIG, title=title, group=GROUP, level=LEVEL, topic=chapter, chapter=chapter, aim=aim, kernel=kernel,
        params=params, autorun=True, camera={"pos": [0.0, 0.7, 0.85], "look": [0, 0.05, -0.1]}, floor=-0.03,
        bodies=_bodies(), knobs=knobs, instruments=insts, steps=steps, theory=theory,
        safety=safety or "Bench supplies only, a few volts. Switch the power off before changing a connection.",
        tour=[{"say": "The circuit is on the breadboard; the supply and generator panel is on the left, the scope at the "
                      "back and two multimeters on the right."}],
        questions=questions, sources=sources, check=check)


def _q(q, opts, ans, why):
    return {"q": q, "options": opts, "answer": ans, "why": why}


# ====================================================================================== p-n diode V-I
def pn_diode() -> dict:
    return _mk(
        "u8-pn-diode", "V-I characteristic of a p-n junction diode: forward and reverse bias",
        "Take the forward and reverse V-I characteristic of a silicon junction diode in series with a resistor, and find "
        "its cut-in voltage and its dynamic resistance from the curve.",
        "u8_diode", {"Vs": 1.0, "Rser": 100.0, "Is": 7.03e-9, "n": 1.80, "Rs": 0.034, "Rsh": 1.0e8, "T": 300.0},
        [knob("Vs", "Supply voltage", "Vs", -10, 3, 0.05, 1.0, "V")],
        [inst("v", "readout", "Diode voltage", "V", unit="V", digits=3),
         inst("i", "readout", "Diode current", "I_mA", unit="mA", digits=3),
         inst("gr", "graph", "Current against voltage", "I_mA", x="V", xlabel="V (V)", dots=True)],
        "A p-n junction carries I = I_s (exp(V/(n V_T)) - 1), with V_T = kT/q (25.85 mV at 300 K) and an ideality factor n "
        "between 1 and 2. In forward bias the current is tiny until the voltage nears the cut-in value (about 0.6 V for "
        "silicon, 0.2-0.3 V for germanium), then rises steeply; the body's series resistance straightens the top of the "
        "curve. The slope there gives the dynamic resistance r_d = dV/dI, close to n V_T / I plus the series resistance. In "
        "reverse bias only a small saturation and leakage current flows. Here the cut-in voltage is taken as the voltage at "
        "which the forward current reaches 1 mA.",
        ["Connect the diode in series with the 100 ohm resistor across the bench supply; voltmeter across the diode, "
         "milliammeter (microammeter for reverse bias) in series.",
         "Forward bias: raise the supply in small steps and record the diode voltage and current.",
         "Reverse the diode and record the reverse current up to 10 V.",
         "Plot I against V, find the voltage at 1 mA (the cut-in voltage) and the slope of the steep part."],
        [_q("Why is a resistor placed in series with the diode?", ["To limit the forward current", "To make the diode conduct",
            "To reverse the bias"], 0, "Past the cut-in voltage the current would otherwise be limited only by the supply."),
         _q("Which diode has the lower cut-in voltage?", ["germanium", "silicon", "both the same"], 0,
            "Germanium's smaller band gap gives a much larger saturation current.")],
        [UGC, SEDRA, SZE, MEMO, {"title": "1N4007 SPICE model (Is = 7.03 nA, n = 1.80, Rs = 0.034 ohm)",
                                 "note": "From memory - verify; the widely circulated vendor SPICE model of the 1N4007. The "
                                         "100 Mohm reverse leakage is illustrative"}],
        {"params": {}, "reading": "Vcut", "textbook": "u8_diode_vcut", "tol": 0.01})


# ====================================================================================== Boltzmann constant
def boltzmann() -> dict:
    return _mk(
        "u8-diode-boltzmann", "Boltzmann constant from the V-I characteristic of a junction",
        "Measure the forward current of a diode-connected transistor at several voltages at a known temperature, plot "
        "ln I against V, and find the Boltzmann constant from the slope.",
        "u8_diode", {"Vs": 0.8, "Rser": 1000.0, "Is": 1.0e-14, "n": 1.0, "Rs": 0.3, "Rsh": 1.0e12, "T": 300.0,
                     "kB": 1.380649e-23, "adc": 0.0},
        [knob("Vs", "Supply voltage", "Vs", 0.5, 2, 0.05, 0.8, "V"),
         knob("kB", "Boltzmann constant (hidden)", "kB", 1.0, 2.0, 0.000001, 1.380649, "e-23 J/K", k=1e-23, hidden=True)],
        [inst("v", "readout", "Junction voltage", "V", unit="V", digits=4),
         inst("i", "readout", "Current", "I_mA", unit="mA", digits=4)],
        "In the exponential part of the characteristic I = I_s exp(qV/(n k T)), so ln I = ln I_s + (q/(n k T)) V: a straight "
        "line whose slope gives k = q/(n T x slope). A transistor with its base and collector joined behaves as a junction "
        "with an ideality factor very close to 1, so n = 1 is used. The temperature is the room's, 300 K; the electron's "
        "charge is exact in the SI. Keep the current below about a milliamp so that the series resistance does not bend the "
        "line.",
        ["Join the base and collector of the BC547; connect it in series with 1 kohm across the supply.",
         "Read the room temperature on the thermometer (300 K).",
         "Raise the supply in steps and record the junction voltage and the current (the voltage across 1 kohm divided by "
         "1 kohm).",
         "Plot ln I against V, find the slope and work out k = q / (n T x slope)."],
        [_q("Why is the current kept below about 1 mA?", ["So that the series resistance does not bend the line",
            "To save the battery", "To make the diode cut in"], 0, "I R_s adds to the voltage and lowers the slope."),
         _q("Doubling the absolute temperature makes the slope of ln I against V", ["half as large", "twice as large",
            "unchanged"], 0, "The slope is q/(n k T).")],
        [DU, SI_K, SZE, ILLU, {"title": "Diode-connected BC547: ideality factor close to 1",
                               "note": "From memory - verify; I_s = 10 fA and R_s = 0.3 ohm are illustrative"}],
        {"params": {}, "reading": "kfit", "textbook": "u8_diode_kb", "tol": 0.01}, chapter=CH_ANA)


# ====================================================================================== LED
def led() -> dict:
    return _mk(
        "u8-led-vi", "I-V characteristic of a light-emitting diode and its turn-on voltage",
        "Take the I-V characteristic of a red LED in series with a resistor and find its turn-on voltage.",
        "u8_diode", {"Vs": 2.5, "Rser": 220.0, "Is": 1.0e-18, "n": 2.0, "Rs": 10.0, "Rsh": 1.0e9, "T": 300.0},
        [knob("Vs", "Supply voltage", "Vs", 0, 6, 0.05, 2.5, "V")],
        [inst("v", "readout", "LED voltage", "V", unit="V", digits=3),
         inst("i", "readout", "LED current", "I_mA", unit="mA", digits=3)],
        "An LED is a junction of a wide-gap semiconductor, so its current only becomes appreciable at a much larger forward "
        "voltage than a silicon diode's: about 1.7-2 V for red, more for green and blue. Above that the current rises "
        "exponentially and then almost linearly as the series resistance takes over, and the LED glows. Here the turn-on "
        "voltage is taken as the voltage at which the current reaches 1 mA, the point where the light is clearly seen.",
        ["Connect the LED with the 220 ohm resistor across the supply, voltmeter across the LED, milliammeter in series.",
         "Raise the supply from zero in small steps and record the LED voltage and current; note when it starts to glow.",
         "Plot I against V and read the voltage at 1 mA."],
        [_q("Why does a blue LED need a larger voltage than a red one?", ["Its band gap is larger", "It is brighter",
            "Its resistance is larger"], 0, "The photon energy is close to the band gap, about q V."),
         _q("What limits the current above the turn-on voltage?", ["The series resistor", "The LED's colour",
            "The voltmeter"], 0, "The LED's own voltage hardly changes once it conducts.")],
        [DU, SEDRA, ILLU, {"title": "Red LED model: I_s = 1e-18 A, n = 2, R_s = 10 ohm",
                           "note": "Illustrative values giving about 1.8 V at 1 mA, typical of a red indicator LED"}],
        {"params": {}, "reading": "Vcut", "textbook": "u8_diode_vcut", "tol": 0.01})


# ====================================================================================== tunnel diode
def tunnel() -> dict:
    return _mk(
        "u8-tunnel-diode", "Tunnel diode: I-V characteristic, peak-to-valley ratio and negative resistance",
        "Hold a germanium tunnel diode at voltages from 0 to 0.55 V with a stiff source, record the current, and find the "
        "peak and valley currents, their ratio and the negative resistance between them.",
        "u8_tunnel", {"V": 0.1, "Ip": 1.0e-3, "Vp": 0.065, "Iv": 1.2e-4, "Vv": 0.35, "A2": 15.0, "Is": 1.0e-12, "n": 1.0},
        [knob("V", "Diode voltage", "V", 0, 0.6, 0.005, 0.1, "V")],
        [inst("v", "readout", "Diode voltage", "V", unit="V", digits=3),
         inst("i", "readout", "Diode current", "I_mA", unit="mA", digits=4)],
        "A tunnel diode is so heavily doped that the depletion layer is only a few nanometres wide, and electrons tunnel "
        "straight through it. As the forward voltage rises the tunnel current first grows, peaks (I_p at V_p), then FALLS "
        "as the filled and empty bands slide out of line: a region of negative resistance. At the valley (I_v at V_v) only a "
        "small excess current is left, and beyond it the ordinary diffusion current of a junction takes over. The diode is "
        "held at each voltage by a low-resistance divider, because a series resistor larger than the negative resistance "
        "would make it jump across the falling part.",
        ["Connect the diode across a 10 ohm divider fed from the supply so that its voltage is set directly; milliammeter "
         "in series.",
         "Raise the voltage in small steps from zero and record the current, closely spaced near the peak and the valley.",
         "Plot I against V; read the peak and valley currents and work out the peak-to-valley ratio.",
         "Find the steepest slope of the falling part: its inverse is the negative resistance."],
        [_q("Why must the diode be fed from a low-resistance source?", ["A large series resistance makes it jump across the "
            "negative-resistance region", "To protect the meter", "To make it tunnel"], 0,
            "The load line must be steeper than the falling part."),
         _q("What makes the current fall after the peak?", ["The bands move out of alignment and tunnelling stops",
            "The diode heats up", "The meter saturates"], 0, "Fewer filled states face empty ones.")],
        [DU, SZE, MEMO, {"title": "1N3712-type germanium tunnel diode: I_p = 1 mA, V_p = 65 mV, V_v = 350 mV",
                         "note": "From memory - verify; the excess-current settings (I_v 0.12 mA, A2 = 15 /V) and I_s are "
                                 "illustrative"}],
        {"params": {}, "reading": "Ipk", "textbook": "u8_tunnel_ip", "tol": 0.01}, chapter=CH_ANA)


# ====================================================================================== BJT h-parameters
def bjt_h() -> dict:
    return _mk(
        "u8-bjt-hparams", "h-parameters of a transistor in common-emitter connection",
        "Take the input and output characteristics of an n-p-n transistor in common-emitter connection and find the four "
        "h-parameters h_ie, h_fe, h_oe and h_re at an operating point.",
        "u8_bjt", {"Ib": 2.0e-5, "Vce": 5.0, "Is": 1.0e-14, "bF": 250.0, "VA": 80.0, "VAr": 150.0, "Vsat": 0.05},
        [knob("Ib", "Base current", "Ib", 5, 40, 1, 20, "µA", k=1e-6),
         knob("Vce", "Collector-emitter voltage", "Vce", 1, 10, 0.5, 5, "V")],
        [inst("vb", "readout", "Base-emitter voltage", "Vbe", unit="V", digits=4),
         inst("ic", "readout", "Collector current", "Ic_mA", unit="mA", digits=3)],
        "For small changes about an operating point a transistor is described by v_be = h_ie i_b + h_re v_ce and "
        "i_c = h_fe i_b + h_oe v_ce. So h_ie = dV_BE/dI_B and h_fe = dI_C/dI_B are read at constant V_CE (the input "
        "characteristic and the current transfer), and h_oe = dI_C/dV_CE and h_re = dV_BE/dV_CE at constant I_B (the output "
        "characteristic and the small reverse feedback). The model is the Ebers-Moll transistor in its active region with "
        "the Early effect: h_fe is close to the current gain beta, h_ie close to V_T/I_B, and the slope of the output "
        "characteristic comes from the Early voltage.",
        ["Connect the BC547 in common-emitter connection: base supply through 100 kohm and a microammeter, collector "
         "supply with a milliammeter, voltmeters across base-emitter and collector-emitter.",
         "At V_CE = 5 V, set the base current in steps and record V_BE and I_C.",
         "At I_B = 20 µA, set V_CE in steps and record V_BE and I_C.",
         "From the slopes at the operating point (20 µA, 5 V) find h_ie, h_fe, h_oe and h_re."],
        [_q("h_fe is the slope of", ["I_C against I_B at constant V_CE", "V_BE against I_B", "I_C against V_CE"], 0,
            "It is the small-signal current gain."),
         _q("Why is h_re so small?", ["The collector voltage hardly affects the base-emitter junction",
            "The base current is small", "The emitter is grounded"], 0, "Only base-width modulation couples them.")],
        [UGC, SEDRA, ILLU, {"title": "BC547B-like settings: I_s = 10 fA, beta_F = 250, V_A = 80 V",
                            "note": "Illustrative, inside the BC547B hFE group 200-450 (ON Semiconductor BC546/547/548 data "
                                    "sheet, from memory - verify); the reverse-feedback voltage 150 V is illustrative"}],
        {"params": {}, "reading": "hfe", "textbook": "u8_bjt_hfe", "tol": 0.01}, chapter=CH_ANA)


# ====================================================================================== BJT switch
def bjt_switch() -> dict:
    return _mk(
        "u8-bjt-switch", "Transistor as a switch (NOT gate): transfer characteristic and threshold",
        "Drive an n-p-n transistor's base through a resistor from 0 to 5 V, record the collector voltage, and find the "
        "input voltage at which the output switches through half the supply.",
        "u8_bjt", {"Ib": 2.0e-5, "Vce": 5.0, "Is": 1.0e-14, "bF": 250.0, "VA": 80.0, "VAr": 150.0, "Vsat": 0.05,
                   "Vin": 0.0, "Vcc": 5.0, "Rb": 10000.0, "Rc": 1000.0},
        [knob("Vin", "Input voltage", "Vin", 0, 5, 0.05, 0.0, "V")],
        [inst("vo", "readout", "Output voltage", "Vout", unit="V", digits=3)],
        "With the input low the base carries no current and the transistor is OFF: the collector sits at V_CC, a logic 1. "
        "Once the input passes the base-emitter turn-on voltage, base current I_B = (V_in - V_BE)/R_B flows and the "
        "collector current beta I_B pulls the output down along a steep line, until the transistor saturates and the output "
        "stays at V_CE(sat), a logic 0. So the circuit inverts: a NOT gate. Its threshold, where the output passes V_CC/2, is "
        "V_in = V_BE + R_B (V_CC/2)/(beta R_C).",
        ["Connect the base to the input through R_B = 10 kohm, the collector to +5 V through R_C = 1 kohm.",
         "Set the input to 0 V and 5 V and read the output each time: the truth table of a NOT gate.",
         "Raise the input in small steps through the switching region and record the output.",
         "Plot output against input and find the input at which the output is 2.5 V."],
        [_q("With the input at 5 V the output is", ["low (about 0.1 V)", "high (5 V)", "2.5 V"], 0,
            "The transistor is saturated."),
         _q("A larger R_B makes the threshold", ["higher", "lower", "unchanged"], 0, "More input voltage is needed for the same base current.")],
        [UGC, SEDRA, ILLU, {"title": "BC547B-like settings: beta_F = 250, R_B = 10 kohm, R_C = 1 kohm, V_CC = 5 V",
                            "note": "Illustrative; the threshold check uses a constant beta with no Early effect"}],
        {"params": {}, "reading": "Vth", "textbook": "u8_bjt_vth", "tol": 0.01}, chapter=CH_ANA)


# ====================================================================================== push-pull
def push_pull() -> dict:
    return _mk(
        "u8-push-pull", "Complementary push-pull amplifier: output and crossover distortion",
        "Drive a class B complementary push-pull stage with a sine wave, measure its output and its harmonic distortion at "
        "several input levels, find the dead zone that causes the crossover distortion, and see it shrink in class AB.",
        "u8_pp", {"Vp": 3.0, "Vg": 0.6, "Vbias": 0.55, "mode": 0.0, "RL": 8.0, "f": 1000.0},
        [knob("Vp", "Input peak voltage", "Vp", 0.8, 8, 0.1, 3.0, "V"),
         knob("Vg", "Turn-on voltage (hidden)", "Vg", 0.3, 0.9, 0.01, 0.6, "V", hidden=True)],
        [inst("vo", "readout", "Output peak", "Vop", unit="V", digits=3),
         inst("d", "readout", "Total harmonic distortion", "thd_pct", unit="%", digits=2)],
        "In a class B push-pull stage an n-p-n emitter follower handles the positive half-cycles and a p-n-p one the "
        "negative halves. Neither conducts until the input passes its turn-on voltage V_g, so the output is v_in - V_g, zero, "
        "or v_in + V_g: a flat step at every zero crossing, the crossover distortion. The output peak is V_p - V_g, and the "
        "distortion falls as the drive grows. Two diodes biasing the bases (class AB) remove most of the dead zone. The "
        "model is piecewise linear; the distortion is found from the sampled output by Fourier analysis.",
        ["Connect the complementary pair with the 8 ohm load; channel 1 on the input, channel 2 on the output.",
         "With the bias diodes shorted (class B) set the input peak in steps and record the output peak and the distortion.",
         "Look at the output near each zero crossing: the flat step is the crossover distortion.",
         "Plot output peak against input peak: the line's offset is the turn-on voltage V_g.",
         "Switch the bias diodes in (class AB) and compare the distortion."],
        [_q("Why does crossover distortion matter most at low volume?", ["The dead zone is a larger part of a small signal",
            "The transistors heat up", "The load changes"], 0, "The step has a fixed size V_g."),
         _q("Class AB bias diodes", ["hold both transistors just at turn-on", "double the gain", "remove the load"], 0,
            "So the dead zone almost vanishes.")],
        [DU, SEDRA, ILLU, {"title": "Turn-on voltage 0.6 V and bias-diode drop 0.55 V",
                           "note": "Illustrative piecewise-linear settings typical of small silicon power transistors"}],
        {"params": {}, "reading": "thd", "textbook": "u8_pp_thd", "tol": 0.01})


# ====================================================================================== op-amp frequency response
def opamp_fr() -> dict:
    return _mk(
        "u8-opamp-response", "Op-amp amplifiers: frequency response and gain-bandwidth product",
        "Build inverting and non-inverting amplifiers with a 741 op-amp at several gains, measure the gain against "
        "frequency, find each -3 dB frequency and the gain-bandwidth product.",
        "u8_opa", {"A0": 2.0e5, "fa": 5.0, "R1": 1000.0, "Rf": 10000.0, "cfg": 0.0, "f": 1000.0, "Vin": 0.01},
        [knob("f", "Generator frequency", "f", 10, 3000000, 10, 1000, "Hz"),
         knob("fa", "Open-loop corner (hidden)", "fa", 1, 100, 0.01, 5.0, "Hz", hidden=True)],
        [inst("g", "readout", "Closed-loop gain", "gain", digits=3),
         inst("ph", "readout", "Phase", "ph", unit="°", digits=1)],
        "An op-amp's open-loop gain is huge at DC but falls 20 dB a decade above a corner of a few hertz: A = A_0/(1 + j f/f_a). "
        "Their product, the gain-bandwidth product GBW = A_0 f_a, is fixed by the chip. With feedback fraction beta = R_1/(R_1 + "
        "R_f) the closed-loop gain is flat up to f_3 = GBW beta and then falls; the 'noise gain' 1/beta = 1 + R_f/R_1 sets the "
        "bandwidth for both the inverting (gain R_f/R_1) and the non-inverting (gain 1 + R_f/R_1) connection. So GBW = f_3 (1 + "
        "R_f/R_1): measure it at several gains. Below f_3 a single-pole response gives G = G_0/sqrt(1 + (f/f_3)^2).",
        ["Build the inverting amplifier with R_1 = 1 kohm and R_f = 10 kohm; 10 mV input; channel 1 on the input, channel "
         "2 on the output.",
         "Record the gain from 100 Hz up to beyond the roll-off.",
         "Change R_f to 47 kohm and repeat; then build the non-inverting amplifier and repeat.",
         "For each set find f_3 (where the gain is 0.707 of its low-frequency value) and GBW = f_3 (1 + R_f/R_1)."],
        [_q("Raising the gain ten times makes the bandwidth", ["ten times smaller", "ten times larger", "unchanged"], 0,
            "The gain-bandwidth product is constant."),
         _q("An inverting amplifier of gain 10 has the same bandwidth as a non-inverting one of gain", ["11", "10", "9"], 0,
            "Both have the noise gain 1 + R_f/R_1 = 11.")],
        [DU, SEDRA, MEMO, {"title": "LM741 data sheet (Texas Instruments): open-loop gain about 200 V/mV, unity-gain bandwidth "
                                    "about 1 MHz", "note": "From memory - verify"}],
        {"params": {}, "reading": "gbw", "textbook": "u8_opa_gbw", "tol": 0.01})


# ====================================================================================== difference amplifier
def diff_amp() -> dict:
    return _mk(
        "u8-diff-amp", "Precision difference amplifier: differential gain, common-mode gain and CMRR",
        "Build a four-resistor difference amplifier, measure its gain for a differential input and for a common-mode input, "
        "and find its common-mode rejection ratio.",
        "u8_diff", {"R1": 10000.0, "R2": 100000.0, "R3": 10000.0, "R4": 100000.0, "eps": 0.004, "A0": 2.0e5,
                    "Vd": 0.1, "Vc": 1.0, "mode": 0.0},
        [knob("Vd", "Differential input", "Vd", 0.02, 0.5, 0.01, 0.1, "V"),
         knob("eps", "Resistor mismatch (hidden)", "eps", -0.02, 0.02, 0.0001, 0.004, "", hidden=True)],
        [inst("vo", "readout", "Output voltage", "Vout", unit="V", digits=4)],
        "A difference amplifier amplifies V_2 - V_1 by R_2/R_1 when R_4/R_3 = R_2/R_1 exactly. Any mismatch lets a voltage "
        "common to both inputs through: A_cm = R_4'/(R_3 + R_4') (1 + R_2/R_1) - R_2/R_1, about (R_2/R_1)/(1 + R_2/R_1) times "
        "the fractional mismatch. The common-mode rejection ratio CMRR = A_d/A_cm (often in dB, 20 log10) measures how well "
        "the circuit ignores hum and offsets common to both inputs. With 1 % resistors it is set far more by the resistors "
        "than by the op-amp; precision difference amplifiers use matched resistor networks for that reason.",
        ["Build the amplifier with R_1 = R_3 = 10 kohm and R_2 = R_4 = 100 kohm (1 % resistors).",
         "Apply a differential signal (V_2 = +V_d/2, V_1 = -V_d/2) at several levels and record the output: A_d = V_out/V_d.",
         "Tie both inputs together to a 1 V common signal and record the (small) output: A_cm = V_out/V_cm.",
         "Work out CMRR = A_d/A_cm and in decibels."],
        [_q("What sets the CMRR here?", ["The mismatch between the resistor ratios", "The supply voltage",
            "The input level"], 0, "A perfect match would cancel the common-mode signal."),
         _q("A CMRR of 2000 is about", ["66 dB", "33 dB", "2000 dB"], 0, "20 log10 2000 = 66.")],
        [DU, GAYAKWAD, ILLU, {"title": "Resistor mismatch 0.4 % (within 1 % tolerance) and open-loop gain 200 V/mV",
                              "note": "Illustrative; the op-amp's own common-mode rejection is much higher and is left out"}],
        {"params": {}, "reading": "Acm", "textbook": "u8_diff_acm", "tol": 0.01})


# ====================================================================================== analog computer
def analog_computer() -> dict:
    return _mk(
        "u8-analog-computer", "Op-amp analog computer: simultaneous and differential equations",
        "Wire op-amp summers and integrators to solve a pair of simultaneous equations, a first-order and a second-order "
        "differential equation, read each solution on the scope, and find the integrator resistor from the time constants.",
        "u8_acomp", {"cfg": 2.0, "R": 100000.0, "C": 1.0e-7, "a1": 2.0, "b1": 1.0, "c1": 5.0, "a2": 1.0, "b2": 3.0,
                     "c2": 10.0, "V0": 5.0, "z": 0.2},
        [knob("C", "Integrator capacitor", "C", 1e-8, 1e-6, 1e-9, 1e-7, "F"),
         knob("R", "Integrator resistor (hidden)", "R", 10000, 1000000, 100, 100000, "Ω", hidden=True)],
        [inst("rc", "readout", "Integrator time constant", "rc", unit="s", digits=5)],
        "An integrator of resistor R and capacitor C gives V_out = -(1/RC) integral of V_in dt, and a summer adds "
        "weighted voltages. Wired in a loop they solve equations. Simultaneous equations a1 x + b1 y = c1, a2 x + b2 y = c2: "
        "two integrators driven by the error of each equation settle where both errors vanish, at the solution. A first-order "
        "equation RC dv/dt = -v gives a decay v = V_0 exp(-t/RC). Two integrators and an inverter in a ring solve "
        "x'' + 2 zeta w x' + w^2 x = 0 with w = 1/RC: a damped oscillation of frequency sqrt(1 - zeta^2)/(2 pi RC). The time "
        "constant and the frequency both measure RC.",
        ["Simultaneous equations: patch the two integrators and summers for 2x + y = 5, x + 3y = 10 and read x and y.",
         "First order: patch one integrator with feedback, charge it to 5 V, release and time the fall to 1/e of the start.",
         "Second order: patch the two-integrator loop with damping 0.2, release from 5 V and time the oscillation.",
         "Repeat the time-constant runs with other capacitors and find R from tau = RC and f = sqrt(1 - zeta^2)/(2 pi RC)."],
        [_q("Doubling C makes the oscillation", ["half as fast", "twice as fast", "unchanged"], 0, "w = 1/RC."),
         _q("The steady outputs of the simultaneous-equation circuit are", ["the solution x and y", "zero",
            "the coefficients"], 0, "The integrators stop when both equations are satisfied.")],
        [DU, GAYAKWAD, ILLU, {"title": "Integrator resistor 100 kohm, damping 0.2 and the equation coefficients",
                              "note": "Illustrative choices; the integration is an RK4 solution of the circuit's equations"}],
        {"params": {}, "reading": "fd", "textbook": "u8_acomp_fd", "tol": 0.01})


# ====================================================================================== active filters
def active_filters() -> dict:
    return _mk(
        "u8-active-filters", "Active filters: second-order Sallen-Key low-pass cut-off frequency",
        "Build a second-order active filter of a given cut-off, measure its gain against frequency, and find the cut-off "
        "frequency from the -3 dB point.",
        "u8_filt", {"kind": 0.0, "R": 10000.0, "C": 1.0e-8, "K": 1.586, "Q": 2.0, "f": 1000.0},
        [knob("f", "Generator frequency", "f", 10, 200000, 1, 1000, "Hz")],
        [inst("g", "readout", "Gain", "gain", digits=3), inst("f0", "readout", "Design frequency", "f0", unit="Hz", digits=1)],
        "A second-order filter has the response 1 - x^2 + j x/Q in its denominator, x = f/f_0, f_0 = 1/(2 pi R C). The equal-"
        "component Sallen-Key circuit sets Q = 1/(3 - K) through the op-amp's gain K; K = 1.586 gives Q = 0.707, the "
        "Butterworth response, whose -3 dB frequency is f_0 itself. The low-pass passes low frequencies with gain K and "
        "falls 40 dB a decade above f_0; the high-pass is its mirror image; a band-pass of quality Q passes a band of width "
        "f_0/Q between two -3 dB edges; a band-reject (notch) filter removes that band. The cut-off is where the gain is "
        "1/sqrt 2 (-3 dB) of the pass-band gain.",
        ["Build the filter with R = 10 kohm and C = 10 nF and the op-amp gain set by 5.86 kohm and 10 kohm.",
         "Apply a 1 V sine; record the output and the gain from a tenth to ten times f_0, closely spaced near f_0.",
         "Plot gain in dB against log frequency and find the frequency at which the gain is 3 dB below the pass band.",
         "Compare it with 1/(2 pi R C)."],
        [_q("Above the cut-off a second-order low-pass falls by", ["40 dB a decade", "20 dB a decade", "6 dB a decade"], 0,
            "Two reactive elements give two poles."),
         _q("A band-pass of Q = 2 at 1.6 kHz has a bandwidth of about", ["800 Hz", "3.2 kHz", "1.6 kHz"], 0, "B = f_0/Q.")],
        [DU, GAYAKWAD, SEDRA, {"title": "IEC 60063 preferred values (E12 / E24) for every resistor and capacitor"}],
        {"params": {}, "reading": "fc", "textbook": "u8_filt_fc", "tol": 0.01}, chapter=CH_ANA)


# ====================================================================================== JFET CS amplifier
def jfet_cs() -> dict:
    return _mk(
        "u8-jfet-cs", "Common-source JFET amplifier: gain and frequency response",
        "Bias an n-channel JFET with a source resistor, measure the gain of the common-source amplifier from 10 Hz to "
        "10 MHz, and find its mid-band gain and bandwidth.",
        "u8_jfet", {"Vdd": 15.0, "Idss": 0.010, "Vp": -4.0, "Rs": 680.0, "Rd": 2200.0, "RL": 10000.0, "Rg": 1.0e6,
                    "Rsig": 10000.0, "Cin": 1.0e-7, "Cout": 1.0e-6, "Cs": 2.2e-5, "Cgs": 4.0e-12, "Cgd": 1.0e-12, "f": 10000.0},
        [knob("f", "Generator frequency", "f", 10, 10000000, 10, 10000, "Hz")],
        [inst("id", "readout", "Drain current", "Id_mA", unit="mA", digits=3),
         inst("vg", "readout", "Gate-source voltage", "Vgs", unit="V", digits=3),
         inst("gm", "readout", "Transconductance", "gm_mS", unit="mS", digits=3)],
        "A JFET's drain current follows the square law I_D = I_DSS (1 - V_GS/V_P)^2. With a source resistor the gate sits at "
        "0 V and V_GS = -I_D R_S, which fixes the operating point. Its transconductance is g_m = (2 I_DSS/|V_P|)(1 - V_GS/V_P), "
        "and the mid-band gain of the common-source stage is -g_m (R_D || R_L). The coupling capacitors and the source "
        "bypass capacitor set the lower -3 dB frequency; the gate capacitances, the gate-drain one multiplied by the gain "
        "(the Miller effect), set the upper one. The bandwidth is the difference.",
        ["Check the bias with no signal: measure I_D and V_GS.",
         "Apply a small sine through the 10 kohm source resistor; channel 1 on the input, channel 2 on the output.",
         "Record the gain at frequencies from 10 Hz to 10 MHz, closer together near each roll-off.",
         "Plot gain in dB against log frequency; find the mid-band gain and the two -3 dB frequencies."],
        [_q("The output of a common-source amplifier is", ["inverted", "in phase", "a quarter cycle late"], 0,
            "Its gain is -g_m R_D'."),
         _q("What sets the upper -3 dB frequency here?", ["The gate capacitances, magnified by the Miller effect",
            "The coupling capacitors", "The source resistor"], 0, "C_gd appears multiplied by 1 + g_m R_L'.")],
        [DU, SEDRA, MEMO, {"title": "BFW10 n-channel JFET data sheet: I_DSS 8-20 mA, V_GS(off) up to -8 V",
                           "note": "From memory - verify; I_DSS = 10 mA, V_P = -4 V and the gate capacitances are "
                                   "illustrative settings inside that range"}],
        {"params": {}, "reading": "Amid", "textbook": "u8_jfet_amid", "tol": 0.01})


# ====================================================================================== DAC
def dac() -> dict:
    return _mk(
        "u8-dac", "R-2R ladder digital-to-analog converter of a given step size",
        "Build a 4-bit R-2R ladder DAC with an op-amp buffer designed for a 0.5 V step, set every input code with the "
        "switches, record the output, and find the step size (resolution) and full-scale output.",
        "u8_dac", {"D": 9.0, "Vref": 5.0, "R": 10000.0, "Rf": 6200.0, "Rg": 10000.0},
        [knob("D", "Input code", "D", 0, 15, 1, 9, "")],
        [inst("vo", "readout", "Output voltage", "Vout", unit="V", digits=4)],
        "In an R-2R ladder every bit switches its 2R leg between V_ref and ground. Seen from the far end each section halves "
        "the voltage passed along it, so the MSB node carries V_ref D/2^n for the binary code D: the voltage is weighted by "
        "the bits without any resistor other than R and 2R. A non-inverting buffer of gain 1 + R_f/R_g scales the output to "
        "the specification. For a 4-bit converter with V_ref = 5 V and a 0.5 V step the gain must be 1.6; the nearest E24 "
        "pair, 6.2 kohm and 10 kohm, gives 1.62.",
        ["Build the ladder with R = 10 kohm and 2R = 20 kohm, the four switches feeding 5 V or 0 V, and the buffer.",
         "Set each code from 0000 to 1111 with the switches and record the output.",
         "Plot the output against the code; the slope is the step size (one LSB) and the top is full scale.",
         "Compare the step with V_ref (1 + R_f/R_g) / 16."],
        [_q("The resolution of a 4-bit DAC is one part in", ["16", "4", "256"], 0, "2^4 = 16 levels."),
         _q("Why is an R-2R ladder preferred to binary-weighted resistors?", ["It needs only two resistor values",
            "It is faster", "It uses no op-amp"], 0, "Matching two values is far easier than eight or more.")],
        [DU, GAYAKWAD, {"title": "IEC 60063 E24 values for R_f and R_g"}, ILLU],
        {"params": {}, "reading": "Vout", "textbook": "u8_dac_v", "tol": 0.01})


# ====================================================================================== ADC
def adc() -> dict:
    return _mk(
        "u8-adc", "Analog-to-digital converter IC: transfer characteristic and step size",
        "Feed known voltages into an 8-bit successive-approximation ADC IC, read the output code on its LEDs, and find the "
        "step size and the span from the transfer characteristic.",
        "u8_adc", {"Vin": 2.0, "Vref": 5.0},
        [knob("Vin", "Input voltage", "Vin", 0, 5, 0.01, 2.0, "V")],
        [inst("c", "readout", "Output code", "code", digits=0)],
        "A successive-approximation converter finds the code one bit at a time: it tries the MSB, compares the input with "
        "the trial level from its internal DAC, keeps the bit if the input is at least as large, and moves on to the next "
        "bit; eight comparisons give an 8-bit code. On the ADC0804 the voltage on its Vref/2 pin sets the span, so 2.5 V "
        "there gives a 0-5 V input range and one LSB of 5/256 = 19.5 mV. Its levels sit half an LSB low, so each code is the "
        "nearest one. The code rises in a staircase with the input; the slope of the staircase is 1/LSB.",
        ["Set 2.5 V on the Vref/2 pin, start the free-running conversion, and connect the input potentiometer.",
         "Set the input in steps from 0.2 V to 4.8 V, read the eight LEDs and write the code in decimal.",
         "Plot the code against the input voltage and fit a straight line.",
         "The step size is 1/slope; compare it with Vref/256."],
        [_q("An 8-bit ADC with a 5 V span has a step of about", ["19.5 mV", "5 mV", "0.63 V"], 0, "5 V/256."),
         _q("How many comparisons does a successive-approximation ADC need for 8 bits?", ["8", "256", "1"], 0,
            "One for each bit.")],
        [UGC, GAYAKWAD, MEMO, {"title": "ADC0804 data sheet (National / Texas Instruments): 8-bit SAR converter, span set by "
                                        "the Vref/2 pin", "note": "From memory - verify"}],
        {"params": {}, "reading": "code", "textbook": "u8_adc_code", "tol": 0.01})


# ====================================================================================== sample and hold
def sample_hold() -> dict:
    return _mk(
        "u8-sample-hold", "Sample-and-hold circuit: acquisition time, droop and the hold capacitor",
        "Close the sampling switch of a sample-and-hold onto a DC level, measure the acquisition time with the scope's "
        "cursors for several source resistors, find the hold capacitor, and read the droop while holding.",
        "u8_sh", {"Vs": 2.0, "Rsrc": 1000.0, "Ron": 125.0, "Ch": 1.0e-8, "Ileak": 1.0e-9},
        [knob("Rsrc", "Source resistor", "Rsrc", 100, 22000, 100, 1000, "Ω"),
         knob("Ch", "Hold capacitor (hidden)", "Ch", 1e-9, 1e-7, 1e-10, 1e-8, "F", hidden=True)],
        [inst("t", "readout", "Charging time constant", "tau_us", unit="µs", digits=2)],
        "A sample-and-hold has an analog switch in series with a capacitor, followed by a buffer. While the switch is closed "
        "(sample) the capacitor charges towards the input through the source and switch resistance, V_s (1 - exp(-t/tau)) "
        "with tau = (R_src + R_on) C_h; the time from 10 % to 90 % of the step, tau ln 9, is the acquisition time. When the "
        "switch opens (hold) the capacitor keeps the voltage, apart from a slow droop I_leak/C_h from leakage. A larger "
        "capacitor droops less but acquires more slowly: the design trade-off.",
        ["Connect the 2 V level through the source resistor to the CD4066 switch and the hold capacitor, buffered.",
         "Channel 1 on the sampling pulse, channel 2 on the capacitor. Trigger on the pulse.",
         "Measure the 10 % to 90 % rise of channel 2 with the cursors; repeat for several source resistors.",
         "Find C_h = t_acq / ((R_src + R_on) ln 9) and read the droop rate while holding."],
        [_q("A larger hold capacitor gives", ["less droop but slower acquisition", "more droop", "faster acquisition"], 0,
            "Droop is I/C; acquisition is RC."),
         _q("The 10-90 % rise of an RC charge takes", ["2.2 RC", "RC", "0.69 RC"], 0, "ln 9 = 2.197.")],
        [DU, GAYAKWAD, MEMO, {"title": "CD4066B data sheet: on-resistance about 125 ohm at V_DD = 10 V",
                              "note": "From memory - verify; the 1 nA leakage and the hold capacitor are illustrative"}],
        {"params": {}, "reading": "tau", "textbook": "u8_sh_tau", "tol": 0.01}, chapter=CH_INS)


# ====================================================================================== 7805 supply
def reg7805() -> dict:
    return _mk(
        "u8-regulated-supply", "Regulated 5 V supply with a bridge and a 7805: line and load regulation",
        "Build a 5 V adapter from a transformer secondary, a bridge rectifier, a reservoir capacitor and a 7805 regulator; "
        "measure its output as the input and the load change, and find its line and load regulation and where it drops out.",
        "u8_reg", {"Vsec": 15.0, "f": 50.0, "Cf": 2.2e-3, "Io": 0.5, "Iq": 0.005, "Vf": 0.85, "Vnom": 5.0, "kl": 1.7e-4,
                   "Ro": 0.01, "Vdo": 2.0},
        [knob("Io", "Load current", "Io", 0.1, 1.0, 0.05, 0.5, "A"),
         knob("Ro", "Output resistance (hidden)", "Ro", 0.001, 0.1, 0.0005, 0.01, "Ω", hidden=True)],
        [inst("vi", "readout", "Regulator input (DC)", "Vin", unit="V", digits=3),
         inst("vo", "readout", "Output voltage", "Vout", unit="V", digits=4)],
        "The bridge rectifies both halves of the secondary's sine; the reservoir capacitor holds it near the peak sqrt 2 V_sec "
        "minus two diode drops, sagging by a ripple of about I/(2 f C) between charging pulses. The 7805 keeps 5 V out as long "
        "as its input stays about 2 V above the output (its dropout); below that the output follows the input's valleys "
        "down. Line regulation is the output's change per volt of input change; load regulation is the output's change from "
        "light to full load, an output resistance of a few milliohms.",
        ["Wire the bridge, the 2200 µF reservoir capacitor and the 7805 on the transformer's secondary; the primary is in a "
         "closed box and is never touched.",
         "At 0.25 A load, switch the secondary taps from 9 V to 18 V and record the regulator's input and output.",
         "On the 15 V tap, change the load from 0.1 A to 1 A and record the output.",
         "Find the line regulation (mV per volt) and the load regulation (output resistance); note any reading in dropout."],
        [_q("Why does the output fall on the 9 V tap at full load?", ["The ripple valleys go below the dropout voltage",
            "The 7805 overheats", "The diodes reverse"], 0, "The regulator needs about 2 V of headroom."),
         _q("A larger reservoir capacitor", ["reduces the ripple", "raises the output to 6 V", "increases the dropout"], 0,
            "Ripple is about I/(2 f C).")],
        [DU, MEMO, {"title": "LM7805 data sheet: line regulation 3 mV typical (7-25 V in), load regulation 15 mV typical "
                             "(5 mA-1.5 A), dropout 2 V", "note": "From memory - verify; the 0.85 V diode drop and 5 mA "
                                                                    "quiescent current are illustrative"}],
        {"params": {}, "reading": "line", "textbook": "u8_reg_line", "tol": 0.01},
        safety="The transformer's primary is wired inside a closed, fused box: work only on its low-voltage secondary. "
               "Switch off before changing a connection.")


# ====================================================================================== PLL
def pll() -> dict:
    return _mk(
        "u8-pll", "Phase-locked loop IC (565): free-running frequency, lock range and capture range",
        "Feed a 565 phase-locked loop from a generator, sweep the input out from the centre to find the lock range, and "
        "sweep it in from outside to find the capture range.",
        "u8_pll", {"R1": 6800.0, "C1": 1.0e-8, "C2": 1.0e-6, "V": 10.0, "fin": 4500.0, "mode": 0.0},
        [knob("fin", "Generator frequency", "fin", 100, 20000, 1, 4500, "Hz"),
         knob("C1", "Timing capacitor", "C1", 1e-9, 1e-7, 1e-10, 1e-8, "F")],
        [inst("f0", "readout", "Free-running frequency", "f0", unit="Hz", digits=1)],
        "A PLL locks a voltage-controlled oscillator to an input. A phase detector compares the two; its output, smoothed by "
        "the loop filter, pulls the VCO's frequency towards the input's. The 565's VCO runs free at f_0 = 0.3/(R_1 C_1). Once "
        "locked it follows the input over the lock range f_0 +- f_L, f_L = 8 f_0/V (V the total supply); starting unlocked it "
        "can only pull in over the smaller capture range +- f_C, which the loop filter (3.6 kohm inside the chip with C_2) "
        "limits; a textbook estimate is f_C = (1/2 pi) sqrt(2 pi f_L/tau). The model here is the loop's averaged phase "
        "equation, integrated step by step.",
        ["Connect the 565 with R_1 = 6.8 kohm, C_1 = 10 nF and C_2 = 1 µF on +-5 V; read the free-running frequency at pin 4.",
         "Apply a 1 V input at f_0 and confirm lock: the VCO follows the input.",
         "Raise the input slowly until lock is lost, then lower it back through f_0 to the lower edge: the lock range.",
         "From well outside, sweep the input towards f_0 until the loop captures it, on both sides: the capture range."],
        [_q("Which is wider?", ["the lock range", "the capture range", "they are equal"], 0,
            "Starting unlocked, the filtered beat note is too weak to pull the VCO far."),
         _q("A larger C_2 makes the capture range", ["smaller", "larger", "unchanged"], 0,
            "It filters the beat note more strongly.")],
        [DU, GAYAKWAD, MEMO, {"title": "NE565 data sheet: f_0 = 0.3/(R_1 C_1), lock range +-8 f_0/V, internal 3.6 kohm filter "
                                       "resistor", "note": "From memory - verify; K_d = 1 V is a normalisation of the model"}],
        {"params": {}, "reading": "lock", "textbook": "u8_pll_lock", "tol": 0.01}, chapter=CH_ANA)


# ====================================================================================== universal counter
def counter() -> dict:
    return _mk(
        "u8-counter", "Universal counter: frequency, time period and average period of a signal",
        "Measure an oscillator's frequency with a universal counter at several gate times, its period and its period "
        "averaged over many cycles, and compare the resolution of each mode.",
        "u8_count", {"f": 1234.5678, "ph": 0.37, "ps": 0.61, "fclk": 1.0e7, "Tg": 1.0, "Np": 1.0},
        [knob("Tg", "Gate time", "Tg", 0.01, 10, 0.01, 1.0, "s"),
         knob("f", "Oscillator frequency (hidden)", "f", 100, 10000, 0.0001, 1234.5678, "Hz", hidden=True)],
        [inst("f", "readout", "Counter display", "f", unit="Hz", digits=2)],
        "A universal counter counts edges. In frequency mode it opens a gate for a time T_g from its crystal time base and "
        "counts the input's cycles: f = N/T_g, uncertain by one count, so a longer gate gives a finer answer (1 s gives 1 Hz, "
        "10 s gives 0.1 Hz). In period mode the input's own edges open the gate for one cycle and the counter totals its 10 MHz "
        "clock: T = M/f_clk, uncertain by 0.1 µs. Averaging over N_p periods divides that uncertainty by N_p. Low frequencies "
        "are measured better by period, high frequencies by frequency.",
        ["Connect the oscillator to input A and let the counter warm up.",
         "In frequency mode read the display at gate times 0.01, 0.1, 1 and 10 s.",
         "In period mode read one period, then the average over 10, 100 and 1000 periods.",
         "Work out the frequency from each reading and compare the resolutions."],
        [_q("A 10 s gate measures a frequency to about", ["0.1 Hz", "10 Hz", "1 Hz"], 0, "One count in 10 s."),
         _q("For a 50 Hz signal the better mode is", ["period averaging", "frequency with a 0.1 s gate", "both equal"], 0,
            "A 0.1 s gate counts only 5 cycles.")],
        [DU, ILLU, {"title": "Counter with a 10 MHz time base; the oscillator frequency and the phases at which the gates "
                             "open are illustrative"}],
        {"params": {}, "reading": "f1", "textbook": "u8_count_f", "tol": 0.01}, chapter=CH_INS)


# ====================================================================================== distortion factor meter
def distortion() -> dict:
    return _mk(
        "u8-distortion-meter", "Distortion factor meter: harmonic distortion of a signal generator",
        "Set the reference level of a distortion factor meter on a signal generator's output, tune its notch to null the "
        "fundamental, and read the generator's distortion factor.",
        "u8_dfm", {"V1": 1.0, "h2": 0.03, "h3": 0.02, "h4": 0.005, "h5": 0.004, "f0": 100000.0, "Q": 10.0, "fn": 100000.0},
        [knob("fn", "Notch tuning", "fn", 50000, 200000, 10, 100000, "Hz"),
         knob("h2", "Second harmonic (hidden)", "h2", 0, 0.2, 0.0001, 0.03, "", hidden=True)],
        [inst("d", "readout", "Meter reading", "D_pct", unit="%", digits=2)],
        "A signal generator's sine is never pure: harmonics at 2f, 3f ... ride on it. A distortion factor meter first reads "
        "the total rms (set to the 100 % reference), then switches in a sharp notch filter tuned to the fundamental. When "
        "the notch is tuned exactly, only the harmonics (and noise) remain, and the meter reads the distortion factor "
        "D = sqrt(V_2^2 + V_3^2 + ...)/V_total. Mistuning lets part of the fundamental through, so the reading is a minimum "
        "at the right setting. A notch of finite Q also trims the second harmonic slightly.",
        ["Connect the generator's 100 kHz output to the meter; set the meter to SET LEVEL and adjust to 100 %.",
         "Switch to DISTORTION and tune the notch through the fundamental, recording the reading at each setting.",
         "The minimum reading is the distortion factor; note it in per cent."],
        [_q("Why is the reading a minimum at one setting?", ["Only then is the fundamental removed", "The meter saturates",
            "The harmonics vanish"], 0, "Away from it, part of the fundamental passes."),
         _q("A distortion factor of 3.7 % means the harmonics' rms is about", ["3.7 % of the total rms", "37 %",
            "3.7 dB"], 0, "D is a ratio of rms values.")],
        [DU, ILLU, {"title": "Generator harmonics 3 %, 2 %, 0.5 % and 0.4 %, notch Q = 10",
                    "note": "Illustrative levels for a bench generator; the relations are the textbook ones"}],
        {"params": {}, "reading": "Dbest", "textbook": "u8_dfm_d", "tol": 0.01}, chapter=CH_INS)


# ====================================================================================== thermostat
def thermostat() -> dict:
    return _mk(
        "u8-thermostat", "Thermostat: switching temperatures, set point and hysteresis",
        "Let an on-off thermostat control a heated water bath, read the temperatures at which it switches the heater off "
        "and on for several dial settings, and find its set points, its hysteresis and the cycle times.",
        "u8_tstat", {"D": 50.0, "a": 1.5, "b": 0.97, "H": 3.0, "P": 500.0, "hA": 10.0, "Cth": 4186.0, "Ta": 25.0},
        [knob("D", "Dial setting", "D", 30, 65, 1, 50, "°C"),
         knob("H", "Hysteresis (hidden)", "H", 0.5, 8, 0.1, 3.0, "°C", hidden=True)],
        [inst("ts", "readout", "True set point", "Tset", unit="°C", digits=1)],
        "An on-off thermostat switches the heater off when the temperature rises to its upper point and back on when it has "
        "fallen to its lower point; the gap between them, the hysteresis (differential), stops it chattering. The set point "
        "is midway, and how far it sits from the dial's marking is the dial's calibration. Between switchings the bath warms "
        "towards T_a + P/(hA) or cools towards the room, exponentially with time constant C/(hA), so the heating time is "
        "tau ln((T_inf - T_on)/(T_inf - T_off)).",
        ["Fill the bath with 1 kg of water, fit the thermometer beside the thermostat's bulb and switch the heater on.",
         "At each dial setting let the temperature cycle; read the thermometer when the relay clicks off and on, and time "
         "each half cycle.",
         "Repeat for several dial settings.",
         "Find the hysteresis (upper minus lower point), the true set point against the dial, and the heating and cooling "
         "times."],
        [_q("Hysteresis in a thermostat", ["prevents rapid on-off switching", "makes it more accurate", "is a fault"], 0,
            "Without it the relay would chatter near the set point."),
         _q("Raising the heater power makes the heating time", ["shorter", "longer", "unchanged"], 0,
            "T_inf moves further above the switching points.")],
        [DU, ILLU, {"title": "Specific heat of water 4186 J/(kg K) (handbook value); heater 500 W, loss 10 W/K, dial "
                             "calibration and 3 C hysteresis are illustrative"}],
        {"params": {}, "reading": "theat", "textbook": "u8_tstat_theat", "tol": 0.01}, chapter=CH_INS,
        safety="The heater runs from a low-voltage supply in an insulated bath; do not touch the bath while it is hot.")


# ====================================================================================== cable noise pick-up
def cable_noise() -> dict:
    return _mk(
        "u8-cable-noise", "Noise pick-up in cables and the importance of grounding: an unshielded wire",
        "Run a signal cable beside a wire carrying a strong signal, measure the noise picked up at several frequencies with "
        "the shield grounded and floating, and find the coupling capacitance.",
        "u8_noise", {"V1": 10.0, "f": 10000.0, "R": 10000.0, "C12": 5.0e-12, "C2g": 1.0e-10, "k": 1.0, "sg": 1.0},
        [knob("f", "Aggressor frequency", "f", 100, 100000, 100, 10000, "Hz"),
         knob("C12", "Coupling capacitance (hidden)", "C12", 0.1, 50, 0.01, 5, "pF", k=1e-12, hidden=True)],
        [inst("vn", "readout", "Picked-up noise", "VN_mV", unit="mV", digits=3)],
        "A changing voltage on one conductor drives current through the stray capacitance C_12 to a nearby wire; across the "
        "receiving circuit's resistance R it appears as noise V_N = j w R C_12 V_1 / (1 + j w R (C_12 + C_2g)), growing in "
        "proportion to frequency while w R C stays small. A shield placed round the wire and GROUNDED intercepts the field: "
        "only the uncovered part of C_12 is left. A FLOATING shield does almost nothing, because it simply passes the "
        "coupling on; that is why a shield must be grounded (at one end, to avoid a ground loop). The model is the electric-"
        "field coupling only; magnetic pick-up in ground loops is a separate effect.",
        ["Lay the test cable alongside the aggressor wire fed with 10 V from the generator; terminate it in 10 kohm.",
         "Record the noise amplitude on the scope at several frequencies with the shield grounded.",
         "Disconnect the shield's ground (floating) and repeat.",
         "From the grounded readings find the effective coupling capacitance C = V_N/(2 pi f R V_1)."],
        [_q("Why must a shield be grounded?", ["A floating shield passes the coupling on", "To carry the signal",
            "To heat the cable"], 0, "Grounded, it returns the coupled current to ground."),
         _q("Doubling the aggressor frequency makes the capacitive noise", ["about twice as large", "half", "unchanged"], 0,
            "V_N is about w R C V_1.")],
        [DU, ILLU, {"title": "H. W. Ott, Electromagnetic Compatibility Engineering (Wiley 2009): capacitive coupling between "
                             "two conductors", "note": "Cited from memory - verify"},
         {"title": "Coupling 5 pF, stray 100 pF and the shields' uncovered fractions",
          "note": "Illustrative values, not measured cable data"}],
        {"params": {}, "reading": "VN", "textbook": "u8_noise_vn", "tol": 0.01}, chapter=CH_INS)


BUILDERS = (pn_diode, boltzmann, led, tunnel, bjt_h, bjt_switch, push_pull, opamp_fr, diff_amp, analog_computer,
            active_filters, jfet_cs, dac, adc, sample_hold, reg7805, pll, counter, distortion, thermostat, cable_noise)
