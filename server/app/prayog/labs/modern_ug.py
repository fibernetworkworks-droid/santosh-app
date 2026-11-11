"""Lab pack `modern_ug`: the B.Sc. benches of modern and atomic physics, nuclear and radiation physics, solid
state physics and nanomaterials (UGC LOCF 2019 / DU UGCF 2022 practical lists). The physics lives in
`packs/modern_ug.py` (and its JavaScript twin); every lab here names the studio RIG that draws the real bench.

These labs carry no `table` block: the observation table and the result are worked out by the rig, which reads
every number from the lab's own params through the kernel.

Radioactive work follows the real rules of a teaching lab: sealed sources only, handled with tongs from behind a
lead shield, counted at a set distance and locked away afterwards. The procedure says so at every step.
"""
from __future__ import annotations

import math
from typing import Any

from ..catalog import B, S12, SIM, board, dial, inst, knob, lab, needle

DEG = math.pi / 180
R2D = 180 / math.pi

UGC = {"title": "UGC Learning Outcomes based Curriculum Framework for B.Sc. Physics (2019) and the University of "
                "Delhi B.Sc. (Hons.) Physics practical lists (LOCF 2019 / UGCF 2022)"}
CODATA = {"title": "CODATA / SI 2019 defining constants: h = 6.62607015e-34 J s, c = 299792458 m/s, "
                   "e = 1.602176634e-19 C, k = 1.380649e-23 J/K"}
CRC_WF = {"title": "CRC Handbook of Chemistry and Physics, table 'Electron work function of the elements'"}
NIST_HG = {"title": "NIST Atomic Spectra Database: the mercury lines 365.0, 404.7, 435.8, 546.1 and 578.0 nm"}
CRC_SEMI = {"title": "CRC Handbook of Chemistry and Physics and S. M. Sze, Physics of Semiconductor Devices: "
                     "band gaps and intrinsic resistivities of Ge, Si and GaAs at 300 K"}
NNDC = {"title": "NNDC / IAEA evaluated nuclear data: half-lives and gamma energies of In-116m, Ba-137m, "
                 "Cs-137, Co-60, Ba-133 and Na-22"}
XCOM = {"title": "NIST XCOM / Hubbell photon attenuation tables: mass attenuation coefficients at 662 keV"}
HAISS = {"title": "W. Haiss, N. T. K. Thanh, J. Aveyard, D. G. Fernig, 'Determination of size and concentration "
                  "of gold nanoparticles from UV-Vis spectra', Anal. Chem. 79 (2007) 4215"}
RAD_SAFE = {"title": "AERB Safety Guidelines for sealed radioactive sources in teaching laboratories "
                     "(source handled with tongs behind a shield, kept in its locked store)"}


def _w(id: str, pts: list[list[float]], color: str = "red") -> dict:
    return B(id, "wire", pts=pts, r=0.003, color=color)


def _lcd(id: str, x: float, z: float, name: str, info: str, var: str, w: float = 0.18) -> list[dict]:
    """A bench-top digital instrument drawn as data (the rig draws the real one)."""
    return [B(id, "box", name=name, info=info, size=[w, 0.055, 0.13], pos=[x, 0.0275, z], color="#2b2f36"),
            B(id + "_s", "box", size=[w - 0.05, 0.002, 0.04], pos=[x, 0.056, z - 0.03], color="#9eab8b",
              bind={"sx": {"var": var, "k": 0.0, "c": 1.0}}),
            B(id + "_k", "cylinder", r=0.012, h=0.008, pos=[x, 0.059, z + 0.035], color="black")]


# ==================================================================================== photoelectric effect (Planck)
def photoelectric() -> dict:
    return lab(
        id="photoelectric-planck", rig="photoelectric-bench",
        title="Photoelectric effect: Planck's constant", group="Physics · Modern Physics", level="B.Sc.",
        topic="Elements of Modern Physics", chapter="Modern and atomic physics",
        aim="Measure the stopping potential of a photocell at four wavelengths of a mercury lamp and find "
            "Planck's constant and the work function of the cathode.",
        kernel="photocell",
        params={"lam": 4.0466e-7, "phi": 2.14, "Vr": 0.0, "P": 1.0, "Isat0": 1.2e-9, "dark": 2.0e-12,
                "lam1": 3.6502e-7, "lam2": 4.0466e-7, "lam3": 4.3583e-7, "lam4": 5.4607e-7, "lam5": 5.7907e-7},
        autorun=True, camera={"pos": [0.0, 0.7, 0.9], "look": [0, 0.02, -0.1]}, floor=-0.03,
        bodies=[
            board(1.0, 0.6),
            B("lamp", "cylinder", name="Mercury lamp", info="A high-pressure mercury lamp in its housing: its "
              "light is a few sharp lines, not a continuous spectrum.", r=0.035, h=0.1,
              pos=[-0.34, 0.05, -0.12], color="#cfd6de"),
            B("house", "box", size=[0.12, 0.12, 0.12], pos=[-0.34, 0.06, -0.12], color="#3a4049", opacity=0.45),
            B("filt", "cylinder", name="Filter wheel", info="Five interference filters: 365, 405, 436, 546 and "
              "578 nm. Only one line reaches the photocell at a time.", r=0.055, h=0.012,
              pos=[-0.14, 0.06, -0.12], rot=[0, 0, 1.5708], color="#2b2f36"),
            B("cellb", "cylinder", name="Photocell", info="An evacuated glass bulb: light falls on the coated "
              "cathode and the electrons are collected by the ring anode.", r=0.045, h=0.07,
              pos=[0.08, 0.06, -0.12], rot=[0, 0, 1.5708], color="glass", opacity=0.6),
            B("cath", "box", size=[0.002, 0.05, 0.04], pos=[0.1, 0.06, -0.12], color="#8c949e"),
            B("anode", "torus", r=0.012, tube=0.0015, pos=[0.055, 0.06, -0.12], rot=[0, 1.5708, 0], color="brass"),
            B("psu", "box", name="Retarding voltage supply", info="A fine 0-3 V supply that pushes the electrons "
              "back; its reading is the retarding voltage.", size=[0.2, 0.07, 0.13],
              pos=[0.36, 0.035, -0.1], color="#3a4f6e"),
            *dial("ua", [0.3, 0.0, 0.12], "Micro-ammeter (nA)", "Reads the photocurrent, a few nanoamperes."),
            needle("uan", [0.3, 0.0, 0.12], "I_nA", -1.6, 1.2),
            *dial("vm", [0.0, 0.0, 0.14], "Voltmeter (0-3 V)", "Reads the retarding voltage on the anode."),
            needle("vmn", [0.0, 0.0, 0.14], "V", -0.8, 1.2),
            _w("w1", [[0.12, 0.03, -0.12], [0.3, 0.03, 0.06]]),
            _w("w2", [[0.04, 0.03, -0.12], [0.0, 0.03, 0.08]], "black"),
            _w("w3", [[0.3, 0.03, -0.1], [0.3, 0.03, 0.06]], "blue"),
        ],
        knobs=[knob("Vr", "Retarding voltage", "Vr", 0, 3, 0.01, 0, "V"),
               knob("lam", "Filter (wavelength)", "lam", 300, 700, 1, 405, "nm", 1e-9),
               knob("P", "Light power (lamp distance)", "P", 0.2, 1.0, 0.05, 1.0),
               knob("phi", "Cathode (its work function is hidden)", "phi", 1.5, 3.0, 0.01, 2.14, "eV", hidden=True)],
        instruments=[inst("I", "readout", "Photocurrent", "I", k=1e9, unit="nA", lc=0.01, digits=2),
                     inst("V", "readout", "Retarding voltage", "V", unit="V", lc=0.01, digits=2),
                     inst("gr", "graph", "Photocurrent against retarding voltage", "I", k=1e9, x="p.Vr",
                          xlabel="V (V)", dots=True)],
        steps=["Put the 365 nm filter in front of the photocell and switch the mercury lamp on.",
               "Raise the retarding voltage until the photocurrent just falls to zero: that is the stopping potential.",
               "Repeat for the 405, 436 and 546 nm filters.",
               "Plot the stopping potential against the frequency of the light: the slope is h/e.",
               "The intercept on the voltage axis is the work function of the cathode in electron volts."],
        theory="Light of frequency f carries its energy in photons of hf. One photon gives all of it to one "
               "electron in the cathode, which needs the work function φ to escape, so the fastest electron "
               "leaves with the energy hf − φ. A retarding voltage V on the anode turns back every electron "
               "with less energy than eV, so the current stops at the stopping potential eVs = hf − φ. The plot "
               "of Vs against f is a straight line of slope h/e, whatever the metal; the metal only moves the "
               "line up or down. The brightness of the light changes how many electrons come out, never how "
               "fast they are: that is what a wave picture cannot explain.",
        safety="Never look into the mercury lamp: it gives strong ultraviolet light. Keep its housing closed and "
               "let it warm up before taking readings.",
        tour=[{"say": "The mercury lamp, the filter wheel, the photocell and the retarding voltage supply, in a line."},
              {"set": {"lam": 365}, "say": "The 365 nanometre line: the most energetic photons, so the largest stopping potential."},
              {"set": {"Vr": 1.2}, "say": "With 1.2 volts pushing the electrons back the current has fallen to zero."},
              {"set": {"lam": 546, "Vr": 0.0}, "say": "The green 546 nanometre line: much weaker photons, so the current stops at a far smaller voltage."}],
        questions=[{"q": "Making the light brighter changes", "options": [
            "The photocurrent, not the stopping potential", "The stopping potential, not the photocurrent",
            "Neither"], "answer": 0,
            "why": "More photons free more electrons, but each photon still carries the same energy hf."},
            {"q": "The slope of the stopping potential against frequency gives", "options": [
                "h/e", "The work function", "The threshold frequency"], "answer": 0,
             "why": "eVs = hf − φ, so dVs/df = h/e."}],
        sources=[UGC, CODATA, CRC_WF, NIST_HG, SIM],
        check={"params": {"lam": 4.0466e-7, "phi": 2.14}, "reading": "Vs", "textbook": "photo_Vs"},
    )


# ==================================================================================== Planck's constant with LEDs
def led_planck() -> dict:
    return lab(
        id="led-planck-constant", rig="led-planck-bench",
        title="Planck's constant from LEDs of four colours", group="Physics · Modern Physics", level="B.Sc.",
        topic="Elements of Modern Physics", chapter="Modern and atomic physics",
        aim="Measure the turn-on voltage of light-emitting diodes of five colours and find Planck's constant "
            "from the slope of the turn-on voltage against 1/λ.",
        kernel="ledgap",
        params={"lam": 5.25e-7, "Iref": 0.001, "nD": 2.0, "Rs": 220.0, "Eb": 1.0,
                "lam1": 6.3e-7, "lam2": 5.9e-7, "lam3": 5.25e-7, "lam4": 4.7e-7, "lam5": 4.05e-7},
        autorun=True, camera={"pos": [0.0, 0.6, 0.75], "look": [0, 0.02, -0.08]}, floor=-0.03,
        bodies=[
            board(0.9, 0.55),
            B("psu", "box", name="Variable DC supply", info="0-5 V, turned up slowly from zero.",
              size=[0.2, 0.07, 0.13], pos=[-0.3, 0.035, -0.1], color="#3a4f6e"),
            B("strip", "box", name="LED strip", info="Five LEDs on one board: red 630, amber 590, green 525, "
              "blue 470 and violet 405 nm, each with its own 220 Ω resistor.", size=[0.3, 0.014, 0.08],
              pos=[0.06, 0.007, -0.02], color="#1f6b3a"),
            B("led1", "cylinder", name="Red LED (630 nm)", r=0.0025, h=0.009, pos=[-0.05, 0.02, -0.02], color="red"),
            B("led2", "cylinder", name="Amber LED (590 nm)", r=0.0025, h=0.009, pos=[-0.0, 0.02, -0.02], color="gold"),
            B("led3", "cylinder", name="Green LED (525 nm)", r=0.0025, h=0.009, pos=[0.05, 0.02, -0.02], color="green"),
            B("led4", "cylinder", name="Blue LED (470 nm)", r=0.0025, h=0.009, pos=[0.1, 0.02, -0.02], color="blue"),
            B("led5", "cylinder", name="Violet LED (405 nm)", r=0.0025, h=0.009, pos=[0.15, 0.02, -0.02], color="#6a3ad0"),
            B("res", "box", name="Series resistor 220 Ω", size=[0.05, 0.01, 0.01], pos=[-0.14, 0.02, -0.02],
              color="#d9b46a"),
            *dial("ma", [-0.08, 0.0, 0.16], "Milliammeter (0-5 mA)", "The current through the LED."),
            needle("man", [-0.08, 0.0, 0.16], "I", -480.0, 1.2),
            *dial("vm", [0.22, 0.0, 0.16], "Voltmeter (0-5 V)", "The voltage across the LED."),
            needle("vmn", [0.22, 0.0, 0.16], "V", -0.48, 1.2),
            _w("w1", [[-0.21, 0.03, -0.08], [-0.17, 0.03, -0.02]]),
            _w("w2", [[-0.11, 0.03, -0.02], [-0.08, 0.03, 0.1]]),
            _w("w3", [[0.2, 0.03, -0.02], [0.22, 0.03, 0.1]], "gold"),
            _w("w4", [[-0.3, 0.03, -0.04], [-0.3, 0.03, 0.2], [0.22, 0.03, 0.2]], "black"),
        ],
        knobs=[knob("Eb", "Supply voltage", "Eb", 0, 5, 0.01, 1.0, "V"),
               knob("lam", "LED (peak wavelength)", "lam", 380, 700, 1, 525, "nm", 1e-9),
               knob("Rs", "Series resistor", "Rs", 100, 1000, 10, 220, "Ω")],
        instruments=[inst("V", "readout", "Voltage across the LED", "V", unit="V", lc=0.01, digits=3),
                     inst("I", "readout", "Current", "I", k=1000, unit="mA", lc=0.01, digits=3),
                     inst("gr", "graph", "I against V for this LED", "I", k=1000, x="V", xlabel="V (V)", dots=True)],
        steps=["Join the red LED through its 220 Ω resistor and turn the supply up from zero.",
               "Note the voltage across the LED when the current reaches 1 mA: that is its turn-on voltage.",
               "Repeat for the amber, green, blue and violet LEDs.",
               "Plot the turn-on voltage against 1/λ: the slope is hc/e.",
               "Multiply the slope by e/c to get Planck's constant."],
        theory="An LED gives out one photon of its own colour for each electron that crosses the junction, so "
               "the junction cannot conduct until the applied voltage can pay for that photon: eV₀ = hc/λ. "
               "Below V₀ the current is almost nothing; above it the current rises steeply. Measuring V₀ for "
               "LEDs of several colours and plotting it against 1/λ gives a straight line of slope hc/e, and "
               "that is Planck's constant without a single quantum of light being seen. The series resistor "
               "keeps the current safe and takes the extra voltage; the turn-on voltage is read across the LED "
               "itself, never across the pair.",
        safety="Never look straight into the blue or violet LED from close by, and keep the series resistor in "
               "circuit: an LED without one burns out at once.",
        tour=[{"say": "Five LEDs on one board, each with its own series resistor, and meters across the one in use."},
              {"set": {"lam": 630, "Eb": 2.0}, "say": "The red LED glows at about 1.97 volts: the smallest photon energy of the five."},
              {"set": {"lam": 405, "Eb": 3.4}, "say": "The violet LED needs more than three volts: a violet photon costs much more energy."}],
        questions=[{"q": "Which LED needs the largest voltage before it lights?", "options": [
            "The violet one", "The red one", "They are all the same"], "answer": 0,
            "why": "eV₀ = hc/λ, and violet light has the shortest wavelength of the five."},
            {"q": "The slope of V₀ against 1/λ is", "options": ["hc/e", "h/e", "e/hc"], "answer": 0,
             "why": "V₀ = (hc/e)(1/λ)."}],
        sources=[UGC, CODATA, SIM,
                 {"title": "Kingbright and Cree LED datasheets: peak wavelengths of 5 mm red, amber, green, blue "
                           "and violet LEDs (630, 590, 525, 470 and 405 nm)"}],
        check={"params": {"lam": 5.25e-7}, "reading": "V0", "textbook": "led_V0"},
    )


# ==================================================================================== Franck-Hertz
def franck_hertz() -> dict:
    return lab(
        id="franck-hertz", rig="franck-hertz-bench",
        title="Franck-Hertz experiment: quantised energy levels", group="Physics · Modern Physics", level="B.Sc.",
        topic="Elements of Modern Physics", chapter="Modern and atomic physics",
        aim="Sweep the accelerating voltage of a Franck-Hertz tube, record the collector current, and find the "
            "first excitation potential of the atom from the spacing of the current peaks.",
        kernel="fhtube",
        params={"Vg": 0.0, "Ue": 4.9, "Vc": 1.5, "V0": 7.0, "Vmid": 20.0, "damp": 0.85,
                "Iscale": 1.0e-9, "Ioff": 1.0e-11, "Vmax": 32.0},
        autorun=True, camera={"pos": [0.0, 0.7, 0.85], "look": [0, 0.05, -0.1]}, floor=-0.03,
        bodies=[
            board(1.0, 0.6),
            B("oven", "box", name="Tube oven", info="Holds the tube at a steady temperature so that the vapour "
              "pressure stays the same through the sweep.", size=[0.2, 0.2, 0.18], pos=[-0.22, 0.1, -0.12],
              color="#4a4f57"),
            B("tube", "cylinder", name="Franck-Hertz tube", info="Cathode, grid and collector in the vapour. "
              "Electrons are accelerated to the grid and have to climb a small retarding voltage to be collected.",
              r=0.045, h=0.13, pos=[-0.22, 0.12, -0.12], color="glass", opacity=0.55),
            B("fila", "cylinder", name="Heated cathode", r=0.004, h=0.05, pos=[-0.22, 0.09, -0.12], color="gold"),
            B("gridm", "torus", r=0.025, tube=0.0015, pos=[-0.22, 0.14, -0.12], rot=[-1.5708, 0, 0], color="steel"),
            B("coll", "box", size=[0.04, 0.002, 0.04], pos=[-0.22, 0.17, -0.12], color="#8c949e"),
            B("unit", "box", name="Franck-Hertz control unit", info="Sets the accelerating voltage and reads the "
              "collector current through a built-in electrometer.", size=[0.34, 0.1, 0.2],
              pos=[0.24, 0.05, -0.08], color="#2b2f36"),
            B("face", "box", size=[0.3, 0.002, 0.16], pos=[0.24, 0.101, -0.08], color="white"),
            B("kn1", "cylinder", name="Accelerating voltage knob", r=0.018, h=0.012, pos=[0.14, 0.107, -0.04],
              color="black"),
            B("kn2", "cylinder", name="Retarding voltage knob", r=0.014, h=0.01, pos=[0.3, 0.107, -0.04],
              color="black"),
            B("meter", "box", name="Current readout", size=[0.1, 0.003, 0.05], pos=[0.24, 0.103, -0.14],
              color="#9eab8b", bind={"sx": {"var": "I", "k": 0.0, "c": 1.0}}),
            _w("w1", [[-0.12, 0.03, -0.12], [0.08, 0.03, -0.08]]),
            _w("w2", [[-0.12, 0.03, -0.1], [0.08, 0.03, -0.02]], "black"),
        ],
        knobs=[knob("Vg", "Accelerating voltage", "Vg", 0, 32, 0.1, 0, "V"),
               knob("Ue", "Gas in the tube (its excitation potential is hidden)", "Ue", 3, 25, 0.1, 4.9, "V",
                    hidden=True),
               knob("damp", "Vapour pressure (depth of the dips)", "damp", 0.4, 0.95, 0.05, 0.85)],
        instruments=[inst("I", "readout", "Collector current", "I", k=1e9, unit="nA", lc=0.001, digits=3),
                     inst("V", "readout", "Accelerating voltage", "V", unit="V", lc=0.1, digits=1),
                     inst("gr", "graph", "Collector current against accelerating voltage", "I", k=1e9,
                          x="p.Vg", xlabel="V (V)")],
        steps=["Let the oven reach its working temperature, then set the accelerating voltage to zero.",
               "Raise the voltage in steps of 0.2 V and note the collector current each time.",
               "Mark the voltages of the current peaks.",
               "The difference between one peak and the next is the first excitation potential of the atom.",
               "Take the average of all the differences, or the slope of peak voltage against peak number."],
        theory="An electron that meets an atom can only give it energy in the exact amount of one of the atom's "
               "jumps. Below the first excitation energy every collision is elastic and the electron keeps its "
               "speed, so the collector current rises with the accelerating voltage. The moment an electron has "
               "gained the first excitation energy it can lose all of it in one collision, arrives at the grid "
               "too slow to climb the retarding voltage, and the current falls. A little further on it has "
               "enough energy for a second such collision, and the pattern repeats: the peaks are one "
               "excitation potential apart. The whole curve is shifted by the contact potential between the "
               "electrodes, which is why the first peak is not at the excitation potential itself and why only "
               "the SPACING may be used.",
        safety="The oven and the tube get hot: do not touch them. Keep the accelerating voltage below the "
               "maximum marked on the tube, or it strikes a continuous discharge and is ruined.",
        tour=[{"say": "The tube in its oven on the left, the control unit on the right: one knob sweeps the accelerating voltage."},
              {"set": {"Vg": 6.4}, "say": "The first peak: the electrons reach the grid with their full energy."},
              {"set": {"Vg": 8.9}, "say": "A little higher and the current has fallen: the electrons are losing their energy to the atoms."},
              {"set": {"Vg": 11.3}, "say": "The second peak, 4.9 volts after the first. That spacing is the first excitation potential."}],
        questions=[{"q": "Why does the collector current fall after each peak?", "options": [
            "The electrons lose all their energy in an inelastic collision", "The tube runs out of electrons",
            "The oven cools down"], "answer": 0,
            "why": "At that energy the atom can take the whole of it in one jump."},
            {"q": "The first peak is not at the excitation potential itself because of", "options": [
                "The contact potential between the electrodes", "The oven temperature", "The retarding voltage only"],
             "answer": 0, "why": "The contact potential shifts the whole curve, so only the spacing of the peaks is used."}],
        sources=[UGC, SIM,
                 {"title": "NIST Atomic Spectra Database: mercury 6s6p 3P1 level at 4.887 eV (the 253.7 nm "
                           "resonance line), the first excitation potential of mercury"}],
        check={"params": {"Vg": 10.0}, "reading": "spacing", "textbook": "fh_spacing"},
    )


# ==================================================================================== hydrogen spectrum (grating)
def hydrogen_balmer() -> dict:
    return lab(
        id="hydrogen-balmer-grating", rig="grating-spectrometer",
        title="Balmer lines of hydrogen and the Rydberg constant", group="Physics · Modern Physics",
        level="B.Sc.", topic="Elements of Modern Physics", chapter="Modern and atomic physics",
        aim="Measure the diffraction angles of the Balmer lines of hydrogen with a plane grating on a "
            "spectrometer, find their wavelengths and work out the Rydberg constant.",
        kernel="grating", params={"Nl": 600000.0, "order": 1.0, "nq": 3.0, "nl": 2.0, "Rh": 10967758.3},
        autorun=True, camera={"pos": [0.0, 0.8, 0.9], "look": [0, 0.04, -0.1]}, floor=-0.03,
        bodies=[
            board(1.0, 0.7),
            B("circle", "cylinder", name="Spectrometer circle", info="A divided circle with a vernier: the "
              "telescope's angle is read on it to one minute of arc.", r=0.17, h=0.016,
              pos=[0.0, 0.008, -0.1], color="#3b4048"),
            B("dvd", "cylinder", r=0.165, h=0.002, pos=[0.0, 0.017, -0.1], color="brass"),
            B("grat", "box", name="Plane transmission grating", info="600 rulings per millimetre on glass, "
              "upright at the centre of the circle and square to the collimator.", size=[0.05, 0.05, 0.004],
              pos=[0.0, 0.045, -0.1], color="glass", opacity=0.5),
            B("gstand", "cylinder", r=0.008, h=0.03, pos=[0.0, 0.03, -0.1], color="steel"),
            B("coll", "cylinder", name="Collimator", info="Makes a parallel beam from the slit in front of the "
              "discharge tube.", r=0.022, h=0.22, pos=[0.0, 0.055, 0.04], rot=[1.5708, 0, 0], color="#4a4f57"),
            B("tele", "cylinder", name="Telescope", info="Swung round the circle to find each line; the "
              "cross-wires are set on the line and the angle read off.", r=0.022, h=0.22,
              pos=[0.14, 0.055, -0.24], rot=[1.5708, 0.6, 0], color="#4a4f57"),
            B("tube", "cylinder", name="Hydrogen discharge tube", info="Hydrogen at low pressure glows pink: "
              "its light is the Balmer series.", r=0.012, h=0.14, pos=[0.0, 0.06, 0.2], rot=[1.5708, 0, 0],
              color="#e0618a"),
            B("hv", "box", name="High-voltage supply", info="Runs the discharge tube; never touched while on.",
              size=[0.16, 0.08, 0.1], pos=[-0.34, 0.04, 0.16], color="#2b2f36"),
            B("lens", "lens", name="Telescope objective", r=0.02, thick=0.006, pos=[0.14, 0.055, -0.3],
              color="glass", opacity=0.6),
            _w("w1", [[-0.26, 0.03, 0.16], [-0.01, 0.03, 0.2]], "black"),
        ],
        knobs=[knob("nq", "Balmer line (upper level n)", "nq", 3, 7, 1, 3),
               knob("order", "Order of the spectrum", "order", 1, 2, 1, 1),
               knob("Nl", "Grating (rulings per mm)", "Nl", 100, 1200, 100, 600, "/mm", 1000.0),
               knob("Rh", "This hydrogen tube (its Rydberg constant is hidden)", "Rh", 1.0e7, 1.2e7, 1000.0,
                    10967758.3, "1/m", hidden=True)],
        instruments=[inst("th", "readout", "Diffraction angle", "theta", k=R2D, unit="°", lc=0.0167, digits=3),
                     inst("lam", "readout", "Wavelength from the grating equation", "lam", k=1e9, unit="nm",
                          digits=2)],
        steps=["Level the spectrometer, focus the telescope on the slit and set the grating square to the beam.",
               "Read the direct angle with the telescope straight through, then swing it to the red Hα line.",
               "Set the cross-wires on the line and read the angle on both verniers.",
               "Repeat for the blue-green Hβ, the violet Hγ and the faint Hδ line.",
               "Work out each wavelength from sin θ = mλN, then the Rydberg constant from 1/λ = R(1/4 − 1/n²)."],
        theory="Hydrogen's visible lines are the Balmer series: an electron falling from level n to level 2 "
               "gives out a photon of wavenumber 1/λ = R(1/2² − 1/n²), with R the Rydberg constant of hydrogen. "
               "A plane transmission grating of N rulings per metre sends light of wavelength λ into the "
               "direction sin θ = mλN for the m-th order, so reading θ on the spectrometer circle gives λ "
               "directly, with no need for a standard lamp. Each line gives its own value of R and they are "
               "averaged. The angles must be read on both verniers and the direct reading subtracted, because "
               "the circle's zero is not the straight-through direction.",
        safety="The discharge tube runs on a few kilovolts: switch the supply off before touching any lead, and "
               "do not stare into the tube for long.",
        tour=[{"say": "A spectrometer with a 600 line per millimetre grating at the centre and a hydrogen tube behind the slit."},
              {"say": "The telescope is swung round until the red Hα line sits on the cross-wires; its angle is read on the circle.", "set": {"nq": 3}},
              {"set": {"nq": 4}, "say": "The blue-green Hβ line is at a smaller angle: a shorter wavelength is bent less."},
              {"set": {"order": 2}, "say": "In the second order the same line comes out at a much larger angle, so it can be read more accurately."}],
        questions=[{"q": "In the grating equation sin θ = mλN, a longer wavelength is", "options": [
            "Bent through a larger angle", "Bent through a smaller angle", "Not bent at all"], "answer": 0,
            "why": "sin θ is proportional to λ."},
            {"q": "The Balmer series are the jumps that end on", "options": ["n = 2", "n = 1", "n = 3"],
             "answer": 0, "why": "1/λ = R(1/2² − 1/n²)."}],
        sources=[UGC, SIM,
                 {"title": "CODATA 2018: Rydberg constant R∞ = 1.0973731568160e7 /m; for hydrogen itself "
                           "R_H = R∞/(1 + mₑ/m_p) = 1.09677583e7 /m"},
                 {"title": "NIST Atomic Spectra Database: hydrogen Balmer lines Hα 656.28, Hβ 486.13, "
                           "Hγ 434.05 and Hδ 410.17 nm"}],
        check={"params": {"nq": 3.0}, "reading": "lam", "textbook": "balmer_lam"},
    )


# ==================================================================================== GM tube: plateau
_GM_BODIES = [
    board(1.1, 0.7),
    B("stand", "box", name="Source stand", info="Shelves at set distances below the tube, so the geometry never "
      "changes between readings.", size=[0.12, 0.2, 0.12], pos=[-0.1, 0.1, -0.14], color="#3b4048"),
    B("tube", "cylinder", name="GM tube", info="An end-window Geiger-Muller tube in its holder. Each particle "
      "that gets in starts an avalanche and the counter records one count.", r=0.018, h=0.1,
      pos=[-0.1, 0.25, -0.14], color="#8c949e"),
    B("win", "cylinder", name="Mica end window", r=0.016, h=0.002, pos=[-0.1, 0.199, -0.14], color="#cfd6de"),
    B("shelf", "box", name="Source shelf", size=[0.1, 0.004, 0.1], pos=[-0.1, 0.12, -0.14], color="#565c66"),
    B("src", "cylinder", name="Sealed check source", info="A sealed disc source in its holder, moved only with "
      "tongs and kept in its lead store when not in use.", r=0.012, h=0.006, pos=[-0.1, 0.125, -0.14],
      color="#c0392b"),
    B("shield", "box", name="Lead shield", info="Stands between the bench and the student while the source is "
      "out of its store.", size=[0.14, 0.12, 0.02], pos=[-0.1, 0.06, 0.02], color="#4a4a52"),
    B("tongs", "box", name="Source tongs", size=[0.16, 0.008, 0.012], pos=[0.0, 0.004, 0.2], color="steel"),
    B("count", "box", name="Counter and timer", info="Sets the tube voltage, counts for a chosen time and holds "
      "the count.", size=[0.3, 0.1, 0.2], pos=[0.3, 0.05, -0.06], color="#2b2f36"),
    B("cface", "box", size=[0.26, 0.002, 0.16], pos=[0.3, 0.101, -0.06], color="white"),
    B("cdisp", "box", name="Count display", size=[0.12, 0.003, 0.05], pos=[0.3, 0.103, -0.12], color="#9eab8b",
      bind={"sx": {"var": "rate", "k": 0.0, "c": 1.0}}),
    B("vknob", "cylinder", name="Tube voltage knob", r=0.018, h=0.012, pos=[0.22, 0.107, -0.01], color="black"),
    B("tkey", "box", name="Start / stop key", size=[0.04, 0.012, 0.03], pos=[0.38, 0.107, -0.01], color="green"),
    B("coax", "wire", pts=[[-0.1, 0.03, -0.1], [0.05, 0.03, -0.04], [0.17, 0.03, -0.06]], r=0.003, color="black"),
]


def gm_plateau() -> dict:
    return lab(
        id="gm-plateau", rig="gm-plateau-bench",
        title="GM tube: operating voltage and plateau", group="Physics · Nuclear Physics", level="B.Sc.",
        topic="Radiation Safety and Nuclear Physics", chapter="Nuclear and radiation physics",
        aim="Raise the voltage of a Geiger-Muller tube in steps with a sealed source in place, plot the count "
            "rate against voltage, and choose the operating voltage from the plateau.",
        kernel="gmtube",
        params={"V": 300.0, "Vs": 330.0, "Vp": 650.0, "slope": 0.03, "rise": 25.0, "N0": 60.0, "bg": 0.5,
                "tau": 2.5e-4, "t": 30.0, "nrep": 3.0, "seed": 7.0},
        autorun=True, camera={"pos": [0.05, 0.8, 0.9], "look": [0.05, 0.1, -0.1]}, floor=-0.03,
        bodies=list(_GM_BODIES),
        knobs=[knob("V", "Tube voltage", "V", 250, 750, 10, 300, "V"),
               knob("t", "Counting time", "t", 10, 120, 10, 30, "s"),
               knob("Vs", "This tube (its starting voltage is hidden)", "Vs", 250, 500, 1, 330, "V", hidden=True)],
        instruments=[inst("r", "readout", "Count rate", "rate", unit="counts/s", lc=0.01, digits=2),
                     inst("n", "readout", "Counts in the counting time", "counts", unit="counts", digits=0),
                     inst("gr", "graph", "Count rate against tube voltage", "rate", x="p.V", xlabel="V (V)",
                          dots=True)],
        steps=["Put the sealed source on a shelf with the tongs, from behind the shield, and leave it there.",
               "Set the tube voltage low and raise it in steps of 20 V, counting for 30 s at each step.",
               "Note the voltage at which counts first appear: the starting voltage.",
               "Plot the count rate against voltage: a steep rise, then a long flat plateau.",
               "Set the working voltage about a third of the way along the plateau and never go past its end."],
        theory="A Geiger-Muller tube only counts once the voltage is high enough for one ion pair to start a "
               "full avalanche. Above that starting voltage almost every particle that enters is counted, so "
               "the count rate hardly changes with voltage: this is the plateau, and a good tube's plateau "
               "rises only two or three per cent per hundred volts. Past the end of the plateau the gas goes "
               "into continuous discharge and the rate runs away, which ruins the tube. The working voltage is "
               "chosen in the first third of the plateau, where the rate is steady and the tube is safe. Each "
               "count leaves the tube dead for a short time τ, so the true rate is N = N_obs/(1 − N_obs τ).",
        safety="Sealed source only. Move it with the tongs, from behind the lead shield, never with your "
               "fingers; keep it at arm's length, put it back in its locked store as soon as the readings are "
               "done, and wash your hands afterwards.",
        tour=[{"say": "A GM tube over a shelf stand, the sealed source on a shelf below it, and the counter with its timer."},
              {"set": {"V": 300}, "say": "At 300 volts nothing counts at all: the tube has not started."},
              {"set": {"V": 450}, "say": "On the plateau: a steady count rate."},
              {"set": {"V": 740}, "say": "Far past the plateau the rate runs away: this is continuous discharge, and it ruins the tube."}],
        questions=[{"q": "The operating voltage of a GM tube is chosen", "options": [
            "In the first third of the plateau", "Just above the starting voltage",
            "At the end of the plateau"], "answer": 0,
            "why": "There the count rate is steady and the tube is well clear of continuous discharge."},
            {"q": "A good GM plateau rises by about", "options": ["2-3 % per 100 V", "30 % per 100 V",
                                                                  "Nothing at all, exactly"], "answer": 0,
             "why": "A small slope is normal; a steep one means the tube is ageing."}],
        sources=[UGC, RAD_SAFE, SIM,
                 {"title": "G. F. Knoll, Radiation Detection and Measurement, ch. 7: the GM counting curve, "
                           "the plateau and dead time"}],
        check={"params": {"V": 450.0}, "reading": "rate_corr", "textbook": "gm_true_rate"},
    )


def gm_statistics() -> dict:
    return lab(
        id="gm-counting-statistics", rig="gm-statistics-bench",
        title="Counting statistics with a GM counter", group="Physics · Nuclear Physics", level="B.Sc.",
        topic="Radiation Safety and Nuclear Physics", chapter="Nuclear and radiation physics",
        aim="Take fifty counts of the same source for the same time, and show that they scatter about the mean "
            "with a standard deviation equal to the square root of the mean, as Poisson statistics demand.",
        kernel="gmtube",
        params={"V": 450.0, "Vs": 330.0, "Vp": 650.0, "slope": 0.03, "rise": 25.0, "N0": 9.5, "bg": 0.5,
                "tau": 2.5e-4, "t": 10.0, "nrep": 50.0, "seed": 23.0},
        autorun=True, camera={"pos": [0.05, 0.8, 0.9], "look": [0.05, 0.1, -0.1]}, floor=-0.03,
        bodies=list(_GM_BODIES),
        knobs=[knob("t", "Counting time", "t", 2, 60, 1, 10, "s"),
               knob("nrep", "Number of counts to take", "nrep", 10, 100, 5, 50),
               knob("V", "Tube voltage", "V", 350, 650, 10, 450, "V"),
               knob("N0", "This source (its true rate is hidden)", "N0", 2, 200, 0.5, 9.5, "counts/s",
                    hidden=True)],
        instruments=[inst("r", "readout", "Count rate", "rate", unit="counts/s", lc=0.01, digits=2),
                     inst("n", "readout", "Expected counts in the counting time", "counts", unit="counts",
                          digits=1),
                     inst("gr", "graph", "Count rate against tube voltage", "rate", x="p.V", xlabel="V (V)")],
        steps=["Set the tube to its operating voltage and put the source on a shelf with the tongs.",
               "Count for ten seconds, write the count down, and repeat fifty times without touching anything.",
               "Work out the mean of the fifty counts and their standard deviation.",
               "Compare the standard deviation with the square root of the mean.",
               "Group the counts into bins and see that the histogram follows a Poisson curve."],
        theory="Radioactive decay is random: each nucleus decays on its own, so the number of counts in a fixed "
               "time is a Poisson number. Its standard deviation is the square root of its mean, which is why "
               "a count of N has an uncertainty of √N and a fractional uncertainty of 1/√N: counting four times "
               "as long halves the error. For a mean above about twenty the Poisson distribution is already "
               "close to a Gaussian of the same width. Nothing in the apparatus changes between the readings, "
               "so all the scatter is the statistics of decay itself.",
        safety="Sealed source only, moved with tongs from behind the lead shield and returned to its locked "
               "store when the counting is over.",
        tour=[{"say": "The same source, the same shelf, the same counting time, over and over: only the statistics change."},
              {"set": {"t": 10}, "say": "Ten second counts of about a hundred: so a scatter of about ten counts is expected."},
              {"set": {"t": 40}, "say": "Four times as long: four times the counts, but only twice the scatter."}],
        questions=[{"q": "If a count of 400 is recorded, its standard deviation is about", "options": [
            "20", "400", "2"], "answer": 0, "why": "σ = √N = √400 = 20."},
            {"q": "Counting for four times as long makes the fractional error", "options": [
                "Half as big", "A quarter as big", "Four times as big"], "answer": 0,
             "why": "The fractional error is 1/√N, and N is four times larger."}],
        sources=[UGC, RAD_SAFE, SIM,
                 {"title": "G. F. Knoll, Radiation Detection and Measurement, ch. 3: counting statistics, "
                           "σ = √N for Poisson counts"}],
        check={"params": {"V": 450.0}, "reading": "rate_corr", "textbook": "gm_true_rate"},
    )


def gamma_attenuation() -> dict:
    return lab(
        id="gamma-attenuation", rig="gm-absorption-bench",
        title="Attenuation of gamma rays in aluminium", group="Physics · Nuclear Physics", level="B.Sc.",
        topic="Radiation Safety and Nuclear Physics", chapter="Nuclear and radiation physics",
        aim="Put aluminium sheets of known thickness between a sealed gamma source and a GM tube, and find the "
            "linear attenuation coefficient and the half-value thickness.",
        kernel="gmabsorb",
        params={"x": 0.0, "mu": 20.14, "N0": 80.0, "bg": 0.5, "tau": 2.5e-4, "t": 60.0, "seed": 11.0},
        autorun=True, camera={"pos": [0.05, 0.8, 0.9], "look": [0.05, 0.1, -0.1]}, floor=-0.03,
        bodies=list(_GM_BODIES) + [
            B("abs1", "box", name="Absorber sheets", info="Aluminium sheets of measured thickness, laid on the "
              "shelf between the source and the window.", size=[0.08, 0.004, 0.08], pos=[-0.1, 0.16, -0.14],
              color="#b8bec6", bind={"sy": {"var": "x_mm", "k": 0.08, "min": 0.05}}),
            B("abs2", "box", name="Absorber box", size=[0.1, 0.03, 0.1], pos=[0.14, 0.015, 0.14], color="wood"),
        ],
        knobs=[knob("x", "Absorber thickness", "x", 0, 60, 0.5, 0, "mm", 0.001),
               knob("t", "Counting time", "t", 30, 300, 10, 60, "s"),
               knob("mu", "This absorber (its attenuation coefficient is hidden)", "mu", 5, 400, 0.01, 20.14,
                    "1/m", hidden=True)],
        instruments=[inst("r", "readout", "Count rate with the absorber", "rate", unit="counts/s", lc=0.01,
                          digits=2),
                     inst("net", "readout", "Net rate above background", "net", unit="counts/s", digits=2),
                     inst("gr", "graph", "Net rate against absorber thickness", "net", x="p.x", xk=1000.0,
                          xlabel="x (mm)", dots=True)],
        steps=["Count the background for two minutes with the source still in its store.",
               "Bring the source out with the tongs, from behind the shield, and put it on its shelf.",
               "Count with no absorber, then with sheets of 2, 5, 10, 20, 30 and 40 mm of aluminium.",
               "Subtract the background from every count rate.",
               "Plot ln of the net rate against thickness: the slope is −μ, and the half-value thickness is "
               "ln2/μ."],
        theory="A narrow beam of gamma rays is not slowed down as it goes through matter: each photon is either "
               "scattered or absorbed, or passes untouched. The chance of being removed in a thin layer is the "
               "same everywhere, so the surviving rate falls exponentially: N = N₀ exp(−μx), where μ is the "
               "linear attenuation coefficient of the material at that photon energy. On a logarithmic plot "
               "that is a straight line of slope −μ, and the thickness that halves the beam is ln2/μ. The "
               "background must be taken off first, because it is not attenuated by the sheets. Gamma rays have "
               "no range: however much absorber is used, something always gets through.",
        safety="Sealed source only. Handle it with the tongs from behind the lead shield, keep your body behind "
               "the shield while counting, do not point the window at anyone, and return the source to its "
               "locked store as soon as the readings are finished.",
        tour=[{"say": "The sealed gamma source on its shelf, the GM tube above it, and a box of measured aluminium sheets."},
              {"set": {"x": 0}, "say": "With no absorber the net rate is the full beam."},
              {"set": {"x": 34.4}, "say": "About 34 millimetres of aluminium halves the rate: that is the half-value thickness."},
              {"set": {"x": 60}, "say": "Even with 60 millimetres of aluminium some gamma rays still get through: there is no range."}],
        questions=[{"q": "A plot of ln(net rate) against absorber thickness is", "options": [
            "A straight line of slope −μ", "A curve that ends at the range", "A horizontal line"], "answer": 0,
            "why": "N = N₀e^(−μx), so ln N falls linearly."},
            {"q": "The half-value thickness is", "options": ["ln2/μ", "1/μ", "2/μ"], "answer": 0,
             "why": "Setting N = N₀/2 in the attenuation law gives x = ln2/μ."}],
        sources=[UGC, RAD_SAFE, XCOM, NNDC, SIM],
        check={"reading": "x_half", "textbook": "gm_hvl"},
    )


def half_life() -> dict:
    return lab(
        id="short-half-life", rig="gm-halflife-bench",
        title="Half-life of a short-lived source", group="Physics · Nuclear Physics", level="B.Sc.",
        topic="Radiation Safety and Nuclear Physics", chapter="Nuclear and radiation physics",
        aim="Count a freshly activated short-lived source at regular intervals and find its half-life from the "
            "slope of the logarithm of the net count rate against time.",
        kernel="gmdecay",
        params={"t": 0.0, "T": 3257.4, "N0": 120.0, "bg": 0.5, "tau": 2.5e-4, "tc": 120.0, "seed": 13.0},
        autorun=True, camera={"pos": [0.05, 0.8, 0.9], "look": [0.05, 0.1, -0.1]}, floor=-0.03,
        bodies=list(_GM_BODIES) + [
            B("clock", "box", name="Laboratory clock", info="The counting intervals are timed from the moment "
              "the source is put in place.", size=[0.08, 0.08, 0.015], pos=[0.3, 0.22, -0.22], color="white"),
        ],
        knobs=[knob("t", "Time since the source was made", "t", 0, 20000, 10, 0, "s"),
               knob("tc", "Counting time per reading", "tc", 30, 300, 10, 120, "s"),
               knob("T", "This source (its half-life is hidden)", "T", 0.5, 120, 0.01, 54.29, "min", 60.0)],
        instruments=[inst("r", "readout", "Count rate", "rate", unit="counts/s", lc=0.01, digits=2),
                     inst("net", "readout", "Net rate above background", "net", unit="counts/s", digits=2),
                     inst("gr", "graph", "Net rate against time", "net", x="p.t", xlabel="t (s)", dots=True)],
        steps=["Count the background with the source still in its store.",
               "Put the freshly activated source on its shelf with the tongs and start the clock.",
               "Count for two minutes at a time, noting the middle time of each counting interval.",
               "Carry on for at least three half-lives.",
               "Subtract the background, plot ln of the net rate against time, and get the half-life from "
               "ln2 divided by the slope."],
        theory="Every nucleus of the same kind has the same chance of decaying in the next second, whatever has "
               "happened before, so the number left falls exponentially: N = N₀ exp(−λt), and the activity "
               "follows it. The half-life is the time in which half of them have gone, T = ln2/λ. A count rate "
               "measured over an interval is the average over that interval, so it is plotted against the "
               "middle of the interval. The background is not decaying and must be taken off first; readings "
               "are carried on for several half-lives, because a short run cannot tell an exponential from a "
               "straight line.",
        safety="Sealed source only, moved with tongs from behind the lead shield. A freshly activated source is "
               "at its most active in the first minutes: keep it at arm's length, behind the shield, and in its "
               "locked store once the count rate has fallen to the background.",
        tour=[{"say": "A short-lived source on the shelf, the GM tube above it, and the clock: counts are taken at fixed intervals."},
              {"set": {"t": 0}, "say": "At the start the net rate is at its highest."},
              {"set": {"t": 3257}, "say": "One half-life later the net rate has fallen to half."},
              {"set": {"t": 9772}, "say": "After three half-lives only an eighth is left."}],
        questions=[{"q": "In two half-lives the activity falls to", "options": ["A quarter", "A half", "Nothing"],
                    "answer": 0, "why": "Each half-life halves it: 1/2 × 1/2 = 1/4."},
                   {"q": "The count rate of an interval is plotted against", "options": [
                       "The middle of the interval", "Its start", "Its end"], "answer": 0,
                    "why": "The rate measured is the average over the interval."}],
        sources=[UGC, RAD_SAFE, NNDC, SIM],
        check={"reading": "t_half", "textbook": "decay_T"},
    )


# ==================================================================================== four-probe band gap
def four_probe() -> dict:
    return lab(
        id="four-probe-band-gap", rig="four-probe-bench",
        title="Four-probe resistivity and the band gap", group="Physics · Solid State Physics", level="B.Sc.",
        topic="Solid State Physics", chapter="Solid state physics and materials",
        aim="Measure the resistivity of a germanium slice by the four-probe method as it is heated in an oven, "
            "and find the band gap from the slope of ln ρ against 1/T.",
        kernel="fourprobe",
        params={"T": 300.0, "Eg": 0.67, "rho300": 0.46, "I": 0.002, "s": 0.002, "w": 0.0005},
        autorun=True, camera={"pos": [0.0, 0.75, 0.85], "look": [0, 0.06, -0.1]}, floor=-0.03,
        bodies=[
            board(1.0, 0.6),
            B("oven", "box", name="Oven", info="A small furnace with the probe head inside it; the thermometer "
              "sits beside the sample.", size=[0.24, 0.16, 0.2], pos=[-0.24, 0.08, -0.1], color="#4a4f57"),
            B("ovlid", "box", size=[0.26, 0.012, 0.22], pos=[-0.24, 0.166, -0.1], color="#3b4048"),
            B("slice", "box", name="Germanium slice", info="A thin slice of germanium, 0.5 mm thick, on the "
              "probe stage.", size=[0.04, 0.0015, 0.04], pos=[-0.24, 0.08, -0.1], color="#6e747c"),
            B("p1", "cylinder", name="Four probes", info="Four spring-loaded probes 2 mm apart in a line: "
              "current through the outer pair, voltage across the inner pair.", r=0.0012, h=0.05,
              pos=[-0.27, 0.105, -0.1], color="steel"),
            B("p2", "cylinder", r=0.0012, h=0.05, pos=[-0.25, 0.105, -0.1], color="steel"),
            B("p3", "cylinder", r=0.0012, h=0.05, pos=[-0.23, 0.105, -0.1], color="steel"),
            B("p4", "cylinder", r=0.0012, h=0.05, pos=[-0.21, 0.105, -0.1], color="steel"),
            B("therm", "cylinder", name="Thermometer", info="Reads the sample's temperature; readings are taken "
              "only while it is steady.", r=0.004, h=0.14, pos=[-0.12, 0.09, -0.1], color="glass", opacity=0.6),
            *_lcd("csrc", 0.12, -0.12, "Constant-current source",
                  "Holds the probe current steady at 2 mA whatever the sample's resistance does.", "T"),
            *_lcd("dvm", 0.38, -0.12, "Digital voltmeter",
                  "Reads the millivolts between the two inner probes.", "V"),
            B("ovctl", "box", name="Oven controller", info="Sets the oven temperature; the sample is left to "
              "settle at each step.", size=[0.16, 0.07, 0.12], pos=[0.26, 0.035, 0.14], color="#2b2f36"),
            _w("w1", [[-0.2, 0.05, -0.1], [0.04, 0.03, -0.12]]),
            _w("w2", [[-0.28, 0.05, -0.1], [0.0, 0.03, -0.18]], "black"),
            _w("w3", [[-0.24, 0.05, -0.08], [0.3, 0.03, -0.12]], "gold"),
            _w("w4", [[-0.26, 0.05, -0.08], [0.32, 0.03, -0.18]], "blue"),
        ],
        knobs=[knob("T", "Oven temperature", "T", 300, 450, 1, 300, "K"),
               knob("I", "Probe current", "I", 0.5, 10, 0.5, 2, "mA", 0.001),
               knob("w", "Slice thickness", "w", 0.2, 1.0, 0.05, 0.5, "mm", 0.001),
               knob("Eg", "This sample (its band gap is hidden)", "Eg", 0.3, 1.6, 0.01, 0.67, "eV", hidden=True)],
        instruments=[inst("V", "readout", "Voltage between the inner probes", "V", k=1000, unit="mV", lc=0.1,
                          digits=1),
                     inst("rho", "readout", "Resistivity", "rho", k=100, unit="Ω·cm", digits=3),
                     inst("gr", "graph", "Resistivity against temperature", "rho", k=100, x="p.T",
                          xlabel="T (K)", dots=True)],
        steps=["Set the four probes down on the germanium slice and pass 2 mA through the outer pair.",
               "Read the voltage between the inner probes at room temperature.",
               "Raise the oven in steps of about 10 K, waiting at each step for the thermometer to settle.",
               "Work out the resistivity at each temperature from ρ = π w V / (ln2 · I).",
               "Plot ln ρ against 1/T: the slope is Eg/2k, so the band gap is twice k times the slope."],
        theory="In an intrinsic semiconductor the number of carriers goes as exp(−Eg/2kT), so the resistivity "
               "falls steeply as the sample is heated: ln ρ against 1/T is a straight line of slope Eg/2k. The "
               "four-probe method keeps the contact resistance out of the answer, because the current goes "
               "through the outer probes while the voltage is read between the inner two, which carry almost no "
               "current. For a slice much thinner than the probe spacing the geometry correction "
               "G₇(w/s) = (2s/w)ln2 turns the infinite-medium result 2πs(V/I) into ρ = πwV/(ln2·I). The current "
               "is kept small so that the sample does not heat itself.",
        safety="The oven and the probe head stay hot long after the heater is switched off: handle them with the "
               "tongs. Do not press the probes down hard on the slice, which is brittle.",
        tour=[{"say": "A germanium slice under four probes inside a small oven, with a constant-current source and a digital voltmeter."},
              {"set": {"T": 300}, "say": "At room temperature the probe voltage is a few hundred millivolts."},
              {"set": {"T": 400}, "say": "A hundred degrees hotter and the voltage has fallen many times over: far more carriers are free."}],
        questions=[{"q": "As an intrinsic semiconductor is heated, its resistivity", "options": [
            "Falls steeply", "Rises steeply", "Does not change"], "answer": 0,
            "why": "The carrier number goes as exp(−Eg/2kT), so heating frees many more carriers."},
            {"q": "The four-probe method is used because", "options": [
                "It keeps the contact resistance out of the answer", "It needs no current",
                "It works only on metals"], "answer": 0,
             "why": "The voltage probes carry almost no current, so their contact resistance drops no voltage."}],
        sources=[UGC, CRC_SEMI, SIM,
                 {"title": "L. B. Valdes, 'Resistivity measurements on germanium for transistors', Proc. IRE 42 "
                           "(1954) 420: the four-probe geometry correction G₇(w/s)"}],
        check={"params": {"T": 350.0}, "reading": "rho", "textbook": "fourprobe_rho"},
    )


# ==================================================================================== Hall effect
def hall_effect() -> dict:
    return lab(
        id="hall-effect", rig="hall-effect-bench",
        title="Hall coefficient of a semiconductor", group="Physics · Solid State Physics", level="B.Sc.",
        topic="Solid State Physics", chapter="Solid state physics and materials",
        aim="Measure the Hall voltage of a germanium crystal against the magnetic field and the current, and "
            "find the Hall coefficient, the sign of the carriers and their number per cubic metre.",
        kernel="hallbar",
        params={"B": 0.0, "I": 0.005, "th": 0.0005, "n21": 2.0, "sg": -1.0, "rho": 0.02, "wid": 0.004},
        autorun=True, camera={"pos": [0.0, 0.7, 0.85], "look": [0, 0.06, -0.08]}, floor=-0.03,
        bodies=[
            board(1.0, 0.6),
            B("yoke", "box", name="Electromagnet", info="An iron yoke with two coils; the crystal sits in the "
              "gap between its flat poles.", size=[0.26, 0.18, 0.1], pos=[-0.2, 0.09, -0.12], color="#3b4048"),
            B("coil1", "cylinder", name="Field coils", r=0.045, h=0.05, pos=[-0.3, 0.1, -0.12],
              rot=[0, 0, 1.5708], color="copper"),
            B("coil2", "cylinder", r=0.045, h=0.05, pos=[-0.1, 0.1, -0.12], rot=[0, 0, 1.5708], color="copper"),
            B("gap", "box", name="Pole gap", size=[0.03, 0.05, 0.05], pos=[-0.2, 0.1, -0.12], color="#8c949e",
              opacity=0.4),
            B("probe", "box", name="Hall probe board", info="The germanium crystal on a thin board, with four "
              "soldered leads: two for the current, two across the width for the Hall voltage.",
              size=[0.02, 0.003, 0.05], pos=[-0.2, 0.1, -0.12], color="#1f6b3a"),
            B("xtal", "box", name="Germanium crystal", info="A thin crystal 0.5 mm thick. The current goes "
              "along it and the field across it, so the Hall voltage appears across its width.",
              size=[0.01, 0.0008, 0.016], pos=[-0.2, 0.103, -0.12], color="#6e747c"),
            *_lcd("gauss", 0.1, -0.14, "Digital gaussmeter",
                  "A separate Hall probe in the same gap reads the field in the gap in tesla.", "B"),
            *_lcd("hvm", 0.36, -0.14, "Hall voltmeter",
                  "Reads the millivolts across the crystal's width.", "Vh"),
            B("csrc", "box", name="Constant-current source", info="Holds the crystal current steady in "
              "milliamperes.", size=[0.16, 0.07, 0.12], pos=[0.14, 0.035, 0.14], color="#2b2f36"),
            B("magsup", "box", name="Magnet supply", info="Sets the coil current, and so the field in the gap.",
              size=[0.18, 0.08, 0.12], pos=[-0.3, 0.04, 0.16], color="#3a4f6e"),
            _w("w1", [[-0.22, 0.1, -0.09], [0.06, 0.03, 0.14]]),
            _w("w2", [[-0.18, 0.1, -0.09], [0.2, 0.03, 0.14]], "black"),
            _w("w3", [[-0.2, 0.1, -0.1], [0.3, 0.03, -0.14]], "gold"),
            _w("w4", [[-0.2, 0.1, -0.14], [0.4, 0.03, -0.14]], "blue"),
            _w("w5", [[-0.3, 0.05, 0.1], [-0.25, 0.05, -0.08]], "green"),
        ],
        knobs=[knob("B", "Magnetic field in the gap", "B", 0, 0.6, 0.01, 0, "T"),
               knob("I", "Crystal current", "I", 1, 10, 0.5, 5, "mA", 0.001),
               knob("th", "Crystal thickness", "th", 0.2, 1.0, 0.05, 0.5, "mm", 0.001),
               knob("n21", "This crystal (its carrier number is hidden)", "n21", 0.01, 100, 0.01, 2.0,
                    "10²¹/m³", hidden=True)],
        instruments=[inst("Vh", "readout", "Hall voltage", "Vh", k=1000, unit="mV", lc=0.01, digits=2),
                     inst("RH", "readout", "Hall coefficient", "RH", unit="m³/C", digits=4),
                     inst("gr", "graph", "Hall voltage against magnetic field", "Vh", k=1000, x="p.B",
                          xlabel="B (T)", dots=True)],
        steps=["Put the crystal board in the pole gap, square to the field, and pass 5 mA along the crystal.",
               "With the magnet off, note the small voltage across the Hall leads and take it off every reading.",
               "Raise the field in steps and read the Hall voltage at each step.",
               "Plot the Hall voltage against the field: the slope is I/(n e t).",
               "Work out the Hall coefficient, read the sign to see whether the carriers are electrons or "
               "holes, and get their number per cubic metre."],
        theory="A current in a magnetic field has its carriers pushed sideways, and they pile up on one face "
               "until the transverse electric field they build up balances the magnetic force. That is the Hall "
               "voltage V_H = IB/(n e t), with t the thickness along the field and n the carrier number per "
               "cubic metre. Its SIGN tells which kind of carrier is moving, which is the only simple "
               "experiment that does: electrons and holes are pushed to opposite faces. The Hall coefficient "
               "R_H = V_H t/(IB) = ±1/(ne), and with the resistivity of the same crystal the mobility follows "
               "as µ = |R_H|/ρ. The small zero-field voltage is a misalignment of the contacts and is "
               "subtracted.",
        safety="The magnet coils get warm: do not leave them at full current. Keep the crystal board flat in "
               "the gap and never force the poles together on it.",
        tour=[{"say": "The germanium crystal on its board sits in the gap of the electromagnet, current along it and field across it."},
              {"set": {"B": 0}, "say": "With no field there is almost no voltage across the width."},
              {"set": {"B": 0.3}, "say": "At 0.3 tesla the Hall voltage is tens of millivolts, and it grows in step with the field."},
              {"set": {"I": 10}, "say": "Twice the current, twice the Hall voltage: V_H is proportional to both I and B."}],
        questions=[{"q": "The sign of the Hall voltage tells you", "options": [
            "Whether the carriers are electrons or holes", "The thickness of the crystal",
            "The size of the field"], "answer": 0,
            "why": "Electrons and holes are pushed to opposite faces, so the sign of V_H reverses with them."},
            {"q": "The Hall coefficient of a sample with more carriers is", "options": [
                "Smaller", "Larger", "Unchanged"], "answer": 0, "why": "R_H = 1/(ne)."}],
        sources=[UGC, CRC_SEMI, SIM],
        check={"params": {"B": 0.3}, "reading": "Vh", "textbook": "hall_vh"},
    )


# ==================================================================================== UV-visible spectrum of a colloid
def gold_colloid() -> dict:
    return lab(
        id="gold-colloid-uv-vis", rig="uv-vis-bench",
        title="Gold nanoparticles: plasmon band and particle size", group="Physics · Nanomaterials",
        level="B.Sc.", topic="Nano Materials and Applications", chapter="Nanomaterials",
        aim="Record the UV-visible absorption spectrum of a gold colloid, find the surface plasmon peak, and "
            "work out the particle diameter from the published absorbance-ratio relation.",
        kernel="colloid", params={"d": 20.0, "conc": 1.0, "lam": 4.5e-7, "A450": 0.5, "wid": 60.0,
                                  "bgdecay": 120.0},
        autorun=True, camera={"pos": [0.0, 0.65, 0.8], "look": [0, 0.05, -0.08]}, floor=-0.03,
        bodies=[
            board(1.0, 0.6),
            B("spec", "box", name="UV-visible spectrophotometer", info="A double-beam instrument: a lamp, a "
              "grating monochromator, the cuvette holder and a detector.", size=[0.4, 0.14, 0.26],
              pos=[-0.12, 0.07, -0.12], color="#e4e0d6"),
            B("lid", "box", name="Sample compartment lid", size=[0.14, 0.012, 0.12], pos=[-0.02, 0.141, -0.12],
              color="#2b2f36"),
            B("cuv", "box", name="Quartz cuvette", info="A 10 mm path-length cuvette holding the colloid; a "
              "matching cuvette of water is the blank.", size=[0.012, 0.045, 0.012], pos=[-0.02, 0.09, -0.12],
              color="glass", opacity=0.5),
            B("liq", "box", name="Gold colloid", info="A clear red colloid of gold spheres in water. Its colour "
              "comes from the plasmon band in the green.", size=[0.01, 0.03, 0.01], pos=[-0.02, 0.083, -0.12],
              color="#b2353a"),
            B("blank", "box", name="Blank cuvette", size=[0.012, 0.045, 0.012], pos=[-0.06, 0.09, -0.12],
              color="glass", opacity=0.4),
            B("screen", "box", name="Spectrum display", info="Draws the absorbance against wavelength as the "
              "instrument scans.", size=[0.16, 0.1, 0.01], pos=[-0.12, 0.19, -0.22], color="#1b2116",
              bind={"sx": {"var": "A", "k": 0.0, "c": 1.0}}),
            B("vials", "cylinder", name="Colloid vials", info="Vials of colloid made with different amounts of "
              "citrate, which set the particle size.", r=0.012, h=0.05, pos=[0.28, 0.025, 0.1],
              color="#b2353a"),
            B("pip", "cylinder", name="Pipette", r=0.004, h=0.14, pos=[0.18, 0.004, 0.18], rot=[0, 0, 1.5708],
              color="glass", opacity=0.6),
            B("stand", "box", name="Vial stand", size=[0.1, 0.02, 0.06], pos=[0.28, 0.01, 0.1], color="wood"),
            B("pc", "box", name="Instrument computer", info="Records the scan and reads the absorbance at any "
              "wavelength.", size=[0.2, 0.12, 0.02], pos=[0.26, 0.06, -0.2], color="#2b2f36"),
        ],
        knobs=[knob("lam", "Wavelength", "lam", 400, 750, 1, 450, "nm", 1e-9),
               knob("conc", "Dilution (how much colloid in the cuvette)", "conc", 0.2, 1.5, 0.05, 1.0),
               knob("d", "This colloid (its particle diameter is hidden)", "d", 5, 100, 0.1, 20, "nm",
                    hidden=True)],
        instruments=[inst("A", "readout", "Absorbance at this wavelength", "A", unit="", lc=0.001, digits=3),
                     inst("lp", "readout", "Plasmon peak of this colloid", "lam_spr", unit="nm", digits=1),
                     inst("gr", "graph", "Absorbance against wavelength", "A", x="p.lam", xk=1e9,
                          xlabel="λ (nm)")],
        steps=["Put the blank cuvette of water in the reference beam and zero the instrument.",
               "Put the colloid in the sample cuvette and scan from 400 to 750 nm.",
               "Read the wavelength of the plasmon peak and the absorbance there.",
               "Read the absorbance at 450 nm as well.",
               "Work out the diameter from d = exp(3.00 A_spr/A₄₅₀ − 2.20), and check it against the peak "
               "position."],
        theory="The free electrons of a gold sphere much smaller than the wavelength of light can be driven "
               "together by the light's field, and at one frequency they resonate: the surface plasmon "
               "resonance, which for gold in water lies near 520 nm and is what makes a gold colloid red. Both "
               "the position of that band and its height above the absorbance at 450 nm grow with the particle "
               "size, and Haiss and co-workers fitted both to measured sizes: "
               "λ_spr = 512 + 6.53 exp(0.0216 d) and d = exp(3.00 A_spr/A₄₅₀ − 2.20), with d in nanometres. "
               "The ratio is used rather than the absorbance itself because the ratio does not depend on how "
               "much colloid is in the cuvette. Said plainly: this is an empirical relation fitted to spherical "
               "citrate-capped gold between about 5 and 100 nm. It is not a size measurement of the kind an "
               "electron microscope gives, it says nothing about the spread of sizes, and it must not be used "
               "for silver, for rods or for coated particles.",
        safety="Gold colloid is handled with gloves and a pipette filler; never pipette by mouth. Wipe the "
               "cuvette's clear faces with lens tissue only, and keep the lid closed while the lamp is on.",
        tour=[{"say": "A UV-visible spectrophotometer with the colloid in a 10 mm cuvette and water as the blank."},
              {"set": {"lam": 522}, "say": "At the plasmon peak near 520 nanometres the absorbance is at its highest: this is why the colloid looks red."},
              {"set": {"lam": 450}, "say": "At 450 nanometres the absorbance is much lower. The ratio of the two is what gives the size."},
              {"set": {"d": 80}, "say": "A colloid of 80 nanometre spheres: the peak has moved well to the red and the ratio is larger."}],
        questions=[{"q": "Why is the ratio A_spr/A₄₅₀ used rather than A_spr itself?", "options": [
            "The ratio does not depend on how much colloid is in the cuvette",
            "A_spr cannot be measured", "450 nm is the peak"], "answer": 0,
            "why": "Both absorbances scale with concentration, so their ratio does not."},
            {"q": "As gold spheres are made larger, the plasmon peak", "options": [
                "Moves to longer wavelengths", "Moves to shorter wavelengths", "Stays where it is"], "answer": 0,
             "why": "λ_spr = 512 + 6.53 exp(0.0216 d): it red-shifts with size."}],
        sources=[UGC, HAISS, SIM],
        check={"reading": "d_est", "textbook": "colloid_d"},
    )


BUILDERS = (photoelectric, led_planck, franck_hertz, hydrogen_balmer, gm_plateau, gm_statistics,
            gamma_attenuation, half_life, four_probe, hall_effect, gold_colloid)
