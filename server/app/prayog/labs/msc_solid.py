"""Lab pack `msc_solid`: M.Sc. physics benches for solid state, materials characterisation, vacuum and plasma
(see `labs/__init__.py`). The physics is in `packs/msc_solid.py` (and its JavaScript twin); every lab names the studio
RIG that draws the real bench, and each carries a `check` that lands within 1 % of its textbook formula.

Said plainly in every lab: the numbers are the lab's own simulation of the textbook law, not a real crystal; samples
named in a family file carry a real, sourced constant, samples marked "illustrative" carry a value chosen for the lab.
"""
from __future__ import annotations

from ..catalog import B, SIM, board, inst, knob, lab

SSP = "Physics · Solid State Physics"
MATS = "Physics · Materials Physics"
VAC = "Physics · Vacuum and Plasma Physics"
CH_SS = "Solid state and materials"
CH_MS = "Materials synthesis and characterisation"
CH_VP = "Vacuum, low temperature and plasma"

PGLAB = {"title": "M.Sc. Physics advanced laboratory courses (typical university practical lists: solid state, "
                  "materials, vacuum and plasma physics)"}
KITTEL = {"title": "C. Kittel, Introduction to Solid State Physics, 8th ed. (Wiley, 2005)"}
ASHCROFT = {"title": "N. W. Ashcroft and N. D. Mermin, Solid State Physics (Saunders, 1976)"}
CODATA = {"title": "CODATA / SI 2019 defining constants (k, e, h) and CODATA 2018 electron mass and atomic mass unit"}
CULLITY = {"title": "B. D. Cullity and S. R. Stock, Elements of X-ray Diffraction, 3rd ed. (Prentice Hall, 2001)"}
CHAMBERS = {"title": "A. Chambers, Modern Vacuum Physics (CRC Press, 2005)"}
LIEBERMAN = {"title": "M. A. Lieberman and A. J. Lichtenberg, Principles of Plasma Discharges and Materials "
                      "Processing, 2nd ed. (Wiley, 2005), chapter 6"}
ILLUS = {"title": "Illustrative sample", "note": "its hidden value is chosen for this lab, not taken from a named material"}
MODEL = {"title": "Hoola Prayogshala model", "note": "a simulation of the textbook law, checked against its closed "
                                                   "formula in Hoola's tests; not a measurement of a real crystal"}


def _bench(extra: list[dict] | None = None, w: float = 1.0) -> list[dict]:
    return [board(w, 0.6),
            B("ctl", "box", name="Control box", info="Sets and reads the control variable of the run.",
              size=[0.2, 0.07, 0.13], pos=[0.3, 0.035, 0.12], color="#2b2f36"),
            B("dvm", "box", name="Digital meter", info="Reads the response of the sample.",
              size=[0.2, 0.07, 0.13], pos=[0.3, 0.035, -0.1], color="#2b2f36")] + (extra or [])


def _mk(id: str, rig: str, title: str, aim: str, kernel: str, params: dict, knobs: list, insts: list, steps: list,
        theory: str, safety: str, tour: list, questions: list, sources: list, check: dict, group: str = SSP,
        chapter: str = CH_SS, topic: str = "Advanced laboratory", extra: list | None = None) -> dict:
    return lab(id=id, rig=rig, title=title, group=group, level="M.Sc.", topic=topic, chapter=chapter, aim=aim,
               kernel=kernel, params=params, autorun=True, camera={"pos": [0.0, 0.7, 0.9], "look": [0, 0.04, -0.05]},
               floor=-0.03, bodies=_bench(extra), knobs=knobs, instruments=insts, steps=steps, theory=theory,
               safety=safety, tour=tour, questions=questions, sources=sources + [SIM], check=check)


def _q(q: str, opts: list[str], ans: int, why: str) -> dict:
    return {"q": q, "options": opts, "answer": ans, "why": why}


# ====================================================================================== transport and phase transitions
def metal_conductivity_t() -> dict:
    return _mk(
        "metal-conductivity-t", "msc-sweep-bench", "Electrical resistance of a metal against temperature",
        "Heat a coil of copper wire in an oven, measure its resistance at a series of temperatures and find the "
        "temperature coefficient of resistance from the straight line R against T.",
        "msc_metal", {"T": 293.0, "R0": 1.2, "alpha": 0.0039, "Tref": 293.0, "I": 0.01},
        [knob("T", "Oven temperature", "T", 293, 400, 1, 293, "K"),
         knob("alpha", "This metal (its coefficient is hidden)", "alpha", 0.0003, 0.007, 0.00001, 0.0039, "1/K", hidden=True)],
        [inst("R", "readout", "Coil resistance", "R", unit="Ω", lc=0.001, digits=3),
         inst("gr", "graph", "Resistance against temperature", "R", x="p.T", xlabel="T (K)", dots=True)],
        ["Connect the coil to the four-wire ohmmeter and put it in the oven with the thermometer beside it.",
         "Read the resistance at room temperature.",
         "Raise the oven in steps of about 15 K, waiting at each step for the thermometer to settle.",
         "Plot R against T: it is a straight line.",
         "The temperature coefficient is the slope divided by the resistance at the reference temperature."],
        "Between about 250 K and 500 K the resistance of a pure metal grows linearly with temperature, "
        "R = R0[1 + α(T − T0)], because the lattice vibrations scatter the conduction electrons more strongly as they "
        "get larger. α is the temperature coefficient of resistance. The line is fitted over all the readings, and "
        "α = slope / R(T0), where R(T0) is the fitted value at the reference temperature, not a single reading.",
        "The oven stays hot long after it is switched off. Do not touch the coil or the oven wall, and let the oven "
        "cool before opening it.",
        [{"say": "A coil of insulated copper wire on a former, an oven, and a four-wire ohmmeter."},
         {"set": {"T": 400}, "say": "At 400 K the coil resistance is about 40 % higher than at room temperature."}],
        [_q("When a pure metal is heated its resistance", ["Rises", "Falls", "Stays the same"], 0,
            "More lattice vibration scatters the electrons more."),
         _q("A four-wire ohmmeter is used so that", ["The lead resistance does not count", "The current is larger",
                                                       "The coil does not heat"], 0,
            "The voltage leads carry almost no current.")],
        [PGLAB, KITTEL, {"title": "Serway and Jewett, Physics for Scientists and Engineers, table of temperature "
                                  "coefficients of resistivity (20 °C)"}],
        {"reading": "alpha", "textbook": "mss_alpha"})


def thermoelectric_power() -> dict:
    return _mk(
        "thermoelectric-power", "msc-sweep-bench", "Thermoelectric power (Seebeck coefficient)",
        "Hold one junction of a thermocouple at room temperature and heat the other, read the thermo-EMF against the "
        "temperature difference and find the Seebeck coefficient from the slope.",
        "msc_seebeck", {"dT": 50.0, "S": 40.96, "Voff": 1.5, "Tcold": 293.0},
        [knob("dT", "Hot junction above cold (ΔT)", "dT", 0, 100, 1, 50, "K"),
         knob("S", "This thermocouple (its coefficient is hidden)", "S", 5, 80, 0.01, 40.96, "µV/K", hidden=True)],
        [inst("V", "readout", "Thermo-EMF", "V", unit="µV", lc=0.1, digits=1),
         inst("gr", "graph", "Thermo-EMF against ΔT", "V", x="p.dT", xlabel="ΔT (K)", dots=True)],
        ["Put the cold junction in a beaker of water at room temperature and the hot junction in the oil bath.",
         "Zero the microvoltmeter with the junctions at the same temperature.",
         "Heat the bath and read the EMF at ΔT = 10, 20, ... 90 K.",
         "Plot the EMF against ΔT; the slope is the Seebeck coefficient.",
         "The small intercept is the meter's zero error; it does not change the slope."],
        "Where two different metals are joined, the electrons diffuse differently in each when the junction is "
        "warmer than the rest of the circuit, and an EMF appears. Over a modest range it is proportional to the "
        "temperature difference of the two junctions, V = SΔT, and S, in microvolts per kelvin, is the Seebeck "
        "coefficient of that pair. A straight-line fit takes out the meter's zero error.",
        "The oil bath is hot: use the stirrer, not your hand, and keep the thermometer clear of the heater.",
        [{"say": "A thermocouple with one junction in a beaker of water and one in a heated oil bath, read on a microvoltmeter."},
         {"set": {"dT": 80}, "say": "At ΔT = 80 K the EMF is a few millivolts."}],
        [_q("The Seebeck EMF of a thermocouple is proportional to", ["The temperature difference of the junctions",
                                                                       "The temperature of the hot junction only",
                                                                       "The length of the wires"], 0,
            "V = S ΔT over a modest range."),
         _q("The intercept of the V against ΔT line is", ["The meter's zero error", "The Seebeck coefficient",
                                                            "The cold junction temperature"], 0,
            "A zero-offset shifts the line, not its slope.")],
        [PGLAB, KITTEL, {"title": "NIST ITS-90 thermocouple reference tables (EMF at 100 °C, 0 °C reference)"}],
        {"reading": "S", "textbook": "mss_S"})


def ionic_conductivity() -> dict:
    return _mk(
        "ionic-conductivity", "msc-sweep-bench", "Ionic conductivity of an alkali halide",
        "Measure the resistance of an ionic crystal pellet from 400 to 650 K and find the activation energy for the "
        "movement of vacancies from the slope of ln(σT) against 1/T.",
        "msc_ionic", {"T": 500.0, "Ea": 0.8, "A": 4.0e7, "Lp": 0.002, "Ap": 1.0e-4},
        [knob("T", "Furnace temperature", "T", 400, 650, 1, 500, "K"),
         knob("Ea", "This crystal (its activation energy is hidden)", "Ea", 0.3, 1.5, 0.01, 0.8, "eV", hidden=True)],
        [inst("R", "readout", "Pellet resistance", "R", k=1e-6, unit="MΩ", digits=3),
         inst("gr", "graph", "ln(σT) against T", "lnsT", x="p.T", xlabel="T (K)", dots=True)],
        ["Place the pellet between the two silver electrodes and the spring contact in the furnace.",
         "Heat to 400 K and wait until the thermocouple is steady.",
         "Read the pellet resistance with the electrometer, then raise the furnace in 25 K steps.",
         "Work out σ = L / (R A) at every temperature.",
         "Plot ln(σT) against 1/T: the slope is −Ea/k."],
        "In an ionic crystal charge is carried by vacancies that hop from site to site, and each hop needs thermal "
        "energy, so σT = A exp(−Ea/kT). The conductivity rises steeply with temperature; a plot of ln(σT) against "
        "1/T is a straight line of slope −Ea/k, from which the activation energy follows. The factor T in σT "
        "comes from the attempt frequency of the hopping ion. Ionic conduction is read in the extrinsic region, "
        "below the temperature where the intrinsic vacancies take over.",
        "The furnace and the pellet holder are hot: use the tongs. The electrometer input is high-impedance; keep "
        "the leads short and clear of the mains cable.",
        [{"say": "A pressed pellet between two electrodes inside a small furnace, with an electrometer reading its resistance."},
         {"set": {"T": 650}, "say": "At 650 K the resistance has fallen by more than an order of magnitude."}],
        [_q("The slope of ln(σT) against 1/T gives", ["−Ea/k", "Ea·k", "The band gap"], 0,
            "σT = A exp(−Ea/kT)."),
         _q("On heating, the conductivity of an ionic crystal", ["Rises steeply", "Falls", "Is unchanged"], 0,
            "More vacancies hop more often.")],
        [PGLAB, KITTEL, ILLUS],
        {"reading": "Ea", "textbook": "mss_Ea"})


def superconductor_rt() -> dict:
    return _mk(
        "superconductor-rt", "msc-sweep-bench", "Resistance of a high-Tc superconductor against temperature",
        "Cool a high-temperature superconductor in liquid nitrogen vapour, measure its resistance by the four-lead "
        "method as it warms and find the critical temperature Tc.",
        "msc_super", {"T": 100.0, "Tc": 92.0, "w": 1.0, "Rn100": 0.06, "I": 0.01},
        [knob("T", "Sample temperature", "T", 78, 140, 0.5, 100, "K"),
         knob("Tc", "This sample (its Tc is hidden)", "Tc", 60, 130, 0.1, 92, "K", hidden=True)],
        [inst("V", "readout", "Voltage across the bar", "V", k=1e6, unit="µV", lc=0.1, digits=1),
         inst("gr", "graph", "Resistance against temperature", "R", k=1000, x="p.T", xlabel="T (K)", dots=True)],
        ["Mount the bar on the cold finger with four spring contacts and a silicon-diode thermometer beside it.",
         "Pass a steady 10 mA through the outer leads and read the voltage on the inner pair.",
         "Cool the sample to about 80 K, then let it warm slowly.",
         "Read the voltage at every kelvin, and at every half kelvin through the fall.",
         "Plot R against T; Tc is where R has fallen to half its normal-state value."],
        "Below its critical temperature Tc a superconductor has no electrical resistance. Above it the sample is a "
        "poor metal whose resistance rises about linearly with T. The change takes place over a few kelvin, "
        "so Tc is quoted at the midpoint of the fall, where R has reached half the normal-state value extrapolated "
        "to that temperature. The four-lead method keeps the contact resistance out of the reading.",
        "Liquid nitrogen at 77 K causes cold burns and can displace the air in a closed room. Wear the face shield "
        "and cryogenic gloves, pour slowly, and never seal a vessel that contains it.",
        [{"say": "A pressed pellet of superconducting ceramic on a copper cold finger, four spring contacts, a diode thermometer."},
         {"set": {"T": 85}, "say": "Below the transition the voltage across the bar is zero."},
         {"set": {"T": 100}, "say": "Above it the bar has its normal resistance."}],
        [_q("At the critical temperature the resistance of a superconductor", ["Falls to zero", "Doubles", "Diverges"], 0,
            "That is the defining property of the superconducting state."),
         _q("Tc is quoted at the", ["Midpoint of the transition", "Highest temperature of the run",
                                      "Start of the cooling"], 0,
            "R has fallen to half its normal-state value.")],
        [PGLAB, KITTEL, {"title": "Tinkham, Introduction to Superconductivity, 2nd ed. (McGraw-Hill, 1996)"}],
        {"reading": "Tc", "textbook": "mss_Tc_sc"})


def magnetoresistance() -> dict:
    return _mk(
        "magnetoresistance", "msc-sweep-bench", "Transverse magnetoresistance of a semiconductor",
        "Measure the resistance of a semiconductor bar in a transverse magnetic field and find the carrier mobility "
        "from the slope of the resistance against B squared.",
        "msc_magres", {"B": 0.0, "mu": 7.7, "R0": 2.0, "xi": 1.0, "I": 0.005},
        [knob("B", "Magnetic field", "B", 0, 0.8, 0.01, 0, "T"),
         knob("mu", "This crystal (its mobility is hidden)", "mu", 0.05, 10, 0.01, 7.7, "m²/V s", hidden=True)],
        [inst("R", "readout", "Bar resistance", "R", unit="Ω", lc=0.001, digits=3),
         inst("gr", "graph", "Resistance against field", "R", x="p.B", xlabel="B (T)", dots=True)],
        ["Put the bar between the pole pieces with its flat face square to the field and its current along its length.",
         "Read the resistance with the magnet off.",
         "Raise the field in 0.1 T steps and read the resistance each time.",
         "Plot R against B²: it is a straight line.",
         "The mobility follows from the slope divided by the zero-field resistance."],
        "A magnetic field perpendicular to the current bends the carriers sideways. Once the Hall field has balanced "
        "the average force, carriers of different speed are still deflected, so their paths lengthen and the "
        "resistance rises: Δρ/ρ0 = ξ(μB)². This lab takes ξ = 1, a good first approximation for a clean crystal; "
        "ξ in a real sample depends on the scattering. The effect is large in high-mobility crystals and tiny in "
        "silicon.",
        "Keep watches, credit cards and steel tools well away from the magnet. The coils warm up: do not leave "
        "the magnet at full current.",
        [{"say": "A thin bar between the poles of an electromagnet, a gaussmeter probe in the gap beside it."},
         {"set": {"B": 0.6}, "say": "At 0.6 T the resistance of a high-mobility bar is many times its zero-field value."}],
        [_q("Magnetoresistance grows as", ["B squared", "B", "The square root of B"], 0, "Δρ/ρ ∝ (μB)²."),
         _q("It is largest in", ["A high-mobility semiconductor", "A good metal at room temperature", "An insulator"], 0,
            "μB measures the angle the carriers turn between collisions.")],
        [PGLAB, KITTEL, {"title": "S. M. Sze and K. K. Ng, Physics of Semiconductor Devices, 3rd ed. (Wiley, 2007): "
                                  "electron mobilities at 300 K"}],
        {"reading": "mu", "textbook": "mss_mu"})


def ferroelectric_curie() -> dict:
    return _mk(
        "ferroelectric-curie", "msc-sweep-bench", "Ferroelectric Curie temperature from the dielectric constant",
        "Measure the capacitance of a ferroelectric crystal plate as it is heated through its transition and find "
        "the Curie temperature and the Curie-Weiss law above it.",
        "msc_ferro", {"T": 340.0, "Tc": 322.15, "C": 3000.0, "eb": 5.0, "dl": 0.6, "Ap": 1.0e-4, "d": 1.0e-3},
        [knob("T", "Hot-stage temperature", "T", 300, 360, 0.1, 340, "K"),
         knob("Tc", "This crystal (its transition is hidden)", "Tc", 280, 380, 0.05, 322.15, "K", hidden=True)],
        [inst("e", "readout", "Dielectric constant", "eps", digits=1),
         inst("gr", "graph", "Dielectric constant against temperature", "eps", x="p.T", xlabel="T (K)", dots=True)],
        ["Mount the crystal plate between the two electrodes on the hot stage and connect the LCR meter at 1 kHz.",
         "Heat slowly from 300 K, reading the capacitance every 2 K, and every 0.5 K near the peak.",
         "Work out the dielectric constant from ε = C d / (ε0 A).",
         "The peak of ε against T is the Curie temperature.",
         "Above the peak plot 1/ε against T: it is a straight line cutting the axis at the Curie-Weiss temperature."],
        "At the Curie temperature a ferroelectric loses its spontaneous polarisation. The dielectric constant "
        "peaks sharply and, above Tc, follows the Curie-Weiss law ε = C/(T − Tc): the line of 1/ε against T has "
        "slope 1/C and cuts the temperature axis at Tc. For a second-order transition, as in triglycine sulphate, "
        "the Curie-Weiss temperature and Tc coincide, and the constant below Tc is half the constant above it.",
        "The stage and the crystal holder are hot. Triglycine sulphate is mildly toxic: handle the crystal with "
        "gloves and wash your hands after the experiment.",
        [{"say": "A thin ferroelectric plate with two electrodes on a heated stage, read by an LCR meter."},
         {"set": {"T": 322}, "say": "At the Curie temperature the dielectric constant is at its maximum."}],
        [_q("Above Tc the dielectric constant follows", ["The Curie-Weiss law", "Ohm's law", "Hooke's law"], 0,
            "ε = C/(T − Tc)."),
         _q("A plot of 1/ε against T above Tc is", ["A straight line", "A parabola", "A horizontal line"], 0,
            "1/ε = (T − Tc)/C.")],
        [PGLAB, KITTEL, {"title": "M. E. Lines and A. M. Glass, Principles and Applications of Ferroelectrics (Oxford, "
                                  "1977): triglycine sulphate Tc = 49 °C, Curie constant about 3000 K"}],
        {"reading": "Tc", "textbook": "mss_Tc_fe", "tol": 0.01})


def ferrite_curie() -> dict:
    return _mk(
        "ferrite-curie", "msc-sweep-bench", "Curie temperature of a ferrite",
        "Heat a coil wound on a ferrite core and watch its inductance collapse at the Curie temperature; find Tc by "
        "the tangent method.",
        "msc_curie", {"T": 300.0, "Tc": 573.0, "K": 40.0, "L0": 2.0e-3, "w": 3.0},
        [knob("T", "Furnace temperature", "T", 250, 1150, 1, 300, "K"),
         knob("Tc", "This core (its Curie point is hidden)", "Tc", 250, 1100, 0.5, 573, "K", hidden=True)],
        [inst("L", "readout", "Coil inductance", "L_mH", unit="mH", lc=0.01, digits=2),
         inst("gr", "graph", "Inductance against temperature", "L_mH", x="p.T", xlabel="T (K)", dots=True)],
        ["Put the coil and its core in the furnace, with the thermocouple touching the core.",
         "Measure the inductance at room temperature with the LCR meter at 1 kHz.",
         "Heat in steps, reading L at each step, and take smaller steps where it falls fastest.",
         "Draw the tangent to the steepest part of the fall and the horizontal baseline at high T.",
         "The temperature where they meet is the Curie temperature."],
        "A ferromagnet or ferrite has a large permeability, so a coil on it has a large inductance. At the Curie "
        "temperature the spontaneous magnetisation vanishes and the core becomes paramagnetic, so μ falls to about "
        "1 and the inductance drops to that of the coil alone. Because the fall is spread over a few kelvin, Tc is "
        "taken from the intersection of the tangent at the steepest part with the high-temperature baseline.",
        "The furnace is hot: use the tongs and let it cool before opening. Do not use the LCR meter's bias "
        "supply on the coil.",
        [{"say": "A coil wound on a ferrite ring, inside a small furnace with a thermocouple and an LCR meter."},
         {"set": {"T": 570}, "say": "Just below the Curie temperature the inductance is falling fast."}],
        [_q("At the Curie temperature a ferromagnet becomes", ["Paramagnetic", "Superconducting", "Diamagnetic"], 0,
            "Thermal agitation destroys the spontaneous alignment."),
         _q("Above Tc the inductance of the coil", ["Drops to its air-core value", "Doubles", "Is unchanged"], 0,
            "μ falls to about 1.")],
        [PGLAB, KITTEL, {"title": "Cullity and Graham, Introduction to Magnetic Materials, 2nd ed. (Wiley, 2009)"}],
        {"reading": "Tc", "textbook": "mss_Tc_cu"})


def liquid_crystal_transition() -> dict:
    return _mk(
        "liquid-crystal-transition", "msc-sweep-bench", "Transition temperature of a liquid crystal",
        "Heat a nematic liquid-crystal cell between crossed polarisers and find the temperature at which the "
        "transmitted light disappears: the nematic to isotropic transition.",
        "msc_lc", {"T": 300.0, "Tni": 308.15, "dn0": 0.32, "d": 2.4e-6, "lam": 6.328e-7, "I0": 1.0, "stray": 0.004},
        [knob("T", "Hot-stage temperature", "T", 295, 325, 0.05, 300, "K"),
         knob("Tni", "This liquid crystal (its clearing point is hidden)", "Tni", 290, 330, 0.05, 308.15, "K", hidden=True)],
        [inst("I", "readout", "Photodiode signal", "I", digits=3),
         inst("gr", "graph", "Transmitted light against temperature", "I", x="p.T", xlabel="T (K)", dots=True)],
        ["Place the cell on the hot stage between crossed polarisers with its axis at 45° to them.",
         "Shine the He-Ne laser through it onto the photodiode.",
         "Heat slowly, reading the photodiode and the stage temperature every 0.5 K.",
         "Near the transition read every 0.1 K.",
         "The temperature at which the signal drops to the dark level is the transition temperature."],
        "A nematic liquid crystal is birefringent: its molecules lie, on average, along one direction, and the order "
        "falls as it is warmed (Haller's law). Between crossed polarisers a birefringent cell passes light "
        "I = I0 sin²(π Δn d/λ). The birefringence Δn follows the order parameter, so the signal moves through bright "
        "and dark fringes on heating. At the nematic-isotropic temperature the order disappears, Δn is zero and the "
        "field stays dark.",
        "Do not look into the laser beam or its reflections; keep the beam below eye level. Keep the hot stage "
        "away from the polarisers' plastic mounts.",
        [{"say": "A thin liquid-crystal cell on a heated stage between crossed polarisers, a laser and a photodiode."},
         {"set": {"T": 304}, "say": "Just below the transition the cell is bright."},
         {"set": {"T": 312}, "say": "Above it the field is dark."}],
        [_q("Above the clearing point the cell between crossed polarisers is", ["Dark", "Bright", "Coloured"], 0,
            "The isotropic liquid is not birefringent."),
         _q("Haller's law describes how", ["The order parameter falls with temperature", "The cell is filled",
                                             "The laser is polarised"], 0,
            "S = (1 − 0.98 T/T*)^0.22.")],
        [PGLAB, {"title": "P. J. Collings and M. Hird, Introduction to Liquid Crystals (Taylor & Francis, 1997)"}],
        {"reading": "Tni", "textbook": "mss_Tni"})


def dielectric_lcr() -> dict:
    return _mk(
        "dielectric-lcr", "msc-sweep-bench", "Dielectric constant and loss with an LCR meter",
        "Measure the capacitance of a guarded parallel-plate cell with a disc of the sample between its plates, "
        "from 100 Hz to 1 MHz, and find the dielectric constant and the loss tangent.",
        "msc_diel", {"f": 1000.0, "es": 6.0, "einf": 3.0, "fr": 4.0e4, "Ap": 9.6e-4, "d": 1.0e-3},
        [knob("f", "Meter frequency", "f", 100, 1000000, 10, 1000, "Hz"),
         knob("es", "This sample (its dielectric constant is hidden)", "es", 1.5, 12, 0.01, 6, "", hidden=True)],
        [inst("C", "readout", "Capacitance", "C_pF", unit="pF", lc=0.01, digits=2),
         inst("D", "readout", "Loss tangent", "D", digits=4)],
        ["Zero the LCR meter with the cell open (open compensation) and then with the plates shorted.",
         "Clamp the sample disc between the plates and measure its thickness with a micrometer.",
         "Measure C and tan δ at 100, 200, 500 Hz, 1, 2, 5, 10, 20, 50, 100, 200, 500 kHz and 1 MHz.",
         "Work out ε' = C d / (ε0 A) at each frequency.",
         "The low-frequency value is the static dielectric constant."],
        "A dielectric between the plates of a capacitor multiplies its capacitance by the dielectric constant ε'. "
        "A polar material cannot follow a field that reverses faster than its dipoles relax: ε' falls round the "
        "relaxation frequency and the loss tan δ peaks there (Debye relaxation). A non-polar solid such as "
        "polytetrafluoroethylene is flat over the whole range. The disc is smaller than the guard ring so that edge "
        "fields are not counted.",
        "The test voltage is small, but the plates are exposed: switch the meter off before changing the sample.",
        [{"say": "A guarded parallel-plate cell, a sample disc, a micrometer and an LCR meter."},
         {"set": {"f": 1000000}, "say": "At 1 MHz a polar sample has relaxed: the dielectric constant has fallen."}],
        [_q("With a dielectric between the plates the capacitance", ["Increases by the factor ε'", "Falls",
                                                                    "Is unchanged"], 0, "C = ε0 ε' A/d."),
         _q("The loss tangent of a polar material peaks near", ["The relaxation frequency", "Zero frequency",
                                                                  "The highest frequency"], 0,
            "ε'' = (εs − ε∞) x/(1 + x²) with x = f/fr.")],
        [PGLAB, KITTEL, ILLUS],
        {"reading": "er", "textbook": "mss_er"})


# ====================================================================================== hysteresis loops
def _loop(id: str, title: str, aim: str, params: dict, hunit: str, hk: float, hmax: float, hval: float, hhid_max: float,
          steps: list, theory: str, safety: str, sources: list, hc_label: str, hc_unit: str, hc_k: float,
          tours: list, sample_note: str, hc_min: float) -> dict:
    return _mk(
        id, "msc-loop-bench", title, aim, "msc_loop", params,
        [knob("H0", "Drive amplitude", "H0", 1, hmax, 1, hval, hunit, hk),
         knob("Hc", hc_label, "Hc", hc_min, hhid_max, 0.01, params["Hc"] / hc_k, hc_unit, hc_k, hidden=True)],
        [inst("M", "readout", "Loop value at H = 0 (remanence)", "M", digits=3),
         inst("gr", "graph", "The loop (rising branch)", "M", x="p.H", xlabel="H", dots=True)],
        steps, theory, safety, tours,
        [_q("The coercive field is the field that brings the magnetisation (or polarisation) to", ["Zero",
                                                                                                     "Saturation",
                                                                                                     "Its maximum"], 0,
            "It is where the loop cuts the field axis."),
         _q("The area inside the loop is", ["The energy lost per cycle per unit volume", "The saturation value",
                                              "The remanence"], 0, "The area of an M-H or B-H loop is the energy "
                                                                    "dissipated in one cycle.")],
        sources, {"reading": "Hc", "textbook": "mss_Hc", "tol": 0.01}, group=SSP if id != "vsm-magnetisation" else MATS,
        chapter=CH_SS if id != "vsm-magnetisation" else CH_MS)


def bh_hysteresis() -> dict:
    return _loop(
        "bh-hysteresis", "B-H hysteresis loop of a transformer core",
        "Trace the B-H loop of a ferromagnetic ring on an oscilloscope and find its coercive field, remanence, "
        "saturation flux density and the energy lost per cycle.",
        {"H": 0.0, "Ms": 1.5, "Hc": 80.0, "a": 32.0, "H0": 400.0, "br": 1.0, "kind": 1.0},
        "A/m", 1.0, 800, 400, 200,
        ["Connect the primary of the ring through the sense resistor to the 50 Hz supply, and its secondary through "
         "the integrator to the Y plates.",
         "Calibrate H and B: H = N1 V_x / (R l), B = R C V_y / (N2 A).",
         "Raise the drive until the loop just stops growing: the ring is saturated.",
         "Read the field where the loop cuts the H axis (the coercive field) and the B value where it cuts the B axis.",
         "Capture two smaller loops to see how the loop shrinks when the core is not saturated."],
        "Magnetising a ferromagnet and then reversing the field, the flux density B lags behind H. Going round a "
        "full cycle draws the hysteresis loop. Where it crosses B = 0 is the coercive field Hc; where it crosses "
        "H = 0 is the remanent flux Br; the flat tops are the saturation Bs. The area inside the loop is the "
        "energy dissipated in the core per cycle per unit volume. A soft core has a thin loop and small Hc; a "
        "permanent magnet has a wide one. The coercive field is only the material's own value once the loop is "
        "driven to saturation.",
        "The primary carries the mains supply. The ring and the board are isolated, but keep the supply off while "
        "changing connections.",
        [PGLAB, KITTEL, {"title": "Cullity and Graham, Introduction to Magnetic Materials, 2nd ed. (Wiley, 2009), "
                                      "chapter 1 and 9"}, ILLUS],
        "Coercive field of this core", "A/m", 1.0,
        [{"say": "A toroidal core with two windings, a sense resistor, an integrator and a scope in X-Y mode."},
         {"set": {"H0": 400}, "say": "Driven far past saturation the loop has its full width."},
         {"set": {"H0": 40}, "say": "A weak drive gives a narrow loop with a smaller apparent coercive field."}],
        "Transformer steel ring (illustrative)", 20.0)


def pe_hysteresis() -> dict:
    return _loop(
        "pe-hysteresis", "P-E hysteresis loop of a ferroelectric",
        "Trace the polarisation-field loop of a barium titanate ceramic in a Sawyer-Tower circuit and find its "
        "coercive field, remanent polarisation and saturation polarisation.",
        {"H": 0.0, "Ms": 0.26, "Hc": 500000.0, "a": 200000.0, "H0": 2000000.0, "br": 1.0, "kind": 2.0},
        "kV/cm", 1.0e5, 40, 20, 100,
        ["Connect the sample in series with a large reference capacitor; the sample voltage goes to X through a "
         "divider and the reference voltage to Y.",
         "Calibrate the field E = V/d and the polarisation P = C_ref V_y / A.",
         "Raise the amplitude until the loop saturates.",
         "Read the field where the loop cuts the E axis (coercive field) and the P value at E = 0 (remanent polarisation).",
         "Capture a smaller loop to see the effect of an unsaturated drive."],
        "A ferroelectric has a spontaneous electric polarisation that can be reversed by a field. Plotting P "
        "against E as the field is cycled draws a hysteresis loop like the B-H loop of a ferromagnet: the "
        "coercive field Ec is where P = 0, the remanent polarisation Pr is the value at E = 0 and the "
        "saturation polarisation Ps the plateau. In the Sawyer-Tower circuit the charge on the large series "
        "capacitor equals that on the sample, so its voltage is proportional to P.",
        "The drive reaches kilovolts across the sample: keep the sample in its guarded holder, switch off the "
        "supply and discharge the sample before touching it.",
        [PGLAB, KITTEL, {"title": "Lines and Glass, Principles and Applications of Ferroelectrics (Oxford, 1977): "
                                  "BaTiO3 spontaneous polarisation about 0.26 C/m2 at room temperature"}, ILLUS],
        "Coercive field of this ceramic", "kV/cm", 1.0e5,
        [{"say": "A ceramic disc with silver electrodes in a guarded holder, a reference capacitor and a scope in X-Y mode."},
         {"set": {"H0": 20}, "say": "Driven well past the coercive field the loop is a full ferroelectric loop."}],
        "Barium titanate ceramic (illustrative coercive field)", 1.0e5 / 1.0e5 * 1.0)


def vsm_magnetisation() -> dict:
    return _loop(
        "vsm-magnetisation", "Magnetisation of magnetic nanoparticles by VSM",
        "Record the M-H loop of magnetite nanoparticles in a vibrating-sample magnetometer and find the "
        "saturation magnetisation, the coercive field and the remanence.",
        {"H": 0.0, "Ms": 60.0, "Hc": 8000.0, "a": 6000.0, "H0": 400000.0, "br": 1.0, "kind": 3.0},
        "kA/m", 1000.0, 800, 400, 50,
        ["Weigh the powder into the holder and mount it between the pole pieces on the vibrating rod.",
         "Set the sweep range to ± 400 kA/m and start the sweep.",
         "Read the saturation magnetisation (the plateau) in A m²/kg.",
         "Read the field where the loop cuts the H axis: the coercive field.",
         "Read the remanence at H = 0, and compare it with the saturation."],
        "A vibrating-sample magnetometer moves the sample at a fixed frequency between pick-up coils; the signal "
        "induced is proportional to its magnetic moment. Divided by the mass it gives the magnetisation per "
        "kilogram. For nanoparticles the loop depends on size: large particles are ferrimagnetic with a wide loop, "
        "particles below a critical size become superparamagnetic and show no coercivity at all. The plateau "
        "gives the saturation magnetisation Ms; the coercive field and the remanence are read from the loop.",
        "The magnet is strong: keep steel tools, watches and pacemakers away. The instrument in the lab is a "
        "shared facility instrument; this simulated bench demonstrates its measurement, not its operation.",
        [PGLAB, CULLITY, {"title": "Cullity and Graham, Introduction to Magnetic Materials, 2nd ed.: magnetite "
                                   "saturation about 92 A m2/kg (bulk)"}, ILLUS],
        "Coercive field of this powder", "kA/m", 1000.0,
        [{"say": "A powder holder on the vibrating rod between the poles, with pick-up coils."},
         {"set": {"H0": 400}, "say": "The sweep to 400 kA/m saturates the nanoparticles."}],
        "Magnetite nanoparticles (illustrative)", 0.5)


def nano_ferroelectric() -> dict:
    return _loop(
        "nano-ferroelectric", "Ferroelectric loop of a nanocrystalline ceramic",
        "Trace the P-E loop of a nanocrystalline barium titanate pellet and compare its coercive field and "
        "remanent polarisation with the coarse-grained ceramic.",
        {"H": 0.0, "Ms": 0.12, "Hc": 800000.0, "a": 320000.0, "H0": 3000000.0, "br": 1.0, "kind": 2.0},
        "kV/cm", 1.0e5, 60, 30, 150,
        ["Connect the pellet in the Sawyer-Tower circuit and calibrate E and P as for the bulk ceramic.",
         "Raise the amplitude until the loop saturates.",
         "Read the coercive field and the remanent polarisation.",
         "Compare them with the coarse-grained ceramic's loop.",
         "Note how the loop is slimmer and its coercive field larger."],
        "In a ceramic of nanometre-sized grains each grain holds fewer domains, and grain boundaries pin the "
        "walls that move when the polarisation reverses. The coercive field is larger and the remanent polarisation "
        "smaller than in the coarse-grained ceramic. The measurement is the same Sawyer-Tower trace: Ec is where "
        "P = 0, Pr the value at E = 0.",
        "The drive reaches kilovolts across the pellet: keep it in its guarded holder and discharge it before "
        "touching it.",
        [PGLAB, KITTEL, ILLUS],
        "Coercive field of this pellet", "kV/cm", 1.0e5,
        [{"say": "A thin nanocrystalline ceramic pellet in a guarded holder, a reference capacitor and a scope."},
         {"set": {"H0": 30}, "say": "The loop of the nanocrystalline pellet is wider but lower than a coarse ceramic's."}],
        "Nanocrystalline barium titanate (illustrative)", 1.0)


# ====================================================================================== diffraction
def xrd_powder_photograph() -> dict:
    return _mk(
        "xrd-powder-photograph", "msc-xrd-bench", "Crystal structure by X-ray powder diffraction",
        "Record the powder diffraction pattern of a cubic material with Cu K-alpha X-rays, index the lines from "
        "the allowed reflections of the lattice and find the lattice parameter.",
        "msc_xrd", {"tth": 30.0, "lam": 1.5406e-10, "a": 4.0495e-10, "ltype": 3.0, "Z1": 13.0, "Z2": 0.0,
                    "Lx": 2.0e-7, "eps": 0.0, "binst": 0.1, "K": 0.9, "bg": 40.0, "I0": 10000.0},
        [knob("tth", "Detector angle 2θ", "tth", 20, 120, 0.02, 30, "°")],
        [inst("I", "readout", "Counts", "I", digits=0),
         inst("gr", "graph", "Counts against 2θ", "I", x="p.tth", xlabel="2θ (°)", dots=True)],
        ["Pack the powder into the holder with a flat surface and mount it on the goniometer.",
         "Set the generator to 40 kV and 20 mA and open the shutter behind the interlocked cabinet door.",
         "Scan 2θ from 20° to 120° at 0.02° steps.",
         "Find the peak positions, work out sin²θ for each and take the ratios to the first line.",
         "Compare the ratio pattern with BCC, FCC and diamond lattices, index the lines and calculate a from the "
         "highest-angle line with a = λ√N / (2 sinθ)."],
        "X-rays reflect from a set of lattice planes only when Bragg's law 2d sinθ = λ is satisfied. For a cubic "
        "crystal d = a/√(h²+k²+l²), so sin²θ ∝ N = h²+k²+l². The structure factor kills some reflections: a "
        "body-centred lattice needs h+k+l even, a face-centred lattice needs h, k, l all odd or all even, and the "
        "diamond structure also loses h+k+l = 4n+2. The observed sequence of N therefore identifies the lattice. "
        "The most accurate a comes from the line at the highest angle, where the error in θ matters least. "
        "Relative line heights in this simulation use a simple scattering-factor model: positions are exact, "
        "intensities are illustrative.",
        "The X-ray tube is interlocked: never bypass the cabinet door switch. Radiation badges must be worn, and "
        "the shutter is opened only from outside the cabinet.",
        [{"say": "A powder diffractometer: tube, powder holder on the goniometer, and a detector."},
         {"set": {"tth": 38.5}, "say": "At 38.5° the detector sits on the first (111) line of aluminium."}],
        [_q("A face-centred cubic lattice shows reflections for", ["h, k, l all odd or all even",
                                                                    "h + k + l even", "Every h, k, l"], 0,
            "The structure factor of an FCC lattice is zero for mixed parity."),
         _q("The best value of a comes from", ["The line at the highest angle", "The first line",
                                                "The strongest line"], 0, "Δa/a = cotθ Δθ is smallest there.")],
        [PGLAB, CULLITY, {"title": "ICDD / CRC Handbook: lattice parameters of Si, Ge, NaCl, Al, Cu and W"}],
        {"reading": "a", "textbook": "mss_a", "tol": 0.005}, group=MATS, chapter=CH_SS, topic="Crystal structure")


def xrd_size_strain() -> dict:
    return _mk(
        "xrd-size-strain", "msc-xrd-bench", "Crystallite size and strain by X-ray diffraction",
        "Measure the widths of the diffraction lines of a nanocrystalline powder, correct them for the "
        "instrument and find the crystallite size and micro-strain from a Williamson-Hall plot.",
        "msc_xrd", {"tth": 30.0, "lam": 1.5406e-10, "a": 3.6149e-10, "ltype": 3.0, "Z1": 29.0, "Z2": 0.0,
                    "Lx": 3.0e-8, "eps": 0.002, "binst": 0.1, "K": 0.9, "bg": 40.0, "I0": 10000.0},
        [knob("tth", "Detector angle 2θ", "tth", 20, 120, 0.02, 30, "°"),
         knob("Lx", "This powder (its crystallite size is hidden)", "Lx", 5, 300, 0.1, 30, "nm", 1e-9, hidden=True)],
        [inst("I", "readout", "Counts", "I", digits=0),
         inst("gr", "graph", "Counts against 2θ", "I", x="p.tth", xlabel="2θ (°)", dots=True)],
        ["Mount the nanocrystalline powder and scan 2θ from 20° to 120° in 0.02° steps.",
         "Measure the full width at half maximum of every line.",
         "Subtract the instrumental width (from the standard run) in quadrature.",
         "Plot β cosθ against 4 sinθ (Williamson-Hall).",
         "The intercept is Kλ/L and the slope is the strain."],
        "Crystals smaller than about 100 nm broaden a diffraction line: Scherrer's formula gives the width "
        "β = Kλ/(L cosθ). A lattice strained by defects broadens it differently, β = 4ε tanθ. The "
        "two add, so β cosθ = Kλ/L + 4ε sinθ: a straight line against 4 sinθ whose intercept gives the size and "
        "whose slope gives the strain. The instrument itself has a width, which is subtracted in quadrature "
        "before the plot. Transmission electron microscopy is a facility technique; this simulated bench "
        "demonstrates the X-ray measurement only.",
        "The X-ray tube is interlocked: never bypass the cabinet door switch. Radiation badges must be worn.",
        [{"say": "The same diffractometer with a nanocrystalline powder: the lines are broader than a coarse powder's."}],
        [_q("A smaller crystallite size gives", ["Broader lines", "Narrower lines", "Shifted lines"], 0,
            "β = Kλ/(L cosθ)."),
         _q("In a Williamson-Hall plot the intercept gives", ["The crystallite size", "The strain",
                                                                "The lattice parameter"], 0, "Intercept = Kλ/L.")],
        [PGLAB, CULLITY, {"title": "G. K. Williamson and W. H. Hall, Acta Metallurgica 1 (1953) 22"}],
        {"reading": "L_wh", "textbook": "mss_L", "tol": 0.04}, group=MATS, chapter=CH_MS, topic="Crystallite size")


# ====================================================================================== magnetic susceptibility
def quincke_susceptibility() -> dict:
    return _mk(
        "quincke-susceptibility", "msc-quincke-bench", "Magnetic susceptibility of a liquid by Quincke's method",
        "Measure the rise of a paramagnetic solution in one limb of a U-tube placed between the poles of an "
        "electromagnet and find the magnetic susceptibility.",
        "msc_quincke", {"I": 0.0, "kB": 0.4, "c": 1.0, "chim": 13660.0, "chiw": -9.05e-6, "rho": 1100.0},
        [knob("I", "Magnet current", "I", 0, 2, 0.05, 0, "A"),
         knob("chim", "This salt (its molar susceptibility is hidden)", "chim", 100, 20000, 1, 13660, "10⁻⁶ cm³/mol", hidden=True)],
        [inst("h", "readout", "Level rise", "h_mm", unit="mm", lc=0.01, digits=2),
         inst("gr", "graph", "Rise against field", "h_mm", x="p.I", xlabel="I (A)", dots=True)],
        ["Fill the U-tube with the solution so that one meniscus lies midway between the pole faces.",
         "Read the meniscus with the travelling microscope with the magnet off.",
         "Raise the current in steps and read the new meniscus position at each step.",
         "Calibrate B against the current with the gaussmeter.",
         "Plot the rise h against B²; the slope gives the volume susceptibility."],
        "A paramagnetic liquid is drawn into a magnetic field, a diamagnetic one is pushed out. The magnetic "
        "pressure χB²/2μ0 on the meniscus balances the weight of the raised column, so h = χB²/(2μ0ρg) and "
        "a plot of h against B² is a straight line. A solution adds the solvent's susceptibility to the "
        "solute's, χ = χ(water) + 4π χm c /1000, so the molar susceptibility of the salt comes out once the "
        "solvent's value is subtracted. Without the solute (a water-only tube) the same set-up measures the "
        "diamagnetism of water.",
        "The magnet is strong: keep steel tools and watches away. Manganese and iron salts are harmful if "
        "swallowed: wear gloves and wipe up any spill.",
        [{"say": "A U-tube with one limb between the poles of an electromagnet, a gaussmeter and a travelling microscope."},
         {"set": {"I": 1.5}, "say": "At 1.5 A the meniscus has risen by about a millimetre."}],
        [_q("A paramagnetic liquid in the field", ["Rises", "Falls", "Stays level"], 0,
            "It is drawn into the strong field."),
         _q("The rise is proportional to", ["B squared", "B", "1/B"], 0, "The pressure is χB²/(2μ0).")],
        [PGLAB, {"title": "CRC Handbook of Chemistry and Physics, 'Magnetic susceptibility of the elements and "
                          "inorganic compounds' (molar, cgs)"}, KITTEL],
        {"reading": "chi", "textbook": "mss_chi"})


# ====================================================================================== vacuum and plasma
def gaede_vacuum_pump() -> dict:
    return _mk(
        "gaede-vacuum-pump", "msc-vacuum-bench", "Vacuum pump performance and Gaede's equation",
        "Pump down a chamber with a rotary pump, read the pressure with a Pirani gauge against time and find the "
        "pumping speed from Gaede's equation.",
        "msc_vac", {"t": 0.0, "V": 0.05, "S": 1.39e-3, "Q": 7.0e-4, "P0": 101325.0, "Psat": 5000.0},
        [knob("t", "Time since the pump started", "t", 0, 1500, 1, 0, "s"),
         knob("S", "This pump (its speed is hidden)", "S", 2e-4, 5e-3, 1e-5, 1.39e-3, "m³/s", hidden=True)],
        [inst("P", "readout", "Pirani gauge", "Ppir", unit="Pa", digits=2),
         inst("gr", "graph", "Pressure against time", "Ppir", x="p.t", xlabel="t (s)", dots=True)],
        ["Close the vent valve, start the rotary pump and start the stopwatch.",
         "The Pirani gauge is accurate only below about 1 kPa; note when it comes on scale.",
         "Read the pressure every 30 s until it stops falling: that is the ultimate pressure.",
         "Plot ln(P − Pu) against time: the slope is −S/V.",
         "Find the pumping speed S = V × slope, and check it with Gaede's equation between two readings."],
        "A chamber of volume V pumped at speed S with a small gas load Q obeys V dP/dt = −SP + Q. The pressure "
        "falls exponentially to the ultimate pressure Pu = Q/S: P = Pu + (P0 − Pu)e^(−St/V). Gaede's equation "
        "S = (V/t) ln[(P1 − Pu)/(P2 − Pu)] gives the speed from two readings a time t apart. A Pirani gauge "
        "measures the heat the gas conducts away from a hot wire: it saturates above about a kilopascal, "
        "so it cannot be read in the first minutes of a pump-down from atmosphere.",
        "Do not touch the pump housing: it runs hot. Vent the chamber slowly with the needle valve to avoid "
        "breaking the glass. Never switch an ionisation gauge on above 0.1 Pa.",
        [{"say": "A glass bell jar on a baseplate, a rotary pump, a Pirani gauge and a stopwatch."},
         {"set": {"t": 400}, "say": "After a few minutes the Pirani gauge comes on scale."},
         {"set": {"t": 1500}, "say": "The pressure has levelled off at the ultimate pressure."}],
        [_q("The ultimate pressure of a pump-down is set by", ["The gas load divided by the pumping speed",
                                                               "The volume of the chamber",
                                                               "The reading of the gauge"], 0, "Pu = Q/S."),
         _q("A Pirani gauge reads wrongly at atmospheric pressure because", ["It saturates", "It is switched off",
                                                                               "It is too hot"], 0,
            "Gas conduction no longer depends on pressure.")],
        [PGLAB, CHAMBERS, ILLUS], {"reading": "S", "textbook": "mss_Spump"}, group=VAC, chapter=CH_VP,
        topic="Vacuum physics")


def vacuum_gauges() -> dict:
    return _mk(
        "vacuum-gauges", "msc-vacuum-bench", "Gas pressure with different pumps and gauges",
        "Pump a chamber with a rotary pump backing a diffusion pump, read the pressure with a Pirani gauge and "
        "then an ionisation gauge, and find the ultimate pressure.",
        "msc_vac", {"t": 0.0, "V": 0.05, "S": 0.01, "Q": 5.0e-6, "P0": 10.0, "Psat": 5000.0},
        [knob("t", "Time since the diffusion pump took over", "t", 0, 200, 1, 0, "s"),
         knob("Q", "This system (its gas load is hidden)", "Q", 1e-7, 1e-4, 1e-7, 5e-6, "Pa m³/s", hidden=True)],
        [inst("P", "readout", "Pirani gauge", "Ppir", unit="Pa", digits=3),
         inst("gr", "graph", "Pirani pressure against time", "Ppir", x="p.t", xlabel="t (s)", dots=True)],
        ["Rough the chamber with the rotary pump until the Pirani gauge reads about 10 Pa.",
         "Switch on the diffusion pump heater and wait for it to warm up, then open the high-vacuum valve.",
         "Read the Pirani gauge: it floors at 0.1 Pa.",
         "Below 0.1 Pa switch on the ionisation gauge and read the pressure from it.",
         "Read the ultimate pressure once the ionisation gauge has stopped falling."],
        "A rotary pump alone cannot go below about 1 Pa; a diffusion pump, backed by a rotary pump, takes the "
        "pressure to the 10⁻⁴ Pa range. No single gauge covers the whole range: a Pirani gauge works from about "
        "1 kPa down to 0.1 Pa, an ionisation gauge from 0.1 Pa down to 10⁻⁶ Pa, and an ionisation gauge must "
        "never be switched on at a higher pressure. The ultimate pressure is the gas load divided by the "
        "pumping speed, Pu = Q/S.",
        "The diffusion pump oil and heater are hot, and the cooling water must be running before the heater "
        "is switched on. The ionisation gauge's filament burns out if it is switched on above 0.1 Pa.",
        [{"say": "A glass bell jar, a diffusion pump with a baffle and a rotary backing pump, a Pirani and an ionisation gauge."},
         {"set": {"t": 100}, "say": "The Pirani gauge has gone to its floor, and the ionisation gauge now reads."}],
        [_q("An ionisation gauge may be switched on only when the pressure is below", ["About 0.1 Pa", "1 kPa",
                                                                                        "Atmospheric pressure"], 0,
            "At higher pressure the filament burns out."),
         _q("A diffusion pump needs", ["A rotary backing pump", "No other pump", "A compressor"], 0,
            "It cannot exhaust to atmosphere.")],
        [PGLAB, CHAMBERS, ILLUS], {"reading": "Pu", "textbook": "mss_Pu"}, group=VAC, chapter=CH_VP,
        topic="Vacuum physics")


def plasma_glow_discharge() -> dict:
    return _mk(
        "plasma-glow-discharge", "msc-plasma-bench", "Production and characterisation of a plasma",
        "Strike a DC glow discharge in a low-pressure gas, record the current-voltage characteristic of a "
        "Langmuir probe and find the electron temperature, the plasma potential and the electron density.",
        "msc_langmuir", {"V": 0.0, "Te": 3.0, "Vp": 8.0, "ne": 1.0e16, "Ap": 2.0e-6, "M": 39.948},
        [knob("V", "Probe voltage", "V", -40, 20, 0.1, 0, "V"),
         knob("Te", "This discharge (its electron temperature is hidden)", "Te", 0.5, 8, 0.01, 3, "eV", hidden=True)],
        [inst("I", "readout", "Probe current", "I_uA", unit="µA", lc=0.1, digits=1),
         inst("gr", "graph", "Probe characteristic", "I_uA", x="p.V", xlabel="V (V)", dots=True)],
        ["Pump the tube down to 1 Pa, admit the gas to about 10 Pa and strike the discharge at the anode.",
         "Sweep the probe voltage from −40 V to +20 V with the source-meter.",
         "Read the ion saturation current at the far negative end of the sweep.",
         "Add the ion current back to each reading and plot ln(I_e) against V in the transition region.",
         "The slope of that line is 1/Te; the knee where the current saturates is the plasma potential."],
        "A small metal probe in a plasma collects electrons and ions. Far below the plasma potential only ions "
        "are collected (ion saturation, Bohm). Between the floating potential and the plasma potential the "
        "electrons, with a Maxwell distribution, are repelled in proportion to exp(−eΔV/kTe), so ln of the electron "
        "current is a straight line of slope 1/Te in volts. Above the plasma potential the probe draws the full "
        "electron saturation current. A cylindrical probe in a glow discharge reads true to within the usual "
        "10 to 30 % systematic uncertainty of the method; this simulation has none.",
        "The discharge needs a high voltage: keep the cover on the tube and never touch the electrodes while "
        "the supply is on. The glass and the cathode get hot.",
        [{"say": "A glass discharge tube with an anode, a cathode and a small probe wire, a gas inlet and a source-meter."},
         {"set": {"V": -35}, "say": "Far negative the probe collects only ions."},
         {"set": {"V": 20}, "say": "Far positive it collects the full electron saturation current."}],
        [_q("The slope of ln(I_e) against V is", ["1/Te (per volt)", "Te", "The plasma potential"], 0,
            "I_e ∝ exp(V/Te) with Te in electron-volts."),
         _q("A plasma is quasi-neutral. This means", ["Ions and electrons are almost equal in number", "It has no charge carriers",
                                                       "It is at room temperature"], 0,
            "The net charge is nearly zero on scales above the Debye length.")],
        [PGLAB, LIEBERMAN, CODATA, {"title": "IUPAC atomic weights: Ar 39.948, Ne 20.180, He 4.0026, H 1.008"}],
        {"reading": "Te", "textbook": "mss_Te"}, group=VAC, chapter=CH_VP, topic="Plasma physics")


BUILDERS = (metal_conductivity_t, thermoelectric_power, ionic_conductivity, superconductor_rt, magnetoresistance,
            ferroelectric_curie, ferrite_curie, liquid_crystal_transition, dielectric_lcr, bh_hysteresis,
            pe_hysteresis, vsm_magnetisation, nano_ferroelectric, xrd_powder_photograph, xrd_size_strain,
            quincke_susceptibility, gaede_vacuum_pump, vacuum_gauges, plasma_glow_discharge)
