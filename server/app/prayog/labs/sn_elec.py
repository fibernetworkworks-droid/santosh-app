"""Lab pack `sn_elec`: undergraduate SENSOR, INSTRUMENT, ANALOG and COMMUNICATION set-ups of `syllabus/physics/ug.json`
(chapters "Electronic instrumentation and sensors", "Analog electronics and devices" and "Communication electronics and
microwaves"). The physics is in `packs/sn_elec.py` (and its JavaScript twin); every lab here names the studio RIG that
draws the bench:

  rig `sn-sensor-bench`   a sensor on the bench, a stimulus the hand sets, two digital multimeters and a record book
  rig `sn-scope-bench`    a breadboard, a function generator and a two-channel scope whose screen is drawn from the
                          sampled waveform of the lab's own kernel
  rig `msc-signal-bench`  (existing) the feedback-oscillator bench, reused for the three oscillator set-ups

Every lab's `check` compares one reading the kernel finds on its own simulated signal with an exact textbook relation.
Bench supplies only: every voltage here is a low-voltage laboratory source, and no step handles mains.
"""
from __future__ import annotations

from ..catalog import B, SIM, board, dial, inst, knob, lab

GROUP = "Physics · Electronics"
LEVEL = "B.Sc. (Hons.) Physics"
CH_SENS = "Electronic instrumentation and sensors"
CH_ANA = "Analog electronics and devices"
CH_COM = "Communication electronics and microwaves"

DU = {"title": "University of Delhi B.Sc. (Hons.) Physics laboratory lists: DSE Experimental Techniques, DSE Physics of "
               "Devices and Communication, C-X Analog Systems and SEC Basic of Instruments"}
IEC60063 = {"title": "IEC 60063 preferred number series (E12 / E24) for every resistor and capacitor value used"}
SEDRA = {"title": "A. S. Sedra and K. C. Smith, Microelectronic Circuits (small-signal CE amplifier, Miller effect, "
                  "diode wave-shaping circuits)"}
HOROWITZ = {"title": "P. Horowitz and W. Hill, The Art of Electronics, 3rd ed. (oscilloscope bandwidth and rise time "
                     "t_r = 0.35/BW, 555 timer, sensors and bridges)"}
HOROWITZ_SCOPE = {"title": "Tektronix, XYZs of Oscilloscopes primer: rise time t_r = 0.35/BW and the 10-90 % definition"}
BEAUTY = {"title": "Sensors: standard textbook relations (A. Morris and R. Langari, Measurement and Instrumentation: "
                   "LVDT, strain gauge bridge, capacitive level)"}
UNSOURCED = {"title": "Unsourced / illustrative settings", "note": "Values marked illustrative in the procedure are lab "
             "settings chosen to be typical; the relations that produce the readings are the textbook ones"}


def _bodies(extra: list[dict] | None = None, two: bool = True) -> list[dict]:
    out = [board(1.0, 0.6),
           B("rack", "box", name="Instrument rack", info="Supply, signal source and meters sit here.",
             size=[0.5, 0.1, 0.2], pos=[0.0, 0.05, -0.3], color="#2b2f36")]
    out += dial("dm1", [-0.3, 0.0, -0.1], "Digital multimeter 1", "Reads the sensor output.")
    if two:
        out += dial("dm2", [0.3, 0.0, -0.1], "Digital multimeter 2", "Reads the second quantity.")
    return out + list(extra or [])


def _mk(id, rig, title, aim, kernel, params, knobs, insts, theory, steps, questions, sources, check, chapter=CH_SENS,
        safety=None, extra=None, tour=None, two=True):
    return lab(
        id=id, rig=rig, title=title, group=GROUP, level=LEVEL, topic=chapter, chapter=chapter, aim=aim, kernel=kernel,
        params=params, autorun=True, camera={"pos": [0.0, 0.7, 0.85], "look": [0, 0.05, -0.1]}, floor=-0.03,
        bodies=_bodies(extra, two), knobs=knobs, instruments=insts, steps=steps, theory=theory,
        safety=safety or "Bench supplies only, a few volts. Switch the instrument off before changing a connection.",
        tour=tour or [{"say": "The sensor is on the bench with its stimulus; two multimeters read it and the record "
                              "book is on the left."}],
        questions=questions, sources=sources, check=check)


def _q(q, opts, ans, why):
    return {"q": q, "options": opts, "answer": ans, "why": why}


# ====================================================================================== LVDT
def lvdt() -> dict:
    return _mk(
        "sn-lvdt", "sn-sensor-bench", "LVDT: output against core displacement and an unknown displacement",
        "Move the core of an LVDT through known displacements, read the phase-sensitive output, find the sensitivity "
        "from the straight line, then use it to measure an unknown displacement.",
        "sn_lvdt", {"x": 0.002, "Vp": 3.0, "fex": 2500.0, "S": 20.0, "xs": 0.05, "Vq": 0.0015, "xu": 0.0037},
        [knob("x", "Core displacement from the centre", "x", -5, 5, 0.5, 2.0, "mm", k=1e-3),
         knob("xu", "Unknown displacement (hidden)", "xu", 0.1, 5, 0.01, 3.7, "mm", k=1e-3, hidden=True)],
        [inst("v", "readout", "Detector output", "Vout_mV", unit="mV", digits=2),
         inst("pp", "readout", "Secondary peak-to-peak", "Vpp_mV", unit="mV", digits=1),
         inst("gr", "graph", "Output against displacement", "Vout_mV", x="knob:x", xlabel="x (mm)", dots=True)],
        "A linear variable differential transformer has a primary between two secondaries wound in opposition. A "
        "movable core couples the primary more to one secondary than the other, so the output is zero at the "
        "centre and rises linearly with the core's displacement x, V = V_p S x, in phase with the primary on one "
        "side and in antiphase on the other. A phase-sensitive detector keeps that sign and rejects the small "
        "quadrature voltage left at the null. The slope of the line is the sensitivity; an unknown displacement "
        "is then read off the line.",
        ["Switch the instrument on and let the excitation settle: V_p = 3 V rms at 2.5 kHz.",
         "Move the core to the centre and read the detector: the residual is the null voltage.",
         "Move the core in steps on both sides and record the detector output at each position.",
         "Plot the output against displacement and fit a straight line through the points.",
         "Move the core to the unknown position, read the output and find the displacement from your line."],
        [_q("What happens to the output's phase when the core crosses the centre?",
            ["It reverses by 180 degrees", "It stays the same", "It advances by 90 degrees"], 0,
            "The two secondaries are wound in opposition, so the difference changes sign."),
         _q("Why is a phase-sensitive detector used instead of a plain rectifier?",
            ["It keeps the sign of the displacement and ignores the quadrature residual",
             "It makes the output larger", "It removes the need for a primary"], 0,
            "A rectifier cannot tell positive from negative displacement.")],
        [DU, BEAUTY, {"title": "Excitation 3 V rms at 2.5 kHz, sensitivity 20 mV/V/mm and null residual 1.5 mV rms",
                      "note": "Unsourced / illustrative: typical LVDT figures chosen for the lab; the relation is textbook"}],
        {"params": {"x": 0.002}, "reading": "Vout", "textbook": "sn_lvdt_v", "tol": 0.01})


# ====================================================================================== strain gauge
def strain() -> dict:
    return _mk(
        "sn-strain-gauge", "sn-sensor-bench", "Strain gauge on a cantilever: bridge output and an unknown weight",
        "Load a steel cantilever with known masses, read the bridge amplifier, find the strain from the bridge "
        "output, and use the line to weigh an unknown mass.",
        "sn_strain", {"m": 0.5, "L": 0.2, "b": 0.025, "h": 0.002, "E": 200.0e9, "GF": 2.0, "Vs": 5.0, "Rg": 350.0,
                      "nb": 1.0, "G": 100.0, "Voff": 0.0032, "mu": 0.773},
        [knob("m", "Load on the cantilever", "m", 0, 1.5, 0.1, 0.5, "kg"),
         knob("mu", "Unknown mass (hidden)", "mu", 0.2, 1.4, 0.001, 0.773, "kg", hidden=True)],
        [inst("v", "readout", "Amplifier output", "Vout_V", unit="V", digits=4),
         inst("e", "readout", "Strain at the gauge", "eps_ue", unit="µε", digits=1),
         inst("gr", "graph", "Output against load", "Vout_V", x="knob:m", xlabel="m (kg)", dots=True)],
        "A metal-foil gauge changes its resistance by dR/R = GF x strain, with a gauge factor GF of about 2. Four "
        "arms of a Wheatstone bridge turn that into a voltage: for one active gauge V = V_s d / (2(2 + d)), close to "
        "V_s GF strain / 4, and two or four active gauges give two or four times as much. At the root of a "
        "cantilever the strain from a load m g at distance L is 6 m g L / (E b h^2). An instrumentation amplifier "
        "of gain 100 lifts the millivolts to a readable level; the straight line of output against load is a "
        "calibration for weighing.",
        ["Check the gauge is bonded on the top face near the clamp and the bridge is balanced with no load.",
         "Switch on the bridge supply (5 V) and the amplifier, and record the output with no load: the offset.",
         "Hang the masses one after another and record the amplifier output each time.",
         "Plot output against mass; the slope is the volts per kilogram. Subtract the offset first.",
         "Hang the unknown mass and find it from your line. Then work out its strain from the bridge output."],
        [_q("Why does a half bridge give twice the output of a quarter bridge?",
            ["Two active gauges, one in tension and one in compression, both unbalance it the same way",
             "The supply voltage doubles", "The gauge factor doubles"], 0,
            "The two changes add at the bridge output."),
         _q("Why is the amplifier offset recorded with no load?",
            ["It must be subtracted from every reading", "To set the gauge factor", "To calibrate the masses"], 0,
            "The offset is added to every reading, loaded or not.")],
        [DU, BEAUTY, {"title": "Gauge factor 2.0 for a metal-foil gauge; E = 200 GPa for steel (standard handbook value); "
                               "350 ohm is a standard gauge resistance",
                      "note": "Amplifier offset 3.2 mV and the cantilever size are illustrative lab settings"}],
        {"params": {}, "reading": "Vb", "textbook": "sn_strain_vb", "tol": 0.01})


# ====================================================================================== capacitive level
def capl() -> dict:
    return _mk(
        "sn-capacitive-level", "sn-sensor-bench", "Capacitive level probe: calibration and an unknown level",
        "Fill a tank in steps, record the capacitance of a coaxial probe, find the sensitivity from the line, and "
        "measure the level in an unknown tank.",
        "sn_capl", {"h": 0.1, "H": 0.3, "a": 0.003, "b": 0.010, "er": 80.2, "Cs": 12.0e-12, "hu": 0.137},
        [knob("h", "Liquid level", "h", 0, 28, 2, 10.0, "cm", k=0.01),
         knob("hu", "Unknown level (hidden)", "hu", 3, 27, 0.1, 13.7, "cm", k=0.01, hidden=True)],
        [inst("c", "readout", "Probe capacitance", "C_pF", unit="pF", digits=1),
         inst("gr", "graph", "Capacitance against level", "C_pF", x="knob:h", xlabel="h (cm)", dots=True)],
        "A coaxial probe, an inner rod inside a tube, is a cylindrical capacitor C = 2 pi eps0 e_r L / ln(b/a). When "
        "a liquid of relative permittivity e_r fills the gap to a level h, the wet part has e_r and the dry part "
        "has 1, and the two are in parallel: C = 2 pi eps0 (H + (e_r - 1) h)/ln(b/a) + C_stray. The capacitance rises "
        "linearly with level at 2 pi eps0 (e_r - 1)/ln(b/a) per metre, so a straight-line calibration gives the level "
        "from a capacitance. The inner rod is insulated so a conducting liquid does not short it.",
        ["Connect the probe to the LCR meter with a short screened lead: its capacitance adds to the reading.",
         "Read the capacitance of the empty probe.",
         "Raise the level in steps of 2 cm and record the capacitance at each level.",
         "Plot capacitance against level; the slope is the sensitivity in picofarads per centimetre.",
         "Read the capacitance in the unknown tank and find its level from your line."],
        [_q("Why is the line straight?",
            ["The wet and dry parts are capacitors in parallel and the wet part grows in proportion to h",
             "The liquid is a perfect conductor", "The probe is very long"], 0,
            "Parallel capacitances add, and the wet length is h."),
         _q("What does the stray cable capacitance do to the calibration line?",
            ["It shifts the line up without changing its slope", "It changes the slope", "Nothing at all"], 0,
            "It adds a constant to every reading.")],
        [DU, BEAUTY, {"title": "Relative permittivity of water 80.2 at 20 degC: CRC Handbook of Chemistry and Physics, "
                               "table of dielectric constants of liquids"},
         {"title": "eps0 = 8.8541878128e-12 F/m (CODATA 2018)"}],
        {"params": {}, "reading": "dCdh", "textbook": "sn_capl_slope", "tol": 0.01})


# ====================================================================================== ultrasonic
def ultra() -> dict:
    return _mk(
        "sn-ultrasonic-ranging", "sn-sensor-bench", "Ultrasonic ranging: echo time against distance",
        "Measure the echo time of a 40 kHz burst for a target at known distances, find the speed of sound and the "
        "electronics delay from the line, then measure an unknown distance.",
        "sn_ultra", {"d": 0.5, "T": 20.0, "t0": 1.8e-4, "f": 40000.0, "A": 1.0, "dx": 0.737},
        [knob("d", "Target distance on the rail", "d", 0.2, 3.0, 0.2, 0.6, "m"),
         knob("T", "Air temperature", "T", 0, 40, 0.5, 20.0, "°C"),
         knob("dx", "Unknown distance (hidden)", "dx", 0.2, 3.0, 0.001, 0.737, "m", hidden=True)],
        [inst("te", "readout", "Echo time", "te_ms", unit="ms", digits=3),
         inst("c", "readout", "Speed of sound at this temperature", "c", unit="m/s", digits=1),
         inst("gr", "graph", "Echo time against distance", "te_ms", x="knob:d", xlabel="d (m)", dots=True)],
        "A transmitter sends a burst of 40 kHz sound; the receiver's comparator fires on the first echo. The echo "
        "time is te = 2 d / c + t0, where c = 331.3 sqrt(1 + T/273.15) m/s is the speed of sound in air at T degC "
        "and t0 is a fixed delay inside the electronics. Plotting te against d gives a straight line of slope 2/c and "
        "intercept t0, so the line calibrates the instrument for temperature and delay at once; an unknown distance is "
        "then d = (te - t0)/slope.",
        ["Read the air temperature on the thermometer and note it.",
         "Place the target at the first mark on the rail, trigger the burst and record the echo time.",
         "Move the target through at least six distances and record the echo time each time.",
         "Plot echo time against distance; find the slope and the intercept.",
         "Put the target at the unknown position and find its distance from your line."],
        [_q("What does the intercept of the line represent?",
            ["The fixed delay inside the electronics", "The speed of sound", "The air temperature"], 0,
            "At d = 0 the echo time is the delay t0."),
         _q("On a hotter day the same distance gives",
            ["A shorter echo time, because sound travels faster", "A longer echo time", "The same echo time"], 0,
            "c rises with temperature.")],
        [DU, {"title": "Speed of sound in air c = 331.3 sqrt(1 + T/273.15) m/s (ideal-gas relation, textbook)"},
         {"title": "Electronics delay 180 microseconds, 8-cycle burst and 20 % comparator level are illustrative",
          "note": "Unsourced / illustrative lab settings"}],
        {"params": {"d": 0.5}, "reading": "d_est", "textbook": "sn_ultra_d", "tol": 0.01})


# ====================================================================================== temperature sensors
def tsens() -> dict:
    return _mk(
        "sn-temp-sensor", "sn-sensor-bench", "Temperature sensor calibration: AD590 against a reference",
        "Calibrate a temperature sensor in a stirred bath against a reference thermometer, find its sensitivity from "
        "the line, and measure an unknown bath temperature with it.",
        "sn_tsens", {"dev": 0.0, "T": 25.0, "ge": 0.003, "off": 0.4, "R0": 100.0, "Tu": 47.3},
        [knob("T", "Bath temperature (reference thermometer)", "T", 20, 80, 5, 25.0, "°C"),
         knob("Tu", "Unknown bath temperature (hidden)", "Tu", 22, 78, 0.1, 47.3, "°C", hidden=True)],
        [inst("r", "readout", "Sensor reading", "reading", digits=3),
         inst("gr", "graph", "Reading against bath temperature", "reading", x="knob:T", xlabel="T (°C)", dots=True)],
        "A temperature sensor turns temperature into an electrical quantity. The AD590 is a two-terminal current "
        "source that passes 1 microampere per kelvin, so I = (T + 273.15) uA. Comparing it with a reference "
        "thermometer in a stirred bath gives a calibration line: its slope is the sensitivity and its intercept the "
        "offset. Once calibrated, the sensor reading gives the temperature of an unknown bath. A real specimen differs "
        "from the nominal slope by a small gain error, which only a calibration reveals.",
        ["Stir the bath and wait until the reference thermometer is steady before each reading.",
         "Set the bath to the lowest temperature and record the reference and the sensor reading.",
         "Raise the temperature in steps of 5 K and record both each time, stirring throughout.",
         "Plot the reading against the reference temperature and find the slope and intercept.",
         "Put the sensor in the unknown bath and find its temperature from your line."],
        [_q("Why is the bath stirred?",
            ["So the sensor and the thermometer are at the same temperature", "To heat it faster", "To cool the sensor"], 0,
            "Without stirring the two can sit in different layers."),
         _q("What does a calibration line tell you that the datasheet does not?",
            ["The slope and offset of this particular specimen", "The sensor's name", "The bath volume"], 0,
            "Every specimen differs a little from the nominal values.")],
        [DU, {"title": "Analog Devices AD590 datasheet: current output 1 uA per kelvin"},
         {"title": "Specimen gain error 0.3 % and 0.4 degC offset are simulation settings inside the datasheet limits",
          "note": "Unsourced / illustrative lab settings"}],
        {"params": {"T": 50.0}, "reading": "slope", "textbook": "sn_tsens_slope", "tol": 0.01})


# ====================================================================================== meter loading
def mload() -> dict:
    return _mk(
        "sn-meter-loading", "sn-sensor-bench", "Loading effect of a multimeter and its input resistance",
        "Measure a divider's output with a meter across a range of source resistances, see the loading error grow "
        "with resistance, and find the meter's input resistance.",
        "sn_mload", {"Vs": 5.0, "R1": 1.0e6, "R2": 1.0e6, "Rm": 1.0e7},
        [knob("R1", "Series resistance R1 (= R2)", "R1", 1000, 10000000, 1000, 1000000, "Ω"),
         knob("Rm", "Meter input resistance (hidden)", "Rm", 1e5, 2e7, 1000, 1e7, "Ω", hidden=True)],
        [inst("vm", "readout", "Meter reading", "Vm", unit="V", digits=4),
         inst("vt", "readout", "True divider output", "Vt", unit="V", digits=4),
         inst("er", "readout", "Loading error", "err_pct", unit="%", digits=2)],
        "A voltmeter is not an ideal instrument: it draws current through its input resistance R_m. Across a divider "
        "of two equal resistors R, the meter puts R_m in parallel with the lower one and the reading falls below the "
        "true value by the factor R_m/(R_m + R_th), where R_th = R1 R2/(R1 + R2) is the resistance the meter sees "
        "looking back into the source. Across a low resistance the error is negligible; across a high one it is "
        "large. Plotting V_true/V_meter - 1 against R_th gives a line of slope 1/R_m.",
        ["Set R1 = R2 = 1 kilohm and read the divider with the meter; compute the true value from the supply and R.",
         "Repeat with R = 10 k, 100 k, 1 M and 10 M, recording the meter reading each time.",
         "For each setting compute V_true/V_meter - 1 and the Thevenin resistance R/2.",
         "Plot V_true/V_meter - 1 against R_th; the slope is 1/R_m. Find the meter's input resistance."],
        [_q("Across which kind of circuit does a voltmeter read best?",
            ["A low-resistance one", "A high-resistance one", "It makes no difference"], 0,
            "The meter's current then causes only a small drop."),
         _q("A better meter has",
            ["A higher input resistance", "A lower input resistance", "A larger display"], 0,
            "Then it draws less current.")],
        [DU, HOROWITZ, {"title": "Typical input resistances: 10 megohm for a handheld digital meter, 1 megohm for a scope "
                                 "input, 20 kilohm per volt for an analogue meter", "note": "Typical class values, not one model"}],
        {"params": {}, "reading": "err", "textbook": "sn_mload_err", "tol": 0.01})


# ====================================================================================== meter bandwidth
def mbw() -> dict:
    return _mk(
        "sn-meter-bandwidth", "sn-sensor-bench", "Limits of a multimeter at high frequency: AC volts",
        "Feed a constant amplitude at rising frequency to an AC voltmeter, plot the reading against frequency, and "
        "find the frequency at which it has fallen by 3 dB.",
        "sn_mbw", {"f": 1000.0, "V": 1.0, "fc": 20000.0},
        [knob("f", "Generator frequency", "f", 100, 1000000, 100, 1000, "Hz")],
        [inst("r", "readout", "Meter reading", "reading", unit="V", digits=4),
         inst("e", "readout", "Error", "err_pct", unit="%", digits=1)],
        "An AC meter's rectifier and amplifier have a limited bandwidth: well above their rated range the reading "
        "falls below the true value. A single-pole roll-off reads V/sqrt(1 + (f/f_c)^2), which is 70.7 % of the true "
        "value, 3 dB down, at f = f_c. Keeping the generator amplitude constant and plotting the reading against "
        "log frequency finds the meter's useful limit. The settings of a real meter are in its manual; the value "
        "here is illustrative.",
        ["Set the generator to 1 V rms at 100 Hz and check the meter reads 1 V.",
         "Raise the frequency in steps (1, 2, 5 times each decade) up to 1 MHz, checking the generator amplitude each time.",
         "Record the meter reading at each frequency.",
         "Plot the reading against log frequency and find where it has fallen to 0.707 of its low-frequency value."],
        [_q("Why is the generator amplitude checked at every frequency?",
            ["A generator's own output can change with frequency", "To protect the meter", "To save time"], 0,
            "Otherwise a change in the reading could be the generator's, not the meter's."),
         _q("A reading 3 dB below the true value is",
            ["0.707 of the true value", "half of it", "0.9 of it"], 0, "20 log10(0.707) = -3 dB.")],
        [DU, {"title": "Meter bandwidth figure (20 kHz) is illustrative: every meter's manual states its own AC bandwidth",
              "note": "Unsourced / illustrative lab setting"}],
        {"params": {}, "reading": "f3", "textbook": "sn_mbw_f3", "tol": 0.01}, two=False)


# ====================================================================================== photodiode
def photo() -> dict:
    return _mk(
        "sn-photodiode", "sn-sensor-bench", "Photodiode: photocurrent against light intensity",
        "Move a red LED away from a photodiode, find the photocurrent at each irradiance, and find the diode's "
        "responsivity in amperes per watt from the line.",
        "sn_photo", {"d": 0.10, "Ie": 0.13, "lam": 660.0e-9, "eta": 0.8, "A": 7.5e-6, "Id": 2.0e-9},
        [knob("d", "LED distance from the photodiode", "d", 0.05, 0.30, 0.01, 0.10, "m")],
        [inst("i", "readout", "Photocurrent", "I_uA", unit="µA", digits=3),
         inst("e", "readout", "Irradiance on the chip", "E", unit="W/m²", digits=2),
         inst("gr", "graph", "Photocurrent against distance", "I_uA", x="knob:d", xlabel="d (m)", dots=True)],
        "A reverse-biased photodiode passes a current proportional to the light power on it: I = R P + I_dark, with "
        "the responsivity R = eta lambda q/(h c) amperes per watt for a quantum efficiency eta. A small LED of radiant "
        "intensity I_e gives an irradiance E = I_e/d^2 at distance d, so the power on a chip of area A is "
        "P = I_e A/d^2. Plotting the current against that power gives a straight line of slope R; the dark current "
        "is the intercept.",
        ["Darken the room and read the dark current with the LED off.",
         "Switch the LED on at 10 cm and read the photocurrent.",
         "Move it out in steps to 30 cm, recording the photocurrent each time.",
         "For each distance compute the power on the chip from the LED's radiant intensity and the chip area.",
         "Plot the current against that power; the slope is the responsivity."],
        [_q("Why does the photocurrent fall as 1/d^2?",
            ["The light spreads over a sphere whose area grows as d^2", "The LED dims", "The diode saturates"], 0,
            "Irradiance from a point source is I_e/d^2."),
         _q("Why is stray room light a problem?",
            ["It adds to the photocurrent and moves the intercept", "It heats the LED", "It lowers the responsivity"], 0,
            "The diode cannot tell it from the LED's light.")],
        [DU, {"title": "Responsivity R = eta lambda q / (h c); q, h, c exact SI values"},
         {"title": "Quantum efficiency 0.8, chip area 7.5 mm^2, radiant intensity 130 mW/sr and dark current 2 nA are "
                   "illustrative values typical of a small silicon photodiode and a red LED",
          "note": "Unsourced / illustrative lab settings"}],
        {"params": {}, "reading": "R", "textbook": "sn_photo_r", "tol": 0.01})


# ====================================================================================== rotary pump
def vac() -> dict:
    return _mk(
        "sn-rotary-vacuum", "sn-sensor-bench", "Rotary pump: pump-down and the pumping speed",
        "Pump a chamber down with a rotary pump, record the Pirani gauge against time, and find the pumping speed "
        "from the exponential fall of pressure above the ultimate value.",
        "sn_vac", {"t": 20.0, "P0": 1013.25, "Pu": 0.05, "Vch": 0.02, "S": 0.00167},
        [knob("t", "Time since the pump was started", "t", 0, 90, 5, 20, "s")],
        [inst("p", "readout", "Gauge pressure", "P", unit="mbar", digits=3),
         inst("gr", "graph", "Pressure against time", "P", x="knob:t", xlabel="t (s)", dots=True)],
        "A pump of speed S removes gas from a chamber of volume V: dP/dt = -(S/V)(P - P_u), where P_u is the pressure "
        "at which the pump can do no more (its ultimate pressure). The solution is P - P_u = (P_0 - P_u) exp(-S t/V), "
        "so a graph of ln(P - P_u) against time is a straight line of slope -S/V. The pumping speed follows from the "
        "slope and the chamber volume. A Pirani gauge reads from about 1 millibar down to 0.001 millibar.",
        ["Close the chamber, switch on the rotary pump and start the clock.",
         "Read the Pirani gauge every 5 seconds and record the pressure.",
         "Continue until the reading stops falling: that is the ultimate pressure.",
         "Plot ln(P - P_u) against time; the slope is -S/V. Find S from the chamber volume of 20 litres."],
        [_q("Why does the pressure stop falling?",
            ["Leaks and outgassing balance what the pump removes", "The pump switches off", "The gauge saturates"], 0,
            "That balance is the ultimate pressure."),
         _q("A larger chamber at the same pump speed pumps down",
            ["More slowly", "More quickly", "At the same rate"], 0, "The time constant V/S grows with V.")],
        [DU, {"title": "Pump-down relation dP/dt = -(S/V)(P - P_u) (vacuum technology textbooks)"},
         {"title": "Pump speed 100 litres/minute, chamber 20 litres, ultimate pressure 0.05 mbar are illustrative",
          "note": "Unsourced / illustrative lab settings; the speed of a real pump falls at low pressure"}],
        {"params": {"t": 20.0}, "reading": "P", "textbook": "sn_vac_p", "tol": 0.01}, two=False)


# ====================================================================================== scope bench
def _sk(id, title, aim, kernel, params, knobs, insts, theory, steps, questions, sources, check, chapter=CH_SENS, safety=None):
    return _mk(id, "sn-scope-bench", title, aim, kernel, params, knobs, insts, theory, steps, questions, sources, check,
               chapter=chapter, two=False,
               safety=safety or "Low voltages only. Keep the generator output within the circuit's rating and connect the scope "
                                "ground lead to the circuit's common point.",
               extra=[B("scope", "box", name="Oscilloscope", info="Two channels; the screen shows the circuit's signals.",
                        size=[0.32, 0.22, 0.26], pos=[0.3, 0.11, -0.2], color="#cdc9bf")],
               tour=[{"say": "The circuit is on the breadboard; the function generator is on the left and the "
                             "oscilloscope on the right."}])


def cro() -> dict:
    return _sk(
        "sn-cro-measure", "Oscilloscope: voltage, period, frequency and phase of an RC network",
        "Use the oscilloscope to read the voltage, period, frequency and phase of a signal through an RC low-pass "
        "network, and find the unknown capacitor from the phase.",
        "sn_scope", {"f": 1000.0, "A": 2.0, "Vdc": 0.5, "R": 10000.0, "C": 1.0e-8, "n": 4.0},
        [knob("f", "Generator frequency", "f", 200, 20000, 100, 1000, "Hz"),
         knob("C", "Unknown capacitor (hidden)", "C", 1e-9, 1e-7, 1e-10, 1e-8, "F", hidden=True)],
        [inst("t", "readout", "Period", "T_ms", unit="ms", digits=3),
         inst("v1", "readout", "Channel 1 peak-to-peak", "Vpp1", unit="V", digits=3),
         inst("ph", "readout", "Phase lag of channel 2", "phase", unit="°", digits=2)],
        "An oscilloscope draws voltage against time. A vertical scale of volts per division gives the peak-to-peak "
        "voltage and the DC level; a horizontal scale of seconds per division gives the period T, and the frequency "
        "is 1/T. With two channels the delay between the same point on each wave, as a fraction of the period, is "
        "the phase difference. After an RC low-pass the amplitude falls to 1/sqrt(1 + x^2) and the output lags by "
        "phi = arctan(x), where x = 2 pi f R C. So tan(phi) divided by 2 pi f R gives the capacitor.",
        ["Connect the generator to the RC network and the scope: channel 1 on the input, channel 2 on the output.",
         "Set the generator to a frequency and adjust the time base until about four periods fill the screen.",
         "Read the peak-to-peak voltage and the DC level on channel 1, and the period from successive crossings.",
         "Read the delay of channel 2 behind channel 1 and convert it into a phase angle.",
         "Repeat at several frequencies and find the capacitor from tan(phi) / (2 pi f R)."],
        [_q("How is the frequency found from the screen?",
            ["Take 1/T, where T is the period read from the time base", "Count the volts per division", "Measure the DC level"], 0,
            "f = 1/T."),
         _q("A delay of one tenth of a period is a phase of",
            ["36 degrees", "10 degrees", "90 degrees"], 0, "One period is 360 degrees.")],
        [DU, HOROWITZ_SCOPE, IEC60063],
        {"params": {"f": 1000.0}, "reading": "phase", "textbook": "sn_scope_phase", "tol": 0.01})


def pulse() -> dict:
    return _sk(
        "sn-cro-pulse", "Oscilloscope: rise, fall and delay times of a pulse through an RC network",
        "Pass a square pulse through an RC network, measure the 10-90 % rise and fall times and the delay on the "
        "scope, and find the unknown capacitor from the rise time.",
        "sn_pulse", {"R": 10000.0, "C": 1.0e-9, "tg": 5.0e-9, "BW": 1.0e8, "Vh": 5.0},
        [knob("R", "Decade resistance box", "R", 1000, 22000, 1000, 10000, "Ω"),
         knob("C", "Unknown capacitor (hidden)", "C", 1e-10, 1e-8, 1e-10, 1e-9, "F", hidden=True)],
        [inst("tr", "readout", "Rise time (10-90 %)", "tr_us", unit="µs", digits=2),
         inst("tf", "readout", "Fall time (90-10 %)", "tf_us", unit="µs", digits=2),
         inst("td", "readout", "Delay (50 % to 50 %)", "td_us", unit="µs", digits=2)],
        "The rise time of a pulse is the time it takes to go from 10 % to 90 % of its final value; the fall time is the "
        "reverse, and the delay is the time between the 50 % points of the input and the output. For a pulse "
        "through a resistor R and capacitor C to ground the output charges exponentially: t_r = ln 9 R C = 2.197 R C, "
        "t_f is the same, and the delay is ln 2 R C = 0.693 R C. A scope has its own rise time 0.35/BW, which adds in "
        "quadrature and limits the shortest edge it can show; for a 100 MHz scope that is 3.5 ns.",
        ["Connect the generator to the resistor box and capacitor, with channel 1 on the generator and channel 2 on the capacitor.",
         "Set the resistance and the time base so one edge fills most of the screen.",
         "Read the rise time between 10 % and 90 % of the final level, then the fall time of the trailing edge.",
         "Read the delay between the 50 % points of the two channels.",
         "Repeat for several resistances; find the capacitor from t_r / (2.197 R)."],
        [_q("What fraction of RC is the 10-90 % rise time?", ["2.197", "0.693", "1"], 0, "ln 9 = 2.197."),
         _q("Which limits the fastest edge you can measure?",
            ["The scope's own rise time, 0.35 divided by its bandwidth", "The screen size", "The probe cable colour"], 0,
            "Edges faster than the scope's own cannot be shown.")],
        [DU, HOROWITZ_SCOPE, IEC60063, {"title": "Generator edge 5 ns and scope bandwidth 100 MHz are illustrative",
                                        "note": "Unsourced / illustrative lab settings"}],
        {"params": {}, "reading": "tr", "textbook": "sn_pulse_tr", "tol": 0.01})


def shape() -> dict:
    return _sk(
        "sn-waveshaper", "Diode clippers and clampers: the diode's forward drop",
        "Build diode clipper and clamper circuits, read the clipping and clamping levels on the scope, and find the "
        "diode's forward drop from them.",
        "sn_shape", {"mode": 2.0, "Vp": 5.0, "f": 1000.0, "R": 10000.0, "C": 1.0e-6, "RL": 10000000.0, "Vb": 0.0,
                     "Vf": 0.65, "rd": 5.0},
        [knob("mode", "Circuit (0 +clip, 1 -clip, 2 +clamp, 3 -clamp)", "mode", 0, 3, 1, 2, ""),
         knob("Vb", "Bias voltage", "Vb", -2, 2, 0.5, 0.0, "V"),
         knob("Vf", "Diode (hidden)", "Vf", 0.1, 0.8, 0.01, 0.65, "V", hidden=True)],
        [inst("hi", "readout", "Output maximum", "Vmax", unit="V", digits=3),
         inst("lo", "readout", "Output minimum", "Vmin", unit="V", digits=3),
         inst("pp", "readout", "Output peak-to-peak", "Vpp", unit="V", digits=3)],
        "A clipper removes the part of a wave above or below a level. A diode that conducts only when forward biased by "
        "more than its forward drop V_f cuts the wave at V_b + V_f (positive clipper) or V_b - V_f (negative clipper), "
        "where V_b is the bias in series with it. A clamper adds a DC level to a wave without changing its shape: "
        "a capacitor in series charges through the diode on the peaks and holds the level, so the wave's negative "
        "peaks are pushed to V_b - V_f (positive clamper) or its positive peaks to V_b + V_f (negative clamper). "
        "Either circuit measures V_f from the level at which the wave stops.",
        ["Connect the 5 V peak sine at 1 kHz to the positive clipper with no bias; read the output maximum on the scope.",
         "Repeat with the bias at 1 V and note that the clipping level moves with it.",
         "Replace the clipper by the clamper; read the output minimum.",
         "Check that the output peak-to-peak equals the input peak-to-peak: a clamper only shifts the wave.",
         "From each clipping or clamping level subtract the bias to find the diode's forward drop."],
        [_q("What is the difference between a clipper and a clamper?",
            ["A clipper cuts part of the wave off; a clamper shifts the whole wave", "There is none", "A clamper amplifies"], 0,
            "The clamper keeps the shape and adds a DC level."),
         _q("A positive clamper with no bias pushes the output's negative peaks to",
            ["minus the diode's forward drop", "zero exactly", "plus the supply"], 0, "The diode conducts at V_b - V_f.")],
        [DU, SEDRA, {"title": "Forward drops (silicon about 0.65 V, germanium about 0.3 V) are typical textbook values",
                     "note": "Unsourced / illustrative: the drop of a real diode depends on its current"}],
        {"params": {}, "reading": "Vlvl", "textbook": "sn_shape_lvl", "tol": 0.01}, chapter=CH_SENS)


def t555() -> dict:
    return _sk(
        "sn-timer-555", "555 timer as an astable and a monostable multivibrator: an unknown capacitor",
        "Wire a 555 as an astable and as a monostable, read the frequency and the pulse width on the scope, and find "
        "the unknown timing capacitor from each.",
        "sn_mv", {"kind": 0.0, "R1": 1000.0, "R2": 10000.0, "C": 1.0e-7, "Vcc": 9.0},
        [knob("kind", "Mode: 0 astable, 1 monostable", "kind", 0, 1, 1, 0, ""),
         knob("R1", "Resistor R1", "R1", 1000, 100000, 1000, 1000, "Ω"),
         knob("R2", "Resistor R2", "R2", 1000, 100000, 1000, 10000, "Ω"),
         knob("C", "Unknown timing capacitor (hidden)", "C", 1e-8, 1e-5, 1e-9, 1e-7, "F", hidden=True)],
        [inst("f", "readout", "Frequency", "f", unit="Hz", digits=1),
         inst("w", "readout", "Pulse width", "width", unit="s", digits=5),
         inst("d", "readout", "Duty cycle", "duty", digits=3)],
        "The 555 has two comparators set at 2/3 and 1/3 of the supply and a flip-flop. As an astable the capacitor "
        "charges through R1 + R2 from 1/3 to 2/3 of V_cc and discharges through R2 back, so the output is high for "
        "0.693 (R1 + R2) C and low for 0.693 R2 C, giving f = 1.44 / ((R1 + 2 R2) C) and a duty cycle (R1 + R2)/(R1 + 2 R2). "
        "As a monostable a falling trigger starts the output and the capacitor charging through R1 ends it after "
        "T = 1.1 R1 C. Either way the frequency or width measures the unknown capacitor.",
        ["Set the 555 as an astable with R1 = 1 k and R2 = 10 k; read the output on the scope.",
         "Measure the period and the high and low times; compute the frequency and the duty cycle.",
         "Find the capacitor from f = 1.44 / ((R1 + 2 R2) C).",
         "Rewire as a monostable; apply a trigger pulse and measure the output pulse width.",
         "Find the capacitor again from T = 1.1 R1 C and compare."],
        [_q("In the astable the duty cycle is always",
            ["Above 50 %", "Below 50 %", "Exactly 50 %"], 0, "The capacitor charges through R1 + R2 but discharges through R2 only."),
         _q("In the monostable, a second trigger during the pulse",
            ["Is ignored", "Doubles the width", "Stops the pulse"], 0, "The flip-flop is already set.")],
        [DU, {"title": "Texas Instruments NE555 / LM555 datasheet: threshold at 2/3 V_cc, trigger at 1/3 V_cc, "
                       "astable and monostable timing"}, IEC60063],
        {"params": {}, "reading": "main", "textbook": "sn_mv_main", "tol": 0.01}, chapter=CH_ANA)


def ujt() -> dict:
    return _sk(
        "sn-ujt-oscillator", "UJT relaxation oscillator: the intrinsic stand-off ratio",
        "Build a UJT relaxation oscillator, read the sawtooth's peak and valley and its period on the scope, and "
        "find the unknown intrinsic stand-off ratio from the peak voltage.",
        "sn_mv", {"kind": 2.0, "R1": 22000.0, "R2": 0.0, "C": 4.7e-8, "Vcc": 9.0, "eta": 0.65, "Vd": 0.5, "Vv": 1.0},
        [knob("R1", "Charging resistor R", "R1", 10000, 100000, 1000, 22000, "Ω"),
         knob("eta", "UJT (stand-off ratio hidden)", "eta", 0.4, 0.85, 0.01, 0.65, "", hidden=True)],
        [inst("f", "readout", "Oscillation frequency", "f", unit="Hz", digits=1)],
        "A unijunction transistor fires when its emitter voltage reaches V_p = eta V_bb + V_D, where eta is the intrinsic "
        "stand-off ratio and V_D the emitter diode drop (about 0.5 V). The capacitor charges through R toward V_bb; "
        "when V_E reaches V_p the UJT conducts and discharges it to a valley voltage V_v, and the cycle repeats. "
        "The period is T = R C ln((V_bb - V_v) / (V_bb - V_p)), close to R C ln(1/(1 - eta)) when V_v and V_D are small. "
        "The peak of the sawtooth gives eta directly: eta = (V_p - V_D)/V_bb.",
        ["Connect the UJT with R, C and the supply; put channel 1 on the capacitor.",
         "Read the peak and valley of the sawtooth and its period on the scope.",
         "Find the stand-off ratio from the peak: eta = (V_p - V_D)/V_bb, with V_D = 0.5 V.",
         "Change R and check that the period changes in proportion.",
         "Compare the measured period with R C ln((V_bb - V_v)/(V_bb - V_p))."],
        [_q("What does the UJT do when the emitter reaches V_p?",
            ["It conducts and discharges the capacitor", "It switches off", "It doubles the supply"], 0, "Its emitter-base 1 junction turns on."),
         _q("Doubling R changes the frequency to",
            ["Half", "Double", "The same"], 0, "T is proportional to R C.")],
        [DU, SEDRA, {"title": "UJT behaviour: V_p = eta V_BB + V_D (Millman and Halkias, Integrated Electronics)"},
         {"title": "V_D = 0.5 V and V_v = 1 V are illustrative; eta is chosen inside a typical datasheet range",
          "note": "Unsourced / illustrative lab settings"}],
        {"params": {}, "reading": "main", "textbook": "sn_mv_main", "tol": 0.01}, chapter=CH_ANA)


def ce() -> dict:
    return _sk(
        "sn-ce-amplifier", "Common-emitter amplifier: mid-band gain and frequency response",
        "Bias a transistor with a voltage divider, measure the gain of a common-emitter amplifier across the audio "
        "and radio bands, and find its mid-band gain and half-power frequencies.",
        "sn_ce", {"Vcc": 12.0, "R1": 47000.0, "R2": 10000.0, "Rc": 2200.0, "Re": 680.0, "RL": 10000.0, "Rs": 50.0,
                  "Cin": 1.0e-6, "CE": 220.0e-6, "Cout": 1.0e-6, "beta": 200.0, "Vbe": 0.65, "fT": 3.0e8,
                  "Cmu": 4.5e-12, "stages": 1.0, "f": 10000.0, "fmid": 10000.0},
        [knob("f", "Generator frequency", "f", 10, 10000000, 10, 10000, "Hz"),
         knob("RL", "Load resistor R_L", "RL", 1000, 100000, 1000, 10000, "Ω")],
        [inst("ic", "readout", "Collector current", "Ic_mA", unit="mA", digits=3),
         inst("vc", "readout", "Collector-emitter voltage", "Vce", unit="V", digits=2),
         inst("gm", "readout", "Transconductance", "gm_mS", unit="mS", digits=1)],
        "With a voltage divider R1, R2 and an emitter resistor R_E the collector current is I_C = (V_th - V_BE)/(R_th/beta + "
        "R_E(beta + 1)/beta) and hardly depends on beta. For a small signal the transistor has transconductance g_m = I_C/V_T "
        "(V_T = 25.9 mV) and the mid-band voltage gain is -g_m (R_C || R_L) times the input divider R_in/(R_s + R_in), "
        "with R_in = R1 || R2 || r_pi. The coupling and bypass capacitors set the lower half-power frequency; the "
        "transistor's capacitances, magnified by the Miller effect, set the upper one.",
        ["Check the bias: measure the collector current and collector-emitter voltage with no signal.",
         "Apply a 10 mV peak sine at 10 kHz and measure the output peak on channel 2.",
         "Take the gain at about ten frequencies from 10 Hz to 10 MHz, closer together near the roll-off.",
         "Plot gain in dB against log frequency and find the mid-band gain.",
         "Find the lower and upper frequencies at which the gain is 3 dB below the mid-band value."],
        [_q("Why does the output sit upside down relative to the input?",
            ["A common-emitter stage inverts the signal", "The scope is set wrongly", "The capacitor reverses it"], 0,
            "The gain is -g_m R_C."),
         _q("What sets the lower half-power frequency?",
            ["The coupling and emitter bypass capacitors", "The transistor's capacitances", "The supply voltage"], 0,
            "They form high-pass networks with the resistances around them.")],
        [DU, SEDRA, IEC60063,
         {"title": "ON Semiconductor BC546/BC547/BC548 datasheet: hFE group B 200-450 at I_C = 2 mA; f_T is typically 300 MHz",
          "note": "C_mu = 4.5 pF and V_BE = 0.65 V are typical, unsourced lab settings"}],
        {"params": {}, "reading": "Amid", "textbook": "sn_ce_amid", "tol": 0.01}, chapter=CH_ANA)


def am() -> dict:
    return _sk(
        "sn-am-modulation", "Amplitude modulation: modulation index and the modulator's sensitivity",
        "Vary the message amplitude at an amplitude modulator, read the largest and smallest envelope on the scope, "
        "find the modulation index each time, and find the modulator's sensitivity.",
        "sn_am", {"Vc": 2.0, "Vm": 0.5, "fc": 20000.0, "fm": 500.0, "ka": 0.4},
        [knob("Vm", "Message amplitude", "Vm", 0.2, 2.4, 0.2, 0.5, "V"),
         knob("ka", "Modulator (sensitivity hidden)", "ka", 0.1, 0.8, 0.01, 0.4, "1/V", hidden=True)],
        [inst("m", "readout", "Modulation index", "m", digits=3),
         inst("mx", "readout", "Envelope maximum", "Vmax", unit="V", digits=3),
         inst("mn", "readout", "Envelope minimum", "Vmin", unit="V", digits=3)],
        "In amplitude modulation the carrier's amplitude follows the message: s(t) = V_c (1 + m sin w_m t) sin w_c t. The "
        "modulation index m = V_m' / V_c is read from the envelope: m = (V_max - V_min)/(V_max + V_min), where V_max and "
        "V_min are the largest and smallest carrier peaks. A modulator of sensitivity k_a gives m = k_a V_m, so m grows in "
        "proportion to the message. Above m = 1 the envelope no longer follows the message and the signal is over-modulated.",
        ["Connect the message (500 Hz) and the 20 kHz carrier to the modulator and look at the output on the scope.",
         "Set a message amplitude, read V_max and V_min of the envelope and compute m.",
         "Raise the message in steps and record V_max, V_min and m each time.",
         "Plot m against the message amplitude; the slope is the modulator's sensitivity k_a.",
         "Go above m = 1 once and see the envelope distort; then return."],
        [_q("What is the modulation index when V_max = 3 V and V_min = 1 V?", ["0.5", "2", "0.33"], 0, "(3 - 1)/(3 + 1) = 0.5."),
         _q("Why must m stay below 1?",
            ["Above 1 the envelope no longer follows the message", "The carrier would vanish", "The scope would fail"], 0,
            "The carrier amplitude would go negative, which a plain envelope detector cannot undo.")],
        [DU, {"title": "Amplitude modulation: Kennedy and Davis, Electronic Communication Systems; Tomasi, Electronic "
                       "Communications Systems"},
         {"title": "Carrier 20 kHz, message 500 Hz and k_a = 0.4 per volt are illustrative lab settings",
          "note": "Unsourced / illustrative"}],
        {"params": {}, "reading": "m", "textbook": "sn_am_m", "tol": 0.01}, chapter=CH_COM)


def fm() -> dict:
    return _sk(
        "sn-fm-modulation", "Frequency modulation: frequency deviation and the modulator's sensitivity",
        "Frequency-modulate a carrier, find the deviation from the zero-crossing intervals on the scope, and find "
        "the modulator's sensitivity in hertz per volt; recover the message with a frequency discriminator.",
        "sn_fm", {"Vc": 2.0, "Vm": 1.0, "fc": 20000.0, "fm": 250.0, "kf": 1500.0, "kd": 1000.0},
        [knob("Vm", "Message amplitude", "Vm", 0.2, 2.4, 0.2, 1.0, "V"),
         knob("kf", "Modulator (sensitivity hidden)", "kf", 500, 3000, 10, 1500, "Hz/V", hidden=True)],
        [inst("df", "readout", "Frequency deviation", "df_kHz", unit="kHz", digits=3),
         inst("b", "readout", "Modulation index beta", "beta", digits=2),
         inst("vr", "readout", "Recovered message amplitude", "Vrec", unit="V", digits=3)],
        "In frequency modulation the carrier's frequency follows the message: f(t) = f_c + k_f V_m sin w_m t, so the "
        "frequency swings by the deviation delta f = k_f V_m about f_c, independent of the message frequency. The "
        "modulation index is beta = delta f / f_m, and Carson's rule gives the bandwidth 2(delta f + f_m). On the scope the "
        "instantaneous frequency is 1/(interval between successive zero crossings); half the spread of those values "
        "is the deviation. A discriminator that converts frequency into voltage recovers the message.",
        ["Connect the 250 Hz message to the FM generator and look at the output on the scope.",
         "Measure the interval between successive rising zero crossings across a whole message cycle.",
         "Compute the frequency from each interval; the deviation is half the largest minus the smallest.",
         "Repeat for several message amplitudes and plot the deviation against the message amplitude.",
         "The slope is the sensitivity k_f. Read the discriminator output as a check."],
        [_q("What does the deviation depend on?",
            ["The message amplitude, not its frequency", "The message frequency", "The carrier amplitude"], 0,
            "delta f = k_f V_m."),
         _q("Doubling the message amplitude doubles",
            ["The frequency deviation", "The carrier amplitude", "The carrier frequency"], 0, "The deviation is proportional to V_m.")],
        [DU, {"title": "Frequency modulation and Carson's rule: Kennedy and Davis, Electronic Communication Systems"},
         {"title": "Carrier 20 kHz, message 250 Hz and k_f = 1.5 kHz/V are illustrative lab settings",
          "note": "Unsourced / illustrative"}],
        {"params": {}, "reading": "df", "textbook": "sn_fm_df", "tol": 0.01}, chapter=CH_COM)


# ====================================================================================== oscillators on the existing signal bench
def _eb() -> list[dict]:
    return [board(1.0, 0.6),
            B("bb", "box", name="Solderless breadboard", info="The circuit is built on it.", size=[0.42, 0.018, 0.26],
              pos=[-0.1, 0.009, -0.16], color="white"),
            B("gen", "box", name="Dual supply", info="Dual regulated supply.", size=[0.26, 0.1, 0.22],
              pos=[-0.62, 0.05, -0.26], color="#cdc9bf"),
            B("scope", "box", name="Oscilloscope", info="Two-channel oscilloscope.", size=[0.32, 0.22, 0.26],
              pos=[0.38, 0.11, -0.26], color="#cdc9bf")]


OSC_STEPS = ["Check the component values and the polarity of the supply, then switch it on.",
             "Turn the gain up slowly from 1 until a steady sine wave appears on the scope: that is the minimum gain.",
             "Raise the gain a little more and measure the period on the scope from successive zero crossings.",
             "Repeat at a second gain; the frequency should not change with the gain.",
             "Compare the frequency with the formula and the minimum gain with the theory."]


def _osc(id, title, aim, kind, params, theory, questions, sources):
    base = {"kind": float(kind), "R": 10000.0, "C": 1.0e-8, "L": 1.0e-3, "C2": 1.0e-8, "L2": 1.0e-3, "M": 0.0, "A": 1.0,
            "Vsat": 12.0, "t": 0.0, "task": 0.0}
    base.update(params)
    return lab(
        id=id, rig="msc-signal-bench", title=title, group=GROUP, level=LEVEL, topic=CH_ANA, chapter=CH_ANA, aim=aim,
        kernel="msc_osc", params=base, autorun=True, camera={"pos": [-0.08, 0.62, 1.22], "look": [-0.08, 0.05, -0.2]},
        floor=-0.03, bodies=_eb(), knobs=[knob("A", "Amplifier gain", "A", 1, 60, 0.05, 1.0)],
        instruments=[inst("f", "readout", "Frequency of oscillation", "f_kHz", unit="kHz", digits=3),
                     inst("am", "readout", "Minimum gain needed", "amin", digits=2),
                     inst("vo", "readout", "Output amplitude", "vo", unit="V", digits=2)],
        steps=OSC_STEPS, theory=theory,
        safety="Low voltages only. Check the polarity of the supply before switching on: a reversed op-amp or transistor "
               "supply destroys the device. Never exceed the rated supply.",
        tour=[{"say": "The oscillator is built on the breadboard; the supply is on the left and the oscilloscope on the right."}],
        questions=questions, sources=sources, check={"reading": "f", "textbook": "msc_osc_f", "tol": 0.01})


def wien() -> dict:
    return _osc("sn-wien-oscillator", "Wien bridge oscillator with an op-amp: oscillation frequency",
                "Build a Wien-bridge oscillator, find the gain at which it starts, and measure its frequency.", 1,
                {"R": 10000.0, "C": 1.0e-8},
                "The Wien network has zero phase shift at one frequency, w = 1/RC for equal resistors and capacitors, where it "
                "passes one third of the signal. A non-inverting amplifier of gain 3 or a little more closes the loop and the "
                "circuit oscillates at f = 1/(2 pi R C). Below a gain of 3 nothing oscillates; well above, the output "
                "saturates and distorts, so a practical circuit limits the gain.",
                [_q("In a Wien-bridge oscillator the amplifier must have a gain of at least", ["3", "29", "1"], 0,
                    "The network passes one third of the signal at its zero-phase frequency."),
                 _q("If R is doubled the frequency", ["Halves", "Doubles", "Is unchanged"], 0, "f = 1/(2 pi R C).")],
                [DU, IEC60063, {"title": "J. Millman and C. C. Halkias, Integrated Electronics: Wien-bridge and phase-shift oscillators"}, SIM])


def rcphase() -> dict:
    return _osc("sn-phase-shift-oscillator", "RC phase-shift oscillator: oscillation frequency",
                "Build an RC phase-shift oscillator, find the gain at which it starts, and measure its frequency.", 0,
                {"R": 10000.0, "C": 1.0e-8},
                "Three identical RC sections in the feedback path of an inverting amplifier give a phase shift of 180 degrees at "
                "one frequency, f = 1/(2 pi sqrt(6) R C), where the network attenuates the signal by 29. The inverting amplifier "
                "supplies the other 180 degrees and must have a gain of at least 29, which a transistor stage with "
                "a current gain of a few hundred can supply. Below that gain nothing oscillates.",
                [_q("At the oscillation frequency the three-section network attenuates the signal by", ["29", "3", "10"], 0,
                    "beta = 1/29 where the phase is 180 degrees."),
                 _q("Why must the amplifier invert?", ["The network supplies only 180 degrees of the 360 needed", "To reduce noise", "To raise the gain"], 0,
                    "The loop phase must total 360 degrees.")],
                [DU, IEC60063, {"title": "J. Millman and C. C. Halkias, Integrated Electronics: RC phase-shift oscillator"}, SIM])


def colpitts() -> dict:
    return _osc("sn-colpitts-oscillator", "Colpitts oscillator: oscillation frequency",
                "Build a transistor Colpitts oscillator, find the minimum gain, and measure its frequency against the tank values.", 2,
                {"L": 0.01, "C": 1.0e-8, "C2": 4.7e-8},
                "A Colpitts oscillator uses an inductor L with two capacitors C1 and C2 in series as its tank, and the junction of "
                "the capacitors feeds a fraction of the output back. The loop phase is right at the resonance of L with the series "
                "capacitance, f = 1/(2 pi sqrt(L C1 C2/(C1 + C2))), and the amplifier gain must be at least C2/C1.",
                [_q("The capacitance that resonates with L in a Colpitts tank is", ["C1 C2 / (C1 + C2)", "C1 + C2", "C1 - C2"], 0,
                    "The two capacitors are in series around the loop."),
                 _q("Doubling both C1 and C2 changes the frequency by", ["1/sqrt 2", "2", "1/2"], 0, "f is proportional to 1/sqrt(C).")],
                [DU, IEC60063, {"title": "J. Millman and C. C. Halkias, Integrated Electronics: LC oscillators"}, SIM])


# ====================================================================================== op-amp circuits on the scope
LM741 = {"title": "Texas Instruments LM741 datasheet: slew rate 0.5 V/us, large-signal voltage gain 200 V/mV, output swing about "
                  "+-13 V into 10 kilohm (typical values)"}
OPA_BASE = {"kind": 0.0, "f": 1000.0, "Vp": 2.0, "R": 10000.0, "C": 1.0e-8, "Rf": 1.0e7, "Rs": 1000.0, "Vref": 1.0, "A0": 200000.0,
            "Vsat": 13.0, "SR": 500000.0, "n": 1.0}


def opa_cmp() -> dict:
    return _sk(
        "sn-opamp-comparator", "Op-amp comparator and zero-crossing detector: trip point and slew rate",
        "Use an op-amp with no feedback as a comparator, find the input at which its output switches for several "
        "reference voltages (zero gives a zero-crossing detector), and measure the slew rate of its output edge.",
        "sn_opa", dict(OPA_BASE, kind=0.0),
        [knob("Vref", "Reference voltage", "Vref", -1, 2, 0.5, 1.0, "V"), knob("Vp", "Input amplitude (peak)", "Vp", 2, 3, 1, 2.0, "V"),
         knob("SR", "Op-amp (slew rate hidden)", "SR", 100000, 2000000, 1000, 500000, "V/s", hidden=True)],
        [inst("tp", "readout", "Trip point", "trip", unit="V", digits=3), inst("sr", "readout", "Slew rate", "SR_us", unit="V/µs", digits=3)],
        "An op-amp with no feedback has a gain of a few hundred thousand, so its output sits at one supply rail or the other "
        "and swings across when the input passes the voltage on the other input. With a sine on one input and a reference "
        "V_ref on the other, the output is a square wave that switches when V_in = V_ref (to within microvolts); with "
        "V_ref = 0 the circuit is a zero-crossing detector. The swing is not instantaneous: the output stage can only slew "
        "at a fixed rate, 0.5 V per microsecond for the LM741, so each edge is a straight ramp. Extending the ramp back "
        "to the rail gives the instant the output started to move, which is where the input crossed the reference.",
        ["Connect the sine to the inverting input and set the reference with the trimmer; look at both channels.",
         "Set the reference to zero: the output switches at every zero crossing of the input.",
         "Raise the reference: the switching instants move to where the input crosses that level. Read the trip point from the cursors.",
         "Measure the output's 10 % and 90 % points on an edge and work out the slew rate.",
         "Repeat at several references and a second input amplitude."],
        [_q("Why does the output sit at one of two voltages?", ["The gain is so large that any small difference saturates it", "The supply switches", "The reference alternates"], 0,
            "With a gain of 200 000 a millivolt of difference is already far beyond the rails."),
         _q("What does a zero reference make the circuit?", ["A zero-crossing detector", "An integrator", "A rectifier"], 0,
            "The output changes state each time the input passes through zero.")],
        [DU, LM741, {"title": "Comparator and zero-crossing detector: Gayakwad, Op-Amps and Linear Integrated Circuits"}],
        {"params": {"Vref": 1.0}, "reading": "trip", "textbook": "sn_opa_main", "tol": 0.01}, chapter=CH_ANA)


def opa_int() -> dict:
    return _sk(
        "sn-opamp-integrator", "Op-amp integrator: ramp slope and an unknown capacitor",
        "Drive an op-amp integrator with a square wave, measure the slope of the ramp it makes at several frequencies "
        "and amplitudes, and find the unknown feedback capacitor from it.",
        "sn_opa", dict(OPA_BASE, kind=1.0, Vp=0.5, n=4.0),
        [knob("f", "Square-wave frequency", "f", 200, 2000, 100, 1000, "Hz"), knob("Vp", "Square-wave amplitude", "Vp", 0.1, 0.5, 0.05, 0.5, "V"),
         knob("C", "Unknown feedback capacitor (hidden)", "C", 1e-9, 1e-7, 1e-10, 1e-8, "F", hidden=True)],
        [inst("sl", "readout", "Ramp slope", "slope", k=0.001, unit="V/ms", digits=3)],
        "An op-amp with a capacitor C in its feedback and a resistor R at its input holds the inverting input at virtual "
        "earth, so the input current V_in/R all flows into C and the output is V_out = -(1/RC) times the integral of V_in. A square "
        "wave of constant V_in for half a cycle therefore gives a straight ramp of slope V_in/(RC); the next half-cycle "
        "ramps back and the output is a triangle. A large resistor R_f across C stops the output drifting into the rails, at "
        "the cost of a slight droop. The slope measures the capacitor: C = V_in/(R |slope|).",
        ["Connect the square wave to the integrator and look at both channels.",
         "Measure the slope of the output ramp over the first half-cycle with the cursors.",
         "Repeat at several amplitudes and frequencies, keeping the output below the rails.",
         "For each reading find C = V_in / (R |slope|) and average."],
        [_q("What does the integrator do to a square wave?", ["Turns it into a triangle", "Turns it into a sine", "Leaves it unchanged"], 0,
            "A constant input gives a constant slope."),
         _q("Doubling the input amplitude makes the ramp's slope", ["Double", "Half", "The same"], 0, "slope = V_in/(R C).")],
        [DU, LM741, {"title": "Op-amp integrator: Gayakwad, Op-Amps and Linear Integrated Circuits"}, IEC60063],
        {"params": {"Vp": 0.5, "f": 1000.0}, "reading": "slope", "textbook": "sn_opa_main", "tol": 0.01}, chapter=CH_ANA)


def opa_dif() -> dict:
    return _sk(
        "sn-opamp-differentiator", "Op-amp differentiator: output amplitude and an unknown capacitor",
        "Drive an op-amp differentiator with a triangle wave, measure the amplitude of the square wave it makes at several "
        "frequencies and amplitudes, and find the unknown input capacitor from it.",
        "sn_opa", dict(OPA_BASE, kind=2.0, Vp=1.0, n=4.0),
        [knob("f", "Triangle-wave frequency", "f", 200, 2000, 100, 1000, "Hz"), knob("Vp", "Triangle-wave peak", "Vp", 0.5, 2, 0.5, 1.0, "V"),
         knob("C", "Unknown input capacitor (hidden)", "C", 1e-9, 1e-7, 1e-10, 1e-8, "F", hidden=True)],
        [inst("am", "readout", "Output amplitude", "amp", unit="V", digits=3)],
        "In a differentiator the capacitor C is at the input and the resistor R in the feedback, so the output is "
        "V_out = -R C dV_in/dt. A triangle wave of peak V and frequency f has a constant slope of 4 V f, so the output is a square wave "
        "of amplitude R C 4 V f, which changes sign with the slope. A small resistor in series with the capacitor limits the "
        "high-frequency gain so that the circuit is stable. The amplitude measures the capacitor: C = A/(4 V f R).",
        ["Connect the triangle wave to the differentiator and look at both channels.",
         "Measure the amplitude of the square wave output with the cursors.",
         "Repeat at several frequencies and amplitudes, keeping the output below the rails.",
         "For each reading find C = A / (4 V f R) and average."],
        [_q("What does the differentiator do to a triangle wave?", ["Turns it into a square wave", "Turns it into a sine", "Leaves it unchanged"], 0,
            "A triangle has a constant slope on each side."),
         _q("Doubling the frequency makes the output amplitude", ["Double", "Half", "The same"], 0, "The slope 4 V f doubles.")],
        [DU, LM741, {"title": "Op-amp differentiator: Gayakwad, Op-Amps and Linear Integrated Circuits"}, IEC60063],
        {"params": {}, "reading": "amp", "textbook": "sn_opa_main", "tol": 0.01}, chapter=CH_ANA)


BUILDERS = (lvdt, strain, capl, ultra, tsens, mload, mbw, photo, vac, cro, pulse, shape, t555, ujt, ce, am, fm,
            wien, rcphase, colpitts, opa_cmp, opa_int, opa_dif)
