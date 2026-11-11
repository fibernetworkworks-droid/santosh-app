"""Prayogshala lab pack: the B.Sc. heat, thermoelectric, wave and ultrasound benches.

Eight studio rigs (`app/static/prayog/exp/`) serve ten set-ups of `syllabus/physics/ug.json`:
    searle-thermal-conductivity   Searle's bar (copper; aluminium, brass, iron in the family)
    lees-disc                     Lee and Charlton's disc (glass, ebonite; steam or electrical heating)
    thermocouple-null-method      thermocouple on a potentiometer (copper-constantan, iron-constantan)
    thermocouple-opamp            the same bench, op-amp amplifier, neutral temperature of a copper-iron couple
    platinum-resistance-thermometer / rtd-calibration   Pt resistance thermometer on a bridge (null or off-balance)
    melde-experiment              Melde's string (transverse and longitudinal)
    lissajous-figures             two SHMs on a CRO (frequency ratio and phase)
    kundt-tube                    speed of sound in a rod
    ultrasonic-interferometer     velocity of ultrasound in a liquid
Physics: the `heat_wave_ug` kernel pack (never catalog.py / kernels.py). Every lab carries its own check: the kernel's
reading against the textbook formula, within 1 %. English only.
"""
from __future__ import annotations

from ..catalog import B, col, inst, knob, lab

SIM = {"title": "Hoola Prayogshala kernel", "note": "readings come from the simulation code; checked against the textbook formula in Hoola's tests"}
CRC = {"title": "CRC Handbook of Chemistry and Physics - thermal conductivity, specific heat, density and speed of sound tables"}
DU = {"title": "University of Delhi B.Sc. (Hons) Physics practical syllabus (Thermal Physics / Waves and Oscillations labs)"}
HNB = {"title": "HNBGU four-year UG Physics (NEP) practical list - Waves and Acoustics"}
IP = {"title": "Practical Physics, Indu Prakash and Ramakrishna - Searle's apparatus, Kundt's tube, Melde's experiment"}
EDU = {"title": "Education use only: nothing in this experiment is a medical or safety measurement"}


def _board(w=1.6, d=0.7):
    return B("board", "box", name="Bench top", size=[w, 0.02, d], pos=[0, -0.01, 0], color="wood", cut=False)


# =============================================================================================== SEARLE
def searle() -> dict:
    return lab(
        id="searle-thermal-conductivity", title="Thermal conductivity of copper with Searle's apparatus",
        group="Physics · Heat", level="B.Sc.", topic="Conduction of heat", chapter="Heat and thermodynamics",
        aim="Send steam down one end of a lagged copper bar, collect the water that cools the other end, and find the "
            "thermal conductivity K from the temperature gradient and the heat the water carries away.",
        kernel="hw_searle", params={}, speeds=[1, 5, 10, 30], autorun=False,
        camera={"pos": [0.5, 0.45, 1.3], "look": [0.0, 0.1, 0.0]}, floor=-0.02,
        bodies=[_board(),
                B("chest", "cylinder", name="Steam chamber", info="Steam from the boiler heats the left end of the bar to 100 °C.",
                  r=0.045, h=0.1, pos=[-0.5, 0.06, 0], rot=[0, 0, 1.5708], color="brass"),
                B("bar", "cylinder", name="Lagged copper bar", info="The bar is wrapped in felt so heat leaves only along its length.",
                  r=0.0125, h=0.5, pos=[-0.15, 0.06, 0], rot=[0, 0, 1.5708], color="copper"),
                B("lag", "cylinder", name="Felt lagging", r=0.03, h=0.4, pos=[-0.12, 0.06, 0], rot=[0, 0, 1.5708], color="#d9d2c0", opacity=0.9),
                B("coil", "torus", name="Water-cooled coil", r=0.03, tube=0.005, pos=[0.18, 0.06, 0], rot=[0, 1.5708, 0], color="copper")],
        knobs=[knob("K", "Bar material (K hidden)", "K", 20, 450, 0.1, 401, "W/(m·K)", 1.0, hidden=True),
               knob("flow", "Water flow", "mdot", 0.1, 2.0, 0.01, 0.94, "g/s", 0.001,
                    hint="Set the tap so the water leaves 6 to 10 °C warmer than it enters.")],
        instruments=[inst("t1", "readout", "Thermometer 1 (on the bar)", "th1", unit="°C", lc=0.1, digits=1),
                     inst("t2", "readout", "Thermometer 2 (on the bar)", "th2", unit="°C", lc=0.1, digits=1),
                     inst("tout", "readout", "Water leaving the coil", "Tout", unit="°C", lc=0.1, digits=1),
                     inst("sw", "stopwatch", "Stopwatch")],
        table={"columns": [col("m", "Water collected", "manual", "g", 0.001, digits=0),
                           col("t", "Time", "inst:sw", "s", digits=0),
                           col("dTw", "Rise of the water Tout − Tin", "manual", "K", digits=1),
                           col("dth", "Fall along the bar θ1 − θ2", "manual", "K", digits=1)],
               "calc": "hw_searle_K", "rows_min": 2, "truth": "p.K", "result_digits": 0, "result_unit": "W/(m·K)",
               "hint": "Wait until the two bar thermometers stop changing for 5 minutes, then collect water for a timed interval."},
        steps=["Measure the diameter of the bar with a screw gauge and the distance between the two thermometer holes.",
               "Pass steam through the chamber and start the cooling water; set the flow so the rise in the water is 6 to 10 °C.",
               "Wait for the steady state: the two bar thermometers must hold their readings for at least 5 minutes.",
               "Read both bar thermometers and the water entering and leaving; collect the water for 5 minutes and weigh it.",
               "K = m c (Tout − Tin) (x2 − x1) / (t A (θ1 − θ2))."],
        theory="In the steady state the heat that flows along the lagged bar, K A (θ1 − θ2) / (x2 − x1) each second, is "
               "carried away by the cooling water, m c (Tout − Tin) / t. Equating the two gives K. The felt lagging "
               "stops heat leaving through the sides, so the flow is along the bar only. The thermometers are read "
               "only after the readings stop drifting.",
        safety="Steam burns badly. Let the teacher light the boiler, keep your hands away from the steam chamber and "
               "use a mat to hold the hot thermometers.",
        tour=[{"say": "A copper bar, lagged with felt, runs from a steam chamber on the left to a water-cooled coil on the right."},
              {"say": "Two thermometers in the bar read the fall in temperature; the cooling water measures the heat that reached the end."}],
        questions=[{"q": "Why is the bar wrapped in felt?", "options": ["So heat does not leak sideways", "To keep it cold", "To make it heavier"],
                    "answer": 0, "why": "With no sideways loss, all the heat that enters the bar leaves through the coil."},
                   {"q": "When are the thermometer readings taken?", "options": ["When they have stopped drifting", "At once", "When the water boils"],
                    "answer": 0, "why": "Only in the steady state is the heat flow the same through every part of the bar."}],
        sources=[CRC, DU, IP, SIM],
        check={"params": {"K": 401.0, "mdot": 9.4e-4}, "reading": "K", "textbook": "hw_searle_K"},
    )


# =============================================================================================== LEE'S DISC
def lees_disc() -> dict:
    return lab(
        id="lees-disc", title="Thermal conductivity of a bad conductor by Lee and Charlton's disc",
        group="Physics · Heat", level="B.Sc.", topic="Conduction of heat", chapter="Heat and thermodynamics",
        aim="Find the thermal conductivity of a glass or ebonite disc from its steady temperatures and the rate at which "
            "the bare brass disc cools.",
        kernel="hw_lees", params={}, speeds=[1, 5, 10, 30], autorun=False,
        camera={"pos": [0.35, 0.3, 0.7], "look": [0, 0.15, 0]}, floor=-0.02,
        bodies=[_board(1.2, 0.6),
                B("stand", "box", name="Stand base", size=[0.25, 0.02, 0.2], pos=[0, 0.01, 0.0], color="#2b2f36"),
                B("chest", "cylinder", name="Steam chest", r=0.03, h=0.06, pos=[0, 0.28, 0], color="brass"),
                B("samp", "cylinder", name="Sample disc", info="The bad conductor under test.", r=0.025, h=0.008, pos=[0, 0.232, 0], color="glass", opacity=0.6),
                B("disc", "cylinder", name="Brass disc B", info="Its temperature θ2 is read by a thermometer in a hole.", r=0.025, h=0.01, pos=[0, 0.222, 0], color="brass")],
        knobs=[knob("k", "Sample (k hidden)", "k", 0.05, 2.0, 0.001, 1.05, "W/(m·K)", 1.0, hidden=True),
               knob("d", "Thickness of the sample", "d", 1.0, 12.0, 0.1, 8.0, "mm", 0.001)],
        instruments=[inst("t2", "readout", "Disc B temperature", "T", unit="°C", lc=0.1, digits=1),
                     inst("sw", "stopwatch", "Stopwatch")],
        table={"columns": [col("th1", "Temperature of the heated plate θ1", "manual", "°C", digits=1),
                           col("th2", "Steady temperature of disc B θ2", "manual", "°C", digits=1),
                           col("dtdt", "Cooling rate at θ2", "manual", "K/s", digits=4)],
               "calc": "hw_lees_k", "rows_min": 2, "truth": "p.k", "result_digits": 3, "result_unit": "W/(m·K)",
               "hint": "Cool the bare disc through θ2 ± 2.5 K and time it: the rate is 5 K divided by that time."},
        steps=["Measure the thickness of the sample with a screw gauge and the radius and thickness of the brass disc.",
               "Put the sample between the heated plate and disc B and heat until θ1 and θ2 stop changing.",
               "Remove the sample, heat disc B directly to about 3 K above θ2 and let it cool.",
               "Time the fall from θ2 + 2.5 K to θ2 − 2.5 K to find the cooling rate at θ2.",
               "k = m s (dθ/dt) (r + 2h) / (2r + 2h) · d / (π r² (θ1 − θ2))."],
        theory="With the sample on, the heat that crosses it equals the heat lost from the lower face and the edge of "
               "disc B (its top face is covered). That loss is found by letting the bare disc cool: it loses heat over "
               "its whole surface, so only the fraction (r + 2h)/(2r + 2h) of the bare loss applies. This gives k.",
        safety="The steam chest and the disc are hot. Handle the sample with tongs and let everything cool before dismantling.",
        tour=[{"say": "A steam chest on top, the sample disc under it and the brass disc B at the bottom."},
              {"say": "Heat flows down through the sample into disc B, which loses it to the air from its lower face and edge."}],
        questions=[{"q": "Why is the cooling rate measured with the sample removed?", "options": ["To find how fast disc B loses heat at θ2", "To clean the disc", "To heat the sample"],
                    "answer": 0, "why": "At the steady state, the heat through the sample equals the heat disc B loses, and the bare disc's cooling rate measures that loss."},
                   {"q": "Why is the factor (r + 2h)/(2r + 2h) used?", "options": ["The top face of B is covered during the steady state", "Brass is a bad conductor", "The thermometer is large"],
                    "answer": 0, "why": "With the sample on, B loses heat from its lower face and edge only."}],
        sources=[CRC, DU, SIM],
        check={"params": {"k": 1.05, "d": 0.008, "Th": 100.0}, "reading": "k", "textbook": "hw_lees_k"},
    )


# =============================================================================================== THERMOCOUPLE
def _tc_bodies(second: str) -> list[dict]:
    return [_board(1.4, 0.7),
            B("bath", "cylinder", name="Stirred bath on a heater", r=0.07, h=0.12, open=True, pos=[-0.4, 0.06, 0], color="glass", opacity=0.35),
            B("ice", "cylinder", name="Ice flask (cold junction)", r=0.04, h=0.12, open=True, pos=[-0.15, 0.06, 0.12], color="glass", opacity=0.35),
            B("pot", "box", name="Potentiometer wire" if second == "pot" else "Op-amp amplifier box", size=[0.5, 0.04, 0.12], pos=[0.35, 0.02, 0], color="wood" if second == "pot" else "#2b2f36"),
            B("wire", "rope", name="Thermocouple wires", a=[-0.4, 0.14, 0], b=[-0.15, 0.14, 0.12], r=0.002, color="copper")]


def tc_null() -> dict:
    return lab(
        id="thermocouple-null-method", title="Thermo-emf of a copper-constantan thermocouple by a null method, and calibration",
        group="Physics · Heat", level="B.Sc.", topic="Thermoelectricity", chapter="Heat and thermodynamics",
        aim="Heat one junction of a thermocouple in a water bath, keep the other in melting ice, balance the thermo-emf "
            "on a potentiometer and plot the calibration curve.",
        kernel="hw_tcouple", params={"G": 0.0}, speeds=[1, 5, 10, 30], autorun=False,
        camera={"pos": [0.4, 0.45, 1.2], "look": [0.0, 0.1, 0.0]}, floor=-0.02,
        bodies=_tc_bodies("pot"),
        knobs=[knob("heat", "Heater (0 off, 1 on)", "on", 0, 1, 1, 0, "")],
        instruments=[inst("th", "readout", "Bath thermometer", "reading", unit="°C", lc=0.1, digits=1),
                     inst("emf", "readout", "Thermo-emf (the potentiometer will find it)", "e", k=1000, unit="mV", digits=3, hint=True)],
        table={"columns": [col("T", "Bath temperature T", "manual", "°C", digits=1),
                           col("l", "Balancing length l", "manual", "cm", 0.01, digits=1)],
               "calc": "hw_tc_slope", "rows_min": 6, "result_digits": 6, "result_unit": "V/K",
               "hint": "Turn the heater off 3 °C before each target, let the bath settle, then find the null length."},
        steps=["Put the cold junction in melting ice and the hot junction in the stirred water bath.",
               "Standardise the potentiometer: the driver cell gives a known fall of potential per metre of wire.",
               "At each bath temperature, move the jockey until the galvanometer shows no deflection and read l.",
               "Take at least six readings from room temperature to about 90 °C and plot E = k l against T.",
               "The slope of the curve at 50 °C is the thermo-emf per degree."],
        theory="When the two junctions of a pair of dissimilar metals are at different temperatures a thermo-emf appears. "
               "For a modest range e = a (T − Tc) + q (T² − Tc²). The potentiometer balances it without drawing current: "
               "at the null point e = k l, where k is the fall of potential per unit length of the wire.",
        safety="Hot water scalds. Keep the junction clear of the heater and handle the thermometer by its top.",
        tour=[{"say": "A hot bath on the left, an ice flask for the cold junction, and a potentiometer on the right."}],
        questions=[{"q": "Why is a potentiometer used for a thermo-emf?", "options": ["It draws no current at the null point", "It is cheaper", "It makes the emf bigger"],
                    "answer": 0, "why": "A voltmeter would draw current and drop the measured voltage; at balance a potentiometer draws none."},
                   {"q": "The graph of thermo-emf against temperature is", "options": ["nearly a straight line, slightly curved", "a circle", "flat"],
                    "answer": 0, "why": "e = a ΔT + q (T² − Tc²) has a small quadratic part."}],
        sources=[{"title": "NIST ITS-90 thermocouple tables, type T (copper-constantan): 2.036 mV at 50 °C, 4.279 mV at 100 °C"}, DU, SIM],
        check={"params": {"a": 38.65e-6, "q": 4.14e-8, "Th": 60.0}, "reading": "e", "textbook": "hw_tc_emf"},
    )


def tc_opamp() -> dict:
    return lab(
        id="thermocouple-opamp", rig="thermocouple-null-method",
        title="Thermocouple calibration with an op-amp amplifier and neutral temperature",
        group="Physics · Heat", level="B.Sc.", topic="Thermoelectricity", chapter="Heat and thermodynamics",
        aim="Amplify the thermo-emf of a copper-iron couple with an op-amp, plot the output against the hot-junction "
            "temperature up to about 330 °C and find the neutral temperature at the top of the curve.",
        kernel="hw_tcouple",
        params={"a": 13.4e-6, "q": -2.4815e-8, "G": 101.0, "P": 300.0, "C": 1200.0, "hA": 0.8, "Tcap": 400.0, "Th": 200.0},
        speeds=[1, 5, 10, 30], autorun=False,
        camera={"pos": [0.4, 0.45, 1.2], "look": [0.0, 0.1, 0.0]}, floor=-0.02,
        bodies=_tc_bodies("amp"),
        knobs=[knob("heat", "Heater (0 off, 1 on)", "on", 0, 1, 1, 0, "")],
        instruments=[inst("th", "readout", "Oil-bath thermometer", "reading", unit="°C", lc=0.1, digits=1),
                     inst("vo", "readout", "Amplifier output", "Vout", k=1000, unit="mV", digits=1)],
        table={"columns": [col("T", "Hot-junction temperature T", "manual", "°C", digits=1),
                           col("Vout", "Amplifier output", "manual", "mV", 0.001, digits=1)],
               "calc": "hw_tc_neutral", "rows_min": 8, "result_digits": 0, "result_unit": "°C",
               "hint": "Heat the oil bath slowly and read the output every 30 °C; go past the top of the curve."},
        steps=["Zero the amplifier with both junctions in ice; its gain is 1 + Rf/R1 = 101.",
               "Heat the oil bath and read the output voltage every 30 °C up to about 330 °C.",
               "Divide the output by the gain to get the thermo-emf and plot it against T.",
               "The curve is a parabola: its highest point is at the neutral temperature Tn."],
        theory="For a copper-iron couple e = a (T − Tc) + q (T² − Tc²) with q negative, so e rises, reaches a maximum at "
               "the neutral temperature Tn = −a / (2q) and falls again. The amplifier of gain G = 1 + Rf/R1 turns the "
               "small emf into a voltage a digital meter can read.",
        safety="Hot oil is dangerous: heat it slowly, keep water away from it, and let it cool before moving the bath.",
        tour=[{"say": "The same bench, but the readout is an op-amp amplifier, and the bath is oil, which can go well above 100 °C."}],
        questions=[{"q": "The gain of the amplifier is 1 + Rf/R1. With Rf = 100 kΩ and R1 = 1 kΩ it is", "options": ["101", "100", "1"], "answer": 0,
                    "why": "1 + 100/1 = 101."},
                   {"q": "At the neutral temperature the thermo-emf", "options": ["is at its maximum", "is zero", "changes sign"], "answer": 0,
                    "why": "de/dT = 0 there, so the curve turns over."}],
        sources=[{"title": "Absolute thermoelectric power at 0 °C: copper about +1.8, iron about +15 µV/K (CRC Handbook); neutral temperature of a copper-iron couple about 270 °C (standard B.Sc. heat textbooks)"}, DU, SIM],
        check={"params": {"a": 13.4e-6, "q": -2.4815e-8, "Th": 200.0}, "reading": "e", "textbook": "hw_tc_emf"},
    )


# =============================================================================================== RTD
def _rtd_bodies() -> list[dict]:
    return [_board(1.4, 0.7),
            B("bath", "cylinder", name="Stirred bath on a heater", r=0.07, h=0.12, open=True, pos=[-0.4, 0.06, 0], color="glass", opacity=0.35),
            B("probe", "cylinder", name="Platinum resistance probe", r=0.003, h=0.2, pos=[-0.4, 0.1, 0], color="steel"),
            B("bridge", "box", name="Wheatstone bridge and decade box", size=[0.5, 0.05, 0.14], pos=[0.3, 0.025, 0], color="#2b2f36")]


def prt() -> dict:
    return lab(
        id="platinum-resistance-thermometer", title="Temperature coefficient of resistance with a platinum resistance thermometer",
        group="Physics · Heat", level="B.Sc.", topic="Resistance thermometry", chapter="Heat and thermodynamics",
        aim="Measure the resistance of a Pt100 element at the ice point and at the steam point on a Wheatstone bridge "
            "and find its mean temperature coefficient of resistance between 0 and 100 °C.",
        kernel="hw_rtd", params={}, speeds=[1, 5, 10, 30], autorun=False,
        camera={"pos": [0.4, 0.45, 1.2], "look": [0.0, 0.1, 0.0]}, floor=-0.02,
        bodies=_rtd_bodies(),
        knobs=[knob("heat", "Heater (0 off, 1 on)", "on", 0, 1, 1, 0, "")],
        instruments=[inst("th", "readout", "Bath thermometer", "reading", unit="°C", lc=0.1, digits=1),
                     inst("rr", "readout", "Resistance of the probe (the bridge will find it)", "R", unit="Ω", digits=2, hint=True)],
        table={"columns": [col("T", "Temperature T", "manual", "°C", digits=1), col("R", "Resistance R", "manual", "Ω", digits=2)],
               "calc": "hw_rtd_alpha", "rows_min": 2, "result_digits": 6, "result_unit": "1/K",
               "hint": "Read R in melting ice (0 °C) and in boiling water (100 °C); a few points between make the graph."},
        steps=["Put the probe in melting ice and balance the bridge: the decade box then equals the probe's resistance R0.",
               "Heat the bath, reading R at several temperatures on the way.",
               "At the steam point (boiling water) read R100.",
               "α = (R100 − R0) / (100 × R0)."],
        theory="The resistance of platinum rises almost linearly with temperature: R = R0 (1 + A t + B t²), with A = "
               "3.9083×10⁻³ and B = −5.775×10⁻⁷ for the standard element. Its mean temperature coefficient between "
               "0 and 100 °C is α = (R100 − R0) / (100 R0), about 3.85×10⁻³ per kelvin.",
        safety="Keep the bridge current small so the probe does not heat itself. Boiling water scalds.",
        tour=[{"say": "A Pt100 probe in a stirred bath, and a Wheatstone bridge with a decade resistance box."}],
        questions=[{"q": "A Pt100 element has a resistance of 100 Ω at", "options": ["0 °C", "100 °C", "25 °C"], "answer": 0, "why": "The 100 in Pt100 is its resistance at the ice point."},
                   {"q": "At the balance point of the bridge", "options": ["the galvanometer shows no current", "the bath boils", "the probe is at 0 °C"], "answer": 0,
                    "why": "With equal ratio arms the decade box equals the probe resistance when no current flows through the galvanometer."}],
        sources=[{"title": "IEC 60751 / ITS-90 platinum resistance thermometer: A = 3.9083e-3 per °C, B = -5.775e-7 per °C^2, alpha = 0.00385055 per K"}, DU, SIM],
        check={"params": {"R0": 100.0, "A": 3.9083e-3, "B": -5.775e-7}, "reading": "alpha", "textbook": "hw_rtd_alpha"},
    )


def rtd_cal() -> dict:
    return lab(
        id="rtd-calibration", rig="platinum-resistance-thermometer", title="Calibration of a resistance temperature device",
        group="Physics · Heat", level="B.Sc.", topic="Resistance thermometry", chapter="Heat and thermodynamics",
        aim="Calibrate a Pt100 resistance temperature device against a mercury thermometer from room temperature to "
            "boiling and find the slope of its calibration curve at 50 °C.",
        kernel="hw_rtd", params={"mode": 0.0}, speeds=[1, 5, 10, 30], autorun=False,
        camera={"pos": [0.4, 0.45, 1.2], "look": [0.0, 0.1, 0.0]}, floor=-0.02,
        bodies=_rtd_bodies(),
        knobs=[knob("heat", "Heater (0 off, 1 on)", "on", 0, 1, 1, 0, "")],
        instruments=[inst("th", "readout", "Bath thermometer", "reading", unit="°C", lc=0.1, digits=1),
                     inst("rr", "readout", "Resistance of the probe (the bridge will find it)", "R", unit="Ω", digits=2, hint=True)],
        table={"columns": [col("T", "Temperature T", "manual", "°C", digits=1), col("R", "Resistance R", "manual", "Ω", digits=2)],
               "calc": "hw_rtd_slope", "rows_min": 6, "result_digits": 4, "result_unit": "Ω/K",
               "hint": "Take at least six readings between room temperature and boiling; fit a curve through them."},
        steps=["Set up the bridge with equal ratio arms and balance it (null method) or read its output (off-balance method).",
               "Heat the bath and at each temperature read the mercury thermometer and the bridge.",
               "Plot R against T and fit a smooth curve through the points.",
               "The slope of the curve at 50 °C is the sensitivity of the device there."],
        theory="A resistance temperature device is calibrated by comparing it with a reference thermometer. For platinum "
               "the calibration curve is R = R0 (1 + A t + B t²); its slope dR/dt = R0 (A + 2 B t) falls slowly as the "
               "temperature rises. In the off-balance bridge the output Vg = Vs (R / (R + Rref) − 1/2) gives R.",
        safety="Keep the bridge current small so the probe does not heat itself. Boiling water scalds.",
        tour=[{"say": "The probe goes in the same stirred bath as a reference thermometer, so both read the same temperature."}],
        questions=[{"q": "Why is the slope of the calibration curve not quite constant?", "options": ["R has a small t² term", "The bath cools", "The bridge drifts"], "answer": 0,
                    "why": "R = R0 (1 + A t + B t²), so dR/dt = R0 (A + 2 B t)."},
                   {"q": "In the off-balance bridge you read", "options": ["the output voltage", "a null on the galvanometer", "the bath volume"], "answer": 0,
                    "why": "The unbalanced bridge gives a voltage that depends on R."}],
        sources=[{"title": "IEC 60751 / ITS-90 platinum resistance thermometer: A = 3.9083e-3 per °C, B = -5.775e-7 per °C^2"}, DU, SIM],
        check={"params": {"R0": 100.0, "A": 3.9083e-3, "B": -5.775e-7, "Tm": 50.0}, "reading": "slope", "textbook": "hw_rtd_slope"},
    )


# =============================================================================================== WAVES
def melde() -> dict:
    return lab(
        id="melde-experiment", title="Frequency of an electrically maintained tuning fork by Melde's experiment",
        group="Physics · Waves", level="B.Sc.", topic="Standing waves on a string", chapter="Oscillations, waves and acoustics",
        aim="Hang a pan from a thread driven by a tuning fork, change the load until a whole number of loops stands, and "
            "find the frequency of the fork from the tension and the length of the loops.",
        kernel="hw_melde", params={"f": 128.0, "p0": 5.0}, speeds=[1, 2, 5], autorun=False,
        camera={"pos": [0.4, 0.45, 1.5], "look": [0.0, 0.1, 0.0]}, floor=-0.02,
        bodies=[_board(2.0, 0.6),
                B("fork", "box", name="Electrically maintained fork", size=[0.12, 0.08, 0.08], pos=[-0.8, 0.06, 0], color="steel"),
                B("thread", "rope", name="Thread", a=[-0.74, 0.07, 0], b=[0.3, 0.07, 0], r=0.001, color="white"),
                B("pulley", "cylinder", name="Pulley", r=0.03, h=0.01, pos=[0.3, 0.07, 0], rot=[1.5708, 0, 0], color="brass"),
                B("pan", "cylinder", name="Pan with weights", r=0.04, h=0.015, pos=[0.3, -0.2, 0], color="steel")],
        knobs=[knob("f", "Fork (f hidden)", "f", 20, 600, 1, 128, "Hz", 1.0, hidden=True),
               knob("M", "Load on the pan", "M", 0.005, 0.2, 0.001, 0.07, "g", 0.001)],
        instruments=[inst("amp", "readout", "Loop sharpness (1 = best)", "amp", digits=2), inst("loops", "readout", "Loops standing", "p", digits=0)],
        table={"columns": [col("M", "Load M (pan + weights)", "knob:M", "g", 0.001, digits=1), col("p", "Number of loops p", "manual", "", digits=0)],
               "calc": "hw_melde_f", "rows_min": 3, "truth": "p.f", "result_digits": 1, "result_unit": "Hz",
               "hint": "Add weights one gram at a time until the loops are sharpest, then count them."},
        steps=["Weigh a known length of the thread to get its mass per unit length μ.",
               "Set the fork to vibrate across the thread (transverse) and hang the pan from the pulley.",
               "Add weights until the thread shows sharp loops; count the loops p between the fork and the pulley.",
               "Repeat for three different numbers of loops, then f = 2 (p / l) √(Mg/μ) / 2 for the transverse arrangement."],
        theory="A thread of mass μ per unit length under tension T = Mg carries waves at v = √(T/μ). It stands in p loops "
               "when its length l = p λ / 2. In the transverse arrangement the thread moves at half the fork's frequency, "
               "so f = (p / l) √(T/μ); in the longitudinal arrangement it moves at the fork's own frequency, f = (p / 2l) √(T/μ).",
        safety="Keep the load low enough that the thread does not snap, and keep your feet clear of the falling weights.",
        tour=[{"say": "A fork drives one end of a thread; the other end passes over a pulley to a pan of weights."}],
        questions=[{"q": "In the transverse arrangement the thread vibrates at", "options": ["half the fork frequency", "the fork frequency", "twice the fork frequency"], "answer": 0,
                    "why": "The fork's prong moves across the thread, which then goes through one cycle for every two of the fork."},
                   {"q": "If the load is made four times larger, the number of loops", "options": ["halves", "doubles", "stays the same"], "answer": 0,
                    "why": "v = √(T/μ) doubles, so the wavelength doubles and half as many fit."}],
        sources=[{"title": "Scientific-pitch tuning forks: C = 256 Hz, its lower octave 128 Hz (standard tuning-fork set)"}, DU, HNB, IP, SIM],
        check={"params": {"f": 128.0, "mode": 0.0, "p0": 5.0}, "reading": "f", "textbook": "hw_melde_f"},
    )


def lissajous() -> dict:
    return lab(
        id="lissajous-figures", title="Superposition of two SHMs on a CRO: Lissajous figures",
        group="Physics · Waves", level="B.Sc.", topic="Superposition of oscillations", chapter="Oscillations, waves and acoustics",
        aim="Feed two audio generators to the X and Y plates of an oscilloscope, tune one until a steady figure forms, "
            "and find the frequency ratio and the phase difference from it.",
        kernel="hw_lissajous", params={"fx": 100.0, "fy": 150.0}, speeds=[1], autorun=False,
        camera={"pos": [0.3, 0.4, 1.0], "look": [0.0, 0.15, 0.0]}, floor=-0.02,
        bodies=[_board(1.4, 0.6),
                B("cro", "box", name="Cathode ray oscilloscope", size=[0.3, 0.25, 0.3], pos=[0, 0.125, -0.1], color="#9aa3ad"),
                B("g1", "box", name="Audio generator X", size=[0.2, 0.08, 0.15], pos=[-0.4, 0.04, 0.05], color="#2b2f36"),
                B("g2", "box", name="Audio generator Y", size=[0.2, 0.08, 0.15], pos=[0.4, 0.04, 0.05], color="#2b2f36")],
        knobs=[knob("fy", "Generator Y (frequency hidden)", "fy", 20, 1000, 1, 150, "Hz", 1.0, hidden=True),
               knob("fx", "Generator X dial", "fx", 20, 1000, 1, 100, "Hz", 1.0)],
        instruments=[inst("rat", "readout", "Ratio fy / fx (help)", "ratio", digits=3, hint=True)],
        table={"columns": [col("fx", "Generator X frequency fx", "knob:fx", "Hz", digits=0), col("nt", "Touches on the top edge", "manual", "", digits=0),
                           col("ns", "Touches on the side edge", "manual", "", digits=0)],
               "calc": "hw_liss_fy", "rows_min": 3, "truth": "p.fy", "result_digits": 1, "result_unit": "Hz",
               "hint": "Tune fx until the figure stops moving, then count where it touches a horizontal and a vertical tangent."},
        steps=["Connect generator X to the X input and generator Y to the Y input, with the time base off.",
               "Set fx to a simple fraction of the unknown frequency and watch the figure; tune until it is steady.",
               "Count the touches of the figure on the top edge and on the side edge of a box drawn round it.",
               "fy = fx × (touches on the top) / (touches on the side). Repeat for three steady figures.",
               "For equal frequencies the figure is an ellipse: sin φ = y0 / ymax."],
        theory="Two perpendicular simple harmonic motions x = a sin(2π fx t), y = b sin(2π fy t + φ) trace a closed Lissajous "
               "figure when fy/fx is a ratio of small whole numbers. A tangent line drawn along the top edge touches the "
               "figure fy times where one drawn along the side edge touches it fx times (after cancelling), so "
               "fy / fx equals the ratio of the two touch counts.",
        safety="Keep the beam intensity low so the screen is not burnt.",
        tour=[{"say": "Two generators feed the plates of an oscilloscope; the electron beam draws the figure."}],
        questions=[{"q": "A figure touches the top edge 3 times and the side edge 2 times. fy/fx is", "options": ["3/2", "2/3", "1"], "answer": 0,
                    "why": "fy / fx = touches on the top / touches on the side."},
                   {"q": "A drifting figure means", "options": ["the two frequencies are not in exact ratio", "the beam is off", "the phase is 90°"], "answer": 0,
                    "why": "A small frequency difference makes the relative phase change slowly."}],
        sources=[DU, IP, SIM],
        check={"params": {"fx": 100.0, "fy": 150.0}, "reading": "fy", "textbook": "hw_liss_fy"},
    )


def kundt() -> dict:
    return lab(
        id="kundt-tube", title="Speed of sound in a rod with Kundt's tube",
        group="Physics · Waves", level="B.Sc.", topic="Standing waves in air", chapter="Oscillations, waves and acoustics",
        aim="Make a clamped brass rod sing so that dust in a glass tube heaps at the nodes, measure the heap spacing, and "
            "find the speed of sound in the rod.",
        kernel="hw_kundt", params={}, speeds=[1], autorun=False,
        camera={"pos": [0.2, 0.4, 1.4], "look": [0.0, 0.1, 0.0]}, floor=-0.02,
        bodies=[_board(2.2, 0.6),
                B("tube", "cylinder", name="Glass tube with dust", r=0.025, h=1.0, open=True, pos=[0.1, 0.07, 0], rot=[0, 0, 1.5708], color="glass", opacity=0.3),
                B("rod", "cylinder", name="Brass rod, clamped at the middle", r=0.01, h=1.0, pos=[-0.9, 0.07, 0], rot=[0, 0, 1.5708], color="brass"),
                B("piston", "cylinder", name="Piston", r=0.024, h=0.02, pos=[0.55, 0.07, 0], rot=[0, 0, 1.5708], color="steel")],
        knobs=[knob("vr", "Rod (v hidden)", "vr", 1000, 7000, 1, 3436, "m/s", 1.0, hidden=True),
               knob("Lp", "Piston position", "Lp", 0.1, 1.0, 0.001, 0.5, "cm", 0.01)],
        instruments=[inst("cl", "readout", "Dust figure sharpness (1 = best)", "clarity", digits=2),
                     inst("hv", "readout", "Heaps standing", "n", digits=0)],
        table={"columns": [col("Lrod", "Length of the rod", "manual", "cm", 0.01, digits=1), col("dd", "Spacing of the dust heaps d", "manual", "cm", 0.01, digits=2)],
               "calc": "hw_kundt_v", "rows_min": 2, "truth": "p.vr", "result_digits": 0, "result_unit": "m/s",
               "hint": "Move the piston until the dust is sharpest; read the first and last of eight heaps and divide by seven."},
        steps=["Measure the length of the rod and clamp it exactly at its middle.",
               "Read the room temperature and work out the speed of sound in air.",
               "Stroke the rod with a rosined cloth and move the piston until the dust forms sharp, evenly spaced heaps.",
               "Measure the distance across eight heaps and divide by seven to get the spacing d.",
               "v(rod) = v(air) × L / d."],
        theory="A rod clamped at its middle vibrates longitudinally with a node there and antinodes at both ends, so its "
               "wavelength is 2L and f = v(rod) / 2L. The same frequency makes a standing wave in the air column whose "
               "nodes are λ(air)/2 = d apart. Dividing, v(rod) / v(air) = L / d. Young's modulus follows from Y = ρ v².",
        safety="Do not breathe the lycopodium dust; keep the tube stoppered. Do not stroke the glass rod hard.",
        tour=[{"say": "The rod sings; its disc at the tube's end shakes the air column and the dust piles up at the nodes."}],
        questions=[{"q": "The distance between neighbouring dust heaps is", "options": ["half a wavelength of the sound in air", "a whole wavelength", "a quarter wavelength"], "answer": 0,
                    "why": "Neighbouring nodes of a standing wave are λ/2 apart."},
                   {"q": "A rod clamped at its middle sings with a wavelength of", "options": ["twice its length", "its length", "half its length"], "answer": 0,
                    "why": "It has a node in the middle and antinodes at both ends, i.e. half a wavelength."}],
        sources=[{"title": "Young's moduli and densities of metals, glass: CRC Handbook of Chemistry and Physics; v(rod) = √(Y/ρ) for a thin rod"}, IP, SIM],
        check={"params": {"vr": 3436.0, "Lr": 1.0, "Tc": 25.0}, "reading": "vr", "textbook": "hw_kundt_v"},
    )


def usonic() -> dict:
    return lab(
        id="ultrasonic-interferometer", title="Velocity of ultrasound in a liquid with an ultrasonic interferometer",
        group="Physics · Waves", level="B.Sc.", topic="Ultrasonic waves", chapter="Oscillations, waves and acoustics",
        aim="Move a reflector through a liquid in a 2 MHz cell, count the maxima of the crystal current, and find the "
            "velocity of ultrasound and the adiabatic compressibility.",
        kernel="hw_usonic", params={}, speeds=[1], autorun=False,
        camera={"pos": [0.3, 0.35, 0.8], "look": [0.0, 0.1, 0.0]}, floor=-0.02,
        bodies=[_board(1.2, 0.6),
                B("cell", "cylinder", name="Measuring cell with liquid", r=0.03, h=0.08, open=True, pos=[-0.15, 0.04, 0], color="steel"),
                B("mic", "cylinder", name="Micrometer screw", r=0.01, h=0.1, pos=[-0.15, 0.13, 0], color="steel"),
                B("gen", "box", name="High-frequency generator", size=[0.3, 0.15, 0.2], pos=[0.25, 0.075, 0], color="#2b2f36")],
        knobs=[knob("v", "Liquid (v hidden)", "v", 900, 2200, 1, 1482, "m/s", 1.0, hidden=True)],
        instruments=[inst("ma", "readout", "Crystal current", "I", unit="µA", digits=1)],
        table={"columns": [col("n", "Number of the maximum n", "manual", "", digits=0), col("x", "Micrometer reading x", "manual", "mm", 0.001, digits=3)],
               "calc": "hw_usonic_v", "rows_min": 6, "truth": "p.v", "result_digits": 0, "result_unit": "m/s",
               "hint": "Turn the micrometer slowly; each time the current peaks, write the reading."},
        steps=["Fill the cell with the liquid and switch the generator on at 2 MHz.",
               "Turn the micrometer screw slowly and watch the current meter rise and fall.",
               "Note the micrometer reading at ten successive maxima.",
               "Distance between the first and last maximum d = n λ / 2, so v = 2 f d / n.",
               "Adiabatic compressibility β = 1 / (ρ v²)."],
        theory="Sound from the crystal is reflected by the movable plate. When the distance is a whole number of half "
               "wavelengths the reflected wave reinforces the crystal's vibration and its current peaks. Successive "
               "maxima are λ/2 apart, so λ = 2d/n and v = f λ. The adiabatic compressibility of the liquid is β = 1/(ρ v²).",
        safety="Do not run the generator with an empty cell: the crystal can overheat. Keep the liquid away from the electronics.",
        tour=[{"say": "The cell holds the liquid; a quartz crystal at the bottom and a reflector on a micrometer at the top."}],
        questions=[{"q": "Neighbouring current maxima are separated by", "options": ["half a wavelength of the sound", "one wavelength", "a quarter wavelength"], "answer": 0,
                    "why": "The standing wave repeats every λ/2 of reflector travel."},
                   {"q": "The adiabatic compressibility is found from", "options": ["β = 1 / (ρ v²)", "β = ρ v²", "β = v / ρ"], "answer": 0,
                    "why": "The bulk modulus ρv² is the reciprocal of the compressibility."}],
        sources=[{"title": "Speed of sound in liquids: water 1482 m/s at 20 °C, glycerol 1904 m/s (CRC Handbook of Chemistry and Physics); densities from the same tables"}, DU, SIM],
        check={"params": {"v": 1482.0}, "reading": "v", "textbook": "hw_usonic_v"},
    )


BUILDERS = (searle, lees_disc, tc_null, tc_opamp, prt, rtd_cal, melde, lissajous, kundt, usonic)
