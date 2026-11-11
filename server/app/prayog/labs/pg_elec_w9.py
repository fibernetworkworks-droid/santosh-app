"""Lab pack `pg_elec_w9`: M.Sc. ELECTRONICS set-ups of `syllabus/physics/pg.json` (wave 9, chapter "Electronics"). The
physics is in `packs/pg_elec_w9.py` and its JavaScript twin; every lab here runs on ONE studio rig:

  rig `pe9-elec-bench`  a breadboard whose parts follow the lab, a supply / generator / settings panel whose dials the
                        hand turns, two digital multimeters and a two-channel digital storage scope (waveforms, a
                        spectrum or an X-Y plot of the readings). Every number on it comes from the lab's own kernel.

Each set-up's methods (or conditions) are VARIANTS of one base lab in `families/<base>.json`, so the syllabus row is
covered method by method. Every lab's `check` compares one reading the kernel finds on its own simulated circuit
(bisection, a golden-section search, a sampled waveform, a DFT, an RK4 run, a bit-by-bit SAR loop) with an exact
textbook relation. Device constants are either a named data sheet's typical value, written "from memory - verify"
because they were not looked up for this build, or plainly "illustrative". Low-voltage bench supplies only.
"""
from __future__ import annotations

from ..catalog import B, board, dial, inst, knob, lab

GROUP = "Physics · Electronics"
LEVEL = "M.Sc. Physics"
CH = "Electronics"
RIG = "pe9-elec-bench"

DU = {"title": "University of Delhi M.Sc. Physics (2025): PH-DSE5114 Electronics laboratory and PH-DSE5163 Advanced "
               "electronics laboratory lists"}
MLSU = {"title": "MLSU M.Sc. Physics semester III: Advance Electronics Lab list"}
SGGU = {"title": "SGGU M.Sc. Physics (2023): MSC1P209 / MSC1P210 laboratory lists"}
SEDRA = {"title": "A. S. Sedra and K. C. Smith, Microelectronic Circuits (op-amp circuits, single-pole frequency "
                  "response, output stages, regulators)", "note": "Cited from memory - verify chapter and edition"}
GAYAKWAD = {"title": "R. A. Gayakwad, Op-Amps and Linear Integrated Circuits (comparators, detectors, integrator, "
                     "generators, op-amp parameters, analog computation, converters)",
            "note": "Cited from memory - verify chapter and edition"}
MILLMAN = {"title": "J. Millman and H. Taub, Pulse, Digital and Switching Waveforms (sweep circuits, multivibrators)",
           "note": "Cited from memory - verify chapter and edition"}
KENNEDY = {"title": "G. Kennedy and B. Davis, Electronic Communication Systems (AM, FM, Bessel side-bands, Carson's rule)",
           "note": "Cited from memory - verify chapter and edition"}
MALVINO = {"title": "A. P. Malvino and D. J. Bates, Electronic Principles (zener and series regulators, class A and B "
                    "power amplifiers, tuned amplifiers, crystal oscillators)", "note": "Cited from memory - verify"}
DIGITAL = {"title": "M. M. Mano, Digital Design (asynchronous and synchronous counters, propagation delay)",
           "note": "Cited from memory - verify"}
ILLU = {"title": "Illustrative settings", "note": "Values marked illustrative are lab settings chosen to be typical, not "
        "taken from a table; the relations that produce the readings are the textbook ones"}
MEMO = {"title": "Device constants from memory - verify", "note": "Typical data-sheet values written from memory for this "
        "build and not looked up; check them against the named data sheet before relying on them"}
SIMNOTE = ("The circuit is a computed model, not a measured instrument: every reading is worked out by the lab's own "
           "kernel from the component values.")


def _bodies() -> list[dict]:
    out = [board(1.1, 0.62),
           B("panel", "box", name="Supply, generator and settings panel", info="The dials the hand turns.",
             size=[0.26, 0.1, 0.12], pos=[-0.44, 0.05, -0.24], color="#cdc9bf"),
           B("scope", "box", name="Digital storage oscilloscope", info="Two channels, a spectrum, or an X-Y plot.",
             size=[0.5, 0.3, 0.26], pos=[0.06, 0.15, -0.42], color="#cdc9bf")]
    out += dial("dm1", [0.42, 0.0, -0.05], "Digital multimeter 1", "The first reading.")
    out += dial("dm2", [0.42, 0.0, 0.12], "Digital multimeter 2", "The second reading.")
    return out


def _mk(id, title, aim, kernel, params, theory, steps, questions, sources, check, knobs=None, insts=None):
    return lab(
        id=id, rig=RIG, title=title, group=GROUP, level=LEVEL, topic=CH, chapter=CH, aim=aim, kernel=kernel,
        params=params, autorun=True, camera={"pos": [0.0, 0.7, 0.85], "look": [0, 0.05, -0.1]}, floor=-0.03,
        bodies=_bodies(), knobs=knobs or [], instruments=insts or [], steps=steps, theory=theory + " " + SIMNOTE,
        safety="Bench supplies only, a few volts to a few tens of volts. Switch the power off before changing a connection.",
        tour=[{"say": "The circuit is on the breadboard; the supply, generator and settings panel is on the left, the scope "
                      "at the back and two multimeters on the right."}],
        questions=questions, sources=sources, check=check)


def _q(q, opts, ans, why):
    return {"q": q, "options": opts, "answer": ans, "why": why}


# ====================================================================================== regulated supplies
def regulator() -> dict:
    return _mk(
        "pe9-regulator", "Regulated power supply: line and load regulation, ripple (zener shunt)",
        "Feed a regulator from a variable DC supply carrying a 1 V peak-to-peak ripple, measure its output as the input "
        "voltage and the load current change, and find its line regulation, load regulation and ripple rejection.",
        "pe9_reg", {"kind": 0.0, "Vin": 15.0, "IL": 0.02, "Rs": 100.0, "Vz": 6.2, "rz": 5.0, "Vr": 1.0},
        "A regulator holds its output nearly constant. Line regulation is the change of output per volt of input "
        "(dV_o/dV_in) at a fixed load; load regulation is the fall of output per ampere of load, an output resistance "
        "R_o = -dV_o/dI_L; ripple on the input reaches the output reduced by the same factor as a slow line change. For a "
        "zener shunt regulator (series R_s, zener of slope resistance r_z) both follow from the divider of R_s and r_z: "
        "line regulation r_z/(R_s + r_z), R_o = R_s || r_z, as long as the zener still carries current. A series "
        "regulator puts an emitter follower after the zener, so the zener only supplies base current and R_o falls by "
        "about the current gain; an IC regulator adds an error amplifier and does better still.",
        ["Connect the regulator to the variable DC supply (with its 1 V ripple) and a rheostat load with an ammeter.",
         "At a fixed load, vary the input in 1 V steps and record the output and its ripple.",
         "At a fixed input, vary the load current and record the output.",
         "Plot V_o against V_in (slope = line regulation) and against I_L (slope = -R_o)."],
        [_q("Line regulation of a zener shunt regulator is about", ["r_z/(R_s + r_z)", "R_s/r_z", "1"], 0,
            "The zener's slope resistance and the series resistor form a divider for changes."),
         _q("Why does a series-pass regulator have a much lower output resistance?", [
             "The emitter follower divides the zener's resistance by the current gain", "Its zener is bigger",
             "It has no ripple"], 0, "The load current no longer flows through the zener's source resistance.")],
        [DU, MALVINO, SEDRA, ILLU, {"title": "6.2 V zener with a 5 ohm slope resistance", "note": "Illustrative values"}],
        {"params": {}, "reading": "line", "textbook": "pe9_reg_line", "tol": 0.01},
        knobs=[knob("Vin", "Input voltage", "Vin", 8, 20, 0.5, 15, "V")], insts=[inst("vo", "readout", "Output", "Vout", unit="V", digits=4)])


# ====================================================================================== converters
def converters() -> dict:
    return _mk(
        "pe9-converters", "D/A and A/D converters: an R-2R ladder DAC, its resolution and linearity",
        "Set every input code of a 4-bit R-2R ladder DAC with the switches, record the output, and find its step size "
        "(resolution) and its largest deviation from a straight line (linearity).",
        "pe9_conv", {"kind": 0.0, "D": 9.0, "Vref": 5.0, "R": 10000.0, "Rf": 10000.0, "e0": 0.004, "e1": -0.003,
                     "e2": 0.002, "e3": -0.001, "Vin": 2.0, "Voff": 0.004},
        "A current-mode R-2R ladder halves the reference current at every node, so the MSB leg carries V_ref/(2R), the "
        "next V_ref/(4R) and so on; the switched legs are summed by an op-amp of feedback R_f, giving V_o = (V_ref R_f/R) "
        "D/2^n for an n-bit code D. A binary-weighted DAC uses resistors R, 2R, 4R, 8R instead. The step size (one LSB) is "
        "the resolution; real resistors are not exact, so the output departs from a straight line, measured as the "
        "integral non-linearity in LSB. A successive-approximation ADC runs the other way: it tries each bit from the MSB "
        "down, keeping it if the input is still above the trial code, and so settles in n comparisons.",
        ["Set the reference to 5 V; the output is read on the multimeter.",
         "Set each of the 16 codes on the switches and record the output.",
         "Plot V_o against the code; the slope is the step size, the largest deviation from the line the non-linearity."],
        [_q("The step size of a 4-bit R-2R DAC with R_f = R on 5 V is", ["0.3125 V", "5 V", "1.25 V"], 0, "5/16 V."),
         _q("A successive-approximation ADC of n bits needs", ["n comparisons", "2^n comparisons", "one comparison"], 0,
            "One per bit, MSB first.")],
        [DU, GAYAKWAD, ILLU, {"title": "Leg resistor errors +0.4, -0.3, +0.2, -0.1 % (MSB first)",
                              "note": "Illustrative 1 % resistors; the ADC comparator offset 4 mV is illustrative"}],
        {"params": {}, "reading": "main", "textbook": "pe9_conv_main", "tol": 0.01},
        knobs=[knob("Vref", "Reference", "Vref", 1, 10, 0.5, 5, "V")], insts=[inst("o", "readout", "Output", "out", digits=4)])


# ====================================================================================== passive filters
def passive_filters() -> dict:
    return _mk(
        "pe9-passive-filters", "Passive RC filters with Bode plots: low-pass cut-off and roll-off",
        "Measure the gain and phase of a passive RC filter over four decades, draw its Bode plot, and find its cut-off "
        "frequency and roll-off.",
        "pe9_filt", {"kind": 0.0, "R": 10000.0, "C": 1.0e-8, "R2": 100000.0, "C2": 1.0e-9, "f": 1000.0, "Vin": 1.0},
        "An RC low-pass passes low frequencies and attenuates high ones: H = 1/(1 + j f/f_c) with f_c = 1/(2 pi R C), "
        "where the gain is -3 dB and the phase -45 degrees; far above f_c the gain falls 20 dB per decade. Swapping R and "
        "C gives the high-pass, the mirror image. A high-pass section followed by a low-pass section is a band-pass: "
        "H = j w R1 C1 / (1 - w^2 R1 C1 R2 C2 + j w (R1 C1 + R2 C2 + R1 C2)), the second section loading the first; it "
        "peaks at f_0 = 1/(2 pi sqrt(R1 C1 R2 C2)), the geometric mean of its two -3 dB frequencies.",
        ["Feed the filter from the generator at 1 V; channel 1 on the input, channel 2 on the output.",
         "Step the frequency from 100 Hz to 220 kHz and record the gain in dB and the phase at each.",
         "Draw gain and phase against log f; read the -3 dB frequency and the slope far from it."],
        [_q("At the cut-off of an RC low-pass the phase is", ["-45 degrees", "-90 degrees", "0"], 0, "arctan(1)."),
         _q("A first-order filter rolls off at", ["20 dB per decade", "40 dB per decade", "6 dB per decade"], 0,
            "Gain proportional to 1/f far from the corner.")],
        [DU, SEDRA, {"title": "IEC 60063 preferred values (E12 series) for the resistors and capacitors"}],
        {"params": {}, "reading": "fc", "textbook": "pe9_filt_fc", "tol": 0.01},
        knobs=[knob("f", "Frequency", "f", 10, 1000000, 10, 1000, "Hz")], insts=[inst("g", "readout", "Gain", "gain_db", unit="dB", digits=2)])


# ====================================================================================== resonance
def resonance() -> dict:
    return _mk(
        "pe9-resonance", "Series and parallel resonance: frequency, Q and bandwidth (series LCR)",
        "Sweep the generator through resonance of a series LCR circuit, record the current, and find the resonant "
        "frequency, the half-power bandwidth and the quality factor.",
        "pe9_lcr", {"mode": 0.0, "R": 47.0, "L": 0.022, "C": 4.7e-8, "f": 5000.0, "V": 1.0},
        "In a series LCR circuit the reactances cancel at f_r = 1/(2 pi sqrt(L C)), where the current is largest, V/R. The "
        "current falls to 1/sqrt 2 of its peak at two frequencies f_1 and f_2; their difference is the bandwidth and "
        "Q = f_r/(f_2 - f_1) = (1/R) sqrt(L/C). In the parallel (tank) circuit a coil of resistance R is in parallel with "
        "C: the current drawn from the generator is SMALLEST at anti-resonance, f_a = (1/2 pi) sqrt(1/(L C) - R^2/L^2), "
        "where the impedance is the dynamic resistance L/(C R); Q = 2 pi f_a L/R.",
        ["Connect the coil, capacitor and resistor in series with the generator (1 V rms) and the ammeter.",
         "Step the frequency through resonance in small steps and record the current.",
         "Plot I against f; find f_r, the two half-power frequencies and Q."],
        [_q("At series resonance the current is limited only by", ["the resistance", "the inductance", "the capacitance"], 0,
            "The reactances cancel."),
         _q("A parallel resonant circuit draws from the generator", ["its smallest current", "its largest current",
            "no current"], 0, "Its impedance is largest at anti-resonance.")],
        [DU, MALVINO, {"title": "IEC 60063 preferred values; coil resistance illustrative"}],
        {"params": {}, "reading": "fr", "textbook": "pe9_lcr_fr", "tol": 0.01},
        knobs=[knob("f", "Frequency", "f", 100, 100000, 1, 5000, "Hz")], insts=[inst("i", "readout", "Current", "I_mA", unit="mA", digits=3)])


# ====================================================================================== op-amp linear
def opamp_linear() -> dict:
    return _mk(
        "pe9-opamp-linear", "Op-amp linear amplifiers: gain and frequency response (inverting amplifier)",
        "Build an op-amp amplifier, measure its gain at low frequency and against frequency, and find the -3 dB "
        "frequency and the gain-bandwidth product.",
        "pe9_opl", {"kind": 0.0, "R1": 10000.0, "Rf": 100000.0, "A0": 200000.0, "fa": 5.0, "V1": 0.05, "V2": 0.03,
                    "f": 1000.0},
        "With an ideal op-amp the gain follows from the resistors alone: inverting -R_f/R_1, non-inverting 1 + R_f/R_1, "
        "summing -R_f (V_1/R_1 + V_2/R_2), difference (R_f/R_1)(V_2 - V_1), follower 1, averaging the summer with "
        "R_f = R_1/n. A real op-amp has an open-loop gain A = A0/(1 + j f/f_a) that falls 20 dB per decade above a few "
        "hertz; the closed-loop gain is G/(1 + NG/A), where the noise gain NG = 1 + R_f/(the resistance from the "
        "inverting input to the sources). Its -3 dB frequency is f_a (1 + A0/NG), so (-3 dB frequency) x NG is nearly "
        "the same for every circuit: the gain-bandwidth product A0 f_a.",
        ["Build the circuit on the breadboard with a 741; feed 50 mV from the generator.",
         "Record the output amplitude and the gain from 10 Hz up to a few megahertz.",
         "Find the -3 dB frequency; multiply it by the noise gain to get the gain-bandwidth product."],
        [_q("The gain-bandwidth product of a single-pole op-amp is", ["A0 f_a", "A0/f_a", "f_a"], 0,
            "The open-loop gain times its corner."),
         _q("A voltage follower's -3 dB frequency is", ["about the gain-bandwidth product", "f_a", "zero"], 0,
            "Its noise gain is 1.")],
        [DU, SGGU, SEDRA, MEMO, {"title": "LM741 typical A0 = 200 000 and unity-gain bandwidth about 1 MHz",
                                 "note": "From memory - verify against the data sheet"}],
        {"params": {}, "reading": "gain", "textbook": "pe9_opl_gain", "tol": 0.01},
        knobs=[knob("f", "Frequency", "f", 10, 5000000, 10, 1000, "Hz")], insts=[inst("g", "readout", "Gain", "gain", digits=3)])


# ====================================================================================== integrator / differentiator
def integ_diff() -> dict:
    return _mk(
        "pe9-integ-diff", "Op-amp integrator and differentiator: RC from a square wave (integrator)",
        "Drive an op-amp integrator with a square wave, measure the peak-to-peak output at several frequencies, and find "
        "the time constant RC and the unknown capacitor.",
        "pe9_intdiff", {"kind": 0.0, "wave": 0.0, "R": 10000.0, "C": 1.0e-8, "Rf": 1.0e7, "Rs": 1000.0, "Vp": 1.0,
                        "f": 1000.0},
        "An inverting integrator (input R, feedback C) gives v_o = -(1/RC) integral of v_in dt; a large R_f across C stops "
        "it drifting at DC. A square wave of peak V_p becomes a triangle of peak-to-peak V_p T/(2RC); a sine becomes a "
        "cosine of amplitude V_p/(w RC); a triangle becomes parabolic arcs of peak-to-peak V_p T/(4RC). A differentiator "
        "(input C, feedback R) gives v_o = -RC dv_in/dt: a triangle becomes a square of amplitude RC x slope = 4 V_p f RC, "
        "a sine a cosine of amplitude w RC V_p, and a square wave a train of spikes that decay with the time constant R_s C "
        "of the small resistor R_s put in series with C to keep it stable.",
        ["Build the integrator (R = 10 kohm, C unknown, R_f = 10 Mohm) and feed a 1 V peak square wave.",
         "Record the output peak to peak at several frequencies.",
         "Work out RC = V_p T/(2 V_pp) each time and so C."],
        [_q("A square wave into an integrator gives", ["a triangle", "spikes", "a sine"], 0, "A constant input ramps."),
         _q("Why is R_s put in series with the differentiator's capacitor?", ["To limit its gain at high frequency",
            "To raise its gain", "To make it integrate"], 0, "Otherwise noise and the op-amp's own poles make it ring.")],
        [DU, GAYAKWAD, ILLU],
        {"params": {}, "reading": "tau", "textbook": "pe9_intdiff_rc", "tol": 0.01},
        knobs=[knob("f", "Frequency", "f", 100, 10000, 10, 1000, "Hz")], insts=[inst("v", "readout", "Output p-p", "Vpp", unit="V", digits=3)])


# ====================================================================================== comparators
def comparators() -> dict:
    return _mk(
        "pe9-comparators", "Zero-crossing detector: transfer characteristic and input offset",
        "Sweep a DC input slowly through zero at an open-loop op-amp, record its output, draw the transfer "
        "characteristic and find where it switches (the input offset).",
        "pe9_cmp", {"kind": 0.0, "Vin": 0.0, "A0": 200000.0, "Vos": 0.00184, "Vsat": 13.0, "Vp": 2.0, "f": 1000.0,
                    "Ch": 1.0e-6, "RL": 1000000.0, "R": 10000.0, "Rg": 1000.0, "Ra": 10000.0, "Rb": 10000.0, "eps": 0.002},
        "An op-amp with no feedback amplifies the difference of its inputs by its whole open-loop gain, so its output sits "
        "at +V_sat or -V_sat except within a few tens of microvolts of the switching point: a zero-crossing detector. That "
        "point is not exactly zero but the input offset voltage V_os. A precision peak detector (op-amp, diode and "
        "capacitor) charges C to the input's peak; between peaks C discharges through the load, so the output droops by "
        "about V_p T/(R_L C). A three-op-amp instrumentation amplifier has a differential gain (1 + 2R/R_g) R_b/R_a set "
        "by one resistor R_g; its common-mode gain comes only from the mismatch of the difference stage's resistors, and "
        "CMRR = A_d/|A_cm|.",
        ["Connect the generator's DC offset to the non-inverting input; earth the inverting input.",
         "Step the input in 0.1 mV steps through zero and record the output.",
         "Plot the transfer characteristic; find the input at which the output passes through zero."],
        [_q("Why does a zero-crossing detector not switch at exactly 0 V?", ["The input offset voltage", "The slew rate",
            "The supply"], 0, "The op-amp behaves as if V_os were added to its input."),
         _q("The common-mode gain of an instrumentation amplifier comes from", ["resistor mismatch in the difference stage",
            "R_g", "the input stage gain"], 0, "With perfectly matched resistors it would be zero.")],
        [DU, GAYAKWAD, MEMO, {"title": "LM741 typical input offset 1-2 mV, A0 = 200 000, swing +-13 V on +-15 V",
                              "note": "From memory - verify; 1.84 mV is an illustrative offset in that range"}],
        {"params": {}, "reading": "main", "textbook": "pe9_cmp_main", "tol": 0.01},
        knobs=[knob("Vin", "DC input", "Vin", -0.005, 0.005, 0.0001, 0, "V")], insts=[inst("o", "readout", "Output", "Vo", unit="V", digits=3)])


# ====================================================================================== triangle generator
def triangle() -> dict:
    return _mk(
        "pe9-triangle-gen", "Triangular wave generator: an integrator with a Schmitt comparator",
        "Build a triangle-wave generator from an op-amp integrator and a Schmitt comparator, measure its frequency and "
        "amplitude for several integrator resistors, and find the integrator's capacitor.",
        "pe9_tri", {"R1": 10000.0, "R2": 20000.0, "R": 10000.0, "C": 1.0e-8, "Vsat": 13.0},
        "The comparator's output, +-V_sat, drives the integrator, whose output ramps at V_sat/(R C). The comparator has "
        "positive feedback through R1 and R2, so it switches only when the ramp reaches +-V_sat R1/R2: the ramp then "
        "reverses. The output is a triangle of amplitude V_sat R1/R2 and frequency f = R2/(4 R1 R C), with a square wave "
        "at the comparator's output.",
        ["Build the Schmitt comparator (R1 = 10 kohm, R2 = 20 kohm) and the integrator (R from the box, C unknown).",
         "For each integrator resistor read the frequency and the amplitude of the triangle.",
         "Plot f against 1/R: the slope is R2/(4 R1 C)."],
        [_q("Doubling R2 makes the triangle's amplitude", ["half", "double", "unchanged"], 0, "It is V_sat R1/R2."),
         _q("Doubling the integrator's C makes the frequency", ["half", "double", "unchanged"], 0, "f = R2/(4 R1 R C).")],
        [DU, GAYAKWAD, ILLU],
        {"params": {}, "reading": "f", "textbook": "pe9_tri_f", "tol": 0.01},
        knobs=[knob("R", "Integrator resistor", "R", 1000, 100000, 100, 10000, "ohm")], insts=[inst("f", "readout", "Frequency", "f", unit="Hz", digits=1)])


# ====================================================================================== sweeps
def sweeps() -> dict:
    return _mk(
        "pe9-sweep", "Sweep (time-base) generators: period and linearity (RC sweep)",
        "Build a time-base generator, measure its sweep period and slope error for several charging resistors, and find "
        "the timing capacitor.",
        "pe9_sweep", {"kind": 0.0, "V": 20.0, "R": 10000.0, "C": 1.0e-7, "Vs": 2.0, "eta": 0.6, "Vd": 0.6, "Vv": 2.0,
                      "Vz": 5.6, "Vbe": 0.6, "ro": 1.0e6, "A": 0.98, "Vce": 0.2},
        "A sweep is a capacitor charging from V_lo towards an asymptote V_inf and reset at V_hi. Exponential charging "
        "gives the period T = tau ln((V_inf - V_lo)/(V_inf - V_hi)) and a slope error e_s = (V_hi - V_lo)/(V_inf - V_lo): "
        "the sweep is more linear the smaller a fraction of the asymptote it uses. An RC sweep gated at amplitude V_s "
        "has e_s = V_s/V; a UJT sawtooth runs between the valley voltage and the peak voltage eta V_BB + V_D; a zener "
        "sawtooth fires at V_z + V_BE. A constant-current charger (a transistor with a zener-held base) raises the "
        "asymptote to I r_o, and a bootstrap circuit (an emitter follower of gain A feeding the charging resistor) "
        "raises it to V/(1 - A): both make the sweep nearly linear.",
        ["Build the sweep circuit; channel 1 on the capacitor.",
         "For each charging resistor read the sweep period and the start and end slopes.",
         "Work out C from each period and the slope error from the slopes."],
        [_q("The slope error of an RC sweep of 2 V on a 20 V supply is about", ["10 %", "1 %", "50 %"], 0, "V_s/V."),
         _q("A bootstrap sweep is more linear because", ["the charging current stays nearly constant", "it uses a bigger C",
            "it uses a zener"], 0, "The follower lifts the resistor's top end with the capacitor.")],
        [DU, MILLMAN, MEMO, {"title": "2N2646 UJT intrinsic stand-off ratio 0.56-0.75, valley about 2 V",
                             "note": "From memory - verify; eta = 0.6 and the 5.6 V zener are illustrative"}],
        {"params": {}, "reading": "T", "textbook": "pe9_sweep_t", "tol": 0.01},
        knobs=[knob("R", "Charging resistor", "R", 1000, 200000, 100, 10000, "ohm")], insts=[inst("t", "readout", "Period", "T", unit="s", digits=6)])


# ====================================================================================== tuned amplifiers
def tuned() -> dict:
    return _mk(
        "pe9-tuned-amp", "Tuned amplifier: centre frequency, bandwidth and Q (single tuned)",
        "Sweep the generator through the pass band of a tuned amplifier, record the gain, and find its centre frequency, "
        "its bandwidth and the Q of its tank.",
        "pe9_tuned", {"kind": 0.0, "L": 1.0e-4, "C": 1.0e-9, "Q": 40.0, "kq": 1.0, "A0": 50.0, "f": 500000.0},
        "A tuned amplifier's collector load is a parallel LC tank, so its gain peaks at f_0 = 1/(2 pi sqrt(L C)) and falls "
        "as A0/sqrt(1 + x^2), x = Q (f/f_0 - f_0/f): the bandwidth is f_0/Q. A double-tuned stage couples two identical "
        "tanks: its gain goes as 2 kQ/sqrt((1 + k^2Q^2 - x^2)^2 + 4x^2). At critical coupling (kQ = 1) the top is maximally "
        "flat and the bandwidth is sqrt 2 f_0/Q, wider with steeper skirts; over-coupled it shows two humps.",
        ["Feed the amplifier from the RF generator at a small level; channel 2 on the output.",
         "Step the frequency through the pass band in small steps and record the gain.",
         "Find the two half-power frequencies; f_0 is their geometric mean and Q = f_0/bandwidth."],
        [_q("The bandwidth of a single-tuned stage of Q = 50 at 500 kHz is", ["10 kHz", "25 kHz", "1 kHz"], 0, "f_0/Q."),
         _q("At critical coupling a double-tuned stage's bandwidth is", ["sqrt 2 times the single-tuned one",
            "half", "the same"], 0, "x = sqrt 2 at the half-power points.")],
        [DU, MALVINO, ILLU, {"title": "Narrow-band tuned-circuit response (x = Q (f/f0 - f0/f))",
                             "note": "The standard textbook form; Q = 40 and the gain are illustrative"}],
        {"params": {}, "reading": "f0", "textbook": "pe9_tuned_f0", "tol": 0.01},
        knobs=[knob("f", "Frequency", "f", 100000, 2000000, 100, 500000, "Hz")], insts=[inst("g", "readout", "Gain", "gain", digits=3)])


# ====================================================================================== counters
def counters() -> dict:
    return _mk(
        "pe9-counters", "Counters: modulus and propagation delay (asynchronous ripple counter)",
        "Clock mod-N counters at 100 kHz, read the output frequency of the most significant bit to find the modulus, and "
        "measure on the scope how long after the clock edge the MSB changes, to find each flip-flop's propagation delay.",
        "pe9_cnt", {"kind": 0.0, "N": 10.0, "tpd": 2.5e-8, "fclk": 1.0e5},
        "In an asynchronous (ripple) counter each JK flip-flop (J = K = 1) toggles when the one before it falls, so a "
        "change ripples through the chain: on the clock that sets the MSB every lower bit changes first, and the MSB "
        "changes n t_pd after the clock edge for an n-stage counter. A mod-N counter is cleared when it reaches N, so its "
        "MSB repeats every N clocks: f_out = f_clk/N. In a synchronous counter every flip-flop shares the clock and the "
        "next-state logic sets each J and K, so every output changes one t_pd after the edge, however many stages there are.",
        ["Set the clock to 100 kHz; connect the universal counter to the MSB and the scope to the clock and the MSB.",
         "For each modulus N read the MSB frequency and the delay after the clock edge.",
         "Modulus = f_clk / f_out; t_pd = delay / (number of stages) for the ripple counter."],
        [_q("A mod-10 ripple counter's MSB changes, after the clock edge, after", ["4 t_pd", "t_pd", "10 t_pd"], 0,
            "Four stages ripple in turn."),
         _q("Why are synchronous counters used at high speed?", ["Every output changes one t_pd after the clock",
            "They need fewer flip-flops", "They have no clock"], 0, "No ripple delay adds up.")],
        [DU, DIGITAL, MEMO, {"title": "74LS76 / 74LS112 propagation delay of order 15-25 ns",
                             "note": "From memory - verify; 25 ns is illustrative"}],
        {"params": {}, "reading": "mod", "textbook": "pe9_cnt_mod", "tol": 0.01},
        knobs=[knob("N", "Modulus", "N", 2, 16, 1, 10)], insts=[inst("m", "readout", "Modulus", "mod", digits=0)])


# ====================================================================================== AM / FM
def am_fm() -> dict:
    return _mk(
        "pe9-am-fm", "Amplitude modulation: modulation index, side-bands and demodulation",
        "Amplitude-modulate a 20 kHz carrier, measure the modulation index from the envelope and from the side-band lines "
        "of the spectrum for several message amplitudes, and find the modulator's sensitivity.",
        "pe9_amfm", {"kind": 0.0, "Vc": 2.0, "Vm": 0.5, "fc": 20000.0, "fm": 500.0, "ka": 0.4, "kf": 1500.0, "kd": 0.001},
        "In AM the carrier's amplitude follows the message: v = V_c (1 + m sin w_m t) sin w_c t, with modulation index "
        "m = k_a V_m. From the envelope's largest and smallest values m = (V_max - V_min)/(V_max + V_min); the spectrum "
        "has the carrier and two side-bands at f_c +- f_m, each of amplitude m V_c/2, and an envelope detector gives back "
        "m V_c. In FM the frequency follows the message: beta = k_f V_m / f_m, and the spectrum has lines at f_c + n f_m "
        "of amplitude V_c J_n(beta). The carrier line vanishes where J0(beta) = 0, first at beta = 2.405: the classic "
        "carrier-null way to find k_f. A discriminator gives back an output proportional to the deviation.",
        ["Feed the carrier and the message to the modulator; channel 1 on the modulated wave, the scope's FFT on the spectrum.",
         "For each message amplitude read V_max and V_min of the envelope and the side-band level.",
         "Work out m each time; plot m against V_m: the slope is k_a."],
        [_q("Each side-band of an AM wave with m = 0.5 and V_c = 2 V has amplitude", ["0.5 V", "1 V", "2 V"], 0, "m V_c/2."),
         _q("The FM carrier first vanishes at beta =", ["2.405", "1", "5.52"], 0, "The first zero of J0.")],
        [DU, KENNEDY, ILLU, {"title": "Bessel J0 first zero 2.404826", "note": "From memory - verify against a table"}],
        {"params": {}, "reading": "main", "textbook": "pe9_amfm_main", "tol": 0.01},
        knobs=[knob("Vm", "Message amplitude", "Vm", 0, 3, 0.01, 0.5, "V")], insts=[inst("m", "readout", "Index", "m", digits=3)])


# ====================================================================================== analog computer
def analog_comp() -> dict:
    return _mk(
        "pe9-analog-comp", "Analogue computer: the motion of a falling body",
        "Patch two op-amp integrators to compute the motion of a falling body, read the velocity and the height against "
        "time on the scope, find the landing time for several integrator capacitors, and from it the integrator resistor.",
        "pe9_acomp", {"kind": 0.0, "R": 100000.0, "C": 1.0e-7, "Vg": 1.0, "V0": 5.0, "a1": 2.0, "b1": 1.0, "c1": 5.0,
                      "a2": 1.0, "b2": 3.0, "c2": 10.0, "z": 0.2},
        "An integrator of time constant tau = RC turns a voltage into its time integral. For a falling body, a constant "
        "V_g (standing for g) into the first integrator gives the velocity v = V_g t/tau; the second integrator, set to "
        "start at V_0 (the height), gives y = V_0 - V_g t^2/(2 tau^2), which reaches zero at T_0 = tau sqrt(2 V_0/V_g). "
        "Two simultaneous linear equations are solved by integrators that keep changing x and y until both equations are "
        "satisfied; x'' + 2 zeta w x' + w^2 x = 0 is solved by a loop of two integrators and a summer, ringing at "
        "f_d = sqrt(1 - zeta^2)/(2 pi tau).",
        ["Patch the two integrators (R unknown, C from the box) and set the initial height V_0 = 5 V and V_g = 1 V.",
         "Release the hold and record the landing time T_0 (y = 0) on the scope.",
         "Repeat for several C; RC = T_0/sqrt(2 V_0/V_g) gives R."],
        [_q("Doubling the integrator's RC makes the landing time", ["twice as long", "half", "unchanged"], 0,
            "T_0 = RC sqrt(2 V_0/V_g)."),
         _q("The height-time graph of the falling body on the scope is", ["a parabola", "a straight line", "a sine"], 0,
            "y falls as t^2.")],
        [MLSU, GAYAKWAD, ILLU],
        {"params": {}, "reading": "main", "textbook": "pe9_acomp_main", "tol": 0.01},
        knobs=[knob("V0", "Initial height voltage", "V0", 1, 10, 0.5, 5, "V")], insts=[inst("m", "readout", "Reading", "main", digits=4)])


# ====================================================================================== power amplifiers
def power_amp() -> dict:
    return _mk(
        "pe9-power-amp", "Transistor power amplifier: output power, efficiency and distortion (class A)",
        "Drive a series-fed class A power amplifier into an 8 ohm load at several levels, measure the output power, the "
        "power drawn from the supply and the distortion, and find its largest efficiency.",
        "pe9_pa", {"kind": 0.0, "Vcc": 12.0, "RL": 8.0, "Vd": 3.0, "Vg": 0.6},
        "A series-fed class A stage is biased at half the supply, I_C = V_cc/(2 R_L), and the transistor conducts all the "
        "time. The supply delivers V_cc I_C whatever the signal, while the load receives V_o^2/(2 R_L): the efficiency "
        "eta = (V_o/V_cc)^2 is at most 25 % at the largest undistorted swing V_o = V_cc/2. A class B push-pull pair on "
        "+-V_cc lets each transistor conduct for half a cycle; the supplies deliver 2 V_cc V_o/(pi R_L), so eta = "
        "pi V_o/(4 V_cc), at most 78.5 %. Each transistor needs about 0.6 V before it conducts, so a class B stage shows "
        "crossover distortion near zero; driving either stage past its swing clips the wave.",
        ["Connect the amplifier to the supply and an 8 ohm load; the scope across the load, the ammeter in the supply lead.",
         "For each drive level read the output amplitude, the supply current and the distortion factor.",
         "Work out P_o, P_dc and eta; plot eta against the output swing and extrapolate to the largest swing."],
        [_q("The largest efficiency of a series-fed class A amplifier is", ["25 %", "50 %", "78.5 %"], 0, "(V_o/V_cc)^2 at V_cc/2."),
         _q("Crossover distortion happens in", ["class B", "class A", "neither"], 0, "Neither transistor conducts near zero.")],
        [DU, MALVINO, SEDRA, ILLU],
        {"params": {"Vg": 0.0}, "reading": "eta", "textbook": "pe9_pa_eta", "tol": 0.01},
        knobs=[knob("Vd", "Drive", "Vd", 0.5, 14, 0.5, 3, "V")], insts=[inst("e", "readout", "Efficiency", "eta", digits=3)])


# ====================================================================================== op-amp parameters
def opamp_params() -> dict:
    return _mk(
        "pe9-opamp-params", "Op-amp parameters: offset, bias current, CMRR, slew rate, GBW (741)",
        "Measure the input offset voltage, the input bias current, the common-mode rejection ratio, the slew rate and the "
        "gain-bandwidth product of an op-amp, each in its standard test circuit.",
        "pe9_opp", {"test": 0.0, "Vos": 1.0e-3, "Ib": 8.0e-8, "cmrr_db": 90.0, "SR": 5.0e5, "A0": 2.0e5, "fa": 5.0,
                    "f": 1000.0},
        "Offset: with both inputs earthed through small resistors and a gain of 1001, the output is 1001 V_os (plus a "
        "little I_b R_f). Bias current: a 1 Mohm resistor in series with the non-inverting input of a follower shifts the "
        "output by I_b x 1 Mohm. CMRR: a difference amplifier of gain 100 with both inputs moved together by 10 V shows "
        "an output change of 100 x 10 V / CMRR. Slew rate: a follower driven by a large square wave turns its edges into "
        "ramps of slope SR. Gain-bandwidth: an amplifier of gain 100 rolls off at f_a (1 + A0/101), so (-3 dB frequency) "
        "x 101 is nearly A0 f_a.",
        ["Offset: gain 1001, inputs earthed; read V_o.",
         "Bias: follower with the 1 Mohm in and out of the + input; read both outputs.",
         "CMRR: difference amplifier of gain 100; move the common input by 10 V; read the change of V_o.",
         "Slew rate: follower, 10 V square wave; read the 10-90 % rise time of the output.",
         "Gain-bandwidth: inverting gain 100; find the -3 dB frequency."],
        [_q("A 741's slew rate of 0.5 V/us limits a 10 V peak sine to about", ["8 kHz", "1 MHz", "100 Hz"], 0,
            "f_max = SR/(2 pi V_p)."),
         _q("A CMRR of 90 dB means the common-mode gain is smaller than the differential gain by", ["about 31 600", "90",
            "1000"], 0, "10^(90/20).")],
        [SGGU, GAYAKWAD, MEMO, {"title": "LM741 typical: V_os 1 mV, I_b 80 nA, CMRR 90 dB, SR 0.5 V/us, GBW 1 MHz",
                                "note": "From memory - verify against the data sheet"}],
        {"params": {}, "reading": "gbw", "textbook": "pe9_opp_gbw", "tol": 0.01},
        knobs=[knob("f", "Frequency", "f", 10, 1000000, 10, 1000, "Hz")])


# ====================================================================================== crystal oscillator
def crystal() -> dict:
    return _mk(
        "pe9-crystal-osc", "Crystal oscillator: frequency, pulling and temperature stability",
        "Run a 10 MHz quartz crystal oscillator with several load capacitors, read its frequency on a counter, find the "
        "crystal's motional capacitance from the pulling, and measure its frequency drift with temperature.",
        "pe9_xtal", {"L1": 0.012, "C1": 2.0e-14, "C0": 5.0e-12, "CL": 2.0e-11, "T": 25.0, "Ti": 25.0, "a3": 1.0e-4,
                     "a1": -0.2},
        "A quartz crystal is electrically a series resonator (motional L1 and C1) shunted by its holder capacitance C0. "
        "In a Pierce or Colpitts oscillator it runs slightly above its series resonance f_s = 1/(2 pi sqrt(L1 C1)), at "
        "f_L = f_s (1 + C1/(2 (C0 + C_L))) with load capacitance C_L: the crystal can be 'pulled' a little by C_L, and the "
        "pulling gives C1. Because C1 is a few femtofarads the frequency hardly depends on the rest of the circuit, which "
        "is the oscillator's stability; what remains is temperature: an AT-cut crystal's frequency follows a cubic about "
        "its inflection temperature, a few ppm over tens of degrees.",
        ["Build the Pierce oscillator with the crystal and a trimmer load capacitor; connect the frequency counter.",
         "At 25 C record the frequency for each load capacitance.",
         "Put the crystal in the oven and record the frequency at several temperatures.",
         "Plot f against 1/(C0 + C_L): slope/intercept = C1/2."],
        [_q("Increasing the load capacitance makes the frequency", ["fall slightly", "rise", "double"], 0,
            "f_L = f_s (1 + C1/(2(C0 + C_L)))."),
         _q("A crystal oscillator is stable because", ["C1 is tiny and Q is very high", "it uses a big inductor",
            "it has no capacitor"], 0, "The rest of the circuit barely moves its frequency.")],
        [DU, MALVINO, MEMO, {"title": "10 MHz AT-cut crystal: C1 about 20 fF, C0 about 5 pF; AT-cut cubic coefficient "
                                      "about 1e-4 ppm/K^3", "note": "From memory - verify against a crystal maker's data"}],
        {"params": {}, "reading": "f", "textbook": "pe9_xtal_f", "tol": 0.01},
        knobs=[knob("T", "Oven temperature", "T", -20, 80, 1, 25, "C")], insts=[inst("f", "readout", "Frequency", "f", unit="Hz", digits=0)])


# ====================================================================================== multivibrators
def multivibrators() -> dict:
    return _mk(
        "pe9-multivibrators", "Astable, monostable and bistable multivibrators: transistor astable",
        "Build an astable multivibrator, measure its period and duty cycle for several timing resistors, and find the "
        "timing capacitor.",
        "pe9_mv", {"tech": 0.0, "mode": 0.0, "R1": 10000.0, "R2": 22000.0, "R": 10000.0, "C": 1.0e-7, "Vcc": 9.0,
                   "Vbe": 0.65, "Vce": 0.1, "Vsat": 13.0, "Vd": 0.7, "ftrig": 1000.0},
        "A multivibrator switches between two states. Astable: neither state is stable, so it oscillates. In the "
        "transistor astable each base is driven about V_cc below zero when the other transistor switches on and charges "
        "back to V_BE through its resistor, so each half lasts R C ln((2 V_cc - V_CE - V_BE)/(V_cc - V_BE)), close to "
        "0.69 R C. The 555 astable charges C between V_cc/3 and 2V_cc/3: t_high = 0.693 (R1 + R2) C, t_low = 0.693 R2 C; "
        "the op-amp astable gives T = 2 R C ln((1 + b)/(1 - b)), b = R1/(R1 + R2). Monostable: one stable state; a trigger "
        "gives one pulse of width about 0.69 R C (transistor), 1.1 R C (555). Bistable: two stable states; triggered it "
        "toggles (dividing the trigger frequency by two), or as a Schmitt trigger it switches at two different thresholds.",
        ["Build the circuit; channel 1 on one collector (or the output), channel 2 on the timing node.",
         "For each timing resistor record the period and the high time.",
         "Work out the capacitor from each period."],
        [_q("A 555 astable with R1 = R2 has a duty cycle of", ["2/3", "1/2", "1/3"], 0, "(R1 + R2)/(R1 + 2 R2)."),
         _q("A bistable toggled by a 1 kHz trigger gives an output of", ["500 Hz", "1 kHz", "2 kHz"], 0,
            "Two triggers per output cycle.")],
        [DU, MILLMAN, GAYAKWAD, MEMO, {"title": "NE555 thresholds V_cc/3 and 2V_cc/3; BC547 V_BE about 0.65 V, V_CE(sat) "
                                                "about 0.1 V", "note": "From memory - verify against the data sheets"}],
        {"params": {}, "reading": "main", "textbook": "pe9_mv_main", "tol": 0.01},
        knobs=[knob("Vcc", "Supply", "Vcc", 5, 15, 0.5, 9, "V")], insts=[inst("m", "readout", "Reading", "main", digits=6)])


# ====================================================================================== CE amplifier design
def ce_design() -> dict:
    return _mk(
        "pe9-ce-design", "CE amplifier designed for a given gain: mid gain specification (about 20)",
        "Design a voltage-divider-biased common-emitter amplifier for a voltage gain of about 20 by choosing its unbypassed "
        "emitter resistor, then measure its mid-band gain, its bandwidth and its input impedance.",
        "pe9_ce", {"Vcc": 12.0, "R1": 47000.0, "R2": 10000.0, "Rc": 2200.0, "RL": 10000.0, "Re1": 68.0, "Re2": 932.0,
                   "beta": 200.0, "Vbe": 0.65, "Cin": 1.0e-5, "CE": 1.0e-4, "Co": 1.0e-5, "Cx": 2.4e-11, "f": 10000.0,
                   "Rx": 0.0},
        "The divider R1, R2 and the total emitter resistance set the operating point: I_E = (V_th - V_BE)/(R_E + R_th/(beta "
        "+ 1)), and the transistor's own emitter resistance r_e = V_T/I_E (about 26 mV/I_E). Splitting R_E into a part Re1 "
        "left unbypassed and a part bypassed by C_E leaves the bias alone but sets the mid-band gain: A_v = alpha (R_c || "
        "R_L)/(r_e + Re1). Re1 = 0 gives the largest, least predictable gain (it depends on r_e); a larger Re1 gives a "
        "smaller gain fixed by resistors, a higher input impedance (beta + 1)(r_e + Re1) || R_th and a wider low-frequency "
        "response. The coupling and bypass capacitors set the lower half-power frequency, the collector's capacitance the "
        "upper one. The input impedance is measured by putting a known resistor R_x in series: Z_in = R_x v/(v_0 - v).",
        ["Design: for A_v = 20, Re1 = alpha (R_c || R_L)/20 - r_e; pick the nearest preferred value.",
         "Build the stage; generator at 10 mV through the test resistor R_x (0 to start); channel 2 on the output.",
         "Sweep the frequency from 1 Hz to 10 MHz and record the gain; find the mid-band gain and the half-power points.",
         "At 10 kHz insert R_x = 1, 2.2, 4.7, 10 kohm and record the gain; work out Z_in."],
        [_q("Leaving more of the emitter resistance unbypassed makes the gain", ["smaller and more predictable", "larger",
            "unchanged"], 0, "A_v = alpha (R_c || R_L)/(r_e + Re1)."),
         _q("The input impedance of the stage rises with Re1 because", ["the base sees (beta + 1)(r_e + Re1)", "R1 rises",
            "the gain rises"], 0, "Emitter degeneration is reflected into the base.")],
        [DU, SEDRA, MALVINO, MEMO, {"title": "BC547B current gain about 200, V_BE about 0.65 V; C_x = 4 pF collector-base plus "
                                             "a 20 pF probe", "note": "From memory - verify; illustrative capacitances"}],
        {"params": {}, "reading": "Amid", "textbook": "pe9_ce_amid", "tol": 0.01},
        knobs=[knob("f", "Frequency", "f", 1, 10000000, 1, 10000, "Hz")], insts=[inst("g", "readout", "Gain", "gain", digits=3)])


BUILDERS = (regulator, converters, passive_filters, resonance, opamp_linear, integ_diff, comparators, triangle, sweeps,
            tuned, counters, am_fm, analog_comp, power_amp, opamp_params, crystal, multivibrators, ce_design)
