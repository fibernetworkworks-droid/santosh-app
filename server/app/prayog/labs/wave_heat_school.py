"""Prayogshala lab pack: the school (Class 6-10) measurement, sound and heat set-ups.

Three rigs serve them all (`app/static/prayog/exp/`):
    school-measuring-bench   length by hand span / cubit / foot step, by a metre scale, and a curved line by thread
    school-heat-bench        the clinical and laboratory thermometers; melting ice and boiling water
    school-conduction-bench  a metal rod with wax-stuck pins; spoons of different materials in hot water
Physics: the `wave_heat_school` kernel pack (never catalog.py / kernels.py). Every lab carries its own NCERT
check (the kernel's reading against the textbook formula, within 1 %). English only.
"""
from __future__ import annotations

from ..catalog import B, col, inst, knob, lab

SIM = {"title": "Hoola Prayogshala kernel", "note": "readings come from the simulation code; checked against the textbook formula in Hoola's tests"}
S6 = {"title": "Science, Textbook for Class VI, NCERT - Motion and Measurement of Distances"}
S6M = {"title": "Curiosity, Science Textbook for Class VI, NCERT - Measurement of Length and Motion"}
S6T = {"title": "Curiosity, Science Textbook for Class VI, NCERT - Temperature and its Measurement"}
S7 = {"title": "Science, Textbook for Class VII, NCERT - Heat"}
S7C = {"title": "Curiosity, Science Textbook for Class VII, NCERT - Heat Transfer in Nature"}
L9 = {"title": "Laboratory Manual Science, Class IX, NCERT - melting point of ice and boiling point of water"}
CRC = {"title": "CRC Handbook of Chemistry and Physics, thermal conductivity and thermal diffusivity of the elements"}


# =============================================================================================== MEASUREMENT
def _bench_bodies(obj_name: str, obj_info: str, extra: list[dict] | None = None) -> list[dict]:
    """The measuring bench as data (the realistic rig is the studio module; this keeps the lab openable)."""
    out = [
        B("board", "box", name="Working board", size=[1.2, 0.02, 0.5], pos=[0, -0.01, 0], color="wood", cut=False),
        B("obj", "box", name=obj_name, info=obj_info, size=[0.4, 0.02, 0.03], pos=[0, 0.02, -0.08], color="#b5651d",
          bind={"sx": {"var": "p.L", "k": 2.5}}),
        B("scale", "scale", name="Metre scale (cm and mm)", length=1.0, spacing=0.001, major=10, labels=True,
          label_step=10, tick=0.008, font=0.014, pos=[-0.5, 0.012, 0.06]),
        B("lbl", "text", text="0", size=0.02, pos=[-0.5, 0.02, 0.12]),
    ]
    return out + (extra or [])


def length_nonstandard() -> dict:
    return lab(
        id="school-length-nonstandard", rig="school-measuring-bench",
        title="Measuring a length with non-standard units", group="Physics · Measurement", level="Class VI",
        topic="Measurement", chapter="Measurement",
        aim="Measure the same length with your hand span, your cubit and your foot step, and see why such units cannot be shared.",
        kernel="length_measure", params={"unit": 0.22, "lc": 0.055, "par": 0.0}, autorun=True,
        camera={"pos": [0.3, 0.45, 1.0], "look": [0, 0.02, -0.02]}, floor=-0.02,
        bodies=_bench_bodies("Length being measured", "A strip of cloth laid along the bench. Its true length is hidden."),
        knobs=[knob("L", "Take another length (true length hidden)", "L", 40, 160, 1, 110, "cm", 0.01, hidden=True),
               knob("unit", "One unit of this method", "unit", 10, 60, 0.5, 22, "cm", 0.01,
                    hint="A hand span is about 22 cm, a cubit about 45 cm, a foot step about 60 cm - and every person's is different.")],
        instruments=[inst("ct", "readout", "Units counted (help)", "count", digits=2, hint=True),
                     inst("rd", "readout", "Length so far", "reading", k=100, unit="cm", lc=0.1, digits=1)],
        table={"columns": [col("reading", "Length measured", "manual", "cm", 0.01, digits=1)],
               "calc": "gauge_mean", "rows_min": 2, "truth": "p.L", "result_k": 100, "result_unit": "cm",
               "result_digits": 1, "hint": "Lay the unit end to end without a gap and without overlapping."},
        steps=["Lay your hand span along the cloth, end to end, and count the spans.",
               "Estimate the last part of a span to the nearest quarter.",
               "Write the length down in hand spans, then in cubits and in foot steps.",
               "Compare with a friend's count: the same cloth, a different number. That is why we need a standard unit."],
        theory="A length can be measured with any unit, but a hand span, a cubit and a foot step are different for "
               "every person, so the same cloth gives different numbers. This is why the metre, which is the same "
               "everywhere, was agreed upon.",
        safety="Lay the units end to end along the cloth; do not leave gaps and do not let them overlap.",
        tour=[{"say": "A strip of cloth on the bench. We will measure it with a hand span first."},
              {"set": {"unit": 45}, "say": "A cubit is longer than a hand span, so the same cloth is fewer cubits."},
              {"set": {"unit": 22}, "say": "Record the length with each method in the table."}],
        questions=[{"q": "Why is a hand span a poor unit of length?", "options": ["It is different for every person",
                    "It is too small", "It cannot measure cloth"], "answer": 0,
                    "why": "A unit must be the same for everybody; a hand span is not."},
                   {"q": "The same cloth comes to 5 hand spans but only 2.5 cubits. Why?",
                    "options": ["A cubit is about twice a hand span", "The cloth shrank", "One count is wrong"],
                    "answer": 0, "why": "The bigger the unit, the smaller the number of units."}],
        sources=[S6, SIM],
        check={"params": {"L": 1.10, "par": 0.0}, "reading": "reading", "textbook": "length_true"},
    )


def length_ruler() -> dict:
    return lab(
        id="school-length-ruler", rig="school-measuring-bench",
        title="Measuring length with a scale", group="Physics · Measurement", level="Class VI",
        topic="Measurement", chapter="Measurement",
        aim="Measure a rod with a metre scale: place the scale correctly, keep the eye right above the mark, and read to the millimetre.",
        kernel="length_measure", params={"unit": 0.001, "lc": 0.001}, autorun=True,
        camera={"pos": [0.25, 0.4, 0.8], "look": [0, 0.02, 0]}, floor=-0.02,
        bodies=_bench_bodies("Rod being measured", "A wooden rod on the bench. Its true length is hidden: you must measure it."),
        knobs=[knob("L", "Take another rod (true length hidden)", "L", 5, 60, 0.1, 23.7, "cm", 0.01, hidden=True),
               knob("par", "Eye to one side (parallax error)", "par", -0.4, 0.4, 0.1, 0, "cm", 0.01,
                    hint="Looking from the side shifts the mark. Keep the eye straight above it and this becomes zero.")],
        instruments=[inst("rd", "readout", "Reading on the scale", "reading", k=100, unit="cm", lc=0.1, digits=1),
                     inst("lc", "readout", "Least count", "lc", k=1000, unit="mm", digits=1)],
        table={"columns": [col("reading", "Length of the rod", "manual", "cm", 0.01, digits=2)],
               "calc": "gauge_mean", "rows_min": 2, "truth": "p.L", "result_k": 100, "result_unit": "cm",
               "result_digits": 2, "hint": "Measure the rod twice, from two different starting marks, and average."},
        steps=["Lay the rod along the scale with one end exactly on a full centimetre mark.",
               "Bring your eye straight above the other end: no squint from the side.",
               "Read the centimetres, then count the millimetres after them.",
               "Repeat from a different starting mark and take the average."],
        theory="A metre scale has millimetre divisions, so its least count is 1 mm. Start from a clear mark (not "
               "the worn end of the scale), keep the eye vertically above the mark being read, and subtract the "
               "starting mark from the finishing mark.",
        safety="Never measure from a broken or worn end of the scale; start from a clear mark instead.",
        tour=[{"say": "A rod on the bench beside a metre scale, which has millimetre divisions."},
              {"set": {"par": 0.3}, "say": "Looking from the side moves the mark: this is parallax error."},
              {"set": {"par": 0}, "say": "Eye straight above the mark: now the reading is right. Record it in the table."}],
        questions=[{"q": "The least count of an ordinary metre scale is", "options": ["1 mm", "1 cm", "0.1 mm"],
                    "answer": 0, "why": "The smallest printed division is one millimetre."},
                   {"q": "Why should the eye be straight above the mark?", "options": ["To avoid parallax error",
                    "To see the numbers bigger", "To keep the scale straight"], "answer": 0,
                    "why": "From the side, the mark appears shifted and the reading is wrong."}],
        sources=[S6M, SIM],
        check={"params": {"L": 0.237, "par": 0.0}, "reading": "reading", "textbook": "length_true"},
    )


def length_curve() -> dict:
    return lab(
        id="school-length-curve", rig="school-measuring-bench",
        title="Length of a curved line with a thread", group="Physics · Measurement", level="Class VI",
        topic="Measurement", chapter="Measurement",
        aim="Lay a thread along a curved line, mark its ends, straighten it on the scale and so measure a length a scale cannot reach.",
        kernel="length_measure", params={"unit": 0.001, "lc": 0.001, "par": 0.0}, autorun=True,
        camera={"pos": [0.2, 0.5, 0.75], "look": [0, 0.02, -0.02]}, floor=-0.02,
        bodies=_bench_bodies("Card with the curved line", "The ink line curves, so a straight scale cannot measure it.",
                             [B("thread", "rope", name="Thread", info="Light thread laid along the line, then straightened on the scale.",
                                a=[-0.3, 0.025, -0.2], b=[0.3, 0.025, -0.2], r=0.0008, color="white")]),
        knobs=[knob("L", "Take another line (true length hidden)", "L", 10, 90, 0.1, 46, "cm", 0.01, hidden=True)],
        instruments=[inst("rd", "readout", "Thread length on the scale", "reading", k=100, unit="cm", lc=0.1, digits=1),
                     inst("lc", "readout", "Least count", "lc", k=1000, unit="mm", digits=1)],
        table={"columns": [col("reading", "Length of the curved line", "manual", "cm", 0.01, digits=1)],
               "calc": "gauge_mean", "rows_min": 2, "truth": "p.L", "result_k": 100, "result_unit": "cm",
               "result_digits": 1, "hint": "Lay the thread along the line twice and average the two readings."},
        steps=["Tie a knot at one end of the thread and hold that knot at the start of the line.",
               "Press the thread along the line with your finger, following every bend.",
               "Mark the thread with ink where the line ends.",
               "Straighten the thread along the metre scale and read the length between the knot and the mark."],
        theory="A straight scale cannot follow a curve. A thread can: laid along the line it takes up the same "
               "length, and straightened on the scale that length can be read. The thread must not be stretched, "
               "or the answer comes out too large.",
        safety="Use thread that does not stretch, and do not pull it tight while laying it along the line.",
        tour=[{"say": "An ink line on a card curves across the bench; a straight scale cannot measure it."},
              {"say": "The thread is laid along the line, marked, and then straightened on the scale."}],
        questions=[{"q": "Why is a thread used for a curved line?", "options": ["It bends along the curve and keeps the same length",
                    "It is longer than the scale", "It is lighter"], "answer": 0,
                    "why": "The thread follows the bends, then it is straightened and read on the scale."},
                   {"q": "If the thread is stretched while laying it, the answer comes out",
                    "options": ["Too large", "Too small", "Unchanged"], "answer": 0,
                    "why": "A stretched thread is longer than the line it was laid along."}],
        sources=[S6, SIM],
        check={"params": {"L": 0.46, "par": 0.0}, "reading": "reading", "textbook": "length_true"},
    )


# =============================================================================================== HEAT
def _heat_bodies(liquid_name: str) -> list[dict]:
    return [
        B("stand", "box", name="Stand base", size=[0.3, 0.02, 0.2], pos=[0, -0.07, 0], color="iron" if False else "#2b2f36"),
        B("tripod", "cylinder", name="Tripod stand", r=0.055, h=0.01, open=True, pos=[0, -0.05, 0], color="#2b2f36"),
        B("gauze", "box", name="Wire gauze", size=[0.11, 0.002, 0.11], pos=[0, -0.045, 0], color="#9aa3ad"),
        B("beaker", "cylinder", name="Beaker", r=0.055, h=0.13, open=True, pos=[0, 0.02, 0], color="glass", opacity=0.3),
        B("liq", "cylinder", name=liquid_name, r=0.052, h=0.09, pos=[0, 0.0, 0], color="water", opacity=0.55),
        B("tglass", "cylinder", name="Laboratory thermometer", r=0.006, h=0.3, pos=[0.02, 0.16, 0], color="glass", opacity=0.35),
        B("tbulb", "sphere", r=0.009, pos=[0.02, 0.01, 0], color="mercury"),
        B("thg", "cylinder", r=0.0028, h=0.01, pos=[0.02, 0.02, 0], color="mercury",
          bind={"sy": {"var": "T", "k": 0.22, "min": 0.01}, "y": {"var": "T", "k": 0.0011}}),
        B("tsc", "scale", length=0.25, spacing=0.0025, major=10, labels=True, label_step=10, tick=0.006, font=0.012,
          pos=[0.028, 0.02, 0], rot=[0, 0, 1.5708], down=True),
        B("lamp", "cylinder", name="Spirit lamp", info="The teacher lights it. It warms the liquid through the wire gauze.",
          r=0.03, h=0.05, pos=[0, -0.12, 0], color="brass"),
    ]


def thermometer_read() -> dict:
    return lab(
        id="school-thermometer-read", rig="school-heat-bench",
        title="Reading a clinical and a laboratory thermometer", group="Physics · Measurement", level="Class VI",
        topic="Measurement", chapter="Measurement",
        aim="Read the mercury thread on a clinical thermometer (35-42 °C, least count 0.1 °C) and on a laboratory thermometer (-10 to 110 °C, least count 0.5 °C).",
        kernel="thermo_bath", params={"P": 0.0, "hA": 0.0, "Q0": 0.0, "lc": 0.1, "Ts": 30.0}, autorun=True,
        camera={"pos": [0.22, 0.25, 0.5], "look": [0.02, 0.1, 0]}, floor=-0.14,
        bodies=_heat_bodies("Water in the beaker"),
        knobs=[knob("T0", "Take another reading (true temperature hidden)", "T0", 34, 42, 0.1, 37.2, "°C", hidden=True),
               knob("lc", "Least count of this thermometer", "lc", 0.1, 0.5, 0.4, 0.1, "°C",
                    hint="A clinical thermometer reads to 0.1 °C; a laboratory thermometer to 0.5 °C or 1 °C.")],
        instruments=[inst("rd", "readout", "Thermometer reading", "reading", unit="°C", lc=0.1, digits=1),
                     inst("lcr", "readout", "Least count", "p.lc", unit="°C", digits=1)],
        table={"columns": [col("reading", "Temperature read", "manual", "°C", digits=1)],
               "calc": "gauge_mean", "rows_min": 2, "truth": "p.T0", "result_unit": "°C", "result_digits": 1,
               "hint": "Hold the thermometer level with your eye and read the end of the mercury thread."},
        steps=["Find the range printed on the thermometer and its smallest division.",
               "Put the bulb where the temperature is to be measured and wait until the thread stops moving.",
               "Hold it level with your eye and read the number at the end of the mercury thread.",
               "Record the reading; take it again to be sure."],
        theory="A thermometer is read at the end of the mercury thread, with the eye level with it. The clinical "
               "thermometer covers only 35 to 42 °C because body temperature lies in that range, and it has a kink "
               "that holds the thread until it is shaken down. A laboratory thermometer has a wider range, -10 to "
               "110 °C, so its divisions are coarser.",
        safety="Mercury thermometers are glass: never shake a laboratory thermometer and never put a clinical "
               "thermometer in boiling water - it would break. A broken thermometer is cleared up by the teacher.",
        tour=[{"say": "Two thermometers: the clinical one with the short scale, and the laboratory one that reads much further."},
              {"set": {"lc": 0.5}, "say": "The laboratory thermometer has coarser divisions, so it is read to half a degree."},
              {"set": {"lc": 0.1}, "say": "Record each reading in the table."}],
        questions=[{"q": "The range of a clinical thermometer is", "options": ["35 to 42 °C", "0 to 100 °C",
                    "-10 to 110 °C"], "answer": 0, "why": "Body temperature lies between 35 and 42 °C."},
                   {"q": "Why must the eye be level with the end of the thread?",
                    "options": ["Otherwise the reading is shifted by parallax", "To warm the bulb", "To hold it steady"],
                    "answer": 0, "why": "Looking from above or below shifts the mark that appears to line up."}],
        sources=[S6T, SIM],
        check={"params": {"T0": 37.2, "lc": 0.1}, "reading": "reading", "textbook": "bath_T"},
    )


def melting_boiling() -> dict:
    return lab(
        id="school-melting-boiling", rig="school-heat-bench",
        title="Melting point of ice and boiling point of water", group="Physics · Heat", level="Class IX",
        topic="Heat", chapter="Heat",
        aim="Heat the beaker steadily and watch the thermometer: while the state changes, the temperature does not rise at all.",
        kernel="thermo_bath", params={"T0": 28.0, "Ts": 30.0, "C": 1256.0, "hA": 2.0, "Tp": 100.0, "Q0": 90000.0, "lc": 0.5},
        speed=20, speeds=[5, 20, 60],
        camera={"pos": [0.24, 0.26, 0.55], "look": [0.02, 0.1, 0]}, floor=-0.14,
        bodies=_heat_bodies("Water being heated"),
        knobs=[knob("P", "Flame (heat going in)", "P", 100, 400, 10, 300, "W",
                    hint="A bigger flame boils the water sooner, but it still boils at the same temperature."),
               knob("Ts", "Room temperature", "Ts", 15, 40, 1, 30, "°C")],
        instruments=[inst("T", "readout", "Thermometer", "T", unit="°C", lc=0.5, digits=1),
                     inst("sw", "stopwatch", "Stopwatch"),
                     inst("gr", "graph", "Temperature against time", "T", xlabel="t (s)")],
        table={"columns": [col("reading", "Temperature while the state changes", "manual", "°C", digits=1)],
               "calc": "gauge_mean", "rows_min": 3, "truth": "p.Tp", "result_unit": "°C", "result_digits": 1,
               "hint": "Once the thermometer stops rising, record a reading every 30 s."},
        steps=["Start the stopwatch and the flame together, and stir gently.",
               "Note the temperature every 30 seconds while it climbs.",
               "When the thermometer stops rising although the flame is still on, record those readings: that is the "
               "temperature of the change of state.",
               "Draw the graph: a slope, then a flat part while the state changes."],
        theory="While a substance changes state, the heat going in does not raise the temperature: it is latent heat, "
               "spent on the change itself. So melting ice holds at 0 °C and boiling water holds at 100 °C under one "
               "atmosphere, however big the flame is. On the temperature-time graph this is a flat part.",
        safety="The teacher lights and puts out the spirit lamp. Keep the beaker on the wire gauze, fill it only "
               "half way, stir with the stirrer and never lean over boiling water. Use a laboratory thermometer, "
               "never a clinical one.",
        tour=[{"say": "Water in a beaker on a wire gauze, warmed by the lamp. The simulation runs faster than the lab.", "run": True},
              {"say": "The temperature climbs and then stops at the boiling point, although the flame is still burning."},
              {"set": {"P": 400}, "say": "A bigger flame boils it sooner, but at the same temperature."}],
        questions=[{"q": "While ice is melting, the temperature of the mixture", "options": ["Stays at 0 °C",
                    "Rises steadily", "Falls"], "answer": 0, "why": "The heat goes into melting, not into warming."},
                   {"q": "A bigger flame under boiling water", "options": ["Boils it away faster at the same temperature",
                    "Makes it hotter than 100 °C", "Stops it boiling"], "answer": 0,
                    "why": "The extra heat turns more water into steam; the temperature stays at the boiling point."}],
        sources=[L9, S7, SIM],
        check={"params": {}, "reading": "Tplateau_K", "textbook": "phase_T_K"},
    )


def _rod_bodies(sample: str) -> list[dict]:
    out = [
        B("board", "box", name="Working board", size=[1.0, 0.02, 0.4], pos=[0, -0.01, 0], color="wood", cut=False),
        B("rod", "cylinder", name=sample, info="Heated at the left end; wax-stuck pins hang along it.",
          r=0.006, h=0.3, pos=[0, 0.06, 0], rot=[0, 0, 1.5708], color="copper"),
        B("clampL", "box", name="Clamp", size=[0.03, 0.08, 0.03], pos=[-0.17, 0.02, 0], color="#2b2f36"),
        B("clampR", "box", name="Clamp", size=[0.03, 0.08, 0.03], pos=[0.17, 0.02, 0], color="#2b2f36"),
        B("lamp", "cylinder", name="Spirit lamp", info="The teacher lights it under the left end of the rod.",
          r=0.028, h=0.05, pos=[-0.15, -0.03, 0], color="brass"),
        B("thermo", "cylinder", name="Thermometer at the measuring point", r=0.006, h=0.22, pos=[0.12, 0.17, 0.02],
          color="glass", opacity=0.35),
        B("tbulb", "sphere", r=0.008, pos=[0.12, 0.065, 0.02], color="mercury"),
        B("thg", "cylinder", r=0.0026, h=0.01, pos=[0.12, 0.07, 0.02], color="mercury",
          bind={"sy": {"var": "Tx", "k": 0.16, "min": 0.01}, "y": {"var": "Tx", "k": 0.0008}}),
    ]
    for i, x in enumerate((-0.1, -0.05, 0.0, 0.05, 0.1)):
        out.append(B(f"pin{i}", "cylinder", name="Wax-stuck pin", r=0.0012, h=0.025, pos=[x, 0.045, 0.008], color="steel"))
        out.append(B(f"wax{i}", "sphere", name="Wax", r=0.0035, pos=[x, 0.056, 0.006], color="white"))
    return out


def conduction_rod() -> dict:
    return lab(
        id="school-conduction-rod", rig="school-conduction-bench",
        title="Conduction along a metal rod", group="Physics · Heat", level="Class VII",
        topic="Heat", chapter="Heat",
        aim="Heat one end of a metal rod and watch the wax-stuck pins fall one after another; measure how hot the far end becomes.",
        kernel="conduction_fin",
        params={"k": 401.0, "d": 0.012, "Lr": 0.3, "Th": 95.0, "Ts": 30.0, "h": 12.0, "alpha": 1.17e-4,
                "Tmelt": 52.0, "xm": 0.25, "t0": 4.0},
        speed=5, speeds=[1, 5, 20],
        camera={"pos": [0.3, 0.3, 0.7], "look": [0, 0.06, 0]}, floor=-0.02,
        bodies=_rod_bodies("Copper rod"),
        knobs=[knob("k", "Rod material (conductivity hidden)", "k", 0.15, 430, 0.05, 401, "W/(m·K)", hidden=True),
               knob("Th", "Temperature of the hot end", "Th", 60, 100, 1, 95, "°C"),
               knob("Ts", "Room temperature", "Ts", 15, 40, 1, 30, "°C")],
        instruments=[inst("Tx", "readout", "Thermometer at the measuring point", "Tx", unit="°C", lc=0.5, digits=1),
                     inst("sw", "stopwatch", "Stopwatch"),
                     inst("gr", "graph", "Temperature at the measuring point", "Tx", xlabel="t (s)")],
        table={"columns": [col("x", "Distance from the hot end", "manual", "cm", 0.01, digits=1),
                           col("reading", "Temperature there", "manual", "°C", digits=1)],
               "calc": "gauge_mean", "rows_min": 3, "result_unit": "°C", "result_digits": 1,
               "hint": "Note the time each pin falls, and the temperature the thermometer settles at that distance."},
        steps=["Stick the pins along the rod with wax and clamp the rod level.",
               "The teacher lights the lamp under the left end; start the stopwatch at the same moment.",
               "Note the time each pin falls: the nearest first, the farthest last.",
               "Touch the thermometer to the rod at each pin's place and record the temperature it settles at."],
        theory="In a solid, heat travels by conduction: the particles pass it on without moving from their places. "
               "Along a rod heated at one end, the temperature falls away from the hot end, because heat is lost to "
               "the air on the way. At the steady state, T(x) = Ts + (Th - Ts) cosh((L - x)/λ) / cosh(L/λ), where "
               "λ = √(k d / 4h) is larger for a better conductor - so a copper rod stays hot much further along "
               "than a glass one.",
        safety="The teacher lights and puts out the spirit lamp. Never touch the hot end or the rod near it; let the "
               "rod cool on the stand before taking it off.",
        tour=[{"say": "A metal rod clamped level, with pins stuck along it by wax, and the lamp under its left end.", "run": True},
              {"say": "The pin nearest the flame falls first: the heat reaches it soonest."},
              {"set": {"k": 1.05}, "say": "With a glass rod the far pins never fall at all: glass is a poor conductor."},
              {"set": {"k": 401}, "say": "Back to copper. Record the time of each fall and the temperature there."}],
        questions=[{"q": "Why does the pin nearest the flame fall first?", "options": ["The heat reaches it soonest",
                    "Its wax is thinner", "It is heavier"], "answer": 0,
                    "why": "Heat is conducted along the rod, so the near end gets hot first."},
                   {"q": "With a glass rod in place of copper, the far pins", "options": ["Do not fall",
                    "Fall sooner", "Fall at the same time"], "answer": 0,
                    "why": "Glass conducts heat poorly, so the far end hardly warms."}],
        sources=[S7C, S7, CRC, SIM],
        check={"params": {}, "reading": "Tx", "textbook": "fin_Tx"},
    )


def spoons() -> dict:
    return lab(
        id="school-spoons-conduction", rig="school-conduction-bench",
        title="Good and poor conductors: spoons in hot water", group="Physics · Heat", level="Class VII",
        topic="Heat", chapter="Heat",
        aim="Stand spoons of different materials in hot water and measure how warm each handle becomes: which materials carry heat and which do not.",
        kernel="conduction_fin",
        params={"k": 16.0, "d": 0.008, "Lr": 0.12, "Th": 90.0, "Ts": 30.0, "h": 12.0, "alpha": 4.05e-6,
                "Tmelt": 34.0, "xm": 0.1, "t0": 2.0},
        speed=5, speeds=[1, 5, 20],
        camera={"pos": [0.26, 0.26, 0.55], "look": [0.0, 0.08, 0]}, floor=-0.02,
        bodies=_rod_bodies("Spoon handle"),
        knobs=[knob("k", "Spoon material (conductivity hidden)", "k", 0.15, 430, 0.05, 16, "W/(m·K)", hidden=True),
               knob("Th", "Temperature of the hot water", "Th", 50, 95, 1, 90, "°C"),
               knob("Ts", "Room temperature", "Ts", 15, 40, 1, 30, "°C")],
        instruments=[inst("Tx", "readout", "Thermometer at the handle top", "Tx", unit="°C", lc=0.5, digits=1),
                     inst("sw", "stopwatch", "Stopwatch"),
                     inst("gr", "graph", "Temperature of the handle top", "Tx", xlabel="t (s)")],
        table={"columns": [col("x", "Distance up the handle", "manual", "cm", 0.01, digits=1),
                           col("reading", "Temperature there", "manual", "°C", digits=1)],
               "calc": "gauge_mean", "rows_min": 3, "result_unit": "°C", "result_digits": 1,
               "hint": "Stick a little butter at the top of each handle and watch which ones melt."},
        steps=["Stand the spoon in the beaker of hot water, handle up and clear of the glass.",
               "Stick a small blob of butter at the top of the handle.",
               "Wait two minutes, then touch the thermometer to the handle and record the temperature.",
               "Repeat with the other spoons and compare: metals carry heat, wood and plastic hardly do."],
        theory="Materials that pass heat on quickly are conductors; those that hardly pass it on are insulators. "
               "The handle of a spoon standing in hot water reaches the steady temperature "
               "T(x) = Ts + (Th - Ts) cosh((L - x)/λ) / cosh(L/λ) with λ = √(k d / 4h). A copper handle has a long "
               "λ and becomes nearly as hot as the water; a wooden one stays at room temperature, which is why "
               "cooking spoons are made of wood.",
        safety="Hot water can scald. Pour it with the teacher, hold the spoon by the very top, and keep the beaker "
               "on the bench, never on the edge.",
        tour=[{"say": "A spoon stands in hot water, with a blob of butter at the top of the handle.", "run": True},
              {"set": {"k": 401}, "say": "A copper spoon: the handle gets hot in moments and the butter melts."},
              {"set": {"k": 0.15}, "say": "A wooden spoon: the handle stays cool and the butter does not melt."},
              {"set": {"k": 16}, "say": "The steel spoon again. Record the handle temperature for each material."}],
        questions=[{"q": "Cooking spoons are made of wood because wood", "options": ["Hardly conducts heat",
                    "Is cheap", "Is light"], "answer": 0, "why": "A poor conductor keeps the handle cool."},
                   {"q": "Which handle becomes hottest in the same hot water?", "options": ["Copper", "Stainless steel",
                    "Plastic"], "answer": 0, "why": "Copper has by far the highest thermal conductivity of the three."}],
        sources=[S7, CRC, SIM],
        check={"params": {}, "reading": "Tx", "textbook": "fin_Tx"},
    )


BUILDERS = (length_nonstandard, length_ruler, length_curve, thermometer_read, melting_boiling, conduction_rod, spoons)
